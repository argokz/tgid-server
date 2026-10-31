"""Похожие аварии рядом и места повторных отказов (database/defect_similarity.py).

GET  /api/v1/defects/{id}/similar   — дефекты, похожие на этот (вид, труба, Ду, место, слова)
POST /api/v1/defects/similar        — по тексту («свищ Т2 Ду100») и, если задано, месту
GET  /api/v1/defects/hotspots       — скопления отказов «потеря воды» за годы — кандидаты на перекладку
GET  /api/v1/defects/line-binding        — предпросмотр: нарушения без участка → участок по месту (право «Журналы»)
POST /api/v1/defects/line-binding        — записать участки в журнал одной операцией (exclude — снятые)
POST /api/v1/defects/line-binding/undo   — отменить запись по change_group_id

Тексты дефектов — свободные (туда бывает вписан житель или телефон): без права «Персональные данные» ФИО и номера
в них маскируются (database/pii.py).
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import defect_binding
from database import defect_similarity as ds
from database import pii
from database.connect import acquire_conn

router = APIRouter(tags=["defects"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
WRITE = [Depends(require_mutations_enabled)]
Radius = Annotated[float, Query(ge=10, le=ds.MAX_RADIUS_M)]
Limit = Annotated[int, Query(ge=1, le=100)]


class SimilarIn(BaseModel):
    text: str = Field(min_length=2, max_length=1000, description="Описание аварии: вид, труба, Ду, место")
    lon: Optional[float] = Field(None, ge=-180, le=180)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    radius_m: float = Field(ds.DEFAULT_RADIUS_M, ge=10, le=ds.MAX_RADIUS_M)
    limit: int = Field(20, ge=1, le=100)


def masked(result: dict[str, Any], user: AuthUser) -> dict[str, Any]:
    """ФИО и номера в текстах дефектов — только с правом «Персональные данные»."""
    if not pii.enabled() or pii.can_view(user):
        return result
    for item in result.get("items", ()):
        item["text"] = pii.mask_person_text(item["text"])
    return result


@router.get("/api/v1/defects/{defect_id}/similar")
async def defect_similar(defect_id: Annotated[int, Path(ge=1)], user: Viewer,
                         radius_m: Radius = ds.DEFAULT_RADIUS_M, limit: Limit = 20) -> dict[str, Any]:
    async with acquire_conn() as conn:
        ref = await ds.reference(conn, defect_id)
        if ref is None:
            raise HTTPException(status_code=404, detail="Дефект не найден")
        result = await ds.similar(conn, ref["text"] or "", lon=ref["lon"], lat=ref["lat"], radius_m=radius_m,
                                  exclude_id=defect_id, limit=limit)
    return masked({"defect_id": defect_id, **result}, user)


@router.post("/api/v1/defects/similar")
async def defect_similar_text(body: SimilarIn, user: Viewer) -> dict[str, Any]:
    if (body.lon is None) != (body.lat is None):
        raise HTTPException(status_code=422, detail="Место — обе координаты (lon и lat) или ни одной")
    async with acquire_conn() as conn:
        result = await ds.similar(conn, body.text, lon=body.lon, lat=body.lat, radius_m=body.radius_m,
                                  limit=body.limit)
    return masked(result, user)


@router.get("/api/v1/defects/hotspots")
async def defect_hotspots(
    _: Viewer,
    years: Annotated[int, Query(ge=1, le=30)] = ds.YEARS,
    eps_m: Annotated[float, Query(ge=5, le=500)] = ds.CLUSTER_EPS_M,
    min_count: Annotated[int, Query(ge=2, le=50)] = ds.CLUSTER_MIN,
) -> dict[str, Any]:
    async with acquire_conn() as conn:
        items = await ds.hotspots(conn, years=years, eps_m=eps_m, min_count=min_count)
    return {"years": years, "eps_m": eps_m, "min_count": min_count, "items": items}


class BindIn(BaseModel):
    exclude: list[int] = Field(default_factory=list, max_length=100_000, description="Нарушения, которые не трогать")


class UndoIn(BaseModel):
    change_group_id: str = Field(min_length=8, max_length=64)


@router.get("/api/v1/defects/line-binding")
async def defect_line_binding_preview(_: Writer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        plan = await defect_binding.preview(conn)
    plan["items"] = plan["items"][:defect_binding.PREVIEW_ROWS]  # для просмотра; запись пересчитывает всё
    return plan


@router.post("/api/v1/defects/line-binding", dependencies=WRITE)
async def defect_line_binding_apply(body: BindIn, user: Writer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await defect_binding.apply(conn, user.username, exclude=set(body.exclude))
    except defect_binding.BindingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/api/v1/defects/line-binding/undo", dependencies=WRITE)
async def defect_line_binding_undo(body: UndoIn, user: Writer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            result = await defect_binding.undo(conn, body.change_group_id, user.username)
    except defect_binding.BindingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Операция привязки не найдена")
    return result
