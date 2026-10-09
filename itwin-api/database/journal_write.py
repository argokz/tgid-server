"""Запись эксплуатационных журналов: карточки, контуры, утверждение планов, документы.

Эталон — gid6 remont (``opres2.cpp`` SaveOpresNew/SaveOpres/delOsmotrOrRemont,
``remont2.cpp`` OnRemontAddPlan/OnShurfUtverditALL, ``fun.cpp`` OnRemontUtverdit,
правила ``gidr/tab/remont/*.validate``).

Все функции работают в соединении/транзакции вызывающего (роутер открывает транзакцию
и пишет audit_log в ней же). Имена таблиц и колонок — только из ``journal_specs`` и
только после сверки с каталогом (``sql_ident.resolve_table/resolve_column``).
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Optional

from database.journal_specs import (
    JOURNAL_TABLES,
    TIME_PATTERN,
    FieldSpec,
    JournalSpec,
)
from database.sql_ident import quote_ident, resolve_column, resolve_table

MAX_STR_LENGTH = 4000
MAX_CONTOUR_LINES = 5000
_TIME_RE = re.compile(TIME_PATTERN)


class JournalWriteError(Exception):
    """Ошибка записи с HTTP-статусом (роутер превращает её в HTTPException)."""

    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Идентификаторы
# ---------------------------------------------------------------------------

async def _t(conn, name: str) -> str:
    """Таблица из allow-list журналов → имя в кавычках."""
    return quote_ident(await resolve_table(conn, name, JOURNAL_TABLES))


async def _c(conn, table: str, column: str) -> str:
    actual_table = await resolve_table(conn, table, JOURNAL_TABLES)
    return quote_ident(await resolve_column(conn, actual_table, column))


async def _has_column(conn, table: str, column: str) -> bool:
    try:
        await _c(conn, table, column)
        return True
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# Значения полей
# ---------------------------------------------------------------------------

def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return date(int(match[1]), int(match[2]), int(match[3]))
    match = re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", text)
    if match:
        return date(int(match[3]), int(match[2]), int(match[1]))
    raise ValueError("ожидается дата ГГГГ-ММ-ДД")


def _parse_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text) or re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
        d = _parse_date(text)
        return datetime(d.year, d.month, d.day)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("ожидается дата и время ISO 8601") from exc
    return parsed.replace(tzinfo=None)


def coerce_value(field: FieldSpec, value: Any) -> Any:
    """Приводит значение из JSON к типу колонки; пустая строка → NULL."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    kind = field.kind
    if kind == "int":
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("ожидается целое число")
        try:
            return int(str(value).strip()) if not isinstance(value, (int, float)) else int(value)
        except ValueError as exc:
            raise ValueError("ожидается целое число") from exc
    if kind in ("float", "money"):
        if isinstance(value, bool):
            raise ValueError("ожидается число")
        try:
            number = float(str(value).strip().replace(",", ".")) if isinstance(value, str) else float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("ожидается число") from exc
        if number != number or number in (float("inf"), float("-inf")):
            raise ValueError("ожидается конечное число")
        if kind == "money":
            try:
                return Decimal(str(round(number, 2)))
            except InvalidOperation as exc:  # pragma: no cover
                raise ValueError("ожидается сумма") from exc
        return number
    if kind == "date":
        return _parse_date(value)
    if kind == "timestamp":
        return _parse_timestamp(value)
    if kind == "time":
        text = str(value).strip()
        if not _TIME_RE.match(text):
            raise ValueError("время в формате чч:мм")
        return text
    # str
    text = str(value)
    limit = field.max_length or MAX_STR_LENGTH
    if len(text) > limit:
        raise ValueError(f"не длиннее {limit} символов")
    return text


def coerce_fields(
    spec: JournalSpec,
    fields: dict[str, Any],
    catalog: Optional[dict[str, FieldSpec]] = None,
) -> dict[str, Any]:
    """{ключ: значение} → проверенные значения; неизвестные ключи и ошибки типа — 422."""
    catalog = catalog if catalog is not None else spec.fields
    unknown = sorted(k for k in fields if k not in catalog)
    if unknown:
        raise JournalWriteError(422, {
            "message": "Поля не записываются в этом журнале",
            "unknown_fields": unknown,
        })
    result: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for key, value in fields.items():
        try:
            result[key] = coerce_value(catalog[key], value)
        except ValueError as exc:
            errors[key] = str(exc)
    if errors:
        raise JournalWriteError(422, {"message": "Неверные значения полей", "field_errors": errors})
    return result


def check_rules(spec: JournalSpec, record: dict[str, Any], *, creating: bool = False) -> dict[str, str]:
    """Правила *.validate gid6 по итоговой записи: NotNull при создании, After, NotNIfExists."""
    errors: dict[str, str] = {}
    if creating:
        for key in spec.required_on_create:
            if record.get(key) in (None, ""):
                errors[key] = "обязательное поле"
    for earlier, later in spec.date_order:
        a, b = record.get(earlier), record.get(later)
        if a is not None and b is not None:
            a_d = a.date() if isinstance(a, datetime) else a
            b_d = b.date() if isinstance(b, datetime) else b
            if b_d < a_d:
                errors[later] = f"не раньше «{spec.fields[earlier].label or earlier}»"
    for first, second in spec.both_or_none:
        a, b = record.get(first), record.get(second)
        if (a in (None, "")) != (b in (None, "")):
            missing = second if a not in (None, "") else first
            errors[missing] = "заполняется вместе с «{}»".format(
                spec.fields[first if missing == second else second].label
            )
    return errors


def _placeholder(field: FieldSpec, index: int) -> str:
    if field.kind == "money":
        return f"${index}::numeric::money"
    return f"${index}"


async def _check_refs(conn, catalog: dict[str, FieldSpec], values: dict[str, Any]) -> None:
    missing: dict[str, str] = {}
    for key, value in values.items():
        field = catalog[key]
        if not field.ref or value is None:
            continue
        table = await _t(conn, field.ref)
        extra = ""
        if field.ref == "linesobj":
            extra = " AND COALESCE(removed, 0) = 0"
        exists = await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE id = $1{extra})", value)
        if not exists:
            missing[key] = f"нет записи {value} в справочнике"
    if missing:
        raise JournalWriteError(422, {"message": "Ссылка на несуществующую запись", "field_errors": missing})


async def _check_unique(conn, spec: JournalSpec, values: dict[str, Any], exclude_id: Optional[int]) -> None:
    table = await _t(conn, spec.table)
    for key in spec.unique_fields:
        value = values.get(key)
        if value in (None, ""):
            continue
        column = await _c(conn, spec.table, spec.fields[key].column)
        clash = await conn.fetchval(
            f"SELECT id FROM {table} WHERE lower(trim({column})) = lower(trim($1)) "
            f"AND ($2::int IS NULL OR id <> $2) LIMIT 1",
            value, exclude_id,
        )
        if clash is not None:
            raise JournalWriteError(409, {
                "message": f"«{spec.fields[key].label}» уже есть в записи {clash}",
                "field_errors": {key: "должно быть уникальным"},
                "conflict_id": clash,
            })


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


async def load_record(conn, spec: JournalSpec, record_id: int, *, lock: bool = False) -> Optional[dict[str, Any]]:
    """Текущие значения записываемых полей (ключи — как в spec.fields) + служебные."""
    table = await _t(conn, spec.table)
    parts = []
    for key, field in spec.fields.items():
        column = await _c(conn, spec.table, field.column)
        expr = f"{column}::numeric" if field.kind == "money" else column
        parts.append(f"{expr} AS {quote_ident(key)}")
    if spec.approval:
        parts.append(f"{await _c(conn, spec.table, spec.approval.flag_column)} AS \"__approval_flag\"")
        parts.append(f"{await _c(conn, spec.table, spec.approval.date_column)} AS \"__approved_on\"")
        for key, field in spec.approval.signer_columns.items():
            parts.append(f"{await _c(conn, spec.table, field.column)} AS {quote_ident('__signer_' + key)}")
        if spec.approval.state_on_approve:
            parts.append(f"{await _c(conn, spec.table, spec.approval.state_on_approve[0])} AS \"__state\"")
    sql = f"SELECT id, {', '.join(parts)} FROM {table} WHERE id = $1"
    if lock:
        sql += " FOR UPDATE"
    row = await conn.fetchrow(sql, record_id)
    return dict(row) if row else None


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {k: _jsonable(v) for k, v in record.items() if not k.startswith("__")}


# ---------------------------------------------------------------------------
# Геометрия точечных журналов (нарушения, шурфы)
# ---------------------------------------------------------------------------

def _valid_lon_lat(longitude: Any, latitude: Any) -> Optional[tuple[float, float]]:
    if longitude is None and latitude is None:
        return None
    try:
        lon, lat = float(longitude), float(latitude)
    except (TypeError, ValueError) as exc:
        raise JournalWriteError(422, {"message": "Координаты: ожидаются числа", "field_errors": {"longitude": "число"}}) from exc
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise JournalWriteError(422, {"message": "Координаты вне диапазона WGS84"})
    return lon, lat


async def _set_point(conn, spec: JournalSpec, record_id: int, point: Optional[tuple[float, float]], line_id: Optional[int]) -> bool:
    """shape точки: из координат клика или середина участка (как привязка к трубе в gid6)."""
    if not spec.point_geometry:
        return False
    table = await _t(conn, spec.table)
    shape = await _c(conn, spec.table, "shape")
    srid = await conn.fetchval("SELECT Find_SRID('public', $1, 'shape')", spec.table)
    if point is not None:
        await conn.execute(
            f"UPDATE {table} SET {shape} = ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), $3::int) WHERE id = $4",
            point[0], point[1], srid, record_id,
        )
        return True
    if line_id is not None:
        status = await conn.execute(
            # участок внутренней схемы узла — точка узла-владельца (схема в условных координатах)
            f"""UPDATE {table} SET {shape} = (
                    SELECT ST_Transform(COALESCE(owner.shape,
                               CASE WHEN GeometryType(ST_LineMerge(l.shape)) = 'LINESTRING'
                                    THEN ST_LineInterpolatePoint(ST_LineMerge(l.shape), 0.5) END), $1::int)
                      FROM linesobj l LEFT JOIN nodes owner ON owner.id = l.internalnodeid
                     WHERE l.id = $2 AND l.shape IS NOT NULL)
                WHERE id = $3 AND {shape} IS NULL""",
            srid, line_id, record_id,
        )
        return status.endswith("1")
    return False


# ---------------------------------------------------------------------------
# Создание / правка / удаление
# ---------------------------------------------------------------------------

async def create_record(
    conn,
    spec: JournalSpec,
    fields: dict[str, Any],
    *,
    mode: Optional[str] = None,
    line_ids: Optional[list[int]] = None,
    include_pairs: bool = True,
    longitude: Any = None,
    latitude: Any = None,
) -> dict[str, Any]:
    values = coerce_fields(spec, fields)
    errors = check_rules(spec, values, creating=True)
    if errors:
        raise JournalWriteError(422, {"message": "Запись не прошла проверку", "field_errors": errors})
    if mode is not None and mode not in spec.create_modes:
        raise JournalWriteError(422, {"message": f"Режим создания «{mode}» не поддерживается",
                                      "modes": sorted(spec.create_modes)})
    point = _valid_lon_lat(longitude, latitude)
    await _check_refs(conn, spec.fields, values)
    await _check_unique(conn, spec, values, None)

    columns: list[str] = []
    placeholders: list[str] = []
    args: list[Any] = []
    defaults = dict(spec.create_modes.get(mode or "", {})) if mode else {}
    if not mode and spec.create_modes:
        # без режима — плановая запись, как основной пункт меню gid6
        first = "plan" if "plan" in spec.create_modes else sorted(spec.create_modes)[0]
        defaults = dict(spec.create_modes[first])
    by_column = {spec.fields[k].column: (spec.fields[k], v) for k, v in values.items()}
    for column, default in defaults.items():
        if column not in by_column:
            by_column[column] = (FieldSpec(column, "int"), default)
    if spec.created_at_column and spec.created_at_column not in by_column:
        kind = next((f.kind for f in spec.fields.values() if f.column == spec.created_at_column), "timestamp")
        now = datetime.now().replace(microsecond=0)
        by_column[spec.created_at_column] = (FieldSpec(spec.created_at_column, kind), now.date() if kind == "date" else now)
    for column, (field, value) in by_column.items():
        columns.append(await _c(conn, spec.table, column))
        args.append(value)
        placeholders.append(_placeholder(field, len(args)))
    table = await _t(conn, spec.table)
    if columns:
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
    else:
        sql = f"INSERT INTO {table} DEFAULT VALUES RETURNING id"
    new_id = await conn.fetchval(sql, *args)

    result: dict[str, Any] = {"id": new_id, "warnings": []}
    if spec.point_geometry:
        result["has_geometry"] = await _set_point(conn, spec, new_id, point, values.get("line_id"))
    if line_ids:
        contour = await set_contour(conn, spec, new_id, line_ids, include_pairs=include_pairs)
        result["contour"] = {k: contour[k] for k in ("total", "added", "removed", "pairs_added")}
        result["warnings"].extend(contour["warnings"])
    record = await load_record(conn, spec, new_id)
    result["record"] = public_record(record or {})
    return result


async def update_record(
    conn,
    spec: JournalSpec,
    record_id: int,
    fields: dict[str, Any],
    *,
    longitude: Any = None,
    latitude: Any = None,
) -> dict[str, Any]:
    values = coerce_fields(spec, fields)
    point = _valid_lon_lat(longitude, latitude)
    if not values and point is None:
        raise JournalWriteError(422, {"message": "Нет полей для записи"})
    old = await load_record(conn, spec, record_id, lock=True)
    if old is None:
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    changed = {k: v for k, v in values.items() if _jsonable(old.get(k)) != _jsonable(v)}
    merged = {**{k: old.get(k) for k in spec.fields}, **changed}
    errors = check_rules(spec, merged)
    for key in spec.required_on_create:
        if key in changed and changed[key] in (None, ""):
            errors[key] = "обязательное поле"
    if errors:
        raise JournalWriteError(422, {"message": "Запись не прошла проверку", "field_errors": errors})
    await _check_refs(conn, spec.fields, changed)
    await _check_unique(conn, spec, changed, record_id)
    if changed:
        table = await _t(conn, spec.table)
        sets = []
        args: list[Any] = []
        for key, value in changed.items():
            field = spec.fields[key]
            args.append(value)
            sets.append(f"{await _c(conn, spec.table, field.column)} = {_placeholder(field, len(args))}")
        args.append(record_id)
        await conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ${len(args)}", *args)
    geometry_changed = False
    if spec.point_geometry and point is not None:
        geometry_changed = await _set_point(conn, spec, record_id, point, None)
    return {
        "id": record_id,
        "changed": {k: _jsonable(v) for k, v in changed.items()},
        "old": {k: _jsonable(old.get(k)) for k in changed},
        "geometry_changed": geometry_changed,
    }


async def delete_record(conn, spec: JournalSpec, record_id: int) -> dict[str, Any]:
    """Удаление с зависимыми строками, как delOsmotrOrRemont (контур, факторы риска)."""
    old = await load_record(conn, spec, record_id, lock=True)
    if old is None:
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    summary: dict[str, Any] = {"id": record_id, "cascade": {}, "detached": {}}
    if spec.deployed_table:
        deployed = await _t(conn, spec.deployed_table)
        status = await conn.execute(f"DELETE FROM {deployed} WHERE directionid = $1", record_id)
        summary["cascade"][spec.deployed_table] = _affected(status)
    if spec.risk_type is not None:
        risks = await _t(conn, "faktory_riska_truboprovoda")
        status = await conn.execute(
            f"DELETE FROM {risks} WHERE objid = $1 AND obj_type_faktory_riskaid = $2", record_id, spec.risk_type
        )
        summary["cascade"]["faktory_riska_truboprovoda"] = _affected(status)
    if spec.documents_table:
        docs = await _t(conn, spec.documents_table)
        status = await conn.execute(f"DELETE FROM {docs} WHERE objid = $1", record_id)
        summary["cascade"][spec.documents_table] = _affected(status)
    for table_name, column in spec.cascade:
        table = await _t(conn, table_name)
        col = await _c(conn, table_name, column)
        status = await conn.execute(f"DELETE FROM {table} WHERE {col} = $1", record_id)
        summary["cascade"][table_name] = _affected(status)
    for table_name, column in spec.detach:
        table = await _t(conn, table_name)
        col = await _c(conn, table_name, column)
        status = await conn.execute(f"UPDATE {table} SET {col} = NULL WHERE {col} = $1", record_id)
        summary["detached"][f"{table_name}.{column}"] = _affected(status)
    table = await _t(conn, spec.table)
    await conn.execute(f"DELETE FROM {table} WHERE id = $1", record_id)
    summary["old"] = public_record(old)
    return summary


def _affected(status: str) -> int:
    try:
        return int(str(status).rsplit(" ", 1)[-1])
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Контуры (remont2Deployed / opresDeployed / osmotrDeployed)
# ---------------------------------------------------------------------------

def _require_contour(spec: JournalSpec) -> str:
    if not spec.deployed_table:
        raise JournalWriteError(404, "У журнала нет контура")
    return spec.deployed_table


async def get_contour(conn, spec: JournalSpec, record_id: int) -> dict[str, Any]:
    deployed_name = _require_contour(spec)
    if not await _exists(conn, spec, record_id):
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    deployed = await _t(conn, deployed_name)
    rows = await conn.fetch(
        f"""
        SELECT d.lineid AS line_id,
               l.id IS NOT NULL AS exists,
               COALESCE(l.removed, 0) <> 0 AS removed,
               l.nodeid1, l.nodeid2, l.externalsignlineid AS external_sign,
               COALESCE(NULLIF(n1.nodename, ''), n1.externalnodename) AS start_node_name,
               COALESCE(NULLIF(n2.nodename, ''), n2.externalnodename) AS end_node_name,
               hp.diametercondit AS diameter,
               COALESCE(hp.pipesectlength, ST_Length(l.shape)) AS length,
               hp.id IS NOT NULL AS has_heat_pipe_section,
               COALESCE(hp.pipesectionid, 0) > 0 AS has_pipe_section,
               CASE WHEN l.shape IS NULL THEN NULL
                    ELSE ST_AsGeoJSON(ST_Transform(l.shape, 4326), 6)::json END AS geometry
          FROM {deployed} d
          LEFT JOIN linesobj l ON l.id = d.lineid
          LEFT JOIN nodes n1 ON n1.id = l.nodeid1
          LEFT JOIN nodes n2 ON n2.id = l.nodeid2
          LEFT JOIN LATERAL (
                SELECT * FROM heatpipesections h WHERE h.lineid = l.id ORDER BY h.id LIMIT 1
          ) hp ON TRUE
         WHERE d.directionid = $1
         ORDER BY d.id
        """,
        record_id,
    )
    features = []
    lines = []
    for row in rows:
        item = dict(row)
        geometry = item.pop("geometry")
        if isinstance(geometry, str):
            geometry = json.loads(geometry)
        lines.append({k: (float(v) if isinstance(v, Decimal) else v) for k, v in item.items()})
        if geometry:
            features.append({
                "type": "Feature",
                "geometry": geometry,
                "properties": {"line_id": item["line_id"], "removed": item["removed"],
                               "external_sign": item["external_sign"]},
            })
    bbox = await conn.fetchrow(
        f"""SELECT ST_XMin(e) AS xmin, ST_YMin(e) AS ymin, ST_XMax(e) AS xmax, ST_YMax(e) AS ymax
              FROM (SELECT ST_Extent(ST_Transform(l.shape, 4326)) AS e
                      FROM {deployed} d JOIN linesobj l ON l.id = d.lineid
                     WHERE d.directionid = $1 AND l.shape IS NOT NULL) s""",
        record_id,
    )
    return {
        "id": record_id,
        "total": len(lines),
        "lines": lines,
        "warnings": _contour_warnings(lines),
        "geojson": {"type": "FeatureCollection", "features": features},
        "bbox": [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]] if bbox and bbox["xmin"] is not None else None,
    }


def _contour_warnings(lines: list[dict[str, Any]]) -> list[str]:
    warnings = []
    missing = [l["line_id"] for l in lines if not l.get("exists")]
    removed = [l["line_id"] for l in lines if l.get("exists") and l.get("removed")]
    no_hps = [l["line_id"] for l in lines if l.get("exists") and not l.get("has_heat_pipe_section")]
    no_ps = [l["line_id"] for l in lines if l.get("has_heat_pipe_section") and not l.get("has_pipe_section")]
    if missing:
        warnings.append(f"Участков нет в сети: {_short(missing)}")
    if removed:
        warnings.append(f"Участки удалены из сети: {_short(removed)}")
    if no_hps:
        warnings.append(f"Нет характеристик трубопровода (heatPipeSections): {_short(no_hps)}")
    if no_ps:
        # gid6 SaveOpresNew запрещает контур ремонта/осмотра по таким участкам; здесь —
        # предупреждение: в Алматы трубы не привязаны к участкам ПТС вовсе
        warnings.append(f"Участки не привязаны к участкам ПТС (факторы риска и паспорт не заполнятся): {_short(no_ps)}")
    return warnings


def _short(ids: list[int], limit: int = 10) -> str:
    head = ", ".join(str(i) for i in ids[:limit])
    return head + (f" и ещё {len(ids) - limit}" if len(ids) > limit else "")


async def _exists(conn, spec: JournalSpec, record_id: int) -> bool:
    table = await _t(conn, spec.table)
    return bool(await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {table} WHERE id = $1)", record_id))


def normalize_ids(values: Iterable[Any], what: str = "участка", limit: int = MAX_CONTOUR_LINES) -> list[int]:
    """Целые > 0 без повторов, порядок сохраняется."""
    if isinstance(values, (str, bytes)) or values is None:
        raise JournalWriteError(422, {"message": "Ожидается список идентификаторов"})
    result: list[int] = []
    seen: set[int] = set()
    for raw in values:
        if isinstance(raw, bool):
            raise JournalWriteError(422, {"message": f"Идентификатор {what} «{raw}» — не число"})
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise JournalWriteError(422, {"message": f"Идентификатор {what} «{raw}» — не число"}) from exc
        if value <= 0:
            raise JournalWriteError(422, {"message": f"Идентификатор {what} {value} должен быть положительным"})
        if value not in seen:
            seen.add(value)
            result.append(value)
    if len(result) > limit:
        raise JournalWriteError(422, {"message": f"Не больше {limit} идентификаторов за раз"})
    return result


async def set_contour(
    conn,
    spec: JournalSpec,
    record_id: int,
    line_ids: Iterable[Any],
    *,
    include_pairs: bool = True,
) -> dict[str, Any]:
    """Замена состава контура, как SaveOpres: DELETE … Deployed + INSERT (directionID, lineID).

    include_pairs — добавить парную трубу (подача ↔ обратка): gid6 пишет в контур обе
    трубы двухтрубной линии графа (nomP и nomO).
    """
    deployed_name = _require_contour(spec)
    ids = normalize_ids(line_ids)
    if not await _exists(conn, spec, record_id):
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    if ids:
        rows = await conn.fetch(
            "SELECT id, COALESCE(removed, 0) <> 0 AS removed FROM linesobj WHERE id = ANY($1::int[])", ids
        )
        found = {r["id"]: r["removed"] for r in rows}
        missing = [i for i in ids if i not in found]
        removed = [i for i in ids if found.get(i)]
        if missing or removed:
            raise JournalWriteError(422, {
                "message": "Участки нельзя включить в контур",
                "missing_lines": missing,
                "removed_lines": removed,
            })
    pairs_added: list[int] = []
    if include_pairs and ids:
        from database.topology import find_pair_line

        present = set(ids)
        for line_id in list(ids):
            pair = await find_pair_line(conn, line_id)
            if pair and pair["line_id"] not in present:
                present.add(pair["line_id"])
                ids.append(pair["line_id"])
                pairs_added.append(pair["line_id"])
    deployed = await _t(conn, deployed_name)
    before = {r["lineid"] for r in await conn.fetch(
        f"SELECT lineid FROM {deployed} WHERE directionid = $1", record_id)}
    await conn.execute(f"DELETE FROM {deployed} WHERE directionid = $1", record_id)
    if ids:
        await conn.execute(
            f"INSERT INTO {deployed} (directionid, lineid) SELECT $1, unnest($2::int[])", record_id, ids
        )
    after = set(ids)
    contour = await get_contour(conn, spec, record_id)
    return {
        "id": record_id,
        "total": len(after),
        "added": sorted(after - before),
        "removed": sorted(before - after),
        "pairs_added": pairs_added,
        "warnings": contour["warnings"],
        "bbox": contour["bbox"],
    }


# ---------------------------------------------------------------------------
# Утверждение планов
# ---------------------------------------------------------------------------

def _require_approval(spec: JournalSpec):
    if not spec.approval:
        raise JournalWriteError(404, "Журнал не утверждается")
    return spec.approval


async def _contour_size(conn, spec: JournalSpec, record_id: int) -> int:
    if not spec.deployed_table:
        return 0
    deployed = await _t(conn, spec.deployed_table)
    return int(await conn.fetchval(f"SELECT count(*) FROM {deployed} WHERE directionid = $1", record_id))


async def approve_records(
    conn,
    spec: JournalSpec,
    ids: Iterable[Any],
    *,
    approved_on: Any = None,
    signers: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Утверждение одного или нескольких планов.

    remont2 — OnRemontUtverdit: data_utverzhdeniya_plana, stateID=2, utverdit=1;
    shurfy — OnShurfUtverditALL: utverdit=1, дата, назначение и подписанты;
    opres — utverdit=1, дата и утверждающий.
    Записи, которые не прошли проверку, не утверждаются; остальные — утверждаются.
    """
    approval = _require_approval(spec)
    record_ids = normalize_ids(ids, "записи", 500)
    if not record_ids:
        raise JournalWriteError(422, {"message": "Не выбраны записи для утверждения"})
    approved_date = coerce_value(FieldSpec("", "date"), approved_on) if approved_on not in (None, "") else date.today()
    signer_values = coerce_fields(spec, signers or {}, approval.signer_columns)
    await _check_refs(conn, approval.signer_columns, signer_values)

    approved: list[int] = []
    rejected: dict[int, Any] = {}
    changes: dict[int, dict[str, Any]] = {}
    table = await _t(conn, spec.table)
    for record_id in record_ids:
        record = await load_record(conn, spec, record_id, lock=True)
        if record is None:
            rejected[record_id] = "не найдена"
            continue
        flag = record.get("__approval_flag")
        if approval.not_applicable_flag is not None and flag == approval.not_applicable_flag:
            rejected[record_id] = "текущий ремонт не утверждается планом"
            continue
        if flag == 1:
            rejected[record_id] = "уже утверждено"
            continue
        missing = [k for k in approval.required_fields if record.get(k) in (None, "")]
        if missing:
            rejected[record_id] = {
                "message": "не заполнены поля плана",
                "missing_fields": missing,
                "labels": [spec.fields[k].label for k in missing],
            }
            continue
        if approval.require_contour and await _contour_size(conn, spec, record_id) == 0:
            rejected[record_id] = "контур пуст — выберите участки"
            continue
        sets = [f"{await _c(conn, spec.table, approval.flag_column)} = 1",
                f"{await _c(conn, spec.table, approval.date_column)} = $1"]
        args: list[Any] = [approved_date]
        for key, value in signer_values.items():
            args.append(value)
            sets.append(f"{await _c(conn, spec.table, approval.signer_columns[key].column)} = ${len(args)}")
        if approval.state_on_approve:
            column, value = approval.state_on_approve
            args.append(value)
            sets.append(f"{await _c(conn, spec.table, column)} = ${len(args)}")
        args.append(record_id)
        await conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = ${len(args)}", *args)
        approved.append(record_id)
        changes[record_id] = {
            "old": {"approval_flag": flag, "approved_on": _jsonable(record.get("__approved_on")),
                    "state": record.get("__state")},
            "new": {"approval_flag": 1, "approved_on": approved_date.isoformat(),
                    "state": approval.state_on_approve[1] if approval.state_on_approve else None,
                    **{k: _jsonable(v) for k, v in signer_values.items()}},
        }
    return {"approved": approved, "rejected": rejected, "approved_on": approved_date.isoformat(), "changes": changes}


async def revoke_approval(conn, spec: JournalSpec, record_id: int) -> dict[str, Any]:
    """Снятие утверждения: utverdit=0, дата очищается; состояние «в процессе» → «план»."""
    approval = _require_approval(spec)
    record = await load_record(conn, spec, record_id, lock=True)
    if record is None:
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    if record.get("__approval_flag") != 1:
        raise JournalWriteError(409, "Запись не утверждена")
    table = await _t(conn, spec.table)
    sets = [f"{await _c(conn, spec.table, approval.flag_column)} = 0",
            f"{await _c(conn, spec.table, approval.date_column)} = NULL"]
    if approval.state_on_approve:
        column, value = approval.state_on_approve
        sets.append(
            f"{await _c(conn, spec.table, column)} = CASE WHEN {await _c(conn, spec.table, column)} = {int(value)} "
            f"THEN 1 ELSE {await _c(conn, spec.table, column)} END"
        )
    await conn.execute(f"UPDATE {table} SET {', '.join(sets)} WHERE id = $1", record_id)
    return {
        "id": record_id,
        "old": {"approval_flag": 1, "approved_on": _jsonable(record.get("__approved_on")), "state": record.get("__state")},
    }


async def approval_info(conn, spec: JournalSpec, record_id: int) -> dict[str, Any]:
    """Кто и когда утвердил: поля записи (как в gid6) + последняя запись audit_log."""
    approval = _require_approval(spec)
    record = await load_record(conn, spec, record_id)
    if record is None:
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    flag = record.get("__approval_flag")
    last = await conn.fetchrow(
        """SELECT changed_by, changed_at, operation FROM audit_log
            WHERE table_name = $1 AND record_id = $2 AND operation IN ('APPROVE', 'UNAPPROVE')
            ORDER BY changed_at DESC, log_id DESC LIMIT 1""",
        spec.table, record_id,
    ) if await _audit_has_operation_column(conn) else None
    missing = [k for k in approval.required_fields if record.get(k) in (None, "")]
    return {
        "id": record_id,
        "approved": flag == 1,
        "approval_flag": flag,
        "not_applicable": approval.not_applicable_flag is not None and flag == approval.not_applicable_flag,
        "approved_on": _jsonable(record.get("__approved_on")),
        "signers": {k: _jsonable(record.get("__signer_" + k)) for k in approval.signer_columns},
        "last_action": {
            "operation": last["operation"],
            "by": last["changed_by"],
            "at": _jsonable(last["changed_at"]),
        } if last else None,
        "missing_fields": missing,
        "contour_size": await _contour_size(conn, spec, record_id) if spec.deployed_table else None,
    }


async def _audit_has_operation_column(conn) -> bool:
    return bool(await conn.fetchval(
        """SELECT count(*) = 4 FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'audit_log'
              AND column_name IN ('changed_by', 'changed_at', 'operation', 'record_id')"""
    ))


async def list_approval_candidates(
    conn,
    spec: JournalSpec,
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> list[dict[str, Any]]:
    """Неутверждённые планы сезона (диалог выбора gid6 OnRemontPlanUtverdit / OnRemontShurfPlanUtverdit)."""
    approval = _require_approval(spec)
    table = await _t(conn, spec.table)
    flag = await _c(conn, spec.table, approval.flag_column)
    planned = await _c(conn, spec.table, "data_nachala_plan")
    label_key = "name" if "name" in spec.fields else None
    label = await _c(conn, spec.table, spec.fields[label_key].column) if label_key else "NULL"
    conditions = [f"COALESCE({flag}, 0) = 0"]
    args: list[Any] = []
    if spec.key == "shurfs":
        conditions.append(f"{await _c(conn, spec.table, 'naznachenie_vskrid')} = 1")
    if spec.key == "repairs":
        conditions.append(f"COALESCE({await _c(conn, spec.table, 'plan_flag')}, 0) = 1")
    if date_from:
        args.append(date_from)
        conditions.append(f"{planned} >= ${len(args)}")
    if date_to:
        args.append(date_to)
        conditions.append(f"{planned} <= ${len(args)}")
    rows = await conn.fetch(
        f"SELECT id, {label} AS name, {planned} AS planned_start FROM {table} "
        f"WHERE {' AND '.join(conditions)} ORDER BY {planned} NULLS LAST, id LIMIT 500",
        *args,
    )
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


# ---------------------------------------------------------------------------
# Документы плана (remontDocuments / opresDocuments / osmotrDocuments / …)
# ---------------------------------------------------------------------------

DOCUMENT_FIELDS: dict[str, FieldSpec] = {
    "document_type_id": FieldSpec("remontdocumenttypeid", "int", "Вид документа"),
    "date_doc": FieldSpec("date_doc", "date", "Дата документа"),
    "path": FieldSpec("path", "str", "Файл / ссылка", max_length=1000),
}


def _require_documents(spec: JournalSpec) -> str:
    if not spec.documents_table:
        raise JournalWriteError(404, "У журнала нет документов")
    return spec.documents_table


async def list_documents(conn, spec: JournalSpec, record_id: int) -> list[dict[str, Any]]:
    docs = await _t(conn, _require_documents(spec))
    types = await _t(conn, spec.document_types_table)
    rows = await conn.fetch(
        f"""SELECT d.id, d.objid, d.remontdocumenttypeid AS document_type_id, t.name AS document_type_name,
                   d.date_doc, d.path
              FROM {docs} d LEFT JOIN {types} t ON t.id = d.remontdocumenttypeid
             WHERE d.objid = $1 ORDER BY d.date_doc NULLS LAST, d.id""",
        record_id,
    )
    return [{k: _jsonable(v) for k, v in dict(r).items()} for r in rows]


async def document_types(conn, spec: JournalSpec) -> list[dict[str, Any]]:
    types = await _t(conn, spec.document_types_table)
    order = "COALESCE(ord, id), id" if await _has_column(conn, spec.document_types_table, "ord") else "id"
    rows = await conn.fetch(f"SELECT id, name FROM {types} ORDER BY {order}")
    return [dict(r) for r in rows]


async def _check_document(conn, spec: JournalSpec, values: dict[str, Any], creating: bool) -> None:
    if creating and not values.get("path"):
        raise JournalWriteError(422, {"message": "Укажите файл или ссылку", "field_errors": {"path": "обязательное поле"}})
    type_id = values.get("document_type_id")
    if type_id is not None:
        types = await _t(conn, spec.document_types_table)
        if not await conn.fetchval(f"SELECT EXISTS (SELECT 1 FROM {types} WHERE id = $1)", type_id):
            raise JournalWriteError(422, {"message": "Нет такого вида документа",
                                          "field_errors": {"document_type_id": "нет в справочнике"}})


async def add_document(conn, spec: JournalSpec, record_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    docs = await _t(conn, _require_documents(spec))
    if not await _exists(conn, spec, record_id):
        raise JournalWriteError(404, f"{spec.title} {record_id} не найден")
    values = coerce_fields(spec, fields, DOCUMENT_FIELDS)
    await _check_document(conn, spec, values, creating=True)
    doc_id = await conn.fetchval(
        f"INSERT INTO {docs} (objid, remontdocumenttypeid, date_doc, path) VALUES ($1, $2, $3, $4) RETURNING id",
        record_id, values.get("document_type_id"), values.get("date_doc"), values.get("path"),
    )
    return {"id": doc_id, "objid": record_id, **{k: _jsonable(v) for k, v in values.items()}}


async def update_document(conn, spec: JournalSpec, record_id: int, doc_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    docs_name = _require_documents(spec)
    docs = await _t(conn, docs_name)
    old = await conn.fetchrow(
        f"SELECT id, remontdocumenttypeid AS document_type_id, date_doc, path FROM {docs} "
        f"WHERE id = $1 AND objid = $2 FOR UPDATE",
        doc_id, record_id,
    )
    if old is None:
        raise JournalWriteError(404, f"Документ {doc_id} не найден у записи {record_id}")
    values = coerce_fields(spec, fields, DOCUMENT_FIELDS)
    if "path" in values and not values["path"]:
        raise JournalWriteError(422, {"message": "Путь к документу не может быть пустым"})
    await _check_document(conn, spec, values, creating=False)
    if values:
        sets, args = [], []
        for key, value in values.items():
            args.append(value)
            sets.append(f"{await _c(conn, docs_name, DOCUMENT_FIELDS[key].column)} = ${len(args)}")
        args.append(doc_id)
        await conn.execute(f"UPDATE {docs} SET {', '.join(sets)} WHERE id = ${len(args)}", *args)
    return {
        "id": doc_id,
        "changed": {k: _jsonable(v) for k, v in values.items()},
        "old": {k: _jsonable(old[k]) for k in values},
    }


async def delete_document(conn, spec: JournalSpec, record_id: int, doc_id: int) -> dict[str, Any]:
    docs = await _t(conn, _require_documents(spec))
    old = await conn.fetchrow(
        f"DELETE FROM {docs} WHERE id = $1 AND objid = $2 "
        f"RETURNING id, remontdocumenttypeid AS document_type_id, date_doc, path",
        doc_id, record_id,
    )
    if old is None:
        raise JournalWriteError(404, f"Документ {doc_id} не найден у записи {record_id}")
    return {"id": doc_id, "old": {k: _jsonable(v) for k, v in dict(old).items()}}
