"""Dedicated technical-conditions mutations (gid6 ТУ vertical) + field allow-list."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

# Columns safe to write from the web journal (gid6 tab2 / tu form subset).
TU_MUTABLE_FIELDS: frozenset[str] = frozenset(
    {
        "nomer_tu",
        "data_vydachi_tu",
        "organizatsiya",
        "obekt",
        "adres",
        "istochnik",
        "rayon_ekspluatatsii",
        "sostoyanie",
        "dogovor",
        "kamera",
        "srok_deystviya_tu",
        "dopolnitelnye_tehnicheskie_meropriyatiya",
        "v_tom_chisle_prirost_otoplenie",
        "v_tom_chisle_prirost_ventilyatsiya",
        "v_tom_chisle_prirost_gvs_maks",
        "v_tom_chisle_prirost_gvs_sredn",
        "nomer_soglasovaniya_ts",
        "data_soglasovaniya_ts",
        "nomer_soglasovaniya_ov",
        "data_soglasovaniya_ov",
        "nomer_soglasovaniya_tp",
        "data_soglasovaniya_tp",
        "ispolnenie_dop_tehn_i_energ_meropriyatiy_v_ramkah_tu",
        "stadiya_stroitelstva_obektov",
        "teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch",
        "v_tom_chisle_otoplenie_po_aktu",
        "v_tom_chisle_ventilyatsiya_po_aktu",
        "v_tom_chisle_gvs_maks_po_aktu",
        "v_tom_chisle_gvs_sredn_po_aktu",
        "zdanie",
        "tehnicheskie_usloviya",
        "tehnicheskie_usloviya_2",
        "tehnicheskie_usloviya_3",
        "tehnicheskie_usloviya_4",
        "tehnicheskie_usloviya_5",
        "akt",
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


def filter_tu_fields(fields: dict[str, Any]) -> dict[str, Any]:
    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided")
    # Prefer exact keys from allow-list (case as in DB: snake lowercase)
    normalized: dict[str, Any] = {}
    allow_lower = {f.lower(): f for f in TU_MUTABLE_FIELDS}
    for key, value in fields.items():
        canon = allow_lower.get(key.lower())
        if canon:
            normalized[canon] = value
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail=f"None of the fields are writable. Allowed: {sorted(TU_MUTABLE_FIELDS)[:20]}…",
        )
    return normalized
