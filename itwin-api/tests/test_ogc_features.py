"""OGC API — Features (database/ogc_features.py, routers/ogc.py): фильтры, страницы, ответы по стандарту."""

from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

import database.ogc_features as ogc
import main
import routers.ogc as ogc_router


def test_parse_bbox():
    assert ogc.parse_bbox(None) is None
    assert ogc.parse_bbox("76.9,43.2,77.0,43.3") == (76.9, 43.2, 77.0, 43.3)
    for bad in ("1,2,3", "a,b,c,d", "77,43,76,44", "0,-91,1,1"):
        with pytest.raises(ValueError):
            ogc.parse_bbox(bad)


def test_query_filters_and_paging():
    sql, params = ogc._query("pipes", fid=None, bbox=(76.9, 43.2, 77.0, 43.3), fileid=74, limit=50, offset=100)
    assert params == [74, 76.9, 43.2, 77.0, 43.3, 50, 100]
    assert "lo.fileid = $1" in sql and "ST_MakeEnvelope($2, $3, $4, $5, 4326)" in sql
    assert sql.endswith("LIMIT $6 OFFSET $7")
    sql, params = ogc._query("valves", fid=7, bbox=None, fileid=None, limit=1, offset=0)
    assert "d.id = $1" in sql and params == [7, 1, 0]


def test_every_collection_has_keys():
    assert set(ogc.COLLECTIONS) == set(ogc._KEYS)


class FakeConn:
    async def fetchrow(self, sql, *args):  # охват сети
        return {"x1": 76.8, "y1": 43.1, "x2": 77.1, "y2": 43.4}


def _client(monkeypatch, items=None, item=None):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setattr(ogc_router, "_extent", {})

    @asynccontextmanager
    async def acquire():
        yield FakeConn()

    async def fake_items(conn, cid, *, bbox=None, fileid=None, limit=100, offset=0):
        return (items or [])[:limit]

    async def fake_item(conn, cid, fid):
        return item

    monkeypatch.setattr(ogc_router, "acquire_conn", acquire)
    monkeypatch.setattr(ogc_router, "get_items", fake_items)
    monkeypatch.setattr(ogc_router, "get_item", fake_item)
    return TestClient(main.app)


def _feature(i):
    return {"type": "Feature", "id": i, "geometry": {"type": "Point", "coordinates": [76.9, 43.2]}, "properties": {}}


def test_landing_conformance_collections(monkeypatch):
    client = _client(monkeypatch)
    landing = client.get("/api/ogc").json()
    assert {link["rel"] for link in landing["links"]} >= {"self", "conformance", "data", "service-desc"}
    assert "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core" in client.get("/api/ogc/conformance").json()["conformsTo"]
    cols = client.get("/api/ogc/collections").json()["collections"]
    assert [c["id"] for c in cols] == list(ogc.COLLECTIONS)
    assert cols[0]["extent"]["spatial"]["bbox"] == [[76.8, 43.1, 77.1, 43.4]]
    assert client.get("/api/ogc/collections/pipes").json()["id"] == "pipes"
    assert client.get("/api/ogc/collections/unknown").status_code == 404


def test_items_paging_links(monkeypatch):
    client = _client(monkeypatch, items=[_feature(i) for i in range(1, 6)])
    r = client.get("/api/ogc/collections/nodes/items", params={"limit": 2, "offset": 4, "fileid": 74})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/geo+json")
    body = r.json()
    assert body["type"] == "FeatureCollection" and body["numberReturned"] == 2
    rels = {link["rel"]: link["href"] for link in body["links"]}
    assert "offset=6" in rels["next"] and "fileid=74" in rels["next"]   # полная страница — есть следующая
    assert "offset=2" in rels["prev"]
    last = client.get("/api/ogc/collections/nodes/items", params={"limit": 10}).json()
    assert "next" not in {link["rel"] for link in last["links"]}       # 5 < 10 — последняя страница
    assert client.get("/api/ogc/collections/nodes/items", params={"bbox": "1,2,3"}).status_code == 400
    assert client.get("/api/ogc/collections/nodes/items", params={"limit": 0}).status_code == 422


def test_single_item(monkeypatch):
    client = _client(monkeypatch, item=_feature(7))
    r = client.get("/api/ogc/collections/pipes/items/7")
    assert r.status_code == 200 and r.json()["id"] == 7
    assert any(link["rel"] == "collection" for link in r.json()["links"])
    assert _client(monkeypatch, item=None).get("/api/ogc/collections/pipes/items/7").status_code == 404


def test_ogc_requires_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert TestClient(main.app).get("/api/ogc/collections").status_code == 401
