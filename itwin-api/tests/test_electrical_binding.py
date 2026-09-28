"""Этап 10: электросеть — сверка привязки и привязка по правилам gid6 GeoFile.cpp (без живой БД)."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import electrical_binding as eb  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _line(**kw):
    row = {"object_type": "line", "id": 1, "name": "ЛЭП-1", "has_geometry": True,
           "source_id": None, "source_exists": False, "source_name": None, "source_distance": None,
           "receiver_id": None, "receiver_exists": False, "receiver_name": None, "receiver_distance": None,
           "candidate_source_id": None, "candidate_source_distance": None,
           "candidate_receiver_id": None, "candidate_receiver_distance": None,
           "longitude": 71.4, "latitude": 51.1}
    row.update(kw)
    return row


def _point(**kw):
    row = {"object_type": "coupling", "id": 5, "name": "М-5", "has_geometry": True, "geometry_type": "POINT",
           "snap_type": True, "line_id": None, "line_exists": False, "line_name": None, "line_distance": None,
           "nearest_line_id": None, "nearest_line_distance": None, "search_tolerance": 8.0,
           "longitude": 71.4, "latitude": 51.1}
    row.update(kw)
    return row


class FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    """ЛЭП 1 без источника (у конца источник 11), муфта 5 без ЛЭП в 2 м от ЛЭП 1."""

    def __init__(self):
        self.lines = [_line(candidate_source_id=11, candidate_source_distance=0.5,
                            receiver_id=21, receiver_exists=True, receiver_distance=0.0, candidate_receiver_id=21,
                            candidate_receiver_distance=0.0)]
        self.points = [_point(nearest_line_id=1, nearest_line_distance=2.0)]
        self.executed: list[tuple] = []

    def transaction(self, **kw):
        return FakeTx()

    async def fetch(self, sql, *args):
        if "WITH line AS" in sql:
            return self.lines
        if "WITH obj AS" in sql:
            return self.points
        raise AssertionError(sql)

    async def fetchrow(self, sql, *args):
        self.executed.append((sql, args))
        return {"new_wkt": "POINT(1 0)", "old_wkt": "POINT(1 2)"}

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return "UPDATE 1"


@pytest.fixture(autouse=True)
def _tables(monkeypatch):
    async def fake_tables(conn):
        return {name: f'"{name}"' for name in eb.ALLOWED_TABLES}

    monkeypatch.setattr(eb, "_tables", fake_tables)


def test_classify_line_matches_desktop_rules():
    assert eb.classify_line(_line(has_geometry=False), 8) == ["line_no_geometry"]
    assert eb.classify_line(_line(), 8) == ["line_no_source", "line_no_receiver"]
    row = _line(source_id=3, source_exists=False, receiver_id=4, receiver_exists=True, receiver_distance=9.5)
    assert eb.classify_line(row, 8) == ["line_source_missing", "line_receiver_far"]
    assert eb.classify_line(_line(source_id=3, source_exists=True, source_distance=0.2, receiver_id=4,
                                  receiver_exists=True, receiver_distance=7.9), 8) == []


def test_classify_point_and_candidate():
    assert eb.classify_point(_point(has_geometry=False)) == ["point_no_geometry"]
    assert eb.classify_point(_point()) == ["point_no_line"]
    assert eb.classify_point(_point(line_id=9)) == ["point_line_missing"]
    far = _point(line_id=9, line_exists=True, line_distance=20.0, nearest_line_id=2, nearest_line_distance=1.0)
    assert eb.classify_point(far) == ["point_off_line", "point_closer_other"]
    # на пересечении ЛЭП (равные расстояния) — не «ближе к другой»
    tie = _point(line_id=9, line_exists=True, line_distance=0.0, nearest_line_id=2, nearest_line_distance=0.0)
    assert eb.classify_point(tie) == []
    area = _point(geometry_type="POLYGON", search_tolerance=80.0, nearest_line_id=2, nearest_line_distance=50.0)
    assert eb._point_candidate(area) == (2, 50.0)
    assert eb._point_candidate(_point(nearest_line_id=2, nearest_line_distance=8.5)) == (None, None)


def test_plan_fill_only_empty_unless_overwrite():
    row = _line(source_id=3, source_exists=True, source_distance=100.0, candidate_source_id=11,
                candidate_source_distance=0.5, candidate_receiver_id=21, candidate_receiver_distance=0.0)
    assert eb.plan_line(row, 8, overwrite=False) == [
        {"field": "naimenovanie_priemnika", "old": None, "new": 21, "distance": 0.0}]
    fields = [c["field"] for c in eb.plan_line(row, 8, overwrite=True)]
    assert fields == ["naimenovanie_istochnika", "naimenovanie_priemnika"]
    point = _point(line_id=9, line_exists=True, line_distance=20.0, nearest_line_id=2, nearest_line_distance=1.0)
    assert eb.plan_point(point, overwrite=False, snap=False) == ([], None)
    changes, target = eb.plan_point(point, overwrite=True, snap=True)
    assert target == 2 and [c["field"] for c in changes] == ["naimenovanie_lep", "shape"]
    sleeve = _point(object_type="sleeve", snap_type=False, nearest_line_id=2, nearest_line_distance=1.0)
    assert [c["field"] for c in eb.plan_point(sleeve, overwrite=False, snap=True)[0]] == ["naimenovanie_lep"]


def test_reconcile_and_bind_dry_run_and_apply():
    conn = FakeConn()
    result = asyncio.run(eb.reconcile(conn, 8))
    kinds = {k["kind"]: k["count"] for k in result["kinds"]}
    assert kinds["line_no_source"] == 1 and kinds["point_no_line"] == 1 and result["checked"]["line"] == 1
    assert eb.filter_items(result, kind="point_no_line", object_type=None)[0]["candidate_line_id"] == 1
    with pytest.raises(eb.ElectricalError):
        eb.filter_items(result, kind="bogus", object_type=None)

    plan = asyncio.run(eb.bind(conn, dry_run=True))
    assert plan["counts"] == {"records": 2, "fields": 2, "unresolved": 0} and not conn.executed

    audit = []

    async def audit_row(c, *, operation, table, record_id, old=None, new=None, group=None):
        audit.append((table, record_id, old, new, group))
        return group or "g-1"

    done = asyncio.run(eb.bind(conn, dry_run=False, snap_points=True, audit_row=audit_row))
    assert done["applied"] == 2 and done["change_group_id"] == "g-1"
    assert audit[0] == ("liniya_elektroperedach", 1, {"naimenovanie_istochnika": None},
                        {"naimenovanie_istochnika": 11}, None)
    assert audit[1][0] == "mufta" and audit[1][3] == {"naimenovanie_lep": 1, "shape": "POINT(1 0)"}
    assert audit[1][4] == "g-1"
    assert all("IS NOT DISTINCT FROM" in sql for sql, _ in conn.executed if sql.startswith("UPDATE") and "SET \"" in sql)

    with pytest.raises(eb.ElectricalError) as missing:
        asyncio.run(eb.bind(conn, targets=[("line", 99)]))
    assert missing.value.status == 404


def test_concurrent_change_raises_conflict():
    conn = FakeConn()

    async def stale(sql, *args):
        return "UPDATE 0"

    conn.execute = stale
    with pytest.raises(eb.ElectricalError) as exc:
        asyncio.run(eb.bind(conn, dry_run=False))
    assert exc.value.status == 409


def test_routes_require_editor_and_mutations(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")

    @asynccontextmanager
    async def _acquire():
        yield FakeConn()

    monkeypatch.setattr("routers.electrical_binding.acquire_conn", _acquire)
    client = TestClient(main.app)
    body = {"dry_run": True}
    assert client.post("/api/electrical-network/binding", json=body).status_code == 401
    assert client.post("/api/electrical-network/binding", json=body, headers=_bearer("viewer")).status_code == 403
    h = _bearer("editor")
    r = client.post("/api/electrical-network/binding", json=body, headers=h)
    assert r.status_code == 200 and r.json()["dry_run"] is True and r.json()["counts"]["records"] == 2
    r = client.post("/api/electrical-network/binding", json={"items": [{"object_type": "pipe", "id": 1}]}, headers=h)
    assert r.status_code == 422
    r = client.get("/api/electrical-network/reconciliation", params={"kind": "line_no_source"}, headers=h)
    assert r.status_code == 200 and r.json()["total"] == 1
    assert client.get("/api/electrical-network/reconciliation", params={"kind": "x"}, headers=h).status_code == 422
    r = client.get("/api/electrical-network/reconciliation/report.xlsx", headers=h)
    assert r.status_code == 200 and r.content[:2] == b"PK"
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.post("/api/electrical-network/binding", json={"dry_run": False}, headers=h).status_code == 503
    assert client.post("/api/electrical-network/binding", json=body, headers=h).status_code == 200
