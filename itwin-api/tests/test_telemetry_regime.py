"""Расчёт по фактическому режиму: факт в узлах заданного напора, -zn_fakt для sety, запуск."""

import argparse
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from auth import create_access_token, invalidate_user_status
from database import telemetry_regime as rg
from worker import validate_sety_params

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def _row(code, kind, pipe, unit, value, *, node=535303, age_min=1):
    return {"id": hash(code) % 1000, "code": code, "kind": kind, "pipe": pipe, "unit": unit, "node_id": node,
            "fileid": 74, "node_name": "ТЭЦ-1", "set_p1": 120.0, "set_p2": 54.0, "avg_value": value,
            "last_ts": NOW - timedelta(minutes=age_min)}


def test_group_nodes_converts_units_and_skips_silent():
    nodes = rg.group_nodes([
        _row("P1", "pressure", "supply", "kgf_cm2", 11.6),
        _row("P2", "pressure", "return", "bar", 5.3),
        _row("T1", "temperature", "supply", "c", 128.44),
        _row("P1b", "pressure", "supply", "kgf_cm2", 99.0),  # второй манометр подачи — первый важнее
        _row("X", "pressure", "supply", "kgf_cm2", 7.0, node=2, age_min=10_000),  # молчит
    ], NOW)
    tec, silent = nodes
    assert tec["fact"] == {"p1": 116.0, "p2": 54.04, "t1": 128.44}
    assert tec["sensors"] == ["P1", "P2", "T1", "P1b"] and tec["set"] == {"p1": 120.0, "p2": 54.0}
    assert silent["fact"] == {"p1": None, "p2": None, "t1": None} and silent["silent"] == ["X"]


@pytest.mark.parametrize("fact, problem", [
    ({"p1": 116.0, "p2": 54.0, "t1": 128.0}, None),
    ({"p1": 116.0, "p2": None, "t1": None}, None),
    ({"p1": None, "p2": None, "t1": None}, "нет свежих"),
    ({"p1": 50.0, "p2": 54.0, "t1": None}, "перепутаны"),
    ({"p1": 12000.0, "p2": 54.0, "t1": None}, "единицы"),
    ({"p1": 116.0, "p2": 54.0, "t1": -3.0}, "температура"),
])
def test_node_problem(fact, problem):
    got = rg.node_problem(fact)
    assert (got is None) if problem is None else (problem in got)


def test_changes_over_threshold_only():
    node = {"fact": {"p1": 116.5, "p2": 55.0, "t1": 128.0}, "model": {"p1": 120.0, "p2": 54.0, "t1": 132.0}}
    assert rg.changes(node) == ["напор подачи 120 → 116,5 м", "температура подачи 132 → 128 °C"]
    assert rg.changes({"fact": node["fact"], "model": None}) == []


def test_zn_spec_passes_worker_whitelist():
    nodes = [{"node_id": 535303, "fact": {"p1": 116.004, "p2": 54.0, "t1": 128.44}, "problem": None},
             {"node_id": 7, "fact": {"p1": None, "p2": 30.5, "t1": None}, "problem": None},
             {"node_id": 8, "fact": {"p1": 1.0, "p2": 9.0, "t1": None}, "problem": "перепутаны"}]
    spec = rg.zn_spec(nodes)
    assert spec == "535303:116:54:128.4;7::30.5:"
    assert validate_sety_params(f"-Tn -25 -zn_fakt {spec} -fileID 74")


@pytest.mark.parametrize("value", ["535303:116:54", "x:1:2:3", "1:-5:2:3", "1:1:2:3;", "1:1:2:3 -dross_yes"])
def test_worker_rejects_bad_zn_fakt(value):
    with pytest.raises(ValueError):
        validate_sety_params(f'-zn_fakt "{value}"')


def test_sety_parses_zn_fakt():
    from sety.config import parse_zn_fakt

    assert parse_zn_fakt("535303:116:54:128.4;7::30.5:") == {535303: (116.0, 54.0, 128.4), 7: (None, 30.5, None)}
    with pytest.raises(argparse.ArgumentTypeError):
        parse_zn_fakt("1:2:3")


def test_by_fact_flag():
    assert rg._by_fact('{"Tn": -25, "zn_fakt": {"535303": [116, 54, null]}}') is True
    assert rg._by_fact('{"Tn": -25, "zn_fakt": {}}') is False
    assert rg._by_fact(None) is False and rg._by_fact("{bad") is False


def test_run_requires_calc_permission_and_dispatches(monkeypatch):
    import main
    from routers import telemetry as router

    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-123")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    invalidate_user_status()
    prepared = {"fileid": 74, "mode": "plan", "tn": -25.0, "params": "-Tn -25 -zn_fakt 1:2:1:", "zn_fakt": "1:2:1:",
                "nodes": []}
    calls = {}

    class _Conn:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    async def prepare(conn, fileid, *, tn, mode, user):
        calls["prepare"] = (fileid, tn, mode, user)
        return prepared

    async def audit(**kw):
        calls["audit"] = kw

    monkeypatch.setattr(router, "acquire_conn", lambda: _Conn())
    monkeypatch.setattr(router.regime, "prepare", prepare)
    monkeypatch.setattr(router.regime, "dispatch", lambda p: {"task_id": "t1", "request_id": "r1"})
    monkeypatch.setattr(router, "write_audit_log", audit)
    client = TestClient(main.app)
    viewer = create_access_token(username="petr", role="viewer", subject="petr")
    r = client.post("/api/v1/telemetry/regime/run", json={"fileid": 74},
                    headers={"Authorization": f"Bearer {viewer}"})
    assert r.status_code == 403
    editor = create_access_token(username="ivan", role="editor", subject="ivan")
    r = client.post("/api/v1/telemetry/regime/run", json={"fileid": 74, "tn": -10},
                    headers={"Authorization": f"Bearer {editor}"})
    assert r.status_code == 200, r.text
    assert r.json()["task_id"] == "t1" and calls["prepare"] == (74, -10.0, "plan", "ivan")
    assert calls["audit"]["new_data"]["regime"] == "fact" and calls["audit"]["new_data"]["fileid"] == 74
    invalidate_user_status()
