"""Изменение топологии сети: узлы, участки, разрезание, слияние, разворот.

Все операции (этап 8, Stage B):
  * транзакционны: изменения, перенос зависимых объектов и запись audit_log — в одной
    транзакции (audit через SAVEPOINT той же транзакции);
  * с оптимистичной блокировкой: клиент передаёт версию объекта, которую он видел
    (`version_token`), сервер берёт строку `SELECT … FOR UPDATE` и при несовпадении
    отвечает TopologyConflictError (HTTP 409 «объект изменён другим пользователем»);
  * «опасные» операции (split, merge, reverse) поддерживают dry-run: выполняются в
    транзакции и откатываются, возвращая отчёт «что и куда будет перенесено».
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

from audit import write_audit_log
from database.connect import get_pool
from database.outage_simulation import invalidate_outage_cache
from database.topology_transfer import (
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


async def _audit(conn, actor: Optional[str], operation: str, table: str, record_id: Optional[int], data: dict) -> None:
    if actor:
        await write_audit_log(
            changed_by=actor,
            operation=operation,
            table_name=table,
            record_id=record_id,
            new_data=data,
            conn=conn,
        )


async def _run(dry_run: bool, body):
    """Выполняет body(conn) в транзакции; dry_run — откатывает и возвращает отчёт."""
    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                result = await body(conn)
                if dry_run:
                    raise _DryRunRollback({"dry_run": True, **result})
                return result
        except _DryRunRollback as e:
            return e.payload


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
    async def body(conn):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
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
        await _audit(conn, actor, "MOVE", "nodes", node_id, {"lng": lng, "lat": lat, **result})
        return result

    return await _run(False, body)


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
    async def body(conn):
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
        if removed_lines:
            await conn.execute(
                "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                removed_lines, now,
            )
            await _soft_remove_heatpipesections(conn, removed_lines, now)
        await conn.execute("UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1", node_id, now)
        result = {"node_id": node_id, "removed_lines": removed_lines, "cleared_references": node_deps}
        await _audit(conn, actor, "DELETE", "nodes", node_id, {"cascade": cascade, **result})
        return result

    return await _run(False, body)


async def create_node(lng: float, lat: float, actor: Optional[str] = None) -> int:
    """Новый узел: блокировать нечего (объекта ещё нет)."""
    async def body(conn):
        new_id = await conn.fetchval(
            """
            INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid)
            VALUES (
              ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998),
              ST_X(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              -ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              0,
              $3,
              1 -- default node type (e.g. unknown or simple node)
            ) RETURNING id
            """,
            lng, lat, datetime.now(),
        )
        await _audit(conn, actor, "INSERT", "nodes", new_id, {"lng": lng, "lat": lat})
        return {"id": new_id}

    return (await _run(False, body))["id"]


# ---------------------------------------------------------------------------
# Участки
# ---------------------------------------------------------------------------

async def create_line(
    nodeid1: int,
    nodeid2: int,
    nodeid1_version: Optional[str] = None,
    nodeid2_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> int:
    if nodeid1 == nodeid2:
        raise ValueError("A line requires two different nodes")

    async def body(conn):
        # Узлы-концы блокируются: их не должны удалить/сдвинуть, пока строится участок
        await _lock_active(conn, "node", [nodeid1, nodeid2], {nodeid1: nodeid1_version, nodeid2: nodeid2_version})
        valid = await conn.fetchval(
            "SELECT count(*) FROM nodes WHERE id = ANY($1::int[]) AND shape IS NOT NULL",
            [nodeid1, nodeid2],
        )
        if valid != 2:
            raise ValueError("Both active nodes with geometry are required")
        now = datetime.now()
        line_id = await conn.fetchval(
            """
            INSERT INTO linesobj (nodeid1, nodeid2, shape, removed, archivechangedate)
            VALUES (
              $1,
              $2,
              ST_MakeLine((SELECT shape FROM nodes WHERE id = $1), (SELECT shape FROM nodes WHERE id = $2)),
              0,
              $3
            ) RETURNING id
            """,
            nodeid1, nodeid2, now,
        )
        try:
            # В asyncpg вложенная transaction создаёт SAVEPOINT. Без него любая SQL-ошибка
            # оставляет внешнюю транзакцию aborted, даже если исключение было поймано.
            async with conn.transaction():
                await conn.execute(
                    """
                    INSERT INTO heatpipesections (lineid, pipesectlength)
                    VALUES ($1, ST_Length((SELECT shape FROM linesobj WHERE id = $1)))
                    """,
                    line_id,
                )
        except Exception as e:
            logger.error(f"Error creating heatPipeSection (table might not exist or schema differs): {e}")
        await _audit(conn, actor, "INSERT", "linesobj", line_id, {"nodeid1": nodeid1, "nodeid2": nodeid2})
        return {"id": line_id}

    return (await _run(False, body))["id"]


async def delete_line(line_id: int, expected_version: Optional[str] = None, actor: Optional[str] = None) -> dict:
    """Мягкое удаление участка вместе с его паспортом; отчёт по зависимому оборудованию.

    Оборудование (задвижки, регуляторы…) на удалённой линии не пропадает
    (soft-delete сохраняет данные), но возвращается в отчёте, чтобы оператор
    знал, какие объекты теперь ссылаются на снятый участок.
    """
    async def body(conn):
        await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        now = datetime.now()
        equipment = await line_dependency_report(conn, line_id)
        await conn.execute("UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = $1", line_id, now)
        await _soft_remove_heatpipesections(conn, [line_id], now)
        result = {"line_id": line_id, "dependent_equipment": equipment}
        await _audit(conn, actor, "DELETE", "linesobj", line_id, result)
        return result

    return await _run(False, body)


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


async def split_line(
    line_id: int,
    lng: float,
    lat: float,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Разрезает участок точкой, перенося зависимые объекты на нужную половину.

    dry_run=True — выполнить всё в транзакции, вернуть отчёт и откатить (ничего не
    сохраняется). Отчёт показывает, что будет перенесено и что требует ручной проверки,
    и версию участка (`versions`) — её клиент передаёт при подтверждении.
    """
    async def body(conn):
        rows = await _lock_active(conn, "line", [line_id], {line_id: expected_version})
        before = _tokens("line", rows)
        result = await _split_line_body(conn, line_id, lng, lat)
        if dry_run:
            return {**result, "versions": before}
        result["versions"] = {
            **await _versions(conn, "line", [line_id, result["new_line_id"]]),
            **await _versions(conn, "node", [result["new_node_id"]]),
        }
        await _audit(conn, actor, "SPLIT", "linesobj", line_id, {"lng": lng, "lat": lat, **result})
        return result

    return await _run(dry_run, body)


async def _split_line_body(conn, line_id: int, lng: float, lat: float) -> dict:
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


async def reverse_line(
    line_id: int,
    dry_run: bool = False,
    expected_version: Optional[str] = None,
    accept_direction_change: bool = False,
    actor: Optional[str] = None,
) -> dict:
    """Разворот участка: nodeid1 <-> nodeid2, ST_Reverse(shape), externalsignlineid 4 <-> 5.

    Как десктоп (GidWidget::swap). Оборудование остаётся на участке:
      * привязанное к узлу (регуляторы: nodeid — регулируемый узел) сохраняет узел;
      * не зависящее от направления (задвижки, диафрагмы…) не меняется;
      * зависящее от направления (насосы, обратные клапаны, элеваторы) меняет
        направление действия вместе с участком — применяется только с
        accept_direction_change=True (иначе 409 с отчётом), dry-run показывает список.
    """
    async def body(conn):
        rows = await _lock_active(conn, "line", [line_id], {line_id: expected_version})
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
        report = {
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
        if dry_run:
            return {**report, "versions": _tokens("line", rows)}
        if equipment["directional"] and not accept_direction_change:
            raise TopologyDependencyError(
                "Разворот изменит направление действия оборудования — подтвердите в превью",
                blockers={"equipment": equipment["directional"], "requires_confirmation": True},
            )
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
            line_id, n2, n1, sign_after, datetime.now(),
        )
        report["versions"] = await _versions(conn, "line", [line_id])
        await _audit(conn, actor, "REVERSE", "linesobj", line_id, report)
        return {"success": True, **report}

    result = await _run(dry_run, body)
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

    async def body(conn):
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
        await _audit(conn, actor, "MERGE", "nodes", target_node_id, report)
        return {"success": True, **report}

    result = await _run(dry_run, body)
    if not dry_run:
        invalidate_outage_cache()
    return result


async def update_line_geometry(
    line_id: int,
    coordinates: list[list[float]],
    expected_version: Optional[str] = None,
    actor: Optional[str] = None,
) -> dict:
    """Обновление геометрии полилинии (добавление/перемещение промежуточных вершин)."""
    if len(coordinates) < 2:
        raise ValueError("Полилиния должна содержать как минимум 2 точки.")

    async def body(conn):
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
        await _audit(conn, actor, "UPDATE_GEOMETRY", "linesobj", line_id, {"point_count": len(coordinates), **result})
        return result

    result = await _run(False, body)
    invalidate_outage_cache()
    return result
