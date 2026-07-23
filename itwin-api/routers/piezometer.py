"""Пьезометрический график: кратчайший путь по графу сети и данные узлов."""

import time

import networkx as nx
from fastapi import APIRouter, HTTPException

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
        G.add_edge(row['nodeid1'], row['nodeid2'], id=row['id'], weight=row['length'])

    _piezo_cached_graph = G
    _piezo_cached_graph_time = now
    return G


def invalidate_topology_cache():
    global _piezo_cached_graph
    _piezo_cached_graph = None


@router.get("/piezometer/path")
async def get_piezometer_path(start: int, end: int):
    """Строит кратчайший путь между двумя узлами и возвращает данные для пьезометрического графика."""
    try:
        pool = get_pool()
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)

            if start not in G or end not in G:
                raise HTTPException(status_code=404, detail="Начальный или конечный узел не найдены в графе.")

            try:
                path_nodes = nx.shortest_path(G, source=start, target=end, weight='weight')
            except nx.NetworkXNoPath:
                raise HTTPException(status_code=404, detail="Нет пути между данными узлами.")

            # 3. Calculate cumulative distance
            path_data = []
            cum_dist = 0.0

            for i, n_id in enumerate(path_nodes):
                if i > 0:
                    prev_node = path_nodes[i-1]
                    edge_data = G.get_edge_data(prev_node, n_id)
                    cum_dist += float(edge_data.get('weight', 0.0))

                path_data.append({
                    "node_id": n_id,
                    "distance": cum_dist
                })

            # 4. Fetch node attributes (Z, H_pod, H_obr)
            q_nodes = '''
                SELECT id, geomarktoptube, calcpressflow, calcpressret
                FROM nodes
                WHERE id = ANY($1::int[])
            '''
            nodes_attrs = await conn.fetch(q_nodes, path_nodes)
            attrs_map = { r['id']: r for r in nodes_attrs }

            # 5. Merge data
            for item in path_data:
                n_id = item["node_id"]
                attrs = attrs_map.get(n_id)
                if attrs:
                    # Не подменяем отсутствующие результаты расчёта фиктивными напорами.
                    z = float(attrs['geomarktoptube'] or 0.0)
                    h_pod = attrs['calcpressflow']
                    h_obr = attrs['calcpressret']
                    item["z"] = z
                    item["h_pod"] = z + float(h_pod) if h_pod is not None else None
                    item["h_obr"] = z + float(h_obr) if h_obr is not None else None
                else:
                    item["z"] = 0.0
                    item["h_pod"] = 0.0
                    item["h_obr"] = 0.0

            return {"path": path_data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching piezometer path: {e}")
        raise HTTPException(status_code=500, detail=str(e))
