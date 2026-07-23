from datetime import date
from typing import Any, Optional

import asyncpg


REPAIR_SUMMARY_SELECT = """
    SELECT
        repair.id,
        repair.otchet_po_defektu AS name,
        repair.stateid AS state_id,
        state.name AS state_name,
        repair.remonttypeid AS repair_type_id,
        repair_type.name AS repair_type_name,
        repair.remontcatid AS category_id,
        category.name AS category_name,
        repair.utverdit AS approval_id,
        CASE WHEN COALESCE(repair.utverdit, 0)=0 THEN 'Не утверждено' ELSE 'Утверждено' END AS approval_name,
        repair.data_nachala_plan AS planned_start,
        repair.data_okonchaniya_plan AS planned_finish,
        repair.data_utverzhdeniya_plana AS plan_approved_on,
        repair.data_nachala_remonta AS actual_start,
        repair.data_zaversheniya_remonta AS actual_finish,
        COALESCE(repair.data_nachala_remonta, repair.data_nachala_plan, repair.data_osmotra::date) AS effective_start,
        COALESCE(repair.data_zaversheniya_remonta, repair.data_okonchaniya_plan) AS effective_finish,
        repair.harakteristika_uchastkov_remontiruemoj_teplovoj_seti AS section_characteristics,
        repair.opisanie_rabot AS work_description,
        repair.harakteristika_rabot AS work_characteristics,
        repair.rezultaty_remonta AS results,
        repair.primechanie AS note,
        repair.responsibleid AS responsible_id,
        responsible.fio AS responsible_name,
        repair.subdivisionid AS subdivision_id,
        subdivision.name AS subdivision_name,
        repair.teplovaya_setid AS network_type_id,
        CASE repair.teplovaya_setid WHEN 1 THEN 'Магистральная сеть'
          WHEN 2 THEN 'Внутриквартальная сеть' END AS network_type_name,
        repair.len_tube_plan AS planned_pipe_length,
        repair.len_tube_cur AS actual_pipe_length,
        repair.vydelennye_sredstva_plan AS planned_budget,
        repair.vydelennye_sredstva AS actual_budget,
        COALESCE(deployed.line_count, 0) AS line_count,
        COALESCE(risks.risk_count, 0) AS work_section_count,
        COALESCE(defects.defect_count, 0) AS defect_count,
        deployed.longitude,
        deployed.latitude
    FROM remont2 repair
    LEFT JOIN stateremont2 state ON state.id=repair.stateid
    LEFT JOIN remonttypes repair_type ON repair_type.id=repair.remonttypeid
    LEFT JOIN remontcat category ON category.id=repair.remontcatid
    LEFT JOIN nachalniki_uchastkov responsible ON responsible.id=repair.responsibleid
    LEFT JOIN subdivisions subdivision ON subdivision.id=repair.subdivisionid
    LEFT JOIN LATERAL (
        SELECT
            count(DISTINCT relation.lineid)::int AS line_count,
            ST_X(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS longitude,
            ST_Y(ST_Centroid(ST_Collect(ST_Transform(line.shape, 4326)))) AS latitude
        FROM remont2deployed relation
        LEFT JOIN linesobj line ON line.id=relation.lineid
        WHERE relation.directionid=repair.id
    ) deployed ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS risk_count
        FROM faktory_riska_truboprovoda risk
        WHERE risk.objid=repair.id AND risk.obj_type_faktory_riskaid=3
    ) risks ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS defect_count
        FROM defect defect_item
        WHERE defect_item.remontid=repair.id
    ) defects ON TRUE
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    state_id: Optional[int],
    repair_type_id: Optional[int],
    category_id: Optional[int],
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
        _add_filter(clauses, values, "repair.stateid={param}", state_id)
    if repair_type_id is not None:
        _add_filter(clauses, values, "repair.remonttypeid={param}", repair_type_id)
    if category_id is not None:
        _add_filter(clauses, values, "repair.remontcatid={param}", category_id)
    if responsible_id is not None:
        _add_filter(clauses, values, "repair.responsibleid={param}", responsible_id)
    if approved is not None:
        clauses.append(
            "COALESCE(repair.utverdit, 0)<>0" if approved else "COALESCE(repair.utverdit, 0)=0"
        )
    date_expression = "COALESCE(repair.data_nachala_remonta, repair.data_nachala_plan, repair.data_osmotra::date)"
    if date_from is not None:
        _add_filter(clauses, values, f"{date_expression}>={{param}}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, f"{date_expression}<={{param}}", date_to)
    if line_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1 FROM remont2deployed relation
                WHERE relation.directionid=repair.id AND relation.lineid={param}
            )""",
            line_id,
        )
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            """EXISTS (
                SELECT 1 FROM remont2deployed relation
                JOIN linesobj line ON line.id=relation.lineid
                WHERE relation.directionid=repair.id AND line.removed=0
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
                repair.id::text={param}
                OR COALESCE(repair.otchet_po_defektu, '') ILIKE '%' || {param} || '%'
                OR COALESCE(repair.harakteristika_uchastkov_remontiruemoj_teplovoj_seti, '') ILIKE '%' || {param} || '%'
                OR COALESCE(repair.opisanie_rabot, '') ILIKE '%' || {param} || '%'
                OR COALESCE(repair.harakteristika_rabot, '') ILIKE '%' || {param} || '%'
                OR COALESCE(repair.rezultaty_remonta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(repair.nomer_prikaza, '') ILIKE '%' || {param} || '%'
                OR COALESCE(responsible.fio, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_repairs(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    state_id: Optional[int] = None,
    repair_type_id: Optional[int] = None,
    category_id: Optional[int] = None,
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
        repair_type_id=repair_type_id,
        category_id=category_id,
        responsible_id=responsible_id,
        approved=approved,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )
    total = await conn.fetchval(
        """SELECT count(*) FROM remont2 repair
           LEFT JOIN nachalniki_uchastkov responsible ON responsible.id=repair.responsibleid"""
        + where_sql,
        *values,
    )
    query_values = [*values, page_size, (page - 1) * page_size]
    rows = await conn.fetch(
        REPAIR_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY COALESCE(repair.data_nachala_remonta, repair.data_nachala_plan, repair.data_osmotra::date)
              DESC NULLS LAST, repair.id DESC
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


async def get_repair_lookups(conn: asyncpg.Connection) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for key, table in (
        ("states", "stateremont2"),
        ("repair_types", "remonttypes"),
        ("categories", "remontcat"),
        ("subdivisions", "subdivisions"),
        ("document_types", "remontdocumenttypes"),
    ):
        rows = await conn.fetch(f"SELECT id, name FROM {table} ORDER BY COALESCE(ord, id), id")
        result[key] = [dict(row) for row in rows]
    responsible = await conn.fetch(
        "SELECT id, fio AS name FROM nachalniki_uchastkov ORDER BY fio, id"
    )
    result["responsible_people"] = [dict(row) for row in responsible]
    return result


async def _get_repair_relations(
    conn: asyncpg.Connection, repair_id: int
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
                CASE WHEN line.shape IS NULL THEN NULL ELSE ST_X(ST_Centroid(ST_Transform(line.shape, 4326))) END AS longitude,
                CASE WHEN line.shape IS NULL THEN NULL ELSE ST_Y(ST_Centroid(ST_Transform(line.shape, 4326))) END AS latitude
            FROM remont2deployed relation
            LEFT JOIN linesobj line ON line.id=relation.lineid
            LEFT JOIN nodes start_node ON start_node.id=line.nodeid1
            LEFT JOIN nodes end_node ON end_node.id=line.nodeid2
            LEFT JOIN LATERAL (
                SELECT candidate.* FROM heatpipesections candidate
                WHERE candidate.lineid=line.id ORDER BY candidate.id LIMIT 1
            ) pipe ON TRUE
            LEFT JOIN tubingtypes tubing ON tubing.id=pipe.tubingtypeid
            WHERE relation.directionid=$1
            ORDER BY relation.id
        """,
        repair_id,
    )
    defects = await conn.fetch(
        """
            SELECT
                defect_item.id, defect_item.lineid AS line_id,
                defect_item.data_osmotra AS detected_at,
                defect_item.defectdescription AS description,
                source.name AS source_name, state.name AS state_name,
                CASE WHEN defect_item.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(defect_item.shape, 4326)) END AS longitude,
                CASE WHEN defect_item.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(defect_item.shape, 4326)) END AS latitude
            FROM defect defect_item
            LEFT JOIN defecttypes source ON source.id=defect_item.remonttypeid
            LEFT JOIN statedefect state ON state.id=defect_item.stateid
            WHERE defect_item.remontid=$1
            ORDER BY defect_item.data_osmotra DESC NULLS LAST, defect_item.id DESC
        """,
        repair_id,
    )
    documents = await conn.fetch(
        """
            SELECT document.id, document.date_doc, document.path,
                   document.remontdocumenttypeid AS document_type_id,
                   document_type.name AS document_type_name
            FROM remontdocuments document
            LEFT JOIN remontdocumenttypes document_type
              ON document_type.id=document.remontdocumenttypeid
            WHERE document.objid=$1
            ORDER BY document.date_doc DESC NULLS LAST, document.id DESC
        """,
        repair_id,
    )
    work_sections = await conn.fetch(
        """
            SELECT
                risk.id, risk.lineid AS legacy_pipe_section_id,
                tubing.name AS tubing_type_name,
                risk.diametercondit AS diameter,
                risk.diameterinternal AS internal_diameter,
                risk.diameterexternal AS external_diameter,
                risk.wallthickness AS wall_thickness,
                risk.len_tube AS pipe_length,
                risk.len_izol AS insulation_area,
                risk.len_channel AS channel_length,
                risk.asfaltirovanie AS asphalt_area,
                risk.zamena_kanala_procent AS channel_replacement_percent,
                risk.zamena_kompensatorov AS compensator_replacements,
                risk.rekonstrukciya_kamery_nachalnogo_uzla AS reconstruct_start_chamber,
                risk.rekonstrukciya_kamery_konechnogo_uzla AS reconstruct_end_chamber,
                risk.ustanovka_i_zamena_zadvizhek AS valve_replacements,
                ground.name AS ground_name,
                surface.name AS surface_name,
                communication.name AS nearby_communication_name,
                metal.name AS pipe_metal_state_name,
                corrosion_flow.name AS corrosion_flow_name,
                corrosion_return.name AS corrosion_return_name
            FROM faktory_riska_truboprovoda risk
            LEFT JOIN tubingtypes tubing ON tubing.id=risk.tubingtypeid
            LEFT JOIN harakter_grunta_shurf ground ON ground.id=risk.harakter_gruntaid
            LEFT JOIN poverhnost_nad_trassoj surface ON surface.id=risk.poverhnost_nad_trassojid
            LEFT JOIN nalichie_vblizi_kommunikacij communication
              ON communication.id=risk.nalichie_vblizi_kommunikacijid
            LEFT JOIN sostoyanie_metalla_truboprovoda metal
              ON metal.id=risk.sostoyanie_metalla_truboprovodaid
            LEFT JOIN nalichie_korrozii_shurf corrosion_flow
              ON corrosion_flow.id=risk.nalichie_korrozii_podachaid
            LEFT JOIN nalichie_korrozii_shurf corrosion_return
              ON corrosion_return.id=risk.nalichie_korrozii_obratkaid
            WHERE risk.objid=$1 AND risk.obj_type_faktory_riskaid=3
            ORDER BY risk.id
        """,
        repair_id,
    )
    work_items = await conn.fetch(
        """
            WITH target_ids AS (
                SELECT $1::int AS id
                UNION
                SELECT risk.id FROM faktory_riska_truboprovoda risk
                WHERE risk.objid=$1 AND risk.obj_type_faktory_riskaid=3
            ), items AS (
                SELECT 'Инвестиционный · трубопровод' category, type.name
                  FROM remontinvesttube relation JOIN remontinvesttubetypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Инвестиционный · канал', type.name
                  FROM remontinvestchannel relation JOIN remontinvestchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Инвестиционный · камера', type.name
                  FROM remontinvestkamera relation JOIN remontinvestchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Капитальный · трубопровод', type.name
                  FROM remontcapitaltube relation JOIN remontcapitaltubetypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Капитальный · канал', type.name
                  FROM remontcapitalchannel relation JOIN remontcapitalchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Капитальный · камера', type.name
                  FROM remontcapitalkamera relation JOIN remontcapitalchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Текущий · трубопровод', type.name
                  FROM remonttube relation JOIN remonttubetypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Текущий · канал', type.name
                  FROM remontchannel relation JOIN remontchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
                UNION SELECT 'Текущий · камера', type.name
                  FROM remontkamera relation JOIN remontchanneltypes type ON type.id=relation.activityid
                  WHERE relation.objid IN (SELECT id FROM target_ids)
            ) SELECT category, name FROM items ORDER BY category, name
        """,
        repair_id,
    )
    return {
        "lines": [dict(row) for row in lines],
        "defects": [dict(row) for row in defects],
        "documents": [dict(row) for row in documents],
        "work_sections": [dict(row) for row in work_sections],
        "work_items": [dict(row) for row in work_items],
    }


async def get_repair(conn: asyncpg.Connection, repair_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        REPAIR_SUMMARY_SELECT.replace(
            "repair.id,",
            """repair.id,
        repair.data_osmotra AS inspected_at,
        repair.vremya_osmotra AS inspected_time,
        repair.plan_flag,
        repair.transfer_flag,
        repair.len_izol_plan AS planned_insulation_area,
        repair.len_channel_plan AS planned_channel_length,
        repair.asfaltirovanie_plan AS planned_asphalt_area,
        repair.diametr_trub_plan AS planned_pipe_diameter,
        repair.remontnyj_personal_plan AS planned_personnel,
        repair.len_izol_cur AS actual_insulation_area,
        repair.len_channel_cur AS actual_channel_length,
        repair.asfaltirovanie AS actual_asphalt_area,
        repair.remontnyj_personal AS actual_personnel,
        repair.kolichestvo_otklyuchennyh_potrebitelej AS disconnected_consumers,
        repair.kolichestvo_nedootpushchennoj_teplovoj_energii AS undelivered_heat,
        repair.nomer_prikaza AS commissioning_order_number,
        repair.data_prikaza_vvoda_v_ekspluataciyu AS commissioning_order_date,
        repair.prikaz_vvoda_v_ekspluataciyu AS commissioning_order_file,""",
            1,
        )
        + " WHERE repair.id=$1",
        repair_id,
    )
    if row is None:
        return None
    result = dict(row)
    result["relations"] = await _get_repair_relations(conn, repair_id)
    return result
