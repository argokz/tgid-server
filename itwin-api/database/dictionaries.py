"""Редактируемые справочники (этап 9): удельные расходы, Kv, расчётные температуры, графики ГВС,
организации, районы, техники.

Эталон — gid8 ``dialog/NoVisual.cpp`` (дерево «Неграфические данные»: initUR/initTR/initKV/initGV,
onAdd — строка с fileID текущего фрагмента, onDelete — запрет удаления, если код используется
потребителями/участками: inConsumer/inTable). Справочники расчётной схемы (UR/TR/KV/GV) живут
по фрагментам (``fileid``).

Правила: таблица — из ``DICTIONARIES`` (allow-list), колонки — из каталога этой таблицы минус
служебные; значения приводятся к типу колонки; удаление при ссылках → 409 со списком ссылок
(внешних ключей в legacy-схеме нет, ссылки перечислены в спецификации явно). Все функции
работают в транзакции вызывающего; audit_log пишет роутер.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from database.sql_ident import UnknownIdentifierError, quote_ident, resolve_column, resolve_table

LIST_LIMIT_MAX = 500


class DictionaryError(Exception):
    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class Usage:
    table: str
    column: str
    label: str
    match: str = "id"  # id — целочисленная ссылка; name — текстовая колонка хранит наименование


@dataclass(frozen=True)
class Lookup:
    table: str
    label_column: str = "name"


@dataclass(frozen=True)
class DictSpec:
    key: str
    label: str
    table: str
    label_column: str
    usages: tuple[Usage, ...]
    fragment_scoped: bool = False
    unique_label: bool = False
    order_sql: Optional[str] = None
    affects_calc: bool = False
    note: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    lookups: dict[str, Lookup] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    desktop: str = ""


EXCLUDED_COLUMNS = frozenset({"id", "id_old", "shape", "geom"})

_RC, _GC = "realconsumers", "generalizedconsumers"


def _consumers(column: str) -> tuple[Usage, ...]:
    return (Usage(_RC, column, "Потребители реальные"), Usage(_GC, column, "Потребители обобщённые"))


_RAYON_USAGES = tuple(
    Usage(t, "rayon_ekspluatatsii", label) for t, label in (
        ("istochniki_tepla", "Источники тепла"),
        ("uchastki_ekspluatatsii", "Участки эксплуатации"),
        ("zdaniya_tu", "Здания ТУ"),
        ("capital2", "Капремонт"),
        ("defekt2", "Дефекты (2)"),
        ("kapremont_uchastok_teploprovoda_ishodnyy", "Капремонт: исходные участки"),
        ("kapremont_uchastok_teploprovoda_posle_remonta", "Капремонт: участки после ремонта"),
    )
)

_ORG_USAGES = (
    Usage("linesobj", "organizationid", "Линейные объекты"),
    Usage("nodes", "organizationid", "Узлы"),
    Usage("heatpipesections", "organizationid", "Участки теплопроводов"),
    Usage("pipesections", "organizationid", "Трубопроводы"),
    Usage("pavilion", "organizationid", "Павильоны"),
    Usage("pavilion", "yuridicheskoe_litso", "Павильоны (юр. лицо)"),
    Usage("tkamera", "organizationid", "Тепловые камеры"),
    Usage("tkamera", "yuridicheskoe_litso", "Тепловые камеры (юр. лицо)"),
    Usage("kanal", "yuridicheskoe_litso", "Каналы"),
    Usage("kompensator", "yuridicheskoe_litso", "Компенсаторы"),
    Usage("kamera_opuska_ili_podema", "yuridicheskoe_litso", "Камеры опуска/подъёма"),
    Usage("uchastok_rs", "predpriyatie_vladelets", "Участки РС"),
    Usage("kontrol_tehnicheskogo_sostoyaniya", "organizatsiya", "Контроль техсостояния"),
)

_RESPONSIBLE_USAGES = (Usage(_RC, "responsibleid", "Потребители реальные"),) + tuple(
    Usage(t, "responsibleid", label) for t, label in (
        ("defect", "Нарушения"), ("diag", "Диагностика"), ("indikator_korrozii", "Индикаторы коррозии"),
        ("mufta", "Муфты"), ("opres", "Опрессовки"), ("remont", "Ремонты"), ("remont2", "Ремонты (контуры)"),
        ("uchastok_ms", "Участки МС"), ("uchastok_rs", "Участки РС"),
    )
)

_DICTS: tuple[DictSpec, ...] = (
    DictSpec("spec-expends", "Удельные расходы", "specexpends", "specexpendid", _consumers("specexpendid"),
             fragment_scoped=True, unique_label=True, affects_calc=True,
             labels={"specexpendid": "Код удельных расходов", "hsourcecode": "Код источника"},
             desktop="gid8 NoVisual initUR (specExpends)"),
    DictSpec("var-coefficients", "Коэффициенты вариации (Kv)", "varcoefficients", "kodkv",
             _consumers("varcoeffid") + (Usage("heatpipesections", "varcoeffidflow", "Участки (подача)"),
                                         Usage("heatpipesections", "varcoeffidret", "Участки (обратка)")),
             fragment_scoped=True, unique_label=True, affects_calc=True,
             note="Kv умножают расчётные нагрузки потребителей и расходы на участках: расчёт с Kv и без Kv "
                  "расходится (docs/acceptance-numeric.md). После правки пересчитайте режим.",
             desktop="gid8 NoVisual initKV (varCoefficients)"),
    DictSpec("calc-temperatures", "Расчётные температуры", "calctemperatures", "calctemperatureid",
             _consumers("calctemperatureid"), fragment_scoped=True, unique_label=True, affects_calc=True,
             labels={"calctemperatureid": "Код расчётных температур"},
             desktop="gid8 NoVisual initTR (calcTemperatures)"),
    DictSpec("gvs-load-graphs", "Графики нагрузки ГВС", "gvsloadgraphs", "gvsloadgraphid",
             _consumers("gvsloadgraphid"), fragment_scoped=True, unique_label=True, affects_calc=True,
             labels={"gvsloadgraphid": "Код графика ГВС"},
             desktop="gid8 NoVisual initGV (gvsLoadGraphs)"),
    DictSpec("organizations", "Организации", "organizations", "name", _ORG_USAGES,
             labels={"name": "Наименование", "sign": "Признак", "phone": "Телефон",
                     "managerphone": "Телефон руководителя", "street": "Улица", "housenumber": "Дом",
                     "organizationtypeid": "Тип организации", "ownerorganizationtypeid": "Тип собственности"},
             lookups={"organizationtypeid": Lookup("organizationtypes"),
                      "ownerorganizationtypeid": Lookup("ownerorganizationtypes")},
             desktop="gid8 aSetOrg (organizations), GID.lookup linesobj/nodes.organizationID"),
    DictSpec("exploitation-districts", "Эксплуатационные районы", "rayon_ekspluatatsii",
             "naimenovanie_rayona_ekspluatatsii_istochnika_tepla", _RAYON_USAGES, unique_label=True,
             order_sql="nomer_po_poryadku NULLS LAST, id",
             labels={"naimenovanie_rayona_ekspluatatsii_istochnika_tepla": "Наименование района",
                     "nomer_po_poryadku": "№ по порядку"},
             desktop="GID.lookup istochniki_tepla/uchastki_ekspluatatsii.rayon_ekspluatatsii"),
    DictSpec("administrative-districts", "Административные районы", "administrativnyy_rayon", "name",
             (Usage("zhile", "administrativnyy_rayon", "Жильё", "name"),
              Usage("zhile1", "administrativnyy_rayon", "Жильё (1)", "name"),
              Usage("organizatsii", "administrativnyy_rayon_po_obektu", "Договоры АЛСЕКО", "name")),
             unique_label=True, labels={"name": "Наименование"},
             note="Ссылки хранят наименование района, а не id: переименование не обновляет их."),
    DictSpec("responsibles", "Техники (ответственные)", "responsibles", "name", _RESPONSIBLE_USAGES,
             labels={"name": "ФИО", "statusid": "Статус"}, defaults={"statusid": 15},
             note="Установщик «ФИО техников» (gid8 aSetOtv) показывает техников со статусом 15.",
             desktop="gid8 aSetOtv (responsibles)"),
)

DICTIONARIES: dict[str, DictSpec] = {d.key: d for d in _DICTS}

DICTIONARY_TABLES: frozenset[str] = frozenset(
    {d.table for d in _DICTS}
    | {u.table for d in _DICTS for u in d.usages}
    | {lk.table for d in _DICTS for lk in d.lookups.values()}
    | {"fragments"}
)

_KINDS = {
    "integer": "int", "smallint": "int", "bigint": "int",
    "double precision": "float", "real": "float", "numeric": "float",
    "character varying": "str", "text": "str", "character": "str",
    "date": "date", "timestamp without time zone": "timestamp", "boolean": "bool",
}


def get_spec(key: str) -> DictSpec:
    spec = DICTIONARIES.get(key)
    if spec is None:
        raise DictionaryError(404, {"code": "not_found", "message": f"Справочник «{key}» не найден"})
    return spec


def _rus(table: str, column: str) -> str:
    try:
        from utils.russian_names import russian_names_manager

        if not russian_names_manager.initialized:
            russian_names_manager.init_column_rus_name("gid")
        name = russian_names_manager.map_col.get((table.lower(), column.lower()))
        return name[0] if name and name[0] else column
    except Exception:  # noqa: BLE001 — подписи не критичны
        return column


async def _table(conn, spec: DictSpec) -> str:
    return await resolve_table(conn, spec.table, DICTIONARY_TABLES)


async def fields(conn, spec: DictSpec) -> list[dict[str, Any]]:
    """Редактируемые поля: колонки таблицы из каталога минус служебные."""
    table = await _table(conn, spec)
    rows = await conn.fetch(
        """SELECT column_name, data_type, character_maximum_length FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position""",
        table,
    )
    result = []
    for r in rows:
        column = str(r["column_name"])
        kind = _KINDS.get(str(r["data_type"]).lower())
        if column.lower() in EXCLUDED_COLUMNS or kind is None:
            continue
        if column.lower() == "fileid" and not spec.fragment_scoped:
            continue
        label = "Фрагмент" if column.lower() == "fileid" else spec.labels.get(column) or _rus(spec.table, column)
        item: dict[str, Any] = {
            "column": column, "kind": kind, "label": label,
            "max_length": r["character_maximum_length"],
            "required": column == spec.label_column or (column.lower() == "fileid"),
        }
        if column in spec.lookups:
            item["lookup"] = spec.lookups[column].table
        if column.lower() == "fileid":
            item["lookup"] = "fragments"
        result.append(item)
    return result


async def describe(conn, spec: DictSpec) -> dict[str, Any]:
    info = {
        "key": spec.key, "label": spec.label, "table": spec.table, "label_column": spec.label_column,
        "fragment_scoped": spec.fragment_scoped, "affects_calc": spec.affects_calc, "note": spec.note,
        "desktop": spec.desktop, "usages": [f"{u.table}.{u.column}" for u in spec.usages],
    }
    info["fields"] = await fields(conn, spec)
    lookups: dict[str, list[dict[str, Any]]] = {}
    for column, lk in spec.lookups.items():
        try:
            t = await resolve_table(conn, lk.table, DICTIONARY_TABLES)
            c = await resolve_column(conn, t, lk.label_column)
            lookups[column] = [dict(r) for r in await conn.fetch(
                f"SELECT id, {quote_ident(c)} AS name FROM {quote_ident(t)} ORDER BY id")]
        except UnknownIdentifierError:
            lookups[column] = []
    info["lookups"] = lookups
    return info


def coerce(kind: str, value: Any, max_length: Optional[int] = None) -> Any:
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if kind == "int":
        if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
            raise ValueError("ожидается целое число")
        try:
            return int(value) if isinstance(value, (int, float)) else int(str(value).strip())
        except ValueError as exc:
            raise ValueError("ожидается целое число") from exc
    if kind == "float":
        if isinstance(value, bool):
            raise ValueError("ожидается число")
        try:
            number = float(str(value).strip().replace(",", ".")) if isinstance(value, str) else float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("ожидается число") from exc
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError("ожидается конечное число")
        return number
    if kind == "bool":
        if isinstance(value, bool):
            return value
        if str(value).strip().lower() in ("1", "true", "да"):
            return True
        if str(value).strip().lower() in ("0", "false", "нет"):
            return False
        raise ValueError("ожидается да/нет")
    if kind in ("date", "timestamp"):
        if isinstance(value, datetime):
            return value if kind == "timestamp" else value.date()
        if isinstance(value, date):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                parsed = datetime.strptime(text[:10], fmt)
                return parsed if kind == "timestamp" else parsed.date()
            except ValueError:
                continue
        raise ValueError("ожидается дата ГГГГ-ММ-ДД")
    text = str(value).strip()
    if max_length and len(text) > int(max_length):
        raise ValueError(f"не длиннее {max_length} символов")
    return text


async def coerce_fields(conn, spec: DictSpec, raw: dict[str, Any], *, creating: bool) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DictionaryError(422, {"code": "bad_fields", "message": "fields — объект"})
    meta = {f["column"].lower(): f for f in await fields(conn, spec)}
    unknown = sorted(k for k in raw if str(k).lower() not in meta)
    if unknown:
        raise DictionaryError(422, {"code": "unknown_fields", "message": "Неизвестные поля",
                                    "unknown_fields": unknown})
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for key, value in raw.items():
        f = meta[str(key).lower()]
        try:
            values[f["column"]] = coerce(f["kind"], value, f["max_length"])
        except ValueError as exc:
            errors[str(key)] = str(exc)
    if creating:
        for column, default in spec.defaults.items():
            if column.lower() in meta:
                values.setdefault(meta[column.lower()]["column"], default)
    for f in meta.values():
        if not f["required"]:
            continue
        present = f["column"] in values
        if (creating or present) and values.get(f["column"]) is None:
            errors[f["column"]] = "обязательное поле"
    if errors:
        raise DictionaryError(422, {"code": "field_errors", "message": "Ошибки в полях", "field_errors": errors})
    return values


async def _check_unique(conn, spec: DictSpec, table: str, values: dict[str, Any], record_id: Optional[int]) -> None:
    if not spec.unique_label:
        return
    label_col = await resolve_column(conn, table, spec.label_column)
    if label_col not in values:
        return
    args: list[Any] = [values[label_col]]
    where = f"lower(trim({quote_ident(label_col)}::text)) = lower(trim($1::text))"
    if spec.fragment_scoped:
        current_file = values.get("fileid")
        if current_file is None and record_id is not None:
            current_file = await conn.fetchval(f"SELECT fileid FROM {quote_ident(table)} WHERE id = $1", record_id)
        args.append(current_file)
        where += f" AND fileid IS NOT DISTINCT FROM ${len(args)}"
    if record_id is not None:
        args.append(record_id)
        where += f" AND id <> ${len(args)}"
    other = await conn.fetchval(f"SELECT id FROM {quote_ident(table)} WHERE {where} LIMIT 1", *args)
    if other is not None:
        raise DictionaryError(409, {"code": "duplicate", "message": f"Запись «{values[label_col]}» уже есть"
                                    + (" в этом фрагменте" if spec.fragment_scoped else ""), "id": other})


async def _check_lookups(conn, spec: DictSpec, values: dict[str, Any]) -> None:
    checks = {**{c: lk.table for c, lk in spec.lookups.items()}}
    if spec.fragment_scoped:
        checks["fileid"] = "fragments"
    for column, lookup_table in checks.items():
        value = values.get(column)
        if value is None:
            continue
        t = await resolve_table(conn, lookup_table, DICTIONARY_TABLES)
        if not await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {quote_ident(t)} WHERE id = $1)", value):
            raise DictionaryError(422, {"code": "field_errors", "message": "Ошибки в полях",
                                        "field_errors": {column: f"нет записи {value} в {lookup_table}"}})


async def list_rows(conn, spec: DictSpec, *, q: Optional[str] = None, fragment_id: Optional[int] = None,
                    limit: int = 100, offset: int = 0) -> dict[str, Any]:
    table = await _table(conn, spec)
    label_col = await resolve_column(conn, table, spec.label_column)
    conditions: list[str] = []
    args: list[Any] = []
    if spec.fragment_scoped and fragment_id is not None:
        args.append(fragment_id)
        conditions.append(f"fileid = ${len(args)}")
    if q and q.strip():
        args.append(f"%{q.strip()}%")
        conditions.append(f"{quote_ident(label_col)}::text ILIKE ${len(args)}")
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    total = await conn.fetchval(f"SELECT count(*) FROM {quote_ident(table)}{where}", *args)
    order = spec.order_sql or f"{quote_ident(label_col)}, id"
    columns = ["id"] + [quote_ident(f["column"]) for f in await fields(conn, spec)]
    args += [max(1, min(int(limit), LIST_LIMIT_MAX)), max(0, int(offset))]
    rows = await conn.fetch(
        f"SELECT {', '.join(columns)} FROM {quote_ident(table)}{where} ORDER BY {order} "
        f"LIMIT ${len(args) - 1} OFFSET ${len(args)}", *args)
    return {"items": [_row(r) for r in rows], "total": total}


def _row(record) -> dict[str, Any]:
    out = {}
    for k, v in dict(record).items():
        out[k] = v.isoformat() if isinstance(v, (date, datetime)) else float(v) if hasattr(v, "is_finite") else v
    return out


async def get_row(conn, spec: DictSpec, record_id: int) -> dict[str, Any]:
    table = await _table(conn, spec)
    columns = ["id"] + [quote_ident(f["column"]) for f in await fields(conn, spec)]
    row = await conn.fetchrow(f"SELECT {', '.join(columns)} FROM {quote_ident(table)} WHERE id = $1", record_id)
    if row is None:
        raise DictionaryError(404, {"code": "not_found", "message": f"Запись {record_id} не найдена"})
    return _row(row)


async def usage(conn, spec: DictSpec, record_id: int, row: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Где используется запись (по списку ссылок спецификации; отсутствующие таблицы пропускаются)."""
    row = row or await get_row(conn, spec, record_id)
    by: list[dict[str, Any]] = []
    for u in spec.usages:
        try:
            t = await resolve_table(conn, u.table, DICTIONARY_TABLES)
            c = await resolve_column(conn, t, u.column)
        except UnknownIdentifierError:
            continue
        if u.match == "name":
            label = row.get(spec.label_column)
            if label is None:
                continue
            count = await conn.fetchval(
                f"SELECT count(*) FROM {quote_ident(t)} WHERE lower(trim({quote_ident(c)}::text)) = lower(trim($1))",
                str(label))
        else:
            count = await conn.fetchval(f"SELECT count(*) FROM {quote_ident(t)} WHERE {quote_ident(c)} = $1",
                                        record_id)
        if count:
            by.append({"table": t, "column": c, "label": u.label, "count": int(count)})
    return {"total": sum(b["count"] for b in by), "by": by}


async def create_row(conn, spec: DictSpec, raw: dict[str, Any]) -> dict[str, Any]:
    table = await _table(conn, spec)
    values = await coerce_fields(conn, spec, raw, creating=True)
    await _check_lookups(conn, spec, values)
    await _check_unique(conn, spec, table, values, None)
    columns = list(values)
    placeholders = ", ".join(f"${i + 1}" for i in range(len(columns)))
    new_id = await conn.fetchval(
        f"INSERT INTO {quote_ident(table)} ({', '.join(quote_ident(c) for c in columns)}) "
        f"VALUES ({placeholders}) RETURNING id", *values.values())
    return await get_row(conn, spec, int(new_id))


async def update_row(conn, spec: DictSpec, record_id: int, raw: dict[str, Any]) -> tuple[dict, dict]:
    table = await _table(conn, spec)
    before = await get_row(conn, spec, record_id)
    values = await coerce_fields(conn, spec, raw, creating=False)
    if not values:
        return before, before
    if spec.fragment_scoped and "fileid" in values and values["fileid"] != before.get("fileid"):
        used = await usage(conn, spec, record_id, before)
        if used["total"]:
            raise DictionaryError(409, {"code": "in_use", "message": "Нельзя перенести в другой фрагмент: "
                                        "запись используется", "usage": used})
    await _check_lookups(conn, spec, values)
    await _check_unique(conn, spec, table, values, record_id)
    sets = ", ".join(f"{quote_ident(c)} = ${i + 1}" for i, c in enumerate(values))
    await conn.execute(f"UPDATE {quote_ident(table)} SET {sets} WHERE id = ${len(values) + 1}",
                       *values.values(), record_id)
    return before, await get_row(conn, spec, record_id)


async def delete_row(conn, spec: DictSpec, record_id: int) -> dict[str, Any]:
    table = await _table(conn, spec)
    before = await get_row(conn, spec, record_id)
    used = await usage(conn, spec, record_id, before)
    if used["total"]:
        raise DictionaryError(409, {"code": "in_use",
                                    "message": f"Запись используется ({used['total']} ссылок) — удаление запрещено",
                                    "usage": used})
    await conn.execute(f"DELETE FROM {quote_ident(table)} WHERE id = $1", record_id)
    return before
