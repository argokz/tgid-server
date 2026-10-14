"""Мастер-учётка владельца, защита входа от перебора, удаление пользователей (без живой БД)."""

from __future__ import annotations

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import login_guard  # noqa: E402
from auth import MASTER_SUB, create_access_token, hash_password, master_token  # noqa: E402
from database import users_admin  # noqa: E402
from routers import admin, auth_routes  # noqa: E402

MASTER_PASSWORD = "Мастер-пароль-2026"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")
    monkeypatch.setenv("AUTH_BACKEND", "usersdb")
    monkeypatch.setenv("MASTER_LOGIN", "Owner")
    monkeypatch.setenv("MASTER_PASSWORD_HASH", hash_password(MASTER_PASSWORD))
    login_guard.reset()
    app = FastAPI()
    app.include_router(auth_routes.router)
    app.include_router(admin.router)
    yield TestClient(app)
    login_guard.reset()


def _login(client, username, password, ip="203.0.113.7"):
    return client.post("/auth/login", json={"username": username, "password": password},
                       headers={"CF-Connecting-IP": ip})


def test_master_login_any_case_gives_admin(client):
    r = _login(client, "owner", MASTER_PASSWORD)
    assert r.status_code == 200, r.text
    assert r.json()["role"] == "admin" and r.json()["username"] == "Owner"
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["is_master"] is True and me.json()["role"] == "admin"


def test_master_wrong_password_never_reaches_usersdb(client, monkeypatch):
    async def boom(*_a, **_k):  # pragma: no cover - не должен вызываться
        raise AssertionError("UsersDB не должна опрашиваться для логина мастер-учётки")

    monkeypatch.setattr("database.connect.async_session", boom)
    assert _login(client, "Owner", "wrong-password").status_code == 401


def test_changed_master_password_closes_old_sessions(client, monkeypatch):
    token = _login(client, "Owner", MASTER_PASSWORD).json()["access_token"]
    monkeypatch.setenv("MASTER_PASSWORD_HASH", hash_password("другой-пароль-123"))
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401
    monkeypatch.setenv("MASTER_PASSWORD_HASH", "")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {master_token()}"}).status_code == 401


def test_forged_master_token_without_fingerprint_rejected(client):
    forged = create_access_token(username="Owner", role="admin", subject=MASTER_SUB)
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_login_throttled_after_five_failures(client):
    for _ in range(5):
        assert _login(client, "Owner", "bad").status_code == 401
    r = _login(client, "Owner", MASTER_PASSWORD)
    assert r.status_code == 429 and "Повторите" in r.json()["detail"]
    # другой адрес не заблокирован
    assert _login(client, "Owner", MASTER_PASSWORD, ip="198.51.100.2").status_code == 200


def test_master_password_not_changeable_from_web(client):
    token = _login(client, "Owner", MASTER_PASSWORD).json()["access_token"]
    r = client.post("/auth/password", json={"current_password": MASTER_PASSWORD, "new_password": "новый-пароль-1"},
                    headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 409 and "set-master-password" in r.json()["detail"]


def test_config_reports_login_requirement(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    assert client.get("/auth/config").json()["auth_required_get"] is True


@pytest.mark.asyncio
async def test_master_login_name_reserved_for_new_users(monkeypatch):
    monkeypatch.setenv("MASTER_LOGIN", "Owner")
    monkeypatch.setenv("MASTER_PASSWORD_HASH", hash_password(MASTER_PASSWORD))
    with pytest.raises(users_admin.UserAdminError) as exc:
        await users_admin.create_user("OWNER", "password-123", "viewer")
    assert exc.value.status_code == 409


def test_delete_user_endpoint(client, monkeypatch):
    calls = []

    async def fake_delete(uid, *, actor_id):
        calls.append((uid, actor_id))
        return {"id": uid, "username": "ivanov", "role": "viewer", "is_active": True, "is_admin": False}

    async def fake_audit(*_a, **_k):
        return None

    monkeypatch.setattr(admin, "delete_user", fake_delete)
    monkeypatch.setattr(admin, "_audit_users", fake_audit)
    token = master_token()
    r = client.delete("/api/v1/admin/users/12", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200 and calls == [(12, MASTER_SUB)]
    viewer = create_access_token(username="v", role="viewer", subject="v")
    assert client.delete("/api/v1/admin/users/12", headers={"Authorization": f"Bearer {viewer}"}).status_code == 403


@pytest.mark.asyncio
async def test_delete_self_refused():
    with pytest.raises(users_admin.UserAdminError) as exc:
        await users_admin.delete_user(7, actor_id="7")
    assert exc.value.status_code == 409


def test_geoserver_cookie_issued_by_me_and_checked(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    token = _login(client, "Owner", MASTER_PASSWORD).json()["access_token"]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}", "X-Forwarded-Proto": "https"})
    cookie = me.headers["set-cookie"]
    assert "tgid_gs=" in cookie and "Path=/geoserver" in cookie and "HttpOnly" in cookie and "Secure" in cookie
    client.cookies.clear()
    assert client.get("/auth/check").status_code == 401
    assert client.get("/auth/check", cookies={"tgid_gs": token}).status_code == 200
    assert client.get("/auth/check", cookies={"tgid_gs": token + "x"}).status_code == 401
    # мастер-пароль сменили — старый cookie не пускает
    monkeypatch.setenv("MASTER_PASSWORD_HASH", hash_password("другой-пароль-123"))
    assert client.get("/auth/check", cookies={"tgid_gs": token}).status_code == 401


def test_geoserver_open_while_login_not_required(client, monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED_GET", "false")
    assert client.get("/auth/check").status_code == 200
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert client.get("/auth/check").status_code == 200


def test_logout_clears_geoserver_cookie(client):
    r = client.post("/auth/logout")
    assert r.status_code == 200
    assert "tgid_gs=" in r.headers["set-cookie"] and "Max-Age=0" in r.headers["set-cookie"]
