"""Комментарии на карте (database/map_comments.py, routers/map_comments.py)."""

import asyncio
from datetime import datetime, timezone

import pytest

from database import map_comments as mc

NOW = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, *, comment=None, alive=2, resolved=False, update_status="UPDATE 1"):
        self.comment = comment
        self.alive = alive
        self.resolved = resolved
        self.update_status = update_status
        self.executed: list[tuple[str, tuple]] = []

    def transaction(self):
        return _Tx()

    async def fetchval(self, sql, *args):
        if "INSERT INTO tgid_map_thread" in sql:
            self.executed.append((sql, args))
            return 5
        if "resolved_at IS NOT NULL FROM tgid_map_thread" in sql:
            return self.resolved
        if "count(*) FROM tgid_map_comment WHERE thread_id" in sql:
            return self.alive
        return 0

    async def fetchrow(self, sql, *args):
        if "FROM tgid_map_comment WHERE id" in sql:
            return self.comment
        return None

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return self.update_status if sql.lstrip().startswith("UPDATE tgid_map_thread SET resolved") else "OK"


@pytest.fixture
def stub_get(monkeypatch):
    calls = []

    async def fake_get(conn, thread_id, user, mark_seen=True):
        calls.append(thread_id)
        return {"id": thread_id}

    monkeypatch.setattr(mc, "get_thread", fake_get)
    return calls


def test_mentions_known_logins_only_in_order():
    body = "@ivanov посмотри, и @Petrov.  Почта a@b.kz не упоминание, @ivanov ещё раз, @неизвестный."
    assert mc.mentions_in(body) == ["ivanov", "Petrov", "неизвестный"]
    assert mc.mentions_in(body, {"ivanov", "petrov", "admin"}) == ["ivanov", "petrov"]
    assert mc.mentions_in("без упоминаний", set()) == []


def test_thread_row_snippet_unread_resolved():
    long = "Течь " * 60
    row = {"id": 1, "lon": 76.9, "lat": 43.2, "created_at": NOW, "last_at": NOW, "resolved_at": None,
           "first_body": long, "first_deleted": None, "comment_count": 2, "unread_since": NOW, "mentions_me": True}
    out = mc._thread_row(row)
    assert out["snippet"].endswith("…") and len(out["snippet"]) == mc.SNIPPET + 1
    assert out["unread"] and not out["resolved"] and out["created_at"] == NOW.isoformat()
    assert "first_body" not in out
    gone = mc._thread_row({**row, "first_deleted": NOW, "resolved_at": NOW, "unread_since": None})
    assert gone["snippet"] == "" and gone["resolved"] and not gone["unread"]


def test_create_thread_stores_point_and_mentions(stub_get):
    conn = FakeConn()
    body = mc.ThreadIn(lon=76.9, lat=43.2, zoom=16.5, object_kind="node", object_id=7, body=" Нужен осмотр, @ivanov ")
    asyncio.run(mc.create_thread(conn, body, "dispatcher", {"ivanov"}))
    thread = next(a for s, a in conn.executed if "INSERT INTO tgid_map_thread" in s)
    assert thread == (76.9, 43.2, 16.5, "node", 7, "dispatcher")
    comment = next(a for s, a in conn.executed if "INSERT INTO tgid_map_comment" in s)
    assert comment == (5, "Нужен осмотр, @ivanov", ["ivanov"], "dispatcher")
    with pytest.raises(mc.CommentError, match="вместе"):
        asyncio.run(mc.create_thread(FakeConn(), mc.ThreadIn(lon=1, lat=2, object_kind="line", body="x"), "u"))
    with pytest.raises(mc.CommentError, match="Пустой"):
        asyncio.run(mc.create_thread(FakeConn(), mc.ThreadIn(lon=1, lat=2, body="   "), "u"))


def test_reply_reopens_resolved_thread(stub_get):
    conn = FakeConn(resolved=True)
    asyncio.run(mc.reply(conn, 5, mc.CommentIn(body="Сделали"), "brig"))
    assert any("resolved_at = NULL" in s for s, _ in conn.executed)
    open_conn = FakeConn(resolved=False)
    asyncio.run(mc.reply(open_conn, 5, mc.CommentIn(body="Ещё"), "brig"))
    assert not any("resolved_at = NULL" in s for s, _ in open_conn.executed)

    class Gone(FakeConn):
        async def fetchval(self, sql, *args):
            return None

    with pytest.raises(mc.CommentError) as e:
        asyncio.run(mc.reply(Gone(), 5, mc.CommentIn(body="x"), "brig"))
    assert e.value.status == 404


def test_edit_and_delete_only_own_or_admin(stub_get):
    mine = {"id": 9, "thread_id": 5, "author": "brig", "deleted_at": None}
    conn = FakeConn(comment=mine)
    asyncio.run(mc.edit_comment(conn, 9, mc.CommentIn(body="Исправил, @ivanov"), "brig", known={"ivanov"}))
    edit = next(a for s, a in conn.executed if "UPDATE tgid_map_comment SET body" in s)
    assert edit == (9, "Исправил, @ivanov", ["ivanov"])
    with pytest.raises(mc.CommentError) as e:
        asyncio.run(mc.edit_comment(FakeConn(comment=mine), 9, mc.CommentIn(body="x"), "other"))
    assert e.value.status == 403
    asyncio.run(mc.delete_comment(FakeConn(comment=mine), 9, "other", is_admin=True))
    with pytest.raises(mc.CommentError) as e:
        asyncio.run(mc.delete_comment(FakeConn(comment={**mine, "deleted_at": NOW}), 9, "brig"))
    assert e.value.status == 404


def test_delete_last_message_removes_thread(stub_get):
    mine = {"id": 9, "thread_id": 5, "author": "brig", "deleted_at": None}
    conn = FakeConn(comment=mine, alive=1)
    assert asyncio.run(mc.delete_comment(conn, 9, "brig")) is None
    assert any("DELETE FROM tgid_map_thread" in s for s, _ in conn.executed)
    keep = FakeConn(comment=mine, alive=3)
    assert asyncio.run(mc.delete_comment(keep, 9, "brig")) == {"id": 5}
    assert any("SET deleted_at = now()" in s for s, _ in keep.executed)


def test_resolve_and_missing_thread(stub_get):
    conn = FakeConn()
    asyncio.run(mc.set_resolved(conn, 5, "disp", True))
    sql, args = next(x for x in conn.executed if "resolved_at = now()" in x[0])
    assert args == (5, "disp")
    asyncio.run(mc.set_resolved(conn, 5, "disp", False))
    assert any("resolved_at = NULL" in s and a == (5,) for s, a in conn.executed)
    with pytest.raises(mc.CommentError):
        asyncio.run(mc.set_resolved(FakeConn(update_status="UPDATE 0"), 5, "disp", True))


def test_endpoints(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from auth import invalidate_user_status
    from routers import map_comments as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()
    calls = {}

    class Conn(FakeConn):
        async def fetch(self, sql, *args):
            return [{"author": "brig"}]

    @asynccontextmanager
    async def acquire():
        yield Conn()

    async def fake_create(conn, body, user, known):
        calls["create"] = (body.body, known)
        return {"id": 5}

    async def fake_list(conn, user, *, status, scope, q):
        calls["list"] = (status, scope, q)
        return {"items": []}

    async def fake_users():
        raise RuntimeError("UsersDB недоступна")

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(mc, "create_thread", fake_create)
    monkeypatch.setattr(mc, "list_threads", fake_list)
    monkeypatch.setattr("database.users_admin.list_users", fake_users)
    router._people_cache.clear()
    client = TestClient(main.app)
    assert client.post("/api/v1/map-comments", json={"lon": 76.9, "lat": 43.2, "body": "@brig глянь"}).json() == {"id": 5}
    assert calls["create"] == ("@brig глянь", {"brig"})  # без UsersDB — авторы комментариев
    assert client.get("/api/v1/map-comments/people").json() == {"items": [{"login": "brig", "role": ""}]}
    client.get("/api/v1/map-comments", params={"status": "all", "scope": "mine", "q": "течь"})
    assert calls["list"] == ("all", "mine", "течь")
    assert client.get("/api/v1/map-comments", params={"status": "maybe"}).status_code == 422
    assert client.post("/api/v1/map-comments", json={"lon": 200, "lat": 0, "body": "x"}).status_code == 422
    router._people_cache.clear()
