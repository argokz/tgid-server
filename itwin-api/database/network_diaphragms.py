from typing import Any, Literal, Optional

import asyncpg


DiaphragmQualityStatus = Literal[
    "ready",
    "line_missing",
    "line_removed",
    "topology_missing",
    "state_missing",
    "count_invalid",
    "diameter_unresolved",
]
DiaphragmDiameterMode = Literal[
    "available",
    "pending_calculation",
    "unresolved",
]


DIAPHRAGM_CTE = """
    WITH diaphragm_inventory AS (
        SELECT diaphragm.id, diaphragm.lineid AS line_id,
               line.id AS linked_line_id,
               coalesce(nullif(btrim(diaphragm.throtdiaphloc), ''),
                        'Диафрагма №' || diaphragm.id) AS display_name,
               diaphragm.throtdiaphloc AS installation_place,
               diaphragm.diameterinternal AS internal_diameter,
               diaphragm.consinstdiaphcount AS installed_count,
               diaphragm.entrymark AS entry_mark,
               nullif(btrim(coalesce(diaphragm.entrymark, '')), '') IS NOT NULL
                   AS calculation_writeback_allowed,
               CASE WHEN diaphragm.diameterinternal>0 THEN 'available'
                    WHEN diaphragm.diameterinternal=0
                     AND nullif(btrim(coalesce(diaphragm.entrymark, '')), '') IS NOT NULL
                      THEN 'pending_calculation'
                    ELSE 'unresolved' END AS diameter_mode,
               diaphragm.stateid AS state_id, state.id AS linked_state_id,
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
               internal_node.id AS internal_node_id,
               internal_code.name AS internal_node_code,
               internal_node.externalnodename AS internal_node_name,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS longitude,
               CASE WHEN line.shape IS NULL THEN NULL
                    ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END AS latitude
          FROM diaphragms diaphragm
          LEFT JOIN linesobj line ON line.id=diaphragm.lineid
          LEFT JOIN states state ON state.id=diaphragm.stateid
          LEFT JOIN externalsignline external_sign ON external_sign.id=line.externalsignlineid
          LEFT JOIN fragments fragment ON fragment.id=line.fileid
          LEFT JOIN nodes node1 ON node1.id=line.nodeid1
          LEFT JOIN nodes node2 ON node2.id=line.nodeid2
          LEFT JOIN externalcodes code1 ON code1.id=node1.externalcodeid
          LEFT JOIN externalcodes code2 ON code2.id=node2.externalcodeid
          LEFT JOIN nodes internal_node ON internal_node.id=node1.internalnodeid
          LEFT JOIN externalcodes internal_code ON internal_code.id=internal_node.externalcodeid
          LEFT JOIN organizations organization ON organization.id=line.organizationid
          LEFT JOIN operators operator ON operator.id=line.operatorid
    ), classified_diaphragms AS (
        SELECT inventory.*,
               CASE WHEN inventory.linked_line_id IS NULL THEN 'line_missing'
                    WHEN coalesce(inventory.line_removed, 0)<>0 THEN 'line_removed'
                    WHEN inventory.linked_state_id IS NULL THEN 'state_missing'
                    WHEN inventory.installed_count IS NULL OR inventory.installed_count<=0
                      THEN 'count_invalid'
                    WHEN inventory.diameter_mode='unresolved' THEN 'diameter_unresolved'
                    WHEN inventory.linked_node_id_1 IS NULL OR inventory.linked_node_id_2 IS NULL
                      THEN 'topology_missing'
                    ELSE 'ready' END AS quality_status
          FROM diaphragm_inventory inventory
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


async def get_network_diaphragm_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    states = await conn.fetch("SELECT id, name, code FROM states ORDER BY ord, id")
    external_signs = await conn.fetch(
        "SELECT id, name, code FROM externalsignline ORDER BY ord, id"
    )
    locations = await conn.fetch(
        """SELECT throtdiaphloc AS name, count(*)::int AS total
             FROM diaphragms
            WHERE throtdiaphloc IS NOT NULL AND btrim(throtdiaphloc)<>''
            GROUP BY throtdiaphloc ORDER BY count(*) DESC, throtdiaphloc"""
    )
    entry_marks = await conn.fetch(
        """SELECT entrymark AS name, count(*)::int AS total
             FROM diaphragms
            WHERE entrymark IS NOT NULL AND btrim(entrymark)<>''
            GROUP BY entrymark ORDER BY count(*) DESC, entrymark"""
    )
    fragments = await conn.fetch(
        DIAPHRAGM_CTE
        + """
        SELECT fragment_id AS id, fragment_name AS name, count(*)::int AS total
          FROM classified_diaphragms
         WHERE fragment_id IS NOT NULL
         GROUP BY fragment_id, fragment_name ORDER BY fragment_name, fragment_id
        """
    )
    counts = await conn.fetchrow(
        DIAPHRAGM_CTE
        + """
        SELECT count(*)::int AS total,
               count(*) FILTER (WHERE quality_status='ready')::int AS ready,
               count(*) FILTER (WHERE quality_status='line_missing')::int AS line_missing,
               count(*) FILTER (WHERE quality_status='line_removed')::int AS line_removed,
               count(*) FILTER (WHERE quality_status='topology_missing')::int AS topology_missing,
               count(*) FILTER (WHERE quality_status='state_missing')::int AS state_missing,
               count(*) FILTER (WHERE quality_status='count_invalid')::int AS count_invalid,
               count(*) FILTER (WHERE quality_status='diameter_unresolved')::int AS diameter_unresolved,
               count(*) FILTER (WHERE state_id=1)::int AS opened,
               count(*) FILTER (WHERE state_id=2)::int AS closed,
               count(*) FILTER (WHERE longitude IS NOT NULL AND latitude IS NOT NULL)::int AS locatable,
               count(*) FILTER (WHERE longitude IS NULL OR latitude IS NULL)::int AS geometry_missing,
               count(*) FILTER (WHERE diameter_mode='available')::int AS diameter_available,
               count(*) FILTER (WHERE diameter_mode='pending_calculation')::int AS diameter_pending_calculation,
               count(*) FILTER (WHERE diameter_mode='unresolved')::int AS diameter_unavailable,
               count(*) FILTER (WHERE calculation_writeback_allowed)::int AS calculation_writeback_allowed,
               count(*) FILTER (WHERE installed_count IS NULL OR installed_count<=0)::int AS installed_count_invalid
          FROM classified_diaphragms
        """
    )
    return {
        "states": [dict(row) for row in states],
        "external_signs": [dict(row) for row in external_signs],
        "locations": [dict(row) for row in locations],
        "entry_marks": [dict(row) for row in entry_marks],
        "fragments": [dict(row) for row in fragments],
        "counts": dict(counts) if counts else {},
        "calculation_count": await conn.fetchval("SELECT count(*) FROM calculation"),
        "result_count": await conn.fetchval("SELECT count(*) FROM dro_out"),
    }


async def get_network_diaphragms(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    quality_status: Optional[DiaphragmQualityStatus] = None,
    diameter_mode: Optional[DiaphragmDiameterMode] = None,
    state_id: Optional[int] = None,
    external_sign_line_id: Optional[int] = None,
    fragment_id: Optional[int] = None,
    line_id: Optional[int] = None,
    installation_place: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    clauses: list[str] = []
    values: list[Any] = []
    if quality_status:
        _add_filter(clauses, values, "item.quality_status={param}", quality_status, "::text")
    if diameter_mode:
        _add_filter(clauses, values, "item.diameter_mode={param}", diameter_mode, "::text")
    if state_id is not None:
        _add_filter(clauses, values, "item.state_id={param}", state_id)
    if external_sign_line_id is not None:
        _add_filter(
            clauses, values, "item.external_sign_line_id={param}", external_sign_line_id
        )
    if fragment_id is not None:
        _add_filter(clauses, values, "item.fragment_id={param}", fragment_id)
    if line_id is not None:
        _add_filter(clauses, values, "item.line_id={param}", line_id)
    if installation_place:
        _add_filter(
            clauses,
            values,
            "item.installation_place={param}",
            installation_place.strip(),
            "::text",
        )
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
                 OR coalesce(item.internal_node_code, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.internal_node_name, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.registration_number, '') ILIKE '%' || {param} || '%'
                 OR coalesce(item.organization_name, '') ILIKE '%' || {param} || '%')""",
            normalized_search,
            "::text",
        )
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    total = await conn.fetchval(
        DIAPHRAGM_CTE + " SELECT count(*) FROM classified_diaphragms item" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        DIAPHRAGM_CTE
        + " SELECT * FROM classified_diaphragms item"
        + where_sql
        + f"""
          ORDER BY CASE item.quality_status
                     WHEN 'line_missing' THEN 1 WHEN 'line_removed' THEN 2
                     WHEN 'state_missing' THEN 3 WHEN 'count_invalid' THEN 4
                     WHEN 'diameter_unresolved' THEN 5 WHEN 'topology_missing' THEN 6
                     ELSE 7 END,
                   item.installation_place NULLS LAST, item.id
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


async def get_network_diaphragm(
    conn: asyncpg.Connection, diaphragm_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        DIAPHRAGM_CTE + " SELECT * FROM classified_diaphragms item WHERE item.id=$1",
        diaphragm_id,
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow("SELECT * FROM diaphragms WHERE id=$1", diaphragm_id)
    latest_output = await conn.fetchrow(
        """
        SELECT output.id, output.calculationid AS calculation_id,
               calculation.name AS calculation_name, calculation.date1 AS calculated_at,
               output.sos AS state_text,
               output.externalsignlineid AS external_sign_line_id,
               output.a8 AS installation_place, output.ras AS flow,
               output.a10 AS head_loss,
               output.a11 AS total_hydraulic_resistance,
               output.a12 AS available_head_end,
               output.a13 AS piezometric_head_end,
               output.a14 AS geodetic_mark_end,
               output.a15 AS total_head_end,
               output.ist AS heat_source_id, source.sourcename AS heat_source_name
          FROM dro_out output
          LEFT JOIN calculation ON calculation.id=output.calculationid
          LEFT JOIN heatsources source ON source.id=output.ist
         WHERE output.lineid=$1
         ORDER BY calculation.date1 DESC NULLS LAST,
                  output.calculationid DESC, output.id DESC LIMIT 1
        """,
        summary["line_id"],
    )
    related = await conn.fetch(
        DIAPHRAGM_CTE
        + """
        SELECT id, display_name, state_id, state_name, diameter_mode, quality_status
          FROM classified_diaphragms item
         WHERE item.line_id=$1 AND item.id<>$2 ORDER BY item.id LIMIT 50
        """,
        summary["line_id"],
        diaphragm_id,
    )
    result = dict(summary)
    result.update(
        {
            "attributes": dict(attributes) if attributes else {},
            "latest_output": dict(latest_output) if latest_output else None,
            "related_diaphragms": [dict(row) for row in related],
        }
    )
    return result
