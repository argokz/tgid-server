import os
import json
import zipfile
import io
import tempfile
import geopandas as gpd
from fastapi import HTTPException
from database.connect import acquire_conn

async def export_network_to_shp():
    try:
        async with acquire_conn() as conn:
            # Get nodes
            q_nodes = "SELECT id, ST_AsGeoJSON(geom) as geom, objecttype, objectid, name, external_code FROM nodes"
            res_nodes = await conn.fetch(q_nodes)
            
            # Get lines
            q_lines = "SELECT id, ST_AsGeoJSON(geom) as geom, objecttype, objectid, name, nodeid1, nodeid2 FROM linesobj"
            res_lines = await conn.fetch(q_lines)

        features_nodes = []
        for r in res_nodes:
            if r['geom']:
                props = {k: v for k, v in dict(r).items() if k != 'geom'}
                features_nodes.append({
                    "type": "Feature",
                    "geometry": json.loads(r['geom']),
                    "properties": props
                })

        features_lines = []
        for r in res_lines:
            if r['geom']:
                props = {k: v for k, v in dict(r).items() if k != 'geom'}
                features_lines.append({
                    "type": "Feature",
                    "geometry": json.loads(r['geom']),
                    "properties": props
                })

        gdf_nodes = gpd.GeoDataFrame.from_features(features_nodes) if features_nodes else gpd.GeoDataFrame()
        if not gdf_nodes.empty:
            gdf_nodes.set_crs(epsg=4326, inplace=True, allow_override=True)

        gdf_lines = gpd.GeoDataFrame.from_features(features_lines) if features_lines else gpd.GeoDataFrame()
        if not gdf_lines.empty:
            gdf_lines.set_crs(epsg=4326, inplace=True, allow_override=True)
            
        memory_file = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmpdir:
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                if not gdf_nodes.empty:
                    nodes_path = os.path.join(tmpdir, "nodes.shp")
                    gdf_nodes.to_file(nodes_path, driver="ESRI Shapefile")
                    for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                        fpath = os.path.join(tmpdir, f"nodes.{ext}")
                        if os.path.exists(fpath):
                            zf.write(fpath, f"nodes.{ext}")
                
                if not gdf_lines.empty:
                    lines_path = os.path.join(tmpdir, "lines.shp")
                    gdf_lines.to_file(lines_path, driver="ESRI Shapefile")
                    for ext in ['shp', 'shx', 'dbf', 'prj', 'cpg']:
                        fpath = os.path.join(tmpdir, f"lines.{ext}")
                        if os.path.exists(fpath):
                            zf.write(fpath, f"lines.{ext}")

        memory_file.seek(0)
        return memory_file.getvalue()
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error exporting SHP: {str(e)}")
