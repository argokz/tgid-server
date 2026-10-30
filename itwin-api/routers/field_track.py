"""Трек бригады из полевого приложения (database/field_track.py).

POST /api/v1/field/track      — пачка точек телефона (повтор пачки без дублей)
GET  /api/v1/field/positions  — где бригады сейчас: последняя точка каждого за 12 часов
GET  /api/v1/field/track      — трек бригады или пользователя за период (по умолчанию — сутки)

Всё — право «Журналы» (journals): пишет бригада, смотрит диспетчер. Местоположение сотрудников другим
пользователям не показывается.
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import AuthUser, require_permission
from database import field_track as ft
from database.connect import acquire_conn

router = APIRouter(tags=["work-orders"])
Journals = Annotated[AuthUser, Depends(require_permission("journals"))]


@router.post("/api/v1/field/track")
async def field_track_add(body: ft.TrackIn, user: Journals):
    async with acquire_conn() as conn:
        return await ft.add_points(conn, body, user.username)


@router.get("/api/v1/field/positions")
async def field_positions(_: Journals, hours: int = Query(ft.POSITION_MAX_AGE_H, ge=1, le=72)):
    async with acquire_conn() as conn:
        return await ft.positions(conn, hours=hours)


@router.get("/api/v1/field/track")
async def field_track_get(
    _: Journals,
    brigade_id: Optional[int] = Query(None, ge=1),
    user: Optional[str] = Query(None, max_length=100, description="Вход сотрудника"),
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
):
    try:
        async with acquire_conn() as conn:
            return await ft.track(conn, brigade_id=brigade_id, by_user=user, since=since, until=until)
    except ft.TrackError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
