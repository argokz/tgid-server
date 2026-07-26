"""Универсальные CRUD-маршруты для атрибутов объектов (за флагом MUTATIONS_ENABLED)."""

from typing import Annotated, Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app_logging import get_logger
from audit import write_audit_log
from auth import (
    AuthUser,
    assert_mutable_table,
    get_current_user,
    require_mutations_enabled,
    role_for_mutation,
)
from database.db import create_object, delete_object, update_object_attributes
from database.ops_mutations import filter_ops_fields
from database.tu_mutations import filter_tu_fields

logger = get_logger(__name__)

router = APIRouter(tags=["crud"])


class UpdateAttributesParams(BaseModel):
    fields: Dict[str, Any]


def _prepare_fields(table: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    key = table.lower()
    if key == "tehnicheskie_usloviya":
        return filter_tu_fields(fields)
    if key in {"defect", "shurfy", "osmotr", "remont2", "opres"}:
        return filter_ops_fields(table, fields)
    return fields


@router.put("/update/{table}/{id}")
@router.put("/api/v1/update/{table}/{id}")
async def update_object(
    table: str,
    id: int,
    body: UpdateAttributesParams,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Обновляет атрибуты объекта в БД."""
    require_mutations_enabled()
    table = assert_mutable_table(table)
    if not user.has_role(role_for_mutation(table)):
        raise HTTPException(status_code=403, detail=f"Role {user.role} cannot mutate {table}")
    fields = _prepare_fields(table, body.fields)
    try:
        success = await update_object_attributes(table, id, fields)
        await write_audit_log(
            changed_by=user.username,
            operation="UPDATE",
            table_name=table,
            record_id=id,
            new_data=fields,
        )
        return {"success": success, "message": "Атрибуты успешно обновлены"}
    except Exception as e:
        logger.error(f"Error updating object {table} {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при обновлении: {str(e)}")


@router.post("/create/{table}")
@router.post("/api/v1/create/{table}")
async def api_create_object(
    table: str,
    body: UpdateAttributesParams,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Создает новый объект в БД."""
    require_mutations_enabled()
    table = assert_mutable_table(table)
    if not user.has_role(role_for_mutation(table)):
        raise HTTPException(status_code=403, detail=f"Role {user.role} cannot mutate {table}")
    fields = _prepare_fields(table, body.fields)
    try:
        new_id = await create_object(table, fields)
        await write_audit_log(
            changed_by=user.username,
            operation="INSERT",
            table_name=table,
            record_id=new_id,
            new_data=fields,
        )
        return {"success": True, "id": new_id, "message": "Объект успешно создан"}
    except Exception as e:
        logger.error(f"Error creating object {table}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при создании: {str(e)}")


@router.delete("/delete/{table}/{id}")
@router.delete("/api/v1/delete/{table}/{id}")
async def api_delete_object(
    table: str,
    id: int,
    user: Annotated[AuthUser, Depends(get_current_user)],
):
    """Удаляет объект из БД."""
    require_mutations_enabled()
    table = assert_mutable_table(table)
    if not user.has_role(role_for_mutation(table)):
        raise HTTPException(status_code=403, detail=f"Role {user.role} cannot mutate {table}")
    try:
        success = await delete_object(table, id)
        await write_audit_log(
            changed_by=user.username,
            operation="DELETE",
            table_name=table,
            record_id=id,
        )
        return {"success": success, "message": "Объект успешно удален"}
    except Exception as e:
        logger.error(f"Error deleting object {table} {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при удалении: {str(e)}")
