from typing import Any, Literal, Optional

import asyncpg


BypassQualityStatus = Literal[
    "ready",
    "line_missing",
    "line_removed",
    "connection_node_missing",
    "setpoint_missing",
    "geometry_parameters_invalid",
]


BYPASS_CTE = """
    WITH bypass_inventory AS (
        SELECT bypass.id, bypass.lineid AS line_id,
               line.id AS linked_line_id, bypass.nodeid AS connection_node_id,
               connection_node.id AS linked_connection_node_id,
               coalesce(nullif(btrim(bypass.locinstall), ''), 'Байпас №' || bypass.id) AS display_name,
               bypass.q AS target_flow, bypass.deltaq AS flow_tolerance,
               bypass.h AS target_head, bypass.deltah AS head_tolerance,
               bypass.length, bypass.diameterinternal AS internal_diameter,
               bypass.tuberoughness AS tube_roughness,
               bypass.rescoeffssum AS local_resistance_coefficients,
               bypass.locinstall AS installation_place,
               bypass.standardid AS standard_id, standard.name AS standard_name,
               bypass.standardtubelink AS standard_tube_id,
               tube.stand AS tube_standard, tube.diametr_usl AS tube_nominal_diameter,
               tube.diamvne AS tube_external_diameter, tube.diametr AS tube_internal_diameter,
               tube.tol AS tube_wall_thickness,
               bypass.regulatorstateid AS state_id, state.name AS state_name,
               bypass.pipelinesignid AS pipeline_sign_id,
               pipeline_sign.name AS pipeline_sign_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               connection_code.name AS connection_node_code,
               connection_node.externalnodename AS connection_node_name,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM bypass
          LEFT JOIN linesobj line ON line.id=bypass.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN nodes connection_node ON connection_node.id=bypass.nodeid
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN externalcodes connection_code ON connection_code.id=connection_node.externalcodeid
          LEFT JOIN regulatorstates state ON state.id=bypass.regulatorstateid
          LEFT JOIN pipelinesigns pipeline_sign ON pipeline_sign.id=bypass.pipelinesignid
          LEFT JOIN standards standard ON standard.id=bypass.standardid
          LEFT JOIN standardtubes tube ON tube.id=bypass.standardtubelink
    ), classified_bypasses AS (
        SELECT inventory.*,
               CASE WHEN inventory.linked_line_id IS NULL THEN 'line_missing'
                    WHEN coalesce(inventory.line_removed, 0)<>0 THEN 'line_removed'
                    WHEN inventory.connection_node_id IS NULL
                      OR inventory.linked_connection_node_id IS NULL THEN 'connection_node_missing'
                    WHEN inventory.target_flow IS NULL OR inventory.target_flow<=0
                      THEN 'setpoint_missing'
                    WHEN inventory.length IS NULL OR inventory.length<=0
                      OR inventory.internal_diameter IS NULL OR inventory.internal_diameter<=0
                      OR inventory.tube_roughness IS NULL OR inventory.tube_roughness<0
                      OR inventory.local_resistance_coefficients IS NULL
                      OR inventory.local_resistance_coefficients<0
                      THEN 'geometry_parameters_invalid'
                    ELSE 'ready' END AS quality_status
          FROM bypass_inventory inventory
    )
"""


TUBE_CTE = """
    WITH tube_catalog AS (
        SELECT tube.id,
               coalesce(nullif(btrim(tube.name), ''), tube.stand || ' DN ' || tube.diametr_usl::text) AS display_name,
               tube.name, tube.stand AS standard, tube.izgotov AS manufacturer,
               tube.material, tube.diametr_usl AS nominal_diameter,
               tube.diamvne AS external_diameter, tube.diametr AS internal_diameter,
               tube.tol AS wall_thickness, tube.s_sech AS section_area,
               tube.s_1m AS surface_per_meter, tube.massa_1m AS mass_per_meter,
               tube.massa_1m_izol AS insulated_mass_per_meter,
               CASE WHEN tube.stand IS NULL OR btrim(tube.stand)=''
                          OR tube.diametr_usl IS NULL OR tube.diametr_usl<=0
                          OR tube.diamvne IS NULL OR tube.diamvne<=0
                          OR tube.diametr IS NULL OR tube.diametr<=0
                          OR tube.tol IS NULL OR tube.tol<=0
                    THEN 'incomplete' ELSE 'ready' END AS quality_status,
               (SELECT count(*)::int FROM bypass WHERE bypass.standardtubelink=tube.id) AS installed_count
          FROM standardtubes tube
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_network_bypass_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch("SELECT id, name, code FROM regulatorstates ORDER BY ord, id")
    pipeline_signs = await conn.fetch(
        "SELECT id, name, code FROM pipelinesigns ORDER BY ord, id"
    )
    standards = await conn.fetch("SELECT id, name, code FROM standards ORDER BY ord, id")
    tube_standards = await conn.fetch(
        "SELECT DISTINCT stand AS name FROM standardtubes "
        "WHERE stand IS NOT NULL AND btrim(stand)<>'' ORDER BY stand"
    )
    fragments = await conn.fetch(
        BYPASS_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total
          FROM classified_bypasses
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name ORDER BY fragment_name, fragment_id
        """
    )
    counts = await conn.fetchrow(
        BYPASS_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE quality_status='line_removed')::int AS line_removed,
               count(*) FILTER (WHERE quality_status='connection_node_missing')::int AS connection_node_missing,
               count(*) FILTER (WHERE quality_status='setpoint_missing')::int AS setpoint_missing,
               count(*) FILTER (WHERE quality_status='geometry_parameters_invalid')::int AS geometry_parameters_invalid,
               count(*) FILTER (WHERE state_id=1)::int AS opened,
               count(*) FILTER (WHERE state_id=2)::int AS closed,
               count(*) FILTER (WHERE state_id=3)::int AS inactive,
               count(*) FILTER (WHERE longitude IS NOT NULL AND latitude IS NOT NULL)::int AS locatable,
               count(*) FILTER (WHERE longitude IS NULL OR latitude IS NULL)::int AS geometry_missing
          FROM classified_bypasses
        """
    )
    tube_counts = await conn.fetchrow(
        TUBE_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='incomplete')::int AS incomplete,
               count(DISTINCT standard)::int AS standards
          FROM tube_catalog
        """
    )
    return {
        "states": [dict(row) for row in states],
        "pipeline_signs": [dict(row) for row in pipeline_signs],
        "standards": [dict(row) for row in standards],
        "tube_standards": [dict(row) for row in tube_standards],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "tube_counts": dict(tube_counts) if tube_counts else {},
        "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
        "result_count": await conn.fetchval("SELECT count(*) FROM bp_out"),
    }


async def get_network_bypasses(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    quality_status: Optional[BypassQualityStatus] = None,
    state_id: Optional[int] = None,
    pipeline_sign_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    line_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    if state_id is not None:
        _add_filter(clauses, values, "item.state_id={param}", state_id)
    if pipeline_sign_id is not None:
        _add_filter(clauses, values, "item.pipeline_sign_id={param}", pipeline_sign_id)
    if fragment_id is not None:
        _add_filter(clauses, values, "item.fragment_id={param}", fragment_id)
    if line_id is not None:
        _add_filter(clauses, values, "item.line_id={param}", line_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(item.id::text={param} OR item.line_id::text={param}
                 OR coalesce(item.display_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.connection_node_code, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.connection_node_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.fragment_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        BYPASS_CTE + " SELECT count(*) FROM classified_bypasses item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        BYPASS_CTE
        + " SELECT * FROM classified_bypasses item"
        + where_sql
        + f"""
          ORDER BY CASE item.quality_status
                     WHEN 'line_missing' THEN 1 WHEN 'line_removed' THEN 2
                     WHEN 'connection_node_missing' THEN 3 WHEN 'setpoint_missing' THEN 4
                     WHEN 'geometry_parameters_invalid' THEN 5 ELSE 6 END,
                   item.fragment_name NULLS LAST, item.id
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


async def get_network_bypass(
    conn: asyncpg.Connection, bypass_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        BYPASS_CTE + " SELECT * FROM classified_bypasses item WHERE item.id=$1",
        bypass_id,
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow("SELECT * FROM bypass WHERE id=$1", bypass_id)
    latest_output = await conn.fetchrow(
        """
        SELECT output.id, output.calculationid AS calculation_id,
               calculation.name AS calculation_name, calculation.date1 AS calculated_at,
               output.sos AS state_text, output.externalsignlineid AS external_sign_line_id,
               output.a4 AS geodetic_mark_in, output.a5 AS piezometric_head_in,
               output.a9 AS geodetic_mark_out, output.a10 AS piezometric_head_out,
               output.a11 AS diaphragm_diameter, output.a12 AS diaphragm_head_loss,
               output.a13 AS flow, output.a14 AS installation_place,
               output.a15 AS bypass_internal_diameter, output.a16 AS bypass_length,
               output.a17 AS bypass_head_loss, output.a18 AS total_head_loss,
               output.sopr AS hydraulic_resistance,
               output.ist AS heat_source_id, source.sourcename AS heat_source_name
          FROM bp_out output
          LEFT JOIN calculation ON calculation.id=output.calculationid
          LEFT JOIN heatsources source ON source.id=output.ist
         WHERE output.lineid=$1
         ORDER BY calculation.date1 DESC NULLS LAST,
                  output.calculationid DESC, output.id DESC LIMIT 1
        """,
        summary["line_id"],
    )
    selected_tube = None
    if summary["standard_tube_id"] is not None:
        selected_tube = await conn.fetchrow(
            TUBE_CTE + " SELECT * FROM tube_catalog item WHERE item.id=$1",
            summary["standard_tube_id"],
        )
    related = await conn.fetch(
        BYPASS_CTE
        + """
        SELECT id, display_name, state_id, state_name, quality_status
          FROM classified_bypasses item
         WHERE item.line_id=$1 AND item.id<>$2 ORDER BY item.id LIMIT 50
        """,
        summary["line_id"],
        bypass_id,
    )
    result = dict(summary)
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "latest_output": dict(latest_output) if latest_output else None,
            "selected_tube": dict(selected_tube) if selected_tube else None,
            "related_bypasses": [dict(row) for row in related],
        }
    )
    return result


async def get_standard_tubes(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    standard: Optional[str] = None,
    quality_status: Optional[Literal["ready", "incomplete"]] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if standard:
        _add_filter(clauses, values, "item.standard={param}", standard, "::text")
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(item.id::text={param}
                 OR coalesce(item.display_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.standard, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.manufacturer, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.material, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        TUBE_CTE + " SELECT count(*) FROM tube_catalog item" + where_sql, *values
    )
    rows = await conn.fetch(
        TUBE_CTE
        + " SELECT * FROM tube_catalog item"
        + where_sql
        + f" ORDER BY item.standard, item.nominal_diameter, item.external_diameter, item.id LIMIT ${len(values)+1} OFFSET ${len(values)+2}",
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


async def get_standard_tube(
    conn: asyncpg.Connection, standard_tube_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        TUBE_CTE + " SELECT * FROM tube_catalog item WHERE item.id=$1",
        standard_tube_id,
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow(
        "SELECT * FROM standardtubes WHERE id=$1", standard_tube_id
    )
    result = dict(summary)
    result["attributes"] = dict(attributes) if attributes else {}
    return result
