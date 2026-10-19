"""«История» правок пользователя: операции журнала отмены (сеть и карточки) и откат до выбранной.

Список — из topology_undo_log (только свои операции, как отмена): что сделано, когда, отменено ли,
и где это на карте (bbox по узлам и участкам операции — для «Показать»).
Откат до выбранной — последовательная отмена от последней операции до неё включительно; первая же
операция, которую отменить нельзя (объекты изменены после неё), останавливает откат.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from database.connect import get_pool
from database.topology import TopologyConflictError, TopologyNothingToUndo, undo_last_operation
from database.topology_journal import JOURNAL_TABLE, journal_available, redo_available

HISTORY_LIMIT = 200


def _ids(summary: dict, *keys: str) -> list[int]:
    out: list[int] = []
    for k in keys:
        v = summary.get(k)
        if isinstance(v, list):
            out += [int(x) for x in v if isinstance(x, (int, float)) or str(x).isdigit()]
        elif v is not None and str(v).isdigit():
            out.append(int(v))
    return out


async def _bbox(conn, summary: dict, before_tables: dict[str, list[int]]) -> Optional[list[float]]:
    """[minLng, minLat, maxLng, maxLat] узлов и участков операции (включая снятые) — для «Показать»."""
    nodes = set(_ids(summary, "node_id", "target_node_id", "source_node_id", "new_node_id", "created_nodes", "updated_nodes"))
    lines = set(_ids(summary, "line_id", "pair_line_id", "new_line_id", "created_lines", "removed_lines", "split_lines"))
    nodes |= set(before_tables.get("nodes", []))
    lines |= set(before_tables.get("linesobj", []))
    # строка карточки — по её участку или узлу
    if summary.get("table") and summary.get("id") is not None:
        table, rid = str(summary["table"]).lower(), int(summary["id"])
        if table in ("heatpipesections",):
            lid = await conn.fetchval("SELECT lineid FROM heatpipesections WHERE id = $1", rid)
            if lid:
                lines.add(int(lid))
        elif table == "linesobj":
            lines.add(rid)
        elif table == "nodes":
            nodes.add(rid)
        else:
            try:
                nid = await conn.fetchval(f'SELECT nodeid FROM "{table}" WHERE id = $1', rid)
            except Exception:  # noqa: BLE001 — нет колонки nodeid
                nid = None
            if nid:
                nodes.add(int(nid))
    if not nodes and not lines:
        return None
    row = await conn.fetchrow(
        """
        WITH g AS (
            SELECT shape FROM nodes WHERE id = ANY($1::int[]) AND shape IS NOT NULL
            UNION ALL SELECT shape FROM linesobj WHERE id = ANY($2::int[]) AND shape IS NOT NULL
        )
        SELECT ST_XMin(e) x1, ST_YMin(e) y1, ST_XMax(e) x2, ST_YMax(e) y2
        FROM (SELECT ST_Extent(ST_Transform(shape, 4326)) e FROM g) t
        """,
        list(nodes)[:500], list(lines)[:500],
    )
    if row is None or row["x1"] is None:
        return None
    return [round(row["x1"], 7), round(row["y1"], 7), round(row["x2"], 7), round(row["y2"], 7)]


async def operation_history(actor: Optional[str], limit: int = 30) -> list[dict[str, Any]]:
    """Последние операции пользователя, новые сверху: отменена ли, можно ли откатить до неё, где на карте."""
    limit = max(1, min(limit, HISTORY_LIMIT))
    pool = get_pool()
    async with pool.acquire() as conn:
        if not await journal_available(conn):
            return []
        redo_cols = ", redone_at" if await redo_available(conn) else ", NULL::timestamp AS redone_at"
        rows = await conn.fetch(
            f"""
            SELECT id, operation, created_at, summary, undone_at{redo_cols}, unsupported,
                   jsonb_array_length(before_rows) AS objects,
                   (SELECT jsonb_object_agg(t, ids) FROM (
                        SELECT e->>'t' AS t, jsonb_agg((e->>'id')::int) AS ids
                        FROM jsonb_array_elements(before_rows) e
                        WHERE e->>'t' IN ('nodes', 'linesobj') GROUP BY e->>'t') x) AS tables
            FROM {JOURNAL_TABLE}
            WHERE actor IS NOT DISTINCT FROM $1
            ORDER BY id DESC
            LIMIT $2
            """,
            actor, limit,
        )
        items = []
        for r in rows:
            summary = r["summary"]
            if isinstance(summary, str):
                summary = json.loads(summary)
            tables = r["tables"]
            if isinstance(tables, str):
                tables = json.loads(tables)
            items.append({
                "operation_id": r["id"],
                "operation": r["operation"],
                "created_at": r["created_at"].isoformat(timespec="seconds") if r["created_at"] else None,
                "undone_at": r["undone_at"].isoformat(timespec="seconds") if r["undone_at"] else None,
                "redone_at": r["redone_at"].isoformat(timespec="seconds") if r["redone_at"] else None,
                "summary": summary or {},
                "objects": r["objects"],
                "undo_supported": not r["unsupported"],
                "bbox": await _bbox(conn, summary or {}, tables or {}),
            })
    return items


async def undo_to(actor: Optional[str], operation_id: int) -> dict[str, Any]:
    """Отменить операции пользователя от последней до operation_id включительно.

    → {undone: [id…], stopped: {operation_id, reason} | None}. Каждая отмена — своя транзакция:
    отменённое до остановки остаётся отменённым (как несколько Ctrl+Z подряд).
    """
    undone: list[int] = []
    stopped = None
    for _ in range(HISTORY_LIMIT):
        try:
            res = await undo_last_operation(actor)
        except TopologyNothingToUndo:
            break
        except TopologyConflictError as exc:
            stopped = {"reason": str(exc), "conflicts": exc.conflicts}
            break
        except Exception as exc:  # noqa: BLE001 — операция без поддержки отмены и т. п.
            stopped = {"reason": str(exc)}
            break
        done_id = int(res.get("operation_id") or 0)
        undone.append(done_id)
        if done_id <= operation_id:
            break
    return {"undone": undone, "stopped": stopped, "target": operation_id,
            "complete": bool(undone) and min(undone) <= operation_id}
