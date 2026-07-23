from typing import Any, Literal, Optional

import asyncpg


ElevatorQualityStatus = Literal[
    "ready",
    "line_missing",
    "line_removed",
    "topology_missing",
    "state_missing",
    "nozzle_unresolved",
    "pending_calculation",
]


ELEVATOR_CTE = """
    WITH elevator_inventory AS (
        SELECT elevator.id, elevator.lineid AS line_id,
               line.id AS linked_line_id,
               coalesce(nullif(btrim(elevator.elevatortype::text), ''),
                        'Элеватор №' || elevator.id) AS display_name,
               elevator.elevatortype AS elevator_type,
               elevator.elevatornuminst AS elevator_num_inst,
               elevator.diameternozzle AS diameter_nozzle,
               elevator.entrymark AS entry_mark,
               elevator.diameterchamber AS diameter_chamber,
               elevator.length,
               elevator.diameterinletflange AS diameter_inlet_flange,
               elevator.diameteroutletflange AS diameter_outlet_flange,
               elevator.diametersuctionpipe AS diameter_suction_pipe,
               elevator.material,
               elevator.stateid AS state_id, state.id AS linked_state_id,
               state.name AS state_name,
               line.externalsignlineid AS external_sign_line_id,
               external_sign.name AS external_sign_line_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed,
               line.hydrores AS line_hydraulic_resistance,
               line.registnum AS registration_number,
               line.firstpicdate AS commissioned_at,
               line.lastmaintdate AS last_maintenance_at,
               line.organizationid AS organization_id,
               organization.name AS organization_name,
               line.operatorid AS operator_id, operator.name AS operator_name,
               line.nodeid1 AS node_id_1, node1.id AS linked_node_id_1,
               line.nodeid2 AS node_id_2, node2.id AS linked_node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM elevators elevator
          LEFT JOIN linesobj line ON line.id=elevator.lineid
          LEFT JOIN states state ON state.id=elevator.stateid
          LEFT JOIN externalsignline external_sign ON external_sign.id=line.externalsignlineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN organizations organization ON organization.id=line.organizationid
          LEFT JOIN operators operator ON operator.id=line.operatorid
    ), classified_elevators AS (
        SELECT inventory.*,
               CASE WHEN inventory.linked_line_id IS NULL THEN 'line_missing'
                    WHEN coalesce(inventory.line_removed, 0)<>0 THEN 'line_removed'
                    WHEN inventory.linked_state_id IS NULL THEN 'state_missing'
                    WHEN inventory.diameter_nozzle=0
                     AND nullif(btrim(coalesce(inventory.entry_mark::text, '')), '') IS NOT NULL
                      THEN 'pending_calculation'
                    WHEN coalesce(inventory.diameter_nozzle, 0)=0 THEN 'nozzle_unresolved'
                    WHEN inventory.linked_node_id_1 IS NULL OR inventory.linked_node_id_2 IS NULL
                      THEN 'topology_missing'
                    ELSE 'ready' END AS quality_status
          FROM elevator_inventory inventory
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_elevator_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch("SELECT id, name, code FROM states ORDER BY ord, id")
    elevator_types = await conn.fetch(
        """SELECT elevatortype AS name, count(*)::int AS total
             FROM elevators
            WHERE elevatortype IS NOT NULL AND btrim(elevatortype::text)<>''
            GROUP BY elevatortype ORDER BY count(*) DESC, elevatortype"""
    )
    materials = await conn.fetch(
        """SELECT material AS name, count(*)::int AS total
             FROM elevators
            WHERE material IS NOT NULL AND btrim(material::text)<>''
            GROUP BY material ORDER BY count(*) DESC, material"""
    )
    fragments = await conn.fetch(
        ELEVATOR_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total
          FROM classified_elevators
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name ORDER BY fragment_name, fragment_id
        """
    )
    counts = await conn.fetchrow(
        ELEVATOR_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE quality_status='line_removed')::int AS line_removed,
               count(*) FILTER (WHERE quality_status='topology_missing')::int AS topology_missing,
               count(*) FILTER (WHERE quality_status='state_missing')::int AS state_missing,
               count(*) FILTER (WHERE quality_status='nozzle_unresolved')::int AS nozzle_unresolved,
               count(*) FILTER (WHERE quality_status='pending_calculation')::int AS pending_calculation,
               count(*) FILTER (WHERE longitude IS NOT NULL AND latitude IS NOT NULL)::int AS locatable
          FROM classified_elevators
        """
    )
    return {
        "states": [dict(row) for row in states],
        "elevator_types": [dict(row) for row in elevator_types],
        "materials": [dict(row) for row in materials],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
    }


async def get_elevators(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    search: Optional[str] = None,
    quality_status: Optional[ElevatorQualityStatus] = None,
    state_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    if state_id is not None:
        _add_filter(clauses, values, "item.state_id={param}", state_id)
    if fragment_id is not None:
        _add_filter(clauses, values, "item.fragment_id={param}", fragment_id)
    if line_id is not None:
        _add_filter(clauses, values, "item.line_id={param}", line_id)
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            "(item.node_id_1={param} OR item.node_id_2={param})",
            node_id,
        )
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(item.id::text={param} OR item.line_id::text={param}
                 OR coalesce(item.display_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.elevator_num_inst::text, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.material::text, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.registration_number, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        ELEVATOR_CTE + " SELECT count(*) FROM classified_elevators item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        ELEVATOR_CTE
        + " SELECT * FROM classified_elevators item"
        + where_sql
        + f"""
          ORDER BY CASE item.quality_status
                     WHEN 'line_missing' THEN 1 WHEN 'line_removed' THEN 2
                     WHEN 'state_missing' THEN 3 WHEN 'nozzle_unresolved' THEN 4
                     WHEN 'pending_calculation' THEN 5 WHEN 'topology_missing' THEN 6
                     ELSE 7 END,
                   item.elevator_type NULLS LAST, item.id
          LIMIT ${len(values) + 1} OFFSET ${len(values) + 2}
        """,
        *values,
        page_size,
        (page - 1) * page_size,
    )
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


async def _get_latest_any_output(
    conn: asyncpg.Connection, line_id: Optional[int]
) -> Optional[dict[str, Any]]:
    if line_id is None:
        return None
    columns = {
        row["column_name"]
        for row in await conn.fetch(
            """SELECT column_name FROM information_schema.columns
                WHERE table_schema=ANY(current_schemas(false)) AND table_name='any_out'"""
        )
    }
    if "lineid" not in columns:
        return None
    order = [
        column
        for column in ("calculationid", "id")
        if column in columns
    ]
    order_sql = ", ".join(f"output.{column} DESC NULLS LAST" for column in order)
    row = await conn.fetchrow(
        "SELECT output.* FROM any_out output WHERE output.lineid=$1"
        + (f" ORDER BY {order_sql}" if order_sql else "")
        + " LIMIT 1",
        line_id,
    )
    result = dict(row) if row else None
    if result and "calculationid" in result:
        calculation = await conn.fetchrow(
            "SELECT * FROM calculation WHERE id=$1", result["calculationid"]
        )
        result["calculation"] = dict(calculation) if calculation else None
    return result


async def get_elevator(
    conn: asyncpg.Connection, elevator_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        ELEVATOR_CTE + " SELECT * FROM classified_elevators item WHERE item.id=$1",
        elevator_id,
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow("SELECT * FROM elevators WHERE id=$1", elevator_id)
    result = dict(summary)
    try:
        latest_output = await _get_latest_any_output(conn, summary["line_id"])
    except (asyncpg.PostgresError, KeyError, TypeError):
        latest_output = None
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "latest_output": latest_output,
        }
    )
    return result
