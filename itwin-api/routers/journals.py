"""Запись эксплуатационных журналов (этап 9): карточки, контуры, утверждение, документы.

Журналы: defects, shurfs, inspections, repairs, pressure-tests (см. database/journal_specs.py).
Запись — роль editor+ и MUTATIONS_ENABLED (проверяются здесь, на сервере), каждая операция
пишет audit_log в той же транзакции.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, get_current_user, require_mutations_enabled
from database.connect import acquire_conn
from database.journal_specs import JOURNALS, JournalSpec, describe
from database.journal_write import (
    JournalWriteError,
    add_document,
    approval_info,
    approve_records,
    create_record,
    delete_document,
    delete_record,
    document_types,
    get_contour,
    list_approval_candidates,
    list_documents,
    revoke_approval,
    set_contour,
    update_document,
    update_record,
)
from database.sql_ident import UnknownIdentifierError

logger = get_logger(__name__)

router = APIRouter(tags=["journals"])

# Журнал ремонтов — предметное право «Ремонты» (бит 1024 десктопа), остальные — роль editor.
# Окончательно права проверяет БД (sql/pg_auth/03_grants.sql).
_JOURNAL_CAPS = {"repairs": "repairs"}


async def _journal_editor(journal: str, user: Annotated[AuthUser, Depends(get_current_user)]) -> AuthUser:
    cap = _JOURNAL_CAPS.get(journal)
    if user.allows("editor", cap):
        return user
    raise HTTPException(status_code=403, detail="Нет права «ремонты»" if cap and user.is_pg_user
                        else f"Requires one of roles: editor (have {user.role})")


Editor = Annotated[AuthUser, Depends(_journal_editor)]
PREFIX = "/api/v1/journals/{journal}"


class RecordBody(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    mode: Optional[str] = Field(None, description="Режим создания: plan / current / unplanned")
    line_ids: Optional[list[int]] = Field(None, description="Участки контура (linesobj.id)")
    include_pairs: bool = Field(True, description="Добавлять парную трубу подачи/обратки")
    longitude: Optional[float] = None
    latitude: Optional[float] = None


class ContourBody(BaseModel):
    line_ids: list[int]
    include_pairs: bool = True


class ApproveBody(BaseModel):
    ids: Optional[list[int]] = Field(None, description="Для пакетного утверждения")
    approved_on: Optional[date] = None
    signers: dict[str, Any] = Field(default_factory=dict)


class DocumentBody(BaseModel):
    fields: dict[str, Any]


def _spec(journal: str) -> JournalSpec:
    spec = JOURNALS.get(journal)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Журнал «{journal}» не поддерживает запись")
    return spec


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, JournalWriteError):
        detail = exc.detail
        if isinstance(detail, str):
            # код в detail — веб отличает «записи нет» от «маршрута нет» (устаревший API)
            detail = {"code": "not_found" if exc.status == 404 else "conflict", "message": detail}
        return HTTPException(status_code=exc.status, detail=detail)
    if isinstance(exc, UnknownIdentifierError):
        # схема БД не совпала с описанием журнала — ошибка конфигурации, не клиента
        logger.error("journal schema mismatch: %s", exc)
        return HTTPException(status_code=500, detail=f"Схема БД не совпадает с описанием журнала: {exc.name}")
    raise exc


async def _audit(conn, user: AuthUser, operation: str, table: str, record_id: Optional[int],
                 old: Optional[dict] = None, new: Optional[dict] = None, group: Optional[str] = None) -> str:
    return await write_audit_log(
        changed_by=user.username, operation=operation, table_name=table, record_id=record_id,
        old_data=old, new_data=new, change_group_id=group, conn=conn,
    )


# --- описание журналов -------------------------------------------------------

@router.get("/api/v1/journals")
async def journals_schema():
    """Какие журналы и поля пишутся из веба (для форм)."""
    return {key: describe(spec) for key, spec in JOURNALS.items()}


@router.get(PREFIX + "/schema")
async def journal_schema(journal: str):
    spec = _spec(journal)
    result = describe(spec)
    refs = {f.ref for f in spec.fields.values()}
    if spec.approval:
        refs |= {f.ref for f in spec.approval.signer_columns.values()}
    needs_people = bool(refs & {"dolzhnosti", "subdivisions"})
    if spec.documents_table or needs_people:
        async with acquire_conn() as conn:
            try:
                if spec.documents_table:
                    result["document_types"] = await document_types(conn, spec)
                if needs_people:
                    result["positions"] = [dict(r) for r in await conn.fetch(
                        "SELECT id, znachenie AS name FROM dolzhnosti ORDER BY znachenie, id")]
                    result["subdivisions"] = [dict(r) for r in await conn.fetch(
                        "SELECT id, name FROM subdivisions ORDER BY COALESCE(ord, id), id")]
            except (JournalWriteError, UnknownIdentifierError) as exc:
                raise _http(exc)
    return result


# --- карточка ----------------------------------------------------------------

@router.post(PREFIX)
async def create_journal_record(journal: str, body: RecordBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await create_record(
                    conn, spec, body.fields, mode=body.mode, line_ids=body.line_ids,
                    include_pairs=body.include_pairs, longitude=body.longitude, latitude=body.latitude,
                )
                new_data = {**result["record"], "mode": body.mode}
                if "contour" in result:
                    new_data["contour"] = result["contour"]
                group = await _audit(conn, user, "INSERT", spec.table, result["id"], new=new_data)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result, "change_group_id": group}


@router.patch(PREFIX + "/{record_id}")
async def update_journal_record(journal: str, record_id: int, body: RecordBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await update_record(
                    conn, spec, record_id, body.fields, longitude=body.longitude, latitude=body.latitude,
                )
                if result["changed"] or result["geometry_changed"]:
                    new = dict(result["changed"])
                    if result["geometry_changed"]:
                        new["geometry"] = {"longitude": body.longitude, "latitude": body.latitude}
                    await _audit(conn, user, "UPDATE", spec.table, record_id, old=result["old"], new=new)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}


@router.delete(PREFIX + "/{record_id}")
async def delete_journal_record(journal: str, record_id: int, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await delete_record(conn, spec, record_id)
                await _audit(conn, user, "DELETE", spec.table, record_id, old={
                    **result["old"], "cascade": result["cascade"], "detached": result["detached"],
                })
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, "id": record_id, "cascade": result["cascade"], "detached": result["detached"]}


# --- контур ------------------------------------------------------------------

@router.get(PREFIX + "/{record_id}/contour")
async def journal_contour(journal: str, record_id: int):
    """Участки контура с геометрией (GeoJSON, EPSG:4326) и предупреждениями."""
    spec = _spec(journal)
    async with acquire_conn() as conn:
        try:
            return await get_contour(conn, spec, record_id)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.put(PREFIX + "/{record_id}/contour")
async def save_journal_contour(journal: str, record_id: int, body: ContourBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await set_contour(conn, spec, record_id, body.line_ids, include_pairs=body.include_pairs)
                if result["added"] or result["removed"]:
                    await _audit(
                        conn, user, "CONTOUR", spec.deployed_table or spec.table, record_id,
                        old={"removed_lines": result["removed"]},
                        new={"added_lines": result["added"], "total": result["total"],
                             "pairs_added": result["pairs_added"]},
                    )
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}


# --- утверждение планов ------------------------------------------------------

@router.get(PREFIX + "/approval/candidates")
async def journal_approval_candidates(
    journal: str,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Неутверждённые планы (по дате начала по плану) — список для пакетного утверждения."""
    spec = _spec(journal)
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        try:
            return {"items": await list_approval_candidates(conn, spec, date_from=date_from, date_to=date_to)}
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get(PREFIX + "/{record_id}/approval")
async def journal_approval_info(journal: str, record_id: int):
    spec = _spec(journal)
    async with acquire_conn() as conn:
        try:
            return await approval_info(conn, spec, record_id)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)


async def _approve(spec: JournalSpec, ids: list[int], body: ApproveBody, user: AuthUser) -> dict[str, Any]:
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await approve_records(
                    conn, spec, ids, approved_on=body.approved_on, signers=body.signers,
                )
                group = None
                for record_id in result["approved"]:
                    change = result["changes"][record_id]
                    group = await _audit(conn, user, "APPROVE", spec.table, record_id,
                                         old=change["old"], new=change["new"], group=group)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    result.pop("changes", None)
    return result


@router.post(PREFIX + "/{record_id}/approve")
async def approve_journal_record(journal: str, record_id: int, body: ApproveBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    result = await _approve(spec, [record_id], body, user)
    if not result["approved"]:
        reason = result["rejected"].get(record_id)
        status = 404 if reason == "не найдена" else 409 if reason == "уже утверждено" else 422
        raise HTTPException(status_code=status, detail={"message": "План не утверждён", "reason": reason})
    return {"success": True, **result}


@router.post(PREFIX + "/approve")
async def approve_journal_batch(journal: str, body: ApproveBody, user: Editor):
    """Пакетное утверждение (как «Утвердить план шурфовок» gid6): что не прошло проверку — в rejected."""
    spec = _spec(journal)
    require_mutations_enabled()
    if not body.ids:
        raise HTTPException(status_code=422, detail="Не выбраны записи для утверждения")
    result = await _approve(spec, body.ids, body, user)
    return {"success": bool(result["approved"]), **result}


@router.post(PREFIX + "/{record_id}/unapprove")
async def unapprove_journal_record(journal: str, record_id: int, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await revoke_approval(conn, spec, record_id)
                await _audit(conn, user, "UNAPPROVE", spec.table, record_id,
                             old=result["old"], new={"approval_flag": 0})
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}


# --- документы ---------------------------------------------------------------

@router.get(PREFIX + "/{record_id}/documents")
async def journal_documents(journal: str, record_id: int):
    spec = _spec(journal)
    async with acquire_conn() as conn:
        try:
            return {"items": await list_documents(conn, spec, record_id)}
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/{record_id}/documents")
async def add_journal_document(journal: str, record_id: int, body: DocumentBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await add_document(conn, spec, record_id, body.fields)
                await _audit(conn, user, "INSERT", spec.documents_table or "", result["id"], new=result)
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}


@router.patch(PREFIX + "/{record_id}/documents/{doc_id}")
async def update_journal_document(journal: str, record_id: int, doc_id: int, body: DocumentBody, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await update_document(conn, spec, record_id, doc_id, body.fields)
                if result["changed"]:
                    await _audit(conn, user, "UPDATE", spec.documents_table or "", doc_id,
                                 old=result["old"], new={**result["changed"], "objid": record_id})
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}


@router.delete(PREFIX + "/{record_id}/documents/{doc_id}")
async def delete_journal_document(journal: str, record_id: int, doc_id: int, user: Editor):
    spec = _spec(journal)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await delete_document(conn, spec, record_id, doc_id)
                await _audit(conn, user, "DELETE", spec.documents_table or "", doc_id,
                             old={**result["old"], "objid": record_id})
        except (JournalWriteError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"success": True, **result}
