"""Resolve passport site (MS/RS) when nodes.belong*Site are NULL.

Desktop historically kept belongMagistralSite / belongDistSite on nodes.
Production dumps often have them NULL while heatpipesections still carries
magistralSite / distSite — use that as fallback so Excel passport works.
"""

from __future__ import annotations

from typing import Optional, Tuple


def resolve_site_from_node_row(bms, bds) -> Optional[Tuple[str, int]]:
    if bms and int(bms) > 0:
        return "ms", int(bms)
    if bds and int(bds) > 0:
        return "rs", int(bds)
    return None


def resolve_site_via_heatpipesections(cur, node_id: int, line_id: Optional[int] = None):
    """Return (ms_rs, site_id) using heatpipesections, or None."""
    if line_id:
        cur.execute(
            """
            SELECT NULLIF(magistralsite, 0), NULLIF(distsite, 0)
              FROM heatpipesections
             WHERE lineid = %s
             LIMIT 1
            """,
            (line_id,),
        )
        row = cur.fetchone()
        if row:
            ms, rs = row
            if ms:
                return "ms", int(ms)
            if rs:
                return "rs", int(rs)

    # Majority vote among incident lines of the node
    cur.execute(
        """
        SELECT site_kind, site_id, cnt FROM (
          SELECT 'ms' AS site_kind, hps.magistralsite AS site_id, COUNT(*)::int AS cnt
            FROM linesobj lo
            JOIN heatpipesections hps ON hps.lineid = lo.id
           WHERE (lo.nodeid1 = %s OR lo.nodeid2 = %s)
             AND NULLIF(hps.magistralsite, 0) IS NOT NULL
           GROUP BY hps.magistralsite
          UNION ALL
          SELECT 'rs', hps.distsite, COUNT(*)::int
            FROM linesobj lo
            JOIN heatpipesections hps ON hps.lineid = lo.id
           WHERE (lo.nodeid1 = %s OR lo.nodeid2 = %s)
             AND NULLIF(hps.distsite, 0) IS NOT NULL
           GROUP BY hps.distsite
        ) t
        ORDER BY cnt DESC
        LIMIT 1
        """,
        (node_id, node_id, node_id, node_id),
    )
    row = cur.fetchone()
    if not row:
        return None
    kind, site_id, _cnt = row
    return str(kind), int(site_id)
