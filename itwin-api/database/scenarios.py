"""Сценарии «что если» (фаза 1): вариант сети, который правят и считают отдельно от основы.

Сценарий — копия фрагмента, как это делает десктоп (выгрузка .tgid и загрузка новыми id,
database/fragment_transfer.py): десктоп видит её обычным фрагментом, sety считает её как любой
фрагмент, редактор веба правит её как любой фрагмент. Своё у веба — только соответствие
объектов копии объектам основы (tgid_scenario_object, sql/migrations/20261029_scenarios.sql)
и отпечаток каждой строки основы на момент создания (base_hash).

Сравнение трёхстороннее: в момент создания копия равна основе (тот же отпечаток), поэтому
  * отпечаток копии ≠ сохранённого — объект правили в сценарии;
  * отпечаток основы ≠ сохранённого — объект правили в основе после создания сценария;
  * оба — конфликт: при переносе правок в основу его решает человек.
Отпечаток считается по тем же колонкам, что выгрузка .tgid; ссылки (nodeid, lineid…) — в id
основы, поэтому перенумерация копии различием не считается.

Создание — одна транзакция database/topology._run с журналом отмены: отмена удаляет и копию,
и запись сценария (каскадом — соответствие объектов).
"""

from __future__ import annotations

import datetime as dt
import decimal
import hashlib
import json
from typing import Any, Optional

from database.fragment_transfer import (
    IMPORT_ORDER,
    REF_COLUMNS,
    _columns,
    _export_query,
    export_fragment_text,
    import_sections,
    parse_tgid,
)
from database.regime_queries import attach_coords

SCENARIO_TABLE = "tgid_scenario"
OBJECT_TABLE = "tgid_scenario_object"
DIFF_LIMIT = 500
STATUSES = ("active", "archived")

# fileid у копии всегда свой; fragments — сама запись фрагмента (название копии другое)
_IGNORED_COLUMNS = {"id", "fileid"}
_SKIP_TABLES = {"fragments"}
_INT_TYPES = ("integer", "bigint", "smallint")
# ссылки, которые импорт переводит отдельно от REF_COLUMNS (ispr_nodes)
_DIFF_REFS = {**REF_COLUMNS, "internalnodeid": "nodes"}
_FLOAT_DIGITS = 9

CHANGE_KINDS = {
    "changed": "Изменён в сценарии",
    "added": "Добавлен в сценарии",
    "removed": "Удалён в сценарии",
    "conflict": "Изменён и в сценарии, и в основе",
    "base_changed": "Изменён в основе после создания сценария",
    "base_added": "Появился в основе после создания сценария",
    "base_removed": "Удалён из основы после создания сценария",
}


class ScenarioError(ValueError):
    """Сценарий нельзя создать или изменить (понятная пользователю причина)."""


async def scenarios_available(conn) -> bool:
    return bool(await conn.fetchval(f"SELECT to_regclass('public.{OBJECT_TABLE}') IS NOT NULL"))


# ---------------------------------------------------------------------------
# Сравнение строк
# ---------------------------------------------------------------------------

def _norm(v: Any) -> Any:
    """Значение для сравнения: .tgid не различает NULL и пустой текст, хвостовые пробелы char(n)."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.rstrip()
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float, decimal.Decimal)):
        return round(float(v), _FLOAT_DIGITS)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    return str(v)


def _plain(v: Any) -> Any:
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    return v


def normalized_row(
    row: dict, columns: list[str], refs: dict[str, str], base_ids: dict[str, set[int]],
    copy_to_base: Optional[dict[str, dict[int, int]]] = None,
) -> dict[str, Any]:
    """Строка в «координатах основы».

    copy_to_base=None — строка основы: ссылка за пределы фрагмента (выгрузка её обнуляет) → NULL.
    Иначе — строка копии: ссылка на свой объект → id основы, на новый объект сценария → «новый #id»."""
    out: dict[str, Any] = {}
    for c in columns:
        v = row.get(c)
        target = refs.get(c)
        if target is not None and v is not None:
            if copy_to_base is None:
                v = v if v in base_ids.get(target, ()) else None
            else:
                mapped = copy_to_base.get(target, {}).get(v)
                v = mapped if mapped is not None else f"новый #{v}"
        out[c] = v
    return out


def fingerprint(normalized: dict[str, Any]) -> str:
    payload = json.dumps([[c, _norm(v)] for c, v in normalized.items()], ensure_ascii=False, default=str)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def field_changes(base: dict[str, Any], copy: dict[str, Any]) -> dict[str, list]:
    """{колонка: [в основе, в сценарии]} для отличающихся полей нормализованных строк."""
    return {c: [_plain(base.get(c)), _plain(copy.get(c))]
            for c in base if _norm(base.get(c)) != _norm(copy.get(c))}


def classify(base_fp: str, copy_fp: str, stored_fp: Optional[str]) -> Optional[str]:
    """Вид отличия пары объектов; None — объекты совпадают."""
    if base_fp == copy_fp:
        return None
    if stored_fp is None or base_fp == stored_fp:
        return "changed"
    if copy_fp == stored_fp:
        return "base_changed"
    return "conflict"


async def _table_rows(conn, table: str, fileid: int) -> tuple[dict[int, dict], list[str], dict[str, str]]:
    """Строки фрагмента в таблице (как в выгрузке .tgid), сравниваемые колонки и ссылки."""
    cols = await _columns(conn, table)
    if "id" not in cols:
        return {}, [], {}
    query, names = _export_query(table, cols)
    columns = [c for c in names if c not in _IGNORED_COLUMNS]
    refs = {c: _DIFF_REFS[c] for c in columns if c in _DIFF_REFS and cols[c] in _INT_TYPES}
    rows = {r["id"]: dict(r) for r in await conn.fetch(query, fileid)}
    return rows, columns, refs


# ---------------------------------------------------------------------------
# Создание, список, статус
# ---------------------------------------------------------------------------

async def create_scenario(conn, op, base_fileid: int, name: str, note: Optional[str] = None) -> dict[str, Any]:
    """Копия фрагмента-основы и запись сценария с соответствием объектов (в транзакции op)."""
    if not await scenarios_available(conn):
        raise ScenarioError("Таблицы сценариев ещё не созданы в базе города (city_schema)")
    base = await conn.fetchrow(
        "SELECT id, name FROM fragments WHERE id = $1 AND COALESCE(removed, 0) = 0", base_fileid)
    if base is None:
        raise LookupError(f"Фрагмент {base_fileid} не найден")
    if await conn.fetchval(f"SELECT 1 FROM {SCENARIO_TABLE} WHERE fileid = $1", base_fileid):
        raise ScenarioError("Фрагмент сам является сценарием: создайте сценарий от его основы")

    text, _counts = await export_fragment_text(conn, base_fileid)
    id_map: dict[str, dict[int, int]] = {}
    rep = await import_sections(conn, op, parse_tgid(text.encode("utf-8")), name=name, id_map=id_map,
                                restore_geometry=False)
    # геометрия — точная копия основы (восстановление по x/y и coords десктопа дало бы ту же,
    # но с округлением до сантиметра); фрагменты-сценарии лежат на основе
    for table in ("nodes", "linesobj"):
        mapping = id_map.get(table, {})
        await conn.execute(
            f"""UPDATE {table} c SET shape = b.shape
                  FROM unnest($1::int[], $2::int[]) AS m(base_id, copy_id)
                  JOIN {table} b ON b.id = m.base_id
                 WHERE c.id = m.copy_id AND b.shape IS NOT NULL""",
            list(mapping.keys()), list(mapping.values()),
        )
    scenario_id = await conn.fetchval(
        f"""INSERT INTO {SCENARIO_TABLE} (name, note, base_fileid, fileid, created_by)
            VALUES ($1, $2, $3, $4, $5) RETURNING id""",
        name, note, base_fileid, rep["fileid"], op.actor,
    )
    op.journal.created(SCENARIO_TABLE, scenario_id)

    base_ids = {t: set(m) for t, m in id_map.items()}
    tables: list[str] = []
    base_col: list[int] = []
    copy_col: list[int] = []
    hashes: list[Optional[str]] = []
    for table, mapping in id_map.items():
        base_rows, columns, refs = ({}, [], {}) if table in _SKIP_TABLES else \
            await _table_rows(conn, table, base_fileid)
        for base_id, copy_id in mapping.items():
            row = base_rows.get(base_id)
            tables.append(table)
            base_col.append(base_id)
            copy_col.append(copy_id)
            hashes.append(fingerprint(normalized_row(row, columns, refs, base_ids)) if row else None)
    await conn.execute(
        f"""INSERT INTO {OBJECT_TABLE} (scenario_id, table_name, base_id, copy_id, base_hash)
            SELECT $1, t, b, c, h FROM unnest($2::text[], $3::int[], $4::int[], $5::text[]) AS u(t, b, c, h)""",
        scenario_id, tables, base_col, copy_col, hashes,
    )
    return {
        "scenario_id": scenario_id,
        "name": name,
        "base_fileid": base_fileid,
        "base_name": base["name"],
        "fileid": rep["fileid"],
        "tables": rep["tables"],
        "created_nodes": rep["created_nodes"],
        "created_lines": rep["created_lines"],
        "unresolved_refs": rep["unresolved_refs"],
    }


async def list_scenarios(conn, include_archived: bool = False) -> list[dict[str, Any]]:
    """Сценарии с названиями фрагментов; exists=False — копию удалили (например, в десктопе)."""
    if not await scenarios_available(conn):
        return []
    rows = await conn.fetch(
        f"""SELECT s.id, s.name, s.note, s.base_fileid, s.fileid, s.created_by, s.created_at, s.status,
                   b.name AS base_name, f.name AS fragment_name,
                   f.id IS NOT NULL AND COALESCE(f.removed, 0) = 0 AS exists
              FROM {SCENARIO_TABLE} s
              LEFT JOIN fragments b ON b.id = s.base_fileid
              LEFT JOIN fragments f ON f.id = s.fileid
             WHERE $1 OR s.status = 'active'
             ORDER BY s.id DESC""",
        include_archived,
    )
    return [dict(r) for r in rows]


async def set_scenario_status(conn, scenario_id: int, status: str) -> Optional[dict[str, Any]]:
    """Убрать сценарий в архив или вернуть; копия фрагмента остаётся. None — сценария нет."""
    if status not in STATUSES:
        raise ScenarioError(f"Недопустимый статус {status!r}")
    row = await conn.fetchrow(
        f"UPDATE {SCENARIO_TABLE} SET status = $2 WHERE id = $1 RETURNING id, status", scenario_id, status)
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Сравнение с основой
# ---------------------------------------------------------------------------

async def scenario_row(conn, scenario_id: int):
    return await conn.fetchrow(
        f"SELECT id, name, base_fileid, fileid FROM {SCENARIO_TABLE} WHERE id = $1", scenario_id)


async def object_mapping(conn, scenario_id: int) -> tuple[dict[str, dict[int, int]], dict[tuple[str, int], Optional[str]]]:
    """Соответствие объектов {таблица: {id копии: id основы}} и отпечатки основы {(таблица, id копии): md5}.

    Строки, добавленные переносом в основу (merge_group_id), чья операция отменена, не учитываются:
    созданные ею объекты основы удалены отменой."""
    copy_to_base: dict[str, dict[int, int]] = {}
    stored: dict[tuple[str, int], Optional[str]] = {}
    for r in await conn.fetch(
            f"""SELECT o.table_name, o.base_id, o.copy_id, o.base_hash FROM {OBJECT_TABLE} o
                 WHERE o.scenario_id = $1
                   AND (o.merge_group_id IS NULL OR NOT EXISTS (
                        SELECT 1 FROM topology_undo_log u
                         WHERE u.change_group_id = o.merge_group_id AND u.undone_at IS NOT NULL))""",
            scenario_id):
        copy_to_base.setdefault(r["table_name"], {})[r["copy_id"]] = r["base_id"]
        stored[(r["table_name"], r["copy_id"])] = r["base_hash"]
    return copy_to_base, stored


async def collect_differences(conn, sc) -> dict[str, Any]:
    """Все отличия сценария sc от основы: found — [(таблица, отличие)], плюс соответствие и колонки
    таблиц (их использует перенос в основу, database/scenario_merge.py)."""
    copy_to_base, stored = await object_mapping(conn, sc["id"])
    base_ids = {t: set(m.values()) for t, m in copy_to_base.items()}
    found_all: list[tuple[str, dict[str, Any]]] = []
    tables: dict[str, dict[str, Any]] = {}
    for table in IMPORT_ORDER:
        if table in _SKIP_TABLES:
            continue
        base_rows, columns, refs = await _table_rows(conn, table, sc["base_fileid"])
        copy_rows, _, _ = await _table_rows(conn, table, sc["fileid"])
        tables[table] = {"columns": columns, "refs": refs}
        mapping = copy_to_base.get(table, {})

        found: list[dict[str, Any]] = []
        for copy_id, row in copy_rows.items():
            base_id = mapping.get(copy_id)
            if base_id is None:
                found.append({"kind": "added", "copy_id": copy_id, "row": row})
                continue
            if base_id not in base_rows:
                found.append({"kind": "base_removed", "copy_id": copy_id, "base_id": base_id, "row": row})
                continue
            b = normalized_row(base_rows[base_id], columns, refs, base_ids)
            c = normalized_row(row, columns, refs, base_ids, copy_to_base)
            kind = classify(fingerprint(b), fingerprint(c), stored.get((table, copy_id)))
            if kind:
                found.append({"kind": kind, "copy_id": copy_id, "base_id": base_id,
                              "fields": field_changes(b, c), "row": row})
        mapped_base = set(mapping.values())
        for copy_id, base_id in mapping.items():
            if copy_id not in copy_rows and base_id in base_rows:
                found.append({"kind": "removed", "base_id": base_id, "row": base_rows[base_id]})
        for base_id, row in base_rows.items():
            if base_id not in mapped_base:
                found.append({"kind": "base_added", "base_id": base_id, "row": row})
        found_all += [(table, f) for f in found]

    # сначала правки сценария, потом конфликты, потом изменения основы
    order = {k: i for i, k in enumerate(CHANGE_KINDS)}
    found_all.sort(key=lambda tf: (order[tf[1]["kind"]], IMPORT_ORDER.index(tf[0]),
                                   tf[1].get("copy_id") or tf[1].get("base_id") or 0))
    return {"found": found_all, "copy_to_base": copy_to_base, "base_ids": base_ids, "tables": tables}


async def scenario_diff(conn, scenario_id: int, limit: int = DIFF_LIMIT) -> Optional[dict[str, Any]]:
    """Отличия сценария от основы по всем таблицам фрагмента. None — сценария нет."""
    sc = await scenario_row(conn, scenario_id)
    if sc is None:
        return None
    found_all = (await collect_differences(conn, sc))["found"]
    summary: dict[str, dict[str, int]] = {}
    for table, f in found_all:
        counts = summary.setdefault(table, {})
        counts[f["kind"]] = counts.get(f["kind"], 0) + 1
    items = [_item(table, f) for table, f in found_all[:limit]]
    await _attach_item_coords(conn, items)
    by_kind: dict[str, int] = {}
    for counts in summary.values():
        for k, n in counts.items():
            by_kind[k] = by_kind.get(k, 0) + n
    return {
        "scenario_id": sc["id"],
        "name": sc["name"],
        "base_fileid": sc["base_fileid"],
        "fileid": sc["fileid"],
        "summary": summary,
        "by_kind": by_kind,
        "total": len(found_all),
        "limit": limit,
        "truncated": len(found_all) > len(items),
        "kinds": CHANGE_KINDS,
        "items": items,
    }


def _item(table: str, found: dict[str, Any]) -> dict[str, Any]:
    """Строка отличия; anchor — узел или участок, по которому объект показывается на карте."""
    row = found["row"]
    object_id = found.get("copy_id") or found.get("base_id")
    if table == "nodes":
        anchor = ("node", object_id)
    elif table == "linesobj":
        anchor = ("line", object_id)
    elif row.get("nodeid") is not None:
        anchor = ("node", row["nodeid"])
    elif row.get("lineid") is not None:
        anchor = ("line", row["lineid"])
    else:
        anchor = (None, None)
    name = row.get("name") if isinstance(row.get("name"), str) else row.get("nodename")
    return {
        "table": table,
        "kind": found["kind"],
        "base_id": found.get("base_id"),
        "copy_id": found.get("copy_id"),
        "name": name.strip() if isinstance(name, str) and name.strip() else None,
        "fields": found.get("fields"),
        "anchor_type": anchor[0],
        "anchor_id": anchor[1],
    }


async def _attach_item_coords(conn, items: list[dict[str, Any]]) -> None:
    nodes = [{"node_id": i["anchor_id"]} for i in items if i["anchor_type"] == "node"]
    lines = [{"line_id": i["anchor_id"]} for i in items if i["anchor_type"] == "line"]
    await attach_coords(conn, nodes, key="node_id")
    await attach_coords(conn, lines, key="line_id")
    coords = {("node", n["node_id"]): n for n in nodes}
    coords.update({("line", ln["line_id"]): ln for ln in lines})
    for i in items:
        c = coords.get((i["anchor_type"], i["anchor_id"]), {})
        i["lat"], i["lng"] = c.get("latitude"), c.get("longitude")
