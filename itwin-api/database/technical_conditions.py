from datetime import date
from typing import Any, Optional

import asyncpg


TECHNICAL_CONDITION_SUMMARY_SELECT = """
    SELECT
        tu.id,
        tu.nomer_tu AS number,
        tu.data_vydachi_tu AS issued_on,
        tu.data_annulirovaniya AS annulled_on,
        tu.sostoyanie_dogovora AS state_id,
        state.name AS state_name,
        tu.naimenovanie_organizatsii__zaprashivayuschey_tu AS organization_name,
        tu.naimenovanie_obekta AS object_name,
        tu.adres_obekta AS address,
        tu.istochnik AS heat_source_name,
        tu.rayon_ekspluatatsii AS district_name,
        tu.teplovye_potoki__gkal_ch AS total_heat_load,
        tu.v_tom_chisle_otoplenie AS heating_load,
        tu.v_tom_chisle_ventilyatsiya AS ventilation_load,
        tu.v_tom_chisle_gvs_maks AS hot_water_max_load,
        tu.v_tom_chisle_gvs_sredn AS hot_water_average_load,
        tu.prirost_nagruzki AS load_increase,
        tu.nomer_dogovora AS contract_number,
        tu.data_dogovora AS contract_date,
        tu.nomer_vydachi_akta_dopuska AS admission_act_number,
        tu.data_vydachi_akta_dopuska AS admission_act_date,
        tu.zdanie AS building_id,
        tu.truba AS pipe_id,
        (building.id IS NOT NULL) AS building_link_valid,
        concat_ws(', ', NULLIF(building.gorod, ''), NULLIF(building.mikrorayon, ''),
            NULLIF(building.ulitsa, ''), NULLIF(building.dom, '')) AS building_address,
        CASE WHEN building.shape IS NULL THEN NULL
             ELSE ST_X(ST_Transform(ST_PointOnSurface(building.shape), 4326)) END AS longitude,
        CASE WHEN building.shape IS NULL THEN NULL
             ELSE ST_Y(ST_Transform(ST_PointOnSurface(building.shape), 4326)) END AS latitude
    FROM tehnicheskie_usloviya tu
    LEFT JOIN statetu state ON state.id=tu.sostoyanie_dogovora
    LEFT JOIN zdaniya_tu building ON building.id=tu.zdanie
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    state_id: Optional[int],
    issue_year: Optional[int],
    heat_source: Optional[str],
    district: Optional[str],
    linked: Optional[bool],
    date_from: Optional[date],
    date_to: Optional[date],
    building_id: Optional[int],
    pipe_id: Optional[int],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if state_id is not None:
        _add_filter(clauses, values, "tu.sostoyanie_dogovora={param}", state_id)
    if issue_year is not None:
        _add_filter(
            clauses,
            values,
            "EXTRACT(YEAR FROM tu.data_vydachi_tu)::int={param}",
            issue_year,
        )
    if heat_source:
        _add_filter(clauses, values, "tu.istochnik={param}", heat_source, "::text")
    if district:
        _add_filter(
            clauses, values, "tu.rayon_ekspluatatsii={param}", district, "::text"
        )
    if linked is not None:
        clauses.append(
            "tu.zdanie IS NOT NULL AND tu.zdanie<>0 AND building.id IS NOT NULL"
            if linked
            else "(tu.zdanie IS NULL OR tu.zdanie=0 OR building.id IS NULL)"
        )
    if date_from is not None:
        _add_filter(clauses, values, "tu.data_vydachi_tu>={param}", date_from)
    if date_to is not None:
        _add_filter(clauses, values, "tu.data_vydachi_tu<={param}", date_to)
    if building_id is not None:
        _add_filter(clauses, values, "tu.zdanie={param}", building_id)
    if pipe_id is not None:
        _add_filter(clauses, values, "tu.truba={param}", pipe_id)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                tu.id::text={param}
                OR COALESCE(tu.nomer_tu, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.naimenovanie_organizatsii__zaprashivayuschey_tu, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.naimenovanie_obekta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.adres_obekta, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.istochnik, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.rayon_ekspluatatsii, '') ILIKE '%' || {param} || '%'
                OR COALESCE(tu.nomer_dogovora, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_technical_conditions(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    state_id: Optional[int] = None,
    issue_year: Optional[int] = None,
    heat_source: Optional[str] = None,
    district: Optional[str] = None,
    linked: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    building_id: Optional[int] = None,
    pipe_id: Optional[int] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        state_id=state_id,
        issue_year=issue_year,
        heat_source=heat_source,
        district=district,
        linked=linked,
        date_from=date_from,
        date_to=date_to,
        building_id=building_id,
        pipe_id=pipe_id,
        search=search,
    )
    total = await conn.fetchval(
        """SELECT count(*)
             FROM tehnicheskie_usloviya tu
             LEFT JOIN zdaniya_tu building ON building.id=tu.zdanie"""
        + where_sql,
        *values,
    )
    rows = await conn.fetch(
        TECHNICAL_CONDITION_SUMMARY_SELECT
        + where_sql
        + f"""
            ORDER BY tu.data_vydachi_tu DESC NULLS LAST, tu.id DESC
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


async def get_technical_condition_lookups(
    conn: asyncpg.Connection,
) -> dict[str, list[dict[str, Any]]]:
    states = await conn.fetch(
        "SELECT id, name, code FROM statetu ORDER BY COALESCE(ord, id), id"
    )
    heat_sources = await conn.fetch(
        """SELECT istochnik AS name, count(*)::int AS count
             FROM tehnicheskie_usloviya
            WHERE NULLIF(BTRIM(istochnik), '') IS NOT NULL
            GROUP BY istochnik ORDER BY istochnik"""
    )
    districts = await conn.fetch(
        """SELECT rayon_ekspluatatsii AS name, count(*)::int AS count
             FROM tehnicheskie_usloviya
            WHERE NULLIF(BTRIM(rayon_ekspluatatsii), '') IS NOT NULL
            GROUP BY rayon_ekspluatatsii ORDER BY rayon_ekspluatatsii"""
    )
    years = await conn.fetch(
        """SELECT EXTRACT(YEAR FROM data_vydachi_tu)::int AS value, count(*)::int AS count
             FROM tehnicheskie_usloviya WHERE data_vydachi_tu IS NOT NULL
            GROUP BY 1 ORDER BY 1 DESC"""
    )
    return {
        "states": [dict(row) for row in states],
        "heat_sources": [dict(row) for row in heat_sources],
        "districts": [dict(row) for row in districts],
        "years": [dict(row) for row in years],
    }


DETAIL_FIELDS = """
    SELECT
        tu.kamera AS connection_chamber,
        tu.srok_deystviya_tu AS validity_period,
        tu.dopolnitelnye_tehnicheskie_meropriyatiya AS additional_measures,
        tu.v_tom_chisle_prirost_otoplenie AS heating_load_increase,
        tu.v_tom_chisle_prirost_ventilyatsiya AS ventilation_load_increase,
        tu.v_tom_chisle_prirost_gvs_maks AS hot_water_max_load_increase,
        tu.v_tom_chisle_prirost_gvs_sredn AS hot_water_average_load_increase,
        tu.nomer_soglasovaniya_ts AS network_approval_number,
        tu.data_soglasovaniya_ts AS network_approval_date,
        tu.nomer_soglasovaniya_ov AS heating_approval_number,
        tu.data_soglasovaniya_ov AS heating_approval_date,
        tu.nomer_soglasovaniya_tp AS project_approval_number,
        tu.data_soglasovaniya_tp AS project_approval_date,
        tu.ispolnenie_dop_tehn_i_energ_meropriyatiy_v_ramkah_tu AS measures_completion,
        tu.stadiya_stroitelstva_obektov AS construction_stage,
        tu.teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch AS admitted_total_heat_load,
        tu.v_tom_chisle_otoplenie_po_aktu AS admitted_heating_load,
        tu.v_tom_chisle_ventilyatsiya_po_aktu AS admitted_ventilation_load,
        tu.v_tom_chisle_gvs_maks_po_aktu AS admitted_hot_water_max_load,
        tu.v_tom_chisle_gvs_sredn_po_aktu AS admitted_hot_water_average_load,
        tu.dogovor AS contract_file,
        tu.akt AS admission_act_file,
        tu.kod1, tu.uzel1, tu.protsent_nagruzki_1,
        tu.kod2, tu.uzel2, tu.protsent_nagruzki_2,
        tu.kod3, tu.uzel3, tu.protsent_nagruzki_3,
        tu.kod4, tu.uzel4, tu.protsent_nagruzki_4,
        tu.kod5, tu.uzel5, tu.protsent_nagruzki_5,
        tu.tehnicheskie_usloviya,
        tu.tehnicheskie_usloviya_2, tu.tehnicheskie_usloviya_3,
        tu.tehnicheskie_usloviya_4, tu.tehnicheskie_usloviya_5,
        tu.tehnicheskie_usloviya_6, tu.tehnicheskie_usloviya_7,
        tu.tehnicheskie_usloviya_8, tu.tehnicheskie_usloviya_9,
        tu.tehnicheskie_usloviya_10,
        building.gorod AS building_city,
        building.mikrorayon AS building_microdistrict,
        building.ulitsa AS building_street,
        building.dom AS building_house,
        building.kommentariy AS building_note,
        building.kod_rs_uzla_prisoedineniya AS building_connection_code,
        building.uzel_prisoedineniya AS building_connection_node
""" + "".join(
    f""", tu.izmeneniya_prodleniya_{index}, tu.data_izmeneniya_prodleniya_{index},
        tu.teplovye_potoki__gkal_ch_{index}, tu.v_tom_chisle_otoplenie_{index},
        tu.v_tom_chisle_ventilyatsiya_{index}, tu.v_tom_chisle_gvs_maks_{index},
        tu.v_tom_chisle_gvs_sredn_{index}, tu.prirost_nagruzki_{index},
        tu.v_tom_chisle_prirost_otoplenie_{index},
        tu.v_tom_chisle_prirost_ventilyatsiya_{index},
        tu.v_tom_chisle_prirost_gvs_maks_{index},
        tu.v_tom_chisle_prirost_gvs_sredn_{index},
        tu.dopolnitelnye_tehnicheskie_meropriyatiya_{index}"""
    for index in range(1, 8)
)


def _extract_relations(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    extensions: list[dict[str, Any]] = []
    for index in range(1, 8):
        prefix_fields = {
            "description": f"izmeneniya_prodleniya_{index}",
            "changed_on": f"data_izmeneniya_prodleniya_{index}",
            "total_heat_load": f"teplovye_potoki__gkal_ch_{index}",
            "heating_load": f"v_tom_chisle_otoplenie_{index}",
            "ventilation_load": f"v_tom_chisle_ventilyatsiya_{index}",
            "hot_water_max_load": f"v_tom_chisle_gvs_maks_{index}",
            "hot_water_average_load": f"v_tom_chisle_gvs_sredn_{index}",
            "load_increase": f"prirost_nagruzki_{index}",
            "heating_load_increase": f"v_tom_chisle_prirost_otoplenie_{index}",
            "ventilation_load_increase": f"v_tom_chisle_prirost_ventilyatsiya_{index}",
            "hot_water_max_load_increase": f"v_tom_chisle_prirost_gvs_maks_{index}",
            "hot_water_average_load_increase": f"v_tom_chisle_prirost_gvs_sredn_{index}",
            "additional_measures": f"dopolnitelnye_tehnicheskie_meropriyatiya_{index}",
        }
        extension = {"index": index}
        for target, source in prefix_fields.items():
            extension[target] = result.pop(source, None)
        if any(value not in (None, "") for key, value in extension.items() if key != "index"):
            extensions.append(extension)

    documents: list[dict[str, Any]] = []
    for index in range(1, 11):
        key = "tehnicheskie_usloviya" if index == 1 else f"tehnicheskie_usloviya_{index}"
        path = result.pop(key, None)
        if path:
            documents.append({"kind": "technical_conditions", "index": index, "path": path})
    for kind, key in (("contract", "contract_file"), ("admission_act", "admission_act_file")):
        path = result.get(key)
        if path:
            documents.append({"kind": kind, "path": path})

    connections: list[dict[str, Any]] = []
    for index in range(1, 6):
        connection = {
            "index": index,
            "code": result.pop(f"kod{index}", None),
            "node": result.pop(f"uzel{index}", None),
            "load_percent": result.pop(f"protsent_nagruzki_{index}", None),
        }
        if any(value not in (None, "") for key, value in connection.items() if key != "index"):
            connections.append(connection)
    return {
        "extensions": extensions,
        "documents": documents,
        "connections": connections,
    }


async def get_technical_condition(
    conn: asyncpg.Connection, condition_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        TECHNICAL_CONDITION_SUMMARY_SELECT + " WHERE tu.id=$1", condition_id
    )
    if summary is None:
        return None
    detail = await conn.fetchrow(
        DETAIL_FIELDS
        + """ FROM tehnicheskie_usloviya tu
               LEFT JOIN zdaniya_tu building ON building.id=tu.zdanie
              WHERE tu.id=$1""",
        condition_id,
    )
    result = dict(summary)
    if detail:
        result.update(dict(detail))
    result["relations"] = _extract_relations(result)
    return result
