"""Пьезометрический график: путь по графу сети и данные узлов.

Как в десктопе (cxema/graph2.cpp): маршрут задаётся последовательностью узлов
(waypoints). Между соседними точками строится кратчайший путь, что позволяет
направить трассу через нужные участки, а не только «старт → финиш».
"""

import time

import networkx as nx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app_logging import get_logger
from database.connect import get_pool

logger = get_logger(__name__)

router = APIRouter(tags=["piezometer"])

_piezo_cached_graph = None
_piezo_cached_graph_time = 0.0


async def _get_topology_graph(conn):
    global _piezo_cached_graph, _piezo_cached_graph_time
    now = time.time()
    if _piezo_cached_graph is not None and (now - _piezo_cached_graph_time) < 60.0:
        return _piezo_cached_graph

    q_lines = '''
        SELECT L.id, L.nodeid1, L.nodeid2, COALESCE(HPS.pipesectlength, 10.0) as length
        FROM linesobj L
        LEFT JOIN heatpipesections HPS ON HPS.lineid = L.id
        WHERE L.nodeid1 IS NOT NULL AND L.nodeid2 IS NOT NULL AND COALESCE(L.removed, 0) = 0
    '''
    lines = await conn.fetch(q_lines)
    G = nx.Graph()
    for row in lines:
        # При параллельных рёбрах оставляем самое короткое
        prev = G.get_edge_data(row['nodeid1'], row['nodeid2'])
        if prev is None or row['length'] < prev.get('weight', 1e18):
            G.add_edge(row['nodeid1'], row['nodeid2'], id=row['id'], weight=row['length'])

    _piezo_cached_graph = G
    _piezo_cached_graph_time = now
    return G


def invalidate_topology_cache():
    global _piezo_cached_graph
    _piezo_cached_graph = None


def _build_route(G: nx.Graph, waypoints: list[int]) -> list[int]:
    """Кратчайший путь, проходящий через все waypoints по порядку."""
    for node in waypoints:
        if node not in G:
            raise HTTPException(status_code=404, detail=f"Узел {node} не найден в графе сети.")

    full_path: list[int] = []
    for i in range(len(waypoints) - 1):
        try:
            segment = nx.shortest_path(G, source=waypoints[i], target=waypoints[i + 1], weight='weight')
        except nx.NetworkXNoPath:
            raise HTTPException(
                status_code=404,
                detail=f"Нет пути между узлами {waypoints[i]} и {waypoints[i + 1]}.",
            )
        # Стыкуем сегменты, не дублируя общий узел
        full_path.extend(segment if i == 0 else segment[1:])
    return full_path


async def _assemble_path_data(conn, G: nx.Graph, path_nodes: list[int]) -> list[dict]:
    """Собирает по узлам пути: расстояние, отметку, напоры, температуры, координаты."""
    q_nodes = '''
        SELECT
            n.id,
            n.geomarktoptube,
            n.calcpressflow,
            n.calcpressret,
            COALESCE(NULLIF(n.nodename, ''), NULLIF(n.externalnodename, ''), n.id::text) AS label,
            CASE WHEN n.shape IS NULL THEN NULL
                 ELSE ST_X(ST_Transform(n.shape, 4326)) END AS lng,
            CASE WHEN n.shape IS NULL THEN NULL
                 ELSE ST_Y(ST_Transform(n.shape, 4326)) END AS lat,
            pt.t1 AS t_pod,
            pt.t2 AS t_obr
        FROM nodes n
        LEFT JOIN pt_out pt ON pt.nodeid = n.id
        WHERE n.id = ANY($1::int[])
    '''
    rows = await conn.fetch(q_nodes, path_nodes)
    attrs_map = {r['id']: r for r in rows}

    path_data: list[dict] = []
    cum_dist = 0.0
    for i, n_id in enumerate(path_nodes):
        if i > 0:
            edge = G.get_edge_data(path_nodes[i - 1], n_id)
            cum_dist += float(edge.get('weight', 0.0)) if edge else 0.0

        attrs = attrs_map.get(n_id)
        item: dict = {"node_id": n_id, "distance": round(cum_dist, 2)}
        if attrs:
            z = float(attrs['geomarktoptube'] or 0.0)
            h_pod = attrs['calcpressflow']
            h_obr = attrs['calcpressret']
            item.update({
                "label": attrs['label'],
                "z": z,
                # Пьезометрический напор = отметка + давление; None если расчёта нет
                "h_pod": z + float(h_pod) if h_pod is not None else None,
                "h_obr": z + float(h_obr) if h_obr is not None else None,
                "t_pod": float(attrs['t_pod']) if attrs['t_pod'] is not None else None,
                "t_obr": float(attrs['t_obr']) if attrs['t_obr'] is not None else None,
                "lng": float(attrs['lng']) if attrs['lng'] is not None else None,
                "lat": float(attrs['lat']) if attrs['lat'] is not None else None,
            })
        else:
            item.update({"label": str(n_id), "z": 0.0, "h_pod": None, "h_obr": None,
                         "t_pod": None, "t_obr": None, "lng": None, "lat": None})
        path_data.append(item)
    return path_data


def _has_calc(path_data: list[dict]) -> bool:
    return any(i.get("h_pod") is not None or i.get("h_obr") is not None for i in path_data)


@router.get("/piezometer/path")
async def get_piezometer_path(start: int, end: int):
    """Кратчайший путь между двумя узлами (обратная совместимость)."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)
            path_nodes = _build_route(G, [start, end])
            path_data = await _assemble_path_data(conn, G, path_nodes)
            return {"path": path_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching piezometer path: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class RouteRequest(BaseModel):
    nodes: list[int] = Field(..., min_length=2, description="Последовательность узлов маршрута")


@router.post("/piezometer/route")
async def build_piezometer_route(body: RouteRequest):
    """Маршрут через последовательность узлов (waypoints), как выделение направления в десктопе."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)
            path_nodes = _build_route(G, body.nodes)
            path_data = await _assemble_path_data(conn, G, path_nodes)
            total_length = path_data[-1]["distance"] if path_data else 0.0
            return {
                "path": path_data,
                "waypoints": body.nodes,
                "node_count": len(path_data),
                "total_length": total_length,
                "has_calculation": _has_calc(path_data),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building piezometer route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
