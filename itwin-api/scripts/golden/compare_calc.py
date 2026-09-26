"""Сравнение двух расчётов sety по ut_out / us_out (приёмка desktop = web).

Эталон — расчёт, записанный десктопом (gid8 запускает тот же sety/ww.py), кандидат —
расчёт, запущенный через веб (/run-sety-cmd → Celery). Оба лежат в одной БД,
различаются calculationid.

    set -a; . ./.env.copy; set +a
    ./venv/Scripts/python.exe scripts/golden/compare_calc.py --base 1 --new 2 [--out report.md]

Только чтение. Колонки — по смыслу из database/ut_out_columns.py.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from database import ut_out_columns as C  # noqa: E402

UT_COLUMNS = {
    "длина, м": C.UT_LENGTH_M,
    "диаметр, мм": C.UT_DIAMETER_MM,
    "скорость, м/с": C.UT_VELOCITY_MS,
    "расход, т/ч": C.UT_FLOW_TH,
    "уд. потери, мм/м": C.UT_SPEC_LOSS_MM_M,
    "потери общие, м": C.UT_LOSS_TOTAL_M,
    "располаг. напор, м": C.UT_AVAIL_HEAD_END_M,
    "пьез. напор, м": C.UT_PIEZO_HEAD_END_M,
}
US_COLUMNS = {"пьез. напор узла, м": C.US_PIEZO_HEAD_M, "температура, °C": C.US_TEMPERATURE_C}


def _stats(pairs: list[tuple[float, float]]) -> dict:
    diffs = [abs(a - b) for a, b in pairs]
    rel = [abs(a - b) / max(abs(a), 1e-9) for a, b in pairs if abs(a) > 1e-6]
    return {
        "n": len(pairs),
        "max_abs": max(diffs, default=0.0),
        "mean_abs": sum(diffs) / len(diffs) if diffs else 0.0,
        "max_rel": max(rel, default=0.0),
    }


async def compare(conn, base: int, new: int) -> tuple[str, bool]:
    lines = [f"# Сравнение расчётов sety: #{base} (эталон) и #{new}\n"]
    for cid in (base, new):
        row = await conn.fetchrow("SELECT id, fileid, tn, date1, calc_params FROM calculation WHERE id = $1", cid)
        lines.append(f"- расчёт #{cid}: фрагмент {row['fileid']}, Tн {row['tn']}, {row['date1']}")
        lines.append(f"  параметры: `{row['calc_params']}`")
    lines.append("")

    ok = True
    ut_cols = ", ".join(f"{col} AS \"{col}\"" for col in UT_COLUMNS.values())
    rows = {}
    for cid in (base, new):
        rows[cid] = {
            (r["lineid"], r["externalsignlineid"]): r
            for r in await conn.fetch(
                f"SELECT lineid, externalsignlineid, {ut_cols} FROM ut_out WHERE calculationid = $1", cid
            )
        }
    only_base = set(rows[base]) - set(rows[new])
    only_new = set(rows[new]) - set(rows[base])
    common = set(rows[base]) & set(rows[new])
    lines.append("## Участки (ut_out)\n")
    lines.append(f"Строк: эталон {len(rows[base])}, кандидат {len(rows[new])}, общих {len(common)}, "
                 f"только в эталоне {len(only_base)}, только в кандидате {len(only_new)}.\n")
    if only_base or only_new:
        ok = False
    lines.append("| величина | сравнено | max |Δ| | среднее |Δ| | max отн. |")
    lines.append("|---|---|---|---|---|")
    worst: list[tuple[float, tuple]] = []
    for title, col in UT_COLUMNS.items():
        pairs = [(float(rows[base][k][col] or 0), float(rows[new][k][col] or 0)) for k in common]
        s = _stats(pairs)
        lines.append(f"| {title} | {s['n']} | {s['max_abs']:.4g} | {s['mean_abs']:.4g} | {s['max_rel']:.2%} |")
        if s["max_rel"] > 0.001:
            ok = False
        if col == C.UT_FLOW_TH:
            worst = sorted(((abs(a - b), k) for (a, b), k in zip(pairs, common)), reverse=True)[:20]

    lines.append("\nХудшие участки по расходу (lineid, признак трубы, |Δ| т/ч): "
                 + ", ".join(f"{k[0]}/{k[1]}: {d:.3g}" for d, k in worst if d > 0) or "расхождений нет")

    us_cols = ", ".join(f"{col} AS \"{col}\"" for col in US_COLUMNS.values())
    nrows = {}
    for cid in (base, new):
        nrows[cid] = {
            (r["nodeid"], r["externalsign"]): r
            for r in await conn.fetch(f"SELECT nodeid, externalsign, {us_cols} FROM us_out WHERE calculationid = $1", cid)
        }
    ncommon = set(nrows[base]) & set(nrows[new])
    lines.append("\n## Узлы (us_out)\n")
    lines.append(f"Строк: эталон {len(nrows[base])}, кандидат {len(nrows[new])}, общих {len(ncommon)}.\n")
    if len(ncommon) != len(nrows[base]) or len(ncommon) != len(nrows[new]):
        ok = False
    lines.append("| величина | сравнено | max |Δ| | среднее |Δ| | max отн. |")
    lines.append("|---|---|---|---|---|")
    for title, col in US_COLUMNS.items():
        pairs = [(float(nrows[base][k][col] or 0), float(nrows[new][k][col] or 0)) for k in ncommon]
        s = _stats(pairs)
        lines.append(f"| {title} | {s['n']} | {s['max_abs']:.4g} | {s['mean_abs']:.4g} | {s['max_rel']:.2%} |")
        if s["max_rel"] > 0.001:
            ok = False

    lines.append(f"\n**Итог:** {'совпадают (допуск 0.1 %)' if ok else 'есть расхождения — см. таблицы'}")
    return "\n".join(lines) + "\n", ok


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=int, required=True, help="calculationid эталона (десктоп)")
    ap.add_argument("--new", type=int, required=True, help="calculationid кандидата (веб)")
    ap.add_argument("--out", type=str, default="", help="куда записать отчёт Markdown")
    args = ap.parse_args()
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], database=os.environ["DB_NAME"],
    )
    try:
        report, ok = await compare(conn, args.base, args.new)
    finally:
        await conn.close()
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    print(report)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
