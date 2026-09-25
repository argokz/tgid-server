"""Temperature graph write helpers (stationary fill + OTOP recalculate)."""

from __future__ import annotations

from typing import Any

import asyncpg

from database.tg_otop import calculate_otop_curve


async def apply_stationary_graph(
    conn: asyncpg.Connection,
    source_id: int,
    *,
    t1: float,
    t2: float,
    t3: float,
    tv: float,
) -> int:
    """Desktop «Стационарный»: replace all curve values for existing points."""
    result = await conn.execute(
        """
        UPDATE deployedtempgraphs
           SET t1=$2, t2=$3, t3=$4, tv=$5
         WHERE hsourceid=$1
        """,
        source_id,
        t1,
        t2,
        t3,
        tv,
    )
    # asyncpg returns e.g. "UPDATE 42"
    try:
        return int(str(result).split()[-1])
    except (ValueError, IndexError):
        return 0


async def clear_temperature_graph(conn: asyncpg.Connection, source_id: int) -> None:
    await conn.execute("DELETE FROM deployedtempgraphs WHERE hsourceid=$1", source_id)


async def seed_otop_graph(conn: asyncpg.Connection, source_id: int, params: dict[str, Any]) -> int:
    """Replace deployedTempGraphs with desktop OTOP curve."""
    points = calculate_otop_curve(params)
    # delete + insert атомарно: при ошибке вставки график источника не должен пропасть
    async with conn.transaction():
        await clear_temperature_graph(conn, source_id)
        await conn.executemany(
            """
            INSERT INTO deployedtempgraphs (hsourceid, tn, t1, t2, t3, tv, t_bn, q_otn)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            [
                (
                    source_id,
                    p["tn"],
                    p["t1"],
                    p["t2"],
                    p["t3"],
                    p["tv"],
                    p["t_bn"],
                    p["q_otn"],
                )
                for p in points
            ],
        )
    return len(points)


async def seed_linear_graph(
    conn: asyncpg.Connection,
    source_id: int,
    *,
    tn_min: float,
    tn_max: float,
    t1_design: float,
    t2_design: float,
    t3_design: float,
) -> int:
    """Fallback linear fill if OTOP inputs are incomplete (kept for tests)."""
    if tn_max < tn_min:
        tn_min, tn_max = tn_max, tn_min
    npoints = int(round(tn_max - tn_min)) + 1
    if npoints < 2 or npoints > 200:
        raise ValueError("Invalid outdoor temperature range for graph seed")
    await clear_temperature_graph(conn, source_id)
    inserted = 0
    for i in range(npoints):
        tn = tn_min + i
        ratio = 0.0 if npoints == 1 else i / (npoints - 1)
        cold_ratio = 1.0 - ratio
        t1 = t2_design + (t1_design - t2_design) * cold_ratio
        t2 = t2_design
        t3 = t2_design + (t3_design - t2_design) * cold_ratio if t3_design else t1
        tv = t1
        await conn.execute(
            """
            INSERT INTO deployedtempgraphs (hsourceid, tn, t1, t2, t3, tv)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            source_id,
            float(tn),
            float(round(t1, 1)),
            float(round(t2, 1)),
            float(round(t3, 1)),
            float(round(tv, 1)),
        )
        inserted += 1
    return inserted


async def source_design_temps(conn: asyncpg.Connection, source_id: int) -> dict[str, Any] | None:
    row = await conn.fetchrow(
        """
        SELECT id, tn_5, tn_1, tvn_r, t1_r, t2_r, t3_r, q_r, q_gv,
               t1_2r, t1_4r, t2_2r, tvb_tr, uf, v
          FROM heatsources
         WHERE id=$1
        """,
        source_id,
    )
    return dict(row) if row else None
