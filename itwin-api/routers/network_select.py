"""Выборка объектов сети по условиям (database/network_select.py).

GET  /api/v1/network-select/fields  — цели, поля, операции и значения справочников (конструктор, ИИ)
POST /api/v1/network-select         — выполнить запрос: описание, строки, GeoJSON, итоги
POST /api/v1/network-select/export  — результат файлом ГИС: GeoPackage, FlatGeobuf, Shapefile (zip)
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth import AuthUser, require_permission, require_roles
from database import network_select as ns
from database import thematic as th
from database import vector_export as ve
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


class ExportRequest(SelectRequest):
    format: str = Field("gpkg", max_length=10, description=", ".join(ve.FORMATS))


@router.post("/api/v1/network-select/export")
async def network_select_export(body: ExportRequest,
                                user: Annotated[AuthUser, Depends(require_permission("export"))]):
    """Результат выборки файлом: слой lines или nodes со значениями полей запроса (до предела запроса)."""
    try:
        fmt = ve.get_format(body.format)
    except ve.VectorExportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    box = parse_bbox(body.bbox)
    try:
        async with acquire_conn() as conn:
            result = await ns.run_select(conn, body.spec, bbox=box, user_key=user.username or user.sub or "")
    except ns.SelectError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    layer = ve.frame(ns.result_features(result))
    try:
        content, media_type, filename = await run_in_threadpool(
            ve.write_layers, {result["target"]: layer}, fmt, f"selection_{result['target']}")
    except ve.VectorExportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return Response(content, media_type=media_type, headers={
        "Content-Disposition": f"attachment; filename={filename}",
        "X-Export-Rows": str(len(result["items"])),
        "X-Export-Truncated": "1" if result["truncated"] else "0",
        "Access-Control-Expose-Headers": "Content-Disposition, X-Export-Rows, X-Export-Truncated",
    })
