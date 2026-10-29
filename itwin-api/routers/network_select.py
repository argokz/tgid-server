"""Выборка объектов сети по условиям (database/network_select.py).

GET  /api/v1/network-select/fields  — цели, поля, операции и значения справочников (конструктор, ИИ)
POST /api/v1/network-select         — выполнить запрос: описание, строки, GeoJSON, итоги
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import AuthUser, require_roles
from database import network_select as ns
from database import thematic as th
from database.connect import acquire_conn

router = APIRouter(tags=["analysis"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


class SelectRequest(BaseModel):
    spec: ns.SelectSpec
    bbox: Optional[str] = Field(None, max_length=200, description="Охват карты «запад,юг,восток,север» (WGS 84)")


def parse_bbox(bbox: Optional[str]):
    try:
        return th.clean_bbox(bbox)
    except th.ThematicError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.get("/api/v1/network-select/fields")
async def network_select_fields(user: Viewer):
    async with acquire_conn() as conn:
        return await ns.fields_payload(conn)


@router.post("/api/v1/network-select")
async def network_select(body: SelectRequest, user: Viewer):
    box = parse_bbox(body.bbox)
    try:
        async with acquire_conn() as conn:
            return await ns.run_select(conn, body.spec, bbox=box, user_key=user.username or user.sub or "")
    except ns.SelectError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
