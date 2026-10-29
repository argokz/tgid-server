"""Мастер импорта: векторные форматы GDAL (GeoPackage, ESRI JSON, FlatGeobuf, KML, *.gdb) и защита архива."""

from __future__ import annotations

import io
import json
import os
import zipfile

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point

from database import network_import as ni


def _write(tmp_path, name: str, driver: str, frames: dict[str, gpd.GeoDataFrame]) -> bytes:
    path = tmp_path / name
    for layer, gdf in frames.items():
        gdf.to_file(path, driver=driver, layer=layer if driver in ("GPKG", "OpenFileGDB") else None)
    return b"" if path.is_dir() else path.read_bytes()


def _lines(n: int = 2) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"DU": [150 + i for i in range(n)]},
                            geometry=[LineString([(76.9 + i * 0.01, 43.2), (76.905 + i * 0.01, 43.21)]) for i in range(n)],
                            crs=4326)


def _points() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"KOD": ["A-1"]}, geometry=[Point(76.9, 43.2)], crs=4326)


def test_geopackage_picks_layer_and_lists_all(tmp_path):
    content = _write(tmp_path, "net.gpkg", "GPKG", {"pipes": _lines(), "wells": _points()})
    src = ni.parse_upload([("net.gpkg", content)])
    assert src.kind == "vector" and src.format == "GeoPackage" and src.layer == "pipes"
    assert {l["name"]: l["count"] for l in src.source_layers} == {"pipes": 2, "wells": 1}
    assert src.geometry_type == "LineString" and src.rows[0]["DU"] == 150 and src.geometry_srid == 4326
    assert any("Слоёв в файле: 2" in w for w in src.warnings)
    wells = ni.parse_upload([("net.gpkg", content)], layer="wells")
    assert wells.layer == "wells" and wells.rows == [{"KOD": "A-1"}] and not wells.warnings
    with pytest.raises(ValueError, match="Слоя «none»"):
        ni.parse_upload([("net.gpkg", content)], layer="none")
    info = ni.describe_source(src, "lines")
    assert info["format"] == "GeoPackage" and info["layer"] == "pipes" and len(info["source_layers"]) == 2


def test_esri_json_feature_set():
    """Выгрузка слоя ArcGIS (FeatureServer/query?f=json) — ESRI JSON."""
    doc = {
        "geometryType": "esriGeometryPolyline", "spatialReference": {"wkid": 4326},
        "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"}, {"name": "DN", "type": "esriFieldTypeInteger"}],
        "features": [{"attributes": {"OBJECTID": 1, "DN": 300},
                      "geometry": {"paths": [[[76.9, 43.2], [76.91, 43.21]]]}}],
    }
    src = ni.parse_upload([("layer.json", json.dumps(doc).encode())])
    assert src.kind == "vector" and src.geometry_type == "LineString"
    assert src.rows[0]["DN"] == 300 and src.geometry_srid == 4326


@pytest.mark.parametrize("name, driver", [("a.fgb", "FlatGeobuf"), ("a.kml", "KML"), ("a.geojson", "GeoJSON")])
def test_single_file_formats(tmp_path, name, driver):
    content = _write(tmp_path, name, driver, {"x": _lines(1)})
    src = ni.parse_upload([(name, content)])
    assert src.kind == "vector" and src.geometry_type == "LineString" and len(src.rows) == 1


def test_file_geodatabase_in_zip(tmp_path):
    _write(tmp_path, "net.gdb", "OpenFileGDB", {"pipes": _lines(3)})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for f in os.listdir(tmp_path / "net.gdb"):
            zf.write(tmp_path / "net.gdb" / f, f"export/net.gdb/{f}")
    src = ni.parse_upload([("net.zip", buf.getvalue())])
    assert src.format == "ArcGIS File Geodatabase" and src.layer == "pipes" and len(src.rows) == 3


def test_archive_guards(tmp_path):
    # путь из архива не выходит из каталога распаковки
    content = _write(tmp_path, "a.geojson", "GeoJSON", {"x": _lines(1)})
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../evil/a.geojson", content)
    assert len(ni.parse_upload([("a.zip", buf.getvalue())]).rows) == 1
    # архив без данных ГИС
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("readme.txt", "x")
    with pytest.raises(ValueError, match="нет данных ГИС"):
        ni.parse_upload([("a.zip", buf.getvalue())])


def test_zip_bomb_limit(monkeypatch):
    monkeypatch.setattr(ni, "MAX_UNZIPPED_BYTES", 1000)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.geojson", "0" * 5000)
    with pytest.raises(ValueError, match="200 МБ"):
        ni.parse_upload([("a.zip", buf.getvalue())])


def test_validate_layer_param():
    with pytest.raises(ValueError, match="layer"):
        ni.validate_params({"mode": "lines", "layer": ["a"]})
