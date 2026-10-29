"""OGC API — Processes (часть 1: Core, OGC process description, JSON): расчёт, трассировки, выборки.

GET  /api/ogc/processes                        — список процессов
GET  /api/ogc/processes/{id}                   — описание: входы (JSON Schema) и выход
POST /api/ogc/processes/{id}/execution         — запуск {"inputs": {...}, "response": "raw"|"document"}
GET  /api/ogc/jobs/{jobId}                     — состояние задания (асинхронный расчёт)
GET  /api/ogc/jobs/{jobId}/results             — результат задания

Процессы — те же операции, что у MCP-сервера (tgid_mcp/tools.py): параметры, права, частота вызовов и
ответы общие. Синхронные возвращают результат сразу; гидравлический расчёт — задание Celery
(201 + Location на /jobs/{id}). Список заданий (класс job-list) не поддерживается: состояние — по id.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, ValidationError

from auth import AuthUser, require_roles
from routers.ogc import _base, _link
from tgid_mcp import tools as mcp

router = APIRouter(tags=["ogc-processes"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]

_EXC = "http://www.opengis.net/def/exceptions/ogcapi-processes-1/1.0/"
VERSION = "1.0.0"


@dataclass(frozen=True)
class Process:
    id: str
    tool: str
    asynchronous: bool = False
    keywords: tuple[str, ...] = ()


PROCESSES: dict[str, Process] = {p.id: p for p in (
    Process("network-trace", "network_trace", keywords=("трассировка", "topology")),
    Process("valve-isolation", "valve_isolation", keywords=("авария", "задвижки", "mincut")),
    Process("network-select", "select_network", keywords=("выборка", "selection")),
    Process("network-statistics", "network_statistics", keywords=("длина", "объём", "диаметры")),
    Process("regime-analysis", "regime_analysis", keywords=("режим", "пьезометр")),
    Process("thematic-summary", "thematic_summary", keywords=("тематическая карта",)),
    Process("wear-priorities", "wear_priorities", keywords=("износ", "ремонт")),
    Process("data-quality", "data_quality", keywords=("качество данных",)),
    Process("heat-hydraulic", "run_calculation", asynchronous=True, keywords=("расчёт", "sety", "гидравлика")),
)}

# состояние задачи Celery → статус задания OGC
_STATUS = {"PENDING": "accepted", "RECEIVED": "accepted", "STARTED": "running", "PROGRESS": "running",
           "RETRY": "running", "SUCCESS": "successful", "FAILURE": "failed", "REVOKED": "dismissed"}


class ExecuteBody(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: Optional[dict[str, Any]] = None
    response: Literal["raw", "document"] = "raw"


def _problem(status: int, kind: str, title: str, detail: str = "") -> JSONResponse:
    """Исключение OGC API (RFC 7807): type — из словаря стандарта, если он есть."""
    body = {"type": kind if kind.startswith(("http", "about:")) else _EXC + kind, "title": title, "status": status}
    if detail:
        body["detail"] = detail
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def _inline(schema: Any, defs: dict[str, Any]) -> Any:
    """JSON Schema без $ref (описание процесса — самодостаточное)."""
    if isinstance(schema, dict):
        ref = schema.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            return _inline(defs.get(ref.split("/")[-1], {}), defs)
        return {k: _inline(v, defs) for k, v in schema.items() if k != "$defs"}
    if isinstance(schema, list):
        return [_inline(v, defs) for v in schema]
    return schema


def _summary(base: str, process: Process) -> dict[str, Any]:
    tool = mcp.TOOLS[process.tool]
    return {
        "id": process.id,
        "title": tool.title,
        "description": tool.description,
        "version": VERSION,
        "keywords": list(process.keywords),
        "jobControlOptions": ["async-execute"] if process.asynchronous else ["sync-execute"],
        "outputTransmission": ["value"],
        "links": [_link(f"{base}/processes/{process.id}", "self", title=tool.title),
                  _link(f"{base}/processes/{process.id}/execution",
                        "http://www.opengis.net/def/rel/ogc/1.0/execute", title="Запуск")],
    }


def _description(base: str, process: Process) -> dict[str, Any]:
    tool = mcp.TOOLS[process.tool]
    schema = tool.params.model_json_schema()
    defs = schema.get("$defs", {})
    required = set(schema.get("required", []))
    inputs = {}
    for name, field_schema in (schema.get("properties") or {}).items():
        resolved = _inline(field_schema, defs)
        inputs[name] = {
            "title": resolved.pop("title", name),
            "description": resolved.get("description", ""),
            "schema": resolved,
            "minOccurs": 1 if name in required else 0,
            "maxOccurs": 1,
        }
    outputs = {"result": {
        "title": "Результат",
        "description": ("Задание: task_id и состояние; итог — /jobs/{id}/results" if process.asynchronous
                        else "Ответ операции (JSON)"),
        "schema": {"type": "object", "contentMediaType": "application/json"},
    }}
    return {**_summary(base, process), "inputs": inputs, "outputs": outputs}


@router.get("/api/ogc/processes")
async def ogc_processes(request: Request, _: Viewer):
    base = _base(request)
    return {"processes": [_summary(base, p) for p in PROCESSES.values()],
            "links": [_link(f"{base}/processes", "self")]}


@router.get("/api/ogc/processes/{process_id}")
async def ogc_process(request: Request, _: Viewer, process_id: Annotated[str, Path(max_length=60)]):
    process = PROCESSES.get(process_id)
    if process is None:
        return _problem(404, "no-such-process", f"Нет процесса {process_id}")
    return _description(_base(request), process)


def _status_info(base: str, process_id: str, job_id: str, task: dict[str, Any]) -> dict[str, Any]:
    status = _STATUS.get(task.get("status", ""), "running")
    result = task.get("result")
    message = ""
    if status == "successful" and isinstance(result, dict) and result.get("status") not in (None, "success"):
        status = "failed"  # задача отработала, а расчёт — с ошибкой (status: error)
    if isinstance(result, dict):
        message = str(result.get("message") or result.get("error") or "")
    elif task.get("error"):
        message = str(task["error"])
    elif isinstance(task.get("meta"), dict):
        message = str(task["meta"].get("message") or "")
    info: dict[str, Any] = {
        "type": "process",
        "processID": process_id,
        "jobID": job_id,
        "status": status,
        "message": message[:500],
        "links": [_link(f"{base}/jobs/{job_id}", "self", title="Состояние")],
    }
    if status == "successful":
        info["links"].append(_link(f"{base}/jobs/{job_id}/results", "http://www.opengis.net/def/rel/ogc/1.0/results",
                                   title="Результат"))
    return info


@router.post("/api/ogc/processes/{process_id}/execution")
async def ogc_execute(request: Request, user: Viewer, body: ExecuteBody,
                      process_id: Annotated[str, Path(max_length=60)]):
    process = PROCESSES.get(process_id)
    if process is None:
        return _problem(404, "no-such-process", f"Нет процесса {process_id}")
    try:
        result = await mcp.execute(process.tool, body.inputs, user)
    except ValidationError as exc:
        detail = "; ".join(f"{'.'.join(map(str, e['loc'])) or 'inputs'} — {e['msg']}" for e in exc.errors())
        return _problem(400, "invalid-parameter-value", "Неверные входы процесса", detail)
    except mcp.ToolError as exc:
        return _problem(exc.status, "about:blank" if exc.status != 400 else "invalid-parameter-value",
                        str(exc))
    except HTTPException as exc:
        if exc.status_code >= 500:
            return _problem(exc.status_code, "about:blank", "Внутренняя ошибка сервера при выполнении процесса")
        return _problem(exc.status_code, "about:blank", str(exc.detail))
    base = _base(request)
    if process.asynchronous:
        job_id = str(result.get("task_id") or "")
        if not job_id:
            return _problem(500, "about:blank", "Задание не поставлено в очередь")
        info = _status_info(base, process.id, job_id, {"status": "PENDING"})
        return JSONResponse(info, status_code=201, headers={"Location": f"{base}/jobs/{job_id}"})
    payload = {"result": result} if body.response == "document" else result
    return JSONResponse(mcp._compact(payload))


async def _task(job_id: str) -> dict[str, Any]:
    from routers.calc import get_task_status

    return await get_task_status(job_id)


@router.get("/api/ogc/jobs/{job_id}")
async def ogc_job(request: Request, _: Viewer, job_id: Annotated[str, Path(max_length=100)]):
    try:
        task = await _task(job_id)
    except HTTPException:
        return _problem(404, "no-such-job", f"Нет задания {job_id}")
    return _status_info(_base(request), "heat-hydraulic", job_id, task)


@router.get("/api/ogc/jobs/{job_id}/results")
async def ogc_job_results(request: Request, user: Viewer, job_id: Annotated[str, Path(max_length=100)]):
    try:
        task = await _task(job_id)
    except HTTPException:
        return _problem(404, "no-such-job", f"Нет задания {job_id}")
    info = _status_info(_base(request), "heat-hydraulic", job_id, task)
    if info["status"] in ("accepted", "running"):
        return _problem(404, "result-not-ready", "Задание ещё выполняется", info["message"])
    if info["status"] != "successful":
        return _problem(500, "about:blank", "Задание завершилось с ошибкой", info["message"])
    # тот же ответ, что task_status у MCP: журнал sety — текстом, без разметки окна протокола
    status = await mcp.TOOLS["task_status"].run(mcp.TaskParams(task_id=job_id), user)
    return JSONResponse({"result": mcp._compact(status.get("result"))})
