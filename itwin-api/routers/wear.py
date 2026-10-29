"""Износ участков и приоритет ремонта (/api/v1/wear/*): расчёт через Celery, сводка, участки, GeoJSON."""

from __future__ import annotations

import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from audit import write_audit_log
from auth import AuthUser, require_permission, require_roles
from cities import task_queue
from database import wear
from database.connect import acquire_conn

router = APIRouter(tags=["wear"])


class WearRunBody(BaseModel):
    fragment_ids: Optional[list[int]] = Field(None, max_length=200, description="Пусто — вся сеть")
    name: Optional[str] = Field(None, max_length=200)


@router.post("/api/v1/wear/calculate")
async def wear_calculate(body: WearRunBody, user: Annotated[AuthUser, Depends(require_permission("calc_run"))]):
    """Запуск расчёта износа (Celery): шапка в calculation_iznos, строки в wear_out; статус — GET /api/v1/task/{id}."""
    from worker import run_wear_index as task_fn

    async with acquire_conn() as conn:
        if not await wear.table_exists(conn):
            raise HTTPException(status_code=503, detail="Нет таблицы wear_out: API доводит схему при старте (city_schema)")
    kwargs = {"fragment_ids": body.fragment_ids, "user": user.username, "name": body.name}
    queue = task_queue(os.getenv("HEAT_LOSSES_QUEUE") or None)
    task = task_fn.apply_async(kwargs=kwargs, queue=queue) if queue else task_fn.apply_async(kwargs=kwargs)
    await write_audit_log(changed_by=user.username, operation="RUN", table_name="wear_out",
                          new_data={"fragment_ids": body.fragment_ids, "task_id": task.id})
    return {"task_id": task.id, "status": "queued"}


@router.get("/api/v1/wear/runs")
async def wear_runs(_: Annotated[AuthUser, Depends(require_roles("viewer"))], limit: int = Query(50, ge=1, le=200)):
    async with acquire_conn() as conn:
        return {"items": await wear.list_runs(conn, limit=limit)}


@router.get("/api/v1/wear/latest")
async def wear_latest(_: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    async with acquire_conn() as conn:
        cid = await wear.latest_id(conn)
        if cid is None:
            return {"calculation_id": None}
        return await wear.summary(conn, cid)


@router.get("/api/v1/wear/{calculation_id}")
async def wear_summary(calculation_id: int, _: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    async with acquire_conn() as conn:
        try:
            return await wear.summary(conn, calculation_id)
        except wear.WearError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/v1/wear/{calculation_id}/sections")
async def wear_sections(
    calculation_id: int, _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    fragment_id: Optional[int] = Query(None, ge=1), min_category: Optional[int] = Query(None, ge=1, le=5),
    order: str = Query("priority", pattern="^(priority|wear|age|defects)$"),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
):
    async with acquire_conn() as conn:
        return await wear.sections(conn, calculation_id, fragment_id=fragment_id, min_category=min_category,
                                   order=order, limit=limit, offset=offset)


@router.get("/api/v1/wear/{calculation_id}/geojson")
async def wear_geojson(
    calculation_id: int, _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    fragment_id: Optional[int] = Query(None, ge=1), min_category: Optional[int] = Query(None, ge=1, le=5),
    limit: int = Query(20000, ge=1, le=100000),
):
    async with acquire_conn() as conn:
        return await wear.geojson(conn, calculation_id, fragment_id=fragment_id, min_category=min_category, limit=limit)


@router.delete("/api/v1/wear/{calculation_id}")
async def wear_delete(calculation_id: int, user: Annotated[AuthUser, Depends(require_permission("calc_save"))]):
    async with acquire_conn() as conn:
        n = await wear.delete_run(conn, calculation_id)
    await write_audit_log(changed_by=user.username, operation="DELETE", table_name="wear_out", record_id=calculation_id)
    return {"deleted": n}
