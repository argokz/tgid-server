"""Прогноз аварийности участков теплосети (database/failure_forecast.py).

POST /api/v1/forecast/failures/run               — обучить, проверить по времени и записать риск (право «Расчёт»)
GET  /api/v1/forecast/failures/runs              — расчёты: срезы, проверка, вклад признаков
GET  /api/v1/forecast/failures/runs/{id}/top     — участки с наибольшим риском (+ GeoJSON для карты)
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import failure_forecast as ff
from database.connect import acquire_conn

router = APIRouter(tags=["failure-forecast"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Calc = Annotated[AuthUser, Depends(require_permission("calc_run"))]


def _http(exc: ff.ForecastError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.post("/api/v1/forecast/failures/run", dependencies=[Depends(require_mutations_enabled)])
async def failures_run(user: Calc, horizon_years: int = Query(ff.HORIZON_YEARS, ge=1, le=5)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await ff.run(conn, user=user.username, horizon=horizon_years)
    except ff.ForecastError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/forecast/failures/runs")
async def failures_runs(_: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await ff.list_runs(conn)


@router.get("/api/v1/forecast/failures/runs/{run_id}/top")
async def failures_top(run_id: Annotated[int, Path(ge=1)], _: Viewer, limit: int = Query(200, ge=1, le=2000),
                       fileid: Optional[int] = Query(None, ge=1)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await ff.top_risk(conn, run_id, limit, fileid)
    except ff.ForecastError as exc:
        raise _http(exc) from exc
