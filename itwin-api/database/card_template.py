"""Окно свойств: шаблоны значений и «как у соседнего».

Шаблон — значения полей карточки ({таблица: {поле: значение}}) для вида объекта (line — участок).
Применяется к выбранным или новым участкам так же, как правка нескольких объектов
(``card_batch.apply``: одна группа audit_log, отмена — /api/v1/group-setters/undo): значения
шаблона — в каждую колонку (подача и обратка).

«Как у соседнего» — значения конструктива смежного участка (общий узел; предпочтительно тот же
признак П/О и тот же Ду) — те же колонки, что копирует создание участка
(``topology.PASSPORT_TEMPLATE_COLUMNS``), без длины, инвентарного номера и т.п.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from database import card_batch as cb
from database import card_edit as ce
from database import typed_edit as te
from database.sql_ident import resolve_table

KINDS = frozenset({"line"})
NAME_MAX = 200
TEMPLATE_SQL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "sql", "migrations", "20261017_card_template.sql")
# Поля участка, которые «как у соседнего» берёт с соседа (кроме конструктива heatpipesections)
NEIGHBOR_LINE_COLUMNS = ("organizationid",)

_ready: set[str] = set()


def _err(status: int, code: str, message: str) -> te.TypedEditError:
    return te.TypedEditError(status, {"code": code, "message": message})


async def ensure_table(conn) -> None:
    """Таблицы нет — создать (sql/migrations/20261017_card_template.sql)."""
    db = await conn.fetchval("SELECT current_database()")
    if db in _ready:
        return
    if not await conn.fetchval("SELECT to_regclass('public.card_template') IS NOT NULL"):
        with open(TEMPLATE_SQL, encoding="utf-8") as fh:
            await conn.execute(fh.read())
    _ready.add(db)


def _row(r) -> dict:
    values = r["values"]
    if isinstance(values, str):
        values = json.loads(values)
    return {"id": r["id"], "kind": r["kind"], "name": r["name"], "values": values or {},
            "author": r["author"], "shared": r["shared"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None}


async def clean_values(conn, kind: str, values: dict) -> dict:
    """Значения шаблона: только правимые поля карточки, типы по схеме (как при сохранении карточки)."""
    if kind not in KINDS:
        raise _err(422, "bad_kind", f"Шаблоны для «{kind}» пока не поддерживаются")
    out: dict[str, dict[str, Any]] = {}
    for table, fields in (values or {}).items():
        t = str(table).lower()
        if t not in ce.EDIT_TABLES:
            raise _err(422, "table_not_editable", f"Таблица {table} не правится через карточку")
        if not isinstance(fields, dict) or not fields:
            continue
        specs = ce.check_inline_codes(t, await ce.writable_specs(conn, t), fields)
        by_name, typed = te.prepare_values(specs, fields)
        await te._check_refs(conn, by_name, typed)
        out[t] = {c: te.jsonable(v) for c, v in typed.items()}
    if not any(out.values()):
        raise _err(422, "no_values", "В шаблоне нет значений")
    return out


async def list_templates(conn, kind: str, user: str) -> list[dict]:
    await ensure_table(conn)
    rows = await conn.fetch(
        "SELECT * FROM card_template WHERE kind = $1 AND (shared OR author = $2) ORDER BY lower(name), id",
        kind, user)
    out = []
    for r in rows:
        item = _row(r)
        item["titles"] = await _titles(conn, item["values"])
        out.append(item)
    return out


async def _titles(conn, values: dict) -> dict:
    """Подписи значений списков шаблона ({таблица: {поле: подпись}})."""
    titles: dict[str, dict[str, Any]] = {}
    for table, fields in (values or {}).items():
        for field, value in fields.items():
            if value is not None and ce.storage.get_lookup(table, field):
                titles.setdefault(table, {})[field] = await cb.value_title(conn, table, field, value)
    return titles


async def get_template(conn, template_id: int, user: str) -> dict:
    await ensure_table(conn)
    r = await conn.fetchrow("SELECT * FROM card_template WHERE id = $1", int(template_id))
    if r is None or not (r["shared"] or r["author"] == user):
        raise _err(404, "not_found", "Шаблон не найден")
    return _row(r)


async def create_template(conn, *, kind: str, name: str, values: dict, shared: bool, user: str) -> dict:
    await ensure_table(conn)
    name = (name or "").strip()[:NAME_MAX]
    if not name:
        raise _err(422, "no_name", "Укажите название шаблона")
    clean = await clean_values(conn, kind, values)
    r = await conn.fetchrow(
        'INSERT INTO card_template (kind, name, "values", author, shared) VALUES ($1, $2, $3::jsonb, $4, $5) '
        "RETURNING *", kind, name, json.dumps(clean, ensure_ascii=False), user, bool(shared))
    return _row(r)


async def update_template(conn, template_id: int, *, name: Optional[str], values: Optional[dict],
                          shared: Optional[bool], user: str, is_admin: bool) -> dict:
    cur = await get_template(conn, template_id, user)
    if cur["author"] != user and not is_admin:
        raise _err(403, "not_author", "Изменить шаблон может только автор")
    new_name = (name if name is not None else cur["name"]).strip()[:NAME_MAX]
    if not new_name:
        raise _err(422, "no_name", "Укажите название шаблона")
    clean = await clean_values(conn, cur["kind"], values) if values is not None else cur["values"]
    r = await conn.fetchrow(
        'UPDATE card_template SET name = $2, "values" = $3::jsonb, shared = $4, updated_at = now() '
        "WHERE id = $1 RETURNING *", int(template_id), new_name, json.dumps(clean, ensure_ascii=False),
        cur["shared"] if shared is None else bool(shared))
    return _row(r)


async def delete_template(conn, template_id: int, *, user: str, is_admin: bool) -> None:
    cur = await get_template(conn, template_id, user)
    if cur["author"] != user and not is_admin:
        raise _err(403, "not_author", "Удалить шаблон может только автор")
    await conn.execute("DELETE FROM card_template WHERE id = $1", int(template_id))


async def template_changes(conn, template: dict, line_ids: list[int]) -> list[dict]:
    """Изменения правки выбора: значения шаблона — в каждую колонку выбора (подача/обратка)."""
    columns = await cb.line_columns(conn, line_ids)
    changes = []
    for ci in range(len(columns)):
        for table, fields in (template.get("values") or {}).items():
            for field, value in fields.items():
                if ce.readonly_columns("line", table, field, len(columns), None, True)[ci]:
                    continue
                changes.append({"table": table, "id": ci + 1, "field": field, "value": value})
    return changes


async def neighbor_values(conn, line_id: int) -> dict:
    """«Как у соседнего» для карточки участка: по колонке (подача/обратка) — участок-сосед и его
    значения {таблица: {поле: значение}} с подписями списков."""
    from database.db import line_pair_ids
    from database.topology import PASSPORT_TEMPLATE_COLUMNS

    actual = await resolve_table(conn, "heatpipesections")
    columns = await line_pair_ids(conn, actual, int(line_id))
    hps_cols = {f.name.lower(): f.name for f in await ce.writable_specs(conn, "heatpipesections")}
    line_cols = {f.name.lower(): f.name for f in await ce.writable_specs(conn, "linesobj")}
    take_hps = [hps_cols[c] for c in PASSPORT_TEMPLATE_COLUMNS if c in hps_cols]
    take_line = [line_cols[c] for c in NEIGHBOR_LINE_COLUMNS if c in line_cols]
    out = []
    for lid in columns:
        nb = await conn.fetchrow(
            """
            SELECT b.id
              FROM linesobj a
              JOIN linesobj b ON b.id <> a.id AND COALESCE(b.removed, 0) = 0
               AND (b.nodeid1 IN (a.nodeid1, a.nodeid2) OR b.nodeid2 IN (a.nodeid1, a.nodeid2))
               AND NOT (b.nodeid1 = a.nodeid1 AND b.nodeid2 = a.nodeid2)
              JOIN heatpipesections hb ON hb.lineid = b.id
              LEFT JOIN heatpipesections ha ON ha.lineid = a.id
             WHERE a.id = $1
             ORDER BY (b.externalsignlineid IS NOT DISTINCT FROM a.externalsignlineid) DESC,
                      (hb.diametercondit IS NOT DISTINCT FROM ha.diametercondit) DESC, b.id
             LIMIT 1
            """, lid)
        if nb is None:
            out.append({"line_id": lid, "neighbor_line_id": None, "values": {}, "titles": {}})
            continue
        nid = int(nb["id"])
        values: dict[str, dict[str, Any]] = {}
        titles: dict[str, dict[str, Any]] = {}
        for table, cols, key in (("heatpipesections", take_hps, "lineid"), ("linesobj", take_line, "id")):
            if not cols:
                continue
            sel = ", ".join(f'"{c}"' for c in cols)
            row = await conn.fetchrow(f"SELECT {sel} FROM {table} WHERE {key} = $1 ORDER BY id LIMIT 1", nid)
            if row is None:
                continue
            values[table] = {c: te.jsonable(row[c]) for c in cols}
            titles[table] = {}
            for c in cols:
                if row[c] is not None and ce.storage.get_lookup(table, c):
                    titles[table][c] = await cb.value_title(conn, table, c, row[c])
        out.append({"line_id": lid, "neighbor_line_id": nid, "values": values, "titles": titles})
    return {"columns": out}
