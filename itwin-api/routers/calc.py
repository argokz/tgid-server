"""Запуск расчёта sety через Celery, статус задач и результаты расчётов."""

import io
import time
import uuid
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends
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
from worker import celery_app, run_sety_calculation

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
