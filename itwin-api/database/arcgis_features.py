"""FeatureServer по GeoServices REST (фаза 2, п. 12 плана): слои сети для ArcGIS-клиентов, только чтение.

ArcGIS Pro, ArcGIS Online, QGIS («ArcGIS REST Server»), Esri Leaflet подключают слой по адресу
…/FeatureServer/<номер> и читают его запросом /query. Слои — те же коллекции, что у OGC API Features
(database/ogc_features.py): 0 участки, 1 узлы, 2 потребители, 3 источники, 4 задвижки.

Запрос /query понимает то, что шлют эти клиенты: where (1=1, «поле = число», OBJECTID IN (…)), objectIds,
geometry (оболочка Esri JSON или «xmin,ymin,xmax,ymax») c inSR, outFields, returnGeometry, outSR (4326 или
3857/102100), returnIdsOnly, returnCountOnly, resultOffset/resultRecordCount, f=json|pjson|geojson.
Произвольный SQL в where не принимается — разбирается в параметры.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from database.net_srid import net_srid
from database.ogc_features import COLLECTIONS, _KEYS

CURRENT_VERSION = 10.81
MAX_RECORD_COUNT = 2000
OID = "OBJECTID"
WEB_MERCATOR = {102100, 102113, 3857, 900913}
WGS84 = {4326}

# номер слоя → коллекция OGC
LAYERS: list[str] = ["pipes", "nodes", "consumers", "heat_sources", "valves"]
_GEOMETRY = {"LineString": "esriGeometryPolyline", "Point": "esriGeometryPoint"}
# типы полей Esri по свойствам коллекций (остальные — строки)
_FIELD_TYPES: dict[str, str] = {
    "fileid": "esriFieldTypeInteger", "node_start": "esriFieldTypeInteger", "node_end": "esriFieldTypeInteger",
    "sign": "esriFieldTypeInteger", "node_type": "esriFieldTypeInteger", "node_id": "esriFieldTypeInteger",
    "line_id": "esriFieldTypeInteger", "state": "esriFieldTypeInteger", "state_supply": "esriFieldTypeInteger",
    "state_return": "esriFieldTypeInteger", "diameter_mm": "esriFieldTypeDouble",
    "diameter_internal_mm": "esriFieldTypeDouble", "length_m": "esriFieldTypeDouble", "load_gcal_h": "esriFieldTypeDouble",
}
_ALIASES: dict[str, str] = {
    "fileid": "Фрагмент", "name": "Имя", "node_start": "Узел начала", "node_end": "Узел конца", "sign": "Признак",
    "diameter_mm": "Ду, мм", "diameter_internal_mm": "Внутренний диаметр, мм", "length_m": "Длина, м",
    "state_supply": "Состояние подачи", "state_return": "Состояние обратки", "node_type": "Вид узла",
    "kind": "Вид", "node_id": "Узел", "load_gcal_h": "Нагрузка, Гкал/ч", "line_id": "Участок", "state": "Состояние",
}
_WHERE_ALL = re.compile(r"^\s*(1\s*=\s*1)?\s*$")
_WHERE_EQ = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(-?\d+(?:\.\d+)?)\s*$")
_WHERE_IN = re.compile(r"^\s*OBJECTID\s+IN\s*\(\s*([\d\s,]*)\)\s*$", re.IGNORECASE)


class ArcgisError(Exception):
    """Ошибка запроса: ArcGIS-клиенты ждут {"error": {"code", "message"}} в теле с HTTP 200."""

    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Query:
    where_sql: list[str]
    params: list[Any]
    out_fields: list[str]
    return_geometry: bool
    out_srid: int
    limit: int
    offset: int


def layer_id_of(collection: str) -> int:
    return LAYERS.index(collection)


def collection_of(layer_id: int) -> str:
    if not 0 <= layer_id < len(LAYERS):
        raise ArcgisError(400, f"Слоя {layer_id} нет: 0…{len(LAYERS) - 1}")
    return LAYERS[layer_id]


def fields(cid: str) -> list[dict[str, Any]]:
    out = [{"name": OID, "type": "esriFieldTypeOID", "alias": OID}]
    for name in ["fileid", *(n for n, _ in COLLECTIONS[cid].props)]:
        ftype = _FIELD_TYPES.get(name, "esriFieldTypeString")
        field = {"name": name, "type": ftype, "alias": _ALIASES.get(name, name)}
        if ftype == "esriFieldTypeString":
            field["length"] = 255
        out.append(field)
    return out


def srid_of(raw: Any, default: int = 4326) -> int:
    """inSR/outSR: число или {"wkid": …}; поддерживаются 4326 и Web Mercator (3857/102100)."""
    if raw in (None, ""):
        return default
    if isinstance(raw, str):
        raw = raw.strip()
        if raw.startswith("{"):
            try:
                raw = json.loads(raw)
            except ValueError as exc:
                raise ArcgisError(400, "SR: неверный JSON") from exc
    if isinstance(raw, dict):
        raw = raw.get("latestWkid") or raw.get("wkid")
    try:
        wkid = int(raw)
    except (TypeError, ValueError) as exc:
        raise ArcgisError(400, "SR: ожидается wkid") from exc
    if wkid in WEB_MERCATOR:
        return 3857
    if wkid in WGS84:
        return 4326
    raise ArcgisError(400, f"Система координат {wkid} не поддерживается: 4326 или 3857/102100")


def parse_envelope(raw: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """geometry: {"xmin":…,"ymin":…,"xmax":…,"ymax":…} или «xmin,ymin,xmax,ymax»."""
    if not raw:
        return None
    raw = raw.strip()
    try:
        if raw.startswith("{"):
            g = json.loads(raw)
            box = (float(g["xmin"]), float(g["ymin"]), float(g["xmax"]), float(g["ymax"]))
        else:
            parts = [float(p) for p in raw.split(",")]
            if len(parts) != 4:
                raise ValueError
            box = (parts[0], parts[1], parts[2], parts[3])
    except (ValueError, KeyError, TypeError) as exc:
        raise ArcgisError(400, "geometry: оболочка xmin,ymin,xmax,ymax") from exc
    x1, y1, x2, y2 = box
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def parse_where(where: Optional[str], cid: str, key: str, frag: str) -> tuple[list[str], list[Any]]:
    """where → условия с параметрами; поле — только из полей слоя (имя не попадает в SQL как есть)."""
    if where is None or _WHERE_ALL.match(where):
        return [], []
    m = _WHERE_IN.match(where)
    if m:
        ids = [int(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        return [f"{key} = ANY({{}}::bigint[])"], [ids]
    m = _WHERE_EQ.match(where)
    if m:
        name, value = m.group(1), m.group(2)
        exprs = {OID.lower(): key, "fileid": frag, **{n: e for n, e in COLLECTIONS[cid].props}}
        expr = exprs.get(name.lower())
        if expr is None or (name.lower() not in (OID.lower(), "fileid")
                            and _FIELD_TYPES.get(name.lower(), "esriFieldTypeString") == "esriFieldTypeString"):
            raise ArcgisError(400, f"where: числовое поле слоя, а не «{name}»")
        return [f"{expr} = {{}}"], [float(value) if "." in value else int(value)]
    raise ArcgisError(400, "where: поддерживается 1=1, «поле = число» и OBJECTID IN (…)")


def build_query(cid: str, args: dict[str, Any]) -> Query:
    key, geom, frag = _KEYS[cid]
    where, params = parse_where(args.get("where"), cid, key, frag)
    ids = args.get("objectIds")
    if ids:
        try:
            id_list = [int(x) for x in str(ids).split(",") if x.strip()]
        except ValueError as exc:
            raise ArcgisError(400, "objectIds: числа через запятую") from exc
        where.append(f"{key} = ANY({{}}::bigint[])")
        params.append(id_list)
    box = parse_envelope(args.get("geometry"))
    if box is not None:
        in_srid = srid_of(args.get("inSR") or _sr_of_geometry(args.get("geometry")))
        where.append(f"{geom} && ST_Transform(ST_MakeEnvelope({{}}, {{}}, {{}}, {{}}, {in_srid}), {net_srid()})")
        params += list(box)
    out_fields_raw = str(args.get("outFields") or "*")
    known = [f["name"] for f in fields(cid)]
    if out_fields_raw.strip() == "*":
        out_fields = known
    else:
        wanted = [f.strip() for f in out_fields_raw.split(",") if f.strip()]
        out_fields = [k for k in known if k in wanted or k.lower() in (w.lower() for w in wanted)]
        if OID not in out_fields:
            out_fields.insert(0, OID)
    try:
        limit = int(args.get("resultRecordCount") or MAX_RECORD_COUNT)
        offset = int(args.get("resultOffset") or 0)
    except ValueError as exc:
        raise ArcgisError(400, "resultOffset/resultRecordCount: целые числа") from exc
    return Query(
        where_sql=where, params=params, out_fields=out_fields,
        return_geometry=str(args.get("returnGeometry", "true")).lower() != "false",
        out_srid=srid_of(args.get("outSR"), 4326),
        limit=max(1, min(limit, MAX_RECORD_COUNT)), offset=max(0, offset),
    )


def _sr_of_geometry(raw: Optional[str]) -> Any:
    if raw and raw.strip().startswith("{"):
        try:
            return (json.loads(raw).get("spatialReference") or {}).get("wkid")
        except ValueError:
            return None
    return None


def _numbered(parts: list[str], start: int = 1) -> tuple[str, int]:
    """Заменить {} на $1, $2, … по порядку."""
    out, n = [], start
    for part in parts:
        while "{}" in part:
            part = part.replace("{}", f"${n}", 1)
            n += 1
        out.append(part)
    return " AND ".join(out), n


def _base_sql(cid: str) -> tuple[str, str, str, str]:
    key, geom, frag = _KEYS[cid]
    if cid == "valves":
        geom = f"CASE WHEN GeometryType(ST_LineMerge(lo.shape)) = 'LINESTRING' THEN {geom} ELSE ST_PointOnSurface(lo.shape) END"
    return COLLECTIONS[cid].source, key, geom, frag


async def count(conn, cid: str, q: Query) -> int:
    source, key, _, _ = _base_sql(cid)
    cond, _ = _numbered(q.where_sql)
    return int(await conn.fetchval(f"SELECT count(*) FROM {source}{' AND ' + cond if cond else ''}", *q.params))


async def ids(conn, cid: str, q: Query) -> list[int]:
    source, key, _, _ = _base_sql(cid)
    cond, _ = _numbered(q.where_sql)
    rows = await conn.fetch(f"SELECT {key} AS fid FROM {source}{' AND ' + cond if cond else ''} ORDER BY {key}", *q.params)
    return [r["fid"] for r in rows]


async def features(conn, cid: str, q: Query) -> tuple[list[dict[str, Any]], bool]:
    """Строки слоя: (свойства, геометрия GeoJSON в outSR); второе — есть ещё (exceededTransferLimit)."""
    source, key, geom, frag = _base_sql(cid)
    cond, n = _numbered(q.where_sql)
    props = ", ".join(f"{expr} AS {name}" for name, expr in COLLECTIONS[cid].props)
    geom_sql = f"ST_AsGeoJSON(ST_Transform({geom}, {q.out_srid}), {7 if q.out_srid == 4326 else 2})" \
        if q.return_geometry else "NULL"
    rows = await conn.fetch(
        f"""SELECT {key} AS fid, {frag} AS fileid, {geom_sql} AS geometry, {props}
              FROM {source}{' AND ' + cond if cond else ''}
             ORDER BY {key} LIMIT ${n} OFFSET ${n + 1}""", *q.params, q.limit + 1, q.offset)
    more = len(rows) > q.limit
    out = []
    for r in rows[:q.limit]:
        attrs: dict[str, Any] = {OID: r["fid"], "fileid": r["fileid"]}
        for name, _ in COLLECTIONS[cid].props:
            v = r[name]
            attrs[name] = v.strip() if isinstance(v, str) else (float(v) if hasattr(v, "is_finite") else v)
        out.append({"attributes": {k: v for k, v in attrs.items() if k in q.out_fields},
                    "geometry": json.loads(r["geometry"]) if r["geometry"] else None})
    return out, more


def esri_geometry(g: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """GeoJSON → Esri JSON (точка, полилиния)."""
    if not g:
        return None
    t, c = g.get("type"), g.get("coordinates")
    if t == "Point":
        return {"x": c[0], "y": c[1]}
    if t == "LineString":
        return {"paths": [c]}
    if t == "MultiLineString":
        return {"paths": c}
    if t == "MultiPoint" and c:
        return {"x": c[0][0], "y": c[0][1]}
    return None


def wkid_of(srid: int) -> dict[str, int]:
    return {"wkid": 102100, "latestWkid": 3857} if srid == 3857 else {"wkid": 4326, "latestWkid": 4326}


def layer_info(cid: str, extent: list[float]) -> dict[str, Any]:
    col = COLLECTIONS[cid]
    return {
        "currentVersion": CURRENT_VERSION,
        "id": layer_id_of(cid),
        "name": col.title,
        "type": "Feature Layer",
        "description": col.description,
        "geometryType": _GEOMETRY[col.geometry],
        "sourceSpatialReference": wkid_of(4326),
        "objectIdField": OID,
        "displayField": "name",
        "fields": fields(cid),
        "extent": {"xmin": extent[0], "ymin": extent[1], "xmax": extent[2], "ymax": extent[3],
                   "spatialReference": wkid_of(4326)},
        "hasAttachments": False,
        "htmlPopupType": "esriServerHTMLPopupTypeNone",
        "capabilities": "Query",
        "maxRecordCount": MAX_RECORD_COUNT,
        "standardMaxRecordCount": MAX_RECORD_COUNT,
        "supportedQueryFormats": "JSON, geoJSON",
        "supportsPagination": True,
        "useStandardizedQueries": True,
        "advancedQueryCapabilities": {
            "supportsPagination": True, "supportsQueryWithResultType": False, "supportsOrderBy": False,
            "supportsDistinct": False, "supportsStatistics": False, "supportsReturningQueryExtent": False,
            "supportsCountDistinct": False,
        },
        "minScale": 0,
        "maxScale": 0,
    }


def service_info(extent: list[float], description: str) -> dict[str, Any]:
    env = {"xmin": extent[0], "ymin": extent[1], "xmax": extent[2], "ymax": extent[3], "spatialReference": wkid_of(4326)}
    return {
        "currentVersion": CURRENT_VERSION,
        "serviceDescription": description,
        "description": description,
        "copyrightText": "ТГИД",
        "hasVersionedData": False,
        "supportsDisconnectedEditing": False,
        "supportedQueryFormats": "JSON, geoJSON",
        "maxRecordCount": MAX_RECORD_COUNT,
        "capabilities": "Query",
        "spatialReference": wkid_of(4326),
        "initialExtent": env,
        "fullExtent": env,
        "units": "esriDecimalDegrees",
        "allowGeometryUpdates": False,
        "layers": [{"id": i, "name": COLLECTIONS[cid].title, "parentLayerId": -1, "defaultVisibility": True,
                    "subLayerIds": None, "minScale": 0, "maxScale": 0,
                    "geometryType": _GEOMETRY[COLLECTIONS[cid].geometry]} for i, cid in enumerate(LAYERS)],
        "tables": [],
    }


def to_esri_json(cid: str, q: Query, rows: list[dict[str, Any]], more: bool) -> dict[str, Any]:
    return {
        "objectIdFieldName": OID,
        "globalIdFieldName": "",
        "geometryType": _GEOMETRY[COLLECTIONS[cid].geometry],
        "spatialReference": wkid_of(q.out_srid),
        "fields": [f for f in fields(cid) if f["name"] in q.out_fields],
        "features": [{"attributes": r["attributes"], **({"geometry": esri_geometry(r["geometry"])} if q.return_geometry else {})}
                     for r in rows],
        "exceededTransferLimit": more,
    }


def to_geojson(rows: list[dict[str, Any]], more: bool) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "id": r["attributes"].get(OID), "geometry": r["geometry"],
                      "properties": r["attributes"]} for r in rows],
        "exceededTransferLimit": more,
    }
