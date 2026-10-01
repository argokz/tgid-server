"""Dedicated technical-conditions mutations (gid6 ТУ vertical) + field allow-list.

Клиент может присылать как имена колонок ``tehnicheskie_usloviya``, так и ключи API карточки
(``GET /api/technical-conditions/{id}``: ``number``, ``issued_on``, ``organization_name``…) —
они переводятся в колонки по ``TU_FIELD_ALIASES``. Неизвестное поле → 422 (а не 500 из SQL).
Приведение типов (даты строкой, числа) — в ``database.db`` по схеме таблицы.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

# Ключ API карточки ТУ (database/technical_conditions.py) → колонка tehnicheskie_usloviya.
TU_FIELD_ALIASES: dict[str, str] = {
    "number": "nomer_tu",
    "issued_on": "data_vydachi_tu",
    "annulled_on": "data_annulirovaniya",
    "state_id": "sostoyanie_dogovora",
    "organization_name": "naimenovanie_organizatsii__zaprashivayuschey_tu",
    "object_name": "naimenovanie_obekta",
    "address": "adres_obekta",
    "heat_source_name": "istochnik",
    "district_name": "rayon_ekspluatatsii",
    "connection_chamber": "kamera",
    "validity_period": "srok_deystviya_tu",
    "total_heat_load": "teplovye_potoki__gkal_ch",
    "heating_load": "v_tom_chisle_otoplenie",
    "ventilation_load": "v_tom_chisle_ventilyatsiya",
    "hot_water_max_load": "v_tom_chisle_gvs_maks",
    "hot_water_average_load": "v_tom_chisle_gvs_sredn",
    "load_increase": "prirost_nagruzki",
    "heating_load_increase": "v_tom_chisle_prirost_otoplenie",
    "ventilation_load_increase": "v_tom_chisle_prirost_ventilyatsiya",
    "hot_water_max_load_increase": "v_tom_chisle_prirost_gvs_maks",
    "hot_water_average_load_increase": "v_tom_chisle_prirost_gvs_sredn",
    "network_approval_number": "nomer_soglasovaniya_ts",
    "network_approval_date": "data_soglasovaniya_ts",
    "heating_approval_number": "nomer_soglasovaniya_ov",
    "heating_approval_date": "data_soglasovaniya_ov",
    "project_approval_number": "nomer_soglasovaniya_tp",
    "project_approval_date": "data_soglasovaniya_tp",
    "additional_measures": "dopolnitelnye_tehnicheskie_meropriyatiya",
    "measures_completion": "ispolnenie_dop_tehn_i_energ_meropriyatiy_v_ramkah_tu",
    "construction_stage": "stadiya_stroitelstva_obektov",
    "admission_act_number": "nomer_vydachi_akta_dopuska",
    "admission_act_date": "data_vydachi_akta_dopuska",
    "admitted_total_heat_load": "teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch",
    "admitted_heating_load": "v_tom_chisle_otoplenie_po_aktu",
    "admitted_ventilation_load": "v_tom_chisle_ventilyatsiya_po_aktu",
    "admitted_hot_water_max_load": "v_tom_chisle_gvs_maks_po_aktu",
    "admitted_hot_water_average_load": "v_tom_chisle_gvs_sredn_po_aktu",
    "contract_number": "nomer_dogovora",
    "contract_date": "data_dogovora",
    "contract_file": "dogovor",
    "admission_act_file": "akt",
    "building_id": "zdanie",
    "pipe_id": "truba",
}

# Колонки, которые правит веб-реестр (gid6 tab2 / форма ТУ); сверены с information_schema
# tehnicheskie_usloviya (almatygid_copy, 02.10.2026).
TU_MUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        *TU_FIELD_ALIASES.values(),
        "tehnicheskie_usloviya",
        "tehnicheskie_usloviya_2",
        "tehnicheskie_usloviya_3",
        "tehnicheskie_usloviya_4",
        "tehnicheskie_usloviya_5",
        "kod1",
        "uzel1",
        "protsent_nagruzki_1",
        "kod2",
        "uzel2",
        "protsent_nagruzki_2",
        "kod3",
        "uzel3",
        "protsent_nagruzki_3",
    }
)

TU_TABLE = "tehnicheskie_usloviya"

_CANONICAL: dict[str, str] = {
    **{column.lower(): column for column in TU_MUTABLE_FIELDS},
    **{alias.lower(): column for alias, column in TU_FIELD_ALIASES.items()},
}


def filter_tu_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Ключи API/колонки → колонки allow-list; пусто → 400, неизвестные поля → 422."""
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided")
    normalized: dict[str, Any] = {}
    unknown: list[str] = []
    for key, value in fields.items():
        canon = _CANONICAL.get(str(key).lower())
        if canon:
            normalized[canon] = value
        else:
            unknown.append(str(key))
    if unknown:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "unknown_fields",
                "fields": unknown,
                "message": f"Поля не редактируются в реестре ТУ: {', '.join(unknown)}",
            },
        )
    return normalized
