from datetime import date
from typing import Any, Optional

import asyncpg


DEFECT_SUMMARY_SELECT = """
    SELECT
        d.id,
        d.lineid AS line_id,
        d.name,
        d.data_osmotra AS detected_at,
        d.vremya_osmotra AS detected_time,
        d.defectdescription AS description,
        d.otchet_po_defektu AS report_note,
        d.data_nachala_remonta AS repair_started_on,
        d.data_zaversheniya_remonta AS repair_finished_on,
        d.remonttypeid AS source_id,
        source.name AS source_name,
        d.stateid AS state_id,
        state.name AS state_name,
        d.remontcatid AS category_id,
        category.name AS category_name,
        d.vid_narusheniyaid AS violation_type_id,
        violation.name AS violation_type_name,
        violation.code AS violation_type_code,
        d.priznak_truboprovoda AS pipeline_sign_id,
        pipeline_sign.name AS pipeline_sign_name,
        NULLIF(CONCAT_WS(' ', street.name, NULLIF(d.nomer_doma, '')), '') AS address,
        COALESCE(NULLIF(line_node_1.nodename, ''), line_node_1.externalnodename) AS line_start_node,
        COALESCE(NULLIF(line_node_2.nodename, ''), line_node_2.externalnodename) AS line_end_node,
        CASE WHEN d.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(d.shape, 4326)) END AS longitude,
        CASE WHEN d.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(d.shape, 4326)) END AS latitude
    FROM defect d
    LEFT JOIN defecttypes source ON source.id = d.remonttypeid
    LEFT JOIN statedefect state ON state.id = d.stateid
    LEFT JOIN remontcat category ON category.id = d.remontcatid
    LEFT JOIN vid_narusheniya violation ON violation.id = d.vid_narusheniyaid
    LEFT JOIN externalsigns pipeline_sign ON pipeline_sign.id = d.priznak_truboprovoda
    LEFT JOIN ulitsy street ON street.id = d.ulicaid
    LEFT JOIN linesobj line ON line.id = d.lineid
    LEFT JOIN nodes line_node_1 ON line_node_1.id = line.nodeid1
    LEFT JOIN nodes line_node_2 ON line_node_2.id = line.nodeid2
"""


def _add_filter(
    clauses: list[str],
    values: list[Any],
    expression: str,
    value: Any,
    cast: str = "",
) -> None:
    values.append(value)
    placeholder = f"${len(values)}{cast}"
    clauses.append(expression.format(param=placeholder))


def _build_filters(
    *,
    source_id: Optional[int],
    state_id: Optional[int],
    category_id: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
    line_id: Optional[int],
    node_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []

    if source_id is not None:
        _add_filter(clauses, values, "d.remonttypeid = {param}", source_id)
    if state_id is not None:
        _add_filter(clauses, values, "d.stateid = {param}", state_id)
    if category_id is not None:
        _add_filter(clauses, values, "d.remontcatid = {param}", category_id)
    if date_from is not None:
        _add_filter(clauses, values, "d.data_osmotra::date >= {param}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, "d.data_osmotra::date <= {param}", date_to)
    if line_id is not None:
        _add_filter(clauses, values, "d.lineid = {param}", line_id)
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            """(
                d.nodeid1 = {param}
                OR d.nodeid2 = {param}
                OR EXISTS (
                    SELECT 1
                    FROM linesobj selected_line
                    WHERE selected_line.id = d.lineid
                      AND selected_line.removed = 0
                      AND (selected_line.nodeid1 = {param} OR selected_line.nodeid2 = {param})
                )
            )""",
            node_id,
        )
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                d.id::text = {param}
                OR COALESCE(d.name, '') ILIKE '%' || {param} || '%'
                OR COALESCE(d.defectdescription, '') ILIKE '%' || {param} || '%'
                OR COALESCE(d.otchet_po_defektu, '') ILIKE '%' || {param} || '%'
                OR COALESCE(d.nomer_akta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(street.name, '') ILIKE '%' || {param} || '%'
                OR COALESCE(d.nomer_doma, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_defects(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    source_id: Optional[int] = None,
    state_id: Optional[int] = None,
    category_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        source_id=source_id,
        state_id=state_id,
        category_id=category_id,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )

    count_sql = """
        SELECT count(*)
        FROM defect d
        LEFT JOIN ulitsy street ON street.id = d.ulicaid
    """ + where_sql
    total = await conn.fetchval(count_sql, *values)

    query_values = [*values, page_size, (page - 1) * page_size]
    limit_placeholder = f"${len(values) + 1}"
    offset_placeholder = f"${len(values) + 2}"
    rows = await conn.fetch(
        DEFECT_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY d.data_osmotra DESC NULLS LAST, d.id DESC
            LIMIT {limit_placeholder} OFFSET {offset_placeholder}
        """,
        *query_values,
    )

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


async def get_defect_lookups(conn: asyncpg.Connection) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for response_key, table_name in (
        ("sources", "defecttypes"),
        ("states", "statedefect"),
        ("categories", "remontcat"),
    ):
        rows = await conn.fetch(
            f"SELECT id, name, code FROM {table_name} ORDER BY COALESCE(ord, id), id"
        )
        result[response_key] = [dict(row) for row in rows]
    return result


async def _get_named_relations(
    conn: asyncpg.Connection, defect_id: int
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    relations = (
        ("damage_elements", "povrezhdennyielementfordefect", "povrezhdennyielement"),
        ("technical_causes", "prichinypovrezhdeniafordefect", "prichinypovrezhdenia"),
        (
            "organizational_causes",
            "prichiny_narusheniya_organizacionnye_for_defect",
            "prichiny_narusheniya_organizacionnye",
        ),
        ("contributing_causes", "soputstvuiushchieprichinyfordefect", "soputstvuiushchieprichiny"),
        ("channel_states", "sostkonstruktsiikanalafordefect", "sostkonstruktsiikanala"),
        ("chamber_states", "sostkonstruktsiikameryfordefect", "sostkonstruktsiikamery"),
    )
    for response_key, relation_table, lookup_table in relations:
        rows = await conn.fetch(
            f"""
                SELECT DISTINCT lookup.id, lookup.name
                FROM {relation_table} relation
                JOIN {lookup_table} lookup ON lookup.id = relation.activityid
                WHERE relation.objid = $1
                ORDER BY lookup.name
            """,
            defect_id,
        )
        result[response_key] = [dict(row) for row in rows]

    repair_rows = await conn.fetch(
        """
            SELECT DISTINCT
                work.id AS work_id,
                work.name AS work_name,
                element.id AS element_id,
                element.name AS element_name
            FROM defecttube relation
            LEFT JOIN remonttruboprovodaspisok work ON work.id = relation.activityid
            LEFT JOIN spisokelementov element ON element.id = relation.elementid
            WHERE relation.objid = $1
            ORDER BY work.name NULLS LAST, element.name NULLS LAST
        """,
        defect_id,
    )
    result["pipe_repairs"] = [dict(row) for row in repair_rows]
    return result


async def get_defect(conn: asyncpg.Connection, defect_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        DEFECT_SUMMARY_SELECT
        + """
        LEFT JOIN tippoverhnosti surface ON surface.id = d.tippoverhnostiid
        LEFT JOIN tippovrezhdenia damage_type ON damage_type.id = d.tippovrezhdeniaid
        LEFT JOIN vid_rabot work_type ON work_type.id = d.vid_rabotid
        LEFT JOIN sostteploizol thermal_state ON thermal_state.id = d.sostteploizolid
        LEFT JOIN sostnaruzhnoipoverkhnosti outer_state ON outer_state.id = d.sostnaruzhnoipoverkhnostiid
        LEFT JOIN sostvnutrenneipoverkhnosti inner_state ON inner_state.id = d.sostvnutrenneipoverkhnostiid
        LEFT JOIN nodes nearest_chamber ON nearest_chamber.id = d.nodeid_bizhajshej_kamery
        LEFT JOIN nodes disconnect_node_1 ON disconnect_node_1.id = d.nodeid1
        LEFT JOIN nodes disconnect_node_2 ON disconnect_node_2.id = d.nodeid2
        LEFT JOIN opres pressure_test ON pressure_test.id = d.opresid
        LEFT JOIN osmotr inspection ON inspection.id = d.osmotrid
        LEFT JOIN remont repair ON repair.id = d.remontid
        LEFT JOIN subdivisions subdivision ON subdivision.id = d.subdivisionid
        LEFT JOIN nachalniki_uchastkov responsible ON responsible.id = d.responsibleid
        LEFT JOIN brigades brigade ON brigade.id = d.brigadesid
        WHERE d.id = $1
        """.replace(
            "d.id,",
            """d.id,
        d.primechanie AS note,
        d.meropriyatiya AS liquidation_method,
        d.data_shurfovki AS excavation_date,
        d.nomer_akta AS act_number,
        d.data_sostavleniya_akta AS act_date,
        d.nomer_prikaza AS order_number,
        d.data_prikaza_vvoda_v_ekspluataciyu AS commissioning_order_date,
        d.rasstoyaniedopovrezhdeniyanachkamery AS distance_to_nearest_chamber,
        d.tsentrpovrezhdenia AS damage_clock_position,
        d.vysotapovrezhdenia AS damage_height,
        d.shirinapovrezhdenia AS damage_width,
        d.ploshchadpovrezhdenia AS damage_area,
        d.shirinazaplatki AS patch_width,
        d.vysotazaplatki AS patch_height,
        d.len_tube_cur AS replaced_pipe_length,
        d.len_izol_cur AS replaced_insulation_length,
        d.len_channel_cur AS repaired_channel_length,
        d.trudozatratynaremont AS repair_labor,
        d.stoimostremonta::text AS repair_cost,
        d.kolichestvo_otklyuchennyh_potrebitelej AS disconnected_consumers,
        d.kolichestvo_nedootpushchennoj_teplovoj_energii AS undelivered_heat,
        d.zatraty_na_vosstanovlenie::text AS recovery_cost,
        d.inye_socialnye_posledstviya AS social_consequences,
        surface.name AS surface_name,
        damage_type.name AS damage_type_name,
        work_type.name AS work_type_name,
        thermal_state.name AS thermal_insulation_state,
        outer_state.name AS outer_surface_state,
        inner_state.name AS inner_surface_state,
        COALESCE(NULLIF(nearest_chamber.nodename, ''), nearest_chamber.externalnodename) AS nearest_chamber_name,
        COALESCE(NULLIF(disconnect_node_1.nodename, ''), disconnect_node_1.externalnodename) AS disconnect_start_node,
        COALESCE(NULLIF(disconnect_node_2.nodename, ''), disconnect_node_2.externalnodename) AS disconnect_end_node,
        pressure_test.id AS pressure_test_id,
        pressure_test.name AS pressure_test_name,
        inspection.id AS inspection_id,
        inspection.name AS inspection_name,
        repair.id AS repair_id,
        repair.otchet_po_defektu AS repair_name,
        subdivision.name AS subdivision_name,
        responsible.fio AS responsible_name,
        brigade.name AS brigade_name,""",
            1,
        ),
        defect_id,
    )
    if row is None:
        return None

    result = dict(row)
    result["relations"] = await _get_named_relations(conn, defect_id)
    return result

async def get_defects_geojson(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch("""
        SELECT
            d.id,
            d.defectdescription AS description,
            d.data_osmotra AS detected_at,
            ST_AsGeoJSON(ST_Transform(d.shape, 4326)) AS geometry
        FROM defect d
        WHERE d.shape IS NOT NULL
    """)
    
    import json
    features = []
    for row in rows:
        geom = row["geometry"]
        if not geom:
            continue
            
        features.append({
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": row["id"],
                "description": row["description"] or """,
                "detected_at": str(row["detected_at"]) if row["detected_at"] else """,
                "type": "defect"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

