"""Один API на несколько городов (TGID_CITY_DBS): город запроса, пулы, кеши и доводка по городам."""

import asyncio

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

import cities
from city_context import CityPathMiddleware, split_city_path
from database import city_schema, connect, net_srid, sql_ident

CITY_DBS = "almaty=almatygid,astana=astanagid_2026_09_22"


@pytest.fixture
def multi(monkeypatch):
    monkeypatch.setenv("TGID_CITY_DBS", CITY_DBS)
    monkeypatch.setenv("DB_NAME", "almatygid")  # общий .env: в режиме нескольких городов не используется
    monkeypatch.delenv("TGID_CITY", raising=False)


def test_city_databases_parse(multi):
    assert cities.city_databases() == {"almaty": "almatygid", "astana": "astanagid_2026_09_22"}
    assert cities.multi_city()


@pytest.mark.parametrize("bad", ["almaty", "almaty=", "Al maty=x", "almaty=a;drop", "almaty=a,almaty=b"])
def test_city_databases_rejects_bad_config(monkeypatch, bad):
    monkeypatch.setenv("TGID_CITY_DBS", bad)
    with pytest.raises(cities.CityError):
        cities.city_databases()


def test_current_city_and_db_follow_context(multi):
    assert cities.current_city() == ""  # вне запроса города нет — не DB_NAME
    with pytest.raises(cities.CityError):
        cities.city_db_name()
    with cities.use_city("astana"):
        assert cities.current_city() == "astana"
        assert cities.city_db_name() == "astanagid_2026_09_22"
        assert cities.cache_key() == "astana"
    assert cities.city_db_name("almaty") == "almatygid"


def test_single_city_mode_unchanged(monkeypatch):
    monkeypatch.delenv("TGID_CITY_DBS", raising=False)
    monkeypatch.delenv("TGID_CITY", raising=False)
    monkeypatch.setenv("DB_NAME", "astanagid_2026_09_22")
    assert cities.current_city() == "astana" and cities.city_db_name() == "astanagid_2026_09_22"
    assert cities.cache_key() == ""


@pytest.mark.parametrize("path, expected", [
    ("/city/almaty/api/v1/x", ("almaty", "/api/v1/x")),
    ("/city/astana", ("astana", "/")),
    ("/api/v1/x", (None, "/api/v1/x")),
    ("/city/", (None, "/city/")),
    ("/city/Almaty/x", (None, "/city/Almaty/x")),
])
def test_split_city_path(path, expected):
    assert split_city_path(path) == expected


def _app():
    async def echo(request):
        return JSONResponse({"path": request.url.path, "city": cities.current_city(),
                             "raw": request.scope.get("raw_path", b"").decode()})

    app = Starlette(routes=[Route("/api/v1/echo", echo), Route("/health", echo)])
    app.add_middleware(CityPathMiddleware)
    return TestClient(app)


def test_middleware_routes_by_city_prefix(multi):
    client = _app()
    body = client.get("/city/astana/api/v1/echo?x=1").json()
    assert body == {"path": "/api/v1/echo", "city": "astana", "raw": "/api/v1/echo"}
    assert client.get("/city/almaty/api/v1/echo").json()["city"] == "almaty"


def test_middleware_rejects_unknown_or_missing_city(multi):
    client = _app()
    resp = client.get("/city/shatura/api/v1/echo")
    assert resp.status_code == 404 and "shatura" in resp.json()["detail"]
    resp = client.get("/api/v1/echo")
    assert resp.status_code == 404 and "/city/" in resp.json()["detail"]
    # проверка живости процесса — без города
    assert client.get("/health").json() == {"path": "/health", "city": "", "raw": "/health"}


def test_middleware_passthrough_for_single_city(monkeypatch):
    monkeypatch.delenv("TGID_CITY_DBS", raising=False)
    monkeypatch.setenv("TGID_CITY", "almaty")
    assert _app().get("/api/v1/echo").json()["city"] == "almaty"


class _Pool:
    def __init__(self, name):
        self.name = name
        self.released = []

    async def acquire(self):
        return f"conn-{self.name}"

    async def release(self, conn):
        self.released.append(conn)


def test_pools_follow_request_city(multi, monkeypatch):
    pools = {"almaty": _Pool("almaty"), "astana": _Pool("astana")}
    monkeypatch.setattr(connect, "city_pools", pools)
    with pytest.raises(connect.DatabaseConnectionError):
        connect.get_pool()  # без города не берётся «какая-нибудь» база

    async def use():
        async with connect.acquire_conn() as conn:
            return conn

    with cities.use_city("astana"):
        assert connect.get_pool() is pools["astana"]
        assert asyncio.run(use()) == "conn-astana"
    assert pools["astana"].released == ["conn-astana"] and pools["almaty"].released == []


def test_unavailable_city_pool_is_reopened_on_demand(multi, monkeypatch):
    opened = []

    async def fake_open(config):
        opened.append(config["database"])
        return _Pool(config["database"])

    monkeypatch.setattr(connect, "city_pools", {})
    monkeypatch.setattr(connect, "_pool_locks", {})
    monkeypatch.setattr(connect, "_open_pool", fake_open)
    with cities.use_city("astana"):
        with pytest.raises(connect.DatabaseConnectionError):
            connect.get_pool()  # синхронно пул не открыть
        assert asyncio.run(connect.ensure_city_pool("astana")).name == "astanagid_2026_09_22"
        assert connect.get_pool().name == "astanagid_2026_09_22"
    assert opened == ["astanagid_2026_09_22"]


def test_net_srid_is_per_city(multi, monkeypatch):
    monkeypatch.setattr(net_srid, "_net_srid", {})
    with cities.use_city("astana"):
        net_srid.set_net_srid(9995)
    with cities.use_city("almaty"):
        assert net_srid.net_srid() == net_srid.DEFAULT_NET_SRID
    with cities.use_city("astana"):
        assert net_srid.net_srid() == 9995


def test_catalog_cache_reset_only_for_its_city(multi, monkeypatch):
    monkeypatch.setattr(sql_ident, "_tables_cache", {"almaty": (0.0, {}), "astana": (0.0, {})})
    monkeypatch.setattr(sql_ident, "_columns_cache", {("almaty", "nodes"): (0.0, {}), ("astana", "nodes"): (0.0, {})})
    with cities.use_city("astana"):
        sql_ident.reset_catalog_cache()
    assert list(sql_ident._tables_cache) == ["almaty"] and list(sql_ident._columns_cache) == [("almaty", "nodes")]


def test_schema_state_per_city(multi, monkeypatch):
    monkeypatch.setattr(city_schema, "STATES", {})
    with cities.use_city("astana"):
        city_schema.state()["status"] = "ok"
    with cities.use_city("almaty"):
        assert city_schema.state()["status"] == "unknown"
    assert city_schema.STATES["astana"]["status"] == "ok"


# --- Celery: очередь и город задачи ---

def test_task_queue_per_city(multi, monkeypatch):
    with cities.use_city("astana"):
        assert cities.task_queue() == "tgid.astana"
        assert cities.task_queue("files") == "files.astana"
    with pytest.raises(cities.CityError):
        cities.task_queue()  # задача вне запроса города
    assert cities.city_task_queues() == ["tgid.almaty", "tgid.astana"]
    monkeypatch.delenv("TGID_CITY_DBS")
    assert cities.task_queue() is None and cities.task_queue("files") == "files"


class _Request(dict):
    pass


class _Task:
    name = "run_sety_calculation"

    def __init__(self, city):
        self.request = _Request({"tgid_city": city} if city else {})


def test_worker_routes_stamps_and_enters_city(multi):
    import worker

    with cities.use_city("astana"):
        assert worker._route_by_city("x", (), {}, {}) == {"queue": "tgid.astana"}
        headers = {}
        worker._stamp_city(headers=headers)
        assert headers == {"tgid_city": "astana"}

    worker._enter_city(task=_Task("astana"))
    try:
        assert cities.current_city() == "astana"
        cmd = worker._sety_base_cmd("out.txt", dross=True)
        assert cmd[cmd.index("-database") + 1] == "astanagid_2026_09_22"
    finally:
        worker._leave_city()
    assert cities.current_city() == ""


def test_worker_refuses_task_without_known_city(multi):
    import worker

    worker._enter_city(task=_Task("shatura"))
    try:
        with pytest.raises(cities.CityError):
            worker._city_db()  # чужой/неизвестный город — не DB_NAME из .env
    finally:
        worker._leave_city()


def test_worker_single_city_unchanged(monkeypatch):
    import worker

    monkeypatch.delenv("TGID_CITY_DBS", raising=False)
    monkeypatch.setenv("DB_NAME", "almatygid_copy")
    assert worker._route_by_city("x", (), {}, {}) is None
    headers = {}
    worker._stamp_city(headers=headers)
    assert headers == {}
    assert worker._city_db() == "almatygid_copy"


def test_task_db_pool_opens_only_task_city(multi, monkeypatch):
    opened, closed = [], []

    class _P(_Pool):
        async def close(self):
            closed.append(self.name)

    async def fake_open(config):
        opened.append(config["database"])
        return _P(config["database"])

    monkeypatch.setattr(connect, "city_pools", {})
    monkeypatch.setattr(connect, "_open_pool", fake_open)

    async def job():
        async with connect.task_db_pool() as p:
            assert connect.get_pool() is p
        return p.name

    with cities.use_city("astana"):
        assert asyncio.run(job()) == "astanagid_2026_09_22"
    assert opened == closed == ["astanagid_2026_09_22"] and connect.city_pools == {}


def test_health_checks_every_city_without_prefix(multi, monkeypatch):
    import redis

    from routers import core

    class _R:
        def __init__(self, *a, **k):
            pass

        def ping(self):
            return True

        def close(self):
            pass

    async def fake_check():
        city = cities.current_city()
        return (city == "almaty", None if city == "almaty" else "нет связи")

    monkeypatch.setattr(redis, "Redis", _R)
    monkeypatch.setattr(core, "_db_check", fake_check)
    monkeypatch.setattr(city_schema, "STATES", {})
    body = asyncio.run(core.health())
    assert body["status"] == "degraded"
    assert body["database"]["cities"] == {"almaty": {"ok": True, "error": None},
                                          "astana": {"ok": False, "error": "нет связи"}}
    assert body["database"]["error"] == "astana: нет связи"
    assert set(body["city_schema"]["cities"]) == {"almaty", "astana"}
    with cities.use_city("almaty"):
        single = asyncio.run(core.health())
    assert single["status"] == "ok" and "cities" not in single["database"]


# --- замечания проверки безопасности ---

def test_uncatalogued_city_closed_for_restricted_users(multi, monkeypatch):
    monkeypatch.setenv("TGID_CITIES", "almaty:Алматы")
    assert not cities.allowed(["almaty"], "astana")  # astana есть в TGID_CITY_DBS, но не в справочнике
    assert cities.allowed(None, "astana")
    monkeypatch.delenv("TGID_CITY_DBS")
    assert cities.allowed(["almaty"], "stand")  # API одного города (стенд) — как раньше


def test_pg_user_status_cached_per_city(multi, monkeypatch):
    import auth

    calls = []

    async def load(role):
        calls.append(cities.current_city())
        return (cities.current_city() == "almaty", "viewer", ())

    monkeypatch.setattr(auth, "_load_pg_user_status", load)
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "true")
    auth.invalidate_user_status()
    user = auth.AuthUser(sub=auth.PG_USER_PREFIX + "ivan", role="viewer", username="ivan")
    with cities.use_city("almaty"):
        asyncio.run(auth.apply_live_user_status(user))
    with cities.use_city("astana"):
        with pytest.raises(auth.HTTPException):  # в Астане роль заблокирована — кеш Алматы не помогает
            asyncio.run(auth.apply_live_user_status(user))
    assert calls == ["almaty", "astana"]
    auth.invalidate_user_status(user.sub)
    assert not auth._user_status_cache


def test_task_results_only_for_their_city(multi, monkeypatch):
    from database import file_jobs

    store = {}

    class _R:
        def set(self, key, value, ex=None):
            store[key] = value.encode()

        def get(self, key):
            return store.get(key)

    monkeypatch.setattr(file_jobs, "_redis", lambda: _R())
    import worker

    with cities.use_city("astana"):
        worker._stamp_city(headers={"id": "t-1"})
        assert file_jobs.task_in_request_city("t-1")
        assert not file_jobs.task_in_request_city("unknown")
    with cities.use_city("almaty"):
        assert not file_jobs.task_in_request_city("t-1")


def test_route_without_auth_dependency_checks_user_city(multi, monkeypatch):
    """Карточка /line без зависимости авторизации: токен пользователя Алматы в Астане — отказ."""
    from fastapi.testclient import TestClient

    import auth
    import main

    async def status_row(user_id):
        return (True, "viewer", (), ["almaty"], "")

    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "true")
    monkeypatch.setenv("TGID_CITIES", "almaty:Алматы,astana:Астана")
    monkeypatch.setattr(auth, "_load_user_status", status_row)
    auth.invalidate_user_status()
    token = auth.create_access_token(username="u", role="viewer", subject="7")
    client = TestClient(main.app)
    resp = client.get("/city/astana/line/linesobj/1", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401 and "Астана" in resp.json()["detail"]
    auth.invalidate_user_status()
