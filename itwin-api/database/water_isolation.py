"""Отключение участка водопровода задвижками (фаза 4, шаг 3).

Задвижка (tgid_water_valve) стоит на трубе у её конца — узла. Отключаемый участок (сегмент) трубы — всё, до чего
от неё можно дойти, не проходя через задвижку: трубы и узлы. Закрыть нужно задвижки на его границе; насосы и
арматура EPANET (PRV, TCV…) на границе тоже закрываются — через них сегмент не идёт. Последствия:

- без воды — узлы сегмента и узлы, отрезанные от всех источников (резервуаров и баков) закрытием сегмента;
- расчёт (по желанию) — EPANET с закрытыми участками и отбором по давлению (PDD): недоподача в остальной сети
  из-за падения давления, сохраняется как расчёт модели (перемотка по часам, карта давления).

Расстановка «N−1» (Walski) для моделей без задвижек — учебных сетей: у узла с N трубами задвижки на N−1 из них
(без задвижки остаётся самая крупная труба — магистраль), у резервуаров и баков — на всех трубах.
"""
from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any

from database.water import WaterError, engine_call
from database.water_zones import DEMAND_SQL

VALVE_OFFSET_M = 5.0          # задвижка на трубе в 5 м от узла (на карте)
DEVICE_TYPES = ("Pump", "Valve")
SOURCE_TYPES = ("Reservoir", "Tank")
ISOLATION_DURATION_H = 24
PDD_DROP_SHARE = 0.05         # подача упала больше чем на 5 % нужного против работы без отключения — следствие
PDD_DROP_MIN_LS = 0.01


# --- расстановка задвижек ------------------------------------------------------------------------

def strategic_valves(nodes: list[dict[str, Any]], links: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Задвижки «N−1»: (труба, узел). У узла-потребителя с N ≥ 2 трубами — на всех, кроме самой крупной
    (при равных — с меньшим именем); у тупика — нет; у резервуара и бака — на всех трубах."""
    node_type = {n["id"]: n["type"] for n in nodes}
    pipes_at: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for link in links:
        if link["type"] == "Pipe":
            for end in (link["start"], link["end"]):
                if end in node_type:
                    pipes_at[end].append(link)
    out = []
    for node, pipes in sorted(pipes_at.items()):
        if node_type[node] in SOURCE_TYPES:
            chosen = pipes
        elif len(pipes) < 2:
            continue
        else:
            main = min(pipes, key=lambda p: (-(p.get("diameter_mm") or 0), p["id"]))
            chosen = [p for p in pipes if p is not main]
        out.extend((p["id"], node) for p in chosen)
    return sorted(set(out))


# --- сегмент и отрезанные узлы -------------------------------------------------------------------

def _closed(link: dict[str, Any]) -> bool:
    return str(link.get("status") or "").lower() == "closed"


def segment(broken: str, nodes: list[dict[str, Any]], links: list[dict[str, Any]],
            valves: set[tuple[str, str]]) -> dict[str, Any]:
    """Сегмент трубы broken между задвижками: трубы, узлы, задвижки и устройства (насосы, арматура) на границе."""
    by_id = {link["id"]: link for link in links}
    link = by_id.get(broken)
    if link is None:
        raise WaterError(404, f"Нет участка «{broken}» в модели")
    if link["type"] in DEVICE_TYPES:
        raise WaterError(422, f"«{broken}» — {'насос' if link['type'] == 'Pump' else 'арматура'}: отключается сам")
    if _closed(link):
        raise WaterError(422, f"Труба «{broken}» и так закрыта")
    at_node: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in links:
        at_node[item["start"]].append(item)
        at_node[item["end"]].append(item)
    seg_links, seg_nodes = {broken}, set()
    close_valves, devices = set(), set()
    queue = deque([broken])
    while queue:
        cur = by_id[queue.popleft()]
        for node in (cur["start"], cur["end"]):
            if (cur["id"], node) in valves:
                close_valves.add((cur["id"], node))
                continue
            if node in seg_nodes:
                continue
            seg_nodes.add(node)
            for nxt in at_node[node]:
                if nxt["id"] in seg_links:
                    continue
                if nxt["type"] in DEVICE_TYPES:
                    devices.add(nxt["id"])
                elif _closed(nxt):
                    continue
                elif (nxt["id"], node) in valves:
                    close_valves.add((nxt["id"], node))
                else:
                    seg_links.add(nxt["id"])
                    queue.append(nxt["id"])
    node_type = {n["id"]: n["type"] for n in nodes}
    return {"links": sorted(seg_links), "nodes": sorted(seg_nodes),
            "close_valves": sorted(close_valves), "devices": sorted(devices),
            "sources_inside": sorted(n for n in seg_nodes if node_type.get(n) in SOURCE_TYPES)}


def cut_off(nodes: list[dict[str, Any]], links: list[dict[str, Any]], closed: set[str]) -> set[str]:
    """Узлы, не связанные ни с одним источником (резервуаром, баком) после закрытия участков closed."""
    adj: dict[str, list[str]] = defaultdict(list)
    for link in links:
        if link["id"] in closed or (link["type"] == "Pipe" and _closed(link)):
            continue
        adj[link["start"]].append(link["end"])
        adj[link["end"]].append(link["start"])
    seen = {n["id"] for n in nodes if n["type"] in SOURCE_TYPES}
    queue = deque(seen)
    while queue:
        for nxt in adj[queue.popleft()]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return {n["id"] for n in nodes if n["id"] not in seen}


def analyse(broken: str, nodes: list[dict[str, Any]], links: list[dict[str, Any]],
            valves: dict[tuple[str, str], int]) -> dict[str, Any]:
    """Отключение трубы: что закрыть, какие узлы без воды и какой отбор теряется (базовый отбор узлов, л/с)."""
    seg = segment(broken, nodes, links, set(valves))
    # закрытая задвижка перекрывает свою трубу целиком — она тоже закрыта (и для связности, и для расчёта)
    closing = set(seg["links"]) | set(seg["devices"]) | {link for link, _ in seg["close_valves"]}
    junction = {n["id"]: n for n in nodes if n["type"] == "Junction"}
    in_segment = [n for n in seg["nodes"] if n in junction]
    lost = sorted(n for n in cut_off(nodes, links, closing) if n in junction and n not in set(seg["nodes"]))
    length = sum(link.get("length_m") or 0 for link in links if link["id"] in set(seg["links"]))
    demand = sum(junction[n].get("demand_ls") or 0 for n in [*in_segment, *lost])
    return {
        "link": broken,
        "segment": {"links": seg["links"], "nodes": seg["nodes"], "length_m": round(length, 1)},
        "close_valves": [{"id": valves[v], "link": v[0], "node": v[1]} for v in seg["close_valves"]],
        "close_devices": seg["devices"],
        "sources_inside": seg["sources_inside"],
        "no_water": {"segment_nodes": in_segment, "cut_off_nodes": lost, "demand_ls": round(demand, 3)},
        "closed_links": sorted(closing),
    }


# --- база ----------------------------------------------------------------------------------------

async def _graph(conn, model_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if await conn.fetchval("SELECT 1 FROM tgid_water_model WHERE id = $1", model_id) is None:
        raise WaterError(404, "Модель водопровода не найдена")
    nodes = [{"id": r["node_id"], "type": r["type"], "demand_ls": r["demand"]} for r in await conn.fetch(
        f"""SELECT node_id, type, {DEMAND_SQL} AS demand FROM tgid_water_node WHERE model_id = $1""", model_id)]
    links = [{"id": r["link_id"], "type": r["type"], "start": r["start_node"], "end": r["end_node"],
              "status": r["status"], "diameter_mm": r["diameter_mm"], "length_m": r["length_m"]}
             for r in await conn.fetch(
                 """SELECT link_id, type, start_node, end_node, attrs->>'status' AS status, diameter_mm, length_m
                      FROM tgid_water_link WHERE model_id = $1""", model_id)]
    return nodes, links


async def _valves(conn, model_id: int) -> dict[tuple[str, str], int]:
    return {(r["link_id"], r["node_id"]): r["id"] for r in await conn.fetch(
        "SELECT id, link_id, node_id FROM tgid_water_valve WHERE model_id = $1", model_id)}


async def list_valves(conn, model_id: int) -> dict[str, Any]:
    """Задвижки модели точками для карты (на трубе у узла)."""
    rows = await conn.fetch(
        """SELECT id, link_id, node_id, source, ST_AsGeoJSON(geom, 7) AS g
             FROM tgid_water_valve WHERE model_id = $1 ORDER BY id""", model_id)
    by_source: dict[str, int] = defaultdict(int)
    features = []
    for r in rows:
        by_source[r["source"]] += 1
        if r["g"]:
            features.append({"type": "Feature", "geometry": json.loads(r["g"]),
                             "properties": {"kind": "valve", "id": r["id"], "link": r["link_id"], "node": r["node_id"],
                                            "source": r["source"]}})
    return {"count": len(rows), "by_source": dict(by_source), "type": "FeatureCollection", "features": features}


async def generate_valves(conn, model_id: int, user: str) -> dict[str, Any]:
    """Расставить задвижки «N−1»: прежние расставленные так же заменяются, поставленные вручную — остаются."""
    nodes, links = await _graph(conn, model_id)
    pairs = strategic_valves(nodes, links)
    async with conn.transaction():
        await conn.execute("DELETE FROM tgid_water_valve WHERE model_id = $1 AND source = 'strategic'", model_id)
        await insert_valves(conn, model_id, pairs, "strategic", user)
    return await list_valves(conn, model_id)


async def insert_valves(conn, model_id: int, pairs: list[tuple[str, str]], source: str, user: str) -> None:
    """Задвижки (труба, узел) — точкой на трубе в VALVE_OFFSET_M от узла; уже стоящие не дублируются."""
    await conn.executemany(
        """INSERT INTO tgid_water_valve (model_id, link_id, node_id, source, created_by, geom)
           SELECT $1::int, l.link_id, $3::varchar, $6::varchar, $4::varchar,
                  ST_LineInterpolatePoint(l.geom, CASE WHEN l.start_node = $3::varchar THEN f ELSE 1 - f END)
             FROM tgid_water_link l,
                  LATERAL (SELECT least(0.5, $5::float / greatest(ST_Length(l.geom::geography), 0.01)) AS f) x
            WHERE l.model_id = $1::int AND l.link_id = $2::varchar AND l.geom IS NOT NULL
           ON CONFLICT (model_id, link_id, node_id) DO NOTHING""",
        [(model_id, link, node, user, VALVE_OFFSET_M, source) for link, node in pairs])


async def isolation(conn, model_id: int, link_id: str) -> dict[str, Any]:
    """Отключение трубы без расчёта: задвижки, устройства, узлы без воды и их отбор."""
    nodes, links = await _graph(conn, model_id)
    valves = await _valves(conn, model_id)
    if not valves:
        raise WaterError(422, "В модели нет задвижек: расставьте «N−1» или загрузите из ГИС")
    return {**analyse(link_id, nodes, links, valves), "valves_total": len(valves)}


def worse_than_base(short: list[dict[str, Any]], base: dict[str, float], skip: set[str]) -> list[dict[str, Any]]:
    """Недоподача из-за отключения: узлы, которым подано заметно меньше, чем без отключения (base — подача узлов,
    недополучающих воду и в обычном режиме). Узлы без воды (сегмент и отрезанные) — skip."""
    out = []
    for item in short:
        if item["node"] in skip:
            continue
        was = base.get(item["node"])
        drop = max(PDD_DROP_MIN_LS, PDD_DROP_SHARE * (item["expected_ls"] or 0))
        if was is None or (item["delivered_ls"] or 0) < was - drop:
            out.append({**item, "base_delivered_ls": was})
    return out


async def _pdd_baseline(conn, model_id: int, inp: str) -> dict[str, float]:
    """Подача узлов с недоподачей при отборе по давлению без отключений — один раз на модель (модель после загрузки
    не меняется), хранится в summary модели."""
    cached = await conn.fetchval("SELECT summary->'pdd_baseline' FROM tgid_water_model WHERE id = $1", model_id)
    if cached is not None:
        return json.loads(cached)
    res = await engine_call("POST", "/simulate", {"inp": inp, "duration_h": ISOLATION_DURATION_H, "report_step_h": 1,
                                                  "demand_model": "PDD"})
    base = {s["node"]: s["delivered_ls"] or 0 for s in (res["summary"].get("supply") or {}).get("short", [])}
    await conn.execute(
        "UPDATE tgid_water_model SET summary = summary || jsonb_build_object('pdd_baseline', $2::jsonb) WHERE id = $1",
        model_id, json.dumps(base))
    return base


async def isolation_run(conn, model_id: int, link_id: str, *, user: str) -> dict[str, Any]:
    """Отключение с расчётом: EPANET с закрытым сегментом и отбором по давлению (PDD) на сутки — расчёт модели.
    Недоподача за пределами сегмента и отрезанных узлов — следствие падения давления в остальной сети."""
    result = await isolation(conn, model_id, link_id)
    inp = await conn.fetchval("SELECT inp FROM tgid_water_model WHERE id = $1", model_id)
    base = await _pdd_baseline(conn, model_id, inp)
    try:
        res = await engine_call("POST", "/simulate", {
            "inp": inp, "duration_h": ISOLATION_DURATION_H, "report_step_h": 1,
            "closed_links": result["closed_links"], "demand_model": "PDD"})
    except WaterError as exc:
        if exc.status != 422:
            raise
        # расчёт не сошёлся (EPANET остановлен) — это тоже ответ: без участка сеть не работает
        return {**result, "run_id": None, "simulation_error": exc.message}
    no_water = set(result["no_water"]["segment_nodes"]) | set(result["no_water"]["cut_off_nodes"])
    supply = res["summary"].get("supply") or {}
    pressure_short = worse_than_base(supply.get("short", []), base, no_water)
    result["supply"] = {
        "expected_ls": supply.get("expected_ls"), "delivered_ls": supply.get("delivered_ls"),
        "short_nodes": supply.get("short_nodes", 0), "pressure_short_nodes": len(pressure_short),
        "pressure_short": pressure_short[:50],
    }
    summary = {**res["summary"], "isolation": {
        "link": link_id, "close_valves": len(result["close_valves"]), "close_devices": result["close_devices"],
        "segment_links": len(result["segment"]["links"]), "no_water_nodes": len(no_water),
        "demand_ls": result["no_water"]["demand_ls"], "pressure_short_nodes": len(pressure_short)}}
    run_id = await conn.fetchval(
        """INSERT INTO tgid_water_run (model_id, duration_h, report_step_h, summary, results, created_by)
           VALUES ($1, $2, 1, $3::jsonb, $4::jsonb, $5) RETURNING id""",
        model_id, ISOLATION_DURATION_H, json.dumps(summary),
        json.dumps({"times_s": res["times_s"], "node": res["node"], "link": res["link"]}), user)
    return {**result, "run_id": run_id, "simulation_error": None}
