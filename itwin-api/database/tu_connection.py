"""ТУ: подбор точки подключения нового потребителя и оценка нагрузки по аналогам (этап 4 ИИ-плана).

Детерминированное ядро (без LLM): узлы сети рядом с объектом, по каждому — участок с наибольшим
диаметром, режим из последнего расчёта фрагмента (us_out: напоры подачи/обратки, температуры;
ut_out: a8 диаметр, a10 скорость, a13 расход, a14 удельные потери — database/ut_out_columns.py),
источник (us_out.ist → heatsources), прогноз скорости после подключения и оценка по порогам
sql/admissibility/10.sql (1,5–3,5 м/с). Узлы, продублированные в нескольких фрагментах
(варианты магистралей), схлопываются по имени и координатам — остаётся вариант со свежим расчётом.
"""

from __future__ import annotations

from statistics import median
from typing import Any, Optional

from database.net_srid import net_srid

# Пороги скорости в участках (sql/admissibility/10.sql)
V_MIN = 1.5
V_MAX = 3.5
# Минимальный располагаемый напор на вводе потребителя для зависимой схемы, м
MIN_AVAILABLE_HEAD = 15.0
# Если температур в узле нет: расчётный перепад на вводе, °C (консервативно)
DEFAULT_DT = 60.0
DEFAULT_RADIUS_M = 300
MAX_RADIUS_M = 2000


def extra_flow_t_h(load_gcal_h: Optional[float], dt: Optional[float]) -> float:
    """Прирост расхода сетевой воды, т/ч: G = Q·1000/Δt (Q в Гкал/ч, c = 1 ккал/(кг·°C))."""
    if not load_gcal_h or load_gcal_h <= 0:
        return 0.0
    delta = dt if dt and dt >= 10 else DEFAULT_DT
    return load_gcal_h * 1000.0 / delta


def velocity_after(v_now: Optional[float], g_now: Optional[float], g_extra: float) -> Optional[float]:
    """Скорость в участке после прироста расхода (линейно по расходу)."""
    if v_now is None or g_now is None or abs(g_now) < 1e-6:
        return None
    # расход в ut_out со знаком направления — берём модуль
    return abs(v_now) * (abs(g_now) + g_extra) / abs(g_now)


_SQL = """
WITH pt AS (
    SELECT ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), $5::int) AS g
),
near AS (
    SELECT n.id, n.externalnodename AS name, n.fileid, n.nodetypeid,
           ST_Distance(n.shape, pt.g) AS dist,
           ST_X(ST_Transform(n.shape, 4326)) AS lon, ST_Y(ST_Transform(n.shape, 4326)) AS lat,
           round(ST_X(n.shape)::numeric, 0) AS rx, round(ST_Y(n.shape)::numeric, 0) AS ry
      FROM nodes n, pt
     WHERE n.removed = 0 AND n.internalnodeid IS NULL AND n.shape IS NOT NULL
       AND ST_DWithin(n.shape, pt.g, $3)
),
calc AS (
    SELECT fileid, MAX(id) AS cid FROM calculation
     WHERE fileid IN (SELECT DISTINCT fileid FROM near)
       AND ($6::int IS NULL OR id = $6)
     GROUP BY fileid
),
line AS (
    -- участок с наибольшим диаметром у узла (подающая линия, если есть)
    SELECT DISTINCT ON (q.node_id) q.*
      FROM (
        SELECT nr.id AS node_id, l.id AS line_id, l.externalsignlineid AS sign,
               h.diametercondit AS diameter, h.pipesectlength AS length, h.firstpicdatehp AS laid_at,
               tt.name AS tubing
          FROM near nr
          JOIN linesobj l ON (l.nodeid1 = nr.id OR l.nodeid2 = nr.id) AND l.removed = 0
          JOIN heatpipesections h ON h.lineid = l.id
          LEFT JOIN tubingtypes tt ON tt.id = h.tubingtypeid
      ) q
     ORDER BY q.node_id, (q.sign IN (1, 2, 4)) DESC, q.diameter DESC NULLS LAST
)
SELECT nr.id AS node_id, nr.name, nr.fileid, nr.nodetypeid, nr.dist, nr.lon, nr.lat, nr.rx, nr.ry,
       f.name AS fragment_name, c.cid AS calculation_id,
       ln.line_id, ln.diameter, ln.length, ln.laid_at, ln.tubing,
       us1.pih AS head_supply, us2.pih AS head_return, us1.t AS t_supply, us2.t AS t_return,
       COALESCE(hs.sourcename, hs.name) AS source_name, hs.id AS source_id,
       ut.a8 AS calc_diameter, ut.a10 AS velocity, ut.a13 AS flow, ut.a14 AS dp_per_m, ut.a19 AS piezo_head
  FROM near nr
  LEFT JOIN fragments f ON f.id = nr.fileid
  LEFT JOIN calc c ON c.fileid = nr.fileid
  LEFT JOIN line ln ON ln.node_id = nr.id
  LEFT JOIN us_out us1 ON us1.calculationid = c.cid AND us1.nodeid = nr.id AND us1.externalsign = 1
  LEFT JOIN us_out us2 ON us2.calculationid = c.cid AND us2.nodeid = nr.id AND us2.externalsign = 2
  LEFT JOIN heatsources hs ON hs.id = COALESCE(us1.ist, us2.ist)
  LEFT JOIN ut_out ut ON ut.calculationid = c.cid AND ut.lineid = ln.line_id
 ORDER BY nr.dist, (c.cid IS NULL), c.cid DESC
 LIMIT $4
"""


def _f(v: Any) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def assess(row: dict[str, Any], load_gcal_h: Optional[float]) -> dict[str, Any]:
    """Оценка одной точки: располагаемый напор, скорость после подключения, причины, балл."""
    head_s, head_r = _f(row.get("head_supply")), _f(row.get("head_return"))
    available = round(head_s - head_r, 2) if head_s is not None and head_r is not None else None
    t_s, t_r = _f(row.get("t_supply")), _f(row.get("t_return"))
    dt = (t_s - t_r) if t_s is not None and t_r is not None else None
    g_extra = extra_flow_t_h(load_gcal_h, dt)
    v_now, g_now = _f(row.get("velocity")), _f(row.get("flow"))
    v_new = velocity_after(v_now, g_now, g_extra)
    diameter = _f(row.get("diameter")) or _f(row.get("calc_diameter"))

    reasons: list[str] = []
    score = 100.0
    dist = _f(row.get("dist")) or 0.0
    score -= min(dist, 1000) / 20  # −1 балл за каждые 20 м
    if row.get("calculation_id") is None:
        reasons.append("по фрагменту нет расчёта — режим неизвестен")
        score -= 30
    if available is not None:
        if available < MIN_AVAILABLE_HEAD:
            reasons.append(f"располагаемый напор {available} м меньше {MIN_AVAILABLE_HEAD:.0f} м")
            score -= 25
        else:
            reasons.append(f"располагаемый напор {available} м")
    if v_new is not None:
        if v_new > V_MAX:
            reasons.append(f"скорость после подключения {v_new:.2f} м/с выше {V_MAX} м/с")
            score -= 30
        elif v_now is not None and v_now > V_MAX:
            reasons.append(f"участок уже перегружен: {v_now:.2f} м/с")
            score -= 20
        else:
            reasons.append(f"скорость {v_now:.2f} → {v_new:.2f} м/с")
    elif v_now is not None:
        reasons.append(f"скорость в участке {v_now:.2f} м/с")
    if diameter is not None:
        if diameter < 100:
            reasons.append(f"диаметр {diameter:.0f} мм — малый")
            score -= 10
        else:
            reasons.append(f"диаметр {diameter:.0f} мм")
    if row.get("source_name"):
        reasons.append(f"источник: {row['source_name']}")
    return {
        "node_id": row.get("node_id"),
        "name": row.get("name") or "",
        "fragment_id": row.get("fileid"),
        "fragment_name": row.get("fragment_name"),
        "calculation_id": row.get("calculation_id"),
        "distance_m": round(dist, 1),
        "longitude": _f(row.get("lon")),
        "latitude": _f(row.get("lat")),
        "line_id": row.get("line_id"),
        "diameter_mm": diameter,
        "laid_at": row["laid_at"].isoformat() if row.get("laid_at") else None,
        "tubing": row.get("tubing"),
        "head_supply": head_s,
        "head_return": head_r,
        "available_head": available,
        "t_supply": t_s,
        "t_return": t_r,
        "velocity": v_now,
        "velocity_after": round(v_new, 3) if v_new is not None else None,
        "flow_t_h": g_now,
        "extra_flow_t_h": round(g_extra, 2),
        "dp_per_m": _f(row.get("dp_per_m")),
        "source_id": row.get("source_id"),
        "source_name": row.get("source_name"),
        "score": round(score, 1),
        "reasons": reasons,
    }


def dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Один и тот же узел в нескольких фрагментах: оставить вариант с расчётом (самым свежим)."""
    best: dict[tuple, dict[str, Any]] = {}
    for r in rows:
        key = ((r.get("name") or "").strip().lower(), r.get("rx"), r.get("ry"))
        cur = best.get(key)
        if cur is None or (r.get("calculation_id") or -1) > (cur.get("calculation_id") or -1):
            best[key] = r
    return sorted(best.values(), key=lambda r: (_f(r.get("dist")) or 0.0))


async def connection_candidates(
    conn,
    *,
    lon: float,
    lat: float,
    load_gcal_h: Optional[float] = None,
    radius_m: int = DEFAULT_RADIUS_M,
    limit: int = 8,
    calculation_id: Optional[int] = None,
) -> dict[str, Any]:
    radius = max(20, min(int(radius_m), MAX_RADIUS_M))
    rows = [dict(r) for r in await conn.fetch(_SQL, lon, lat, radius, max(limit * 6, 30), net_srid(), calculation_id)]
    items = [assess(r, load_gcal_h) for r in dedupe(rows)]
    items.sort(key=lambda i: (-i["score"], i["distance_m"]))
    items = items[:limit]
    return {
        "point": {"longitude": lon, "latitude": lat},
        "radius_m": radius,
        "load_gcal_h": load_gcal_h,
        "items": items,
        "thresholds": {"v_min": V_MIN, "v_max": V_MAX, "min_available_head": MIN_AVAILABLE_HEAD},
        "note": None if items else "В радиусе поиска нет узлов сети — увеличьте радиус или уточните точку",
    }


_ANALOG_SQL = """
SELECT nagr, shape_area, floor::int AS floor
  FROM zdaniya_2
 WHERE nagr > 0 AND shape_area > 0 AND floor ~ '^[0-9]+$'
   AND floor::int BETWEEN $1 AND $2
"""


async def estimate_load(conn, *, floors: Optional[int] = None, area_m2: Optional[float] = None) -> dict[str, Any]:
    """Нагрузка по аналогам АЛСЕКО (zdaniya_2): медиана по зданиям той же этажности (±1),
    при известной площади застройки — медиана удельной нагрузки на 1000 м² × площадь."""
    if not floors or floors < 1:
        return {"load_gcal_h": None, "analogs": 0, "basis": "не задана этажность"}
    # слой АЛСЕКО есть не в каждой базе города (в Астане его нет) — без проверки запрос падал с 500
    if not await conn.fetchval("SELECT to_regclass('zdaniya_2') IS NOT NULL"):
        return {"load_gcal_h": None, "analogs": 0, "basis": "в базе города нет слоя зданий с нагрузками (zdaniya_2)"}
    lo, hi = max(1, floors - 1), floors + 1
    rows = await conn.fetch(_ANALOG_SQL, lo, hi)
    if not rows:
        return {"load_gcal_h": None, "analogs": 0, "basis": f"нет зданий {lo}–{hi} этажей в АЛСЕКО"}
    loads = [float(r["nagr"]) for r in rows]
    if area_m2 and area_m2 > 0:
        per_1000 = median(float(r["nagr"]) / float(r["shape_area"]) * 1000.0 for r in rows)
        return {
            "load_gcal_h": round(per_1000 * area_m2 / 1000.0, 4),
            "analogs": len(rows),
            "basis": f"медиана {per_1000:.3f} Гкал/ч на 1000 м² по {len(rows)} зданиям {lo}–{hi} этажей × {area_m2:.0f} м²",
            "per_1000m2": round(per_1000, 4),
        }
    med = median(loads)
    return {
        "load_gcal_h": round(med, 4),
        "analogs": len(rows),
        "basis": f"медиана нагрузки {len(rows)} зданий {lo}–{hi} этажей",
    }
