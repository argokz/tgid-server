"""Этап 7: allow-list идентификаторов SQL, флаги записи для расчётов, администрирование, audit_log.

Без живой БД: соединение подменяется фейком, который отвечает только на запросы каталога
и запоминает все SQL — так проверяется, что недопустимое имя не доходит до запроса.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import AuthUser, create_access_token  # noqa: E402
from database import sql_ident  # noqa: E402
from database.audit_history import build_filters, compute_changes  # noqa: E402
from database.sql_ident import (  # noqa: E402
    UnknownIdentifierError,
    quote_ident,
    resolve_column,
    resolve_table,
)

CATALOG = {
    "nodes": ["id", "externalcodeid", "externalnodename"],
    "defect": ["id", "name", "comment"],
    "defecttypes": ["id", "name", "ord"],
    "users": ["id", "username", "hashed_password"],
    "audit_log": ["log_id"],
}


class FakeConn:
    def __init__(self):
        self.sql: list[str] = []

    async def fetch(self, sql, *args):
        self.sql.append(sql)
        if "information_schema.tables" in sql:
            return [{"table_name": t} for t in CATALOG]
        if "information_schema.columns" in sql:
            return [{"column_name": c} for c in CATALOG.get(args[0], [])]
        return []

    async def fetchval(self, sql, *args):
        self.sql.append(sql)
        return 1

    async def execute(self, sql, *args):
        self.sql.append(sql)
        return "UPDATE 1"


@pytest.fixture
def fake_conn(monkeypatch):
    conn = FakeConn()

    @asynccontextmanager
    async def _acquire():
        yield conn

    import database.db as db

    monkeypatch.setattr(db, "acquire_conn", _acquire)
    sql_ident.reset_catalog_cache()
    yield conn
    sql_ident.reset_catalog_cache()


def _run(coro):
    return asyncio.run(coro)


def _bearer(role: str, username: str = "tester") -> dict:
    return {"Authorization": f"Bearer {create_access_token(username=username, role=role)}"}


# ---------------------------------------------------------------- sql_ident
@pytest.mark.parametrize("bad", ['nodes"; DROP TABLE nodes; --', "../../etc", "a b", "", "1abc", "x" * 64, None])
def test_quote_ident_rejects_bad_names(bad):
    with pytest.raises(UnknownIdentifierError):
        quote_ident(bad)


def test_quote_ident_quotes_valid_names():
    assert quote_ident("heatpipesections") == '"heatpipesections"'


def test_resolve_table_allow_list_and_catalog():
    sql_ident.reset_catalog_cache()
    conn = FakeConn()
    assert _run(resolve_table(conn, "NODES", {"nodes"})) == "nodes"
    for name, allowed in (
        ("missing_table", None),          # нет в каталоге
        ("defect", {"nodes"}),            # есть в каталоге, но не в allow-list эндпоинта
        ("users", None),                  # служебная таблица — запрещена всегда
        ("audit_log", {"audit_log"}),
        ('nodes"--', {"nodes"}),          # синтаксис
    ):
        with pytest.raises(UnknownIdentifierError) as exc:
            _run(resolve_table(conn, name, allowed))
        assert exc.value.kind == "table"
    sql_ident.reset_catalog_cache()


def test_resolve_column_uses_catalog():
    sql_ident.reset_catalog_cache()
    conn = FakeConn()
    assert _run(resolve_column(conn, "nodes", "ExternalCodeID")) == "externalcodeid"
    with pytest.raises(UnknownIdentifierError) as exc:
        _run(resolve_column(conn, "nodes", "hashed_password"))
    assert exc.value.kind == "column"
    sql_ident.reset_catalog_cache()


# ---------------------------------------------------------------- эндпоинты с идентификаторами из запроса
def test_card_unknown_table_is_404_without_sql(fake_conn):
    client = TestClient(main.app)
    for path in ("/line/users/1", "/node/audit_log/1", "/node/no_such_table/1", "/line/nodes%3Bdrop/1"):
        r = client.get(path)
        assert r.status_code == 404, (path, r.text)
    assert all("information_schema" in q for q in fake_conn.sql)


def test_lookup_only_for_lookup_tables_and_catalog_columns(fake_conn, monkeypatch):
    from utils.ini import storage

    monkeypatch.setattr(storage, "map_lookup", {("defect", "typeid"): ("defect", "typeid", "defecttypes", "id", "name", 1)})
    client = TestClient(main.app)
    r = client.get("/lookup", params={"table": "users", "id_col": "id", "name_col": "hashed_password"})
    assert r.status_code == 404
    r = client.get("/lookup", params={"table": "defecttypes", "id_col": "id", "name_col": 'name" FROM users --'})
    assert r.status_code == 400
    r = client.get("/lookup", params={"table": "defecttypes", "id_col": "id", "name_col": "name", "sort_col": "1"})
    assert r.status_code == 200
    data_sql = [q for q in fake_conn.sql if "information_schema" not in q]
    assert data_sql == ['SELECT "id" AS value, "name" AS title FROM "defecttypes" ORDER BY "name"']


def test_crud_rejects_unknown_columns_before_sql(fake_conn, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    client = TestClient(main.app)
    r = client.put(
        "/api/v1/update/defect/1",
        json={"fields": {'name" = 1, "id': 5}},
        headers=_bearer("editor"),
    )
    assert r.status_code == 400
    r = client.put("/api/v1/update/defect/1", json={"fields": {"nosuch": 5}}, headers=_bearer("editor"))
    assert r.status_code == 400
    assert not any(q.startswith("UPDATE") for q in fake_conn.sql)


# ---------------------------------------------------------------- расчёты, пишущие исходные данные
def test_heat_loss_run_requires_mutations_and_calculator(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    r = client.post("/api/v1/heat-losses/run", json={"fragment_id": 1}, headers=_bearer("calculator"))
    assert r.status_code == 503
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    r = client.post("/api/v1/heat-losses/run", json={"fragment_id": 1}, headers=_bearer("viewer"))
    assert r.status_code == 403
    r = client.post("/api/v1/heat-losses/run", json={"fragment_id": 1})
    assert r.status_code == 401


def test_source_writing_sety_flags_require_mutations(monkeypatch):
    from routers.calc import writes_source_data

    assert writes_source_data(["-tg", "-save_po"]) and writes_source_data(["-dross_yes"])
    assert not writes_source_data(["-tg", "-char_sety"])
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    client = TestClient(main.app)
    r = client.post("/api/v1/run-sety-cmd", json={"params": "-fileID 3 -save_po"}, headers=_bearer("calculator"))
    assert r.status_code == 503
    r = client.post(
        "/api/v1/calculations/run",
        json={"mode": "plan", "fragment_ids": [3], "save_po": True},
        headers=_bearer("calculator"),
    )
    assert r.status_code == 503


# ---------------------------------------------------------------- администрирование пользователей
def test_admin_users_only_for_admin(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    for role in ("viewer", "calculator", "editor"):
        assert client.get("/api/admin/users", headers=_bearer(role)).status_code == 403
        r = client.post(
            "/api/admin/users",
            json={"username": "bob", "password": "longpassword", "role": "admin"},
            headers=_bearer(role),
        )
        assert r.status_code == 403
    assert client.get("/api/admin/users").status_code == 401


def test_admin_user_writes_need_real_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    client = TestClient(main.app)
    r = client.post("/api/admin/users", json={"username": "bob", "password": "longpassword", "role": "viewer"})
    assert r.status_code == 503
    r = client.patch("/api/admin/users/5", json={"is_active": False})
    assert r.status_code == 503


def test_admin_create_user_validates_and_audits(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    import routers.admin as admin

    created, audited = [], []

    async def fake_create(username, password, role):
        created.append((username, role))
        return {"id": 7, "username": username, "role": role, "is_active": True, "is_admin": False}

    async def fake_audit(**kw):
        audited.append(kw)
        return "g"

    monkeypatch.setattr(admin, "create_user", fake_create)
    monkeypatch.setattr(admin, "write_audit_log", fake_audit)
    client = TestClient(main.app)
    bad = client.post("/api/admin/users", json={"username": "bob", "password": "short", "role": "viewer"},
                      headers=_bearer("admin"))
    assert bad.status_code == 422
    bad = client.post("/api/admin/users", json={"username": "bob", "password": "longpassword", "role": "root"},
                      headers=_bearer("admin"))
    assert bad.status_code == 422
    ok = client.post("/api/admin/users", json={"username": "bob", "password": "longpassword", "role": "editor"},
                     headers=_bearer("admin"))
    assert ok.status_code == 201 and created == [("bob", "editor")]
    assert "password" not in str(audited) and "longpassword" not in str(audited)


def test_live_user_status_blocks_and_downgrades(monkeypatch):
    import auth

    auth.invalidate_user_status()
    token_user = AuthUser(sub="42", role="admin", username="alice")

    async def blocked(_uid):
        return (False, "admin")

    monkeypatch.setattr(auth, "_load_user_status", blocked)
    with pytest.raises(HTTPException) as exc:
        _run(auth.apply_live_user_status(token_user))
    assert exc.value.status_code == 401

    auth.invalidate_user_status()

    async def downgraded(_uid):
        return (True, "viewer")

    monkeypatch.setattr(auth, "_load_user_status", downgraded)
    assert _run(auth.apply_live_user_status(token_user)).role == "viewer"
    # dev-login токены (sub = имя) в UsersDB не сверяются
    dev = AuthUser(sub="alice", role="editor", username="alice")
    assert _run(auth.apply_live_user_status(dev)) is dev
    auth.invalidate_user_status()


# ---------------------------------------------------------------- история правок
def test_audit_changes_diff_hides_geometry():
    changes = compute_changes(
        {"id": 1, "name": "a", "shape": "0102", "d": 100},
        {"id": 1, "name": "b", "shape": "0103", "d": 100},
    )
    assert changes == [{"field": "name", "old": "a", "new": "b"}]
    inserted = compute_changes(None, {"id": 2, "name": "x", "note": None})
    assert [c["field"] for c in inserted] == ["id", "name"]


def test_audit_filters_are_parameters_only():
    where, args = build_filters(
        table="linesObj'; drop", record_id=5, changed_by="itw", operation="update",
        date_from=date(2026, 9, 1), date_to=date(2026, 9, 27),
    )
    assert "drop" not in where and "itw" not in where
    assert args[0] == "linesObj'; drop" and args[1] == 5 and args[2] == "%itw%"
    assert where.count("$") == 6


def test_audit_log_requires_token_when_auth_on(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    assert client.get("/api/audit-log").status_code == 401
    assert client.get("/api/audit-log", params={"page_size": 500}, headers=_bearer("viewer")).status_code == 422
