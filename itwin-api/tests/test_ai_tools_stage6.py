"""Этап 6: качество данных (database/data_quality.py), поиск фразой, сопоставление колонок импорта
(ai/tools.py), эндпоинты. Без БД и сети."""

from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai import tools  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import data_quality as dq  # noqa: E402
from routers import ai as ai_router  # noqa: E402
from routers import data_quality as dq_router  # noqa: E402


class FakeConn:
    """Подменяет SQL: COUNT → число, список → строки; запоминает запросы."""

    def __init__(self, count=3, rows=None, consumers=None):
        self.count, self.rows, self.consumers, self.sql = count, rows or [], consumers, []

    async def fetchval(self, sql, *args):
        self.sql.append(sql)
        return self.count

    async def fetchrow(self, sql, *args):
        self.sql.append(sql)
        return {"n": self.count, "s": 12.5}

    async def fetch(self, sql, *args):
        self.sql.append((sql, args))
        return self.rows


def test_rules_are_well_formed():
    specs = dq.rule_specs()
    assert len(specs) == len(dq.RULES) >= 8
    for key, rule in dq.RULES.items():
        assert rule["severity"] in ("error", "warning", "info") and rule["fix"] in dq.FIX_LABELS
        assert "$1" in rule["sql"] and rule["sql"].lstrip().upper().startswith("FROM")
    assert "50" in dq.RULES["consumer_load_outlier"]["label"]
    assert ", 1400)" in dq.RULES["diameter_nonstandard"]["sql"]


def test_summary_counts_and_sums():
    conn = FakeConn(count=4)
    out = asyncio.run(dq.summary(conn, fragment_id=74))
    assert out["fragment_id"] == 74 and len(out["items"]) == len(dq.RULES)
    by = {i["rule"]: i for i in out["items"]}
    assert by["line_node_fragment_mismatch"]["count"] == 4 and by["line_node_fragment_mismatch"]["sum_gcal_h"] is None
    assert by["contract_load_without_source"]["sum_gcal_h"] == 12.5
    assert out["total_errors"] == 8 and out["total_warnings"] == 16


def test_summary_survives_missing_table():
    class Broken(FakeConn):
        async def fetchval(self, sql, *args):
            raise RuntimeError("UndefinedTable")

    out = asyncio.run(dq.summary(Broken()))
    assert all(i["count"] is None and i["error"] == "RuntimeError" for i in out["items"] if not dq.RULES[i["rule"]].get("sum"))


def test_issues_and_geojson():
    rows = [{"id": 1, "name": "ТК-1", "fragment_id": 74, "value": 0, "longitude": 76.9, "latitude": 43.2},
            {"id": 2, "name": "ТК-2", "fragment_id": 74, "value": 1, "longitude": None, "latitude": None}]
    conn = FakeConn(count=2, rows=rows)
    out = asyncio.run(dq.issues(conn, "node_low_elevation", fragment_id=74, limit=10))
    assert out["total"] == 2 and out["items"][0]["name"] == "ТК-1" and conn.sql[-1][1] == (74, 10, 0)
    gj = asyncio.run(dq.geojson(conn, "node_low_elevation"))
    assert len(gj["features"]) == 1 and gj["features"][0]["properties"]["rule"] == "node_low_elevation"
    with pytest.raises(KeyError):
        asyncio.run(dq.issues(conn, "no_such_rule"))


def test_execute_search_kinds(monkeypatch):
    conn = FakeConn(rows=[{"id": 5, "name": "3-47", "fragment_id": 74}])
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="node", text=" 3-47 ", fragment_id=74)))
    assert out["items"][0]["name"] == "3-47" and conn.sql[-1][1] == ("3-47", 74, tools.MAX_RESULTS)
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="line", text="3-47", text2="3-49")))
    assert conn.sql[-1][1] == ("3-47", "3-49", None, tools.MAX_RESULTS)
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="tool", tool_key="wearIndex", scope_text="фр 74")))
    assert out["open_tool"] == {"key": "wearIndex", "scope": {"text": "фр 74", "fragment_id": None}} and out["items"] == []
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="tool", tool_key="rm -rf")))
    assert out["open_tool"] is None

    async def fake_diag(conn_, **kw):
        return {"items": [{"id": 1}], "total": 1, "kw": kw}

    monkeypatch.setattr(tools, "get_consumer_load_diagnostics", fake_diag)
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="consumer", diagnostic="zero_load", fragment_id=74)))
    assert out["total"] == 1 and out["open_tool"]["key"] == "consumerLoad" and out["open_tool"]["scope"]["diagnostic"] == "zero_load"
    out = asyncio.run(tools.execute_search(conn, tools.SearchQuery(kind="unknown", note="уточните")))
    assert out["items"] == [] and out["open_tool"] is None


def test_search_uses_visible_fragment_and_filters_tool(monkeypatch):
    calls = []

    async def fake_ask(**kw):
        calls.append(kw)
        return tools.SearchQuery(kind="tool", tool_key="hack", confidence=0.9)

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    out = asyncio.run(tools.search(FakeConn(), text="открой что-то", fragment_ids=[74]))
    assert out["query"]["tool_key"] is None and out["query"]["fragment_id"] == 74
    assert calls[0]["effort"] == "low" and "Видимые фрагменты" in calls[0]["user"]


def test_import_mapping_merges_model_and_heuristic(monkeypatch):
    async def fake_ask(**kw):
        return tools.ImportMapping(matches=[
            tools.ColumnMatch(target="code", column="Номер", confidence=0.9),
            tools.ColumnMatch(target="elevation", column="Z", confidence=0.6),
            tools.ColumnMatch(target="name", column="Номер", confidence=0.4),  # колонка уже занята
            tools.ColumnMatch(target="bogus", column="X", confidence=1.0),      # нет такого поля
        ], note="ок")

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    out = asyncio.run(tools.suggest_import_mapping(mode="nodes", columns=["Номер", "X", "Y", "Z"],
                                                   samples=[["ТК-1", 76.9, 43.2, 800]], has_geometry=False))
    assert out["mapping"] == {"code": "Номер", "elevation": "Z", "x": "X", "y": "Y"}
    assert out["confidence"]["code"] == 0.9 and out["confidence"]["x"] == 1.0 and out["heuristic"]["x"] == "X"
    with pytest.raises(ai_client.AiError):
        asyncio.run(tools.suggest_import_mapping(mode="bad", columns=["a"], samples=[], has_geometry=False))


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='u', role=role)}"}


def test_endpoints(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    conn = FakeConn(count=1, rows=[{"id": 1, "name": "ТК-1", "fragment_id": 74, "longitude": 76.9, "latitude": 43.2}])

    class _Acquire:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(dq_router, "acquire_conn", lambda: _Acquire())
    monkeypatch.setattr(ai_router, "acquire_conn", lambda: _Acquire())

    async def fake_ask(**kw):
        if kw["output_format"] is tools.SearchQuery:
            return tools.SearchQuery(kind="node", text="ТК-1", confidence=0.8)
        if kw["output_format"] is tools.DataQualityAdvice:
            return tools.DataQualityAdvice(summary="ок", rules=[tools.RuleAdvice(
                rule="dangling_node", cause="c", impact="i", fix_tool="topology", priority=1),
                tools.RuleAdvice(rule="fake", cause="c", impact="i", fix_tool="card", priority=3)])
        return tools.ImportMapping()

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    client = TestClient(main.app)
    assert len(client.get("/api/v1/data-quality/rules", headers=_auth("viewer")).json()["items"]) == len(dq.RULES)
    assert client.get("/api/v1/data-quality/summary", headers=_auth("viewer")).json()["total_errors"] == 2
    assert client.get("/api/v1/data-quality/issues", params={"rule": "dangling_node"}, headers=_auth("viewer")).json()["total"] == 1
    assert client.get("/api/v1/data-quality/issues", params={"rule": "x"}, headers=_auth("viewer")).status_code == 404
    assert len(client.get("/api/v1/data-quality/geojson", params={"rule": "dangling_node"}, headers=_auth("viewer")).json()["features"]) == 1
    r = client.post("/api/v1/ai/search", json={"text": "камера ТК-1"}, headers=_auth())
    assert r.status_code == 200 and r.json()["items"][0]["name"] == "ТК-1"
    r = client.post("/api/v1/ai/data-quality/explain", json={}, headers=_auth())
    assert r.status_code == 200 and [a["rule"] for a in r.json()["advice"]["rules"]] == ["dangling_node"]
    r = client.post("/api/v1/ai/import/suggest-mapping", json={"mode": "nodes", "columns": ["X", "Y"]}, headers=_auth("editor"))
    assert r.status_code == 200 and r.json()["mapping"] == {"x": "X", "y": "Y"}
    assert client.post("/api/v1/ai/import/suggest-mapping", json={"mode": "nodes", "columns": ["X"]}, headers=_auth()).status_code == 403
    assert client.post("/api/v1/ai/search", json={"text": "x"}, headers=_auth()).status_code == 422
