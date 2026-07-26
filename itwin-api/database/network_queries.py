"""Desktop «Запросы» (zaprosy.cpp Zap1/2/3/7) — read-only aggregates for PG."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import asyncpg


def _frag_clause(alias: str, fragment_ids: Optional[Sequence[int]]) -> tuple[str, list[Any]]:
    if not fragment_ids:
        return "", []
    return f" AND {alias}.fileid = ANY($1::int[])", [list(fragment_ids)]


async def query_network_volume(
    conn: asyncpg.Connection,
    *,
    fragment_ids: Optional[Sequence[int]] = None,
) -> dict[str, Any]:
    """Zap1: объём сети, м³."""
    extra, args = _frag_clause("n1", fragment_ids)
    row = await conn.fetchrow(
        f"""
        SELECT COALESCE(SUM(
            POWER(hps.diameterinternal / 1000.0, 2)
            * hps.pipesectlength
            * CASE WHEN lo.externalsignlineid = 1 THEN 2 ELSE 1 END
            * pi() / 4.0
        ), 0)::float AS volume_m3
          FROM linesobj lo
          JOIN heatpipesections hps ON hps.lineid = lo.id
          JOIN nodes n1 ON n1.id = lo.nodeid1
         WHERE COALESCE(lo.removed, 0) = 0
           AND n1.internalnodeid IS NULL
           {extra}
        """,
        *args,
    )
    return {
        "query": "volume",
        "title": "Объём сети, м³",
        "fragment_ids": list(fragment_ids or []),
        "volume_m3": float(row["volume_m3"] if row else 0),
    }


async def query_network_length(
    conn: asyncpg.Connection,
    *,
    fragment_ids: Optional[Sequence[int]] = None,
) -> dict[str, Any]:
    """Zap2: длина теплопроводов подача/обратка."""
    extra, args = _frag_clause("n1", fragment_ids)
    row = await conn.fetchrow(
        f"""
        SELECT
            COALESCE(SUM(
              CASE WHEN lo.externalsignlineid IN (1, 2, 4)
                   THEN hps.pipesectlength ELSE 0 END
            ), 0)::float AS length_supply_m,
            COALESCE(SUM(
              CASE WHEN lo.externalsignlineid IN (1, 3, 5)
                   THEN hps.pipesectlength ELSE 0 END
            ), 0)::float AS length_return_m
          FROM linesobj lo
          JOIN heatpipesections hps ON hps.lineid = lo.id
          JOIN nodes n1 ON n1.id = lo.nodeid1
         WHERE COALESCE(lo.removed, 0) = 0
           AND n1.internalnodeid IS NULL
           {extra}
        """,
        *args,
    )
    supply = float(row["length_supply_m"] if row else 0)
    ret = float(row["length_return_m"] if row else 0)
    return {
        "query": "length",
        "title": "Длина теплопроводов, м",
        "fragment_ids": list(fragment_ids or []),
        "length_supply_m": supply,
        "length_return_m": ret,
        "length_total_m": supply + ret,
    }


async def query_length_by_diameter(
    conn: asyncpg.Connection,
    *,
    fragment_ids: Optional[Sequence[int]] = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Zap7: длина по условным диаметрам."""
    extra, args = _frag_clause("n1", fragment_ids)
    # limit as last bind
    limit_idx = len(args) + 1
    rows = await conn.fetch(
        f"""
        SELECT
            hps.diametercondit AS diameter_condit,
            COALESCE(SUM(
              hps.pipesectlength
              * CASE WHEN lo.externalsignlineid = 1 THEN 2 ELSE 1 END
            ), 0)::float AS length_m
          FROM linesobj lo
          JOIN heatpipesections hps ON hps.lineid = lo.id
          JOIN nodes n1 ON n1.id = lo.nodeid1
         WHERE COALESCE(lo.removed, 0) = 0
           AND n1.internalnodeid IS NULL
           {extra}
         GROUP BY hps.diametercondit
         ORDER BY hps.diametercondit NULLS LAST
         LIMIT ${limit_idx}
        """,
        *args,
        limit,
    )
    items = [
        {
            "diameter_condit": r["diameter_condit"],
            "length_m": float(r["length_m"] or 0),
        }
        for r in rows
    ]
    return {
        "query": "length_by_diameter",
        "title": "Длина теплопроводов по диаметрам, м",
        "fragment_ids": list(fragment_ids or []),
        "items": items,
        "total_length_m": sum(i["length_m"] for i in items),
    }


async def query_heat_consumption(
    conn: asyncpg.Connection,
    *,
    fragment_ids: Optional[Sequence[int]] = None,
) -> dict[str, Any]:
    """Zap3: теплопотребление из PT_OUT по последнему calculation на фрагмент."""
    if not fragment_ids:
        # Without fragment scope desktop still requires fileID IN (...); we use all latest calcs.
        row = await conn.fetchrow(
            """
            SELECT
              COALESCE(SUM(p.qotz), 0)::float AS n_otz,
              COALESCE(SUM(p.qotn), 0)::float AS n_otn,
              COALESCE(SUM(p.dop12), 0)::float AS n_vn,
              COALESCE(SUM(p.dop18), 0)::float AS n_gvop,
              COALESCE(SUM(p.dop19), 0)::float AS n_gvoo,
              COALESCE(SUM(p.dop20), 0)::float AS n_rez,
              COALESCE(SUM(p.dop17), 0)::float AS n_gvz,
              COALESCE(SUM(p.a4), 0)::float AS q_otz,
              COALESCE(SUM(p.a5), 0)::float AS q_otn,
              COALESCE(SUM(p.a6), 0)::float AS q_vn,
              COALESCE(SUM(p.a12), 0)::float AS q_gvop,
              COALESCE(SUM(p.a13), 0)::float AS q_gvoo,
              COALESCE(SUM(p.a14), 0)::float AS q_rez,
              COALESCE(SUM(p.a15), 0)::float AS q_gvz
              FROM pt_out p
              JOIN nodes n ON n.id = p.nodeid AND COALESCE(n.removed, 0) = 0
              JOIN (
                SELECT fileid, MAX(id) AS cid
                  FROM calculation
                 GROUP BY fileid
              ) calc ON calc.fileid = n.fileid AND calc.cid = p.calculationid
            """
        )
    else:
        row = await conn.fetchrow(
            """
            SELECT
              COALESCE(SUM(p.qotz), 0)::float AS n_otz,
              COALESCE(SUM(p.qotn), 0)::float AS n_otn,
              COALESCE(SUM(p.dop12), 0)::float AS n_vn,
              COALESCE(SUM(p.dop18), 0)::float AS n_gvop,
              COALESCE(SUM(p.dop19), 0)::float AS n_gvoo,
              COALESCE(SUM(p.dop20), 0)::float AS n_rez,
              COALESCE(SUM(p.dop17), 0)::float AS n_gvz,
              COALESCE(SUM(p.a4), 0)::float AS q_otz,
              COALESCE(SUM(p.a5), 0)::float AS q_otn,
              COALESCE(SUM(p.a6), 0)::float AS q_vn,
              COALESCE(SUM(p.a12), 0)::float AS q_gvop,
              COALESCE(SUM(p.a13), 0)::float AS q_gvoo,
              COALESCE(SUM(p.a14), 0)::float AS q_rez,
              COALESCE(SUM(p.a15), 0)::float AS q_gvz
              FROM pt_out p
              JOIN nodes n ON n.id = p.nodeid AND COALESCE(n.removed, 0) = 0
              JOIN (
                SELECT fileid, MAX(id) AS cid
                  FROM calculation
                 WHERE fileid = ANY($1::int[])
                 GROUP BY fileid
              ) calc ON calc.fileid = n.fileid AND calc.cid = p.calculationid
             WHERE n.fileid = ANY($1::int[])
            """,
            list(fragment_ids),
        )
    totals = dict(row) if row else {}
    return {
        "query": "heat_consumption",
        "title": "Теплопотребление полученное, Гкал/ч",
        "fragment_ids": list(fragment_ids or []),
        "totals": {k: float(v or 0) for k, v in totals.items()},
        "note": "Агрегат по PT_OUT последнего calculation на фрагмент(ы)",
    }
