"""Формы обходов (database/forms.py).

GET    /api/v1/forms                     — формы с полями текущей версии (active=true — только действующие:
                                           полевое приложение хранит их на телефоне)
GET    /api/v1/forms/types               — типы полей
GET    /api/v1/forms/{id}?version=       — форма (версия — по умолчанию текущая)
POST   /api/v1/forms                     — новая форма (администратор)
PUT    /api/v1/forms/{id}                — изменить; поля изменились — новая версия (администратор)
PATCH  /api/v1/forms/{id}                — включить / выключить (администратор)
POST   /api/v1/forms/import-xlsform      — разобрать XLSForm (.xlsx): описание формы и что не перенесено (без записи)
GET    /api/v1/forms/{id}/export.xlsx    — заполнения формы в Excel (право «Выгрузка»)
POST   /api/v1/forms/submissions         — заполнение с телефона (право «Журналы»); повтор с тем же client_id — 200
GET    /api/v1/work-orders/{id}/forms    — заполнения наряда с полями своей версии
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, Response, UploadFile

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import forms as fm
from database.connect import acquire_conn

router = APIRouter(tags=["forms"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Admin = Annotated[AuthUser, Depends(require_roles("admin"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
Exporter = Annotated[AuthUser, Depends(require_permission("export"))]
WRITE = [Depends(require_mutations_enabled)]
FormId = Annotated[int, Path(ge=1)]
MAX_XLSFORM_BYTES = 2_000_000
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _http(exc: fm.FormError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/forms")
async def forms_list(_: Viewer, active: bool = False) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await fm.list_forms(conn, active_only=active)


@router.get("/api/v1/forms/types")
async def form_types(_: Viewer) -> list[dict[str, str]]:
    return [{"type": k, "label": v} for k, v in fm.TYPE_LABELS.items()]


@router.post("/api/v1/forms/import-xlsform")
async def form_import_xlsform(_: Admin, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read(MAX_XLSFORM_BYTES + 1)
    if len(data) > MAX_XLSFORM_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 2 МБ")
    try:
        form, warnings = fm.parse_xlsform(data)
        fm.FormSchema.model_validate(form["schema"])  # то, что перенесено, должно быть правильной формой
    except fm.FormError as exc:
        raise _http(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Форма из файла не прошла проверку: {exc}") from exc
    return {"form": form, "warnings": warnings}


@router.get("/api/v1/forms/{form_id}")
async def form_get(form_id: FormId, _: Viewer, version: Optional[int] = Query(None, ge=1)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await fm.get_form(conn, form_id, version)
    except fm.FormError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/forms", dependencies=WRITE)
async def form_create(body: fm.FormIn, user: Admin) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await fm.create_form(conn, body, user.username)


@router.put("/api/v1/forms/{form_id}", dependencies=WRITE)
async def form_update(form_id: FormId, body: fm.FormIn, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await fm.update_form(conn, form_id, body, user.username)
    except fm.FormError as exc:
        raise _http(exc) from exc


@router.patch("/api/v1/forms/{form_id}", dependencies=WRITE)
async def form_set_active(form_id: FormId, body: fm.FormPatch, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await fm.set_active(conn, form_id, body.active, user.username)
    except fm.FormError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/forms/{form_id}/export.xlsx")
async def form_export(form_id: FormId, _: Exporter) -> Response:
    try:
        async with acquire_conn() as conn:
            name, data = await fm.export_xlsx(conn, form_id)
    except fm.FormError as exc:
        raise _http(exc) from exc
    return Response(data, media_type=XLSX,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})


@router.post("/api/v1/forms/submissions", dependencies=WRITE)
async def form_submit(body: fm.SubmissionIn, response: Response, user: Writer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out, created = await fm.submit(conn, body, user.username)
    except fm.FormError as exc:
        raise _http(exc) from exc
    response.status_code = 201 if created else 200
    return out


@router.get("/api/v1/work-orders/{order_id}/forms")
async def work_order_forms(order_id: Annotated[int, Path(ge=1)], _: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await fm.order_submissions(conn, order_id)
