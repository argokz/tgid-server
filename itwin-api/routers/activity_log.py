"""Журнал действий пользователей (activity.py): просмотр с фильтрами и выгрузка CSV.

Право — «Просмотр журнала действий» (permissions.GENERAL audit_view).
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select

from activity import ACTION_LABELS
from app_logging import get_logger
from auth import AuthUser, require_permission
from database.connect import async_session
from database.models import ActivityLog

logger = get_logger(__name__)
router = APIRouter(tags=["activity-log"])
Viewer = Annotated[AuthUser, Depends(require_permission("audit_view"))]
CSV_LIMIT = 50000


def _filters(username, action, city, date_from, date_to, q, failed):
    conds = []
    if username:
        conds.append(ActivityLog.username == username)
    if action:
        conds.append(ActivityLog.action == action)
    if city:
        conds.append(ActivityLog.city == city)
    if date_from:
        conds.append(ActivityLog.at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        conds.append(ActivityLog.at < datetime.combine(date_to + timedelta(days=1), datetime.min.time()))
    if q:
        like = f"%{q}%"
        conds.append(or_(ActivityLog.username.ilike(like), ActivityLog.path.ilike(like), ActivityLog.ip.ilike(like),
                         ActivityLog.details.ilike(like)))
    if failed:
        conds.append(ActivityLog.status >= 400)
    return conds


def _row(r: ActivityLog) -> dict:
    return {
        "id": r.id, "at": r.at.isoformat(timespec="seconds") if r.at else None, "username": r.username,
        "city": r.city, "action": r.action, "action_label": ACTION_LABELS.get(r.action, r.action),
        "method": r.method, "path": r.path, "status": r.status, "duration_ms": r.duration_ms,
        "ip": r.ip, "user_agent": r.user_agent, "details": r.details,
    }



@router.get("/api/v1/activity-log")
async def activity_log(
    _: Viewer,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    username: Optional[str] = Query(None, max_length=100),
    action: Optional[str] = Query(None, max_length=20),
    city: Optional[str] = Query(None, max_length=20),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    q: Optional[str] = Query(None, max_length=100, description="поиск по пользователю, адресу запроса, IP, подробностям"),
    failed: bool = Query(False, description="только с ошибкой (статус ≥ 400)"),
):
    """Журнал действий: новые сверху; total — всего по фильтру; lookups — пользователи и действия."""
    conds = _filters(username, action, city, date_from, date_to, q, failed)
    try:
        async with async_session() as s:
            total = (await s.execute(select(func.count()).select_from(ActivityLog).where(*conds))).scalar_one()
            rows = (await s.execute(
                select(ActivityLog).where(*conds).order_by(ActivityLog.at.desc(), ActivityLog.id.desc())
                .offset((page - 1) * page_size).limit(page_size)
            )).scalars().all()
            users = (await s.execute(
                select(ActivityLog.username).where(ActivityLog.username.isnot(None)).distinct().order_by(ActivityLog.username)
            )).scalars().all()
            cities = (await s.execute(
                select(ActivityLog.city).where(ActivityLog.city.isnot(None)).distinct()
            )).scalars().all()
    except Exception as exc:  # noqa: BLE001
        logger.error("activity_log read failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="Журнал действий недоступен (нет таблицы activity_log в UsersDB?)")
    return {
        "items": [_row(r) for r in rows], "total": int(total), "page": page, "page_size": page_size,
        "lookups": {
            "users": list(users), "cities": sorted(c for c in cities if c),
            "actions": [{"value": k, "title": v} for k, v in ACTION_LABELS.items()],
        },
    }


@router.get("/api/v1/activity-log.csv")
async def activity_log_csv(
    _: Viewer,
    username: Optional[str] = Query(None, max_length=100),
    action: Optional[str] = Query(None, max_length=20),
    city: Optional[str] = Query(None, max_length=20),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    q: Optional[str] = Query(None, max_length=100),
    failed: bool = Query(False),
):
    """Выгрузка журнала по фильтру (до 50 000 строк), CSV в UTF-8 с BOM — открывается в Excel."""
    conds = _filters(username, action, city, date_from, date_to, q, failed)
    async with async_session() as s:
        rows = (await s.execute(
            select(ActivityLog).where(*conds).order_by(ActivityLog.at.desc(), ActivityLog.id.desc()).limit(CSV_LIMIT)
        )).scalars().all()
    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Время", "Пользователь", "Город", "Действие", "Метод", "Адрес", "Статус", "мс", "IP", "Подробности"])
    for r in rows:
        w.writerow([r.at.strftime("%d.%m.%Y %H:%M:%S") if r.at else "", r.username or "", r.city or "",
                    ACTION_LABELS.get(r.action, r.action), r.method or "", r.path or "", r.status or "",
                    r.duration_ms or "", r.ip or "", r.details or ""])
    name = f"activity-log-{date.today().isoformat()}.csv"
    return StreamingResponse(iter([buf.getvalue().encode("utf-8")]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{name}"'})
