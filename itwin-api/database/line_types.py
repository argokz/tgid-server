"""Тип линии (участок или оборудование) — как «Изменить тип объекта» десктопа gid8.

Тип линии — таблица карточки по lineID (``cxema1.cpp`` ``linef``): участок — heatPipeSections, насос —
pumps, задвижка — dampers и т. д. ``linesObj.typ`` с этим не связан. Смена типа (``gidr_add.cpp``
``ch_type_line``): карточка старой таблицы удаляется, в новой создаётся строка {lineID} с умолчаниями
таблицы; у регулятора давления и байпаса ещё pipelineSignID (1 — подающий, 2 — обратный) и h = 0.
Двухтрубная линия десктопа — пара участков подачи и обратки: тип меняется у обоих.

Меню десктопа (``getLineTypMenu``) не предлагает элеватор, радиатор, теплообменник и калорифер — они
только распознаются. Все изменения — операция топологии: одна транзакция, журнал отмены, dry-run.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from database.node_types import _existing_tables

# вид → таблица, в порядке меню десктопа
LINE_TYPES: dict[str, str] = {
    "line": "heatpipesections",
    "pump": "pumps",
    "pressregulator": "pressregulators",
    "consregulator": "consumptregulators",
    "damper": "dampers",
    "regarmature": "regularmatures",
    "bypass": "bypass",
    "diaphragm": "diaphragms",
    "pressdropregulator": "pressdropregulators",
    "reversevalve": "reversevalves",
}
# распознаются, но в меню смены типа их нет (как в десктопе)
DETECT_ONLY: dict[str, str] = {
    "elevator": "elevators",
    "radiator": "systemradiators",
    "heatexchanger": "heatexchangers",
    "airheater": "airheaters",
}
ALL_LINE_TABLES: dict[str, str] = {**LINE_TYPES, **DETECT_ONLY}
LINE_TYPE_LABELS: dict[str, str] = {
    "line": "Участок трубопровода",
    "pump": "Насос",
    "pressregulator": "Регулятор давления",
    "consregulator": "Регулятор расхода",
    "damper": "Задвижка",
    "regarmature": "Регулирующая арматура",
    "bypass": "Байпас",
    "diaphragm": "Диафрагма",
    "pressdropregulator": "Регулятор перепада давления",
    "reversevalve": "Обратный клапан",
    "elevator": "Элеватор",
    "radiator": "Радиатор",
    "heatexchanger": "Теплообменник",
    "airheater": "Калориферная установка",
    "none": "Без карточки",
}
# pipelineSignID и h при создании (ch_type_line: TIP_RD, TIP_BP)
_SIGNED = frozenset({"pressregulator", "bypass"})


def check_line_type(kind: str) -> str:
    k = str(kind or "").lower()
    if k not in LINE_TYPES:
        raise ValueError(f"Тип линии «{kind}» не задаётся (элеватор, радиатор, теплообменник, калорифер — как в десктопе)")
    return k


async def line_cards(conn, line_id: int) -> dict:
    """Тип линии и её карточки: {kind, cards: [{table, kind, id}], conflict}; kind none — карточки нет."""
    present = await _existing_tables(conn, ALL_LINE_TABLES.values())
    cards: list[dict] = []
    kinds: list[str] = []
    for kind, table in ALL_LINE_TABLES.items():
        if table not in present:
            continue
        rows = await conn.fetch(f"SELECT id FROM {table} WHERE lineid = $1 ORDER BY id", line_id)
        for r in rows:
            cards.append({"table": table, "kind": kind, "id": r["id"]})
        if rows:
            kinds.append(kind)
    return {"kind": kinds[0] if kinds else "none", "cards": cards, "conflict": len(kinds) > 1}


async def insert_line_card(conn, journal, line_id: int, kind: str, sign: Optional[int]) -> dict:
    """Строка карточки нового типа: {lineID} + умолчания таблицы (у участка — длина по геометрии)."""
    from database.topology import ground_length_sql

    table = LINE_TYPES[kind]
    if table not in await _existing_tables(conn, [table]):
        raise ValueError(f"В базе нет таблицы {table} — тип «{LINE_TYPE_LABELS[kind]}» недоступен")
    if kind == "line":
        # как create_line: длина паспорта — по геометрии до сантиметров; без геометрии — умолчание
        card_id = await conn.fetchval(
            f"""
            INSERT INTO heatpipesections (lineid, pipesectlength)
            SELECT $1, COALESCE(round({ground_length_sql('l.shape')}::numeric, 2), 1)
              FROM linesobj l WHERE l.id = $1
            RETURNING id
            """,
            line_id,
        )
    elif kind in _SIGNED:
        card_id = await conn.fetchval(
            f"INSERT INTO {table} (lineid, pipelinesignid, h) VALUES ($1, $2, 0) RETURNING id",
            line_id, 2 if sign == 3 else 1,
        )
    else:
        card_id = await conn.fetchval(f"INSERT INTO {table} (lineid) VALUES ($1) RETURNING id", line_id)
    journal.created(table, card_id)
    return {"table": table, "kind": kind, "id": card_id, "line_id": line_id}


async def change_line_type(
    line_id: int,
    kind: str,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    include_pair: bool = True,
    actor: Optional[str] = None,
) -> dict:
    """Смена типа линии (ch_type_line десктопа) вместе с парной трубой; dry_run — что удалится."""
    from database.topology import _lock_active, _run, _versions, find_pair_line

    new_kind = check_line_type(kind)

    async def body(conn, op):
        await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        pair = await find_pair_line(conn, line_id) if include_pair else None
        ids = [line_id] + ([pair["line_id"]] if pair else [])
        if pair:
            await _lock_active(conn, "line", [pair["line_id"]])
        signs = {r["id"]: r["externalsignlineid"] for r in await conn.fetch(
            "SELECT id, externalsignlineid FROM linesobj WHERE id = ANY($1::int[])", ids)}
        now = datetime.now()
        lines: list[dict] = []
        for lid in ids:
            info = await line_cards(conn, lid)
            if info["kind"] == new_kind and not info["conflict"]:
                lines.append({"line_id": lid, "old_kind": info["kind"], "removed_cards": [], "created_card": None})
                continue
            keep = next((c for c in info["cards"] if c["kind"] == new_kind), None)
            removed = [c for c in info["cards"] if c is not keep]
            for c in removed:
                await op.journal.capture_ids(conn, c["table"], [c["id"]])
                await conn.execute(f"DELETE FROM {c['table']} WHERE id = $1", c["id"])
            created = None if keep else await insert_line_card(conn, op.journal, lid, new_kind, signs.get(lid))
            await op.journal.capture_ids(conn, "linesobj", [lid])
            await conn.execute("UPDATE linesobj SET archivechangedate = $2 WHERE id = $1", lid, now)
            lines.append({"line_id": lid, "old_kind": info["kind"], "removed_cards": removed, "created_card": created})
        if all(not x["removed_cards"] and not x["created_card"] for x in lines):
            raise ValueError(f"Участок {line_id} уже имеет тип «{LINE_TYPE_LABELS[new_kind]}»")
        old_kind = lines[0]["old_kind"]
        result = {
            "line_id": line_id,
            "pair_line_id": pair["line_id"] if pair else None,
            "old_type": old_kind,
            "new_type": new_kind,
            "old_label": LINE_TYPE_LABELS.get(old_kind, old_kind),
            "new_label": LINE_TYPE_LABELS[new_kind],
            "lines": lines,
            "versions": await _versions(conn, "line", ids),
        }
        await op.audit("UPDATE", "linesobj", line_id, {"change_type": result})
        return result

    result = await _run(dry_run, body, "CHANGE_LINE_TYPE", actor)
    if not dry_run:
        # задвижки и прочее оборудование влияют на расчёт отключений
        from database.topology import invalidate_outage_cache

        invalidate_outage_cache()
    return result
