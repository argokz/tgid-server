"""Социальные объекты (database/poi.py).

GET    /api/v1/poi/summary                 — категории: сколько объектов, по источникам, скрытые
GET    /api/v1/poi                         — список (category, source, q, hidden)
GET    /api/v1/poi/geojson                 — точками для карты (category, bbox)
POST   /api/v1/poi/refresh-consumers       — найти среди потребителей сети по названиям (администратор)
POST   /api/v1/poi/import                  — загрузить из файла акимата: GeoJSON (администратор)
POST   /api/v1/poi/import-osm              — загрузить из OpenStreetMap в охвате сети (администратор)
PATCH  /api/v1/poi/{id}                    — скрыть, сменить категорию или название (администратор)
DELETE /api/v1/poi?source=                 — удалить всё из источника (администратор)

Читать может любой вошедший; загрузка и правка — администратор, с записью в журнал действий.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

import activity
from auth import AuthUser, require_roles
from database import poi
from database.connect import acquire_conn
from database.ogc_features import parse_bbox
from routers.ogc import _network_extent

router = APIRouter(tags=["poi"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Admin = Annotated[AuthUser, Depends(require_roles("admin"))]
PoiId = Annotated[int, Path(ge=1)]


def _http(exc: poi.PoiError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


def _categories(raw: Optional[str]) -> list[str]:
    try:
        return poi.check_categories([c.strip() for c in (raw or "").split(",") if c.strip()])
    except poi.PoiError as exc:
        raise _http(exc) from exc


async def _audit(request: Request, user: AuthUser, action: str, details: dict[str, Any]) -> None:
    await activity.write(username=user.username, action=action, method=request.method, path=request.url.path,
                         status=200, details=details, ip=activity.client_ip(request.scope),
                         user_agent=request.headers.get("user-agent", "")[:300])


@router.get("/api/v1/poi/summary")
async def poi_summary(_: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await poi.summary(conn)


@router.get("/api/v1/poi")
async def poi_list(_: Viewer, category: Optional[str] = Query(None, max_length=200),
                   source: Optional[str] = Query(None, max_length=20), q: Optional[str] = Query(None, max_length=100),
                   hidden: bool = False, limit: int = Query(poi.MAX_LIST, ge=1, le=poi.MAX_LIST)) -> list[dict[str, Any]]:
    cats = _categories(category)
    async with acquire_conn() as conn:
        return await poi.list_poi(conn, categories=cats, q=q, source=source, hidden=hidden, limit=limit)


@router.get("/api/v1/poi/geojson")
async def poi_geojson(_: Viewer, category: Optional[str] = Query(None, max_length=200),
                      bbox: Optional[str] = Query(None, max_length=200)) -> dict[str, Any]:
    cats = _categories(category)
    try:
        box = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    async with acquire_conn() as conn:
        return await poi.geojson(conn, categories=cats, bbox=box)


@router.post("/api/v1/poi/refresh-consumers")
async def poi_refresh_consumers(request: Request, user: Admin) -> dict[str, Any]:
    async with acquire_conn() as conn:
        out = await poi.refresh_from_consumers(conn, user.username)
    await _audit(request, user, "POI_REFRESH_CONSUMERS", {"saved": out["saved"], "removed": out["removed"]})
    return out


@router.post("/api/v1/poi/import")
async def poi_import(body: poi.ImportIn, request: Request, user: Admin) -> dict[str, Any]:
    extent = await _network_extent()
    try:
        async with acquire_conn() as conn:
            out = await poi.import_file(conn, body, user.username, extent)
    except poi.PoiError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "POI_IMPORT_FILE", {"saved": out["saved"], "removed": out["removed"]})
    return out


@router.post("/api/v1/poi/import-osm")
async def poi_import_osm(request: Request, user: Admin) -> dict[str, Any]:
    extent = await _network_extent()
    try:
        async with acquire_conn() as conn:
            out = await poi.import_osm(conn, user.username, extent)
    except poi.PoiError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "POI_IMPORT_OSM", {"saved": out["saved"], "removed": out["removed"]})
    return out


@router.patch("/api/v1/poi/{poi_id}")
async def poi_update(poi_id: PoiId, body: poi.PoiPatch, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await poi.update_poi(conn, poi_id, body, user.username)
    except poi.PoiError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "POI_UPDATE", {"id": poi_id, **body.model_dump(exclude_none=True)})
    return out


@router.delete("/api/v1/poi")
async def poi_delete_source(request: Request, user: Admin, source: str = Query(..., max_length=20)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            removed = await poi.delete_source(conn, source)
    except poi.PoiError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "POI_DELETE_SOURCE", {"source": source, "removed": removed})
    return {"removed": removed}
