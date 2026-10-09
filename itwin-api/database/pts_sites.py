"""Участки ПТС (паспорта): участки МС/РС и привязка к ним труб (этап 9).

Эталон — gid8: док «Участки МС/РС» (``docks/DockPTS.cpp``: дерево начальник → участок,
«Характеристика», «Перейти к участку», «Паспорт») и назначение участка выделенным трубам
(``GidWidget::onSaveMS/onSaveRS``: пишется ``heatpipesections.magistralSite``/``distSite``,
вторая привязка снимается).

Назначение/снятие привязки идёт через групповые установщики (``pts_site_ms``, ``pts_site_rs``,
``pts_site_clear`` в ``database/group_setters.py``) — отсюда dry-run, одна транзакция,
audit_log с группой и отмена ``/api/v1/group-setters/undo``.
Выбор труб — список linesobj.id (клики на карте) или цепочка узлов: между соседними узлами
цепочки берётся кратчайший по длине путь по линейным объектам (трубы, арматура), к участку
привязываются трубы пути (десктоп: выделение «по пути» между узлами).
"""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from typing import Any, Optional

from database import typed_edit as te
from database.sql_ident import quote_ident

MAX_CHAIN_NODES = 50


class PtsError(Exception):
    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class SiteKind:
    key: str  # ms | rs
    table: str
    pipe_column: str  # колонка heatpipesections
    name_column: str
    title: str
    setter: str  # групповой установщик назначения


KINDS: dict[str, SiteKind] = {
    "ms": SiteKind("ms", "uchastok_ms", "magistralsite", "opisanie_uchastka_ms", "Участок МС", "pts_site_ms"),
    "rs": SiteKind("rs", "uchastok_rs", "distsite", "naimenovanie_uchastka_rs", "Участок РС", "pts_site_rs"),
}
CLEAR_SETTER = "pts_site_clear"
SITE_TABLES = frozenset(k.table for k in KINDS.values())


def get_kind(key: str) -> SiteKind:
    kind = KINDS.get(str(key).lower())
    if kind is None:
        raise PtsError(404, {"code": "bad_kind", "message": "Вид участка: ms | rs"})
    return kind


async def site_fields(conn, kind: SiteKind) -> list[te.FieldSpec]:
    return await te.editable_fields(conn, kind.table)


async def list_sites(conn, kind: SiteKind) -> list[dict[str, Any]]:
    """Участки с иерархией десктопного дока (начальник, участок эксплуатации) и статистикой труб."""
    t, name, col = quote_ident(kind.table), quote_ident(kind.name_column), quote_ident(kind.pipe_column)
    rows = await conn.fetch(
        f"""
        WITH p AS (
            SELECT h.{col} AS site_id, count(*)::int AS pipes,
                   round(sum(COALESCE(h.pipesectlength, ST_Length(l.shape), 0))::numeric, 1)::float8 AS length
              FROM heatpipesections h
              JOIN linesobj l ON l.id = h.lineid AND COALESCE(l.removed, 0) = 0
             WHERE h.{col} IS NOT NULL AND h.{col} <> 0
             GROUP BY h.{col}
        )
        SELECT s.id, s.{name} AS name, s.nomer_uchastka AS ue_id, ue.nomer_uchastka AS ue_name,
               nach.id AS nach_id, nach.fio AS nach_name, s.magistral AS magistral_id,
               m.naimenovanie_magistrali AS magistral_name,
               COALESCE(p.pipes, 0) AS pipes, COALESCE(p.length, 0) AS length
          FROM {t} s
          LEFT JOIN uchastki_ekspluatatsii ue ON ue.id = s.nomer_uchastka
          LEFT JOIN nachalniki_uchastkov nach ON nach.id = ue.nachalnik_uchastka
          LEFT JOIN magistrali m ON m.id = s.magistral
          LEFT JOIN p ON p.site_id = s.id
         ORDER BY nach.fio NULLS LAST, s.{name}, s.id
        """
    )
    return [dict(r) for r in rows]


async def site_stats(conn, kind: SiteKind, site_id: int) -> dict[str, Any]:
    col = quote_ident(kind.pipe_column)
    row = await conn.fetchrow(
        f"""SELECT count(*)::int AS pipes,
                   round(COALESCE(sum(COALESCE(h.pipesectlength, ST_Length(l.shape), 0)), 0)::numeric, 1)::float8
                       AS length,
                   array_remove(array_agg(DISTINCT l.fileid), NULL) AS fragment_ids
              FROM heatpipesections h
              JOIN linesobj l ON l.id = h.lineid AND COALESCE(l.removed, 0) = 0
             WHERE h.{col} = $1""",
        site_id,
    )
    return {"pipes": row["pipes"], "length": row["length"], "fragment_ids": list(row["fragment_ids"] or [])}


async def get_site(conn, kind: SiteKind, site_id: int) -> dict[str, Any]:
    fields = await site_fields(conn, kind)
    record = await te.read_record(conn, kind.table, "id", site_id, fields)
    return {"kind": kind.key, "id": site_id, "title": kind.title, **record,
            "stats": await site_stats(conn, kind, site_id)}


async def _features(conn, where_sql: str, *args: Any) -> dict[str, Any]:
    """Трубы (linesobj + heatpipesections) → GeoJSON для подсветки на карте."""
    rows = await conn.fetch(
        f"""
        SELECT l.id AS line_id, l.fileid AS fragment_id, h.magistralsite, h.distsite,
               COALESCE(NULLIF(n1.nodename, ''), n1.externalnodename, '№' || n1.id) AS start_name,
               COALESCE(NULLIF(n2.nodename, ''), n2.externalnodename, '№' || n2.id) AS end_name,
               h.diametercondit AS diameter,
               round(COALESCE(h.pipesectlength, ST_Length(l.shape))::numeric, 1)::float8 AS length,
               -- участок внутренней схемы узла без геометрии: она в условных координатах схемы
               CASE WHEN l.shape IS NULL OR l.internalnodeid IS NOT NULL THEN NULL
                    ELSE ST_AsGeoJSON(ST_Transform(l.shape, 4326), 6) END AS geometry
          FROM linesobj l
          JOIN heatpipesections h ON h.lineid = l.id
          LEFT JOIN nodes n1 ON n1.id = l.nodeid1
          LEFT JOIN nodes n2 ON n2.id = l.nodeid2
         WHERE COALESCE(l.removed, 0) = 0 AND {where_sql}
         ORDER BY l.id
        """,
        *args,
    )
    features, lines = [], []
    xs: list[float] = []
    ys: list[float] = []
    for r in rows:
        item = dict(r)
        geometry = item.pop("geometry")
        item["diameter"] = float(item["diameter"]) if item["diameter"] is not None else None
        lines.append(item)
        if geometry:
            geom = json.loads(geometry)
            features.append({"type": "Feature", "geometry": geom, "properties": {"line_id": item["line_id"]}})
            for x, y in _coords(geom):
                xs.append(x)
                ys.append(y)
    bbox = [min(xs), min(ys), max(xs), max(ys)] if xs else None
    return {"lines": lines, "geojson": {"type": "FeatureCollection", "features": features}, "bbox": bbox}


def _coords(geom: dict[str, Any]):
    coords = geom.get("coordinates") or []
    if geom.get("type") == "LineString":
        yield from ((c[0], c[1]) for c in coords)
    elif geom.get("type") == "MultiLineString":
        for part in coords:
            yield from ((c[0], c[1]) for c in part)


async def site_pipes(conn, kind: SiteKind, site_id: int) -> dict[str, Any]:
    if not await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {quote_ident(kind.table)} WHERE id = $1)", site_id):
        raise PtsError(404, {"code": "not_found", "message": f"{kind.title} {site_id} не найден"})
    return await _features(conn, f"h.{quote_ident(kind.pipe_column)} = $1", site_id)


HIGHLIGHT_WHERE = {
    "ms": "h.magistralsite = $1",
    "rs": "h.distsite = $1",
    "nach": """(h.magistralsite IN (SELECT s.id FROM uchastok_ms s
                                     JOIN uchastki_ekspluatatsii ue ON ue.id = s.nomer_uchastka
                                    WHERE ue.nachalnik_uchastka = $1)
              OR h.distsite IN (SELECT s.id FROM uchastok_rs s
                                  JOIN uchastki_ekspluatatsii ue ON ue.id = s.nomer_uchastka
                                 WHERE ue.nachalnik_uchastka = $1))""",
}


async def highlight_extent(conn, kind: str, item_id: int) -> dict[str, Any]:
    """Подсветка на карте: трубы начальника участка (все его МС и РС) или одного участка.

    Отбор — как поле ``warning`` SQL-view heatpipesections (web-itwin
    scripts/geoserver/gid_desktop_style.py): трубы вне внутренних схем, фрагмент — по узлу 1.
    Охват — для «Перейти к участку», фрагменты — для предупреждения десктопа «фрагмент не подключен».
    """
    where = HIGHLIGHT_WHERE.get(str(kind).lower())
    if where is None:
        raise PtsError(404, {"code": "bad_kind", "message": "Подсветка: nach | ms | rs"})
    row = await conn.fetchrow(
        f"""
        WITH p AS (
            SELECT n1.fileid, l.shape
              FROM heatpipesections h
              JOIN linesobj l ON l.id = h.lineid AND l.removed = 0
              JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.internalnodeid IS NULL
             WHERE {where}
        ), e AS (SELECT ST_Extent(ST_Transform(shape, 4326)) AS box FROM p WHERE shape IS NOT NULL)
        SELECT (SELECT count(*)::int FROM p) AS pipes,
               (SELECT array_agg(DISTINCT fileid ORDER BY fileid) FROM p WHERE fileid IS NOT NULL) AS fragment_ids,
               ST_XMin(box) AS x1, ST_YMin(box) AS y1, ST_XMax(box) AS x2, ST_YMax(box) AS y2
          FROM e
        """,
        item_id,
    )
    bbox = [row["x1"], row["y1"], row["x2"], row["y2"]] if row["x1"] is not None else None
    return {"kind": kind, "id": item_id, "pipes": row["pipes"],
            "fragment_ids": list(row["fragment_ids"] or []), "bbox": bbox}


async def pipes_by_ids(conn, line_ids: list[int]) -> dict[str, Any]:
    return await _features(conn, "l.id = ANY($1::int[])", line_ids)


# ---------------------------------------------------------------------------
# Цепочка узлов → трубы пути
# ---------------------------------------------------------------------------

def shortest_path(adj: dict[int, list[tuple[int, int, float]]], start: int, goal: int) -> Optional[list[int]]:
    """Дейкстра по графу узлов; возвращает id линий пути (None — пути нет)."""
    if start == goal:
        return []
    dist = {start: 0.0}
    prev: dict[int, tuple[int, int]] = {}
    heap = [(0.0, start)]
    while heap:
        d, node = heapq.heappop(heap)
        if node == goal:
            break
        if d > dist.get(node, float("inf")):
            continue
        for other, line_id, w in adj.get(node, ()):
            nd = d + w
            if nd < dist.get(other, float("inf")):
                dist[other] = nd
                prev[other] = (node, line_id)
                heapq.heappush(heap, (nd, other))
    if goal not in prev:
        return None
    path: list[int] = []
    node = goal
    while node != start:
        node, line_id = prev[node]
        path.append(line_id)
    path.reverse()
    return path


async def resolve_chain(conn, node_ids: list[int]) -> dict[str, Any]:
    """Цепочка узлов → трубы кратчайших путей между соседними узлами (по порядку)."""
    chain = [int(n) for n in node_ids]
    if len(chain) < 2:
        raise PtsError(422, {"code": "bad_chain", "message": "Укажите минимум два узла цепочки"})
    if len(chain) > MAX_CHAIN_NODES:
        raise PtsError(422, {"code": "bad_chain", "message": f"Не больше {MAX_CHAIN_NODES} узлов в цепочке"})
    known = {r["id"] for r in await conn.fetch(
        "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0", chain)}
    missing = [n for n in chain if n not in known]
    if missing:
        raise PtsError(422, {"code": "bad_chain", "message": f"Узлы не найдены: {missing}"})
    rows = await conn.fetch(
        """SELECT l.id, l.nodeid1, l.nodeid2, GREATEST(COALESCE(ST_Length(l.shape), 1), 0.01)::float8 AS w,
                  EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id) AS is_pipe
             FROM linesobj l
            WHERE COALESCE(l.removed, 0) = 0 AND l.nodeid1 IS NOT NULL AND l.nodeid2 IS NOT NULL""")
    adj: dict[int, list[tuple[int, int, float]]] = {}
    pipes: set[int] = set()
    for r in rows:
        adj.setdefault(r["nodeid1"], []).append((r["nodeid2"], r["id"], r["w"]))
        adj.setdefault(r["nodeid2"], []).append((r["nodeid1"], r["id"], r["w"]))
        if r["is_pipe"]:
            pipes.add(r["id"])
    ordered: list[int] = []
    other_lines = 0
    segments = []
    for a, b in zip(chain, chain[1:]):
        path = shortest_path(adj, a, b)
        if path is None:
            raise PtsError(422, {"code": "no_path", "from": a, "to": b,
                                 "message": f"Между узлами {a} и {b} нет пути по сети — "
                                            "проверьте фрагменты или добавьте промежуточный узел"})
        segments.append({"from": a, "to": b, "lines": len(path)})
        for line_id in path:
            if line_id not in pipes:
                other_lines += 1
            elif line_id not in ordered:
                ordered.append(line_id)
    result = await pipes_by_ids(conn, ordered)
    return {"node_ids": chain, "line_ids": ordered, "segments": segments,
            "other_lines": other_lines, **result}


async def site_line_ids(conn, kind: SiteKind, site_id: int, line_ids: Optional[list[int]] = None) -> list[int]:
    """Трубы участка (или их пересечение с line_ids) — для снятия привязки только с этого участка."""
    col = quote_ident(kind.pipe_column)
    if line_ids is None:
        rows = await conn.fetch(f"SELECT DISTINCT lineid FROM heatpipesections WHERE {col} = $1", site_id)
    else:
        rows = await conn.fetch(
            f"SELECT DISTINCT lineid FROM heatpipesections WHERE {col} = $1 AND lineid = ANY($2::int[])",
            site_id, line_ids)
    return sorted(int(r["lineid"]) for r in rows)
