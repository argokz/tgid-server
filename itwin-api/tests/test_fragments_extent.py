"""QA F25: охват фрагментов для центрирования карты при выборе фрагмента."""

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from routers import core


class _Conn:
    def __init__(self, row):
        self.row = row
        self.args = None

    async def fetchrow(self, sql, *args):
        self.args = args
        return self.row


def _client(monkeypatch, conn):
    import main

    @asynccontextmanager
    async def _acq():
        yield conn

    monkeypatch.setattr(core, "acquire_conn", _acq)
    return TestClient(main.app)


def test_extent_returns_bbox(monkeypatch):
    conn = _Conn({"min_lng": 76.8, "min_lat": 43.2, "max_lng": 77.0, "max_lat": 43.3})
    r = _client(monkeypatch, conn).get("/api/v1/fragments/extent", params={"fragments": "75,74"})
    assert r.status_code == 200
    assert r.json() == {"fragments": [74, 75], "bbox": [76.8, 43.2, 77.0, 43.3]}
    assert conn.args == ([74, 75],)


def test_extent_empty_and_required(monkeypatch):
    client = _client(monkeypatch, _Conn({"min_lng": None, "min_lat": None, "max_lng": None, "max_lat": None}))
    assert client.get("/api/v1/fragments/extent", params={"fragment_id": 5}).json()["bbox"] is None
    assert client.get("/api/v1/fragments/extent").status_code == 422
