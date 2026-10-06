"""Администрирование: пользователи и роли (только admin) и история правок (audit_log)."""

from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import (
    PG_USER_PREFIX,
    AuthUser,
    auth_disabled,
    invalidate_user_status,
    pg_auth_enabled,
    require_roles,
)
from database import pg_users
from database.audit_history import get_audit_entry, get_audit_log, get_audit_lookups
from database.connect import acquire_conn
from database.db_role import default_db_role
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


CapName = Literal["network", "network_struct", "acts", "geo", "pts", "corrosion", "repairs"]


class CreateUserBody(BaseModel):
    # логины десктопа — «Фамилия Имя» (пробел), UsersDB — буквы, цифры, . _ @ -
    username: str = Field(..., min_length=2, max_length=50, pattern=r"^[\w .@-]+$")
    password: str = PASSWORD_FIELD
    role: RoleName = "viewer"
    # AUTH_BACKEND=pg: предметные права, территория (фрагменты), профиль
    caps: list[CapName] = Field(default_factory=list)
    fragments: list[int] = Field(default_factory=list)
    display_name: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, max_length=200)
    web_access: bool = True


class UpdateUserBody(BaseModel):
    role: Optional[RoleName] = None
    is_active: Optional[bool] = None
    caps: Optional[list[CapName]] = None
    fragments: Optional[list[int]] = None  # [] — правка во всей сети
    display_name: Optional[str] = Field(None, max_length=200)
    full_name: Optional[str] = Field(None, max_length=200)
    web_access: Optional[bool] = None


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


def _pg_admin_role(user: AuthUser) -> str:
    """Роль PostgreSQL, от имени которой выполняется администрирование (права проверяет БД)."""
    if user.sub.startswith(PG_USER_PREFIX):
        return user.sub
    return default_db_role()  # AUTH_DISABLED: только чтение списка (запись закрыта _require_real_auth)


def _pg_error(exc: "pg_users.PgUserError") -> None:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.get("/api/admin/roles")
@router.get("/api/v1/admin/roles")
async def admin_roles(_: Annotated[AuthUser, Depends(require_roles("admin"))]):
    if pg_auth_enabled():
        return {"items": pg_users.roles_catalog(), "caps": pg_users.caps_catalog(), "backend": "pg"}
    return {"items": roles_catalog()}


@router.get("/api/admin/users")
@router.get("/api/v1/admin/users")
async def admin_users(user: Annotated[AuthUser, Depends(require_roles("admin"))]):
    try:
        items = await (pg_users.list_users(_pg_admin_role(user)) if pg_auth_enabled() else list_users())
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
    if pg_auth_enabled():
        # История пишется функцией tgid_auth.create_user от имени администратора
        try:
            return await pg_users.create_user(
                _pg_admin_role(user), login=body.username, password=body.password,
                base_role=body.role, caps=list(body.caps), fragments=list(body.fragments),
                display_name=body.display_name, full_name=body.full_name, web_access=body.web_access,
            )
        except pg_users.PgUserError as exc:
            _pg_error(exc)
    try:
        created = await create_user(body.username, body.password, body.role)
    except UserAdminError as exc:
        _raise_admin_error(exc)
    await _audit_users(user, "INSERT", created["id"], new=created)
    return created


def _usersdb_id(user_id: str) -> int:
    if not user_id.isdigit() or int(user_id) < 1:
        raise HTTPException(status_code=422, detail="Идентификатор пользователя UsersDB — число ≥ 1")
    return int(user_id)


@router.patch("/api/admin/users/{user_id}")
@router.patch("/api/v1/admin/users/{user_id}")
async def admin_update_user(
    body: UpdateUserBody,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    user_id: str = Path(..., min_length=1, max_length=70),
):
    """Роль, права, территория, профиль и блокировка. Действует на выданные токены сразу.

    user_id — число (UsersDB) или имя роли tgid_u_* (AUTH_BACKEND=pg).
    """
    _require_real_auth()
    if pg_auth_enabled():
        if not user_id.startswith(PG_USER_PREFIX):
            raise HTTPException(status_code=422, detail="Ожидается роль пользователя tgid_u_*")
        if all(v is None for v in body.model_dump().values()):
            raise HTTPException(status_code=422, detail="Нечего менять")
        try:
            after = await pg_users.update_user(
                _pg_admin_role(user), user_id, base_role=body.role,
                caps=list(body.caps) if body.caps is not None else None,
                fragments=body.fragments, display_name=body.display_name,
                full_name=body.full_name, web_access=body.web_access, is_active=body.is_active,
            )
        except pg_users.PgUserError as exc:
            _pg_error(exc)
        invalidate_user_status(user_id)
        return after
    uid = _usersdb_id(user_id)
    if body.role is None and body.is_active is None:
        raise HTTPException(status_code=422, detail="Нужно указать role и/или is_active")
    try:
        before, after = await update_user(
            uid, actor_id=user.sub, role=body.role, is_active=body.is_active
        )
    except UserAdminError as exc:
        _raise_admin_error(exc)
    invalidate_user_status(uid)
    await _audit_users(user, "UPDATE", uid, old=before, new=after)
    return after


@router.put("/api/admin/users/{user_id}/password")
@router.put("/api/v1/admin/users/{user_id}/password")
async def admin_set_password(
    body: PasswordBody,
    user: Annotated[AuthUser, Depends(require_roles("admin"))],
    user_id: str = Path(..., min_length=1, max_length=70),
):
    _require_real_auth()
    if pg_auth_enabled():
        if not user_id.startswith(PG_USER_PREFIX):
            raise HTTPException(status_code=422, detail="Ожидается роль пользователя tgid_u_*")
        try:
            # временный пароль: пользователь сменит его при входе
            await pg_users.set_password(_pg_admin_role(user), user_id, body.password, must_change=True)
        except pg_users.PgUserError as exc:
            _pg_error(exc)
        return {"success": True, "id": user_id}
    uid = _usersdb_id(user_id)
    try:
        result = await set_password(uid, body.password)
    except UserAdminError as exc:
        _raise_admin_error(exc)
    await _audit_users(user, "PASSWORD", uid, new={"username": result["username"]})
    return {"success": True, "id": uid}


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
