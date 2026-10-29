"""MCP-сервер ТГИД (tgid_mcp) по HTTP и токены ИИ-клиентов.

POST /mcp                — JSON-RPC MCP (Streamable HTTP, ответ application/json, без сессий); в режиме
                           нескольких городов — /city/<код>/mcp, за nginx — /tgid/<город>/map-api/mcp
GET|DELETE /mcp          — 405: потока событий и сессий у сервера нет
POST /api/v1/mcp/token   — токен ИИ-клиента (scope mcp, MCP_TOKEN_DAYS дней): действует только на /mcp
GET  /api/v1/mcp/info    — включён ли MCP, инструменты и срок токена (кабинет веба)

Вход — Bearer: токен сессии веба или токен ИИ-клиента. Права в инструментах — пользователя токена;
заблокированный пользователь теряет доступ сразу (живая проверка, как у веба). У пользователя UsersDB токен
ИИ-клиента несёт отпечаток хеша пароля: смена пароля закрывает все его токены; UsersDB недоступна — вход
закрыт (а не «доверяем токену»). MCP_ENABLED=false — выключен.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

import jwt

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

import activity
from auth import (
    MCP_SCOPE,
    AuthUser,
    apply_live_user_status,
    auth_disabled,
    bind_db_role,
    create_access_token,
    decode_access_token,
    get_current_user,
    jwt_algorithm,
    jwt_secret,
)
from tgid_mcp import protocol
from tgid_mcp.tools import TOOLS

router = APIRouter(tags=["mcp"])

MAX_BODY_BYTES = 1_000_000
# пакет сообщений (2025-03-26; в 2025-06-18 убран): небольшой — иначе один запрос обходит лимиты nginx
MAX_BATCH = 10
PASSWORD_CLAIM = "pwf"
DEFAULT_TOKEN_DAYS = 30
MAX_TOKEN_DAYS = 90


def mcp_enabled() -> bool:
    return os.getenv("MCP_ENABLED", "true").strip().lower() in ("1", "true", "yes", "on")


def mcp_token_days() -> int:
    try:
        days = int(os.getenv("MCP_TOKEN_DAYS", str(DEFAULT_TOKEN_DAYS)))
    except ValueError:
        days = DEFAULT_TOKEN_DAYS
    return max(1, min(MAX_TOKEN_DAYS, days))


def _allowed_origins() -> set[str]:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "https://itwin.kz,http://localhost:3000,http://localhost:3007")
    return {o.strip() for o in raw.split(",") if o.strip()}


def _client(request: Request) -> dict[str, str]:
    return {"ip": activity.client_ip(request.scope), "user_agent": request.headers.get("user-agent", "")[:300]}


async def _unauthorized(request: Request, detail: str) -> JSONResponse:
    await activity.write(username=None, action="MCP", method="POST", path="/mcp", status=401,
                         details={"denied": detail}, **_client(request))
    return JSONResponse(status_code=401, content={"detail": detail}, headers={"WWW-Authenticate": "Bearer"})


async def _password_fingerprint(sub: str) -> Optional[str]:
    """Отпечаток хеша пароля пользователя UsersDB (HMAC с JWT_SECRET); у прочих (роль PostgreSQL,
    мастер-учётка — у неё свой отпечаток mv) — None. Ошибка UsersDB — исключение: вход закрыт."""
    if not sub.isdigit():
        return None
    from sqlalchemy import select

    from database.connect import async_session
    from database.models import User

    async with async_session() as session:
        hashed = (await session.execute(select(User.hashed_password).where(User.id == int(sub)))).scalar_one_or_none()
    if not hashed:
        return None
    return hmac.new(jwt_secret().encode(), hashed.encode(), hashlib.sha256).hexdigest()[:24]


async def _mcp_user(request: Request) -> AuthUser:
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Нужен заголовок Authorization: Bearer <токен ИИ-клиента>")
    token = header.split(" ", 1)[1].strip()
    user = decode_access_token(token, allow_scopes=(MCP_SCOPE,))
    user = await apply_live_user_status(user)
    if user.scope == MCP_SCOPE:
        claim = str(jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()]).get(PASSWORD_CLAIM) or "")
        try:
            current = await _password_fingerprint(user.sub)
        except Exception as exc:  # noqa: BLE001 — долгий токен без проверки не пускаем
            raise HTTPException(status_code=401, detail="Не удалось проверить токен — попробуйте позже") from exc
        if current is not None and not hmac.compare_digest(claim, current):
            raise HTTPException(status_code=401, detail="Пароль сменён — выдайте новый токен ИИ-клиента")
    bind_db_role(user)
    return user


@router.post("/mcp", include_in_schema=False)
async def mcp_post(request: Request):
    if not mcp_enabled():
        raise HTTPException(status_code=404, detail="MCP выключен (MCP_ENABLED)")
    # защита от DNS rebinding (требование спецификации): чужой сайт в браузере не достучится
    origin = request.headers.get("origin")
    if origin and origin not in _allowed_origins():
        return JSONResponse(status_code=403, content={"detail": "Origin не разрешён"})
    version = request.headers.get("mcp-protocol-version")
    if version and version not in protocol.PROTOCOL_VERSIONS:
        return JSONResponse(status_code=400, content={"detail": f"Версия MCP {version} не поддерживается"})
    try:
        user = await _mcp_user(request)
    except HTTPException as exc:
        if exc.status_code == 401:
            return await _unauthorized(request, str(exc.detail))
        raise
    too_big = JSONResponse(status_code=413, content=protocol.error_response(
        None, protocol.INVALID_REQUEST, "Сообщение больше 1 МБ"))
    try:
        if int(request.headers.get("content-length") or 0) > MAX_BODY_BYTES:
            return too_big
    except ValueError:
        return JSONResponse(status_code=400, content={"detail": "Неверный Content-Length"})
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_BODY_BYTES:
            return too_big
    try:
        message = json.loads(bytes(body))
    except (ValueError, UnicodeDecodeError, RecursionError):
        return JSONResponse(status_code=400, content=protocol.error_response(
            None, protocol.PARSE_ERROR, "Тело запроса — не JSON"))
    client = _client(request)
    if isinstance(message, list):
        # пакет (2025-03-26): ответы на запросы пакета, уведомления — без ответа
        if not message or len(message) > MAX_BATCH:
            return JSONResponse(status_code=400, content=protocol.error_response(
                None, protocol.INVALID_REQUEST, f"Пакет — от 1 до {MAX_BATCH} сообщений"))
        replies = [r for r in [await protocol.handle_message(m, user, client) for m in message] if r is not None]
        return JSONResponse(replies) if replies else Response(status_code=202)
    reply = await protocol.handle_message(message, user, client)
    if reply is None:
        return Response(status_code=202)
    return JSONResponse(reply)


@router.get("/mcp", include_in_schema=False)
@router.delete("/mcp", include_in_schema=False)
async def mcp_no_stream():
    return Response(status_code=405, headers={"Allow": "POST"})


@router.get("/api/v1/mcp/info")
async def mcp_info(user: Annotated[AuthUser, Depends(get_current_user)]):
    return {
        "enabled": mcp_enabled(),
        "token_days": mcp_token_days(),
        "path": "/mcp",
        "tools": [{"name": t.name, "title": t.title, "permission": t.permission} for t in TOOLS.values()],
    }


@router.post("/api/v1/mcp/token")
async def mcp_token(request: Request, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Токен ИИ-клиента на MCP_TOKEN_DAYS дней. Действует только на /mcp; права — пользователя;
    у пользователя UsersDB смена пароля закрывает токен."""
    if not mcp_enabled():
        raise HTTPException(status_code=404, detail="MCP выключен (MCP_ENABLED)")
    days = mcp_token_days()
    extra: dict[str, Any] = {"scope": MCP_SCOPE}
    if user.mv:
        extra["mv"] = user.mv
    fingerprint = await _password_fingerprint(user.sub)
    if fingerprint:
        extra[PASSWORD_CLAIM] = fingerprint
    token = create_access_token(username=user.username, role=user.role, subject=user.sub,
                                expires_minutes=days * 24 * 60, extra=extra)
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)
    await activity.write(username=user.username, action="MCP_TOKEN", method="POST", path="/api/v1/mcp/token",
                         status=200, details={"days": days}, **_client(request))
    return {"token": token, "expires_at": expires_at.isoformat(timespec="seconds"), "days": days, "path": "/mcp"}
