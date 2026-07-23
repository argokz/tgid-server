from datetime import date
from typing import Any, Optional

import asyncpg


CORROSION_FROM = """
    FROM indikator_korrozii indicator
    LEFT JOIN LATERAL (
        SELECT history.*
          FROM indikator_korrozii_po_godam history
         WHERE history.id_i=indicator.id
         ORDER BY COALESCE(history.data_izvlecheniya, history.data_ustanovki,
                           history.data_planirovaniya) DESC NULLS LAST,
                  history.id DESC
         LIMIT 1
    ) latest ON TRUE
    LEFT JOIN stateindicator phase ON phase.id=COALESCE(latest.sostoyanie, indicator.sostoyanie)
    LEFT JOIN stateinds rod_state ON rod_state.id=COALESCE(latest.stateindid, indicator.stateindid)
    LEFT JOIN corrosionprocessmarks process_mark
      ON process_mark.id=COALESCE(latest.otsenka_korrozionnogo_protsessa,
                                  indicator.otsenka_korrozionnogo_protsessa)
    LEFT JOIN netwateraggressivenesses water
      ON water.id=COALESCE(latest.agressivnost_setevoy_vody,
                           indicator.agressivnost_setevoy_vody)
    LEFT JOIN coolanttypes coolant ON coolant.id=indicator.teplonositel
    LEFT JOIN externalsignline pipeline_sign ON pipeline_sign.id=indicator.truboprovod
    LEFT JOIN responsibles_korrozia responsible ON responsible.id=indicator.responsibleid
    LEFT JOIN dolzhnosti_korrozia position ON position.id=indicator.dolzhnostid
    LEFT JOIN linesobj line ON line.id=indicator.lineid
    LEFT JOIN nodes linked_node ON linked_node.id=indicator.nodeid
    LEFT JOIN nodes start_node ON start_node.id=line.nodeid1
    LEFT JOIN nodes end_node ON end_node.id=line.nodeid2
    LEFT JOIN LATERAL (
        SELECT pipe.* FROM heatpipesections pipe
         WHERE pipe.lineid=line.id ORDER BY pipe.id LIMIT 1
    ) pipe ON TRUE
    LEFT JOIN LATERAL (
        SELECT count(*)::int AS count
          FROM indikator_korrozii_po_godam history_count
         WHERE history_count.id_i=indicator.id
    ) history_stats ON TRUE
"""


CORROSION_SUMMARY_SELECT = """
    SELECT
        indicator.id,
        indicator.nomer_indikatora_korrozii AS number,
        COALESCE(latest.sostoyanie, indicator.sostoyanie) AS phase_id,
        phase.name AS phase_name,
        COALESCE(latest.stateindid, indicator.stateindid) AS rod_state_id,
        rod_state.name AS rod_state_name,
        COALESCE(latest.data_planirovaniya, indicator.data_planirovaniya) AS planned_on,
        COALESCE(latest.data_ustanovki, indicator.data_ustanovki) AS installed_on,
        COALESCE(latest.data_izvlecheniya, indicator.data_izvlecheniya) AS extracted_on,
        indicator.mesto_ustanovki AS installation_place,
        concat_ws(', ', NULLIF(indicator.ulitsa, ''), NULLIF(indicator.nomer_doma, '')) AS address,
        indicator.istochnik_tepla AS heat_source_name,
        indicator.uchastok_ekspluatatsii AS operation_site_name,
        indicator.magistral_raspredset AS network_name,
        indicator.nachalnik_uchastka AS site_manager_name,
        indicator.lineid AS line_id,
        indicator.nodeid AS node_id,
        line.nodeid1 AS start_node_id,
        line.nodeid2 AS end_node_id,
        COALESCE(NULLIF(start_node.nodename, ''), start_node.externalnodename) AS start_node_name,
        COALESCE(NULLIF(end_node.nodename, ''), end_node.externalnodename) AS end_node_name,
        COALESCE(NULLIF(linked_node.nodename, ''), linked_node.externalnodename) AS linked_node_name,
        pipe.id AS heat_pipe_section_id,
        pipe.pipesectionid AS legacy_pipe_section_id,
        pipe.diametercondit AS diameter,
        pipeline_sign.id AS pipeline_sign_id,
        pipeline_sign.name AS pipeline_sign_name,
        coolant.id AS coolant_type_id,
        coolant.name AS coolant_type_name,
        responsible.id AS responsible_id,
        responsible.name AS responsible_name,
        position.id AS position_id,
        position.znachenie AS position_name,
        COALESCE(latest.srednyaya_skorost_korrozii__mm_god,
                 indicator.srednyaya_skorost_korrozii__mm_god) AS corrosion_rate,
        COALESCE(latest.otsenka_korrozionnogo_protsessa,
                 indicator.otsenka_korrozionnogo_protsessa) AS process_mark_id,
        process_mark.name AS process_mark_name,
        COALESCE(latest.agressivnost_setevoy_vody,
                 indicator.agressivnost_setevoy_vody) AS water_aggressiveness_id,
        water.name AS water_aggressiveness_name,
        COALESCE(latest.primechanie, indicator.primechanie) AS note,
        COALESCE(history_stats.count, 0) AS history_count,
        CASE
          WHEN indicator.shape IS NOT NULL THEN ST_X(ST_Transform(ST_PointOnSurface(indicator.shape), 4326))
          WHEN linked_node.shape IS NOT NULL THEN ST_X(ST_Transform(linked_node.shape, 4326))
          WHEN line.shape IS NOT NULL THEN ST_X(ST_Centroid(ST_Transform(line.shape, 4326)))
        END AS longitude,
        CASE
          WHEN indicator.shape IS NOT NULL THEN ST_Y(ST_Transform(ST_PointOnSurface(indicator.shape), 4326))
          WHEN linked_node.shape IS NOT NULL THEN ST_Y(ST_Transform(linked_node.shape, 4326))
          WHEN line.shape IS NOT NULL THEN ST_Y(ST_Centroid(ST_Transform(line.shape, 4326)))
        END AS latitude
""" + CORROSION_FROM


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    phase_id: Optional[int],
    rod_state_id: Optional[int],
    process_mark_id: Optional[int],
    water_aggressiveness_id: Optional[int],
    season_year: Optional[int],
    date_from: Optional[date],
    date_to: Optional[date],
    line_id: Optional[int],
    node_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if phase_id is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(latest.sostoyanie, indicator.sostoyanie)={param}",
            phase_id,
        )
    if rod_state_id is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(latest.stateindid, indicator.stateindid)={param}",
            rod_state_id,
        )
    if process_mark_id is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(latest.otsenka_korrozionnogo_protsessa, indicator.otsenka_korrozionnogo_protsessa)={param}",
            process_mark_id,
        )
    if water_aggressiveness_id is not None:
        _add_filter(
            clauses,
            values,
            "COALESCE(latest.agressivnost_setevoy_vody, indicator.agressivnost_setevoy_vody)={param}",
            water_aggressiveness_id,
        )
    if season_year is not None:
        _add_filter(
            clauses,
            values,
            """(
              EXTRACT(YEAR FROM COALESCE(indicator.data_ustanovki, indicator.data_planirovaniya))::int = {param}
              OR EXISTS (
                SELECT 1 FROM indikator_korrozii_po_godam season
                 WHERE season.id_i=indicator.id
                   AND EXTRACT(YEAR FROM COALESCE(season.data_ustanovki, season.data_planirovaniya))::int = {param}
              )
            )""",
            season_year,
        )
    effective_date = "COALESCE(latest.data_ustanovki, latest.data_planirovaniya, indicator.data_ustanovki, indicator.data_planirovaniya)"
    if date_from is not None:
        _add_filter(clauses, values, f"{effective_date}>={{param}}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, f"{effective_date}<={{param}}", date_to)
    if line_id is not None:
        _add_filter(clauses, values, "indicator.lineid={param}", line_id)
    if node_id is not None:
        _add_filter(
            clauses,
            values,
            "(indicator.nodeid={param} OR line.nodeid1={param} OR line.nodeid2={param})",
            node_id,
        )
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
              indicator.id::text={param}
              OR COALESCE(indicator.nomer_indikatora_korrozii, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.mesto_ustanovki, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.ulitsa, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.nomer_doma, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.istochnik_tepla, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.uchastok_ekspluatatsii, '') ILIKE '%' || {param} || '%'
              OR COALESCE(responsible.name, '') ILIKE '%' || {param} || '%'
              OR COALESCE(indicator.primechanie, '') ILIKE '%' || {param} || '%'
              OR COALESCE(latest.primechanie, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_corrosion_indicators(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    phase_id: Optional[int] = None,
    rod_state_id: Optional[int] = None,
    process_mark_id: Optional[int] = None,
    water_aggressiveness_id: Optional[int] = None,
    season_year: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = None,
    node_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        phase_id=phase_id,
        rod_state_id=rod_state_id,
        process_mark_id=process_mark_id,
        water_aggressiveness_id=water_aggressiveness_id,
        season_year=season_year,
        date_from=date_from,
        date_to=date_to,
        line_id=line_id,
        node_id=node_id,
        search=search,
    )
    total = await conn.fetchval(
        "SELECT count(DISTINCT indicator.id) " + CORROSION_FROM + where_sql,
        *values,
    )
    rows = await conn.fetch(
        CORROSION_SUMMARY_SELECT
        + where_sql
        + f"""
          ORDER BY COALESCE(latest.data_ustanovki, latest.data_planirovaniya,
                            indicator.data_ustanovki, indicator.data_planirovaniya)
                   DESC NULLS LAST,
                   indicator.id DESC
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


async def get_corrosion_indicator_lookups(
    conn: asyncpg.Connection,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for key, table, name_column in (
        ("phases", "stateindicator", "name"),
        ("rod_states", "stateinds", "name"),
        ("process_marks", "corrosionprocessmarks", "name"),
        ("water_aggressiveness", "netwateraggressivenesses", "name"),
        ("coolant_types", "coolanttypes", "name"),
        ("pipeline_signs", "externalsignline", "name"),
        ("responsible_people", "responsibles_korrozia", "name"),
    ):
        rows = await conn.fetch(
            f"SELECT id, {name_column} AS name FROM {table} ORDER BY id"
        )
        result[key] = [dict(row) for row in rows]
    years = await conn.fetch(
        """SELECT value, count(*)::int AS count FROM (
             SELECT EXTRACT(YEAR FROM COALESCE(data_ustanovki, data_planirovaniya))::int AS value
               FROM indikator_korrozii
             UNION ALL
             SELECT EXTRACT(YEAR FROM COALESCE(data_ustanovki, data_planirovaniya))::int AS value
               FROM indikator_korrozii_po_godam
           ) seasons WHERE value IS NOT NULL GROUP BY value ORDER BY value DESC"""
    )
    result["years"] = [dict(row) for row in years]
    return result


DETAIL_SELECT = """
    SELECT
      indicator.kod_rs_nachalnoy_kamery AS start_chamber_code,
      indicator.nachalnaya_kamera AS start_chamber_name,
      indicator.kod_rs_konechnoy_kamery AS end_chamber_code,
      indicator.konechnaya_kamera AS end_chamber_name,
      indicator.kod_rs_blizhayshey_kamery AS nearest_chamber_code,
      indicator.blizhayshaya_kamera AS nearest_chamber_name,
      indicator.rasstoyanie_do_kamery__m AS chamber_distance,
      indicator.god_vvoda_v_ekspluatatsiyu AS commissioned_on,
      indicator.vid_prokladki AS tubing_type_id,
      tubing.name AS tubing_type_name,
      indicator.diametr_truby_podayuschiy__uslovn__mm AS flow_diameter,
      indicator.diametr_truby_obratnyy__uslovn__mm AS return_diameter,
      COALESCE(latest.kolichestvo_plastin_v_sborke,
               indicator.kolichestvo_plastin_v_sborke) AS plate_count,
      COALESCE(latest.sredniy_ves_plastiny_pri_ustanovke__g,
               indicator.sredniy_ves_plastiny_pri_ustanovke__g) AS initial_plate_weight,
      COALESCE(latest.radius_krugloy_plastiny__mm,
               indicator.radius_krugloy_plastiny__mm) AS plate_radius,
      COALESCE(latest.radius_vtulki__mm, indicator.radius_vtulki__mm) AS bush_radius,
      COALESCE(latest.tolschina_plastiny__mm,
               indicator.tolschina_plastiny__mm) AS plate_thickness,
      COALESCE(latest.sredniy_ves_plastiny_posle_ispytaniy__g,
               indicator.sredniy_ves_plastiny_posle_ispytaniy__g) AS final_plate_weight,
      COALESCE(latest.poterya_massy_srednyaya_pri_kislotnoy_obraboke__g,
               indicator.poterya_massy_srednyaya_pri_kislotnoy_obraboke__g) AS acid_treatment_mass_loss,
      COALESCE(latest.vneshniy_vid_plastin,
               indicator.vneshniy_vid_plastin) AS plate_external_view,
      indicator.regimid AS mode_id
    FROM indikator_korrozii indicator
    LEFT JOIN LATERAL (
      SELECT history.* FROM indikator_korrozii_po_godam history
       WHERE history.id_i=indicator.id
       ORDER BY COALESCE(history.data_izvlecheniya, history.data_ustanovki,
                         history.data_planirovaniya) DESC NULLS LAST,
                history.id DESC LIMIT 1
    ) latest ON TRUE
    LEFT JOIN tubingtypes tubing ON tubing.id=indicator.vid_prokladki
    WHERE indicator.id=$1
"""


async def get_corrosion_indicator(
    conn: asyncpg.Connection, indicator_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        CORROSION_SUMMARY_SELECT + " WHERE indicator.id=$1", indicator_id
    )
    if summary is None:
        return None
    detail = await conn.fetchrow(DETAIL_SELECT, indicator_id)
    history = await conn.fetch(
        """
          SELECT
            history.id, history.id_i AS indicator_id,
            history.sostoyanie AS phase_id, phase.name AS phase_name,
            history.tekuschiy_nomer AS current_number,
            history.nomer_indikatora_korrozii AS number,
            history.truboprovod AS pipeline_sign,
            history.data_planirovaniya AS planned_on,
            history.data_ustanovki AS installed_on,
            history.data_izvlecheniya AS extracted_on,
            history.kolichestvo_dney_ispytaniy AS exposure_days,
            history.kolichestvo_plastin_v_sborke AS plate_count,
            history.sredniy_ves_plastiny_pri_ustanovke__g AS initial_plate_weight,
            history.radius_krugloy_plastiny__mm AS plate_radius,
            history.radius_vtulki__mm AS bush_radius,
            history.tolschina_plastiny__mm AS plate_thickness,
            history.stateindid AS rod_state_id, rod_state.name AS rod_state_name,
            history.sredniy_ves_plastiny_posle_ispytaniy__g AS final_plate_weight,
            history.poterya_massy_srednyaya_pri_kislotnoy_obraboke__g AS acid_treatment_mass_loss,
            history.srednyaya_skorost_korrozii__mm_god AS corrosion_rate,
            history.otsenka_korrozionnogo_protsessa AS process_mark_id,
            process_mark.name AS process_mark_name,
            history.agressivnost_setevoy_vody AS water_aggressiveness_id,
            water.name AS water_aggressiveness_name,
            history.vneshniy_vid_plastin AS plate_external_view,
            history.primechanie AS note
          FROM indikator_korrozii_po_godam history
          LEFT JOIN stateindicator phase ON phase.id=history.sostoyanie
          LEFT JOIN stateinds rod_state ON rod_state.id=history.stateindid
          LEFT JOIN corrosionprocessmarks process_mark
            ON process_mark.id=history.otsenka_korrozionnogo_protsessa
          LEFT JOIN netwateraggressivenesses water
            ON water.id=history.agressivnost_setevoy_vody
          WHERE history.id_i=$1
          ORDER BY COALESCE(history.data_izvlecheniya, history.data_ustanovki,
                            history.data_planirovaniya) DESC NULLS LAST,
                   history.id DESC
        """,
        indicator_id,
    )
    result = dict(summary)
    if detail:
        result.update(dict(detail))
    result["relations"] = {"history": [dict(row) for row in history]}
    return result

async def get_corrosion_indicators_geojson(conn: asyncpg.Connection) -> dict[str, Any]:
    rows = await conn.fetch("""
        SELECT
            d.id,
            -- В indikator_korrozii нет колонки name: подпись собираем из номера
            -- индикатора и места установки (см. legacy-модель gid6)
            COALESCE(
                NULLIF(d.nomer_indikatora_korrozii, ''),
                NULLIF(d.mesto_ustanovki, ''),
                'Индикатор ' || d.id::text
            ) AS label,
            ST_AsGeoJSON(ST_Transform(d.shape, 4326)) AS geometry
        FROM indikator_korrozii d
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
                "label": row["label"] or "",
                "type": "corrosion"
            }
        })
        
    return {
        "type": "FeatureCollection",
        "features": features
    }

