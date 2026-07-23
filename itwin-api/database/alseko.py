from typing import Any, Literal, Optional

import asyncpg


BUILDING_KEYS_CTE = """
    WITH building_keys AS MATERIALIZED (
        SELECT
            z.mkr2,
            z.street2,
            lower(replace(z.house2, ' ', '')) AS house_key,
            count(*)::int AS building_match_count,
            count(*) FILTER (WHERE z.potrebitel IS NOT NULL)::int AS assigned_building_count,
            min(z.id) AS building_id
        FROM zdaniya_2 z
        WHERE z.house2 IS NOT NULL
        GROUP BY z.mkr2, z.street2, lower(replace(z.house2, ' ', ''))
    )
"""


LOAD_SUMMARY_SELECT = BUILDING_KEYS_CTE + """
    SELECT
        n.id,
        n.city,
        n.mkr AS microdistrict,
        n.street,
        n.house,
        n.addr AS source_address,
        n.name AS customer_type,
        n.owner,
        n.dogovor AS contract_number,
        n.numb AS registry_number,
        n.adm_rayon AS administrative_district,
        n.rayon AS operation_district,
        n.uchastok AS operation_site,
        n.ist AS heat_source,
        n.tg AS temperature_graph,
        n.otop AS heating_load,
        n.gvs AS hot_water_load,
        n.vent AS ventilation_load,
        n.par AS steam_load,
        coalesce(n.otop, 0) + coalesce(n.gvs, 0)
            + coalesce(n.vent, 0) + coalesce(n.par, 0) AS total_load,
        coalesce(keys.building_match_count, 0) AS building_match_count,
        coalesce(keys.assigned_building_count, 0) AS assigned_building_count,
        keys.building_id,
        building.potrebitel AS building_consumer,
        CASE WHEN building.shape IS NULL THEN NULL
             ELSE ST_X(ST_Transform(ST_PointOnSurface(building.shape), 4326)) END AS longitude,
        CASE WHEN building.shape IS NULL THEN NULL
             ELSE ST_Y(ST_Transform(ST_PointOnSurface(building.shape), 4326)) END AS latitude
    FROM nagruzki n
    LEFT JOIN building_keys keys
      ON n.mkr IS NOT DISTINCT FROM keys.mkr2
     AND n.street IS NOT DISTINCT FROM keys.street2
     AND lower(replace(n.house, ' ', ''))=keys.house_key
    LEFT JOIN zdaniya_2 building ON building.id=keys.building_id
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_load_filters(
    *,
    match_status: Optional[Literal["matched", "unmatched"]],
    customer_group: Optional[Literal["apartment", "other"]],
    operation_district: Optional[str],
    administrative_district: Optional[str],
    heat_source: Optional[str],
    temperature_graph: Optional[str],
    building_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if match_status == "matched":
        clauses.append("keys.building_id IS NOT NULL")
    elif match_status == "unmatched":
        clauses.append("keys.building_id IS NULL")
    if customer_group == "apartment":
        _add_filter(clauses, values, "n.name={param}", "МЖД", "::text")
    elif customer_group == "other":
        _add_filter(
            clauses,
            values,
            "n.name IS DISTINCT FROM {param}",
            "МЖД",
            "::text",
        )
    for value, expression in (
        (operation_district, "n.rayon={param}"),
        (administrative_district, "n.adm_rayon={param}"),
        (heat_source, "n.ist={param}"),
        (temperature_graph, "n.tg={param}"),
    ):
        if value:
            _add_filter(clauses, values, expression, value, "::text")
    if building_id is not None:
        _add_filter(clauses, values, "keys.building_id={param}", building_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                n.id::text={param}
                OR coalesce(n.addr, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.mkr, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.street, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.house, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.name, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.owner, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.dogovor, '') ILIKE '%' || {param} || '%'
                OR coalesce(n.numb, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_alseko_loads(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    match_status: Optional[Literal["matched", "unmatched"]] = None,
    customer_group: Optional[Literal["apartment", "other"]] = None,
    operation_district: Optional[str] = None,
    administrative_district: Optional[str] = None,
    heat_source: Optional[str] = None,
    temperature_graph: Optional[str] = None,
    building_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_load_filters(
        match_status=match_status,
        customer_group=customer_group,
        operation_district=operation_district,
        administrative_district=administrative_district,
        heat_source=heat_source,
        temperature_graph=temperature_graph,
        building_id=building_id,
        search=search,
    )
    base_from = BUILDING_KEYS_CTE + """
        SELECT count(*)
        FROM nagruzki n
        LEFT JOIN building_keys keys
          ON n.mkr IS NOT DISTINCT FROM keys.mkr2
         AND n.street IS NOT DISTINCT FROM keys.street2
         AND lower(replace(n.house, ' ', ''))=keys.house_key
    """
    total = await conn.fetchval(base_from + where_sql, *values)
    rows = await conn.fetch(
        LOAD_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY n.mkr NULLS FIRST, n.street NULLS FIRST, n.house NULLS FIRST,
                     n.numb NULLS LAST, n.id
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


async def get_alseko_load_lookups(
    conn: asyncpg.Connection,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for key, column in (
        ("operation_districts", "rayon"),
        ("administrative_districts", "adm_rayon"),
        ("heat_sources", "ist"),
        ("temperature_graphs", "tg"),
    ):
        rows = await conn.fetch(
            f"""SELECT {column} AS name, count(*)::int AS count
                  FROM nagruzki
                 WHERE nullif(btrim({column}), '') IS NOT NULL
                 GROUP BY {column} ORDER BY {column}"""
        )
        result[key] = [dict(row) for row in rows]
    counts = await conn.fetchrow(
        BUILDING_KEYS_CTE
        + """
        SELECT
            count(*)::int AS total,
            count(*) FILTER (WHERE keys.building_id IS NOT NULL)::int AS matched,
            count(*) FILTER (WHERE keys.building_id IS NULL)::int AS unmatched,
            count(*) FILTER (WHERE n.name='МЖД')::int AS apartment,
            count(*) FILTER (WHERE n.name IS DISTINCT FROM 'МЖД')::int AS other
        FROM nagruzki n
        LEFT JOIN building_keys keys
          ON n.mkr IS NOT DISTINCT FROM keys.mkr2
         AND n.street IS NOT DISTINCT FROM keys.street2
         AND lower(replace(n.house, ' ', ''))=keys.house_key
        """
    )
    result["counts"] = [dict(counts)] if counts else []
    return result


async def get_alseko_load(
    conn: asyncpg.Connection, load_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        LOAD_SUMMARY_SELECT + " WHERE n.id=$1", load_id
    )
    if summary is None:
        return None
    result = dict(summary)
    buildings = await conn.fetch(
        """
        SELECT
            z.id,
            z.mkr2 AS microdistrict,
            z.street2 AS street,
            z.house2 AS house,
            z.id_adr_mas AS address_massif,
            z.street_nam AS source_street,
            z.number_1 AS source_house,
            z.floor,
            z.year_of_fo AS construction_year,
            z.otop AS heating_load,
            z.gvs AS hot_water_load,
            z.vent AS ventilation_load,
            z.par AS steam_load,
            z.nagr AS total_load,
            z.otop_cxema AS heating_scheme_id,
            z.gvs_cxema AS hot_water_scheme_id,
            z.potrebitel AS consumer,
            CASE WHEN z.shape IS NULL THEN NULL
                 ELSE ST_X(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS longitude,
            CASE WHEN z.shape IS NULL THEN NULL
                 ELSE ST_Y(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS latitude
        FROM zdaniya_2 z
        JOIN nagruzki n ON n.id=$1
        WHERE n.mkr IS NOT DISTINCT FROM z.mkr2
          AND n.street IS NOT DISTINCT FROM z.street2
          AND lower(replace(n.house, ' ', ''))=lower(replace(z.house2, ' ', ''))
        ORDER BY z.id
        """,
        load_id,
    )
    address_loads = await conn.fetch(
        """
        SELECT sibling.id, sibling.name AS customer_type,
               sibling.owner, sibling.dogovor AS contract_number,
               sibling.numb AS registry_number,
               sibling.otop AS heating_load, sibling.gvs AS hot_water_load,
               sibling.vent AS ventilation_load, sibling.par AS steam_load
        FROM nagruzki sibling
        JOIN nagruzki selected ON selected.id=$1
        WHERE sibling.mkr IS NOT DISTINCT FROM selected.mkr
          AND sibling.street IS NOT DISTINCT FROM selected.street
          AND lower(replace(sibling.house, ' ', ''))=lower(replace(selected.house, ' ', ''))
        ORDER BY sibling.numb NULLS LAST, sibling.id
        LIMIT 200
        """,
        load_id,
    )
    result["relations"] = {
        "matched_buildings": [dict(row) for row in buildings],
        "address_loads": [dict(row) for row in address_loads],
    }
    return result


async def get_unassigned_alseko_buildings(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses = ["z.potrebitel IS NULL", "z.otop IS NOT NULL"]
    values: list[Any] = []
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                z.id::text={param}
                OR coalesce(z.mkr2, '') ILIKE '%' || {param} || '%'
                OR coalesce(z.street2, '') ILIKE '%' || {param} || '%'
                OR coalesce(z.house2, '') ILIKE '%' || {param} || '%'
                OR coalesce(z.id_adr_mas, '') ILIKE '%' || {param} || '%'
                OR coalesce(z.street_nam, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses)
    total = await conn.fetchval(
        "SELECT count(*) FROM zdaniya_2 z" + where_sql, *values
    )
    rows = await conn.fetch(
        """
        SELECT z.id, z.mkr2 AS microdistrict, z.street2 AS street,
               z.house2 AS house, z.otop AS heating_load,
               z.gvs AS hot_water_load, z.vent AS ventilation_load,
               z.par AS steam_load, z.nagr AS total_load,
               z.otop_cxema AS heating_scheme_id,
               z.gvs_cxema AS hot_water_scheme_id,
               CASE WHEN z.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS longitude,
               CASE WHEN z.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS latitude
        FROM zdaniya_2 z
        """
        + where_sql
        + f"""
          ORDER BY z.mkr2 NULLS FIRST, z.street2 NULLS FIRST, z.house2 NULLS FIRST, z.id
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


async def get_alseko_building(
    conn: asyncpg.Connection, building_id: int
) -> Optional[dict[str, Any]]:
    building = await conn.fetchrow(
        """
        SELECT z.id, z.mkr2 AS microdistrict, z.street2 AS street,
               z.house2 AS house, z.id_adr_mas AS address_massif,
               z.street_nam AS source_street, z.number_1 AS source_house,
               z.floor, z.year_of_fo AS construction_year,
               z.otop AS heating_load, z.gvs AS hot_water_load,
               z.vent AS ventilation_load, z.par AS steam_load,
               z.nagr AS total_load, z.otop_cxema AS heating_scheme_id,
               z.gvs_cxema AS hot_water_scheme_id, z.potrebitel AS consumer,
               CASE WHEN z.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS longitude,
               CASE WHEN z.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(z.shape), 4326)) END AS latitude
        FROM zdaniya_2 z WHERE z.id=$1
        """,
        building_id,
    )
    if building is None:
        return None
    result = dict(building)
    loads = await conn.fetch(
        """
        SELECT n.id, n.name AS customer_type, n.owner,
               n.dogovor AS contract_number, n.numb AS registry_number,
               n.otop AS heating_load, n.gvs AS hot_water_load,
               n.vent AS ventilation_load, n.par AS steam_load
        FROM nagruzki n
        JOIN zdaniya_2 z ON z.id=$1
        WHERE n.mkr IS NOT DISTINCT FROM z.mkr2
          AND n.street IS NOT DISTINCT FROM z.street2
          AND lower(replace(n.house, ' ', ''))=lower(replace(z.house2, ' ', ''))
        ORDER BY n.numb NULLS LAST, n.id
        LIMIT 200
        """,
        building_id,
    )
    result["relations"] = {"matched_loads": [dict(row) for row in loads]}
    return result
