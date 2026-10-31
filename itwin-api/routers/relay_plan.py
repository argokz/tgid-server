"""План перекладок (database/relay_plan.py): расценки за метр по диаметру и план в пределах бюджета.

GET  /api/v1/relay/prices      — расценки перекладки по классам диаметра
PUT  /api/v1/relay/prices      — заменить расценки (право «Справочники»)
POST /api/v1/relay/plan        — план: объекты перекладки, снятый ожидаемый ущерб, сравнение «старые первыми»
POST /api/v1/relay/plan.xlsx   — тот же план в Excel: итоги, объекты, участки (право «Выгрузка»)
GET  /api/v1/relay/consequences          — когда считались последствия аварий участков (кого отключит)
POST /api/v1/relay/consequences/refresh  — пересчитать их после изменения сети (право «Расчёт»)
"""
from __future__ import annotations

from typing import Annotated, Any, Literal, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import outage_consequence as oc
from database import relay_plan as rp
from database.connect import acquire_conn
from database.passport_excel import XLSX_MEDIA_TYPE

router = APIRouter(tags=["relay-plan"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Refs = Annotated[AuthUser, Depends(require_permission("refs"))]
Calc = Annotated[AuthUser, Depends(require_permission("calc_run"))]
Export = Annotated[AuthUser, Depends(require_permission("export"))]


def _http(exc: rp.PlanError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


class PriceIn(BaseModel):
    dn_max_mm: int = Field(ge=10, le=3000)
    price_per_m: float = Field(gt=0, le=1e9)
    currency: str = Field("KZT", min_length=1, max_length=8)
    source: Optional[str] = Field(None, max_length=300)


class PricesIn(BaseModel):
    prices: list[PriceIn] = Field(max_length=100)


class PlanIn(BaseModel):
    budget: float = Field(gt=0, le=1e13, description="Километры (unit=km) или деньги (unit=money)")
    unit: Literal["km", "money"] = "km"
    run_id: Optional[int] = Field(None, ge=1, description="Расчёт прогноза; нет — последний")
    fileid: Optional[int] = Field(None, ge=1, description="Только этот фрагмент")
    job_overhead_m: float = Field(rp.JOB_OVERHEAD_M, ge=0, le=1000,
                                  description="Постоянные затраты объекта перекладки в метрах трубы")
    objective: Literal["consumers", "load", "wear", "failures"] = Field(
        "consumers", description="Последствия повреждения: потребители, нагрузка, оценка износа или без них")


@router.get("/api/v1/relay/prices")
async def relay_prices(_: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await rp.list_prices(conn)


@router.put("/api/v1/relay/prices", dependencies=[Depends(require_mutations_enabled)])
async def relay_prices_put(body: PricesIn, user: Refs) -> list[dict[str, Any]]:
    try:
        async with acquire_conn() as conn:
            return await rp.set_prices(conn, [p.model_dump() for p in body.prices], user.username)
    except rp.PlanError as exc:
        raise _http(exc) from exc


async def _plan(body: PlanIn, *, with_lines: bool = False) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await rp.plan(conn, budget=body.budget, unit=body.unit, run_id=body.run_id, fileid=body.fileid,
                                 job_overhead_m=body.job_overhead_m, objective=body.objective, with_lines=with_lines)
    except rp.PlanError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/relay/plan")
async def relay_plan(body: PlanIn, _: Viewer) -> dict[str, Any]:
    return await _plan(body)


@router.post("/api/v1/relay/plan.xlsx")
async def relay_plan_xlsx(body: PlanIn, _: Export) -> Response:
    p = await _plan(body, with_lines=True)
    filename = "План перекладок.xlsx"
    return Response(rp.plan_workbook(p), media_type=XLSX_MEDIA_TYPE, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    })


@router.get("/api/v1/relay/consequences")
async def relay_consequences(_: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await oc.status(conn)


@router.post("/api/v1/relay/consequences/refresh", dependencies=[Depends(require_mutations_enabled)])
async def relay_consequences_refresh(user: Calc) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await oc.refresh(conn, user.username)
