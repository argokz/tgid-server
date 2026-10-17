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
from database import card_edit as ce
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
