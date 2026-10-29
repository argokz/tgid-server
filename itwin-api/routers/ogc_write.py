"""OGC API — Features, часть 4: создание, замена, правка и удаление объектов сети (/api/ogc/…).

POST   /api/ogc/collections/{id}/items        — создать узел (Point) или участок (концы node_start/node_end)
PUT    /api/ogc/collections/{id}/items/{fid}  — заменить: геометрия и правимые свойства
PATCH  /api/ogc/collections/{id}/items/{fid}  — частичная правка (JSON Merge Patch по объекту)
DELETE /api/ogc/collections/{id}/items/{fid}  — удалить узел (без участков) или участок

Каждая операция — та же, что в вебе: права вида объекта и охват «только свои», журнал отмены
(«Отменить» в вебе отменяет и правку из QGIS), audit_log. Версия — ETag в ответе GET и записи;
If-Match с устаревшим ETag → 412. Правила записи — database/ogc_transactions.py.
"""
from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse, Response

from auth import AuthUser, get_current_user
from database import ogc_transactions as ot
from database.connect import acquire_conn
from database.ogc_features import COLLECTIONS, get_item
from routers import card_edit as card_router
from routers import topology as topo
from routers.ogc import GEOJSON, _base, _collection_or_404, _link

router = APIRouter(tags=["ogc-features"])

Editor = Annotated[AuthUser, Depends(get_current_user)]
FeatureId = Annotated[int, Path(ge=1)]
# Тело запроса: GeoJSON Feature; объект сети — не больше нескольких тысяч вершин
MAX_BODY_BYTES = 2_000_000


async def _body(request: Request) -> Any:
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Слишком большой объект")
    try:
        return json.loads(raw or b"null")
    except ValueError:
        raise HTTPException(status_code=400, detail="Тело запроса — JSON (GeoJSON Feature)") from None


def _http(exc: ot.OgcWriteError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


async def _state(cid: str, fid: int) -> tuple[Optional[dict], Optional[dict[str, str]]]:
    async with acquire_conn() as conn:
        return await get_item(conn, cid, fid), await ot.row_versions(conn, cid, fid)


async def _current(cid: str, fid: int) -> tuple[dict, dict[str, str]]:
    feature, versions = await _state(cid, fid)
    if feature is None or versions is None:
        raise HTTPException(status_code=404, detail=f"Объекта {fid} в коллекции {cid} нет")
    return feature, versions


def _precondition(request: Request, versions: dict[str, str]) -> bool:
    """If-Match: 412 при устаревшей версии; True — клиент прислал If-Match (конфликт версий → 412)."""
    header = request.headers.get("if-match")
    if not ot.if_match_ok(header, ot.etag(versions)):
        raise HTTPException(status_code=412, detail="Объект изменён — перечитайте его (ETag устарел)")
    return header is not None


def _conflict_as_412(exc: HTTPException, if_match: bool) -> HTTPException:
    detail = exc.detail if isinstance(exc.detail, dict) else {}
    if if_match and exc.status_code == 409 and detail.get("code") == "version_conflict":
        return HTTPException(status_code=412, detail=detail.get("message") or "Объект изменён другим пользователем")
    return exc


def _writable_or_405(cid: str, allowed: frozenset[str] | None = None) -> None:
    if not ot.writable(cid) or (allowed is not None and cid not in allowed):
        raise HTTPException(status_code=405, detail=f"Коллекция {cid} этой операции не поддерживает")


async def _apply_properties(cid: str, fid: int, changes: dict[str, Any], versions: dict[str, str],
                            user: AuthUser, *, check_versions: bool) -> None:
    """Свойства — окном свойств (права «Свойства», журнал, audit_log, версии строк → 409)."""
    if not changes:
        return
    rows = ot.card_changes(cid, fid, changes, versions)
    expected = {k: ot.row_xmin(v) for k, v in versions.items()} if check_versions else {}
    await card_router.card_edit_save(
        card_router.SaveBody(changes=[card_router.Change(**r) for r in rows], versions=expected), user)


async def _apply_geometry(cid: str, fid: int, geometry: dict, versions: dict[str, str], user: AuthUser) -> None:
    """Геометрия — операцией редактора сети (журнал отмены, проверка правил связности)."""
    if cid == "nodes":
        lng, lat = ot.point(geometry)
        await topo.move_node_endpoint(
            fid, topo.MoveNodeParams(lng=lng, lat=lat, expected_version=versions[f"nodes:{fid}"]), user)
    else:
        await topo.api_update_line_geometry(
            fid, topo.UpdateLineGeometryRequest(coordinates=ot.line_coords(geometry),
                                                expected_version=versions[f"linesobj:{fid}"]), user)


async def _written(request: Request, cid: str, fid: int, status_code: int = 200) -> JSONResponse:
    feature, versions = await _state(cid, fid)
    if feature is None or versions is None:
        raise HTTPException(status_code=404, detail=f"Объекта {fid} в коллекции {cid} нет")
    url = f"{_base(request)}/collections/{cid}"
    feature["links"] = [_link(f"{url}/items/{fid}", "self", GEOJSON), _link(url, "collection")]
    headers = {"ETag": ot.etag(versions)}
    if status_code == 201:
        headers["Location"] = f"{url}/items/{fid}"
    return JSONResponse(feature, status_code=status_code, media_type=GEOJSON, headers=headers)


async def _update(request: Request, cid: str, fid: int, user: AuthUser, *, replace: bool) -> JSONResponse:
    _collection_or_404(cid)
    _writable_or_405(cid)
    try:
        geometry, props = ot.feature_parts(await _body(request))
        if replace and geometry is None and cid in ot.GEOMETRY_EDITABLE:
            raise ot.OgcWriteError(400, "PUT: объект целиком, с геометрией")
        current, versions = await _current(cid, fid)
        if_match = _precondition(request, versions)
        changes = ot.property_changes(cid, current["properties"], props)
        move = geometry is not None and cid in ot.GEOMETRY_EDITABLE \
            and not ot.same_geometry(cid, current["geometry"], geometry)
        # положение задвижки и источника производное: в PATCH геометрию им не передают
        if geometry is not None and cid not in ot.GEOMETRY_EDITABLE and not replace:
            raise ot.OgcWriteError(422, f"Положение объектов коллекции {cid} производное — геометрия не правится")
        ot.card_changes(cid, fid, changes, versions)  # проверка до записи: несколько паспортов → 409
    except ot.OgcWriteError as exc:
        raise _http(exc)
    try:
        if move:
            await _apply_geometry(cid, fid, geometry, versions, user)
        # после правки геометрии версии строк сменились — свойства без проверки версий
        await _apply_properties(cid, fid, changes, versions, user, check_versions=not move)
    except HTTPException as exc:
        raise _conflict_as_412(exc, if_match)
    return await _written(request, cid, fid)


@router.put("/api/ogc/collections/{collection_id}/items/{feature_id}")
async def ogc_replace(request: Request, collection_id: str, feature_id: FeatureId, user: Editor):
    """Заменить объект: геометрия (узел, участок) и правимые свойства; только читаемые — без изменений."""
    return await _update(request, collection_id, feature_id, user, replace=True)


@router.patch("/api/ogc/collections/{collection_id}/items/{feature_id}")
async def ogc_patch(request: Request, collection_id: str, feature_id: FeatureId, user: Editor):
    """Частичная правка (JSON Merge Patch): переданные свойства и/или геометрия."""
    return await _update(request, collection_id, feature_id, user, replace=False)


@router.post("/api/ogc/collections/{collection_id}/items", status_code=201)
async def ogc_create(request: Request, collection_id: str, user: Editor):
    """Создать узел (Point; node_kind — расчётный тип, fileid — фрагмент) или участок между узлами
    node_start и node_end (геометрия — промежуточные вершины, по умолчанию прямая)."""
    cid = collection_id
    _collection_or_404(cid)
    _writable_or_405(cid, ot.CREATABLE)
    try:
        geometry, props = ot.feature_parts(await _body(request))
        extra = ot.CREATE_ONLY[cid]
        known = set(ot.writable(cid)) | extra
        unknown = sorted(set(props) - known - {name for name, _ in COLLECTIONS[cid].props} - {"fileid"})
        if unknown:
            raise ot.OgcWriteError(422, f"У коллекции {cid} нет свойств: {', '.join(unknown)}")
        changes = {k: v for k, v in props.items() if k in ot.writable(cid) and v is not None}
        if cid == "nodes":
            if geometry is None:
                raise ot.OgcWriteError(400, "Новый узел — геометрия Point")
            lng, lat = ot.point(geometry)
            kind = props.get("node_kind") or "US"
            if kind not in ot.NODE_KINDS:
                raise ot.OgcWriteError(422, f"node_kind — одно из {', '.join(ot.NODE_KINDS)}")
            fileid = props.get("fileid")
            if fileid is not None and (not isinstance(fileid, int) or fileid < 1):
                raise ot.OgcWriteError(422, "fileid — номер фрагмента")
        else:
            ends = (props.get("node_start"), props.get("node_end"))
            if not all(isinstance(n, int) and n > 0 for n in ends) or ends[0] == ends[1]:
                raise ot.OgcWriteError(422, "Новый участок — node_start и node_end: id двух разных узлов")
            coords = ot.line_coords(geometry) if geometry is not None else None
    except ot.OgcWriteError as exc:
        raise _http(exc)

    if cid == "nodes":
        created = await topo.create_node_endpoint(
            topo.CreateNodeParams(lng=lng, lat=lat, fileid=fileid, node_type=kind), user)
    else:
        created = await topo.create_line_endpoint(topo.CreateLineParams(nodeid1=ends[0], nodeid2=ends[1]), user)
    fid = int(created["id"])
    if (cid == "pipes" and coords and len(coords) > 2) or changes:
        _, versions = await _current(cid, fid)
        if cid == "pipes" and coords and len(coords) > 2:
            await _apply_geometry(cid, fid, {"type": "LineString", "coordinates": coords}, versions, user)
            _, versions = await _current(cid, fid)
        try:
            ot.card_changes(cid, fid, changes, versions)
        except ot.OgcWriteError as exc:
            raise _http(exc)
        await _apply_properties(cid, fid, changes, versions, user, check_versions=True)
    return await _written(request, cid, fid, status_code=201)


@router.delete("/api/ogc/collections/{collection_id}/items/{feature_id}", status_code=204)
async def ogc_delete(request: Request, collection_id: str, feature_id: FeatureId, user: Editor):
    """Удалить узел (без примыкающих участков — иначе 409 со списком) или участок (без парной трубы)."""
    cid = collection_id
    _collection_or_404(cid)
    _writable_or_405(cid, ot.DELETABLE)
    _, versions = await _current(cid, feature_id)
    if_match = _precondition(request, versions)
    try:
        if cid == "nodes":
            await topo.delete_node_endpoint(feature_id, user, cascade=False,
                                            expected_version=versions[f"nodes:{feature_id}"])
        else:
            await topo.api_delete_line(feature_id, user, expected_version=versions[f"linesobj:{feature_id}"],
                                       expected_section_id=None, include_pair=False)
    except HTTPException as exc:
        raise _conflict_as_412(exc, if_match)
    return Response(status_code=204)
