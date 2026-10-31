"""Теплосеть в 3D (фаза 5): участки видимой области с глубиной заложения — для подземного вида Cesium.

Глубина — tgid_heat_depth (database/heat_depth.py): до верха трубы у начала и у конца геометрии участка, из отметок
узлов или оценкой по соседним узлам. У участка без глубины — null: веб рисует его на поверхности отдельным цветом,
глубина не придумывается (поле паспорта pipelinelayingdepth в базах — значение по умолчанию). Подача и обратка на одной
геометрии — одна труба с pipes = 2. Сценарии и фрагменты-копии не отдаются, если фрагменты не заданы явно.

Трубы в масштабе — по наружному диаметру (heatpipesections.diameterexternal, мм; нет — Ду). Камеры — узлы с карточкой
heatchambers или видом «Тепловая камера»: внутренние длина, ширина, высота и направление самого крупного участка узла.
Размеры камер в базах внесены в разных единицах при подписи «мм» в десктопе (Астана: 1,8 и 2400 — оба про 2 м),
поэтому единица берётся по величине (chamber_size_m); размер меньше 0,5 м не принимается — камера без размеров.
"""
from __future__ import annotations

import time
from typing import Any, Optional

from database.net_srid import line_inner_sql, net_srid

MAX_LINES = 20_000
MAX_CHAMBERS = 5_000
CHAMBER_NODE_TYPE = 9            # nodetypes: «Тепловая камера»
CHAMBER_MIN_M = 0.5              # меньше — не размер камеры (опечатка или единица не та)
CHAMBER_MAX_M = 15.0
MAX_BBOX_DEG = 0.5            # больше — запрос на весь город: вид надо приблизить
COORD_DIGITS = 6              # ~0,1 м
MODEL_CACHE_S = 600           # фрагменты модели (без копий) считаются секунды — держать 10 минут на базу
_model_cache: dict[str, tuple[float, list[int]]] = {}


class Network3dError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def check_bbox(bbox: tuple[float, float, float, float]) -> None:
    x1, y1, x2, y2 = bbox
    if not (-180 <= x1 < x2 <= 180 and -90 <= y1 < y2 <= 90):
        raise Network3dError(422, "bbox: границы вне WGS84 или перепутаны")
    if x2 - x1 > MAX_BBOX_DEG or y2 - y1 > MAX_BBOX_DEG:
        raise Network3dError(422, "Слишком большая область — приблизьте вид (до 0,5° по стороне)")


def merge_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Подача и обратка на общей геометрии (пара П/О десктопа) — одна труба: наибольший Ду, глубины первой с ними,
    pipes — сколько участков в ней."""
    by_geom: dict[str, dict[str, Any]] = {}
    for r in rows:
        key = r["coords"]
        cur = by_geom.get(key)
        if cur is None:
            by_geom[key] = {**r, "pipes": 1}
            continue
        cur["pipes"] += 1
        cur["dn"] = max(cur["dn"] or 0, r["dn"] or 0) or None
        cur["de"] = max(cur.get("de") or 0, r.get("de") or 0) or None
        if cur["d0"] is None and r["d0"] is not None:
            cur["d0"], cur["d1"] = r["d0"], r["d1"]
    return list(by_geom.values())


async def lines(conn, bbox: tuple[float, float, float, float], fileids: Optional[list[int]] = None) -> dict[str, Any]:
    from database import em_chapter, heat_depth

    check_bbox(bbox)
    await heat_depth.ensure(conn)
    if not fileids:
        fileids = await _model_fileids(conn, em_chapter)
    rows = await conn.fetch(
        f"""SELECT l.id, l.fileid, h.diametercondit AS dn, h.diameterexternal AS de,
                   d.depth_start AS d0, d.depth_end AS d1,
                   ST_AsText(ST_SnapToGrid(ST_Transform(ST_LineMerge(l.shape), 4326), {10 ** -COORD_DIGITS})) AS wkt
              FROM linesobj l
              LEFT JOIN LATERAL (SELECT diametercondit, diameterexternal FROM heatpipesections
                                  WHERE lineid = l.id ORDER BY id LIMIT 1) h
                     ON true
              LEFT JOIN tgid_heat_depth d ON d.lineid = l.id
             WHERE coalesce(l.removed, 0) = 0 AND {line_inner_sql('l')} IS NULL AND l.shape IS NOT NULL
               AND l.fileid = ANY($5::int[])
               AND l.shape && ST_Transform(ST_MakeEnvelope($1, $2, $3, $4, 4326), {net_srid()})
             LIMIT {MAX_LINES + 1}""",
        *bbox, fileids)
    truncated = len(rows) > MAX_LINES
    parsed = []
    for r in rows[:MAX_LINES]:
        coords = _coords(r["wkt"])
        if len(coords) < 4:
            continue
        parsed.append({"id": r["id"], "fileid": r["fileid"], "dn": float(r["dn"]) if r["dn"] else None,
                       "de": float(r["de"]) if r["de"] else None,
                       "d0": r["d0"], "d1": r["d1"], "coords": ",".join(map(str, coords))})
    merged = merge_pairs(parsed)
    known = sum(1 for x in merged if x["d0"] is not None)
    chambers = await chamber_rows(conn, bbox, fileids)
    return {
        "bbox": list(bbox), "truncated": truncated, "lines": len(parsed), "pipes": len(merged),
        "with_depth": known,
        # компактно: [id, Ду, глубина у начала, у конца, участков в трубе, [lon, lat, lon, lat, …], Dн мм]
        "items": [[x["id"], x["dn"], _r(x["d0"]), _r(x["d1"]), x["pipes"], [float(v) for v in x["coords"].split(",")],
                   x.get("de")]
                  for x in merged],
        "chambers": chambers,
        "chambers_sized": sum(1 for c in chambers if c[3] is not None),
    }


def chamber_size_m(value: Optional[float]) -> Optional[float]:
    """Размер камеры из карточки → метры: до 15 — метры, до 1000 — сантиметры, дальше — миллиметры (подпись
    десктопа); вне 0,5–15 м — не размер."""
    if value is None or value <= 0:
        return None
    v = float(value)
    metres = v if v <= CHAMBER_MAX_M else v / 100 if v < 1000 else v / 1000
    return round(metres, 2) if CHAMBER_MIN_M <= metres <= CHAMBER_MAX_M else None


async def chamber_rows(conn, bbox: tuple[float, float, float, float], fileids: list[int]) -> list[list[Any]]:
    """Камеры области: [id узла, lon, lat, длина м, ширина м, высота м, азимут °, название]; без размеров — None."""
    rows = await conn.fetch(
        f"""SELECT n.id, ST_X(p) AS lon, ST_Y(p) AS lat, c.name,
                   c.internallength AS l, c.internalwidth AS w, c.internalheight AS h,
                   degrees(ST_Azimuth(n.shape, ln.next_pt)) AS az
              FROM nodes n
              LEFT JOIN LATERAL (SELECT name, internallength, internalwidth, internalheight FROM heatchambers
                                  WHERE nodeid = n.id ORDER BY id LIMIT 1) c ON true
              CROSS JOIN LATERAL ST_Transform(n.shape, 4326) AS p
              LEFT JOIN LATERAL (
                    SELECT CASE WHEN l.nodeid1 = n.id THEN ST_PointN(ST_LineMerge(l.shape), 2)
                                ELSE ST_PointN(ST_LineMerge(l.shape), ST_NPoints(ST_LineMerge(l.shape)) - 1) END AS next_pt
                      FROM linesobj l
                      LEFT JOIN heatpipesections h ON h.lineid = l.id
                     WHERE (l.nodeid1 = n.id OR l.nodeid2 = n.id) AND coalesce(l.removed, 0) = 0
                       AND GeometryType(ST_LineMerge(l.shape)) = 'LINESTRING'
                     ORDER BY h.diametercondit DESC NULLS LAST, l.id LIMIT 1) ln ON true
             WHERE coalesce(n.removed, 0) = 0 AND n.shape IS NOT NULL AND n.internalnodeid IS NULL
               AND n.fileid = ANY($5::int[])
               AND (c.name IS NOT NULL OR n.nodetypeid = {CHAMBER_NODE_TYPE}
                    OR EXISTS (SELECT 1 FROM heatchambers hc WHERE hc.nodeid = n.id))
               AND n.shape && ST_Transform(ST_MakeEnvelope($1, $2, $3, $4, 4326), {net_srid()})
             LIMIT {MAX_CHAMBERS}""",
        *bbox, fileids)
    out = []
    for r in rows:
        size = [chamber_size_m(r[k]) for k in ("l", "w", "h")]
        sized = all(v is not None for v in size)
        out.append([r["id"], round(float(r["lon"]), 7), round(float(r["lat"]), 7),
                    *(size if sized else [None, None, None]),
                    round(float(r["az"]), 1) if r["az"] is not None else None, r["name"]])
    return out


async def _model_fileids(conn, em_chapter) -> list[int]:
    db = await conn.fetchval("SELECT current_database()")
    hit = _model_cache.get(db)
    if hit and time.monotonic() - hit[0] < MODEL_CACHE_S:
        return hit[1]
    ids, _ = await em_chapter._fileids(conn, None)
    _model_cache[db] = (time.monotonic(), ids)
    return ids


def _r(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(float(v), 2)


def _coords(wkt: Optional[str]) -> list[float]:
    """LINESTRING / MULTILINESTRING (после LineMerge — части подряд) → плоский список lon, lat."""
    if not wkt:
        return []
    body = wkt[wkt.index("(") :].replace("(", " ").replace(")", " ")
    out: list[float] = []
    for pair in body.split(","):
        parts = pair.split()
        if len(parts) >= 2:
            out.extend((round(float(parts[0]), COORD_DIGITS), round(float(parts[1]), COORD_DIGITS)))
    return out
