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
    TopologyNothingToUndo,
    TopologyObjectMismatch,
    create_line,
    create_node,
    delete_line,
    delete_node,
    get_line_geometry,
    get_line_ref,
    get_versions,
    last_undoable_operation,
    merge_nodes,
    move_node,
    reverse_line,
    split_line,
    undo_last_operation,
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
    # Откуда взять фрагмент/код/признак узла (иначе — ближайший узел сети):
    fileid: Optional[int] = None
    near_node_id: Optional[int] = None
    near_line_id: Optional[int] = None


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
    # Решение оператора по оборудованию без узла/позиции (transferred.review_items превью):
    # {таблица: [id, …]} — на новую (вторую) половину, остальное — на первой; {} — всё на первой.
    # Если такое оборудование есть, а решения нет — 409 requires_resolution.
    review_to_new: Optional[dict[str, list[int]]] = None


class ReverseLineRequest(BaseModel):
    line_id: int
    dry_run: bool = False
    expected_version: VersionField = None
    # подтверждение оператора: насосы/обратные клапаны/элеваторы поменяют направление действия
    accept_direction_change: bool = False
    # парная труба (подача ↔ обратка) разворачивается вместе, как в десктопе;
    # pair_line_id/pair_version — пара из превью (если перестала быть парой — 409)
    include_pair: bool = True
    pair_line_id: Optional[int] = None
    pair_version: VersionField = None
    # heatpipesections.id из карточки участка: сервер сверит его с паспортом line_id,
    # при расхождении — 409 object_mismatch (QA F54: карточка несла id паспорта, не участка)
    expected_section_id: Optional[int] = None


class UndoRequest(BaseModel):
    # операция, которую показывала кнопка «Отменить»; другая последняя — 409
    operation_id: Optional[int] = None


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
    if isinstance(exc, TopologyNothingToUndo):
        return HTTPException(status_code=404, detail={"code": "nothing_to_undo", "message": str(exc)})
    if isinstance(exc, TopologyConflictError):
        return HTTPException(
            status_code=409,
            detail={"code": "version_conflict", "message": str(exc), "conflicts": exc.conflicts},
        )
    if isinstance(exc, TopologyObjectMismatch):
        return HTTPException(
            status_code=409,
            detail={"code": "object_mismatch", "message": str(exc), **exc.details},
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


@router.get("/api/topology/line-ref")
@router.get("/api/v1/topology/line-ref")
async def topology_line_ref(
    _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    line_id: Optional[int] = Query(None, description="linesobj.id"),
    section_id: Optional[int] = Query(None, description="heatpipesections.id (паспорт трубы)"),
):
    """Участок ↔ паспорт трубы: linesobj.id по heatpipesections.id и обратно.

    Слой GeoServer `id_heatpipesections` отдаёт heatpipesections.id, а все операции
    с участком (история, журналы, анализ отключения, топология) ждут linesobj.id (QA F12).
    """
    try:
        ref = await get_line_ref(line_id=line_id, section_id=section_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if ref is None:
        raise HTTPException(status_code=404, detail="Участок не найден")
    return ref


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
        result = await create_node(
            params.lng, params.lat,
            actor=user.username,
            fileid=params.fileid,
            near_node_id=params.near_node_id,
            near_line_id=params.near_line_id,
        )
        return {"success": True, **result}
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
        result = await create_line(
            params.nodeid1,
            params.nodeid2,
            nodeid1_version=params.nodeid1_version,
            nodeid2_version=params.nodeid2_version,
            actor=user.username,
        )
        return {"success": True, **result}
    except Exception as e:
        raise _topology_http_error(e, "creating line")


@router.delete("/api/topology/line/{line_id}")
@router.delete("/api/v1/topology/line/{line_id}")
async def api_delete_line(
    line_id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    expected_version: VersionField = None,
    expected_section_id: Optional[int] = Query(None, description="heatpipesections.id из карточки (сверка, 409 object_mismatch)"),
):
    require_topology_mutations_enabled()
    try:
        result = await delete_line(
            line_id, expected_version=expected_version, actor=user.username,
            expected_section_id=expected_section_id,
        )
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
            review_to_new=req.review_to_new,
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
            include_pair=req.include_pair,
            pair_line_id=req.pair_line_id,
            pair_version=req.pair_version,
            expected_section_id=req.expected_section_id,
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


@router.get("/api/topology/line/{line_id}/geometry")
@router.get("/api/v1/topology/line/{line_id}/geometry")
async def api_get_line_geometry(
    line_id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    """Полная геометрия участка (WGS84), узлы-концы и версия — для правки вершин."""
    try:
        return await get_line_geometry(line_id)
    except Exception as e:
        raise _topology_http_error(e, f"reading geometry for line {line_id}")


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


@router.get("/api/topology/undo")
@router.get("/api/v1/topology/undo")
async def api_last_undoable(user: Annotated[AuthUser, Depends(require_roles("admin"))]):
    """Последняя неотменённая операция топологии пользователя (для кнопки «Отменить»)."""
    return {"operation": await last_undoable_operation(user.username)}


@router.post("/api/topology/undo")
@router.post("/api/v1/topology/undo")
async def api_undo(
    req: UndoRequest,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    """Отмена последней операции топологии пользователя.

    404 — отменять нечего; 409 version_conflict — объекты операции изменены после неё
    (или последней стала другая операция); 409 blocked — операцию отменить нельзя.
    """
    require_topology_mutations_enabled()
    try:
        return await undo_last_operation(user.username, operation_id=req.operation_id)
    except Exception as e:
        raise _topology_http_error(e, "undoing topology operation")
