"""Показатели эксплуатации (database/kpi.py).

GET /api/v1/kpi/dashboard        — сводка: аварийность, ремонты, наряды, отключения, сеть, износ
GET /api/v1/kpi/defects/geojson  — дефекты периода точками (месяц, категория или состояние с графика)

Фильтры как у карты: date_from / date_to (по умолчанию — последние 12 месяцев), fileid, bbox (видимая область,
«минДолгота,минШирота,максДолгота,максШирота»). Читать может любой вошедший.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import AuthUser, require_roles
from cities import cache_key
from database import kpi
from database.connect import acquire_conn

router = APIRouter(tags=["kpi"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


def _period(date_from: Optional[date], date_to: Optional[date]) -> tuple[date, date]:
    start, end = kpi.default_period()
    return date_from or start, date_to or end


@router.get("/api/v1/kpi/dashboard")
async def kpi_dashboard(
    _: Viewer,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    fileid: Optional[int] = Query(None, ge=1),
    bbox: Optional[str] = Query(None, max_length=100),
):
    try:
        start, end = _period(date_from, date_to)
        box = kpi.parse_bbox(bbox)
        async with acquire_conn() as conn:
            return await kpi.dashboard(conn, start, end, fileid=fileid, bbox=box, cache_key=cache_key())
    except kpi.KpiError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.get("/api/v1/kpi/defects/geojson")
async def kpi_defect_points(
    _: Viewer,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    month: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}$"),
    category_id: Optional[int] = Query(None, ge=0, description="0 — без категории"),
    state_id: Optional[int] = Query(None, ge=0, description="0 — без состояния"),
    fileid: Optional[int] = Query(None, ge=1),
    bbox: Optional[str] = Query(None, max_length=100),
):
    try:
        start, end = _period(date_from, date_to)
        box = kpi.parse_bbox(bbox)
        async with acquire_conn() as conn:
            return await kpi.defect_points(conn, start, end, month=month, category_id=category_id,
                                           state_id=state_id, fileid=fileid, bbox=box)
    except kpi.KpiError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
