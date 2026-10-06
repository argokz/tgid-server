"""Права через роли PostgreSQL (sql/pg_auth/01–04) — проверка на живой копии БД.

Запуск (только копия; env из .env + .env.copy, DB_NAME должен быть копией с маркером _this_is_copy):
    PG_AUTH_TESTS=1 ./venv/Scripts/python.exe -m pytest tests/pg -q

Каждый тест — одна транзакция суперпользователя с откатом: тестовые роли (CREATE ROLE транзакционен),
пользователи tgid_auth и правки данных исчезают. Пользователь «входит» через SET ROLE, как API.
"""

from __future__ import annotations

import asyncio
import os
import uuid

import pytest

pytestmark = pytest.mark.skipif(os.getenv("PG_AUTH_TESTS") != "1", reason="PG_AUTH_TESTS=1 — тесты на копии БД")

asyncpg = pytest.importorskip("asyncpg")

from utils.scram import scram_sha256_verifier  # noqa: E402

TERRITORY = "вне вашей территории"


def _run(coro):
    return asyncio.run(coro)


async def _connect():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"), port=int(os.getenv("DB_PORT", "5440")),
        user=os.getenv("DB_USER"), password=os.getenv("DB_PASSWORD"), database=os.getenv("DB_NAME"),
    )
    marker = await conn.fetchval("SELECT to_regclass('public._this_is_copy') IS NOT NULL")
    if not marker:
        await conn.close()
        pytest.skip("DB_NAME — не копия (нет _this_is_copy): тесты прав только на копии")
    return conn


def in_tx(test):
    """Тест получает соединение внутри транзакции; в конце — ROLLBACK."""
    def wrapper():
        async def body():
            conn = await _connect()
            tx = conn.transaction()
            await tx.start()
            try:
                await test(conn)
            finally:
                await tx.rollback()
                await conn.close()
        _run(body())
    wrapper.__name__ = test.__name__
    return wrapper


async def denied(conn, exc, sql, *args, match=None):
    """Ожидаемая ошибка — в точке сохранения, чтобы не прервать транзакцию теста."""
    with pytest.raises(exc, match=match):
        async with conn.transaction():
            if sql.lstrip().upper().startswith("SELECT"):
                await conn.fetchval(sql, *args)
            else:
                await conn.execute(sql, *args)


async def make_user(conn, base: str, caps=(), fragments=(), web_access=True) -> str:
    login = f"qa_{base}_{uuid.uuid4().hex[:6]}"
    return await conn.fetchval(
        "SELECT tgid_auth._create_user('qa_test', $1, $2, $3::text[], $4::int[], NULL, NULL, $5)",
        login, base, list(caps), list(fragments), web_access)


async def as_user(conn, role: str):
    await conn.execute("RESET ROLE")
    await conn.execute(f'SET ROLE "{role}"')


async def node_in(conn, fragment: int) -> int:
    return await conn.fetchval(
        "SELECT min(id) FROM nodes WHERE fileid = $1 AND removed = 0", fragment)


async def other_fragment(conn, not_this: int) -> int:
    return await conn.fetchval(
        "SELECT fileid FROM nodes WHERE removed = 0 AND fileid <> $1 GROUP BY fileid ORDER BY count(*) DESC LIMIT 1",
        not_this)


# ── Роли и чтение ───────────────────────────────────────────────────────────────────────

@in_tx
async def test_role_hierarchy(conn):
    rows = await conn.fetch(
        "SELECT r, pg_has_role('tgid_admin', r, 'USAGE') AS admin_has FROM unnest($1::text[]) r",
        ["tgid_editor", "tgid_calculator", "tgid_viewer", "tgid_anon", "tgid_cap_network_struct", "tgid_cap_repairs"])
    assert all(r["admin_has"] for r in rows)
    assert not await conn.fetchval("SELECT pg_has_role('tgid_api', 'tgid_admin', 'USAGE')")  # NOINHERIT/INHERIT FALSE
    assert await conn.fetchval("SELECT pg_has_role('tgid_api', 'tgid_admin', 'SET')")


@in_tx
async def test_viewer_reads_but_cannot_write(conn):
    u = await make_user(conn, "viewer")
    n74 = await node_in(conn, 74)
    await as_user(conn, u)
    assert await conn.fetchval("SELECT count(*) FROM nodes WHERE id = $1", n74) == 1
    await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n74)


@in_tx
async def test_credentials_are_hidden(conn):
    u = await make_user(conn, "editor", caps=["network"])
    await as_user(conn, u)
    for sql in ("SELECT count(*) FROM passwords",
                "SELECT count(*) FROM tgid_auth.legacy_credentials",
                "SELECT count(*) FROM auth.users"):
        await denied(conn, asyncpg.InsufficientPrivilegeError, sql)
    # таблица пользователей: видна только своя строка
    assert await conn.fetchval("SELECT count(*) FROM tgid_auth.users") == 1


@in_tx
async def test_anon_and_geoserver_read_only(conn):
    n74 = await node_in(conn, 74)
    for role in ("tgid_anon", "tgid_geoserver"):
        await as_user(conn, role)
        assert await conn.fetchval("SELECT count(*) FROM nodes WHERE id = $1", n74) == 1
        await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n74)
        await denied(conn, asyncpg.InsufficientPrivilegeError, "SELECT count(*) FROM audit_log")


# ── Территория ──────────────────────────────────────────────────────────────────────────

@in_tx
async def test_editor_edits_only_own_fragments(conn):
    other = await other_fragment(conn, 74)
    n74, n_other = await node_in(conn, 74), await node_in(conn, other)
    u = await make_user(conn, "editor", caps=["network"], fragments=[74])
    await as_user(conn, u)
    assert await conn.execute("UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n74) == "UPDATE 1"
    await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n_other, match=TERRITORY)
    # перенести свой узел в чужой фрагмент тоже нельзя
    await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE nodes SET fileid = $2 WHERE id = $1", n74, other, match=TERRITORY)


@in_tx
async def test_territory_applies_to_equipment_and_journals(conn):
    # чужой фрагмент, где есть участки с трубами
    line_other = await conn.fetchval(
        "SELECT min(l.id) FROM linesobj l JOIN heatpipesections h ON h.lineid = l.id "
        "WHERE l.fileid IS NOT NULL AND l.fileid <> 74 AND l.removed = 0")
    assert line_other is not None
    u = await make_user(conn, "editor", caps=["network"], fragments=[74])
    await as_user(conn, u)
    await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE heatpipesections SET lineid = lineid WHERE lineid = $1", line_other, match=TERRITORY)
    await denied(conn, asyncpg.InsufficientPrivilegeError, "INSERT INTO shurfy (lineid) VALUES ($1)", line_other, match=TERRITORY)


@in_tx
async def test_no_scope_means_whole_network(conn):
    other = await other_fragment(conn, 74)
    n_other = await node_in(conn, other)
    u = await make_user(conn, "editor", caps=["network"])
    await as_user(conn, u)
    assert await conn.execute(
        "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n_other) == "UPDATE 1"


@in_tx
async def test_network_struct_needed_to_delete(conn):
    n74 = await node_in(conn, 74)
    u = await make_user(conn, "editor", caps=["network"], fragments=[74])
    await as_user(conn, u)
    await denied(conn, asyncpg.InsufficientPrivilegeError, "DELETE FROM nodes WHERE id = $1", n74)


@in_tx
async def test_admin_edits_everywhere(conn):
    other = await other_fragment(conn, 74)
    n_other = await node_in(conn, other)
    u = await make_user(conn, "admin", fragments=[74])  # территория администратору не мешает
    await as_user(conn, u)
    assert await conn.execute(
        "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n_other) == "UPDATE 1"


@in_tx
async def test_calculator_and_worker_write_results_only(conn):
    u = await make_user(conn, "calculator")
    n74 = await node_in(conn, 74)
    for role in (u, "tgid_worker"):
        await as_user(conn, role)
        await conn.execute("DELETE FROM ut_out WHERE calculationid = -1")  # право есть, строк нет
        await denied(conn, asyncpg.InsufficientPrivilegeError, "UPDATE nodes SET externalnodename = externalnodename WHERE id = $1", n74)


# ── История правок ──────────────────────────────────────────────────────────────────────

@in_tx
async def test_audit_records_real_user_and_cannot_be_forged(conn):
    n74 = await node_in(conn, 74)
    u = await make_user(conn, "editor", caps=["network"], fragments=[74])
    await as_user(conn, u)
    # триггер аудита пишет только реальные изменения
    await conn.execute("UPDATE nodes SET externalnodename = 'QA-3009' WHERE id = $1", n74)
    author = await conn.fetchval(
        "SELECT changed_by FROM audit_log WHERE table_name ILIKE 'nodes' AND record_id = $1 "
        "ORDER BY log_id DESC LIMIT 1", n74)
    assert author == u
    await denied(conn, asyncpg.InsufficientPrivilegeError, "INSERT INTO audit_log (operation, table_name, changed_by) VALUES ('X', 'nodes', 'postgres')")
    await denied(conn, asyncpg.InsufficientPrivilegeError, "DELETE FROM audit_log WHERE log_id = -1")


# ── Администрирование и пароли ──────────────────────────────────────────────────────────

@in_tx
async def test_only_admin_manages_users(conn):
    admin = await make_user(conn, "admin")
    editor = await make_user(conn, "editor")
    await as_user(conn, editor)
    await denied(conn, asyncpg.InsufficientPrivilegeError, "SELECT tgid_auth.create_user('qa_x', 'viewer')")
    # DEFINER-функции рядовым не выданы
    await denied(conn, asyncpg.InsufficientPrivilegeError, "SELECT tgid_auth._set_password('x', $1, $2, false)",
                 admin, scram_sha256_verifier("x" * 12))
    await as_user(conn, admin)
    login = f"qa_new_{uuid.uuid4().hex[:6]}"
    role = await conn.fetchval("SELECT tgid_auth.create_user($1, 'editor', '{repairs}', '{74}')", login)
    row = await conn.fetchrow("SELECT base_role, caps, fragments FROM tgid_auth.v_users WHERE role_name = $1", role)
    assert (row["base_role"], list(row["caps"]), list(row["fragments"])) == ("editor", ["repairs"], [74])
    await conn.execute("SELECT tgid_auth.set_active($1, false)", role)
    assert not await conn.fetchval("SELECT rolcanlogin FROM pg_roles WHERE rolname = $1", role)
    await denied(conn, asyncpg.InsufficientPrivilegeError, "SELECT tgid_auth.set_active($1, false)", admin)  # себя


@in_tx
async def test_password_only_as_scram_verifier(conn):
    u = await make_user(conn, "viewer")
    other = await make_user(conn, "viewer")
    await as_user(conn, u)
    await conn.execute("SELECT tgid_auth.set_password($1, $2)", u, scram_sha256_verifier("Новый-пароль-1"))
    assert await conn.fetchval("SELECT password_set FROM tgid_auth.users WHERE role_name = $1", u)
    await denied(conn, asyncpg.PostgresError, "SELECT tgid_auth.set_password($1, 'plain-text')", u, match="SCRAM")
    await denied(conn, asyncpg.InsufficientPrivilegeError, "SELECT tgid_auth.set_password($1, $2)", other, scram_sha256_verifier("x" * 12))


@in_tx
async def test_me_and_legacy_right(conn):
    u = await make_user(conn, "editor", caps=["network", "repairs", "corrosion"], fragments=[74, 89])
    await as_user(conn, u)
    me = await conn.fetchval("SELECT tgid_auth.me()")
    import json
    me = json.loads(me)
    assert me["base_role"] == "editor"
    assert sorted(me["fragments"]) == [74, 89]
    # не админ (2) + режимы (4) + нет актов (8) + нет геобазы (16) + без добавления/удаления (32)
    # + индикаторы (128) + веб (256) + веб-запись (512) + ремонты (1024)
    assert me["legacy_right"] == 2 + 4 + 8 + 16 + 32 + 128 + 256 + 512 + 1024
