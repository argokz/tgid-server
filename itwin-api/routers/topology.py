"""Изменение топологии сети (за флагами TOPOLOGY_MUTATIONS_ENABLED + MUTATIONS_ENABLED)."""

import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database.topology import (
    TopologyDependencyError,
    create_line,
    create_node,
    delete_line,
    delete_node,
    move_node,
    split_line,
)

logger = get_logger(__name__)

router = APIRouter(tags=["topology"])


class MoveNodeParams(BaseModel):
    lng: float
    lat: float


class CreateNodeParams(BaseModel):
    lng: float
    lat: float


class CreateLineParams(BaseModel):
    nodeid1: int
    nodeid2: int


class SplitLineRequest(BaseModel):
    line_id: int
    lng: float
    lat: float
    # dry_run=true — вернуть отчёт «что перенесётся» без сохранения (превью в UI)
    dry_run: bool = False


def require_topology_mutations_enabled():
    enabled = os.getenv("TOPOLOGY_MUTATIONS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise HTTPException(
            status_code=503,
            detail="Topology mutations are disabled until dependent-table migration and RBAC are complete",
        )
    require_mutations_enabled()


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
        await move_node(id, params.lng, params.lat)
        await write_audit_log(
            changed_by=user.username,
            operation="MOVE",
            table_name="nodes",
            record_id=id,
            new_data={"lng": params.lng, "lat": params.lat},
        )
        return {"success": True, "id": id}
    except Exception as e:
        logger.error(f"Error moving node {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/node")
@router.post("/api/topology/node")
@router.post("/api/v1/topology/node")
async def create_node_endpoint(
    params: CreateNodeParams,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        new_id = await create_node(params.lng, params.lat)
        await write_audit_log(
            changed_by=user.username,
            operation="INSERT",
            table_name="nodes",
            record_id=new_id,
            new_data={"lng": params.lng, "lat": params.lat},
        )
        return {"success": True, "id": new_id}
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topology/node/{id}")
@router.delete("/api/topology/node/{id}")
@router.delete("/api/v1/topology/node/{id}")
async def delete_node_endpoint(
    id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    cascade: bool = False,
):
    require_topology_mutations_enabled()
    try:
        result = await delete_node(id, cascade=cascade)
        await write_audit_log(
            changed_by=user.username,
            operation="DELETE",
            table_name="nodes",
            record_id=id,
            new_data={"cascade": cascade, **result},
        )
        return {"success": True, "id": id, **result}
    except TopologyDependencyError as e:
        # 409: узел не удалён, т.к. на нём висят зависимости; отчёт — в detail
        raise HTTPException(status_code=409, detail={"message": str(e), "blockers": e.blockers})
    except Exception as e:
        logger.error(f"Error deleting node {id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topology/line")
@router.post("/api/topology/line")
@router.post("/api/v1/topology/line")
async def create_line_endpoint(
    params: CreateLineParams,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        new_id = await create_line(params.nodeid1, params.nodeid2)
        await write_audit_log(
            changed_by=user.username,
            operation="INSERT",
            table_name="linesobj",
            record_id=new_id,
            new_data={"nodeid1": params.nodeid1, "nodeid2": params.nodeid2},
        )
        return {"success": True, "id": new_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating line: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/topology/line/{line_id}")
@router.delete("/api/v1/topology/line/{line_id}")
async def api_delete_line(
    line_id: int,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    require_topology_mutations_enabled()
    try:
        await delete_line(line_id)
        await write_audit_log(
            changed_by=user.username,
            operation="DELETE",
            table_name="linesobj",
            record_id=line_id,
        )
        return {"status": "success", "id": line_id}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        result = await split_line(req.line_id, req.lng, req.lat, dry_run=req.dry_run)
        if not req.dry_run:
            await write_audit_log(
                changed_by=user.username,
                operation="SPLIT",
                table_name="linesobj",
                record_id=req.line_id,
                new_data=result if isinstance(result, dict) else {"result": str(result)},
            )
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
