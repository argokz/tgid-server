"""Администрирование: пользователи и роли (только admin) и история правок (audit_log)."""

from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, auth_disabled, invalidate_user_status, require_roles
from database.audit_history import get_audit_entry, get_audit_log, get_audit_lookups
from database.connect import acquire_conn
from database.users_admin import (
    UserAdminError,
    create_user,
    list_users,
    roles_catalog,
    set_password,
    update_user,
)

logger = get_logger(__name__)

router = APIRouter(tags=["admin"])

RoleName = Literal["viewer", "calculator", "editor", "admin"]
# bcrypt учитывает только первые 72 байта пароля — длиннее не принимаем
PASSWORD_FIELD = Field(..., min_length=8, max_length=72)


class CreateUserBody(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[\w.@-]+$")
    password: str = PASSWORD_FIELD
    role: RoleName = "viewer"


class UpdateUserBody(BaseModel):
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None


class PasswordBody(BaseModel):
    password: str = PASSWORD_FIELD


def _require_real_auth() -> None:
    """Запись в UsersDB — только при включённой аутентификации.

    При AUTH_DISABLED каждый запрос — «dev admin», и любой посетитель мог бы завести
    себе учётную запись администратора.
    """
    if auth_disabled():
        raise HTTPException(
            status_code=503,
            detail="Управление пользователями доступно только при AUTH_DISABLED=false",
        )


def _raise_admin_error(exc: UserAdminError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)


async def _audit_users(user: AuthUser, operation: str, record_id: int, old=None, new=None) -> None:
    await write_audit_log(
        changed_by=user.username,
        operation=operation,
        table_name="usersdb.users",
        record_id=record_id,
        old_data=old,
        new_data=new,
    )


@router.get("/api/admin/roles")
@router.get("/api/v1/admin/roles")
async def admin_roles(_: Annotated[AuthUser, Depends(require_roles("admin"))]):
    return {"items": roles_catalog()}


@router.get("/api/admin/users")
@router.get("/api/v1/admin/users")
async def admin_users(_: Annotated[AuthUser, Depends(require_roles("admin"))]):
    try:
        items = await list_users()
    except Exception as exc:  # noqa: BLE001
        logger.error("UsersDB list failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=503, detail="UsersDB недоступна или не обновлена (нужна колонка users.role)")
    return {
        "items": items,
        "can_write": not auth_disabled(),
        "note": None if not auth_disabled() else "AUTH_DISABLED=true: изменения пользователей отключены",
    }


@router.post("/api/admin/users", status_code=201)
@router.post("/api/v1/admin/users", status_code=201)
async def admin_create_user(
    body: CreateUserBody,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
):
    _require_real_auth()
    try:
        created = await create_user(body.username, body.password, body.role)
    except UserAdminError as exc:
        _raise_admin_error(exc)
    await _audit_users(user, "INSERT", created["id"], new=created)
    return created


@router.patch("/api/admin/users/{user_id}")
@router.patch("/api/v1/admin/users/{user_id}")
async def admin_update_user(
    body: UpdateUserBody,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    user_id: int = Path(..., ge=1),
):
    """Смена роли и блокировка (is_active=false). Действует на выданные токены сразу."""
    _require_real_auth()
    if body.role is None and body.is_active is None:
        raise HTTPException(status_code=422, detail="Нужно указать role и/или is_active")
    try:
        before, after = await update_user(
            user_id, actor_id=user.sub, role=body.role, is_active=body.is_active
        )
    except UserAdminError as exc:
        _raise_admin_error(exc)
    invalidate_user_status(user_id)
    await _audit_users(user, "UPDATE", user_id, old=before, new=after)
    return after


@router.put("/api/admin/users/{user_id}/password")
@router.put("/api/v1/admin/users/{user_id}/password")
async def admin_set_password(
    body: PasswordBody,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    user_id: int = Path(..., ge=1),
):
    _require_real_auth()
    try:
        result = await set_password(user_id, body.password)
    except UserAdminError as exc:
        _raise_admin_error(exc)
    await _audit_users(user, "PASSWORD", user_id, new={"username": result["username"]})
    return {"success": True, "id": user_id}


@router.get("/api/audit-log/lookups")
@router.get("/api/v1/audit-log/lookups")
async def audit_log_lookups(_: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    async with acquire_conn() as conn:
        return await get_audit_lookups(conn)


@router.get("/api/audit-log")
@router.get("/api/v1/audit-log")
async def audit_log_journal(
    _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    table: Optional[str] = Query(None, max_length=100),
    record_id: Optional[int] = Query(None),
    changed_by: Optional[str] = Query(None, max_length=100),
    operation: Optional[str] = Query(None, max_length=10),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    change_group_id: Optional[str] = Query(None, max_length=36),
):
    """История правок с фильтрами: таблица, объект (record_id), пользователь, операция, даты."""
    async with acquire_conn() as conn:
        return await get_audit_log(
            conn,
            page=page,
            page_size=page_size,
            table=table,
            record_id=record_id,
            changed_by=changed_by,
            operation=operation,
            date_from=date_from,
            date_to=date_to,
            change_group_id=change_group_id,
        )


@router.get("/api/audit-log/{log_id}")
@router.get("/api/v1/audit-log/{log_id}")
async def audit_log_entry(
    _: Annotated[AuthUser, Depends(require_roles("viewer"))],
    log_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        item = await get_audit_entry(conn, log_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Запись журнала не найдена")
    return item
