"""Выгрузка сети фрагментов (узлы и участки) в файлы ГИС: Shapefile, GeoPackage, FlatGeobuf.

Слои: lines (участки: узлы концов, признак, фрагмент, Ду и длина по паспорту) и nodes (узлы фрагментов
и концы их участков). Запись — database/vector_export.py.
"""

from __future__ import annotations

import json
from typing import Optional, Sequence

import geopandas as gpd
from fastapi import HTTPException
from fastapi.concurrency import run_in_threadpool

from app_logging import get_logger
from database import vector_export as ve
from database.connect import acquire_conn
from database.fragment_filter import LINE_IN_FRAGMENTS_SQL, LIVE_LINE_SQL
from database.network_export import split_limited

logger = get_logger(__name__)

# Участки фрагмента — по linesobj.fileid (единое правило database.fragment_filter, QA F13);
# паспорт — самый длинный (как в износе и тематических картах)
_LINES_SQL = f"""
    SELECT lo.id, lo.nodeid1, lo.nodeid2, lo.externalsignlineid, lo.fileid,
           h.diametercondit AS diameter, h.pipesectlength AS length,
           ST_AsGeoJSON(ST_Transform(lo.shape, 4326)) AS geom
      FROM linesobj lo
      LEFT JOIN LATERAL (SELECT hp.diametercondit, hp.pipesectlength FROM heatpipesections hp
                          WHERE hp.lineid = lo.id
                          ORDER BY hp.pipesectlength DESC NULLS LAST, hp.id DESC LIMIT 1) h ON true
     WHERE {LIVE_LINE_SQL}
       AND {LINE_IN_FRAGMENTS_SQL}
       AND lo.shape IS NOT NULL
     ORDER BY lo.id
     LIMIT $2
"""

# Узлы фрагмента: свои (nodes.fileid) и концы его участков — у части участков узлы
# числятся в другом фрагменте, без них слой линий ссылался бы на отсутствующие узлы
_NODES_SQL = f"""
    SELECT n.id, n.fileid, n.nodename AS name,
           ST_AsGeoJSON(ST_Transform(n.shape, 4326)) AS geom
      FROM nodes n
     WHERE COALESCE(n.removed, 0) = 0
       AND n.shape IS NOT NULL
       AND ($1::int[] IS NULL
            OR n.fileid = ANY($1::int[])
            OR n.id IN (SELECT unnest(ARRAY[lo.nodeid1, lo.nodeid2])
                          FROM linesobj lo
                         WHERE {LIVE_LINE_SQL} AND lo.fileid = ANY($1::int[])))
     ORDER BY n.id
     LIMIT $2
"""


def _features(rows) -> list[dict]:
    return [{"type": "Feature", "geometry": json.loads(r["geom"]),
             "properties": {k: v for k, v in dict(r).items() if k != "geom"}}
            for r in rows if r["geom"]]


async def network_layers(fragment_ids: Optional[Sequence[int]], *, limit: int,
                         stats: Optional[dict] = None) -> dict[str, gpd.GeoDataFrame]:
    """Слои lines и nodes; stats получает lines/nodes/truncated (запрос limit + 1 строки, QA F84)."""
    frags = sorted({int(f) for f in fragment_ids}) if fragment_ids else None
    async with acquire_conn() as conn:
        res_lines, lines_cut = split_limited(await conn.fetch(_LINES_SQL, frags, limit + 1), limit)
        res_nodes, nodes_cut = split_limited(await conn.fetch(_NODES_SQL, frags, limit + 1), limit)
    if stats is not None:
        stats.update(lines=len(res_lines), nodes=len(res_nodes), truncated=lines_cut or nodes_cut)
    return {"nodes": ve.frame(_features(res_nodes)), "lines": ve.frame(_features(res_lines))}


async def export_network(fragment_ids: Optional[Sequence[int]], fmt: ve.VectorFormat, *, limit: int = 50000,
                         stats: Optional[dict] = None, base_name: str = "network_export",
                         allow_empty: bool = False) -> tuple[bytes, str, str]:
    """Сеть фрагментов в формате fmt: (содержимое, тип, имя файла)."""
    try:
        layers = await network_layers(fragment_ids, limit=limit, stats=stats)
        return await run_in_threadpool(ve.write_layers, layers, fmt, base_name, allow_empty=allow_empty)
    except ve.VectorExportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Выгрузка сети (%s) не удалась", fmt.key, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось выгрузить сеть в {fmt.title}") from exc


async def export_network_to_shp(
    fragment_ids: Optional[Sequence[int]] = None,
    *,
    limit: int = 50000,
    stats: Optional[dict] = None,
) -> bytes:
    """ZIP с nodes.shp и lines.shp (прежний адрес /api/export/shp)."""
    content, _, _ = await export_network(fragment_ids, ve.FORMATS["shp"], limit=limit, stats=stats, allow_empty=True)
    return content
