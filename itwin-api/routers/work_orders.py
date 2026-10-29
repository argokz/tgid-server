"""Наряды и заявки (database/work_orders.py).

GET    /api/v1/work-orders/lookups          — бригады, ответственные, виды, срочность, статусы и переходы
GET    /api/v1/work-orders                  — список (status, brigade_id, fileid, q, open_only) и счётчики
GET    /api/v1/work-orders/geojson          — открытые наряды точками для карты
GET    /api/v1/work-orders/{id}             — наряд с историей
POST   /api/v1/work-orders                  — создать (по дефекту — участок, точка и описание из него)
PATCH  /api/v1/work-orders/{id}             — изменить (revision; закрытые и отменённые — нет)
POST   /api/v1/work-orders/{id}/transition  — сменить статус (дефект: «Ремонт» / «После ремонта»)
POST   /api/v1/work-orders/{id}/comments    — комментарий в историю

Чтение — вход; запись — право «Журналы» (journals), как у журналов дефектов и ремонтов.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import work_orders as wo
from database.connect import acquire_conn

router = APIRouter(tags=["work-orders"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
# запись — ещё и при включённых правках (MUTATIONS_ENABLED), как у журналов дефектов
WRITE = [Depends(require_mutations_enabled)]
OrderId = Annotated[int, Path(ge=1)]


class CommentIn(BaseModel):
    note: str = Field(..., min_length=1, max_length=2000)


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
async def work_order_comment(order_id: OrderId, body: CommentIn, user: Writer):
    try:
        async with acquire_conn() as conn:
            return await wo.add_comment(conn, order_id, body.note, user.username)
    except wo.WorkOrderError as exc:
        raise _http(exc) from exc
