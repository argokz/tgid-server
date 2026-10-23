"""Качество исходных данных (/api/v1/data-quality/*): сводка по правилам, список проблем, GeoJSON."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import AuthUser, require_roles
from database import data_quality as dq
from database.connect import acquire_conn

router = APIRouter(tags=["data-quality"])


@router.get("/api/v1/data-quality/rules")
async def data_quality_rules(_: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    return {"items": dq.rule_specs()}


@router.get("/api/v1/data-quality/summary")
async def data_quality_summary(_: Annotated[AuthUser, Depends(require_roles("viewer"))],
                               fragment_id: Optional[int] = Query(None, ge=1)):
    async with acquire_conn() as conn:
        return await dq.summary(conn, fragment_id=fragment_id)


@router.get("/api/v1/data-quality/issues")
async def data_quality_issues(
    _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    rule: str = Query(..., max_length=64), fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0),
):
    async with acquire_conn() as conn:
        try:
            return await dq.issues(conn, rule, fragment_id=fragment_id, limit=limit, offset=offset)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Нет правила {rule}") from None


@router.get("/api/v1/data-quality/geojson")
async def data_quality_geojson(
    _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    rule: str = Query(..., max_length=64), fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(5000, ge=1, le=50000),
):
    async with acquire_conn() as conn:
        try:
            return await dq.geojson(conn, rule, fragment_id=fragment_id, limit=limit)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Нет правила {rule}") from None
