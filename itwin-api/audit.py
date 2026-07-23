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


async def write_audit_log(
    *,
    changed_by: str,
    operation: str,
    table_name: str,
    record_id: Optional[int] = None,
    old_data: Optional[dict[str, Any]] = None,
    new_data: Optional[dict[str, Any]] = None,
    change_group_id: Optional[str] = None,
) -> str:
    group_id = change_group_id or str(uuid.uuid4())
    payload = {
        "changed_by": changed_by,
        "operation": operation,
        "table_name": table_name,
        "record_id": record_id,
        "old_data": old_data,
        "new_data": new_data,
        "change_group_id": group_id,
    }

    try:
        async with acquire_conn() as conn:
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
            if exists:
                # Best-effort insert matching common legacy columns; ignore shape drift.
                cols = await conn.fetch(
                    """
                    SELECT column_name
                      FROM information_schema.columns
                     WHERE table_schema = 'public' AND table_name = 'audit_log'
                    """
                )
                available = {row["column_name"].lower() for row in cols}
                fields: dict[str, Any] = {}
                if "changed_by" in available:
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
                    fields["change_group_id"] = group_id
                if "old_data" in available:
                    fields["old_data"] = json.dumps(old_data, ensure_ascii=False, default=str) if old_data else None
                if "new_data" in available:
                    fields["new_data"] = json.dumps(new_data, ensure_ascii=False, default=str) if new_data else None
                if "changed_at" in available:
                    fields["changed_at"] = await conn.fetchval("SELECT now()")

                if fields:
                    columns = ", ".join(f'"{k}"' for k in fields)
                    placeholders = ", ".join(f"${i}" for i in range(1, len(fields) + 1))
                    await conn.execute(
                        f'INSERT INTO audit_log ({columns}) VALUES ({placeholders})',
                        *fields.values(),
                    )
                    return group_id
    except Exception as exc:
        logger.warning("audit_log write failed, falling back to app log: %s", exc)

    logger.info("AUDIT %s", json.dumps(payload, ensure_ascii=False, default=str))
    return group_id
