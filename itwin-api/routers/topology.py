"""Изменение топологии сети (за флагами TOPOLOGY_MUTATIONS_ENABLED + MUTATIONS_ENABLED)."""

import os
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app_logging import get_logger
from auth import AuthUser, require_mutations_enabled, require_roles
from database.topology import (
    TopologyConflictError,
    TopologyDependencyError,
    create_line,
    create_node,
    delete_line,
    delete_node,
    get_versions,
    merge_nodes,
    move_node,
    reverse_line,
    split_line,
    update_line_geometry,
)

logger = get_logger(__name__)

router = APIRouter(tags=["topology"])

# Версия объекта, которую видел клиент (оптимистичная блокировка): токен из
# GET /topology/versions или из ответа dry-run; допускается и archivechangedate из
# карточки объекта. None — не проверять (совместимость со старыми клиентами).
VersionField = Optional[str]


class MoveNodeParams(BaseModel):
    lng: float
    lat: float
    expected_version: VersionField = None


class CreateNodeParams(BaseModel):
    lng: float
    lat: float


class CreateLineParams(BaseModel):
    nodeid1: int
    nodeid2: int
    nodeid1_version: VersionField = None
    nodeid2_version: VersionField = None


class SplitLineRequest(BaseModel):
    line_id: int
    lng: float
    lat: float
    # dry_run=true — вернуть отчёт «что перенесётся» без сохранения (превью в UI)
    dry_run: bool = False
    expected_version: VersionField = None


class ReverseLineRequest(BaseModel):
    line_id: int
    dry_run: bool = False
    expected_version: VersionField = None
    # подтверждение оператора: насосы/обратные клапаны/элеваторы поменяют направление действия
    accept_direction_change: bool = False


class MergeNodesRequest(BaseModel):
    target_node_id: int
    source_node_id: int
    dry_run: bool = False
    target_version: VersionField = None
    source_version: VersionField = None


class UpdateLineGeometryRequest(BaseModel):
    coordinates: list[list[float]]
    expected_version: VersionField = None


def require_topology_mutations_enabled():
    enabled = os.getenv("TOPOLOGY_MUTATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise HTTPException(
            status_code=503,
            detail="Topology mutations are disabled until dependent-table migration and RBAC are complete",
        )
    require_mutations_enabled()


def _topology_http_error(exc: Exception, what: str) -> HTTPException:
    """Единое отображение ошибок топологии в HTTP.

    409 version_conflict — объект изменён другим пользователем (перезагрузить объект);
    409 blocked — операция заблокирована зависимыми объектами; 400 — неверный запрос.
    """
    if isinstance(exc, HTTPException):
        return exc
    if isinstance(exc, TopologyConflictError):
        return HTTPException(
            status_code=409,
            detail={"code": "version_conflict", "message": str(exc), "conflicts": exc.conflicts},
        )
    if isinstance(exc, TopologyDependencyError):
        return HTTPException(
            status_code=409,
            detail={"code": "blocked", "message": str(exc), "blockers": exc.blockers},
        )
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    logger.error(f"Error {what}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail=str(exc))


def _parse_ids(raw: Optional[str]) -> list[int]:
    if not raw:
        return []
    try:
        ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be comma-separated integers")
    if len(ids) > 500:
        raise HTTPException(status_code=400, detail="too many ids (max 500)")
    return ids


@router.get("/api/topology/versions")
@router.get("/api/v1/topology/versions")
async def topology_versions(
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    nodes: Optional[str] = Query(None, description="id узлов через запятую"),
    lines: Optional[str] = Query(None, description="id участков через запятую"),
):
    """Версии узлов/участков для оптимистичной блокировки (запоминаются при выборе объекта)."""
    return await get_versions(_parse_ids(nodes), _parse_ids(lines))


@router.put("/topology/node/{id}/move")
@router.put("/api/topology/node/{id}/move")
@router.put("/api/v1/topology/node/{id}/move")
async def move_node_endpoint(
    id: int,
    params: MoveNodeParams,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        result = await move_node(
            id, params.lng, params.lat, expected_version=params.expected_version, actor=user.username,
        )
        return {"success": True, "id": id, **result}
    except Exception as e:
        raise _topology_http_error(e, f"moving node {id}")


@router.post("/topology/node")
@router.post("/api/topology/node")
@router.post("/api/v1/topology/node")
async def create_node_endpoint(
    params: CreateNodeParams,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        new_id = await create_node(params.lng, params.lat, actor=user.username)
        return {"success": True, "id": new_id}
    except Exception as e:
        raise _topology_http_error(e, "creating node")


@router.delete("/topology/node/{id}")
@router.delete("/api/topology/node/{id}")
@router.delete("/api/v1/topology/node/{id}")
async def delete_node_endpoint(
    id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    cascade: bool = False,
    expected_version: VersionField = None,
):
    require_topology_mutations_enabled()
    try:
        result = await delete_node(id, cascade=cascade, expected_version=expected_version, actor=user.username)
        return {"success": True, "id": id, **result}
    except Exception as e:
        # 409: узел не удалён — зависимости (blockers) или конфликт версий
        raise _topology_http_error(e, f"deleting node {id}")


@router.post("/topology/line")
@router.post("/api/topology/line")
@router.post("/api/v1/topology/line")
async def create_line_endpoint(
    params: CreateLineParams,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        new_id = await create_line(
            params.nodeid1,
            params.nodeid2,
            nodeid1_version=params.nodeid1_version,
            nodeid2_version=params.nodeid2_version,
            actor=user.username,
        )
        return {"success": True, "id": new_id}
    except Exception as e:
        raise _topology_http_error(e, "creating line")


@router.delete("/api/topology/line/{line_id}")
@router.delete("/api/v1/topology/line/{line_id}")
async def api_delete_line(
    line_id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    expected_version: VersionField = None,
):
    require_topology_mutations_enabled()
    try:
        result = await delete_line(line_id, expected_version=expected_version, actor=user.username)
        return {"status": "success", "id": line_id, **result}
    except Exception as e:
        raise _topology_http_error(e, f"deleting line {line_id}")


@router.post("/api/topology/split-line")
@router.post("/api/v1/topology/split-line")
async def api_split_line(
    req: SplitLineRequest,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    # Превью (dry_run) безопасно — транзакция откатывается, ничего не сохраняется,
    # поэтому не требует включённого флага записи; RBAC (admin) остаётся.
    if not req.dry_run:
        require_topology_mutations_enabled()
    try:
        result = await split_line(
            req.line_id, req.lng, req.lat,
            dry_run=req.dry_run,
            expected_version=req.expected_version,
            actor=user.username,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise _topology_http_error(e, f"splitting line {req.line_id}")


@router.post("/api/topology/reverse-line")
@router.post("/api/v1/topology/reverse-line")
async def api_reverse_line(
    req: ReverseLineRequest,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    """Разворот участка; dry_run=true — превью: узлы, геометрия, оборудование."""
    if not req.dry_run:
        require_topology_mutations_enabled()
    try:
        return await reverse_line(
            req.line_id,
            dry_run=req.dry_run,
            expected_version=req.expected_version,
            accept_direction_change=req.accept_direction_change,
            actor=user.username,
        )
    except Exception as e:
        raise _topology_http_error(e, f"reversing line {req.line_id}")


@router.post("/api/topology/merge-nodes")
@router.post("/api/v1/topology/merge-nodes")
async def api_merge_nodes(
    req: MergeNodesRequest,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    """Слияние узла-источника в целевой; dry_run=true — превью переноса и блокеров."""
    if not req.dry_run:
        require_topology_mutations_enabled()
    try:
        return await merge_nodes(
            req.target_node_id,
            req.source_node_id,
            dry_run=req.dry_run,
            target_version=req.target_version,
            source_version=req.source_version,
            actor=user.username,
        )
    except Exception as e:
        raise _topology_http_error(e, f"merging nodes {req.target_node_id} and {req.source_node_id}")


@router.put("/api/topology/line/{line_id}/geometry")
@router.put("/api/v1/topology/line/{line_id}/geometry")
async def api_update_line_geometry(
    line_id: int,
    req: UpdateLineGeometryRequest,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        return await update_line_geometry(
            line_id, req.coordinates, expected_version=req.expected_version, actor=user.username,
        )
    except Exception as e:
        raise _topology_http_error(e, f"updating geometry for line {line_id}")
