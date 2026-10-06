"""Пользователи — роли PostgreSQL tgid_u_<логин> (AUTH_BACKEND=pg; sql/pg_auth, docs/pg-auth.md).

Вход: пароль проверяет сам PostgreSQL (SCRAM) — короткое подключение под ролью пользователя, тот же
пароль, что у десктопа. Пока пароль роли не задан (перенос пользователей), принимается старый хеш:
MD5 из passwords (десктоп, UTF-8 и cp1251), bcrypt из UsersDB или sha256 из auth.users (QGIS); при успехе
пароль переносится в роль (SCRAM-верификатор), старый хеш удаляется.

Администрирование — функции tgid_auth.* под ролью администратора (SET LOCAL ROLE): права проверяет БД.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import asyncpg

from database.connect import DATABASE_CONFIG, acquire_conn
from database.db_role import NO_ROLE, quote_role, reset_db_role, set_db_role
from utils.scram import scram_sha256_verifier

logger = logging.getLogger(__name__)

BASE_ROLES = ("viewer", "calculator", "editor", "admin")
# Предметные права и их подписи — как в списке прав десктопа (gid8/gid8/any/rights.cpp)
CAPS: dict[str, str] = {
    "network": "Группа режимов: правка гидравлической сети",
    "network_struct": "Добавление и удаление объектов сети",
    "acts": "Акты раздела",
    "geo": "Геобаза",
    "pts": "Производственная служба (ПТС)",
    "corrosion": "Индикаторы коррозии",
    "repairs": "Ремонты",
}
ROLE_DESCRIPTIONS: dict[str, str] = {
    "viewer": "Просмотр карты, журналов и результатов",
    "calculator": "Просмотр + запуск расчётов (режимщик)",
    "editor": "Расчёты + правка журналов, ТУ, справочников",
    "admin": "Всё, включая топологию и управление пользователями",
}


class PgUserError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def role_for_login(login: str) -> str:
    return "tgid_u_" + login.strip()  # как tgid_auth.role_for_login


@asynccontextmanager
async def as_role(role: str):
    """Соединение, переключённое на роль на время транзакции (не зависит от DB_ROLE_SWITCH)."""
    async with acquire_conn() as conn:
        async with conn.transaction():
            await conn.execute(f"SET LOCAL ROLE {quote_role(role)}")
            yield conn


@asynccontextmanager
async def as_pool_login():
    """Соединение под собственным логином пула (tgid_api): функции входа tgid_auth._login_info."""
    token = set_db_role(NO_ROLE)
    try:
        async with acquire_conn() as conn:
            yield conn
    finally:
        reset_db_role(token)


# ── Вход ────────────────────────────────────────────────────────────────────────────────

def _md5_matches(password: str, stored: str) -> bool:
    want = (stored or "")[:32].lower()
    if len(want) != 32:
        return False
    for enc in ("utf-8", "cp1251"):  # десктоп хеширует toLocal8Bit (cp1251), GeoServer — UTF-8
        try:
            got = hashlib.md5(password.encode(enc)).hexdigest()
        except UnicodeEncodeError:
            continue
        if hmac.compare_digest(got, want):
            return True
    return False


def legacy_password_matches(source: str, stored: str, password: str) -> bool:
    if not password or not stored:
        return False
    if source == "passwords":
        return _md5_matches(password, stored)
    if source == "auth":
        return hmac.compare_digest(hashlib.sha256(password.encode("utf-8")).hexdigest(), stored.lower())
    if source == "usersdb":
        from auth import verify_password

        return verify_password(password, stored)
    return False


async def verify_pg_password(role: str, password: str) -> bool:
    """Пароль проверяет PostgreSQL: подключение под ролью пользователя."""
    for attempt in (1, 2):
        try:
            conn = await asyncpg.connect(
                host=DATABASE_CONFIG["host"], port=DATABASE_CONFIG["port"],
                database=DATABASE_CONFIG["database"], user=role, password=password, timeout=10,
            )
        except asyncpg.InvalidPasswordError:
            return False
        except asyncpg.InvalidAuthorizationSpecificationError as exc:
            text = str(exc)
            if "pg_hba" in text:
                logger.error("pg_hba не разрешает вход пользователей tgid_users: %s", text)
                raise PgUserError(503, "Сервер БД не разрешает вход пользователей (pg_hba: +tgid_users)") from exc
            return False  # роль заблокирована (NOLOGIN) и т. п.
        except (asyncpg.ConnectionDoesNotExistError, ConnectionResetError, OSError) as exc:
            # Windows: после отказа в пароле сервер закрывает соединение раньше, чем asyncpg прочтёт
            # ответ (WinError 64). Пул основной базы при этом работает — повтор, затем «неверный пароль».
            if attempt == 1:
                continue
            logger.warning("Проверка пароля %s: соединение закрыто сервером (%s) — считаем отказом", role, exc)
            return False
        await conn.close()
        return True
    return False


async def login(login_name: str, password: str) -> dict[str, Any]:
    """Проверка логина и пароля; {role_name, login, base_role} или PgUserError(401/403)."""
    if not login_name.strip() or not password:
        raise PgUserError(401, "Неверный логин или пароль")
    async with as_pool_login() as conn:
        rows = await conn.fetch("SELECT * FROM tgid_auth._login_info($1)", login_name)
    if not rows:
        raise PgUserError(401, "Неверный логин или пароль")
    info = rows[0]
    role = info["role_name"]
    if not info["is_active"] or not info["can_login"]:
        raise PgUserError(401, "Учётная запись заблокирована")

    if info["password_set"]:
        ok = await verify_pg_password(role, password)
    else:
        ok = any(legacy_password_matches(r["legacy_source"], r["legacy_hash"], password)
                 for r in rows if r["legacy_source"])
        if ok:
            async with as_pool_login() as conn:
                await conn.execute("SELECT tgid_auth._migrate_password($1, $2)",
                                   role, scram_sha256_verifier(password))
            logger.info("Пароль пользователя %s перенесён в роль PostgreSQL", role)
    if not ok:
        raise PgUserError(401, "Неверный логин или пароль")
    if not info["web_access"]:
        raise PgUserError(403, "Нет доступа к веб-приложению (право «Веб приложение»)")
    profile = await me(role)
    return {"role_name": role, "login": profile.get("login") or login_name,
            "base_role": profile.get("base_role") or "viewer", "profile": profile}


async def me(role: str) -> dict[str, Any]:
    async with as_role(role) as conn:
        raw = await conn.fetchval("SELECT tgid_auth.me()")
    return json.loads(raw) if isinstance(raw, str) else dict(raw or {})


async def change_own_password(role: str, current_password: str, new_password: str) -> None:
    if not await verify_pg_password(role, current_password):
        raise PgUserError(401, "Текущий пароль неверен")
    async with as_role(role) as conn:
        await conn.execute("SELECT tgid_auth.set_password(current_user, $1)",
                           scram_sha256_verifier(new_password))


# ── Администрирование (под ролью администратора — права проверяет БД) ───────────────────

def roles_catalog() -> list[dict[str, Any]]:
    return [{"role": r, "description": ROLE_DESCRIPTIONS[r]} for r in BASE_ROLES]


def caps_catalog() -> list[dict[str, Any]]:
    return [{"cap": c, "description": d} for c, d in CAPS.items()]


def _user_row(r: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": r["role_name"],
        "role_name": r["role_name"],
        "username": r["login"],
        "display_name": r["display_name"],
        "full_name": r["full_name"],
        "role": r["base_role"],
        "caps": list(r["caps"] or []),
        "fragments": list(r["fragments"] or []),
        "is_active": bool(r["is_active"]) and bool(r["can_login"]),
        "web_access": bool(r["web_access"]),
        "password_set": bool(r["password_set"]),
        "must_change_password": bool(r["must_change_password"]),
        "legacy_right": r["legacy_right"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
    }


async def list_users(admin_role: str) -> list[dict[str, Any]]:
    async with as_role(admin_role) as conn:
        rows = await conn.fetch("SELECT * FROM tgid_auth.v_users ORDER BY login")
    return [_user_row(r) for r in rows]


async def get_user(admin_role: str, role: str) -> dict[str, Any]:
    async with as_role(admin_role) as conn:
        row = await conn.fetchrow("SELECT * FROM tgid_auth.v_users WHERE role_name = $1", role)
    if row is None:
        raise PgUserError(404, "Пользователь не найден")
    return _user_row(row)


def _check(base: Optional[str], caps: Optional[list[str]]) -> None:
    if base is not None and base not in BASE_ROLES:
        raise PgUserError(422, f"Неизвестная роль: {base}")
    unknown = [c for c in (caps or []) if c not in CAPS]
    if unknown:
        raise PgUserError(422, f"Неизвестные права: {', '.join(unknown)}")


async def create_user(admin_role: str, *, login: str, password: Optional[str], base_role: str,
                      caps: list[str], fragments: list[int], display_name: Optional[str] = None,
                      full_name: Optional[str] = None, web_access: bool = True) -> dict[str, Any]:
    _check(base_role, caps)
    async with as_role(admin_role) as conn:
        try:
            role = await conn.fetchval(
                "SELECT tgid_auth.create_user($1, $2, $3::text[], $4::int[], $5, $6, $7)",
                login, base_role, caps, fragments, display_name, full_name, web_access)
        except asyncpg.UniqueViolationError as exc:
            raise PgUserError(409, f"Пользователь {login} уже есть") from exc
        except asyncpg.InvalidParameterValueError as exc:
            raise PgUserError(422, str(exc)) from exc
        if password:
            await conn.execute("SELECT tgid_auth.set_password($1, $2, true)", role,
                               scram_sha256_verifier(password))
    return await get_user(admin_role, role)


async def update_user(admin_role: str, role: str, *, base_role: Optional[str] = None,
                      caps: Optional[list[str]] = None, fragments: Optional[list[int]] = None,
                      display_name: Optional[str] = None, full_name: Optional[str] = None,
                      web_access: Optional[bool] = None, is_active: Optional[bool] = None) -> dict[str, Any]:
    _check(base_role, caps)
    # БД переназначает роль и права вместе: недостающее — из текущего профиля
    if (base_role is None) != (caps is None):
        current = await get_user(admin_role, role)
        base_role = base_role or current["role"]
        caps = caps if caps is not None else current["caps"]
    async with as_role(admin_role) as conn:
        try:
            await conn.execute(
                "SELECT tgid_auth.update_user($1, $2, $3::text[], $4::int[], $5, $6, $7)",
                role, base_role, caps, fragments, display_name, full_name, web_access)
            if is_active is not None:
                await conn.execute("SELECT tgid_auth.set_active($1, $2)", role, is_active)
        except asyncpg.NoDataFoundError as exc:
            raise PgUserError(404, "Пользователь не найден") from exc
        except asyncpg.InvalidParameterValueError as exc:
            raise PgUserError(422, str(exc)) from exc
    return await get_user(admin_role, role)


async def set_password(admin_role: str, role: str, password: str, must_change: bool = True) -> None:
    async with as_role(admin_role) as conn:
        try:
            await conn.execute("SELECT tgid_auth.set_password($1, $2, $3)", role,
                               scram_sha256_verifier(password), must_change)
        except asyncpg.NoDataFoundError as exc:
            raise PgUserError(404, "Пользователь не найден") from exc
