"""Окно свойств: шаблоны значений и «как у соседнего».

Шаблон — значения полей карточки ({таблица: {поле: значение}}) для вида объекта (line — участок,
node — узел).
Применяется к выбранным или новым участкам так же, как правка нескольких объектов
(``card_batch.apply``: одна группа audit_log, отмена — /api/v1/group-setters/undo): значения
шаблона — в каждую колонку (подача и обратка).

«Как у соседнего» — значения конструктива смежного участка (общий узел; предпочтительно тот же
признак П/О и тот же Ду) — те же колонки, что копирует создание участка
(``topology.PASSPORT_TEMPLATE_COLUMNS``), без длины, инвентарного номера и т.п. У узла — смежный
по участку узел (предпочтительно того же типа), иначе ближайший в том же фрагменте: код расчётной
схемы, конструкция, балансовая принадлежность, геодезические отметки.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

from database import card_batch as cb
from database import card_edit as ce
from database import typed_edit as te
from database.sql_ident import resolve_table

KINDS = frozenset(ce.CARD_TABLES)
NAME_MAX = 200
TEMPLATE_SQL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "sql", "migrations", "20261017_card_template.sql")
# Поля участка, которые «как у соседнего» берёт с соседа (кроме конструктива heatpipesections)
NEIGHBOR_LINE_COLUMNS = ("organizationid",)
# Поля узла, которые «как у соседнего» берёт с соседнего узла (без имени, номеров и признака П/О)
NEIGHBOR_NODE_COLUMNS = ("externalcodeid", "nodetypeid", "organizationid", "geomarktoptube", "geomarknodearea")
# Потребители: «как у соседнего» — расчётные коды и признаки, без имени, схемы, нагрузок, адреса,
# договора и диаметров (свои у каждого здания)
NEIGHBOR_OWNER_COLUMNS: dict[str, tuple[str, ...]] = {
    "consumer": (
        "automdegid", "buildingtypeid", "specexpendid", "calctemperatureid", "varcoeffid", "accumcoeff",
        "volwaterhs", "volwatervs", "hourirregcoeff", "calctemphr", "calctempvs", "calctemphwdo",
        "temprecircpipe", "circhlosopen", "closesyscalcsignid", "calcsignopensysflowid", "calcsignreswdoretid",
        "hydromodesignid", "throtstagesignid", "temperchartsignid", "pdvalveinstalllocid", "setpdonregulator",
        "wemeteringdeviceid",
    ),
    "genconsumer": (
        "specexpendid", "calctemperatureid", "varcoeffid", "volwaterhs", "volwatervs", "pdvalveinstalllocid",
        "setpdonregulator", "wemeteringdeviceid", "closesyscalcsignid", "calcsignopensysflowid",
        "calcsignreswdoretid", "connectionschemeid", "calctempdep", "calctempindep", "calctempha",
        "hourirregcoeffparall", "hourirregcoeffmix", "hourirregcoeffconseq", "hourirregcoeffpreon",
        "hourirregcoeffopen", "calctemphrparall", "calctemphrmix", "calctemphrconseq", "calctemphrpreon",
        "calctemphwdoparall", "calctemphwdomix", "calctemphwdoconseq", "calctemphwdopreon", "calctemphwdoopen",
    ),
}
# соседи ищутся в радиусе (единицы геометрии узлов); дальше — ближайший с той же схемой не важнее близости
NEIGHBOR_RADIUS = 500

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
        if t not in ce.CARD_TABLES[kind]:
            raise _err(422, "table_not_editable", f"Таблица {table} не правится через карточку")
        if not isinstance(fields, dict) or not fields:
            continue
        funs = await ce.storage.read_fun(t)
        fields = {f: v for f, v in fields.items()
                  if ce.fun_name(funs.get(str(f).lower())) not in ce.BATCH_READONLY_FUNS}
        if not fields:
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
    kind = template.get("kind") or "line"
    columns = await cb.object_columns(conn, kind, line_ids)
    changes = []
    for ci in range(len(columns)):
        for table, fields in (template.get("values") or {}).items():
            for field, value in fields.items():
                if ce.readonly_columns(kind, table, field, len(columns), None, True)[ci]:
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
        out.append({"line_id": lid, "neighbor_line_id": nid, "neighbor_id": nid,
                    "values": values, "titles": titles})
    return {"columns": out}


async def neighbor_node_values(conn, node_id: int) -> dict:
    """«Как у соседнего» для карточки узла: узел, смежный по участку (предпочтительно того же типа),
    иначе ближайший в том же фрагменте; его значения NEIGHBOR_NODE_COLUMNS."""
    cols = {f.name.lower(): f.name for f in await ce.writable_specs(conn, "nodes")}
    take = [cols[c] for c in NEIGHBOR_NODE_COLUMNS if c in cols]
    me = await conn.fetchrow("SELECT id, fileid, nodetypeid, shape FROM nodes WHERE id = $1", int(node_id))
    if me is None:
        raise _err(404, "not_found", "Узел не найден")
    nb = await conn.fetchval(
        """
        SELECT b.id
          FROM linesobj l
          JOIN nodes b ON b.id = CASE WHEN l.nodeid1 = $1 THEN l.nodeid2 ELSE l.nodeid1 END
         WHERE (l.nodeid1 = $1 OR l.nodeid2 = $1) AND COALESCE(l.removed, 0) = 0
           AND COALESCE(b.removed, 0) = 0 AND b.id <> $1
         ORDER BY (b.nodetypeid IS NOT DISTINCT FROM $2) DESC, b.id
         LIMIT 1
        """, int(node_id), me["nodetypeid"])
    if nb is None and me["shape"] is not None:
        nb = await conn.fetchval(
            "SELECT b.id FROM nodes b, nodes a WHERE a.id = $1 AND b.id <> a.id AND COALESCE(b.removed, 0) = 0 "
            "AND b.fileid IS NOT DISTINCT FROM a.fileid AND b.shape IS NOT NULL "
            "ORDER BY b.shape <-> a.shape LIMIT 1", int(node_id))
    if nb is None or not take:
        return {"columns": [{"node_id": int(node_id), "neighbor_id": None, "values": {}, "titles": {}}]}
    sel = ", ".join(f'"{c}"' for c in take)
    row = await conn.fetchrow(f"SELECT {sel} FROM nodes WHERE id = $1", int(nb))
    # пустые значения соседа не переносятся: не стирать заполненное (тип камеры рядом с обычным узлом)
    take = [c for c in take if row[c] is not None]
    values = {"nodes": {c: te.jsonable(row[c]) for c in take}}
    titles: dict[str, dict[str, Any]] = {"nodes": {}}
    for c in take:
        if row[c] is not None and ce.storage.get_lookup("nodes", c):
            titles["nodes"][c] = await cb.value_title(conn, "nodes", c, row[c])
    return {"columns": [{"node_id": int(node_id), "neighbor_id": int(nb), "values": values, "titles": titles}]}


async def neighbor_owner_values(conn, kind: str, node_id: int) -> dict:
    """«Как у соседнего» для потребителя (обобщённого потребителя): ближайший объект того же вида
    в том же фрагменте (у потребителя — предпочтительно с той же схемой присоединения в пределах
    NEIGHBOR_RADIUS); его значения NEIGHBOR_OWNER_COLUMNS[kind] — в каждую колонку карточки."""
    if kind not in NEIGHBOR_OWNER_COLUMNS:
        raise _err(422, "no_neighbor", "Для этого вида объектов «как у соседнего» нет")
    table = ce.NODE_CARD_TABLE[kind].lower()
    actual = await resolve_table(conn, table)
    cols = {f.name.lower(): f.name for f in await ce.writable_specs(conn, table)}
    take = [cols[c] for c in NEIGHBOR_OWNER_COLUMNS[kind] if c in cols]
    own_rows = await conn.fetch(f'SELECT id FROM "{actual}" WHERE nodeid = $1 ORDER BY id', int(node_id))
    if not own_rows:
        raise _err(404, "not_found", "Объект не найден")
    ncols = min(len(own_rows), 2)  # как карточка: не больше двух колонок
    has_scheme = "schemenum" in cols
    same_scheme = (f'((SELECT schemenum FROM "{actual}" s WHERE s.nodeid = c.id ORDER BY s.id LIMIT 1) '
                   f'IS NOT DISTINCT FROM (SELECT schemenum FROM "{actual}" s WHERE s.nodeid = $1 ORDER BY s.id LIMIT 1)) '
                   'DESC, ' if has_scheme else "")
    nb = await conn.fetchval(
        f"""
        SELECT id FROM (
            SELECT b.id, b.shape <-> a.shape AS d
              FROM nodes a, nodes b
             WHERE a.id = $1 AND b.id <> a.id AND COALESCE(b.removed, 0) = 0
               AND b.fileid IS NOT DISTINCT FROM a.fileid AND b.shape IS NOT NULL AND a.shape IS NOT NULL
               AND EXISTS (SELECT 1 FROM "{actual}" t WHERE t.nodeid = b.id)
             ORDER BY b.shape <-> a.shape
             LIMIT 50
        ) c
        ORDER BY (c.d > {NEIGHBOR_RADIUS}), {same_scheme}c.d
        LIMIT 1
        """, int(node_id))
    empty = [{"node_id": int(node_id), "neighbor_id": None, "values": {}, "titles": {}}] * ncols
    if nb is None or not take:
        return {"columns": empty}
    sel = ", ".join(f'"{c}"' for c in take)
    row = await conn.fetchrow(f'SELECT {sel} FROM "{actual}" WHERE nodeid = $1 ORDER BY id LIMIT 1', int(nb))
    take = [c for c in take if row[c] is not None]
    values = {table: {c: te.jsonable(row[c]) for c in take}}
    titles: dict[str, dict[str, Any]] = {table: {}}
    for c in take:
        if ce.storage.get_lookup(table, c):
            titles[table][c] = await cb.value_title(conn, table, c, row[c])
    col = {"node_id": int(node_id), "neighbor_id": int(nb), "values": values, "titles": titles}
    return {"columns": [col] * ncols}
