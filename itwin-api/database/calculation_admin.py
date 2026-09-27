"""Список расчётов sety и удаление расчёта вместе с его результатами (*_out).

Таблицы результатов ищутся в каталоге: все базовые таблицы текущей схемы с колонкой
calculationid и именем *_out (ut_out, us_out, pt_out, dr_out, ut_teplo_out, …).
Прочие таблицы с calculationid (например, iznos — «Износ оборудования») результатами
расчёта не считаются: если в них есть строки удаляемого расчёта, удаление отклоняется.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

import asyncpg

_OUT_TABLE_RE = re.compile(r"^[a-z0-9_]+_out$")
_IDENT_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

MODE_PATTERNS = {
    # calc_params пишет sety/config.get_args_json (json.dumps с bool → int)
    "plan": '%"g_is_avar": 0%',
    "emergency": '%"g_is_avar": 1%',
}


class CalculationReferencedError(Exception):
    """На расчёт ссылаются строки не из *_out-таблиц — удалять нельзя."""

    def __init__(self, tables: dict[str, int]):
        self.tables = tables
        super().__init__(", ".join(f"{t}: {n}" for t, n in tables.items()))


def _parse_params(raw: Optional[str]) -> Optional[dict[str, Any]]:
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def calculation_mode(params: Optional[dict[str, Any]]) -> Optional[str]:
    if not params or "g_is_avar" not in params:
        return None
    return "emergency" if int(params["g_is_avar"] or 0) else "plan"


async def list_calculations(
    conn: asyncpg.Connection,
    *,
    file_id: Optional[int] = None,
    mode: Optional[str] = None,
    author: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    where = ["TRUE"]
    args: list[Any] = []

    def add(cond: str, value: Any) -> None:
        args.append(value)
        where.append(cond.replace("?", f"${len(args)}"))

    if file_id is not None:
        add("c.fileid = ?", file_id)
    if mode is not None:
        add("c.calc_params LIKE ?", MODE_PATTERNS[mode])
    if author:
        add("c.user_gid ILIKE ?", f"%{author}%")
    if date_from is not None:
        add("c.date1 >= ?", date_from)
    if date_to is not None:
        add("c.date1 <= ?", date_to)
    where_sql = " AND ".join(where)

    total = await conn.fetchval(f"SELECT count(*) FROM calculation c WHERE {where_sql}", *args)
    rows = await conn.fetch(
        f"""
        SELECT c.id, c.fileid, f.name AS fragment_name, c.date1 AS calculated_at, c.tn,
               c.name, c.user_gid, c.calc_plan, c.calc_params,
               c.id = (SELECT max(c2.id) FROM calculation c2 WHERE c2.fileid = c.fileid) AS is_latest,
               EXISTS (SELECT 1 FROM ut_out u WHERE u.calculationid = c.id) AS has_results
        FROM calculation c
        LEFT JOIN fragments f ON f.id = c.fileid
        WHERE {where_sql}
        ORDER BY c.date1 DESC NULLS LAST, c.id DESC
        LIMIT ${len(args) + 1} OFFSET ${len(args) + 2}
        """,
        *args, limit, offset,
    )
    items = []
    for row in rows:
        item = dict(row)
        params = _parse_params(item.pop("calc_params"))
        item["params"] = params
        item["mode"] = calculation_mode(params)
        items.append(item)
    return {"total": total, "items": items}


async def _calculation_tables(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch(
        """
        SELECT c.table_name
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = current_schema()
          AND lower(c.column_name) = 'calculationid'
          AND t.table_type = 'BASE TABLE'
          AND c.table_name <> 'calculation'
        ORDER BY c.table_name
        """
    )
    return [r["table_name"] for r in rows if _IDENT_RE.match(r["table_name"])]


def _affected(status: str) -> int:
    # asyncpg execute → "DELETE 123"
    try:
        return int(status.rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return 0


async def get_calculation(conn: asyncpg.Connection, calculation_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        "SELECT id, fileid, name, user_gid, date1 AS calculated_at, tn FROM calculation WHERE id = $1",
        calculation_id,
    )
    return dict(row) if row else None


async def delete_calculation(conn: asyncpg.Connection, calculation_id: int) -> Optional[dict[str, Any]]:
    """Удаляет расчёт и его строки во всех *_out в одной транзакции. None — расчёта нет."""
    async with conn.transaction():
        row = await conn.fetchrow(
            "SELECT id, fileid, name, user_gid, date1 AS calculated_at, tn "
            "FROM calculation WHERE id = $1 FOR UPDATE",
            calculation_id,
        )
        if row is None:
            return None

        tables = await _calculation_tables(conn)
        out_tables = [t for t in tables if _OUT_TABLE_RE.match(t)]
        referenced: dict[str, int] = {}
        for table in tables:
            if table in out_tables:
                continue
            n = await conn.fetchval(f'SELECT count(*) FROM "{table}" WHERE calculationid = $1', calculation_id)
            if n:
                referenced[table] = n
        if referenced:
            raise CalculationReferencedError(referenced)

        deleted: dict[str, int] = {}
        for table in out_tables:
            n = _affected(await conn.execute(f'DELETE FROM "{table}" WHERE calculationid = $1', calculation_id))
            if n:
                deleted[table] = n
        await conn.execute("DELETE FROM calculation WHERE id = $1", calculation_id)

    return {"calculation": dict(row), "deleted_rows": deleted, "out_tables": out_tables}
