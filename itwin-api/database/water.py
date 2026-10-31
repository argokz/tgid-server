"""Водопровод (фаза 4): модели EPANET в базе города, сеть на карте и расчёты отдельного движка (water_engine).

Движок — отдельная служба (WATER_ENGINE_URL, по умолчанию http://127.0.0.1:8070, секрет WATER_ENGINE_TOKEN): разбор
.inp и гидравлический расчёт EPANET 2.2 через WNTR. ТГИД хранит модель (текст .inp — из него и считает движок),
узлы и участки на карте и результаты расчётов.

Привязка к карте:
- srid — координаты модели в заданной системе координат (настоящая сеть водоканала): перевод в 4326 PostGIS;
- schematic — учебная сеть в условных координатах: размещается у центра города (центр источников тепла или
  WATER_ORIGIN_LON / WATER_ORIGIN_LAT) с размером по числу узлов — схема, а не реальные трассы.
"""
from __future__ import annotations

import json
import math
import os
from typing import Any, Optional

import httpx

ENGINE_TIMEOUT_S = 120
SCHEMATIC_M_PER_SQRT_NODE = 150.0          # Net3 (97 узлов) — ~1,5 км, Net6 (3356) — ~8,7 км
SCHEMATIC_EXTENT_M = (1000.0, 15000.0)
LOW_PRESSURE_M = 10.0


class WaterError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def engine_url() -> str:
    return (os.getenv("WATER_ENGINE_URL") or "http://127.0.0.1:8070").rstrip("/")


async def engine_call(method: str, path: str, body: Optional[dict[str, Any]] = None,
                      client: Optional[httpx.AsyncClient] = None) -> Any:
    """Запрос к движку; недоступен — WaterError 503, ошибка модели — с текстом движка."""
    token = os.getenv("WATER_ENGINE_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    own = client is None
    http = client or httpx.AsyncClient(timeout=ENGINE_TIMEOUT_S, trust_env=False)
    try:
        resp = await http.request(method, engine_url() + path, json=body, headers=headers)
    except httpx.HTTPError as exc:
        raise WaterError(503, f"Расчётный движок водопровода недоступен ({engine_url()}): {type(exc).__name__}") from exc
    finally:
        if own:
            await http.aclose()
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except ValueError:
            detail = resp.text[:300]
        raise WaterError(resp.status_code if resp.status_code < 500 else 502, f"Движок водопровода: {detail}")
    return resp.json()


# --- привязка к карте ---------------------------------------------------------------------------

def schematic_placement(nodes: list[dict[str, Any]], origin: tuple[float, float]) -> dict[str, Any]:
    """Масштаб и центр условной схемы: размер — по числу узлов, центр схемы — в origin (широта, долгота)."""
    xs = [n["x"] for n in nodes if n.get("x") is not None]
    ys = [n["y"] for n in nodes if n.get("y") is not None]
    if not xs:
        raise WaterError(422, "В модели нет координат узлов — схему не разместить на карте")
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    lo, hi = SCHEMATIC_EXTENT_M
    extent = min(hi, max(lo, SCHEMATIC_M_PER_SQRT_NODE * math.sqrt(len(nodes))))
    return {"mode": "schematic", "origin_lat": origin[0], "origin_lon": origin[1], "scale_m": extent / span,
            "center_x": (max(xs) + min(xs)) / 2, "center_y": (max(ys) + min(ys)) / 2, "extent_m": round(extent)}


def to_lonlat(x: float, y: float, p: dict[str, Any]) -> tuple[float, float]:
    """Условные координаты схемы → долгота / широта (равнопромежуточно у центра: для схемы до 15 км достаточно)."""
    dx = (x - p["center_x"]) * p["scale_m"]
    dy = (y - p["center_y"]) * p["scale_m"]
    lat = p["origin_lat"] + dy / 110_540
    lon = p["origin_lon"] + dx / (111_320 * math.cos(math.radians(p["origin_lat"])))
    return round(lon, 7), round(lat, 7)


async def _origin(conn) -> tuple[float, float]:
    lat, lon = os.getenv("WATER_ORIGIN_LAT"), os.getenv("WATER_ORIGIN_LON")
    if lat and lon:
        return float(lat), float(lon)
    from database import weather

    coords = await weather.coordinates(conn)
    if coords is None:
        raise WaterError(422, "Нет центра города для схемы: задайте WATER_ORIGIN_LAT и WATER_ORIGIN_LON")
    return coords


# --- модели --------------------------------------------------------------------------------------

async def import_model(conn, *, name: Optional[str], user: str, library: Optional[str] = None,
                       inp: Optional[str] = None, srid: Optional[int] = None) -> dict[str, Any]:
    """Разобрать модель движком и записать сеть на карту: своя СК (srid) или условная схема у центра города."""
    parsed = await engine_call("POST", "/parse", {"library": library} if library else {"inp": inp})
    text = parsed.pop("inp", None) or inp
    nodes, links = parsed["nodes"], parsed["links"]
    if srid:
        placement: dict[str, Any] = {"mode": "srid", "srid": srid}
    else:
        placement = schematic_placement(nodes, await _origin(conn))
    source = f"library:{library}" if library else "file"
    async with conn.transaction():
        model_id = await conn.fetchval(
            """INSERT INTO tgid_water_model (name, source, inp, units_in_file, placement, summary, created_by)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7) RETURNING id""",
            (name or library or "Модель водопровода")[:200], source, text, parsed.get("units_in_file"),
            json.dumps(placement), json.dumps({**parsed["summary"], "duration_h": parsed.get("duration_h"),
                                               "report_step_h": parsed.get("report_step_h"),
                                               "headloss_formula": parsed.get("headloss_formula")}), user)
        coords = {n["id"]: (n["x"], n["y"]) for n in nodes}
        node_rows, link_rows = [], []
        for n in nodes:
            attrs = {k: v for k, v in n.items() if k not in ("id", "type", "x", "y", "elevation")}
            node_rows.append((model_id, n["id"], n["type"], n.get("elevation"), json.dumps(attrs), n["x"], n["y"]))
        for link in links:
            pts = [coords.get(link["start"]), *[tuple(v) for v in link.get("vertices") or []], coords.get(link["end"])]
            if any(p is None or p[0] is None for p in pts):
                continue
            attrs = {k: v for k, v in link.items() if k not in ("id", "type", "start", "end", "vertices", "length_m",
                                                                    "diameter_mm")}
            link_rows.append((model_id, link["id"], link["type"], link["start"], link["end"], link.get("length_m"),
                              link.get("diameter_mm"), json.dumps(attrs), json.dumps(pts)))
        if placement["mode"] == "schematic":
            node_rows = [(*r[:5], *to_lonlat(r[5], r[6], placement)) for r in node_rows]
            link_rows = [(*r[:8], json.dumps([to_lonlat(x, y, placement) for x, y in json.loads(r[8])]))
                         for r in link_rows]
            point_sql, srid_arg = "ST_SetSRID(ST_MakePoint($6, $7), 4326)", 4326
        else:
            point_sql, srid_arg = "ST_Transform(ST_SetSRID(ST_MakePoint($6, $7), $8), 4326)", srid
        if placement["mode"] == "schematic":
            await conn.executemany(
                f"""INSERT INTO tgid_water_node (model_id, node_id, type, elevation, attrs, geom)
                    VALUES ($1, $2, $3, $4, $5::jsonb, {point_sql})""", node_rows)
        else:
            await conn.executemany(
                f"""INSERT INTO tgid_water_node (model_id, node_id, type, elevation, attrs, geom)
                    VALUES ($1, $2, $3, $4, $5::jsonb, {point_sql})""", [(*r, srid_arg) for r in node_rows])
        line_sql = ("ST_SetSRID(ST_MakeLine(ARRAY(SELECT ST_MakePoint((p->>0)::float, (p->>1)::float) "
                    "FROM jsonb_array_elements($9::jsonb) p)), {srid})")
        geom = line_sql.format(srid=4326) if placement["mode"] == "schematic" else \
            f"ST_Transform({line_sql.format(srid=int(srid))}, 4326)"
        await conn.executemany(
            f"""INSERT INTO tgid_water_link (model_id, link_id, type, start_node, end_node, length_m, diameter_mm,
                                            attrs, geom)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, {geom})""", link_rows)
    return {"id": model_id, "nodes": len(node_rows), "links": len(link_rows), "placement": placement,
            "summary": parsed["summary"]}


async def list_models(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """SELECT m.id, m.name, m.source, m.units_in_file, m.placement, m.summary, m.created_by, m.created_at,
                  (SELECT count(*) FROM tgid_water_run r WHERE r.model_id = m.id) AS runs
             FROM tgid_water_model m ORDER BY m.id DESC""")
    return [{**dict(r), "placement": json.loads(r["placement"]), "created_at": r["created_at"].isoformat(),
             "summary": {k: v for k, v in json.loads(r["summary"]).items() if k != "pdd_baseline"}} for r in rows]


async def delete_model(conn, model_id: int) -> bool:
    return (await conn.execute("DELETE FROM tgid_water_model WHERE id = $1", model_id)) != "DELETE 0"


# --- расчёты -------------------------------------------------------------------------------------

async def run(conn, model_id: int, *, user: str, duration_h: Optional[float] = None,
              report_step_h: Optional[float] = None,
              leaks: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    """Расчёт модели движком; результаты по шагам — в tgid_water_run. leaks — сценарий утечек [{node, area_cm2}]:
    расход утечек по шагам — в summary.leaks (баланс по зонам сравнивает его с базовым расчётом)."""
    inp = await conn.fetchval("SELECT inp FROM tgid_water_model WHERE id = $1", model_id)
    if inp is None:
        raise WaterError(404, "Модель водопровода не найдена")
    body: dict[str, Any] = {"inp": inp}
    if duration_h is not None:
        body["duration_h"] = duration_h
    if report_step_h is not None:
        body["report_step_h"] = report_step_h
    if leaks:
        body["leaks"] = leaks
    res = await engine_call("POST", "/simulate", body)
    summary = res["summary"]
    run_id = await conn.fetchval(
        """INSERT INTO tgid_water_run (model_id, duration_h, report_step_h, summary, results, created_by)
           VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6) RETURNING id""",
        model_id, duration_h, report_step_h, json.dumps(summary),
        json.dumps({"times_s": res["times_s"], "node": res["node"], "link": res["link"]}), user)
    return {"id": run_id, "model_id": model_id, "times_s": res["times_s"], "summary": summary}


async def list_runs(conn, model_id: int) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """SELECT id, duration_h, report_step_h, summary, created_by, created_at,
                  jsonb_array_length(results->'times_s') AS steps
             FROM tgid_water_run WHERE model_id = $1 ORDER BY id DESC LIMIT 50""", model_id)
    return [{**dict(r), "summary": json.loads(r["summary"]), "created_at": r["created_at"].isoformat()} for r in rows]


def node_status(pressure: Optional[float]) -> str:
    if pressure is None:
        return "no_data"
    if pressure < 0:
        return "negative"
    return "low" if pressure < LOW_PRESSURE_M else "ok"


async def step_values(conn, model_id: int, run_id: int, step: int) -> dict[str, Any]:
    """Значения шага расчёта без геометрии (для перемотки по времени): давление узлов, расход и скорость участков."""
    row = await conn.fetchrow(
        """SELECT results->'times_s' AS times,
                  (SELECT jsonb_object_agg(k, v->($3::int)) FROM jsonb_each(results->'node'->'pressure_m') e(k, v)) AS p,
                  (SELECT jsonb_object_agg(k, v->($3::int)) FROM jsonb_each(results->'link'->'flow_ls') e(k, v)) AS q,
                  (SELECT jsonb_object_agg(k, v->($3::int)) FROM jsonb_each(results->'link'->'velocity_ms') e(k, v)) AS w
             FROM tgid_water_run WHERE id = $1 AND model_id = $2""", run_id, model_id, step)
    if row is None:
        raise WaterError(404, "Расчёт не найден")
    times = json.loads(row["times"])
    if not 0 <= step < len(times):
        raise WaterError(422, f"Шаг — от 0 до {len(times) - 1}")
    return {"step": step, "time_s": times[step], "times_s": times, "pressure_m": json.loads(row["p"] or "{}"),
            "flow_ls": json.loads(row["q"] or "{}"), "velocity_ms": json.loads(row["w"] or "{}")}


async def geojson(conn, model_id: int, *, run_id: Optional[int] = None, step: int = 0) -> dict[str, Any]:
    """Сеть модели для карты; с расчётом — значения на шаге step: давление узлов, расход и скорость участков."""
    values: dict[str, Any] = {}
    times: list[int] = []
    if run_id is not None:
        v = await step_values(conn, model_id, run_id, step)
        times = v["times_s"]
        values = {"p": v["pressure_m"], "q": v["flow_ls"], "w": v["velocity_ms"]}
    features = []
    for r in await conn.fetch(
            """SELECT link_id, type, diameter_mm, length_m, ST_AsGeoJSON(geom, 7) AS g
                 FROM tgid_water_link WHERE model_id = $1 AND geom IS NOT NULL""", model_id):
        props: dict[str, Any] = {"kind": "link", "id": r["link_id"], "type": r["type"], "diameter_mm": r["diameter_mm"],
                                 "length_m": r["length_m"]}
        if values:
            props.update(flow_ls=values["q"].get(r["link_id"]), velocity_ms=values["w"].get(r["link_id"]))
        features.append({"type": "Feature", "geometry": json.loads(r["g"]), "properties": props})
    for r in await conn.fetch(
            """SELECT node_id, type, elevation, ST_AsGeoJSON(geom, 7) AS g
                 FROM tgid_water_node WHERE model_id = $1 AND geom IS NOT NULL""", model_id):
        props = {"kind": "node", "id": r["node_id"], "type": r["type"], "elevation": r["elevation"]}
        if values:
            p = values["p"].get(r["node_id"])
            props.update(pressure_m=p, status=node_status(p) if r["type"] == "Junction" else "source")
        features.append({"type": "Feature", "geometry": json.loads(r["g"]), "properties": props})
    return {"type": "FeatureCollection", "features": features, "times_s": times, "step": step}
