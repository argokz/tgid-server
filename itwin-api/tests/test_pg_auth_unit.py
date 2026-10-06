"""Авторизация через роли PostgreSQL (AUTH_BACKEND=pg, DB_ROLE_SWITCH) — логика без БД.

Живая проверка на копии: tests/pg (PG_AUTH_TESTS=1) и docs/pg-auth.md.
"""

import asyncio
import hashlib
import re

import pytest

import auth
from audit import build_audit_insert
from database import db_role, pg_users
from database.db_errors import privilege_error_detail
from utils.scram import scram_sha256_verifier


# ── роль БД запроса ─────────────────────────────────────────────────────────────────────

def test_db_role_for_users(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    pg = auth.AuthUser(sub="tgid_u_Иванов Иван", role="editor", username="Иванов Иван")
    legacy = auth.AuthUser(sub="5", role="calculator", username="bob")
    assert auth.db_role_for(pg) == "tgid_u_Иванов Иван"
    assert auth.db_role_for(legacy) == "tgid_calculator"
    assert auth.db_role_for(None) is None
    monkeypatch.setenv("AUTH_DISABLED", "true")
    assert auth.db_role_for(pg) is None  # AUTH_DISABLED → DB_DEV_ROLE


def test_default_role_and_validation(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert db_role.default_db_role() == "tgid_anon"
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.delenv("DB_DEV_ROLE", raising=False)
    assert db_role.default_db_role() == "tgid_admin"
    assert db_role.valid_role("tgid_u_Абдрахманова Асем")
    assert db_role.valid_role(db_role.NO_ROLE)
    for bad in ("postgres", 'tgid_u_x"; DROP ROLE postgres; --', "tgid_u_" + "я" * 60):
        assert not db_role.valid_role(bad)
        with pytest.raises(ValueError):
            db_role.set_db_role(bad)
    assert db_role.role_statement('tgid_u_a"b') == 'SET ROLE "tgid_u_a""b"'
    assert db_role.role_statement(db_role.NO_ROLE) == "RESET ROLE"


class _Conn:
    def __init__(self):
        self.sql = []

    async def execute(self, sql, *args):
        self.sql.append(sql)


def test_pool_setup_sets_role_only_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    conn = _Conn()
    monkeypatch.setenv("DB_ROLE_SWITCH", "false")
    asyncio.run(db_role.apply_db_role(conn))
    assert conn.sql == []

    monkeypatch.setenv("DB_ROLE_SWITCH", "true")

    async def run(role):
        token = db_role.set_db_role(role)
        try:
            await db_role.apply_db_role(conn)
        finally:
            db_role.reset_db_role(token)

    asyncio.run(run(None))
    asyncio.run(run("tgid_u_ivanov"))
    asyncio.run(run(db_role.NO_ROLE))
    assert conn.sql == ['SET ROLE "tgid_anon"', 'SET ROLE "tgid_u_ivanov"', "RESET ROLE"]


# ── проверки API: роль и предметные права ───────────────────────────────────────────────

def test_allows_caps_for_pg_users_only():
    calc_net = auth.AuthUser(sub="tgid_u_rezh", role="calculator", username="r", caps=frozenset({"network"}))
    editor = auth.AuthUser(sub="tgid_u_ed", role="editor", username="e")
    admin = auth.AuthUser(sub="tgid_u_adm", role="admin", username="a")
    usersdb_editor = auth.AuthUser(sub="7", role="editor", username="old")
    # режимщик десктопа правит сеть без веб-роли editor
    assert calc_net.allows("editor", "network")
    assert not calc_net.allows("editor")            # журналы — нужна роль editor
    assert not editor.allows("editor", "network")   # editor без права сети
    assert editor.allows("editor")
    assert admin.allows("editor", "network_struct")
    assert usersdb_editor.allows("editor", "network")  # UsersDB — как раньше, по роли


def test_cap_for_mutation():
    assert auth.cap_for_mutation("nodes", "update") == "network"
    assert auth.cap_for_mutation("Nodes", "delete") == "network_struct"
    assert auth.cap_for_mutation("pumps", "insert") == "network_struct"
    assert auth.cap_for_mutation("remont2", "update") == "repairs"
    assert auth.cap_for_mutation("indikator_korrozii", "delete") == "corrosion"
    assert auth.cap_for_mutation("defect", "update") is None


# ── ошибки прав PostgreSQL → 403 ────────────────────────────────────────────────────────

@pytest.mark.parametrize("message, expected", [
    ("Объект вне вашей территории: фрагмент 72", "Объект вне вашей территории: фрагмент 72"),
    ("нет доступа к таблице remont2", "Недостаточно прав: ваша роль не может изменять «remont2»"),
    ("permission denied for table nodes", "Недостаточно прав: ваша роль не может изменять «nodes»"),
    ('new row violates row-level security policy for table "shurfy"',
     "Недостаточно прав: запись в «shurfy» вне вашей территории"),
    ("Требуется роль администратора", "Требуется роль администратора"),
    ("relation \"x\" does not exist", None),
])
def test_privilege_error_detail(message, expected):
    assert privilege_error_detail(message) == expected


# ── история правок: автор — роль сессии ─────────────────────────────────────────────────

def test_audit_author_current_user_when_role_switching():
    cols = {"changed_by", "operation", "table_name", "changed_at"}
    sql, args = build_audit_insert(cols, changed_by=None, operation="UPDATE", table_name="nodes",
                                   record_id=None, old_data=None, new_data=None,
                                   change_group_id="00000000-0000-0000-0000-000000000001")
    assert '"changed_by"' in sql and "current_user" in sql
    assert "UPDATE" in args and None not in args
    sql2, args2 = build_audit_insert(cols, changed_by="dev", operation="UPDATE", table_name="nodes",
                                     record_id=None, old_data=None, new_data=None,
                                     change_group_id="00000000-0000-0000-0000-000000000001")
    assert "current_user" not in sql2 and "dev" in args2


# ── вход: старые хеши и SCRAM ───────────────────────────────────────────────────────────

def test_legacy_password_matches():
    pw = "Пароль-1"
    assert pg_users.legacy_password_matches("passwords", hashlib.md5(pw.encode("utf-8")).hexdigest(), pw)
    # десктоп хешировал toLocal8Bit (cp1251)
    assert pg_users.legacy_password_matches("passwords", hashlib.md5(pw.encode("cp1251")).hexdigest().upper(), pw)
    assert not pg_users.legacy_password_matches("passwords", hashlib.md5(b"other").hexdigest(), pw)
    assert not pg_users.legacy_password_matches("passwords", "", "")  # пустой пароль не принимается
    assert pg_users.legacy_password_matches("auth", hashlib.sha256(pw.encode()).hexdigest(), pw)
    assert pg_users.legacy_password_matches("usersdb", auth.hash_password(pw), pw)
    assert not pg_users.legacy_password_matches("usersdb", auth.hash_password(pw), "wrong")


def test_scram_verifier_format():
    v = scram_sha256_verifier("секрет", salt=b"0123456789abcdef")
    # тот же формат, что принимает tgid_auth._set_password (sql/pg_auth/02_auth_schema.sql)
    assert re.fullmatch(r"SCRAM-SHA-256\$4096:[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+:[A-Za-z0-9+/=]+", v)
    assert v == scram_sha256_verifier("секрет", salt=b"0123456789abcdef")
    assert v != scram_sha256_verifier("секрет")  # соль случайная


def test_verify_pg_password_retries_reset_then_fails(monkeypatch):
    import asyncpg

    calls = []

    async def fake_connect(**kw):
        calls.append(kw["user"])
        raise OSError(64, "The specified network name is no longer available")

    monkeypatch.setattr(asyncpg, "connect", fake_connect)
    assert asyncio.run(pg_users.verify_pg_password("tgid_u_x", "pw")) is False
    assert calls == ["tgid_u_x", "tgid_u_x"]


def test_verify_pg_password_pg_hba_is_service_error(monkeypatch):
    import asyncpg

    async def fake_connect(**kw):
        raise asyncpg.InvalidAuthorizationSpecificationError('no pg_hba.conf entry for host "1.2.3.4"')

    monkeypatch.setattr(asyncpg, "connect", fake_connect)
    with pytest.raises(pg_users.PgUserError) as exc:
        asyncio.run(pg_users.verify_pg_password("tgid_u_x", "pw"))
    assert exc.value.status_code == 503
