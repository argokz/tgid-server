"""P0 auth: JWT + RBAC roles for mutation endpoints.

Roles (least → most privilege):
  viewer      — read-only
  calculator  — run sety / engineering calcs
  editor      — journal + attribute mutations
  admin       — all of the above + topology when flag allows
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Annotated, Iterable, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    import jwt
except ImportError:  # pragma: no cover
    jwt = None  # type: ignore

try:
    from passlib.context import CryptContext
except ImportError:  # pragma: no cover
    CryptContext = None  # type: ignore

ROLE_ORDER = {"viewer": 1, "calculator": 2, "editor": 3, "admin": 4}
_DEFAULT_JWT_SECRET = "dev-insecure-change-me"

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") if CryptContext else None


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def auth_disabled() -> bool:
    """Local/dev escape hatch. Production must set AUTH_DISABLED=false."""
    return _env_bool("AUTH_DISABLED", "true")


def mutations_enabled() -> bool:
    return _env_bool("MUTATIONS_ENABLED", "false")


def auth_required_get() -> bool:
    """When true, Bearer JWT is required for GET /api/* (except public allow-list)."""
    return _env_bool("AUTH_REQUIRED_GET", "false")


def strict_auth() -> bool:
    return _env_bool("STRICT_AUTH", "false")


def auth_backend() -> str:
    """usersdb — пользователи в UsersDB (как раньше); pg — роли PostgreSQL tgid_u_* (docs/pg-auth.md)."""
    return os.getenv("AUTH_BACKEND", "usersdb").strip().lower()


def pg_auth_enabled() -> bool:
    return auth_backend() == "pg"


PG_USER_PREFIX = "tgid_u_"


def jwt_secret() -> str:
    return os.getenv("JWT_SECRET", _DEFAULT_JWT_SECRET)


def jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", "HS256")


def jwt_expire_minutes() -> int:
    try:
        return int(os.getenv("JWT_EXPIRE_MINUTES", "480"))
    except ValueError:
        return 480


@dataclass(frozen=True)
class AuthUser:
    sub: str
    role: str
    username: str
    # Предметные права пользователя-роли PostgreSQL (tgid_cap_*): network, network_struct, pts, …
    caps: frozenset = frozenset()

    def has_role(self, minimum: str) -> bool:
        return ROLE_ORDER.get(self.role, 0) >= ROLE_ORDER.get(minimum, 99)

    @property
    def is_pg_user(self) -> bool:
        return self.sub.startswith(PG_USER_PREFIX)

    def allows(self, minimum: str, cap: Optional[str] = None) -> bool:
        """Пользователь PostgreSQL: администратор или предметное право cap (как в десктопе, где
        режимщик правит сеть без веб-роли editor); без cap — минимальная роль. UsersDB — минимальная роль."""
        if cap and self.is_pg_user:
            return self.role == "admin" or cap in self.caps
        return self.has_role(minimum)


def create_access_token(
    *,
    username: str,
    role: str = "viewer",
    subject: Optional[str] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    if jwt is None:
        raise RuntimeError("PyJWT is required. Install PyJWT from requirements.txt")
    if role not in ROLE_ORDER:
        raise ValueError(f"Unknown role: {role}")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject or username,
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes or jwt_expire_minutes()),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=jwt_algorithm())


def decode_access_token(token: str) -> AuthUser:
    if jwt is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT library is not installed",
        )
    try:
        payload = jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from exc

    username = str(payload.get("username") or payload.get("sub") or "")
    role = str(payload.get("role") or "viewer")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing subject")
    if role not in ROLE_ORDER:
        role = "viewer"
    return AuthUser(sub=str(payload.get("sub") or username), role=role, username=username)


def resolve_user_role(role: Optional[str], is_admin: Optional[bool]) -> str:
    """Роль записи UsersDB: колонка role, иначе legacy is_admin → admin/viewer."""
    resolved = role or ("admin" if is_admin else "viewer")
    if resolved not in ROLE_ORDER:
        resolved = "admin" if is_admin else "viewer"
    return resolved


# Живая проверка учётной записи: блокировка и смена роли администратором действуют
# на уже выданные токены (кэш на USER_STATUS_TTL секунд, сброс при правке пользователя).
_user_status_cache: dict[object, tuple[float, Optional[tuple[bool, str]]]] = {}


def _user_status_ttl() -> float:
    try:
        return float(os.getenv("USER_STATUS_TTL", "30"))
    except ValueError:
        return 30.0


def invalidate_user_status(user_id: Optional[object] = None) -> None:
    if user_id is None:
        _user_status_cache.clear()
    else:
        _user_status_cache.pop(user_id, None)


async def _load_user_status(user_id: int) -> Optional[tuple[bool, str]]:
    """(is_active, role) из UsersDB; None — пользователя нет."""
    from sqlalchemy import select

    from database.connect import async_session
    from database.models import User

    async with async_session() as session:
        row = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if row is None:
            return None
        return bool(row.is_active), resolve_user_role(row.role, row.is_admin)


async def _load_pg_user_status(role_name: str) -> Optional[tuple]:
    """(is_active, базовая роль, предметные права) пользователя-роли PostgreSQL; None — роли нет."""
    import asyncpg

    from database.connect import acquire_conn
    from database.db_role import quote_role

    async with acquire_conn() as conn:
        async with conn.transaction():
            try:
                await conn.execute(f"SET LOCAL ROLE {quote_role(role_name)}")
            except asyncpg.InvalidParameterValueError:
                return None  # роль удалена
            row = await conn.fetchrow(
                "SELECT (m->>'is_active')::boolean AS is_active, m->>'base_role' AS base_role, "
                "ARRAY(SELECT jsonb_array_elements_text(m->'caps')) AS caps "
                "FROM (SELECT tgid_auth.me() AS m) x"
            )
    if row is None or row["base_role"] not in ROLE_ORDER:
        return False, "viewer", ()
    return bool(row["is_active"]), row["base_role"], tuple(row["caps"] or ())


async def apply_live_user_status(user: AuthUser) -> AuthUser:
    """Живая сверка учётной записи: заблокированный → 401, роль — текущая из БД.

    Токен UsersDB — sub числовой id; токен PostgreSQL — sub = роль tgid_u_*. Токены dev-login
    (sub = имя) не сверяются. Если БД недоступна — доверяем токену (подпись и срок уже
    проверены), в лог пишется предупреждение.
    """
    if not _env_bool("AUTH_LIVE_USER_CHECK", "true"):
        return user
    if user.sub.startswith(PG_USER_PREFIX):
        key: object = user.sub
        loader = lambda: _load_pg_user_status(user.sub)  # noqa: E731
    elif user.sub.isdigit():
        key = int(user.sub)
        loader = lambda: _load_user_status(int(user.sub))  # noqa: E731
    else:
        return user
    now = time.monotonic()
    cached = _user_status_cache.get(key)  # type: ignore[arg-type]
    if cached and now - cached[0] < _user_status_ttl():
        status_row = cached[1]
    else:
        try:
            status_row = await loader()
        except Exception as exc:  # noqa: BLE001
            logger.warning("User status check failed, trusting token: %s", exc)
            return user
        _user_status_cache[key] = (now, status_row)  # type: ignore[index]
    if status_row is None or not status_row[0]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Учётная запись заблокирована или удалена",
            headers={"WWW-Authenticate": "Bearer"},
        )
    caps = frozenset(status_row[2]) if len(status_row) > 2 else user.caps
    if status_row[1] != user.role or caps != user.caps:
        return AuthUser(sub=user.sub, role=status_row[1], username=user.username, caps=caps)
    return user


def db_role_for(user: Optional[AuthUser]) -> Optional[str]:
    """Роль PostgreSQL для запроса пользователя (database/db_role.py); None — роль по умолчанию."""
    if user is None or auth_disabled():
        return None
    if user.sub.startswith(PG_USER_PREFIX):
        return user.sub
    return f"tgid_{user.role}" if user.role in ROLE_ORDER else "tgid_anon"


def bind_db_role(user: Optional[AuthUser]) -> None:
    from database.db_role import set_db_role

    set_db_role(db_role_for(user))


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> AuthUser:
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await apply_live_user_status(decode_access_token(credentials.credentials))
    bind_db_role(user)
    return user


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> Optional[AuthUser]:
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    if credentials is None or not credentials.credentials:
        return None
    user = await apply_live_user_status(decode_access_token(credentials.credentials))
    bind_db_role(user)
    return user


CAP_LABELS = {
    "network": "правка гидравлической сети",
    "network_struct": "добавление и удаление объектов сети",
    "pts": "производственная служба (ПТС)",
    "corrosion": "индикаторы коррозии",
    "repairs": "ремонты",
    "acts": "акты",
    "geo": "геобаза",
}


def require_roles(*roles: str, cap: Optional[str] = None):
    """Dependency factory: user must meet the minimum of any listed role.

    cap — предметное право (AUTH_BACKEND=pg): пользователю PostgreSQL достаточно права cap
    или роли администратора; окончательно права проверяет БД (GRANT, RLS).
    """

    minimums = roles or ("viewer",)

    async def _dependency(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if any(user.allows(role, cap) for role in minimums):
            return user
        if cap and user.is_pg_user:
            detail = f"Нет права «{CAP_LABELS.get(cap, cap)}»"
        else:
            detail = f"Requires one of roles: {', '.join(minimums)} (have {user.role})"
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    return _dependency


def require_mutations_enabled() -> None:
    if not mutations_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mutations are disabled until AUTH/RBAC acceptance (MUTATIONS_ENABLED=false)",
        )


# Allow-list for generic CRUD (SQL identifier safety + domain boundary).
MUTABLE_TABLES: frozenset[str] = frozenset(
    {
        "defect",
        "shurfy",
        "osmotr",
        "remont2",
        "opres",
        "tehnicheskie_usloviya",
        "indikator_korrozii",
        "nagruzki",
        "zdaniya_2",
        "elevators",
        "dampers",
        "regularmatures",
        "bypass",
        "diaphragms",
        "pumps",
        "heatsources",
        "heatlosesmain",
        "pressregulators",
        "consumptregulators",
        "pressdropregulators",
        "istochnik_elektrosnabzheniya",
        "liniya_elektroperedach",
        "priemnik_elektrosnabzheniya",
        "kabelnyy_kanal_es",
        "mufta",
        "opora_es",
        "gilza_es",
        "nodes",
        "linesobj",
        "heatpipesections",
    }
)


def assert_mutable_table(table: str) -> str:
    normalized = table.strip()
    if not normalized or not normalized.replace("_", "").isalnum():
        raise HTTPException(status_code=400, detail="Invalid table name")
    key = normalized.lower()
    # Match case-insensitively against allow-list; return original for SQL quoting
    allowed = {t.lower(): t for t in MUTABLE_TABLES}
    if key not in allowed:
        raise HTTPException(
            status_code=403,
            detail=f"Table '{table}' is not in the mutation allow-list",
        )
    return normalized


def role_for_mutation(table: str) -> str:
    """Topology tables need admin; journals/engineering need editor."""
    if table.lower() in {"nodes", "linesobj", "heatpipesections"}:
        return "admin"
    return "editor"


# Предметные права для универсального CRUD (AUTH_BACKEND=pg) — как в sql/pg_auth/03_grants.sql
_NETWORK_TABLES = frozenset({
    "nodes", "linesobj", "heatpipesections", "heatsources", "pumps", "dampers", "regularmatures", "bypass",
    "diaphragms", "elevators", "pressregulators", "consumptregulators", "pressdropregulators",
})


def cap_for_mutation(table: str, operation: str) -> Optional[str]:
    """operation: insert / update / delete. None — достаточно роли role_for_mutation()."""
    t = table.lower()
    if t in _NETWORK_TABLES:
        return "network" if operation == "update" else "network_struct"
    if t == "remont2":
        return "repairs"
    if t == "indikator_korrozii":
        return "corrosion"
    return None


def hash_password(plain: str) -> str:
    if _pwd_context is None:
        raise RuntimeError("passlib is required. Install passlib[bcrypt] from requirements.txt")
    return "{bcrypt}" + _pwd_context.hash(plain)


def verify_password(plain: str, stored: str) -> bool:
    """Accept {noop}plaintext (legacy), {bcrypt}..., or raw bcrypt hashes."""
    if not stored:
        return False
    if stored.startswith("{noop}"):
        return stored[6:] == plain
    digest = stored[8:] if stored.startswith("{bcrypt}") else stored
    if _pwd_context is None:
        return False
    try:
        return _pwd_context.verify(plain, digest)
    except Exception:  # noqa: BLE001
        return False


def dev_login_enabled() -> bool:
    return _env_bool("DEV_LOGIN_ENABLED", "false")


def assert_production_auth_safe() -> None:
    """Fail-fast when STRICT_AUTH is on and secrets/auth are unsafe."""
    if not strict_auth():
        return
    if auth_disabled():
        raise RuntimeError("STRICT_AUTH=true forbids AUTH_DISABLED=true")
    if jwt_secret() in {"", _DEFAULT_JWT_SECRET, "change-me-to-a-long-random-string"}:
        raise RuntimeError("STRICT_AUTH=true requires a non-default JWT_SECRET")
    if dev_login_enabled():
        raise RuntimeError("STRICT_AUTH=true forbids DEV_LOGIN_ENABLED=true")


# Paths that stay public even when AUTH_REQUIRED_GET=true.
PUBLIC_GET_PREFIXES: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/fragments",
    "/russian-names",
    "/auth/config",
    "/api/v1/auth/config",
    "/auth/login",
    "/api/v1/auth/login",
)
