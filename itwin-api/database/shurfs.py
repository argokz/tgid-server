from datetime import date
from typing import Any, Optional

import asyncpg


SHURF_SUMMARY_SELECT = """
    SELECT
        s.id,
        s.lineid AS line_id,
        s.naznachenie_vskrid AS purpose_id,
        purpose.name AS purpose_name,
        s.sostoyanie_shurfaid AS state_id,
        state.name AS state_name,
        s.data_nachala_plan AS planned_start,
        s.data_okonchaniya_plan AS planned_finish,
        s.data_nachala AS actual_start,
        s.data_okonchaniya AS actual_finish,
        COALESCE(s.data_nachala, s.data_nachala_plan) AS effective_start,
        COALESCE(s.data_okonchaniya, s.data_okonchaniya_plan) AS effective_finish,
        s.utverdit AS approval_id,
        CASE WHEN COALESCE(s.utverdit, 0) = 0 THEN 'Не утверждено' ELSE 'Утверждено' END AS approval_name,
        s.data_utverzhdeniya_plana_shurfovok AS approved_on,
        NULLIF(CONCAT_WS(' ', street.name, NULLIF(s.nomer_doma, '')), '') AS address,
        s.nomer_akta AS act_number,
        s.rezultaty_osmotra AS inspection_results,
        s.namechennye_meropriyatiya AS planned_measures,
        s.primechanie AS note,
        material.name AS material_name,
        COALESCE(NULLIF(line_node_1.nodename, ''), line_node_1.externalnodename) AS line_start_node,
        COALESCE(NULLIF(line_node_2.nodename, ''), line_node_2.externalnodename) AS line_end_node,
        CASE WHEN s.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(s.shape, 4326)) END AS longitude,
        CASE WHEN s.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(s.shape, 4326)) END AS latitude
    FROM shurfy s
    LEFT JOIN naznachenie_vskr purpose ON purpose.id = s.naznachenie_vskrid
    LEFT JOIN sostoyanie_shurfa state ON state.id = s.sostoyanie_shurfaid
    LEFT JOIN ulitsy street ON street.id = s.ulicaid
    LEFT JOIN materialy_i_mekhanizmy material ON material.id = s.materialy_i_mekhanizmyid
    LEFT JOIN linesobj line ON line.id = s.lineid
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
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    purpose_id: Optional[int],
    state_id: Optional[int],
    approved: Optional[bool],
    date_from: Optional[date],
    date_to: Optional[date],
    line_id: Optional[int],
    node_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []

    if purpose_id is not None:
        _add_filter(clauses, values, "s.naznachenie_vskrid = {param}", purpose_id)
    if state_id is not None:
        _add_filter(clauses, values, "s.sostoyanie_shurfaid = {param}", state_id)
    if approved is not None:
        clauses.append(
            "COALESCE(s.utverdit, 0) <> 0" if approved else "COALESCE(s.utverdit, 0) = 0"
        )
    if date_from is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(s.data_nachala, s.data_nachala_plan) >= {param}",
            date_from,
        )
    if date_to is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(s.data_nachala, s.data_nachala_plan) <= {param}",
            date_to,
        )
    if line_id is not None:
        _add_filter(clauses, values, "s.lineid = {param}", line_id)
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1
                FROM linesobj selected_line
                WHERE selected_line.id = s.lineid
                  AND selected_line.removed = 0
                  AND (selected_line.nodeid1 = {param} OR selected_line.nodeid2 = {param})
            )""",
            node_id,
        )
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                s.id::text = {param}
                OR COALESCE(street.name, '') ILIKE '%' || {param} || '%'
                OR COALESCE(s.nomer_doma, '') ILIKE '%' || {param} || '%'
                OR COALESCE(s.nomer_akta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(s.rezultaty_osmotra, '') ILIKE '%' || {param} || '%'
                OR COALESCE(s.namechennye_meropriyatiya, '') ILIKE '%' || {param} || '%'
                OR COALESCE(s.primechanie, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )

    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_shurfs(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    purpose_id: Optional[int] = None,
    state_id: Optional[int] = None,
    approved: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        purpose_id=purpose_id,
        state_id=state_id,
        approved=approved,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )

    total = await conn.fetchval(
        "SELECT count(*) FROM shurfy s LEFT JOIN ulitsy street ON street.id=s.ulicaid"
        + where_sql,
        *values,
    )
    query_values = [*values, page_size, (page - 1) * page_size]
    rows = await conn.fetch(
        SHURF_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY COALESCE(s.data_nachala, s.data_nachala_plan) DESC NULLS LAST, s.id DESC
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


async def get_shurf_lookups(conn: asyncpg.Connection) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for response_key, table_name in (
        ("purposes", "naznachenie_vskr"),
        ("states", "sostoyanie_shurfa"),
        ("materials", "materialy_i_mekhanizmy"),
    ):
        rows = await conn.fetch(
            f"SELECT id, name FROM {table_name} ORDER BY COALESCE(ord, id), id"
        )
        result[response_key] = [dict(row) for row in rows]
    return result


async def _get_shurf_relations(
    conn: asyncpg.Connection, shurf_id: int
) -> dict[str, list[dict[str, Any]]]:
    inspected = await conn.fetch(
        """
            SELECT DISTINCT lookup.id, lookup.name
            FROM vidy_elementov_for_shurfy relation
            JOIN vidy_elementov_shurf lookup ON lookup.id=relation.activityid
            WHERE relation.objid=$1
            ORDER BY lookup.name
        """,
        shurf_id,
    )
    communications = await conn.fetch(
        """
            SELECT DISTINCT lookup.id, lookup.name
            FROM nalichie_vblizi_kommunikacij_for_shurfy relation
            JOIN nalichie_vblizi_kommunikacij lookup ON lookup.id=relation.activityid
            WHERE relation.objid=$1
            ORDER BY lookup.name
        """,
        shurf_id,
    )
    defects = await conn.fetch(
        """
            SELECT
                d.id,
                d.data_osmotra AS detected_at,
                d.defectdescription AS description,
                source.name AS source_name,
                state.name AS state_name
            FROM defectsforshurfy relation
            JOIN defect d ON d.id=relation.defectid
            LEFT JOIN defecttypes source ON source.id=d.remonttypeid
            LEFT JOIN statedefect state ON state.id=d.stateid
            WHERE relation.objid=$1
            ORDER BY d.data_osmotra DESC NULLS LAST, d.id DESC
        """,
        shurf_id,
    )
    documents = await conn.fetch(
        """
            SELECT
                document.id,
                document.date_doc,
                document.path,
                document.remontdocumenttypeid AS document_type_id,
                document_type.name AS document_type_name
            FROM shurfdocuments document
            LEFT JOIN remontdocumenttypes document_type
              ON document_type.id=document.remontdocumenttypeid
            WHERE document.objid=$1
            ORDER BY document.date_doc DESC NULLS LAST, document.id DESC
        """,
        shurf_id,
    )
    risk_factors = await conn.fetch(
        """
            SELECT
                risk.id,
                risk.lineid AS pipe_section_id,
                ground.name AS ground_name,
                surface.name AS surface_name,
                communications.name AS nearby_communications_name,
                risk.podtoplenie_do_truby,
                risk.elektrich,
                risk.transportelekricht,
                risk.ponezial,
                risk.vnesnkorrozia,
                risk.vnunrenkorrozia,
                risk.tol1,
                risk.tol2,
                risk.glubina_kor,
                risk.razmery_kor
            FROM faktory_riska_truboprovoda risk
            LEFT JOIN harakter_grunta_shurf ground ON ground.id=risk.harakter_gruntaid
            LEFT JOIN poverhnost_nad_trassoj surface ON surface.id=risk.poverhnost_nad_trassojid
            LEFT JOIN nalichie_vblizi_kommunikacij communications
              ON communications.id=risk.nalichie_vblizi_kommunikacijid
            WHERE risk.objid=$1 AND risk.obj_type_faktory_riskaid=1
            ORDER BY risk.id
        """,
        shurf_id,
    )
    return {
        "inspected_elements": [dict(row) for row in inspected],
        "nearby_communications": [dict(row) for row in communications],
        "defects": [dict(row) for row in defects],
        "documents": [dict(row) for row in documents],
        "risk_factors": [dict(row) for row in risk_factors],
    }


async def get_shurf(conn: asyncpg.Connection, shurf_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        SHURF_SUMMARY_SELECT.replace(
            "s.id,",
            """s.id,
        s.rasstoyanie_do_blizhajshej_kamery AS distance_to_nearest_chamber,
        s.dlina_osmotra AS inspection_length,
        s.glubina_zalozheniya AS laying_depth,
        s.podtoplenie_do_truby,
        s.rasstoyanie_do_relsov AS distance_to_rails,
        s.nalichie_vblizi_elektrificirovannogo_transporta AS nearby_electric_transport,
        s.nalichie_vblizi_rabotayushchih_elektrozashchitnyh_ustanovokid AS nearby_electroprotection,
        s.mesto_kontrolnoj_vyrezki_truboprovoda AS control_cut_location,
        s.rezultaty_vyrezki AS cut_results,
        s.meropriyatiya_po_vosstanovleniyu_prokladki AS restoration_measures,
        s.data_utverzhdenija_akta AS act_approved_on,
        s.naznachenie AS approval_purpose,
        s.fio_utverzhdaemogo AS approver_name,
        s.fio_viziruemogo_1 AS reviewer_name,
        s.fio_1 AS commission_member_1,
        s.fio_2 AS commission_member_2,
        ground.name AS ground_name,
        drainage.name AS drainage_name,
        surface.name AS surface_name,
        nearby_communication.name AS nearby_communication_name,
        nearest_chamber.id AS nearest_chamber_id,
        COALESCE(NULLIF(nearest_chamber.nodename, ''), nearest_chamber.externalnodename) AS nearest_chamber_name,
        waterproof_flow.name AS waterproof_flow_name,
        waterproof_return.name AS waterproof_return_name,
        anticorrosion_flow.name AS anticorrosion_flow_name,
        anticorrosion_return.name AS anticorrosion_return_name,
        corrosion_flow.name AS corrosion_flow_name,
        corrosion_return.name AS corrosion_return_name,
        channel_structure.name AS channel_structure_name,
        channel_structure_state.name AS channel_structure_state_name,
        channel_inside.name AS channel_inside_name,
        drain_structure.name AS drain_structure_name,
        insulation_flow.name AS insulation_flow_name,
        insulation_return.name AS insulation_return_name,
        outer_cover_flow.name AS outer_cover_flow_name,
        outer_cover_return.name AS outer_cover_return_name,
        ground_fill.name AS ground_fill_name,
        approver_position.znachenie AS approver_position,
        approver_service.name AS approver_service,
        reviewer_position.znachenie AS reviewer_position,""",
            1,
        )
        + """
        LEFT JOIN harakter_grunta_shurf ground ON ground.id=s.harakter_gruntaid
        LEFT JOIN ustrojstva_vodootvedeniya drainage ON drainage.id=s.ustrojstva_vodootvedeniyaid
        LEFT JOIN poverhnost_nad_trassoj surface ON surface.id=s.poverhnost_nad_trassojid
        LEFT JOIN nalichie_vblizi_kommunikacij nearby_communication
          ON nearby_communication.id=s.nalichie_vblizi_kommunikacijid
        LEFT JOIN nodes nearest_chamber ON nearest_chamber.id=s.nodeid_bizhajshej_kamery
        LEFT JOIN gidroizolyacionnaya_konstrukciya waterproof_flow
          ON waterproof_flow.id=s.gidroizolyacionnaya_konstrukciya_podachaid
        LEFT JOIN gidroizolyacionnaya_konstrukciya waterproof_return
          ON waterproof_return.id=s.gidroizolyacionnaya_konstrukciya_obratkaid
        LEFT JOIN sostoyanie_protivokorrozionnogo_pokrytiya_shurf anticorrosion_flow
          ON anticorrosion_flow.id=s.sostoyanie_protivokorrozionnogo_pokrytiya_podachaid
        LEFT JOIN sostoyanie_protivokorrozionnogo_pokrytiya_shurf anticorrosion_return
          ON anticorrosion_return.id=s.sostoyanie_protivokorrozionnogo_pokrytiya_obratkaid
        LEFT JOIN nalichie_korrozii_shurf corrosion_flow
          ON corrosion_flow.id=s.nalichie_korrozii_podachaid
        LEFT JOIN nalichie_korrozii_shurf corrosion_return
          ON corrosion_return.id=s.nalichie_korrozii_obratkaid
        LEFT JOIN stroitelnye_konstrukcii_kanala channel_structure
          ON channel_structure.id=s.stroitelnye_konstrukcii_kanalaid
        LEFT JOIN sostoyanie_stroitelnyh_konstrukcij_kanala channel_structure_state
          ON channel_structure_state.id=s.sostoyanie_stroitelnyh_konstrukcij_kanalaid
        LEFT JOIN vnutrennee_sostoyanie_kanala channel_inside
          ON channel_inside.id=s.vnutrennee_sostoyanie_kanalaid
        LEFT JOIN konstrukciya_drenazhnogo_ustrojstva drain_structure
          ON drain_structure.id=s.konstrukciya_drenazhnogo_ustrojstvaid
        LEFT JOIN sostoyanie_teplovoj_izolyacii insulation_flow
          ON insulation_flow.id=s.sostoyanie_teplovoj_izolyacii_podachaid
        LEFT JOIN sostoyanie_teplovoj_izolyacii insulation_return
          ON insulation_return.id=s.sostoyanie_teplovoj_izolyacii_obratkaid
        LEFT JOIN sostoyanie_naruzhnogo_pokrytiya outer_cover_flow
          ON outer_cover_flow.id=s.sostoyanie_naruzhnogo_pokrytiya_podachaid
        LEFT JOIN sostoyanie_naruzhnogo_pokrytiya outer_cover_return
          ON outer_cover_return.id=s.sostoyanie_naruzhnogo_pokrytiya_obratkaid
        LEFT JOIN zanos_kanala_gruntom ground_fill ON ground_fill.id=s.zanos_kanala_gruntomid
        LEFT JOIN dolzhnosti approver_position ON approver_position.id=s.dolzhnost_utverzhdaemogoid
        LEFT JOIN subdivisions approver_service ON approver_service.id=s.sluzhba_utverzhdaemogoid
        LEFT JOIN dolzhnosti reviewer_position ON reviewer_position.id=s.dolzhnost_viziruemogoid_1
        WHERE s.id=$1
        """,
        shurf_id,
    )
    if row is None:
        return None
    result = dict(row)
    result["relations"] = await _get_shurf_relations(conn, shurf_id)
    return result
