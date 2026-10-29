"""Барьеры по условию (network_trace.stop_barriers) и именованные настройки трассировки (trace_configs)."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from database import trace_configs as tc
from database.network_trace import run_trace, stop_barriers
from tests.test_network_trace import _net


class _Conn:
    """fetch по SQL барьеров: насосные — узел 3, узлы заданного напора — 5, источники — 1."""

    async def fetch(self, sql, *args):
        if "pumpstations" in sql:
            return [{"nodeid": 3}]
        if "setpressnodes" in sql:
            return [{"nodeid": 5}]
        if "heatsources" in sql:
            return [{"nodeid": 1}]
        return []


def _run(**kwargs):
    with patch("database.network_trace.get_outage_network_graph", AsyncMock(return_value=_net())):
        return asyncio.run(run_trace(_Conn(), **kwargs))


def test_stop_barriers_by_kind():
    net = {"dampers_by_line": {20: [1]}, "dampers_by_node": {7: [2]}}
    lines, nodes = asyncio.run(stop_barriers(_Conn(), net, ["valves", "pumpstations"]))
    assert lines == {20} and nodes == {7, 3}
    with pytest.raises(ValueError, match="Неизвестный барьер"):
        asyncio.run(stop_barriers(_Conn(), net, ["walls"]))


def test_connected_stops_at_pumpstation():
    # магистраль 1-2-3, за насосной (узел 3) — кольцо 3-4-5 и тупик 5-6: обход на 3 останавливается
    free = _run(trace_type="connected", start_line_ids=[], start_node_ids=[2])
    stopped = _run(trace_type="connected", start_line_ids=[], start_node_ids=[2], stop_at=["pumpstations"])
    assert 6 in free["node_ids"] and 6 not in stopped["node_ids"]
    assert 3 in stopped["node_ids"] and stopped["stopped_at_node_ids"] == [3]
    # путь к источнику барьеры по условию не меняют
    up = _run(trace_type="upstream", start_line_ids=[], start_node_ids=[6], stop_at=["pumpstations"])
    assert up["node_ids"] == _run(trace_type="upstream", start_line_ids=[], start_node_ids=[6])["node_ids"]


def test_clean_params():
    assert tc.clean_params({"trace_type": "connected", "stop_at": ["setpress", "valves"]}) == {
        "trace_type": "connected", "stop_at": ["valves", "setpress"]}
    for bad in ({"trace_type": "sideways"}, {"trace_type": "connected", "stop_at": ["walls"]},
                {"trace_type": "upstream", "stop_at": ["valves"]}, "connected"):
        with pytest.raises(tc.TraceConfigError) as e:
            tc.clean_params(bad)
        assert e.value.status == 422
    for c in tc.BUILTIN:
        assert tc.clean_params(c["params"]) == c["params"]


class _TableConn:
    def __init__(self, row=None):
        self.row = row

    async def fetchval(self, sql, *args):
        return True

    async def fetchrow(self, sql, *args):
        return self.row

    async def fetch(self, sql, *args):
        return []


def test_get_and_protect_configs():
    assert asyncio.run(tc.get_config(_TableConn(), "builtin:quarter", "u"))["builtin"]
    with pytest.raises(tc.TraceConfigError) as e:
        asyncio.run(tc.get_config(_TableConn(), "builtin:none", "u"))
    assert e.value.status == 404
    with pytest.raises(tc.TraceConfigError) as e:
        asyncio.run(tc.update_config(_TableConn(), "builtin:zone", name="x", params=None, shared=None,
                                     user="u", can_shared=True))
    assert e.value.status == 403
    # чужая общая настройка: без права «Справочники» не правится
    other = _TableConn({"id": 4, "author": "boss", "shared": True})
    with pytest.raises(tc.TraceConfigError) as e:
        asyncio.run(tc.delete_config(other, "4", user="u", can_shared=False))
    assert e.value.status == 403
    # чужая личная — как будто её нет
    private = _TableConn({"id": 4, "author": "boss", "shared": False})
    with pytest.raises(tc.TraceConfigError) as e:
        asyncio.run(tc.delete_config(private, "4", user="u", can_shared=True))
    assert e.value.status == 404


def test_trace_endpoint_uses_config(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from routers import analysis

    monkeypatch.setenv("AUTH_DISABLED", "true")
    seen = {}

    async def fake_run(conn, **kwargs):
        seen.update(kwargs)
        return {"success": True}

    async def fake_get(conn, config_id, user):
        return {"id": config_id, "name": "Квартал", "params": {"trace_type": "connected", "stop_at": ["setpress"]}}

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def acquire():
        yield None

    monkeypatch.setattr(analysis, "acquire_conn", acquire)
    monkeypatch.setattr(analysis, "run_trace", fake_run)
    monkeypatch.setattr(analysis.trace_configs, "get_config", fake_get)
    client = TestClient(main.app)
    r = client.post("/api/analysis/trace", json={"config_id": "7", "start_node_ids": [1], "stop_at": ["valves"]})
    assert r.status_code == 200 and r.json()["config"] == {"id": "7", "name": "Квартал"}
    assert seen["trace_type"] == "connected" and seen["stop_at"] == ["setpress", "valves"]
    assert client.post("/api/analysis/trace", json={"start_node_ids": [1]}).status_code == 422
