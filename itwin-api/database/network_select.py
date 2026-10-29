"""Выборка объектов сети по условиям (п. 10 фазы 1: «вопрос на естественном языке → выборка»).

Запрос — структура SelectSpec, а не SQL: что выбрать (участки или узлы), условия по полям из белого
списка (паспорт, последний гидравлический расчёт фрагмента, износ, теплопотери, карточка узла),
«в N м от узла или точки», «в видимой области», фрагменты, порядок и предел. Из неё сервер сам
собирает параметризованный SQL и человекочитаемое описание запроса — его веб показывает рядом с
результатом, а помощник ИИ (ai/tools.py) и MCP заполняют ту же структуру из фразы пользователя.

Только чтение; таблицы десктопа не меняются. Время запроса ограничено (statement_timeout).
"""
from __future__ import annotations

import json
import math
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field

from database.net_srid import line_inner_sql, net_srid
from database.ogc_features import GC_LOAD, RC_LOAD
from database.thematic import THEMES, source_run
from database.ut_out_columns import UT_SIGN_SUPPLY

MAX_LIMIT = 5000
DEFAULT_LIMIT = 1000
MAX_CONDITIONS = 8
MAX_NEAR_M = 5000
MAX_FRAGMENTS = 500
STATEMENT_TIMEOUT = "20s"
# одновременных выборок: на процесс API (пул соединений — 20) и на пользователя
MAX_CONCURRENT = 4
MAX_CONCURRENT_PER_USER = 2
INT32_MAX = 2**31 - 1
COORD_DIGITS = 6
M_PER_DEG = 111_320.0


class SelectError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# --- поля -----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Field_:
    key: str
    label: str
    kind: str                # number | category | text
    sql: str                 # выражение над алиасами запроса цели
    units: str = ""
    source: str = "passport"  # passport | calc | wear | heat_losses | node
    digits: int = 1
    # справочник категорий: (таблица, колонка подписи) или фиксированный список (значение, подпись)
    ref: Optional[tuple[str, str]] = None
    choices: tuple[tuple[str, str], ...] = ()
    hint: str = ""


CARD_TYPES: tuple[tuple[str, str], ...] = (
    ("PR", "Потребитель"), ("PO", "Обобщённый потребитель"), ("IS", "Источник тепла"),
    ("HS", "Насосная станция"), ("US", "Узел"),
)

_LINE_FIELDS: dict[str, Field_] = {f.key: f for f in (
    *(Field_(t.key, t.label, t.kind, f"({t.value_sql})", t.units, t.source, t.digits, t.ref, hint=t.hint)
      for t in THEMES.values()),
    Field_("length", "Длина по паспорту", "number", "h.pipesectlength", "м", digits=1),
    Field_("depth", "Глубина заложения", "number", "h.pipelinelayingdepth", "м", digits=2),
    Field_("damages", "Число повреждений", "number", "h.damagenum", digits=0,
           hint="Из паспорта участка (damageNum)"),
)}

# Тип узла по карточке (как node_types.py: PR, PO, IS, HS; остальное — простой узел) и нагрузка потребителей
CONS_JOIN = f"""
      LEFT JOIN (SELECT nodeid, SUM(load) AS load, MIN(k) AS k FROM (
                   SELECT rc.nodeid, ({RC_LOAD})::float AS load, 1 AS k FROM realconsumers rc
                   UNION ALL
                   SELECT gc.nodeid, ({GC_LOAD})::float AS load, 2 AS k FROM generalizedconsumers gc) x
                 GROUP BY nodeid) cons ON cons.nodeid = n.id
      LEFT JOIN (SELECT DISTINCT nodeid FROM heatsources) hs ON hs.nodeid = n.id
      LEFT JOIN (SELECT DISTINCT nodeid FROM pumpstations) ps ON ps.nodeid = n.id"""
CARD_SQL = ("CASE WHEN cons.k = 1 THEN 'PR' WHEN cons.k = 2 THEN 'PO' WHEN hs.nodeid IS NOT NULL THEN 'IS'"
            " WHEN ps.nodeid IS NOT NULL THEN 'HS' ELSE 'US' END")

_NODE_FIELDS: dict[str, Field_] = {f.key: f for f in (
    Field_("card_type", "Тип узла (карточка)", "category", CARD_SQL, source="node", choices=CARD_TYPES,
           hint="Потребитель, обобщённый потребитель, источник, насосная или простой узел"),
    Field_("node_type", "Вид узла", "category", "n.nodetypeid", source="node", ref=("nodetypes", "name"),
           hint="Камера, павильон, ввод в здание… (справочник nodetypes)"),
    Field_("name", "Имя узла", "text", "n.externalnodename", source="node"),
    Field_("load", "Нагрузка потребителя", "number", "cons.load", "Гкал/ч", source="node", digits=3,
           hint="Сумма расчётных нагрузок реальных и обобщённых потребителей узла"),
)}

TARGETS = {"lines": ("Участки", _LINE_FIELDS), "nodes": ("Узлы", _NODE_FIELDS)}

OPS_BY_KIND = {
    "number": ("lt", "le", "gt", "ge", "eq", "ne", "between", "is_null", "not_null"),
    "category": ("in", "not_in", "is_null", "not_null"),
    "text": ("contains", "eq", "is_null", "not_null"),
}
OP_LABELS = {"lt": "<", "le": "≤", "gt": ">", "ge": "≥", "eq": "=", "ne": "≠", "between": "от … до",
             "in": "из", "not_in": "кроме", "is_null": "не задано", "not_null": "задано",
             "contains": "содержит"}
_OP_SQL = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "=", "ne": "<>"}


# --- запрос ---------------------------------------------------------------------------------

class Condition(BaseModel):
    field: str = Field(..., max_length=40)
    op: Literal["lt", "le", "gt", "ge", "eq", "ne", "between", "in", "not_in", "is_null", "not_null",
                "contains"]
    value: Optional[Union[float, str]] = None
    value2: Optional[float] = None
    values: list[Union[int, str]] = Field(default_factory=list, max_length=50)


class Near(BaseModel):
    """Центр «в N м от»: узел по id, узел по имени (лучшее совпадение) или точка WGS 84."""
    node_id: Optional[int] = Field(None, ge=1, le=INT32_MAX)
    node_name: Optional[str] = Field(None, max_length=100)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    meters: float = Field(..., gt=0, le=MAX_NEAR_M)


class SelectSpec(BaseModel):
    target: Literal["lines", "nodes"] = "lines"
    conditions: list[Condition] = Field(default_factory=list, max_length=MAX_CONDITIONS)
    match: Literal["all", "any"] = "all"
    near: Optional[Near] = None
    in_view: bool = False
    fragment_ids: Optional[list[Annotated[int, Field(ge=0, le=INT32_MAX)]]] = Field(None, max_length=MAX_FRAGMENTS)
    order_by: Optional[str] = Field(None, max_length=40)
    order_desc: bool = True
    limit: int = Field(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)


# --- справочник полей (веб и ИИ) ------------------------------------------------------------

async def _choices(conn, f: Field_) -> list[dict[str, Any]]:
    if f.choices:
        return [{"value": v, "label": label} for v, label in f.choices]
    if f.ref:
        table, column = f.ref
        if not await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{table}"):
            return []
        rows = await conn.fetch(f"SELECT id, {column}::text AS label FROM {table} ORDER BY id")
        return [{"value": r["id"], "label": (r["label"] or f"код {r['id']}").strip()} for r in rows]
    return []


async def fields_payload(conn) -> dict[str, Any]:
    targets = []
    for key, (label, fields) in TARGETS.items():
        targets.append({"key": key, "label": label, "fields": [{
            "key": f.key, "label": f.label, "kind": f.kind, "units": f.units, "source": f.source,
            "hint": f.hint, "ops": list(OPS_BY_KIND[f.kind]), "choices": await _choices(conn, f),
        } for f in fields.values()]})
    return {"targets": targets, "op_labels": OP_LABELS, "max_limit": MAX_LIMIT, "max_near_m": MAX_NEAR_M}


# --- проверка и описание --------------------------------------------------------------------

def _field(target: str, key: str) -> Field_:
    fields = TARGETS[target][1]
    f = fields.get(key)
    if f is None:
        raise SelectError(422, f"Поле «{key}» недоступно для «{TARGETS[target][0].lower()}»: "
                               f"{', '.join(fields)}")
    return f


def _number(v: Any, what: str) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError) as exc:
        raise SelectError(422, f"{what}: нужно число") from exc
    if not math.isfinite(x):
        raise SelectError(422, f"{what}: нужно конечное число")
    return x


def validate(spec: SelectSpec) -> SelectSpec:
    """Поля и операции из белого списка, значения нужного типа; возвращает очищенную копию."""
    conditions = []
    for c in spec.conditions:
        f = _field(spec.target, c.field)
        if c.op not in OPS_BY_KIND[f.kind]:
            ops = ", ".join(OP_LABELS[o] for o in OPS_BY_KIND[f.kind])
            raise SelectError(422, f"«{f.label}»: операция «{OP_LABELS.get(c.op, c.op)}» недоступна ({ops})")
        c = c.model_copy()
        if c.op in ("is_null", "not_null"):
            c.value, c.value2, c.values = None, None, []
        elif f.kind == "number":
            c.value = _number(c.value, f.label)
            if c.op == "between":
                c.value2 = _number(c.value2, f.label)
                if c.value2 < c.value:
                    c.value, c.value2 = c.value2, c.value
            else:
                c.value2 = None
            c.values = []
        elif f.kind == "category":
            if not c.values:
                raise SelectError(422, f"«{f.label}»: выберите хотя бы одно значение")
            if f.choices:
                allowed = {v for v, _ in f.choices}
                bad = [v for v in c.values if v not in allowed]
                if bad:
                    raise SelectError(422, f"«{f.label}»: неизвестные значения {bad}")
            else:
                try:
                    c.values = [int(v) for v in c.values]
                except (TypeError, ValueError) as exc:
                    raise SelectError(422, f"«{f.label}»: значения — коды справочника") from exc
                if any(abs(v) > INT32_MAX for v in c.values):
                    raise SelectError(422, f"«{f.label}»: код справочника вне диапазона")
            c.value, c.value2 = None, None
        else:
            text = str(c.value or "").strip()
            if not text:
                raise SelectError(422, f"«{f.label}»: введите текст")
            c.value, c.value2, c.values = text[:100], None, []
        conditions.append(c)
    order_by = spec.order_by
    if order_by and order_by != "distance":
        _field(spec.target, order_by)
    if order_by == "distance" and not spec.near:
        order_by = None
    near = spec.near
    if near and near.node_id is None and not (near.node_name or "").strip() and (near.lon is None or near.lat is None):
        raise SelectError(422, "«Рядом с»: укажите узел (имя или id) или точку")
    fragments = sorted({int(f) for f in spec.fragment_ids}) if spec.fragment_ids else None
    return spec.model_copy(update={"conditions": conditions, "order_by": order_by, "fragment_ids": fragments})


def _fmt(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def describe(spec: SelectSpec, choices: dict[str, dict[Any, str]], *, near_label: Optional[str] = None) -> str:
    """Человекочитаемый запрос: «Участки: Ду ≥ 400 мм и износ > 60 %; в 300 м от узла «ТК-12»; …»."""
    target_label, _ = TARGETS[spec.target]
    parts = []
    for c in spec.conditions:
        f = _field(spec.target, c.field)
        units = f" {f.units}" if f.units else ""
        if c.op in ("is_null", "not_null"):
            parts.append(f"{f.label} {OP_LABELS[c.op]}")
        elif c.op == "between":
            parts.append(f"{f.label} от {_fmt(c.value)} до {_fmt(c.value2)}{units}")
        elif f.kind == "category":
            names = [choices.get(f.key, {}).get(v, f"код {v}") for v in c.values]
            word = "—" if c.op == "in" else "не"
            parts.append(f"{f.label} {word} {', '.join(names)}")
        elif f.kind == "text":
            parts.append(f"{f.label} {OP_LABELS[c.op]} «{c.value}»")
        else:
            parts.append(f"{f.label} {OP_LABELS[c.op]} {_fmt(c.value)}{units}")
    joiner = " и " if spec.match == "all" else " или "
    text = f"{target_label}: {joiner.join(parts) if parts else 'все'}"
    extra = []
    if spec.near:
        extra.append(f"в {_fmt(spec.near.meters)} м от {near_label or 'точки'}")
    if spec.in_view:
        extra.append("в видимой области карты")
    if spec.fragment_ids:
        shown = ", ".join(str(f) for f in spec.fragment_ids[:10])
        more = f" и ещё {len(spec.fragment_ids) - 10}" if len(spec.fragment_ids) > 10 else ""
        extra.append(f"фрагмент{'ы' if len(spec.fragment_ids) > 1 else ''} {shown}{more}")
    else:
        extra.append("все фрагменты")
    if spec.order_by:
        label = "расстоянию" if spec.order_by == "distance" else _field(spec.target, spec.order_by).label.lower()
        extra.append(f"по {'убыванию' if spec.order_desc else 'возрастанию'}: {label}")
    return "; ".join([text, *extra])


# --- SQL ------------------------------------------------------------------------------------

class _Params:
    def __init__(self):
        self.values: list[Any] = []

    def add(self, value: Any) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


def _condition_sql(c: Condition, f: Field_, p: _Params) -> str:
    expr = f.sql
    if c.op == "is_null":
        return f"({expr}) IS NULL"
    if c.op == "not_null":
        return f"({expr}) IS NOT NULL"
    if f.kind == "number":
        if c.op == "between":
            return f"({expr})::float BETWEEN {p.add(c.value)} AND {p.add(c.value2)}"
        return f"({expr})::float {_OP_SQL[c.op]} {p.add(c.value)}"
    if f.kind == "category":
        cast = "text[]" if f.choices else "int[]"
        values = [str(v) for v in c.values] if f.choices else c.values
        sql = f"({expr}) = ANY({p.add(values)}::{cast})"
        return sql if c.op == "in" else f"(({expr}) IS NULL OR NOT {sql})"
    if c.op == "contains":
        return f"({expr}) ILIKE '%' || {p.add(c.value)} || '%'"
    return f"lower({expr}) = lower({p.add(c.value)})"


async def _resolve_near(conn, near: Near, fragment_ids: Optional[list[int]]) -> tuple[float, float, str]:
    """Центр «рядом с»: (lon, lat, подпись). Узел по имени — сначала из выбранных фрагментов."""
    if near.node_id is not None or (near.node_name or "").strip():
        if near.node_id is not None:
            row = await conn.fetchrow(
                "SELECT id, fileid, externalnodename AS name, ST_X(ST_Transform(shape, 4326)) AS lon,"
                " ST_Y(ST_Transform(shape, 4326)) AS lat FROM nodes WHERE id = $1 AND removed = 0"
                " AND shape IS NOT NULL", near.node_id)
        else:
            name = near.node_name.strip()
            row = await conn.fetchrow(
                "SELECT id, fileid, externalnodename AS name, ST_X(ST_Transform(shape, 4326)) AS lon,"
                " ST_Y(ST_Transform(shape, 4326)) AS lat FROM nodes"
                " WHERE removed = 0 AND internalnodeid IS NULL AND shape IS NOT NULL"
                "   AND externalnodename ILIKE '%' || $1 || '%'"
                " ORDER BY (lower(externalnodename) = lower($1)) DESC, (fileid = ANY($2::int[])) DESC NULLS LAST,"
                "          length(externalnodename), id LIMIT 1", name, fragment_ids or [])
        if row is None:
            what = f"id {near.node_id}" if near.node_id is not None else f"«{near.node_name}»"
            raise SelectError(404, f"Узел {what} не найден (или без координат)")
        return float(row["lon"]), float(row["lat"]),             f"узла «{row['name'] or row['id']}» (id {row['id']}, фрагмент {row['fileid']})"
    return float(near.lon), float(near.lat), f"точки {near.lat:.5f}, {near.lon:.5f}"


def _spatial_sql(geom: str, p: _Params, near_center: Optional[tuple[float, float]], meters: float,
                 bbox: Optional[tuple[float, float, float, float]]) -> tuple[list[str], list[str], str]:
    """Условия по месту: (по индексу shape — охват в SRID сети; точные — по геодезическому расстоянию;
    выражение расстояния в метрах)."""
    srid = net_srid()
    indexed: list[str] = []
    exact: list[str] = []
    distance = "NULL::float"
    if bbox:
        w, s, e, n = (p.add(v) for v in bbox)
        indexed.append(f"{geom} && ST_Transform(ST_MakeEnvelope({w}, {s}, {e}, {n}, 4326), {srid})")
    if near_center:
        lon, lat = near_center
        # охват центра с запасом 20 %: местная система сети не обязательно в метрах
        dlat = meters / M_PER_DEG * 1.2
        dlon = meters / (M_PER_DEG * max(math.cos(math.radians(lat)), 0.05)) * 1.2
        box = (max(lon - dlon, -180.0), max(lat - dlat, -90.0), min(lon + dlon, 180.0), min(lat + dlat, 90.0))
        w, s, e, n = (p.add(v) for v in box)
        indexed.append(f"{geom} && ST_Transform(ST_MakeEnvelope({w}, {s}, {e}, {n}, 4326), {srid})")
        center = f"ST_SetSRID(ST_MakePoint({p.add(lon)}, {p.add(lat)}), 4326)::geography"
        distance = f"ST_Distance(ST_Transform({geom}, 4326)::geography, {center})"
        exact.append(f"{distance} <= {p.add(meters)}")
    return indexed, exact, distance


def _order_sql(spec: SelectSpec, fields: dict[str, Field_], distance: str, id_col: str) -> str:
    if spec.order_by == "distance" or (spec.near and not spec.order_by):
        return f"{distance} ASC, {id_col}"
    if spec.order_by:
        direction = "DESC" if spec.order_desc else "ASC"
        return f"({fields[spec.order_by].sql}) {direction} NULLS LAST, {id_col}"
    return id_col


def _cast(f: Field_) -> str:
    if f.kind == "number":
        return "float"
    return "int" if f.kind == "category" and not f.choices else "text"


def _used_fields(spec: SelectSpec, fields: dict[str, Field_]) -> list[Field_]:
    keys = [c.field for c in spec.conditions]
    if spec.order_by and spec.order_by != "distance":
        keys.append(spec.order_by)
    return [fields[k] for k in dict.fromkeys(keys)]


def _columns_sql(used: list[Field_]) -> tuple[str, str]:
    """Значения полей запроса (f_<поле>) и подписи справочников (l_<поле>) с их JOIN."""
    values = "".join(f", ({f.sql})::{_cast(f)} AS f_{f.key}" for f in used)
    values += "".join(f", ref_{f.key}.{f.ref[1]}::text AS l_{f.key}" for f in used if f.ref)
    joins = "".join(f"\n      LEFT JOIN {f.ref[0]} ref_{f.key} ON ref_{f.key}.id = ({f.sql})" for f in used if f.ref)
    return values, joins


def _where_sql(spec: SelectSpec, fields: dict[str, Field_], p: _Params, base: list[str]) -> str:
    conds = [_condition_sql(c, fields[c.field], p) for c in spec.conditions]
    where = list(base)
    if conds:
        joiner = " AND " if spec.match == "all" else " OR "
        where.append(f"({joiner.join(conds)})")
    return f"WHERE {' AND '.join(where)}" if where else ""


async def _lines_sql(conn, spec: SelectSpec, p: _Params, near_center, bbox, with_geometry: bool):
    fields = _LINE_FIELDS
    used = _used_fields(spec, fields)
    sources = {f.source for f in used}
    runs: dict[str, str] = {}
    for source in sorted(sources & {"wear", "heat_losses"}):
        run_id, _ = await source_run(conn, source)
        if run_id is None:
            what = "износа" if source == "wear" else "нормативных теплопотерь"
            raise SelectError(404, f"Расчёта {what} ещё нет — условие по нему проверить нельзя")
        runs[source] = p.add(run_id)

    frag = p.add(spec.fragment_ids)
    ctes = []
    joins = []
    if "calc" in sources:
        # последний гидравлический расчёт фрагмента, строки подачи — MATERIALIZED (как в thematic.py)
        ctes.append(f"""calc AS (SELECT fileid, MAX(id) AS cid FROM calculation
                  WHERE {frag}::int[] IS NULL OR fileid = ANY({frag}::int[]) GROUP BY fileid),
    calc_ut AS MATERIALIZED (SELECT u.* FROM calc c JOIN ut_out u ON u.calculationid = c.cid
                              AND u.externalsignlineid = {UT_SIGN_SUPPLY})""")
        joins.append("LEFT JOIN calc_ut ut ON ut.lineid = l.id")
    if "wear" in runs:
        joins.append(f"LEFT JOIN wear_out w ON w.calculationid = {runs['wear']} AND w.lineid = l.id")
    if "heat_losses" in runs:
        joins.append(f"""LEFT JOIN (SELECT lineid, SUM(q) AS q FROM ut_teplo_out
                  WHERE calculationid = {runs['heat_losses']} GROUP BY lineid) tl ON tl.lineid = l.id""")

    indexed, exact, distance = _spatial_sql("l.shape", p, near_center, spec.near.meters if spec.near else 0, bbox)
    # паспорт участка — самый длинный (как в износе и тематических картах)
    ctes.append(f"""pipes AS (
      SELECT DISTINCT ON (l.id) l.id AS lid, h.id AS hid
        FROM linesobj l LEFT JOIN heatpipesections h ON h.lineid = l.id
       WHERE l.removed = 0 AND l.shape IS NOT NULL AND {line_inner_sql("l")} IS NULL
         AND ({frag}::int[] IS NULL OR l.fileid = ANY({frag}::int[])){"".join(f" AND {s}" for s in indexed)}
       ORDER BY l.id, h.pipesectlength DESC NULLS LAST, h.id DESC)""")
    values, ref_joins = _columns_sql(used)
    where = _where_sql(spec, fields, p, exact)
    geometry = f"ST_AsGeoJSON(ST_Transform(l.shape, 4326), {COORD_DIGITS})" if with_geometry else "NULL"
    sql = f"""
    WITH {", ".join(ctes)}
    SELECT l.id, l.fileid, n1.externalnodename AS node1, n2.externalnodename AS node2,
           h.pipesectlength AS length, {distance} AS distance_m{values},
           ST_X(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS lon,
           ST_Y(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS lat,
           {geometry} AS geometry, COUNT(*) OVER () AS total, SUM(h.pipesectlength) OVER () AS total_length
      FROM pipes p
      JOIN linesobj l ON l.id = p.lid
      LEFT JOIN heatpipesections h ON h.id = p.hid
      LEFT JOIN nodes n1 ON n1.id = l.nodeid1
      LEFT JOIN nodes n2 ON n2.id = l.nodeid2
      {" ".join(joins)}{ref_joins}
     {where}
     ORDER BY {_order_sql(spec, fields, distance, "l.id")}
     LIMIT {p.add(spec.limit)}"""
    return sql, used


async def _nodes_sql(conn, spec: SelectSpec, p: _Params, near_center, bbox, with_geometry: bool):
    fields = _NODE_FIELDS
    used = _used_fields(spec, fields)
    frag = p.add(spec.fragment_ids)
    indexed, exact, distance = _spatial_sql("n.shape", p, near_center, spec.near.meters if spec.near else 0, bbox)
    base = ["n.removed = 0", "n.internalnodeid IS NULL", "n.shape IS NOT NULL",
            f"({frag}::int[] IS NULL OR n.fileid = ANY({frag}::int[]))", *indexed, *exact]
    values, ref_joins = _columns_sql(used)
    where = _where_sql(spec, fields, p, base)
    geometry = f"ST_AsGeoJSON(ST_Transform(n.shape, 4326), {COORD_DIGITS})" if with_geometry else "NULL"
    sql = f"""
    SELECT n.id, n.fileid, n.externalnodename AS name, nt.name AS node_type_label, {CARD_SQL} AS card,
           {distance} AS distance_m{values},
           ST_X(ST_Transform(n.shape, 4326)) AS lon, ST_Y(ST_Transform(n.shape, 4326)) AS lat,
           {geometry} AS geometry, COUNT(*) OVER () AS total, NULL::float AS total_length
      FROM nodes n
      LEFT JOIN nodetypes nt ON nt.id = n.nodetypeid{CONS_JOIN}{ref_joins}
     {where}
     ORDER BY {_order_sql(spec, fields, distance, "n.id")}
     LIMIT {p.add(spec.limit)}"""
    return sql, used


_inflight: dict[str, int] = {}


@contextmanager
def _slot(user_key: str):
    """Место для выборки: не больше MAX_CONCURRENT на процесс и MAX_CONCURRENT_PER_USER на пользователя
    (каждая держит соединение пула до statement_timeout)."""
    if sum(_inflight.values()) >= MAX_CONCURRENT:
        raise SelectError(429, "Сервер занят другими выборками — повторите через несколько секунд")
    if _inflight.get(user_key, 0) >= MAX_CONCURRENT_PER_USER:
        raise SelectError(429, "Дождитесь окончания предыдущей выборки")
    _inflight[user_key] = _inflight.get(user_key, 0) + 1
    try:
        yield
    finally:
        _inflight[user_key] -= 1
        if not _inflight[user_key]:
            del _inflight[user_key]


async def run_select(conn, spec: SelectSpec, *, bbox: Optional[tuple[float, float, float, float]] = None,
                     with_geometry: bool = True, user_key: str = "") -> dict[str, Any]:
    """Выполнить выборку: описание запроса, строки, GeoJSON (with_geometry) и итоги.

    user_key — кто спрашивает (ограничение одновременных выборок); все запросы — с statement_timeout."""
    spec = validate(spec)
    if spec.in_view and not bbox:
        raise SelectError(422, "«В видимой области»: нет охвата карты")
    if not spec.in_view:
        bbox = None
    with _slot(user_key):
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
            try:
                return await _run(conn, spec, bbox, with_geometry)
            except SelectError:
                raise
            except Exception as exc:
                name = exc.__class__.__name__
                if name == "QueryCanceledError":
                    raise SelectError(422, "Выборка слишком долгая — сузьте условия (фрагменты, область)") from exc
                if name in ("DataError", "NumericValueOutOfRangeError", "InvalidParameterValueError"):
                    raise SelectError(422, "Недопустимое значение в запросе выборки") from exc
                raise


async def _run(conn, spec: SelectSpec, bbox, with_geometry: bool) -> dict[str, Any]:
    fields = TARGETS[spec.target][1]
    near_center = near_label = None
    if spec.near:
        lon, lat, near_label = await _resolve_near(conn, spec.near, spec.fragment_ids)
        near_center = (lon, lat)

    choices: dict[str, dict[Any, str]] = {}
    for c in spec.conditions:
        f = fields[c.field]
        if f.kind == "category" and f.key not in choices:
            choices[f.key] = {x["value"]: x["label"] for x in await _choices(conn, f)}

    p = _Params()
    build = _lines_sql if spec.target == "lines" else _nodes_sql
    sql, used = await build(conn, spec, p, near_center, bbox, with_geometry)
    rows = await conn.fetch(sql, *p.values)

    total = int(rows[0]["total"]) if rows else 0
    total_length = float(rows[0]["total_length"]) if rows and rows[0]["total_length"] is not None else None
    items, features = [], []
    for r in rows:
        values: dict[str, Any] = {}
        for f in used:
            v = r[f"f_{f.key}"]
            if f.kind == "number" and v is not None:
                v = round(float(v), f.digits) if f.digits else round(float(v))
            if f.kind == "category" and v is not None:
                label = r[f"l_{f.key}"] if f.ref else None
                v = label or choices.get(f.key, {}).get(v) or dict(f.choices).get(v) or v
            values[f.key] = v
        if spec.target == "lines":
            title = f"{r['node1'] or '?'} — {r['node2'] or '?'}"
            item = {"id": r["id"], "fileid": r["fileid"], "title": title,
                    "length": round(float(r["length"]), 1) if r["length"] is not None else None}
        else:
            item = {"id": r["id"], "fileid": r["fileid"], "title": r["name"] or f"узел {r['id']}",
                    "node_type": r["node_type_label"], "card_type": dict(CARD_TYPES).get(r["card"])}
        if r["distance_m"] is not None:
            item["distance_m"] = round(float(r["distance_m"]), 1)
        item.update(values=values, lon=r["lon"], lat=r["lat"])
        items.append(item)
        if with_geometry and r["geometry"]:
            features.append({"type": "Feature", "id": r["id"], "geometry": json.loads(r["geometry"]),
                             "properties": {"id": r["id"], "fileid": r["fileid"]}})

    columns = [{"key": f.key, "label": f.label, "units": f.units} for f in used]
    out: dict[str, Any] = {
        "spec": spec.model_dump(),
        "description": describe(spec, choices, near_label=near_label),
        "target": spec.target,
        "columns": columns,
        "total": total,
        "truncated": total > len(items),
        "items": items,
    }
    if total_length is not None:
        out["total_length_m"] = round(total_length, 1)
    if near_center:
        out["near_center"] = {"lon": near_center[0], "lat": near_center[1], "meters": spec.near.meters}
    if with_geometry:
        out["geojson"] = {"type": "FeatureCollection", "features": features}
    return out


def result_features(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Строки выборки с геометрией → объекты GeoJSON для выгрузки в файл (database/vector_export.py)."""
    geometry = {f["id"]: f["geometry"] for f in (result.get("geojson") or {}).get("features", [])}
    out = []
    for item in result["items"]:
        geom = geometry.get(item["id"])
        if geom is None:
            continue
        props: dict[str, Any] = {"id": item["id"], "fileid": item.get("fileid"), "title": item.get("title")}
        if result["target"] == "lines":
            props["length"] = item.get("length")
        else:
            props.update(node_type=item.get("node_type"), card_type=item.get("card_type"))
        if "distance_m" in item:
            props["distance_m"] = item["distance_m"]
        props.update(item.get("values", {}))
        out.append({"type": "Feature", "geometry": geom, "properties": props})
    return out
