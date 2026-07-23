from typing import Any, Literal, Optional

import asyncpg


RegulatorType = Literal["pressure", "flow", "differential"]
RegulatorQualityStatus = Literal[
    "ready",
    "line_missing",
    "line_removed",
    "control_node_missing",
    "setpoint_missing",
    "capacity_missing",
]


REGULATOR_TABLES: dict[str, str] = {
    "pressure": "pressregulators",
    "flow": "consumptregulators",
    "differential": "pressdropregulators",
}

CATALOG_TABLES: dict[str, str] = {
    "pressure": "standardpressregulators",
    "flow": "standardconsregulators",
    "differential": "standardpressdropregulators",
}


REGULATOR_CTE = """
    WITH regulator_inventory AS (
        SELECT 'pressure'::text AS regulator_type, regulator.id,
               regulator.lineid AS line_id, regulator.nodeid AS control_node_id,
               'Регулятор давления №' || regulator.id AS display_name,
               regulator.h AS set_value, regulator.deltah AS tolerance,
               regulator.regvalverelcap::double precision AS capacity,
               regulator.valvehydroresopen AS hydraulic_resistance_open,
               regulator.valvehydroresclose AS hydraulic_resistance_closed,
               regulator.relleakage AS relative_leakage,
               regulator.consdrip AS leakage_flow,
               NULL::double precision AS actual_flow,
               NULL::double precision AS actual_value,
               NULL::varchar AS opc,
               regulator.workattrid AS work_attribute_id,
               work_attribute.name AS work_attribute_name,
               regulator.regulatorstateid AS state_id, state.name AS state_name,
               regulator.pipelinesignid AS pipeline_sign_id,
               pipeline_sign.name AS pipeline_sign_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               control_code.name AS control_node_code,
               control_node.externalnodename AS control_node_name,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM pressregulators regulator
          LEFT JOIN linesobj line ON line.id=regulator.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN regulatorstates state ON state.id=regulator.regulatorstateid
          LEFT JOIN workattributes work_attribute ON work_attribute.id=regulator.workattrid
          LEFT JOIN pipelinesigns pipeline_sign ON pipeline_sign.id=regulator.pipelinesignid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN nodes control_node ON control_node.id=regulator.nodeid
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN externalcodes control_code ON control_code.id=control_node.externalcodeid
        UNION ALL
        SELECT 'flow'::text AS regulator_type, regulator.id,
               regulator.lineid AS line_id, regulator.nodeid AS control_node_id,
               'Регулятор расхода №' || regulator.id AS display_name,
               regulator.regconsmean AS set_value, regulator.deltah AS tolerance,
               regulator.regvalvecap::double precision AS capacity,
               regulator.hydroresopen AS hydraulic_resistance_open,
               regulator.hydroresclose AS hydraulic_resistance_closed,
               regulator.relatleakage AS relative_leakage,
               regulator.plumsconsumption AS leakage_flow,
               NULL::double precision AS actual_flow,
               NULL::double precision AS actual_value,
               regulator.opc,
               regulator.workattrid AS work_attribute_id,
               work_attribute.name AS work_attribute_name,
               regulator.regulatorstateid AS state_id, state.name AS state_name,
               NULL::integer AS pipeline_sign_id, NULL::varchar AS pipeline_sign_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               control_code.name AS control_node_code,
               control_node.externalnodename AS control_node_name,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM consumptregulators regulator
          LEFT JOIN linesobj line ON line.id=regulator.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN regulatorstates state ON state.id=regulator.regulatorstateid
          LEFT JOIN workattributes work_attribute ON work_attribute.id=regulator.workattrid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN nodes control_node ON control_node.id=regulator.nodeid
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN externalcodes control_code ON control_code.id=control_node.externalcodeid
        UNION ALL
        SELECT 'differential'::text AS regulator_type, regulator.id,
               regulator.lineid AS line_id, regulator.nodeid AS control_node_id,
               'Регулятор перепада №' || regulator.id AS display_name,
               regulator.pressdropmean AS set_value, regulator.deltah AS tolerance,
               regulator.regvalverelcap::double precision AS capacity,
               regulator.regvalvehydrores AS hydraulic_resistance_open,
               NULL::double precision AS hydraulic_resistance_closed,
               regulator.maxleakageclosevalve AS relative_leakage,
               regulator.consdrip AS leakage_flow,
               regulator.consthroughregvalve AS actual_flow,
               regulator.thrustdropmean AS actual_value,
               NULL::varchar AS opc,
               regulator.workattrid AS work_attribute_id,
               work_attribute.name AS work_attribute_name,
               regulator.regulatorstateid AS state_id, state.name AS state_name,
               NULL::integer AS pipeline_sign_id, NULL::varchar AS pipeline_sign_name,
               line.fileid AS fragment_id, fragment.name AS fragment_name,
               line.removed AS line_removed, line.hydrores AS line_hydraulic_resistance,
               line.nodeid1 AS node_id_1, line.nodeid2 AS node_id_2,
               code1.name AS node_code_1, node1.externalnodename AS node_name_1,
               code2.name AS node_code_2, node2.externalnodename AS node_name_2,
               control_code.name AS control_node_code,
               control_node.externalnodename AS control_node_name,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM pressdropregulators regulator
          LEFT JOIN linesobj line ON line.id=regulator.lineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN regulatorstates state ON state.id=regulator.regulatorstateid
          LEFT JOIN workattributes work_attribute ON work_attribute.id=regulator.workattrid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN nodes control_node ON control_node.id=regulator.nodeid
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN externalcodes control_code ON control_code.id=control_node.externalcodeid
    ), classified_regulators AS (
        SELECT inventory.*,
               CASE WHEN inventory.line_removed IS NULL THEN 'line_missing'
                    WHEN inventory.line_removed<>0 THEN 'line_removed'
                    WHEN inventory.regulator_type IN ('pressure', 'differential')
                     AND inventory.control_node_id IS NULL THEN 'control_node_missing'
                    WHEN inventory.set_value IS NULL OR inventory.set_value<=0
                      THEN 'setpoint_missing'
                    WHEN inventory.capacity IS NULL OR inventory.capacity<=0
                      THEN 'capacity_missing'
                    ELSE 'ready' END AS quality_status
          FROM regulator_inventory inventory
    )
"""


CATALOG_CTE = """
    WITH regulator_catalog AS (
        SELECT 'pressure'::text AS catalog_type, standard.id,
               standard.name_rd AS display_name, standard.typ_rd AS series,
               standard.typ AS model, standard.producer,
               standard.d_usl AS nominal_diameter, standard.kv AS capacity,
               NULL::varchar AS medium, standard.t AS max_temperature,
               NULL::double precision AS pressure_min,
               NULL::double precision AS pressure_max,
               NULL::varchar AS drive_type, NULL::varchar AS installation_place,
               CASE WHEN standard.name_rd IS NULL OR standard.typ IS NULL
                          OR standard.d_usl IS NULL OR standard.d_usl<=0
                          OR standard.kv IS NULL OR standard.kv<=0
                    THEN 'incomplete' ELSE 'ready' END AS quality_status
          FROM standardpressregulators standard
        UNION ALL
        SELECT 'flow'::text AS catalog_type, standard.id,
               standard.name_rr AS display_name, standard.tyip_rr AS series,
               standard.typ_valve AS model, standard.producer,
               standard.d AS nominal_diameter, standard.kv AS capacity,
               NULL::varchar AS medium, NULL::double precision AS max_temperature,
               standard.dp_min AS pressure_min, standard.dp_max AS pressure_max,
               standard.typ_drive AS drive_type, NULL::varchar AS installation_place,
               CASE WHEN standard.name_rr IS NULL OR standard.tyip_rr IS NULL
                          OR standard.d IS NULL OR standard.d<=0
                          OR standard.kv IS NULL OR standard.kv<=0
                    THEN 'incomplete' ELSE 'ready' END AS quality_status
          FROM standardconsregulators standard
        UNION ALL
        SELECT 'differential'::text AS catalog_type, standard.id,
               standard.tip AS display_name, NULL::varchar AS series,
               standard.tip AS model, standard.proizvod AS producer,
               standard.du AS nominal_diameter, standard.kv AS capacity,
               standard.sreda AS medium, standard.tmax_sreda AS max_temperature,
               standard.pmin_zad AS pressure_min, standard.pmax_zad AS pressure_max,
               NULL::varchar AS drive_type, standard.pr_ustanovki AS installation_place,
               CASE WHEN standard.tip IS NULL OR standard.du IS NULL OR standard.du<=0
                          OR standard.kv IS NULL OR standard.kv<=0
                    THEN 'incomplete' ELSE 'ready' END AS quality_status
          FROM standardpressdropregulators standard
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_network_regulator_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch("SELECT id, name, code FROM regulatorstates ORDER BY ord, id")
    work_attributes = await conn.fetch(
        "SELECT id, name, code FROM workattributes ORDER BY ord, id"
    )
    pipeline_signs = await conn.fetch(
        "SELECT id, name, code FROM pipelinesigns ORDER BY ord, id"
    )
    fragments = await conn.fetch(
        REGULATOR_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total,
               count(*) FILTER (WHERE regulator_type='pressure')::int AS pressure,
               count(*) FILTER (WHERE regulator_type='flow')::int AS flow,
               count(*) FILTER (WHERE regulator_type='differential')::int AS differential
          FROM classified_regulators
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name ORDER BY fragment_name, fragment_id
        """
    )
    counts = await conn.fetchrow(
        REGULATOR_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE regulator_type='pressure')::int AS pressure,
               count(*) FILTER (WHERE regulator_type='flow')::int AS flow,
               count(*) FILTER (WHERE regulator_type='differential')::int AS differential,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE quality_status='line_removed')::int AS line_removed,
               count(*) FILTER (WHERE quality_status='control_node_missing')::int AS control_node_missing,
               count(*) FILTER (WHERE quality_status='setpoint_missing')::int AS setpoint_missing,
               count(*) FILTER (WHERE quality_status='capacity_missing')::int AS capacity_missing,
               count(*) FILTER (WHERE state_id=1)::int AS opened,
               count(*) FILTER (WHERE state_id=2)::int AS closed,
               count(*) FILTER (WHERE state_id=3)::int AS inactive,
               count(*) FILTER (WHERE longitude IS NOT NULL AND latitude IS NOT NULL)::int AS locatable,
               count(*) FILTER (WHERE longitude IS NULL OR latitude IS NULL)::int AS geometry_missing
          FROM classified_regulators
        """
    )
    catalog_counts = await conn.fetchrow(
        CATALOG_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE catalog_type='pressure')::int AS pressure,
               count(*) FILTER (WHERE catalog_type='flow')::int AS flow,
               count(*) FILTER (WHERE catalog_type='differential')::int AS differential,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='incomplete')::int AS incomplete
          FROM regulator_catalog
        """
    )
    return {
        "states": [dict(row) for row in states],
        "work_attributes": [dict(row) for row in work_attributes],
        "pipeline_signs": [dict(row) for row in pipeline_signs],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "catalog_counts": dict(catalog_counts) if catalog_counts else {},
        "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
        "result_count": await conn.fetchval("SELECT count(*) FROM rs_out"),
    }


async def get_network_regulators(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    regulator_type: Optional[RegulatorType] = None,
    quality_status: Optional[RegulatorQualityStatus] = None,
    state_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    work_attribute_id: Optional[int] = None,
    line_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if regulator_type:
        _add_filter(clauses, values, "item.regulator_type={param}", regulator_type, "::text")
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    if state_id is not None:
        _add_filter(clauses, values, "item.state_id={param}", state_id)
    if fragment_id is not None:
        _add_filter(clauses, values, "item.fragment_id={param}", fragment_id)
    if work_attribute_id is not None:
        _add_filter(clauses, values, "item.work_attribute_id={param}", work_attribute_id)
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
                 OR coalesce(item.control_node_code, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.control_node_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.fragment_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        REGULATOR_CTE + " SELECT count(*) FROM classified_regulators item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        REGULATOR_CTE
        + " SELECT * FROM classified_regulators item"
        + where_sql
        + f"""
          ORDER BY CASE item.quality_status
                     WHEN 'line_missing' THEN 1 WHEN 'line_removed' THEN 2
                     WHEN 'control_node_missing' THEN 3 WHEN 'setpoint_missing' THEN 4
                     WHEN 'capacity_missing' THEN 5 ELSE 6 END,
                   item.fragment_name NULLS LAST, item.regulator_type, item.id
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


async def get_network_regulator(
    conn: asyncpg.Connection, regulator_type: RegulatorType, regulator_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        REGULATOR_CTE
        + """ SELECT * FROM classified_regulators item
               WHERE item.regulator_type=$1 AND item.id=$2""",
        regulator_type,
        regulator_id,
    )
    if summary is None:
        return None
    table_name = REGULATOR_TABLES[regulator_type]
    attributes = await conn.fetchrow(f"SELECT * FROM {table_name} WHERE id=$1", regulator_id)
    latest_output = await conn.fetchrow(
        """
        SELECT output.id, output.calculationid AS calculation_id,
               calculation.name AS calculation_name, calculation.date1 AS calculated_at,
               output.sos AS state_text, output.a4 AS geodetic_mark_in,
               output.a8 AS geodetic_mark_out,
               output.kod3 AS control_node_code, output.uzel3 AS control_node_name,
               output.pr3 AS control_pipeline_sign,
               output.a11 AS flow, output.a12 AS hydraulic_resistance,
               output.a13 AS piezometric_head_in, output.a14 AS piezometric_head_out,
               output.a15 AS regulator_kind, output.a16 AS target_value,
               output.a17 AS actual_value, output.a18 AS tolerance,
               output.dx AS difference, output.a19 AS valve_position,
               output.ist AS heat_source_id, source.sourcename AS heat_source_name
          FROM rs_out output
          LEFT JOIN calculation ON calculation.id=output.calculationid
          LEFT JOIN heatsources source ON source.id=output.ist
         WHERE output.lineid=$1
         ORDER BY calculation.date1 DESC NULLS LAST,
                  output.calculationid DESC, output.id DESC LIMIT 1
        """,
        summary["line_id"],
    )
    related = await conn.fetch(
        REGULATOR_CTE
        + """
        SELECT regulator_type, id, display_name, state_id, state_name, quality_status
          FROM classified_regulators item
         WHERE item.line_id=$1 AND NOT (item.regulator_type=$2 AND item.id=$3)
         ORDER BY item.regulator_type, item.id LIMIT 50
        """,
        summary["line_id"],
        regulator_type,
        regulator_id,
    )
    result = dict(summary)
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "latest_output": dict(latest_output) if latest_output else None,
            "related_regulators": [dict(row) for row in related],
        }
    )
    return result


async def get_regulator_catalog(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    catalog_type: Optional[RegulatorType] = None,
    quality_status: Optional[Literal["ready", "incomplete"]] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if catalog_type:
        _add_filter(clauses, values, "item.catalog_type={param}", catalog_type, "::text")
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(item.id::text={param}
                 OR coalesce(item.display_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.series, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.model, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.producer, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        CATALOG_CTE + " SELECT count(*) FROM regulator_catalog item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        CATALOG_CTE
        + " SELECT * FROM regulator_catalog item"
        + where_sql
        + f" ORDER BY item.catalog_type, item.display_name, item.nominal_diameter, item.id LIMIT ${len(values)+1} OFFSET ${len(values)+2}",
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


async def get_regulator_catalog_item(
    conn: asyncpg.Connection, catalog_type: RegulatorType, catalog_id: int
) -> Optional[dict[str, Any]]:
    table_name = CATALOG_TABLES[catalog_type]
    row = await conn.fetchrow(f"SELECT * FROM {table_name} WHERE id=$1", catalog_id)
    if row is None:
        return None
    summary = await conn.fetchrow(
        CATALOG_CTE
        + " SELECT * FROM regulator_catalog item WHERE item.catalog_type=$1 AND item.id=$2",
        catalog_type,
        catalog_id,
    )
    result = dict(summary) if summary else {"catalog_type": catalog_type, "id": catalog_id}
    result["attributes"] = dict(row)
    result["installed_count"] = None
    result["link_note"] = (
        "В таблицах установленных регуляторов отсутствует ссылка на типовую модель каталога."
    )
    return result
