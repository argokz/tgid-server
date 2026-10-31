"""Перспективный прирост тепловой нагрузки на 5–15 лет по реестру ТУ (database/load_perspective.py).

GET /api/v1/perspective/loads?horizon=15 — тренд подключений и верхняя оценка по выданным ТУ, по годам и источникам,
с проверкой на прошлом
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import AuthUser, require_roles
from database import load_perspective as lp
from database.connect import acquire_conn

router = APIRouter(tags=["load-perspective"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


@router.get("/api/v1/perspective/loads")
async def perspective_loads(_: Viewer, horizon: int = Query(15, ge=1, le=lp.MAX_LAG)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await lp.perspective(conn, horizon=horizon)
    except lp.PerspectiveError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
