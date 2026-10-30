"""Социальные объекты (POI, фаза 2): школы, детские сады, больницы, поликлиники, учреждения соцзащиты.

Зачем: выборки «участки в 500 м от школ» (database/network_select.py, near_poi) и приоритет при отключениях —
какие социальные объекты попадают в зону (database/outages.py).

Источники (tgid_poi.source):
- consumers — найдены по названию потребителя сети («Школа 23», «Д/С № 26», «Роддом N1»): объект в точке узла
  присоединения, по одному на узел и категорию. Загрузок из интернета не нужно;
- file — файл акимата (GeoJSON; CSV веб превращает в GeoJSON сам): точки или контуры (берётся точка внутри);
- osm — OpenStreetMap через Overpass API (OVERPASS_URL) в охвате сети города, по кнопке администратора.
Ошибочно найденный объект администратор скрывает (hidden): повторная загрузка этот выбор не сбрасывает.
"""
from __future__ import annotations

import json
import math
import os
import re
from collections import Counter, defaultdict
from typing import Any, Optional

from pydantic import BaseModel, Field

CATEGORIES: dict[str, str] = {
    "school": "Школы",
    "kindergarten": "Детские сады",
    "hospital": "Больницы",
    "clinic": "Поликлиники",
    "social": "Соцучреждения",
}
CATEGORY_ONE: dict[str, str] = {
    "school": "школа", "kindergarten": "детский сад", "hospital": "больница", "clinic": "поликлиника",
    "social": "соцучреждение",
}
SOURCES: dict[str, str] = {"consumers": "потребители сети", "file": "файл", "osm": "OpenStreetMap"}

MAX_IMPORT = 20_000
MAX_LIST = 2_000
CONSUMERS_KEPT = 20
# одно здание: потребители с тем же названием не дальше этого
MERGE_RADIUS_M = 150
OVERPASS_TIMEOUT_S = 90
DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# дальше этого от охвата сети — подозрение на перепутанные широту и долготу
OUTSIDE_MARGIN_DEG = 0.5

# Название потребителя → категория. Порядок важен: «детская больница» — больница, «лицей-интернат» — школа
_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("hospital", re.compile(r"больниц|госпитал|роддом|родильн|перинатал|аурухана|хоспис", re.I)),
    ("clinic", re.compile(r"поликлиник|амбулатор|\bфап\b|медпункт|мед\.?\s?центр|центр здоровья|диспансер|"
                          r"емхана|травмпункт", re.I)),
    ("kindergarten", re.compile(r"детск\w*\s+сад|\bд/\s?с|\bд/сад|\bдс\b|ясл[иь]|балабақша|бөбекжай|мини-центр", re.I)),
    ("school", re.compile(r"школ|гимнази|лице[йяе]\b|лицей|\bсош\b|\bсш\b|\bсш[№n\d]|мектеп", re.I)),
    ("social", re.compile(r"интернат|приют|дом\s+престарел|дом\s+ребенка|центр\s+социальн|соц\.?\s?центр", re.I)),
)
# не социальные, хотя похожи
_NOT_SOCIAL = re.compile(r"автошкол|школ\w*\s+вожден|яз\.?\s*школ|языков|бизнес[- ]школ", re.I)

# OpenStreetMap: amenity → категория
OSM_AMENITY: dict[str, str] = {
    "school": "school", "kindergarten": "kindergarten", "hospital": "hospital", "clinic": "clinic",
    "doctors": "clinic", "social_facility": "social",
}


class PoiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def classify(name: Optional[str]) -> Optional[str]:
    """Категория по названию потребителя; None — не социальный объект."""
    text = (name or "").strip()
    if not text or _NOT_SOCIAL.search(text):
        return None
    for category, rx in _RULES:
        if rx.search(text):
            return category
    return None


def check_categories(values: Optional[list[str]]) -> list[str]:
    cats = [c for c in (values or []) if c]
    unknown = [c for c in cats if c not in CATEGORIES]
    if unknown:
        raise PoiError(422, f"Неизвестные категории: {', '.join(unknown)}")
    return cats or list(CATEGORIES)


def categories_label(categories: list[str]) -> str:
    """«школ и детских садов» — для описания выборки."""
    plural = {"school": "школ", "kindergarten": "детских садов", "hospital": "больниц", "clinic": "поликлиник",
              "social": "соцучреждений"}
    words = [plural[c] for c in categories if c in plural]
    if len(words) == len(CATEGORIES):
        return "социальных объектов"
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " и " + words[-1]


# --- запись ---------------------------------------------------------------------------------

_UPSERT = """
INSERT INTO tgid_poi (category, name, address, shape, source, source_key, attrs, updated_at, updated_by)
SELECT x.category, x.name, x.address, ST_SetSRID(ST_MakePoint(x.lon, x.lat), 4326), $1, x.source_key, x.attrs, now(), $2
  FROM unnest($3::text[], $4::text[], $5::text[], $6::float8[], $7::float8[], $8::text[], $9::jsonb[])
       AS x(category, name, address, lon, lat, source_key, attrs)
ON CONFLICT (source, source_key) DO UPDATE
   SET category = EXCLUDED.category, name = EXCLUDED.name, address = EXCLUDED.address, shape = EXCLUDED.shape,
       attrs = EXCLUDED.attrs, updated_at = now(), updated_by = EXCLUDED.updated_by
"""


async def _upsert(conn, source: str, rows: list[dict[str, Any]], user: str) -> None:
    if not rows:
        return
    await conn.execute(
        _UPSERT, source, user,
        [r["category"] for r in rows], [r["name"] for r in rows], [r.get("address") for r in rows],
        [r["lon"] for r in rows], [r["lat"] for r in rows], [r["source_key"] for r in rows],
        [json.dumps(r.get("attrs"), ensure_ascii=False) if r.get("attrs") is not None else None for r in rows])


async def _replace(conn, source: str, rows: list[dict[str, Any]], user: str,
                   categories: Optional[list[str]] = None) -> dict[str, int]:
    """Записать набор источника: новые и изменённые — обновить, пропавшие — удалить (скрытые остаются скрытыми)."""
    async with conn.transaction():
        await _upsert(conn, source, rows, user)
        keys = [r["source_key"] for r in rows]
        if categories is None:
            removed = await conn.fetchval(
                "WITH d AS (DELETE FROM tgid_poi WHERE source = $1 AND NOT (source_key = ANY($2::text[])) RETURNING 1)"
                " SELECT count(*) FROM d", source, keys)
        else:
            removed = await conn.fetchval(
                "WITH d AS (DELETE FROM tgid_poi WHERE source = $1 AND category = ANY($3::text[])"
                " AND NOT (source_key = ANY($2::text[])) RETURNING 1) SELECT count(*) FROM d", source, keys, categories)
    by_cat = Counter(r["category"] for r in rows)
    return {"saved": len(rows), "removed": int(removed or 0), **{f"n_{c}": by_cat.get(c, 0) for c in CATEGORIES}}


# --- из потребителей сети -------------------------------------------------------------------

_CONSUMERS_SQL = """
SELECT 'real' AS type, rc.id, rc.name, rc.nodeid,
       ST_X(ST_Transform(n.shape, 4326)) AS lon, ST_Y(ST_Transform(n.shape, 4326)) AS lat
  FROM realconsumers rc JOIN nodes n ON n.id = rc.nodeid
 WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL AND COALESCE(btrim(rc.name), '') <> ''
UNION ALL
SELECT 'generalized', gc.id, gc.name, gc.nodeid,
       ST_X(ST_Transform(n.shape, 4326)), ST_Y(ST_Transform(n.shape, 4326))
  FROM generalizedconsumers gc JOIN nodes n ON n.id = gc.nodeid
 WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL AND COALESCE(btrim(gc.name), '') <> ''
"""


def _name_key(name: str) -> str:
    """«Школа,5», «школа.5», «Школа 5» — одно название."""
    return re.sub(r"[\W_]+", "", name.lower())


def _meters(a: dict[str, Any], b: dict[str, Any]) -> float:
    dx = (float(a["lon"]) - float(b["lon"])) * 111_320.0 * math.cos(math.radians(float(a["lat"])))
    dy = (float(a["lat"]) - float(b["lat"])) * 111_320.0
    return math.hypot(dx, dy)


def group_consumers(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Потребители с социальными названиями → объекты. Вместе — корпуса и вводы одного здания: потребители одного
    узла и одной категории, а также с тем же названием в пределах MERGE_RADIUS_M (здание на нескольких узлах,
    фрагменты-копии)."""
    by_node: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for r in records:
        cat = classify(r["name"])
        if cat and r["lon"] is not None and r["lat"] is not None:
            by_node[(r["nodeid"], cat)].append(r)
    clusters: list[dict[str, Any]] = []
    for (node, cat), items in sorted(by_node.items()):
        names = Counter(" ".join(str(i["name"]).split()) for i in items)
        name = names.most_common(1)[0][0]
        here = {"category": cat, "name": name, "key": _name_key(name), "lon": items[0]["lon"], "lat": items[0]["lat"],
                "nodes": [node], "items": list(items)}
        twin = next((c for c in clusters if c["category"] == cat and c["key"] == here["key"]
                     and _meters(c, here) <= MERGE_RADIUS_M), None)
        if twin:
            twin["nodes"].append(node)
            twin["items"] += items
        else:
            clusters.append(here)
    out = []
    for c in clusters:
        items = c["items"]
        out.append({
            "category": c["category"], "name": c["name"], "address": None,
            "lon": float(c["lon"]), "lat": float(c["lat"]), "source_key": f"node:{c['nodes'][0]}:{c['category']}",
            "attrs": {"node_ids": c["nodes"], "consumers_count": len(items),
                      "consumers": [{"type": i["type"], "id": i["id"], "name": " ".join(str(i["name"]).split())}
                                    for i in items[:CONSUMERS_KEPT]]},
        })
    return out


async def refresh_from_consumers(conn, user: str) -> dict[str, Any]:
    rows = group_consumers([dict(r) for r in await conn.fetch(_CONSUMERS_SQL)])
    return await _replace(conn, "consumers", rows, user)


# --- из файла -------------------------------------------------------------------------------

class ImportIn(BaseModel):
    """Объекты из файла акимата: GeoJSON (CSV веб переводит в GeoJSON). Категория — из поля category
    (код или название), иначе — category по умолчанию."""
    features: list[dict[str, Any]] = Field(..., min_length=1, max_length=MAX_IMPORT)
    category: Optional[str] = None
    name_field: Optional[str] = Field(None, max_length=60)


_NAME_KEYS = ("name", "Name", "NAME", "название", "Название", "naimenovanie", "наименование", "Наименование")
_ADDRESS_KEYS = ("address", "Address", "адрес", "Адрес", "addr")
_CATEGORY_BY_WORD = {**{v.lower(): k for k, v in CATEGORIES.items()}, **{v: k for k, v in CATEGORY_ONE.items()},
                     **{k: k for k in CATEGORIES}}


def _point_of(geometry: Any) -> Optional[tuple[float, float]]:
    """Точка объекта: точка как есть, у мультиточки и контура — среднее вершин внешнего кольца."""
    if not isinstance(geometry, dict):
        return None
    t, c = geometry.get("type"), geometry.get("coordinates")
    try:
        if t == "Point":
            return float(c[0]), float(c[1])
        if t == "MultiPoint":
            pts = c
        elif t == "Polygon":
            pts = c[0]
        elif t == "MultiPolygon":
            pts = c[0][0]
        else:
            return None
        if len(pts) > 1 and list(pts[0]) == list(pts[-1]):
            pts = pts[:-1]  # кольцо замкнуто повтором первой вершины
        if not pts:
            return None
        return sum(float(p[0]) for p in pts) / len(pts), sum(float(p[1]) for p in pts) / len(pts)
    except (TypeError, ValueError, IndexError):
        return None


def _first(props: dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = props.get(k)
        if v not in (None, ""):
            return " ".join(str(v).split())
    return ""


def parse_features(body: ImportIn) -> tuple[list[dict[str, Any]], list[str]]:
    """Строки для записи и замечания (пропущенные объекты по причинам)."""
    default = body.category
    if default is not None and default not in CATEGORIES:
        raise PoiError(422, f"Неизвестная категория: {default}")
    rows, skipped = [], Counter()
    for i, f in enumerate(body.features):
        props = f.get("properties") or {}
        point = _point_of(f.get("geometry"))
        if point is None or not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
            skipped["нет точки или неверные координаты"] += 1
            continue
        raw_cat = str(props.get("category") or props.get("категория") or "").strip().lower()
        cat = _CATEGORY_BY_WORD.get(raw_cat) or default
        if cat is None:
            skipped["нет категории"] += 1
            continue
        name = " ".join(str(props.get(body.name_field) or "").split()) if body.name_field else _first(props, _NAME_KEYS)
        key = str(props.get("id") or f.get("id") or i)
        rows.append({"category": cat, "name": name[:300], "address": _first(props, _ADDRESS_KEYS)[:300] or None,
                     "lon": point[0], "lat": point[1], "source_key": f"{cat}:{key}"[:120], "attrs": None})
    seen: dict[str, dict[str, Any]] = {}
    for r in rows:
        seen[r["source_key"]] = r  # повтор ключа в файле — последняя строка
    notes = [f"{reason}: {n}" for reason, n in skipped.items()]
    return list(seen.values()), notes


def outside_extent(rows: list[dict[str, Any]], extent: list[float]) -> int:
    x1, y1, x2, y2 = extent
    m = OUTSIDE_MARGIN_DEG
    return sum(1 for r in rows if not (x1 - m <= r["lon"] <= x2 + m and y1 - m <= r["lat"] <= y2 + m))


async def import_file(conn, body: ImportIn, user: str, extent: list[float]) -> dict[str, Any]:
    rows, notes = parse_features(body)
    if not rows:
        raise PoiError(422, "В файле нет объектов с точкой и категорией" + (f" ({'; '.join(notes)})" if notes else ""))
    far = outside_extent(rows, extent)
    if far == len(rows):
        raise PoiError(422, "Все объекты далеко от сети города — проверьте систему координат и порядок «долгота, широта»")
    result = await _replace(conn, "file", rows, user, categories=sorted({r["category"] for r in rows}))
    return {**result, "notes": notes, "outside": far}


# --- из OpenStreetMap -----------------------------------------------------------------------

def overpass_query(extent: list[float]) -> str:
    x1, y1, x2, y2 = extent
    amenity = "|".join(OSM_AMENITY)
    return (f'[out:json][timeout:{OVERPASS_TIMEOUT_S - 10}];'
            f'nwr["amenity"~"^({amenity})$"]({y1:.5f},{x1:.5f},{y2:.5f},{x2:.5f});'
            'out center tags;')


def parse_overpass(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for el in data.get("elements") or []:
        tags = el.get("tags") or {}
        cat = OSM_AMENITY.get(tags.get("amenity", ""))
        lon = el.get("lon", (el.get("center") or {}).get("lon"))
        lat = el.get("lat", (el.get("center") or {}).get("lat"))
        if not cat or lon is None or lat is None:
            continue
        name = tags.get("name:ru") or tags.get("name") or tags.get("name:kk") or ""
        street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
        rows.append({"category": cat, "name": name[:300], "address": street[:300] or None, "lon": float(lon),
                     "lat": float(lat), "source_key": f"{el.get('type')}/{el.get('id')}",
                     "attrs": {"osm": f"{el.get('type')}/{el.get('id')}"}})
    return rows


def overpass_url() -> str:
    return (os.getenv("OVERPASS_URL") or DEFAULT_OVERPASS_URL).strip()


async def fetch_overpass(extent: list[float]) -> dict[str, Any]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=OVERPASS_TIMEOUT_S) as client:
            res = await client.post(overpass_url(), data={"data": overpass_query(extent)},
                                    headers={"User-Agent": "TGID/1.0 (heat network GIS)"})
    except httpx.HTTPError as exc:
        raise PoiError(502, f"OpenStreetMap (Overpass) недоступен: {exc.__class__.__name__}") from exc
    if res.status_code != 200:
        raise PoiError(502, f"OpenStreetMap (Overpass) ответил {res.status_code} — попробуйте позже")
    try:
        return res.json()
    except ValueError as exc:
        raise PoiError(502, "OpenStreetMap (Overpass) вернул не JSON") from exc


async def import_osm(conn, user: str, extent: list[float]) -> dict[str, Any]:
    rows = parse_overpass(await fetch_overpass(extent))
    return {**await _replace(conn, "osm", rows, user), "notes": [], "outside": 0}


# --- чтение ---------------------------------------------------------------------------------

async def summary(conn) -> dict[str, Any]:
    rows = await conn.fetch("SELECT category, source, count(*) FILTER (WHERE NOT hidden) AS n,"
                            " count(*) FILTER (WHERE hidden) AS hidden FROM tgid_poi GROUP BY 1, 2")
    cats = {c: {"id": c, "title": t, "count": 0, "hidden": 0, "by_source": {}} for c, t in CATEGORIES.items()}
    for r in rows:
        if r["category"] in cats:
            c = cats[r["category"]]
            c["count"] += r["n"]
            c["hidden"] += r["hidden"]
            c["by_source"][r["source"]] = r["n"]
    return {"categories": list(cats.values()), "sources": SOURCES, "overpass": overpass_url()}


def _poi_row(r) -> dict[str, Any]:
    attrs = r["attrs"]
    if isinstance(attrs, str):
        attrs = json.loads(attrs)
    return {"id": r["id"], "category": r["category"], "category_label": CATEGORY_ONE.get(r["category"], r["category"]),
            "name": r["name"], "address": r["address"], "source": r["source"], "hidden": r["hidden"],
            "lon": r["lon"], "lat": r["lat"], "consumers_count": (attrs or {}).get("consumers_count")}


async def list_poi(conn, *, categories: list[str], q: Optional[str] = None, source: Optional[str] = None,
                   hidden: bool = False, limit: int = MAX_LIST) -> list[dict[str, Any]]:
    args: list[Any] = [categories, hidden]
    where = ["category = ANY($1::text[])", "hidden = $2"]
    if source:
        args.append(source)
        where.append(f"source = ${len(args)}")
    if q and q.strip():
        args.append(q.strip())
        where.append(f"(name ILIKE '%' || ${len(args)} || '%' OR address ILIKE '%' || ${len(args)} || '%')")
    args.append(min(max(limit, 1), MAX_LIST))
    rows = await conn.fetch(
        f"SELECT id, category, name, address, source, hidden, attrs, ST_X(shape) AS lon, ST_Y(shape) AS lat"
        f"  FROM tgid_poi WHERE {' AND '.join(where)} ORDER BY category, name, id LIMIT ${len(args)}", *args)
    return [_poi_row(r) for r in rows]


async def geojson(conn, *, categories: list[str], bbox: Optional[tuple[float, float, float, float]] = None) -> dict[str, Any]:
    args: list[Any] = [categories]
    where = "category = ANY($1::text[]) AND NOT hidden"
    if bbox:
        args += list(bbox)
        where += " AND shape && ST_MakeEnvelope($2, $3, $4, $5, 4326)"
    rows = await conn.fetch(
        f"SELECT id, category, name, address, source, hidden, attrs, ST_X(shape) AS lon, ST_Y(shape) AS lat"
        f"  FROM tgid_poi WHERE {where} ORDER BY id LIMIT {MAX_IMPORT}", *args)
    features = []
    for r in rows:
        p = _poi_row(r)
        features.append({"type": "Feature", "id": p["id"], "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                         "properties": {k: p[k] for k in ("id", "category", "category_label", "name", "address", "source")}})
    return {"type": "FeatureCollection", "features": features}


class PoiPatch(BaseModel):
    hidden: Optional[bool] = None
    category: Optional[str] = None
    name: Optional[str] = Field(None, max_length=300)


async def update_poi(conn, poi_id: int, body: PoiPatch, user: str) -> dict[str, Any]:
    if body.category is not None and body.category not in CATEGORIES:
        raise PoiError(422, f"Неизвестная категория: {body.category}")
    row = await conn.fetchrow(
        """UPDATE tgid_poi SET hidden = COALESCE($2, hidden), category = COALESCE($3, category),
                  name = COALESCE($4, name), updated_at = now(), updated_by = $5
            WHERE id = $1
        RETURNING id, category, name, address, source, hidden, attrs, ST_X(shape) AS lon, ST_Y(shape) AS lat""",
        poi_id, body.hidden, body.category, " ".join(body.name.split()) if body.name is not None else None, user)
    if row is None:
        raise PoiError(404, f"Объект {poi_id} не найден")
    return _poi_row(row)


async def delete_source(conn, source: str) -> int:
    if source not in SOURCES:
        raise PoiError(422, f"Неизвестный источник: {source}")
    return int(await conn.fetchval(
        "WITH d AS (DELETE FROM tgid_poi WHERE source = $1 RETURNING 1) SELECT count(*) FROM d", source) or 0)


async def in_area(conn, area: Optional[dict[str, Any]]) -> list[dict[str, Any]]:
    """Социальные объекты в зоне (GeoJSON WGS 84) — для отключений. Таблицы ещё нет — пусто."""
    if not area or await conn.fetchval("SELECT to_regclass('public.tgid_poi')") is None:
        return []
    rows = await conn.fetch(
        """SELECT id, category, name, address, source, hidden, attrs, ST_X(shape) AS lon, ST_Y(shape) AS lat
             FROM tgid_poi
            WHERE NOT hidden AND ST_Intersects(shape, ST_SetSRID(ST_GeomFromGeoJSON($1), 4326))
            ORDER BY array_position(ARRAY['hospital','clinic','kindergarten','school','social']::text[], category), name
            LIMIT 500""", json.dumps(area))
    return [_poi_row(r) for r in rows]


def near_poi_sql(table: str, id_col: str, categories_param: str, meters_param: str, srid: int) -> str:
    """Условие «в N м от социальных объектов» для выборки: зона вокруг каждого объекта — круг N м (география),
    переведённый в систему координат сети; объекты сети — по индексу shape и пересечению с зоной. Зоны —
    MATERIALIZED: иначе планировщик встраивает их построение в фильтр и строит буфер для каждого кандидата."""
    return (
        f"{id_col} IN (WITH z AS MATERIALIZED (SELECT ST_Transform(ST_Buffer(p.shape::geography, {meters_param}::float8)"
        f"::geometry, {srid}) AS zone FROM tgid_poi p WHERE NOT p.hidden AND p.category = ANY({categories_param}::text[]))"
        f" SELECT t.id FROM z JOIN {table} t ON t.shape && z.zone AND ST_Intersects(t.shape, z.zone))"
    )
