"""Вебхуки (database/webhooks.py, database/api_events.py) — подписки внешних систем, только администратор.

GET    /api/v1/webhooks/event-types              — типы событий
GET    /api/v1/webhooks                          — подписки города с числом доставок
POST   /api/v1/webhooks                          — новая подписка; секрет подписи — в ответе, один раз
PATCH  /api/v1/webhooks/{id}                     — название, адрес, события, вкл/выкл
DELETE /api/v1/webhooks/{id}                     — удалить с журналом доставок
POST   /api/v1/webhooks/{id}/secret              — новый секрет (старый перестаёт действовать сразу)
POST   /api/v1/webhooks/{id}/test                — событие ping сейчас, с ответом адреса
GET    /api/v1/webhooks/{id}/deliveries          — последние доставки (status: pending, ok, failed)
POST   /api/v1/webhooks/deliveries/{id}/retry    — отправить доставку ещё раз
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

import activity
from auth import AuthUser, require_roles
from cities import current_city
from database import api_events
from database import webhooks as wh
from database.connect import acquire_conn

router = APIRouter(tags=["webhooks"])
Admin = Annotated[AuthUser, Depends(require_roles("admin"))]
HookId = Annotated[int, Path(ge=1)]


def _http(exc: wh.WebhookError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _safe_url(url: str) -> str:
    """Адрес для журнала действий — без параметров: в них бывает ключ получателя (?token=…)."""
    return url.split("?", 1)[0]


async def _audit(request: Request, user: AuthUser, action: str, details: dict[str, Any]) -> None:
    await activity.write(username=user.username, action=action, method=request.method, path=request.url.path,
                         status=200, details=details, ip=activity.client_ip(request.scope),
                         user_agent=request.headers.get("user-agent", "")[:300])


@router.get("/api/v1/webhooks/event-types")
async def webhook_event_types(_: Admin) -> list[dict[str, str]]:
    return [{"type": k, "label": v} for k, v in api_events.EVENT_TYPES.items()]


@router.get("/api/v1/webhooks")
async def webhooks_list(_: Admin) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await wh.list_hooks(conn)


@router.post("/api/v1/webhooks")
async def webhook_create(body: wh.WebhookIn, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await wh.create_hook(conn, body, user.username)
    except wh.WebhookError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "WEBHOOK_CREATE", {"id": out["id"], "name": out["name"], "url": _safe_url(out["url"]),
                                                   "events": out["events"]})
    return out


@router.patch("/api/v1/webhooks/{hook_id}")
async def webhook_update(hook_id: HookId, body: wh.WebhookPatch, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await wh.update_hook(conn, hook_id, body)
    except wh.WebhookError as exc:
        raise _http(exc) from exc
    details = body.model_dump(exclude_none=True)
    if "url" in details:
        details["url"] = _safe_url(details["url"])
    await _audit(request, user, "WEBHOOK_UPDATE", {"id": hook_id, **details})
    return out


@router.delete("/api/v1/webhooks/{hook_id}")
async def webhook_delete(hook_id: HookId, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await wh.delete_hook(conn, hook_id)
    except wh.WebhookError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "WEBHOOK_DELETE", out)
    return out


@router.post("/api/v1/webhooks/{hook_id}/secret")
async def webhook_rotate_secret(hook_id: HookId, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await wh.rotate_secret(conn, hook_id)
    except wh.WebhookError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "WEBHOOK_SECRET", {"id": hook_id, "name": out["name"]})
    return out


@router.post("/api/v1/webhooks/{hook_id}/test")
async def webhook_test(hook_id: HookId, _: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await wh.test_hook(conn, hook_id, current_city())
    except wh.WebhookError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/webhooks/{hook_id}/deliveries")
async def webhook_deliveries(hook_id: HookId, _: Admin,
                             status: Optional[Literal["pending", "ok", "failed"]] = None,
                             limit: int = Query(100, ge=1, le=500)) -> list[dict[str, Any]]:
    try:
        async with acquire_conn() as conn:
            return await wh.deliveries(conn, hook_id, status=status, limit=limit)
    except wh.WebhookError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/webhooks/deliveries/{delivery_id}/retry")
async def webhook_retry(delivery_id: Annotated[int, Path(ge=1)], request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await wh.retry_delivery(conn, delivery_id)
    except wh.WebhookError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "WEBHOOK_RETRY", out)
    return out
