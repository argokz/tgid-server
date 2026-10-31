"""Водопровод в ТГИД (database/water.py): размещение схемы, оценка давления, связь с движком, права."""

import asyncio
import math

import httpx
import pytest
from fastapi.testclient import TestClient

from auth import create_access_token, invalidate_user_status
from database import water


def test_schematic_placement_fits_extent_by_node_count():
    nodes = [{"x": 8.0, "y": 0.0}, {"x": 44.86, "y": 31.06}] + [{"x": 20.0, "y": 10.0}] * 95  # как Net3: 97 узлов
    p = water.schematic_placement(nodes, (43.3153, 76.9409))
    assert p["mode"] == "schematic" and p["extent_m"] == round(150 * math.sqrt(97))
    lon, lat = water.to_lonlat(p["center_x"], p["center_y"], p)
    assert (lat, lon) == (43.3153, 76.9409)  # центр схемы — центр города
    e_lon, _ = water.to_lonlat(44.86, p["center_y"], p)
    half_m = (e_lon - 76.9409) * 111_320 * math.cos(math.radians(43.3153))
    assert half_m == pytest.approx(p["extent_m"] / 2, rel=0.01)
    big = water.schematic_placement([{"x": i, "y": i} for i in range(20_000)], (43.3, 76.9))
    assert big["extent_m"] == 15000  # не больше 15 км
    with pytest.raises(water.WaterError):
        water.schematic_placement([{"x": None, "y": None}], (43.3, 76.9))


def test_node_status():
    assert [water.node_status(v) for v in (None, -0.6, 4.0, 10.0, 55.0)] == ["no_data", "negative", "low", "ok", "ok"]


def test_engine_errors_are_reported(monkeypatch):
    def handler(request):
        if request.url.path == "/parse":
            return httpx.Response(422, json={"detail": "Модель EPANET не читается: [JUNCTIONS] …"})
        raise httpx.ConnectError("refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(water.WaterError) as e:
        asyncio.run(water.engine_call("POST", "/parse", {"inp": "x"}, client=client))
    assert e.value.status == 422 and "не читается" in e.value.message
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(water.WaterError) as e:
        asyncio.run(water.engine_call("GET", "/health", client=client))
    assert e.value.status == 503 and "недоступен" in e.value.message


def test_endpoints_permissions(monkeypatch):
    import main
    from routers import water as router

    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    invalidate_user_status()

    async def down(*a, **kw):
        raise water.WaterError(503, "Расчётный движок водопровода недоступен")

    class _Acquire:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(router.water, "engine_call", down)
    monkeypatch.setattr(router, "acquire_conn", lambda: _Acquire())
    client = TestClient(main.app)
    auth = lambda role: {"Authorization": f"Bearer {create_access_token(username=role, role=role)}"}  # noqa: E731
    r = client.get("/api/v1/water/status", headers=auth("viewer"))
    assert r.status_code == 200 and r.json()["available"] is False
    assert client.post("/api/v1/water/models", json={"library": "Net3"}, headers=auth("viewer")).status_code == 403
    assert client.post("/api/v1/water/models", json={"library": "Net3"}, headers=auth("admin")).status_code == 503
    assert client.post("/api/v1/water/models/1/runs", json={}, headers=auth("viewer")).status_code == 403
    invalidate_user_status()
