"""Аутентификация: выдача JWT и информация о текущем пользователе."""

import os
import time
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

import cities as city_access
import login_guard
from app_logging import get_logger
from auth import (
    GEOSERVER_COOKIE,
    GEOSERVER_COOKIE_PATH,
    MASTER_SUB,
    PG_USER_PREFIX,
    AuthUser,
    ROLE_ORDER,
    auth_backend,
    auth_disabled,
    auth_required_get,
    apply_live_user_status,
    decode_access_token,
    create_access_token,
    dev_login_enabled,
    get_current_user,
    invalidate_user_status,
    is_master_login,
    master_login,
    master_token,
    mutations_enabled,
    pg_auth_enabled,
    resolve_user_role,
    security,
    strict_auth,
    verify_master_password,
    verify_password,
)
from auth_models import AuthConfigResponse, ChangePasswordRequest, LoginRequest, MeResponse, TokenResponse

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/api/v1/auth/login", response_model=TokenResponse)
@router.post("/auth/login", response_model=TokenResponse)
async def auth_login(body: LoginRequest, request: Request):
    """Issue JWT. Production: verify against UsersDB (+ passlib). Dev: DEV_LOGIN_ENABLED or AUTH_DISABLED.

    Мастер-учётка (MASTER_LOGIN/MASTER_PASSWORD_HASH) проверяется первой; после серии неудач вход
    с адреса временно закрыт (login_guard).
    """
    role = body.role if body.role in ROLE_ORDER else "viewer"
    if auth_disabled() or dev_login_enabled():
        token = create_access_token(username=body.username, role=role)
        return TokenResponse(access_token=token, role=role, username=body.username)

    ip = login_guard.client_ip(request)
    login_guard.check(ip, body.username)
    try:
        result = await _verify_login(body)
    except HTTPException as exc:
        if exc.status_code == 401:
            login_guard.record_failure(ip, body.username)
            logger.warning("Неудачный вход: логин %r, адрес %s", body.username[:64], ip)
        raise
    login_guard.record_success(ip, body.username)
    return result


async def _verify_login(body: LoginRequest) -> TokenResponse:
    if is_master_login(body.username):
        # логин мастер-учётки занят ею: в базу пользователей с ним не идём
        if not verify_master_password(body.username, body.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        logger.info("Вход мастер-учётки %s", master_login())
        return TokenResponse(access_token=master_token(), role="admin", username=master_login())

    if pg_auth_enabled():
        # Пользователь — роль PostgreSQL; пароль проверяет сам PostgreSQL (database/pg_users.py)
        from database import pg_users

        try:
            result = await pg_users.login(body.username, body.password)
        except pg_users.PgUserError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception as exc:  # noqa: BLE001
            logger.error("PG login failed: %s", exc, exc_info=True)
            raise HTTPException(status_code=503, detail="База пользователей недоступна") from exc
        token = create_access_token(
            username=result["login"], role=result["base_role"], subject=result["role_name"]
        )
        return TokenResponse(access_token=token, role=result["base_role"], username=result["login"])

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
            # пароль верный, но город этого API пользователю не открыт (users.cities)
            if not city_access.allowed(city_access.parse_stored(user_row.cities)):
                raise HTTPException(status_code=403, detail=city_access.denied_detail())
            resolved_role = resolve_user_role(user_row.role, user_row.is_admin)
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
        auth_required_get=auth_required_get(),
        dev_login_enabled=dev_login_enabled(),
        strict_auth=strict_auth(),
        mutations_enabled=mutations_enabled(),
        topology_mutations_enabled=_topology_mutations_enabled(),
        city=city_access.current_city(),
        city_label=city_access.city_label(),
    )


def _https(request: Request) -> bool:
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "").split(",")[0].strip()
    return proto.lower() == "https"


def _set_geoserver_cookie(response: Response, request: Request, token: str) -> None:
    """Cookie с тем же JWT для GeoServer (nginx auth_request) — живёт столько же, сколько токен."""
    try:
        exp = int(decode_access_token_payload_exp(token))
    except Exception:  # noqa: BLE001
        return
    max_age = exp - int(time.time())
    if max_age <= 0:
        return
    response.set_cookie(
        GEOSERVER_COOKIE, token, max_age=max_age, path=GEOSERVER_COOKIE_PATH,
        httponly=True, secure=_https(request), samesite="lax",
    )


def decode_access_token_payload_exp(token: str) -> int:
    import jwt

    from auth import jwt_algorithm, jwt_secret

    return int(jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()])["exp"])


@router.get("/api/v1/auth/me", response_model=MeResponse)
@router.get("/auth/me", response_model=MeResponse)
async def auth_me(
    user: Annotated[AuthUser, Depends(get_current_user)],
    request: Request,
    response: Response,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)] = None,
):
    # веб вызывает /auth/me после входа и при каждом открытии страницы — тут же выдаём cookie для GeoServer
    if credentials is not None and credentials.credentials and not auth_disabled():
        _set_geoserver_cookie(response, request, credentials.credentials)
    extra: dict = {"auth_backend": auth_backend(), "is_master": user.sub == MASTER_SUB}
    # города, куда пользователь может перейти: UsersDB — по users.cities, остальным — все
    user_cities = list(user.cities) if user.cities is not None else None
    extra.update(
        city=city_access.current_city(),
        city_label=city_access.city_label(),
        cities=city_access.visible_catalog(user_cities),
        all_cities=user_cities is None,
    )
    if user.sub.startswith(PG_USER_PREFIX):
        from database import pg_users

        profile = await pg_users.me(user.sub)
        extra.update(
            display_name=profile.get("display_name"),
            caps=list(profile.get("caps") or []),
            fragments=profile.get("fragments"),
            must_change_password=bool(profile.get("must_change_password")),
        )
    from permissions import ROLE_LABELS

    # действующие права (шаблон роли + отличия): веб прячет недоступные кнопки, проверяет сервер
    extra.update(permissions=user.perms.to_dict(), role_label=ROLE_LABELS.get(user.role, user.role))
    return MeResponse(
        sub=user.sub,
        username=user.username,
        role=user.role,
        mutations_enabled=mutations_enabled(),
        topology_mutations_enabled=_topology_mutations_enabled(),
        auth_disabled=auth_disabled(),
        dev_login_enabled=dev_login_enabled(),
        strict_auth=strict_auth(),
        **extra,
    )


@router.post("/api/v1/auth/password")
@router.post("/auth/password")
async def auth_change_password(
    body: ChangePasswordRequest, user: Annotated[AuthUser, Depends(get_current_user)]
):
    """Смена своего пароля: роль PostgreSQL (тот же пароль у веба и десктопа) или UsersDB."""
    if user.sub == MASTER_SUB:
        raise HTTPException(
            status_code=409,
            detail=r"Мастер-пароль меняется на сервере: H:\deploy\set-master-password.cmd",
        )
    if user.sub.isdigit():
        from database.users_admin import UserAdminError, change_own_password

        try:
            await change_own_password(int(user.sub), body.current_password, body.new_password)
        except UserAdminError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        invalidate_user_status(int(user.sub))
        return {"success": True}
    if not user.sub.startswith(PG_USER_PREFIX):
        raise HTTPException(status_code=409, detail="Смена пароля недоступна для этой учётной записи")
    from database import pg_users

    try:
        await pg_users.change_own_password(user.sub, body.current_password, body.new_password)
    except pg_users.PgUserError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    invalidate_user_status(user.sub)
    return {"success": True}


@router.post("/api/v1/auth/logout")
@router.post("/auth/logout")
async def auth_logout(response: Response):
    """Выход: убрать cookie GeoServer (сам JWT веб удаляет у себя)."""
    response.delete_cookie(GEOSERVER_COOKIE, path=GEOSERVER_COOKIE_PATH)
    return {"success": True}


@router.get("/auth/check")
async def auth_check(request: Request):
    """Доступ к GeoServer для nginx auth_request: 200 — пропустить, 401 — нет.

    Пока вход не обязателен (AUTH_DISABLED или AUTH_REQUIRED_GET=false), GeoServer открыт, как раньше —
    выключение защиты скриптом открывает и тайлы. Иначе нужен действующий JWT в cookie tgid_gs
    (или в заголовке Authorization): подпись, срок, блокировка и удаление пользователя.
    Пользователю с ограничением по городам (users.cities) — только рабочие области своих городов: 403.
    """
    if auth_disabled() or not auth_required_get():
        return Response(status_code=200)
    token = request.cookies.get(GEOSERVER_COOKIE) or ""
    header = request.headers.get("authorization") or ""
    if not token and header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()
    if not token:
        return Response(status_code=401)
    try:
        # GeoServer общий для всех городов: город API тут ни при чём — проверяем город данных запроса
        user = await apply_live_user_status(decode_access_token(token), check_city=False)
    except HTTPException:
        return Response(status_code=401)
    # исходный запрос передаёт nginx (X-Original-URI, X-Original-Method): рабочая область → город
    denied = city_access.geoserver_denied(
        user.cities,
        request.headers.get("x-original-uri") or "",
        request.headers.get("x-original-method") or "GET",
    )
    if denied:
        return Response(status_code=403, content=denied, media_type="text/plain; charset=utf-8")
    return Response(status_code=200)
