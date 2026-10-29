"""Безопасные SQL-идентификаторы (имена таблиц и колонок из запроса клиента).

asyncpg параметризует только значения, но не идентификаторы, поэтому имя таблицы
или колонки, пришедшее из URL/тела запроса, нельзя подставлять в SQL как есть.
Правило для всех таких мест:

1. синтаксис: только буквы (латиница и кириллица — у десктопа есть колонка ``kolichestvoСhelovek``
   с кириллической «С»), цифры и «_», не с цифры (≤ 63 символов, лимит PostgreSQL);
2. allow-list: таблица должна входить в явный перечень для данного эндпоинта
   и реально существовать в схеме public (сверка по каталогу без учёта регистра);
3. в SQL подставляется имя из каталога, взятое в двойные кавычки (quote_ident).

Колонки сверяются с каталогом той же таблицы.
"""

from __future__ import annotations

import re
import time
from typing import Any, Iterable, Optional

IDENT_RE = re.compile(r"^[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё0-9_]{0,62}$")

# Служебные таблицы, которые не отдаются через универсальные эндпоинты ни при каком allow-list.
FORBIDDEN_TABLES: frozenset[str] = frozenset(
    {"audit_log", "alembic_version", "users", "user_permissions", "_this_is_copy"}
)

_CACHE_TTL_S = 300.0
# по городам (cities.cache_key): город → (время, таблицы); (город, таблица) → (время, колонки)
_tables_cache: dict[str, tuple[float, dict[str, str]]] = {}
_columns_cache: dict[tuple[str, str], tuple[float, dict[str, str]]] = {}


def _city() -> str:
    from cities import cache_key

    return cache_key()


class UnknownIdentifierError(ValueError):
    """Имя таблицы/колонки не прошло проверку (синтаксис, allow-list или каталог)."""

    def __init__(self, kind: str, name: Any):
        self.kind = kind
        self.name = name
        super().__init__(f"Unknown {kind}: {name!r}")


def is_valid_ident(name: Any) -> bool:
    return isinstance(name, str) and bool(IDENT_RE.match(name))


def quote_ident(name: str) -> str:
    """Экранирование идентификатора PostgreSQL. Принимает только валидные имена."""
    if not is_valid_ident(name):
        raise UnknownIdentifierError("identifier", name)
    return '"' + name.replace('"', '""') + '"'


def reset_catalog_cache() -> None:
    city = _city()
    _tables_cache.pop(city, None)
    for key in [k for k in _columns_cache if k[0] == city]:
        del _columns_cache[key]


async def _public_tables(conn) -> dict[str, str]:
    """{lower(name): name} для таблиц и представлений схемы public (кэш 5 мин)."""
    now = time.monotonic()
    cached = _tables_cache.get(_city())
    if cached and now - cached[0] < _CACHE_TTL_S:
        return cached[1]
    rows = await conn.fetch(
        """SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'"""
    )
    mapping = {str(r["table_name"]).lower(): str(r["table_name"]) for r in rows}
    _tables_cache[_city()] = (now, mapping)
    return mapping


async def _table_columns(conn, table: str) -> dict[str, str]:
    """{lower(column): column} для таблицы из каталога (кэш 5 мин)."""
    now = time.monotonic()
    cached = _columns_cache.get((_city(), table))
    if cached and now - cached[0] < _CACHE_TTL_S:
        return cached[1]
    rows = await conn.fetch(
        """SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1""",
        table,
    )
    mapping = {str(r["column_name"]).lower(): str(r["column_name"]) for r in rows}
    _columns_cache[(_city(), table)] = (now, mapping)
    return mapping


async def resolve_table(conn, name: Any, allowed: Optional[Iterable[str]] = None) -> str:
    """Имя таблицы из каталога для подстановки в SQL (без кавычек; quote_ident — отдельно).

    ``allowed`` — allow-list эндпоинта (регистр не важен). None — любая таблица public,
    кроме FORBIDDEN_TABLES.
    """
    if not is_valid_ident(name):
        raise UnknownIdentifierError("table", name)
    key = name.lower()
    if key in FORBIDDEN_TABLES:
        raise UnknownIdentifierError("table", name)
    if allowed is not None and key not in {a.lower() for a in allowed}:
        raise UnknownIdentifierError("table", name)
    actual = (await _public_tables(conn)).get(key)
    if actual is None:
        raise UnknownIdentifierError("table", name)
    return actual


async def resolve_column(conn, table: str, name: Any) -> str:
    """Имя колонки из каталога таблицы ``table`` (уже разрешённой через resolve_table)."""
    if not is_valid_ident(name):
        raise UnknownIdentifierError("column", name)
    actual = (await _table_columns(conn, table)).get(name.lower())
    if actual is None:
        raise UnknownIdentifierError("column", name)
    return actual


async def resolve_columns(conn, table: str, names: Iterable[Any]) -> dict[Any, str]:
    """{исходное имя: имя из каталога}; первая неизвестная колонка — исключение."""
    return {n: await resolve_column(conn, table, n) for n in names}
