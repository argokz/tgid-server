from typing import Any, Literal, Optional

import asyncpg


ArmatureType = Literal["damper", "regulating"]
ArmatureQualityStatus = Literal[
    "ready", "line_missing", "line_removed", "purpose_unknown", "diameter_suspicious"
]


ARMATURE_CTE = """
    WITH armature_inventory AS (
        SELECT 'damper'::text AS equipment_type, damper.id,
               damper.lineid AS line_id,
               coalesce(nullif(btrim(damper.name), ''), 'Задвижка №' || damper.id) AS display_name,
               nullif(btrim(damper.dispatcherswitch), '') AS purpose_name,
               damper.diametercondit AS nominal_diameter,
               damper.partdempopen AS opening_percent,
               damper.relatleakage AS relative_leakage,
               damper.turncount AS turn_count,
               damper.gatecontrol AS gate_control,
               damper.clue, damper.thrustcollar AS thrust_collar,
               damper.opc,
               nullif(damper.standarddamplink, 0) AS standard_id,
               standard.name_zc AS standard_mark,
               CASE WHEN standard.id IS NOT NULL THEN 'linked'
                    WHEN damper.standarddamplink IS NOT NULL
                     AND damper.standarddamplink<>0 THEN 'orphan'
                    ELSE 'unassigned' END AS catalog_status,
               NULL::double precision AS set_pressure_drop,
               NULL::double precision AS set_head,
               NULL::double precision AS set_delta_head,
               NULL::double precision AS set_delta_flow,
               NULL::double precision AS set_flow,
               damper.damperarmaturestateid AS state_id,
               state.name AS state_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM dampers damper
          LEFT JOIN linesobj line ON line.id=damper.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN damperarmaturestates state ON state.id=damper.damperarmaturestateid
          LEFT JOIN standarddampers standard ON standard.id=nullif(damper.standarddamplink, 0)
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
        UNION ALL
        SELECT 'regulating'::text AS equipment_type, armature.id,
               armature.lineid AS line_id,
               coalesce(nullif(btrim(armature.name), ''),
                        'Регулирующая арматура №' || armature.id) AS display_name,
               nullif(btrim(armature.regarmtype), '') AS purpose_name,
               armature.diametercondit AS nominal_diameter,
               armature.damperopendeg AS opening_percent,
               armature.relleakage AS relative_leakage,
               armature.rotationcount AS turn_count,
               armature.gatecontrol, armature.clue,
               armature.thrustcollar AS thrust_collar,
               armature.opc,
               NULL::integer AS standard_id, NULL::varchar AS standard_mark,
               'unassigned'::text AS catalog_status,
               armature.regpdmean AS set_pressure_drop,
               armature.h AS set_head, armature.deltah AS set_delta_head,
               armature.deltaq AS set_delta_flow, armature.q AS set_flow,
               armature.damperarmaturestateid AS state_id,
               state.name AS state_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM regularmatures armature
          LEFT JOIN linesobj line ON line.id=armature.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN damperarmaturestates state ON state.id=armature.damperarmaturestateid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
    ), classified_armatures AS (
        SELECT inventory.*,
               CASE WHEN inventory.line_removed IS NULL THEN 'line_missing'
                    WHEN inventory.line_removed<>0 THEN 'line_removed'
                    WHEN inventory.purpose_name IS NULL OR inventory.purpose_name='?'
                      THEN 'purpose_unknown'
                    WHEN inventory.nominal_diameter IS NULL
                      OR inventory.nominal_diameter<=0
                      OR inventory.nominal_diameter>5000 THEN 'diameter_suspicious'
                    ELSE 'ready' END AS quality_status
          FROM armature_inventory inventory
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_network_armature_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch(
        "SELECT id, name, code FROM damperarmaturestates ORDER BY ord, id"
    )
    purposes = await conn.fetch(
        ARMATURE_CTE
        + """
        SELECT equipment_type, purpose_name AS name, count(*)::int AS total
          FROM classified_armatures
         WHERE purpose_name IS NOT NULL
         GROUP BY equipment_type, purpose_name
         ORDER BY equipment_type, total DESC, purpose_name
        """
    )
    fragments = await conn.fetch(
        ARMATURE_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total,
               count(*) FILTER (WHERE equipment_type='damper')::int AS dampers,
               count(*) FILTER (WHERE equipment_type='regulating')::int AS regulating
          FROM classified_armatures
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name ORDER BY fragment_name, fragment_id
        """
    )
    counts = await conn.fetchrow(
        ARMATURE_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE equipment_type='damper')::int AS dampers,
               count(*) FILTER (WHERE equipment_type='regulating')::int AS regulating,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE quality_status='line_removed')::int AS line_removed,
               count(*) FILTER (WHERE quality_status='purpose_unknown')::int AS purpose_unknown,
               count(*) FILTER (WHERE quality_status='diameter_suspicious')::int AS diameter_suspicious,
               count(*) FILTER (WHERE line_removed=0)::int AS active_lines,
               count(*) FILTER (WHERE purpose_name IS NULL OR purpose_name='?')::int AS purpose_unknown_total,
               count(*) FILTER (WHERE nominal_diameter IS NULL OR nominal_diameter<=0
                                  OR nominal_diameter>5000)::int AS diameter_suspicious_total,
               count(*) FILTER (WHERE state_id=1)::int AS opened,
               count(*) FILTER (WHERE state_id=2)::int AS closed,
               count(*) FILTER (WHERE longitude IS NOT NULL AND latitude IS NOT NULL)::int AS locatable,
               count(*) FILTER (WHERE longitude IS NULL OR latitude IS NULL)::int AS geometry_missing,
               count(*) FILTER (WHERE catalog_status='linked')::int AS catalog_linked,
               count(*) FILTER (WHERE catalog_status='unassigned')::int AS catalog_unassigned,
               count(*) FILTER (WHERE catalog_status='orphan')::int AS catalog_orphan
          FROM classified_armatures
        """
    )
    return {
        "states": [dict(row) for row in states],
        "purposes": [dict(row) for row in purposes],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "catalog_count": await conn.fetchval("SELECT count(*) FROM standarddampers"),
        "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
        "damper_result_count": await conn.fetchval("SELECT count(*) FROM zd_out"),
        "regulating_result_count": await conn.fetchval("SELECT count(*) FROM zd2_out"),
        "passport_asset_count": await conn.fetchval(
            "SELECT count(*) FROM zapornaya_armatura"
        ),
    }


async def get_network_armatures(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    equipment_type: Optional[ArmatureType] = None,
    quality_status: Optional[ArmatureQualityStatus] = None,
    state_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    purpose: Optional[str] = None,
    line_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if equipment_type:
        _add_filter(clauses, values, "item.equipment_type={param}", equipment_type, "::text")
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    if state_id is not None:
        _add_filter(clauses, values, "item.state_id={param}", state_id)
    if fragment_id is not None:
        _add_filter(clauses, values, "item.fragment_id={param}", fragment_id)
    if purpose:
        _add_filter(clauses, values, "item.purpose_name={param}", purpose, "::text")
    if line_id is not None:
        _add_filter(clauses, values, "item.line_id={param}", line_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(item.id::text={param} OR item.line_id::text={param}
                 OR coalesce(item.display_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.purpose_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.standard_mark, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_1, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_code_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.node_name_2, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.fragment_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        ARMATURE_CTE + " SELECT count(*) FROM classified_armatures item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        ARMATURE_CTE
        + " SELECT * FROM classified_armatures item"
        + where_sql
        + f"""
          ORDER BY CASE item.quality_status
                     WHEN 'line_missing' THEN 1 WHEN 'line_removed' THEN 2
                     WHEN 'purpose_unknown' THEN 3 WHEN 'diameter_suspicious' THEN 4
                     ELSE 5 END,
                   item.fragment_name NULLS LAST, item.equipment_type, item.id
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


async def get_network_armature(
    conn: asyncpg.Connection, equipment_type: ArmatureType, armature_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        ARMATURE_CTE
        + """ SELECT * FROM classified_armatures item
               WHERE item.equipment_type=$1 AND item.id=$2""",
        equipment_type,
        armature_id,
    )
    if summary is None:
        return None
    table_name = "dampers" if equipment_type == "damper" else "regularmatures"
    output_table = "zd_out" if equipment_type == "damper" else "zd2_out"
    attributes = await conn.fetchrow(
        f"SELECT * FROM {table_name} WHERE id=$1", armature_id
    )
    standard = None
    if summary["standard_id"] is not None:
        row = await conn.fetchrow(
            "SELECT * FROM standarddampers WHERE id=$1", summary["standard_id"]
        )
        if row:
            standard = dict(row)
            standard.update(
                {
                    "installed_count": await conn.fetchval(
                        "SELECT count(*) FROM dampers WHERE nullif(standarddamplink, 0)=$1",
                        summary["standard_id"],
                    ),
                    "installed_armatures": [],
                    "quality_status": "incomplete"
                    if any(row[field] is None for field in ("name_zc", "d", "p", "t"))
                    else "ready",
                }
            )
    latest_output = await conn.fetchrow(
        f"""
        SELECT output.id, output.calculationid AS calculation_id,
               calculation.name AS calculation_name, calculation.date1 AS calculated_at,
               output.sos AS state_code, output.a7 AS state_text,
               output.a8 AS content_name, output.a9 AS flow,
               output.a10 AS head_loss, output.a11 AS hydraulic_resistance,
               output.a12 AS available_head_end, output.a13 AS piezometric_head_end,
               output.a14 AS geodetic_mark_end, output.a15 AS total_head_end
          FROM {output_table} output
          LEFT JOIN calculation ON calculation.id=output.calculationid
         WHERE output.lineid=$1
         ORDER BY calculation.date1 DESC NULLS LAST,
                  output.calculationid DESC, output.id DESC LIMIT 1
        """,
        summary["line_id"],
    )
    related = await conn.fetch(
        ARMATURE_CTE
        + """
        SELECT equipment_type, id, display_name, purpose_name, state_id, state_name,
               quality_status
          FROM classified_armatures item
         WHERE item.line_id=$1 AND NOT (item.equipment_type=$2 AND item.id=$3)
         ORDER BY item.equipment_type, item.id LIMIT 50
        """,
        summary["line_id"],
        equipment_type,
        armature_id,
    )
    result = dict(summary)
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "standard": standard,
            "latest_output": dict(latest_output) if latest_output else None,
            "related_armatures": [dict(row) for row in related],
        }
    )
    return result


async def get_standard_dampers(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    search: Optional[str] = None,
) -> dict[str, Any]:
    values: list[Any] = []
    where_sql = ""
    normalized_search = (search or "").strip()
    if normalized_search:
        values.append(normalized_search)
        where_sql = """ WHERE standard.id::text=$1 OR coalesce(standard.name, '') ILIKE '%' || $1 || '%'
                          OR coalesce(standard.name_zc, '') ILIKE '%' || $1 || '%'
                          OR coalesce(standard.producer, '') ILIKE '%' || $1 || '%'
                          OR coalesce(standard.material, '') ILIKE '%' || $1 || '%'"""
    base_sql = """
        SELECT standard.*,
               (SELECT count(*)::int FROM dampers damper
                 WHERE nullif(damper.standarddamplink, 0)=standard.id) AS installed_count,
               CASE WHEN standard.name_zc IS NULL OR standard.d IS NULL
                          OR standard.p IS NULL OR standard.t IS NULL
                    THEN 'incomplete' ELSE 'ready' END AS quality_status
          FROM standarddampers standard
    """
    total = await conn.fetchval(
        "SELECT count(*) FROM standarddampers standard" + where_sql, *values
    )
    rows = await conn.fetch(
        base_sql
        + where_sql
        + f" ORDER BY standard.name_zc, standard.d, standard.id LIMIT ${len(values)+1} OFFSET ${len(values)+2}",
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


async def get_standard_damper(
    conn: asyncpg.Connection, standard_id: int
) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow("SELECT * FROM standarddampers WHERE id=$1", standard_id)
    if row is None:
        return None
    installed = await conn.fetch(
        ARMATURE_CTE
        + """
        SELECT equipment_type, id, line_id, display_name, purpose_name,
               nominal_diameter, state_id, state_name, fragment_id, fragment_name,
               quality_status, longitude, latitude
          FROM classified_armatures item
         WHERE item.equipment_type='damper' AND item.standard_id=$1
         ORDER BY item.id LIMIT 100
        """,
        standard_id,
    )
    result = dict(row)
    result["installed_count"] = len(installed)
    result["installed_armatures"] = [dict(item) for item in installed]
    result["quality_status"] = (
        "incomplete"
        if any(result.get(field) is None for field in ("name_zc", "d", "p", "t"))
        else "ready"
    )
    return result
