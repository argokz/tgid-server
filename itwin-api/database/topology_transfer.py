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
              автоматически НЕ переносим — «угадывать» размещение оборудования нельзя.
              Сценарий разрешения (B2): dry-run перечисляет объекты поштучно
              (`review_items`), оператор указывает, какие уходят на вторую половину
              (`review_to_new`), без решения запись разрезания отклоняется (409).

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


# Колонки, по которым оператор узнаёт объект «на ручную проверку» в превью разрезания.
REVIEW_LABEL_COLUMNS: dict[str, tuple[str, ...]] = {
    "dampers": ("name", "diametercondit", "damperarmaturestateid"),
    "diaphragms": ("throtdiaphloc", "diameterinternal", "entrymark"),
    "elevators": ("elevatortype", "diameternozzle", "entrymark"),
    "systemradiators": ("name", "type", "count"),
    "pumps": ("number", "thrust", "pumpstationid"),
    "heatexchangers": ("heatexchtype", "heatexchcode", "location"),
    "airheaters": ("airheatertype", "location"),
}


def review_items_sql(table: str, columns: tuple[str, ...]) -> str:
    """Объекты на ручную проверку с опознавательными колонками. Параметр: $1 = line_id."""
    cols = "".join(f", {_ident(c)}" for c in columns)
    return f"SELECT id{cols} FROM {_ident(table)} WHERE lineid = $1 ORDER BY id"


def review_transfer_sql(table: str) -> str:
    """Перенос выбранных оператором объектов на новую половину.

    Параметры: $1 = orig_line_id, $2 = new_line_id, $3 = id[]; только объекты исходной линии.
    """
    return f"UPDATE {_ident(table)} SET lineid = $2 WHERE lineid = $1 AND id = ANY($3::int[]) RETURNING id"


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


_NODE_REF_CACHE: list[tuple[str, str]] | None = None

# Ссылки на узел, чьё имя не начинается с nodeid, но по смыслу — тот же FK на nodes.id:
# internalnodeid — узел-владелец внутренней схемы (ИТП потребителя), remontnodeid — узел ремонта.
EXTRA_NODE_REF_COLUMNS: tuple[tuple[str, str], ...] = (
    ("nodes", "internalnodeid"),
    ("linesobj", "internalnodeid"),
    ("texts", "internalnodeid"),
    ("defect", "remontnodeid"),
)


def _is_node_ref_column(table: str, column: str) -> bool:
    t, c = table.lower(), column.lower()
    if t == "linesobj" and c in {"nodeid1", "nodeid2"}:
        return False  # инцидентные линии считаются и переносятся отдельно
    return c.startswith("nodeid") or (t, c) in EXTRA_NODE_REF_COLUMNS


async def _node_ref_columns(conn) -> list[tuple[str, str]]:
    """Все (таблица, колонка), ссылающиеся на узел, кроме nodeid1/nodeid2 самой linesobj.

    nodeid* числового типа + EXTRA_NODE_REF_COLUMNS. Кэшируется — набор таблиц
    в рамках одной БД не меняется.
    """
    global _NODE_REF_CACHE
    if _NODE_REF_CACHE is None:
        rows = await conn.fetch(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
              AND (lower(column_name) LIKE 'nodeid%'
                   OR lower(column_name) IN ('internalnodeid', 'remontnodeid'))
              -- nodeid текстового типа (импорт из внешних систем) с id узла не сравнить
              AND data_type IN ('integer', 'bigint', 'smallint', 'numeric')
            """
        )
        _NODE_REF_CACHE = [
            (r["table_name"], r["column_name"])
            for r in rows
            if _is_node_ref_column(r["table_name"], r["column_name"])
        ]
    return _NODE_REF_CACHE


async def node_dependency_report(conn, node_id: int) -> dict:
    """Что ссылается на узел, кроме инцидентных линий: {table.column: count} для count>0."""
    deps: dict[str, int] = {}
    for table, col in await _node_ref_columns(conn):
        try:
            # savepoint: отчёт вызывается внутри транзакций delete/merge, и ошибка
            # одного запроса без него обрывает всю транзакцию
            async with conn.transaction():
                n = await conn.fetchval(f'SELECT count(*) FROM {_ident(table)} WHERE {_ident(col)} = $1', node_id)
        except Exception:  # noqa: BLE001 - таблица могла исчезнуть/сменить тип
            continue
        if n:
            deps[f"{table}.{col}"] = int(n)
    return deps


async def line_dependency_report(conn, line_id: int) -> dict:
    """Оборудование, ссылающееся на линию через lineid: {table: count} для count>0.

    Использует те же таблицы, что и перенос при разрезании (реальный FK на linesobj).
    heatpipesections (паспорт 1:1) не включается — он снимается вместе с линией.
    """
    deps: dict[str, int] = {}
    for rule in SPLIT_TRANSFER_RULES:
        if not await _table_exists(conn, rule.table):
            continue
        n = await conn.fetchval(f'SELECT count(*) FROM {_ident(rule.table)} WHERE lineid = $1', line_id)
        if n:
            deps[rule.table] = int(n)
    return deps


async def transfer_dependents(
    conn,
    orig_line_id: int,
    new_line_id: int,
    split_fraction: float,
    orig_nodeid2: int,
    review_to_new: Optional[dict] = None,
) -> dict:
    """Переносит зависимые объекты на новую половину и возвращает отчёт.

    Должно вызываться ВНУТРИ транзакции split_line и ДО усечения геометрии
    исходной линии. review_to_new — решение оператора по REVIEW-оборудованию
    ({table: [id, …]} → на новую половину; остальное остаётся на первой). Возвращает:
      {
        "moved": {table: n, ...},           # реально перенесено на новую половину
        "review": {table: n, ...},          # оборудование без узла/позиции на участке (решает оператор)
        "review_items": {table: [{id, attrs}]},  # оно же поштучно — для превью
        "review_moved": {table: [id, ...]}, # перенесено по решению оператора
        "skipped": [table, ...],            # таблицы/колонки отсутствуют в схеме
      }
    ValueError — в review_to_new id, которого нет на исходном участке.
    """
    moved: dict[str, int] = {}
    review: dict[str, int] = {}
    review_items: dict[str, list] = {}
    review_moved: dict[str, list] = {}
    skipped: list[str] = []
    wanted = {str(t): {int(i) for i in ids} for t, ids in (review_to_new or {}).items() if ids}
    review_tables = {r.table for r in SPLIT_TRANSFER_RULES if r.kind is TransferKind.REVIEW}
    unknown_tables = sorted(set(wanted) - review_tables)
    if unknown_tables:
        raise ValueError(f"Решение по таблицам вне ручной проверки: {', '.join(unknown_tables)}")

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
            label_cols = tuple(
                [c for c in REVIEW_LABEL_COLUMNS.get(rule.table, ()) if await _column_exists(conn, rule.table, c)]
            )
            rows = await conn.fetch(review_items_sql(rule.table, label_cols), orig_line_id)
            if not rows:
                if wanted.get(rule.table):
                    raise ValueError(f"{rule.table}: на участке {orig_line_id} нет объектов для переноса")
                continue
            review[rule.table] = len(rows)
            review_items[rule.table] = [
                {"id": r["id"], "attrs": {c: r[c] for c in label_cols if r[c] is not None}} for r in rows
            ]
            ids = wanted.get(rule.table)
            if ids:
                present = {r["id"] for r in rows}
                missing = sorted(ids - present)
                if missing:
                    raise ValueError(
                        f"{rule.table}: объекты {', '.join(map(str, missing))} не на участке {orig_line_id}"
                    )
                done = await conn.fetch(review_transfer_sql(rule.table), orig_line_id, new_line_id, sorted(ids))
                review_moved[rule.table] = sorted(r["id"] for r in done)
                moved[rule.table] = moved.get(rule.table, 0) + len(done)

    return {
        "moved": moved,
        "review": review,
        "review_items": review_items,
        "review_moved": review_moved,
        "skipped": skipped,
    }


# ---------------------------------------------------------------------------
# Слияние узлов (merge): перенос всех ссылок на узел-источник на целевой узел
# ---------------------------------------------------------------------------
#
# Правила по классам таблиц (docs/stage-b-topology-editor-plan.md, класс 4):
#   MULTI     — у узла может быть много таких записей (потребители, направления,
#               регуляторы, приборы учёта, журналы): переносятся всегда;
#   SINGLETON — не более одной записи на узел (камера, источник, насосная станция,
#               узел подпитки/установки давления…): переносится, только если у
#               целевого узла такой записи нет, иначе — блокер (не угадываем, какая верна);
#   INTERNAL  — узел-владелец внутренней схемы (internalnodeid): переносится, только если
#               у целевого узла своей внутренней схемы нет, иначе — блокер;
#   RESULT    — выход расчёта (*_out): не переносится, устаревает до следующего расчёта.
MERGE_SINGLETON_TABLES = frozenset({
    "connectnodes",
    "heatchambers",
    "heatsources",
    "pumpstations",
    "refillnodes",
    "setpressnodes",
    "threewayvalves",
})


class MergeRefKind(str, Enum):
    MULTI = "multi"
    SINGLETON = "singleton"
    INTERNAL = "internal"
    RESULT = "result"


def merge_ref_kind(table: str, column: str) -> MergeRefKind:
    t, c = table.lower(), column.lower()
    if t.endswith("_out"):
        return MergeRefKind.RESULT
    if c == "internalnodeid":
        return MergeRefKind.INTERNAL
    if t in MERGE_SINGLETON_TABLES:
        return MergeRefKind.SINGLETON
    return MergeRefKind.MULTI


def node_ref_count_sql(table: str, column: str) -> str:
    """Параметры: $1 = node_id."""
    return f"SELECT count(*) FROM {_ident(table)} WHERE {_ident(column)} = $1"


def node_ref_transfer_sql(table: str, column: str) -> str:
    """Перенос ссылки с узла-источника на целевой. Параметры: $1 = source, $2 = target."""
    col = _ident(column)
    return f"UPDATE {_ident(table)} SET {col} = $2 WHERE {col} = $1"


def _rowcount(status: str) -> int:
    """'UPDATE 3' → 3 (статус asyncpg.execute)."""
    try:
        return int(str(status).rsplit(" ", 1)[-1])
    except (ValueError, IndexError):
        return 0


async def plan_node_merge(conn, source_node_id: int, target_node_id: int) -> dict:
    """Что будет перенесено при слиянии source → target и что блокирует.

    Возвращает {"transfer": {"t.c": n}, "results_skipped": {"t.c": n},
    "conflicts": {"t.c": {"source": n, "target": m}}}. Ничего не меняет.
    """
    transfer: dict[str, int] = {}
    results: dict[str, int] = {}
    conflicts: dict[str, dict] = {}
    for table, col in await _node_ref_columns(conn):
        key = f"{table}.{col}"
        kind = merge_ref_kind(table, col)
        try:
            async with conn.transaction():  # savepoint: битая таблица не рвёт транзакцию
                n_src = await conn.fetchval(node_ref_count_sql(table, col), source_node_id)
                n_tgt = 0
                if n_src and kind in (MergeRefKind.SINGLETON, MergeRefKind.INTERNAL):
                    n_tgt = await conn.fetchval(node_ref_count_sql(table, col), target_node_id)
        except Exception:  # noqa: BLE001 - таблица могла исчезнуть/сменить тип
            continue
        if not n_src:
            continue
        if kind is MergeRefKind.RESULT:
            results[key] = int(n_src)
        elif n_tgt:
            conflicts[key] = {"source": int(n_src), "target": int(n_tgt)}
        else:
            transfer[key] = int(n_src)
    return {"transfer": transfer, "results_skipped": results, "conflicts": conflicts}


async def apply_node_merge(conn, source_node_id: int, target_node_id: int, plan: dict) -> dict:
    """Переносит ссылки из plan["transfer"] на целевой узел; {"t.c": перенесено}.

    Вызывать внутри транзакции слияния, после проверки блокеров. Ошибка любой
    таблицы — исключение (вся операция откатывается), молча не пропускаем.
    """
    moved: dict[str, int] = {}
    for key in plan.get("transfer", {}):
        table, col = key.split(".", 1)
        status = await conn.execute(node_ref_transfer_sql(table, col), source_node_id, target_node_id)
        moved[key] = _rowcount(status)
    return moved


# ---------------------------------------------------------------------------
# Разворот участка (reverse): что зависит от направления nodeid1 → nodeid2
# ---------------------------------------------------------------------------
#
# Эталон — десктоп gid8 GidWidget::swap (gidr_del.cpp): меняет nodeID1/nodeID2,
# разворачивает координаты и externalSignLineID 4 <-> 5 (подающий-обратный <->
# обратный-подающий); оборудование не трогает. Классы оборудования по смыслу для sety:
#   DIRECTIONAL — действие задаётся направлением участка (насос создаёт напор
#                 nodeid1 -> nodeid2, обратный клапан пропускает nodeid1 -> nodeid2,
#                 элеватор: сопло -> камера смешения). Колонки направления у них нет,
#                 поэтому направление действия меняется вместе с участком — нужно
#                 явное подтверждение оператора;
#   NODE_BOUND  — привязаны к абсолютному узлу (nodeid — регулируемый узел РД/РР):
#                 узел сохраняется, меняется его положение (начало <-> конец). Клапан
#                 регулятора при этом тоже «разворачивается» (sety считает расход против
#                 участка режимом реверса РД), поэтому они же входят в DIRECTIONAL;
#   NEUTRAL     — от направления не зависят (задвижки, диафрагмы: throtdiaphloc —
#                 функциональное место «Подпорная/Отопление/Вход ТП…», а не начало/конец).
REVERSE_DIRECTIONAL_TABLES: tuple[str, ...] = ("pumps", "reversevalves", "elevators")
REVERSE_NODE_BOUND_TABLES: tuple[str, ...] = (
    "pressregulators", "consumptregulators", "pressdropregulators", "bypass", "regularmatures",
)
REVERSE_NEUTRAL_TABLES: tuple[str, ...] = (
    "dampers", "diaphragms", "systemradiators", "heatexchangers", "airheaters", "localhydroresistances2",
)
EXTERNAL_SIGN_LINE_SWAP = {4: 5, 5: 4}


def reversed_external_sign(value):
    return EXTERNAL_SIGN_LINE_SWAP.get(value, value) if value is not None else None


def _end_position(node_id, nodeid1, nodeid2) -> str:
    if node_id is not None and node_id == nodeid1:
        return "start"
    if node_id is not None and node_id == nodeid2:
        return "end"
    return "other"


async def plan_line_reverse(conn, line_id: int, nodeid1: int, nodeid2: int) -> dict:
    """Отчёт «что поменяется» при развороте участка (без изменений в БД)."""
    directional: dict[str, int] = {}
    neutral: dict[str, int] = {}
    node_bound: dict[str, list] = {}
    for table in REVERSE_DIRECTIONAL_TABLES + REVERSE_NEUTRAL_TABLES:
        if not await _table_exists(conn, table):
            continue
        n = await conn.fetchval(f"SELECT count(*) FROM {_ident(table)} WHERE lineid = $1", line_id)
        if n:
            (directional if table in REVERSE_DIRECTIONAL_TABLES else neutral)[table] = int(n)
    for table in REVERSE_NODE_BOUND_TABLES:
        if not await _table_exists(conn, table) or not await _column_exists(conn, table, "nodeid"):
            continue
        rows = await conn.fetch(f"SELECT id, nodeid FROM {_ident(table)} WHERE lineid = $1 ORDER BY id", line_id)
        if rows:
            directional[table] = len(rows)
            node_bound[table] = [
                {
                    "id": r["id"],
                    "nodeid": r["nodeid"],
                    "position_before": _end_position(r["nodeid"], nodeid1, nodeid2),
                    "position_after": _end_position(r["nodeid"], nodeid2, nodeid1),
                }
                for r in rows
            ]
    diaphragm_locations: dict[str, int] = {}
    if neutral.get("diaphragms") and await _column_exists(conn, "diaphragms", "throtdiaphloc"):
        for r in await conn.fetch(
            "SELECT coalesce(throtdiaphloc, '') AS loc, count(*) AS n FROM diaphragms WHERE lineid = $1 GROUP BY 1",
            line_id,
        ):
            diaphragm_locations[r["loc"] or "—"] = int(r["n"])
    return {
        "directional": directional,
        "node_bound": node_bound,
        "neutral": neutral,
        "diaphragm_locations": diaphragm_locations,
    }
