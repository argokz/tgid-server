"""Тепловой контур: диагностика, TG, теплопотери + запуск расчёта / edit TG."""

import os
from typing import Annotated, Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
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
from database import heat_losses_norm as heat_norm
from database import heat_losses_store as heat_store
from database.tg_otop import OtopError, calculate_otop_curve
from database.tg_pov_skk import GRAPH_NAMES, TgInputError, calculate_graph, graph_mode
from database.temperature_graph_write import (
    apply_stationary_graph,
    seed_otop_graph,
    seed_pov_skk_graph,
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


TG_MODES = ("auto", "otop", "pov", "skk_pov", "skk_pon")


def _tg_mode(src: dict, mode: str) -> str:
    return graph_mode(src) if mode == "auto" else mode


@router.post("/api/temperature-graphs/sources/{source_id}/recalculate")
async def temperature_graph_recalculate(
    source_id: int,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
    mode: str = Query("otop", pattern="^(auto|otop|pov|skk_pov|skk_pon)$",
                      description="otop — ОТОП; pov — повышенный (П); skk_pov/skk_pon — скорректированный "
                                  "повышенный (СВ) / пониженный (СН); auto — по heatsources.graphtypeid, как десктоп"),
):
    """Пересчёт графика источника (gid8 CTempGraph) с заменой deployedTempGraphs."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        src = await source_design_temps(conn, source_id)
        if src is None:
            raise HTTPException(status_code=404, detail="Heat source not found")
        mode = _tg_mode(src, mode)
        try:
            if mode == "otop":
                inserted = await seed_otop_graph(conn, source_id, src)
            else:
                inserted = await seed_pov_skk_graph(conn, source_id, src, mode)
        except (OtopError, TgInputError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    await write_audit_log(
        changed_by=user.username,
        operation="RECALC",
        table_name="deployedTempGraphs",
        record_id=source_id,
        new_data={"points": inserted, "mode": mode},
    )
    return {"success": True, "points": inserted, "mode": mode}


@router.get("/api/temperature-graphs/sources/{source_id}/preview")
async def temperature_graph_preview(
    source_id: int,
    mode: str = Query("auto", pattern="^(auto|otop|pov|skk_pov|skk_pon)$"),
):
    """Расчёт графика без записи: точки и ошибки проверки исходных данных (коды десктопа)."""
    async with acquire_conn() as conn:
        src = await source_design_temps(conn, source_id)
    if src is None:
        raise HTTPException(status_code=404, detail="Heat source not found")
    mode = _tg_mode(src, mode)
    try:
        if mode == "otop":
            points = calculate_otop_curve(src)
        else:
            points = calculate_graph(src, mode)["points"]
    except TgInputError as exc:
        return {"mode": mode, "name": GRAPH_NAMES.get(mode), "points": [], "errors": exc.codes, "message": str(exc)}
    except (OtopError, ValueError) as exc:
        return {"mode": mode, "name": GRAPH_NAMES.get(mode), "points": [], "errors": [], "message": str(exc)}
    return {"mode": mode, "name": GRAPH_NAMES.get(mode), "points": points, "errors": [], "message": None,
            "graph_type_id": src.get("graphtypeid")}


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
    used by web for fragment heat-loss runs. Расчёт теплопотерь пишет результаты в БД,
    поэтому, кроме роли calculator, нужен MUTATIONS_ENABLED.
    """
    require_mutations_enabled()
    from worker import run_sety_calculation, validate_sety_params

    params = f"-fileID {body.fragment_id} -tg"
    if body.extra_params.strip():
        try:
            validate_sety_params(body.extra_params)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
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


# ---------------------------------------------------------------- нормативные теплопотери (poteriNewPg)


class HeatLossNormRunBody(BaseModel):
    season_id: int = Field(..., ge=1, description="heatLosesMain.id (fact — heatLosesMainFact.id) — сезон")
    loses_type: Literal["norm", "fact"] = Field(
        default="norm", description="norm — нормативные потери, fact — фактические (таблицы *Fact)")
    heat_source_ids: Optional[list[int]] = Field(
        default=None, max_length=500, description="Источники; пусто — все, к которым приписаны участки")
    fragment_id: Optional[int] = Field(default=None, ge=1, description="Режим «по фрагменту» десктопа")
    line_ids: Optional[list[int]] = Field(default=None, max_length=50000,
                                          description="Явный список участков вместо фрагмента")


@router.post("/api/v1/heat-losses/norm/run")
async def run_heat_losses_norm(
    body: HeatLossNormRunBody,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    """Нормативные или фактические теплопотери по источникам (десктоп «Теплопотери», poteriNewPg) через Celery.

    Результат — расчёт (calculation, fileid = NULL) с листами и удельными потерями участков
    (ut_teplo_out); удаление — DELETE /api/v1/calculations/{id}. Очередь задачи — HEAT_LOSSES_QUEUE
    (по умолчанию основная очередь Celery).
    """
    require_mutations_enabled()
    from worker import run_heat_losses_norm as task_fn

    main_table = heat_norm.LOSES_TABLES[body.loses_type]["main"]
    async with acquire_conn() as conn:
        if not await conn.fetchval(f"SELECT count(*) FROM {main_table} WHERE id = $1", body.season_id):
            raise HTTPException(status_code=404, detail="Сезон не найден")
        if not await heat_store.report_table_exists(conn):
            raise HTTPException(
                status_code=503,
                detail="Нет таблицы heatlosses_report_out: примените sql/migrations/20260928_heat_losses_report_out.sql",
            )
    kwargs = body.model_dump()
    kwargs["user"] = user.username
    queue = os.getenv("HEAT_LOSSES_QUEUE") or None
    task = task_fn.apply_async(kwargs=kwargs, queue=queue) if queue else task_fn.apply_async(kwargs=kwargs)
    await write_audit_log(
        changed_by=user.username,
        operation="RUN",
        table_name="heat_losses_norm",
        record_id=body.fragment_id,
        new_data={**body.model_dump(exclude={"line_ids"}), "line_count": len(body.line_ids or []),
                  "task_id": task.id},
    )
    return {"success": True, "task_id": task.id}


@router.get("/api/v1/heat-losses/norm/seasons")
async def heat_losses_norm_seasons(loses_type: Literal["norm", "fact"] = Query("norm")):
    """Сезоны расчёта: heatLosesMain (norm) или heatLosesMainFact (fact)."""
    table = heat_norm.LOSES_TABLES[loses_type]["main"]
    async with acquire_conn() as conn:
        rows = await conn.fetch(f"SELECT id, name, city, d1, d2, a FROM {table} ORDER BY d1 DESC NULLS LAST, id DESC")
    return heat_norm.json_safe({"loses_type": loses_type, "items": [dict(r) for r in rows]})


@router.get("/api/v1/heat-losses/norm/scope")
async def heat_losses_norm_scope(
    season_id: int = Query(..., ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    loses_type: Literal["norm", "fact"] = Query("norm"),
):
    """Что попадёт в расчёт: источники участков (фрагмента), число участков, заданы ли «Условия работы»."""
    tbl = heat_norm.LOSES_TABLES[loses_type]
    async with acquire_conn() as conn:
        season = await conn.fetchrow(f"SELECT id, name, city, d1, d2, a FROM {tbl['main']} WHERE id = $1", season_id)
        if season is None:
            raise HTTPException(status_code=404, detail="Сезон не найден")
        line_filter = "AND l.fileid = $1" if fragment_id is not None else ""
        args = [fragment_id] if fragment_id is not None else []
        sql = heat_norm.SECTIONS_SQL.replace("{hls_table}", tbl["source"]).replace(
            "{line_filter}", line_filter).replace(
            "{source_filter}", "hpsi.heatsourceid IS NOT NULL").replace("ORDER BY hpsi.section_id", "")
        rows = await conn.fetch(
            f"""SELECT s.heatsourceid AS id, count(*)::int AS sections, sum(s.lenp + s.leno) AS pipe_length,
                       hs.name, hs.sourcename,
                       EXISTS(SELECT 1 FROM {tbl['months']} m WHERE m.heatsourceid = s.heatsourceid) AS has_months,
                       EXISTS(SELECT 1 FROM {tbl['source']} p WHERE p.heatsourceid = s.heatsourceid) AS has_parameters,
                       EXISTS(SELECT 1 FROM deployedtempgraphs g WHERE g.hsourceid = s.heatsourceid) AS has_temp_graph
                  FROM ({sql}) s LEFT JOIN heatsources hs ON hs.id = s.heatsourceid
                 GROUP BY s.heatsourceid, hs.name, hs.sourcename ORDER BY s.heatsourceid""",
            *args,
        )
    return heat_norm.json_safe({"season": dict(season), "fragment_id": fragment_id, "loses_type": loses_type,
                                "sources": [dict(r) for r in rows]})


@router.get("/api/v1/heat-losses/norm/results")
async def heat_losses_norm_results(
    fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Расчёты нормативных теплопотерь (новые первыми)."""
    async with acquire_conn() as conn:
        return await heat_store.list_runs(conn, limit=limit, offset=offset, fragment_id=fragment_id)


async def _heat_run_or_404(conn, calculation_id: int) -> dict:
    try:
        run = await heat_store.get_run(conn, calculation_id)
    except heat_store.HeatLossStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if run is None:
        raise HTTPException(status_code=404, detail="Расчёт теплопотерь не найден")
    return run


@router.get("/api/v1/heat-losses/norm/results/{calculation_id}")
async def heat_losses_norm_result(
    calculation_id: int = Path(..., ge=1),
    include_sheets: bool = Query(True),
):
    """Итоги расчёта (по источникам и в целом) и листы десктопа."""
    async with acquire_conn() as conn:
        run = await _heat_run_or_404(conn, calculation_id)
    if not include_sheets:
        run = {k: v for k, v in run.items() if k != "sheets"}
    return run


@router.get("/api/v1/heat-losses/norm/results/{calculation_id}/sections")
async def heat_losses_norm_sections(
    calculation_id: int = Path(..., ge=1),
    heat_source_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
):
    """Удельные потери по участкам (ut_teplo_out) с потерями участка, координаты для карты."""
    async with acquire_conn() as conn:
        run = await _heat_run_or_404(conn, calculation_id)
        return await heat_store.get_sections(conn, calculation_id, heat_source_id=heat_source_id, line_id=line_id,
                                             page=page, page_size=page_size, run=run)


@router.get("/api/v1/heat-losses/norm/results/{calculation_id}/excel")
async def heat_losses_norm_excel(calculation_id: int = Path(..., ge=1)):
    """Excel: листы десктопа (МатХарМаг, МесТемп, НормыЗима/Лето, МесПотери, ГодПотери), итоги и участки."""
    async with acquire_conn() as conn:
        run = await _heat_run_or_404(conn, calculation_id)
        sections = await heat_store.get_sections(conn, calculation_id, page_size=0, run=run)
    data = heat_store.build_excel(run, sections["items"])
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=heat_losses_{calculation_id}.xlsx"},
    )


class WorkConditionsBody(BaseModel):
    season_id: int = Field(..., ge=1)
    tx: Optional[dict[int, float]] = Field(default=None, description="Температура подпитки по месяцам 1..12, °С")
    t_percent: Optional[float] = Field(default=None, ge=0, le=100,
                                       description="heatLosesSource.t_percent, %")
    dry_run: bool = False


@router.post("/api/v1/heat-losses/sources/{source_id}/work-conditions")
async def heat_losses_work_conditions(
    body: WorkConditionsBody,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
    source_id: int = Path(..., ge=1),
):
    """«Условия работы» источника (десктоп set_cond_env_temperatures): месяцы сезона с температурами
    среды и сетевой воды по развёрнутому температурному графику. dry_run — только показать."""
    if body.tx and any(not 1 <= m <= 12 for m in body.tx):
        raise HTTPException(status_code=400, detail="tx: месяцы 1..12")
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            result = await heat_store.prepare_work_conditions(
                conn, heat_source_id=source_id, season_id=body.season_id, tx=body.tx,
                t_percent=body.t_percent, dry_run=body.dry_run)
        except heat_norm.HeatLossInputError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not body.dry_run:
        await write_audit_log(
            changed_by=user.username,
            operation="UPDATE",
            table_name="heatlosessourcemonths",
            record_id=source_id,
            new_data={"season_id": body.season_id, "rows": len(result["months"]), "t_percent": body.t_percent,
                      "created_source_parameters": result["creates_source_parameters"]},
        )
    return result
