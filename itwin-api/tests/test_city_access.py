"""Доступ пользователей UsersDB к городам (cities.py, users.cities) — без живой БД."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import auth  # noqa: E402
import cities  # noqa: E402
import login_guard  # noqa: E402
from auth import create_access_token, hash_password, master_token  # noqa: E402
from database import users_admin  # noqa: E402
from routers import admin, auth_routes  # noqa: E402


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.delenv("TGID_CITIES", raising=False)
    monkeypatch.delenv("TGID_CITY", raising=False)
    monkeypatch.setenv("DB_NAME", "astanagid_2026_09_22")
    auth.invalidate_user_status()
    yield
    auth.invalidate_user_status()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")
    monkeypatch.setenv("AUTH_BACKEND", "usersdb")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "true")
    monkeypatch.setenv("MASTER_LOGIN", "Owner")
    monkeypatch.setenv("MASTER_PASSWORD_HASH", hash_password("Мастер-пароль-2026"))
    login_guard.reset()
    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(admin.router)
    yield TestClient(app)
    login_guard.reset()


def _status(monkeypatch, user_cities, *, active=True, role="editor"):
    async def fake(_uid):
        return active, role, (), user_cities

    monkeypatch.setattr(auth, "_load_user_status", fake)


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_catalog_default_and_custom(monkeypatch):
    assert [c["code"] for c in cities.cities_catalog()] == ["almaty", "astana"]
    assert cities.cities_catalog()[1] == {"code": "astana", "label": "Астана", "path": "/tgid/astana/"}
    monkeypatch.setenv("TGID_CITIES", "almaty:Алматы, shymkent:Шымкент:/shym/, bad code:x, almaty:дубль")
    assert cities.cities_catalog() == [
        {"code": "almaty", "label": "Алматы", "path": "/tgid/almaty/"},
        {"code": "shymkent", "label": "Шымкент", "path": "/shym/"},
    ]


@pytest.mark.parametrize("db, code", [
    ("almatygid", "almaty"), ("almatygid_copy", "almaty"), ("astanagid_2026_09_22", "astana"), ("other", "other"),
])
def test_current_city_from_db_name(monkeypatch, db, code):
    monkeypatch.setenv("DB_NAME", db)
    assert cities.current_city() == code
    monkeypatch.setenv("TGID_CITY", "Shymkent")
    assert cities.current_city() == "shymkent"


def test_normalize_and_allowed():
    assert cities.normalize(None) is None
    assert cities.normalize(["Astana", "almaty", "astana"]) == ["almaty", "astana"]
    with pytest.raises(cities.CityError):
        cities.normalize(["moscow"])
    with pytest.raises(cities.CityError):
        cities.normalize([])
    assert cities.allowed(None)
    assert cities.allowed(["astana"]) and not cities.allowed(["almaty"])
    # API не из справочника (стенд) — город не ограничивает
    assert cities.allowed(["almaty"], "stand")
    assert cities.parse_stored(" almaty, astana ") == ["almaty", "astana"]
    assert cities.parse_stored("") is None and cities.to_stored(None) is None


def test_config_reports_city(client):
    body = client.get("/auth/config").json()
    assert body["city"] == "astana" and body["city_label"] == "Астана"


def test_user_without_city_access_rejected_on_requests(client, monkeypatch):
    _status(monkeypatch, ["almaty"])
    token = create_access_token(username="ivanov", role="editor", subject="5")
    r = client.get("/auth/me", headers=_bearer(token))
    assert r.status_code == 401 and "Астана" in r.json()["detail"]


def test_user_with_city_access_sees_allowed_cities(client, monkeypatch):
    _status(monkeypatch, ["astana"])
    token = create_access_token(username="ivanov", role="editor", subject="5")
    me = client.get("/auth/me", headers=_bearer(token)).json()
    assert me["city"] == "astana" and me["all_cities"] is False
    assert [c["code"] for c in me["cities"]] == ["astana"]


def test_all_cities_user_and_master(client, monkeypatch):
    _status(monkeypatch, None)
    token = create_access_token(username="ivanov", role="editor", subject="5")
    me = client.get("/auth/me", headers=_bearer(token)).json()
    assert me["all_cities"] is True and len(me["cities"]) == 2
    master = client.get("/auth/me", headers=_bearer(master_token())).json()
    assert master["all_cities"] is True and master["is_master"] is True


def test_geoserver_check_ignores_api_city(client, monkeypatch):
    # GeoServer общий: пользователь Алматы проходит проверку и через API Астаны (без адреса — без города)
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    _status(monkeypatch, ["almaty"])
    token = create_access_token(username="ivanov", role="editor", subject="5")
    assert client.get("/auth/check", cookies={"tgid_gs": token}).status_code == 200


class _FakeSession:
    def __init__(self, row):
        self.row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_a):
        return False

    async def execute(self, _stmt):
        return SimpleNamespace(scalar_one_or_none=lambda: self.row)


def test_login_refused_for_other_city(client, monkeypatch):
    row = SimpleNamespace(
        id=5, username="ivanov", hashed_password=hash_password("password-123"),
        is_active=True, is_admin=False, role="editor", cities="almaty",
    )
    monkeypatch.setattr("database.connect.async_session", lambda: _FakeSession(row))
    r = client.post("/auth/login", json={"username": "ivanov", "password": "password-123"})
    assert r.status_code == 403 and "Астана" in r.json()["detail"]
    row.cities = "almaty,astana"
    assert client.post("/auth/login", json={"username": "ivanov", "password": "password-123"}).status_code == 200
    row.cities = None
    assert client.post("/auth/login", json={"username": "ivanov", "password": "password-123"}).status_code == 200


def test_admin_patch_cities(client, monkeypatch):
    calls = []

    async def fake_update(uid, *, actor_id, role=None, is_active=None, **kw):
        calls.append(kw)
        return {}, {"id": uid}

    async def fake_audit(*_a, **_k):
        return None

    monkeypatch.setattr(admin, "update_user", fake_update)
    monkeypatch.setattr(admin, "_audit_users", fake_audit)
    h = _bearer(master_token())
    assert client.patch("/api/v1/admin/users/5", json={"cities": ["astana"]}, headers=h).status_code == 200
    assert client.patch("/api/v1/admin/users/5", json={"cities": None}, headers=h).status_code == 200
    assert client.patch("/api/v1/admin/users/5", json={"role": "viewer"}, headers=h).status_code == 200
    assert calls == [{"cities": ["astana"]}, {"cities": None}, {}]
    assert client.patch("/api/v1/admin/users/5", json={}, headers=h).status_code == 422


def test_admin_list_has_catalog(client, monkeypatch):
    async def fake_list():
        return [{"id": 5, "username": "ivanov", "role": "editor", "is_active": True, "is_admin": False,
                 "cities": ["almaty"]}]

    monkeypatch.setattr(admin, "list_users", fake_list)
    body = client.get("/api/v1/admin/users", headers=_bearer(master_token())).json()
    assert body["current_city"] == "astana" and [c["code"] for c in body["cities_catalog"]] == ["almaty", "astana"]


@pytest.mark.asyncio
async def test_create_user_unknown_city_rejected_before_db():
    with pytest.raises(users_admin.UserAdminError) as exc:
        await users_admin.create_user("ivanov", "password-123", "viewer", cities=["moscow"])
    assert exc.value.status_code == 422


@pytest.mark.parametrize("uri, expected, is_global", [
    ("/geoserver/AlmatyGIS/gwc/service/wmts?SERVICE=WMTS&LAYER=AlmatyGIS:heatpipesections&TileCol=1", {"almaty"}, False),
    ("/geoserver/Astana2/ows?service=WFS&typeName=Astana2:fragments", {"astana"}, False),
    ("/geoserver/wms?REQUEST=GetFeatureInfo&LAYERS=AlmatyGIS:uzel,AstanaGIS:uzel&QUERY_LAYERS=AlmatyGIS:uzel",
     {"almaty", "astana"}, True),
    ("/geoserver/gwc/service/tms/1.0.0/Astana1%3Aheatpipesections@EPSG%3A900913@pbf/10/1/2.pbf", {"astana"}, True),
    ("/geoserver/gwc/service/wmts?REQUEST=GetCapabilities", set(), True),
    ("/geoserver/OtherProject/wms?layers=OtherProject:roads", set(), False),
])
def test_geoserver_city_detection(uri, expected, is_global):
    assert cities.geoserver_request_cities(uri) == (expected, is_global)


def test_geoserver_denied_rules():
    tile_astana = "/geoserver/AstanaGIS/gwc/service/wmts?LAYER=AstanaGIS:uzel"
    assert cities.geoserver_denied(None, tile_astana) is None
    assert "Астана" in cities.geoserver_denied(["almaty"], tile_astana)
    assert cities.geoserver_denied(["astana"], tile_astana) is None
    # слой чужого города в параметрах виртуального сервиса своего города
    assert cities.geoserver_denied(["almaty"], "/geoserver/AlmatyGIS/wms?layers=AstanaGIS:uzel")
    # тело POST к общему сервису не видно — только при доступе ко всем городам
    assert cities.geoserver_denied(["almaty"], "/geoserver/wfs", "POST")
    assert cities.geoserver_denied(["almaty"], "/geoserver/AlmatyGIS/wfs", "POST") is None
    assert cities.geoserver_denied(None, "/geoserver/wfs", "POST") is None


def test_geoserver_check_by_city(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    _status(monkeypatch, ["almaty"])
    token = create_access_token(username="ivanov", role="editor", subject="5")
    client.cookies.set("tgid_gs", token)
    own = {"X-Original-URI": "/geoserver/AlmatyGIS/gwc/service/wmts?LAYER=AlmatyGIS:uzel"}
    other = {"X-Original-URI": "/geoserver/Astana1/wms?layers=Astana1:uzel"}
    assert client.get("/auth/check", headers=own).status_code == 200
    r = client.get("/auth/check", headers=other)
    assert r.status_code == 403 and "Астана" in r.text
    post = {"X-Original-URI": "/geoserver/wfs", "X-Original-Method": "POST"}
    assert client.get("/auth/check", headers=post).status_code == 403
    # мастер-учётке — все города
    client.cookies.set("tgid_gs", master_token())
    assert client.get("/auth/check", headers=other).status_code == 200
    client.cookies.clear()
