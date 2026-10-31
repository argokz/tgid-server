"""Общая карта коммуникаций (database/utility_conflicts.py): нормы расстояний, сближения и пересечения сетей,
сети в зоне раскопок.

GET  /api/v1/utilities/norms                 — нормативные расстояния между видами сетей
PUT  /api/v1/utilities/norms                 — изменить норму (право «Справочники»)
GET  /api/v1/utilities/conflicts             — сближения и пересечения: модель водопровода × теплосеть
POST /api/v1/utilities/excavation            — сети в зоне работ: участки, владельцы, расстояние
GET  /api/v1/utilities/depths                — глубина теплосети из отметок узлов: сколько участков и откуда
POST /api/v1/utilities/depths/refresh        — пересчитать глубины (право «Справочники»)
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import heat_depth
from database import utility_conflicts as uc
from database.connect import acquire_conn

router = APIRouter(tags=["utilities"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Refs = Annotated[AuthUser, Depends(require_permission("refs"))]
Kind = Literal["heat", "water"]


def _http(exc: uc.UtilityError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


class NormIn(BaseModel):
    kind_a: Kind
    kind_b: Kind
    horizontal_m: Optional[float] = Field(None, ge=0, le=100)
    vertical_m: Optional[float] = Field(None, ge=0, le=20)
    source: Optional[str] = Field(None, max_length=300)


class ExcavationIn(BaseModel):
    geometry: dict[str, Any] = Field(description="Зона работ: GeoJSON Point, LineString или Polygon (WGS84)")
    buffer_m: float = Field(5.0, ge=0, le=uc.MAX_DIG_BUFFER_M, description="Отступ от зоны работ, м")
    water_model: Optional[int] = Field(None, ge=1, description="Только эта модель водопровода")


@router.get("/api/v1/utilities/norms")
async def utilities_norms(_: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await uc.list_norms(conn)


@router.put("/api/v1/utilities/norms", dependencies=[Depends(require_mutations_enabled)])
async def utilities_norm_put(body: NormIn, user: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await uc.set_norm(conn, body.kind_a, body.kind_b, body.horizontal_m, body.vertical_m, body.source,
                                     user.username)
    except uc.UtilityError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/utilities/conflicts")
async def utilities_conflicts(_: Viewer, water_model: int = Query(..., ge=1)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await uc.water_heat_conflicts(conn, water_model)
    except uc.UtilityError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/utilities/excavation")
async def utilities_excavation(body: ExcavationIn, _: Viewer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await uc.excavation(conn, body.geometry, body.buffer_m, body.water_model)
    except uc.UtilityError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/utilities/depths")
async def utilities_depths(_: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await heat_depth.status(conn)


@router.post("/api/v1/utilities/depths/refresh", dependencies=[Depends(require_mutations_enabled)])
async def utilities_depths_refresh(user: Refs) -> dict[str, Any]:
    async with acquire_conn() as conn:
        result = await heat_depth.refresh(conn, user.username)
    if result.get("busy"):
        raise HTTPException(status_code=409, detail="Глубины уже пересчитываются")
    return result
