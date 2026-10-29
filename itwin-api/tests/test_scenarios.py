"""Сценарии «что если» (database/scenarios.py, routers/scenarios.py): сравнение строк и эндпоинты."""

from contextlib import asynccontextmanager
from decimal import Decimal

from fastapi.testclient import TestClient

import database.scenarios as sc
import main
import routers.scenarios as scenarios_router

COLUMNS = ["nodeid1", "nodeid2", "name", "diametercondit"]
REFS = {"nodeid1": "nodes", "nodeid2": "nodes"}
# основа: узлы 1, 2 (и 3 — тоже во фрагменте); копия: 101, 102, 103; 150 — новый в сценарии
COPY_TO_BASE = {"nodes": {101: 1, 102: 2, 103: 3}}
BASE_IDS = {"nodes": {1, 2, 3}}


def _norm_pair(base_row, copy_row):
    b = sc.normalized_row(base_row, COLUMNS, REFS, BASE_IDS)
    c = sc.normalized_row(copy_row, COLUMNS, REFS, BASE_IDS, COPY_TO_BASE)
    return b, c


def test_fresh_copy_equals_base():
    # перенумерация, NULL ↔ '' и хвостовые пробелы, Decimal ↔ float — не различия
    b, c = _norm_pair({"nodeid1": 1, "nodeid2": 2, "name": None, "diametercondit": Decimal("300.0")},
                      {"nodeid1": 101, "nodeid2": 102, "name": "", "diametercondit": 300.0})
    assert sc.fingerprint(b) == sc.fingerprint(c)
    assert sc.field_changes(b, c) == {}


def test_ref_outside_fragment_dropped_by_export_is_not_a_change():
    # конец участка в другом фрагменте: выгрузка .tgid обнуляет ссылку в копии
    b, c = _norm_pair({"nodeid1": 1, "nodeid2": 999, "name": "a", "diametercondit": 1},
                      {"nodeid1": 101, "nodeid2": None, "name": "a", "diametercondit": 1})
    assert sc.fingerprint(b) == sc.fingerprint(c)


def test_field_changes_in_base_ids():
    b, c = _norm_pair({"nodeid1": 1, "nodeid2": 2, "name": "a", "diametercondit": 300},
                      {"nodeid1": 103, "nodeid2": 150, "name": "a ", "diametercondit": 400})
    assert sc.field_changes(b, c) == {
        "nodeid1": [1, 3],                 # перецеплен на другой узел основы
        "nodeid2": [2, "новый #150"],      # на узел, созданный в сценарии
        "diametercondit": [300, 400],
    }


def test_classify_three_way():
    assert sc.classify("a", "a", "a") is None
    assert sc.classify("a", "b", "a") == "changed"        # правили сценарий
    assert sc.classify("b", "a", "a") == "base_changed"   # правили основу
    assert sc.classify("b", "c", "a") == "conflict"       # правили оба
    assert sc.classify("a", "b", None) == "changed"       # отпечатка нет — считаем правкой сценария


def test_change_kinds_order_puts_scenario_edits_first():
    assert list(sc.CHANGE_KINDS)[:4] == ["changed", "added", "removed", "conflict"]


class FakeConn:
    pass


def _client(monkeypatch, **patches):
    monkeypatch.setenv("AUTH_DISABLED", "true")

    @asynccontextmanager
    async def acquire():
        yield FakeConn()

    monkeypatch.setattr(scenarios_router, "acquire_conn", acquire)
    for name, fn in patches.items():
        monkeypatch.setattr(scenarios_router, name, fn)
    return TestClient(main.app)


def test_list_and_diff_endpoints(monkeypatch):
    async def fake_list(conn, include_archived):
        return [{"id": 1, "name": "Перекладка", "include_archived": include_archived}]

    async def fake_diff(conn, scenario_id, limit):
        return None if scenario_id == 404 else {"scenario_id": scenario_id, "limit": limit, "items": []}

    client = _client(monkeypatch, list_scenarios=fake_list, scenario_diff=fake_diff)
    r = client.get("/api/v1/scenarios", params={"include_archived": "true"})
    assert r.status_code == 200 and r.json()["items"][0]["include_archived"] is True
    r = client.get("/api/v1/scenarios/7/diff", params={"limit": 20})
    assert r.status_code == 200 and r.json() == {"scenario_id": 7, "limit": 20, "items": []}
    assert client.get("/api/v1/scenarios/404/diff").status_code == 404
    assert client.get("/api/v1/scenarios/0/diff").status_code == 422
    assert client.get("/api/v1/scenarios/7/diff", params={"limit": 0}).status_code == 422


def test_create_validation_and_errors(monkeypatch):
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "true")
    calls = []

    async def fake_run(dry_run, body, operation=None, actor=None):
        calls.append((dry_run, operation))
        raise sc.ScenarioError("Фрагмент сам является сценарием")

    client = _client(monkeypatch, _run=fake_run)
    assert client.post("/api/v1/scenarios", json={"base_fileid": 74, "name": "  "}).status_code == 422
    assert client.post("/api/v1/scenarios", json={"base_fileid": 0, "name": "x"}).status_code == 422
    assert client.post("/api/v1/scenarios", json={"base_fileid": 74, "name": "x" * 61}).status_code == 422
    r = client.post("/api/v1/scenarios", json={"base_fileid": 74, "name": "Перекладка"})
    assert r.status_code == 409 and "сценарием" in r.json()["detail"]
    assert calls[-1] == (False, "SCENARIO_CREATE")


def test_status_endpoint(monkeypatch):
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "true")

    async def fake_status(conn, scenario_id, status):
        return None if scenario_id == 404 else {"id": scenario_id, "status": status}

    client = _client(monkeypatch, set_scenario_status=fake_status)
    r = client.post("/api/v1/scenarios/3/status", json={"status": "archived"})
    assert r.status_code == 200 and r.json() == {"id": 3, "status": "archived"}
    assert client.post("/api/v1/scenarios/3/status", json={"status": "merged"}).status_code == 422
    assert client.post("/api/v1/scenarios/404/status", json={"status": "active"}).status_code == 404


def test_scenarios_require_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert TestClient(main.app).get("/api/v1/scenarios").status_code == 401
