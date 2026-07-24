import logging
from database.connect import get_pool
from database.topology_transfer import (
    line_dependency_report,
    node_dependency_report,
    transfer_dependents,
)
from datetime import datetime

logger = logging.getLogger(__name__)


class _DryRunRollback(Exception):
    """Служебное исключение: форсирует ROLLBACK транзакции dry-run, неся отчёт."""

    def __init__(self, payload: dict):
        self.payload = payload


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
                    'lineid', $2,
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
