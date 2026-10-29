"""MCP-сервер ТГИД: протокол JSON-RPC, маршрут /mcp, токен ИИ-клиента, инструменты."""

import asyncio
import time

import jwt
import pytest
from fastapi.testclient import TestClient

from auth import MCP_SCOPE, AuthUser, create_access_token, decode_access_token, invalidate_user_status
from tgid_mcp import protocol
from tgid_mcp import tools as mcp_tools

ADMIN = AuthUser(sub="ivan", role="admin", username="ivan")
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}


def _handle(message, user=ADMIN):
    return asyncio.run(protocol.handle_message(message, user))


def test_initialize_negotiates_version():
    res = _handle(INIT)["result"]
    assert res["protocolVersion"] == "2025-03-26" and res["capabilities"] == {"tools": {"listChanged": False}}
    assert res["serverInfo"]["name"] == "tgid"
    old = _handle({**INIT, "params": {"protocolVersion": "1999-01-01"}})["result"]
    assert old["protocolVersion"] == protocol.LATEST_VERSION


def test_messages_errors_and_notifications():
    assert _handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert _handle({"jsonrpc": "2.0", "id": 5, "result": {}}) is None  # ответ клиента
    assert _handle({"jsonrpc": "2.0", "id": 2, "method": "ping"}) == {"jsonrpc": "2.0", "id": 2, "result": {}}
    assert _handle({"jsonrpc": "1.0", "id": 2, "method": "ping"})["error"]["code"] == protocol.INVALID_REQUEST
    assert _handle({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})["error"]["code"] == protocol.METHOD_NOT_FOUND
    err = _handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "drop_db"}})["error"]
    assert err["code"] == protocol.INVALID_PARAMS
    assert _handle({"jsonrpc": "2.0", "id": 4, "method": "ping", "params": [1]})["error"]["code"] == protocol.INVALID_PARAMS


def test_tools_list_schemas():
    tools = {t["name"]: t for t in _handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]}
    assert {"list_fragments", "search_network", "network_trace", "valve_isolation", "run_calculation"} <= set(tools)
    trace = tools["network_trace"]["inputSchema"]
    assert trace["type"] == "object" and "start_node_ids" in trace["properties"]
    assert tools["list_fragments"]["inputSchema"]["properties"] == {}
    assert tools["run_calculation"]["annotations"]["readOnlyHint"] is False
    assert tools["network_trace"]["annotations"]["readOnlyHint"] is True


@pytest.fixture
def no_activity(monkeypatch):
    calls = []

    async def write(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(mcp_tools.activity, "write", write)
    return calls


def test_call_tool_validation_permission_and_log(no_activity, monkeypatch):
    res = asyncio.run(mcp_tools.call_tool("search_network", {"kind": "planet", "text": "x"}, ADMIN))
    assert res["isError"] is True and "kind" in res["content"][0]["text"]
    viewer = AuthUser(sub="petr", role="viewer", username="petr")
    res = asyncio.run(mcp_tools.call_tool("run_calculation", {"fragment_ids": [74]}, viewer))
    assert res["isError"] is True and "Запуск расчётов" in res["content"][0]["text"]
    assert [c["details"]["tool"] for c in no_activity] == ["search_network", "run_calculation"]
    assert no_activity[0]["action"] == "MCP" and no_activity[0]["path"] == "/mcp/search_network"

    async def boom(p, user):
        raise RuntimeError("secret detail")

    monkeypatch.setitem(mcp_tools.TOOLS, "list_fragments", mcp_tools.TOOLS["list_fragments"].__class__(
        **{**mcp_tools.TOOLS["list_fragments"].__dict__, "run": boom}))
    res = asyncio.run(mcp_tools.call_tool("list_fragments", {}, ADMIN))
    assert res["isError"] is True and "secret" not in res["content"][0]["text"]


def test_compact_drops_geometry_and_caps_lists():
    data = {"geojson": {"x": 1}, "items": [{"id": i, "geometry": {}} for i in range(mcp_tools.MAX_LIST_ITEMS + 5)]}
    out = mcp_tools._compact(data)
    assert "geojson" not in out and len(out["items"]) == mcp_tools.MAX_LIST_ITEMS + 1
    assert out["items"][0] == {"id": 0} and out["items"][-1].startswith("… ещё 5")
    res = mcp_tools._text_result({"a": 1})
    assert res["structuredContent"] == {"a": 1} and res["isError"] is False


def test_theme_summary_classes(no_activity, monkeypatch):
    from contextlib import asynccontextmanager

    from database import thematic as th

    @asynccontextmanager
    async def acquire():
        yield None

    async def fake(conn, theme, ids, **kw):
        assert kw["with_geometry"] is False
        feats = [{"properties": {"id": i, "fileid": 74, "v": v}} for i, v in enumerate([0.1, 0.5, 1.0, 3.0, None])]
        return {"theme": next(t for t in th.themes_payload() if t["key"] == "velocity"), "source_run": None,
                "summary": {"count": 5, "with_value": 4}, "truncated": False, "geojson": {"features": feats}}

    monkeypatch.setattr(mcp_tools, "acquire_conn", acquire)
    monkeypatch.setattr(th, "theme_features", fake)
    res = asyncio.run(mcp_tools.call_tool("thematic_summary", {"theme": "velocity", "fragment_ids": [74], "top": 2},
                                          ADMIN))
    s = res["structuredContent"]
    assert [c["count"] for c in s["classes"]] == [1, 1, 1, 0, 1]
    assert s["top"] == [{"line_id": 3, "fragment_id": 74, "value": 3.0}, {"line_id": 2, "fragment_id": 74, "value": 1.0}]


def test_scoped_token_only_for_mcp(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-123")
    token = create_access_token(username="ivan", role="viewer", extra={"scope": MCP_SCOPE})
    with pytest.raises(Exception) as exc:
        decode_access_token(token)
    assert getattr(exc.value, "status_code", None) == 401
    assert decode_access_token(token, allow_scopes=(MCP_SCOPE,)).scope == MCP_SCOPE
    assert decode_access_token(create_access_token(username="ivan")).scope == ""


@pytest.fixture
def client(monkeypatch):
    import main

    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-123")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://itwin.kz")
    monkeypatch.setenv("MCP_TOKEN_DAYS", "30")
    invalidate_user_status()

    async def write(**kwargs):
        pass

    monkeypatch.setattr(mcp_tools.activity, "write", write)
    from routers import mcp as mcp_router

    monkeypatch.setattr(mcp_router.activity, "write", write)
    yield TestClient(main.app)
    invalidate_user_status()


def _bearer(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"}


def test_endpoint_auth_and_transport(client):
    session = create_access_token(username="ivan", role="viewer")
    assert client.post("/mcp", json=INIT).status_code == 401
    r = client.post("/mcp", json=INIT, headers=_bearer(session))
    assert r.status_code == 200 and r.json()["result"]["serverInfo"]["name"] == "tgid"
    note = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    assert client.post("/mcp", json=note, headers=_bearer(session)).status_code == 202
    assert client.get("/mcp", headers=_bearer(session)).status_code == 405
    bad_origin = {**_bearer(session), "Origin": "https://evil.example"}
    assert client.post("/mcp", json=INIT, headers=bad_origin).status_code == 403
    assert client.post("/mcp", json=INIT, headers={**_bearer(session), "Origin": "https://itwin.kz"}).status_code == 200
    bad_version = {**_bearer(session), "MCP-Protocol-Version": "1999-01-01"}
    assert client.post("/mcp", json=INIT, headers=bad_version).status_code == 400
    r = client.post("/mcp", content=b"{not json", headers={**_bearer(session), "Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["error"]["code"] == protocol.PARSE_ERROR
    batch = client.post("/mcp", json=[INIT, note, {"jsonrpc": "2.0", "id": 2, "method": "ping"}],
                        headers=_bearer(session))
    assert [m["id"] for m in batch.json()] == [1, 2]


def test_mcp_token_issue_and_scope(client):
    session = create_access_token(username="ivan", role="calculator", subject="ivan")
    r = client.post("/api/v1/mcp/token", headers=_bearer(session))
    assert r.status_code == 200
    token = r.json()["token"]
    payload = jwt.decode(token, "test-secret-test-secret-test-secret-123", algorithms=["HS256"])
    assert payload["scope"] == MCP_SCOPE and payload["role"] == "calculator"
    assert 29 * 86400 < payload["exp"] - time.time() <= 30 * 86400
    # на /mcp действует, остальное API (и выдачу нового токена) — нет
    assert client.post("/mcp", json=INIT, headers=_bearer(token)).status_code == 200
    assert client.get("/api/v1/mcp/info", headers=_bearer(token)).status_code == 401
    assert client.post("/api/v1/mcp/token", headers=_bearer(token)).status_code == 401
    # маршрут без своей зависимости (закрывает только общий middleware) и с зависимостью
    assert client.get("/api/network-queries/length", headers=_bearer(token)).status_code == 401
    assert client.get("/api/v1/thematic/themes", headers=_bearer(token)).status_code == 401
    info = client.get("/api/v1/mcp/info", headers=_bearer(session)).json()
    assert info["enabled"] is True and info["token_days"] == 30 and len(info["tools"]) == len(mcp_tools.TOOLS)


def test_mcp_disabled(client, monkeypatch):
    monkeypatch.setenv("MCP_ENABLED", "false")
    session = create_access_token(username="ivan", role="viewer")
    assert client.post("/mcp", json=INIT, headers=_bearer(session)).status_code == 404
    assert client.post("/api/v1/mcp/token", headers=_bearer(session)).status_code == 404


def test_auth_check_rejects_mcp_token(client):
    token = create_access_token(username="ivan", role="viewer", extra={"scope": MCP_SCOPE})
    assert client.get("/auth/check", headers=_bearer(token)).status_code == 401
    assert client.get("/auth/check", headers=_bearer(create_access_token(username="ivan"))).status_code == 200


def test_password_change_and_db_failure_close_token(client, monkeypatch):
    from routers import mcp as mcp_router

    fingerprint = {"value": "fp-old"}

    async def fake_fp(sub):
        if fingerprint["value"] is None:
            raise RuntimeError("UsersDB down")
        return fingerprint["value"] if sub.isdigit() else None

    monkeypatch.setattr(mcp_router, "_password_fingerprint", fake_fp)
    session = create_access_token(username="ivan", role="viewer", subject="7")
    token = client.post("/api/v1/mcp/token", headers=_bearer(session)).json()["token"]
    assert jwt.decode(token, "test-secret-test-secret-test-secret-123", algorithms=["HS256"])["pwf"] == "fp-old"
    assert client.post("/mcp", json=INIT, headers=_bearer(token)).status_code == 200
    fingerprint["value"] = "fp-new"  # пароль сменили
    r = client.post("/mcp", json=INIT, headers=_bearer(token))
    assert r.status_code == 401 and "Пароль сменён" in r.json()["detail"]
    fingerprint["value"] = None  # UsersDB недоступна — долгий токен не пускаем
    assert client.post("/mcp", json=INIT, headers=_bearer(token)).status_code == 401
    # токен сессии веба отпечатка не требует
    assert client.post("/mcp", json=INIT, headers=_bearer(session)).status_code == 200


def test_blocked_user_rejected(client, monkeypatch):
    import auth

    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "true")

    async def blocked(user_id):
        return (False, "viewer", (), None, "")

    monkeypatch.setattr(auth, "_load_user_status", blocked)
    invalidate_user_status()
    token = create_access_token(username="ivan", role="viewer", subject="7", extra={"scope": MCP_SCOPE})
    assert client.post("/mcp", json=INIT, headers=_bearer(token)).status_code == 401


def test_batch_limit(client):
    session = create_access_token(username="ivan", role="viewer")
    pings = [{"jsonrpc": "2.0", "id": i, "method": "ping"} for i in range(11)]
    r = client.post("/mcp", json=pings, headers=_bearer(session))
    assert r.status_code == 400 and r.json()["error"]["code"] == protocol.INVALID_REQUEST
    assert client.post("/mcp", json=[], headers=_bearer(session)).status_code == 400


def test_rate_limit_and_server_errors(no_activity, monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(mcp_tools, "RATE_LIMIT", (2, 60))
    monkeypatch.setattr(mcp_tools, "_calls", mcp_tools.defaultdict(mcp_tools.deque))

    async def db_error(p, user):
        raise HTTPException(status_code=500, detail="relation secret_table does not exist")

    tool = mcp_tools.TOOLS["list_fragments"]
    monkeypatch.setitem(mcp_tools.TOOLS, "list_fragments", tool.__class__(**{**tool.__dict__, "run": db_error}))
    user = AuthUser(sub="anna", role="viewer", username="anna")
    first = asyncio.run(mcp_tools.call_tool("list_fragments", {}, user, {"ip": "10.0.0.1", "user_agent": "t"}))
    assert first["isError"] and "secret_table" not in first["content"][0]["text"]
    asyncio.run(mcp_tools.call_tool("list_fragments", {}, user))
    third = asyncio.run(mcp_tools.call_tool("list_fragments", {}, user))
    assert "Слишком часто" in third["content"][0]["text"]
    assert no_activity[0]["ip"] == "10.0.0.1" and no_activity[0]["status"] == 500
