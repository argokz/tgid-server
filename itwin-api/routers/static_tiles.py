"""Статичные слои в PMTiles (database/static_tiles.py).

GET    /api/v1/static-tiles                        — архивы города и слои, которые можно запечь
POST   /api/v1/static-tiles/{layer}/build          — запечь (Celery; статус — GET /api/v1/task/{id}), админ
DELETE /api/v1/static-tiles/{layer}                — удалить архив (слой снова из martin/GeoServer), админ
GET    /api/v1/static-tiles/{layer}/{z}/{x}/{y}    — тайл MVT из архива (gzip как есть); нет тайла — 204
GET    /api/v1/static-tiles/{layer}.pmtiles        — архив целиком (Range — для офлайна и клиентов PMTiles)
"""
from __future__ import annotations

import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from audit import write_audit_log
from auth import AuthUser, require_roles
from cities import task_queue
from database import pmtiles
from database import static_tiles as st
from database.connect import acquire_conn

router = APIRouter(tags=["static-tiles"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Admin = Annotated[AuthUser, Depends(require_roles("admin"))]
LayerName = Annotated[str, Path(pattern=st.LAYER_RE.pattern, max_length=60)]

MVT_MEDIA_TYPE = "application/vnd.mapbox-vector-tile"
# адрес тайла несёт версию архива (?v=…): новый архив — новые адреса, поэтому кеш браузера долгий
TILE_CACHE = "private, max-age=604800"


class BuildBody(BaseModel):
    minzoom: Optional[int] = Field(None, ge=0, le=st.MAX_MAXZOOM, description="Пусто — с какого зума виден слой")
    maxzoom: int = Field(st.DEFAULT_MAXZOOM, ge=0, le=st.MAX_MAXZOOM)


def _http(exc: st.StaticTilesError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/static-tiles")
async def static_tiles_list(user: Viewer):
    archives = await run_in_threadpool(st.list_archives)
    layers: list[dict] = []
    if user.has_role("admin"):
        async with acquire_conn() as conn:
            layers = [x for x in await st.bakeable_layers(conn) if x["static"]]
    return {"archives": archives, "layers": layers, "can_build": user.has_role("admin")}


@router.post("/api/v1/static-tiles/{layer}/build")
async def static_tiles_build(layer: LayerName, body: BuildBody, user: Admin):
    from worker import bake_static_tiles as task_fn

    async with acquire_conn() as conn:
        layers = {x["layer"]: x for x in await st.bakeable_layers(conn)}
    info = layers.get(layer)
    if info is None:
        raise HTTPException(status_code=404, detail=f"В базе города нет функции тайлов {st.FUNC_PREFIX}{layer}")
    if not info["static"]:
        raise HTTPException(status_code=422, detail=f"Слой {layer} зависит от фрагментов и подписей — запечь нельзя")
    minzoom = info["minzoom"] if body.minzoom is None else body.minzoom
    if minzoom > body.maxzoom:
        raise HTTPException(status_code=422, detail="Нижний зум больше верхнего")
    kwargs = {"layer": layer, "minzoom": minzoom, "maxzoom": body.maxzoom, "user": user.username}
    queue = task_queue(os.getenv("STATIC_TILES_QUEUE") or None)
    task = task_fn.apply_async(kwargs=kwargs, queue=queue) if queue else task_fn.apply_async(kwargs=kwargs)
    await write_audit_log(changed_by=user.username, operation="RUN", table_name="static_tiles",
                          new_data={**kwargs, "task_id": task.id})
    return {"task_id": task.id, "status": "queued"}


@router.delete("/api/v1/static-tiles/{layer}")
async def static_tiles_delete(layer: LayerName, user: Admin):
    if not await run_in_threadpool(st.delete_archive, layer):
        raise HTTPException(status_code=404, detail="Архива слоя нет")
    await write_audit_log(changed_by=user.username, operation="DELETE", table_name="static_tiles",
                          old_data={"layer": layer})
    return {"deleted": layer}


@router.get("/api/v1/static-tiles/{layer}.pmtiles")
async def static_tiles_file(layer: LayerName, user: Viewer):
    path = st.archive_path(layer)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Архива слоя нет")
    return FileResponse(path, media_type="application/vnd.pmtiles", filename=f"{layer}.pmtiles")


@router.get("/api/v1/static-tiles/{layer}/{z}/{x}/{y}")
async def static_tiles_tile(
    layer: LayerName,
    user: Viewer,
    z: Annotated[int, Path(ge=0, le=pmtiles.MAX_ZOOM)],
    x: Annotated[int, Path(ge=0)],
    y: Annotated[str, Path(max_length=20)],
):
    try:
        row = int(y.removesuffix(".mvt").removesuffix(".pbf"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="y — номер ряда тайла") from exc
    try:
        reader = await run_in_threadpool(st.reader, layer)
    except pmtiles.PMTilesError as exc:
        raise HTTPException(status_code=500, detail="Архив слоя повреждён — пересоберите его") from exc
    if reader is None:
        raise HTTPException(status_code=404, detail="Архива слоя нет")
    data = await run_in_threadpool(reader.get, z, x, row)
    headers = {"Cache-Control": TILE_CACHE}
    if not data:
        return Response(status_code=204, headers=headers)
    if reader.header.tile_compression == pmtiles.COMPRESSION_GZIP:
        headers["Content-Encoding"] = "gzip"
    return Response(content=data, media_type=MVT_MEDIA_TYPE, headers=headers)
