"""Тематические карты участков (Smart Mapping) и сохранённые стили слоя.

GET    /api/v1/thematic/themes             — темы: подпись, единицы, классы по умолчанию
GET    /api/v1/thematic/pipes              — участки фрагментов со значением темы (GeoJSON + сводка)
GET    /api/v1/layer-styles                — общие и свои стили
POST   /api/v1/layer-styles                — сохранить (общий — с правом «Справочники и шаблоны»)
PUT    /api/v1/layer-styles/{id}           — изменить (revision — версия, которую правили)
DELETE /api/v1/layer-styles/{id}
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import AuthUser, require_roles
from database import layer_styles as ls
from database import thematic as th
from database.connect import acquire_conn

router = APIRouter(tags=["analysis"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


def _fragment_ids(text: str) -> list[int]:
    try:
        ids = [int(v) for v in text.split(",") if v.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="fragment_ids — номера фрагментов через запятую") from exc
    if not ids:
        raise HTTPException(status_code=422, detail="Выберите хотя бы один фрагмент")
    return ids


@router.get("/api/v1/thematic/themes")
async def thematic_themes(user: Viewer):
    return {"themes": th.themes_payload(), "max_features": th.MAX_FEATURES}


@router.get("/api/v1/thematic/pipes")
async def thematic_pipes(
    user: Viewer,
    theme: str = Query(..., max_length=40),
    fragment_ids: str = Query(..., max_length=4000, description="Номера фрагментов через запятую"),
    bbox: Optional[str] = Query(None, max_length=200, description="запад,юг,восток,север (WGS 84)"),
):
    ids = _fragment_ids(fragment_ids)
    try:
        box = th.clean_bbox(bbox)
        async with acquire_conn() as conn:
            return await th.theme_features(conn, theme, ids, bbox=box)
    except th.ThematicError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message)


class StyleBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=ls.NAME_MAX)
    style: dict[str, Any]
    shared: bool = False


class StylePatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=ls.NAME_MAX)
    style: Optional[dict[str, Any]] = None
    shared: Optional[bool] = None
    revision: Optional[int] = Field(None, ge=1)


def _can_shared(user: AuthUser) -> bool:
    return user.perms.has("refs")


def _http(exc: ls.LayerStyleError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/layer-styles")
async def list_layer_styles(user: Viewer):
    async with acquire_conn() as conn:
        return {"styles": await ls.list_styles(conn, user.username), "can_shared": _can_shared(user)}


@router.post("/api/v1/layer-styles", status_code=201)
async def create_layer_style(body: StyleBody, user: Viewer):
    if body.shared and not _can_shared(user):
        raise HTTPException(status_code=403, detail="Общие стили — с правом «Справочники и шаблоны»")
    try:
        async with acquire_conn() as conn:
            return await ls.create_style(conn, name=body.name, style=body.style, shared=body.shared,
                                         user=user.username)
    except ls.LayerStyleError as exc:
        raise _http(exc)


@router.put("/api/v1/layer-styles/{style_id}")
async def update_layer_style(style_id: str, body: StylePatch, user: Viewer):
    if body.shared and not _can_shared(user):
        raise HTTPException(status_code=403, detail="Общие стили — с правом «Справочники и шаблоны»")
    try:
        async with acquire_conn() as conn:
            return await ls.update_style(conn, style_id, name=body.name, style=body.style, shared=body.shared,
                                         revision=body.revision, user=user.username,
                                         can_shared=_can_shared(user))
    except ls.LayerStyleError as exc:
        raise _http(exc)


@router.delete("/api/v1/layer-styles/{style_id}", status_code=204)
async def delete_layer_style(style_id: str, user: Viewer):
    try:
        async with acquire_conn() as conn:
            await ls.delete_style(conn, style_id, user=user.username, can_shared=_can_shared(user))
    except ls.LayerStyleError as exc:
        raise _http(exc)
