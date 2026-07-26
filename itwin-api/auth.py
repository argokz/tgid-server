"""P0 auth: JWT + RBAC roles for mutation endpoints.

Roles (least → most privilege):
  viewer      — read-only
  calculator  — run sety / engineering calcs
  editor      — journal + attribute mutations
  admin       — all of the above + topology when flag allows
"""

from __future__ import annotations

import os
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

    def has_role(self, minimum: str) -> bool:
        return ROLE_ORDER.get(self.role, 0) >= ROLE_ORDER.get(minimum, 99)


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
    return decode_access_token(credentials.credentials)


async def get_optional_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
) -> Optional[AuthUser]:
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    if credentials is None or not credentials.credentials:
        return None
    return decode_access_token(credentials.credentials)


def require_roles(*roles: str):
    """Dependency factory: user must meet the minimum of any listed role."""

    minimums = roles or ("viewer",)

    async def _dependency(user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
        if any(user.has_role(role) for role in minimums):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {', '.join(minimums)} (have {user.role})",
        )

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
