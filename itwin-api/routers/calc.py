"""Запуск расчёта sety через Celery, статус задач и результаты расчётов."""

import io
import time
import uuid
from typing import Annotated, Literal, Optional

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, require_roles
from database.calculations import (
    get_calculation_results_excel,
    get_calculation_results_geojson,
    get_latest_calculations,
)
from database.connect import acquire_conn
from database.throttling_calc import (
    calculate_elevator_parameters,
    calculate_orifice_plate_full,
    generate_throttling_excel,
)
from worker import celery_app, run_sety_calculation, validate_sety_params

logger = get_logger(__name__)

router = APIRouter(tags=["calculations"])


class SetyCmdParams(BaseModel):
    params: str  # строка с параметрами для ww.py


@router.post("/run-sety-cmd")
@router.post("/api/v1/run-sety-cmd")
async def run_sety_cmd(
    body: SetyCmdParams,
    user: Annotated[AuthUser, Depends(require_roles("calculator"))],
):
    try:
        validate_sety_params(body.params)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
