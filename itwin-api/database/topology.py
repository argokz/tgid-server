import json
import logging
from datetime import datetime
from database.connect import get_pool
from database.outage_simulation import invalidate_outage_cache
from database.topology_transfer import (
    line_dependency_report,
    node_dependency_report,
    transfer_dependents,
)

logger = logging.getLogger(__name__)


class _DryRunRollback(Exception):
    """Служебное исключение: форсирует ROLLBACK транзакции dry-run, неся отчёт."""

    def __init__(self, payload: dict):
        self.payload = payload


# Слияние узлов переносит только потребителей; остальное — блокер (как safe-delete B3).
MERGE_MOVABLE_REFS = {"generalizedconsumers.nodeid", "realconsumers.nodeid"}
# Оборудование, для которого важно направление участка: разворот его не переносит.
REVERSE_BLOCKING_TABLES = {"diaphragms", "pumps", "elevators", "heatexchangers", "airheaters", "systemradiators"}
# Допуск для концов новой геометрии участка относительно его узлов, м (SRID 9998 — метры).
GEOMETRY_ENDPOINT_TOLERANCE_M = 5.0


def _is_result_table(ref: str) -> bool:
    """us_out.nodeid, pt_out.nodeid… — выход расчёта, а не данные сети."""
    return ref.split(".", 1)[0].lower().endswith("_out")


class TopologyDependencyError(Exception):
    """Операция заблокирована зависимыми объектами (для ответа 409 с отчётом)."""

    def __init__(self, message: str, blockers: dict):
        super().__init__(message)
        self.blockers = blockers

async def move_node(node_id: int, lng: float, lat: float):
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. Update node
            q_node = """
                UPDATE nodes SET 
                  shape = ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998),
                  x = ST_X(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
                  y = -ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
                  archivechangedate = $4
                WHERE id = $3
            """
            now = datetime.now()
            await conn.execute(q_node, lng, lat, node_id, now)

            # 2. Update lines where this node is nodeid1 (start point -> index 0)
            q_line1 = """
                UPDATE linesobj 
                SET shape = ST_SetPoint(shape, 0, (SELECT shape FROM nodes WHERE id = $1)),
                    archivechangedate = $2
                WHERE nodeid1 = $1 AND shape IS NOT NULL
            """
            await conn.execute(q_line1, node_id, now)

            # 3. Update lines where this node is nodeid2 (end point -> last index)
            q_line2 = """
                UPDATE linesobj
                SET shape = ST_SetPoint(shape, ST_NumPoints(shape) - 1, (SELECT shape FROM nodes WHERE id = $1)),
                    archivechangedate = $2
                WHERE nodeid2 = $1 AND shape IS NOT NULL
            """
            await conn.execute(q_line2, node_id, now)

            # 4. Пересчёт длины паспорта труб у всех инцидентных участков:
            # перемещение узла меняет длину линии, а pipesectlength должен следовать
            # за геометрией — иначе гидравлический расчёт получит устаревшую длину.
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
            return {"node_id": node_id, "recalculated_lines": len(affected)}


async def delete_node(node_id: int, cascade: bool = False) -> dict:
    """Безопасное удаление узла.

    По умолчанию отказывает, если на узле висят инцидентные активные линии или
    другие ссылки (nodeid в зависимых таблицах) — чтобы не осиротить объекты молча.
    cascade=True — удалить узел вместе с инцидентными линиями и их паспортами.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
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

            # cascade: снимаем инцидентные линии и их паспорта
            removed_lines = [r["id"] for r in incident_lines]
            if removed_lines:
                await conn.execute(
                    "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                    removed_lines, now,
                )
                await _soft_remove_heatpipesections(conn, removed_lines, now)

            await conn.execute("UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1", node_id, now)
            return {
                "node_id": node_id,
                "removed_lines": removed_lines,
                "cleared_references": node_deps,
            }

async def create_node(lng: float, lat: float) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        q_insert = """
            INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid)
            VALUES (
              ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998),
              ST_X(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              -ST_Y(ST_Transform(ST_SetSRID(ST_MakePoint($1, $2), 4326), 9998)) * 100.0,
              0,
              $3,
              1 -- default node type (e.g. unknown or simple node)
            ) RETURNING id
        """
        now = datetime.now()
        new_id = await conn.fetchval(q_insert, lng, lat, now)
        return new_id

async def create_line(nodeid1: int, nodeid2: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now()
            if nodeid1 == nodeid2:
                raise ValueError("A line requires two different nodes")
            valid_nodes = await conn.fetch(
                "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND removed = 0 AND shape IS NOT NULL",
                [nodeid1, nodeid2],
            )
            if len(valid_nodes) != 2:
                raise ValueError("Both active nodes with geometry are required")
            # We make a simple 2-point linestring
            q_insert_line = """
                INSERT INTO linesobj (nodeid1, nodeid2, shape, removed, archivechangedate)
                VALUES (
                  $1, 
                  $2,
                  ST_MakeLine((SELECT shape FROM nodes WHERE id = $1), (SELECT shape FROM nodes WHERE id = $2)),
                  0,
                  $3
                ) RETURNING id
            """
            line_id = await conn.fetchval(q_insert_line, nodeid1, nodeid2, now)

            # Also create corresponding heatPipeSections
            # Assuming heatpipesections has id, lineid
            try:
                # В asyncpg вложенная transaction создаёт SAVEPOINT. Без него любая SQL-ошибка
                # оставляет внешнюю транзакцию aborted, даже если исключение было поймано.
                async with conn.transaction():
                    q_insert_heat = """
                        INSERT INTO heatpipesections (lineid, pipesectlength)
                        VALUES (
                        $1,
                        ST_Length(ST_MakeLine((SELECT shape FROM nodes WHERE id = $2), (SELECT shape FROM nodes WHERE id = $3)))
                        )
                    """
                    await conn.execute(q_insert_heat, line_id, nodeid1, nodeid2)
            except Exception as e:
                logger.error(f"Error creating heatPipeSection (table might not exist or schema differs): {e}")

            return line_id

async def delete_line(line_id: int) -> dict:
    """Мягкое удаление участка вместе с его паспортом; отчёт по зависимому оборудованию.

    Оборудование (задвижки, регуляторы…) на удалённой линии не пропадает
    (soft-delete сохраняет данные), но возвращается в отчёте, чтобы оператор
    знал, какие объекты теперь ссылаются на снятый участок.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now()
            equipment = await line_dependency_report(conn, line_id)
            await conn.execute("UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = $1", line_id, now)
            await _soft_remove_heatpipesections(conn, [line_id], now)
            return {"line_id": line_id, "dependent_equipment": equipment}


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

async def split_line(line_id: int, lng: float, lat: float, dry_run: bool = False) -> dict:
    """Разрезает участок точкой, перенося зависимые объекты на нужную половину.

    dry_run=True — выполнить всё в транзакции, вернуть отчёт и откатить (ничего не
    сохраняется). Отчёт показывает, что будет перенесено и что требует ручной проверки.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                result = await _split_line_body(conn, line_id, lng, lat)
                if dry_run:
                    raise _DryRunRollback({"dry_run": True, **result})
                return result
        except _DryRunRollback as e:
            return e.payload


async def _split_line_body(conn, line_id: int, lng: float, lat: float) -> dict:
    now = datetime.now()

    # 1. Locate the clicked point on the original geometry. The fraction is
    # reused for both halves so intermediate vertices are preserved.
    q_old = """
                SELECT nodeid1, nodeid2,
                       ST_LineLocatePoint(
                         shape,
                         ST_Transform(ST_SetSRID(ST_MakePoint($2, $3), 4326), 9998)
                       ) AS split_fraction
                FROM linesobj
                WHERE id = $1 AND removed = 0 AND shape IS NOT NULL
            """
    old_line = await conn.fetchrow(q_old, line_id, lng, lat)
    if not old_line:
        raise ValueError("Line not found")
    orig_nodeid2 = old_line['nodeid2']
    split_fraction = float(old_line['split_fraction'])
    if split_fraction <= 1e-8 or split_fraction >= 1.0 - 1e-8:
        raise ValueError("Split point is too close to a line endpoint")

    # 2. Create the new node at lng, lat
    q_insert_node = """
                INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid)
                SELECT
                  ST_LineInterpolatePoint(l.shape, $2),
                  ST_X(ST_LineInterpolatePoint(l.shape, $2)) * 100.0,
                  -ST_Y(ST_LineInterpolatePoint(l.shape, $2)) * 100.0,
                  0,
                  $3,
                  1
                FROM linesobj l
                WHERE l.id = $1
                RETURNING id
            """
    new_node_id = await conn.fetchval(q_insert_node, line_id, split_fraction, now)

    # 3. Create the new line from new_node_id to old nodeid2
    q_insert_line = """
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
                  NULL, l.id_old
                FROM linesobj l
                WHERE l.id = $1
                RETURNING id
            """
    new_line_id = await conn.fetchval(
        q_insert_line,
        line_id,
        new_node_id,
        split_fraction,
        now,
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

    # 5. Update the old line's nodeid2 to new_node_id (усечение геометрии до 0..f)
    q_update_old = """
                UPDATE linesobj
                SET nodeid2 = $1,
                    shape = ST_LineSubstring(shape, 0.0, $2),
                    archivechangedate = $3
                WHERE id = $4
            """
    await conn.execute(q_update_old, new_node_id, split_fraction, now, line_id)

    # 6. Clone the business passport of the pipe section for the new half,
    # then update geometric lengths for both halves. jsonb_populate_record
    # keeps all current and future columns without a 150-column SQL list.
    q_clone_heat = """
                INSERT INTO heatpipesections
                SELECT (jsonb_populate_record(
                  NULL::heatpipesections,
                  to_jsonb(h) || jsonb_build_object(
                    'id', nextval('heatpipesections_id_seq'),
                    -- явный ::int: в jsonb_build_object аргумент имеет тип "any",
                    -- и без каста PostgreSQL не может вывести тип параметра
                    'lineid', $2::int,
                    'pipesectlength', ST_Length((SELECT shape FROM linesobj WHERE id = $2))
                  )
                )).*
                FROM heatpipesections h
                WHERE h.lineid = $1
            """
    await conn.execute(q_clone_heat, line_id, new_line_id)
    await conn.execute(
        """
                UPDATE heatpipesections
                SET pipesectlength = ST_Length((SELECT shape FROM linesobj WHERE id = $1))
                WHERE lineid = $1
                """,
        line_id,
    )

    return {
        "new_node_id": new_node_id,
        "new_line_id": new_line_id,
        "transferred": transfer_report,
    }


async def reverse_line(line_id: int) -> dict:
    """Разворот направления участка (инвертирование nodeid1 <-> nodeid2 и ST_Reverse)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now()
            row = await conn.fetchrow(
                "SELECT id, nodeid1, nodeid2, shape FROM linesobj WHERE id = $1 AND COALESCE(removed, 0) = 0",
                line_id,
            )
            if not row:
                raise ValueError(f"Линия с ID {line_id} не найдена или удалена.")
            line_deps = await line_dependency_report(conn, line_id)
            blockers = {t: n for t, n in line_deps.items() if t in REVERSE_BLOCKING_TABLES}
            if blockers:
                raise TopologyDependencyError(
                    "Участок нельзя развернуть: на нём оборудование, зависящее от направления",
                    blockers={"equipment": blockers},
                )
            n1, n2 = row["nodeid1"], row["nodeid2"]
            q_update = """
                UPDATE linesobj
                SET nodeid1 = $2,
                    nodeid2 = $3,
                    shape = CASE WHEN shape IS NOT NULL THEN ST_Reverse(shape) ELSE NULL END,
                    archivechangedate = $4
                WHERE id = $1
            """
            await conn.execute(q_update, line_id, n2, n1, now)
            invalidate_outage_cache()
            return {"success": True, "line_id": line_id, "nodeid1": n2, "nodeid2": n1}


async def merge_nodes(target_node_id: int, source_node_id: int) -> dict:
    """Слияние source_node_id в target_node_id: перепривязка всех инцидентных линий и удаление источника."""
    if target_node_id == source_node_id:
        raise ValueError("Невозможно объединить узел с самим собой.")
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now()
            t_node = await conn.fetchrow(
                "SELECT id, shape, fileid FROM nodes WHERE id = $1 AND COALESCE(removed, 0) = 0",
                target_node_id,
            )
            s_node = await conn.fetchrow(
                "SELECT id, shape, fileid FROM nodes WHERE id = $1 AND COALESCE(removed, 0) = 0",
                source_node_id,
            )
            if not t_node or not s_node:
                raise ValueError("Оба объединяемых узла должны существовать и быть активными.")
            if t_node["fileid"] != s_node["fileid"]:
                raise ValueError("Нельзя объединить узлы из разных фрагментов.")

            # Всё, что ссылается на исходный узел и не переносится, блокирует слияние
            blockers: dict = {}
            refs = {
                ref: n for ref, n in (await node_dependency_report(conn, source_node_id)).items()
                if ref not in MERGE_MOVABLE_REFS and not _is_result_table(ref)
            }
            if refs:
                blockers["references"] = refs
            internal = await conn.fetchval(
                "SELECT count(*) FROM linesobj WHERE internalnodeid = $1 AND COALESCE(removed, 0) = 0",
                source_node_id,
            )
            if internal:
                blockers["internal_scheme_lines"] = int(internal)

            # Участки между сливаемыми узлами превратились бы в петли — снимаем их,
            # если на них нет оборудования
            connecting = [r["id"] for r in await conn.fetch(
                """
                SELECT id FROM linesobj
                WHERE ((nodeid1 = $1 AND nodeid2 = $2) OR (nodeid1 = $2 AND nodeid2 = $1))
                  AND COALESCE(removed, 0) = 0
                """,
                source_node_id,
                target_node_id,
            )]
            for lid in connecting:
                line_deps = await line_dependency_report(conn, lid)
                if line_deps:
                    blockers.setdefault("connecting_lines", {})[lid] = line_deps
            if blockers:
                raise TopologyDependencyError(
                    "Узлы нельзя объединить: есть зависимые объекты", blockers=blockers
                )
            if connecting:
                await conn.execute(
                    "UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = ANY($1::int[])",
                    connecting, now,
                )
                await _soft_remove_heatpipesections(conn, connecting, now)

            # 1. Линии, где source_node_id был началом (nodeid1)
            affected1 = await conn.fetch(
                """
                UPDATE linesobj
                SET nodeid1 = $1,
                    shape = CASE WHEN shape IS NOT NULL THEN ST_SetPoint(shape, 0, (SELECT shape FROM nodes WHERE id = $1)) ELSE NULL END,
                    archivechangedate = $3
                WHERE nodeid1 = $2 AND COALESCE(removed, 0) = 0
                RETURNING id
                """,
                target_node_id,
                source_node_id,
                now,
            )

            # 2. Линии, где source_node_id был концом (nodeid2)
            affected2 = await conn.fetch(
                """
                UPDATE linesobj
                SET nodeid2 = $1,
                    shape = CASE WHEN shape IS NOT NULL THEN ST_SetPoint(shape, ST_NumPoints(shape) - 1, (SELECT shape FROM nodes WHERE id = $1)) ELSE NULL END,
                    archivechangedate = $3
                WHERE nodeid2 = $2 AND COALESCE(removed, 0) = 0
                RETURNING id
                """,
                target_node_id,
                source_node_id,
                now,
            )

            all_affected_lines = list({r["id"] for r in (affected1 + affected2)})

            # 3. Пересчет длины в heatpipesections
            if all_affected_lines:
                await conn.execute(
                    """
                    UPDATE heatpipesections h
                    SET pipesectlength = ST_Length(l.shape)
                    FROM linesobj l
                    WHERE h.lineid = l.id AND l.id = ANY($1::int[]) AND l.shape IS NOT NULL
                    """,
                    all_affected_lines,
                )

            # 4. Перенос потребителей
            await conn.execute(
                "UPDATE generalizedconsumers SET nodeid = $1 WHERE nodeid = $2",
                target_node_id,
                source_node_id,
            )
            await conn.execute(
                "UPDATE realconsumers SET nodeid = $1 WHERE nodeid = $2",
                target_node_id,
                source_node_id,
            )

            # 5. Мягкое удаление source_node_id
            await conn.execute(
                "UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1",
                source_node_id,
                now,
            )

            invalidate_outage_cache()
            return {
                "success": True,
                "target_node_id": target_node_id,
                "source_node_id": source_node_id,
                "merged_lines": len(all_affected_lines),
                "removed_lines": connecting,
            }


async def update_line_geometry(line_id: int, coordinates: list[list[float]]) -> dict:
    """Обновление геометрии полилинии (добавление/перемещение промежуточных вершин)."""
    if len(coordinates) < 2:
        raise ValueError("Полилиния должна содержать как минимум 2 точки.")
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            now = datetime.now()
            line = await conn.fetchrow(
                "SELECT id, nodeid1, nodeid2 FROM linesobj WHERE id = $1 AND COALESCE(removed, 0) = 0",
                line_id,
            )
            if not line:
                raise ValueError(f"Линия с ID {line_id} не найдена или удалена.")

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

            q_update = """
                UPDATE linesobj l
                SET shape = ST_SetPoint(
                        ST_SetPoint(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON($2), 4326), 9998), 0, n1.shape),
                        -1, n2.shape),
                    archivechangedate = $3
                FROM nodes n1, nodes n2
                WHERE l.id = $1 AND n1.id = l.nodeid1 AND n2.id = l.nodeid2
                RETURNING ST_Length(l.shape) as new_len
            """
            new_len = await conn.fetchval(q_update, line_id, geojson_geom, now)

            await conn.execute(
                "UPDATE heatpipesections SET pipesectlength = $2 WHERE lineid = $1",
                line_id,
                new_len,
            )

            invalidate_outage_cache()
            return {"success": True, "line_id": line_id, "new_length": round(float(new_len or 0), 2)}

