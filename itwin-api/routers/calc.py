"""Запуск расчёта sety через Celery, статус задач и результаты расчётов."""

import io
import time
import uuid
from typing import Annotated, Literal, Optional

from datetime import datetime

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database.calculation_admin import (
    CalculationReferencedError,
    delete_calculation,
    get_calculation,
    list_calculations,
)
from database.calculations import (
    get_calculation_results_excel,
    get_calculation_results_geojson,
    get_latest_calculations,
)
from database.connect import acquire_conn
from database.throttling_calc import (
    calculate_elevator_engine,
    calculate_elevator_parameters,
    calculate_gvs_circulation_diaphragm,
    calculate_orifice_plate_full,
    generate_throttling_excel,
)
from sety_modes import SetyRunRequest, args_to_params, build_sety_args
from worker import celery_app, run_sety_calculation, validate_sety_params

logger = get_logger(__name__)

router = APIRouter(tags=["calculations"])


# Флаги sety, после которых движок пишет в исходные таблицы, а не только в *_out:
# -save_po/-save_po_yes — нагрузки обобщённых потребителей (SQL выполняет воркер),
# -dross_yes — UPDATE сопротивлений realconsumers/generalizedConsumers (sety/out/pt_out.py),
# -save_uf_new — коэффициенты смешения в том же UPDATE.
SOURCE_WRITE_FLAGS = frozenset({"-save_po", "-save_po_yes", "-dross_yes", "-save_uf_new"})


def writes_source_data(tokens: list[str]) -> bool:
    return any(t in SOURCE_WRITE_FLAGS for t in tokens)


class SetyCmdParams(BaseModel):
    params: str  # строка с параметрами для ww.py


@router.post("/run-sety-cmd")
@router.post("/api/v1/run-sety-cmd")
async def run_sety_cmd(
    body: SetyCmdParams,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    try:
        tokens = validate_sety_params(body.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if writes_source_data(tokens):
        require_mutations_enabled()
    request_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # Отправляем задачу в очередь Celery (не блокируем FastAPI)
    task = run_sety_calculation.delay(body.params, request_id)
    logger.info(f"Task dispatched to Celery: {task.id} by {user.username}")
    await write_audit_log(
        changed_by=user.username,
        operation="RUN_SETY",
        table_name="calculation",
        new_data={"params": body.params, "task_id": task.id, "request_id": request_id},
    )

    return {
        "message": "Расчет добавлен в очередь",
        "task_id": task.id,
        "request_id": request_id
    }


@router.get("/task/{task_id}")
@router.get("/api/v1/task/{task_id}")
async def get_task_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.status,
    }

    if task_result.status == 'SUCCESS':
        response["result"] = task_result.result
    elif task_result.status == 'FAILURE':
        response["error"] = str(task_result.result)
    elif task_result.status == 'PROGRESS':
        response["meta"] = task_result.info

    return response


@router.post("/api/calculations/run")
@router.post("/api/v1/calculations/run")
async def run_sety_mode(
    body: SetyRunRequest,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    """Расчёт в режиме десктопа: плановый / аварийный (фактический), один фрагмент или по списку.

    Аргументы sety собираются сервером из типизированных полей (sety_modes.build_sety_args)
    и проходят белый список воркера; автор (-user_gid) — пользователь из токена.
    """
    args = build_sety_args(body, user.username)
    if writes_source_data(args):
        # -save_po/-dross_yes переписывают исходные данные потребителей, а не только результаты
        require_mutations_enabled()
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            "SELECT id FROM fragments WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0",
            body.fragment_ids,
        )
    missing = sorted(set(body.fragment_ids) - {r["id"] for r in rows})
    if missing:
        raise HTTPException(status_code=404, detail=f"Фрагменты не найдены: {', '.join(map(str, missing))}")

    params = args_to_params(args)
    try:
        validate_sety_params(params)
    except ValueError as e:  # защита на случай рассинхрона билдера и белого списка
        raise HTTPException(status_code=400, detail=str(e))

    request_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    if not body.is_list and body.dross:
        # Сигнатура старой задачи: плановый расчёт одного фрагмента понимает и прежний воркер
        task = run_sety_calculation.delay(f"{params} -fileID {body.fragment_ids[0]}", request_id)
    elif not body.is_list:
        task = run_sety_calculation.delay(f"{params} -fileID {body.fragment_ids[0]}", request_id, dross=False)
    else:
        task = run_sety_calculation.delay(params, request_id, dross=body.dross, file_ids=body.fragment_ids)

    logger.info(f"Task dispatched to Celery: {task.id} mode={body.mode} fragments={body.fragment_ids} by {user.username}")
    await write_audit_log(
        changed_by=user.username,
        operation="RUN_SETY",
        table_name="calculation",
        new_data={
            "mode": body.mode,
            "fragment_ids": body.fragment_ids,
            "params": params,
            "task_id": task.id,
            "request_id": request_id,
        },
    )
    return {
        "message": "Расчет добавлен в очередь",
        "task_id": task.id,
        "request_id": request_id,
        "mode": body.mode,
        "fragment_ids": body.fragment_ids,
        "params": params,
    }


@router.get("/api/calculations")
@router.get("/api/v1/calculations")
async def api_calculations_list(
    file_id: Optional[int] = Query(None, ge=1, description="Фрагмент"),
    mode: Optional[Literal["plan", "emergency"]] = Query(None, description="Режим по calc_params.g_is_avar"),
    author: Optional[str] = Query(None, max_length=100, description="Автор (user_gid), подстрока"),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Расчёты (таблица calculation): дата, режим, Tн, наименование, автор, параметры sety."""
    async with acquire_conn() as conn:
        return await list_calculations(
            conn, file_id=file_id, mode=mode, author=author,
            date_from=date_from, date_to=date_to, limit=limit, offset=offset,
        )


@router.delete("/api/calculations/{calculation_id}")
@router.delete("/api/v1/calculations/{calculation_id}")
async def api_calculation_delete(
    calculation_id: int,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    """Удаляет расчёт и его строки во всех *_out (одна транзакция).

    Только при MUTATIONS_ENABLED; роль calculator удаляет свои расчёты, editor/admin — любые.
    """
    require_mutations_enabled()
    async with acquire_conn() as conn:
        calc = await get_calculation(conn, calculation_id)
        if calc is None:
            raise HTTPException(status_code=404, detail="Расчёт не найден")
        if not user.has_role("editor") and (calc.get("user_gid") or "") != user.username:
            raise HTTPException(status_code=403, detail="Чужой расчёт может удалить только editor или admin")
        try:
            result = await delete_calculation(conn, calculation_id)
        except CalculationReferencedError as e:
            raise HTTPException(
                status_code=409,
                detail=f"На расчёт ссылаются данные вне результатов расчёта ({e}); удаление отменено",
            )
    if result is None:
        raise HTTPException(status_code=404, detail="Расчёт не найден")

    calc_row = result["calculation"]
    await write_audit_log(
        changed_by=user.username,
        operation="DELETE",
        table_name="calculation",
        record_id=calculation_id,
        old_data={
            "fileid": calc_row.get("fileid"),
            "name": calc_row.get("name"),
            "user_gid": calc_row.get("user_gid"),
            "tn": calc_row.get("tn"),
            "calculated_at": calc_row["calculated_at"].isoformat() if calc_row.get("calculated_at") else None,
            "deleted_rows": result["deleted_rows"],
        },
    )
    return {
        "success": True,
        "calculation_id": calculation_id,
        "deleted_rows": result["deleted_rows"],
    }


@router.get("/api/calculations/latest")
async def api_calculations_latest(limit: int = 20):
    async with acquire_conn() as conn:
        return await get_latest_calculations(conn, limit)


@router.get("/api/calculations/{calculation_id}/results/geojson")
async def api_calculations_results_geojson(calculation_id: int):
    async with acquire_conn() as conn:
        return await get_calculation_results_geojson(conn, calculation_id)


@router.get("/api/calculations/{calculation_id}/results/excel")
async def api_calculations_results_excel(calculation_id: int):
    async with acquire_conn() as conn:
        excel_bytes = await get_calculation_results_excel(conn, calculation_id)
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=calculation_{calculation_id}_results.xlsx"}
        )


class OrificePlateRequest(BaseModel):
    flow_g: Optional[float] = None
    delta_h: Optional[float] = None
    p1: Optional[float] = None
    p2: Optional[float] = None
    q_heating_gcal: Optional[float] = None
    q_heating_kcal: Optional[float] = None
    t_supply: float = 130.0
    t_return: float = 70.0
    scheme: Literal[
        "bezelevator", "pump_mix", "pre_nozzle", "nozzle", "ventilation", "heater", "gvs_circulation", "gvs"
    ] = "bezelevator"


class ElevatorNozzleRequest(BaseModel):
    q_heating_gcal: Optional[float] = None
    flow_g: Optional[float] = None
    p1: float = 6.0
    p2: float = 4.0
    t1: float = 130.0
    t2: float = 70.0
    t3: float = 95.0
    delta_h_system: float = 1.5


class ThrottlingSigner(BaseModel):
    position: Optional[str] = None
    name: Optional[str] = None


class ThrottlingSheetRequest(BaseModel):
    district: Optional[str] = None
    site_name: Optional[str] = None
    consumer_name: Optional[str] = None
    address: Optional[str] = None
    p1: float
    p2: float
    q_heating_gcal: float = 0.0
    q_vent_gcal: float = 0.0
    q_gvs_gcal: float = 0.0  # максимальная нагрузка ГВС, Гкал/ч
    t1: float = 130.0
    t2: float = 70.0
    t3: float = 95.0
    signers: list[ThrottlingSigner] = []
    organization: Optional[str] = None


@router.post("/api/calc/orifice-plate")
async def api_calc_orifice_plate(req: OrificePlateRequest):
    try:
        return calculate_orifice_plate_full(
            flow_g=req.flow_g,
            delta_h=req.delta_h,
            p1=req.p1,
            p2=req.p2,
            q_heating_gcal=req.q_heating_gcal,
            q_heating_kcal=req.q_heating_kcal,
            t_supply=req.t_supply,
            t_return=req.t_return,
            scheme=req.scheme,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/api/calc/elevator-nozzle")
async def api_calc_elevator_nozzle(req: ElevatorNozzleRequest):
    try:
        return calculate_elevator_parameters(
            q_heating_gcal=req.q_heating_gcal,
            flow_g=req.flow_g,
            p1=req.p1,
            p2=req.p2,
            t1=req.t1,
            t2=req.t2,
            t3=req.t3,
            delta_h_system=req.delta_h_system,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


class GvsCirculationRequest(BaseModel):
    circulation_flow: float = Field(..., gt=0, description="Расход в циркуляционной линии ГВС, т/ч")
    required_head: float = Field(..., description="Расчётный напор на входе водоразборных приборов a12, м")
    circulation_loss: float = Field(0.0, ge=0, description="Потери напора в циркуляционном трубопроводе a11, м")
    return_head: float = Field(..., description="Пьезометрический напор в обратном трубопроводе узла, м")
    draw_from: Literal["supply", "return"] = "supply"
    min_diameter: float = Field(3.0, gt=0, description="Минимальный диаметр диафрагмы a15, мм")


class ElevatorEngineRequest(BaseModel):
    available_head: float = Field(..., description="Располагаемый напор узла Нп - Но, м")
    heating_flow: float = Field(..., gt=0, description="Расход на отопление, т/ч")
    mixing_ratio: float = Field(..., gt=0, description="Коэффициент смешения элеватора u (a6)")
    system_loss: float = Field(..., gt=0, description="Потери напора в системе отопления hс (a7), м")
    min_nozzle_diameter: float = Field(3.0, gt=0, description="Минимальный диаметр сопла a14, мм")
    min_diameter: float = Field(3.0, gt=0, description="Минимальный диаметр диафрагмы a15, мм")
    regime: int = Field(1, ge=1, le=6, description="Режим расчёта дросселирования (a13): 1 или 6")
    circulation_head: float = Field(0.0, ge=0, description="Напор на подпорно-циркуляционной диафрагме b37, м")
    gvs_heater_loss: float = Field(0.0, ge=0, description="Потери в подогревателе ГВС 2-й ступени a23, м")
    gvs_sequential_flow: float = Field(0.0, ge=0, description="Расход ГВС последовательной схемы, т/ч")
    graph_otop: bool = False
    street_share: float = Field(1.0, ge=0, le=1, description="Доля уличного фасада")


@router.post("/api/calc/gvs-circulation-diaphragm")
async def api_calc_gvs_circulation(req: GvsCirculationRequest):
    """Ограничительная диафрагма циркуляционной линии открытой ГВС (движок sety, drvary1 b39–b41)."""
    try:
        return calculate_gvs_circulation_diaphragm(**req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/api/calc/elevator-engine")
async def api_calc_elevator_engine(req: ElevatorEngineRequest):
    """Сопло элеватора и диафрагма перед соплом по напорам узла (движок sety, drvary1 b7–b9, b21–b26)."""
    try:
        return calculate_elevator_engine(**req.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/api/calc/throttling-sheet")
async def api_calc_throttling_sheet(req: ThrottlingSheetRequest):
    data = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    try:
        excel_bytes = generate_throttling_excel(data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=throttling_calculation_sheet.xlsx"},
    )
