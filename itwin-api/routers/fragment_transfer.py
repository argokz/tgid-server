"""Экспорт, импорт и слияние фрагментов (.tgid десктопа), этап 10.

export — любой вошедший (только чтение);
import/merge с dry_run=true — превью в откатываемой транзакции, роль editor+ и флаги записи;
import/merge с dry_run=false — admin + MUTATIONS_ENABLED + TOPOLOGY_MUTATIONS_ENABLED;
отмена — POST /api/topology/undo (удаляет созданные строки). Формат — database/fragment_transfer.py.
"""

import os
import re
from typing import Annotated, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, require_roles
from database.connect import get_pool
from database.fragment_transfer import (
    MAX_UPLOAD_BYTES,
    FragmentFileError,
    export_fragment_zip,
    fragment_summary,
    import_sections,
    merge_fragments,
    parse_tgid,
)
from database.topology import _run
from routers.piezometer import invalidate_topology_cache
from routers.topology import _topology_http_error, require_topology_mutations_enabled

logger = get_logger(__name__)

router = APIRouter(tags=["fragments"])


def _require_apply_rights(user: AuthUser, dry_run: bool) -> None:
    # dry-run тоже пишет (в откатываемой транзакции) — только при включённой записи
    require_topology_mutations_enabled()
    if not dry_run and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Применение — роль admin (создание узлов и участков)")


def _error(e: Exception, what: str) -> HTTPException:
    if isinstance(e, FragmentFileError):
        return HTTPException(status_code=400, detail=str(e))
    if isinstance(e, LookupError):
        return HTTPException(status_code=404, detail=str(e))
    return _topology_http_error(e, what)


@router.get("/api/fragments/{fileid}/export")
@router.get("/api/v1/fragments/{fileid}/export")
async def export_fragment(fileid: int, _: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    """Файл .tgid (zip с tgid.txt) — как «Экспорт фрагмента» десктопа."""
    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            data, counts, name = await export_fragment_zip(
                conn, fileid, {"database": os.getenv("DB_NAME", ""), "user": "itwin"}
            )
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))
    safe = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or f"fragment_{fileid}"
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename=fragment_{fileid}.tgid; filename*=UTF-8''{quote(safe)}.tgid",
            "X-Fragment-Rows": ",".join(f"{k}={v}" for k, v in counts.items() if v),
        },
    )


@router.get("/api/fragments/{fileid}/summary")
@router.get("/api/v1/fragments/{fileid}/summary")
async def fragment_rows(fileid: int, _: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    """Число строк фрагмента по таблицам экспорта (сверка экспорт → импорт)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            return {"fileid": fileid, "tables": await fragment_summary(conn, fileid)}
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e))


@router.post("/api/fragments/import")
@router.post("/api/v1/fragments/import")
async def import_fragment(
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
    file: UploadFile = File(..., description=".tgid (zip с tgid.txt) или tgid.txt"),
    name: Optional[str] = Form(None, description="Название нового фрагмента"),
    dry_run: bool = Form(True),
):
    """Импорт фрагмента новым фрагментом (все объекты получают новые id)."""
    _require_apply_rights(user, dry_run)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 100 МБ")
    try:
        sections = parse_tgid(content)

        async def body(conn, op):
            rep = await import_sections(conn, op, sections, name=(name or "").strip() or None)
            await op.audit("INSERT", "fragments", rep["fileid"],
                           {"operation": "fragment_import", "file": file.filename, "tables": rep["tables"]})
            return rep

        result = await _run(dry_run, body, operation="fragment_import", actor=user.username)
    except Exception as e:  # noqa: BLE001
        raise _error(e, "importing fragment")
    if not dry_run:
        invalidate_topology_cache()
    return result


class MergeRequest(BaseModel):
    fragment_ids: list[int] = Field(..., min_length=2, max_length=20)
    name: Optional[str] = Field(None, max_length=60, description="Название объединённого фрагмента")
    unify_external_codes: bool = Field(False, description="Свести коды с одинаковым названием в один")
    dry_run: bool = True


@router.post("/api/fragments/merge")
@router.post("/api/v1/fragments/merge")
async def merge(body: MergeRequest, user: Annotated[AuthUser, Depends(require_roles("editor"))]):
    """Слияние: копии фрагментов сводятся в новый фрагмент (unite_tgid.py); исходные не меняются."""
    _require_apply_rights(user, body.dry_run)

    async def run(conn, op):
        rep = await merge_fragments(conn, op, body.fragment_ids, body.name, body.unify_external_codes)
        await op.audit("INSERT", "fragments", rep["fileid"],
                       {"operation": "fragment_merge", "sources": body.fragment_ids, "tables": rep["tables"]})
        return rep

    try:
        result = await _run(body.dry_run, run, operation="fragment_merge", actor=user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # noqa: BLE001
        raise _error(e, "merging fragments")
    if not body.dry_run:
        invalidate_topology_cache()
    return result
