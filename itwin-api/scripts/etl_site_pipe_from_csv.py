#!/usr/bin/env python3
"""Load desktop site↔pipe CSV into etl_site_pipe_staging and optionally apply.

CSV columns (header required):
  lineid,magistralsite,distsite[,source_note]

Usage (from itwin-api/itwin-api):
  python scripts/etl_site_pipe_from_csv.py path/to/site_pipe.csv
  python scripts/etl_site_pipe_from_csv.py path/to/site_pipe.csv --apply

Dry-run (default) only loads staging and prints counts; --apply updates
heatpipesections and prints before/after site fill stats.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from database.connect import acquire_conn, close_db_pool, init_db_pool  # noqa: E402


STAGING_DDL = """
CREATE TABLE IF NOT EXISTS etl_site_pipe_staging (
    lineid          integer PRIMARY KEY,
    magistralsite   integer,
    distsite        integer,
    source_note     text,
    loaded_at       timestamptz NOT NULL DEFAULT now()
)
"""


def _int_or_none(v: str | None) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s.lower() in {"null", "none", "nan"}:
        return None
    return int(float(s))


async def site_counts(conn) -> dict[str, int]:
    row = await conn.fetchrow(
        """
        SELECT
          count(*)::int AS total,
          count(*) FILTER (WHERE NULLIF(magistralsite, 0) IS NOT NULL)::int AS ms,
          count(*) FILTER (WHERE NULLIF(distsite, 0) IS NOT NULL)::int AS rs
          FROM heatpipesections
        """
    )
    return dict(row)


async def run(csv_path: Path, apply: bool) -> int:
    rows: list[tuple[int, int | None, int | None, str | None]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "lineid" not in {h.lower() for h in reader.fieldnames}:
            print("CSV must have header with lineid[,magistralsite,distsite,source_note]")
            return 2
        # normalize keys
        for raw in reader:
            key = {k.lower(): v for k, v in raw.items() if k}
            lineid = _int_or_none(key.get("lineid"))
            if lineid is None:
                continue
            rows.append(
                (
                    lineid,
                    _int_or_none(key.get("magistralsite")),
                    _int_or_none(key.get("distsite")),
                    (key.get("source_note") or "").strip() or None,
                )
            )

    if not rows:
        print("No data rows in CSV")
        return 2

    await init_db_pool()
    try:
        async with acquire_conn() as conn:
            await conn.execute(STAGING_DDL)
            before = await site_counts(conn)
            await conn.execute("TRUNCATE etl_site_pipe_staging")
            await conn.executemany(
                """
                INSERT INTO etl_site_pipe_staging(lineid, magistralsite, distsite, source_note)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (lineid) DO UPDATE SET
                  magistralsite = EXCLUDED.magistralsite,
                  distsite = EXCLUDED.distsite,
                  source_note = EXCLUDED.source_note,
                  loaded_at = now()
                """,
                rows,
            )
            staged = await conn.fetchval("SELECT count(*)::int FROM etl_site_pipe_staging")
            print(f"staged rows: {staged}")
            print(f"hps before: {before}")

            if not apply:
                print("dry-run only (pass --apply to UPDATE heatpipesections)")
                return 0

            updated = await conn.fetchval(
                """
                WITH u AS (
                  UPDATE heatpipesections h
                     SET magistralsite = COALESCE(s.magistralsite, h.magistralsite),
                         distsite = COALESCE(s.distsite, h.distsite)
                    FROM etl_site_pipe_staging s
                   WHERE h.lineid = s.lineid
                     AND (
                          s.magistralsite IS NOT NULL
                       OR s.distsite IS NOT NULL
                     )
                  RETURNING 1
                )
                SELECT count(*)::int FROM u
                """
            )
            after = await site_counts(conn)
            print(f"updated heatpipesections rows: {updated}")
            print(f"hps after: {after}")
            print("Next: run scripts/sql/backfill_belong_site.sql then /api/passports/diagnostics")
            return 0
    finally:
        await close_db_pool()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv_path", type=Path)
    p.add_argument("--apply", action="store_true", help="UPDATE heatpipesections from staging")
    args = p.parse_args()
    if not args.csv_path.is_file():
        print(f"File not found: {args.csv_path}")
        return 2
    return asyncio.run(run(args.csv_path, args.apply))


if __name__ == "__main__":
    sys.exit(main())
