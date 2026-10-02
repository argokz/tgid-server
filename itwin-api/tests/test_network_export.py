"""QA F77/F84: DXF фоновой задачей, предупреждение об обрезке выгрузок сети."""

import asyncio
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from database import file_jobs, network_export
from routers import exports_p4


def test_split_limited_and_headers():
    rows, cut = network_export.split_limited([1, 2, 3], 2)
    assert rows == [1, 2] and cut is True
    assert network_export.split_limited([1, 2], 2) == ([1, 2], False)
    h = network_export.export_headers(2, 2, True, expose=("Content-Disposition",))
    assert h["X-Export-Truncated"] == "1" and h["X-Export-Rows"] == "2" and h["X-Export-Limit"] == "2"
    assert h["Access-Control-Expose-Headers"].startswith("Content-Disposition, X-Export-Rows")
    assert network_export.export_suffix([74]) == "_f74" and network_export.export_suffix(None) == ""


def test_network_dxf_is_a_file_job_kind():
    assert "network_dxf" in file_jobs.KINDS
    params = file_jobs.validate_params("network_dxf", {"fragments": [74]})
    assert params["fragments"] == [74] and params["limit"] == 50000


class _Conn:
    def __init__(self, n):
        self.n = n
        self.args = None

    async def fetch(self, sql, *args):
        self.args = args
        return [{"id": i, "name": "", "fileid": 74, "nodeid1": 1, "nodeid2": 2, "length": 1.0, "diameter": 100,
                 "roughness": 0.5, "wkt": "LINESTRING(0 0, 1 1)", "geometry": '{"type":"LineString","coordinates":[[0,0],[1,1]]}'}
                for i in range(min(self.n, args[1]))]


def test_geojson_export_reports_truncation(monkeypatch):
    import main

    conn = _Conn(5)

    @asynccontextmanager
    async def _acq():
        yield conn

    monkeypatch.setattr(exports_p4, "acquire_conn", _acq)
    client = TestClient(main.app)
    r = client.get("/api/export/geojson", params={"fragment_id": 74, "limit": 3})
    assert r.status_code == 200 and len(r.json()["features"]) == 3
    assert conn.args == ([74], 4)
    assert r.headers["X-Export-Truncated"] == "1" and r.headers["X-Export-Rows"] == "3"
    r = client.get("/api/export/geojson-attrs", params={"fragment_id": 74, "limit": 10})
    assert r.headers["X-Export-Truncated"] == "0" and len(r.json()["features"]) == 5


def test_dxf_without_ezdxf_is_503_with_message(monkeypatch):
    def _no_ezdxf(wkts):
        raise network_export.DxfUnavailable("ezdxf is not installed on the API host")

    monkeypatch.setattr(network_export, "render_dxf", _no_ezdxf)
    try:
        asyncio.run(network_export.build_network_dxf(_Conn(1), [74], 10))
    except network_export.DxfUnavailable as e:
        assert "ezdxf" in str(e)
    else:
        raise AssertionError("ожидалось DxfUnavailable")
