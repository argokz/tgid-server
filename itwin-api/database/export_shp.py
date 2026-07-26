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


async def export_network_to_shp(
    fragment_ids: Optional[Sequence[int]] = None,
    *,
    limit: int = 50000,
) -> bytes:
    try:
        frags = list(fragment_ids) if fragment_ids else None
        async with acquire_conn() as conn:
            if frags:
                res_nodes = await conn.fetch(
                    """
                    SELECT id, fileid, nodename AS name,
                           ST_AsGeoJSON(ST_Transform(shape, 4326)) AS geom
                      FROM nodes
                     WHERE COALESCE(removed, 0) = 0
                       AND fileid = ANY($1::int[])
                       AND shape IS NOT NULL
                     LIMIT $2
                    """,
                    frags,
                    limit,
                )
                res_lines = await conn.fetch(
                    """
                    SELECT lo.id, lo.nodeid1, lo.nodeid2, lo.externalsignlineid,
                           n1.fileid,
                           ST_AsGeoJSON(ST_Transform(lo.shape, 4326)) AS geom
                      FROM linesobj lo
                      JOIN nodes n1 ON n1.id = lo.nodeid1
                     WHERE COALESCE(lo.removed, 0) = 0
                       AND n1.fileid = ANY($1::int[])
                       AND lo.shape IS NOT NULL
                     LIMIT $2
                    """,
                    frags,
                    limit,
                )
            else:
                res_nodes = await conn.fetch(
                    """
                    SELECT id, fileid, nodename AS name,
                           ST_AsGeoJSON(ST_Transform(shape, 4326)) AS geom
                      FROM nodes
                     WHERE COALESCE(removed, 0) = 0
                       AND shape IS NOT NULL
                     LIMIT $1
                    """,
                    limit,
                )
                res_lines = await conn.fetch(
                    """
                    SELECT id, nodeid1, nodeid2, externalsignlineid,
                           ST_AsGeoJSON(ST_Transform(shape, 4326)) AS geom
                      FROM linesobj
                     WHERE COALESCE(removed, 0) = 0
                       AND shape IS NOT NULL
                     LIMIT $1
                    """,
                    limit,
                )

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

