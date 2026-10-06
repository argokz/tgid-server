"""P0 audit logging for mutation endpoints.

Writes to existing audit_log when present; otherwise logs to application logger
so mutations remain auditable even without the legacy trigger table.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional

from database.connect import acquire_conn

logger = logging.getLogger(__name__)


def build_audit_insert(
    available: set[str],
    *,
    changed_by: Optional[str],
    operation: str,
    table_name: str,
    record_id: Optional[int],
    old_data: Optional[dict[str, Any]],
    new_data: Optional[dict[str, Any]],
    change_group_id: str,
) -> Optional[tuple[str, list[Any]]]:
    """INSERT в audit_log под фактический набор колонок; None — писать нечего.

    changed_at задаётся выражением now() на стороне сервера, а не параметром: в legacy-БД
    колонка `timestamp without time zone`, а `SELECT now()` отдаёт в asyncpg aware-datetime,
    который кодек timestamp отвергает («can't subtract offset-naive and offset-aware
    datetimes»). Присваивание now() конвертирует значение в тип колонки (как DEFAULT
    CURRENT_TIMESTAMP) и одинаково работает для timestamp и timestamptz.
    """
    fields: dict[str, Any] = {}
    # changed_by=None — автор = роль PostgreSQL сессии (DB_ROLE_SWITCH: политика RLS audit_log
    # пропускает только changed_by = current_user; см. sql/pg_auth/04_rls.sql)
    by_current_user = changed_by is None and "changed_by" in available
    if "changed_by" in available and not by_current_user:
        fields["changed_by"] = changed_by
    if "operation" in available:
        fields["operation"] = operation
    if "table_name" in available:
        fields["table_name"] = table_name
    elif "tablename" in available:
        fields["tablename"] = table_name
    if "record_id" in available and record_id is not None:
        fields["record_id"] = record_id
    elif "recordid" in available and record_id is not None:
        fields["recordid"] = record_id
    if "change_group_id" in available:
        fields["change_group_id"] = uuid.UUID(str(change_group_id))
    if "old_data" in available:
        fields["old_data"] = json.dumps(old_data, ensure_ascii=False, default=str) if old_data else None
    if "new_data" in available:
        fields["new_data"] = json.dumps(new_data, ensure_ascii=False, default=str) if new_data else None
    if not fields and not by_current_user:
        return None

    columns = [f'"{k}"' for k in fields]
    values = [f"${i}" for i in range(1, len(fields) + 1)]
    if by_current_user:
        columns.append('"changed_by"')
        values.append("current_user")
    if "changed_at" in available:
        columns.append('"changed_at"')
        values.append("now()")
    sql = f'INSERT INTO audit_log ({", ".join(columns)}) VALUES ({", ".join(values)})'
    return sql, list(fields.values())


async def write_audit_log(
    *,
    changed_by: str,
    operation: str,
    table_name: str,
    record_id: Optional[int] = None,
    old_data: Optional[dict[str, Any]] = None,
    new_data: Optional[dict[str, Any]] = None,
    change_group_id: Optional[str] = None,
    conn: Any = None,
) -> str:
    """Пишет запись аудита; conn — писать в транзакции самой операции.

    С conn запись идёт через SAVEPOINT этой транзакции: фиксируется и откатывается
    вместе с операцией, а сбой вставки аудита не обрывает саму операцию.
    """
    from database.db_role import role_switch_enabled

    group_id = change_group_id or str(uuid.uuid4())
    payload = {
        # DB_ROLE_SWITCH: автор — роль PostgreSQL сессии (current_user), иначе — имя из токена
        "changed_by": None if role_switch_enabled() else changed_by,
        "operation": operation,
        "table_name": table_name,
        "record_id": record_id,
        "old_data": old_data,
        "new_data": new_data,
        "change_group_id": group_id,
    }

    try:
        if conn is not None:
            async with conn.transaction():
                if await _insert_audit_row(conn, payload):
                    return group_id
        else:
            async with acquire_conn() as own_conn:
                if await _insert_audit_row(own_conn, payload):
                    return group_id
    except Exception as exc:
        logger.warning("audit_log write failed, falling back to app log: %s", exc)

    logger.info("AUDIT %s", json.dumps({**payload, "changed_by": changed_by}, ensure_ascii=False, default=str))
    return group_id


async def _insert_audit_row(conn, payload: dict[str, Any]) -> bool:
    """INSERT в audit_log под фактический набор колонок; False — таблицы нет/писать нечего."""
    exists = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
              FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_name = 'audit_log'
        )
        """
    )
    if not exists:
        return False
    # Best-effort insert matching common legacy columns; ignore shape drift.
    cols = await conn.fetch(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = 'audit_log'
        """
    )
    available = {row["column_name"].lower() for row in cols}
    built = build_audit_insert(available, **payload)
    if not built:
        return False
    sql, args = built
    await conn.execute(sql, *args)
    return True
