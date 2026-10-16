"""GET /api/v1/map/data-version: версия данных для сброса кеша тайлов."""

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from routers import core


class _Conn:
    def __init__(self, values):
        self.values = list(values)
        self.calls = 0

    async def fetchval(self, sql, *args):
        assert "pg_stat_user_tables" in sql
        self.calls += 1
        return self.values.pop(0)


def _client(monkeypatch, conn):
    import main

    monkeypatch.setenv("AUTH_DISABLED", "true")  # test_auth выставляет false на весь процесс

    @asynccontextmanager
    async def _acq():
        yield conn

    monkeypatch.setattr(core, "acquire_conn", _acq)
    monkeypatch.setattr(core, "_data_version_cache", {"value": None, "at": 0.0})
    return TestClient(main.app)


def test_data_version_cached_then_refreshed(monkeypatch):
    conn = _Conn([1200, 1305])
    client = _client(monkeypatch, conn)
    assert client.get("/api/v1/map/data-version").json() == {"version": "1200"}
    # в пределах 10 с — из кеша процесса, база не опрашивается
    assert client.get("/api/v1/map/data-version").json() == {"version": "1200"}
    assert conn.calls == 1
    core._data_version_cache["at"] -= core.DATA_VERSION_TTL_S + 1
    assert client.get("/api/v1/map/data-version").json() == {"version": "1305"}
    assert conn.calls == 2
