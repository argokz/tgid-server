"""Модуль моделирования аварийных отключений и локализации задвижек (Outage Simulation).

Алгоритм BFS по топологическому графу теплосети (оценка, не аналог десктопа —
в gid8 такой функции нет):
- Граф строится по магистральным участкам (linesobj.internalnodeid IS NULL);
  отключённые трубы (pipesectstateid = 2, как isOtkl в gid8 cxema/read_lines.cpp) не проводят воду.
- Обход останавливается на участке с задвижкой и на узле, во внутренней схеме
  которого (linesobj.internalnodeid = узел) стоят задвижки — камеры, ТРП, насосные.
  Открытые задвижки попадают в «закрыть», уже закрытые — в отдельный список.
- Отключённые потребители (consumerstateid <> 1) не учитываются.
- Потребители ниже по течению за закрытыми задвижками пока не считаются.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any, Optional

import asyncpg

_outage_cached_data = None
_outage_cached_time = 0.0

DAMPER_CLOSED = 2      # damperarmaturestates: 1 открыта, 2 закрыта, 4 частично открыта
PIPE_DISCONNECTED = 2  # pipeSectStateID == 2 → isOtkl


def invalidate_outage_cache():
    global _outage_cached_data, _outage_cached_time
    _outage_cached_data = None
    _outage_cached_time = 0.0


async def get_outage_network_graph(conn: asyncpg.Connection, force_refresh: bool = False):
    global _outage_cached_data, _outage_cached_time
    now = time.time()
    if not force_refresh and _outage_cached_data is not None and (now - _outage_cached_time) < 60.0:
        return _outage_cached_data

    # 1. Магистральные участки (без внутренних схем узлов) и состояние их труб
    q_lines = """
        SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid,
               coalesce(h.pipesectlength, 10.0)::float as length,
               coalesce(h.diametercondit, 100.0)::float as diameter,
               coalesce(h.diameterinternal, h.diametercondit, 100.0)::float as diameter_internal,
               coalesce(h.pipesectstateidflow, 1) as state_flow,
               coalesce(h.pipesectstateidret, 1) as state_ret
        FROM linesobj l
        LEFT JOIN LATERAL (
            SELECT pipesectlength, diametercondit, diameterinternal,
                   pipesectstateidflow, pipesectstateidret
            FROM heatpipesections WHERE lineid = l.id ORDER BY id LIMIT 1
        ) h ON true
        WHERE coalesce(l.removed, 0) = 0
          AND l.internalnodeid IS NULL
          AND l.nodeid1 IS NOT NULL AND l.nodeid2 IS NOT NULL
    """
    lines_rows = await conn.fetch(q_lines)

    # 2. Задвижки: на магистральных участках и во внутренних схемах узлов
    q_dampers = """
        SELECT d.id, d.lineid, l.internalnodeid AS owner_node_id,
               coalesce(nullif(btrim(d.name), ''), 'Задвижка №' || d.id) as display_name,
               coalesce(d.diametercondit, 100.0)::float as nominal_diameter,
               coalesce(d.damperarmaturestateid, 1)::int as state_id,
               coalesce(s.name, CASE WHEN d.damperarmaturestateid = 2 THEN 'Закрыта' ELSE 'Открыта' END) as state_name,
               ST_X(ST_Transform(coalesce(ST_PointOnSurface(l.shape), owner.shape), 4326)) as lng,
               ST_Y(ST_Transform(coalesce(ST_PointOnSurface(l.shape), owner.shape), 4326)) as lat
        FROM dampers d
        JOIN linesobj l ON l.id = d.lineid
        LEFT JOIN nodes owner ON owner.id = l.internalnodeid
        LEFT JOIN damperarmaturestates s ON s.id = d.damperarmaturestateid
        WHERE coalesce(l.removed, 0) = 0
    """
    dampers_rows = await conn.fetch(q_dampers)

    dampers_by_line: dict[int, list[dict[str, Any]]] = {}
    dampers_by_node: dict[int, list[dict[str, Any]]] = {}
    for d in dampers_rows:
        if d["owner_node_id"] is not None:
            dampers_by_node.setdefault(d["owner_node_id"], []).append(dict(d))
        else:
            dampers_by_line.setdefault(d["lineid"], []).append(dict(d))

    line_info: dict[int, dict[str, Any]] = {}
    adj: dict[int, list[tuple[int, int]]] = {}

    for row in lines_rows:
        sign = row["externalsignlineid"]
        flow_off = row["state_flow"] == PIPE_DISCONNECTED
        ret_off = row["state_ret"] == PIPE_DISCONNECTED
        # Двухтрубный участок выключен из сети, только если отключены обе трубы
        if sign == 1:
            disconnected = flow_off and ret_off
        elif sign == 2:
            disconnected = flow_off
        elif sign == 3:
            disconnected = ret_off
        else:
            disconnected = False
        if disconnected:
            continue
        lid = row["id"]
        n1 = row["nodeid1"]
        n2 = row["nodeid2"]
        line_info[lid] = {
            "id": lid,
            "nodeid1": n1,
            "nodeid2": n2,
            "externalsignlineid": sign,
            "length": row["length"],
            "diameter": row["diameter"],
            "diameter_internal": row["diameter_internal"],
        }
        adj.setdefault(n1, []).append((lid, n2))
        adj.setdefault(n2, []).append((lid, n1))

    _outage_cached_data = {
        "line_info": line_info,
        "dampers_by_line": dampers_by_line,
        "dampers_by_node": dampers_by_node,
        "adj": adj,
    }
    _outage_cached_time = now
    return _outage_cached_data


async def simulate_outage_isolation(
    conn: asyncpg.Connection,
    *,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
) -> dict[str, Any]:
    """Выполняет локализацию аварийного участка и сбор всех зависимых объектов."""
    if line_id is None and node_id is None:
        raise ValueError("Необходимо указать line_id или node_id поврежденного элемента сети.")

    net = await get_outage_network_graph(conn)
    line_info = net["line_info"]
    dampers_by_line = net["dampers_by_line"]
    dampers_by_node = net["dampers_by_node"]
    adj = net["adj"]

    queue: list[int] = []
    isolated_lines: set[int] = set()
    isolated_nodes: set[int] = set()
    boundary_nodes: set[int] = set()
    processed_lines: set[int] = set()
    valves_to_close_map: dict[int, dict[str, Any]] = {}
    valves_closed_map: dict[int, dict[str, Any]] = {}

    def take_valves(valves: list[dict[str, Any]]) -> None:
        for v in valves:
            target_map = valves_closed_map if v["state_id"] == DAMPER_CLOSED else valves_to_close_map
            target_map[v["id"]] = v

    def reach_node(nid: int) -> None:
        """Узел с задвижками во внутренней схеме — граница зоны, дальше не идём."""
        if nid in isolated_nodes or nid in boundary_nodes:
            return
        if nid in dampers_by_node:
            boundary_nodes.add(nid)
            take_valves(dampers_by_node[nid])
            return
        isolated_nodes.add(nid)
        queue.append(nid)

    if line_id is not None:
        if line_id not in line_info:
            db_line = await conn.fetchrow(
                "SELECT id, internalnodeid, nodeid1, nodeid2, COALESCE(removed, 0) AS removed "
                "FROM linesobj WHERE id = $1",
                line_id,
            )
            if not db_line:
                raise ValueError(f"Трубопровод с ID {line_id} не найден в базе данных.")
            if db_line["removed"]:
                raise ValueError(f"Трубопровод {line_id} удалён.")
            if db_line["nodeid1"] is None or db_line["nodeid2"] is None:
                raise ValueError(
                    f"Трубопровод {line_id} не привязан к узлам расчётной схемы (нет nodeid1/nodeid2): "
                    "это линия ГИС без топологии, отключение по ней не рассчитывается."
                )
            if db_line["internalnodeid"] is not None:
                raise ValueError(
                    f"Трубопровод {line_id} входит во внутреннюю схему узла {db_line['internalnodeid']}: "
                    "укажите этот узел или магистральный участок."
                )
            raise ValueError(f"Трубопровод {line_id} отключён (обе трубы, pipesectstateid = 2).")

        target = line_info[line_id]
        isolated_lines.add(line_id)
        processed_lines.add(line_id)

        # Если на самой аварийной трубе установлена задвижка, добавляем её
        if line_id in dampers_by_line:
            take_valves(dampers_by_line[line_id])

        for n in (target["nodeid1"], target["nodeid2"]):
            if n:
                reach_node(n)

    elif node_id is not None:
        db_node = await conn.fetchrow("SELECT id FROM nodes WHERE id = $1", node_id)
        if not db_node:
            raise ValueError(f"Узел с ID {node_id} не найден в базе данных.")
        # Авария в самом узле: его внутренние задвижки не помогают, отсекаем снаружи
        isolated_nodes.add(node_id)
        queue.append(node_id)

    # Запуск BFS
    while queue:
        curr_node = queue.pop(0)
        for lid, neighbor in adj.get(curr_node, []):
            if lid in processed_lines:
                continue
            processed_lines.add(lid)

            if lid in dampers_by_line:
                # Участок содержит отсекающую задвижку — закрываем её и не идем дальше
                take_valves(dampers_by_line[lid])
            else:
                # На участке нет задвижки — он попадает в зону отключения
                isolated_lines.add(lid)
                reach_node(neighbor)

    valves_to_close = sorted(valves_to_close_map.values(), key=lambda x: x["id"])
    valves_already_closed = sorted(valves_closed_map.values(), key=lambda x: x["id"])

    # 3. Сбор геометрии и метрик изолированных труб (геометрия — только для зоны)
    total_length_m = 0.0
    total_volume_m3 = 0.0
    pipe_features = []

    geom_rows = await conn.fetch(
        "SELECT id, ST_AsGeoJSON(ST_Transform(shape, 4326)) AS g FROM linesobj "
        "WHERE id = ANY($1::int[]) AND shape IS NOT NULL",
        list(isolated_lines),
    )
    geom_by_line = {r["id"]: r["g"] for r in geom_rows}

    for lid in isolated_lines:
        linfo = line_info.get(lid)
        if not linfo:
            continue
        l_len = linfo["length"]
        d_int = linfo["diameter_internal"]
        mult = 2.0 if linfo["externalsignlineid"] == 1 else 1.0

        total_length_m += l_len * mult
        # V = pi * (d / 2)^2 * L
        pipe_vol = (math.pi / 4.0) * ((d_int / 1000.0) ** 2) * l_len * mult
        total_volume_m3 += pipe_vol

        if geom_by_line.get(lid):
            pipe_features.append({
                "type": "Feature",
                "geometry": json.loads(geom_by_line[lid]),
                "properties": {
                    "id": lid,
                    "length": round(l_len, 2),
                    "diameter": linfo["diameter"],
                    "nodeid1": linfo["nodeid1"],
                    "nodeid2": linfo["nodeid2"],
                },
            })

    # 4. Сбор информации об узлах и потребителях
    affected_consumers = []
    total_q_ot = 0.0
    total_q_gvs = 0.0
    total_q_vent = 0.0

    if isolated_nodes:
        # Узлы с координатами
        q_nodes = """
            SELECT n.id,
                   coalesce(nullif(btrim(n.nodename), ''), nullif(btrim(n.externalnodename), ''), 'Узел ' || n.id) as name,
                   CASE WHEN n.shape IS NULL THEN NULL
                        ELSE ST_X(ST_Transform(n.shape, 4326)) END as lng,
                   CASE WHEN n.shape IS NULL THEN NULL
                        ELSE ST_Y(ST_Transform(n.shape, 4326)) END as lat
            FROM nodes n
            WHERE n.id = ANY($1::int[])
        """
        node_rows = await conn.fetch(q_nodes, list(isolated_nodes))
        node_coords = {r["id"]: (r["lng"], r["lat"], r["name"]) for r in node_rows}

        # Потребители (generalized и real)
        q_consumers = """
            SELECT 'generalized' as ctype, c.id, c.nodeid,
                   coalesce(nullif(btrim(c.name), ''), 'Потребитель №' || c.id) as name,
                   (coalesce(c.calchldep, 0) + coalesce(c.calchlindep, 0)
                    + coalesce(c.calchlparall, 0) + coalesce(c.calchlmix, 0)
                    + coalesce(c.calchlconseq, 0) + coalesce(c.calchlpreon, 0))::double precision AS heating_load,
                   coalesce(c.calchlventil, 0)::double precision AS ventilation_load,
                   (coalesce(c.calchlclosesys, 0) + coalesce(c.calchlopensysflow, 0)
                    + coalesce(c.calchlopensysret, 0) + coalesce(c.calchlgvsparall, 0)
                    + coalesce(c.calchlgvsmix, 0) + coalesce(c.calchlgvsconseq, 0)
                    + coalesce(c.calchlgvspreon, 0))::double precision AS hot_water_load
            FROM generalizedconsumers c
            WHERE c.nodeid = ANY($1::int[]) AND coalesce(c.consumerstateid, 1) = 1
            UNION ALL
            SELECT 'real' as ctype, c.id, c.nodeid,
                   coalesce(nullif(btrim(c.name), ''), 'Потребитель №' || c.id) as name,
                   (coalesce(c.calchldep, 0) + coalesce(c.calchlindep, 0))::double precision,
                   coalesce(c.calchlventil, 0)::double precision,
                   (coalesce(c.avghlclosesys, 0) + coalesce(c.avghlopensysflow, 0)
                    + coalesce(c.avghlopensysret, 0))::double precision
            FROM realconsumers c
            WHERE c.nodeid = ANY($1::int[]) AND coalesce(c.consumerstateid, 1) = 1
        """
        consumers_rows = await conn.fetch(q_consumers, list(isolated_nodes))

        for row in consumers_rows:
            q_ot = float(row["heating_load"] or 0)
            q_v = float(row["ventilation_load"] or 0)
            q_g = float(row["hot_water_load"] or 0)
            q_total = q_ot + q_v + q_g

            total_q_ot += q_ot
            total_q_vent += q_v
            total_q_gvs += q_g

            nid = row["nodeid"]
            coords = node_coords.get(nid, (None, None, ""))

            affected_consumers.append({
                "id": row["id"],
                "consumer_type": row["ctype"],
                "node_id": nid,
                "name": row["name"],
                "heating_load": round(q_ot, 4),
                "ventilation_load": round(q_v, 4),
                "hot_water_load": round(q_g, 4),
                "total_load": round(q_total, 4),
                "longitude": coords[0],
                "latitude": coords[1],
            })

    # 5. GeoJSON для задвижек
    valve_features = []
    for v in valves_to_close:
        if v["lng"] is not None and v["lat"] is not None:
            valve_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [v["lng"], v["lat"]],
                },
                "properties": {
                    "id": v["id"],
                    "line_id": v["lineid"],
                    "name": v["display_name"],
                    "nominal_diameter": v["nominal_diameter"],
                    "state_name": v["state_name"],
                },
            })

    # 6. GeoJSON для отключенных потребителей
    consumer_features = []
    for c in affected_consumers:
        if c["longitude"] is not None and c["latitude"] is not None:
            consumer_features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [c["longitude"], c["latitude"]],
                },
                "properties": {
                    "id": c["id"],
                    "name": c["name"],
                    "total_load": c["total_load"],
                    "heating_load": c["heating_load"],
                    "hot_water_load": c["hot_water_load"],
                },
            })

    summary = {
        "isolated_lines_count": len(isolated_lines),
        "isolated_nodes_count": len(isolated_nodes),
        "valves_count": len(valves_to_close),
        "valves_already_closed_count": len(valves_already_closed),
        "boundary_nodes_count": len(boundary_nodes),
        "consumers_count": len(affected_consumers),
        "total_heating_load_gcal_h": round(total_q_ot, 4),
        "total_gvs_load_gcal_h": round(total_q_gvs, 4),
        "total_vent_load_gcal_h": round(total_q_vent, 4),
        "total_load_gcal_h": round(total_q_ot + total_q_gvs + total_q_vent, 4),
        "total_pipe_length_m": round(total_length_m, 2),
        "total_pipe_volume_m3": round(total_volume_m3, 2),
    }

    return {
        "success": True,
        "target": {"line_id": line_id, "node_id": node_id},
        "summary": summary,
        "valves_to_close": valves_to_close,
        "valves_already_closed": valves_already_closed,
        "boundary_nodes": sorted(boundary_nodes),
        "affected_consumers": affected_consumers,
        "geojson": {
            "isolated_pipes": {
                "type": "FeatureCollection",
                "features": pipe_features,
            },
            "valves_to_close": {
                "type": "FeatureCollection",
                "features": valve_features,
            },
            "affected_consumers": {
                "type": "FeatureCollection",
                "features": consumer_features,
            },
        },
    }
