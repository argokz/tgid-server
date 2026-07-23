from typing import Any, Optional

import asyncpg


SOURCE_STATUS_CTE = """
    WITH source_status AS (
        SELECT hs.id, hs.nodeid AS node_id,
               coalesce(nullif(hs.name, ''), nullif(hs.sourcename, ''),
                        nullif(n.externalnodename, ''), 'Источник №' || hs.id::text) AS name,
               n.fileid AS fragment_id, fr.name AS fragment_name,
               EXISTS(SELECT 1 FROM heatlosessource hls WHERE hls.heatsourceid=hs.id) AS has_source_parameters,
               EXISTS(SELECT 1 FROM heatlosessourcemonths hlsm WHERE hlsm.heatsourceid=hs.id) AS has_month_parameters,
               EXISTS(SELECT 1 FROM losesbyfilling lbf WHERE lbf.heatsourceid=hs.id) AS has_filling_parameters,
               EXISTS(SELECT 1 FROM heatpipesectionsharness harness WHERE harness.heatsourceid=hs.id) AS has_harness,
               CASE WHEN n.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(n.shape), 4326)) END AS longitude,
               CASE WHEN n.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(n.shape), 4326)) END AS latitude
          FROM heatsources hs
          JOIN nodes n ON n.id=hs.nodeid AND coalesce(n.removed, 0)=0
          LEFT JOIN fragments fr ON fr.id=n.fileid
    ), prepared_sources AS (
        SELECT source_status.*,
               (has_source_parameters AND has_month_parameters
                AND (has_filling_parameters OR has_harness)) AS ready_to_calculate
          FROM source_status
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_heat_loss_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    fragments = await conn.fetch(
        SOURCE_STATUS_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS source_count,
               count(*) FILTER (WHERE ready_to_calculate)::int AS ready_count
          FROM prepared_sources
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name
         ORDER BY fragment_name NULLS LAST, fragment_id
        """
    )
    source_counts = await conn.fetchrow(
        SOURCE_STATUS_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE ready_to_calculate)::int AS ready,
               count(*) FILTER (WHERE NOT ready_to_calculate)::int AS incomplete
          FROM prepared_sources
        """
    )
    season_counts = await conn.fetchrow(
        """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE d1 <= CURRENT_DATE AND d2 >= CURRENT_DATE)::int AS current,
               count(DISTINCT city)::int AS cities
          FROM heatlosesmain
        """
    )
    cities = await conn.fetch(
        "SELECT DISTINCT city AS name FROM heatlosesmain WHERE city IS NOT NULL ORDER BY city"
    )
    return {
        "fragments": [dict(row) for row in fragments],
        "cities": [dict(row) for row in cities],
        "source_counts": dict(source_counts) if source_counts else {},
        "season_counts": dict(season_counts) if season_counts else {},
        "result_availability": {
            "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
            "heat_loss_row_count": await conn.fetchval("SELECT count(*) FROM ut_out WHERE tpot IS NOT NULL"),
        },
    }


async def get_heat_loss_seasons(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    city: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if city:
        _add_filter(clauses, values, "season.city={param}", city, "::text")
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(season.id::text={param} OR coalesce(season.name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(season.city, '') ILIKE '%' || {param} || '%'
                 OR to_char(season.d1, 'DD.MM.YYYY') ILIKE '%' || {param} || '%'
                 OR to_char(season.d2, 'DD.MM.YYYY') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        "SELECT count(*) FROM heatlosesmain season" + where_sql, *values
    )
    rows = await conn.fetch(
        """
        SELECT season.id, season.name, season.city, season.d1, season.d2,
               season.t_ot, season.t_vent, season.y, season.a, season.tankbattery_q,
               season.usetabledata, season.volwaterhs, season.volwatervs,
               season.volwateropengvs, season.netwaterfillingnormms,
               season.netwaterfillingnormrs, season.netwaterfillingnormhs,
               season.netwaterfillingnormtb, season.netwaterfillingnormha,
               (season.d1 <= CURRENT_DATE AND season.d2 >= CURRENT_DATE) AS is_current
          FROM heatlosesmain season
        """
        + where_sql
        + f"""
         ORDER BY season.d1 DESC NULLS LAST, season.id DESC
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


async def get_heat_loss_season(
    conn: asyncpg.Connection, season_id: int
) -> Optional[dict[str, Any]]:
    season = await conn.fetchrow(
        """
        SELECT season.*,
               (season.d1 <= CURRENT_DATE AND season.d2 >= CURRENT_DATE) AS is_current
          FROM heatlosesmain season WHERE season.id=$1
        """,
        season_id,
    )
    if season is None:
        return None
    season_data = dict(season)
    climate = await conn.fetch(
        """
        WITH ranked_climate AS (
            SELECT hl.id, hl.heatlosesmainid AS season_id, hl.cityid AS city_id,
                   city.name AS city, hl.r, hl.m, month.name AS month,
                   hl.tn, hl.tpod, hl.tgr,
                   row_number() OVER (
                       PARTITION BY hl.m
                       ORDER BY (hl.heatlosesmainid=$1) DESC, hl.id DESC
                   ) AS priority
              FROM heatloses hl
              LEFT JOIN cities city ON city.id=hl.cityid
              LEFT JOIN months month ON month.id=hl.m
             WHERE hl.heatlosesmainid=$1
                OR (hl.heatlosesmainid IS NULL AND lower(city.name)=lower($2))
        )
        SELECT id, season_id, city_id, city, r, m, month, tn, tpod, tgr
          FROM ranked_climate WHERE priority=1 ORDER BY r, m
        """,
        season_id,
        season_data.get("city") or "",
    )
    season_data["climate"] = [dict(row) for row in climate]
    return season_data


async def get_heat_loss_sources(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    fragment_id: Optional[int] = None,
    readiness: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if fragment_id is not None:
        _add_filter(clauses, values, "source.fragment_id={param}", fragment_id)
    if readiness == "ready":
        clauses.append("source.ready_to_calculate")
    elif readiness == "incomplete":
        clauses.append("NOT source.ready_to_calculate")
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(source.id::text={param} OR source.node_id::text={param}
                 OR coalesce(source.name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(source.fragment_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        SOURCE_STATUS_CTE + " SELECT count(*) FROM prepared_sources source" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        SOURCE_STATUS_CTE
        + " SELECT * FROM prepared_sources source"
        + where_sql
        + f"""
          ORDER BY source.fragment_name NULLS LAST, source.name, source.id
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


async def get_heat_loss_source(
    conn: asyncpg.Connection, source_id: int
) -> Optional[dict[str, Any]]:
    source = await conn.fetchrow(
        SOURCE_STATUS_CTE
        + " SELECT * FROM prepared_sources source WHERE source.id=$1",
        source_id,
    )
    if source is None:
        return None
    result = dict(source)
    attributes = await conn.fetchrow(
        "SELECT * FROM heatsources WHERE id=$1", source_id
    )
    source_parameters = await conn.fetchrow(
        "SELECT * FROM heatlosessource WHERE heatsourceid=$1 ORDER BY id DESC LIMIT 1",
        source_id,
    )
    months = await conn.fetch(
        """
        SELECT source_month.id, source_month.heatsourceid AS heat_source_id,
               source_month.r, source_month.m, month.name AS month,
               source_month.sezon, source_month.tn, source_month.tpod,
               source_month.tgr, source_month.tx, source_month.tgp,
               source_month.tgo, source_month.workcount,
               source_month.netwaterexpflow, source_month.netwaterexpret,
               source_month.regcountflow, source_month.regcountret,
               source_month.workcountflow, source_month.workcountret
          FROM heatlosessourcemonths source_month
          LEFT JOIN months month ON month.id=source_month.m
         WHERE source_month.heatsourceid=$1
         ORDER BY source_month.r, source_month.m, source_month.id
        """,
        source_id,
    )
    filling = await conn.fetch(
        """
        SELECT filling.*, month.name AS month_name
          FROM losesbyfilling filling
          LEFT JOIN months month ON month.id=filling.monthid
         WHERE filling.heatsourceid=$1 ORDER BY filling.monthid, filling.id
        """,
        source_id,
    )
    harness = await conn.fetch(
        "SELECT * FROM heatpipesectionsharness WHERE heatsourceid=$1 ORDER BY id",
        source_id,
    )
    attributes_data = dict(attributes) if attributes else {}
    attributes_data.pop("shape", None)
    result.update(
        {
            "attributes": attributes_data,
            "source_parameters": dict(source_parameters) if source_parameters else None,
            "months": [dict(row) for row in months],
            "filling": [dict(row) for row in filling],
            "harness": [dict(row) for row in harness],
        }
    )
    return result
