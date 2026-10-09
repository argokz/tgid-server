"""Инструменты ПТС: участки МС/РС и привязка к ним труб (этап 9, ``database/pts_sites.py``).

Чтение — любой пользователь; запись — editor+ и MUTATIONS_ENABLED, одна транзакция + audit_log.
Назначение/снятие привязки — групповые установщики ``pts_site_*`` (dry-run → apply с
``expected_changes``; отмена — ``POST /api/v1/group-setters/undo``).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app_logging import get_logger
from auth import AuthUser, require_mutations_enabled, require_roles
from database import group_setters as gs
from database import pts_sites as pts
from database import typed_edit as te
from database.connect import acquire_conn
from database.sql_ident import UnknownIdentifierError, quote_ident
from routers.group_setters import _audit_writer

logger = get_logger(__name__)

router = APIRouter(tags=["pts"])

Editor = Annotated[AuthUser, Depends(require_roles("editor", cap="pts"))]
PREFIX = "/api/v1/pts"


class SiteBody(BaseModel):
    fields: dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = Field(None, description="версия записи из GET (xmin); расхождение → 409")


class ChainBody(BaseModel):
    node_ids: list[int] = Field(..., min_length=2, max_length=pts.MAX_CHAIN_NODES)


class PipesBody(BaseModel):
    action: Literal["assign", "unassign"] = "assign"
    line_ids: Optional[list[int]] = Field(None, description="linesobj.id (выбор на карте)")
    node_ids: Optional[list[int]] = Field(None, description="цепочка узлов: трубы кратчайших путей между ними")
    all_pipes: bool = Field(False, description="unassign: снять привязку со всех труб участка")
    dry_run: bool = True
    expected_changes: Optional[int] = None


def _http(exc: Exception) -> HTTPException:
    if isinstance(exc, (pts.PtsError, te.TypedEditError, gs.GroupSetterError)):
        return HTTPException(status_code=exc.status, detail=exc.detail)
    if isinstance(exc, UnknownIdentifierError):
        logger.error("pts schema mismatch: %s", exc)
        return HTTPException(status_code=500, detail=f"Схема БД не совпадает с описанием: {exc.name}")
    raise exc


_ERRORS = (pts.PtsError, te.TypedEditError, gs.GroupSetterError, UnknownIdentifierError)


def _invalidate_outage_cache() -> None:
    try:
        from database.outage_simulation import invalidate_outage_cache

        invalidate_outage_cache()
    except Exception:  # noqa: BLE001 — кэш не критичен
        pass


@router.get(PREFIX + "/sites")
async def pts_sites_list(kind: str = Query("ms", description="ms | rs")):
    """Участки (дерево дока ПТС: начальник → участок) с числом и длиной привязанных труб."""
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            items = await pts.list_sites(conn, k)
        except _ERRORS as exc:
            raise _http(exc)
    return {"kind": k.key, "title": k.title, "items": items,
            "pipes_total": sum(i["pipes"] for i in items)}


@router.get(PREFIX + "/sites/{kind}/fields")
async def pts_site_fields(kind: str):
    """Поля карточки участка (tab/ps/uchastok_*.txt): тип, подпись, справочник."""
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            return {"kind": k.key, "fields": [f.describe() for f in await pts.site_fields(conn, k)]}
        except _ERRORS as exc:
            raise _http(exc)


@router.get(PREFIX + "/sites/{kind}/{site_id}")
async def pts_site_get(kind: str, site_id: int):
    async with acquire_conn() as conn:
        try:
            return await pts.get_site(conn, pts.get_kind(kind), site_id)
        except _ERRORS as exc:
            raise _http(exc)


@router.get(PREFIX + "/sites/{kind}/{site_id}/pipes")
async def pts_site_pipes(kind: str, site_id: int):
    """Трубы участка: список и GeoJSON (EPSG:4326) с bbox — «Перейти к участку»."""
    async with acquire_conn() as conn:
        try:
            return await pts.site_pipes(conn, pts.get_kind(kind), site_id)
        except _ERRORS as exc:
            raise _http(exc)


@router.get(PREFIX + "/highlight")
async def pts_highlight(kind: str = Query(..., description="nach | ms | rs"), id: int = Query(..., ge=1)):
    """Подсветка на карте (viewparams nach/ms/rs слоя участков): число труб, охват EPSG:4326, фрагменты."""
    async with acquire_conn() as conn:
        try:
            return await pts.highlight_extent(conn, kind, id)
        except _ERRORS as exc:
            raise _http(exc)


@router.post(PREFIX + "/sites/{kind}")
async def pts_site_create(kind: str, body: SiteBody, user: Editor):
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            fields = await pts.site_fields(conn, k)
            async with conn.transaction():
                new_id = await te.insert_record(conn, k.table, fields, body.fields, audit_row=_audit_writer(user))
            return await pts.get_site(conn, k, new_id)
        except _ERRORS as exc:
            raise _http(exc)


@router.put(PREFIX + "/sites/{kind}/{site_id}")
async def pts_site_update(kind: str, site_id: int, body: SiteBody, user: Editor):
    """Правка характеристик участка (типизированный allow-list, версия → 409)."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            fields = await pts.site_fields(conn, k)
            async with conn.transaction():
                result = await te.update_record(conn, k.table, "id", site_id, fields, body.fields,
                                                expected_version=body.version, audit_row=_audit_writer(user))
            return {**result, "site": await pts.get_site(conn, k, site_id)}
        except _ERRORS as exc:
            raise _http(exc)


@router.delete(PREFIX + "/sites/{kind}/{site_id}")
async def pts_site_delete(kind: str, site_id: int, user: Editor,
                          unassign_pipes: bool = Query(False, description="снять привязку труб и удалить")):
    """Удаление участка. Есть привязанные трубы — 409, если не передан unassign_pipes=true."""
    require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            fields = await pts.site_fields(conn, k)
            async with conn.transaction():
                await conn.fetchval(f"SELECT id FROM {quote_ident(k.table)} WHERE id = $1 FOR UPDATE", site_id)
                line_ids = await pts.site_line_ids(conn, k, site_id)
                cleared = None
                if line_ids:
                    if not unassign_pipes:
                        raise pts.PtsError(409, {"code": "has_pipes", "pipes": len(line_ids),
                                                 "message": f"К участку привязано труб: {len(line_ids)}. "
                                                            "Снимите привязку или удалите с unassign_pipes=true"})
                    cleared = await gs.apply(conn, gs.get_spec(pts.CLEAR_SETTER), None,
                                             {"mode": "ids", "ids": line_ids}, actor=user.username,
                                             audit_row=_audit_writer(user))
                await te.delete_record(conn, k.table, site_id, audit_row=_audit_writer(user), fields=fields)
        except _ERRORS as exc:
            raise _http(exc)
    if cleared:
        _invalidate_outage_cache()
    return {"deleted": True, "kind": k.key, "id": site_id,
            "unassigned": cleared["changed"] if cleared else 0,
            "change_group_id": cleared["change_group_id"] if cleared else None}


@router.post(PREFIX + "/chain")
async def pts_chain(body: ChainBody):
    """Цепочка узлов → трубы кратчайших путей между соседними узлами (для предпросмотра на карте)."""
    async with acquire_conn() as conn:
        try:
            return await pts.resolve_chain(conn, body.node_ids)
        except _ERRORS as exc:
            raise _http(exc)


@router.post(PREFIX + "/sites/{kind}/{site_id}/pipes")
async def pts_site_pipes_change(kind: str, site_id: int, body: PipesBody, user: Editor):
    """Назначить трубам участок / снять привязку (dry_run=true — предпросмотр без записи).

    Трубы: ``line_ids`` (выбор на карте) или ``node_ids`` (цепочка узлов); для снятия —
    ещё ``all_pipes``. Снимается привязка только к этому участку.
    """
    if not body.dry_run:
        require_mutations_enabled()
    async with acquire_conn() as conn:
        try:
            k = pts.get_kind(kind)
            if not await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {quote_ident(k.table)} WHERE id = $1)",
                                       site_id):
                raise pts.PtsError(404, {"code": "not_found", "message": f"{k.title} {site_id} не найден"})
            chain = None
            if body.node_ids:
                chain = await pts.resolve_chain(conn, body.node_ids)
                line_ids: Optional[list[int]] = chain["line_ids"]
            elif body.line_ids:
                line_ids = gs.normalize_ids(body.line_ids, field_name="line_ids")
            elif body.action == "unassign" and body.all_pipes:
                line_ids = None
            else:
                raise pts.PtsError(422, {"code": "no_pipes", "message": "Выберите трубы на карте или цепочку узлов"})
            if body.action == "assign":
                spec, value = gs.get_spec(k.setter), site_id
                ids = line_ids or []
            else:
                spec, value = gs.get_spec(pts.CLEAR_SETTER), None
                ids = await pts.site_line_ids(conn, k, site_id, line_ids)
            if not ids:
                raise pts.PtsError(422, {"code": "no_pipes",
                                         "message": "Среди выбранных нет труб" if body.action == "assign"
                                         else "Выбранные трубы не привязаны к этому участку"})
            selection = {"mode": "ids", "ids": ids}
            if body.dry_run:
                result = await gs.preview(conn, spec, value, selection)
                result["dry_run"] = True
            else:
                async with conn.transaction():
                    result = await gs.apply(conn, spec, value, selection, actor=user.username,
                                            expected_changes=body.expected_changes, audit_row=_audit_writer(user))
                result["dry_run"] = False
        except _ERRORS as exc:
            raise _http(exc)
    if not body.dry_run:
        _invalidate_outage_cache()
    result.update({"kind": k.key, "site_id": site_id, "action": body.action, "line_ids": ids})
    if chain is not None:
        result["chain"] = {"segments": chain["segments"], "other_lines": chain["other_lines"]}
    return result
