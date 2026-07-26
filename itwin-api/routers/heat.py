"""Тепловой контур: диагностика, TG, теплопотери + запуск расчёта / edit TG."""

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database.connect import acquire_conn
from database.consumer_load_diagnostics import (
    get_consumer_load_diagnostic,
    get_consumer_load_diagnostics,
    get_consumer_load_lookups,
)
from database.heat_losses import (
    get_heat_loss_lookups,
    get_heat_loss_season,
    get_heat_loss_seasons,
    get_heat_loss_source,
    get_heat_loss_sources,
)
from database.temperature_graph_write import (
    apply_stationary_graph,
    seed_linear_graph,
    source_design_temps,
)
from database.temperature_graphs import (
    get_temperature_graph_lookups,
    get_temperature_graph_source,
    get_temperature_graph_sources,
)

router = APIRouter(tags=["heat"])


@router.get("/api/consumer-load-diagnostics/lookups")
async def consumer_load_diagnostic_lookups():
    async with acquire_conn() as conn:
        return await get_consumer_load_lookups(conn)


@router.get("/api/consumer-load-diagnostics/consumers")
async def consumer_load_diagnostic_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    diagnostic: Optional[str] = Query(
        None, pattern="^(zero_load|closed|disconnected|not_calculated)$"
    ),
    consumer_type: Optional[str] = Query(
        None, pattern="^(generalized|real)$"
    ),
    fragment_id: Optional[int] = Query(None, ge=1),
    state_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_consumer_load_diagnostics(
            conn, page=page, page_size=page_size, diagnostic=diagnostic,
            consumer_type=consumer_type, fragment_id=fragment_id,
            state_id=state_id, search=search,
        )


@router.get("/api/consumer-load-diagnostics/consumers/{consumer_type}/{consumer_id}")
async def consumer_load_diagnostic_card(
    consumer_type: str = Path(..., pattern="^(generalized|real)$"),
    consumer_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        result = await get_consumer_load_diagnostic(
            conn, consumer_type, consumer_id
        )
    if result is None:
        raise HTTPException(status_code=404, detail="Consumer not found")
    return result


@router.get("/api/temperature-graphs/lookups")
async def temperature_graph_lookups():
    async with acquire_conn() as conn:
        return await get_temperature_graph_lookups(conn)


@router.get("/api/temperature-graphs/sources")
async def temperature_graph_source_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    graph_status: Optional[str] = Query(
        None, pattern="^(ready|missing|duplicates|incomplete)$"
    ),
    summer_status: Optional[str] = Query(None, pattern="^(ready|missing)$"),
    graph_type_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_temperature_graph_sources(
            conn, page=page, page_size=page_size, graph_status=graph_status,
            summer_status=summer_status, graph_type_id=graph_type_id,
            fragment_id=fragment_id, search=search,
        )


@router.get("/api/temperature-graphs/sources/{source_id}")
async def temperature_graph_source_card(source_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_temperature_graph_source(conn, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Heat source not found")
    return result


class StationaryGraphBody(BaseModel):
    t1: float
    t2: float
    t3: float
    tv: float


@router.post("/api/temperature-graphs/sources/{source_id}/stationary")
async def temperature_graph_stationary(
    source_id: int,
    body: StationaryGraphBody,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
):
    """Desktop «Стационарный»: overwrite curve values on existing points."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        updated = await apply_stationary_graph(
            conn, source_id, t1=body.t1, t2=body.t2, t3=body.t3, tv=body.tv
        )
    await write_audit_log(
        changed_by=user.username,
        operation="UPDATE",
        table_name="deployedTempGraphs",
        record_id=source_id,
        new_data=body.model_dump(),
    )
    return {"success": True, "updated_points": updated}


@router.post("/api/temperature-graphs/sources/{source_id}/recalculate")
async def temperature_graph_recalculate(
    source_id: int,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
):
    """Seed linear TG from heatsources design temps (OTOP-like minimal port)."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        src = await source_design_temps(conn, source_id)
        if src is None:
            raise HTTPException(status_code=404, detail="Heat source not found")
        tn_min = src.get("tn_5")
        tn_max = src.get("tn_1")
        t1 = src.get("t1_r")
        t2 = src.get("t2_r")
        t3 = src.get("t3_r") or t1
        if None in (tn_min, tn_max, t1, t2):
            raise HTTPException(
                status_code=400,
                detail="Источник не имеет tn_5/tn_1/t1_r/t2_r — заполните параметры перед расчётом TG",
            )
        try:
            inserted = await seed_linear_graph(
                conn,
                source_id,
                tn_min=float(tn_min),
                tn_max=float(tn_max),
                t1_design=float(t1),
                t2_design=float(t2),
                t3_design=float(t3),
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    await write_audit_log(
        changed_by=user.username,
        operation="RECALC",
        table_name="deployedTempGraphs",
        record_id=source_id,
        new_data={"points": inserted},
    )
    return {"success": True, "points": inserted}


@router.get("/api/heat-losses/lookups")
async def heat_loss_lookups():
    async with acquire_conn() as conn:
        return await get_heat_loss_lookups(conn)


@router.get("/api/heat-losses/seasons")
async def heat_loss_season_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    city: Optional[str] = Query(None, max_length=200),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_heat_loss_seasons(
            conn, page=page, page_size=page_size, city=city, search=search
        )


@router.get("/api/heat-losses/seasons/{season_id}")
async def heat_loss_season_card(season_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_heat_loss_season(conn, season_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Heat-loss season not found")
    return result


@router.get("/api/heat-losses/sources")
async def heat_loss_source_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    fragment_id: Optional[int] = Query(None, ge=1),
    readiness: Optional[str] = Query(None, pattern="^(ready|incomplete)$"),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_heat_loss_sources(
            conn, page=page, page_size=page_size, fragment_id=fragment_id,
            readiness=readiness, search=search,
        )


@router.get("/api/heat-losses/sources/{source_id}")
async def heat_loss_source_card(source_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_heat_loss_source(conn, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Heat source not found")
    return result


class HeatLossRunBody(BaseModel):
    fragment_id: int = Field(..., ge=1, description="fileID / fragment for sety")
    extra_params: str = Field(
        default="",
        description="Additional sety CLI flags (space-separated)",
    )


@router.post("/api/heat-losses/run")
@router.post("/api/v1/heat-losses/run")
async def run_heat_losses(
    body: HeatLossRunBody,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    """Launch seasonal heat-loss oriented sety job (-fileID … -tg, no -no_teplopoter).

    Full poteriNewPg desktop suite remains a follow-up; this wires the Celery path
    used by web for fragment heat-loss runs.
    """
    from worker import run_sety_calculation

    params = f"-fileID {body.fragment_id} -tg"
    if body.extra_params.strip():
        params = f"{params} {body.extra_params.strip()}"
    task = run_sety_calculation.delay(params)
    await write_audit_log(
        changed_by=user.username,
        operation="RUN",
        table_name="heat_losses",
        record_id=body.fragment_id,
        new_data={"params": params, "task_id": task.id},
    )
    return {"success": True, "task_id": task.id, "params": params}
