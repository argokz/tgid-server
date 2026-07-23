"""Аутентификация: выдача JWT и информация о текущем пользователе."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app_logging import get_logger
from auth import (
    AuthUser,
    auth_disabled,
    create_access_token,
    get_current_user,
    mutations_enabled,
)
from auth_models import LoginRequest, MeResponse, TokenResponse

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/api/v1/auth/login", response_model=TokenResponse)
@router.post("/auth/login", response_model=TokenResponse)
async def auth_login(body: LoginRequest):
    """Issue JWT. Production: verify against UsersDB. Dev: DEV_LOGIN_ENABLED or AUTH_DISABLED."""
    from auth import ROLE_ORDER, _env_bool

    role = body.role if body.role in ROLE_ORDER else "viewer"
    if auth_disabled() or _env_bool("DEV_LOGIN_ENABLED", "false"):
        token = create_access_token(username=body.username, role=role)
        return TokenResponse(access_token=token, role=role, username=body.username)

    # UsersDB verification (hashed_password plaintext compare only if marked {noop}; else reject until passlib wired)
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
            if stored.startswith("{noop}"):
                if stored[6:] != body.password:
                    raise HTTPException(status_code=401, detail="Invalid credentials")
            else:
                raise HTTPException(
                    status_code=503,
                    detail="Password hashing not configured; use DEV_LOGIN_ENABLED for local or set {noop} passwords",
                )
            resolved_role = user_row.role or ("admin" if user_row.is_admin else "viewer")
            if resolved_role not in ROLE_ORDER:
                resolved_role = "admin" if user_row.is_admin else "viewer"
            token = create_access_token(username=user_row.username, role=resolved_role, subject=str(user_row.id))
            return TokenResponse(access_token=token, role=resolved_role, username=user_row.username)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Login failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="UsersDB unavailable") from exc


@router.get("/api/v1/auth/me", response_model=MeResponse)
@router.get("/auth/me", response_model=MeResponse)
async def auth_me(user: Annotated[AuthUser, Depends(get_current_user)]):
    topo = os.getenv("TOPOLOGY_MUTATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    return MeResponse(
        sub=user.sub,
        username=user.username,
        role=user.role,
        mutations_enabled=mutations_enabled(),
        topology_mutations_enabled=topo,
        auth_disabled=auth_disabled(),
    )
