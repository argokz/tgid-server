"""Расчётный тип узла, заданный напор и подпитка — как в десктопе gid8.

Тип узла — таблица карточки по nodeID (``cxema1.cpp`` ``nodef``): US — без таблицы, PR — realConsumers,
PO — generalizedConsumers, IS — heatSources, HS — pumpStations, US2 — connectNodes. Это не
``nodes.nodeTypeID``: тот — конструктивный вид (павильон, камера, ввод…), правится в карточке узла.

Смена типа (``gidr_add.cpp`` ``ch_type_node2``): карточка старого типа удаляется, нового — создаётся
с умолчаниями таблицы (у потребителя схема 1.3, у источника температуры наружного воздуха — как
``addNode`` десктопа). Узел с внутренней схемой нельзя сделать потребителем; у потребителя при смене
типа внутренняя схема снимается (десктоп ``delCxemaFull``; здесь — мягко, removed = 1, с журналом).

Заданный напор (setPressNodes) и подпитка (refillNodes) — не тип, а дополнение к любому узлу из его
меню (``gidr_rbut.cpp`` ``viewZN``/``viewUP``/``delZN``/``delUP``): строка {nodeID}, значения — в карточке.

Все изменения — операции топологии: одна транзакция, журнал отмены, dry-run для предпросмотра.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

# порядок — приоритет, если у узла (ошибочно) карточки нескольких типов
NODE_TYPES: dict[str, Optional[str]] = {
    "PR": "realconsumers",
    "PO": "generalizedconsumers",
    "IS": "heatsources",
    "HS": "pumpstations",
    "US2": "connectnodes",
    "US": None,
}
NODE_TYPE_LABELS: dict[str, str] = {
    "US": "Узел",
    "PR": "Потребитель",
    "PO": "Обобщённый потребитель",
    "IS": "Источник тепла",
    "HS": "Насосная станция",
    "US2": "Узел соединения",
}
# Карточка нового узла: значения как у addNode десктопа (остальное — умолчания таблицы)
NEW_CARD_VALUES: dict[str, dict[str, object]] = {
    "PR": {"schemenum": "1.3"},
    "IS": {"tn_1": 8.0, "tn_5": -32.0},
}
CONSUMER_TYPES = frozenset({"PR", "PO"})

NODE_FLAGS: dict[str, str] = {"setpress": "setpressnodes", "refill": "refillnodes"}
NODE_FLAG_LABELS: dict[str, str] = {"setpress": "Узел с заданным напором", "refill": "Узел подпитки"}

# таблицы с колонкой name (подпись удаляемой карточки в предпросмотре)
_NAMED = frozenset({"realconsumers", "generalizedconsumers", "heatsources", "pumpstations"})


def check_node_type(node_type: str) -> str:
    t = str(node_type or "").upper()
    if t not in NODE_TYPES:
        raise ValueError(f"Неизвестный тип узла: {node_type}")
    return t


async def _existing_tables(conn, tables) -> set[str]:
    rows = await conn.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name = ANY($1::text[])",
        list(tables),
    )
    return {r["table_name"] for r in rows}


async def node_cards(conn, node_id: int) -> dict:
    """Тип узла и его карточки: {type, cards: [{table, id, name}], flags: {setpress, refill}, conflict}."""
    tables = [t for t in NODE_TYPES.values() if t] + list(NODE_FLAGS.values())
    present = await _existing_tables(conn, tables)
    cards: list[dict] = []
    types: list[str] = []
    for t, table in NODE_TYPES.items():
        if not table or table not in present:
            continue
        name_sql = "name" if table in _NAMED else "NULL::text"
        rows = await conn.fetch(f"SELECT id, {name_sql} AS name FROM {table} WHERE nodeid = $1 ORDER BY id", node_id)
        for r in rows:
            cards.append({"table": table, "type": t, "id": r["id"], "name": r["name"]})
        if rows:
            types.append(t)
    flags: dict[str, Optional[int]] = {}
    for flag, table in NODE_FLAGS.items():
        flags[flag] = (
            await conn.fetchval(f"SELECT id FROM {table} WHERE nodeid = $1 ORDER BY id LIMIT 1", node_id)
            if table in present else None
        )
    return {
        "type": types[0] if types else "US",
        "cards": cards,
        "flags": flags,
        # у узла карточки нескольких типов — ошибка данных; смена типа оставит одну
        "conflict": len(types) > 1,
    }


async def insert_node_card(conn, journal, node_id: int, node_type: str) -> Optional[dict]:
    """Карточка типа для узла (умолчания десктопа); None — у типа нет таблицы."""
    table = NODE_TYPES[node_type]
    if not table:
        return None
    if table not in await _existing_tables(conn, [table]):
        raise ValueError(f"В базе нет таблицы {table} — тип «{NODE_TYPE_LABELS[node_type]}» недоступен")
    values = {"nodeid": node_id, **NEW_CARD_VALUES.get(node_type, {})}
    cols = list(values)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(cols)))
    card_id = await conn.fetchval(
        f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING id",
        *values.values(),
    )
    journal.created(table, card_id)
    return {"table": table, "type": node_type, "id": card_id}


async def _inner_scheme(conn, node_id: int) -> dict:
    nodes = [r["id"] for r in await conn.fetch(
        "SELECT id FROM nodes WHERE internalnodeid = $1 AND COALESCE(removed, 0) = 0 ORDER BY id", node_id)]
    lines = [r["id"] for r in await conn.fetch(
        "SELECT id FROM linesobj WHERE internalnodeid = $1 AND COALESCE(removed, 0) = 0 ORDER BY id", node_id)]
    return {"nodes": nodes, "lines": lines}


async def change_node_type(
    node_id: int,
    node_type: str,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Смена расчётного типа узла (ch_type_node2 десктопа); dry_run — предпросмотр удаляемого."""
    from database.topology import _lock_active, _run, _soft_remove_heatpipesections, _versions

    new_type = check_node_type(node_type)

    async def body(conn, op):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
        info = await node_cards(conn, node_id)
        old_type = info["type"]
        if old_type == new_type and not info["conflict"]:
            raise ValueError(f"Узел {node_id} уже имеет тип «{NODE_TYPE_LABELS[new_type]}»")
        scheme = await _inner_scheme(conn, node_id)
        has_scheme = bool(scheme["nodes"] or scheme["lines"])
        if has_scheme and old_type not in CONSUMER_TYPES and new_type in CONSUMER_TYPES:
            raise ValueError("Нельзя изменить тип узла с внутренней схемой на потребитель (как в десктопе)")
        now = datetime.now()
        await op.journal.capture_ids(conn, "nodes", [node_id])

        # карточки, которые уходят: все, кроме одной карточки нового типа (если она уже есть)
        keep = next((c for c in info["cards"] if c["type"] == new_type), None)
        removed_cards = [c for c in info["cards"] if c is not keep]
        for c in removed_cards:
            await op.journal.capture_ids(conn, c["table"], [c["id"]])
            await conn.execute(f"DELETE FROM {c['table']} WHERE id = $1", c["id"])

        removed_scheme = {"nodes": [], "lines": []}
        if old_type == "PR" and new_type != "PR" and has_scheme:
            removed_scheme = scheme
            if scheme["lines"]:
                await op.journal.capture_ids(conn, "linesobj", scheme["lines"])
                await op.journal.capture(conn, "heatpipesections", "_r.lineid = ANY($1::int[])", scheme["lines"])
                await conn.execute(
                    "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                    scheme["lines"], now,
                )
                await _soft_remove_heatpipesections(conn, scheme["lines"], now)
            if scheme["nodes"]:
                await op.journal.capture_ids(conn, "nodes", scheme["nodes"])
                await conn.execute(
                    "UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                    scheme["nodes"], now,
                )

        created = None if keep else await insert_node_card(conn, op.journal, node_id, new_type)
        await conn.execute("UPDATE nodes SET archivechangedate = $2 WHERE id = $1", node_id, now)
        result = {
            "node_id": node_id,
            "old_type": old_type,
            "new_type": new_type,
            "old_label": NODE_TYPE_LABELS[old_type],
            "new_label": NODE_TYPE_LABELS[new_type],
            "removed_cards": removed_cards,
            "created_card": created,
            "removed_scheme": {"nodes": len(removed_scheme["nodes"]), "lines": len(removed_scheme["lines"])},
            "versions": await _versions(conn, "node", [node_id]),
        }
        await op.audit("UPDATE", "nodes", node_id, {"change_type": result})
        return result

    return await _run(dry_run, body, "CHANGE_NODE_TYPE", actor)


async def set_node_flag(
    node_id: int,
    flag: str,
    on: bool,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Заданный напор / подпитка: добавить строку {nodeID} или удалить (viewZN/delZN десктопа)."""
    from database.topology import _lock_active, _run

    if flag not in NODE_FLAGS:
        raise ValueError(f"Неизвестное дополнение узла: {flag}")
    table = NODE_FLAGS[flag]

    async def body(conn, op):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
        if table not in await _existing_tables(conn, [table]):
            raise ValueError(f"В базе нет таблицы {table}")
        ids = [r["id"] for r in await conn.fetch(f"SELECT id FROM {table} WHERE nodeid = $1 ORDER BY id", node_id)]
        label = NODE_FLAG_LABELS[flag]
        if on:
            if ids:
                raise ValueError(f"{label}: уже задан у узла {node_id}")
            row_id = await conn.fetchval(f"INSERT INTO {table} (nodeid) VALUES ($1) RETURNING id", node_id)
            op.journal.created(table, row_id)
            result = {"node_id": node_id, "flag": flag, "on": True, "id": row_id}
        else:
            if not ids:
                raise ValueError(f"{label}: у узла {node_id} не задан")
            await op.journal.capture_ids(conn, table, ids)
            await conn.execute(f"DELETE FROM {table} WHERE id = ANY($1::int[])", ids)
            result = {"node_id": node_id, "flag": flag, "on": False, "removed": ids}
        await op.audit("INSERT" if on else "DELETE", table, result.get("id") or (ids[0] if ids else None), result)
        return result

    return await _run(dry_run, body, "SET_NODE_FLAG", actor)
