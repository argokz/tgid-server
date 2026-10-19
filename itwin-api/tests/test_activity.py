"""Журнал действий: что пишется, что нет (чтение, предпросмотр, служебное), без секретов."""
import asyncio

import pytest

import activity


@pytest.mark.parametrize("method,path,expected", [
    ("POST", "/api/v1/topology/chains", "NETWORK"),
    ("PUT", "/tgid/almaty/map-api/api/v1/topology/node/5/move", "NETWORK"),
    ("POST", "/api/v1/topology/undo", "UNDO"),
    ("PUT", "/api/v1/card-edit", "CARD"),
    ("POST", "/api/v1/card-edit/batch/apply", "GROUP"),
    ("POST", "/api/v1/calculations/run", "CALC_RUN"),
    ("DELETE", "/api/v1/calculations/7", "CALC_SAVE"),
    ("GET", "/api/export/shp", "EXPORT"),
    ("GET", "/api/v1/fragments/3/export", "EXPORT"),
    ("POST", "/api/v1/auth/logout", "LOGOUT"),
    ("PATCH", "/api/v1/admin/users/3", "USERS"),
    ("POST", "/api/v1/journals/repairs", "JOURNAL"),
    ("PUT", "/api/v1/update/repairs/1", "EDIT"),
    # не пишутся: чтение, вход (пишется явно), расчётные POST без записи
    ("GET", "/api/v1/topology/snap-data", None),
    ("GET", "/api/v1/journals/repairs", None),
    ("GET", "/api/reports/catalog", None),
    ("POST", "/auth/login", None),
    ("GET", "/auth/check", None),
    ("POST", "/api/v1/topology/convert-point", None),
    ("POST", "/piezometer/route", None),
    ("POST", "/api/v1/group-setters/x/preview", None),
    ("OPTIONS", "/api/v1/card-edit", None),
])
def test_classify(method, path, expected):
    assert activity.classify(method, path) == expected


def _run_middleware(monkeypatch, method, path, body=b"", query=b"", headers=()):
    written = []

    async def fake_write(**kw):
        written.append(kw)

    monkeypatch.setattr(activity, "write", fake_write)

    async def app(scope, receive, send):
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"{}"})

    async def main():
        mw = activity.ActivityMiddleware(app)
        messages = [{"type": "http.request", "body": body, "more_body": False}]

        async def receive():
            return messages.pop(0) if messages else {"type": "http.disconnect"}

        async def send(_):
            return None

        scope = {"type": "http", "method": method, "path": path, "query_string": query,
                 "headers": list(headers), "client": ("10.0.0.5", 1234)}
        await mw(scope, receive, send)
        await asyncio.gather(*list(activity._pending))

    asyncio.run(main())
    return written


def test_middleware_writes_action_status_ip_without_secrets(monkeypatch):
    rows = _run_middleware(monkeypatch, "POST", "/api/v1/topology/chains", body=b'{"points": []}',
                           query=b"x=1&token=SECRET", headers=[(b"x-real-ip", b"203.0.113.7")])
    assert len(rows) == 1
    r = rows[0]
    assert r["action"] == "NETWORK" and r["status"] == 200 and r["ip"] == "203.0.113.7"
    assert "SECRET" not in r["path"] and r["path"].endswith("token=***")
    assert r["username"] is None  # без токена


def test_middleware_skips_dry_run_and_reads(monkeypatch):
    assert _run_middleware(monkeypatch, "POST", "/api/v1/topology/chains", body=b'{"dry_run": true}') == []
    assert _run_middleware(monkeypatch, "PUT", "/api/v1/card-edit", body=b'{"changes": [], "dry_run":true}') == []
    assert _run_middleware(monkeypatch, "POST", "/api/topology/split-line", query=b"dry_run=true") == []
    assert _run_middleware(monkeypatch, "GET", "/api/v1/topology/snap-data") == []


def test_middleware_username_from_token(monkeypatch):
    from auth import create_access_token

    token = create_access_token(username="ivan", role="operator").encode()
    rows = _run_middleware(monkeypatch, "DELETE", "/api/v1/topology/line/5",
                           headers=[(b"authorization", b"Bearer " + token)])
    assert rows[0]["username"] == "ivan" and rows[0]["action"] == "NETWORK"


def test_login_success_and_failure_logged_without_password(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from routers import auth_routes

    written = []

    async def fake_write(**kw):
        written.append(kw)

    async def ok(body):
        return auth_routes.TokenResponse(access_token="t", role="editor", username=body.username)

    monkeypatch.setattr(activity, "write", fake_write)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")
    monkeypatch.setattr(auth_routes, "_verify_login", ok)
    client = TestClient(main.app)
    assert client.post("/api/v1/auth/login", json={"username": "ivan", "password": "pass-1234"}).status_code == 200

    async def bad(body):
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail="bad")

    monkeypatch.setattr(auth_routes, "_verify_login", bad)
    assert client.post("/api/v1/auth/login", json={"username": "petr", "password": "pass-9999"}).status_code == 401
    assert [(w["action"], w["username"]) for w in written] == [("LOGIN", "ivan"), ("LOGIN_FAIL", "petr")]
    assert all("pass-" not in str(w) for w in written)
