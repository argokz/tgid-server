"""Окно свойств: правка карточки объекта сети как в десктопе (``database/card_edit.py``).

- ``GET  /api/v1/card-edit/{kind}/{table}/{id}`` — карточка (как ``/line|/node``) со сведениями для
  правки полей, версиями строк и правилами видимости/доступности;
- ``GET  /api/v1/card-edit/options`` — варианты выпадающего списка поля, как в десктопе;
- ``PUT  /api/v1/card-edit`` — сохранить изменения (одна транзакция, версии → 409, audit_log);
- ``GET  /api/v1/card-edit/equipment-at/{node_id}`` — оборудование узла (примыкающее и во внутренней схеме).
Чтение — viewer; запись — право «Свойства» вида объекта (permissions.py; охват own — только свои
объекты) и MUTATIONS_ENABLED.
"""
from __future__ import annotations

import json
import uuid
from typing import Annotated, Any, Literal, Optional

from asyncpg.exceptions import UndefinedColumnError
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, get_current_user, permission_http_error, require_mutations_enabled
from database import card_batch as cb
from database import card_edit as ce
from database import card_template as ct
from database import typed_edit as te
from database.connect import acquire_conn
from database.db import create_select_line, create_select_node
from database.sql_ident import UnknownIdentifierError
from database.sql_ident import resolve_table
from database.topology_journal import OperationJournal
from permissions import PermissionDenied, ensure_can, ensure_targets, table_kind
from routers.group_setters import _audit_writer

logger = get_logger(__name__)

router = APIRouter(tags=["card-edit"])
# Право проверяется по виду объектов правки (_guard_*): у режимщика — потребители и оборудование и т. п.
Editor = Annotated[AuthUser, Depends(get_current_user)]
PREFIX = "/api/v1/card-edit"

_TABLE_TITLES = {"heatpipesections": "паспорт участка", "linesobj": "участок", "nodes": "узел",
                 "realconsumers": "потребитель", "generalizedconsumers": "обобщённый потребитель",
                 "heatsources": "источник", "pumpstations": "насосная станция",
                 "setpressnodes": "заданный напор", "refillnodes": "подпитка"}


def card_edit_summary(rows: list[dict]) -> dict:
    """Запись журнала для правки карточки: что изменено (для «Истории» и подписи «Отменить»)."""
    from utils.russian_names import russian_names_manager

    def label(table: str, field: str) -> str:
        # подпись поля как в карточке (rus_names десктопа); нет — имя колонки
        try:
            name = russian_names_manager.get_russian_name(f"{table}|{field}")[0]
        except Exception:  # noqa: BLE001
            name = ""
        return name if name and name.lower() != field.lower() else field

    fields = []
    for r in rows:
        for field, ch in (r.get("changed") or {}).items():
            fields.append({"table": r.get("table"), "id": r.get("key"), "field": field,
                           "label": label(str(r.get("table") or ""), field),
                           "old": ch.get("old"), "new": ch.get("new")})
    first = rows[0]
    table = str(first.get("table") or "").lower()
    what = f"{_TABLE_TITLES.get(table, table)} {first.get('key')}"
    shown = ", ".join(f"{f['label']}: {f['old']} → {f['new']}" for f in fields[:3])
    more = f" и ещё {len(fields) - 3}" if len(fields) > 3 else ""
    return {"text": f"{what} — {shown}{more}", "fields": fields[:50], "table": table, "id": first.get("key")}


# Вид карточки → вид объекта в правах (permissions.KINDS)
CARD_PERM_KIND: dict[str, str] = {
    "line": "line", "node": "node", "consumer": "consumer", "genconsumer": "consumer",
    "source": "source", "pumpstation": "source", "setpress": "regime", "refill": "regime",
    **{k: "equipment" for k in ce.EQUIPMENT_KINDS},
}


async def _guard_rows(user: AuthUser, rows: dict[str, set[int]]) -> None:
    """Правка строк карточек {таблица: {id}}: право «Свойства» вида каждой таблицы; own — только свои
    (база нужна только для охвата own)."""
    try:
        by_kind: dict[str, dict[str, list[int]]] = {}
        for table, ids in rows.items():
            # таблица вне матрицы прав (справочная часть карточки) — как свойства узла
            kind = table_kind(table) or "node"
            by_kind.setdefault(kind, {})[table] = sorted(ids)
        own = [k for k in by_kind if ensure_can(user.perms, k, "edit") == "own"]
        if own:
            async with acquire_conn() as conn:
                for kind in own:
                    await ensure_targets(conn, user.perms, user.username, kind, "edit", by_kind[kind])
    except PermissionDenied as exc:
        raise permission_http_error(exc)


async def _guard_objects(user: AuthUser, card_kind: str, ids: list[int]) -> None:
    """Групповая правка / шаблон: ids — linesobj.id (участки, оборудование) или nodes.id."""
    kind = CARD_PERM_KIND.get(card_kind, "node")
    table = "linesobj" if card_kind in ce.LINE_CARD_TABLE else "nodes"
    try:
        if ensure_can(user.perms, kind, "edit") == "own":
            async with acquire_conn() as conn:
                await ensure_targets(conn, user.perms, user.username, kind, "edit", {table: ids})
    except PermissionDenied as exc:
        raise permission_http_error(exc)


def _guard_any_edit(user: AuthUser) -> None:
    """Шаблоны и групповая правка — тем, кто может править свойства хоть каких-то объектов."""
    if not any(user.perms.can(k, "edit") for k in CARD_PERM_KIND.values()):
        raise permission_http_error(PermissionDenied("Нет права на правку свойств объектов"))


def _guard_kind(user: AuthUser, card_kind: str, *, shared: bool = False) -> None:
    """Шаблоны вида: свои — с правом «Свойства» вида; общие — ещё и «Справочники и шаблоны»."""
    try:
        ensure_can(user.perms, CARD_PERM_KIND.get(card_kind, "node"), "edit")
        if shared and not user.perms.has("refs"):
            raise PermissionDenied("Общие шаблоны — с правом «Справочники и шаблоны карточек»")
    except PermissionDenied as exc:
        raise permission_http_error(exc)


class Change(BaseModel):
    table: str = Field(..., max_length=64)
    id: int = Field(..., ge=1)
    field: str = Field(..., max_length=64)
    value: Any = None


class SaveBody(BaseModel):
    changes: list[Change] = Field(default_factory=list, max_length=2000)
    versions: dict[str, str] = Field(default_factory=dict, description='"table:id" → версия из GET')
    dry_run: bool = False


Kind = Literal["line", "node", "consumer", "genconsumer", "source", "pumpstation",
               # дополнения узла: заданный напор, подпитка
               "setpress", "refill",
               # оборудование — card_edit.EQUIPMENT_KINDS
               "damper", "regarmature", "reversevalve", "pump", "pressregulator", "consregulator",
               "pressdropregulator", "bypass", "elevator", "heatexchanger"]


class BatchBody(BaseModel):
    kind: Kind = "line"
    ids: list[int] = Field(..., min_length=1, max_length=cb.MAX_LINES,
                           description="linesobj.id выбранных участков (nodes.id — узлов)")
    changes: list[Change] = Field(default_factory=list, max_length=2000,
                                  description="id — колонка карточки выбора: 1 подача/одиночные, 2 обратка")
    expected_changes: Optional[int] = Field(None, ge=0, description="Число строк из предпросмотра")


class TemplateBody(BaseModel):
    kind: Kind = "line"
    name: str = Field(..., min_length=1, max_length=ct.NAME_MAX)
    values: dict[str, dict[str, Any]] = Field(..., description="{таблица: {поле: значение}}")
    shared: bool = False


class TemplatePatch(BaseModel):
    name: Optional[str] = Field(None, max_length=ct.NAME_MAX)
    values: Optional[dict[str, dict[str, Any]]] = None
    shared: Optional[bool] = None


class TemplateApplyBody(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=cb.MAX_LINES, description="linesobj.id / nodes.id")
    expected_changes: Optional[int] = Field(None, ge=0)


class BatchCardBody(BaseModel):
    kind: Kind = "line"
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


@router.get(PREFIX + "/equipment-at/{node_id}")
async def card_edit_node_equipment(node_id: int = Path(..., ge=1)):
    """Оборудование узла: задвижки, регуляторы, насосы… — примыкающие к узлу и во внутренней схеме."""
    async with acquire_conn() as conn:
        try:
            return await ce.node_equipment(conn, node_id)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/batch/card")
async def card_edit_batch_card(body: BatchCardBody):
    """Карточка нескольких участков: поля как у одного, значения сведены по колонкам («разные»)."""
    async with acquire_conn() as conn:
        try:
            return await cb.batch_card(conn, body.ids, body.kind)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/batch/preview")
async def card_edit_batch_preview(body: BatchBody, user: Editor):
    """Предпросмотр правки нескольких участков: сколько строк изменится, какие значения были."""
    if not body.changes:
        raise HTTPException(status_code=422, detail={"code": "no_changes", "message": "Нет изменений"})
    await _guard_objects(user, body.kind, body.ids)
    async with acquire_conn() as conn:
        try:
            return await cb.preview(conn, body.ids, [c.model_dump() for c in body.changes], body.kind)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(PREFIX + "/batch/apply")
async def card_edit_batch_apply(body: BatchBody, user: Editor):
    """Применить правку нескольких участков одной группой (отмена — /api/v1/group-setters/undo)."""
    if not body.changes:
        raise HTTPException(status_code=422, detail={"code": "no_changes", "message": "Нет изменений"})
    require_mutations_enabled()
    await _guard_objects(user, body.kind, body.ids)
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                result = await cb.apply(conn, body.ids, [c.model_dump() for c in body.changes],
                                        audit_row=_audit_writer(user), expected_changes=body.expected_changes,
                                        kind=body.kind)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    if result.get("changed"):
        try:
            from database.outage_simulation import invalidate_outage_cache

            invalidate_outage_cache()
        except Exception:  # noqa: BLE001 — кэш не критичен
            pass
    return result


@router.get(PREFIX + "/neighbor/{kind}/{obj_id}")
async def card_edit_neighbor(kind: Kind, obj_id: int = Path(..., ge=1)):
    """«Как у соседнего»: значения конструктива смежного участка по колонкам карточки (у узла —
    смежного или ближайшего узла)."""
    async with acquire_conn() as conn:
        try:
            if kind == "node":
                return await ct.neighbor_node_values(conn, obj_id)
            if kind == "line":
                return await ct.neighbor_values(conn, obj_id)
            if kind in ce.EQUIPMENT_KINDS:
                return await ct.neighbor_equipment_values(conn, kind, obj_id)
            return await ct.neighbor_owner_values(conn, kind, obj_id)
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


# --- шаблоны -----------------------------------------------------------------------------------

TPL = "/api/v1/card-templates"


@router.get(TPL)
async def card_templates_list(user: Editor, kind: Kind = Query("line")):
    """Шаблоны вида объектов: свои и общие."""
    _guard_kind(user, kind)
    async with acquire_conn() as conn:
        return {"items": await ct.list_templates(conn, kind, user.username)}


@router.post(TPL)
async def card_template_create(body: TemplateBody, user: Editor):
    require_mutations_enabled()
    _guard_kind(user, body.kind, shared=body.shared)
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
            tpl = await ct.get_template(conn, template_id, user.username)
            _guard_kind(user, tpl["kind"], shared=bool(body.shared if body.shared is not None else tpl.get("shared")))
            return await ct.update_template(conn, template_id, name=body.name, values=body.values,
                                            shared=body.shared, user=user.username,
                                            is_admin=user.perms.has("refs"))
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.delete(TPL + "/{template_id}")
async def card_template_delete(user: Editor, template_id: int = Path(..., ge=1)):
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            tpl = await ct.get_template(conn, template_id, user.username)
            _guard_kind(user, tpl["kind"])
            await ct.delete_template(conn, template_id, user=user.username, is_admin=user.perms.has("refs"))
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {"deleted": template_id}


@router.post(TPL + "/{template_id}/preview")
async def card_template_preview(body: TemplateApplyBody, user: Editor, template_id: int = Path(..., ge=1)):
    """Предпросмотр шаблона на участках: как правка нескольких объектов."""
    _guard_any_edit(user)
    async with acquire_conn() as conn:
        try:
            tpl = await ct.get_template(conn, template_id, user.username)
            await _guard_objects(user, tpl["kind"], body.ids)
            changes = await ct.template_changes(conn, tpl, body.ids)
            return await cb.preview(conn, body.ids, changes, tpl["kind"])
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)


@router.post(TPL + "/{template_id}/apply")
async def card_template_apply(body: TemplateApplyBody, user: Editor, template_id: int = Path(..., ge=1)):
    """Применить шаблон к участкам (новым или выбранным): одна группа, отмена — group-setters/undo."""
    _guard_any_edit(user)
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                tpl = await ct.get_template(conn, template_id, user.username)
                await _guard_objects(user, tpl["kind"], body.ids)
                changes = await ct.template_changes(conn, tpl, body.ids)
                result = await cb.apply(conn, body.ids, changes, audit_row=_audit_writer(user),
                                        expected_changes=body.expected_changes, kind=tpl["kind"])
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    return {**result, "template": {"id": tpl["id"], "name": tpl["name"]}}


@router.get(PREFIX + "/{kind}/{table}/{obj_id}")
async def card_edit_get(kind: Kind, table: str = Path(..., max_length=64),
                        obj_id: int = Path(..., ge=1)):
    """Карточка объекта для правки: поля как в просмотре + edit/versions/rules."""
    own = ce.NODE_CARD_TABLE.get(kind) or (ce.EQUIPMENT_KINDS.get(kind))
    if own and table.lower() != own.lower():
        raise HTTPException(status_code=422, detail={"code": "wrong_kind",
                                                     "message": "Таблица не относится к этому виду объектов"})
    try:
        build = create_select_line if kind in ce.LINE_CARD_TABLE else create_select_node
        card = json.loads(await build(table, obj_id, include_hidden=True))
        async with acquire_conn() as conn:
            card = await ce.annotate_card(conn, kind, card)
            card["fileid"] = await ce.card_fileid(conn, kind, obj_id)
            # «Создан: кто, когда» — объекты, созданные в вебе (право «только свои»)
            from database.authorship import owner_of

            card["created"] = await owner_of(conn, "linesobj" if kind in ce.LINE_CARD_TABLE else "nodes", obj_id)
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
    rows: dict[str, set[int]] = {}
    for c in body.changes:
        rows.setdefault(c.table.lower(), set()).add(c.id)
    await _guard_rows(user, rows)
    async with acquire_conn() as conn:
        try:
            async with conn.transaction():
                # общая история отмены с правкой сети: образы строк до правки (Ctrl+Z, «История»)
                journal = await OperationJournal.open(conn, dry_run=body.dry_run)
                if journal.enabled:
                    for table, ids in rows.items():
                        await journal.capture_ids(conn, await resolve_table(conn, table), ids)
                result = await ce.save_card(conn, [c.model_dump() for c in body.changes], body.versions,
                                            audit_row=_audit_writer(user), dry_run=body.dry_run)
                changed_rows = [r for r in result["rows"] if r.get("changed")]
                if journal.enabled and changed_rows:
                    result["operation_id"] = await journal.commit(
                        conn, actor=user.username, operation="CARD_EDIT",
                        group_id=str(changed_rows[0].get("change_group_id") or uuid.uuid4()),
                        summary=card_edit_summary(changed_rows),
                    )
        except (te.TypedEditError, UnknownIdentifierError) as exc:
            raise _http(exc)
    if not body.dry_run and any(r.get("changed") for r in result["rows"]):
        try:
            from database.outage_simulation import invalidate_outage_cache

            invalidate_outage_cache()
        except Exception:  # noqa: BLE001 — кэш не критичен
            pass
    return result
