"""Прогноз тепловой нагрузки источников по погоде (фаза 3, «Цифровой двойник»).

Основа — последний расчёт фрагмента источника (pt_out, нагрузки потребителей при Tн расчёта, Гкал/ч):
- отопление и вентиляция пересчитываются на температуру воздуха по относительной нагрузке Q_отн температурного
  графика источника (deployedtempgraphs: та же таблица, по которой sety берёт температуры от Tн):
  Q(Tн) = Q(Tн расчёта) × Q_отн(Tн) / Q_отн(Tн расчёта); вне графика — крайняя точка (теплее излома графика
  нагрузка отопления держится на изломе: тёплый день в сезон отопление не выключает, начало и конец сезона —
  по календарю). Вентиляция — по тому же отношению (упрощение: у вентиляции своя расчётная температура);
- горячее водоснабжение — среднечасовая нагрузка расчёта (суточного графика ГВС нет): закрытая система и
  циркуляция — постоянны; открытый водоразбор из подачи / обратки — как считает sety, по температуре воды:
  Q × (t − tх) / (t расчёта − tх), t — подачи / обратки по графику;
- температуры подачи и обратки — по тому же графику.
Тепловые потери сети в прогноз не входят: это нагрузка потребителей.

Факт — датчики на выходе источника (телеметрия): расход подачи / обратки на участках у узла источника (выводов
несколько — расходы складываются), температура подачи / обратки в узле: Q = (G1·(t1 − tх) − G2·(t2 − tх)) / 1000, без расхода обратки —
G1·(t1 − t2) / 1000. Прогноз на прошедшие часы по фактической погоде против этого факта — проверка прогноза.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from database import weather
from database.telemetry import UNITS

MAX_PAST_HOURS = 24 * 14
MAX_HOURS = 24 * 16
NEXT_HOURS = 24  # сводка — ближайшие сутки
COLD_WATER_C = 5.0


def graph_at(graph: list[dict[str, float]], tn: float) -> dict[str, float]:
    """Q_отн, t1, t2 графика при Tн: линейно между точками, вне диапазона — крайняя точка (как sety read_tg)."""
    if tn <= graph[0]["tn"]:
        return {k: graph[0][k] for k in ("q_otn", "t1", "t2")}
    for lo, hi in zip(graph, graph[1:]):
        if tn <= hi["tn"]:
            k = (tn - lo["tn"]) / (hi["tn"] - lo["tn"])
            return {key: lo[key] + k * (hi[key] - lo[key]) for key in ("q_otn", "t1", "t2")}
    return {k: graph[-1][k] for k in ("q_otn", "t1", "t2")}


def _water_ratio(t: float, t_calc: float, tx: float) -> float:
    return (t - tx) / (t_calc - tx) if t_calc - tx > 0 else 1.0


def load_at(base: dict[str, Any], graph: list[dict[str, float]], tn: float) -> dict[str, float]:
    """Нагрузка источника, Гкал/ч, и температуры графика при температуре воздуха tn."""
    g = graph_at(graph, tn)
    g_calc = graph_at(graph, base["tn"])
    ratio = g["q_otn"] / g_calc["q_otn"] if g_calc["q_otn"] > 0 else 0.0
    heating, vent = base["heating"] * ratio, base["vent"] * ratio
    tx = base.get("tx", COLD_WATER_C)
    hw = (base.get("hw_closed", base["hw"])
          + base.get("hw_supply", 0.0) * _water_ratio(g["t1"], g_calc["t1"], tx)
          + base.get("hw_return", 0.0) * _water_ratio(g["t2"], g_calc["t2"], tx))
    return {"heating": round(heating, 2), "vent": round(vent, 2), "hw": round(hw, 2),
            "total": round(heating + vent + hw, 2), "t1": round(g["t1"], 1), "t2": round(g["t2"], 1)}


def fact_heat(g1: Optional[float], g2: Optional[float], t1: Optional[float], t2: Optional[float],
              tx: float = COLD_WATER_C) -> Optional[float]:
    """Отпуск тепла источником, Гкал/ч, по расходу (т/ч) и температурам (°C)."""
    if g1 is None or t1 is None:
        return None
    if g2 is not None and t2 is not None:
        return round((g1 * (t1 - tx) - g2 * (t2 - tx)) / 1000, 2)
    if t2 is not None:
        return round(g1 * (t1 - t2) / 1000, 2)
    return None


async def sources(conn, source_id: Optional[int] = None) -> list[dict[str, Any]]:
    """Источники с нагрузками последнего расчёта фрагмента (по pt_out.ist) и температурным графиком."""
    rows = await conn.fetch(
        """WITH src AS (
               SELECT hs.id, coalesce(nullif(hs.name, ''), hs.sourcename) AS name, hs.nodeid, n.fileid,
                      coalesce(hs.tx_r, $2)::float AS tx
                 FROM heatsources hs JOIN nodes n ON n.id = hs.nodeid
                WHERE coalesce(n.removed, 0) = 0 AND n.fileid IS NOT NULL AND ($1::int IS NULL OR hs.id = $1)),
           calc AS (
               SELECT DISTINCT ON (c.fileid) c.fileid, c.id, c.tn::float AS tn, c.date1
                 FROM calculation c
                WHERE c.fileid IN (SELECT fileid FROM src) AND c.tn IS NOT NULL
                  AND EXISTS (SELECT 1 FROM pt_out p WHERE p.calculationid = c.id)
                ORDER BY c.fileid, c.id DESC)
           SELECT src.*, calc.id AS calculation_id, calc.tn, calc.date1, f.name AS fragment, l.*
             FROM src JOIN calc ON calc.fileid = src.fileid
             LEFT JOIN fragments f ON f.id = src.fileid
             JOIN LATERAL (
                 SELECT count(*) AS consumers,
                        sum(coalesce(qotz, 0) + coalesce(qotn, 0))::float AS heating,
                        sum(coalesce(dop12, 0))::float AS vent,
                        sum(coalesce(dop17, 0) + coalesce(dop20, 0))::float AS hw_closed,
                        sum(coalesce(dop18, 0))::float AS hw_supply,
                        sum(coalesce(dop19, 0))::float AS hw_return
                   FROM pt_out p WHERE p.calculationid = calc.id AND p.ist = src.id) l
               ON l.consumers > 0 AND l.heating + l.vent + l.hw_closed + l.hw_supply + l.hw_return > 0
            ORDER BY src.id""", source_id, COLD_WATER_C)
    if not rows:
        return []
    graphs: dict[int, list[dict[str, float]]] = {}
    for g in await conn.fetch(
            """SELECT hsourceid, tn::float AS tn, q_otn::float AS q_otn, t1::float AS t1, t2::float AS t2
                 FROM deployedtempgraphs WHERE hsourceid = ANY($1::int[]) AND tn IS NOT NULL AND q_otn IS NOT NULL
                ORDER BY hsourceid, tn""", [r["id"] for r in rows]):
        graphs.setdefault(g["hsourceid"], []).append(dict(g))
    out = []
    for r in rows:
        graph = graphs.get(r["id"])
        if not graph or len(graph) < 2:
            continue
        out.append({
            "id": r["id"], "name": r["name"], "node_id": r["nodeid"], "fileid": r["fileid"],
            "fragment": r["fragment"], "tx": r["tx"], "consumers": r["consumers"],
            "calculation": {"id": r["calculation_id"], "tn": r["tn"],
                            "at": r["date1"].isoformat() if r["date1"] else None},
            "base": base_loads(r),
            "graph": graph,
        })
    return out


def base_loads(r) -> dict[str, Any]:
    """Нагрузки расчёта-основы по составляющим (Гкал/ч) и tх источника."""
    hw = r["hw_closed"] + r["hw_supply"] + r["hw_return"]
    return {"tn": r["tn"], "tx": r["tx"], "heating": round(r["heating"], 2), "vent": round(r["vent"], 2),
            "hw": round(hw, 2), "hw_closed": round(r["hw_closed"], 2), "hw_supply": round(r["hw_supply"], 2),
            "hw_return": round(r["hw_return"], 2), "total": round(r["heating"] + r["vent"] + hw, 2)}


def summary(src: dict[str, Any], hours: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    """Ближайшие сутки: мин./макс. температура, пик и среднее нагрузки, отпуск за сутки, Tн для расчёта."""
    ahead = [h for h in hours if now <= h["ts"] < now + timedelta(hours=NEXT_HOURS)]
    if not ahead:
        return {"hours": 0}
    loads = [load_at(src["base"], src["graph"], h["t_air"])["total"] for h in ahead]
    t_min = min(h["t_air"] for h in ahead)
    return {"hours": len(ahead), "t_min": round(t_min, 1), "t_max": round(max(h["t_air"] for h in ahead), 1),
            "q_max": round(max(loads), 1), "q_avg": round(sum(loads) / len(loads), 1),
            "q_sum": round(sum(loads), 0), "tn_calc": round(t_min)}


async def overview(conn, *, refresh: bool = True) -> dict[str, Any]:
    """Погода по часам (последние сутки и прогноз) и сводка прогноза по каждому источнику."""
    provider = await weather.refresh(conn) if refresh else {"provider": weather.PROVIDER}
    now = weather.hour_utc(datetime.now(timezone.utc))
    hours = await weather.hourly(conn, now - timedelta(hours=24), now + timedelta(hours=MAX_HOURS))
    items = []
    for src in await sources(conn):
        items.append({k: v for k, v in src.items() if k != "graph"} | {"next": summary(src, hours, now)})
    items.sort(key=lambda s: -s["base"]["total"])
    return {"weather": provider, "now": now.isoformat(),
            "hours": [_hour_json(h) for h in hours], "sources": items}


def _hour_json(h: dict[str, Any]) -> dict[str, Any]:
    return {**h, "ts": h["ts"].isoformat()}


async def _source_sensors(conn, src: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Датчики на выходе источника: расходы подачи / обратки на участках у узла (все выводы), температуры в узле
    (первый датчик по id)."""
    rows = await conn.fetch(
        """SELECT s.id, s.kind, s.pipe, s.unit, s.code FROM tgid_sensor s
            WHERE s.active AND (
                  (s.kind = 'temperature' AND s.node_id = $1)
               OR (s.kind = 'flow' AND s.line_id IN (SELECT id FROM linesobj
                                                      WHERE (nodeid1 = $1 OR nodeid2 = $1)
                                                        AND coalesce(removed, 0) = 0)))
            ORDER BY s.id""", src["node_id"])
    found: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        key = ("g" if r["kind"] == "flow" else "t") + ("1" if r["pipe"] == "supply" else "2")
        if key.startswith("g") or key not in found:
            found.setdefault(key, []).append(dict(r))
    return found


async def _hourly_sensor(conn, sensor: dict[str, Any], start: datetime, end: datetime) -> dict[datetime, float]:
    rows = await conn.fetch(
        """SELECT date_trunc('hour', ts) AS h, avg(value)::float AS v FROM tgid_sensor_reading
            WHERE sensor_id = $1 AND ts >= $2 AND ts < $3 GROUP BY 1""", sensor["id"], start, end)
    k = UNITS[sensor["unit"]].to_base if sensor["unit"] in UNITS else 1.0
    return {weather.hour_utc(r["h"]): r["v"] * k for r in rows}


async def detail(conn, source_id: int, *, past_hours: int = 48, hours: int = 72) -> Optional[dict[str, Any]]:
    """Прогноз источника по часам: погода, нагрузка по составляющим, температуры графика, факт по датчикам."""
    found = await sources(conn, source_id)
    if not found:
        return None
    src = found[0]
    provider = await weather.refresh(conn)
    now = weather.hour_utc(datetime.now(timezone.utc))
    start, end = now - timedelta(hours=past_hours), now + timedelta(hours=hours)
    sensors = await _source_sensors(conn, src)
    series: dict[str, dict[datetime, float]] = {}
    for key, group in sensors.items():
        parts = [await _hourly_sensor(conn, s, start, min(end, now + timedelta(hours=1))) for s in group]
        # час засчитывается, только если есть показания всех датчиков группы (иначе сумма расходов занижена)
        common = set.intersection(*(set(p) for p in parts))
        series[key] = {h: sum(p[h] for p in parts) for h in common}
    points = []
    for h in await weather.hourly(conn, start, end):
        load = load_at(src["base"], src["graph"], h["t_air"])
        fact = fact_heat(*(series.get(k, {}).get(h["ts"]) for k in ("g1", "g2", "t1", "t2")), tx=src["tx"])
        points.append({"ts": h["ts"].isoformat(), "t_air": h["t_air"], "kind": h["kind"], "source": h["source"],
                       **load, "fact": fact})
    checked = [p for p in points if p["fact"] is not None and p["kind"] == "fact" and p["total"] > 0]
    accuracy = None
    if checked:
        errors = [(p["total"] - p["fact"]) / p["fact"] * 100 for p in checked if p["fact"]]
        if errors:
            accuracy = {"hours": len(errors), "mean_pct": round(sum(errors) / len(errors), 1),
                        "mean_abs_pct": round(sum(abs(e) for e in errors) / len(errors), 1)}
    hours_list = [{"ts": datetime.fromisoformat(p["ts"]), "t_air": p["t_air"]} for p in points]
    return {k: v for k, v in src.items() if k != "graph"} | {
        "weather": provider, "now": now.isoformat(),
        "sensors": {k: [s["code"] for s in group] for k, group in sensors.items()},
        "points": points, "accuracy": accuracy, "next": summary(src, hours_list, now)}
