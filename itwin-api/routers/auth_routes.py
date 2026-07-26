"""Аутентификация: выдача JWT и информация о текущем пользователе."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app_logging import get_logger
from auth import (
    AuthUser,
    ROLE_ORDER,
    auth_disabled,
    create_access_token,
    dev_login_enabled,
    get_current_user,
    mutations_enabled,
    strict_auth,
    verify_password,
)
from auth_models import AuthConfigResponse, LoginRequest, MeResponse, TokenResponse

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/api/v1/auth/login", response_model=TokenResponse)
@router.post("/auth/login", response_model=TokenResponse)
async def auth_login(body: LoginRequest):
    """Issue JWT. Production: verify against UsersDB (+ passlib). Dev: DEV_LOGIN_ENABLED or AUTH_DISABLED."""
    role = body.role if body.role in ROLE_ORDER else "viewer"
    if auth_disabled() or dev_login_enabled():
        token = create_access_token(username=body.username, role=role)
        return TokenResponse(access_token=token, role=role, username=body.username)

    # UsersDB verification
    try:
        from database.connect import async_session
        from database.models import User
        from sqlalchemy import select

        async with async_session() as session:
            result = await session.execute(select(User).where(User.username == body.username))
            user_row = result.scalar_one_or_none()
            if user_row is None or not user_row.is_active:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            stored = user_row.hashed_password or ""
            if not verify_password(body.password, stored):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            resolved_role = user_row.role or ("admin" if user_row.is_admin else "viewer")
            if resolved_role not in ROLE_ORDER:
                resolved_role = "admin" if user_row.is_admin else "viewer"
            # Client cannot escalate role when auth is on
            token = create_access_token(
                username=user_row.username,
                role=resolved_role,
                subject=str(user_row.id),
            )
            return TokenResponse(
                access_token=token,
                role=resolved_role,
                username=user_row.username,
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="UsersDB unavailable") from exc


def _topology_mutations_enabled() -> bool:
    return os.getenv("TOPOLOGY_MUTATIONS_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@router.get("/api/v1/auth/config", response_model=AuthConfigResponse)
@router.get("/auth/config", response_model=AuthConfigResponse)
async def auth_config():
    """Public flags for login UI (role picker only when DEV_LOGIN)."""
    return AuthConfigResponse(
        auth_disabled=auth_disabled(),
        dev_login_enabled=dev_login_enabled(),
        strict_auth=strict_auth(),
        mutations_enabled=mutations_enabled(),
        topology_mutations_enabled=_topology_mutations_enabled(),
    )


@router.get("/api/v1/auth/me", response_model=MeResponse)
@router.get("/auth/me", response_model=MeResponse)
async def auth_me(user: Annotated[AuthUser, Depends(get_current_user)]):
    return MeResponse(
        sub=user.sub,
        username=user.username,
        role=user.role,
        mutations_enabled=mutations_enabled(),
        topology_mutations_enabled=_topology_mutations_enabled(),
        auth_disabled=auth_disabled(),
        dev_login_enabled=dev_login_enabled(),
        strict_auth=strict_auth(),
    )
