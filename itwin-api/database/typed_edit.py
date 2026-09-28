"""Типизированная правка атрибутов объектов по описаниям карточек ``tab/*.txt`` (этап 9).

Allow-list полей таблицы = поля карточки десктопа (``tab/*.txt``, как ``PropertyDial``)
∩ реальные колонки таблицы, без служебных (ключи, геометрия, признаки удаления).
Тип значения берётся из схемы БД (information_schema), справочник — из ``kls/gid.lookup``,
подпись — из ``kls/gid.txt1/2``. Неизвестное поле или значение не того типа → 422.

Оптимистичная блокировка: версия строки — ``xmin`` (меняется при любой записи строки,
в том числе десктопом). Клиент присылает версию, прочитанную с карточкой; строка берётся
``SELECT … FOR UPDATE``, при несовпадении — 409 (как правки топологии).
Каждое изменение пишется в ``audit_log`` (старые и новые значения изменённых полей).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Awaitable, Callable, Optional

from database.sql_ident import quote_ident, resolve_table
from utils.ini import storage

# Колонки, которые не правятся через карточку: ключи, связи с топологией, геометрия, служебные.
SYSTEM_COLUMNS = frozenset({
    "id", "nodeid", "lineid", "nodeid1", "nodeid2", "fileid", "shape", "removed",
    "archivechangedate", "archivedate", "guid", "externalsignlineid", "externalsignnodeid",
})

_INT_TYPES = {"integer", "bigint", "smallint"}
_FLOAT_TYPES = {"numeric", "real", "double precision"}
_STR_TYPES = {"character varying", "text", "character"}
_KINDS = {**{t: "int" for t in _INT_TYPES}, **{t: "float" for t in _FLOAT_TYPES},
          **{t: "str" for t in _STR_TYPES}, "date": "date", "boolean": "bool",
          "timestamp without time zone": "datetime", "timestamp with time zone": "datetime"}

AuditRow = Callable[..., Awaitable[Any]]


class TypedEditError(Exception):
    """Ошибка с HTTP-статусом (роутер превращает её в HTTPException)."""

    def __init__(self, status: int, detail: Any):
        super().__init__(str(detail))
        self.status = status
        self.detail = detail


@dataclass(frozen=True)
class FieldSpec:
    name: str  # реальное имя колонки
    label: str
    kind: str  # int | float | str | date | datetime | bool
    max_length: Optional[int] = None
    group: str = ""
    ref_table: Optional[str] = None
    ref_id: Optional[str] = None
    ref_label: Optional[str] = None

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name, "label": self.label, "kind": self.kind, "max_length": self.max_length,
            "group": self.group or None,
            "ref": {"table": self.ref_table, "id": self.ref_id, "label": self.ref_label} if self.ref_table else None,
        }


async def _columns(conn, table: str) -> dict[str, tuple[str, str, Optional[int]]]:
    rows = await conn.fetch(
        "SELECT column_name, data_type, character_maximum_length FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = $1", table)
    return {r["column_name"].lower(): (r["column_name"], r["data_type"], r["character_maximum_length"])
            for r in rows}


async def editable_fields(conn, table: str, *, exclude: frozenset[str] = frozenset()) -> list[FieldSpec]:
    """Поля карточки tab/<table>.txt, которые есть в таблице и правятся (порядок — как в карточке)."""
    actual = await resolve_table(conn, table)
    tab = await storage.read_tab2(table)
    if tab is None:
        raise TypedEditError(404, {"code": "no_card", "message": f"Нет описания карточки для таблицы {table}"})
    columns = await _columns(conn, actual)
    skip = SYSTEM_COLUMNS | {c.lower() for c in exclude}
    fields: list[FieldSpec] = []
    seen: set[str] = set()
    group = ""
    for entry in tab:
        if entry.startswith("!"):
            group = entry[3:].strip() if len(entry) > 3 else ""
            continue
        if entry.startswith("$"):
            continue
        key = entry.lower()
        if key in seen or key in skip or key not in columns:
            continue
        name, data_type, max_len = columns[key]
        kind = _KINDS.get(data_type)
        if kind is None:  # геометрия, bytea, массивы — не через карточку
            continue
        seen.add(key)
        label = storage.get_help(table, entry)[2] or name
        lookup = storage.get_lookup(table, entry)
        fields.append(FieldSpec(
            name=name, label=label, kind=kind, max_length=max_len, group=group,
            ref_table=lookup[2].lower() if lookup else None,
            ref_id=lookup[3].lower() if lookup else None,
            ref_label=lookup[4].lower() if lookup else None,
        ))
    return fields


def coerce_value(field: FieldSpec, value: Any) -> Any:
    """JSON-значение → тип колонки; пустая строка/None → NULL. Ошибка → 422."""
    if value is None or (isinstance(value, str) and not value.strip() and field.kind != "str"):
        return None
    try:
        if field.kind == "int":
            if isinstance(value, bool):
                raise ValueError
            number = float(str(value).replace(",", ".")) if not isinstance(value, int) else value
            if int(number) != number:
                raise ValueError
            return int(number)
        if field.kind == "float":
            if isinstance(value, bool):
                raise ValueError
            number = float(str(value).replace(",", "."))
            if number != number or number in (float("inf"), float("-inf")):
                raise ValueError
            return number
        if field.kind == "str":
            text = str(value)
            if field.max_length is not None and len(text) > field.max_length:
                raise TypedEditError(422, {"code": "too_long", "field": field.name,
                                           "message": f"«{field.label}»: не длиннее {field.max_length} символов"})
            return text
        if field.kind == "date":
            return date.fromisoformat(str(value)[:10])
        if field.kind == "datetime":
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
        if field.kind == "bool":
            if isinstance(value, bool):
                return value
            if str(value).lower() in ("1", "true", "да"):
                return True
            if str(value).lower() in ("0", "false", "нет"):
                return False
            raise ValueError
    except TypedEditError:
        raise
    except (TypeError, ValueError, InvalidOperation):
        pass
    expected = {"int": "целое число", "float": "число", "date": "дата ГГГГ-ММ-ДД",
                "datetime": "дата и время", "bool": "да/нет"}.get(field.kind, "текст")
    raise TypedEditError(422, {"code": "bad_value", "field": field.name,
                               "message": f"«{field.label}»: ожидается {expected}"})


def jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


async def _check_refs(conn, fields: dict[str, FieldSpec], values: dict[str, Any]) -> None:
    for name, value in values.items():
        spec = fields[name]
        if value is None or not spec.ref_table:
            continue
        try:
            ref_table = await resolve_table(conn, spec.ref_table)
        except Exception:  # noqa: BLE001 - справочника нет в этой базе: не проверяем
            continue
        ok = await conn.fetchval(
            f"SELECT EXISTS (SELECT 1 FROM {quote_ident(ref_table)} WHERE {quote_ident(spec.ref_id or 'id')}::text"
            f" = $1::text)", str(value))
        if not ok:
            raise TypedEditError(422, {"code": "bad_ref", "field": name,
                                       "message": f"«{spec.label}»: значения {value} нет в справочнике {spec.ref_table}"})


def prepare_values(fields: list[FieldSpec], raw: dict[str, Any]) -> tuple[dict[str, FieldSpec], dict[str, Any]]:
    by_key = {f.name.lower(): f for f in fields}
    values: dict[str, Any] = {}
    for key, value in (raw or {}).items():
        spec = by_key.get(str(key).lower())
        if spec is None:
            raise TypedEditError(422, {"code": "field_not_editable", "field": key,
                                       "message": f"Поле «{key}» не редактируется"})
        values[spec.name] = coerce_value(spec, value)
    return {f.name: f for f in fields}, values


async def read_record(conn, table: str, key_column: str, key: int, fields: list[FieldSpec]) -> dict[str, Any]:
    actual = await resolve_table(conn, table)
    cols = ", ".join(quote_ident(f.name) for f in fields) or "1 AS _"
    row = await conn.fetchrow(
        f"SELECT xmin::text AS _version, {cols} FROM {quote_ident(actual)} WHERE {quote_ident(key_column)} = $1",
        key)
    if row is None:
        raise TypedEditError(404, {"code": "not_found", "message": f"Запись {table} {key} не найдена"})
    return {"version": row["_version"], "values": {f.name: jsonable(row[f.name]) for f in fields}}


async def update_record(conn, table: str, key_column: str, key: int, fields: list[FieldSpec],
                        raw: dict[str, Any], *, expected_version: Optional[str], audit_row: Optional[AuditRow],
                        dry_run: bool = False) -> dict[str, Any]:
    """Правка строки в транзакции вызывающего: FOR UPDATE, проверка версии, UPDATE, audit_log."""
    actual = await resolve_table(conn, table)
    by_name, values = prepare_values(fields, raw)
    if not values:
        raise TypedEditError(422, {"code": "no_fields", "message": "Нет полей для изменения"})
    await _check_refs(conn, by_name, values)
    cols = ", ".join(quote_ident(c) for c in values)
    row = await conn.fetchrow(
        f"SELECT id AS _row_id, xmin::text AS _version, {cols} FROM {quote_ident(actual)} "
        f"WHERE {quote_ident(key_column)} = $1 FOR UPDATE", key)
    if row is None:
        raise TypedEditError(404, {"code": "not_found", "message": f"Запись {table} {key} не найдена"})
    if expected_version is not None and str(expected_version) != row["_version"]:
        raise TypedEditError(409, {"code": "version_conflict",
                                   "message": "Запись изменена другим пользователем — обновите карточку",
                                   "expected": expected_version, "actual": row["_version"]})
    old = {c: row[c] for c in values}
    changed = {c: v for c, v in values.items() if old[c] != v}
    result = {"table": actual, "key": key, "changed": {c: {"old": jsonable(old[c]), "new": jsonable(v)}
                                                         for c, v in changed.items()},
              "dry_run": dry_run, "version": row["_version"]}
    if dry_run or not changed:
        return result
    sets = ", ".join(f"{quote_ident(c)} = ${i + 2}" for i, c in enumerate(changed))
    new_version = await conn.fetchval(
        f"UPDATE {quote_ident(actual)} SET {sets} WHERE {quote_ident(key_column)} = $1 RETURNING xmin::text",
        key, *changed.values())
    if audit_row is not None:
        await audit_row(conn, operation="UPDATE", table=actual, record_id=row["_row_id"],
                        old={c: jsonable(old[c]) for c in changed},
                        new={c: jsonable(v) for c, v in changed.items()})
    result["version"] = new_version
    return result


async def insert_record(conn, table: str, fields: list[FieldSpec], raw: dict[str, Any], *,
                        audit_row: Optional[AuditRow], extra: Optional[dict[str, Any]] = None) -> int:
    """Новая строка (id — из последовательности таблицы) с полями из allow-list."""
    actual = await resolve_table(conn, table)
    by_name, values = prepare_values(fields, raw)
    await _check_refs(conn, by_name, values)
    values = {**values, **(extra or {})}
    if values:
        cols = ", ".join(quote_ident(c) for c in values)
        params = ", ".join(f"${i + 1}" for i in range(len(values)))
        new_id = await conn.fetchval(
            f"INSERT INTO {quote_ident(actual)} ({cols}) VALUES ({params}) RETURNING id", *values.values())
    else:
        new_id = await conn.fetchval(f"INSERT INTO {quote_ident(actual)} DEFAULT VALUES RETURNING id")
    if audit_row is not None:
        await audit_row(conn, operation="INSERT", table=actual, record_id=new_id, old=None,
                        new={c: jsonable(v) for c, v in values.items()})
    return int(new_id)


async def delete_record(conn, table: str, key: int, *, audit_row: Optional[AuditRow],
                        fields: list[FieldSpec]) -> None:
    actual = await resolve_table(conn, table)
    cols = ", ".join(quote_ident(f.name) for f in fields) or "id"
    row = await conn.fetchrow(f"DELETE FROM {quote_ident(actual)} WHERE id = $1 RETURNING {cols}", key)
    if row is None:
        raise TypedEditError(404, {"code": "not_found", "message": f"Запись {table} {key} не найдена"})
    if audit_row is not None:
        await audit_row(conn, operation="DELETE", table=actual, record_id=key,
                        old={k: jsonable(v) for k, v in dict(row).items()}, new=None)
