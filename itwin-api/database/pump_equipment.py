from typing import Any, Literal, Optional

import asyncpg


PumpConfigurationStatus = Literal[
    "configured", "missing_model", "coefficients_missing", "line_missing"
]
PumpCatalogStatus = Literal["ready", "non_monotonic", "incomplete"]


PUMP_CTE = """
    WITH pump_inventory AS (
        SELECT pump.id, pump.lineid AS line_id, pump.number,
               nullif(btrim(pump.pumpstationid), '') AS station_name,
               pump.thrust, pump.standardpumpid AS standard_pump_id,
               standard.name AS model_name, standard.tip_nas AS model_type,
               pump.parallagregcount AS parallel_count,
               pump.drivetypeid AS drive_type_id, drive.name AS drive_type_name,
               pump.rotordiametertypeid AS rotor_diameter_type_id,
               rotor.name AS rotor_diameter_type_name,
               pump.standardemid AS standard_motor_id, motor.name AS motor_name,
               pump.rotorrotspeedset AS configured_rotation_speed,
               pump.rotordiameterset AS configured_rotor_diameter,
               pump.stateid AS state_id, state.name AS state_name,
               pump.opc, line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.nodeid1 AS node_id_1,
               line.nodeid2 AS node_id_2,
               CASE
                   WHEN line.id IS NULL THEN 'line_missing'
                   WHEN standard.id IS NULL THEN 'missing_model'
                   WHEN (coalesce(pump.r0, 0)=0 AND coalesce(pump.r1, 0)=0 AND coalesce(pump.r2, 0)=0)
                     OR (coalesce(pump.e0, 0)=0 AND coalesce(pump.e1, 0)=0 AND coalesce(pump.e2, 0)=0)
                     OR (coalesce(pump.k0, 0)=0 AND coalesce(pump.k1, 0)=0 AND coalesce(pump.k2, 0)=0)
                     OR (coalesce(pump.r0_z, 0)=0 AND coalesce(pump.r1_z, 0)=0 AND coalesce(pump.r2_z, 0)=0)
                     OR (coalesce(pump.e0_z, 0)=0 AND coalesce(pump.e1_z, 0)=0 AND coalesce(pump.e2_z, 0)=0)
                     OR (coalesce(pump.k0_z, 0)=0 AND coalesce(pump.k1_z, 0)=0 AND coalesce(pump.k2_z, 0)=0)
                       THEN 'coefficients_missing'
                   ELSE 'configured'
               END AS configuration_status,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_LineInterpolatePoint(line.shape, 0.5), 4326))
               END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_LineInterpolatePoint(line.shape, 0.5), 4326))
               END AS latitude
          FROM pumps pump
          LEFT JOIN linesobj line ON line.id=pump.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN standardpumps standard ON standard.id=pump.standardpumpid
          LEFT JOIN drivetypes drive ON drive.id=pump.drivetypeid
          LEFT JOIN rotordiametertypes rotor ON rotor.id=pump.rotordiametertypeid
          LEFT JOIN standardems motor ON motor.id=pump.standardemid
          LEFT JOIN states state ON state.id=pump.stateid
    )
"""


CATALOG_CTE = """
    WITH pump_catalog AS (
        SELECT standard.id, standard.name, standard.tip_nas AS pump_type,
               standard.producer,
               standard.q_min AS min_flow, standard.h_min AS head_at_min_flow,
               standard.q_max AS max_flow, standard.h_max AS head_at_max_flow,
               standard.q_nomin AS nominal_flow, standard.h_nomin AS nominal_head,
               standard.k_nomin AS nominal_efficiency,
               standard.d_nomin AS nominal_rotor_diameter,
               standard.rate_nomin AS nominal_rotation_speed,
               standard.t_max AS max_temperature,
               (SELECT count(*)::int FROM generate_series(1, 10) index
                 WHERE (ARRAY[standard.q1,standard.q2,standard.q3,standard.q4,standard.q5,
                              standard.q6,standard.q7,standard.q8,standard.q9,standard.q10])[index] IS NOT NULL
                   AND (ARRAY[standard.h1,standard.h2,standard.h3,standard.h4,standard.h5,
                              standard.h6,standard.h7,standard.h8,standard.h9,standard.h10])[index] IS NOT NULL
                   AND (ARRAY[standard.n1,standard.n2,standard.n3,standard.n4,standard.n5,
                              standard.n6,standard.n7,standard.n8,standard.n9,standard.n10])[index] IS NOT NULL
                   AND (ARRAY[standard.k1,standard.k2,standard.k3,standard.k4,standard.k5,
                              standard.k6,standard.k7,standard.k8,standard.k9,standard.k10])[index] IS NOT NULL
               ) AS point_count,
               coalesce((SELECT bool_and(q[index] < q[index + 1])
                   FROM (SELECT ARRAY[standard.q1,standard.q2,standard.q3,standard.q4,standard.q5,
                                      standard.q6,standard.q7,standard.q8,standard.q9,standard.q10] q) values
                   CROSS JOIN generate_series(1, 9) index
                  WHERE q[index] IS NOT NULL AND q[index + 1] IS NOT NULL), false) AS flow_is_monotonic,
               (standard.q_min IS NOT NULL AND standard.q_max IS NOT NULL
                AND standard.q_min < standard.q_max) AS has_valid_working_zone,
               (SELECT count(*)::int FROM pumps pump
                 WHERE pump.standardpumpid=standard.id) AS installed_count
          FROM standardpumps standard
    ), classified_catalog AS (
        SELECT catalog.*,
               CASE WHEN point_count < 10 OR NOT has_valid_working_zone THEN 'incomplete'
                    WHEN NOT flow_is_monotonic THEN 'non_monotonic'
                    ELSE 'ready' END AS quality_status
          FROM pump_catalog catalog
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_pump_equipment_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch("SELECT id, name, code FROM states ORDER BY ord, id")
    drive_types = await conn.fetch(
        "SELECT id, name, code FROM drivetypes ORDER BY ord, id"
    )
    rotor_types = await conn.fetch(
        "SELECT id, name, code FROM rotordiametertypes ORDER BY ord, id"
    )
    fragments = await conn.fetch(
        PUMP_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total,
               count(*) FILTER (WHERE configuration_status='configured')::int AS configured,
               count(*) FILTER (WHERE configuration_status='missing_model')::int AS missing_model,
               count(*) FILTER (WHERE configuration_status='coefficients_missing')::int AS coefficients_missing,
               count(*) FILTER (WHERE configuration_status='line_missing')::int AS line_missing
          FROM pump_inventory GROUP BY fragment_id, fragment_name
         ORDER BY fragment_name NULLS LAST, fragment_id
        """
    )
    counts = await conn.fetchrow(
        PUMP_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE configuration_status='configured')::int AS configured,
               count(*) FILTER (WHERE configuration_status='missing_model')::int AS missing_model,
               count(*) FILTER (WHERE configuration_status='coefficients_missing')::int AS coefficients_missing,
               count(*) FILTER (WHERE configuration_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE coalesce(line_removed, 0)=0)::int AS active_lines,
               count(*) FILTER (WHERE lower(coalesce(state_name, ''))='открыт')::int AS open,
               count(*) FILTER (WHERE lower(coalesce(state_name, ''))='закрыт')::int AS closed
          FROM pump_inventory
        """
    )
    catalog_counts = await conn.fetchrow(
        CATALOG_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='non_monotonic')::int AS non_monotonic,
               count(*) FILTER (WHERE quality_status='incomplete')::int AS incomplete,
               count(*) FILTER (WHERE installed_count > 0)::int AS used
          FROM classified_catalog
        """
    )
    pump_types = await conn.fetch(
        """
        SELECT tip_nas AS name, count(*)::int AS total
          FROM standardpumps WHERE nullif(btrim(tip_nas), '') IS NOT NULL
         GROUP BY tip_nas ORDER BY tip_nas
        """
    )
    return {
        "states": [dict(row) for row in states],
        "drive_types": [dict(row) for row in drive_types],
        "rotor_diameter_types": [dict(row) for row in rotor_types],
        "fragments": [dict(row) for row in fragments],
        "pump_types": [dict(row) for row in pump_types],
        "counts": dict(counts) if counts else {},
        "catalog_counts": dict(catalog_counts) if catalog_counts else {},
        "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
        "result_count": await conn.fetchval("SELECT count(*) FROM ns_out"),
    }


async def get_installed_pumps(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    configuration_status: Optional[PumpConfigurationStatus] = None,
    fragment_id: Optional[int] = None,
    state_id: Optional[int] = None,
    line_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if configuration_status:
        _add_filter(
            clauses, values, "pump.configuration_status={param}", configuration_status, "::text"
        )
    if fragment_id is not None:
        _add_filter(clauses, values, "pump.fragment_id={param}", fragment_id)
    if state_id is not None:
        _add_filter(clauses, values, "pump.state_id={param}", state_id)
    if line_id is not None:
        _add_filter(clauses, values, "pump.line_id={param}", line_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(pump.id::text={param} OR pump.line_id::text={param}
                 OR coalesce(pump.number, '') ILIKE '%' || {param} || '%'
                 OR coalesce(pump.station_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(pump.model_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(pump.model_type, '') ILIKE '%' || {param} || '%'
                 OR coalesce(pump.fragment_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        PUMP_CTE + " SELECT count(*) FROM pump_inventory pump" + where_sql, *values
    )
    rows = await conn.fetch(
        PUMP_CTE
        + " SELECT * FROM pump_inventory pump"
        + where_sql
        + f"""
          ORDER BY CASE pump.configuration_status
                       WHEN 'line_missing' THEN 1 WHEN 'missing_model' THEN 2
                       WHEN 'coefficients_missing' THEN 3 ELSE 4 END,
                   pump.fragment_name NULLS LAST, pump.id
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


async def get_pump_catalog(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    quality_status: Optional[PumpCatalogStatus] = None,
    pump_type: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if quality_status:
        _add_filter(clauses, values, "catalog.quality_status={param}", quality_status, "::text")
    if pump_type:
        _add_filter(clauses, values, "catalog.pump_type={param}", pump_type, "::text")
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(catalog.id::text={param}
                 OR coalesce(catalog.name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(catalog.pump_type, '') ILIKE '%' || {param} || '%'
                 OR coalesce(catalog.producer, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        CATALOG_CTE + " SELECT count(*) FROM classified_catalog catalog" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        CATALOG_CTE
        + " SELECT * FROM classified_catalog catalog"
        + where_sql
        + f"""
          ORDER BY CASE catalog.quality_status WHEN 'incomplete' THEN 1
                       WHEN 'non_monotonic' THEN 2 ELSE 3 END,
                   catalog.pump_type NULLS LAST, catalog.name, catalog.id
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


async def _get_standard_pump(
    conn: asyncpg.Connection, standard_pump_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        CATALOG_CTE
        + " SELECT * FROM classified_catalog catalog WHERE catalog.id=$1",
        standard_pump_id,
    )
    if summary is None:
        return None
    standard = await conn.fetchrow("SELECT * FROM standardpumps WHERE id=$1", standard_pump_id)
    points = await conn.fetch(
        """
        SELECT index, q[index] AS flow, h[index] AS head,
               n[index] AS power, k[index] AS efficiency
          FROM (SELECT ARRAY[q1,q2,q3,q4,q5,q6,q7,q8,q9,q10] q,
                       ARRAY[h1,h2,h3,h4,h5,h6,h7,h8,h9,h10] h,
                       ARRAY[n1,n2,n3,n4,n5,n6,n7,n8,n9,n10] n,
                       ARRAY[k1,k2,k3,k4,k5,k6,k7,k8,k9,k10] k
                  FROM standardpumps WHERE id=$1) values
         CROSS JOIN generate_series(1, 10) index ORDER BY index
        """,
        standard_pump_id,
    )
    result = dict(summary)
    result["parameters"] = dict(standard) if standard else {}
    result["points"] = [dict(row) for row in points]
    return result


async def get_installed_pump(
    conn: asyncpg.Connection, pump_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        PUMP_CTE + " SELECT * FROM pump_inventory pump WHERE pump.id=$1", pump_id
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow("SELECT * FROM pumps WHERE id=$1", pump_id)
    standard = None
    if summary["standard_pump_id"] is not None:
        standard = await _get_standard_pump(conn, summary["standard_pump_id"])
    latest_output = await conn.fetchrow(
        """
        SELECT output.id, output.calculationid AS calculation_id,
               calculation.name AS calculation_name, calculation.date1 AS calculated_at,
               output.sos AS equipment_state,
               output.a4 AS inlet_dynamic_head,
               output.a8 AS outlet_dynamic_head,
               output.a13 AS working_head,
               output.a14 AS working_flow,
               output.a15 AS inlet_piezometric_head,
               output.a16 AS outlet_piezometric_head,
               output.a17 AS operation_status,
               output.a18 AS working_pump_count
          FROM ns_out output
          LEFT JOIN calculation ON calculation.id=output.calculationid
         WHERE output.lineid=$1
         ORDER BY calculation.date1 DESC NULLS LAST, output.calculationid DESC, output.id DESC
         LIMIT 1
        """,
        summary["line_id"],
    )
    related = await conn.fetch(
        """
        SELECT id, lineid AS line_id, number, pumpstationid AS station_name,
               standardpumpid AS standard_pump_id, stateid AS state_id
          FROM pumps
         WHERE id<>$1 AND (
               (nullif(btrim($2::text), '') IS NOT NULL
                AND lower(btrim(pumpstationid))=lower(btrim($2::text)))
               OR lineid=$3)
         ORDER BY id LIMIT 50
        """,
        pump_id,
        summary["station_name"],
        summary["line_id"],
    )
    station = None
    if summary["station_name"]:
        station = await conn.fetchrow(
            """
            SELECT station.*, node.fileid AS fragment_id,
                   CASE WHEN node.shape IS NULL THEN NULL
                        ELSE ST_X(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS longitude,
                   CASE WHEN node.shape IS NULL THEN NULL
                        ELSE ST_Y(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS latitude
              FROM pumpstations station LEFT JOIN nodes node ON node.id=station.nodeid
             WHERE lower(btrim(station.name))=lower(btrim($1)) ORDER BY station.id LIMIT 1
            """,
            summary["station_name"],
        )
    result = dict(summary)
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "standard_pump": standard,
            "latest_output": dict(latest_output) if latest_output else None,
            "station": dict(station) if station else None,
            "related_pumps": [dict(row) for row in related],
        }
    )
    return result


async def get_standard_pump(
    conn: asyncpg.Connection, standard_pump_id: int
) -> Optional[dict[str, Any]]:
    result = await _get_standard_pump(conn, standard_pump_id)
    if result is None:
        return None
    installed = await conn.fetch(
        PUMP_CTE
        + """
        SELECT id, line_id, number, station_name, state_id, state_name,
               fragment_id, fragment_name, configuration_status, longitude, latitude
          FROM pump_inventory pump WHERE standard_pump_id=$1 ORDER BY id LIMIT 100
        """,
        standard_pump_id,
    )
    result["installed_pumps"] = [dict(row) for row in installed]
    return result
