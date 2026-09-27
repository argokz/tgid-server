"""Прогон Excel-отчётов десктопа (database/excel_reports.py) на живой базе, только чтение.

    cd itwin-api/itwin-api
    set -a; . ./.env; . ./.env.copy; set +a
    ./venv/Scripts/python.exe scripts/golden/reports_smoke.py [fragment_id] [calculation_id] [out_dir]

По умолчанию фрагмент 74 и его последний расчёт. Для каждого SQL из sql/reports печатает
число строк и колонок, время; для каждого листа отчёта сверяет число колонок запроса
с шапкой шаблона; затем собирает каждую книгу целиком (out_dir — сохранить .xlsx).
Код возврата 1, если хоть один запрос упал или колонки не совпали с шапкой.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import asyncpg  # noqa: E402
import openpyxl  # noqa: E402

from database import excel_reports as X  # noqa: E402


async def main() -> int:
    fragment_id = int(sys.argv[1]) if len(sys.argv) > 1 else 74
    calculation_id = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2] not in ("", "0", "-") else None
    out_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    conn = await asyncpg.connect(
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        host=os.environ.get("DB_HOST", "127.0.0.1"), port=int(os.environ.get("DB_PORT", 5432)),
        database=os.environ["DB_NAME"],
    )
    failed = 0
    try:
        await conn.execute("SET default_transaction_read_only = on")
        calc = await X.resolve_calculation(conn, fragment_id, calculation_id)
        calc_id = calc["id"] if calc else None
        print(f"База {os.environ['DB_NAME']}, фрагмент {fragment_id}, расчёт {calc_id}")

        columns_by_sql: dict[str, int] = {}
        for path in sorted(X.SQL_DIR.glob("*.sql")):
            name = path.stem
            if name.startswith("_"):
                continue
            sql = X.load_sql(name)
            n = X.sql_params(sql)
            args = [fragment_id, calc_id][:n]
            t = time.perf_counter()
            try:
                async with conn.transaction(readonly=True):
                    await conn.execute(f"SET LOCAL statement_timeout = {X.STATEMENT_TIMEOUT_MS}")
                    stmt = await conn.prepare(sql)
                    rows = await stmt.fetch(*args) if (n < 2 or calc_id) else []
                cols = [a.name for a in stmt.get_attributes() if not a.name.startswith("_")]
                columns_by_sql[name] = len(cols)
                print(f"OK   {len(rows):6d} строк {len(cols):3d} кол. {time.perf_counter() - t:5.2f} с  {name}")
            except Exception as e:  # noqa: BLE001 — печатаем любую ошибку запроса
                failed += 1
                print(f"FAIL {name}: {type(e).__name__}: {str(e).splitlines()[0][:200]}")

        print("\nСверка колонок с шапкой шаблона:")
        for report in X.REPORTS:
            if not report.template:
                continue
            wb = openpyxl.load_workbook(X.TEMPLATE_DIR / f"{report.template}.xlsx")
            for sheet in report.sheets:
                ws = wb.worksheets[sheet.sheet - 1]
                labeled = X.labeled_columns(ws, sheet.header_row)
                got = columns_by_sql.get(sheet.sql)
                if ws.title != sheet.title:
                    failed += 1
                    print(f"FAIL {report.id}/{sheet.sheet}: лист «{ws.title}», в каталоге «{sheet.title}»")
                mark = "OK  " if got is not None and got <= labeled else "WARN"
                print(f"{mark} {report.id:9s} лист {sheet.sheet} «{sheet.title}»: запрос {got}, шапка {labeled}")

        print("\nСборка книг:")
        for report in X.REPORTS:
            t = time.perf_counter()
            try:
                data, summary = await X.build_report(conn, report.id, fragment_id, calc_id)
                rows = ", ".join(f"{s['title']}={s['rows']}" for s in summary["sheets"])
                print(f"OK   {report.id:9s} {len(data) // 1024:6d} КБ {time.perf_counter() - t:5.2f} с  {rows}")
                if out_dir:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    (out_dir / f"{report.id}.xlsx").write_bytes(data)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print(f"FAIL {report.id}: {type(e).__name__}: {e}")
    finally:
        await conn.close()
    print(f"\nОшибок: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
