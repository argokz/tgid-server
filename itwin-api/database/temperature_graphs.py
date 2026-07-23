from typing import Any, Literal, Optional

import asyncpg


GraphStatus = Literal["ready", "missing", "duplicates", "incomplete"]
SummerStatus = Literal["ready", "missing"]


SOURCE_GRAPH_CTE = """
    WITH graph_stats AS (
        SELECT graph.hsourceid AS source_id,
               count(*)::int AS raw_point_count,
               count(DISTINCT graph.tn)::int AS point_count,
               (count(*) - count(DISTINCT graph.tn))::int AS duplicate_point_count,
               min(graph.tn)::double precision AS min_outdoor_temperature,
               max(graph.tn)::double precision AS max_outdoor_temperature,
               count(*) FILTER (
                   WHERE graph.tn IS NULL OR graph.t1 IS NULL OR graph.t2 IS NULL
                      OR graph.t3 IS NULL OR graph.tv IS NULL
               )::int AS incomplete_point_count,
               count(*) FILTER (WHERE graph.t1 < graph.t2)::int AS invalid_order_count
          FROM deployedtempgraphs graph
         GROUP BY graph.hsourceid
    ), source_graphs AS (
        SELECT source.id, source.nodeid AS node_id,
               coalesce(nullif(source.name, ''), nullif(source.sourcename, ''),
                        nullif(node.externalnodename, ''), 'Источник №' || source.id::text) AS name,
               source.sourcename, source.stateid AS state_id, state.name AS state_name,
               source.hsourcetypeid AS source_type_id, source_type.name AS source_type_name,
               source.graphtypeid AS graph_type_id, graph_type.name AS graph_type_name,
               graph_type.code AS graph_type_code,
               node.fileid AS fragment_id, fragment.name AS fragment_name,
               coalesce(stats.raw_point_count, 0)::int AS raw_point_count,
               coalesce(stats.point_count, 0)::int AS point_count,
               coalesce(stats.duplicate_point_count, 0)::int AS duplicate_point_count,
               coalesce(stats.incomplete_point_count, 0)::int AS incomplete_point_count,
               coalesce(stats.invalid_order_count, 0)::int AS invalid_order_count,
               stats.min_outdoor_temperature, stats.max_outdoor_temperature,
               CASE WHEN source.tn_5 IS NOT NULL AND source.tn_1 IS NOT NULL
                          AND source.tn_1 >= source.tn_5
                    THEN floor(source.tn_1 - source.tn_5)::int + 1 ELSE NULL
               END AS expected_point_count,
               source.tn_5 AS design_outdoor_temperature,
               source.tn_1 AS heating_end_temperature,
               source.t1_r AS design_flow_temperature,
               source.t2_r AS design_return_temperature,
               source.t3_r AS design_mixed_temperature,
               source.temperdwflowsummer AS summer_flow_temperature,
               source.temperdwretsummer AS summer_return_temperature,
               source.hsourcepower AS source_power,
               source.q_r AS heating_load, source.q_gv AS hot_water_load,
               (coalesce(source.temperdwflowsummer, 0) <> 0
                AND coalesce(source.temperdwretsummer, 0) <> 0) AS has_summer_temperatures,
               CASE WHEN stats.source_id IS NULL THEN 'missing'
                    WHEN stats.duplicate_point_count > 0 THEN 'duplicates'
                    WHEN stats.incomplete_point_count > 0 OR stats.invalid_order_count > 0
                         OR (source.tn_5 IS NOT NULL AND source.tn_1 IS NOT NULL
                             AND source.tn_1 >= source.tn_5
                             AND stats.point_count <> floor(source.tn_1 - source.tn_5)::int + 1)
                         THEN 'incomplete'
                    ELSE 'ready'
               END AS graph_status,
               CASE WHEN node.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS longitude,
               CASE WHEN node.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(node.shape), 4326)) END AS latitude
          FROM heatsources source
          JOIN nodes node ON node.id=source.nodeid AND coalesce(node.removed, 0)=0
          LEFT JOIN fragments fragment ON fragment.id=node.fileid
          LEFT JOIN states state ON state.id=source.stateid
          LEFT JOIN heatsourcetypes source_type ON source_type.id=source.hsourcetypeid
          LEFT JOIN graphtypes graph_type ON graph_type.id=source.graphtypeid
          LEFT JOIN graph_stats stats ON stats.source_id=source.id
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    graph_status: Optional[GraphStatus],
    summer_status: Optional[SummerStatus],
    graph_type_id: Optional[int],
    fragment_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if graph_status:
        _add_filter(clauses, values, "source.graph_status={param}", graph_status, "::text")
    if summer_status == "ready":
        clauses.append("source.has_summer_temperatures")
    elif summer_status == "missing":
        clauses.append("NOT source.has_summer_temperatures")
    if graph_type_id is not None:
        _add_filter(clauses, values, "source.graph_type_id={param}", graph_type_id)
    if fragment_id is not None:
        _add_filter(clauses, values, "source.fragment_id={param}", fragment_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(source.id::text={param} OR source.node_id::text={param}
                 OR coalesce(source.name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(source.fragment_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(source.graph_type_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_temperature_graph_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    graph_types = await conn.fetch("SELECT id, name, code FROM graphtypes ORDER BY ord, id")
    source_types = await conn.fetch("SELECT id, name, code FROM heatsourcetypes ORDER BY ord, id")
    fragments = await conn.fetch(
        SOURCE_GRAPH_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total,
               count(*) FILTER (WHERE graph_status='ready')::int AS ready,
               count(*) FILTER (WHERE graph_status='missing')::int AS missing,
               count(*) FILTER (WHERE graph_status='duplicates')::int AS duplicates,
               count(*) FILTER (WHERE graph_status='incomplete')::int AS incomplete
          FROM source_graphs
         GROUP BY fragment_id, fragment_name
         ORDER BY fragment_name NULLS LAST, fragment_id
        """
    )
    counts = await conn.fetchrow(
        SOURCE_GRAPH_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE graph_status='ready')::int AS ready,
               count(*) FILTER (WHERE graph_status='missing')::int AS missing,
               count(*) FILTER (WHERE graph_status='duplicates')::int AS duplicates,
               count(*) FILTER (WHERE graph_status='incomplete')::int AS incomplete,
               count(*) FILTER (WHERE has_summer_temperatures)::int AS summer_ready,
               count(*) FILTER (WHERE NOT has_summer_temperatures)::int AS summer_missing,
               sum(raw_point_count)::int AS raw_points,
               sum(point_count)::int AS distinct_points
          FROM source_graphs
        """
    )
    return {
        "graph_types": [dict(row) for row in graph_types],
        "source_types": [dict(row) for row in source_types],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "fact_point_count": await conn.fetchval("SELECT count(*) FROM deployedtempgraphsfact"),
    }


async def get_temperature_graph_sources(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    graph_status: Optional[GraphStatus] = None,
    summer_status: Optional[SummerStatus] = None,
    graph_type_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        graph_status=graph_status,
        summer_status=summer_status,
        graph_type_id=graph_type_id,
        fragment_id=fragment_id,
        search=search,
    )
    total = await conn.fetchval(
        SOURCE_GRAPH_CTE + " SELECT count(*) FROM source_graphs source" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        SOURCE_GRAPH_CTE
        + " SELECT * FROM source_graphs source"
        + where_sql
        + f"""
          ORDER BY CASE source.graph_status
                       WHEN 'duplicates' THEN 1 WHEN 'missing' THEN 2
                       WHEN 'incomplete' THEN 3 ELSE 4 END,
                   source.fragment_name NULLS LAST, source.name, source.id
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


async def get_temperature_graph_source(
    conn: asyncpg.Connection, source_id: int
) -> Optional[dict[str, Any]]:
    source = await conn.fetchrow(
        SOURCE_GRAPH_CTE + " SELECT * FROM source_graphs source WHERE source.id=$1",
        source_id,
    )
    if source is None:
        return None
    inputs = await conn.fetchrow(
        """
        SELECT id, sourcename, name, stateid AS state_id,
               hsourcetypeid AS source_type_id, hsourcepower AS source_power,
               hsourcepowerinst AS installed_power, hseasonbegindate AS season_begin,
               hseasonenddate AS season_end, hsourcecode AS source_code,
               powerset AS configured_power, poweravailable AS available_power,
               temperdwflowsummer AS summer_flow_temperature,
               temperdwretsummer AS summer_return_temperature,
               t1_summer, t2_summer, name_tg AS graph_name,
               heatloscalcyear AS calculation_year, graphtypeid AS graph_type_id,
               tn_5 AS design_outdoor_temperature,
               tn_1 AS heating_end_temperature,
               tvn_r AS design_indoor_temperature,
               t1_r AS design_flow_temperature,
               t2_r AS design_return_temperature,
               t3_r AS design_mixed_temperature,
               q_r AS heating_load, q_gv AS hot_water_load,
               t1_2r AS lower_flow_cut, t1_4r AS upper_flow_cut,
               t2_2r AS lower_return_cut,
               tvb_tr AS required_indoor_temperature,
               uf AS mixing_correction, tg_r AS hot_water_temperature,
               tx_r AS cold_water_temperature, t2_gv AS return_switch_temperature,
               pr AS hot_water_draw_mode, g1 AS flow_stability,
               g2 AS return_stability, t_gv1 AS first_stage_underheating,
               v AS wind_speed, date_on, name_exe AS executor,
               name_manager AS manager
          FROM heatsources WHERE id=$1
        """,
        source_id,
    )
    points = await conn.fetch(
        """
        WITH ranked AS (
            SELECT graph.id, graph.hsourceid AS source_id, graph.tn, graph.q_otn,
                   graph.t1, graph.t2, graph.t3, graph.tv, graph.t_bn, graph.tg,
                   count(*) OVER (PARTITION BY graph.tn)::int AS duplicate_count,
                   row_number() OVER (PARTITION BY graph.tn ORDER BY graph.id DESC) AS position
              FROM deployedtempgraphs graph WHERE graph.hsourceid=$1
        )
        SELECT id, source_id, tn, q_otn, t1, t2, t3, tv, t_bn, tg, duplicate_count
          FROM ranked WHERE position=1 ORDER BY tn
        """,
        source_id,
    )
    fact_points = await conn.fetch(
        """
        SELECT id, hsourceid AS source_id, tn, q_otn, t1, t2, t3, tv, t_bn, tg
          FROM deployedtempgraphsfact WHERE hsourceid=$1 ORDER BY tn, id
        """,
        source_id,
    )
    result = dict(source)
    result.update(
        {
            "inputs": dict(inputs) if inputs else {},
            "points": [dict(row) for row in points],
            "fact_points": [dict(row) for row in fact_points],
        }
    )
    return result
