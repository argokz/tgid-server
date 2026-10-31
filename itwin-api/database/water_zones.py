"""Зоны водоучёта (DMA) модели водопровода и баланс подачи по ним (фаза 4, шаг 2).

Зона — связная часть сети между границами: насосами, арматурой (PRV, TCV…), закрытыми трубами и трубами, на
которых стоит расходомер (tgid_water_model.meters — их задаёт пользователь, как вводы DMA). Подача в зону на шаге
расчёта — сумма расходов через границы внутрь зоны и подача из резервуаров и баков внутри неё; потребление — отбор
узлов зоны (с утечками: в EPANET излучатель входит в отбор узла). В расчёте модели подача равна потреблению —
баланс проверяет полноту границ; смысл — в сравнении:

- минимальный ночной расход (МНР) и его доля от среднего: чем выше доля, тем больше в подаче расхода, не зависящего
  от режима водопотребления (утечки);
- расчёт со сценарием утечки против базового: рост МНР в каждой зоне и показания каждого расходомера — видно, в какой
  зоне утечку заметят по расходомерам и заметят ли вообще (рост меньше погрешности учёта — не заметят).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from database.water import WaterError

DETECT_SHARE = 0.05        # рост МНР больше 5 % — заметен по расходомерам (класс точности учёта ~2 %, с запасом)
DETECT_MIN_LS = 0.1
MAX_METERS = 500
BOUNDARY_TYPES = {"Pump": "pump", "Valve": "valve"}
# отбор узла: средний за сутки по графикам (движок с шага 3), у моделей, загруженных раньше, — базовый
DEMAND_SQL = "coalesce((attrs->>'avg_demand_ls')::float, (attrs->>'base_demand_ls')::float)"


# --- зоны ----------------------------------------------------------------------------------------

def boundary_reason(link: dict[str, Any], meters: set[str]) -> Optional[str]:
    """Почему участок — граница зоны: расходомер, насос, арматура, закрытая труба; None — внутри зоны."""
    if link["id"] in meters:
        return "meter"
    if link["type"] in BOUNDARY_TYPES:
        return BOUNDARY_TYPES[link["type"]]
    if str(link.get("status") or "").lower() == "closed":
        return "closed"
    return None


def split_zones(nodes: list[dict[str, Any]], links: list[dict[str, Any]], meters: set[str]) -> dict[str, Any]:
    """Зоны — связные части сети без граничных участков. Номер зоны — по числу узлов-потребителей (1 — крупнейшая).

    nodes: [{id, type, demand_ls}], links: [{id, type, start, end, status}]."""
    parent = {n["id"]: n["id"] for n in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    boundary = []
    for link in links:
        if link["start"] not in parent or link["end"] not in parent:
            continue
        reason = boundary_reason(link, meters)
        if reason:
            boundary.append({"link": link["id"], "type": link["type"], "reason": reason,
                             "start": link["start"], "end": link["end"]})
            continue
        a, b = find(link["start"]), find(link["end"])
        if a != b:
            parent[max(a, b)] = min(a, b)

    groups: dict[str, list[dict[str, Any]]] = {}
    for n in nodes:
        groups.setdefault(find(n["id"]), []).append(n)

    def junctions(members: list[dict[str, Any]]) -> int:
        return sum(1 for n in members if n["type"] == "Junction")

    ordered = sorted(groups.values(), key=lambda g: (-junctions(g), min(n["id"] for n in g)))
    node_zone: dict[str, int] = {}
    zones = []
    for index, members in enumerate(ordered, start=1):
        demand = sum(n.get("demand_ls") or 0 for n in members if n["type"] == "Junction")
        sources = sorted(n["id"] for n in members if n["type"] in ("Reservoir", "Tank"))
        kind = "dma" if demand > 0 else ("source" if sources else "transit")
        zones.append({"index": index, "name": f"Зона {index}", "kind": kind, "nodes": len(members),
                      "junctions": junctions(members), "sources": sources, "demand_ls": round(demand, 3)})
        for n in members:
            node_zone[n["id"]] = index
    for b in boundary:
        b["start_zone"], b["end_zone"] = node_zone[b["start"]], node_zone[b["end"]]
    link_zone = {}
    boundary_ids = {b["link"] for b in boundary}
    for link in links:
        if link["id"] not in boundary_ids and link["start"] in node_zone:
            link_zone[link["id"]] = node_zone[link["start"]]
    for z in zones:
        z["inlets"] = sorted({b["link"] for b in boundary
                              if b["start_zone"] != b["end_zone"] and z["index"] in (b["start_zone"], b["end_zone"])})
    return {"zones": zones, "boundary": boundary, "node_zone": node_zone, "link_zone": link_zone}


# --- баланс --------------------------------------------------------------------------------------

def _series(values: Optional[list[Optional[float]]], steps: int) -> list[float]:
    out = [float(v) if v is not None else 0.0 for v in (values or [])]
    return (out + [0.0] * steps)[:steps]


def zone_balance(split: dict[str, Any], node_types: dict[str, str], times: list[int],
                 demand: dict[str, list], flow: dict[str, list],
                 leaks: Optional[list[dict[str, Any]]] = None) -> list[dict[str, Any]]:
    """Подача, потребление и МНР по зонам. Подача = расход через границы внутрь + отдача резервуаров и баков зоны
    (отбор резервуара и бака в EPANET отрицателен, когда они отдают воду); потребление = отбор узлов (Junction)."""
    steps = len(times)
    node_zone = split["node_zone"]
    zones = {z["index"]: {"supply": [0.0] * steps, "use": [0.0] * steps, "leak": [0.0] * steps}
             for z in split["zones"]}
    for node, zone in node_zone.items():
        series = _series(demand.get(node), steps)
        acc = zones[zone]["use"] if node_types.get(node) == "Junction" else zones[zone]["supply"]
        sign = 1.0 if node_types.get(node) == "Junction" else -1.0
        for i, v in enumerate(series):
            acc[i] += sign * v
    for b in split["boundary"]:
        if b["start_zone"] == b["end_zone"]:
            continue
        series = _series(flow.get(b["link"]), steps)  # плюс — от начала участка к концу
        for i, q in enumerate(series):
            zones[b["end_zone"]]["supply"][i] += q
            zones[b["start_zone"]]["supply"][i] -= q
    for leak in leaks or []:
        zone = node_zone.get(leak["node"])
        if zone is not None:
            for i, q in enumerate(_series(leak.get("flow_ls"), steps)):
                zones[zone]["leak"][i] += q

    out = []
    for z in split["zones"]:
        s = zones[z["index"]]
        supply, use = s["supply"], s["use"]
        avg = sum(supply) / steps if steps else 0.0
        mnf_i = min(range(steps), key=lambda i: supply[i]) if steps else None
        mnf = supply[mnf_i] if mnf_i is not None else None
        item = {
            "index": z["index"], "name": z["name"], "kind": z["kind"],
            "supply_avg_ls": round(avg, 3), "use_avg_ls": round(sum(use) / steps, 3) if steps else None,
            "mnf_ls": round(mnf, 3) if mnf is not None else None,
            "mnf_time_s": times[mnf_i] if mnf_i is not None else None,
            # доля МНР — только у районов водоучёта: у источника подача около нуля, доля теряет смысл
            "mnf_share": round(mnf / avg, 3) if z["kind"] == "dma" and mnf is not None and avg > 0 else None,
            "imbalance_ls": round(max((abs(a - b) for a, b in zip(supply, use)), default=0.0), 3),
            "leak_avg_ls": round(sum(s["leak"]) / steps, 3) if steps and any(s["leak"]) else None,
            "supply_ls": [round(v, 3) for v in supply],
        }
        out.append(item)
    return out


def detect(base: list[dict[str, Any]], scenario: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Сценарий против базового расчёта по каждой зоне: рост средней подачи и МНР; заметна ли утечка по
    расходомерам зоны (рост МНР больше DETECT_SHARE от базового и больше DETECT_MIN_LS)."""
    by_index = {z["index"]: z for z in base}
    out = []
    for z in scenario:
        b = by_index.get(z["index"])
        if b is None or z["mnf_ls"] is None or b["mnf_ls"] is None:
            continue
        d_mnf = z["mnf_ls"] - b["mnf_ls"]
        d_avg = z["supply_avg_ls"] - b["supply_avg_ls"]
        threshold = max(DETECT_MIN_LS, DETECT_SHARE * abs(b["mnf_ls"]))
        out.append({"index": z["index"], "d_supply_avg_ls": round(d_avg, 3), "d_mnf_ls": round(d_mnf, 3),
                    "d_mnf_share": round(d_mnf / b["mnf_ls"], 3) if b["mnf_ls"] > 0 else None,
                    "threshold_ls": round(threshold, 3), "detected": z["kind"] == "dma" and d_mnf > threshold})
    return out


def meter_changes(split: dict[str, Any], base_flow: dict[str, list], flow: dict[str, list],
                  steps: int) -> list[dict[str, Any]]:
    """Показания расходомеров (граница — meter): средний расход и его изменение против базового расчёта."""
    out = []
    for b in split["boundary"]:
        if b["reason"] != "meter":
            continue
        now, was = _series(flow.get(b["link"]), steps), _series(base_flow.get(b["link"]), steps)
        avg_now = sum(now) / steps if steps else 0.0
        avg_was = sum(was) / steps if steps else 0.0
        out.append({"link": b["link"], "from_zone": b["start_zone"], "to_zone": b["end_zone"],
                    "avg_ls": round(avg_now, 3), "d_avg_ls": round(avg_now - avg_was, 3)})
    return out


# --- база ----------------------------------------------------------------------------------------

async def _graph(conn, model_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    meters = await conn.fetchval("SELECT meters FROM tgid_water_model WHERE id = $1", model_id)
    if meters is None:
        raise WaterError(404, "Модель водопровода не найдена")
    nodes = [{"id": r["node_id"], "type": r["type"], "demand_ls": r["demand"]} for r in await conn.fetch(
        f"""SELECT node_id, type, {DEMAND_SQL} AS demand FROM tgid_water_node WHERE model_id = $1""", model_id)]
    links = [{"id": r["link_id"], "type": r["type"], "start": r["start_node"], "end": r["end_node"],
              "status": r["status"]} for r in await conn.fetch(
        """SELECT link_id, type, start_node, end_node, attrs->>'status' AS status
             FROM tgid_water_link WHERE model_id = $1""", model_id)]
    return nodes, links, json.loads(meters)


async def zones(conn, model_id: int) -> dict[str, Any]:
    """Зоны модели с текущими расходомерами: список зон, границы, зона каждого узла и участка (для карты)."""
    nodes, links, meters = await _graph(conn, model_id)
    split = split_zones(nodes, links, set(meters))
    return {"meters": meters, **split}


async def set_meters(conn, model_id: int, links: list[str]) -> dict[str, Any]:
    """Расходомеры модели — трубы-вводы зон; не трубы и чужие участки — ошибка."""
    wanted = sorted(set(links))
    if len(wanted) > MAX_METERS:
        raise WaterError(422, f"Расходомеров — не больше {MAX_METERS}")
    if await conn.fetchval("SELECT 1 FROM tgid_water_model WHERE id = $1", model_id) is None:
        raise WaterError(404, "Модель водопровода не найдена")
    pipes = {r["link_id"] for r in await conn.fetch(
        "SELECT link_id FROM tgid_water_link WHERE model_id = $1 AND type = 'Pipe' AND link_id = ANY($2::text[])",
        model_id, wanted)}
    missing = [x for x in wanted if x not in pipes]
    if missing:
        raise WaterError(422, f"Не трубы модели: {', '.join(missing[:10])}")
    await conn.execute("UPDATE tgid_water_model SET meters = $2::jsonb WHERE id = $1", model_id, json.dumps(wanted))
    return await zones(conn, model_id)


async def _run(conn, model_id: int, run_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        """SELECT id, summary, results->'times_s' AS times, results->'node'->'demand_ls' AS demand,
                  results->'link'->'flow_ls' AS flow
             FROM tgid_water_run WHERE id = $1 AND model_id = $2""", run_id, model_id)
    if row is None:
        return None
    return {"id": row["id"], "summary": json.loads(row["summary"]), "times": json.loads(row["times"] or "[]"),
            "demand": json.loads(row["demand"] or "{}"), "flow": json.loads(row["flow"] or "{}")}


async def _baseline_id(conn, model_id: int, run_id: int, steps: int) -> Optional[int]:
    """Базовый расчёт для сценария утечки: последний расчёт той же модели без утечек и отключений с тем же числом
    шагов."""
    return await conn.fetchval(
        """SELECT id FROM tgid_water_run
            WHERE model_id = $1 AND id <> $2 AND NOT (summary ?| array['leaks', 'isolation'])
              AND jsonb_array_length(results->'times_s') = $3
            ORDER BY id DESC LIMIT 1""", model_id, run_id, steps)


async def balance(conn, model_id: int, run_id: int, baseline_id: Optional[int] = None) -> dict[str, Any]:
    """Баланс по зонам расчёта; расчёт с утечками — ещё и против базового: где утечку заметят расходомеры."""
    nodes, links, meters = await _graph(conn, model_id)
    current = await _run(conn, model_id, run_id)
    if current is None:
        raise WaterError(404, "Расчёт не найден")
    split = split_zones(nodes, links, set(meters))
    types = {n["id"]: n["type"] for n in nodes}
    leaks = current["summary"].get("leaks") or []
    result = zone_balance(split, types, current["times"], current["demand"], current["flow"], leaks)
    info = {z["index"]: z for z in split["zones"]}
    for z in result:
        z.update(nodes=info[z["index"]]["nodes"], junctions=info[z["index"]]["junctions"],
                 sources=info[z["index"]]["sources"], inlets=info[z["index"]]["inlets"])
    out: dict[str, Any] = {"run_id": run_id, "times_s": current["times"], "meters": meters, "zones": result,
                           "leaks": [{**{k: v for k, v in leak.items() if k != "flow_ls"},
                                      "zone": split["node_zone"].get(leak["node"])} for leak in leaks],
                           "baseline_id": None, "detection": [], "meter_changes": []}
    if baseline_id is None and leaks:
        baseline_id = await _baseline_id(conn, model_id, run_id, len(current["times"]))
    if baseline_id is not None:
        base = await _run(conn, model_id, baseline_id)
        if base is None:
            raise WaterError(404, "Базовый расчёт не найден")
        if len(base["times"]) != len(current["times"]):
            raise WaterError(422, "Базовый расчёт — с другим числом шагов: сравнивать нельзя")
        base_zones = zone_balance(split, types, base["times"], base["demand"], base["flow"])
        out.update(baseline_id=baseline_id, detection=detect(base_zones, result),
                   meter_changes=meter_changes(split, base["flow"], current["flow"], len(current["times"])))
    return out
