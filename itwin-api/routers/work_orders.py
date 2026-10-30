"""Наряды и заявки (database/work_orders.py).

GET    /api/v1/work-orders/lookups          — бригады, ответственные, виды, срочность, статусы и переходы
GET    /api/v1/work-orders                  — список (status, brigade_id, fileid, q, open_only) и счётчики
GET    /api/v1/work-orders/geojson          — открытые наряды точками для карты
GET    /api/v1/work-orders/{id}             — наряд с историей
POST   /api/v1/work-orders                  — создать (по дефекту — участок, точка и описание из него)
POST   /api/v1/work-orders/field-defect     — дефект с обхода: запись в журнал дефектов и заявка по нему
PATCH  /api/v1/work-orders/{id}             — изменить (revision; закрытые и отменённые — нет)
POST   /api/v1/work-orders/{id}/transition  — сменить статус (дефект: «Ремонт» / «После ремонта»)
POST   /api/v1/work-orders/{id}/comments    — комментарий в историю
POST   /api/v1/work-orders/{id}/photos      — фото с места работ (multipart: file, caption, lon, lat, taken_at, client_id)
GET    /api/v1/work-orders/photos/{photo_id} — само фото

Чтение — вход; запись — право «Журналы» (journals), как у журналов дефектов и ремонтов.
Переход, комментарий и фото принимают client_id — ключ действия с устройства в поле: повтор отправки из очереди
(связь пропала после записи) не создаёт дубль.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Response, UploadFile
from pydantic import ValidationError

from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import work_orders as wo
from database.connect import acquire_conn

router = APIRouter(tags=["work-orders"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
# запись — ещё и при включённых правках (MUTATIONS_ENABLED), как у журналов дефектов
WRITE = [Depends(require_mutations_enabled)]
OrderId = Annotated[int, Path(ge=1)]


def _http(exc: wo.WorkOrderError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/work-orders/lookups")
async def work_order_lookups(_: Viewer):
    async with acquire_conn() as conn:
        return await wo.lookups(conn)


@router.get("/api/v1/work-orders")
async def work_orders_list(
    _: Viewer,
    status: Optional[str] = Query(None, max_length=20),
    brigade_id: Optional[int] = Query(None, ge=1),
    fileid: Optional[int] = Query(None, ge=1),
    q: Optional[str] = Query(None, max_length=100),
    open_only: bool = Query(False, description="Только заявки, назначенные и в работе"),
    limit: int = Query(500, ge=1, le=wo.MAX_LIST),
):
    try:
        async with acquire_conn() as conn:
            return await wo.list_orders(conn, status=status, brigade_id=brigade_id, fileid=fileid, q=q,
                                        open_only=open_only, limit=limit)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/work-orders/geojson")
async def work_orders_geojson(_: Viewer, open_only: bool = Query(True)):
    async with acquire_conn() as conn:
        return await wo.geojson(conn, open_only=open_only)


@router.get("/api/v1/work-orders/{order_id}")
async def work_order_get(order_id: OrderId, _: Viewer):
    try:
        async with acquire_conn() as conn:
            return await wo.get_order(conn, order_id)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/work-orders", dependencies=WRITE)
async def work_order_create(body: wo.WorkOrderIn, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await wo.create(conn, body, user.username)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/work-orders/field-defect", dependencies=WRITE)
async def work_order_field_defect(body: wo.FieldDefectIn, user: Writer):
    """«Дефект одной кнопкой» с обхода: дефект в журнал десктопа и заявка на ремонт по нему."""
    try:
        async with acquire_conn() as conn:
            try:
                async with conn.transaction():
                    order, created = await wo.report_defect(conn, body, user.username)
                    if created:
                        await write_audit_log(
                            changed_by=user.username, operation="INSERT", table_name="defect",
                            record_id=order["defect_id"], conn=conn,
                            new_data={"description": body.description.strip(), "line_id": order["line_id"],
                                      "lon": body.lon, "lat": body.lat, "work_order": order["number"],
                                      "source": "field"})
            except asyncpg.UniqueViolationError:
                # та же отправка пришла дважды одновременно: вторая упёрлась в ключ первой
                order = await wo.order_of_action(conn, body.client_id)
                if order is None:
                    raise
            return order
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.patch("/api/v1/work-orders/{order_id}", dependencies=WRITE)
async def work_order_update(order_id: OrderId, body: wo.WorkOrderPatch, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await wo.update(conn, order_id, body, user.username)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/work-orders/{order_id}/transition", dependencies=WRITE)
async def work_order_transition(order_id: OrderId, body: wo.TransitionIn, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await wo.transition(conn, order_id, body, user.username)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/work-orders/{order_id}/comments", dependencies=WRITE)
async def work_order_comment(order_id: OrderId, body: wo.CommentIn, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await wo.add_comment(conn, order_id, body, user.username)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/work-orders/{order_id}/photos", dependencies=WRITE)
async def work_order_photo_add(
    order_id: OrderId,
    user: Writer,
    file: UploadFile = File(..., description="JPEG, PNG или WebP до 2 МБ (на телефоне уменьшается заранее)"),
    caption: str = Form("", max_length=500),
    lon: Optional[float] = Form(None),
    lat: Optional[float] = Form(None),
    taken_at: Optional[datetime] = Form(None),
    client_id: Optional[UUID] = Form(None),
):
    try:
        stamp = wo.FieldStamp(client_id=client_id, lon=lon, lat=lat)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="Неверные координаты") from exc
    data = await file.read(wo.MAX_PHOTO_BYTES + 1)
    try:
        async with acquire_conn() as conn:
            return await wo.add_photo(conn, order_id, data, user.username, caption=caption, taken_at=taken_at,
                                      stamp=stamp)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/work-orders/photos/{photo_id}")
async def work_order_photo_get(photo_id: Annotated[int, Path(ge=1)], _: Viewer):
    try:
        async with acquire_conn() as conn:
            content_type, data = await wo.get_photo(conn, photo_id)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc
    # фото не меняются — кешировать можно надолго, но только в браузере пользователя
    return Response(content=data, media_type=content_type,
                    headers={"Cache-Control": "private, max-age=86400", "X-Content-Type-Options": "nosniff"})
