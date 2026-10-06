"""Правка оборудования сети (этап 9): задвижки, регулирующая арматура, насосы, регуляторы,
перемычки, диафрагмы, элеваторы и т.п.

Реестры (``routers/equipment.py``) — чтение; здесь — типизированная правка атрибутов строки
(``database/typed_edit.py``): поля карточки десктопа ``tab/*.txt`` (+ поля, которые правят
реестры веба, — ``EXTRA_FIELDS``), тип из схемы БД, версия ``xmin`` → 409, audit_log со
старыми и новыми значениями. Запись — editor+ и MUTATIONS_ENABLED.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, require_mutations_enabled, require_roles
from database import typed_edit as te
from database.connect import acquire_conn
from database.sql_ident import UnknownIdentifierError
from routers.group_setters import _audit_writer

logger = get_logger(__name__)

router = APIRouter(tags=["equipment-edit"])

Editor = Annotated[AuthUser, Depends(require_roles("editor", cap="network"))]
PREFIX = "/api/v1/equipment-edit"

# Таблица оборудования → подпись. Ключ строки — id таблицы (как в реестрах).
EQUIPMENT_TABLES: dict[str, str] = {
    "dampers": "Задвижки",
    "regularmatures": "Регулирующая арматура",
    "reversevalves": "Обратные клапаны",
    "pumps": "Насосы",
    "pumpstations": "Насосные станции",
    "pressregulators": "Регуляторы давления",
    "consumptregulators": "Регуляторы расхода",
    "pressdropregulators": "Регуляторы перепада",
    "bypass": "Перемычки",
    "diaphragms": "Диафрагмы",
    "elevators": "Элеваторы",
    "heatexchangers": "Теплообменники",
    "tankbatteries": "Баки-аккумуляторы",
}

# Поля сверх карточки десктопа, которые правят реестры веба (у диафрагм карточки tab/*.txt нет).
EXTRA_FIELDS: dict[str, tuple[str, ...]] = {
    "regularmatures": ("q",),  # заданный расход (реестр арматуры)
    "pressdropregulators": ("regvalvehydrores", "consthroughregvalve", "thrustdropmean"),
    "bypass": ("standardtubelink",),
    "diaphragms": ("throtdiaphloc", "stateid", "diameterinternal", "consinstdiaphcount", "entrymark"),
}


class EditBody(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = Field(None, description="версия из GET (xmin); расхождение → 409")
    dry_run: bool = False


def _table(table: str) -> str:
    key = table.lower()
    if key not in EQUIPMENT_TABLES:
        raise HTTPException(status_code=404, detail={"code": "not_equipment",
                                                     "message": f"Таблица {table} не относится к оборудованию"})
    return key


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, te.TypedEditError):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, UnknownIdentifierError):
        logger.error("equipment edit schema mismatch: %s", exc)
        return HTTPException(status_code=404, detail={"code": "no_table", "message": f"Нет таблицы {exc.name}"})
    raise exc


async def _fields(conn, table: str) -> list[te.FieldSpec]:
    return await te.editable_fields(conn, table, extra=EXTRA_FIELDS.get(table, ()))


@router.get(PREFIX)
async def equipment_edit_tables():
    return {"tables": [{"table": t, "label": label} for t, label in EQUIPMENT_TABLES.items()]}


@router.get(PREFIX + "/{table}/fields")
async def equipment_edit_fields(table: str):
    key = _table(table)
    async with acquire_conn() as conn:
        try:
            return {"table": key, "label": EQUIPMENT_TABLES[key],
                    "fields": [f.describe() for f in await _fields(conn, key)]}
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.get(PREFIX + "/{table}/{row_id}")
async def equipment_edit_get(table: str, row_id: int = Path(..., ge=1)):
    """Поля карточки, текущие значения и версия строки (для формы правки)."""
    key = _table(table)
    async with acquire_conn() as conn:
        try:
            fields = await _fields(conn, key)
            record = await te.read_record(conn, key, "id", row_id, fields)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"table": key, "label": EQUIPMENT_TABLES[key], "id": row_id,
            "fields": [f.describe() for f in fields], **record}


@router.put(PREFIX + "/{table}/{row_id}")
async def equipment_edit_update(table: str, body: EditBody, user: Editor, row_id: int = Path(..., ge=1)):
    """Правка атрибутов: только поля allow-list, типы по схеме, версия → 409, audit_log."""
    key = _table(table)
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            fields = await _fields(conn, key)
            async with conn.transaction():
                result = await te.update_record(conn, key, "id", row_id, fields, body.fields,
                                                expected_version=body.version, audit_row=_audit_writer(user),
                                                dry_run=body.dry_run)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    if result["changed"] and not body.dry_run:
        try:
            from database.outage_simulation import invalidate_outage_cache

            invalidate_outage_cache()
        except Exception:  # noqa: BLE001 — кэш не критичен
            pass
    return result
