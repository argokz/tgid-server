"""Журнал операций топологии с before-image — основа отмены (Stage B, B5 undo).

Каждая операция редактора (create/move/delete/split/merge/reverse/geometry) в своей
транзакции:
  1. до изменений снимает before-image всех строк, которые может затронуть
     (`capture*`): полный образ строки в jsonb, геометрия — hex EWKB (точный round-trip
     через jsonb_populate_record, без потерь GeoJSON);
  2. отмечает строки, которые создаёт (`created`) — при отмене они удаляются;
  3. в конце, в той же транзакции, пишет запись в `topology_undo_log`: образы «до» и
     md5 образов «после» (`after_hashes`).

Отмена (`undo_operation` в database/topology.py) берёт последнюю неотменённую операцию
пользователя, блокирует строки и сверяет их текущий md5 с `after_hashes`: если объект
менялся после операции (другим пользователем, десктопом или следующей операцией) — 409,
ничего не трогаем. Иначе восстанавливает образы «до» и удаляет созданные строки.

Почему не legacy audit_log (триггер log_changes + rollback_group): триггеры стоят только на
23 таблицах (merge переносит ссылки в любых из 57 nodeid-таблиц), rollback_change
восстанавливает геометрию из GeoJSON-текста и упорядочивает записи по changed_at, который
внутри одной транзакции одинаков. Поэтому отдельная таблица; группа операции при этом
совпадает с change_group_id записей audit_log (и триггерных, через tgid.current_group_id).

Таблица журнала создаётся миграцией sql/migrations/20260927_topology_undo_log.sql. Без неё
операции работают как раньше, но отмена недоступна (`operation_id` = None).
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from database.topology_transfer import _ident

JOURNAL_TABLE = "topology_undo_log"

_GEOMETRY_COLUMNS: dict[str, tuple[str, ...]] = {}
_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {}


async def journal_available(conn) -> bool:
    return bool(await conn.fetchval(f"SELECT to_regclass('public.{JOURNAL_TABLE}') IS NOT NULL"))


async def table_columns(conn, table: str) -> tuple[str, ...]:
    """Колонки таблицы (public), в порядке объявления; кэшируется на процесс."""
    if table not in _TABLE_COLUMNS:
        rows = await conn.fetch(
            "SELECT column_name, udt_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position",
            table,
        )
        _TABLE_COLUMNS[table] = tuple(r["column_name"] for r in rows)
        _GEOMETRY_COLUMNS[table] = tuple(r["column_name"] for r in rows if r["udt_name"] == "geometry")
    return _TABLE_COLUMNS[table]


async def geometry_columns(conn, table: str) -> tuple[str, ...]:
    await table_columns(conn, table)
    return _GEOMETRY_COLUMNS.get(table, ())


def row_image_sql(table: str, geom_cols: Iterable[str], alias: str = "_r") -> str:
    """Выражение jsonb-образа строки: to_jsonb(row) + геометрия как hex EWKB.

    Алиас, а не имя таблицы: у heatpipesections есть колонка «h», у других могут быть
    колонки, совпадающие с коротким именем — to_jsonb(<алиас>) должен взять строку.
    """
    expr = f"to_jsonb({alias})"
    geoms = list(geom_cols)
    if geoms:
        pairs = ", ".join(f"'{c}', encode(ST_AsEWKB({alias}.{_ident(c)}), 'hex')" for c in geoms)
        expr = f"({expr} || jsonb_build_object({pairs}))"
    return expr


def restore_sql(table: str, columns: Iterable[str]) -> str:
    """UPDATE строки из образа. Параметры: $1 = образ (jsonb), $2 = id."""
    cols = [c for c in columns if c != "id"]
    target = ", ".join(_ident(c) for c in cols)
    source = ", ".join(f"_p.{_ident(c)}" for c in cols)
    t = _ident(table)
    return (
        f"UPDATE {t} AS _t SET ({target}) = "
        f"(SELECT {source} FROM jsonb_populate_record(NULL::{t}, $1::jsonb) AS _p) "
        f"WHERE _t.id = $2"
    )


def reinsert_sql(table: str) -> str:
    """Строка, которой после операции нет (не должно случаться — операции не удаляют физически)."""
    t = _ident(table)
    return f"INSERT INTO {t} SELECT (jsonb_populate_record(NULL::{t}, $1::jsonb)).*"


def key(table: str, row_id: int) -> str:
    return f"{table}:{row_id}"


class OperationJournal:
    """Сбор before-image внутри транзакции операции.

    enabled=False (нет таблицы журнала или dry-run) — все методы ничего не делают.
    """

    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.before: dict[tuple[str, int], Optional[str]] = {}
        self.unsupported: set[str] = set()

    @classmethod
    async def open(cls, conn, dry_run: bool = False) -> "OperationJournal":
        return cls(enabled=(not dry_run) and await journal_available(conn))

    async def capture(self, conn, table: str, where: str, *args: Any) -> list[int]:
        """Снимает образы строк `table` под условием where (алиас строки — _r); id строк."""
        if not self.enabled:
            return []
        cols = await table_columns(conn, table)
        if not cols:
            return []  # таблицы нет в этой БД — и изменять операции в ней нечего
        if "id" not in cols:
            self.unsupported.add(table)
            return []
        expr = row_image_sql(table, await geometry_columns(conn, table))
        rows = await conn.fetch(
            f"SELECT _r.id AS id, {expr}::text AS img FROM {_ident(table)} AS _r WHERE {where}",
            *args,
        )
        ids = []
        for r in rows:
            k = (table, int(r["id"]))
            # первый снимок — до операции; повторный capture той же строки его не затирает
            self.before.setdefault(k, r["img"])
            ids.append(k[1])
        return ids

    async def capture_ids(self, conn, table: str, ids: Iterable[int]) -> list[int]:
        ids = [int(i) for i in ids if i is not None]
        if not ids:
            return []
        return await self.capture(conn, table, "_r.id = ANY($1::int[])", ids)

    def created(self, table: str, row_id: Optional[int]) -> None:
        if self.enabled and row_id is not None:
            self.before.setdefault((table, int(row_id)), None)

    async def created_where(self, conn, table: str, where: str, *args: Any) -> None:
        if not self.enabled:
            return
        for r in await conn.fetch(f"SELECT _r.id AS id FROM {_ident(table)} AS _r WHERE {where}", *args):
            self.created(table, r["id"])

    def _by_table(self) -> dict[str, list[int]]:
        grouped: dict[str, list[int]] = {}
        for (table, row_id) in self.before:
            grouped.setdefault(table, []).append(row_id)
        return grouped

    async def commit(
        self,
        conn,
        *,
        actor: Optional[str],
        operation: str,
        group_id: str,
        summary: dict,
    ) -> Optional[int]:
        """Пишет запись журнала (в транзакции операции); id записи = operation_id для отмены."""
        if not self.enabled or not self.before:
            return None
        after = await current_hashes(conn, self._by_table())
        # Образы — текст jsonb из PostgreSQL, вставляются как есть: разбор в Python
        # потерял бы точность numeric-колонок.
        parts = []
        for (table, row_id), img in self.before.items():
            parts.append(
                '{"t": %s, "id": %d, "row": %s}' % (json.dumps(table), row_id, img if img is not None else "null")
            )
        before_json = "[" + ", ".join(parts) + "]"
        return await conn.fetchval(
            f"""
            INSERT INTO {JOURNAL_TABLE}
                (change_group_id, actor, operation, summary, before_rows, after_hashes, unsupported)
            VALUES ($1::uuid, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb, $7::jsonb)
            RETURNING id
            """,
            group_id,
            actor,
            operation,
            json.dumps(summary, ensure_ascii=False, default=str),
            before_json,
            json.dumps(after),
            json.dumps(sorted(self.unsupported)) if self.unsupported else None,
        )


async def current_hashes(conn, by_table: dict[str, list[int]], lock: bool = False) -> dict[str, Optional[str]]:
    """md5 текущих образов строк: {"table:id": md5 | None (строки нет)}."""
    result: dict[str, Optional[str]] = {}
    for table, ids in sorted(by_table.items()):
        expr = row_image_sql(table, await geometry_columns(conn, table))
        suffix = " ORDER BY _r.id FOR UPDATE" if lock else ""
        rows = await conn.fetch(
            f"SELECT _r.id AS id, md5({expr}::text) AS h FROM {_ident(table)} AS _r "
            f"WHERE _r.id = ANY($1::int[]){suffix}",
            sorted(set(ids)),
        )
        found = {int(r["id"]): r["h"] for r in rows}
        for row_id in ids:
            result[key(table, row_id)] = found.get(int(row_id))
    return result


def changed_since(after_hashes: dict, current: dict) -> dict:
    """Строки, изменённые после операции: {"table:id": {"expected": md5, "actual": md5|None}}."""
    return {
        k: {"expected": v, "actual": current.get(k)}
        for k, v in after_hashes.items()
        if current.get(k) != v
    }


async def restore_rows(conn, before_rows: list[dict]) -> dict:
    """Восстанавливает образы «до»; строки, созданные операцией (row = null), удаляет.

    Возвращает {"restored": {table: n}, "deleted": {table: [id…]}}.
    """
    restored: dict[str, int] = {}
    deleted: dict[str, list[int]] = {}
    # удаление созданных — до восстановления (порядок без FK не важен, но так проще читать отчёт)
    for item in before_rows:
        if item.get("row") is None:
            table, row_id = item["t"], int(item["id"])
            await conn.execute(f"DELETE FROM {_ident(table)} WHERE id = $1", row_id)
            deleted.setdefault(table, []).append(row_id)
    for item in before_rows:
        img = item.get("row")
        if img is None:
            continue
        table, row_id = item["t"], int(item["id"])
        cols = await table_columns(conn, table)
        img_text = img if isinstance(img, str) else json.dumps(img)
        status = await conn.execute(restore_sql(table, cols), img_text, row_id)
        if str(status).endswith(" 0"):
            await conn.execute(reinsert_sql(table), img_text)
        restored[table] = restored.get(table, 0) + 1
    return {"restored": restored, "deleted": deleted}
