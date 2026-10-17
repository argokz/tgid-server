"""Окно свойств: правка карточки объекта сети как в десктопе (``database/card_edit.py``).

- ``GET  /api/v1/card-edit/{kind}/{table}/{id}`` — карточка (как ``/line|/node``) со сведениями для
  правки полей, версиями строк и правилами видимости/доступности;
- ``GET  /api/v1/card-edit/options`` — варианты выпадающего списка поля, как в десктопе;
- ``PUT  /api/v1/card-edit`` — сохранить изменения (одна транзакция, версии → 409, audit_log).
Чтение — viewer; запись — editor с правом ``network`` и MUTATIONS_ENABLED.
"""
from __future__ import annotations

import json
from typing import Annotated, Any, Literal, Optional

from asyncpg.exceptions import UndefinedColumnError
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, require_mutations_enabled, require_roles
from database import card_batch as cb
from database import card_edit as ce
from database import card_template as ct
from database import typed_edit as te
from database.connect import acquire_conn
from database.db import create_select_line, create_select_node
from database.sql_ident import UnknownIdentifierError
from routers.group_setters import _audit_writer

logger = get_logger(__name__)

router = APIRouter(tags=["card-edit"])
Editor = Annotated[AuthUser, Depends(require_roles("editor", cap="network"))]
PREFIX = "/api/v1/card-edit"


class Change(BaseModel):
    table: str = Field(..., max_length=64)
    id: int = Field(..., ge=1)
    field: str = Field(..., max_length=64)
    value: Any = None


class SaveBody(BaseModel):
    changes: list[Change] = Field(default_factory=list, max_length=2000)
    versions: dict[str, str] = Field(default_factory=dict, description='"table:id" → версия из GET')
    dry_run: bool = False


class BatchBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=cb.MAX_LINES, description="linesobj.id выбранных участков")
    changes: list[Change] = Field(default_factory=list, max_length=2000,
                                  description="id — колонка карточки выбора: 1 подача/одиночные, 2 обратка")
    expected_changes: Optional[int] = Field(None, ge=0, description="Число строк из предпросмотра")


class TemplateBody(BaseModel):
    kind: Literal["line"] = "line"
    name: str = Field(..., min_length=1, max_length=ct.NAME_MAX)
    values: dict[str, dict[str, Any]] = Field(..., description="{таблица: {поле: значение}}")
    shared: bool = False


class TemplatePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=ct.NAME_MAX)
    values: Optional[dict[str, dict[str, Any]]] = None
    shared: Optional[bool] = None


class TemplateApplyBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=cb.MAX_LINES, description="linesobj.id")
    expected_changes: Optional[int] = Field(None, ge=0)


class BatchCardBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=cb.MAX_LINES)


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, te.TypedEditError):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, UnknownIdentifierError):
        return HTTPException(status_code=404, detail={"code": "unknown", "message": f"Нет {exc.kind} {exc.name}"})
    if isinstance(exc, UndefinedColumnError):
        return HTTPException(status_code=400, detail={"code": "wrong_kind",
                                                      "message": "Таблица не относится к этому виду объектов"})
    raise exc


@router.get(PREFIX + "/options")
async def card_edit_options(
    table: str = Query(..., max_length=64),
    field: str = Query(..., max_length=64),
    fileid: Optional[int] = Query(None, ge=1, description="Фрагмент объекта ($fragments$, фильтр по fileID)"),
    row_id: Optional[int] = Query(None, ge=1, description="id строки ($id$ в SQL справочника)"),
    q: str = Query("", max_length=100),
    limit: int = Query(ce.OPTIONS_LIMIT, ge=1, le=ce.OPTIONS_LIMIT),
):
    """Варианты выпадающего списка поля — как в карточке десктопа."""
    async with acquire_conn() as conn:
        try:
            return await ce.field_options(conn, table, field, fileid=fileid, row_id=row_id, q=q, limit=limit)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get(PREFIX + "/helper")
async def card_edit_helper(
    table: str = Query(..., max_length=64),
    field: str = Query(..., max_length=64),
    standard_id: Optional[int] = Query(None, description="standardID участка (выбор по сортаменту)"),
):
    """Окно-помощник поля, как функция десктопа: сортамент труб, справочная таблица, местные сопротивления."""
    async with acquire_conn() as conn:
        try:
            return await ce.field_helper(conn, table, field, standard_id=standard_id)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get(PREFIX + "/after")
async def card_edit_after(
    table: str = Query(..., max_length=64),
    field: str = Query(..., max_length=64),
    value: Optional[str] = Query(None, max_length=64),
):
    """Зависимые поля после выбора значения (магистраль / участок МС / участок РС — как ms_rs десктопа)."""
    async with acquire_conn() as conn:
        try:
            return await ce.after_change(conn, table, field, value)
        except ValueError:
            raise HTTPException(status_code=422, detail={"code": "bad_value", "message": "Ожидается код"})


@router.post(PREFIX + "/batch/card")
async def card_edit_batch_card(body: BatchCardBody):
    """Карточка нескольких участков: поля как у одного, значения сведены по колонкам («разные»)."""
    async with acquire_conn() as conn:
        try:
            return await cb.batch_card(conn, body.ids)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/batch/preview")
async def card_edit_batch_preview(body: BatchBody, user: Editor):
    """Предпросмотр правки нескольких участков: сколько строк изменится, какие значения были."""
    if not body.changes:
        raise HTTPException(status_code=422, detail={"code": "no_changes", "message": "Нет изменений"})
    async with acquire_conn() as conn:
        try:
            return await cb.preview(conn, body.ids, [c.model_dump() for c in body.changes])
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/batch/apply")
async def card_edit_batch_apply(body: BatchBody, user: Editor):
    """Применить правку нескольких участков одной группой (отмена — /api/v1/group-setters/undo)."""
    if not body.changes:
        raise HTTPException(status_code=422, detail={"code": "no_changes", "message": "Нет изменений"})
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await cb.apply(conn, body.ids, [c.model_dump() for c in body.changes],
                                        audit_row=_audit_writer(user), expected_changes=body.expected_changes)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    if result.get("changed"):
        try:
            from database.outage_simulation import invalidate_outage_cache

            invalidate_outage_cache()
        except Exception:  # noqa: BLE001 — кэш не критичен
            pass
    return result


@router.get(PREFIX + "/neighbor/line/{line_id}")
async def card_edit_neighbor(line_id: int = Path(..., ge=1)):
    """«Как у соседнего»: значения конструктива смежного участка по колонкам карточки."""
    async with acquire_conn() as conn:
        try:
            return await ct.neighbor_values(conn, line_id)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


# --- шаблоны -----------------------------------------------------------------------------------

TPL = "/api/v1/card-templates"


@router.get(TPL)
async def card_templates_list(user: Editor, kind: Literal["line"] = Query("line")):
    """Шаблоны вида объектов: свои и общие."""
    async with acquire_conn() as conn:
        return {"items": await ct.list_templates(conn, kind, user.username)}


@router.post(TPL)
async def card_template_create(body: TemplateBody, user: Editor):
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            return await ct.create_template(conn, kind=body.kind, name=body.name, values=body.values,
                                            shared=body.shared, user=user.username)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.put(TPL + "/{template_id}")
async def card_template_update(body: TemplatePatch, user: Editor, template_id: int = Path(..., ge=1)):
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            return await ct.update_template(conn, template_id, name=body.name, values=body.values,
                                            shared=body.shared, user=user.username,
                                            is_admin=user.has_role("admin"))
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.delete(TPL + "/{template_id}")
async def card_template_delete(user: Editor, template_id: int = Path(..., ge=1)):
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            await ct.delete_template(conn, template_id, user=user.username, is_admin=user.has_role("admin"))
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"deleted": template_id}


@router.post(TPL + "/{template_id}/preview")
async def card_template_preview(body: TemplateApplyBody, user: Editor, template_id: int = Path(..., ge=1)):
    """Предпросмотр шаблона на участках: как правка нескольких объектов."""
    async with acquire_conn() as conn:
        try:
            tpl = await ct.get_template(conn, template_id, user.username)
            changes = await ct.template_changes(conn, tpl, body.ids)
            return await cb.preview(conn, body.ids, changes)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(TPL + "/{template_id}/apply")
async def card_template_apply(body: TemplateApplyBody, user: Editor, template_id: int = Path(..., ge=1)):
    """Применить шаблон к участкам (новым или выбранным): одна группа, отмена — group-setters/undo."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                tpl = await ct.get_template(conn, template_id, user.username)
                changes = await ct.template_changes(conn, tpl, body.ids)
                result = await cb.apply(conn, body.ids, changes, audit_row=_audit_writer(user),
                                        expected_changes=body.expected_changes)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {**result, "template": {"id": tpl["id"], "name": tpl["name"]}}


@router.get(PREFIX + "/{kind}/{table}/{obj_id}")
async def card_edit_get(kind: Literal["line", "node"], table: str = Path(..., max_length=64),
                        obj_id: int = Path(..., ge=1)):
    """Карточка объекта для правки: поля как в просмотре + edit/versions/rules."""
    try:
        build = create_select_line if kind == "line" else create_select_node
        card = json.loads(await build(table, obj_id, include_hidden=True))
        async with acquire_conn() as conn:
            card = await ce.annotate_card(conn, kind, card)
            card["fileid"] = await ce.card_fileid(conn, kind, obj_id)
    except (te.TypedEditError, UnknownIdentifierError, UndefinedColumnError) as exc:
        raise _http(exc)
    card.update({"kind": kind, "table": table, "id": obj_id})
    return card


@router.put(PREFIX)
async def card_edit_save(body: SaveBody, user: Editor):
    """Сохранить изменения карточки: только правимые поля, типы по схеме, версия → 409, audit_log."""
    if not body.changes:
        raise HTTPException(status_code=422, detail={"code": "no_changes", "message": "Нет изменений"})
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await ce.save_card(conn, [c.model_dump() for c in body.changes], body.versions,
                                            audit_row=_audit_writer(user), dry_run=body.dry_run)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    if not body.dry_run and any(r.get("changed") for r in result["rows"]):
        try:
            from database.outage_simulation import invalidate_outage_cache

            invalidate_outage_cache()
        except Exception:  # noqa: BLE001 — кэш не критичен
            pass
    return result
