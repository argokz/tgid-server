"""Универсальные CRUD-маршруты для атрибутов объектов (за флагом MUTATIONS_ENABLED)."""

from typing import Annotated, Any, Dict, Optional

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app_logging import get_logger
from audit import write_audit_log
from auth import (
    AuthUser,
    assert_mutable_table,
    get_current_user,
    require_mutations_enabled,
    cap_for_mutation,
    role_for_mutation,
)
from database.db import create_object, delete_object, update_object_attributes
from database.ops_mutations import filter_ops_fields
from database.sql_ident import UnknownIdentifierError
from database.typed_edit import TypedEditError
from database.tu_mutations import filter_tu_fields

logger = get_logger(__name__)

router = APIRouter(tags=["crud"])


def _identifier_error(exc: UnknownIdentifierError) -> HTTPException:
    if exc.kind == "table":
        return HTTPException(status_code=403, detail="Table is not in the mutation allow-list")
    return HTTPException(status_code=400, detail=f"Unknown column: {exc.name}")


def mutation_client_error(exc: Exception) -> Optional[HTTPException]:
    """Ошибка клиента при записи → 4xx (иначе None — это 500).

    Неизвестная колонка/таблица → 400/403, значение не того типа → 422, нарушение
    ограничений БД (NOT NULL, уникальность, внешний ключ) → 409, неверные данные → 422.
    4xx клиент не повторяет; 500 означает сбой сервера.
    """
    if isinstance(exc, UnknownIdentifierError):
        return _identifier_error(exc)
    if isinstance(exc, TypedEditError):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, asyncpg.exceptions.IntegrityConstraintViolationError):
        return HTTPException(status_code=409, detail=f"Нарушено ограничение БД: {exc.__class__.__name__}")
    if isinstance(exc, asyncpg.exceptions.DataError):
        return HTTPException(status_code=422, detail=f"Недопустимое значение: {exc}")
    return None


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
    if not user.allows(role_for_mutation(table), cap_for_mutation(table, "update")):
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
        client_error = mutation_client_error(e)
        if client_error is not None:
            raise client_error from e
        logger.error(f"Error updating object {table} {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при обновлении")


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
    if not user.allows(role_for_mutation(table), cap_for_mutation(table, "insert")):
        raise HTTPException(status_code=403, detail=f"Role {user.role} cannot mutate {table}")
    fields = _prepare_fields(table, body.fields)
    if not fields:
        # QA F44: пустой create — ошибка клиента (400), а не 500, который выглядит как сбой
        raise HTTPException(status_code=400, detail="No fields provided")
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
        client_error = mutation_client_error(e)
        if client_error is not None:
            raise client_error from e
        logger.error(f"Error creating object {table}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при создании")


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
    if not user.allows(role_for_mutation(table), cap_for_mutation(table, "delete")):
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
        client_error = mutation_client_error(e)
        if client_error is not None:
            raise client_error from e
        logger.error(f"Error deleting object {table} {id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при удалении")
