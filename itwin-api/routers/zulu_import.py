"""Переход с ZuluGIS: загрузка слоя и фоновая конвертация во фрагмент .itwin (database/zulu_import.py).

POST /api/v1/zulu/upload  — файлы слоя Zulu или zip папки: проверка, объекты по типам, upload_id (на TTL хранилища)
POST /api/v1/zulu/convert — фоновая задача file-jobs «zulu_convert» для своей загрузки; статус и файл —
                            GET /api/v1/file-jobs/{task_id} и …/download. Права — как у импорта фрагмента.
"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, require_permission
from database import file_jobs, zulu_import

logger = get_logger(__name__)

router = APIRouter(tags=["zulu-import"])

Importer = Annotated[AuthUser, Depends(require_permission("import", kind="line", action="create"))]
MAX_UPLOAD_BYTES = 200 * 1024 * 1024


class ZuluConvertBody(BaseModel):
    upload_id: str = Field(..., pattern=r"^[0-9a-f]{32}$")
    name: str = Field(..., min_length=1, max_length=50, pattern=r"\S", description="Название фрагмента")
    tn: float = Field(..., ge=-60, le=20, description="Расчётная температура наружного воздуха, °C")


@router.post("/api/v1/zulu/upload")
async def zulu_upload(
    user: Importer,
    files: list[UploadFile] = File(..., description="файлы слоя Zulu (*.b00…, *.d*, *.l*, *.zsx, *.zx, *.sqlite) или zip"),
    layer: Optional[str] = Form(None, max_length=200, description="слой, если в загрузке их несколько"),
):
    """Проверить слой Zulu и сохранить его для конвертации: объекты по типам, строки баз слоя."""
    data: list[tuple[str, bytes]] = []
    total = 0
    for f in files:
        content = await f.read(MAX_UPLOAD_BYTES + 1)
        total += len(content)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Загрузка больше 200 МБ")
        data.append((f.filename or "upload", content))
    try:
        return await run_in_threadpool(zulu_import.upload, data, user.username or user.sub or "", layer or None)
    except zulu_import.ZuluImportError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.post("/api/v1/zulu/convert")
async def zulu_convert(body: ZuluConvertBody, user: Importer):
    """Фоновая конвертация своей загрузки во фрагмент .itwin; дальше — импорт фрагмента с превью."""
    meta = await run_in_threadpool(zulu_import.upload_meta, body.upload_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="Загрузка слоя не найдена или срок хранения истёк")
    if meta.get("owner") != (user.username or user.sub or ""):
        raise HTTPException(status_code=403, detail="Это чужая загрузка")
    from worker import build_file_job

    params = body.model_dump()
    kwargs = {"kind": "zulu_convert", "params": params, "user": user.username}
    queue = file_jobs.queue_name()
    task = build_file_job.apply_async(kwargs=kwargs, queue=queue) if queue else build_file_job.apply_async(kwargs=kwargs)
    logger.info("zulu convert %s слоя %s — %s", task.id, meta.get("layer"), user.username)
    return {"task_id": task.id, "kind": "zulu_convert", "layer": meta.get("layer")}
