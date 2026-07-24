"""Перенос зависимых объектов при разрезании участка.

При разрезании линии L (0..1) на L (0..f) и L2 (f..1) каждый зависимый объект,
ссылающийся на L через `lineid`, должен оказаться на правильной половине.
Логика переноса зависит от того, как объект позиционирован — отсюда декларативная
карта правил (см. docs/stage-b-topology-editor-plan.md, разделы 1–2):

  GEOMETRY  — у объекта есть собственная геометрия (shape): переносим по проекции
              точки на исходную линию (доля >= split_fraction → на новую половину).
  NODE      — объект привязан к узлу (nodeid): следует за своим узлом; узел nodeid2
              исходной линии теперь принадлежит новой половине.
  REVIEW    — нет ни геометрии, ни узла (задвижки, диафрагмы, элеваторы, насосы):
              автоматически НЕ переносим (остаётся на первой половине), но помечаем
              к ручной проверке оператором — «угадывать» размещение оборудования нельзя.

Правила сверяются с реальной схемой БД при выполнении (таблицы/колонки, которых нет,
пропускаются) — это защищает от расхождений схемы между базами.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class TransferKind(str, Enum):
    GEOMETRY = "geometry"
    NODE = "node"
    REVIEW = "review"


@dataclass(frozen=True)
class TransferRule:
    table: str
    kind: TransferKind
    # для NODE — колонка узла установки; для остальных не используется
    node_column: Optional[str] = None


# Карта правил. Добавление новой зависимой таблицы = одна строка здесь.
#
# ВАЖНАЯ ПОПРАВКА ПО ФАКТУ СХЕМЫ (проверено на боевой БД):
# «геометрические» таблицы (ugol_povorota_truboprovoda, lyuki, opora, vvody_v_zdanie,
# perehod_diametra и т.п.) имеют колонку `lineid`, но она **всегда NULL** — эти объекты
# привязаны к сети ПРОСТРАНСТВЕННО (по своей геометрии), а не через FK на linesobj.
# Поэтому при разрезании их переносить по lineid не нужно и нечего: принадлежность
# половине определяется координатами при чтении. Их в карту НЕ включаем.
#
# Реальную поверхность переноса образуют только таблицы, чей `lineid` действительно
# ссылается на linesobj.id:
#   NODE   — регуляторы (есть nodeid): авто-перенос по узлу установки;
#   REVIEW — оборудование (задвижки, диафрагмы, элеваторы, насосы, теплообменники…):
#            реальный FK на линию, но нет ни узла, ни позиции вдоль линии →
#            автоматически НЕ переносим, помечаем к ручной проверке оператором.
SPLIT_TRANSFER_RULES: tuple[TransferRule, ...] = (
    # Регуляторы — привязка к узлу (nodeid ссылается на nodes):
    TransferRule("pressregulators", TransferKind.NODE, node_column="nodeid"),
    TransferRule("consumptregulators", TransferKind.NODE, node_column="nodeid"),
    TransferRule("pressdropregulators", TransferKind.NODE, node_column="nodeid"),
    # Оборудование без узла и позиции — только пометка к ручной проверке:
    TransferRule("diaphragms", TransferKind.REVIEW),
    TransferRule("dampers", TransferKind.REVIEW),
    TransferRule("elevators", TransferKind.REVIEW),
    TransferRule("systemradiators", TransferKind.REVIEW),
    TransferRule("pumps", TransferKind.REVIEW),
    TransferRule("heatexchangers", TransferKind.REVIEW),
    TransferRule("airheaters", TransferKind.REVIEW),
)

# Не входят в карту намеренно:
#  - heatpipesections (паспорт 1:1) — клонируется отдельно в split_line;
#  - геометрические таблицы (lineid всегда NULL) — привязка пространственная;
#  - localhydroresistances2 (2 строки, lineid не резолвится) — до появления данных.


def _ident(name: str) -> str:
    """Простое экранирование идентификатора таблицы/колонки (двойные кавычки).

    Значения в карту правил задаём мы сами (не пользователь), но кавычим для
    единообразия и защиты от неожиданных имён из схемы.
    """
    if not name.replace("_", "").isalnum():
        raise ValueError(f"Недопустимое имя идентификатора: {name!r}")
    return '"' + name + '"'


def geometry_transfer_sql(table: str) -> str:
    """UPDATE переноса геометрического объекта на новую половину по проекции точки.

    Параметры: $1 = orig_line_id, $2 = new_line_id, $3 = split_fraction.
    Выполнять ДО усечения геометрии исходной линии (нужна полная shape L).
    """
    t = _ident(table)
    return f"""
        UPDATE {t} AS d
        SET lineid = $2
        WHERE d.lineid = $1
          AND d.shape IS NOT NULL
          AND ST_LineLocatePoint(
                (SELECT shape FROM linesobj WHERE id = $1), d.shape
              ) >= $3
        RETURNING d.id
    """


def node_transfer_sql(table: str, node_column: str) -> str:
    """UPDATE переноса объекта, привязанного к узлу nodeid2 исходной линии.

    Параметры: $1 = orig_line_id, $2 = new_line_id, $3 = orig_nodeid2.
    """
    t = _ident(table)
    col = _ident(node_column)
    return f"""
        UPDATE {t} AS d
        SET lineid = $2
        WHERE d.lineid = $1 AND d.{col} = $3
        RETURNING d.id
    """


def review_count_sql(table: str) -> str:
    """Число объектов «на ручную проверку», оставшихся на исходной линии.

    Параметр: $1 = orig_line_id.
    """
    t = _ident(table)
    return f"SELECT count(*) FROM {t} WHERE lineid = $1"


async def _table_exists(conn, table: str) -> bool:
    return bool(
        await conn.fetchval(
            "SELECT 1 FROM information_schema.tables WHERE lower(table_name)=lower($1) LIMIT 1",
            table,
        )
    )


async def _column_exists(conn, table: str, column: str) -> bool:
    return bool(
        await conn.fetchval(
            "SELECT 1 FROM information_schema.columns "
            "WHERE lower(table_name)=lower($1) AND lower(column_name)=lower($2) LIMIT 1",
            table,
            column,
        )
    )


async def transfer_dependents(
    conn,
    orig_line_id: int,
    new_line_id: int,
    split_fraction: float,
    orig_nodeid2: int,
) -> dict:
    """Переносит зависимые объекты на новую половину и возвращает отчёт.

    Должно вызываться ВНУТРИ транзакции split_line и ДО усечения геометрии
    исходной линии. Возвращает:
      {
        "moved": {table: n, ...},           # реально перенесено на новую половину
        "review": {table: n, ...},          # оставлено на первой половине, к проверке
        "skipped": [table, ...],            # таблицы/колонки отсутствуют в схеме
      }
    """
    moved: dict[str, int] = {}
    review: dict[str, int] = {}
    skipped: list[str] = []

    for rule in SPLIT_TRANSFER_RULES:
        if not await _table_exists(conn, rule.table):
            skipped.append(rule.table)
            continue

        if rule.kind is TransferKind.GEOMETRY:
            rows = await conn.fetch(geometry_transfer_sql(rule.table), orig_line_id, new_line_id, split_fraction)
            if rows:
                moved[rule.table] = len(rows)

        elif rule.kind is TransferKind.NODE:
            if not rule.node_column or not await _column_exists(conn, rule.table, rule.node_column):
                skipped.append(rule.table)
                continue
            rows = await conn.fetch(
                node_transfer_sql(rule.table, rule.node_column),
                orig_line_id,
                new_line_id,
                orig_nodeid2,
            )
            if rows:
                moved[rule.table] = len(rows)

        elif rule.kind is TransferKind.REVIEW:
            n = await conn.fetchval(review_count_sql(rule.table), orig_line_id)
            if n:
                review[rule.table] = int(n)

    return {"moved": moved, "review": review, "skipped": skipped}
