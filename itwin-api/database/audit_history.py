"""История правок: чтение audit_log (триггеры БД + записи API через audit.write_audit_log).

Строка журнала: operation INSERT/UPDATE/DELETE (триггеры) или RUN/RUN_SETY/MOVE/… (API),
old_data/new_data — jsonb снимки строки. В списке отдаётся только разница полей
(``changes``), геометрия и длинные значения обрезаются: у триггеров в снимке лежит
вся строка, включая shape.
"""

from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta
from typing import Any, Optional

import asyncpg

REQUIRED_COLUMNS = frozenset(
    {"log_id", "operation", "table_name", "record_id", "old_data", "new_data", "changed_at", "changed_by"}
)
OPTIONAL_COLUMNS = ("comment", "node_id", "change_group_id", "is_rolled_back")
HIDDEN_KEYS = frozenset({"shape", "geom", "the_geom"})
MAX_VALUE_LEN = 300


async def audit_columns(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        """SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'audit_log'"""
    )
    return {str(r["column_name"]).lower() for r in rows}


def _as_dict(value: Any) -> Optional[dict[str, Any]]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {"value": value}
    return value if isinstance(value, dict) else {"value": value}


def _short(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, str) and len(value) > MAX_VALUE_LEN:
        return value[:MAX_VALUE_LEN] + "…"
    return value


def compute_changes(old: Optional[dict[str, Any]], new: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Поля, которые отличаются между снимками (для INSERT — все непустые новые, DELETE — старые)."""
    old = old or {}
    new = new or {}
    changes = []
    for key in sorted(set(old) | set(new)):
        if key.lower() in HIDDEN_KEYS:
            continue
        before, after = old.get(key), new.get(key)
        if before == after:
            continue
        if not old and after is None:
            continue
        if not new and before is None:
            continue
        changes.append({"field": key, "old": _short(before), "new": _short(after)})
    return changes


def _clean_snapshot(data: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if data is None:
        return None
    return {k: _short(v) for k, v in data.items() if k.lower() not in HIDDEN_KEYS}


def _row_to_item(row: asyncpg.Record, optional: list[str], *, full: bool) -> dict[str, Any]:
    old = _as_dict(row["old_data"])
    new = _as_dict(row["new_data"])
    item: dict[str, Any] = {
        "log_id": row["log_id"],
        "changed_at": row["changed_at"],
        "changed_by": row["changed_by"],
        "operation": row["operation"],
        "table_name": row["table_name"],
        "record_id": row["record_id"],
        "changes": compute_changes(old, new),
    }
    for col in optional:
        value = row[col]
        item[col] = str(value) if col == "change_group_id" and value is not None else value
    if full:
        item["old_data"] = _clean_snapshot(old)
        item["new_data"] = _clean_snapshot(new)
    return item


def build_filters(
    *,
    table: Optional[str] = None,
    record_id: Optional[int] = None,
    changed_by: Optional[str] = None,
    operation: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    change_group_id: Optional[str] = None,
) -> tuple[str, list[Any]]:
    """WHERE по фильтрам журнала; все значения — параметры ($n), имён из запроса в SQL нет."""
    clauses: list[str] = []
    args: list[Any] = []

    def add(sql: str, value: Any) -> None:
        args.append(value)
        clauses.append(sql.replace("?", f"${len(args)}"))

    if table:
        add("lower(a.table_name) = lower(?)", table)
    if record_id is not None:
        add("a.record_id = ?", record_id)
    if changed_by:
        add("a.changed_by ILIKE ?", f"%{changed_by}%")
    if operation:
        add("upper(a.operation) = upper(?)", operation)
    if date_from:
        add("a.changed_at >= ?", datetime.combine(date_from, time.min))
    if date_to:
        add("a.changed_at < ?", datetime.combine(date_to + timedelta(days=1), time.min))
    if change_group_id:
        add("a.change_group_id::text = ?", change_group_id)
    return ("WHERE " + " AND ".join(clauses)) if clauses else "", args


async def get_audit_log(
    conn: asyncpg.Connection,
    *,
    page: int = 1,
    page_size: int = 50,
    **filters: Any,
) -> dict[str, Any]:
    columns = await audit_columns(conn)
    empty = {"items": [], "total": 0, "page": page, "page_size": page_size, "pages": 0}
    if not columns:
        return {**empty, "note": "Таблицы audit_log нет в этой БД"}
    missing = REQUIRED_COLUMNS - columns
    if missing:
        return {**empty, "note": f"В audit_log нет колонок: {', '.join(sorted(missing))}"}
    optional = [c for c in OPTIONAL_COLUMNS if c in columns]
    if "change_group_id" not in columns:
        filters.pop("change_group_id", None)
    where, args = build_filters(**filters)
    total = await conn.fetchval(f"SELECT count(*) FROM audit_log a {where}", *args)
    select_cols = ", ".join(f"a.{c}" for c in sorted(REQUIRED_COLUMNS) + optional)
    rows = await conn.fetch(
        f"""SELECT {select_cols} FROM audit_log a {where}
             ORDER BY a.changed_at DESC NULLS LAST, a.log_id DESC
             LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}""",
        *args,
        page_size,
        (page - 1) * page_size,
    )
    return {
        "items": [_row_to_item(r, optional, full=False) for r in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


async def get_audit_entry(conn: asyncpg.Connection, log_id: int) -> Optional[dict[str, Any]]:
    columns = await audit_columns(conn)
    if not REQUIRED_COLUMNS <= columns:
        return None
    optional = [c for c in OPTIONAL_COLUMNS if c in columns]
    select_cols = ", ".join(f"a.{c}" for c in sorted(REQUIRED_COLUMNS) + optional)
    row = await conn.fetchrow(f"SELECT {select_cols} FROM audit_log a WHERE a.log_id = $1", log_id)
    return _row_to_item(row, optional, full=True) if row else None


async def get_audit_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    columns = await audit_columns(conn)
    if not REQUIRED_COLUMNS <= columns:
        return {"tables": [], "users": [], "operations": []}
    tables = await conn.fetch(
        """SELECT lower(table_name) AS name, count(*)::int AS count FROM audit_log
            WHERE table_name IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1"""
    )
    users = await conn.fetch(
        """SELECT changed_by AS name, count(*)::int AS count FROM audit_log
            WHERE changed_by IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 200"""
    )
    operations = await conn.fetch(
        """SELECT upper(operation) AS name, count(*)::int AS count FROM audit_log
            WHERE operation IS NOT NULL GROUP BY 1 ORDER BY 2 DESC, 1"""
    )
    return {
        "tables": [dict(r) for r in tables],
        "users": [dict(r) for r in users],
        "operations": [dict(r) for r in operations],
    }
