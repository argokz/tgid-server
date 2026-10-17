"""Правка карточки объекта сети как в десктопе (gid8 ``property/PropertyDial``): окно свойств веба.

Карточка — та же, что для просмотра (``database/db.py`` ``create_select_line/node``: вкладки и разделы
по ``tab/*.txt``, у участка-пары — колонки «Подача»/«Обратка»), плюс для каждого поля сведения для
правки: тип колонки, список (встроенный ``kls/gid.lookup2`` или справочник ``kls/gid.lookup`` со своим
SQL), функция десктопа (``tab/<table>.fun``), обязательность (``.validate`` NotNull), какие колонки
только для чтения (правила ``PropertyDial::fillValues``), правила видимости и доступности
(``.vis``/``.disable``) и версия каждой строки (``xmin`` → 409 при чужой правке).

Запись — ``save_card``: одна транзакция, ``typed_edit.update_record`` по каждой строке, audit_log.
Таблицы, которые правятся через карточку, — ``EDIT_TABLES`` (расширяется по этапам).
"""

from __future__ import annotations

import re
from typing import Any, Optional

from database import typed_edit as te
from database.sql_ident import quote_ident, resolve_column, resolve_table
from utils.ini import storage

# Таблицы, поля которых правятся через карточку (этап 1 — участки)
EDIT_TABLES: dict[str, str] = {
    "heatpipesections": "Участок трубопровода",
    "linesobj": "Линейный объект",
}

# Поля только для чтения всегда (десктоп: fillValues — код и имя узла в карточке линии)
ALWAYS_READONLY = frozenset({("linesobj", "externalcodeid"), ("linesobj", "externalnodename")})
# У пары П/О: признак подачи правится только в колонке подачи, обратки — в колонке обратки
PAIR_READONLY_COLUMN = {("heatpipesections", "pipesectstateidret"): 0, ("heatpipesections", "pipesectstateidflow"): 1}
OPTIONS_LIMIT = 2000


def fun_name(fun: Optional[str]) -> Optional[str]:
    """«Table "sprav","14_…",2» → «Table»; «Местные сопротивления» → как есть."""
    if not fun:
        return None
    m = re.match(r'^([A-Za-z_][\w-]*)\b', fun)
    return m.group(1) if m else fun.strip()


async def column_specs(conn, table: str) -> dict[str, te.FieldSpec]:
    """Колонки таблицы, которые можно править (lower → FieldSpec): без служебных и геометрии."""
    actual = await resolve_table(conn, table)
    specs: dict[str, te.FieldSpec] = {}
    for key, (name, data_type, max_len) in (await te._columns(conn, actual)).items():
        kind = te._KINDS.get(data_type)
        if kind is None or key in te.SYSTEM_COLUMNS:
            continue
        lookup = storage.get_lookup(table, name)
        specs[key] = te.FieldSpec(
            name=name, label=storage.get_help(table, name)[2] or name, kind=kind, max_length=max_len,
            ref_table=lookup[2].lower() if lookup else None,
            ref_id=lookup[3].lower() if lookup else None,
            ref_label=lookup[4].lower() if lookup else None,
        )
    return specs


def _columns_of(field: dict) -> int:
    return 2 if "id2" in field else 1


def readonly_columns(card_kind: str, table: str, col: str, ncols: int, fun: Optional[str],
                     editable: bool) -> list[bool]:
    t, c = table.lower(), col.lower()
    if (not editable or fun_name(fun) == "ReadOnly" or (t, c) in ALWAYS_READONLY
            or (card_kind == "line" and t == "nodes")):
        return [True] * ncols
    ro = [False] * ncols
    if ncols == 2 and (t, c) in PAIR_READONLY_COLUMN:
        ro[PAIR_READONLY_COLUMN[(t, c)]] = True
    return ro


async def card_fileid(conn, card_kind: str, obj_id: int) -> Optional[int]:
    if card_kind == "line":
        return await conn.fetchval(
            "SELECT n.fileid FROM linesobj l JOIN nodes n ON n.id = l.nodeid1 WHERE l.id = $1", obj_id)
    return await conn.fetchval("SELECT fileid FROM nodes WHERE id = $1", obj_id)


async def annotate_card(conn, card_kind: str, card: dict) -> dict:
    """Карточку просмотра (с include_hidden) дополнить сведениями для правки: field['edit'],
    card['versions'] {"table:id": xmin}, card['rules'] {table: {vis, disable}}."""
    specs: dict[str, dict[str, te.FieldSpec]] = {}
    funs: dict[str, dict[str, str]] = {}
    validate: dict[str, dict[str, str]] = {}
    rows: dict[str, set[int]] = {}
    for tab in card.get("tabs", []):
        if tab.get("readonly"):
            continue
        for sub in tab.get("subsections", []):
            for field in sub.get("fields", []):
                t = str(field["table"]).lower()
                if t not in specs:
                    try:
                        specs[t] = await column_specs(conn, t)
                    except Exception:  # noqa: BLE001 — нет таблицы в этой базе: только просмотр
                        specs[t] = {}
                    funs[t] = await storage.read_fun(field["table"])
                    validate[t] = await storage.read_fun(field["table"], "validate")
                c = str(field["field"]).lower()
                spec = specs[t].get(c)
                fun = funs[t].get(c)
                editable = spec is not None and t in EDIT_TABLES
                ncols = _columns_of(field)
                ids = [field.get("id"), field.get("id2")][:ncols]
                if editable:
                    for i in ids:
                        if isinstance(i, int) and i > 0:
                            rows.setdefault(t, set()).add(i)
                lookup = storage.get_lookup(field["table"], field["field"]) if spec else None
                inline = bool(lookup and storage.get_lookup2(lookup[2]))
                is_select = field.get("type") == "select"
                raw = [field.get("code") if is_select else field.get("value"),
                       field.get("code2") if is_select else field.get("value2")][:ncols]
                field["edit"] = {
                    "kind": spec.kind if spec else None,
                    "max_length": spec.max_length if spec else None,
                    "list": ("inline" if inline else "table") if lookup else None,
                    "fun": fun,
                    "fun_name": fun_name(fun),
                    "not_null": fun_name(validate[t].get(c)) == "NotNull",
                    "readonly": readonly_columns(card_kind, t, c, ncols, fun, editable),
                    "raw": raw,
                }
    versions: dict[str, str] = {}
    for t, ids in rows.items():
        actual = await resolve_table(conn, t)
        for r in await conn.fetch(
                f"SELECT id, xmin::text AS v FROM {quote_ident(actual)} WHERE id = ANY($1::int[])", sorted(ids)):
            versions[f"{t}:{r['id']}"] = r["v"]
    card["versions"] = versions
    card["rules"] = {t: {"vis": await storage.read_vis(t), "disable": await storage.read_disable(t)}
                     for t in specs if t in EDIT_TABLES}
    card["edit_tables"] = sorted(t for t in specs if t in EDIT_TABLES)
    return card


# --- варианты выпадающих списков ---------------------------------------------------------------

def desktop_sql(q: str, *, fileids: list[int], row_id: Optional[int], table: str) -> Optional[str]:
    """SQL справочника из gid.lookup для PostgreSQL, как initLookup/getQLookup/ispr_sql десктопа.

    None — запрос с включениями ###…### (new_baza) или без SELECT: тогда список — по таблице.
    """
    if "###" in q or not re.match(r"^\s*SELECT\b", q, re.I):
        return None
    q = q.replace("\\n", "\n").replace(" TOP 2000000 ", " ")
    q = re.sub(r"\n--AND_TXT[^\n]*", "", q)
    frag = ",".join(str(int(f)) for f in fileids) or "NULL"
    q = q.replace("$fragments$", frag).replace("$id$", str(int(row_id or 0))).replace("$table$", table)
    if "$" in q.replace("$$", ""):
        return None  # неизвестная подстановка ($node_type$ и т.п.)
    m = re.match(r"^\s*SELECT\s+(DISTINCT\s+)?TOP\s+([0-9]+)\s+(.+)$", q, re.I | re.S)
    if m:
        q = f"SELECT {m.group(1) or ''}{m.group(3)} LIMIT {m.group(2)}"
    return q


async def field_options(conn, table: str, field: str, *, fileid: Optional[int] = None,
                        row_id: Optional[int] = None, q: str = "", limit: int = OPTIONS_LIMIT) -> dict:
    """Варианты поля как в десктопе: встроенный список (gid.lookup2, по возрастанию кода), иначе
    свой SQL справочника, иначе таблица-справочник (по фрагменту объекта, если в ней есть fileID;
    по имени, если в gid.lookup признак сортировки). → {"source", "items": [{value, title}]}"""
    lookup = storage.get_lookup(table, field)
    if lookup is None:
        raise te.TypedEditError(404, {"code": "no_lookup", "message": f"У поля {table}.{field} нет списка"})
    (_, _, tn2, id2, fn2, srt) = lookup
    needle = (q or "").strip().lower()
    inline = storage.get_lookup2(tn2)
    if inline:
        items = [{"value": int(k), "title": v} for k, v in sorted(inline.items(), key=lambda kv: int(kv[0]))]
        if needle:
            items = [i for i in items if needle in str(i["title"]).lower()]
        return {"source": "list", "items": items[:limit]}

    own = storage.get_lookup_q(table, field)
    fileids = [int(fileid)] if fileid else [int(r["id"]) for r in await conn.fetch("SELECT id FROM fragments")]
    sql = desktop_sql(own, fileids=fileids, row_id=row_id, table=table) if own else None
    if sql:
        # колонки запроса десктопа — «id, имя» под любыми именами: фильтр по имени — здесь
        async with conn.transaction(readonly=True):
            rows = await conn.fetch(f"SELECT * FROM ({sql}) __ LIMIT {int(limit) * 4}")
        items = []
        for r in rows:
            vals = list(r.values())
            if len(vals) < 2:
                continue
            title = vals[1]
            if needle and needle not in str(title or "").lower():
                continue
            items.append({"value": vals[0], "title": title})
        return {"source": "sql", "items": items[:limit]}

    actual = await resolve_table(conn, tn2)
    id_sql = quote_ident(await resolve_column(conn, actual, id2))
    name_sql = quote_ident(await resolve_column(conn, actual, fn2))
    conds, params = [], []
    if fileid:
        try:
            fcol = await resolve_column(conn, actual, "fileid")
            params.append(int(fileid))
            conds.append(f"{quote_ident(fcol)} = ${len(params)}")
        except Exception:  # noqa: BLE001 — справочник без fileID: весь
            pass
    if needle:
        params.append(f"%{needle}%")
        conds.append(f"{name_sql}::text ILIKE ${len(params)}")
    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    order = name_sql if srt else id_sql
    rows = await conn.fetch(
        f"SELECT {id_sql} AS value, {name_sql} AS title FROM {quote_ident(actual)} {where} "
        f"ORDER BY {order} LIMIT {int(limit)}", *params)
    return {"source": "table", "items": [dict(r) for r in rows]}


# --- запись ---------------------------------------------------------------------------------------

def _row_key(table: str, row_id: int) -> str:
    return f"{table.lower()}:{int(row_id)}"


async def save_card(conn, changes: list[dict[str, Any]], versions: dict[str, str], *,
                    audit_row, dry_run: bool = False) -> dict:
    """Изменения карточки [{table, id, field, value}] → по строке update_record в транзакции
    вызывающего. Поле должно быть правимым (EDIT_TABLES, не ReadOnly). → {"rows": [...]}"""
    by_row: dict[tuple[str, int], dict[str, Any]] = {}
    for ch in changes:
        t = str(ch.get("table", "")).lower()
        if t not in EDIT_TABLES:
            raise te.TypedEditError(403, {"code": "table_not_editable", "table": ch.get("table"),
                                          "message": f"Таблица {ch.get('table')} не правится через карточку"})
        try:
            row_id = int(ch["id"])
        except (KeyError, TypeError, ValueError):
            raise te.TypedEditError(422, {"code": "bad_row", "message": "Нет id строки"})
        by_row.setdefault((t, row_id), {})[str(ch.get("field", ""))] = ch.get("value")
    results = []
    specs_cache: dict[str, dict[str, te.FieldSpec]] = {}
    for (t, row_id), raw in by_row.items():
        if t not in specs_cache:
            specs = await column_specs(conn, t)
            funs = await storage.read_fun(t)
            for col, fun in funs.items():
                if fun_name(fun) == "ReadOnly":
                    specs.pop(col, None)
            for (rt, rc) in ALWAYS_READONLY:
                if rt == t:
                    specs.pop(rc, None)
            specs_cache[t] = specs
        fields = list(specs_cache[t].values())
        for name in raw:
            spec = specs_cache[t].get(name.lower())
            lookup = storage.get_lookup(t, name) if spec else None
            if lookup and storage.get_lookup2(lookup[2]):
                value = raw[name]
                allowed = storage.get_lookup2(lookup[2]) or {}
                try:
                    code = None if value in (None, "") else str(int(float(value)))
                except (TypeError, ValueError):
                    code = "?"
                if code is not None and code not in allowed:
                    raise te.TypedEditError(422, {"code": "bad_ref", "field": name,
                                                  "message": f"«{spec.label}»: значения {value} нет в списке"})
        # встроенные списки (gid.lookup2) проверены выше — ссылку на таблицу не проверяем
        fields = [te.FieldSpec(**{**f.__dict__, "ref_table": None})
                  if f.ref_table and storage.get_lookup2(f.ref_table) else f for f in fields]
        result = await te.update_record(conn, t, "id", row_id, fields, raw,
                                        expected_version=versions.get(_row_key(t, row_id)),
                                        audit_row=audit_row, dry_run=dry_run)
        results.append(result)
    return {"rows": results, "dry_run": dry_run}
