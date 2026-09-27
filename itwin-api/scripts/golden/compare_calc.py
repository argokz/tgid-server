"""Сравнение двух расчётов sety по ut_out / us_out / pt_out (приёмка desktop = web).

Эталон — расчёт, записанный десктопом (gid8 запускает тот же sety/ww.py), кандидат —
расчёт, запущенный через веб (POST /api/v1/calculations/run → Celery). Оба лежат в одной
БД, различаются calculationid.

    ./venv/Scripts/python.exe scripts/golden/compare_calc.py --base 1 --new 2 [--out report.md]

Подключение: .env, поверх него .env.copy (копия БД), если файл есть и не указан --no-copy.
Только чтение. Колонки — по смыслу из database/ut_out_columns.py и sety/out/pt_out.py.

Ключи строк: участок (lineid, externalsignlineid), узел (nodeid, externalsign),
потребитель (nodeid, ist). Значение проходит допуск, если |Δ| ≤ abs или |Δ|/|эталон| ≤ rel.
Код возврата 0 — всё в допуске и наборы строк совпадают, 1 — есть расхождения.
"""

from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from database import ut_out_columns as C  # noqa: E402


@dataclass(frozen=True)
class Col:
    title: str
    column: str
    abs_tol: float
    rel_tol: float = 0.001


@dataclass(frozen=True)
class Table:
    title: str
    name: str
    key: tuple[str, str]
    key_title: str
    columns: tuple[Col, ...]


UT = Table(
    "Участки (ut_out)", "ut_out", ("lineid", "externalsignlineid"), "lineid/признак",
    (
        Col("длина, м", C.UT_LENGTH_M, 0.01),
        Col("диаметр, мм", C.UT_DIAMETER_MM, 0.1),
        Col("скорость, м/с", C.UT_VELOCITY_MS, 0.001),
        Col("расход, т/ч", C.UT_FLOW_TH, 0.01),
        Col("уд. потери, мм/м", C.UT_SPEC_LOSS_MM_M, 0.01),
        Col("потери общие, м", C.UT_LOSS_TOTAL_M, 0.01),
        Col("располаг. напор, м", C.UT_AVAIL_HEAD_END_M, 0.01),
        Col("пьез. напор, м", C.UT_PIEZO_HEAD_END_M, 0.01),
    ),
)
US = Table(
    "Узлы (us_out)", "us_out", ("nodeid", "externalsign"), "nodeid/признак",
    (
        Col("пьез. напор узла, м", C.US_PIEZO_HEAD_M, 0.01),
        Col("температура, °C", C.US_TEMPERATURE_C, 0.05),
    ),
)
PT = Table(
    "Потребители (pt_out)", "pt_out", ("nodeid", "ist"), "nodeid/источник",
    (
        Col("треб. нагрузка отопл., Гкал/ч", "qotz_treb", 1e-4),
        Col("нагрузка отопл., Гкал/ч", "qotz", 1e-4),
        Col("расход закр. сист., т/ч", "a15", 0.01),
        Col("располаг. напор, м", "a23", 0.01),
        Col("t1 на вводе, °C", "t1", 0.05),
        Col("t2 на выходе, °C", "t2", 0.05),
    ),
)
TABLES = (UT, US, PT)


def _f(v) -> float:
    if v is None:
        return 0.0
    try:
        x = float(v)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(x) else x


def _excess(a: float, b: float, col: Col) -> float:
    """Во сколько раз расхождение превышает допуск (≤ 1 — в допуске)."""
    d = abs(a - b)
    by_abs = d / col.abs_tol
    by_rel = d / (abs(a) * col.rel_tol) if abs(a) > 0 else math.inf if d > 0 else 0.0
    return min(by_abs, by_rel)


async def _rows(conn, table: Table, cid: int) -> tuple[dict, int]:
    cols = ", ".join(f'{c.column} AS "{c.column}"' for c in table.columns)
    k1, k2 = table.key
    data: dict = {}
    dups = 0
    for r in await conn.fetch(f"SELECT {k1}, {k2}, {cols} FROM {table.name} WHERE calculationid = $1", cid):
        key = (r[k1], r[k2])
        if key in data:
            dups += 1
        data[key] = r
    return data, dups


def compare_rows(table: Table, base: dict, new: dict, top: int = 20) -> dict:
    """Чистая функция сравнения (без БД) — её же проверяют тесты."""
    common = sorted(set(base) & set(new), key=lambda k: tuple(-1 if x is None else x for x in k))
    stats = []
    worst: list[tuple[float, tuple, str, float, float]] = []
    for col in table.columns:
        diffs, rels, bad = [], [], 0
        for k in common:
            a, b = _f(base[k][col.column]), _f(new[k][col.column])
            d = abs(a - b)
            diffs.append(d)
            if abs(a) > 1e-9:
                rels.append(d / abs(a))
            ex = _excess(a, b, col)
            if ex > 1:
                bad += 1
                worst.append((ex, k, col.title, a, b))
        stats.append({
            "col": col, "n": len(diffs),
            "max_abs": max(diffs, default=0.0),
            "mean_abs": sum(diffs) / len(diffs) if diffs else 0.0,
            "max_rel": max(rels, default=0.0),
            "bad": bad,
        })
    worst.sort(key=lambda w: w[0], reverse=True)
    return {
        "n_base": len(base), "n_new": len(new), "n_common": len(common),
        "only_base": len(set(base) - set(new)), "only_new": len(set(new) - set(base)),
        "stats": stats, "worst": worst[:top], "n_bad_values": sum(s["bad"] for s in stats),
    }


def render_table(table: Table, res: dict, dups: tuple[int, int] = (0, 0)) -> tuple[list[str], bool]:
    ok = res["only_base"] == 0 and res["only_new"] == 0 and res["n_bad_values"] == 0
    out = [f"## {table.title}\n",
           f"Строк: эталон {res['n_base']}, кандидат {res['n_new']}, общих {res['n_common']}, "
           f"только в эталоне {res['only_base']}, только в кандидате {res['only_new']}"
           + (f", повторы ключа {dups[0]}/{dups[1]}" if any(dups) else "") + ".\n",
           "| величина | допуск | сравнено | max abs Δ | среднее abs Δ | max отн. | вне допуска |",
           "|---|---|---|---|---|---|---|"]
    for s in res["stats"]:
        c = s["col"]
        out.append(f"| {c.title} | {c.abs_tol:g} или {c.rel_tol:.1%} | {s['n']} | {s['max_abs']:.4g} | "
                   f"{s['mean_abs']:.4g} | {s['max_rel']:.2%} | {s['bad']} |")
    if res["worst"]:
        out += ["", f"Худшие {len(res['worst'])} (по превышению допуска):", "",
                f"| {table.key_title} | величина | эталон | кандидат | Δ |", "|---|---|---|---|---|"]
        for _, k, title, a, b in res["worst"]:
            out.append(f"| {k[0]}/{k[1]} | {title} | {a:.4g} | {b:.4g} | {b - a:+.4g} |")
    else:
        out += ["", "Все значения в допуске."]
    out.append("")
    return out, ok


async def compare(conn, base: int, new: int, top: int = 20) -> tuple[str, bool]:
    lines = [f"# Сравнение расчётов sety: #{base} (эталон) и #{new} (кандидат)\n"]
    for cid in (base, new):
        row = await conn.fetchrow(
            "SELECT id, fileid, tn, date1, name, user_gid, calc_params FROM calculation WHERE id = $1", cid)
        if row is None:
            raise SystemExit(f"Расчёт #{cid} не найден")
        lines.append(f"- #{cid}: фрагмент {row['fileid']}, Tн {row['tn']}, {row['date1']:%Y-%m-%d %H:%M}, "
                     f"«{row['name'] or ''}», автор {row['user_gid'] or '—'}")
        lines.append(f"  параметры: `{row['calc_params']}`")
    lines.append("")
    ok = True
    for table in TABLES:
        b, db = await _rows(conn, table, base)
        n, dn = await _rows(conn, table, new)
        part, t_ok = render_table(table, compare_rows(table, b, n, top), (db, dn))
        lines += part
        ok = ok and t_ok
    lines.append(f"**Итог:** {'совпадают в пределах допусков' if ok else 'есть расхождения — см. таблицы'}")
    return "\n".join(lines) + "\n", ok


async def main() -> int:
    import asyncpg
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=int, required=True, help="calculationid эталона (десктоп)")
    ap.add_argument("--new", type=int, required=True, help="calculationid кандидата (веб)")
    ap.add_argument("--out", type=str, default="", help="куда записать отчёт Markdown")
    ap.add_argument("--top", type=int, default=20, help="сколько худших строк показывать")
    ap.add_argument("--no-copy", action="store_true", help="не подгружать .env.copy")
    args = ap.parse_args()
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    if not args.no_copy and (root / ".env.copy").exists():
        load_dotenv(root / ".env.copy", override=True)
    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], database=os.environ["DB_NAME"],
    )
    try:
        report, ok = await compare(conn, args.base, args.new, args.top)
    finally:
        await conn.close()
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    sys.stdout.buffer.write(report.encode("utf-8"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
