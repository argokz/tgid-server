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
                    "helper": fun_name(fun) in HELPER_FUNS,
                    "after": fun_name(fun) in AFTER_FUNS,
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


# --- помощники полей (функции десктопа prop_fun_progr.cpp) ---------------------------------------

# Функции с окном-помощником в карточке: выбор по сортаменту, строка справочной таблицы,
# местные сопротивления; ms_rs — список с зависимыми полями (магистраль/участок МС/участок РС)
HELPER_FUNS = frozenset({"diameter_std", "Table", "Местные сопротивления"})
AFTER_FUNS = frozenset({"ms_rs"})

# fun_diameter_std: выбранная труба заполняет четыре поля той же колонки
DIAMETER_SET = {"diameterCondit": "diametr_usl", "diameterExternal": "diamvne",
                "diameterInternal": "diametr", "wallThickness": "tol"}
GOST_NAMES = ("ГОСТ", "Стандарт", "Россия")
HELPER_ROWS_LIMIT = 2000

_TRANSL = {
    "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E", "Ж": "Zh", "З": "Z", "И": "I",
    "Й": "Y", "К": "K", "Л": "L", "М": "M", "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T",
    "У": "U", "Ф": "F", "Х": "H", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Sch", "Ъ": "", "Ы": "Y", "Ь": "",
    "Э": "E", "Ю": "Yu", "Я": "Ya",
}
_TRANSL.update({k.lower(): v.lower() for k, v in list(_TRANSL.items())})
_TRANSL.update({"/": "_", " ": "_", "(": "_", ")": "_", ">": "gt", "<": "lt", ".": "_", ",": "_",
                ":": "_", '"': "_"})


def transl(name: str) -> str:
    """Имя справочной таблицы, как transl() десктопа (any/any.cpp): транслит, ≤64 символа, lower."""
    return "".join(_TRANSL.get(ch, ch) for ch in name)[:64].lower()


def parse_table_fun(fun: str) -> Optional[tuple[str, str, int]]:
    """«Table "sprav","14_Шероховатость стальных труб",2» → (база, таблица, № колонки результата)."""
    m = re.match(r'^Table "(.+?)"\s*,\s*"(.+?)"\s*,\s*([0-9]+)\s*$', fun or "")
    return (m.group(1), m.group(2), int(m.group(3))) if m else None


def _qi_catalog(name: str) -> str:
    """Имя из каталога справочной базы (может начинаться с цифры: «14_sherohovatost…»)."""
    if not re.fullmatch(r"\w{1,64}", name or ""):
        raise te.TypedEditError(404, {"code": "no_table", "message": f"Недопустимое имя {name!r}"})
    return f'"{name}"'


def _jsonable(v: Any) -> Any:
    if v is None or isinstance(v, (int, float, str, bool)):
        return v
    try:
        return float(v)  # Decimal
    except (TypeError, ValueError):
        return str(v)


async def _standard_names(conn, table: str, standard_id: Optional[int]) -> tuple[str, ...]:
    """Стандарт труб участка по standardID — как getValueString десктопа (подпись значения).
    ГОСТ/Стандарт/Россия/пусто — одна группа."""
    title = ""
    if standard_id:
        lookup = storage.get_lookup(table, "standardID")
        inline = storage.get_lookup2(lookup[2]) if lookup else None
        if inline:
            title = inline.get(str(int(standard_id)), "")
        else:
            title = await conn.fetchval("SELECT name FROM standards WHERE id = $1", int(standard_id)) or ""
    return GOST_NAMES if title in GOST_NAMES or not title else (title,)


async def _diameter_helper(conn, table: str, standard_id: Optional[int]) -> dict:
    names = list(await _standard_names(conn, table, standard_id))
    rows = await conn.fetch(
        "SELECT tr.id, st.name AS stand, tr.diametr_usl, tr.diamvne, tr.diametr, tr.tol "
        "FROM standardtubes tr "
        "JOIN standards st ON st.name = tr.stand "
        "  OR (st.name = ANY($2::text[]) AND tr.stand = ANY($2::text[])) "
        "WHERE st.name = ANY($1::text[]) ORDER BY tr.diametr_usl, tr.diamvne, tr.tol, tr.id",
        names, list(GOST_NAMES))
    cols = ["stand", "diametr_usl", "diamvne", "diametr", "tol"]
    return {
        "type": "pick",
        "title": "Выберите диаметр трубопровода",
        "columns": [{"key": c, "title": storage.get_help("standardTubes", c)[2]} for c in cols],
        "rows": [{c: _jsonable(r[c]) for c in ["id", *cols]} for r in rows],
        "set": dict(DIAMETER_SET),
    }


async def _table_helper(conn, field: str, fun: str, label: str) -> Optional[dict]:
    """fun_Table/viewTable: строки справочной таблицы (create_select_rus: id, затем остальные колонки
    в порядке таблицы, подписи — kls/gid.txt2); в поле — колонка с номером из функции."""
    parsed = parse_table_fun(fun)
    if not parsed:
        return None
    db, title, n_ret = parsed
    tn = transl(title)
    own = None
    if db not in ("$main$", "$ps$"):
        import asyncpg

        from database.heat_losses_norm import sprav_db_config

        own = await asyncpg.connect(**{**sprav_db_config(), "database": db}, timeout=30)
    src = own or conn
    try:
        cols = [r["column_name"] for r in await src.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = $1 "
            "AND table_schema = 'public' ORDER BY ordinal_position", tn)]
        if not cols:
            raise te.TypedEditError(404, {"code": "no_table", "message": f"Нет справочника «{title}»"})
        id_col = next((c for c in cols if c.lower() == "id"), None)
        rest = [c for c in cols if c.lower() not in ("id", "shape")]
        order = [*([id_col] if id_col else []), *rest]
        select = ", ".join(_qi_catalog(c) for c in order)
        async with src.transaction(readonly=True):
            rows = await src.fetch(f"SELECT {select} FROM {_qi_catalog(tn)} "
                                   f"ORDER BY {_qi_catalog(id_col or order[0])} LIMIT {HELPER_ROWS_LIMIT}")
    finally:
        if own is not None:
            await own.close()
    # номер колонки результата — как TableWindow::value(n) по колонкам запроса; за пределами — последняя
    ret = order[min(n_ret, len(order) - 1)]
    return {
        "type": "pick",
        "title": label or title,
        "subtitle": title,
        "columns": [{"key": c, "title": storage.get_help(tn, c)[2]} for c in rest],
        "rows": [{c: _jsonable(r[c]) for c in order} for r in rows],
        "set": {field: ret},
        # в десктопе — значение колонки; в вебе можно взять и соседнее значение диапазона (min/max)
        "cell_pick": True,
    }


async def local_resistances(conn) -> list[dict]:
    """Виды местных сопротивлений — запрос десктопа sql/sp/s08.sql (MestSopr3)."""
    from utils.ini import open_arg

    path = await open_arg("sql/sp/s08.sql")
    with open(path, encoding="cp1251") as f:
        q = f.read()
    async with conn.transaction(readonly=True):
        rows = await conn.fetch(q)
    out = []
    for r in rows:
        v = list(r.values())
        out.append({"id": int(v[0]), "name": str(v[1]), "min": float(v[2]), "max": float(v[3])})
    return out  # порядок файла, как в окне десктопа


async def field_helper(conn, table: str, field: str, *, standard_id: Optional[int] = None) -> dict:
    """Данные окна-помощника поля (функция tab/<table>.fun) — как одноимённая функция десктопа."""
    fun = (await storage.read_fun(table)).get(field.lower())
    name = fun_name(fun)
    if name not in HELPER_FUNS:
        raise te.TypedEditError(404, {"code": "no_helper", "message": f"У поля {table}.{field} нет помощника"})
    label = storage.get_help(table, field)[2]
    if name == "diameter_std":
        return await _diameter_helper(conn, table, standard_id)
    if name == "Table":
        res = await _table_helper(conn, field, fun or "", label)
        if res is None:
            raise te.TypedEditError(404, {"code": "no_helper", "message": f"Не разобрана функция «{fun}»"})
        return res
    return {"type": "mestn", "title": "Местные сопротивления", "items": await local_resistances(conn),
            "set": {"sum": field, "list": "mestn"}}


async def after_change(conn, table: str, field: str, value: Any) -> dict:
    """Зависимые поля после выбора значения (fun_ms_rs): {"set": {поле: {value, title}}}.

    магистраль → участок РС пусто; участок МС → магистраль участка МС, участок РС пусто;
    участок РС → магистраль и участок МС пусто."""
    fun = (await storage.read_fun(table)).get(field.lower())
    if fun_name(fun) != "ms_rs":
        return {"set": {}}
    empty = {"value": None, "title": None}
    key = field.lower()
    if key == "magistral":
        return {"set": {"distSite": empty}}
    if key == "distsite":
        return {"set": {"magistral": empty, "magistralSite": empty}}
    if key == "magistralsite":
        mag = None
        if value not in (None, ""):
            row = await conn.fetchrow(
                "SELECT m.id, m.naimenovanie_magistrali AS title FROM uchastok_ms u "
                "JOIN magistrali m ON m.id = u.magistral WHERE u.id = $1", int(float(value)))
            if row and int(row["id"]) > 0:
                mag = {"value": int(row["id"]), "title": row["title"]}
        return {"set": {"magistral": mag or empty, "distSite": empty}}
    return {"set": {}}


# --- запись ---------------------------------------------------------------------------------------

def _row_key(table: str, row_id: int) -> str:
    return f"{table.lower()}:{int(row_id)}"


async def writable_specs(conn, table: str) -> list[te.FieldSpec]:
    """Колонки таблицы карточки, которые можно записать: без ReadOnly (.fun) и ALWAYS_READONLY."""
    t = table.lower()
    specs = await column_specs(conn, t)
    for col, fun in (await storage.read_fun(t)).items():
        if fun_name(fun) == "ReadOnly":
            specs.pop(col, None)
    for (rt, rc) in ALWAYS_READONLY:
        if rt == t:
            specs.pop(rc, None)
    return list(specs.values())


def check_inline_codes(table: str, fields: list[te.FieldSpec], raw: dict[str, Any]) -> list[te.FieldSpec]:
    """Коды встроенных списков (gid.lookup2) — только из списка. → поля без проверки ссылки
    на таблицу у встроенных списков (таблицы справочника может и не быть)."""
    by_key = {f.name.lower(): f for f in fields}
    for name, value in raw.items():
        spec = by_key.get(str(name).lower())
        lookup = storage.get_lookup(table, name) if spec else None
        allowed = storage.get_lookup2(lookup[2]) if lookup else None
        if not allowed:
            continue
        try:
            code = None if value in (None, "") else str(int(float(value)))
        except (TypeError, ValueError):
            code = "?"
        if code is not None and code not in allowed:
            raise te.TypedEditError(422, {"code": "bad_ref", "field": name,
                                          "message": f"«{spec.label}»: значения {value} нет в списке"})
    return [te.FieldSpec(**{**f.__dict__, "ref_table": None})
            if f.ref_table and storage.get_lookup2(f.ref_table) else f for f in fields]


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
    specs_cache: dict[str, list[te.FieldSpec]] = {}
    for (t, row_id), raw in by_row.items():
        if t not in specs_cache:
            specs_cache[t] = await writable_specs(conn, t)
        fields = check_inline_codes(t, specs_cache[t], raw)
        result = await te.update_record(conn, t, "id", row_id, fields, raw,
                                        expected_version=versions.get(_row_key(t, row_id)),
                                        audit_row=audit_row, dry_run=dry_run)
        results.append(result)
    return {"rows": results, "dry_run": dry_run}
