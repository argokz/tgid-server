"""Field allow-lists for ops journals (defect → shurf → osmotr → remont → opres)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

OPS_MUTABLE_FIELDS: dict[str, frozenset[str]] = {
    "defect": frozenset(
        {
            "data_osmotra",
            "tip_povrezhdenia",
            "harakter_povrezhdenia",
            "povrezhdennyi_truboprovod",
            "sost_naruzhnoy",
            "rasstoyanie",
            "vremya_nachala_rabot",
            "vremya_okonchaniya_rabot",
            "shirina_povrezhdenia",
            "vysota_povrezhdenia",
            "prichiny",
            "tsentr_povrezhdenia",
            "lineid",
            "nodeid",
            "sostoyanie",
            "primechanie",
            "adres",
        }
    ),
    "shurfy": frozenset(
        {
            "data_shurfa",
            "lineid",
            "nodeid",
            "sostoyanie",
            "primechanie",
            "glubina",
            "shirina",
            "dlina",
            "rezultat",
            "adres",
        }
    ),
    "osmotr": frozenset(
        {
            "data_osmotra",
            "lineid",
            "nodeid",
            "primechanie",
            "adres",
            "rezultat",
            "ispolnitel",
        }
    ),
    "remont2": frozenset(
        {
            "data_remonta",
            "lineid",
            "nodeid",
            "sostoyanie",
            "primechanie",
            "vid_rabot",
            "adres",
            "ispolnitel",
        }
    ),
    "opres": frozenset(
        {
            "data_opressovki",
            "lineid",
            "nodeid",
            "davlenie",
            "rezultat",
            "sostoyanie",
            "primechanie",
            "adres",
        }
    ),
}


def filter_ops_fields(table: str, fields: dict[str, Any]) -> dict[str, Any]:
    allow = OPS_MUTABLE_FIELDS.get(table.lower())
    if allow is None:
        return fields
    allow_lower = {f.lower(): f for f in allow}
    normalized: dict[str, Any] = {}
    for key, value in fields.items():
        canon = allow_lower.get(key.lower())
        if canon:
            normalized[canon] = value
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail=f"No writable fields for {table}. Allowed sample: {sorted(allow)[:12]}",
        )
    return normalized
