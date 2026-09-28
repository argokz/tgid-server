"""Этап 10: импорт SHP, Excel/CSV и координат узлов — разбор, сопоставление, права (без живой БД)."""

from __future__ import annotations

import io
import json
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import network_import as ni  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _xlsx(rows: list[list]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Узлы"
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _shp_zip(geoms, attrs: dict, crs=4326) -> bytes:
    import tempfile

    import geopandas as gpd

    gdf = gpd.GeoDataFrame(attrs, geometry=geoms, crs=crs)
    with tempfile.TemporaryDirectory() as tmp:
        gdf.to_file(os.path.join(tmp, "layer.shp"), encoding="utf-8")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for name in os.listdir(tmp):
                zf.write(os.path.join(tmp, name), name)
    return buf.getvalue()


# --- разбор --------------------------------------------------------------------

def test_xlsx_header_row_numbers_and_mapping_suggestion():
    src = ni.parse_upload([("n.xlsx", _xlsx([[], ["Код", "X", "Y", "Отметка"], ["A-1", 1.5, 2, 800], [None, None], ["A-2", "3,5", 4, None]]))])
    assert src.kind == "table"
    assert src.columns == ["Код", "X", "Y", "Отметка"]
    assert src.row_numbers == [3, 5]
    assert src.warnings == ["Заголовки взяты из строки 2"]
    assert ni.suggest_mapping("nodes", src.columns, False) == {"x": "X", "y": "Y", "code": "Код", "elevation": "Отметка"}
    # из SHP координаты берутся из геометрии — X/Y не предлагаются
    assert "x" not in ni.suggest_mapping("coords", ["id", "X", "Y"], True)


def test_csv_semicolon_cp1251_and_duplicate_columns():
    content = "Узел;X;X\n1;10;20\n".encode("cp1251")
    src = ni.parse_upload([("c.csv", content)])
    assert src.columns == ["Узел", "X", "X_2"]
    assert src.rows == [{"Узел": "1", "X": "10", "X_2": "20"}]


def test_unsupported_and_old_excel_rejected():
    with pytest.raises(ValueError, match="xlsx или CSV"):
        ni.parse_upload([("a.xls", b"x")])
    with pytest.raises(ValueError, match="Неподдерживаемый"):
        ni.parse_upload([("a.pdf", b"x")])


def test_shp_zip_is_reprojected_to_wgs84():
    from shapely.geometry import LineString

    content = _shp_zip([LineString([(0, 0), (100, 0)])], {"DU": [150]}, crs=3857)
    src = ni.parse_upload([("l.zip", content)])
    assert src.kind == "shp" and src.geometry_type == "LineString"
    assert src.geometry_srid == 4326
    assert src.rows == [{"DU": 150}]
    x2 = src.geometries[0].coords[-1][0]
    assert x2 == pytest.approx(100 / 111319.49, rel=1e-4)


def test_shp_without_shx_is_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.shp", b"x")
        zf.writestr("a.dbf", b"x")
    with pytest.raises(ValueError, match="a.shx"):
        ni.parse_upload([("a.zip", buf.getvalue())])


# --- подготовка строк ------------------------------------------------------------

def test_to_float_accepts_comma_and_spaces():
    assert ni.to_float("1 234,5") == 1234.5
    assert ni.to_float("") is None
    assert ni.to_float(7) == 7.0
    with pytest.raises(ValueError):
        ni.to_float("abc")


def test_point_to_source_xy_desktop_is_cm_with_inverted_y():
    assert ni.point_to_source_xy(-923304.0, 304227.0, "desktop") == (-9233.04, -3042.27, 9998)
    assert ni.point_to_source_xy(76.9, 43.2, "wgs84") == (76.9, 43.2, 4326)
    with pytest.raises(ValueError):
        ni.point_to_source_xy(500, 43, "wgs84")
    with pytest.raises(ValueError):
        ni.point_to_source_xy(1, 1, "auto")


def test_prepare_items_reports_row_errors_and_requires_mapping():
    src = ni.parse_upload([("n.xlsx", _xlsx([["id", "X", "Y"], [5, 76.9, 43.2], [None, 76.9, 43.2], [6, None, 1]]))])
    params = {"mode": "coords", "source_crs": "wgs84", "mapping": {"key": "id", "x": "X", "y": "Y"}}
    items = ni.prepare_items(src, params)
    assert [i.error for i in items] == [None, "пустой id/код узла", "нет координат X/Y"]
    assert (items[0].x, items[0].y, items[0].srid, items[0].attrs["key"]) == (76.9, 43.2, 4326, "5")
    with pytest.raises(ValueError, match="обязательное поле"):
        ni.prepare_items(src, {"mode": "coords", "source_crs": "wgs84", "mapping": {"key": "id"}})
    with pytest.raises(ValueError, match="систему координат"):
        ni.prepare_items(src, {**params, "source_crs": "auto"})
    with pytest.raises(ValueError, match="Нет колонок"):
        ni.prepare_items(src, {**params, "mapping": {"key": "nope", "x": "X", "y": "Y"}})


def test_lines_only_from_shp_and_multipart_rejected():
    from shapely.geometry import MultiLineString

    table = ni.parse_upload([("n.csv", b"a;b\n1;2\n")])
    with pytest.raises(ValueError, match="только из SHP"):
        ni.prepare_items(table, {"mode": "lines", "mapping": {}})
    content = _shp_zip([MultiLineString([[(0, 0), (1, 1)], [(2, 2), (3, 3)]])], {"DU": [100]})
    src = ni.parse_upload([("l.zip", content)])
    items = ni.prepare_items(src, {"mode": "lines", "mapping": {"diameter": "DU"}})
    assert "2 частей" in items[0].error


def test_validate_params():
    with pytest.raises(ValueError, match="mode"):
        ni.validate_params({"mode": "x"})
    with pytest.raises(ValueError, match="Допуск"):
        ni.validate_params({"mode": "lines", "snap_tolerance_m": 100})


# --- маршруты и права ----------------------------------------------------------

def test_inspect_requires_editor_and_describes_file(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    files = {"files": ("n.xlsx", _xlsx([["Код", "X", "Y"], ["A", 1, 2]]), "application/octet-stream")}
    r = client.post("/api/v1/import/inspect", files=files, data={"mode": "nodes"}, headers=_bearer("viewer"))
    assert r.status_code == 403
    r = client.post("/api/v1/import/inspect", files=files, data={"mode": "nodes"}, headers=_bearer("editor"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["row_count"] == 1 and body["suggested_mapping"]["code"] == "Код"
    assert {t["key"] for t in body["targets"]} >= {"x", "y", "code"}


def test_run_needs_topology_flag_and_admin_for_apply(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    files = {"files": ("n.csv", b"id;X;Y\n1;76.9;43.2\n", "text/csv")}
    params = json.dumps({"mode": "coords", "match_by": "id", "source_crs": "wgs84", "mapping": {"key": "id", "x": "X", "y": "Y"}})
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "false")
    r = client.post("/api/v1/import/run", files=files, data={"params": params, "dry_run": "true"}, headers=_bearer("editor"))
    assert r.status_code == 503
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    r = client.post("/api/v1/import/run", files=files, data={"params": params, "dry_run": "false"}, headers=_bearer("editor"))
    assert r.status_code == 403
    r = client.post("/api/v1/import/run", files=files, data={"params": "[1]", "dry_run": "true"}, headers=_bearer("editor"))
    assert r.status_code == 400
