"""АЛСЕКО: сверка, привязка зданий и отчёт несоответствий (этап 10).

Логика и эталон десктопа — ``database/alseko_binding.py``. Чтение сверки — всем с токеном;
предпросмотр и запись привязок — роль editor+, запись ещё и MUTATIONS_ENABLED;
одна транзакция + audit_log.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database import alseko_binding as ab
from database.connect import acquire_conn

router = APIRouter(tags=["alseko"])

Editor = Annotated[AuthUser, Depends(require_roles("editor"))]


class AddressBindBody(BaseModel):
    microdistrict: Optional[str] = None
    street: Optional[str] = None
    house: Optional[str] = Field(None, description="Пусто — снять привязку здания к адресу АЛСЕКО")
    dry_run: bool = True


class ConsumerBindBody(BaseModel):
    building_ids: list[int] = Field(default_factory=list, max_length=ab.MAX_CONSUMER_BUILDINGS)
    dry_run: bool = True


def _http(exc: ab.AlsekoError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.detail)


def _audit_writer(user: AuthUser):
    async def write(conn, *, operation: str, table: str, record_id: Optional[int], old=None, new=None,
                    group: Optional[str] = None) -> str:
        return await write_audit_log(
            changed_by=user.username, operation=operation, table_name=table, record_id=record_id,
            old_data=old, new_data=new, change_group_id=group, conn=conn,
        )

    return write


@router.get("/api/alseko/reconciliation")
async def alseko_reconciliation_summary():
    """Сверка nagruzki ↔ zdaniya_2: количество несоответствий по видам (nenaid1–3 и др.)."""
    async with acquire_conn() as conn:
        return await ab.reconciliation_summary(conn)


@router.get("/api/alseko/reconciliation/issues")
async def alseko_reconciliation_issues(
    kind: str = Query(..., description=", ".join(ab.ISSUE_KINDS)),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    async with acquire_conn() as conn:
        try:
            return await ab.reconciliation_issues(conn, kind, limit=limit, offset=offset)
        except ab.AlsekoError as exc:
            raise _http(exc)


@router.get("/api/alseko/reconciliation/report.xlsx")
async def alseko_reconciliation_report(
    kinds: Optional[str] = Query(None, description="виды через запятую; пусто — все"),
):
    selected = [k.strip() for k in (kinds or "").split(",") if k.strip()] or None
    async with acquire_conn() as conn:
        try:
            content = await ab.reconciliation_workbook(conn, selected)
        except ab.AlsekoError as exc:
            raise _http(exc)
    filename = f"alseko_reconciliation_{date.today().isoformat()}.xlsx"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/api/alseko/addresses")
async def alseko_addresses(
    q: Optional[str] = None,
    building_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Адреса АЛСЕКО с суммами нагрузок (Гкал/ч); с building_id без q — подсказка по геоадресу здания."""
    async with acquire_conn() as conn:
        try:
            return await ab.address_candidates(conn, q=q, building_id=building_id, limit=limit)
        except ab.AlsekoError as exc:
            raise _http(exc)


@router.post("/api/alseko/buildings/{building_id}/address")
async def alseko_bind_building_address(building_id: int, body: AddressBindBody, user: Editor):
    """Привязка здания к адресу АЛСЕКО (десктоп BigDialog); dry_run=true — только «было → станет»."""
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                return await ab.bind_building_address(
                    conn, building_id, mkr=body.microdistrict, street=body.street, house=body.house,
                    dry_run=body.dry_run, audit_row=_audit_writer(user),
                )
        except ab.AlsekoError as exc:
            raise _http(exc)


@router.post("/api/alseko/consumers/{node_id}/buildings")
async def alseko_bind_consumer_buildings(node_id: int, body: ConsumerBindBody, user: Editor):
    """Назначить зданиям потребителя (zdaniya_2.potrebitel), прежние здания потребителя отвязать."""
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                return await ab.bind_consumer_buildings(
                    conn, node_id, body.building_ids, dry_run=body.dry_run, audit_row=_audit_writer(user),
                )
        except ab.AlsekoError as exc:
            raise _http(exc)
