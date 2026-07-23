from datetime import date
from typing import Any, Optional

import asyncpg


INSPECTION_SUMMARY_SELECT = """
    SELECT
        inspection.id,
        inspection.name,
        inspection.data_osmotra AS inspected_on,
        inspection.nomer_akta AS act_number,
        inspection.predpolagaemye_prichiny_razrusheniya_izolyacii_korrozii AS suspected_causes,
        inspection.rezultaty_osmotra AS results,
        inspection.namechennye_meropriyatiya AS planned_measures,
        inspection.meropriyatiya_po_vosstanovleniyu_prokladki AS restoration_measures,
        inspection.primechanie AS note,
        inspection.otvetstvennoe_lico_id AS responsible_id,
        responsible.fio AS responsible_name,
        inspection.podrazdelenie_provodivshee_raboty AS subdivision_id,
        subdivision.name AS subdivision_name,
        COALESCE(deployed.line_count, 0) AS line_count,
        COALESCE(risks.risk_count, 0) AS inspected_section_count,
        COALESCE(defects.defect_count, 0) AS defect_count,
        deployed.longitude,
        deployed.latitude
    FROM osmotr inspection
    LEFT JOIN nachalniki_uchastkov responsible
      ON responsible.id=inspection.otvetstvennoe_lico_id
    LEFT JOIN subdivisions subdivision
      ON subdivision.id=inspection.podrazdelenie_provodivshee_raboty
    LEFT JOIN LATERAL (
        SELECT
            count(DISTINCT relation.lineid)::int AS line_count,
            ST_X(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS longitude,
            ST_Y(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS latitude
        FROM osmotrdeployed relation
        LEFT JOIN linesobj line ON line.id=relation.lineid
        WHERE relation.directionid=inspection.id
    ) deployed ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS risk_count
        FROM faktory_riska_truboprovoda risk
        WHERE risk.objid=inspection.id AND risk.obj_type_faktory_riskaid=2
    ) risks ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS defect_count
        FROM defect defect_item
        WHERE defect_item.osmotrid=inspection.id
    ) defects ON TRUE
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    responsible_id: Optional[int],
    has_defects: Optional[bool],
    has_inspected_sections: Optional[bool],
    date_from: Optional[date],
    date_to: Optional[date],
    line_id: Optional[int],
    node_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []

    if responsible_id is not None:
        _add_filter(
            clauses,
            values,
            "inspection.otvetstvennoe_lico_id={param}",
            responsible_id,
        )
    if has_defects is not None:
        condition = "EXISTS" if has_defects else "NOT EXISTS"
        clauses.append(
            f"{condition} (SELECT 1 FROM defect d WHERE d.osmotrid=inspection.id)"
        )
    if has_inspected_sections is not None:
        condition = "EXISTS" if has_inspected_sections else "NOT EXISTS"
        clauses.append(
            f"""{condition} (
                SELECT 1 FROM faktory_riska_truboprovoda risk
                WHERE risk.objid=inspection.id
                  AND risk.obj_type_faktory_riskaid=2
            )"""
        )
    if date_from is not None:
        _add_filter(clauses, values, "inspection.data_osmotra >= {param}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, "inspection.data_osmotra <= {param}", date_to)
    if line_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1 FROM osmotrdeployed relation
                WHERE relation.directionid=inspection.id AND relation.lineid={param}
            )""",
            line_id,
        )
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1
                FROM osmotrdeployed relation
                JOIN linesobj line ON line.id=relation.lineid
                WHERE relation.directionid=inspection.id
                  AND line.removed=0
                  AND (line.nodeid1={param} OR line.nodeid2={param})
            )""",
            node_id,
        )

    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                inspection.id::text={param}
                OR COALESCE(inspection.name, '') ILIKE '%' || {param} || '%'
                OR COALESCE(inspection.nomer_akta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(inspection.rezultaty_osmotra, '') ILIKE '%' || {param} || '%'
                OR COALESCE(inspection.predpolagaemye_prichiny_razrusheniya_izolyacii_korrozii, '')
                   ILIKE '%' || {param} || '%'
                OR COALESCE(inspection.primechanie, '') ILIKE '%' || {param} || '%'
                OR COALESCE(responsible.fio, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_inspections(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    responsible_id: Optional[int] = None,
    has_defects: Optional[bool] = None,
    has_inspected_sections: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        responsible_id=responsible_id,
        has_defects=has_defects,
        has_inspected_sections=has_inspected_sections,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )
    total = await conn.fetchval(
        """SELECT count(*)
           FROM osmotr inspection
           LEFT JOIN nachalniki_uchastkov responsible
             ON responsible.id=inspection.otvetstvennoe_lico_id"""
        + where_sql,
        *values,
    )
    query_values = [*values, page_size, (page - 1) * page_size]
    rows = await conn.fetch(
        INSPECTION_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY inspection.data_osmotra DESC NULLS LAST, inspection.id DESC
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


async def get_inspection_lookups(
    conn: asyncpg.Connection,
) -> dict[str, list[dict[str, Any]]]:
    responsible = await conn.fetch(
        "SELECT id, fio AS name FROM nachalniki_uchastkov ORDER BY fio, id"
    )
    subdivisions = await conn.fetch(
        "SELECT id, name FROM subdivisions ORDER BY COALESCE(ord, id), id"
    )
    states = await conn.fetch(
        "SELECT id, name FROM osmotr_sostoyanie ORDER BY COALESCE(ord, id), id"
    )
    document_types = await conn.fetch(
        "SELECT id, name FROM vidy_dokumentov_osmotra ORDER BY COALESCE(ord, id), id"
    )
    return {
        "responsible_people": [dict(row) for row in responsible],
        "subdivisions": [dict(row) for row in subdivisions],
        "legacy_states": [dict(row) for row in states],
        "document_types": [dict(row) for row in document_types],
    }


async def _get_inspection_relations(
    conn: asyncpg.Connection, inspection_id: int
) -> dict[str, list[dict[str, Any]]]:
    lines = await conn.fetch(
        """
            SELECT
                relation.id,
                relation.lineid AS line_id,
                line.nodeid1 AS start_node_id,
                line.nodeid2 AS end_node_id,
                COALESCE(NULLIF(start_node.nodename, ''), start_node.externalnodename) AS start_node_name,
                COALESCE(NULLIF(end_node.nodename, ''), end_node.externalnodename) AS end_node_name,
                pipe.id AS heat_pipe_section_id,
                pipe.pipesectionid AS legacy_pipe_section_id,
                pipe.diametercondit AS diameter,
                pipe.pipesectlength AS length,
                tubing.name AS tubing_type_name,
                CASE WHEN line.shape IS NULL THEN NULL
                  ELSE ST_X(ST_Centroid(ST_Transform(line.shape, 4326))) END AS longitude,
                CASE WHEN line.shape IS NULL THEN NULL
                  ELSE ST_Y(ST_Centroid(ST_Transform(line.shape, 4326))) END AS latitude
            FROM osmotrdeployed relation
            LEFT JOIN linesobj line ON line.id=relation.lineid
            LEFT JOIN nodes start_node ON start_node.id=line.nodeid1
            LEFT JOIN nodes end_node ON end_node.id=line.nodeid2
            LEFT JOIN LATERAL (
                SELECT candidate.*
                FROM heatpipesections candidate
                WHERE candidate.lineid=line.id
                ORDER BY candidate.id
                LIMIT 1
            ) pipe ON TRUE
            LEFT JOIN tubingtypes tubing ON tubing.id=pipe.tubingtypeid
            WHERE relation.directionid=$1
            ORDER BY relation.id
        """,
        inspection_id,
    )
    defects = await conn.fetch(
        """
            SELECT
                defect_item.id,
                defect_item.lineid AS line_id,
                defect_item.data_osmotra AS detected_at,
                defect_item.defectdescription AS description,
                source.name AS source_name,
                state.name AS state_name,
                CASE WHEN defect_item.shape IS NULL THEN NULL
                  ELSE ST_X(ST_Transform(defect_item.shape, 4326)) END AS longitude,
                CASE WHEN defect_item.shape IS NULL THEN NULL
                  ELSE ST_Y(ST_Transform(defect_item.shape, 4326)) END AS latitude
            FROM defect defect_item
            LEFT JOIN defecttypes source ON source.id=defect_item.remonttypeid
            LEFT JOIN statedefect state ON state.id=defect_item.stateid
            WHERE defect_item.osmotrid=$1
            ORDER BY defect_item.data_osmotra DESC NULLS LAST, defect_item.id DESC
        """,
        inspection_id,
    )
    documents = await conn.fetch(
        """
            SELECT
                document.id,
                document.date_doc,
                document.path,
                document.remontdocumenttypeid AS document_type_id,
                document_type.name AS document_type_name
            FROM osmotrdocuments document
            LEFT JOIN vidy_dokumentov_osmotra document_type
              ON document_type.id=document.remontdocumenttypeid
            WHERE document.objid=$1
            ORDER BY document.date_doc DESC NULLS LAST, document.id DESC
        """,
        inspection_id,
    )
    risk_factors = await conn.fetch(
        """
            SELECT
                risk.id,
                risk.lineid AS legacy_pipe_section_id,
                ground.name AS ground_name,
                surface.name AS surface_name,
                communication.name AS nearby_communication_name,
                outer_view.name AS outer_view_name,
                equipment.name AS equipment_state_name,
                metal.name AS pipe_metal_state_name,
                corrosion_flow.name AS corrosion_flow_name,
                corrosion_return.name AS corrosion_return_name,
                insulation_flow.name AS insulation_flow_name,
                insulation_return.name AS insulation_return_name,
                cover_flow.name AS outer_cover_flow_name,
                cover_return.name AS outer_cover_return_name,
                anticorrosion_flow.name AS anticorrosion_flow_name,
                anticorrosion_return.name AS anticorrosion_return_name,
                construction.name AS channel_construction_state_name,
                channel_inside.name AS channel_inside_state_name,
                drainage.name AS drainage_construction_name,
                risk.podtoplenie_do_truby,
                risk.elektrich,
                risk.transportelekricht,
                risk.ponezial,
                risk.vnesnkorrozia,
                risk.vnunrenkorrozia,
                risk.tol1,
                risk.tol2,
                risk.glubina_kor,
                risk.razmery_kor,
                risk.document_analiz_vlazhnost,
                risk.document_analiz_korrozia,
                risk.document_potenzial,
                risk.document_analiz_vytyazhka,
                risk.dokument_chertezh_objekta_kontrolya
            FROM faktory_riska_truboprovoda risk
            LEFT JOIN harakter_grunta_shurf ground ON ground.id=risk.harakter_gruntaid
            LEFT JOIN poverhnost_nad_trassoj surface ON surface.id=risk.poverhnost_nad_trassojid
            LEFT JOIN nalichie_vblizi_kommunikacij communication
              ON communication.id=risk.nalichie_vblizi_kommunikacijid
            LEFT JOIN vneshny_vid outer_view ON outer_view.id=risk.vnesniivid
            LEFT JOIN sost_oborud equipment ON equipment.id=risk.sostoborudovania
            LEFT JOIN sostoyanie_metalla_truboprovoda metal
              ON metal.id=risk.sostoyanie_metalla_truboprovodaid
            LEFT JOIN nalichie_korrozii_shurf corrosion_flow
              ON corrosion_flow.id=risk.nalichie_korrozii_podachaid
            LEFT JOIN nalichie_korrozii_shurf corrosion_return
              ON corrosion_return.id=risk.nalichie_korrozii_obratkaid
            LEFT JOIN sostoyanie_teplovoj_izolyacii insulation_flow
              ON insulation_flow.id=risk.sostoyanie_teplovoj_izolyacii_podachaid
            LEFT JOIN sostoyanie_teplovoj_izolyacii insulation_return
              ON insulation_return.id=risk.sostoyanie_teplovoj_izolyacii_obratkaid
            LEFT JOIN sostoyanie_naruzhnogo_pokrytiya cover_flow
              ON cover_flow.id=risk.sostoyanie_naruzhnogo_pokrytiya_podachaid
            LEFT JOIN sostoyanie_naruzhnogo_pokrytiya cover_return
              ON cover_return.id=risk.sostoyanie_naruzhnogo_pokrytiya_obratkaid
            LEFT JOIN sostoyanie_protivokorrozionnogo_pokrytiya_shurf anticorrosion_flow
              ON anticorrosion_flow.id=risk.sostoyanie_protivokorrozionnogo_pokrytiya_podachaid
            LEFT JOIN sostoyanie_protivokorrozionnogo_pokrytiya_shurf anticorrosion_return
              ON anticorrosion_return.id=risk.sostoyanie_protivokorrozionnogo_pokrytiya_obratkaid
            LEFT JOIN sostoyanie_stroitelnyh_konstrukcij_kanala construction
              ON construction.id=risk.sostoyanie_stroitelnyh_konstrukcij_kanalaid
            LEFT JOIN vnutrennee_sostoyanie_kanala channel_inside
              ON channel_inside.id=risk.vnutrennee_sostoyanie_kanalaid
            LEFT JOIN konstrukciya_drenazhnogo_ustrojstva drainage
              ON drainage.id=risk.konstrukciya_drenazhnogo_ustrojstvaid
            WHERE risk.objid=$1 AND risk.obj_type_faktory_riskaid=2
            ORDER BY risk.id
        """,
        inspection_id,
    )
    return {
        "lines": [dict(row) for row in lines],
        "defects": [dict(row) for row in defects],
        "documents": [dict(row) for row in documents],
        "risk_factors": [dict(row) for row in risk_factors],
    }


async def get_inspection(
    conn: asyncpg.Connection, inspection_id: int
) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        INSPECTION_SUMMARY_SELECT.replace(
            "inspection.id,",
            """inspection.id,
        inspection.fio_utverzhdaemogo AS approver_name,
        approver_position.znachenie AS approver_position,
        approver_service.name AS approver_service,
        inspection.fio_1 AS commission_member_1,
        commission_position_1.znachenie AS commission_position_1,
        inspection.fio_2 AS commission_member_2,
        commission_position_2.znachenie AS commission_position_2,
        inspection.spisok_trub_ne_uchav AS excluded_pipes,
        inspection.spisok_potrev_ne_predupr AS unnotified_consumers,""",
            1,
        )
        + """
        LEFT JOIN dolzhnosti approver_position
          ON approver_position.id=inspection.dolzhnost_utverzhdaemogoid
        LEFT JOIN subdivisions approver_service
          ON approver_service.id=inspection.sluzhba_utverzhdaemogoid
        LEFT JOIN dolzhnosti commission_position_1
          ON commission_position_1.id=inspection.dolzhnost_1
        LEFT JOIN dolzhnosti commission_position_2
          ON commission_position_2.id=inspection.dolzhnost_2
        WHERE inspection.id=$1
        """,
        inspection_id,
    )
    if row is None:
        return None
    result = dict(row)
    result["relations"] = await _get_inspection_relations(conn, inspection_id)
    return result
