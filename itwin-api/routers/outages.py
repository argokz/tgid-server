"""Плановые и аварийные отключения (database/outages.py).

GET    /api/v1/outages                       — список (status, open_only, q) и счётчики
GET    /api/v1/outages/geojson               — зоны открытых отключений для карты служб
GET    /api/v1/outages/{id}                  — отключение: задвижки, потребители, зона, история, пересечения
POST   /api/v1/outages                       — запланировать (участок, узел или наряд) — расчёт изоляции
PATCH  /api/v1/outages/{id}                  — изменить сроки, причину, публикацию (revision)
POST   /api/v1/outages/{id}/recompute        — пересчитать изоляцию (пока не началось)
POST   /api/v1/outages/{id}/transition       — сменить статус
GET    /api/v1/outages/{id}/announcement     — текст объявления
GET    /api/v1/outages/{id}/notification.xlsx — список потребителей для уведомления
GET    /api/v1/public/outages                — публичная лента (без входа): объявленные и идущие с public —
                                               зона и число потребителей; только при PUBLIC_OUTAGES_ENABLED=true

Чтение — вход; запись — право «Журналы» и включённые правки (MUTATIONS_ENABLED).
"""
from __future__ import annotations

import os
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import outages as og
from database.connect import acquire_conn
from database.passport_excel import XLSX_MEDIA_TYPE

router = APIRouter(tags=["outages"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
WRITE = [Depends(require_mutations_enabled)]
OutageId = Annotated[int, Path(ge=1)]


class Revision(BaseModel):
    revision: int = Field(..., ge=1)


def _http(exc: og.OutageError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def public_enabled() -> bool:
    return os.getenv("PUBLIC_OUTAGES_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


@router.get("/api/v1/outages")
async def outages_list(_: Viewer, status: Optional[str] = Query(None, max_length=20),
                       open_only: bool = Query(False), q: Optional[str] = Query(None, max_length=100)):
    try:
        async with acquire_conn() as conn:
            return await og.list_outages(conn, status=status, open_only=open_only, q=q)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/outages/geojson")
async def outages_geojson(_: Viewer):
    async with acquire_conn() as conn:
        return await og.map_geojson(conn)


@router.get("/api/v1/public/outages")
async def outages_public():
    """Публичная карта отключений (жителям, порталам акиматов): без входа, если служба это включила."""
    if not public_enabled():
        raise HTTPException(status_code=404, detail="Публичная лента отключений выключена")
    async with acquire_conn() as conn:
        return await og.map_geojson(conn, statuses=og.PUBLIC_STATUSES, public_only=True)


@router.get("/api/v1/outages/{outage_id}")
async def outage_get(outage_id: OutageId, _: Viewer):
    try:
        async with acquire_conn() as conn:
            return await og.get_outage(conn, outage_id)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/outages", dependencies=WRITE)
async def outage_create(body: og.OutageIn, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await og.create(conn, body, user.username)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.patch("/api/v1/outages/{outage_id}", dependencies=WRITE)
async def outage_update(outage_id: OutageId, body: og.OutagePatch, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await og.update(conn, outage_id, body, user.username)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/outages/{outage_id}/recompute", dependencies=WRITE)
async def outage_recompute(outage_id: OutageId, body: Revision, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await og.recompute(conn, outage_id, body.revision, user.username)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/outages/{outage_id}/transition", dependencies=WRITE)
async def outage_transition(outage_id: OutageId, body: og.OutageTransition, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await og.transition(conn, outage_id, body, user.username)
    except og.OutageError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/outages/{outage_id}/announcement")
async def outage_announcement(outage_id: OutageId, _: Viewer):
    try:
        async with acquire_conn() as conn:
            outage = await og.get_outage(conn, outage_id)
    except og.OutageError as exc:
        raise _http(exc) from exc
    return {"text": og.announcement(outage)}


@router.get("/api/v1/outages/{outage_id}/notification.xlsx")
async def outage_notification(outage_id: OutageId, _: Annotated[AuthUser, Depends(require_permission("export"))]):
    try:
        async with acquire_conn() as conn:
            outage = await og.get_outage(conn, outage_id)
    except og.OutageError as exc:
        raise _http(exc) from exc
    filename = f"Отключение {outage['number']}.xlsx"
    return Response(og.notification_workbook(outage), media_type=XLSX_MEDIA_TYPE, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    })
