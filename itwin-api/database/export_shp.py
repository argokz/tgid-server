"""SHP export of nodes/lines (optional fragment filter)."""

from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile
from typing import Optional, Sequence

import geopandas as gpd
from fastapi import HTTPException

from database.connect import acquire_conn
from database.fragment_filter import LINE_IN_FRAGMENTS_SQL, LIVE_LINE_SQL


# Участки фрагмента — по linesobj.fileid (единое правило database.fragment_filter, QA F13)
_LINES_SQL = f"""
    SELECT lo.id, lo.nodeid1, lo.nodeid2, lo.externalsignlineid, lo.fileid,
           ST_AsGeoJSON(ST_Transform(lo.shape, 4326)) AS geom
      FROM linesobj lo
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


async def export_network_to_shp(
    fragment_ids: Optional[Sequence[int]] = None,
    *,
    limit: int = 50000,
) -> bytes:
    try:
        frags = sorted({int(f) for f in fragment_ids}) if fragment_ids else None
        async with acquire_conn() as conn:
            res_lines = await conn.fetch(_LINES_SQL, frags, limit)
            res_nodes = await conn.fetch(_NODES_SQL, frags, limit)

        features_nodes = []
        for r in res_nodes:
            if not r["geom"]:
                continue
            props = {k: v for k, v in dict(r).items() if k != "geom"}
            features_nodes.append(
                {"type": "Feature", "geometry": json.loads(r["geom"]), "properties": props}
            )

        features_lines = []
        for r in res_lines:
            if not r["geom"]:
                continue
            props = {k: v for k, v in dict(r).items() if k != "geom"}
            features_lines.append(
                {"type": "Feature", "geometry": json.loads(r["geom"]), "properties": props}
            )

        gdf_nodes = (
            gpd.GeoDataFrame.from_features(features_nodes) if features_nodes else gpd.GeoDataFrame()
        )
        if not gdf_nodes.empty:
            gdf_nodes.set_crs(epsg=4326, inplace=True, allow_override=True)

        gdf_lines = (
            gpd.GeoDataFrame.from_features(features_lines) if features_lines else gpd.GeoDataFrame()
        )
        if not gdf_lines.empty:
            gdf_lines.set_crs(epsg=4326, inplace=True, allow_override=True)

        memory_file = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
                if not gdf_nodes.empty:
                    nodes_path = os.path.join(tmpdir, "nodes.shp")
                    gdf_nodes.to_file(nodes_path, driver="ESRI Shapefile")
                    for ext in ["shp", "shx", "dbf", "prj", "cpg"]:
                        fpath = os.path.join(tmpdir, f"nodes.{ext}")
                        if os.path.exists(fpath):
                            zf.write(fpath, f"nodes.{ext}")

                if not gdf_lines.empty:
                    lines_path = os.path.join(tmpdir, "lines.shp")
                    gdf_lines.to_file(lines_path, driver="ESRI Shapefile")
                    for ext in ["shp", "shx", "dbf", "prj", "cpg"]:
                        fpath = os.path.join(tmpdir, f"lines.{ext}")
                        if os.path.exists(fpath):
                            zf.write(fpath, f"lines.{ext}")

        memory_file.seek(0)
        return memory_file.getvalue()

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error exporting SHP: {e}") from e

