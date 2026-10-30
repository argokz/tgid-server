"""Вебхуки и API v2: адрес подписки, подпись Standard Webhooks, отправка, повторы, лента событий, ключ API."""

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from auth import MCP_SCOPE, create_access_token, invalidate_user_status
from database import api_events
from database import webhooks as wh

SECRET = "test-secret-test-secret-test-secret-123"


# --- адрес подписки --------------------------------------------------------------------------

@pytest.fixture
def no_flags(monkeypatch):
    monkeypatch.delenv("WEBHOOK_ALLOW_HTTP", raising=False)
    monkeypatch.delenv("WEBHOOK_ALLOW_PRIVATE", raising=False)


def test_check_url_scheme_and_shape(no_flags, monkeypatch):
    assert wh.check_url(" https://erp.example.kz/hooks/tgid?x=1 ") == "https://erp.example.kz/hooks/tgid?x=1"
    for bad in ("http://erp.example.kz/h", "ftp://erp.example.kz/h", "https://user:pw@erp.example.kz/h",
                "https:///nohost", "https://erp.example.kz/h#frag", "https://erp.example.kz:99999/h"):
        with pytest.raises(ValueError):
            wh.check_url(bad)
    monkeypatch.setenv("WEBHOOK_ALLOW_HTTP", "1")
    assert wh.check_url("http://1c.local/hs/tgid") == "http://1c.local/hs/tgid"


def test_blocked_networks(no_flags, monkeypatch):
    for ip in ("169.254.169.254", "0.0.0.0", "224.0.0.1", "::ffff:169.254.169.254", "fe80::1"):
        assert "служебная" in wh.blocked_reason(ipaddress.ip_address(ip))
    for ip in ("10.0.0.5", "192.168.1.10", "127.0.0.1", "::1", "fd00::1"):
        assert "WEBHOOK_ALLOW_PRIVATE" in wh.blocked_reason(ipaddress.ip_address(ip))
    assert wh.blocked_reason(ipaddress.ip_address("8.8.8.8")) is None
    with pytest.raises(ValueError):
        wh.check_url("https://10.0.0.5/h")
    monkeypatch.setenv("WEBHOOK_ALLOW_PRIVATE", "1")
    assert wh.blocked_reason(ipaddress.ip_address("10.0.0.5")) is None
    assert wh.blocked_reason(ipaddress.ip_address("127.0.0.1")) is None
    # адреса метаданных облака (link-local, Alibaba в CGNAT), NAT64 и 6to4 закрыты и с разрешением внутренних сетей
    for ip in ("169.254.169.254", "100.100.100.200", "100.64.0.1", "64:ff9b::a9fe:a9fe", "2002:a9fe:a9fe::1"):
        assert wh.blocked_reason(ipaddress.ip_address(ip)) is not None, ip


def test_resolve_checks_every_address(no_flags, monkeypatch):
    async def getaddrinfo(host, port, type=0):  # noqa: A002 — имя параметра как у loop.getaddrinfo
        return [(2, 1, 6, "", ("93.184.216.34", port)), (2, 1, 6, "", ("10.1.2.3", port))]

    async def run():
        loop = asyncio.get_running_loop()
        monkeypatch.setattr(loop, "getaddrinfo", getaddrinfo)
        return await wh._resolve("erp.example.kz", 443)

    with pytest.raises(wh.WebhookError) as exc:
        asyncio.run(run())
    assert exc.value.status == 403
    monkeypatch.setenv("WEBHOOK_ALLOW_PRIVATE", "1")
    assert asyncio.run(run()) == "93.184.216.34"


def test_model_validation(no_flags):
    hook = wh.WebhookIn(name=" ERP ", url="https://erp.example.kz/h",
                        events=["outage.created", "defect.created", "outage.created"])
    assert hook.name == "ERP" and hook.events == ["defect.created", "outage.created"]
    with pytest.raises(ValueError):
        wh.WebhookIn(name="x", url="https://erp.example.kz/h", events=["order.paid"])
    assert wh.WebhookPatch(active=False).model_dump(exclude_none=True) == {"active": False}


# --- подпись и отправка ----------------------------------------------------------------------

def test_signature_matches_standard_webhooks_vector():
    # пример из спецификации Standard Webhooks (https://github.com/standard-webhooks/standard-webhooks)
    body = b'{"test": 2432232314}'
    sig = wh.sign("whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw", "msg_p5jXN8AQM9LWM0D4loKWxJek", 1614265330, body)
    assert sig == "v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE="
    assert wh.new_secret().startswith("whsec_") and wh.new_secret() != wh.new_secret()


def _verify(secret, request):
    key = base64.b64decode(secret.removeprefix("whsec_"))
    msg = f"{request.headers['webhook-id']}.{request.headers['webhook-timestamp']}.".encode() + request.content
    return request.headers["webhook-signature"] == "v1," + base64.b64encode(
        hmac.new(key, msg, hashlib.sha256).digest()).decode()


@pytest.fixture
def public_dns(monkeypatch):
    async def resolve(host, port):
        return "93.184.216.34"

    monkeypatch.setattr(wh, "_resolve", resolve)


def test_send_pins_ip_signs_and_reports(public_dns):
    secret = wh.new_secret()
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(204 if len(seen) == 1 else 503)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            payload = {"id": "evt_almaty_5", "type": "outage.created", "data": {"title": "Отключение"}}
            return [await wh.send("https://erp.example.kz/hooks?a=1", secret, payload, client=client) for _ in range(2)]

    ok, bad = asyncio.run(run())
    assert ok.ok and ok.code == 204 and ok.error is None
    assert not bad.ok and bad.code == 503 and bad.error == "Ответ 503"
    req = seen[0]
    assert str(req.url) == "https://93.184.216.34/hooks?a=1"  # запрос — на проверенный IP
    assert req.headers["host"] == "erp.example.kz" and req.extensions.get("sni_hostname") == "erp.example.kz"
    assert req.headers["webhook-id"] == "evt_almaty_5" and _verify(secret, req)
    assert json.loads(req.content)["data"]["title"] == "Отключение"


def test_send_total_deadline(public_dns, monkeypatch):
    # ответ по байту раз в несколько секунд не превышает таймаут чтения — держит общий срок
    monkeypatch.setattr(wh, "SEND_DEADLINE_S", 0.2)

    async def trickle(request):
        await asyncio.sleep(5)
        return httpx.Response(200)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(trickle)) as client:
            return await wh.send("https://erp.example.kz/h", wh.new_secret(), {"id": "e"}, client=client)

    result = asyncio.run(run())
    assert not result.ok and "Нет ответа" in result.error and result.ms < 2000


def test_send_blocked_and_timeout(no_flags, public_dns, monkeypatch):
    async def blocked(host, port):
        raise wh.WebhookError(403, "Адрес 10.0.0.1 — внутренняя сеть")

    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            timeout = await wh.send("https://erp.example.kz/h", wh.new_secret(), {"id": "e"}, client=client)
            monkeypatch.setattr(wh, "_resolve", blocked)
            refused = await wh.send("https://erp.example.kz/h", wh.new_secret(), {"id": "e"}, client=client)
            return timeout, refused

    timeout, refused = asyncio.run(run())
    assert not timeout.ok and "Нет ответа" in timeout.error
    assert not refused.ok and refused.code is None and "внутренняя сеть" in refused.error


class FakeConn:
    def __init__(self, rows=None):
        self.calls = []
        self.rows = rows or []

    async def execute(self, sql, *args):
        self.calls.append((" ".join(sql.split()), args))
        return "UPDATE 1"

    async def fetch(self, sql, *args):
        self.calls.append((" ".join(sql.split()), args))
        return self.rows


def test_retry_schedule_and_final_failure():
    conn = FakeConn()
    fail = wh.Result(False, 500, "Ответ 500", 5)
    asyncio.run(wh._finish(conn, {"id": 1, "webhook_id": 2, "attempts": 1}, fail))
    sql, args = conn.calls[0]
    assert "interval '60 seconds'" in sql and args[1] == "pending"
    assert "failing_since = coalesce(failing_since, now())" in conn.calls[1][0]
    conn = FakeConn()
    asyncio.run(wh._finish(conn, {"id": 1, "webhook_id": 2, "attempts": wh.MAX_ATTEMPTS}, fail))
    assert conn.calls[0][1][1] == "failed"
    conn = FakeConn()
    asyncio.run(wh._finish(conn, {"id": 1, "webhook_id": 2, "attempts": 3}, wh.Result(True, 200, None, 5)))
    assert "status = 'ok'" in conn.calls[0][0] and "failing_since = NULL" in conn.calls[1][0]
    assert len(wh.RETRY_DELAYS_S) + 1 == wh.MAX_ATTEMPTS and sum(wh.RETRY_DELAYS_S) > 24 * 3600


def test_deliver_due_sends_claimed_batch(public_dns):
    secret = wh.new_secret()
    payload = {"id": "evt_almaty_9", "type": "work_order.created", "data": {}}
    conn = FakeConn(rows=[{"id": 11, "webhook_id": 2, "payload": json.dumps(payload), "attempts": 1,
                           "url": "https://erp.example.kz/h", "secret": secret}])
    got = []

    def handler(request):
        got.append(_verify(secret, request))
        return httpx.Response(200)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await wh.deliver_due(conn, client=client)

    assert asyncio.run(run()) == 1 and got == [True]
    assert "FOR UPDATE OF d SKIP LOCKED" in conn.calls[0][0]
    assert any("status = 'ok'" in sql for sql, _ in conn.calls)


# --- события ---------------------------------------------------------------------------------

def test_event_sources_skip_collected_and_comments():
    by_name = {s.name: s for s in api_events.SOURCES}
    assert set(by_name) == {"defect", "work_order", "outage"}
    for name, src in by_name.items():
        assert f"a.source = '{name}'" in src.insert_sql and "ON CONFLICT (source, source_id) DO NOTHING" in src.insert_sql
    assert "e.to_status IS NOT NULL" in by_name["work_order"].insert_sql  # комментарии — не события
    # свободного текста (название, описание — туда call-центр может вписать телефон) в событиях нет
    for src in api_events.SOURCES:
        assert "o.title" not in src.insert_sql and "description" not in src.insert_sql
    # в данных событий нет имён потребителей и логинов
    for src in api_events.SOURCES:
        assert "consumers'" not in src.insert_sql and "by_user" not in src.insert_sql


def test_feed_pages_by_seq():
    rows = [{"id": i, "type": "outage.created", "occurred_at": datetime(2026, 10, 30, 8, 0, i, tzinfo=timezone.utc),
             "data": json.dumps({"outage_id": i})} for i in (5, 6, 7)]

    class Conn:
        async def fetch(self, sql, *args):
            self.args = args
            return rows[: args[1]]

    conn = Conn()
    page = asyncio.run(api_events.feed(conn, "almaty", after=4, limit=2, types=["outage.created"]))
    assert [e["seq"] for e in page["data"]] == [5, 6] and page["has_more"] and page["next_after"] == 6
    first = page["data"][0]
    assert first["id"] == "evt_almaty_5" and first["occurred_at"] == "2026-10-30T08:00:05Z"
    assert first["data"] == {"outage_id": 5} and conn.args == (4, 3, ["outage.created"])


# --- API v2 ----------------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    import main
    from routers import api_v2

    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    invalidate_user_status()

    async def write(**kwargs):
        pass

    monkeypatch.setattr(api_v2.activity, "write", write)
    yield TestClient(main.app)
    invalidate_user_status()


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_api_key_only_for_v2_and_closed_by_password_change(client, monkeypatch):
    from routers import api_v2

    fingerprint = {"value": "fp-old"}

    async def fake_fp(sub):
        if fingerprint["value"] is None:
            raise RuntimeError("UsersDB down")
        return fingerprint["value"] if sub.isdigit() else None

    monkeypatch.setattr(api_v2, "_password_fingerprint", fake_fp)
    session = create_access_token(username="ivan", role="viewer", subject="7")
    issued = client.post("/api/v1/api-key", headers=_bearer(session)).json()
    token = issued["token"]
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert claims["scope"] == "api" and claims["pwf"] == "fp-old" and issued["api_url"].endswith("/api/v2")
    assert client.get("/api/v2", headers=_bearer(token)).json()["version"] == api_v2.API_VERSION
    assert client.get("/api/v2", headers=_bearer(session)).status_code == 200  # сессия веба — тоже
    assert client.get("/api/v2").status_code == 401
    # ключ API — только на /api/v2
    assert client.get("/api/v1/webhooks", headers=_bearer(token)).status_code == 401
    mcp = create_access_token(username="ivan", role="viewer", subject="7", extra={"scope": MCP_SCOPE})
    assert client.get("/api/v2", headers=_bearer(mcp)).status_code == 401
    fingerprint["value"] = "fp-new"
    r = client.get("/api/v2", headers=_bearer(token))
    assert r.status_code == 401 and "Пароль сменён" in r.json()["detail"]
    fingerprint["value"] = None
    assert client.get("/api/v2", headers=_bearer(token)).status_code == 401


def test_openapi_v2_has_only_v2_paths(client):
    schema = client.get("/api/v2/openapi.json").json()
    assert schema["info"]["version"] == "2.0.0" and schema["paths"]
    assert all(p.startswith("/api/v2") for p in schema["paths"])
    assert {"/api/v2/events", "/api/v2/work-orders", "/api/v2/outages/{outage_id}"} <= set(schema["paths"])
    assert schema["components"]["securitySchemes"]["bearer"]["scheme"] == "bearer"


def test_create_work_order_idempotent(client, monkeypatch):
    from routers import api_v2

    store = {}  # client_id → (наряд, автор)
    now = datetime(2026, 10, 30, tzinfo=timezone.utc)

    def order(oid, title):
        return {"id": oid, "number": f"Н-2026-{oid:05d}", "title": title, "kind": "repair", "priority": 2,
                "status": "new", "created_at": now, "updated_at": now, "revision": 1,
                "events": [{"at": now, "from_status": None, "to_status": "new", "note": "Создан"},
                           {"at": now, "from_status": None, "to_status": None, "note": "комментарий"}]}

    class Conn:
        async def fetchrow(self, sql, client_id):
            hit = store.get(client_id)
            return {"order_id": hit[0]["id"], "by_user": hit[1]} if hit else None

    @asynccontextmanager
    async def conn():
        yield Conn()

    async def get_order(_, order_id):
        return next(o for o, _ in store.values() if o["id"] == order_id)

    async def create(_, body, user, stamp):
        out = order(len(store) + 1, body.title)
        store[stamp.client_id] = (out, user)
        return out

    monkeypatch.setattr(api_v2, "acquire_conn", conn)
    monkeypatch.setattr(api_v2.wo, "get_order", get_order)
    monkeypatch.setattr(api_v2.wo, "create", create)
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    editor = _bearer(create_access_token(username="ivan", role="editor", subject="ivan"))
    body = {"title": "Нет отопления", "lon": 76.93, "lat": 43.25}
    first = client.post("/api/v2/work-orders", json=body, headers={**editor, "Idempotency-Key": "crm-1"})
    assert first.status_code == 201 and first.json()["id"] == 1
    assert first.json()["history"] == [{"at": "2026-10-30T00:00:00Z", "from_status": None, "to_status": "new",
                                        "note": "Создан"}]
    again = client.post("/api/v2/work-orders", json=body, headers={**editor, "Idempotency-Key": "crm-1"})
    assert again.status_code == 200 and again.headers["idempotent-replayed"] == "true" and again.json()["id"] == 1
    other = client.post("/api/v2/work-orders", json=body, headers={**editor, "Idempotency-Key": "crm-2"})
    assert other.json()["id"] == 2
    # тот же ключ с другой заявкой — отказ, а не чужой наряд
    changed = client.post("/api/v2/work-orders", json={**body, "title": "Другое"},
                          headers={**editor, "Idempotency-Key": "crm-1"})
    assert changed.status_code == 422
    # ключ другого пользователя с той же строкой — свой наряд (ключи не пересекаются)
    other_editor = _bearer(create_access_token(username="olga", role="editor", subject="olga"))
    olga = client.post("/api/v2/work-orders", json=body, headers={**other_editor, "Idempotency-Key": "crm-1"})
    assert olga.status_code == 201 and olga.json()["id"] == 3
    assert api_v2.idempotency_id("ivan", "crm-1") != api_v2.idempotency_id("olga", "crm-1")
    nowhere = client.post("/api/v2/work-orders", json={"title": "x"}, headers=editor)
    assert nowhere.status_code == 422
    viewer = _bearer(create_access_token(username="petr", role="viewer", subject="petr"))
    assert client.post("/api/v2/work-orders", json=body, headers=viewer).status_code == 403
