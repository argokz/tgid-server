"""Кто создал объект сети (право «только свои», permissions.py).

object_authorship(table_name, record_id, created_by, created_at, operation_id) — пишется
журналом операций (OperationJournal.commit) для строк, созданных операцией. Отмена создания
запись не удаляет: id из последовательности не переиспользуются, а повтор возвращает те же
строки. Объекты из десктопа и созданные до появления таблицы — без автора («чужие» для всех).

Таблица — миграция sql/migrations/20261020_object_authorship.sql; без неё «свои» объекты
определить нельзя — охват own разрешает только то, что не требует проверки автора.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

TABLE = "object_authorship"


async def authorship_available(conn) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass('public.object_authorship') IS NOT NULL"))


async def record_created(conn, rows: Iterable[tuple[str, int]], actor: Optional[str],
                         operation_id: Optional[int]) -> int:
    """Автор созданных операцией строк (в транзакции операции); → сколько записано."""
    rows = [(t.lower(), int(i)) for t, i in rows]
    if not rows or not actor or not await authorship_available(conn):
        return 0
    await conn.execute(
        f"""
        INSERT INTO {TABLE} (table_name, record_id, created_by, operation_id)
        SELECT t, i, $3, $4 FROM unnest($1::text[], $2::int[]) AS u(t, i)
        ON CONFLICT (table_name, record_id) DO NOTHING
        """,
        [t for t, _ in rows], [i for _, i in rows], actor, operation_id,
    )
    return len(rows)


async def foreign_objects(conn, username: str, targets: dict[str, Iterable[int]]) -> list[str]:
    """Объекты из targets {таблица: [id]}, созданные не username (или без автора) → «таблица:id»."""
    wanted = [(t.lower(), int(i)) for t, ids in targets.items() for i in ids if i is not None]
    if not wanted:
        return []
    if not await authorship_available(conn):
        return [f"{t}:{i}" for t, i in wanted]
    rows = await conn.fetch(
        f"""
        SELECT u.t, u.i FROM unnest($1::text[], $2::int[]) AS u(t, i)
        LEFT JOIN {TABLE} a ON a.table_name = u.t AND a.record_id = u.i
        WHERE a.created_by IS DISTINCT FROM $3
        """,
        [t for t, _ in wanted], [i for _, i in wanted], username,
    )
    foreign = [(r["t"], int(r["i"])) for r in rows]
    # строка карточки (паспорт, потребитель, оборудование…) — своя, если свой её участок или узел
    foreign = [k for k in foreign if not await _parent_is_own(conn, username, *k)]
    return [_label(t, i) for t, i in foreign]


_PARENT_COLUMNS = (("lineid", "linesobj"), ("nodeid", "nodes"))


async def _parent_is_own(conn, username: str, table: str, row_id: int) -> bool:
    if table in ("linesobj", "nodes"):
        return False
    cols = {r["c"] for r in await conn.fetch(
        "SELECT lower(column_name) AS c FROM information_schema.columns "
        "WHERE table_schema = 'public' AND lower(table_name) = $1", table,
    )}
    for col, parent in _PARENT_COLUMNS:
        if col not in cols:
            continue
        actual = await conn.fetchval(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND lower(table_name) = $1",
            table,
        )
        parent_id = await conn.fetchval(f'SELECT {col} FROM public."{actual}" WHERE id = $1', row_id)
        if parent_id is None:
            continue
        owner = await conn.fetchval(
            f"SELECT created_by FROM {TABLE} WHERE table_name = $1 AND record_id = $2", parent, int(parent_id),
        )
        return owner == username
    return False


_LABELS = {"linesobj": "участок", "heatpipesections": "паспорт", "nodes": "узел"}


def _label(table: str, row_id: int) -> str:
    return f"{_LABELS.get(table, table)} {row_id}"


async def owner_of(conn, table: str, record_id: int) -> Optional[dict[str, Any]]:
    """Автор объекта для карточки: {created_by, created_at} или None."""
    if not await authorship_available(conn):
        return None
    row = await conn.fetchrow(
        f"SELECT created_by, created_at FROM {TABLE} WHERE table_name = $1 AND record_id = $2",
        table.lower(), int(record_id),
    )
    return dict(row) if row else None
