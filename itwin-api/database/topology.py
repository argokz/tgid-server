"""Изменение топологии сети: узлы, участки, разрезание, слияние, разворот, геометрия, отмена.

Все операции (этап 8, Stage B):
  * транзакционны: изменения, перенос зависимых объектов, запись audit_log и журнала
    отмены — в одной транзакции (audit через SAVEPOINT той же транзакции);
  * с оптимистичной блокировкой: клиент передаёт версию объекта, которую он видел
    (`version_token`), сервер берёт строку `SELECT … FOR UPDATE` и при несовпадении
    отвечает TopologyConflictError (HTTP 409 «объект изменён другим пользователем»);
  * «опасные» операции (split, merge, reverse) поддерживают dry-run: выполняются в
    транзакции и откатываются, возвращая отчёт «что и куда будет перенесено»;
  * отменяемы (B5): before-image затронутых строк пишется в topology_undo_log
    (database/topology_journal.py), `undo_last_operation` откатывает последнюю операцию
    пользователя, если её объекты после неё не менялись (иначе 409).
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from audit import write_audit_log
from database.connect import get_pool
from database.outage_simulation import invalidate_outage_cache
from database.topology_journal import (
    JOURNAL_TABLE,
    OperationJournal,
    changed_since,
    current_hashes,
    journal_available,
    restore_rows,
    table_columns,
)
from database.topology_transfer import (
    SPLIT_TRANSFER_RULES,
    _ident,
    apply_node_merge,
    line_dependency_report,
    node_dependency_report,
    plan_line_reverse,
    plan_node_merge,
    reversed_external_sign,
    transfer_dependents,
)

logger = logging.getLogger(__name__)


class _DryRunRollback(Exception):
    """Служебное исключение: форсирует ROLLBACK транзакции dry-run, неся отчёт."""

    def __init__(self, payload: dict):
        self.payload = payload


# Допуск для концов новой геометрии участка относительно его узлов, м (SRID 9998 — метры).
GEOMETRY_ENDPOINT_TOLERANCE_M = 5.0
# Радиус поиска узла-образца для нового узла (фрагмент, код, признак подачи/обратки), м.
NEW_NODE_REFERENCE_RADIUS_M = 300.0
# Парная труба при развороте: макс. расхождение трасс подачи и обратки (Хаусдорф), м.
PAIR_LINE_MAX_DEVIATION_M = 1.0

# Паспорт нового участка (create_line) — конструктив трубы от участка-образца: смежного
# (через общий узел) или ближайшего в радиусе NEW_NODE_REFERENCE_RADIUS_M того же фрагмента
# и той же внутренней схемы. Без паспорта участок не попадает ни в слой карты (SQL view
# GeoServer `heatpipesections` — INNER JOIN паспорта), ни в расчёт (sety читает участки
# из heatpipesections); умолчания таблицы (Ду 1000 мм) дают неверную гидравлику.
# Состояние (открыт/закрыт), повреждения, даты и номера образца не копируются.
PASSPORT_TEMPLATE_COLUMNS: tuple[str, ...] = (
    "standardid", "standardtubelink", "tubescount",
    "diameterinternal", "diametercondit", "diameterexternal", "wallthickness",
    "tuberoughness", "locallosesshare", "varcoeffidflow", "varcoeffidret",
    "calcheatlossignid", "tubingtypeid", "channelid", "constrchanwidth", "constrchanheight",
    "heattestscoeff", "isolmaterialid", "isolthickness", "isolmaterialhccoeff",
    "pipelinelayingdepth", "isolhtcoeffabove", "isolhtcoeffunder", "airgroundhtcoeffunder",
    "groundhccoeff", "pipelineaxesdist", "tubecharactid", "tubetypeid", "tubematerial",
    "externmaterialid", "isolationtypeid", "externcoverthick", "anticorrmaterialid",
    "organizationid", "magistralsite", "distsite", "net", "nettype", "magistral",
)


class TopologyDependencyError(Exception):
    """Операция заблокирована зависимыми объектами (для ответа 409 с отчётом)."""

    def __init__(self, message: str, blockers: dict):
        super().__init__(message)
        self.blockers = blockers


class TopologyConflictError(Exception):
    """Объект изменён/удалён другим пользователем после того, как клиент его прочитал (409)."""

    def __init__(self, conflicts: dict, message: str = "Объект изменён другим пользователем"):
        super().__init__(message)
        self.conflicts = conflicts


class TopologyNothingToUndo(Exception):
    """У пользователя нет неотменённых операций (404)."""


class TopologyObjectMismatch(Exception):
    """Клиент прислал id не того объекта (409 object_mismatch, операция не выполняется).

    QA F12/F54: карточка участка из слоя GeoServer `id_heatpipesections` несла
    heatpipesections.id вместо linesobj.id — у 20 тыс. таких id есть другой живой участок.
    Клиент передаёт heatpipesections.id из карточки (expected_section_id), сервер сверяет его
    с паспортом участка line_id и отказывает при расхождении.
    """

    def __init__(self, message: str, details: dict):
        super().__init__(message)
        self.details = details


async def _fetch_line_ref(conn, *, line_id: Optional[int] = None, section_id: Optional[int] = None):
    """Участок (linesobj) и его паспорт трубы (heatpipesections, 1:1 по lineid)."""
    if line_id is not None:
        return await conn.fetchrow(
            "SELECT l.id AS line_id, h.id AS section_id, l.fileid, l.nodeid1, l.nodeid2, "
            "COALESCE(l.removed, 0) <> 0 AS removed "
            "FROM linesobj l "
            "LEFT JOIN LATERAL (SELECT id FROM heatpipesections WHERE lineid = l.id ORDER BY id LIMIT 1) h ON true "
            "WHERE l.id = $1",
            line_id,
        )
    return await conn.fetchrow(
        "SELECT l.id AS line_id, h.id AS section_id, l.fileid, l.nodeid1, l.nodeid2, "
        "COALESCE(l.removed, 0) <> 0 AS removed "
        "FROM heatpipesections h JOIN linesobj l ON l.id = h.lineid "
        "WHERE h.id = $1",
        section_id,
    )


async def get_line_ref(line_id: Optional[int] = None, section_id: Optional[int] = None) -> Optional[dict]:
    """Ссылка «участок ↔ паспорт трубы» по linesobj.id или heatpipesections.id (None — нет)."""
    if (line_id is None) == (section_id is None):
        raise ValueError("Укажите ровно один из параметров: line_id или section_id")
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await _fetch_line_ref(conn, line_id=line_id, section_id=section_id)
    return dict(row) if row else None


async def _check_line_section(conn, line_id: int, expected_section_id: Optional[int]) -> None:
    """Сверка: expected_section_id — паспорт (heatpipesections.id) именно участка line_id."""
    if expected_section_id is None:
        return
    row = await _fetch_line_ref(conn, line_id=line_id)
    actual = row["section_id"] if row else None
    if actual == expected_section_id:
        return
    owner = await _fetch_line_ref(conn, section_id=expected_section_id)
    owner_line = owner["line_id"] if owner else None
    message = (
        f"Участок {line_id} не соответствует карточке: паспорт трубы {expected_section_id} "
        + (f"относится к участку {owner_line}" if owner_line else "не найден")
        + (f", у участка {line_id} паспорт {actual}" if actual else f", у участка {line_id} паспорта нет")
        + ". Операция отменена — откройте карточку участка заново."
    )
    raise TopologyObjectMismatch(
        message,
        {"line_id": line_id, "expected_section_id": expected_section_id,
         "actual_section_id": actual, "section_line_id": owner_line},
    )


# ---------------------------------------------------------------------------
# Версии объектов (оптимистичная блокировка)
# ---------------------------------------------------------------------------

_VERSION_TABLES = {"node": "nodes", "line": "linesobj"}


def version_token(archivechangedate: Optional[datetime], xmin: Any) -> str:
    """Версия строки: «archivechangedate#xmin».

    archivechangedate меняют редакторы (десктоп и этот API), xmin — любая запись строки
    (включая правку атрибутов карточкой, которая дату не трогает).
    """
    ts = archivechangedate.isoformat() if archivechangedate else ""
    return f"{ts}#{xmin}"


def _parse_ts(value: str) -> Optional[datetime]:
    v = value.strip()
    if not v:
        return None
    return datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)


def version_matches(expected: str, archivechangedate: Optional[datetime], xmin: Any) -> bool:
    """Совпадает ли версия клиента с текущей строкой.

    Полный токен («…#xmin», из /topology/versions и dry-run) сравнивается точно;
    голая дата (archivechangedate из карточки объекта) — только с датой.
    """
    if "#" in expected:
        return expected == version_token(archivechangedate, xmin)
    try:
        return _parse_ts(expected) == archivechangedate
    except ValueError:
        return False


async def _lock_objects(conn, kind: str, ids: list[int]) -> dict:
    """SELECT … FOR UPDATE строк узлов/участков (в порядке id — без взаимных блокировок)."""
    table = _VERSION_TABLES[kind]
    rows = await conn.fetch(
        f"SELECT id, COALESCE(removed, 0) AS removed, archivechangedate, xmin::text AS xmin "
        f"FROM {table} WHERE id = ANY($1::int[]) ORDER BY id FOR UPDATE",
        list(ids),
    )
    return {r["id"]: r for r in rows}


def _check_versions(kind: str, rows: dict, expected: dict) -> None:
    """expected: {id: версия | None}; None — клиент версию не передал (не проверяем)."""
    conflicts: dict = {}
    for oid, exp in expected.items():
        if exp is None:
            continue
        row = rows.get(oid)
        if row is None or row["removed"]:
            conflicts[f"{kind}:{oid}"] = {"expected": exp, "actual": None, "removed": True}
        elif not version_matches(exp, row["archivechangedate"], row["xmin"]):
            conflicts[f"{kind}:{oid}"] = {
                "expected": exp,
                "actual": version_token(row["archivechangedate"], row["xmin"]),
                "changed_at": row["archivechangedate"].isoformat() if row["archivechangedate"] else None,
                "removed": False,
            }
    if conflicts:
        raise TopologyConflictError(conflicts)


async def _lock_active(conn, kind: str, ids: list[int], expected: Optional[dict] = None) -> dict:
    """Блокирует строки, проверяет версии; отсутствующий/удалённый объект без версии — ValueError."""
    rows = await _lock_objects(conn, kind, ids)
    _check_versions(kind, rows, expected or {})
    missing = [oid for oid in ids if oid not in rows or rows[oid]["removed"]]
    if missing:
        what = "Узел" if kind == "node" else "Участок"
        raise ValueError(f"{what} {', '.join(map(str, missing))} не найден или удалён")
    return rows


def _tokens(kind: str, rows: dict) -> dict:
    return {f"{kind}:{oid}": version_token(r["archivechangedate"], r["xmin"]) for oid, r in rows.items()}


async def _versions(conn, kind: str, ids: list[int]) -> dict:
    if not ids:
        return {}
    table = _VERSION_TABLES[kind]
    rows = await conn.fetch(
        f"SELECT id, archivechangedate, xmin::text AS xmin FROM {table} WHERE id = ANY($1::int[])",
        list(ids),
    )
    return {f"{kind}:{r['id']}": version_token(r["archivechangedate"], r["xmin"]) for r in rows}


async def get_versions(node_ids: list[int], line_ids: list[int]) -> dict:
    """Текущие версии узлов и участков (клиент запоминает их при выборе объекта)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        result: dict = {"nodes": {}, "lines": {}}
        for kind, ids, key in (("node", node_ids, "nodes"), ("line", line_ids, "lines")):
            if not ids:
                continue
            rows = await conn.fetch(
                f"SELECT id, COALESCE(removed, 0) AS removed, archivechangedate, xmin::text AS xmin "
                f"FROM {_VERSION_TABLES[kind]} WHERE id = ANY($1::int[])",
                list(ids),
            )
            for r in rows:
                result[key][str(r["id"])] = {
                    "version": version_token(r["archivechangedate"], r["xmin"]),
                    "archivechangedate": r["archivechangedate"].isoformat() if r["archivechangedate"] else None,
                    "removed": bool(r["removed"]),
                }
        return result


# ---------------------------------------------------------------------------
# Транзакция операции: группа аудита + журнал отмены
# ---------------------------------------------------------------------------

class _Op:
    """Контекст операции в транзакции: группа изменений, журнал before-image, аудит."""

    def __init__(self, conn, journal: OperationJournal, group_id: str, actor: Optional[str]):
        self.conn = conn
        self.journal = journal
        self.group_id = group_id
        self.actor = actor

    async def audit(self, operation: str, table: str, record_id: Optional[int], data: dict) -> None:
        if self.actor:
            await write_audit_log(
                changed_by=self.actor,
                operation=operation,
                table_name=table,
                record_id=record_id,
                new_data=data,
                change_group_id=self.group_id,
                conn=self.conn,
            )


def _journal_summary(operation: str, result: dict) -> dict:
    """Краткое описание операции для списка отмены (без громоздких отчётов)."""
    keep = (
        "id", "node_id", "line_id", "pair_line_id", "new_node_id", "new_line_id",
        "target_node_id", "source_node_id", "removed_lines", "relinked_lines", "fileid",
        "created_nodes", "created_lines", "updated_nodes", "mode",
    )
    return {"operation": operation, **{k: result[k] for k in keep if k in result}}


async def _run(dry_run: bool, body, operation: Optional[str] = None, actor: Optional[str] = None):
    """Выполняет body(conn, op) в транзакции; dry_run — откатывает и возвращает отчёт.

    operation задан (и не dry-run) — после body пишется запись журнала отмены, её id
    возвращается в `operation_id` (None — журнал на этой БД не установлен).
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                group_id = str(uuid.uuid4())
                if not dry_run:
                    # триггеры legacy-аудита (log_changes) пишут строки с этой группой
                    await conn.execute("SELECT set_config('tgid.current_group_id', $1, true)", group_id)
                journal = await OperationJournal.open(conn, dry_run=dry_run or operation is None)
                op = _Op(conn, journal, group_id, actor)
                result = await body(conn, op)
                if dry_run:
                    raise _DryRunRollback({"dry_run": True, **result})
                if operation:
                    result["operation_id"] = await journal.commit(
                        conn,
                        actor=actor,
                        operation=operation,
                        group_id=group_id,
                        summary=_journal_summary(operation, result),
                    )
                return result
        except _DryRunRollback as e:
            return e.payload


async def _capture_lines_with_passports(conn, op: _Op, line_ids: list[int]) -> None:
    if not op.journal.enabled or not line_ids:
        return
    await op.journal.capture_ids(conn, "linesobj", line_ids)
    await op.journal.capture(conn, "heatpipesections", "_r.lineid = ANY($1::int[])", list(line_ids))


async def _capture_incident_lines(conn, op: _Op, node_ids: list[int]) -> None:
    if not op.journal.enabled:
        return
    ids = await op.journal.capture(
        conn, "linesobj", "(_r.nodeid1 = ANY($1::int[]) OR _r.nodeid2 = ANY($1::int[]))", list(node_ids),
    )
    if ids:
        await op.journal.capture(conn, "heatpipesections", "_r.lineid = ANY($1::int[])", ids)


# ---------------------------------------------------------------------------
# Узлы
# ---------------------------------------------------------------------------

async def move_node(
    node_id: int,
    lng: float,
    lat: float,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    async def body(conn, op):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
        await op.journal.capture_ids(conn, "nodes", [node_id])
        await _capture_incident_lines(conn, op, [node_id])
        now = datetime.now()
        await conn.execute(
            """
            UPDATE nodes SET
              shape = ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998),
              x = ST_X(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              y = -ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              archivechangedate = $4
            WHERE id = $3
            """,
            lng, lat, node_id, now,
        )
        # Концы инцидентных участков следуют за узлом
        await conn.execute(
            """
            UPDATE linesobj
            SET shape = ST_SetPoint(shape, 0, (SELECT shape FROM nodes WHERE id = $1)),
                archivechangedate = $2
            WHERE nodeid1 = $1 AND shape IS NOT NULL
            """,
            node_id, now,
        )
        await conn.execute(
            """
            UPDATE linesobj
            SET shape = ST_SetPoint(shape, ST_NumPoints(shape) - 1, (SELECT shape FROM nodes WHERE id = $1)),
                archivechangedate = $2
            WHERE nodeid2 = $1 AND shape IS NOT NULL
            """,
            node_id, now,
        )
        # Длина паспорта труб следует за геометрией — иначе расчёт получит устаревшую длину
        affected = await conn.fetch(
            """
            UPDATE heatpipesections h
            SET pipesectlength = ST_Length(l.shape)
            FROM linesobj l
            WHERE h.lineid = l.id
              AND (l.nodeid1 = $1 OR l.nodeid2 = $1)
              AND l.shape IS NOT NULL
            RETURNING h.lineid
            """,
            node_id,
        )
        result = {
            "node_id": node_id,
            "recalculated_lines": len(affected),
            "versions": await _versions(conn, "node", [node_id]),
        }
        await op.audit("MOVE", "nodes", node_id, {"lng": lng, "lat": lat, **result})
        return result

    return await _run(False, body, "MOVE", actor)


async def delete_node(
    node_id: int,
    cascade: bool = False,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Безопасное удаление узла.

    По умолчанию отказывает, если на узле висят инцидентные активные линии или
    другие ссылки (nodeid в зависимых таблицах) — чтобы не осиротить объекты молча.
    cascade=True — удалить узел вместе с инцидентными линиями и их паспортами.
    """
    async def body(conn, op):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
        now = datetime.now()
        incident_lines = await conn.fetch(
            "SELECT id FROM linesobj WHERE (nodeid1 = $1 OR nodeid2 = $1) AND COALESCE(removed, 0) = 0",
            node_id,
        )
        node_deps = await node_dependency_report(conn, node_id)
        if not cascade and (incident_lines or node_deps):
            raise TopologyDependencyError(
                "Узел нельзя удалить: есть зависимые объекты",
                blockers={
                    "incident_lines": [r["id"] for r in incident_lines],
                    "references": node_deps,
                },
            )
        removed_lines = [r["id"] for r in incident_lines]
        await op.journal.capture_ids(conn, "nodes", [node_id])
        await _capture_lines_with_passports(conn, op, removed_lines)
        if removed_lines:
            await conn.execute(
                "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                removed_lines, now,
            )
            await _soft_remove_heatpipesections(conn, removed_lines, now)
        await conn.execute("UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1", node_id, now)
        result = {"node_id": node_id, "removed_lines": removed_lines, "cleared_references": node_deps}
        await op.audit("DELETE", "nodes", node_id, {"cascade": cascade, **result})
        return result

    result = await _run(False, body, "DELETE_NODE", actor)
    invalidate_outage_cache()
    return result


async def _new_node_reference(
    conn,
    lng: float,
    lat: float,
    fileid: Optional[int],
    near_node_id: Optional[int],
    near_line_id: Optional[int],
) -> dict:
    """Откуда новый узел берёт фрагмент (fileid), код (externalcodeid) и признак (externalsignid).

    Без fileid/externalcodeid расчёт (sety читает узлы по fileID и JOIN externalCodes) узел
    не увидит, а merge с соседним узлом ответит «разные фрагменты». Как при split:
      1. явно указанный узел-образец (near_node_id);
      2. участок (near_line_id): его начальный узел, fileid участка, internalnodeid участка;
      3. ближайший активный узел основной сети в радиусе NEW_NODE_REFERENCE_RADIUS_M
         (при явном fileid — ближайший узел этого фрагмента).
    Явный fileid имеет приоритет; код тогда — от узла этого фрагмента или первый код фрагмента.
    """
    ref = None
    source = None
    if near_node_id is not None:
        ref = await conn.fetchrow(
            """
            SELECT id, fileid, externalcodeid, externalsignid, internalnodeid
            FROM nodes WHERE id = $1 AND COALESCE(removed, 0) = 0
            """,
            near_node_id,
        )
        if ref is None:
            raise ValueError(f"Узел-образец {near_node_id} не найден или удалён")
        source = "node"
    elif near_line_id is not None:
        ref = await conn.fetchrow(
            """
            SELECT n1.id, COALESCE(n1.fileid, l.fileid) AS fileid, n1.externalcodeid,
                   n1.externalsignid, l.internalnodeid
            FROM linesobj l LEFT JOIN nodes n1 ON n1.id = l.nodeid1
            WHERE l.id = $1 AND COALESCE(l.removed, 0) = 0
            """,
            near_line_id,
        )
        if ref is None:
            raise ValueError(f"Участок-образец {near_line_id} не найден или удалён")
        source = "line"
    if ref is None or (fileid is not None and ref["fileid"] != fileid):
        nearest = await conn.fetchrow(
            """
            WITH p AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998) AS g)
            SELECT n.id, n.fileid, n.externalcodeid, n.externalsignid, n.internalnodeid,
                   ST_Distance(n.shape, p.g) AS distance
            FROM nodes n, p
            WHERE COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL AND n.fileid IS NOT NULL
              AND n.internalnodeid IS NULL
              AND ($4::int IS NULL OR n.fileid = $4)
              AND ST_DWithin(n.shape, p.g, $3)
            ORDER BY n.shape <-> p.g
            LIMIT 1
            """,
            lng, lat, NEW_NODE_REFERENCE_RADIUS_M, fileid,
        )
        if nearest is not None:
            ref, source = nearest, "nearest_node"
    if fileid is not None and (ref is None or ref["fileid"] != fileid):
        code = await conn.fetchval(
            "SELECT min(id) FROM externalcodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0", fileid,
        )
        return {"fileid": fileid, "externalcodeid": code, "externalsignid": 1,
                "internalnodeid": None, "reference_node_id": None, "source": "fileid"}
    if ref is None or ref["fileid"] is None:
        raise ValueError(
            "Не удалось определить фрагмент нового узла: рядом нет узлов сети "
            f"(радиус {NEW_NODE_REFERENCE_RADIUS_M:g} м). Укажите фрагмент (fileid) или узел-образец."
        )
    return {
        "fileid": ref["fileid"],
        "externalcodeid": ref["externalcodeid"],
        "externalsignid": ref["externalsignid"] if ref["externalsignid"] is not None else 1,
        "internalnodeid": ref["internalnodeid"],
        "reference_node_id": ref["id"],
        "source": source,
    }


async def create_node(
    lng: float,
    lat: float,
    actor: Optional[str] = None,
    fileid: Optional[int] = None,
    near_node_id: Optional[int] = None,
    near_line_id: Optional[int] = None,
) -> dict:
    """Новый узел с фрагментом/кодом/признаком от узла-образца (см. _new_node_reference)."""
    async def body(conn, op):
        ref = await _new_node_reference(conn, lng, lat, fileid, near_node_id, near_line_id)
        new_id = await conn.fetchval(
            """
            INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid,
                               fileid, externalcodeid, externalsignid, internalnodeid)
            VALUES (
              ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998),
              ST_X(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              -ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              0,
              $3,
              1, -- простой узел
              $4, $5, $6, $7
            ) RETURNING id
            """,
            lng, lat, datetime.now(),
            ref["fileid"], ref["externalcodeid"], ref["externalsignid"], ref["internalnodeid"],
        )
        op.journal.created("nodes", new_id)
        result = {
            "id": new_id,
            "fileid": ref["fileid"],
            "externalcodeid": ref["externalcodeid"],
            "externalsignid": ref["externalsignid"],
            "internalnodeid": ref["internalnodeid"],
            "reference": {"source": ref["source"], "node_id": ref["reference_node_id"]},
        }
        await op.audit("INSERT", "nodes", new_id, {"lng": lng, "lat": lat, **result})
        return result

    return await _run(False, body, "CREATE_NODE", actor)


# ---------------------------------------------------------------------------
# Участки
# ---------------------------------------------------------------------------

async def _create_line_passport(conn, line_id: int, nodeid1: int, nodeid2: int) -> dict:
    """Паспорт (heatpipesections) нового участка: конструктив от участка-образца.

    Образец — активный участок того же фрагмента и той же схемы (fileid/internalnodeid
    начального узла): сначала смежный через nodeid1/nodeid2, иначе ближайший в радиусе
    NEW_NODE_REFERENCE_RADIUS_M. Копируются PASSPORT_TEMPLATE_COLUMNS (что есть в схеме),
    длина — по геометрии нового участка. Нет образца — паспорт с умолчаниями таблицы.
    Ошибка вставки не глотается: участок без паспорта не виден ни карте, ни расчёту.
    """
    template = await conn.fetchrow(
        """
        WITH nl AS (SELECT shape FROM linesobj WHERE id = $1),
             ref AS (SELECT fileid, internalnodeid FROM nodes WHERE id = $2)
        SELECT hps.id AS passport_id, l.id AS line_id,
               (l.nodeid1 IN ($2, $3) OR l.nodeid2 IN ($2, $3)) AS adjacent
        FROM linesobj l
        JOIN heatpipesections hps ON hps.lineid = l.id
        JOIN nodes o1 ON o1.id = l.nodeid1
        CROSS JOIN nl CROSS JOIN ref
        WHERE COALESCE(l.removed, 0) = 0 AND l.id <> $1 AND l.shape IS NOT NULL
          AND o1.fileid IS NOT DISTINCT FROM ref.fileid
          AND o1.internalnodeid IS NOT DISTINCT FROM ref.internalnodeid
          AND ((l.nodeid1 IN ($2, $3) OR l.nodeid2 IN ($2, $3)) OR ST_DWithin(l.shape, nl.shape, $4))
        ORDER BY adjacent DESC, ST_Distance(l.shape, nl.shape), l.id
        LIMIT 1
        """,
        line_id, nodeid1, nodeid2, NEW_NODE_REFERENCE_RADIUS_M,
    )
    length_sql = "ST_Length((SELECT shape FROM linesobj WHERE id = $1))"
    if template is None:
        await conn.execute(
            f"INSERT INTO heatpipesections (lineid, pipesectlength) VALUES ($1, {length_sql})", line_id,
        )
        return {"source": "defaults", "template_line_id": None}
    existing = set(await table_columns(conn, "heatpipesections"))
    cols = [c for c in PASSPORT_TEMPLATE_COLUMNS if c in existing]
    target = "".join(f", {_ident(c)}" for c in cols)
    source = "".join(f", hps.{_ident(c)}" for c in cols)
    await conn.execute(
        f"INSERT INTO heatpipesections (lineid, pipesectlength{target}) "
        f"SELECT $1, {length_sql}{source} FROM heatpipesections hps WHERE hps.id = $2",
        line_id, template["passport_id"],
    )
    return {
        "source": "adjacent_line" if template["adjacent"] else "nearest_line",
        "template_line_id": template["line_id"],
    }


async def create_line(
    nodeid1: int,
    nodeid2: int,
    nodeid1_version: Optional[str] = None,
    nodeid2_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    if nodeid1 == nodeid2:
        raise ValueError("A line requires two different nodes")

    async def body(conn, op):
        # Узлы-концы блокируются: их не должны удалить/сдвинуть, пока строится участок
        await _lock_active(conn, "node", [nodeid1, nodeid2], {nodeid1: nodeid1_version, nodeid2: nodeid2_version})
        valid = await conn.fetchval(
            "SELECT count(*) FROM nodes WHERE id = ANY($1::int[]) AND shape IS NOT NULL",
            [nodeid1, nodeid2],
        )
        if valid != 2:
            raise ValueError("Both active nodes with geometry are required")
        ends = await conn.fetch(
            "SELECT id, fileid, externalcodeid, internalnodeid FROM nodes WHERE id = ANY($1::int[])",
            [nodeid1, nodeid2],
        )
        # Без фрагмента и кода узла участок не видят ни расчёт (sety: JOIN externalCodes,
        # фильтр n.fileID), ни слой карты (JOIN externalcodes) — такой участок бесполезен.
        incomplete = sorted(r["id"] for r in ends if r["fileid"] is None or r["externalcodeid"] is None)
        if incomplete:
            raise ValueError(
                "У узлов " + ", ".join(map(str, incomplete)) + " нет фрагмента или кода (externalcodeid): "
                "участок не попадёт в расчёт и на карту. Задайте узлу фрагмент/код или пересоздайте его."
            )
        if len({r["fileid"] for r in ends}) > 1:
            raise ValueError("Узлы участка из разных фрагментов: участок соединяет узлы одного фрагмента")
        if len({r["internalnodeid"] for r in ends}) > 1:
            raise ValueError("Узлы участка из разных схем (основная сеть / внутренняя схема потребителя)")
        now = datetime.now()
        line_id = await conn.fetchval(
            """
            INSERT INTO linesobj (nodeid1, nodeid2, shape, removed, archivechangedate, fileid, internalnodeid)
            VALUES (
              $1,
              $2,
              ST_MakeLine((SELECT shape FROM nodes WHERE id = $1), (SELECT shape FROM nodes WHERE id = $2)),
              0,
              $3,
              (SELECT fileid FROM nodes WHERE id = $1),
              (SELECT internalnodeid FROM nodes WHERE id = $1)
            ) RETURNING id
            """,
            nodeid1, nodeid2, now,
        )
        op.journal.created("linesobj", line_id)
        passport = await _create_line_passport(conn, line_id, nodeid1, nodeid2)
        await op.journal.created_where(conn, "heatpipesections", "_r.lineid = $1", line_id)
        result = {"id": line_id, "passport": passport}
        await op.audit("INSERT", "linesobj", line_id, {"nodeid1": nodeid1, "nodeid2": nodeid2, **result})
        return result

    return await _run(False, body, "CREATE_LINE", actor)


async def delete_line(
    line_id: int,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
    expected_section_id: Optional[int] = None,
) -> dict:
    """Мягкое удаление участка вместе с его паспортом; отчёт по зависимому оборудованию.

    Оборудование (задвижки, регуляторы…) на удалённой линии не пропадает
    (soft-delete сохраняет данные), но возвращается в отчёте, чтобы оператор
    знал, какие объекты теперь ссылаются на снятый участок.
    expected_section_id — heatpipesections.id из карточки: при расхождении 409 (F54).
    """
    async def body(conn, op):
        await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        await _check_line_section(conn, line_id, expected_section_id)
        await _capture_lines_with_passports(conn, op, [line_id])
        now = datetime.now()
        equipment = await line_dependency_report(conn, line_id)
        await conn.execute("UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = $1", line_id, now)
        await _soft_remove_heatpipesections(conn, [line_id], now)
        result = {"line_id": line_id, "dependent_equipment": equipment}
        await op.audit("DELETE", "linesobj", line_id, result)
        return result

    result = await _run(False, body, "DELETE_LINE", actor)
    invalidate_outage_cache()
    return result


async def _soft_remove_heatpipesections(conn, line_ids: list, now) -> None:
    """Мягко снимает паспорта труб снятых линий, если в таблице есть колонка removed."""
    if not line_ids:
        return
    has_removed = await conn.fetchval(
        "SELECT 1 FROM information_schema.columns "
        "WHERE lower(table_name)='heatpipesections' AND lower(column_name)='removed' LIMIT 1"
    )
    if has_removed:
        await conn.execute(
            "UPDATE heatpipesections SET removed = 1 WHERE lineid = ANY($1::int[])",
            line_ids,
        )


async def get_line_geometry(line_id: int) -> dict:
    """Полная геометрия участка (WGS84) для правки вершин + узлы-концы и версия.

    Геометрия из векторных тайлов для этого не годится: она обрезана по тайлам и упрощена.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT l.id, l.nodeid1, l.nodeid2, COALESCE(l.removed, 0) AS removed,
                   l.archivechangedate, l.xmin::text AS xmin,
                   ST_AsGeoJSON(ST_Transform(l.shape, 4326), 9) AS geojson,
                   ST_Length(l.shape) AS length,
                   ST_AsGeoJSON(ST_Transform(n1.shape, 4326), 9) AS n1,
                   ST_AsGeoJSON(ST_Transform(n2.shape, 4326), 9) AS n2
            FROM linesobj l
            LEFT JOIN nodes n1 ON n1.id = l.nodeid1
            LEFT JOIN nodes n2 ON n2.id = l.nodeid2
            WHERE l.id = $1
            """,
            line_id,
        )
    if row is None or row["removed"]:
        raise ValueError(f"Участок {line_id} не найден или удалён")
    if row["geojson"] is None:
        raise ValueError(f"У участка {line_id} нет геометрии")
    return {
        "line_id": line_id,
        "nodeid1": row["nodeid1"],
        "nodeid2": row["nodeid2"],
        "coordinates": json.loads(row["geojson"])["coordinates"],
        "node1": json.loads(row["n1"])["coordinates"] if row["n1"] else None,
        "node2": json.loads(row["n2"])["coordinates"] if row["n2"] else None,
        "length_m": round(float(row["length"]), 2) if row["length"] is not None else None,
        "version": version_token(row["archivechangedate"], row["xmin"]),
        "endpoint_tolerance_m": GEOMETRY_ENDPOINT_TOLERANCE_M,
    }


async def split_line(
    line_id: int,
    lng: float,
    lat: float,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
    review_to_new: Optional[dict] = None,
) -> dict:
    """Разрезает участок точкой, перенося зависимые объекты на нужную половину.

    dry_run=True — выполнить всё в транзакции, вернуть отчёт и откатить (ничего не
    сохраняется). Отчёт показывает, что будет перенесено, что требует решения оператора
    (`transferred.review_items`), и версию участка (`versions`) — её клиент передаёт при
    подтверждении.

    review_to_new (B2) — решение оператора по оборудованию без узла и позиции (задвижки,
    диафрагмы, элеваторы, насосы…): {таблица: [id, …]} переносятся на новую (вторую)
    половину, остальные остаются на первой. Если такое оборудование на участке есть, а
    решения нет (None) — 409 с перечнем (угадывать размещение нельзя); {} — «всё на первой».
    """
    async def body(conn, op):
        rows = await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        before = _tokens("line", rows)
        if op.journal.enabled:
            await _capture_lines_with_passports(conn, op, [line_id])
            for rule in SPLIT_TRANSFER_RULES:
                try:
                    async with conn.transaction():
                        await op.journal.capture(conn, rule.table, "_r.lineid = $1", line_id)
                except Exception:  # noqa: BLE001 - таблицы нет в этой БД
                    continue
        result = await _split_line_body(conn, line_id, lng, lat, review_to_new=review_to_new)
        if dry_run:
            return {**result, "versions": before}
        review = result["transferred"].get("review") or {}
        if review and review_to_new is None:
            raise TopologyDependencyError(
                "На участке есть оборудование без узла и позиции — укажите, на какую половину его отнести",
                blockers={
                    "review": result["transferred"].get("review_items", review),
                    "requires_resolution": True,
                },
            )
        op.journal.created("nodes", result["new_node_id"])
        op.journal.created("linesobj", result["new_line_id"])
        await op.journal.created_where(conn, "heatpipesections", "_r.lineid = $1", result["new_line_id"])
        result["versions"] = {
            **await _versions(conn, "line", [line_id, result["new_line_id"]]),
            **await _versions(conn, "node", [result["new_node_id"]]),
        }
        await op.audit("SPLIT", "linesobj", line_id, {"lng": lng, "lat": lat, **result})
        return result

    result = await _run(dry_run, body, "SPLIT", actor)
    if not dry_run:
        invalidate_outage_cache()
    return result


async def _split_line_body(conn, line_id: int, lng: float, lat: float, review_to_new: Optional[dict] = None) -> dict:
    now = datetime.now()

    # 1. Locate the clicked point on the original geometry. The fraction is
    # reused for both halves so intermediate vertices are preserved.
    old_line = await conn.fetchrow(
        """
        SELECT nodeid1, nodeid2,
               ST_LineLocatePoint(
                 shape,
                 ST_Transform(ST_SetSRID(ST_MakePoint($2, $3), 4326), 9998)
               ) AS split_fraction
        FROM linesobj
        WHERE id = $1 AND removed = 0 AND shape IS NOT NULL
        """,
        line_id, lng, lat,
    )
    if not old_line:
        raise ValueError("Line not found")
    # В модели ТГИД участок графа типизирован одним объектом: труба (heatpipesections) или
    # оборудование-звено (задвижка, насос, регулятор… — их lineid и есть этот участок, паспорта
    # трубы у него нет). Половина звена без объекта выпала бы из расчёта (sety строит рёбра по
    # таблицам типов) и разорвала бы сеть — поэтому режем только трубы.
    if not await conn.fetchval("SELECT count(*) FROM heatpipesections WHERE lineid = $1", line_id):
        kinds = await line_dependency_report(conn, line_id)
        raise TopologyDependencyError(
            f"Участок {line_id} — не труба (" + (", ".join(sorted(kinds)) or "нет паспорта трубы")
            + "): разрезать можно только участок теплопровода. Вставьте узел на соседней трубе.",
            blockers={"not_a_pipe": kinds or {"heatpipesections": 0}},
        )
    orig_nodeid2 = old_line['nodeid2']
    split_fraction = float(old_line['split_fraction'])
    if split_fraction <= 1e-8 or split_fraction >= 1.0 - 1e-8:
        raise ValueError("Split point is too close to a line endpoint")

    # 2. Новый узел в точке разреза. Фрагмент (fileid), код и признак подачи/обратки
    # берём у начального узла участка, принадлежность внутренней схеме — у участка: без fileid/externalcodeid расчёт (sety читает
    # узлы по fileID и JOIN externalCodes) не увидит узел и обе половины участка.
    new_node_id = await conn.fetchval(
        """
        INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid,
                           fileid, externalcodeid, externalsignid, internalnodeid)
        SELECT
          ST_LineInterpolatePoint(l.shape, $2),
          ST_X(ST_LineInterpolatePoint(l.shape, $2)) * 100.0,
          -ST_Y(ST_LineInterpolatePoint(l.shape, $2)) * 100.0,
          0,
          $3,
          1,
          COALESCE(n1.fileid, l.fileid), n1.externalcodeid, n1.externalsignid, l.internalnodeid
        FROM linesobj l
        LEFT JOIN nodes n1 ON n1.id = l.nodeid1
        WHERE l.id = $1
        RETURNING id
        """,
        line_id, split_fraction, now,
    )

    # 3. Create the new line from new_node_id to old nodeid2
    new_line_id = await conn.fetchval(
        """
        INSERT INTO linesobj (
          nodeid1, nodeid2, externalsignlineid, location, hydrores,
          organizationid, registnum, firstpicdate, lastmaintdate,
          displaysign, archivechangedate, operatorid, coords, typ,
          removed, idremoved, shape, globalid, gistable, sync, gis,
          sync_tgid, fileid, internalnodeid, id_old
        )
        SELECT
          $2, l.nodeid2, l.externalsignlineid, l.location, l.hydrores,
          l.organizationid, l.registnum, l.firstpicdate, l.lastmaintdate,
          l.displaysign, $4, l.operatorid, NULL, l.typ,
          0, NULL, ST_LineSubstring(l.shape, $3, 1.0), NULL,
          l.gistable, l.sync, l.gis, l.sync_tgid, l.fileid,
          l.internalnodeid, l.id_old
        FROM linesobj l
        WHERE l.id = $1
        RETURNING id
        """,
        line_id, new_node_id, split_fraction, now,
    )

    # 4. Перенос зависимых объектов на нужную половину — ДО усечения геометрии L,
    # т.к. геометрический перенос проецирует точки на полную исходную линию.
    transfer_report = await transfer_dependents(
        conn,
        orig_line_id=line_id,
        new_line_id=new_line_id,
        split_fraction=split_fraction,
        orig_nodeid2=orig_nodeid2,
        review_to_new=review_to_new,
    )

    # 5. Усечение исходного участка до 0..f и перенос его конца на новый узел
    await conn.execute(
        """
        UPDATE linesobj
        SET nodeid2 = $1,
            shape = ST_LineSubstring(shape, 0.0, $2),
            archivechangedate = $3
        WHERE id = $4
        """,
        new_node_id, split_fraction, now, line_id,
    )

    # 6. Клон паспорта трубы для новой половины и длины обеих половин.
    # jsonb_populate_record сохраняет все текущие и будущие колонки без списка из 150 полей.
    # Алиас hps, а не h: у heatpipesections есть колонка «h», и to_jsonb(h) взял бы её
    # (число), а не строку — «populate_composite с массивом нельзя».
    await conn.execute(
        """
        INSERT INTO heatpipesections
        SELECT (jsonb_populate_record(
          NULL::heatpipesections,
          to_jsonb(hps) || jsonb_build_object(
            'id', nextval('heatpipesections_id_seq'),
            -- явный ::int: в jsonb_build_object аргумент имеет тип "any"
            'lineid', $2::int,
            'pipesectlength', ST_Length((SELECT shape FROM linesobj WHERE id = $2))
          )
        )).*
        FROM heatpipesections hps
        WHERE hps.lineid = $1
        """,
        line_id, new_line_id,
    )
    await conn.execute(
        """
        UPDATE heatpipesections
        SET pipesectlength = ST_Length((SELECT shape FROM linesobj WHERE id = $1))
        WHERE lineid = $1
        """,
        line_id,
    )

    return {
        "line_id": line_id,
        "new_node_id": new_node_id,
        "new_line_id": new_line_id,
        "split_fraction": round(split_fraction, 6),
        "transferred": transfer_report,
    }


# ---------------------------------------------------------------------------
# Разворот участка (вместе с парной трубой подачи/обратки)
# ---------------------------------------------------------------------------

PAIR_SIGN = {2: 3, 3: 2}


async def find_pair_line(conn, line_id: int, candidate: Optional[int] = None) -> Optional[dict]:
    """Парная труба участка (подача ↔ обратка), как её видит десктоп.

    gid8 (read_lines.cpp) склеивает в одну двухтрубную линию графа участки с теми же
    nodeID1/nodeID2, тем же типом и теми же coords, если их externalSignLineID — 2 и 3
    (подающий/обратный); GidWidget::swap затем разворачивает оба (`WHERE ID=nomP OR
    ID=nomO`). Для участков, нарисованных в web (coords пуст), та же трасса проверяется по
    геометрии: расхождение (Хаусдорф) не больше PAIR_LINE_MAX_DEVIATION_M.
    candidate — проверить конкретный участок (пара из превью всё ещё пара?).
    """
    row = await conn.fetchrow(
        """
        SELECT b.id,
               CASE WHEN a.coords IS NOT NULL AND a.coords = b.coords THEN 'coords' ELSE 'geometry' END AS matched_by,
               CASE WHEN a.shape IS NOT NULL AND b.shape IS NOT NULL
                    THEN ST_HausdorffDistance(a.shape, b.shape) END AS deviation
        FROM linesobj a
        JOIN linesobj b
          ON b.id <> a.id AND COALESCE(b.removed, 0) = 0
         AND b.nodeid1 = a.nodeid1 AND b.nodeid2 = a.nodeid2
         AND b.externalsignlineid = (CASE a.externalsignlineid WHEN 2 THEN 3 WHEN 3 THEN 2 END)
         AND b.typ IS NOT DISTINCT FROM a.typ
        WHERE a.id = $1 AND COALESCE(a.removed, 0) = 0
          AND ($2::int IS NULL OR b.id = $2)
          AND (
                (a.coords IS NOT NULL AND a.coords = b.coords)
             OR (a.shape IS NOT NULL AND b.shape IS NOT NULL
                 AND ST_HausdorffDistance(a.shape, b.shape) <= $3)
          )
        ORDER BY (a.coords IS NOT NULL AND a.coords = b.coords) DESC,
                 ST_HausdorffDistance(a.shape, b.shape) NULLS LAST, b.id
        LIMIT 1
        """,
        line_id, candidate, PAIR_LINE_MAX_DEVIATION_M,
    )
    if row is None:
        return None
    return {
        "line_id": row["id"],
        "matched_by": row["matched_by"],
        "deviation_m": round(float(row["deviation"]), 3) if row["deviation"] is not None else None,
    }


async def _reverse_report(conn, line_id: int) -> dict:
    row = await conn.fetchrow(
        """
        SELECT nodeid1, nodeid2, externalsignlineid,
               CASE WHEN shape IS NOT NULL THEN ST_NumPoints(shape) END AS points,
               ST_Length(shape) AS length
        FROM linesobj WHERE id = $1
        """,
        line_id,
    )
    n1, n2 = row["nodeid1"], row["nodeid2"]
    sign_before = row["externalsignlineid"]
    sign_after = reversed_external_sign(sign_before)
    equipment = await plan_line_reverse(conn, line_id, n1, n2)
    return {
        "line_id": line_id,
        "nodeid1": n2,
        "nodeid2": n1,
        "before": {"nodeid1": n1, "nodeid2": n2, "externalsignlineid": sign_before},
        "after": {"nodeid1": n2, "nodeid2": n1, "externalsignlineid": sign_after},
        "geometry": {
            "reversed": row["points"] is not None,
            "points": row["points"],
            "length_m": round(float(row["length"]), 2) if row["length"] is not None else None,
        },
        "equipment": equipment,
        "requires_confirmation": bool(equipment["directional"]),
    }


async def reverse_line(
    line_id: int,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    accept_direction_change: bool = False,
    actor: Optional[str] = None,
    include_pair: bool = True,
    pair_line_id: Optional[int] = None,
    pair_version: Optional[str] = None,
    expected_section_id: Optional[int] = None,
) -> dict:
    """Разворот участка: nodeid1 <-> nodeid2, ST_Reverse(shape), externalsignlineid 4 <-> 5.

    expected_section_id — heatpipesections.id из карточки: при расхождении 409 (F54).

    Как десктоп (GidWidget::swap): вместе с участком разворачивается парная труба
    (подача ↔ обратка, см. find_pair_line), обе — в одной транзакции; dry-run отдаёт
    отчёт по обеим (`pair`). Клиент подтверждает пару из превью (`pair_line_id`,
    `pair_version`); если она перестала быть парой — 409. include_pair=False — только участок.

    Оборудование остаётся на участке:
      * привязанное к узлу (регуляторы: nodeid — регулируемый узел) сохраняет узел;
      * не зависящее от направления (задвижки, диафрагмы…) не меняется;
      * зависящее от направления (насосы, обратные клапаны, элеваторы) меняет
        направление действия вместе с участком — применяется только с
        accept_direction_change=True (иначе 409 с отчётом), dry-run показывает список.
    """
    async def body(conn, op):
        await _check_line_section(conn, line_id, expected_section_id)
        pair = None
        if include_pair:
            pair = await find_pair_line(conn, line_id, candidate=pair_line_id)
            if pair_line_id is not None and pair is None:
                raise TopologyDependencyError(
                    f"Участок {pair_line_id} больше не парный к {line_id} — обновите превью",
                    blockers={"pair": {"line_id": pair_line_id, "valid": False}},
                )
        pid = pair["line_id"] if pair else None
        ids = sorted({line_id, pid} - {None})
        rows = await _lock_active(conn, "line", ids, {line_id: expected_version, **({pid: pair_version} if pid else {})})
        report = await _reverse_report(conn, line_id)
        pair_report = {**pair, **await _reverse_report(conn, pid)} if pid else None
        directional = dict(report["equipment"]["directional"])
        if pair_report:
            for t, n in pair_report["equipment"]["directional"].items():
                directional[t] = directional.get(t, 0) + n
        report["pair"] = pair_report
        report["pair_line_id"] = pid
        report["requires_confirmation"] = bool(directional)
        if dry_run:
            return {**report, "versions": _tokens("line", rows)}
        if directional and not accept_direction_change:
            raise TopologyDependencyError(
                "Разворот изменит направление действия оборудования — подтвердите в превью",
                blockers={"equipment": directional, "requires_confirmation": True},
            )
        await op.journal.capture_ids(conn, "linesobj", ids)
        now = datetime.now()
        for part in [report] + ([pair_report] if pair_report else []):
            await conn.execute(
                """
                UPDATE linesobj
                SET nodeid1 = $2,
                    nodeid2 = $3,
                    externalsignlineid = $4,
                    shape = CASE WHEN shape IS NOT NULL THEN ST_Reverse(shape) ELSE NULL END,
                    archivechangedate = $5
                WHERE id = $1
                """,
                part["line_id"], part["after"]["nodeid1"], part["after"]["nodeid2"],
                part["after"]["externalsignlineid"], now,
            )
        report["versions"] = await _versions(conn, "line", ids)
        await op.audit("REVERSE", "linesobj", line_id, report)
        return {"success": True, **report}

    result = await _run(dry_run, body, "REVERSE", actor)
    if not dry_run:
        invalidate_outage_cache()
    return result


# ---------------------------------------------------------------------------
# Слияние узлов
# ---------------------------------------------------------------------------

async def merge_nodes(
    target_node_id: int,
    source_node_id: int,
    dry_run: bool = False,
    target_version: Optional[str] = None,
    source_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Слияние source_node_id в target_node_id.

    Всё в одной транзакции: перепривязка инцидентных участков к целевому узлу (концы
    геометрии — в точку целевого узла, длины паспортов пересчитываются), перенос всех
    ссылок на узел (nodeid*, internalnodeid, remontnodeid) по правилам topology_transfer,
    safe-delete участков между сливаемыми узлами, мягкое удаление источника, audit_log.
    dry_run — тот же отчёт без сохранения; блокеры в dry-run возвращаются, а не бросаются.
    """
    if target_node_id == source_node_id:
        raise ValueError("Невозможно объединить узел с самим собой.")

    async def body(conn, op):
        locked = await _lock_active(
            conn, "node", [target_node_id, source_node_id],
            {target_node_id: target_version, source_node_id: source_version},
        )
        before = _tokens("node", locked)
        nodes = {
            r["id"]: r
            for r in await conn.fetch(
                """
                SELECT id, fileid, internalnodeid, x, y, shape IS NOT NULL AS has_shape,
                       ST_X(ST_Transform(shape, 4326)) AS lng, ST_Y(ST_Transform(shape, 4326)) AS lat
                FROM nodes WHERE id = ANY($1::int[])
                """,
                [target_node_id, source_node_id],
            )
        }
        t, s = nodes[target_node_id], nodes[source_node_id]
        blockers: dict = {}
        warnings: dict = {}

        if t["fileid"] != s["fileid"]:
            blockers["different_fragments"] = {"target": t["fileid"], "source": s["fileid"]}
        if t["internalnodeid"] != s["internalnodeid"]:
            blockers["different_internal_scheme"] = {"target": t["internalnodeid"], "source": s["internalnodeid"]}
        if not t["has_shape"]:
            # Концы участков встают в точку целевого узла; восстанавливать её из x/y
            # нельзя — в части фрагментов x/y в локальной системе схемы, а не в SRID 9998
            blockers["target_without_geometry"] = {"x": t["x"], "y": t["y"]}

        distance = await conn.fetchval(
            "SELECT ST_Distance(a.shape, b.shape) FROM nodes a, nodes b WHERE a.id = $1 AND b.id = $2",
            target_node_id, source_node_id,
        )

        # Участки между сливаемыми узлами превратились бы в петли — снимаются через
        # safe-delete: только если на них нет оборудования (иначе блокер)
        connecting = [r["id"] for r in await conn.fetch(
            """
            SELECT id FROM linesobj
            WHERE ((nodeid1 = $1 AND nodeid2 = $2) OR (nodeid1 = $2 AND nodeid2 = $1))
              AND COALESCE(removed, 0) = 0
            ORDER BY id
            """,
            source_node_id, target_node_id,
        )]
        for lid in connecting:
            line_deps = await line_dependency_report(conn, lid)
            if line_deps:
                blockers.setdefault("connecting_lines", {})[str(lid)] = line_deps

        # Инцидентные участки источника (кроме соединяющих) — перепривязываются к целевому
        incident = await conn.fetch(
            """
            SELECT id, nodeid1, nodeid2 FROM linesobj
            WHERE (nodeid1 = $1 OR nodeid2 = $1) AND COALESCE(removed, 0) = 0
              AND NOT (id = ANY($2::int[]))
            ORDER BY id
            FOR UPDATE
            """,
            source_node_id, connecting,
        )
        relinked = [r["id"] for r in incident]
        # Параллельные участки после слияния (источник–X при уже существующем цель–X)
        others = {r["nodeid2"] if r["nodeid1"] == source_node_id else r["nodeid1"] for r in incident}
        if others:
            dups = await conn.fetch(
                """
                SELECT id, CASE WHEN nodeid1 = $1 THEN nodeid2 ELSE nodeid1 END AS other
                FROM linesobj
                WHERE (nodeid1 = $1 OR nodeid2 = $1) AND COALESCE(removed, 0) = 0
                  AND (CASE WHEN nodeid1 = $1 THEN nodeid2 ELSE nodeid1 END) = ANY($2::int[])
                """,
                target_node_id, list(others),
            )
            if dups:
                warnings["parallel_lines_with"] = sorted({r["other"] for r in dups})

        plan = await plan_node_merge(conn, source_node_id, target_node_id)
        if plan["conflicts"]:
            blockers["conflicting_references"] = plan["conflicts"]

        report = {
            "target_node_id": target_node_id,
            "source_node_id": source_node_id,
            "target_position": {
                "x": t["x"], "y": t["y"],
                "lng": t["lng"], "lat": t["lat"],
            },
            "distance_m": round(float(distance), 2) if distance is not None else None,
            "relinked_lines": relinked,
            "removed_lines": connecting,
            "transfer": plan["transfer"],
            "results_skipped": plan["results_skipped"],
            "blockers": blockers,
            "warnings": warnings,
        }
        if dry_run:
            return {**report, "versions": before}
        if blockers:
            raise TopologyDependencyError("Узлы нельзя объединить: есть блокирующие объекты", blockers=blockers)

        # before-image: оба узла, все участки источника (с паспортами), все переносимые ссылки
        if op.journal.enabled:
            await op.journal.capture_ids(conn, "nodes", [target_node_id, source_node_id])
            await _capture_lines_with_passports(conn, op, relinked + connecting)
            for ref_key in plan["transfer"]:
                table, col = ref_key.split(".", 1)
                await op.journal.capture(conn, table, f'_r."{col}" = $1', source_node_id)

        now = datetime.now()
        if connecting:
            await conn.execute(
                "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                connecting, now,
            )
            await _soft_remove_heatpipesections(conn, connecting, now)

        await conn.execute(
            """
            UPDATE linesobj
            SET nodeid1 = $1,
                shape = CASE WHEN shape IS NOT NULL THEN ST_SetPoint(shape, 0, (SELECT shape FROM nodes WHERE id = $1)) ELSE NULL END,
                archivechangedate = $3
            WHERE nodeid1 = $2 AND COALESCE(removed, 0) = 0
            """,
            target_node_id, source_node_id, now,
        )
        await conn.execute(
            """
            UPDATE linesobj
            SET nodeid2 = $1,
                shape = CASE WHEN shape IS NOT NULL THEN ST_SetPoint(shape, ST_NumPoints(shape) - 1, (SELECT shape FROM nodes WHERE id = $1)) ELSE NULL END,
                archivechangedate = $3
            WHERE nodeid2 = $2 AND COALESCE(removed, 0) = 0
            """,
            target_node_id, source_node_id, now,
        )
        if relinked:
            await conn.execute(
                """
                UPDATE heatpipesections h
                SET pipesectlength = ST_Length(l.shape)
                FROM linesobj l
                WHERE h.lineid = l.id AND l.id = ANY($1::int[]) AND l.shape IS NOT NULL
                """,
                relinked,
            )

        report["transferred"] = await apply_node_merge(conn, source_node_id, target_node_id, plan)

        await conn.execute(
            "UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1", source_node_id, now,
        )
        # Целевой узел получил новые ссылки — его версия меняется (другие клиенты увидят 409)
        await conn.execute("UPDATE nodes SET archivechangedate = $2 WHERE id = $1", target_node_id, now)

        report["merged_lines"] = len(relinked)
        report["versions"] = {
            **await _versions(conn, "node", [target_node_id]),
            **await _versions(conn, "line", relinked),
        }
        await op.audit("MERGE", "nodes", target_node_id, report)
        return {"success": True, **report}

    result = await _run(dry_run, body, "MERGE", actor)
    if not dry_run:
        invalidate_outage_cache()
    return result


# ---------------------------------------------------------------------------
# Геометрия участка (правка вершин)
# ---------------------------------------------------------------------------

async def update_line_geometry(
    line_id: int,
    coordinates: list[list[float]],
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Обновление геометрии полилинии (добавление/перемещение/удаление промежуточных вершин)."""
    if len(coordinates) < 2:
        raise ValueError("Полилиния должна содержать как минимум 2 точки.")

    async def body(conn, op):
        await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        line = await conn.fetchrow("SELECT id, nodeid1, nodeid2 FROM linesobj WHERE id = $1", line_id)
        geojson_geom = json.dumps({"type": "LineString", "coordinates": coordinates})
        # Концы новой геометрии должны лежать у узлов участка (или у прежних концов):
        # иначе геометрия «отрывается» от топологии. Принятые концы прижимаются к узлам.
        ends = await conn.fetchrow(
            """
            WITH g AS (SELECT ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON($2), 4326), 9998) AS geom),
                 l AS (SELECT shape FROM linesobj WHERE id = $1)
            SELECT
                ST_Distance(ST_StartPoint(g.geom), n1.shape) AS d_start_node,
                ST_Distance(ST_EndPoint(g.geom), n2.shape) AS d_end_node,
                ST_Distance(ST_StartPoint(g.geom), ST_StartPoint(l.shape)) AS d_start_old,
                ST_Distance(ST_EndPoint(g.geom), ST_EndPoint(l.shape)) AS d_end_old
            FROM g, l, nodes n1, nodes n2
            WHERE n1.id = $3 AND n2.id = $4
            """,
            line_id, geojson_geom, line["nodeid1"], line["nodeid2"],
        )
        if ends is None:
            raise ValueError(f"У участка {line_id} нет геометрии или узлов для проверки концов.")

        def _near(*dists) -> bool:
            return any(d is not None and d <= GEOMETRY_ENDPOINT_TOLERANCE_M for d in dists)

        if not (_near(ends["d_start_node"], ends["d_start_old"]) and _near(ends["d_end_node"], ends["d_end_old"])):
            raise ValueError(
                "Концы участка должны оставаться у его узлов "
                f"(допуск {GEOMETRY_ENDPOINT_TOLERANCE_M:g} м); для переноса конца переместите узел."
            )

        await _capture_lines_with_passports(conn, op, [line_id])
        new_len = await conn.fetchval(
            """
            UPDATE linesobj l
            SET shape = ST_SetPoint(
                    ST_SetPoint(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON($2), 4326), 9998), 0, n1.shape),
                    -1, n2.shape),
                archivechangedate = $3
            FROM nodes n1, nodes n2
            WHERE l.id = $1 AND n1.id = l.nodeid1 AND n2.id = l.nodeid2
            RETURNING ST_Length(l.shape) as new_len
            """,
            line_id, geojson_geom, datetime.now(),
        )
        await conn.execute("UPDATE heatpipesections SET pipesectlength = $2 WHERE lineid = $1", line_id, new_len)
        result = {
            "success": True,
            "line_id": line_id,
            "new_length": round(float(new_len or 0), 2),
            "versions": await _versions(conn, "line", [line_id]),
        }
        await op.audit("GEOMETRY", "linesobj", line_id, {"point_count": len(coordinates), **result})
        return result

    result = await _run(False, body, "GEOMETRY", actor)
    invalidate_outage_cache()
    return result


# ---------------------------------------------------------------------------
# Отмена (B5)
# ---------------------------------------------------------------------------

def _journal_entry(row) -> dict:
    summary = row["summary"]
    if isinstance(summary, str):
        summary = json.loads(summary)
    return {
        "operation_id": row["id"],
        "operation": row["operation"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "summary": summary or {},
        "objects": row["objects"],
        "undo_supported": not row["unsupported"],
    }


async def last_undoable_operation(actor: Optional[str]) -> Optional[dict]:
    """Последняя неотменённая операция пользователя (для кнопки «Отменить»); None — нечего."""
    pool = get_pool()
    async with pool.acquire() as conn:
        if not await journal_available(conn):
            return None
        row = await conn.fetchrow(
            f"""
            SELECT id, operation, created_at, summary, unsupported,
                   jsonb_array_length(before_rows) AS objects
            FROM {JOURNAL_TABLE}
            WHERE actor IS NOT DISTINCT FROM $1 AND undone_at IS NULL
            ORDER BY id DESC LIMIT 1
            """,
            actor,
        )
    return _journal_entry(row) if row else None


async def undo_last_operation(actor: Optional[str], operation_id: Optional[int] = None) -> dict:
    """Отмена последней операции пользователя.

    operation_id — операция, которую клиент показывал на кнопке: если последней стала другая
    (отменили/сделали в другой вкладке) — 409. Строки, затронутые операцией, блокируются и
    сверяются с их образом «после» (md5): изменённые после операции — 409 version_conflict,
    ничего не трогаем. Иначе образы «до» восстанавливаются, созданные операцией строки
    удаляются; запись журнала помечается отменённой, в audit_log пишется UNDO.
    """
    async def body(conn, op):
        if not await journal_available(conn):
            raise TopologyNothingToUndo("Журнал отмены не установлен в этой БД")
        row = await conn.fetchrow(
            f"""
            SELECT id, operation, created_at, summary, unsupported, change_group_id::text AS group_id,
                   after_hashes::text AS after_hashes, jsonb_array_length(before_rows) AS objects
            FROM {JOURNAL_TABLE}
            WHERE actor IS NOT DISTINCT FROM $1 AND undone_at IS NULL
            ORDER BY id DESC LIMIT 1
            FOR UPDATE
            """,
            actor,
        )
        if row is None:
            raise TopologyNothingToUndo("Нет операций для отмены")
        entry = _journal_entry(row)
        if operation_id is not None and row["id"] != operation_id:
            raise TopologyConflictError(
                {"operation": {"expected": operation_id, "actual": row["id"]}},
                "Последняя операция изменилась — обновите список",
            )
        if row["unsupported"]:
            raise TopologyDependencyError(
                "Операцию нельзя отменить: она затронула таблицы без первичного ключа",
                blockers={"unsupported": row["unsupported"]},
            )
        after = json.loads(row["after_hashes"])
        by_table: dict[str, list[int]] = {}
        for k in after:
            table, rid = k.rsplit(":", 1)
            by_table.setdefault(table, []).append(int(rid))
        current = await current_hashes(conn, by_table, lock=True)
        changed = changed_since(after, current)
        if changed:
            raise TopologyConflictError(
                {k: {**v, "removed": v["actual"] is None} for k, v in changed.items()},
                "Объекты изменены после операции — отмена невозможна",
            )
        items = [
            {"t": r["t"], "id": r["id"], "row": r["img"]}
            for r in await conn.fetch(
                f"""
                SELECT e->>'t' AS t, (e->>'id')::int AS id,
                       CASE WHEN jsonb_typeof(e->'row') = 'null' THEN NULL ELSE (e->'row')::text END AS img
                FROM {JOURNAL_TABLE} j, jsonb_array_elements(j.before_rows) AS e
                WHERE j.id = $1
                """,
                row["id"],
            )
        ]
        report = await restore_rows(conn, items)
        await conn.execute(
            f"UPDATE {JOURNAL_TABLE} SET undone_at = now(), undone_by = $2, undo_group_id = $3::uuid WHERE id = $1",
            row["id"], actor, op.group_id,
        )
        result = {"success": True, **entry, **report, "undone_group_id": row["group_id"]}
        await op.audit("UNDO", JOURNAL_TABLE, row["id"], result)
        return result

    result = await _run(False, body, None, actor)
    invalidate_outage_cache()
    return result
