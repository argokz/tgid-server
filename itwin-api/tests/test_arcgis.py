"""FeatureServer по GeoServices REST (database/arcgis_features.py, routers/arcgis.py)."""

import asyncio
import json

import jwt
import pytest

from auth import create_access_token, invalidate_user_status
from database import arcgis_features as af

SECRET = "test-secret-test-secret-test-secret-123"


def test_spatial_reference_and_envelope():
    assert af.srid_of(None) == 4326 and af.srid_of("4326") == 4326
    assert af.srid_of("102100") == 3857 and af.srid_of('{"wkid":102100,"latestWkid":3857}') == 3857
    assert af.srid_of({"wkid": 3857}) == 3857
    with pytest.raises(af.ArcgisError, match="не поддерживается"):
        af.srid_of("32642")
    assert af.parse_envelope('{"xmin":71.5,"ymin":51.2,"xmax":71.4,"ymax":51.1}') == (71.4, 51.1, 71.5, 51.2)
    assert af.parse_envelope("71.4,51.1,71.5,51.2") == (71.4, 51.1, 71.5, 51.2)
    assert af.parse_envelope("") is None
    with pytest.raises(af.ArcgisError):
        af.parse_envelope("1,2,3")


def test_where_is_parsed_not_injected():
    key, frag = "lo.id", "lo.fileid"
    assert af.parse_where("1=1", "pipes", key, frag) == ([], [])
    assert af.parse_where(" ", "pipes", key, frag) == ([], [])
    assert af.parse_where("OBJECTID IN (5, 7,9)", "pipes", key, frag) == (["lo.id = ANY({}::bigint[])"], [[5, 7, 9]])
    assert af.parse_where("fileid = 74", "pipes", key, frag) == (["lo.fileid = {}"], [74])
    assert af.parse_where("diameter_mm = 108.5", "pipes", key, frag) == (["h.diametercondit = {}"], [108.5])
    for bad in ("1=1; DROP TABLE linesobj", "name = 'x'", "nope = 1", "diameter_mm > 100", "1=1 OR 1=1"):
        with pytest.raises(af.ArcgisError):
            af.parse_where(bad, "pipes", key, frag)


def test_build_query_fields_limits_and_geometry_filter():
    q = af.build_query("pipes", {"where": "1=1", "outFields": "name,DIAMETER_MM", "resultRecordCount": "99999",
                                 "resultOffset": "20", "geometry": '{"xmin":8580000,"ymin":5340000,"xmax":8590000,"ymax":5350000,'
                                 '"spatialReference":{"wkid":102100}}', "outSR": "102100", "objectIds": "1,2"})
    assert q.out_fields == ["OBJECTID", "name", "diameter_mm"]
    assert q.limit == af.MAX_RECORD_COUNT and q.offset == 20 and q.out_srid == 3857
    assert q.where_sql[0].startswith("lo.id = ANY") and "ST_MakeEnvelope({}, {}, {}, {}, 3857)" in q.where_sql[1]
    assert q.params == [[1, 2], 8580000.0, 5340000.0, 8590000.0, 5350000.0]
    all_fields = af.build_query("nodes", {})
    assert all_fields.out_fields == [f["name"] for f in af.fields("nodes")] and all_fields.return_geometry
    assert af.build_query("nodes", {"returnGeometry": "false"}).return_geometry is False


def test_fields_info_and_esri_geometry():
    f = {x["name"]: x for x in af.fields("pipes")}
    assert f["OBJECTID"]["type"] == "esriFieldTypeOID" and f["diameter_mm"]["type"] == "esriFieldTypeDouble"
    assert f["name"]["type"] == "esriFieldTypeString" and f["name"]["length"] == 255
    assert f["node_start"]["alias"] == "Узел начала"
    assert af.esri_geometry({"type": "Point", "coordinates": [1, 2]}) == {"x": 1, "y": 2}
    assert af.esri_geometry({"type": "LineString", "coordinates": [[1, 2], [3, 4]]}) == {"paths": [[[1, 2], [3, 4]]]}
    assert af.esri_geometry({"type": "MultiLineString", "coordinates": [[[1, 2], [3, 4]]]}) == {"paths": [[[1, 2], [3, 4]]]}
    assert af.esri_geometry(None) is None
    info = af.layer_info("valves", [71.0, 51.0, 72.0, 52.0])
    assert info["id"] == 4 and info["geometryType"] == "esriGeometryPoint" and info["capabilities"] == "Query"
    service = af.service_info([71.0, 51.0, 72.0, 52.0], "x")
    assert [l["id"] for l in service["layers"]] == [0, 1, 2, 3, 4] and service["layers"][0]["geometryType"] == "esriGeometryPolyline"
    with pytest.raises(af.ArcgisError):
        af.collection_of(9)


class FakeConn:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""
        self.args = ()

    async def fetch(self, sql, *args):
        self.sql, self.args = sql, args
        return self.rows

    async def fetchval(self, sql, *args):
        self.sql, self.args = sql, args
        return 42


def _row(fid, name=" ТК-1 "):
    return {"fid": fid, "fileid": 74, "geometry": json.dumps({"type": "Point", "coordinates": [71.4, 51.1]}),
            "name": name, "node_type": 3}


def test_features_sql_paging_and_output():
    q = af.build_query("nodes", {"where": "fileid = 74", "resultRecordCount": "2", "outFields": "name"})
    conn = FakeConn([_row(1), _row(2), _row(3)])
    rows, more = asyncio.run(af.features(conn, "nodes", q))
    assert more and len(rows) == 2  # третья строка — признак «есть ещё»
    assert "n.fileid = $1" in conn.sql and "LIMIT $2 OFFSET $3" in conn.sql and conn.args == (74, 3, 0)
    assert rows[0]["attributes"] == {"OBJECTID": 1, "name": "ТК-1"}
    esri = af.to_esri_json("nodes", q, rows, more)
    assert esri["exceededTransferLimit"] and esri["features"][0]["geometry"] == {"x": 71.4, "y": 51.1}
    assert [f["name"] for f in esri["fields"]] == ["OBJECTID", "name"] and esri["spatialReference"]["wkid"] == 4326
    gj = af.to_geojson(rows, more)
    assert gj["features"][0]["id"] == 1 and gj["features"][0]["geometry"]["type"] == "Point"
    assert asyncio.run(af.count(FakeConn([]), "nodes", q)) == 42


@pytest.fixture
def client(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from routers import arcgis as router

    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield FakeConn([_row(1)])

    async def extent():
        return [71.0, 51.0, 72.0, 52.0]

    async def fp(sub):
        return "fp-1" if sub.isdigit() else None

    async def write(**kwargs):
        pass

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(router, "_network_extent", extent)
    monkeypatch.setattr(router, "_password_fingerprint", fp)
    monkeypatch.setattr(router.activity, "write", write)
    yield TestClient(main.app)
    invalidate_user_status()


def test_token_scope_and_query(client, monkeypatch):
    from routers import arcgis as router

    session = create_access_token(username="ivan", role="viewer", subject="7")
    r = client.post("/api/v1/arcgis/token", headers={"Authorization": f"Bearer {session}"})
    token = r.json()["token"]
    payload = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert payload["scope"] == "arcgis" and payload["pwf"] == "fp-1" and r.json()["service_url"].endswith("/FeatureServer")

    base = "/api/arcgis/rest/services/TGID/FeatureServer"
    assert client.get(base, params={"f": "json"}).json()["error"]["code"] == 499  # без ключа
    service = client.get(base, params={"f": "json", "token": token}).json()
    assert len(service["layers"]) == 5
    q = client.get(f"{base}/1/query", params={"where": "1=1", "outFields": "*", "f": "json", "token": token}).json()
    assert q["features"][0]["attributes"]["OBJECTID"] == 1 and q["geometryType"] == "esriGeometryPoint"
    posted = client.post(f"{base}/1/query", data={"where": "1=1", "f": "geojson", "token": token}).json()
    assert posted["type"] == "FeatureCollection"
    bad = client.get(f"{base}/1/query", params={"where": "name = 'x'", "token": token})
    assert bad.status_code == 200 and bad.json()["error"]["code"] == 400  # ошибка — в теле, как у ArcGIS Server
    assert client.get(f"{base}/1/query", params={"token": "garbage"}).json()["error"]["code"] == 498
    # ключ ArcGIS — только здесь: остальное API его не принимает
    assert client.get("/api/v1/kpi/dashboard", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    async def changed(sub):
        return "fp-2"

    monkeypatch.setattr(router, "_password_fingerprint", changed)
    gone = client.get(base, params={"token": token}).json()
    assert gone["error"]["code"] == 498 and "Пароль сменён" in gone["error"]["message"]
    assert "error" not in client.get(base, params={"token": session}).json()  # токен сессии — без отпечатка
    assert client.get("/api/arcgis/rest/info").json()["authInfo"]["isTokenBasedSecurity"] is False
