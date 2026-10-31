"""Общая карта коммуникаций (фаза 4, шаг 5): сближения и пересечения сетей разных видов, проверка раскопок.

Сети: теплосеть (linesobj + паспорт heatpipesections: наружный диаметр; глубина — tgid_heat_depth; SRID сети) и
водопровод (модель tgid_water_link, 4326). Пары подачи и обратки теплосети лежат на одной геометрии — считаются
одним коридором (DISTINCT ON по геометрии).

- **Сближение** — участки, расстояние между которыми в свету (ось — ось минус половины наружных диаметров) меньше
  нормы по горизонтали (tgid_utility_norm): длина сближения и ближайшая точка. Норма теплосети в СНиП — от наружной
  стенки канала; ширины канала в паспорте нет, считается от наружной стенки трубы — в канальной прокладке
  расстояние в свету фактически меньше.
- **Пересечение** — трассы пересекаются в плане: точка пересечения, глубина верха и низа трубы теплосети в ней
  (database/heat_depth.py — из отметок узлов, поле паспорта не заполнено); глубин водопровода в модели нет —
  расстояние по вертикали проверяет инженер.
- **Раскопки** — сети в зоне работ (точка, линия или контур + отступ): участки, владельцы, фрагменты, расстояние.

Поиск — по пространственному индексу сети города (bbox в её SRID с запасом), расстояния — по geography (метры
на эллипсоиде, верно для любой системы координат города).
"""
from __future__ import annotations

import json
import math
from typing import Any, Optional

from database import heat_depth
from database.net_srid import net_srid

KINDS = ("heat", "water")
MAX_CONFLICTS = 2000
MAX_DIG_FEATURES = 500
MAX_DIG_EXTENT_M = 5000.0
MAX_DIG_BUFFER_M = 200.0
MIN_DIG_BUFFER_M = 0.5
PAD_FACTOR = 2.5                      # запас bbox в SRID сети: 3857 растягивает метры в 1/cos(широты), до 60° — в 2


class UtilityError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def clearance_m(axis_m: float, d_a_mm: Optional[float], d_b_mm: Optional[float]) -> float:
    """Расстояние в свету: между осями минус половины наружных диаметров (нет диаметра — 0)."""
    return axis_m - ((d_a_mm or 0) + (d_b_mm or 0)) / 2000


def verdict(crosses: bool, axis_m: float, d_a_mm: Optional[float], d_b_mm: Optional[float],
            norm_m: Optional[float]) -> Optional[str]:
    """crossing — трассы пересекаются; close — ближе нормы; None — норма соблюдена или её нет."""
    if crosses:
        return "crossing"
    if norm_m is None:
        return None
    return "close" if clearance_m(axis_m, d_a_mm, d_b_mm) < norm_m else None


def pad_units(metres: float, srid: int) -> float:
    """Запас поиска в единицах SRID сети: метры (местная, UTM, 3857 — с запасом на растяжение) или градусы."""
    if srid == 4326:
        return metres * PAD_FACTOR / 111_000
    return metres * PAD_FACTOR


def dig_geometry(geojson: dict[str, Any]) -> dict[str, Any]:
    """Зона раскопок: точка, линия или контур в WGS84 не больше MAX_DIG_EXTENT_M по стороне."""
    if not isinstance(geojson, dict) or geojson.get("type") not in ("Point", "LineString", "Polygon"):
        raise UtilityError(422, "Зона работ — GeoJSON Point, LineString или Polygon")
    coords = geojson.get("coordinates")
    flat: list[Any] = []

    def walk(v: Any) -> None:
        if isinstance(v, (list, tuple)) and len(v) >= 2 and all(isinstance(x, (int, float)) for x in v[:2]):
            flat.append(v)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(coords)
    if not flat or len(flat) > 5000:
        raise UtilityError(422, "В зоне работ нет координат или их больше 5000")
    lons, lats = [p[0] for p in flat], [p[1] for p in flat]
    if not (-180 <= min(lons) <= max(lons) <= 180 and -90 <= min(lats) <= max(lats) <= 90):
        raise UtilityError(422, "Координаты зоны работ — долгота и широта WGS84")
    lat0 = (min(lats) + max(lats)) / 2
    width = (max(lons) - min(lons)) * 111_320 * math.cos(math.radians(lat0))
    height = (max(lats) - min(lats)) * 110_540
    if max(width, height) > MAX_DIG_EXTENT_M:
        raise UtilityError(422, f"Зона работ больше {MAX_DIG_EXTENT_M / 1000:g} км")
    return {"type": geojson["type"], "coordinates": coords}


# --- нормы ---------------------------------------------------------------------------------------

def _pair(a: str, b: str) -> tuple[str, str]:
    if a not in KINDS or b not in KINDS:
        raise UtilityError(422, f"Вид сети — {', '.join(KINDS)}")
    return (a, b) if a <= b else (b, a)


async def list_norms(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch("SELECT * FROM tgid_utility_norm ORDER BY kind_a, kind_b")
    return [{**dict(r), "updated_at": r["updated_at"].isoformat()} for r in rows]


async def set_norm(conn, kind_a: str, kind_b: str, horizontal_m: Optional[float], vertical_m: Optional[float],
                   source: Optional[str], user: str) -> dict[str, Any]:
    a, b = _pair(kind_a, kind_b)
    row = await conn.fetchrow(
        """INSERT INTO tgid_utility_norm (kind_a, kind_b, horizontal_m, vertical_m, source, updated_by, updated_at)
           VALUES ($1, $2, $3, $4, $5, $6, now())
           ON CONFLICT (kind_a, kind_b) DO UPDATE SET horizontal_m = EXCLUDED.horizontal_m,
               vertical_m = EXCLUDED.vertical_m, source = EXCLUDED.source, updated_by = EXCLUDED.updated_by,
               updated_at = now()
           RETURNING *""", a, b, horizontal_m, vertical_m, (source or "")[:300] or None, user)
    return {**dict(row), "updated_at": row["updated_at"].isoformat()}


async def _norm(conn, a: str, b: str) -> Optional[dict[str, Any]]:
    a, b = _pair(a, b)
    row = await conn.fetchrow("SELECT * FROM tgid_utility_norm WHERE kind_a = $1 AND kind_b = $2", a, b)
    return dict(row) if row else None


# --- глубина теплосети в точке (database/heat_depth.py) ----------------------------------------------

# глубина верха трубы в точке участка: между концами пропорционально положению точки; известен один конец — он
_DEPTH_AT = ("coalesce(depth_start + (depth_end - depth_start) * ST_LineLocatePoint({line}, {pt}), "
             "depth_start, depth_end)")


def _depth_fields(top_m: Optional[float], d_mm: Optional[float], source: Optional[str]) -> dict[str, Any]:
    """Глубина теплосети в пересечении: верх и низ трубы (верх + наружный диаметр), источник."""
    if top_m is None:
        return {"heat_depth_top_m": None, "heat_depth_bottom_m": None, "heat_depth_source": None}
    return {"heat_depth_top_m": round(top_m, 2),
            "heat_depth_bottom_m": round(top_m + (d_mm or 0) / 1000, 2), "heat_depth_source": source}


# --- сближения и пересечения ---------------------------------------------------------------------

_HEAT_PASSPORT = """LEFT JOIN LATERAL (
        SELECT NULLIF(diameterexternal, 0) AS dext, NULLIF(diametercondit, 0) AS dn
          FROM heatpipesections WHERE lineid = l.id ORDER BY id LIMIT 1) h ON true
      LEFT JOIN tgid_heat_depth hd ON hd.lineid = l.id"""


async def water_heat_conflicts(conn, model_id: int) -> dict[str, Any]:
    """Сближения и пересечения труб модели водопровода с теплосетью города по норме heat — water."""
    if await conn.fetchval("SELECT 1 FROM tgid_water_model WHERE id = $1", model_id) is None:
        raise UtilityError(404, "Модель водопровода не найдена")
    await heat_depth.ensure(conn)
    norm = await _norm(conn, "heat", "water")
    norm_m = norm["horizontal_m"] if norm else None
    reach = (norm_m or 0) + 2.0                     # + наружные диаметры: до 2 м на двоих с запасом
    srid = net_srid()
    rows = await conn.fetch(
        f"""WITH w AS (
                SELECT link_id, diameter_mm AS dw, geom, ST_Transform(geom, {srid}) AS gn
                  FROM tgid_water_link WHERE model_id = $1 AND type = 'Pipe' AND geom IS NOT NULL),
            c AS (
                SELECT DISTINCT ON (w.link_id, md5(ST_AsBinary(l.shape)))
                       w.link_id, w.dw, w.geom AS wg, l.id AS line_id, l.fileid,
                       ST_Transform(l.shape, 4326) AS hg, coalesce(h.dext, h.dn) AS dh,
                       hd.depth_start, hd.depth_end, hd.source AS depth_source,
                       count(*) OVER (PARTITION BY w.link_id, md5(ST_AsBinary(l.shape))) AS pipes
                  FROM w JOIN linesobj l ON l.shape && ST_Expand(w.gn, $2) AND l.shape IS NOT NULL
                  {_HEAT_PASSPORT}
                 ORDER BY w.link_id, md5(ST_AsBinary(l.shape)), l.id),
            d AS (
                SELECT c.*, ST_Distance(wg::geography, hg::geography) AS axis_m, ST_Intersects(wg, hg) AS crosses
                  FROM c)
            SELECT link_id, dw, line_id, fileid, dh, pipes, axis_m, crosses, depth_source,
                   CASE WHEN crosses THEN {_DEPTH_AT.format(line="hg", pt="ST_PointOnSurface(ST_Intersection(wg, hg))")}
                   END AS depth,
                   ST_AsGeoJSON(CASE WHEN crosses THEN ST_PointOnSurface(ST_Intersection(wg, hg))
                                     ELSE ST_ClosestPoint(wg, hg) END, 7) AS pt,
                   CASE WHEN crosses THEN NULL
                        ELSE ST_Length(ST_Intersection(wg, ST_Buffer(hg::geography, $3)::geometry)::geography)
                   END AS near_m
              FROM d
             WHERE crosses OR axis_m < $3
             ORDER BY crosses DESC, axis_m
             LIMIT {MAX_CONFLICTS + 1}""",
        model_id, pad_units(reach, srid), reach)
    crossings, close = [], []
    for r in rows[:MAX_CONFLICTS]:
        kind = verdict(r["crosses"], r["axis_m"], r["dw"], r["dh"], norm_m)
        if kind is None:
            continue
        item = {"water_link": r["link_id"], "heat_line": r["line_id"], "fileid": r["fileid"],
                "water_d_mm": r["dw"], "heat_d_mm": r["dh"], "heat_pipes": r["pipes"],
                "point": json.loads(r["pt"]) if r["pt"] else None}
        if kind == "crossing":
            crossings.append({**item, **_depth_fields(r["depth"], r["dh"], r["depth_source"])})
        else:
            close.append({**item, "axis_m": round(r["axis_m"], 2),
                          "clearance_m": round(clearance_m(r["axis_m"], r["dw"], r["dh"]), 2),
                          "near_length_m": round(r["near_m"] or 0, 1)})
    return {"model_id": model_id, "norm": norm, "crossings": crossings, "close": close,
            "truncated": len(rows) > MAX_CONFLICTS,
            "summary": {"crossings": len(crossings), "close": len(close),
                        "close_length_m": round(sum(c["near_length_m"] for c in close), 1)}}


# --- раскопки ------------------------------------------------------------------------------------

async def excavation(conn, geometry: dict[str, Any], buffer_m: float,
                     water_model: Optional[int] = None) -> dict[str, Any]:
    """Сети в зоне работ (геометрия + отступ buffer_m): теплосеть с владельцами и фрагментами, водопровод моделей.
    Участки отсортированы по расстоянию до зоны работ; features — для карты (зона и участки)."""
    if not 0 <= buffer_m <= MAX_DIG_BUFFER_M:
        raise UtilityError(422, f"Отступ — от 0 до {MAX_DIG_BUFFER_M:g} м")
    g = json.dumps(dig_geometry(geometry))
    reach = max(buffer_m, MIN_DIG_BUFFER_M)     # точка без отступа — ничего не задевает
    await heat_depth.ensure(conn)
    srid = net_srid()
    heat = await conn.fetch(
        f"""WITH a AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON($1), 4326) AS g),
                 z AS (SELECT g, ST_Buffer(g::geography, $2)::geometry AS zone FROM a),
                 zn AS (SELECT z.*, ST_Transform(zone, {srid}) AS zn FROM z)
            SELECT DISTINCT ON (md5(ST_AsBinary(l.shape)))
                   l.id, l.fileid, f.name AS fragment, o.name AS owner, coalesce(h.dext, h.dn) AS d_mm,
                   least(hd.depth_start, hd.depth_end) AS depth_min,
                   greatest(hd.depth_start, hd.depth_end) AS depth_max, hd.source AS depth_source,
                   count(*) OVER (PARTITION BY md5(ST_AsBinary(l.shape))) AS pipes,
                   ST_Distance(zn.g::geography, ST_Transform(l.shape, 4326)::geography) AS dist_m,
                   ST_AsGeoJSON(ST_Transform(l.shape, 4326), 7) AS geom
              FROM zn JOIN linesobj l ON l.shape && zn.zn AND ST_Intersects(l.shape, zn.zn)
              LEFT JOIN fragments f ON f.id = l.fileid
              LEFT JOIN organizations o ON o.id = l.organizationid
              {_HEAT_PASSPORT}
             ORDER BY md5(ST_AsBinary(l.shape)), l.id
             LIMIT {MAX_DIG_FEATURES}""", g, reach)
    water = await conn.fetch(
        """WITH a AS (SELECT ST_SetSRID(ST_GeomFromGeoJSON($1), 4326) AS g),
                z AS (SELECT g, ST_Buffer(g::geography, $2)::geometry AS zone FROM a)
           SELECT wl.model_id, m.name AS model, wl.link_id, wl.type, wl.diameter_mm AS d_mm,
                  ST_Distance(z.g::geography, wl.geom::geography) AS dist_m, ST_AsGeoJSON(wl.geom, 7) AS geom
             FROM z JOIN tgid_water_link wl ON wl.geom && z.zone AND ST_Intersects(wl.geom, z.zone)
             JOIN tgid_water_model m ON m.id = wl.model_id
            WHERE $3::int IS NULL OR wl.model_id = $3
            ORDER BY dist_m LIMIT $4""", g, reach, water_model, MAX_DIG_FEATURES)
    zone = await conn.fetchval(
        "SELECT ST_AsGeoJSON(ST_Buffer(ST_SetSRID(ST_GeomFromGeoJSON($1), 4326)::geography, $2)::geometry, 7)",
        g, reach)
    heat_items = sorted(({"id": r["id"], "fileid": r["fileid"], "fragment": r["fragment"], "owner": r["owner"],
                          "d_mm": r["d_mm"], "depth_min_m": r["depth_min"], "depth_max_m": r["depth_max"],
                          "depth_source": r["depth_source"], "pipes": r["pipes"],
                          "distance_m": round(r["dist_m"], 1)} for r in heat), key=lambda x: x["distance_m"])
    water_items = [{"model_id": r["model_id"], "model": r["model"], "link": r["link_id"], "type": r["type"],
                    "d_mm": r["d_mm"], "distance_m": round(r["dist_m"], 1)} for r in water]
    owners: dict[str, int] = {}
    for x in heat_items:
        owners[x["owner"] or "—"] = owners.get(x["owner"] or "—", 0) + 1
    features = [{"type": "Feature", "geometry": json.loads(zone), "properties": {"kind": "zone"}}]
    features += [{"type": "Feature", "geometry": json.loads(r["geom"]),
                  "properties": {"kind": "heat", "id": r["id"], "distance_m": round(r["dist_m"], 1)}} for r in heat]
    features += [{"type": "Feature", "geometry": json.loads(r["geom"]),
                  "properties": {"kind": "water", "id": r["link_id"], "distance_m": round(r["dist_m"], 1)}}
                 for r in water]
    return {"buffer_m": buffer_m, "heat": heat_items, "water": water_items,
            "owners": dict(sorted(owners.items(), key=lambda kv: -kv[1])),
            "truncated": len(heat) >= MAX_DIG_FEATURES or len(water) >= MAX_DIG_FEATURES,
            "geojson": {"type": "FeatureCollection", "features": features}}
