"""OGC API — Features, часть 1 (Core) и GeoJSON: слои сети для внешних систем (фаза 1).

Обмен с акиматами, QGIS, ArcGIS и другими ГИС без GeoServer: стандартные адреса
/collections/{id}/items, геометрия — GeoJSON в WGS84 (CRS84), постраничная выдача (limit/offset,
ссылка next). Только чтение; запись (часть 4, транзакции) — после прав по объектам.

Коллекция — запрос к таблицам десктопа: участки (с первым паспортом трубы), узлы, потребители
(реальные и обобщённые, точка узла присоединения), источники, задвижки (середина участка).
Фильтры: bbox (WGS84: minLon,minLat,maxLon,maxLat) и fileid — фрагмент.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from database.net_srid import net_srid

DEFAULT_LIMIT = 100
MAX_LIMIT = 10_000

# Нагрузки потребителей, Гкал/ч — те же суммы, что в анализе режима (database/regime_queries.py)
_RC_LOAD = ("COALESCE(rc.calchldep, 0) + COALESCE(rc.calchlindep, 0) + COALESCE(rc.calchlventil, 0)"
            " + COALESCE(rc.avghlclosesys, 0) + COALESCE(rc.avghlopensysflow, 0) + COALESCE(rc.avghlopensysret, 0)")
_GC_LOAD = ("COALESCE(gc.calchldep, 0) + COALESCE(gc.calchlindep, 0) + COALESCE(gc.calchlparall, 0)"
            " + COALESCE(gc.calchlmix, 0) + COALESCE(gc.calchlconseq, 0) + COALESCE(gc.calchlpreon, 0)"
            " + COALESCE(gc.calchlventil, 0) + COALESCE(gc.calchlclosesys, 0)"
            " + COALESCE(gc.calchlopensysflow, 0) + COALESCE(gc.calchlopensysret, 0)")


@dataclass(frozen=True)
class Collection:
    id: str
    title: str
    description: str
    geometry: str           # тип геометрии для метаданных
    # FROM-часть с алиасами; колонки: fid (id объекта), geom (shape сети), fileid, свойства — props
    source: str
    props: tuple[tuple[str, str], ...]   # (имя свойства, SQL-выражение)


COLLECTIONS: dict[str, Collection] = {c.id: c for c in (
    Collection(
        "pipes", "Участки теплосети",
        "Живые участки с геометрией и первым паспортом трубы: Ду, внутренний диаметр, длина, состояние труб.",
        "LineString",
        """linesobj lo
           LEFT JOIN LATERAL (SELECT diametercondit, diameterinternal, pipesectlength,
                                     pipesectstateidflow, pipesectstateidret
                                FROM heatpipesections WHERE lineid = lo.id ORDER BY id LIMIT 1) h ON true
          WHERE COALESCE(lo.removed, 0) = 0 AND lo.shape IS NOT NULL""",
        (("name", "lo.registnum"), ("node_start", "lo.nodeid1"), ("node_end", "lo.nodeid2"),
         ("sign", "lo.externalsignlineid"), ("diameter_mm", "h.diametercondit"),
         ("diameter_internal_mm", "h.diameterinternal"), ("length_m", "h.pipesectlength"),
         ("state_supply", "h.pipesectstateidflow"), ("state_return", "h.pipesectstateidret")),
    ),
    Collection(
        "nodes", "Узлы сети",
        "Живые узлы основной схемы (без узлов внутренних схем) с видом узла.",
        "Point",
        "nodes n WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL AND n.internalnodeid IS NULL",
        (("name", "COALESCE(NULLIF(btrim(n.nodename), ''), n.externalnodename)"),
         ("node_type", "n.nodetypeid")),
    ),
    Collection(
        "consumers", "Потребители",
        "Реальные и обобщённые потребители в точке узла присоединения; нагрузка — сумма расчётных, Гкал/ч.",
        "Point",
        f"""(SELECT rc.id, rc.nodeid, rc.name, 'real' AS kind, ({_RC_LOAD})::float AS load FROM realconsumers rc
             UNION ALL
             SELECT gc.id, gc.nodeid, gc.name, 'generalized', ({_GC_LOAD})::float FROM generalizedconsumers gc) c
           JOIN nodes n ON n.id = c.nodeid
          WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL""",
        (("name", "c.name"), ("kind", "c.kind"), ("node_id", "c.nodeid"), ("load_gcal_h", "c.load")),
    ),
    Collection(
        "heat_sources", "Источники тепла",
        "Источники тепла в точке своего узла.",
        "Point",
        "heatsources hs JOIN nodes n ON n.id = hs.nodeid WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL",
        (("name", "hs.name"), ("node_id", "hs.nodeid")),
    ),
    Collection(
        "valves", "Задвижки",
        "Задвижки на участках основной схемы (в середине участка) и их состояние: 1 открыта, 2 закрыта.",
        "Point",
        """dampers d JOIN linesobj lo ON lo.id = d.lineid
          WHERE COALESCE(lo.removed, 0) = 0 AND lo.shape IS NOT NULL""",
        (("name", "d.name"), ("line_id", "d.lineid"), ("diameter_mm", "d.diametercondit"),
         ("state", "d.damperarmaturestateid")),
    ),
)}

# id объекта, геометрия сети и фрагмент для каждой коллекции
_KEYS: dict[str, tuple[str, str, str]] = {
    "pipes": ("lo.id", "lo.shape", "lo.fileid"),
    "nodes": ("n.id", "n.shape", "n.fileid"),
    "consumers": ("c.id", "n.shape", "n.fileid"),
    "heat_sources": ("hs.id", "n.shape", "n.fileid"),
    "valves": ("d.id", "ST_LineInterpolatePoint(ST_LineMerge(lo.shape), 0.5)", "lo.fileid"),
}


def parse_bbox(raw: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """bbox=minLon,minLat,maxLon,maxLat (CRS84). ValueError — неверный формат или порядок."""
    if raw is None or raw == "":
        return None
    parts = raw.split(",")
    if len(parts) != 4:
        raise ValueError("bbox: четыре числа minLon,minLat,maxLon,maxLat")
    try:
        x1, y1, x2, y2 = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError("bbox: числа через запятую") from exc
    if not (-180 <= x1 <= x2 <= 180 and -90 <= y1 <= y2 <= 90):
        raise ValueError("bbox: долгота −180…180, широта −90…90, min ≤ max")
    return x1, y1, x2, y2


def _query(cid: str, *, fid: Optional[int], bbox, fileid: Optional[int], limit: int, offset: int) -> tuple[str, list]:
    col = COLLECTIONS[cid]
    key, geom, frag = _KEYS[cid]
    # MultiLineString линии — как есть; середина задвижки — только у односвязной линии
    if cid == "valves":
        geom = f"CASE WHEN GeometryType(ST_LineMerge(lo.shape)) = 'LINESTRING' THEN {geom} ELSE ST_PointOnSurface(lo.shape) END"
    props = ", ".join(f"{expr} AS {name}" for name, expr in col.props)
    where, params = [], []
    if fid is not None:
        params.append(fid)
        where.append(f"{key} = ${len(params)}")
    if fileid is not None:
        params.append(fileid)
        where.append(f"{frag} = ${len(params)}")
    if bbox is not None:
        params += list(bbox)
        n = len(params)
        where.append(f"{geom} && ST_Transform(ST_MakeEnvelope(${n - 3}, ${n - 2}, ${n - 1}, ${n}, 4326), {net_srid()})")
    params += [limit, offset]
    extra = "".join(f" AND {w}" for w in where)
    sql = (f"SELECT {key} AS fid, {frag} AS fileid, ST_AsGeoJSON(ST_Transform({geom}, 4326), 7) AS geometry, {props} "
           f"FROM {col.source}{extra} ORDER BY {key} LIMIT ${len(params) - 1} OFFSET ${len(params)}")
    return sql, params


def _feature(cid: str, row) -> dict[str, Any]:
    props = {"fileid": row["fileid"]}
    for name, _ in COLLECTIONS[cid].props:
        v = row[name]
        props[name] = v.strip() if isinstance(v, str) else (float(v) if hasattr(v, "is_finite") else v)
    return {
        "type": "Feature",
        "id": row["fid"],
        "geometry": json.loads(row["geometry"]) if row["geometry"] else None,
        "properties": props,
    }


async def get_items(conn, cid: str, *, bbox=None, fileid: Optional[int] = None,
                    limit: int = DEFAULT_LIMIT, offset: int = 0) -> list[dict[str, Any]]:
    sql, params = _query(cid, fid=None, bbox=bbox, fileid=fileid, limit=limit, offset=offset)
    return [_feature(cid, r) for r in await conn.fetch(sql, *params)]


async def get_item(conn, cid: str, fid: int) -> Optional[dict[str, Any]]:
    sql, params = _query(cid, fid=fid, bbox=None, fileid=None, limit=1, offset=0)
    row = await conn.fetchrow(sql, *params)
    return _feature(cid, row) if row else None
