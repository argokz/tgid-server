"""Теплосеть в 3D (database/network3d.py): участки видимой области с глубиной заложения для подземного вида Cesium.

GET /api/v1/network3d/lines?bbox=минДолгота,минШирота,максДолгота,максШирота&fileids=1,2
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import AuthUser, require_roles
from database import network3d as n3
from database.connect import acquire_conn

router = APIRouter(tags=["network3d"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


def _parse(raw: str, count: Optional[int], what: str, cast=float) -> list:
    try:
        values = [cast(x) for x in raw.split(",") if x.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{what}: числа через запятую") from exc
    if count is not None and len(values) != count:
        raise HTTPException(status_code=422, detail=f"{what}: {count} числа через запятую")
    return values


@router.get("/api/v1/network3d/lines")
async def network3d_lines(_: Viewer, bbox: str = Query(..., max_length=200),
                          fileids: Optional[str] = Query(None, max_length=4000)) -> dict[str, Any]:
    box = tuple(_parse(bbox, 4, "bbox"))
    ids = _parse(fileids, None, "fileids", int) if fileids else None
    try:
        async with acquire_conn() as conn:
            return await n3.lines(conn, box, ids)
    except n3.Network3dError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
