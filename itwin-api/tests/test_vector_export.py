"""Выгрузка слоёв в GeoPackage, FlatGeobuf, Shapefile (database/vector_export.py), сети и выборки."""

import asyncio
import io
import json
import zipfile
from contextlib import asynccontextmanager

import pyogrio
import pytest
from fastapi.testclient import TestClient

from database import network_select as ns
from database import vector_export as ve

LINE = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[76.9, 43.2], [76.91, 43.21]]},
        "properties": {"id": 1, "fileid": 74, "title": "ТК-1 — ТК-2", "diameter": 500.0}}
NODE = {"type": "Feature", "geometry": {"type": "Point", "coordinates": [76.9, 43.2]},
        "properties": {"id": 7, "fileid": 74, "name": "ТК-1"}}


def _read(tmp_path, name: str, content: bytes) -> dict[str, int]:
    """Слои файла (или zip) → число объектов; проверяет систему координат."""
    path = tmp_path / name
    path.write_bytes(content)
    files = [path]
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            zf.extractall(tmp_path / "x")
            files = [tmp_path / "x" / n for n in zf.namelist() if n.endswith((".shp", ".fgb"))]
    out = {}
    for f in files:
        for layer, _ in pyogrio.list_layers(f):
            info = pyogrio.read_info(f, layer=layer)
            assert info["crs"] == "EPSG:4326"
            out[str(layer)] = info["features"]
    return out


@pytest.mark.parametrize("key, expected_name, layers", [
    ("gpkg", "net.gpkg", {"lines": 1, "nodes": 1}),
    ("fgb", "net.zip", {"lines": 1, "nodes": 1}),
    ("shp", "net.zip", {"lines": 1, "nodes": 1}),
])
def test_write_two_layers(tmp_path, key, expected_name, layers):
    content, media, name = ve.write_layers(
        {"lines": ve.frame([LINE]), "nodes": ve.frame([NODE])}, ve.get_format(key), "net")
    assert name == expected_name and _read(tmp_path, name, content) == layers
    assert media == ("application/geopackage+sqlite3" if key == "gpkg" else "application/zip")


def test_single_flatgeobuf_layer_is_a_plain_file_with_unicode_fields(tmp_path):
    content, media, name = ve.write_layers({"lines": ve.frame([LINE]), "nodes": ve.frame([])},
                                           ve.FORMATS["fgb"], "sel")
    assert name == "sel.fgb" and media == "application/octet-stream"
    path = tmp_path / name
    path.write_bytes(content)
    df = pyogrio.read_dataframe(path)
    assert list(df["title"]) == ["ТК-1 — ТК-2"] and float(df["diameter"][0]) == 500.0


def test_empty_and_bad_format():
    with pytest.raises(ve.VectorExportError) as e:
        ve.write_layers({"lines": ve.frame([])}, ve.FORMATS["gpkg"], "x")
    assert e.value.status == 404
    content, media, name = ve.write_layers({"lines": ve.frame([])}, ve.FORMATS["shp"], "x", allow_empty=True)
    assert name == "x.zip" and zipfile.ZipFile(io.BytesIO(content)).namelist() == []
    with pytest.raises(ve.VectorExportError) as e:
        ve.get_format("kml")
    assert e.value.status == 422
    assert ve.get_format("GPKG").key == "gpkg"


def test_selection_result_features():
    result = {"target": "lines", "items": [
        {"id": 1, "fileid": 74, "title": "A — B", "length": 12.5, "distance_m": 40.0, "values": {"diameter": 500}},
        {"id": 2, "fileid": 74, "title": "C — D", "length": 3.0, "values": {"diameter": 400}},
    ], "geojson": {"features": [{"id": 1, "geometry": LINE["geometry"]}]}}
    feats = ns.result_features(result)
    assert len(feats) == 1  # без геометрии — не в файл
    assert feats[0]["properties"] == {"id": 1, "fileid": 74, "title": "A — B", "length": 12.5, "distance_m": 40.0,
                                      "diameter": 500}
    nodes = ns.result_features({"target": "nodes", "items": [
        {"id": 7, "fileid": 74, "title": "ТК-1", "node_type": "Тепловая камера", "card_type": "Узел", "values": {}}],
        "geojson": {"features": [{"id": 7, "geometry": NODE["geometry"]}]}})
    assert nodes[0]["properties"]["node_type"] == "Тепловая камера"


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _SelConn:
    def transaction(self):
        return _Tx()

    async def execute(self, sql, *args):
        pass

    async def fetchval(self, sql, *args):
        return True

    async def fetchrow(self, sql, *args):
        return None

    async def fetch(self, sql, *args):
        return [{"id": 1, "fileid": 74, "node1": "ТК-1", "node2": "ТК-2", "length": 12.5, "distance_m": None,
                 "f_diameter": 500.0, "lon": 76.9, "lat": 43.2, "total": 1, "total_length": 12.5,
                 "geometry": json.dumps(LINE["geometry"])}]


def test_endpoints(tmp_path, monkeypatch):
    import main
    from auth import invalidate_user_status
    from routers import network_select as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield _SelConn()

    monkeypatch.setattr(router, "acquire_conn", acquire)
    client = TestClient(main.app)
    body = {"spec": {"conditions": [{"field": "diameter", "op": "ge", "value": 500}]}, "format": "gpkg"}
    r = client.post("/api/v1/network-select/export", json=body)
    assert r.status_code == 200 and r.headers["x-export-rows"] == "1"
    assert "selection_lines.gpkg" in r.headers["content-disposition"]
    assert _read(tmp_path, "s.gpkg", r.content) == {"lines": 1}
    assert client.post("/api/v1/network-select/export", json={**body, "format": "xls"}).status_code == 422
    assert client.get("/api/export/network", params={"format": "kml"}).status_code == 422
