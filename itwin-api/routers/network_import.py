"""Импорт сети из файлов (этап 10): SHP, Excel/CSV, координаты узлов.

inspect — разбор файла (колонки, образец строк, предложенное сопоставление), роль editor+;
run с dry_run=true — превью (импорт выполняется в транзакции и откатывается), editor+;
run с dry_run=false — применение: admin + TOPOLOGY_MUTATIONS_ENABLED + MUTATIONS_ENABLED
(как правки топологии: создаются/двигаются узлы и участки; отмена — POST /api/topology/undo).
"""

import json
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app_logging import get_logger
from auth import AuthUser, require_roles
from database.network_import import (
    MAX_UPLOAD_BYTES,
    ImportRowErrors,
    describe_source,
    parse_upload,
    run_import,
    validate_params,
)
from routers.topology import _topology_http_error, require_topology_mutations_enabled

logger = get_logger(__name__)

router = APIRouter(tags=["network-import"])


async def _read_files(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    out = []
    total = 0
    for f in files:
        content = await f.read(MAX_UPLOAD_BYTES + 1)
        total += len(content)
        if len(content) > MAX_UPLOAD_BYTES or total > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Загрузка больше 20 МБ")
        out.append((f.filename or "upload", content))
    return out


@router.post("/api/import/inspect")
@router.post("/api/v1/import/inspect")
async def import_inspect(
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
    files: list[UploadFile] = File(..., description="zip с shapefile, файлы .shp/.shx/.dbf/.prj/.cpg, .xlsx или .csv"),
    mode: str = Form("nodes", description="nodes | lines | coords"),
    encoding: Optional[str] = Form(None),
    sheet: Optional[str] = Form(None),
):
    """Разбор файла: колонки, образец строк, поля назначения режима, предложенное сопоставление."""
    try:
        validate_params({"mode": mode})
        src = parse_upload(await _read_files(files), encoding=encoding or None, sheet=sheet or None)
        return describe_source(src, mode)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/import/run")
@router.post("/api/v1/import/run")
async def import_run(
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
    files: list[UploadFile] = File(...),
    params: str = Form(..., description="JSON: mode, fileid, source_crs, mapping, match_by, snap_tolerance_m, "
                                        "recalc_lengths, build_missing_lines, skip_errors, encoding, sheet"),
    dry_run: bool = Form(True),
):
    """Превью (dry_run) или применение импорта; ошибки строк при применении без skip_errors — 422."""
    # dry-run тоже пишет (в откатываемой транзакции) — только при включённой записи
    require_topology_mutations_enabled()
    if not dry_run and not user.has_role("admin"):
        raise HTTPException(status_code=403, detail="Применение импорта — роль admin (правка топологии)")
    try:
        parsed = json.loads(params)
        if not isinstance(parsed, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="params — JSON-объект")
    try:
        validate_params(parsed)
        src = parse_upload(
            await _read_files(files), encoding=parsed.get("encoding") or None, sheet=parsed.get("sheet") or None,
        )
        return await run_import(src, parsed, dry_run=dry_run, actor=user.username)
    except ImportRowErrors as e:
        raise HTTPException(
            status_code=422,
            detail={"code": "row_errors", "message": str(e), "report": e.report},
        )
    except Exception as e:  # noqa: BLE001 — единое отображение ошибок топологии
        raise _topology_http_error(e, "importing network")
