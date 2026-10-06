"""Роль PostgreSQL текущего запроса (sql/pg_auth, docs/pg-auth.md).

При DB_ROLE_SWITCH=true каждое соединение, выданное пулом основной базы, переключается на роль
текущего пользователя (SET ROLE в хуке setup пула — покрывает acquire_conn, pool.acquire и pool.fetch).
Права и территорию проверяет сама БД: GRANT, RLS и триггеры tgid_auth.

Какая роль:
  - пользователь вошёл (AUTH_BACKEND=pg): его роль tgid_u_<логин>;
  - пользователь UsersDB (AUTH_BACKEND=usersdb): групповая роль tgid_<viewer|calculator|editor|admin>;
  - аноним: tgid_anon (только чтение);
  - AUTH_DISABLED=true: DB_DEV_ROLE (по умолчанию tgid_admin — поведение как раньше);
  - NO_ROLE: собственный логин пула (вход: функции tgid_auth._login_info доступны только tgid_api).

Celery-воркер переключение не включает: он ходит своим логином tgid_worker.
"""

from __future__ import annotations

import os
import re
from contextvars import ContextVar, Token
from typing import Optional

NO_ROLE = ""
# имя роли — tgid_u_<логин как есть>: логины десктопа «Фамилия Имя» (пробел), UsersDB — «. @ -»
_ROLE_RE = re.compile(r"^tgid_[\w .@-]{1,58}$", re.UNICODE)

_current_role: ContextVar[Optional[str]] = ContextVar("tgid_db_role", default=None)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def role_switch_enabled() -> bool:
    return _env_bool("DB_ROLE_SWITCH")


def default_db_role() -> str:
    from auth import auth_disabled

    if auth_disabled():
        return os.getenv("DB_DEV_ROLE", "tgid_admin").strip() or "tgid_admin"
    return "tgid_anon"


def valid_role(role: str) -> bool:
    return role == NO_ROLE or bool(_ROLE_RE.match(role))


def set_db_role(role: Optional[str]) -> Token:
    if role is not None and not valid_role(role):
        raise ValueError(f"Недопустимая роль БД: {role!r}")
    return _current_role.set(role)


def reset_db_role(token: Token) -> None:
    _current_role.reset(token)


def current_db_role() -> str:
    role = _current_role.get()
    return default_db_role() if role is None else role


def quote_role(role: str) -> str:
    return '"' + role.replace('"', '""') + '"'


def role_statement(role: str) -> str:
    return "RESET ROLE" if role == NO_ROLE else f"SET ROLE {quote_role(role)}"


async def apply_db_role(conn) -> None:
    """Хук setup пула asyncpg: роль задаётся при каждой выдаче соединения."""
    if not role_switch_enabled():
        return
    role = current_db_role()
    if not valid_role(role):  # pragma: no cover — set_db_role уже проверил
        raise ValueError(f"Недопустимая роль БД: {role!r}")
    await conn.execute(role_statement(role))
