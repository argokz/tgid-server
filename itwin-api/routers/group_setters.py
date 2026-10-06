"""Групповые установщики свойств и редактируемые справочники (этап 9).

Установщики: ``database/group_setters.py`` (описание, dry-run, применение, отмена).
Справочники: ``database/dictionaries.py`` (CRUD, проверка ссылок при удалении → 409).
Запись — роль editor+ и MUTATIONS_ENABLED (проверяются здесь), одна транзакция + audit_log.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database import dictionaries as dicts
from database import group_setters as gs
from database.connect import acquire_conn
from database.sql_ident import UnknownIdentifierError

logger = get_logger(__name__)

router = APIRouter(tags=["group-setters"])

Editor = Annotated[AuthUser, Depends(require_roles("editor", cap="network"))]


class SetterBody(BaseModel):
    selection: dict[str, Any] = Field(..., description="{mode: ids|fragment|filter, ids, fragment_ids, bbox, where}")
    value: Any = None
    expected_changes: Optional[int] = Field(None, description="changes из предпросмотра; расхождение → 409")


class UndoBody(BaseModel):
    change_group_id: str
    dry_run: bool = True


class DictBody(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, (gs.GroupSetterError, dicts.DictionaryError)):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, UnknownIdentifierError):
        logger.error("group setter / dictionary schema mismatch: %s", exc)
        return HTTPException(status_code=500, detail=f"Схема БД не совпадает с описанием: {exc.name}")
    raise exc


def _audit_writer(user: AuthUser):
    async def write(conn, *, operation: str, table: str, record_id: Optional[int], old=None, new=None,
                    group: Optional[str] = None) -> str:
        return await write_audit_log(
            changed_by=user.username, operation=operation, table_name=table, record_id=record_id,
            old_data=old, new_data=new, change_group_id=group, conn=conn,
        )

    return write


def _ids(raw: Optional[str]) -> Optional[list[int]]:
    if not raw:
        return None
    try:
        return [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="fragment_ids: список чисел через запятую")


# --- установщики ---------------------------------------------------------------

@router.get("/api/v1/group-setters")
async def group_setters_list():
    """Установщики (эталон — десктоп aSet*/OnSet*) и поля фильтра по целям."""
    return {
        "setters": gs.describe_all(),
        "targets": {k: {"label": t.label, "filter_fields": list(gs.filter_fields(k))} for k, t in gs.TARGETS.items()},
        "max_objects": gs.MAX_OBJECTS,
    }


@router.get("/api/v1/group-setters/{key}/options")
async def group_setter_options(
    key: str,
    q: Optional[str] = None,
    fragment_ids: Optional[str] = Query(None, description="id фрагментов через запятую"),
    limit: int = Query(gs.OPTIONS_LIMIT, ge=1, le=1000),
):
    async with acquire_conn() as conn:
        try:
            return await gs.list_options(conn, gs.get_spec(key), q=q, fragment_ids=_ids(fragment_ids), limit=limit)
        except (gs.GroupSetterError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post("/api/v1/group-setters/{key}/preview")
async def group_setter_preview(key: str, body: SetterBody, user: Editor):
    """Dry-run: сколько объектов/строк изменится, «было → станет» (без записи)."""
    async with acquire_conn() as conn:
        try:
            return await gs.preview(conn, gs.get_spec(key), body.value, body.selection)
        except (gs.GroupSetterError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post("/api/v1/group-setters/{key}/apply")
async def group_setter_apply(key: str, body: SetterBody, user: Editor):
    spec = gs.get_spec(key) if key in gs.SETTERS else None
    if spec is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Установщик «{key}» не найден"})
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await gs.apply(conn, spec, body.value, body.selection, actor=user.username,
                                        expected_changes=body.expected_changes, audit_row=_audit_writer(user))
        except (gs.GroupSetterError, UnknownIdentifierError) as exc:
            raise _http(exc)
    try:
        from database.outage_simulation import invalidate_outage_cache

        invalidate_outage_cache()
    except Exception:  # noqa: BLE001 — кэш не критичен
        pass
    return result


@router.post("/api/v1/group-setters/undo")
async def group_setter_undo(body: UndoBody, user: Editor):
    """Отмена групповой операции по audit_log; dry_run=true — только отчёт."""
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                return await gs.undo(conn, body.change_group_id, actor=user.username, dry_run=body.dry_run,
                                     audit_row=_audit_writer(user))
        except (gs.GroupSetterError, UnknownIdentifierError) as exc:
            raise _http(exc)


# --- справочники ----------------------------------------------------------------

@router.get("/api/v1/dictionaries")
async def dictionaries_list():
    async with acquire_conn() as conn:
        try:
            return {"dictionaries": [await dicts.describe(conn, d) for d in dicts.DICTIONARIES.values()]}
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get("/api/v1/dictionaries/{key}")
async def dictionary_rows(
    key: str,
    q: Optional[str] = None,
    fragment_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=dicts.LIST_LIMIT_MAX),
    offset: int = Query(0, ge=0),
):
    async with acquire_conn() as conn:
        try:
            return await dicts.list_rows(conn, dicts.get_spec(key), q=q, fragment_id=fragment_id,
                                         limit=limit, offset=offset)
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get("/api/v1/dictionaries/{key}/{record_id}")
async def dictionary_row(key: str, record_id: int):
    async with acquire_conn() as conn:
        try:
            spec = dicts.get_spec(key)
            row = await dicts.get_row(conn, spec, record_id)
            return {"row": row, "usage": await dicts.usage(conn, spec, record_id, row)}
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post("/api/v1/dictionaries/{key}")
async def dictionary_create(key: str, body: DictBody, user: Editor):
    spec = dicts.get_spec(key) if key in dicts.DICTIONARIES else None
    if spec is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Справочник «{key}» не найден"})
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                row = await dicts.create_row(conn, spec, body.fields)
                await _audit_writer(user)(conn, operation="INSERT", table=spec.table, record_id=row["id"], new=row)
                return row
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.put("/api/v1/dictionaries/{key}/{record_id}")
async def dictionary_update(key: str, record_id: int, body: DictBody, user: Editor):
    spec = dicts.get_spec(key) if key in dicts.DICTIONARIES else None
    if spec is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Справочник «{key}» не найден"})
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                before, after = await dicts.update_row(conn, spec, record_id, body.fields)
                if before != after:
                    await _audit_writer(user)(conn, operation="UPDATE", table=spec.table, record_id=record_id,
                                              old=before, new=after)
                return after
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.delete("/api/v1/dictionaries/{key}/{record_id}")
async def dictionary_delete(key: str, record_id: int, user: Editor):
    spec = dicts.get_spec(key) if key in dicts.DICTIONARIES else None
    if spec is None:
        raise HTTPException(status_code=404, detail={"code": "not_found", "message": f"Справочник «{key}» не найден"})
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                before = await dicts.delete_row(conn, spec, record_id)
                await _audit_writer(user)(conn, operation="DELETE", table=spec.table, record_id=record_id, old=before)
                return {"deleted": record_id}
        except (dicts.DictionaryError, UnknownIdentifierError) as exc:
            raise _http(exc)
