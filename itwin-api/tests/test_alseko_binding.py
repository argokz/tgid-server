"""Этап 10: АЛСЕКО — сверка, привязка здания к адресу и зданий к потребителю (без живой БД)."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import alseko_binding as ab  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _run(coro):
    return asyncio.run(coro)


class FakeTx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    """Здание 7 привязано к «ул.А 1», в nagruzki по «ул.Б 2» две записи; узел 50 — «РС1 node_5»."""

    def __init__(self):
        self.building = {"id": 7, "mkr2": None, "street2": "ул.А", "house2": "1", "otop": 0.1, "gvs": 0.0,
                         "vent": 0.0, "par": 0.0, "nagr": 0.1, "txt": "ул.А 1", "potrebitel": None}
        self.updates: list[tuple] = []
        self.potrebitel = {7: None, 8: "РС9 node_1", 9: "РС1 node_5"}

    def transaction(self):
        return FakeTx()

    async def fetchrow(self, sql, *args):
        if "FROM zdaniya_2 WHERE id=$1" in sql:
            return dict(self.building) if args[0] == 7 else None
        if "FROM nagruzki n" in sql and "load_count" in sql:
            if args[1] == "ул.Б" and args[2].replace(" ", "").lower() == "2":
                return {"load_count": 2, "mkr": None, "street": "ул.Б", "house": "2",
                        "otop": 300000.0, "gvs": 100000.0, "vent": 0.0, "par": 0.0}
            return {"load_count": 0, "mkr": None, "street": None, "house": None,
                    "otop": None, "gvs": None, "vent": None, "par": None}
        if "FROM nodes nd" in sql:
            return {"node_id": 50, "node_type_id": 13, "code": "РС1", "node_name": "node_5",
                    "consumer_id": 3} if args[0] == 50 else None
        if "sum(otop * (otop_cxema = 1)::int)" in sql:
            return {"buildings": len(args[0]), "heating_dependent_elevator": 0.2, "heating_dependent_direct": 0.0,
                    "heating_independent": 0.1, "total": 0.3}
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if "SELECT z.id FROM zdaniya_2 z" in sql:
            return []
        if "SELECT id, potrebitel FROM zdaniya_2 WHERE id = ANY" in sql:
            return [{"id": i, "potrebitel": self.potrebitel[i]} for i in args[0] if i in self.potrebitel]
        if "WHERE potrebitel = $1 AND NOT" in sql:
            return [{"id": i, "potrebitel": p} for i, p in self.potrebitel.items() if p == args[0] and i not in args[1]]
        raise AssertionError(sql)

    async def execute(self, sql, *args):
        self.updates.append((sql, args))


async def _audit(conn, *, operation, table, record_id, old=None, new=None, group=None):
    conn.updates.append(("audit", record_id, old, new))
    return group or "g-1"


def test_alseco_text_matches_desktop_format():
    assert ab.alseco_text("", "ул.Б", "2", 300000.0, 0.0, 100000.0, 0.0) == "ул.Б 2\r\nQот=0.3\r\nQгвс=0.1\r\nQсум=0.4"
    assert ab.alseco_text("", "", "", 0, 0, 0, 0) == ""


def test_issue_kinds_cover_desktop_reports():
    desktop = {s["desktop"] for s in ab.ISSUE_KINDS.values() if s["desktop"]}
    assert desktop == {"nenaid1.sql", "nenaid2.sql", "nenaid3.sql"}
    try:
        _run(ab.reconciliation_issues(FakeConn(), "nope"))
    except ab.AlsekoError as exc:
        assert exc.status == 422
    else:
        raise AssertionError("bad kind accepted")


def test_bind_address_dry_run_and_apply():
    conn = FakeConn()
    r = _run(ab.bind_building_address(conn, 7, mkr=None, street="ул.Б", house=" 2", dry_run=True, audit_row=_audit))
    fields = {c["field"]: c["new"] for c in r["changes"]}
    assert r["action"] == "bind" and fields["street2"] == "ул.Б" and fields["house2"] == "2"
    assert abs(fields["otop"] - 0.3) < 1e-12 and abs(fields["nagr"] - 0.4) < 1e-12
    assert conn.updates == []
    r = _run(ab.bind_building_address(conn, 7, mkr=None, street="ул.Б", house="2", dry_run=False, audit_row=_audit))
    assert r["change_group_id"] == "g-1"
    assert conn.updates[0][0].startswith("UPDATE zdaniya_2 SET mkr2=$2")
    assert conn.updates[1][0] == "audit"


def test_bind_address_errors_and_clear():
    conn = FakeConn()
    for building, street, status in ((99, "ул.Б", 404), (7, "ул.Нет", 422)):
        try:
            _run(ab.bind_building_address(conn, building, mkr=None, street=street, house="2", dry_run=True))
        except ab.AlsekoError as exc:
            assert exc.status == status
        else:
            raise AssertionError(street)
    r = _run(ab.bind_building_address(conn, 7, mkr=None, street=None, house="", dry_run=True))
    assert r["action"] == "clear" and {c["field"] for c in r["changes"]} >= {"street2", "house2", "otop", "txt"}


def test_bind_consumer_replaces_previous_buildings():
    conn = FakeConn()
    r = _run(ab.bind_consumer_buildings(conn, 50, [7, 8], dry_run=True))
    assert r["consumer"]["label"] == "РС1 node_5"
    assert [b["id"] for b in r["assign"]] == [7, 8] and [b["id"] for b in r["unassign"]] == [9]
    assert any("разные схемы" in w for w in r["warnings"]) and any("другому потребителю" in w for w in r["warnings"])
    assert conn.updates == []
    r = _run(ab.bind_consumer_buildings(conn, 50, [7, 8], dry_run=False, audit_row=_audit))
    sql = [u[0] for u in conn.updates if u[0] != "audit"]
    assert sql[0].startswith("UPDATE zdaniya_2 SET potrebitel=NULL") and len(sql) == 3
    assert r["change_group_id"] == "g-1"
    try:
        _run(ab.bind_consumer_buildings(conn, 51, [7], dry_run=True))
    except ab.AlsekoError as exc:
        assert exc.status == 404


def test_routes_require_editor_and_mutations(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    fake = FakeConn()

    @asynccontextmanager
    async def _acquire():
        yield fake

    monkeypatch.setattr("routers.alseko_binding.acquire_conn", _acquire)
    client = TestClient(main.app)
    addr = {"street": "ул.Б", "house": "2", "dry_run": False}
    cons = {"building_ids": [7], "dry_run": False}
    assert client.post("/api/alseko/buildings/7/address", json=addr).status_code == 401
    for role in ("viewer", "calculator"):
        h = _bearer(role)
        assert client.post("/api/alseko/buildings/7/address", json=addr, headers=h).status_code == 403
        assert client.post("/api/alseko/consumers/50/buildings", json=cons, headers=h).status_code == 403
    h = _bearer("editor")
    r = client.post("/api/alseko/buildings/7/address", json={**addr, "dry_run": True}, headers=h)
    assert r.status_code == 200 and r.json()["dry_run"] is True
    assert client.post("/api/alseko/buildings/99/address", json=addr, headers=h).status_code == 404
    assert client.post("/api/alseko/consumers/51/buildings", json=cons, headers=h).status_code == 404
    r = client.get("/api/alseko/reconciliation/issues", params={"kind": "nope"}, headers=h)
    assert r.status_code == 422
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.post("/api/alseko/buildings/7/address", json=addr, headers=h).status_code == 503
    assert client.post("/api/alseko/consumers/50/buildings", json=cons, headers=h).status_code == 503
    r = client.post("/api/alseko/consumers/50/buildings", json={**cons, "dry_run": True}, headers=h)
    assert r.status_code == 200
