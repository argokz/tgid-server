"""Фоновые файлы (паспорт, Excel-отчёты, сверки): постановка задачи, статус, скачивание.

Поток: POST /api/v1/file-jobs {kind, params} → task_id; GET /api/v1/file-jobs/{task_id} — статус
(PENDING / PROGRESS / SUCCESS / FAILURE, ready, success, message); GET …/download — готовый файл
из Redis (TTL FILE_JOBS_TTL, по умолчанию 1 ч). Очередь Celery — FILE_JOBS_QUEUE (по умолчанию
основная). Синхронные эндпоинты тех же файлов остаются для совместимости.
"""

from __future__ import annotations

from typing import Annotated, Any

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field, ValidationError

from app_logging import get_logger
from auth import AuthUser, require_roles
from database import file_jobs

logger = get_logger(__name__)
router = APIRouter(tags=["file-jobs"])

Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


class FileJobBody(BaseModel):
    kind: str = Field(..., description=", ".join(file_jobs.KINDS))
    params: dict[str, Any] = Field(default_factory=dict)


def _check_owner(user: AuthUser, owner: str | None) -> None:
    if owner and owner != user.username and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Файл сформирован другим пользователем")


@router.get("/api/v1/file-jobs/kinds")
async def file_job_kinds():
    return {"items": list(file_jobs.KINDS), "ttl": file_jobs.ttl_seconds(), "queue": file_jobs.queue_name()}


@router.post("/api/v1/file-jobs")
async def start_file_job(body: FileJobBody, user: Viewer):
    try:
        params = file_jobs.validate_params(body.kind, body.params)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors(include_url=False, include_context=False))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from worker import build_file_job

    kwargs = {"kind": body.kind, "params": params, "user": user.username}
    queue = file_jobs.queue_name()
    task = build_file_job.apply_async(kwargs=kwargs, queue=queue) if queue else build_file_job.apply_async(kwargs=kwargs)
    logger.info("file job %s kind=%s queued by %s", task.id, body.kind, user.username)
    return {"task_id": task.id, "kind": body.kind, "params": params}


@router.get("/api/v1/file-jobs/{task_id}")
async def file_job_status(task_id: str, user: Viewer):
    from worker import celery_app

    res = AsyncResult(task_id, app=celery_app)
    state = res.status
    out: dict[str, Any] = {"task_id": task_id, "state": state, "ready": state in ("SUCCESS", "FAILURE"),
                           "success": None, "message": None}
    if state == "PROGRESS" and isinstance(res.info, dict):
        out["message"] = res.info.get("message")
        out["kind"] = res.info.get("kind")
    elif state == "SUCCESS":
        result = res.result if isinstance(res.result, dict) else {}
        ok = result.get("status") == "success"
        out.update(success=ok, kind=result.get("kind"), message=result.get("message"))
        if ok:
            meta = await run_in_threadpool(file_jobs.load_meta, task_id)
            if meta is None:
                out.update(success=False, message="Файл удалён по истечении срока хранения — сформируйте заново")
            else:
                _check_owner(user, meta.get("owner"))
                out.update(filename=meta["filename"], size=meta["size"], elapsed_s=result.get("elapsed_s"))
        else:
            out["status_code"] = result.get("status_code")
    elif state == "FAILURE":
        out.update(success=False, message="Задача завершилась с ошибкой воркера")
    return out


@router.get("/api/v1/file-jobs/{task_id}/download")
async def file_job_download(task_id: str, user: Viewer):
    stored = await run_in_threadpool(file_jobs.load_result, task_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Файл не готов или срок хранения истёк")
    meta, data = stored
    _check_owner(user, meta.get("owner"))
    headers = {"Content-Disposition": file_jobs.content_disposition(meta["filename"]), **(meta.get("headers") or {})}
    headers["Access-Control-Expose-Headers"] = ", ".join(["Content-Disposition", *(meta.get("headers") or {})])
    return Response(data, media_type=meta.get("media_type") or file_jobs.XLSX, headers=headers)
