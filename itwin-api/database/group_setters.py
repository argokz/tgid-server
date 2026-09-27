"""Групповые установщики свойств (этап 9): «установить поле X = значение для набора объектов».

Эталон — десктоп: gid8 ``gidview/gidrSlot.cpp`` onSet* + ``set_line/set_line.cpp``
(setSomething/setValue/setMark*Value), gid6 ``set_obl.cpp`` OnSet*. Десктоп применяет значение
ко всем выделенным («Область» → «Выделить область») объектам; здесь набор задаётся списком id
(выделено на карте), фрагментом или фильтром (фрагмент + рамка карты + условия по полям).
Карта соответствия — ``web-itwin/docs/group-setters-parity.md``.

Безопасность:
- установщики, таблицы и колонки — только из ``SETTERS`` (allow-list в коде), имена сверяются с
  каталогом через ``sql_ident``; значения — только параметрами;
- dry-run считает объекты и строки, показывает «было → станет»;
- применение — одна транзакция; legacy-триггеры ``log_changes`` пишут построчный audit_log с
  ``tgid.current_group_id`` (если триггера нет — строки пишем сами), плюс сводная запись
  ``GROUP_SET`` от имени пользователя; отмена (``undo``) возвращает старые значения из audit_log
  той же группы, пропуская строки, изменённые после операции.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, replace
from datetime import date, datetime
from typing import Any, Optional

from database.sql_ident import quote_ident, resolve_column, resolve_table

MAX_OBJECTS = 50_000
SAMPLE_LIMIT = 200
OPTIONS_LIMIT = 200


class GroupSetterError(Exception):
    """Ошибка с HTTP-статусом (роутер превращает её в HTTPException)."""

    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Описание установщиков
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RefSpec:
    """Справочник значения. SQL-фрагменты (where/label_sql) — только константы кода."""

    table: str
    label_column: str = "name"
    fragment_scoped: bool = False  # у записей справочника есть fileid (десктоп: «выберите фрагмент»)
    where: Optional[str] = None
    label_sql: Optional[str] = None
    order_sql: Optional[str] = None
    columns: tuple[str, ...] = ()  # колонки строки справочника, которые пишутся в объект (диаметры)


@dataclass(frozen=True)
class Column:
    column: str
    source: str = "value"  # value | ref:<колонка справочника> | expr:<ключ EXPRESSIONS>


@dataclass(frozen=True)
class Write:
    table: str
    key: str  # колонка связи с объектом: nodeid / lineid / id
    columns: tuple[Column, ...]


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    base_table: str  # nodes | linesobj
    member_sql: Optional[str]  # доп. условие принадлежности (алиас b), константа кода
    name_sql: str


@dataclass(frozen=True)
class SetterSpec:
    key: str
    label: str
    group: str
    target: str
    kind: str  # ref | float | int | date | choice | computed
    writes: tuple[Write, ...]
    desktop: str
    ref: Optional[RefSpec] = None
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    choices: tuple[tuple[int, str], ...] = ()
    affects_calc: bool = False
    note: str = ""
    field_label: str = ""


_NODE_NAME = "COALESCE(NULLIF(trim({a}.nodename), ''), NULLIF(trim({a}.externalnodename), ''), '№' || {a}.id)"
_LINE_NAME = ("(SELECT concat_ws(' – ', " + _NODE_NAME.format(a="n1") + ", " + _NODE_NAME.format(a="n2") + ")"
              " FROM nodes n1, nodes n2 WHERE n1.id = b.nodeid1 AND n2.id = b.nodeid2)")

TARGETS: dict[str, Target] = {
    "consumers": Target(
        "consumers", "Потребители", "nodes",
        "(EXISTS (SELECT 1 FROM realconsumers r WHERE r.nodeid = b.id)"
        " OR EXISTS (SELECT 1 FROM generalizedconsumers g WHERE g.nodeid = b.id))",
        "COALESCE((SELECT r.name FROM realconsumers r WHERE r.nodeid = b.id LIMIT 1),"
        " (SELECT g.name FROM generalizedconsumers g WHERE g.nodeid = b.id LIMIT 1),"
        " " + _NODE_NAME.format(a="b") + ")",
    ),
    "pipes": Target(
        "pipes", "Участки теплопроводов", "linesobj",
        "EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = b.id)",
        _LINE_NAME,
    ),
    "lines": Target(
        "lines", "Линейные объекты (участки, арматура, насосы…)", "linesobj", None,
        _LINE_NAME,
    ),
    "nodes": Target("nodes", "Узлы", "nodes", None, _NODE_NAME.format(a="b")),
}

# Вычисляемые значения (алиас обновляемой таблицы — t). Только константы кода.
EXPRESSIONS: dict[str, str] = {
    # как topology.update_line_geometry: ST_Length в SRID 9998 (метры)
    "line_length": "(SELECT round(ST_Length(l.shape)::numeric, 2)::float8 FROM linesobj l"
                   " WHERE l.id = t.lineid AND l.shape IS NOT NULL)",
}

_RC, _GC, _HP = "realconsumers", "generalizedconsumers", "heatpipesections"


def _both(real: str, gen: Optional[str] = None) -> tuple[Write, ...]:
    """Реальные (TIP_PR) + обобщённые (TIP_PO) потребители, как setSomething + setValue."""
    return (
        Write(_RC, "nodeid", (Column(real),)),
        Write(_GC, "nodeid", (Column(gen or real),)),
    )


def _real(column: str) -> tuple[Write, ...]:
    return (Write(_RC, "nodeid", (Column(column),)),)


def _pipe(*columns: str) -> tuple[Write, ...]:
    return (Write(_HP, "lineid", tuple(Column(c) for c in columns)),)


_VARCOEF = RefSpec("varcoefficients", "kodkv", fragment_scoped=True)
_P, _U, _N, _S = "Потребители", "Участки теплопроводов", "Узлы", "Надписи"
_OPEN = "Потребители: открытая ГВС"
_SHOW_HIDE = ((0, "Показывать надписи"), (1, "Не показывать надписи"))

_SETTERS_LIST: tuple[SetterSpec, ...] = (
    # --- Потребители (gid8: «Область» → «Потребители») ---
    SetterSpec("responsible", "Установить ФИО техников", _P, "consumers", "ref", _real("responsibleid"),
               "gid8 aSetOtv / gid6 OnSetOtv", RefSpec("responsibles", where="statusid = 15"),
               field_label="Техник", note="Список техников — responsibles со statusid = 15 (как GID.lookup gid8)."),
    SetterSpec("calc_temperature", "Установить код расчётных температур", _P, "consumers", "ref",
               _both("calctemperatureid"), "gid8 aSetTr / gid6 OnSetTr",
               RefSpec("calctemperatures", "calctemperatureid", fragment_scoped=True),
               affects_calc=True, field_label="Код расчётных температур"),
    SetterSpec("spec_expend", "Установить код удельных расходов", _P, "consumers", "ref",
               _both("specexpendid"), "gid8 aSetUr / gid6 OnSetUr",
               RefSpec("specexpends", "specexpendid", fragment_scoped=True),
               affects_calc=True, field_label="Код удельных расходов"),
    SetterSpec("var_coeff_consumers", "Установить коэффициенты вариации по потребителям", _P, "consumers", "ref",
               _both("varcoeffid"), "gid8 aSetKvPt / gid6 OnSetKvPt", _VARCOEF,
               affects_calc=True, field_label="Группа Kv потребителя",
               note="Kv меняют требуемую нагрузку в расчёте (docs/acceptance-numeric.md)."),
    SetterSpec("mix_factor", "Установить коэффициент смешения элеватора", _P, "consumers", "float",
               _real("mixfactcoeff"), "gid8 aSetUf / gid6 OnSetUf", default=2.2, min_value=0, max_value=20,
               affects_calc=True, field_label="Коэффициент смешения"),
    SetterSpec("vol_ventilation", "Установить удельный объём системы вентиляции", _P, "consumers", "float",
               _both("volwatervs"), "gid8 aSetUdobVent / gid6 OnSetUdobVent", default=1.0, min_value=0,
               affects_calc=True, field_label="Уд. объём СВ"),
    SetterSpec("vol_heating", "Установить удельный объём системы отопления", _P, "consumers", "float",
               _both("volwaterhs"), "gid8 aSetUdobOt / gid6 OnSetUdobOt", default=1.0, min_value=0,
               affects_calc=True, field_label="Уд. объём СО"),
    SetterSpec("open_hour_coeff", "Коэф. часовой неравномерности (открытая ГВС)", _OPEN, "consumers", "float",
               _both("hourirregcoeff", "hourirregcoeffopen"), "gid8 aSetOpenKoef / gid6 OnSetOpenKoef",
               default=1.2, min_value=0, affects_calc=True, field_label="Коэф. часовой неравномерности"),
    SetterSpec("open_recirc_loss", "Расчётные теплопотери в рециркуляционном контуре ГВС", _OPEN, "consumers",
               "float", _both("circhlosopen", "avghlcompopen"), "gid8 aSetOpenRez / gid6 OnSetOpenRez",
               default=30.0, min_value=0, affects_calc=True, field_label="Теплопотери рециркуляции"),
    SetterSpec("open_recirc_temp", "Температура в рециркуляционном трубопроводе ГВС", _OPEN, "consumers",
               "float", _both("temprecircpipe", "temprecircpipeopen"), "gid8 aSetOpenRezT / gid6 OnSetOpenRezT",
               default=40.0, min_value=0, max_value=150, affects_calc=True, field_label="t рециркуляции"),
    SetterSpec("open_hw_temp", "Расчётная температура горячей воды", _OPEN, "consumers", "float",
               _both("calctemphwdo", "calctemphwdoopen"), "gid8 aSetOpenGvsT / gid6 OnSetOpenGvsT",
               default=60.0, min_value=0, max_value=150, affects_calc=True, field_label="t горячей воды"),
    SetterSpec("heat_point", "Установить тепловой пункт", _P, "consumers", "ref", _real("heatpointid"),
               "gid6 OnSetTp (в gid8 пункт закомментирован)", RefSpec("heatpoint"), field_label="Тепловой пункт"),
    SetterSpec("automation", "Автоматизация потребителей", _P, "consumers", "ref", _real("automdegid"),
               "gid6 OnSetAvtoOn/Off (в gid8 пустые обработчики)", RefSpec("automdegs", order_sql="ord, id"),
               affects_calc=True, field_label="Степень автоматизации"),
    SetterSpec("throttle_sign", "Признак записи диаметров шайб/сопел", _P, "consumers", "ref",
               _real("calcferdiametersignid"), "gid6 OnSetShaiba", RefSpec("calcferdiametersigns", order_sql="ord, id"),
               field_label="Признак записи шайб"),
    # --- Участки теплопроводов (heatpipesections по lineid) ---
    SetterSpec("diameter", "Установить диаметр (сортамент ГОСТ)", _U, "pipes", "ref",
               (Write(_HP, "lineid", (Column("diametercondit", "ref:diametr_usl"),
                                      Column("diameterexternal", "ref:diamvne"),
                                      Column("diameterinternal", "ref:diametr"),
                                      Column("wallthickness", "ref:tol"))),),
               "gid8 aSetDiams / gid6 OnSetDiams",
               RefSpec("standardtubes", where="stand IN ('ГОСТ', 'Стандарт', 'Россия')",
                       label_sql="concat('Ду ', diametr_usl, ' — ', diamvne, '×', tol, ' (dвн ', diametr, ')')",
                       order_sql="diametr_usl, diamvne, tol",
                       columns=("diametr_usl", "diamvne", "diametr", "tol")),
               affects_calc=True, field_label="Условный диаметр"),
    SetterSpec("local_losses_share", "Установить долю местных потерь", _U, "pipes", "float",
               _pipe("locallosesshare"), "gid8 aSetLosesShare / gid6 OnSetLosesShare", default=0.0,
               min_value=0, max_value=10, affects_calc=True, field_label="Доля местных потерь"),
    SetterSpec("work_hours", "Установить количество часов работы", _U, "pipes", "ref", _pipe("signnumwork"),
               "gid8 aSetKolChas / gid6 OnSetKolChas", RefSpec("signnumworks", order_sql="ord, id"),
               field_label="Часов работы в год"),
    SetterSpec("var_coeff_pipes", "Установить коэффициенты вариации по участкам", _U, "pipes", "ref",
               _pipe("varcoeffidflow", "varcoeffidret"), "gid8 aSetKvUt / gid6 OnSetKvUt", _VARCOEF,
               affects_calc=True, field_label="Группа Kv участка"),
    SetterSpec("heat_test_coeff", "Установить коэффициенты тепловых испытаний", _U, "pipes", "float",
               _pipe("heattestscoeff"), "gid8 aSetKti / gid6 OnSetKti", default=1.0, min_value=0, max_value=10,
               affects_calc=True, field_label="Коэф. тепловых испытаний"),
    SetterSpec("pipe_repair_type", "Установить признак ремонта", _U, "pipes", "ref", _pipe("piperemonttypeid"),
               "gid8 aSetPipeRemontType / gid6 OnSetRemontType", RefSpec("piperemonttypes", order_sql="ord, id"),
               field_label="Признак ремонта"),
    SetterSpec("tubing_type", "Установить тип прокладки", _U, "pipes", "ref", _pipe("tubingtypeid"),
               "gid8 aSetTubingType / gid6 OnSetTubingType", RefSpec("tubingtypes", order_sql="ord, id"),
               affects_calc=True, field_label="Тип прокладки"),
    SetterSpec("roughness", "Установить эквивалентную шероховатость", _U, "pipes", "float", _pipe("tuberoughness"),
               "gid8 aSetSher / gid6 OnSetSher", default=0.5, min_value=0, max_value=10,
               affects_calc=True, field_label="Шероховатость, мм"),
    SetterSpec("date_last_relay", "Установить дату последней перекладки", _U, "pipes", "date",
               _pipe("lasttransdate"), "gid6 OnSetDate1 (в gid8 пустой)", field_label="Дата перекладки"),
    SetterSpec("date_commissioning", "Установить дату первичного ввода в эксплуатацию", _U, "pipes", "date",
               _pipe("firstpicdatehp", "lasttransdate"), "gid6 OnSetDate2 (в gid8 пустой)",
               field_label="Дата ввода",
               note="Как gid6 setDate: вместе с датой ввода пишется и дата последней перекладки."),
    SetterSpec("date_planned_repair", "Установить дату планируемого ремонта", _U, "pipes", "date",
               _pipe("repairdateplantp"), "gid6 OnSetDate3 (в gid8 пустой)", field_label="Дата плана ремонта"),
    SetterSpec("length", "Установить длины по геометрии", _U, "pipes", "computed",
               (Write(_HP, "lineid", (Column("pipesectlength", "expr:line_length"),)),),
               "gid8 aSetLength / gid6 OnSetLength", affects_calc=True, field_label="Длина, м",
               note="Длина = ST_Length(linesobj.shape) в метрах (SRID 9998), как правка вершин; "
                    "участки без геометрии не меняются."),
    # --- Линейные объекты и узлы ---
    SetterSpec("organization", "Установить организации", "Линейные объекты", "lines", "ref",
               (Write("linesobj", "id", (Column("organizationid"),)),), "gid8 aSetOrg / gid6 OnSetOrg",
               RefSpec("organizations"), field_label="Организация-владелец",
               note="Как десктоп: пишется linesobj.organizationid (не heatpipesections)."),
    SetterSpec("line_labels", "Надписи линейных объектов", _S, "lines", "choice",
               (Write("linesobj", "id", (Column("displaysign"),)),), "gid8 aSetPodpOn/Off / gid6 OnSetPodpOn/Off",
               choices=_SHOW_HIDE, field_label="Надписи"),
    SetterSpec("scheme_code", "Установить код расчётной схемы", _N, "nodes", "ref",
               (Write("nodes", "id", (Column("externalcodeid"),)),), "gid8 aSetKodRs / gid6 OnSetKodRs",
               RefSpec("externalcodes", fragment_scoped=True, where="COALESCE(removed, 0) = 0"),
               affects_calc=True, field_label="Код расчётной схемы"),
    SetterSpec("node_labels", "Надписи узлов", _S, "nodes", "choice",
               (Write("nodes", "id", (Column("displaysign"),)),), "gid8 aSetPodpOn/Off / gid6 OnSetPodpOn/Off",
               choices=_SHOW_HIDE, field_label="Надписи"),
)

SETTERS: dict[str, SetterSpec] = {s.key: s for s in _SETTERS_LIST}

SETTER_TABLES: frozenset[str] = frozenset(
    {w.table for s in _SETTERS_LIST for w in s.writes}
    | {s.ref.table for s in _SETTERS_LIST if s.ref}
    | {t.base_table for t in TARGETS.values()}
)


def filter_fields(target: str) -> dict[str, SetterSpec]:
    """Поля фильтра объектов цели: значения тех же установщиков (кроме вычисляемых)."""
    return {s.key: s for s in _SETTERS_LIST if s.target == target and s.kind != "computed"}


def describe_setter(spec: SetterSpec) -> dict[str, Any]:
    return {
        "key": spec.key,
        "label": spec.label,
        "group": spec.group,
        "target": spec.target,
        "target_label": TARGETS[spec.target].label,
        "kind": spec.kind,
        "field_label": spec.field_label or spec.label,
        "default": spec.default,
        "min": spec.min_value,
        "max": spec.max_value,
        "choices": [{"value": v, "label": l} for v, l in spec.choices],
        "ref": {"table": spec.ref.table, "fragment_scoped": spec.ref.fragment_scoped} if spec.ref else None,
        "writes": [f"{w.table}.{c.column}" for w in spec.writes for c in w.columns],
        "desktop": spec.desktop,
        "affects_calc": spec.affects_calc,
        "note": spec.note,
    }


def describe_all() -> list[dict[str, Any]]:
    return [describe_setter(s) for s in _SETTERS_LIST]


def get_spec(key: str) -> SetterSpec:
    spec = SETTERS.get(key)
    if spec is None:
        raise GroupSetterError(404, {"code": "not_found", "message": f"Установщик «{key}» не найден"})
    return spec


# ---------------------------------------------------------------------------
# Идентификаторы и типы
# ---------------------------------------------------------------------------

_CAST = {
    "integer": "int4", "smallint": "int2", "bigint": "int8",
    "double precision": "float8", "real": "float4", "numeric": "numeric",
    "date": "date", "timestamp without time zone": "timestamp", "boolean": "bool",
    "character varying": "text", "text": "text", "character": "text",
}


async def _t(conn, name: str) -> str:
    return await resolve_table(conn, name, SETTER_TABLES)


async def _col(conn, table: str, column: str) -> str:
    return await resolve_column(conn, await _t(conn, table), column)


async def _column_cast(conn, table: str, column: str) -> str:
    data_type = await conn.fetchval(
        """SELECT data_type FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1 AND column_name = $2""",
        table, column,
    )
    return _CAST.get(str(data_type or "").lower(), "text")


# ---------------------------------------------------------------------------
# Значение
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError
    number = float(str(value).strip().replace(",", ".")) if isinstance(value, str) else float(value)
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError
    return number


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError
        return int(value)
    return int(str(value).strip())


def _to_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    raise ValueError


def coerce_setter_value(spec: SetterSpec, value: Any) -> Any:
    """Значение из JSON → тип установщика; ошибки — 422 с понятным текстом."""
    if spec.kind == "computed":
        return None
    if value is None or (isinstance(value, str) and not value.strip()):
        raise GroupSetterError(422, {"code": "value_required", "message": "Укажите значение"})
    try:
        if spec.kind == "float":
            number = _to_float(value)
            if spec.min_value is not None and number < spec.min_value:
                raise GroupSetterError(422, {"code": "out_of_range", "message": f"Значение меньше {spec.min_value:g}"})
            if spec.max_value is not None and number > spec.max_value:
                raise GroupSetterError(422, {"code": "out_of_range", "message": f"Значение больше {spec.max_value:g}"})
            return number
        if spec.kind == "date":
            return _to_date(value)
        number = _to_int(value)
    except GroupSetterError:
        raise
    except (TypeError, ValueError):
        expected = {"float": "число", "date": "дата ГГГГ-ММ-ДД"}.get(spec.kind, "целое число")
        raise GroupSetterError(422, {"code": "bad_value", "message": f"Ожидается {expected}"})
    if spec.kind == "choice" and number not in {v for v, _ in spec.choices}:
        raise GroupSetterError(422, {"code": "bad_value", "message": "Недопустимое значение"})
    return number


def _ref_label_sql(ref: RefSpec, label_column: str) -> str:
    return ref.label_sql or f"{quote_ident(label_column)}::text"


async def load_ref_row(conn, spec: SetterSpec, value: int) -> dict[str, Any]:
    """Строка справочника для значения; нет такой — 422."""
    ref = spec.ref
    assert ref is not None
    table = await _t(conn, ref.table)
    label_col = await resolve_column(conn, table, ref.label_column)
    extra = {c: await resolve_column(conn, table, c) for c in ref.columns}
    has_file = ref.fragment_scoped and await _has_column(conn, table, "fileid")
    select = ["id", f"{_ref_label_sql(ref, label_col)} AS label"]
    select += [f"{quote_ident(actual)} AS c{i}" for i, actual in enumerate(extra.values())]
    if has_file:
        select.append("fileid")
    where = "id = $1" + (f" AND ({ref.where})" if ref.where else "")
    row = await conn.fetchrow(f"SELECT {', '.join(select)} FROM {quote_ident(table)} WHERE {where}", value)
    if row is None:
        raise GroupSetterError(422, {"code": "bad_value",
                                     "message": f"Значение {value} не найдено в справочнике {ref.table}"})
    result = {"id": row["id"], "label": row["label"], "fileid": row["fileid"] if has_file else None}
    for i, c in enumerate(extra):
        result[c] = row[f"c{i}"]
    return result


async def _has_column(conn, table: str, column: str) -> bool:
    try:
        await resolve_column(conn, table, column)
        return True
    except Exception:  # noqa: BLE001
        return False


async def list_options(conn, spec: SetterSpec, *, q: Optional[str] = None,
                       fragment_ids: Optional[list[int]] = None, limit: int = OPTIONS_LIMIT) -> dict[str, Any]:
    """Значения справочника для выбора (поиск по подписи, фрагмент — для справочников с fileid)."""
    if spec.kind == "choice":
        return {"items": [{"id": v, "label": l} for v, l in spec.choices], "total": len(spec.choices)}
    if spec.kind != "ref" or spec.ref is None:
        return {"items": [], "total": 0}
    ref = spec.ref
    table = await _t(conn, ref.table)
    label_col = await resolve_column(conn, table, ref.label_column)
    label = _ref_label_sql(ref, label_col)
    has_file = ref.fragment_scoped and await _has_column(conn, table, "fileid")
    conditions: list[str] = []
    args: list[Any] = []
    if ref.where:
        conditions.append(f"({ref.where})")
    if has_file and fragment_ids:
        args.append(list(fragment_ids))
        conditions.append(f"fileid = ANY(${len(args)}::int[])")
    if q and q.strip():
        args.append(f"%{q.strip()}%")
        conditions.append(f"({label}) ILIKE ${len(args)}")
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    order = ref.order_sql or f"{label}, id"
    total = await conn.fetchval(f"SELECT count(*) FROM {quote_ident(table)}{where}", *args)
    args.append(max(1, min(int(limit), 1000)))
    file_sel = ", fileid" if has_file else ""
    rows = await conn.fetch(
        f"SELECT id, {label} AS label{file_sel} FROM {quote_ident(table)}{where} ORDER BY {order} LIMIT ${len(args)}",
        *args,
    )
    return {"items": [{"id": r["id"], "label": r["label"], **({"fileid": r["fileid"]} if has_file else {})}
                      for r in rows],
            "total": total}


# ---------------------------------------------------------------------------
# Набор объектов
# ---------------------------------------------------------------------------

def normalize_ids(values: Any, *, field_name: str = "ids") -> list[int]:
    if not isinstance(values, (list, tuple)):
        raise GroupSetterError(422, {"code": "bad_selection", "message": f"{field_name}: ожидается список id"})
    out: list[int] = []
    seen: set[int] = set()
    for v in values:
        if isinstance(v, bool):
            raise GroupSetterError(422, {"code": "bad_selection", "message": f"{field_name}: неверный id {v!r}"})
        try:
            i = int(v)
        except (TypeError, ValueError):
            raise GroupSetterError(422, {"code": "bad_selection", "message": f"{field_name}: неверный id {v!r}"})
        if i <= 0:
            raise GroupSetterError(422, {"code": "bad_selection", "message": f"{field_name}: неверный id {v!r}"})
        if i not in seen:
            seen.add(i)
            out.append(i)
    if len(out) > MAX_OBJECTS:
        raise GroupSetterError(422, {"code": "too_many", "message": f"Не более {MAX_OBJECTS} объектов за операцию"})
    return out


@dataclass
class Selection:
    mode: str  # ids | fragment | filter
    ids: list[int] = field(default_factory=list)
    fragment_ids: list[int] = field(default_factory=list)
    bbox: Optional[tuple[float, float, float, float]] = None
    where: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        data: dict[str, Any] = {"mode": self.mode}
        if self.mode == "ids":
            data["ids_count"] = len(self.ids)
            data["ids"] = self.ids[:50]
        if self.fragment_ids:
            data["fragment_ids"] = self.fragment_ids
        if self.bbox:
            data["bbox"] = list(self.bbox)
        if self.where:
            data["where"] = self.where
        return data


def parse_selection(raw: Any) -> Selection:
    if not isinstance(raw, dict):
        raise GroupSetterError(422, {"code": "bad_selection", "message": "Не задан набор объектов"})
    mode = raw.get("mode")
    if mode not in ("ids", "fragment", "filter"):
        raise GroupSetterError(422, {"code": "bad_selection", "message": "mode: ids | fragment | filter"})
    sel = Selection(mode=mode)
    if raw.get("fragment_ids"):
        sel.fragment_ids = normalize_ids(raw.get("fragment_ids"), field_name="fragment_ids")
    if mode == "ids":
        sel.ids = normalize_ids(raw.get("ids") or [], field_name="ids")
        if not sel.ids:
            raise GroupSetterError(422, {"code": "bad_selection", "message": "Не выбрано ни одного объекта"})
    elif mode == "fragment":
        if not sel.fragment_ids:
            raise GroupSetterError(422, {"code": "bad_selection", "message": "Не выбран фрагмент"})
    else:
        bbox = raw.get("bbox")
        if bbox is not None:
            try:
                x1, y1, x2, y2 = (float(v) for v in bbox)
            except (TypeError, ValueError):
                raise GroupSetterError(422, {"code": "bad_selection", "message": "bbox: [xmin, ymin, xmax, ymax]"})
            if not (-180 <= x1 < x2 <= 180 and -90 <= y1 < y2 <= 90):
                raise GroupSetterError(422, {"code": "bad_selection", "message": "bbox вне допустимых координат"})
            sel.bbox = (x1, y1, x2, y2)
        where = raw.get("where") or []
        if not isinstance(where, list):
            raise GroupSetterError(422, {"code": "bad_selection", "message": "where: список условий"})
        for cond in where[:10]:
            if not isinstance(cond, dict) or not isinstance(cond.get("field"), str):
                raise GroupSetterError(422, {"code": "bad_selection", "message": "Условие фильтра без поля"})
            op = cond.get("op", "eq")
            if op not in ("eq", "null", "not_null"):
                raise GroupSetterError(422, {"code": "bad_selection", "message": "op: eq | null | not_null"})
            sel.where.append({"field": cond["field"], "op": op, "value": cond.get("value")})
        if not (sel.fragment_ids or sel.bbox or sel.where):
            # десктоп всегда работает с выделенной областью; «вся база» из веба не допускается
            raise GroupSetterError(422, {"code": "bad_selection",
                                         "message": "Фильтр должен содержать фрагмент, рамку карты или условие"})
    return sel


def _filter_spec(spec: SetterSpec) -> SetterSpec:
    """Тип значения условия фильтра: диаметр — число (первая колонка), без границ установщика."""
    if spec.kind == "ref" and spec.ref and spec.ref.columns:
        return replace(spec, kind="float", min_value=None, max_value=None)
    if spec.kind == "float":
        return replace(spec, min_value=None, max_value=None)
    return spec


async def _condition_sql(conn, target: str, cond: dict[str, Any], args: list[Any]) -> str:
    fields = filter_fields(target)
    spec = fields.get(cond["field"])
    if spec is None:
        raise GroupSetterError(422, {"code": "bad_selection",
                                     "message": f"Поле фильтра «{cond['field']}» недоступно для этой цели"})
    parts = []
    value_param = None
    if cond["op"] == "eq":
        args.append(coerce_setter_value(_filter_spec(spec), cond.get("value")))
        value_param = f"${len(args)}"
    for write in spec.writes:
        table = await _t(conn, write.table)
        key = await resolve_column(conn, table, write.key)
        column = await resolve_column(conn, table, write.columns[0].column)
        if cond["op"] == "eq":
            cast = await _column_cast(conn, table, column)
            test = f"f.{quote_ident(column)} = {value_param}::{cast}"
        elif cond["op"] == "null":
            test = f"f.{quote_ident(column)} IS NULL"
        else:
            test = f"f.{quote_ident(column)} IS NOT NULL"
        parts.append(f"EXISTS (SELECT 1 FROM {quote_ident(table)} f WHERE f.{quote_ident(key)} = b.id AND {test})")
    return "(" + " OR ".join(parts) + ")"


async def resolve_objects(conn, spec: SetterSpec, sel: Selection) -> dict[str, Any]:
    """id объектов цели по набору; для mode=ids — ещё и не найденные/чужие id."""
    target = TARGETS[spec.target]
    base = await _t(conn, target.base_table)
    conditions = ["COALESCE(b.removed, 0) = 0"]
    if target.member_sql:
        conditions.append(target.member_sql)
    args: list[Any] = []
    if sel.mode == "ids":
        args.append(sel.ids)
        conditions.append(f"b.id = ANY(${len(args)}::int[])")
    if sel.fragment_ids:
        args.append(sel.fragment_ids)
        conditions.append(f"b.fileid = ANY(${len(args)}::int[])")
    if sel.bbox:
        srid = int(await conn.fetchval("SELECT Find_SRID('public', $1, 'shape')", base) or 4326)
        args.extend(sel.bbox)
        n = len(args)
        conditions.append(
            f"b.shape IS NOT NULL AND ST_Intersects(b.shape, ST_Transform("
            f"ST_MakeEnvelope(${n - 3}::float8, ${n - 2}::float8, ${n - 1}::float8, ${n}::float8, 4326), {srid}))"
        )
    for cond in sel.where:
        conditions.append(await _condition_sql(conn, spec.target, cond, args))
    args.append(MAX_OBJECTS + 1)
    rows = await conn.fetch(
        f"SELECT b.id FROM {quote_ident(base)} b WHERE {' AND '.join(conditions)} ORDER BY b.id LIMIT ${len(args)}",
        *args,
    )
    ids = [int(r["id"]) for r in rows]
    if len(ids) > MAX_OBJECTS:
        raise GroupSetterError(422, {"code": "too_many",
                                     "message": f"В наборе больше {MAX_OBJECTS} объектов — сузьте выбор"})
    missing = sorted(set(sel.ids) - set(ids)) if sel.mode == "ids" else []
    return {"ids": ids, "missing_ids": missing}


# ---------------------------------------------------------------------------
# Dry-run и применение
# ---------------------------------------------------------------------------

@dataclass
class _TablePlan:
    table: str
    key: str
    columns: list[str]
    new_sql: list[str]
    guard_sql: list[str]
    args: list[Any]  # $1 — id объектов, дальше — значения


async def _plans(conn, spec: SetterSpec, value: Any, ref_row: Optional[dict[str, Any]]) -> list[_TablePlan]:
    plans = []
    for write in spec.writes:
        table = await _t(conn, write.table)
        key = await resolve_column(conn, table, write.key)
        plan = _TablePlan(table, key, [], [], [], [None])
        for col in write.columns:
            column = await resolve_column(conn, table, col.column)
            cast = await _column_cast(conn, table, column)
            if col.source == "value":
                plan.args.append(value)
                new = f"${len(plan.args)}::{cast}"
            elif col.source.startswith("ref:"):
                assert ref_row is not None
                plan.args.append(ref_row[col.source[4:]])
                new = f"${len(plan.args)}::{cast}"
            elif col.source.startswith("expr:"):
                new = EXPRESSIONS[col.source[5:]]
                plan.guard_sql.append(f"{new} IS NOT NULL")
            else:  # pragma: no cover - ошибка описания
                raise ValueError(col.source)
            plan.columns.append(column)
            plan.new_sql.append(new)
        plans.append(plan)
    return plans


def _changed_sql(plan: _TablePlan) -> str:
    return "(" + " OR ".join(f"t.{quote_ident(c)} IS DISTINCT FROM {n}"
                             for c, n in zip(plan.columns, plan.new_sql)) + ")"


def _where_sql(plan: _TablePlan) -> str:
    return " AND ".join([f"t.{quote_ident(plan.key)} = ANY($1::int[])", *plan.guard_sql])


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if hasattr(value, "is_finite"):  # Decimal
        return float(value)
    return value


async def _object_names(conn, spec: SetterSpec, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    target = TARGETS[spec.target]
    base = await _t(conn, target.base_table)
    rows = await conn.fetch(
        f"SELECT b.id, {target.name_sql} AS name FROM {quote_ident(base)} b WHERE b.id = ANY($1::int[])", ids)
    return {int(r["id"]): r["name"] for r in rows}


async def _prepare(conn, spec: SetterSpec, raw_value: Any, raw_selection: Any):
    selection = parse_selection(raw_selection)
    value = coerce_setter_value(spec, raw_value)
    ref_row = await load_ref_row(conn, spec, value) if spec.kind == "ref" else None
    objects = await resolve_objects(conn, spec, selection)
    plans = await _plans(conn, spec, value, ref_row)
    for plan in plans:
        plan.args[0] = objects["ids"]
    return selection, value, ref_row, objects, plans


async def _warnings(conn, spec: SetterSpec, ref_row: Optional[dict[str, Any]], ids: list[int]) -> list[str]:
    warnings: list[str] = []
    if spec.affects_calc:
        warnings.append("Поле используется в гидравлическом расчёте — после изменения пересчитайте режим.")
    if ref_row and ref_row.get("fileid") is not None and ids:
        base = await _t(conn, TARGETS[spec.target].base_table)
        other = await conn.fetchval(
            f"SELECT count(*) FROM {quote_ident(base)} b WHERE b.id = ANY($1::int[]) "
            f"AND b.fileid IS DISTINCT FROM $2::int", ids, ref_row["fileid"])
        if other:
            warnings.append(f"{other} объектов не из фрагмента записи справочника (fileid {ref_row['fileid']}); "
                            "десктоп предлагает только записи своего фрагмента.")
    return warnings


async def preview(conn, spec: SetterSpec, raw_value: Any, raw_selection: Any,
                  *, sample_limit: int = SAMPLE_LIMIT) -> dict[str, Any]:
    """Dry-run: сколько объектов и строк изменится, образцы «было → станет»."""
    prepared = await _prepare(conn, spec, raw_value, raw_selection)
    return await _report(conn, spec, prepared, sample_limit)


async def _report(conn, spec: SetterSpec, prepared, sample_limit: int) -> dict[str, Any]:
    selection, value, ref_row, objects, plans = prepared
    by_table: dict[str, dict[str, int]] = {}
    sample: list[dict[str, Any]] = []
    changes_total = 0
    for plan in plans:
        changed = _changed_sql(plan)
        counts = await conn.fetchrow(
            f"SELECT count(*) AS rows, count(*) FILTER (WHERE {changed}) AS changes "
            f"FROM {quote_ident(plan.table)} t WHERE {_where_sql(plan)}", *plan.args)
        rows_count, changes = int(counts["rows"] or 0), int(counts["changes"] or 0)
        by_table[plan.table] = {"rows": rows_count, "changes": changes}
        changes_total += changes
        room = sample_limit - len(sample)
        if room > 0 and changes:
            select = ", ".join(
                f"t.{quote_ident(c)} AS o{i}, {n} AS n{i}" for i, (c, n) in enumerate(zip(plan.columns, plan.new_sql)))
            rows = await conn.fetch(
                f"SELECT t.id AS row_id, t.{quote_ident(plan.key)} AS object_id, {select} "
                f"FROM {quote_ident(plan.table)} t WHERE {_where_sql(plan)} AND {changed} "
                f"ORDER BY t.{quote_ident(plan.key)}, t.id LIMIT {int(room)}", *plan.args)
            for r in rows:
                sample.append({
                    "table": plan.table, "row_id": r["row_id"], "object_id": r["object_id"],
                    "old": {c: _jsonable(r[f"o{i}"]) for i, c in enumerate(plan.columns)},
                    "new": {c: _jsonable(r[f"n{i}"]) for i, c in enumerate(plan.columns)},
                })
    names = await _object_names(conn, spec, sorted({s["object_id"] for s in sample}))
    for s in sample:
        s["name"] = names.get(s["object_id"])
    return {
        "setter": spec.key,
        "label": spec.label,
        "value": _jsonable(value),
        "value_label": ref_row["label"] if ref_row else dict(spec.choices).get(value) if spec.choices else None,
        "selection": selection.summary(),
        "objects": len(objects["ids"]),
        "missing_ids": objects["missing_ids"],
        "changes": changes_total,
        "by_table": by_table,
        "sample": sample,
        "sample_truncated": changes_total > len(sample),
        "warnings": await _warnings(conn, spec, ref_row, objects["ids"]),
    }


async def _has_audit_trigger(conn, table: str) -> bool:
    return bool(await conn.fetchval(
        """SELECT EXISTS (
               SELECT 1 FROM pg_trigger tg JOIN pg_proc p ON p.oid = tg.tgfoid
                WHERE tg.tgrelid = to_regclass('public.' || quote_ident($1))
                  AND NOT tg.tgisinternal AND tg.tgenabled <> 'D' AND p.proname = 'log_changes')""",
        table,
    ))


async def apply(conn, spec: SetterSpec, raw_value: Any, raw_selection: Any, *, actor: str,
                expected_changes: Optional[int] = None, audit_row=None) -> dict[str, Any]:
    """Применение в транзакции вызывающего. audit_row(conn, **kw) — запись строки аудита от API."""
    prepared = await _prepare(conn, spec, raw_value, raw_selection)
    report = await _report(conn, spec, prepared, 0)
    if expected_changes is not None and expected_changes != report["changes"]:
        raise GroupSetterError(409, {"code": "stale_preview",
                                     "message": f"Данные изменились после предпросмотра: изменится "
                                                f"{report['changes']} строк вместо {expected_changes}. "
                                                "Повторите предпросмотр.",
                                     "changes": report["changes"]})
    group_id = str(uuid.uuid4())
    plans = prepared[4]
    # legacy-триггеры log_changes пишут строки аудита с этой группой
    await conn.execute("SELECT set_config('tgid.current_group_id', $1, true)", group_id)
    applied: dict[str, int] = {}
    for plan in plans:
        changed = _changed_sql(plan)
        where = f"{_where_sql(plan)} AND {changed}"
        own_audit = audit_row is not None and not await _has_audit_trigger(conn, plan.table)
        before: list[Any] = []
        if own_audit:
            cols = ", ".join(f"t.{quote_ident(c)} AS o{i}" for i, c in enumerate(plan.columns))
            before = await conn.fetch(
                f"SELECT t.id AS row_id, t.{quote_ident(plan.key)} AS object_id, {cols} "
                f"FROM {quote_ident(plan.table)} t WHERE {where}", *plan.args)
        sets = ", ".join(f"{quote_ident(c)} = {n}" for c, n in zip(plan.columns, plan.new_sql))
        returning = ", ".join(f"t.{quote_ident(c)} AS n{i}" for i, c in enumerate(plan.columns))
        rows = await conn.fetch(
            f"UPDATE {quote_ident(plan.table)} AS t SET {sets} WHERE {where} RETURNING t.id AS row_id, {returning}",
            *plan.args)
        applied[plan.table] = len(rows)
        if own_audit:
            new_by_id = {r["row_id"]: r for r in rows}
            for r in before:
                new = new_by_id.get(r["row_id"])
                await audit_row(
                    conn, operation="UPDATE", table=plan.table, record_id=r["row_id"],
                    old={c: _jsonable(r[f"o{i}"]) for i, c in enumerate(plan.columns)},
                    new={c: _jsonable(new[f"n{i}"]) if new else None for i, c in enumerate(plan.columns)},
                    group=group_id,
                )
    summary = {
        "setter": spec.key, "label": spec.label, "value": report["value"], "value_label": report["value_label"],
        "selection": report["selection"], "objects": report["objects"], "applied": applied,
        "columns": {w.table: [c.column for c in w.columns] for w in spec.writes},
    }
    if audit_row is not None:
        await audit_row(conn, operation="GROUP_SET", table=spec.writes[0].table, record_id=None,
                        old=None, new=summary, group=group_id)
    report.pop("sample", None)
    report.pop("sample_truncated", None)
    return {**report, "applied": applied, "changed": sum(applied.values()), "change_group_id": group_id}


# ---------------------------------------------------------------------------
# Отмена операции по audit_log
# ---------------------------------------------------------------------------

def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


async def undo(conn, change_group_id: str, *, actor: str, dry_run: bool = True, audit_row=None) -> dict[str, Any]:
    """Возвращает значения, записанные операцией GROUP_SET, из audit_log той же группы.

    Строки, которые после операции успели изменить (текущее значение ≠ записанному), не трогаются
    и возвращаются в ``conflicts``.
    """
    try:
        group = str(uuid.UUID(str(change_group_id)))
    except ValueError:
        raise GroupSetterError(422, {"code": "bad_group", "message": "change_group_id — UUID"})
    summary_row = await conn.fetchrow(
        "SELECT new_data FROM audit_log WHERE change_group_id = $1::uuid AND operation = 'GROUP_SET' "
        "ORDER BY log_id DESC LIMIT 1", group)
    if summary_row is None:
        raise GroupSetterError(404, {"code": "not_found", "message": "Групповая операция не найдена"})
    summary = _as_dict(summary_row["new_data"])
    spec = get_spec(str(summary.get("setter")))
    undone_already = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM audit_log WHERE operation = 'GROUP_UNDO' "
        "AND new_data->>'undo_of' = $1)", group)
    result: dict[str, Any] = {"setter": spec.key, "label": spec.label, "change_group_id": group,
                              "by_table": {}, "conflicts": [], "restorable": 0,
                              "already_undone": bool(undone_already), "dry_run": dry_run}
    undo_group = str(uuid.uuid4())
    if not dry_run:
        if undone_already:
            raise GroupSetterError(409, {"code": "already_undone", "message": "Операция уже отменена"})
        await conn.execute("SELECT set_config('tgid.current_group_id', $1, true)", undo_group)
    for write in spec.writes:
        table = await _t(conn, write.table)
        columns = [await resolve_column(conn, table, c.column) for c in write.columns]
        casts = [await _column_cast(conn, table, c) for c in columns]
        audit = ("SELECT DISTINCT ON (record_id) record_id, old_data, new_data FROM audit_log "
                 "WHERE change_group_id = $1::uuid AND table_name = $2 AND operation = 'UPDATE' "
                 "ORDER BY record_id, log_id")
        conflict = " OR ".join(
            f"t.{quote_ident(c)} IS DISTINCT FROM (a.new_data->>'{c}')::{k}" for c, k in zip(columns, casts))
        rows = await conn.fetch(
            f"SELECT t.id AS row_id, ({conflict}) AS conflict FROM {quote_ident(table)} t "
            f"JOIN ({audit}) a ON a.record_id = t.id", group, table)
        ok_ids = [r["row_id"] for r in rows if not r["conflict"]]
        bad_ids = [r["row_id"] for r in rows if r["conflict"]]
        result["by_table"][table] = {"rows": len(rows), "restorable": len(ok_ids), "conflicts": len(bad_ids)}
        result["restorable"] += len(ok_ids)
        result["conflicts"] += [{"table": table, "row_id": i} for i in bad_ids[:200]]
        if dry_run or not ok_ids:
            continue
        sets = ", ".join(f"{quote_ident(c)} = (a.old_data->>'{c}')::{k}" for c, k in zip(columns, casts))
        await conn.execute(
            f"UPDATE {quote_ident(table)} AS t SET {sets} FROM ({audit}) a "
            f"WHERE a.record_id = t.id AND t.id = ANY($3::int[])", group, table, ok_ids)
    if not dry_run:
        has_flag = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'audit_log' AND column_name = 'is_rolled_back')")
        if has_flag:
            await conn.execute("UPDATE audit_log SET is_rolled_back = TRUE WHERE change_group_id = $1::uuid", group)
        if audit_row is not None:
            await audit_row(conn, operation="GROUP_UNDO", table=spec.writes[0].table, record_id=None, old=None,
                            new={"undo_of": group, "setter": spec.key, "restored": result["restorable"],
                                 "conflicts": len(result["conflicts"])}, group=undo_group)
        result["undo_group_id"] = undo_group
    return result
