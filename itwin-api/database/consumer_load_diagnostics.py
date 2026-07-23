from typing import Any, Literal, Optional

import asyncpg


ConsumerType = Literal["generalized", "real"]
DiagnosticType = Literal["zero_load", "closed", "disconnected", "not_calculated"]


CONSUMER_DIAGNOSTICS_CTE = """
    WITH latest_calculation AS (
        SELECT DISTINCT ON (calculation.fileid)
               calculation.fileid, calculation.id, calculation.date1, calculation.name
          FROM calculation
         ORDER BY calculation.fileid, calculation.id DESC
    ), consumer_objects AS (
        SELECT 'generalized'::text AS consumer_type, consumer.id, consumer.nodeid AS node_id,
               consumer.name::text AS name, consumer.consumerstateid AS state_id,
               (coalesce(consumer.calchldep, 0) + coalesce(consumer.calchlindep, 0)
                + coalesce(consumer.calchlparall, 0) + coalesce(consumer.calchlmix, 0)
                + coalesce(consumer.calchlconseq, 0) + coalesce(consumer.calchlpreon, 0))::double precision AS heating_load,
               coalesce(consumer.calchlventil, 0)::double precision AS ventilation_load,
               coalesce(consumer.calchlcond, 0)::double precision AS conditioning_load,
               (coalesce(consumer.calchlclosesys, 0) + coalesce(consumer.calchlopensysflow, 0)
                + coalesce(consumer.calchlopensysret, 0) + coalesce(consumer.calchlgvsparall, 0)
                + coalesce(consumer.calchlgvsmix, 0) + coalesce(consumer.calchlgvsconseq, 0)
                + coalesce(consumer.calchlgvspreon, 0))::double precision AS hot_water_load
          FROM generalizedconsumers consumer
        UNION ALL
        SELECT 'real', consumer.id, consumer.nodeid, consumer.name::text,
               consumer.consumerstateid,
               (coalesce(consumer.calchldep, 0) + coalesce(consumer.calchlindep, 0))::double precision,
               coalesce(consumer.calchlventil, 0)::double precision,
               coalesce(consumer.avghlcond, 0)::double precision,
               (coalesce(consumer.avghlclosesys, 0) + coalesce(consumer.avghlopensysflow, 0)
                + coalesce(consumer.avghlopensysret, 0))::double precision
          FROM realconsumers consumer
    ), consumer_diagnostics AS (
        SELECT consumer.*, state.name AS state_name,
               node.fileid AS fragment_id, fragment.name AS fragment_name,
               external_code.name AS external_code, node.externalnodename AS external_node_name,
               latest.id AS latest_calculation_id, latest.date1 AS latest_calculation_date,
               latest.name AS latest_calculation_name,
               (latest.id IS NOT NULL) AS calculation_available,
               CASE WHEN latest.id IS NULL THEN false ELSE EXISTS(
                   SELECT 1 FROM pt_out output
                    WHERE output.nodeid=consumer.node_id AND output.calculationid=latest.id
               ) END AS has_calculation_output,
               (consumer.heating_load=0) AS zero_heating_load,
               (consumer.state_id=2) AS closed,
               (consumer.heating_load + consumer.ventilation_load
                + consumer.conditioning_load + consumer.hot_water_load)::double precision AS total_load,
               CASE WHEN node.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS longitude,
               CASE WHEN node.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS latitude
          FROM consumer_objects consumer
          JOIN nodes node ON node.id=consumer.node_id AND coalesce(node.removed, 0)=0
          LEFT JOIN fragments fragment ON fragment.id=node.fileid
          LEFT JOIN externalcodes external_code ON external_code.id=node.externalcodeid
          LEFT JOIN consumerstates state ON state.id=consumer.state_id
          LEFT JOIN latest_calculation latest ON latest.fileid=node.fileid
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    diagnostic: Optional[DiagnosticType],
    consumer_type: Optional[ConsumerType],
    fragment_id: Optional[int],
    state_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if diagnostic == "zero_load":
        clauses.append("consumer.zero_heating_load")
    elif diagnostic == "closed":
        clauses.append("consumer.closed")
    elif diagnostic == "disconnected":
        clauses.append("consumer.calculation_available AND NOT consumer.has_calculation_output")
    elif diagnostic == "not_calculated":
        clauses.append("NOT consumer.calculation_available")
    if consumer_type:
        _add_filter(
            clauses, values, "consumer.consumer_type={param}", consumer_type, "::text"
        )
    if fragment_id is not None:
        _add_filter(clauses, values, "consumer.fragment_id={param}", fragment_id)
    if state_id is not None:
        _add_filter(clauses, values, "consumer.state_id={param}", state_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                consumer.id::text={param} OR consumer.node_id::text={param}
                OR coalesce(consumer.name, '') ILIKE '%' || {param} || '%'
                OR coalesce(consumer.external_code, '') ILIKE '%' || {param} || '%'
                OR coalesce(consumer.external_node_name, '') ILIKE '%' || {param} || '%'
                OR coalesce(consumer.fragment_name, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_consumer_load_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch(
        "SELECT id, name, code FROM consumerstates ORDER BY ord, id"
    )
    fragments = await conn.fetch(
        CONSUMER_DIAGNOSTICS_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name,
               count(*)::int AS total,
               count(*) FILTER (WHERE consumer_type='generalized')::int AS generalized,
               count(*) FILTER (WHERE consumer_type='real')::int AS real,
               count(*) FILTER (WHERE zero_heating_load)::int AS zero_load,
               count(*) FILTER (WHERE closed)::int AS closed,
               count(*) FILTER (
                   WHERE calculation_available AND NOT has_calculation_output
               )::int AS disconnected,
               count(*) FILTER (WHERE NOT calculation_available)::int AS not_calculated,
               sum(heating_load)::double precision AS heating_load,
               sum(ventilation_load)::double precision AS ventilation_load,
               sum(hot_water_load)::double precision AS hot_water_load,
               sum(total_load)::double precision AS total_load
          FROM consumer_diagnostics
         GROUP BY fragment_id, fragment_name
         ORDER BY fragment_name NULLS LAST, fragment_id
        """
    )
    counts = await conn.fetchrow(
        CONSUMER_DIAGNOSTICS_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE consumer_type='generalized')::int AS generalized,
               count(*) FILTER (WHERE consumer_type='real')::int AS real,
               count(*) FILTER (WHERE zero_heating_load)::int AS zero_load,
               count(*) FILTER (WHERE closed)::int AS closed,
               count(*) FILTER (
                   WHERE calculation_available AND NOT has_calculation_output
               )::int AS disconnected,
               count(*) FILTER (WHERE NOT calculation_available)::int AS not_calculated,
               count(DISTINCT fragment_id) FILTER (WHERE calculation_available)::int
                   AS calculated_fragments,
               count(DISTINCT fragment_id) FILTER (WHERE NOT calculation_available)::int
                   AS uncalculated_fragments,
               sum(heating_load)::double precision AS heating_load,
               sum(ventilation_load)::double precision AS ventilation_load,
               sum(hot_water_load)::double precision AS hot_water_load,
               sum(total_load)::double precision AS total_load
          FROM consumer_diagnostics
        """
    )
    return {
        "states": [dict(row) for row in states],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "calculation_warning": (
            "В БД нет сохранённых расчётов; отсутствие PT_OUT нельзя считать отключением."
            if not counts or not counts["calculated_fragments"]
            else None
        ),
    }


async def get_consumer_load_diagnostics(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    diagnostic: Optional[DiagnosticType] = None,
    consumer_type: Optional[ConsumerType] = None,
    fragment_id: Optional[int] = None,
    state_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        diagnostic=diagnostic,
        consumer_type=consumer_type,
        fragment_id=fragment_id,
        state_id=state_id,
        search=search,
    )
    total = await conn.fetchval(
        CONSUMER_DIAGNOSTICS_CTE
        + " SELECT count(*) FROM consumer_diagnostics consumer"
        + where_sql,
        *values,
    )
    rows = await conn.fetch(
        CONSUMER_DIAGNOSTICS_CTE
        + " SELECT * FROM consumer_diagnostics consumer"
        + where_sql
        + f"""
          ORDER BY consumer.zero_heating_load DESC, consumer.closed DESC,
                   consumer.fragment_name NULLS LAST, consumer.name NULLS LAST,
                   consumer.consumer_type, consumer.id
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


async def get_consumer_load_diagnostic(
    conn: asyncpg.Connection, consumer_type: ConsumerType, consumer_id: int
) -> Optional[dict[str, Any]]:
    consumer = await conn.fetchrow(
        CONSUMER_DIAGNOSTICS_CTE
        + """
        SELECT * FROM consumer_diagnostics consumer
         WHERE consumer.consumer_type=$1 AND consumer.id=$2
        """,
        consumer_type,
        consumer_id,
    )
    if consumer is None:
        return None
    result = dict(consumer)
    table = (
        "generalizedconsumers"
        if consumer_type == "generalized"
        else "realconsumers"
    )
    attributes = await conn.fetchrow(f"SELECT * FROM {table} WHERE id=$1", consumer_id)
    output = None
    if result["latest_calculation_id"] is not None:
        output = await conn.fetchrow(
            """
            SELECT id, nodeid AS node_id, calculationid AS calculation_id,
                   qotz, qotn, dop12 AS ventilation,
                   dop17 AS hot_water_closed, dop18 AS hot_water_open_flow,
                   dop19 AS hot_water_open_return, dop20 AS recirculation,
                   qsum_z AS delivered_total, qtreb AS required_total,
                   qfact AS actual_total, q_obesp_min AS supply_ratio_min
              FROM pt_out
             WHERE nodeid=$1 AND calculationid=$2
             ORDER BY id DESC LIMIT 1
            """,
            result["node_id"],
            result["latest_calculation_id"],
        )
    related = await conn.fetch(
        CONSUMER_DIAGNOSTICS_CTE
        + """
        SELECT consumer_type, id, name, state_id, state_name,
               heating_load, ventilation_load, hot_water_load, total_load,
               zero_heating_load, closed
          FROM consumer_diagnostics consumer
         WHERE consumer.node_id=$1
           AND NOT (consumer.consumer_type=$2 AND consumer.id=$3)
         ORDER BY consumer.consumer_type, consumer.name, consumer.id
        """,
        result["node_id"],
        consumer_type,
        consumer_id,
    )
    result["attributes"] = dict(attributes) if attributes else {}
    result["latest_output"] = dict(output) if output else None
    result["related_consumers"] = [dict(row) for row in related]
    return result
