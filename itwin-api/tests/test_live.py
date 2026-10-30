"""Живая карта: формат потока событий, присутствие, сбор правок из audit_log, рассылка."""

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from auth import invalidate_user_status
from database import live


def test_sse_format_multiline():
    assert live.sse("presence", "[1]") == b"event: presence\ndata: [1]\n\n"
    assert live.sse("x", "a\nb") == b"event: x\ndata: a\ndata: b\n\n"


def test_session_key_hides_session_id():
    sid = uuid.UUID("11111111-2222-4333-8444-555555555555")
    key = live.session_key(sid)
    assert key == live.session_key(str(sid)) and len(key) == 12 and key not in str(sid)


def test_presence_model_validation():
    body = live.PresenceIn(session_id=uuid.uuid4(), center=(76.9, 43.2), zoom=15,
                           editing={"kind": "node", "id": 5, "label": "узел"})
    assert body.editing.kind == "node"
    with pytest.raises(ValueError):
        live.PresenceIn(session_id=uuid.uuid4(), editing={"kind": "node; drop", "id": 5})
    with pytest.raises(ValueError):
        live.PresenceIn(session_id=uuid.uuid4(), zoom=99)


class Conn:
    """audit_log в памяти: fetch по SQL — строки после курсора, группы, роли."""

    def __init__(self, rows, roles=("postgres", "tgid_editor")):
        self.rows = rows
        self.roles = roles
        self.executed = []

    async def fetchval(self, sql, *args):
        if "max(log_id)" in sql:
            return max((r["log_id"] for r in self.rows), default=0)
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if "pg_roles" in sql:
            return [{"rolname": r} for r in self.roles]
        if "DISTINCT ON (change_group_id)" in sql:
            gids, roles = args
            out = {}
            for r in sorted(self.rows, key=lambda r: r["log_id"]):
                if r["change_group_id"] in gids and r["changed_by"] not in roles:
                    out.setdefault(r["change_group_id"], r["changed_by"])
            return [{"change_group_id": g, "changed_by": u} for g, u in out.items()]
        if "FROM audit_log" in sql:
            after, tables, limit = args
            return [r for r in sorted(self.rows, key=lambda r: r["log_id"])
                    if r["log_id"] > after and r["table_name"] in tables][:limit]
        raise AssertionError(sql)

    async def fetchrow(self, sql, *args):
        assert "ST_Extent" in sql
        return {"x1": 76.9, "y1": 43.2, "x2": 76.91, "y2": 43.21}


def _row(log_id, table, rec, by, op="UPDATE", gid=None):
    return {"log_id": log_id, "table_name": table, "record_id": rec, "changed_by": by, "operation": op,
            "change_group_id": gid}


def test_collect_changes_floor_authors_dedupe():
    g = uuid.uuid4()
    conn = Conn([_row(10, "nodes", 1, "postgres"), _row(11, "usersdb.users", 3, "postgres")])
    cursor = live.ChangeCursor()
    # первый проход — только курсор: история не рассылается
    assert asyncio.run(live.collect_changes(conn, cursor)) == [] and cursor.floor == 11
    conn.rows += [
        # номер 12 занят транзакцией, которая закоммитится позже
        _row(13, "nodes", 7, "postgres", gid=g),     # триггер: роль базы
        _row(14, "nodes", 7, "olga", "MOVE", gid=g),  # API: пользователь веба той же группы
        _row(15, "linesobj", 9, "postgres"),          # мимо веба — десктоп
        _row(16, "usersdb.users", 3, "postgres"),     # учётные записи не рассылаются
    ]
    out = asyncio.run(live.collect_changes(conn, cursor))
    by = {(c["table"], c["by"]): c for c in out}
    assert set(by) == {("nodes", "olga"), ("linesobj", "postgres")}
    assert by[("nodes", "olga")]["ids"] == [7] and by[("nodes", "olga")]["ops"] == ["MOVE", "UPDATE"]
    assert by[("nodes", "olga")]["direct"] is False and by[("linesobj", "postgres")]["direct"] is True
    assert by[("linesobj", "postgres")]["bbox"] == [76.9, 43.2, 76.91, 43.21]
    # повторный проход по окну не повторяет разосланное; запоздавшая запись с меньшим номером — приходит
    conn.rows.append(_row(12, "dampers", 4, "ivan"))
    again = asyncio.run(live.collect_changes(conn, cursor))
    assert [(c["table"], c["by"]) for c in again] == [("dampers", "ivan")]


def test_hub_overflow_marks_slow_subscriber(monkeypatch):
    monkeypatch.setattr(live, "QUEUE_SIZE", 2)
    hub = live.Hub("t")
    sub = live.Subscriber(queue=asyncio.Queue(maxsize=2))
    hub.subscribers.add(sub)
    for i in range(3):
        hub.broadcast("presence", i)
    assert sub.overflow and sub.queue.qsize() == 2


def test_live_routes_require_login(monkeypatch):
    import main

    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-123")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    invalidate_user_status()
    client = TestClient(main.app)
    assert client.get("/api/v1/live/stream").status_code == 401
    assert client.post("/api/v1/live/presence", json={"session_id": str(uuid.uuid4())}).status_code == 401
    invalidate_user_status()


def test_live_paths_not_in_activity_log():
    import activity

    assert activity.classify("POST", "/api/v1/live/presence") is None
    assert activity.classify("DELETE", "/api/v1/live/presence/x") is None
