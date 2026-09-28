"""Электросеть: сверка геометрической привязки и привязка по правилам десктопа (этап 10).

Логика и эталон gid6 — ``database/electrical_binding.py``. Сверка и Excel — всем с токеном;
привязка (в т.ч. предпросмотр) — роль editor+, запись ещё и MUTATIONS_ENABLED;
одна транзакция + audit_log (одна change_group_id на весь пакет).
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database import electrical_binding as eb
from database.connect import acquire_conn

router = APIRouter(tags=["electrical-network"])

Editor = Annotated[AuthUser, Depends(require_roles("editor"))]
ObjectType = Literal["line", "channel", "coupling", "support", "sleeve"]
Tolerance = Query(eb.DEFAULT_TOLERANCE_M, gt=0, le=1000, description="Допуск, м (десктоп D5 = 8)")


class BindTarget(BaseModel):
    object_type: ObjectType
    id: int = Field(..., ge=1)


class BindBody(BaseModel):
    tolerance: float = Field(eb.DEFAULT_TOLERANCE_M, gt=0, le=1000)
    overwrite: bool = Field(False, description="Заменять и неверные привязки, а не только пустые")
    snap_points: bool = Field(False, description="Проецировать муфты и опоры на ЛЭП (десктоп getProject)")
    items: Optional[list[BindTarget]] = Field(None, max_length=5000, description="Пусто — все объекты")
    dry_run: bool = True


def _http(exc: eb.ElectricalError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.detail)


def _audit_writer(user: AuthUser):
    async def write(conn, *, operation: str, table: str, record_id: Optional[int], old=None, new=None,
                    group: Optional[str] = None) -> str:
        return await write_audit_log(
            changed_by=user.username, operation=operation, table_name=table, record_id=record_id,
            old_data=old, new_data=new, change_group_id=group, conn=conn,
        )

    return write


@router.get("/api/electrical-network/reconciliation")
async def electrical_reconciliation(
    tolerance: float = Tolerance,
    kind: Optional[str] = Query(None, description=", ".join(eb.ISSUE_KINDS)),
    object_type: Optional[ObjectType] = None,
    limit: int = Query(200, ge=1, le=5000),
    offset: int = Query(0, ge=0),
):
    """Сверка: концы ЛЭП ↔ источник/приёмник, муфты/опоры/гильзы/каналы ↔ ЛЭП (с координатами)."""
    async with acquire_conn() as conn:
        try:
            result = await eb.reconcile(conn, tolerance)
            items = eb.filter_items(result, kind=kind, object_type=object_type)
        except eb.ElectricalError as exc:
            raise _http(exc)
    return {**result, "total": len(items), "items": items[offset:offset + limit]}


@router.get("/api/electrical-network/reconciliation/report.xlsx")
async def electrical_reconciliation_report(tolerance: float = Tolerance):
    async with acquire_conn() as conn:
        try:
            content = await eb.reconciliation_workbook(conn, tolerance)
        except eb.ElectricalError as exc:
            raise _http(exc)
    filename = f"electrical_reconciliation_{date.today().isoformat()}.xlsx"
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/api/electrical-network/binding")
async def electrical_binding(body: BindBody, user: Editor):
    """Привязка по правилам десктопа; dry_run=true — только план «было → станет»."""
    if not body.dry_run:
        require_mutations_enabled()
    targets = None if body.items is None else [(i.object_type, i.id) for i in body.items]
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                return await eb.bind(
                    conn, tolerance=body.tolerance, overwrite=body.overwrite, snap_points=body.snap_points,
                    targets=targets, dry_run=body.dry_run, audit_row=_audit_writer(user),
                )
        except eb.ElectricalError as exc:
            raise _http(exc)
