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

--all — сверка движков (старый sety и heatnet): все таблицы, которые пишет sety (ALL_TABLES),
все колонки из information_schema; числа — с допуском --abs/--rel, текст — точно.

Нагрузки b101–b106 (ut_out) сверяются отдельно: суммы по видам, поучастково и тождество
b101 = b102+…+b106 у каждой стороны (раздел «Нагрузки»).

--ref-dir/--new-dir — сверка снимков (эталоны scripts/golden/run_reference.py) без БД: все
таблицы и колонки, допуски по классам величин (--tol-head/--tol-flow/--tol-temp/--tol-load,
--tol-rel), баланс и сообщения протокола; отчёт «что ушло и где» с именами узлов и участков.
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
    text: bool = False  # текстовая колонка: сравнение точное, без допуска


@dataclass(frozen=True)
class Table:
    title: str
    name: str
    key: tuple[str, ...]
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

# Таблицы, которые пишет sety (w_out2.w_out, dross1), и их ключи строк — для --all.
ALL_TABLES: dict[str, tuple[str, ...]] = {
    "us_out": ("nodeid", "externalsign"),
    "pt_out": ("nodeid", "ist"),
    "ut_out": ("lineid", "externalsignlineid"),
    "bp_out": ("lineid", "externalsignlineid"),
    "zd_out": ("lineid", "externalsignlineid"),
    "rs_out": ("lineid", "externalsignlineid"),
    "ns_out": ("lineid", "externalsignlineid"),
    "ok_out": ("lineid", "externalsignlineid"),
    "any_out": ("lineid", "externalsignlineid"),
    "any2_out": ("nodeid", "mesto", "externalsignlineid"),
    "dr_out": ("nodeid",),
}
_NUMERIC_TYPES = {"double precision", "real", "numeric", "integer", "smallint", "bigint"}


async def all_tables(conn, abs_tol: float, rel_tol: float) -> tuple[Table, ...]:
    """Все колонки таблиц ALL_TABLES из information_schema (кроме id, calculationid и ключа)."""
    tables = []
    for name, key in ALL_TABLES.items():
        rows = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position", name)
        cols = tuple(
            Col(r["column_name"], r["column_name"], abs_tol, rel_tol, text=r["data_type"] not in _NUMERIC_TYPES)
            for r in rows if r["column_name"] not in {"id", "calculationid", *key})
        if cols:
            tables.append(Table(name, name, key, "/".join(key), cols))
    return tuple(tables)


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
    if d == 0:
        return 0.0
    by_abs = d / col.abs_tol if col.abs_tol > 0 else math.inf
    by_rel = d / (abs(a) * col.rel_tol) if abs(a) > 0 and col.rel_tol > 0 else math.inf
    return min(by_abs, by_rel)


def _t(v) -> str:
    return "" if v is None else str(v).strip()


async def _rows(conn, table: Table, cid: int) -> tuple[dict, int]:
    cols = ", ".join(f'{c.column} AS "{c.column}"' for c in table.columns)
    keys = ", ".join(table.key)
    data: dict = {}
    dups = 0
    for r in await conn.fetch(f"SELECT {keys}, {cols} FROM {table.name} WHERE calculationid = $1", cid):
        key = tuple(r[k] for k in table.key)
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
            if col.text:
                ta, tb = _t(base[k][col.column]), _t(new[k][col.column])
                diffs.append(0.0)
                if ta != tb:
                    bad += 1
                    worst.append((math.inf, k, col.title, ta, tb))
                continue
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
        tol = "точно" if c.text else f"{c.abs_tol:g} или {c.rel_tol:.1%}"
        out.append(f"| {c.title} | {tol} | {s['n']} | {s['max_abs']:.4g} | "
                   f"{s['mean_abs']:.4g} | {s['max_rel']:.2%} | {s['bad']} |")
    if res["worst"]:
        out += ["", f"Худшие {len(res['worst'])} (по превышению допуска):", "",
                f"| {table.key_title} | величина | эталон | кандидат | Δ |", "|---|---|---|---|---|"]
        for _, k, title, a, b in res["worst"]:
            key = "/".join(str(x) for x in k)
            if isinstance(a, str):
                out.append(f"| {key} | {title} | {a} | {b} | — |")
            else:
                out.append(f"| {key} | {title} | {a:.4g} | {b:.4g} | {b - a:+.4g} |")
    else:
        out += ["", "Все значения в допуске."]
    out.append("")
    return out, ok


async def compare(conn, base: int, new: int, top: int = 20,
                  tables: tuple[Table, ...] = TABLES) -> tuple[str, bool]:
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
    for table in tables:
        b, db = await _rows(conn, table, base)
        n, dn = await _rows(conn, table, new)
        part, t_ok = render_table(table, compare_rows(table, b, n, top), (db, dn))
        lines += part
        ok = ok and t_ok
    lines.append(f"**Итог:** {'совпадают в пределах допусков' if ok else 'есть расхождения — см. таблицы'}")
    return "\n".join(lines) + "\n", ok


# ---------------------------------------------------------------------------------------------
# Нагрузки по участкам b101–b106 (ut_out): b101 — суммарная, b102 отопление, b103 вентиляция,
# b104 ГВС закрытое, b105 ГВС из подачи, b106 ГВС из обратки (sety/calc_nagr.NAGR_KEYS).
# В pt_out колонки b101… значат другое (коэффициент смешения, температура воздуха) — не нагрузки.

LOAD_KEYS = ("b101", "b102", "b103", "b104", "b105", "b106")
LOAD_TITLES = {"b101": "суммарная", "b102": "отопление", "b103": "вентиляция", "b104": "ГВС закрытое",
               "b105": "ГВС из подачи", "b106": "ГВС из обратки"}


def load_identity_violations(rows: dict, abs_tol: float, rel_tol: float) -> list[tuple[tuple, float, float]]:
    """Участки, где b101 ≠ b102+…+b106 сверх допуска: [(ключ, b101, сумма видов)]."""
    out = []
    for k, r in rows.items():
        total = _f(r.get("b101"))
        parts = sum(_f(r.get(c)) for c in LOAD_KEYS[1:])
        d = abs(total - parts)
        if d > abs_tol and d > abs(total) * rel_tol:
            out.append((k, total, parts))
    out.sort(key=lambda v: abs(v[1] - v[2]), reverse=True)
    return out


def compare_loads(base: dict, new: dict, abs_tol: float, rel_tol: float, top: int = 10,
                  names: dict | None = None) -> tuple[list[str], bool]:
    """Раздел отчёта: суммы и поучастковая сверка b101–b106, тождество b101 = b102+…+b106."""
    names = names or {}
    lines = ["## Нагрузки по участкам b101–b106 (ut_out)\n",
             f"Допуск {abs_tol:g} Гкал/ч или {rel_tol:.1%}.\n",
             "| вид | Σ эталон | Σ кандидат | Δ Σ | участков вне допуска | max abs Δ |", "|---|---|---|---|---|---|"]
    common = sorted(set(base) & set(new), key=str)
    ok = True
    for c in LOAD_KEYS:
        sb = sum(_f(r.get(c)) for r in base.values())
        sn = sum(_f(r.get(c)) for r in new.values())
        diffs = [abs(_f(base[k].get(c)) - _f(new[k].get(c))) for k in common]
        bad = sum(1 for k, d in zip(common, diffs) if d > abs_tol and d > abs(_f(base[k].get(c))) * rel_tol)
        ok = ok and bad == 0
        lines.append(f"| {c} {LOAD_TITLES[c]} | {sb:.4f} | {sn:.4f} | {sn - sb:+.4g} | {bad} | "
                     f"{max(diffs, default=0.0):.4g} |")
    lines.append("")
    for title, rows in (("эталон", base), ("кандидат", new)):
        viol = load_identity_violations(rows, abs_tol, rel_tol)
        lines.append(f"Тождество b101 = b102+…+b106, {title}: нарушено на {len(viol)} участках из {len(rows)}.")
        for k, total, parts in viol[:top]:
            lines.append(f"  - {_where('ut_out', k, names)}: b101 {total:.4f}, сумма видов {parts:.4f}")
    new_viol = {v[0] for v in load_identity_violations(new, abs_tol, rel_tol)}
    old_viol = {v[0] for v in load_identity_violations(base, abs_tol, rel_tol)}
    if new_viol - old_viol:
        ok = False
        lines.append(f"\n**Новые нарушения тождества у кандидата: {len(new_viol - old_viol)}.**")
    lines.append("")
    return lines, ok


# ---------------------------------------------------------------------------------------------
# Снимки расчётов — эталоны scripts/golden/run_reference.py. Каталог случая: meta.json
# (параметры, код sety, баланс и сообщения протокола) и <таблица>.csv (строки *_out без id и
# calculationid, ключ — первые колонки), objects.csv (имена узлов и участков для отчёта).

KIND_TITLES = {"head": "напор, м", "flow": "расход, т/ч", "temp": "температура, °C",
               "load": "нагрузка, Гкал/ч", "other": "прочее"}
# Допуски по умолчанию: (абсолютный, относительный); значение в допуске, если укладывается в любой.
DEFAULT_TOLERANCES: dict[str, tuple[float, float]] = {
    "head": (0.01, 0.001), "flow": (0.01, 0.001), "temp": (0.05, 0.001),
    "load": (1e-4, 0.001), "other": (0.001, 0.001),
}
BALANCE_TOLERANCE = (0.05, 0.001)  # баланс в протоколе печатается с шагом 0,1

_PT_FLOWS = " ".join(f"a{i}" for i in range(4, 18)) + " gsm gm gx ggws"
_PT_LOADS = ("qotz qotn " + " ".join(f"dop{i}" for i in range(12, 24)) + " qsum_z qras_gv_z qotz_treb "
             "qotn_treb qvent_treb qgvz_treb qgvop_treb qgvoo_treb qrez_treb qtreb qfact")
# Класс величины по таблице и колонке (смысл — из комментариев sety/out/*_out.py).
_KINDS: dict[str, dict[str, str]] = {
    "ut_out": {"head": "a15 a16 a17 a18 a19 a21", "flow": "a13", "temp": "t1 t2", "load": " ".join(LOAD_KEYS)},
    "us_out": {"head": "pih", "temp": "t t2"},
    "pt_out": {"head": "a21 a22 a23 gneob", "flow": _PT_FLOWS, "load": _PT_LOADS,
               "temp": "t1 t2 t01 t02 t03 t2co t2gws tv tg dop8 dop9 b102"},
    "ns_out": {"head": "a9 a11 a13 a15 a16", "flow": "a10 a12 a14"},
    "rs_out": {"flow": "a11"},
    "ok_out": {"flow": "ras"}, "any_out": {"flow": "ras"}, "any2_out": {"flow": "ras"},
}
COLUMN_KINDS: dict[tuple[str, str], str] = {
    (t, c): kind for t, kinds in _KINDS.items() for kind, cols in kinds.items() for c in cols.split()}
COLUMN_TITLES: dict[tuple[str, str], str] = {
    ("ut_out", "a7"): "длина", ("ut_out", "a8"): "диаметр", ("ut_out", "a10"): "скорость",
    ("ut_out", "a12"): "сопротивление", ("ut_out", "a13"): "расход", ("ut_out", "a14"): "уд. потери",
    ("ut_out", "a17"): "потери напора", ("ut_out", "a18"): "располаг. напор", ("ut_out", "a19"): "пьез. напор",
    ("ut_out", "t1"): "t на входе", ("ut_out", "t2"): "t остывания", ("ut_out", "tpot"): "теплопотери",
    ("us_out", "pih"): "пьез. напор", ("us_out", "t"): "температура", ("us_out", "ist"): "источник",
    ("pt_out", "a15"): "расход закр. сист.", ("pt_out", "a21"): "напор подачи", ("pt_out", "a22"): "напор обратки",
    ("pt_out", "a23"): "располаг. напор", ("pt_out", "t1"): "t1 на вводе", ("pt_out", "t2"): "t2 на выходе",
    ("pt_out", "qotz"): "нагрузка отопл.", ("pt_out", "qfact"): "нагрузка факт.", ("pt_out", "qtreb"): "нагрузка треб.",
    **{("ut_out", c): f"нагрузка {LOAD_TITLES[c]}" for c in LOAD_KEYS},
}


def column_kind(table: str, column: str) -> str:
    return COLUMN_KINDS.get((table, column.lower()), "other")


def snapshot_table(name: str, key: tuple[str, ...], columns: list[str], text_columns: set[str],
                   tolerances: dict[str, tuple[float, float]]) -> Table:
    cols = []
    for c in columns:
        kind = column_kind(name, c)
        abs_tol, rel_tol = tolerances[kind]
        title = f"{c} {COLUMN_TITLES.get((name, c), '')}".strip() + ("" if c in text_columns else f" ({KIND_TITLES[kind]})")
        cols.append(Col(title, c, abs_tol, rel_tol, text=c in text_columns))
    return Table(name, name, key, "/".join(key), tuple(cols))


@dataclass
class Snapshot:
    path: Path
    meta: dict
    tables: dict  # имя -> {ключ: {колонка: значение}}
    names: dict   # ("node"|"line", id) -> подпись


def _cell(v: str):
    return None if v == "" else v


def load_snapshot(path: Path) -> Snapshot:
    import csv
    import json

    path = Path(path)
    meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
    tables = {}
    for name, info in meta.get("tables", {}).items():
        key = tuple(info["key"])
        rows: dict = {}
        with open(path / f"{name}.csv", encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                r = {k: _cell(v) for k, v in r.items()}
                rows[tuple(None if r[k] is None else int(float(r[k])) for k in key)] = r
        tables[name] = rows
    names = {}
    if (path / "objects.csv").exists():
        with open(path / "objects.csv", encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                names[(r["kind"], int(r["id"]))] = r["name"]
    return Snapshot(path, meta, tables, names)


def _split_synthetic(rows: dict) -> tuple[dict, int]:
    """(строки с обычными ключами, число строк синтетических узлов с id < 0)."""
    real = {k: v for k, v in rows.items() if not (k and k[0] is not None and k[0] < 0)}
    return real, len(rows) - len(real)


def _where(table: str, key: tuple, names: dict) -> str:
    """«Где»: узел/участок с именем по ключу строки."""
    side = {1: "П", 2: "О"} if table == "us_out" else {2: "П", 3: "О"}
    if table in ("us_out", "pt_out", "dr_out", "any2_out"):
        label = names.get(("node", key[0]), "")
        extra = f" {side.get(key[1], key[1])}" if table == "us_out" and len(key) > 1 else ""
        return f"узел {key[0]}{extra}" + (f" «{label}»" if label else "")
    label = names.get(("line", key[0]), "")
    extra = f" {side.get(key[1], key[1])}" if len(key) > 1 else ""
    return f"участок {key[0]}{extra}" + (f" «{label}»" if label else "")


def compare_balance(base: list, new: list, tol: tuple[float, float] = BALANCE_TOLERANCE) -> tuple[list[str], bool]:
    """Баланс из протокола: [[строка, значение1, значение2], …] — сверка по строкам."""
    b = {r[0]: r[1:] for r in base}
    n = {r[0]: r[1:] for r in new}
    lines = ["## Баланс (протокол sety)\n", "| строка | эталон | кандидат | Δ |", "|---|---|---|---|"]
    ok = True
    for text in list(b) + [t for t in n if t not in b]:
        vb, vn = b.get(text), n.get(text)
        if vb is None or vn is None:
            ok = False
            lines.append(f"| {text} | {'—' if vb is None else vb} | {'—' if vn is None else vn} | **нет пары** |")
            continue
        pairs = [(x, y) for x, y in zip(vb, vn) if x is not None or y is not None]
        cells = []
        for x, y in pairs:
            d = _f(y) - _f(x)
            bad = abs(d) > tol[0] and abs(d) > abs(_f(x)) * tol[1]
            ok = ok and not bad
            cells.append(f"**{d:+.1f}**" if bad else f"{d:+.1f}")
        fmt = lambda v: " / ".join("—" if x is None else f"{x:.1f}" for x in v)  # noqa: E731
        lines.append(f"| {text} | {fmt(p[0] for p in pairs)} | {fmt(p[1] for p in pairs)} | {' / '.join(cells)} |")
    if not b and not n:
        lines.append("| (баланс не печатался) | | | |")
    lines.append("")
    return lines, ok


def compare_messages(base: list, new: list, top: int = 15) -> tuple[list[str], bool]:
    """Сообщения протокола (ошибки и предупреждения): [[важность, текст, повторов], …]."""
    from collections import Counter

    cb = Counter({(s, t): c for s, t, c in base})
    cn = Counter({(s, t): c for s, t, c in new})
    gone, came = cb - cn, cn - cb
    sev = {"error": "ошибка", "warning": "предупр."}
    lines = ["## Сообщения протокола\n",
             f"Ошибок/предупреждений: эталон {sum(1 for s, _ in cb if s == 'error')}/"
             f"{sum(1 for s, _ in cb if s == 'warning')}, кандидат {sum(1 for s, _ in cn if s == 'error')}/"
             f"{sum(1 for s, _ in cn if s == 'warning')} (разных текстов).\n"]
    for title, diff in (("Только в эталоне (пропали)", gone), ("Только в кандидате (появились)", came)):
        if not diff:
            continue
        lines.append(f"{title}: {sum(diff.values())}")
        for (s, t), c in diff.most_common(top):
            one = " ".join(t.split())
            lines.append(f"  - [{sev.get(s, s)}] ×{c} {one[:200]}")
        lines.append("")
    if not gone and not came:
        lines.append("Совпадают.\n")
    return lines, not gone and not came


def compare_snapshots(ref: Snapshot, new: Snapshot, tolerances: dict[str, tuple[float, float]] | None = None,
                      top: int = 20, check_protocol: bool = True) -> tuple[str, bool, dict]:
    """Сверка двух снимков: отчёт Markdown, итог и сводка {раздел: ok}."""
    tol = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    names = {**new.names, **ref.names}
    rm, nm = ref.meta, new.meta
    lines = [f"# Сверка с эталоном: {rm.get('case', ref.path.name)}\n"]
    for title, m in (("эталон", rm), ("кандидат", nm)):
        sety = m.get("sety", {})
        lines.append(f"- {title}: снят {m.get('captured_at', '?')}, sety {sety.get('hash', '?')[:12]} "
                     f"({sety.get('root', '?')}), база {m.get('db')}, расчёт #{m.get('calc_id')}, "
                     f"код выхода {m.get('returncode')}, {m.get('elapsed_s', 0):.1f} с")
    lines.append(f"- фрагмент {rm.get('fragment')}, Tн {rm.get('tn')}, аргументы: `{' '.join(rm.get('args', []))}`")
    lines.append("- допуски: " + ", ".join(f"{KIND_TITLES[k]} {a:g} или {r:.1%}" for k, (a, r) in tol.items()) + "\n")

    sections: dict[str, bool] = {"код выхода": rm.get("returncode") == nm.get("returncode")}
    if not sections["код выхода"]:
        lines.append(f"**Код выхода различается: {rm.get('returncode')} → {nm.get('returncode')}.**\n")

    summary = ["## Что ушло и где\n", "| таблица | величина | сравнено | вне допуска | max abs Δ | где хуже всего |",
               "|---|---|---|---|---|---|"]
    details: list[str] = []
    worst_all: list[tuple] = []
    synthetic: list[str] = []
    tables_ok = True
    for name in sorted(set(rm.get("tables", {})) | set(nm.get("tables", {}))):
        info = rm["tables"].get(name) or nm["tables"][name]
        if name not in rm.get("tables", {}) or name not in nm.get("tables", {}):
            tables_ok = False
            details.append(f"## {name}\n\nТаблица есть только в {'кандидате' if name in nm['tables'] else 'эталоне'}.\n")
            continue
        columns = [c for c in info["columns"] if c in nm["tables"][name]["columns"]]
        missing = set(info["columns"]) ^ set(nm["tables"][name]["columns"])
        table = snapshot_table(name, tuple(info["key"]), columns, set(info.get("text_columns", [])), tol)
        # Синтетические узлы sety (id < 0: внутренние узлы эквивалентных схем потребителей) нумеруются
        # заново при каждом расчёте — по ключу их не сравнить, сверяется только количество.
        b, sb = _split_synthetic(ref.tables[name])
        n, sn = _split_synthetic(new.tables[name])
        if sb or sn:
            synthetic.append(f"| {name} | {sb} | {sn} |")
        res = compare_rows(table, b, n, top=10**9)
        t_ok = (res["only_base"] == 0 and res["only_new"] == 0 and res["n_bad_values"] == 0 and not missing
                and sb == sn)
        tables_ok = tables_ok and t_ok
        if t_ok:
            continue
        details.append(f"## {name}\n")
        details.append(f"Строк: эталон {res['n_base']}, кандидат {res['n_new']}, только в эталоне "
                       f"{res['only_base']}, только в кандидате {res['only_new']}."
                       + (f" Колонки только с одной стороны: {', '.join(sorted(missing))}." if missing else ""))
        for title, keys in (("только в эталоне", sorted(set(b) - set(n), key=str)),
                            ("только в кандидате", sorted(set(n) - set(b), key=str))):
            if keys:
                details.append(f"- {title}: " + "; ".join(_where(name, k, names) for k in keys[:10])
                               + (" …" if len(keys) > 10 else ""))
        details.append("")
        by_col: dict[str, tuple] = {}
        for w in res["worst"]:
            by_col.setdefault(w[2], w)
            worst_all.append((w[0], name, *w[1:]))
        for s in res["stats"]:
            if s["bad"]:
                w = by_col.get(s["col"].title)
                summary.append(f"| {name} | {s['col'].title} | {s['n']} | {s['bad']} | {s['max_abs']:.4g} | "
                               f"{_where(name, w[1], names) if w else ''} |")
    if tables_ok:
        summary.append("| — | все таблицы в допуске | | | | |")
    sections["таблицы"] = tables_ok
    lines += summary + [""]
    if synthetic:
        lines += ["Синтетические узлы sety (id < 0) — сверяется только количество строк:\n",
                  "| таблица | эталон | кандидат |", "|---|---|---|", *synthetic, ""]
    if worst_all:
        worst_all.sort(key=lambda w: w[0], reverse=True)
        lines += [f"Худшие {min(top, len(worst_all))} значений (по превышению допуска):\n",
                  "| где | таблица | величина | эталон | кандидат | Δ | × допуска |", "|---|---|---|---|---|---|---|"]
        for ex, name, k, title, a, b in worst_all[:top]:
            if isinstance(a, str):
                lines.append(f"| {_where(name, k, names)} | {name} | {title} | {a} | {b} | — | текст |")
            else:
                lines.append(f"| {_where(name, k, names)} | {name} | {title} | {a:.4g} | {b:.4g} | {b - a:+.4g} | "
                             f"{ex:.3g} |")
        lines.append("")

    if "ut_out" in ref.tables and "ut_out" in new.tables:
        part, sections["нагрузки b101–b106"] = compare_loads(ref.tables["ut_out"], new.tables["ut_out"],
                                                              *tol["load"], names=names)
        lines += part
    part, sections["баланс"] = compare_balance(rm.get("balance", []), nm.get("balance", []))
    lines += part
    part, msg_ok = compare_messages(rm.get("protocol", []), nm.get("protocol", []))
    lines += part
    if check_protocol:
        sections["сообщения протокола"] = msg_ok
    lines += details
    ok = all(sections.values())
    verdict = "совпадает" if ok else "расходится: " + ", ".join(k for k, v in sections.items() if not v)
    lines.insert(1, f"**Итог: {verdict}.**\n")
    return "\n".join(lines) + "\n", ok, sections


def parse_tolerances(args) -> dict[str, tuple[float, float]]:
    tol = dict(DEFAULT_TOLERANCES)
    for kind in ("head", "flow", "temp", "load"):
        v = getattr(args, f"tol_{kind}", None)
        if v is not None:
            tol[kind] = (v, getattr(args, "tol_rel", None) or tol[kind][1])
        elif getattr(args, "tol_rel", None):
            tol[kind] = (tol[kind][0], args.tol_rel)
    return tol


def add_tolerance_args(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--tol-head", type=float, help=f"допуск напора, м (по умолчанию {DEFAULT_TOLERANCES['head'][0]:g})")
    ap.add_argument("--tol-flow", type=float, help=f"допуск расхода, т/ч ({DEFAULT_TOLERANCES['flow'][0]:g})")
    ap.add_argument("--tol-temp", type=float, help=f"допуск температуры, °C ({DEFAULT_TOLERANCES['temp'][0]:g})")
    ap.add_argument("--tol-load", type=float, help=f"допуск нагрузки, Гкал/ч ({DEFAULT_TOLERANCES['load'][0]:g})")
    ap.add_argument("--tol-rel", type=float, help="относительный допуск для всех классов (0.001 = 0,1 %%)")


async def _load_rows(conn, cid: int) -> dict:
    cols = ", ".join(LOAD_KEYS)
    return {(r["lineid"], r["externalsignlineid"]): dict(r) for r in await conn.fetch(
        f"SELECT lineid, externalsignlineid, {cols} FROM ut_out WHERE calculationid = $1", cid)}


def _snapshot_main(args) -> int:
    report, ok, _ = compare_snapshots(load_snapshot(args.ref_dir), load_snapshot(args.new_dir),
                                      parse_tolerances(args), args.top, not args.ignore_protocol)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    sys.stdout.buffer.write(report.encode("utf-8"))
    return 0 if ok else 1


async def main() -> int:
    import asyncpg
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", type=int, help="calculationid эталона (десктоп)")
    ap.add_argument("--new", type=int, help="calculationid кандидата (веб)")
    ap.add_argument("--ref-dir", type=Path, help="снимок-эталон (каталог случая run_reference.py) — без БД")
    ap.add_argument("--new-dir", type=Path, help="снимок-кандидат для --ref-dir")
    ap.add_argument("--ignore-protocol", action="store_true", help="не считать расхождением сообщения протокола")
    add_tolerance_args(ap)
    ap.add_argument("--out", type=str, default="", help="куда записать отчёт Markdown")
    ap.add_argument("--top", type=int, default=20, help="сколько худших строк показывать")
    ap.add_argument("--no-copy", action="store_true", help="не подгружать .env.copy")
    ap.add_argument("--all", action="store_true", help="все таблицы и колонки, которые пишет sety")
    ap.add_argument("--abs", type=float, default=0.01, help="абсолютный допуск для --all")
    ap.add_argument("--rel", type=float, default=0.001, help="относительный допуск для --all")
    ap.add_argument("--database", type=str, default="", help="база (вместо DB_NAME)")
    args = ap.parse_args()
    if args.ref_dir or args.new_dir:
        if not (args.ref_dir and args.new_dir):
            ap.error("--ref-dir и --new-dir задаются вместе")
        return _snapshot_main(args)
    if args.base is None or args.new is None:
        ap.error("нужны --base и --new (расчёты в БД) или --ref-dir и --new-dir (снимки)")
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env")
    if not args.no_copy and (root / ".env.copy").exists():
        load_dotenv(root / ".env.copy", override=True)
    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        database=args.database or os.environ["DB_NAME"],
    )
    try:
        tables = await all_tables(conn, args.abs, args.rel) if args.all else TABLES
        report, ok = await compare(conn, args.base, args.new, args.top, tables)
        tol = parse_tolerances(args)
        part, loads_ok = compare_loads(await _load_rows(conn, args.base), await _load_rows(conn, args.new),
                                       *tol["load"])
        report += "\n" + "\n".join(part)
        ok = ok and loads_ok
    finally:
        await conn.close()
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
    sys.stdout.buffer.write(report.encode("utf-8"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
