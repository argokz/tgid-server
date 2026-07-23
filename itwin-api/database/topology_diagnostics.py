import logging
from database.connect import get_pool

logger = logging.getLogger(__name__)

async def get_topology_diagnostics(limit: int = 200):
    """
    Returns a list of topology faults in the network.
    Supported faults:
    1. Orphaned nodes (nodes with no connected lines).
    2. Dangling lines (lines with a missing nodeid1 or nodeid2).
    3. Zero-length lines (nodeid1 == nodeid2).
    """
    pool = get_pool()
    faults = []
    
    async with pool.acquire() as conn:
        # 1. Orphaned nodes
        q_orphaned_nodes = """
            SELECT n.id, n.x / 100.0 as lng, n.y / -100.0 as lat
            FROM nodes n
            LEFT JOIN linesobj l ON l.nodeid1 = n.id OR l.nodeid2 = n.id
            WHERE n.removed = 0 AND l.id IS NULL
            LIMIT $1
        """
        orphans = await conn.fetch(q_orphaned_nodes, limit)
        for row in orphans:
            faults.append({
                "type": "orphaned_node",
                "object_type": "node",
                "object_id": row["id"],
                "lat": float(row["lat"]) if row["lat"] else None,
                "lng": float(row["lng"]) if row["lng"] else None,
                "description": "Узел не имеет привязанных линий (изолирован)"
            })
            
        # 2. Dangling lines
        q_dangling_lines = """
            SELECT l.id as line_id, l.nodeid1, l.nodeid2, 
                   n1.id as n1_exists, n2.id as n2_exists,
                   (SELECT x/100.0 FROM nodes WHERE id = COALESCE(n1.id, n2.id)) as lng,
                   (SELECT y/-100.0 FROM nodes WHERE id = COALESCE(n1.id, n2.id)) as lat
            FROM linesobj l
            LEFT JOIN nodes n1 ON l.nodeid1 = n1.id AND n1.removed = 0
            LEFT JOIN nodes n2 ON l.nodeid2 = n2.id AND n2.removed = 0
            WHERE l.removed = 0 AND (n1.id IS NULL OR n2.id IS NULL)
            LIMIT $1
        """
        dangling = await conn.fetch(q_dangling_lines, limit)
        for row in dangling:
            desc = "Отсутствует один или оба узла"
            if not row["n1_exists"] and not row["n2_exists"]:
                desc = "Оба узла линии отсутствуют (удалены или не существуют)"
            elif not row["n1_exists"]:
                desc = f"Начальный узел (ID {row['nodeid1']}) не найден"
            elif not row["n2_exists"]:
                desc = f"Конечный узел (ID {row['nodeid2']}) не найден"
                
            faults.append({
                "type": "dangling_line",
                "object_type": "line",
                "object_id": row["line_id"],
                "lat": float(row["lat"]) if row["lat"] else None,
                "lng": float(row["lng"]) if row["lng"] else None,
                "description": desc
            })
            
        # 3. Zero length lines
        q_zero_lines = """
            SELECT l.id as line_id, n.x/100.0 as lng, n.y/-100.0 as lat
            FROM linesobj l
            JOIN nodes n ON l.nodeid1 = n.id
            WHERE l.removed = 0 AND l.nodeid1 = l.nodeid2
            LIMIT $1
        """
        zero_lines = await conn.fetch(q_zero_lines, limit)
        for row in zero_lines:
            faults.append({
                "type": "zero_length_line",
                "object_type": "line",
                "object_id": row["line_id"],
                "lat": float(row["lat"]) if row["lat"] else None,
                "lng": float(row["lng"]) if row["lng"] else None,
                "description": "Нулевая длина линии (начальный и конечный узел совпадают)"
            })
            
    return faults
