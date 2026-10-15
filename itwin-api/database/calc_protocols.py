"""Протоколы расчётов sety (таблица calculation_protocol, пишет воркер — worker._save_protocol).

Чтение для веба: список, протокол запуска / запроса, координаты объектов протокола для перехода
на карте. Объект внутренней схемы узла показывается точкой узла-владельца (как в attach_coords).
"""

from __future__ import annotations

import json
from typing import Any, Optional

import asyncpg

TABLE = "calculation_protocol"
MISSING_TABLE = "Протоколы расчётов ещё не сохранялись (нет таблицы calculation_protocol)"

_LIST_COLUMNS = """p.id, p.request_id, p.task_id, p.calculationid, p.fileid, f.name AS fragment_name,
                   p.created_at, p.author, p.mode, p.params, p.status, p.errors, p.warnings"""


def _jsonb(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


def _row(r: asyncpg.Record, full: bool = False) -> dict[str, Any]:
    d = dict(r)
    if d.get("created_at") is not None:
        d["created_at"] = d["created_at"].isoformat()
    for key in ("summary", "entries"):
        if key in d:
            d[key] = _jsonb(d[key])
    if not full:
        d.pop("output", None)
    return d


async def table_exists(conn) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass('public.calculation_protocol') IS NOT NULL"))


async def list_protocols(conn, *, file_id: Optional[int] = None, limit: int = 50) -> list[dict[str, Any]]:
    if not await table_exists(conn):
        return []
    rows = await conn.fetch(
        f"""SELECT {_LIST_COLUMNS}
              FROM {TABLE} p LEFT JOIN fragments f ON f.id = p.fileid
             WHERE ($1::int IS NULL OR p.fileid = $1)
             ORDER BY p.created_at DESC, p.id DESC
             LIMIT $2""",
        file_id, limit,
    )
    return [_row(r) for r in rows]


async def get_protocols(conn, *, protocol_id: Optional[int] = None, request_id: Optional[str] = None,
                        calculation_id: Optional[int] = None, with_output: bool = False) -> list[dict[str, Any]]:
    """Протоколы по id, по запросу (все фрагменты расчёта по списку) или по строке calculation."""
    if not await table_exists(conn):
        return []
    rows = await conn.fetch(
        f"""SELECT {_LIST_COLUMNS}, p.summary, p.entries{', p.output' if with_output else ''}
              FROM {TABLE} p LEFT JOIN fragments f ON f.id = p.fileid
             WHERE ($1::int IS NULL OR p.id = $1)
               AND ($2::text IS NULL OR p.request_id = $2)
               AND ($3::int IS NULL OR p.calculationid = $3)
             ORDER BY p.id""",
        protocol_id, request_id, calculation_id,
    )
    return [_row(r, full=with_output) for r in rows]


_NODE_SQL = """
SELECT n.id, COALESCE(owner.id, n.id) AS shown_id,
       ST_AsGeoJSON(ST_Transform(ST_PointOnSurface(COALESCE(owner.shape, n.shape)), 4326), 7)::json AS geom
  FROM nodes n LEFT JOIN nodes owner ON owner.id = n.internalnodeid
 WHERE n.id = ANY($1::int[]) AND COALESCE(owner.shape, n.shape) IS NOT NULL"""

_LINE_SQL = """
SELECT l.id, owner.id AS owner_id,
       ST_AsGeoJSON(ST_Transform(COALESCE(owner.shape, l.shape), 4326), 7)::json AS geom
  FROM linesobj l LEFT JOIN nodes owner ON owner.id = l.internalnodeid
 WHERE l.id = ANY($1::int[]) AND COALESCE(owner.shape, l.shape) IS NOT NULL"""

# участок между двумя узлами (ссылка line2 из протокола): любой неудалённый, в любом направлении
_PAIR_SQL = """
SELECT DISTINCT ON (q.a, q.b) q.a, q.b, l.id
  FROM unnest($1::int[], $2::int[]) AS q(a, b)
  JOIN linesobj l ON COALESCE(l.removed, 0) = 0
                 AND ((l.nodeid1 = q.a AND l.nodeid2 = q.b) OR (l.nodeid1 = q.b AND l.nodeid2 = q.a))
 ORDER BY q.a, q.b, l.id"""


async def locate_objects(conn, objects: list[dict[str, Any]]) -> dict[str, Any]:
    """Геометрия (WGS84 GeoJSON) объектов протокола.

    → {"nodes": {id: {geometry, shown_id}}, "lines": {id: {geometry, owner_id}},
       "pairs": {"id1-id2": {line_id | node_id}}}; объекта без геометрии в ответе нет.
    """
    node_ids: set[int] = set()
    line_ids: set[int] = set()
    pairs: set[tuple[int, int]] = set()
    for o in objects:
        kind = o.get("kind")
        try:
            if kind == "node":
                node_ids.add(int(o["id"]))
            elif kind == "line":
                line_ids.add(int(o["id"]))
            elif kind == "line2":
                a, b = int(o["id1"]), int(o["id2"])
                if a == b:
                    node_ids.add(a)        # обе вершины внутри одного узла — его и показываем
                else:
                    pairs.add((a, b))
        except (KeyError, TypeError, ValueError):
            continue

    pair_result: dict[str, dict[str, int]] = {}
    if pairs:
        pa = [p[0] for p in pairs]
        pb = [p[1] for p in pairs]
        found = {(r["a"], r["b"]): r["id"] for r in await conn.fetch(_PAIR_SQL, pa, pb)}
        for a, b in pairs:
            line_id = found.get((a, b)) or found.get((b, a))
            if line_id:
                pair_result[f"{a}-{b}"] = {"line_id": line_id}
                line_ids.add(line_id)
            else:
                # узлы — внутренние схемы разных камер: показываем первый
                pair_result[f"{a}-{b}"] = {"node_id": a}
                node_ids.add(a)

    nodes: dict[str, Any] = {}
    if node_ids:
        for r in await conn.fetch(_NODE_SQL, sorted(node_ids)):
            nodes[str(r["id"])] = {"geometry": _jsonb(r["geom"]), "shown_id": r["shown_id"]}
    lines: dict[str, Any] = {}
    if line_ids:
        for r in await conn.fetch(_LINE_SQL, sorted(line_ids)):
            lines[str(r["id"])] = {"geometry": _jsonb(r["geom"]), "owner_id": r["owner_id"]}
    return {"nodes": nodes, "lines": lines, "pairs": pair_result}
