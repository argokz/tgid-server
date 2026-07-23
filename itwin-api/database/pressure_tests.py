from datetime import date
from typing import Any, Optional

import asyncpg


PRESSURE_TEST_SUMMARY_SELECT = """
    SELECT
        test.id,
        test.name,
        test.opisaniye_kontura AS contour_description,
        test.granitsa_razdela AS boundary_description,
        test.istochnik_tepla AS heat_source_id,
        heat_source.naimenovanie AS heat_source_name,
        test.opres_typeid AS test_type_id,
        test_type.name AS test_type_name,
        test.sostoyanie_opresid AS state_id,
        state.name AS state_name,
        test.utverdit AS approval_id,
        CASE WHEN COALESCE(test.utverdit, 0)=0 THEN 'Не утверждено' ELSE 'Утверждено' END AS approval_name,
        test.data_nachala_plan AS planned_start,
        test.data_okonchaniya_plan AS planned_finish,
        test.data_utverzhdeniya_plana AS plan_approved_on,
        test.date_opres AS tested_at,
        test.vremya_provedeniya_opressovki AS tested_time,
        test.prodolzhitelnost_opressovki AS duration_minutes,
        COALESCE(test.date_opres::date, test.data_nachala_plan) AS effective_start,
        COALESCE(test.date_opres::date, test.data_okonchaniya_plan) AS effective_finish,
        test.davlenie_opressovki_1_etap AS stage_one_pressure,
        test.davlenie_opressovki_2_etap AS stage_two_pressure,
        test.temperatura_raskholazhivaniya_kontura AS cooling_temperature,
        test.kolichestvo_zvenjev_obhodchikov AS inspection_team_count,
        test.reshenie_komissii AS commission_decision,
        test.otchet AS report,
        test.primechanie AS note,
        test.responsibleid AS responsible_id,
        responsible.fio AS responsible_name,
        test.subdivisionid AS subdivision_id,
        subdivision.name AS subdivision_name,
        test.nodeoprid1 AS pump_node_id,
        pump_node.nodename AS pump_node_name,
        test.objekt_opressovochnogo_nasosaid AS pump_object_id,
        pump_object.name AS pump_object_name,
        COALESCE(deployed.line_count, 0) AS line_count,
        COALESCE(defects.defect_count, 0) AS defect_count,
        COALESCE(documents.document_count, 0) AS document_count,
        deployed.longitude,
        deployed.latitude
    FROM opres test
    LEFT JOIN istochniki_tepla heat_source ON heat_source.id=test.istochnik_tepla
    LEFT JOIN opres_types test_type ON test_type.id=test.opres_typeid
    LEFT JOIN sostoyanie_opres state ON state.id=test.sostoyanie_opresid
    LEFT JOIN nachalniki_uchastkov responsible ON responsible.id=test.responsibleid
    LEFT JOIN subdivisions subdivision ON subdivision.id=test.subdivisionid
    LEFT JOIN nodes pump_node ON pump_node.id=test.nodeoprid1
    LEFT JOIN objekt_opressovochnogo_nasosa pump_object
      ON pump_object.id=test.objekt_opressovochnogo_nasosaid
    LEFT JOIN LATERAL (
        SELECT
            count(DISTINCT relation.lineid)::int AS line_count,
            ST_X(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS longitude,
            ST_Y(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS latitude
        FROM opresdeployed relation
        LEFT JOIN linesobj line ON line.id=relation.lineid
        WHERE relation.directionid=test.id
    ) deployed ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS defect_count
        FROM defect defect_item WHERE defect_item.opresid=test.id
    ) defects ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS document_count FROM (
            SELECT id FROM opresdocuments WHERE objid=test.id
            UNION ALL SELECT id FROM opresacts WHERE objid=test.id
        ) files
    ) documents ON TRUE
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    state_id: Optional[int],
    test_type_id: Optional[int],
    heat_source_id: Optional[int],
    responsible_id: Optional[int],
    approved: Optional[bool],
    date_from: Optional[date],
    date_to: Optional[date],
    line_id: Optional[int],
    node_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if state_id is not None:
        _add_filter(clauses, values, "test.sostoyanie_opresid={param}", state_id)
    if test_type_id is not None:
        _add_filter(clauses, values, "test.opres_typeid={param}", test_type_id)
    if heat_source_id is not None:
        _add_filter(clauses, values, "test.istochnik_tepla={param}", heat_source_id)
    if responsible_id is not None:
        _add_filter(clauses, values, "test.responsibleid={param}", responsible_id)
    if approved is not None:
        clauses.append(
            "COALESCE(test.utverdit, 0)<>0" if approved else "COALESCE(test.utverdit, 0)=0"
        )
    date_expression = "COALESCE(test.date_opres::date, test.data_nachala_plan)"
    if date_from is not None:
        _add_filter(clauses, values, f"{date_expression}>={{param}}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, f"{date_expression}<={{param}}", date_to)
    if line_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1 FROM opresdeployed relation
                WHERE relation.directionid=test.id AND relation.lineid={param}
            )""",
            line_id,
        )
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            """(
                test.nodeoprid1={param} OR test.nodeoprid2={param}
                OR EXISTS (SELECT 1 FROM list_opres_node1 boundary WHERE boundary.objid=test.id AND boundary.nodeid={param})
                OR EXISTS (SELECT 1 FROM list_opres_node2 boundary WHERE boundary.objid=test.id AND boundary.nodeid={param})
                OR EXISTS (
                    SELECT 1 FROM opresdeployed relation
                    JOIN linesobj line ON line.id=relation.lineid
                    WHERE relation.directionid=test.id AND line.removed=0
                      AND (line.nodeid1={param} OR line.nodeid2={param})
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
                test.id::text={param}
                OR COALESCE(test.name, '') ILIKE '%' || {param} || '%'
                OR COALESCE(test.opisaniye_kontura, '') ILIKE '%' || {param} || '%'
                OR COALESCE(test.granitsa_razdela, '') ILIKE '%' || {param} || '%'
                OR COALESCE(test.reshenie_komissii, '') ILIKE '%' || {param} || '%'
                OR COALESCE(test.otchet, '') ILIKE '%' || {param} || '%'
                OR COALESCE(test.primechanie, '') ILIKE '%' || {param} || '%'
                OR COALESCE(heat_source.naimenovanie, '') ILIKE '%' || {param} || '%'
                OR COALESCE(responsible.fio, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_pressure_tests(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    state_id: Optional[int] = None,
    test_type_id: Optional[int] = None,
    heat_source_id: Optional[int] = None,
    responsible_id: Optional[int] = None,
    approved: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        state_id=state_id,
        test_type_id=test_type_id,
        heat_source_id=heat_source_id,
        responsible_id=responsible_id,
        approved=approved,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )
    total = await conn.fetchval(
        """SELECT count(*) FROM opres test
           LEFT JOIN istochniki_tepla heat_source ON heat_source.id=test.istochnik_tepla
           LEFT JOIN nachalniki_uchastkov responsible ON responsible.id=test.responsibleid"""
        + where_sql,
        *values,
    )
    query_values = [*values, page_size, (page - 1) * page_size]
    rows = await conn.fetch(
        PRESSURE_TEST_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY COALESCE(test.date_opres::date, test.data_nachala_plan)
              DESC NULLS LAST, test.id DESC
            LIMIT ${len(values) + 1} OFFSET ${len(values) + 2}
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


async def get_pressure_test_lookups(
    conn: asyncpg.Connection,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for key, table, name_column in (
        ("states", "sostoyanie_opres", "name"),
        ("test_types", "opres_types", "name"),
        ("heat_sources", "istochniki_tepla", "naimenovanie"),
        ("pump_objects", "objekt_opressovochnogo_nasosa", "name"),
        ("subdivisions", "subdivisions", "name"),
        ("document_types", "remontdocumenttypes", "name"),
    ):
        rows = await conn.fetch(
            f"SELECT id, {name_column} AS name FROM {table} "
            f"ORDER BY {name_column} NULLS LAST, id"
        )
        result[key] = [dict(row) for row in rows]
    responsible = await conn.fetch(
        "SELECT id, fio AS name FROM nachalniki_uchastkov ORDER BY fio, id"
    )
    result["responsible_people"] = [dict(row) for row in responsible]
    return result


async def _get_pressure_test_relations(
    conn: asyncpg.Connection, test_id: int
) -> dict[str, list[dict[str, Any]]]:
    lines = await conn.fetch(
        """
            SELECT
                relation.id, relation.lineid AS line_id,
                line.nodeid1 AS start_node_id, line.nodeid2 AS end_node_id,
                COALESCE(NULLIF(start_node.nodename, ''), start_node.externalnodename) AS start_node_name,
                COALESCE(NULLIF(end_node.nodename, ''), end_node.externalnodename) AS end_node_name,
                pipe.id AS heat_pipe_section_id, pipe.pipesectionid AS legacy_pipe_section_id,
                pipe.diametercondit AS diameter, pipe.pipesectlength AS length,
                tubing.name AS tubing_type_name,
                CASE WHEN line.shape IS NULL THEN NULL ELSE ST_X(ST_Centroid(ST_Transform(line.shape, 4326))) END AS longitude,
                CASE WHEN line.shape IS NULL THEN NULL ELSE ST_Y(ST_Centroid(ST_Transform(line.shape, 4326))) END AS latitude
            FROM opresdeployed relation
            LEFT JOIN linesobj line ON line.id=relation.lineid
            LEFT JOIN nodes start_node ON start_node.id=line.nodeid1
            LEFT JOIN nodes end_node ON end_node.id=line.nodeid2
            LEFT JOIN LATERAL (
                SELECT candidate.* FROM heatpipesections candidate
                WHERE candidate.lineid=line.id ORDER BY candidate.id LIMIT 1
            ) pipe ON TRUE
            LEFT JOIN tubingtypes tubing ON tubing.id=pipe.tubingtypeid
            WHERE relation.directionid=$1 ORDER BY relation.id
        """,
        test_id,
    )
    defects = await conn.fetch(
        """
            SELECT defect_item.id, defect_item.lineid AS line_id,
                   defect_item.data_osmotra AS detected_at,
                   defect_item.defectdescription AS description,
                   source.name AS source_name, state.name AS state_name,
                   CASE WHEN defect_item.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(defect_item.shape, 4326)) END AS longitude,
                   CASE WHEN defect_item.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(defect_item.shape, 4326)) END AS latitude
            FROM defect defect_item
            LEFT JOIN defecttypes source ON source.id=defect_item.remonttypeid
            LEFT JOIN statedefect state ON state.id=defect_item.stateid
            WHERE defect_item.opresid=$1
            ORDER BY defect_item.data_osmotra DESC NULLS LAST, defect_item.id DESC
        """,
        test_id,
    )
    documents = await conn.fetch(
        """
            SELECT file.id, file.kind, file.date_doc, file.path,
                   file.remontdocumenttypeid AS document_type_id,
                   document_type.name AS document_type_name
            FROM (
                SELECT id, 'Рабочая программа'::text AS kind, date_doc, path, remontdocumenttypeid
                FROM opresdocuments WHERE objid=$1
                UNION ALL
                SELECT id, 'Акт испытаний'::text AS kind, date_doc, path, remontdocumenttypeid
                FROM opresacts WHERE objid=$1
            ) file
            LEFT JOIN remontdocumenttypes document_type
              ON document_type.id=file.remontdocumenttypeid
            ORDER BY file.date_doc DESC NULLS LAST, file.id DESC
        """,
        test_id,
    )
    boundary_nodes = await conn.fetch(
        """
            SELECT boundary.kind, boundary.node_id,
                   COALESCE(NULLIF(node.nodename, ''), node.externalnodename) AS node_name,
                   CASE WHEN node.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(node.shape, 4326)) END AS longitude,
                   CASE WHEN node.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(node.shape, 4326)) END AS latitude
            FROM (
                SELECT 'Начальная граница'::text AS kind, nodeid AS node_id
                  FROM list_opres_node1 WHERE objid=$1
                UNION ALL
                SELECT 'Конечная граница'::text AS kind, nodeid AS node_id
                  FROM list_opres_node2 WHERE objid=$1
            ) boundary
            LEFT JOIN nodes node ON node.id=boundary.node_id
            ORDER BY boundary.kind, boundary.node_id
        """,
        test_id,
    )
    measures = await conn.fetch(
        """
            SELECT relation.id, relation.activityid AS measure_id, measure.name AS measure_name
            FROM opresmeropr relation
            LEFT JOIN defectmeroprtype measure ON measure.id=relation.activityid
            WHERE relation.objid=$1 ORDER BY measure.ord NULLS LAST, relation.id
        """,
        test_id,
    )
    return {
        "lines": [dict(row) for row in lines],
        "defects": [dict(row) for row in defects],
        "documents": [dict(row) for row in documents],
        "boundary_nodes": [dict(row) for row in boundary_nodes],
        "measures": [dict(row) for row in measures],
    }


async def get_pressure_test(
    conn: asyncpg.Connection, test_id: int
) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        PRESSURE_TEST_SUMMARY_SELECT.replace(
            "test.id,",
            """test.id,
        test.defects AS defects_text,
        test.nodeoprid2 AS secondary_pump_node_id,
        test.ne_preduprezhdennye_potrebiteli AS unnotified_consumers,
        test.spisok_potrev_ne_predupr AS unnotified_consumer_list,
        test.spisok_trub_ne_uchav AS excluded_pipelines,
        test.data_utverzhdeniya_akta_ispytanij AS act_approved_on,
        test.akt_ispytanij AS act_file,
        test.fio_utverzhdaemogo AS approver_name,
        test.fio_rukovoditel_ispytanij AS test_manager_name,
        test.fio_otvetstvennyj_za_obespechenie_rezhimov AS mode_manager_name,
        test.fio_otvetstvennyj_za_blank_pereklyuchenij AS switching_manager_name,
        test.fio_otvetstvennyj_za_ustanovku_manometrov_i_raskhodomerov AS meter_manager_name,
        test.fio_otvetstvennyj_za_obespechenie_avtotransportom AS transport_manager_name,
        test.fio_otvetstvennyj_za_obespechenie_raboty_elektrooborudovaniya AS electrical_manager_name,
        test.fio_otvetstvennyj_po_snip_kontura_istochnika_tepla AS source_safety_manager_name,
        test.fio_otvetstvennyj_za_opoveshchenie_naseleniya_o_ispytaniyah AS public_notification_manager_name,""",
            1,
        )
        + " WHERE test.id=$1",
        test_id,
    )
    if row is None:
        return None
    result = dict(row)
    result["relations"] = await _get_pressure_test_relations(conn, test_id)
    return result
