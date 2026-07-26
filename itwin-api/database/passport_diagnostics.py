"""Диагностика привязок участков для Excel-паспорта."""

from __future__ import annotations

from typing import Any

import asyncpg


async def get_passport_site_diagnostics(conn: asyncpg.Connection) -> dict[str, Any]:
    """Показывает, почему make_graph может вернуть пустой граф."""
    hps_ms = await conn.fetchval(
        "SELECT count(*)::int FROM heatpipesections WHERE NULLIF(magistralsite, 0) IS NOT NULL"
    )
    hps_rs = await conn.fetchval(
        "SELECT count(*)::int FROM heatpipesections WHERE NULLIF(distsite, 0) IS NOT NULL"
    )
    hps_total = await conn.fetchval("SELECT count(*)::int FROM heatpipesections")
    nodes_ms = await conn.fetchval(
        "SELECT count(*)::int FROM nodes WHERE NULLIF(belongmagistralsite, 0) IS NOT NULL"
    )
    nodes_rs = await conn.fetchval(
        "SELECT count(*)::int FROM nodes WHERE NULLIF(belongdistsite, 0) IS NOT NULL"
    )
    uch_ms = await conn.fetchval("SELECT count(*)::int FROM uchastok_ms")
    uch_rs = await conn.fetchval("SELECT count(*)::int FROM uchastok_rs")
    # uzel1/uzel2 — varchar в проде (не integer)
    uch_ms_ends = await conn.fetchval(
        """
        SELECT count(*)::int FROM uchastok_ms
         WHERE NULLIF(TRIM(uzel1::text), '') IS NOT NULL
           AND NULLIF(TRIM(uzel1::text), '0') IS NOT NULL
           AND NULLIF(TRIM(uzel2::text), '') IS NOT NULL
           AND NULLIF(TRIM(uzel2::text), '0') IS NOT NULL
        """
    )
    passports = await conn.fetchval("SELECT count(*)::int FROM passports")

    ready = bool(hps_ms or hps_rs or nodes_ms or nodes_rs)
    blockers: list[str] = []
    if not (hps_ms or hps_rs):
        blockers.append(
            "heatpipesections.magistralSite/distSite пусты — make_graph не находит трубы участка"
        )
    if not (nodes_ms or nodes_rs):
        blockers.append(
            "nodes.belongMagistralSite/belongDistSite пусты — passport по node/line без fallback не откроется"
        )
    if uch_ms_ends == 0:
        blockers.append("uchastok_ms.uzel1/uzel2 пусты — нельзя восстановить участок по концам")
    if passports == 0:
        blockers.append("таблица passports пуста")

    return {
        "ready_for_passport": ready,
        "blockers": blockers,
        "counts": {
            "heatpipesections_total": hps_total,
            "heatpipesections_with_magistral_site": hps_ms,
            "heatpipesections_with_dist_site": hps_rs,
            "nodes_with_belong_magistral_site": nodes_ms,
            "nodes_with_belong_dist_site": nodes_rs,
            "uchastok_ms": uch_ms,
            "uchastok_rs": uch_rs,
            "uchastok_ms_with_endpoints": uch_ms_ends,
            "passports": passports,
        },
        "remediation": [
            "Восстановить привязки участок↔линии из desktop-дампа (поля magistralSite/distSite).",
            "Или выполнить scripts/sql/backfill_belong_site.sql после заполнения heatpipesections.*Site.",
            "Открывать паспорт по uchastok_ms/rs из hierarchy только когда у участка есть трубы.",
        ],
    }
