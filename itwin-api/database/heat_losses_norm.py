"""Нормативные тепловые потери — перенос десктопного модуля gid8 `python/poteriNewPg`.

Десктоп (gid8 gidview/gidrSlot.cpp → `poteriNewPg/tp_main.py norm d1 d2 город yes|no`) считает
потери SQL-представлениями и функциями из `poteriNewPg/functions/new/` (их нет ни в одной БД —
десктоп ставит их скриптом `functions/new/2.bat`) и выгружает результат в Excel. Здесь те же формулы
на Python, данные — те же таблицы, результаты — в БД:

  heatPipeSectionIst[Fragment]   → `load_inputs` (SQL тот же, без функций десктопа)
  getCoeff                       → `get_coeff`
  get_qq / interpolate_q_3       → `get_qq` / `interpolate_q_3`
  tempView                       → `temp_view`
  UT_KTP_OUT_view                → `ktp_beta`
  normMon[Fragment]              → `norm_mon`
  losesVolumesView[Fragment]     → `load_inputs` (часть PR, потребители) + `_volumes_tr`
  avgHeatLosesMonth[Fragment]    → `avg_heat_loses_month`
  листы Excel exportController   → `sheet_*` (МатХарМаг, МесТемп, НормыЗима, НормыЛето,
                                    МесПотери, ГодПотери)

Семантика NULL повторяет SQL: SUM пропускает NULL и даёт NULL, если все слагаемые NULL;
сравнение с NULL — «ложь» в IF/CASE. Нормы (`39_normy_teplovyh_poter`) и коэффициенты местных
потерь (`30_koeffitsienty_mestnyh_teplovyh_poter`) десктоп берёт через dblink из БД `sprav`
на том же сервере; веб читает их отдельным соединением к той же БД (`SPRAV_DB_NAME`).

Режим «по фрагменту» десктопа: TEMP_LINE/TEMP_NODE — выделенные в графе участки/узлы.
Веб: участки и узлы фрагмента (fileid) либо явный список участков.
Фактические потери (`fact`, таблицы *Fact) и листы потерь с водой (ПСВ, заполнение,
опрессовка, промывка, САРЗ, баки-аккумуляторы, ИТОГО) не перенесены.
"""

from __future__ import annotations

import calendar
import math
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Optional

import asyncpg

MODULE = "heat_losses_norm"

MONTH_NAMES = {
    1: "январь", 2: "февраль", 3: "март", 4: "апрель", 5: "май", 6: "июнь", 7: "июль",
    8: "август", 9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
    13: "отопит.период", 14: "летний период", 15: "среднегодовая",
}  # getMon десктопа

TYPNET_NAMES = {
    1: "Магистральные тепловые сети", 2: "Распределительные тепловые сети",
    3: "Районая котельная", 4: "РК сеть отопления", 5: "РК сеть ГВС", 6: "Источник тепла",
    7: "Насосная станция", 8: "ЦТРП", 9: "КРП", 10: "Камера", 11: "Котельная",
    12: "Участок магистрали", 20: "Тепловые сети в технических подвалах",
    30: "Трубопроводы обвязки насосных станций, узлов рассечки и баков-аккумуляторов",
}  # getTypnet десктопа

TUBING_LETTERS = {1: "К", 2: "Б", 3: "П", 4: "Н", 5: "О"}  # канальная, бесканальная, подвальная, надземная, обвязка

COEFF_BASES = ("Ms", "Rs", "Basement", "Harness")
COEFF_KINDS = ("Flow", "Ret", "Underground")
COEFF_COLUMNS = tuple(
    f"coeff{base}{kind}Norms{n}{suffix}".lower()
    for suffix in ("", "_r") for n in (1, 3) for base in COEFF_BASES for kind in COEFF_KINDS
)

S39_COLUMNS = (
    "d", "dy", "date", "proklad", "tg", "tn", "t2", "t1_1", "t1_2", "t1_3", "t1_4",
    "qp_1", "qo_1", "qp_2", "qo_2", "qp_3", "qo_3", "qp_4", "qo_4",
    "qp_1gt5000", "qo_1gt5000", "qp_2gt5000", "qo_2gt5000",
    "qp_3gt5000", "qo_3gt5000", "qp_4gt5000", "qo_4gt5000",
)


class HeatLossInputError(ValueError):
    """Нет данных для расчёта (сезон, источники, нормы)."""


# ---------------------------------------------------------------- NULL-арифметика SQL


def _nn(*values: Any) -> bool:
    return all(v is not None for v in values)


def _add(*values: Optional[float]) -> Optional[float]:
    return sum(values) if _nn(*values) else None  # type: ignore[arg-type]


def _mul(*values: Optional[float]) -> Optional[float]:
    if not _nn(*values):
        return None
    out = 1.0
    for v in values:
        out *= v  # type: ignore[operator]
    return out


def _sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return a - b if _nn(a, b) else None  # type: ignore[operator]


def _div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if not _nn(a, b):
        return None
    if b == 0:
        raise ZeroDivisionError("деление на ноль (в PostgreSQL — ошибка «division by zero»)")
    return a / b  # type: ignore[operator]


def _eq(a: Any, b: Any) -> bool:
    return a is not None and b is not None and a == b


def sql_sum(values: Iterable[Optional[float]]) -> Optional[float]:
    total: Optional[float] = None
    for v in values:
        if v is None:
            continue
        total = v if total is None else total + v
    return total


def sql_max(values: Iterable[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None]
    return max(vals) if vals else None


def pg_round(value: Optional[float], digits: int) -> Optional[float]:
    """ROUND(CAST(float8 AS NUMERIC), n): float8 → numeric даёт 15 значащих цифр, округление от нуля."""
    if value is None:
        return None
    d = Decimal(format(value, ".15g"))
    return float(d.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def _nulls_last(value: Any) -> tuple:
    return (value is None, value if value is not None else 0)


def _nulls_first_desc(value: Any) -> tuple:
    # ORDER BY x DESC: NULL первыми, затем по убыванию
    return (value is not None, -(value if value is not None else 0))


# ---------------------------------------------------------------- формулы десктопа


def get_coeff(po: int, sec: dict[str, Any]) -> Optional[float]:
    """getCoeff: коэффициент к нормам (испытания / по сети и прокладке) — подача po=1, обратка 2."""
    if _eq(sec.get("coeffdefault"), 0):
        return sec.get("heattestscoeff")
    if _eq(sec.get("piperemonttypeid"), 1):
        return 1
    c = {k: sec.get(k) for k in COEFF_COLUMNS}
    if _eq(sec.get("piperemonttypeid"), 2):
        for key in list(c):
            if not key.endswith("_r"):
                c[key] = c[key + "_r"]
    y = sec.get("y_norm")
    if y is not None and y != 1:
        for base in COEFF_BASES:
            for kind in COEFF_KINDS:
                c[f"coeff{base}{kind}norms1".lower()] = c[f"coeff{base}{kind}norms3".lower()]
    typnet = sec.get("typnet")
    src = "rs" if _eq(typnet, 2) else ("basement" if _eq(typnet, 20) else None)
    if src:
        for kind in COEFF_KINDS:
            c[f"coeffms{kind}norms1".lower()] = c[f"coeff{src}{kind}norms1".lower()]
    tt = sec.get("tubingtypeid")
    if tt in (1, 2):
        return c["coeffmsundergroundnorms1"]
    if po == 1:
        return c["coeffmsflownorms1"]
    return c["coeffmsretnorms1"]


def _lin(qa, qb, t, ta, tb):
    return _add(qa, _div(_mul(_sub(qb, qa), _sub(t, ta)), _sub(tb, ta)))


def _lt(a, b) -> bool:
    return a is not None and b is not None and a < b


def _ne(a, b) -> bool:
    return a is not None and b is not None and a != b


def interpolate_q_3(t, t1, t2, t3, t4, q1, q2, q3, q4) -> Optional[float]:
    """interpolate_q_3 десктопа: кусочно-линейная интерполяция нормы по 4 точкам."""
    if _lt(t, t2):
        return _lin(q1, q2, t, t1, t2)
    if _lt(t, t3) and _ne(t3, t2):
        return _lin(q2, q3, t, t2, t3)
    if _lt(t, t4) and _ne(t4, t3):
        return _lin(q3, q4, t, t3, t4)
    if _eq(t2, t3):
        return _lin(q1, q2, t, t1, t2)
    if _eq(t3, t4):
        return _lin(q2, q3, t, t2, t3)
    return _lin(q3, q4, t, t3, t4)


def get_qq(tt, y, kolwork, po, tg_p, tg_o, tgr, tpodv, tn, s39: dict[str, Any]) -> Optional[float]:
    """get_qq: норма удельных потерь (ккал/(ч·м)) при температурах месяца, po=1 подача, 2 обратка."""
    sfx = "gt5000" if _eq(kolwork, 1) else ""
    qp = [s39[f"qp_{i}{sfx}"] for i in range(1, 5)]
    qo = [s39[f"qo_{i}{sfx}"] for i in range(1, 5)]
    t1s = [s39[f"t1_{i}"] for i in range(1, 5)]
    t2 = s39["t2"]
    tn_st, tgr_st = s39["tn"], s39["tg"]
    above = _eq(tt, 4) or _eq(tt, 3)
    if above:
        t = tg_o if _eq(po, 2) else tg_p
    else:
        t = _div(_add(tg_p, tg_o), 2)
    if _eq(y, 1):
        if _eq(tt, 4):
            t = _sub(t, tn)
        elif _eq(tt, 3):
            t = _sub(t, tpodv)
        else:
            t = _sub(t, tgr)
    if _ne(y, 1):
        tn_st = 0
        tgr_st = 0
    if above:
        return interpolate_q_3(t, *[_sub(x, tn_st) for x in t1s], *qp)
    pts = [_sub(_div(_add(x, t2), 2), tgr_st) for x in t1s]
    return interpolate_q_3(t, *pts, *(qp if _eq(po, 1) else qo))


def ktp_beta(diameter_condit, tubing_type, s10: dict[int, dict[str, Any]]) -> Optional[float]:
    """UT_KTP_OUT_view + LEFT JOIN normMon: коэффициент местных потерь β по Ду и прокладке."""
    if diameter_condit is None or tubing_type is None:
        return None
    row_id = {2: 1, 1: 2, 3: 2, 4: 3}.get(tubing_type)
    row = s10.get(row_id) if row_id else None
    if row is None:
        return None
    if _nn(row.get("diametr")) and diameter_condit >= row["diametr"]:
        return row.get("beta_mag")
    return row.get("beta_rasp")


def temp_view(months: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    """tempView: месяцы источника + средние за отопительный (r=15), летний (r=16) периоды и год (r=17)."""
    by_source: dict[int, list[dict[str, Any]]] = {}
    for m in months:
        if m.get("heatsourceid") is None:
            continue
        by_source.setdefault(m["heatsourceid"], []).append(m)
    keys = ("tn", "tpod", "tgr", "tgp", "tgo", "tx")

    def weighted(rows):
        out = {}
        den = sql_sum(1 if _eq(r.get("workcount"), 0) else r.get("workcount") for r in rows)
        for k in keys:
            num = sql_sum(_mul(r.get(k), r.get("workcount")) for r in rows)
            out[k] = _div(num, den)
        out["workcount"] = sql_sum(r.get("workcount") for r in rows)
        return out

    result: dict[int, list[dict[str, Any]]] = {}
    for hid, rows in by_source.items():
        seen: set[tuple] = set()
        items: list[dict[str, Any]] = []

        def push(row: dict[str, Any]) -> None:
            key = (row["r"], row["m"], row["sezon"], *(row.get(k) for k in keys), row.get("workcount"))
            if key in seen:  # UNION убирает одинаковые строки
                return
            seen.add(key)
            items.append(row)

        seasons: dict[Any, list] = {}
        for r in rows:
            seasons.setdefault(r.get("sezon"), []).append(r)
        for sezon, srows in seasons.items():
            agg = weighted(srows)
            push({"r": 15 if _eq(sezon, 1) else 16, "m": 13 if _eq(sezon, 1) else 14, "sezon": sezon, **agg})
        for r in rows:
            push({"r": r.get("r"), "m": r.get("m"), "sezon": r.get("sezon"),
                  **{k: r.get(k) for k in keys}, "workcount": r.get("workcount")})
        push({"r": 17, "m": 15, "sezon": 3, **weighted(rows)})
        for row in items:
            avg = _div(_add(row["tgp"], row["tgo"]), 2)
            row["dt"] = _sub(avg, row["tx"])
            row["dtgr"] = _sub(avg, row["tgr"])
            row["dtpod"] = _sub(avg, row["tpod"])
        result[hid] = items
    return result


def section_coefficients(sections: list[dict[str, Any]]) -> None:
    """heatTestsCoeffP/O для участков (getCoeff), на месте."""
    for s in sections:
        s["heattestscoeffp"] = get_coeff(1, s)
        s["heattestscoeffo"] = get_coeff(2, s)


L1_KEY = ("heatsourceid", "typnet", "y_norm", "tubingtypeid", "signnumwork", "heattestscoeffp",
          "heattestscoeffo", "diameterexternal", "diametercondit", "diameterinternal")


def _s39_matches(group: dict[str, Any], s39_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tt = group["tubingtypeid"]
    if tt is None or group["y_norm"] is None:
        return []
    out = []
    for n in s39_rows:
        if not (_eq(group["diameterexternal"], n["d"]) or _eq(group["diametercondit"], n["dy"])):
            continue
        if not _eq(group["y_norm"], n["date"]):
            continue
        tt39 = 1 if n["proklad"] == "К" else (2 if n["proklad"] == "Б" else 4)
        if _eq(tt, tt39) or (tt in (3, 4, 5) and tt39 == 4):
            out.append(n)
    return out


def norm_mon(sections, s39_rows, tview, s10) -> list[dict[str, Any]]:
    """normMon: группы участков × строки норм × месяцы источника, qp/qo — нормы при температурах месяца."""
    groups: dict[tuple, dict[str, Any]] = {}
    for s in sections:
        key = tuple(s.get(k) for k in L1_KEY)
        g = groups.get(key)
        if g is None:
            g = groups[key] = {k: s.get(k) for k in L1_KEY}
            g["lenp"] = None
            g["leno"] = None
        g["lenp"] = sql_sum([g["lenp"], s.get("lenp")])
        g["leno"] = sql_sum([g["leno"], s.get("leno")])
    rows: list[dict[str, Any]] = []
    for g in groups.values():
        tv_rows = tview.get(g["heatsourceid"]) or []
        if not tv_rows:
            continue
        beta = ktp_beta(g["diametercondit"], g["tubingtypeid"], s10)
        for n in _s39_matches(g, s39_rows):
            for tv in tv_rows:
                args = (g["tubingtypeid"], g["y_norm"], g["signnumwork"])
                temps = (tv["tgp"], tv["tgo"], tv["tgr"], tv["tpod"], tv["tn"])
                rows.append({
                    "heatsourceid": g["heatsourceid"], "r": tv["r"], "m": tv["m"], "sezon": tv["sezon"],
                    "beta": beta, "typnet": g["typnet"], "tubingtypeid": g["tubingtypeid"],
                    "y_norm": g["y_norm"], "signnumwork": g["signnumwork"],
                    "diametercondit": g["diametercondit"], "diameterinternal": g["diameterinternal"],
                    "heattestscoeffp": g["heattestscoeffp"], "heattestscoeffo": g["heattestscoeffo"],
                    "qp": get_qq(*args, 1, *temps, n), "qo": get_qq(*args, 2, *temps, n),
                    "lenp": g["lenp"], "leno": g["leno"],
                })
    return rows


def _volumes_tr(sections) -> set:
    return {s["heatsourceid"] for s in sections if s.get("heatsourceid") is not None}


def avg_heat_loses_month(nm_rows, tview, sections, consumers, season, hls_rows) -> list[dict[str, Any]]:
    """avgHeatLosesMonth: средние за месяц потери, Гкал/ч; V1 — с утечкой, Vall — всего."""
    t1: dict[tuple, dict[str, Any]] = {}
    for r in nm_rows:
        key = (r["heatsourceid"], r["r"], r["m"], r["sezon"])
        acc = t1.setdefault(key, {"p": [], "o": [], "np": [], "no": [], "podz": [], "v": []})
        lp = _mul(r["qp"], r["lenp"], r["beta"], r["heattestscoeffp"])
        lo = _mul(r["qo"], r["leno"], r["beta"], r["heattestscoeffo"])
        tt = r["tubingtypeid"]
        under = tt in (1, 2)  # NULL NOT IN (1,2) — NULL → ветка ELSE
        acc["p"].append(lp)
        acc["o"].append(lo)
        acc["np"].append(lp if (tt is not None and not under) else 0)
        acc["no"].append(lo if (tt is not None and not under) else 0)
        acc["podz"].append(0 if under else _add(lp, lo))
        di = r["diameterinternal"]
        acc["v"].append(_div(_mul(_add(r["lenp"], r["leno"]), math.pi, None if di is None else (di / 1000) ** 2), 4))
    tr = _volumes_tr(sections)
    vols = {c["heatsourceid"]: c for c in consumers}
    a = season.get("a")
    out_rows: dict[tuple, dict[str, Any]] = {}
    for (hs, rr, mm, sezon), acc in t1.items():
        pot_p = _div(sql_sum(acc["p"]), 1e6)
        pot_o = _div(sql_sum(acc["o"]), 1e6)
        pot_np = _div(sql_sum(acc["np"]), 1e6)
        pot_no = _div(sql_sum(acc["no"]), 1e6)
        pot_podz = _div(sql_sum(acc["podz"]), 1e6)
        v = sql_sum(acc["v"])
        if hs in tr:
            c = vols.get(hs)
            vov = _add(c.get("vot"), c.get("vvent")) if c else None
            vgvs = c.get("vgvs") if c else None
        else:
            vov = vgvs = None
        tv_match = [tv for tv in tview.get(hs) or [] if _eq(tv["r"], rr) and tv["m"] is not None and tv["m"] <= 120]
        hls_match = [h for h in hls_rows if _eq(h.get("heatsourceid"), hs)] or [{}]
        for tv in tv_match:
            gkey = (hs, rr, mm, sezon, tv["tgp"], tv["tgo"], tv["tx"], tv["dt"])
            o = out_rows.setdefault(gkey, {"np": [], "no": [], "podz": [], "all": [], "v1": [], "vall": []})
            for h in hls_match:
                k_summer = 1 if _eq(sezon, 1) else _add(0.5, _div(h.get("t_percent"), 200))
                vol = _add(_mul(v, k_summer), (vov if vov is not None else 0) * (1 if _eq(sezon, 1) else 0),
                           vgvs if vgvs is not None else 0)
                leak = _mul(_div(_mul(vol, a), 100), tv["dt"])
                o["np"].append(pot_np)
                o["no"].append(pot_no)
                o["podz"].append(pot_podz)
                o["all"].append(_add(pot_p, pot_o))
                o["v1"].append(leak)
                o["vall"].append(_add(pot_p, pot_o, _div(leak, 1000)))
    result = []
    for (hs, rr, mm, sezon, *_), o in out_rows.items():
        result.append({
            "heatsourceid": hs, "r": rr, "m": mm, "sezon": sezon,
            "potnp": sql_sum(o["np"]), "potno": sql_sum(o["no"]), "potpodz": sql_sum(o["podz"]),
            "potall": sql_sum(o["all"]), "v1": _div(sql_sum(o["v1"]), 1000), "vall": sql_sum(o["vall"]),
        })
    return result


# ---------------------------------------------------------------- листы Excel десктопа


def sheet_material_characteristics(sections, sources) -> list[dict[str, Any]]:
    """Матхар.sql: материальная характеристика сети по источнику, типу сети и диаметру."""
    inner: dict[tuple, dict[str, list]] = {}
    for s in sections:
        tt = s.get("tubingtypeid")
        lp, lo = s.get("lenp"), s.get("leno")
        vals = {
            "lenp_k": lp if tt == 1 else 0, "leno_k": lo if tt == 1 else 0,
            "lenp_b": lp if tt == 2 else 0, "leno_b": lo if tt == 2 else 0,
            "lenp_n": lp if tt in (3, 4, 5) else 0, "leno_n": lo if tt in (3, 4, 5) else 0,
        }
        di = s.get("diameterinternal")
        vals["vv"] = _div(_div(_div(_mul(_add(lp, lo), di, di, math.pi), 4), 1000), 1000)
        key = (s.get("heatsourceid"), s.get("typnet"), s.get("diameterexternal"),
               s.get("diametercondit"), di)
        acc = inner.setdefault(key, {k: [] for k in (*vals, "mp_p", "mp_o", "m")})
        de = s.get("diameterexternal")
        for k, v in vals.items():
            acc[k].append(v)
        acc["mp_p"].append(_mul(_add(vals["lenp_k"], vals["lenp_b"]), de, 0.001))
        acc["mp_o"].append(_mul(_add(vals["leno_k"], vals["leno_b"]), de, 0.001))
        # десктоп: lenP_N + lenP_N (а не lenO_N) — перенесено как есть
        acc["m"].append(_mul(_add(vals["lenp_n"], vals["lenp_n"], vals["lenp_k"], vals["leno_k"],
                                  vals["lenp_b"], vals["leno_b"]), de))
    mid: dict[tuple, dict[str, list]] = {}
    for (hs, typnet, de, dc, di), acc in inner.items():
        sums = {k: sql_sum(v) for k, v in acc.items()}
        sums["mn_p"] = _mul(sums["lenp_n"], de, 0.001)
        sums["mn_o"] = _mul(sums["leno_n"], de, 0.001)
        sums["m"] = _mul(sums["m"], 0.001)
        o = mid.setdefault((hs, typnet, de, di), {})
        for k, v in sums.items():
            o.setdefault(k, []).append(v)
    rows = []
    for (hs, typnet, de, di), acc in mid.items():
        t = {k: sql_sum(v) for k, v in acc.items()}
        rows.append({
            "heatsourceid": hs, "ist": (sources.get(hs) or {}).get("sourcename"),
            "typnet": typnet, "typnet1": TYPNET_NAMES.get(typnet, "Неизвестные тепловые сети"),
            "diameterexternal": de, "diameterinternal": di,
            "lenp_n": t["lenp_n"], "leno_n": t["leno_n"],
            "lenpodzp": _add(t["lenp_k"], t["lenp_b"]), "lenpodzo": _add(t["leno_k"], t["leno_b"]),
            "lenall": _add(t["lenp_n"], t["leno_n"], t["lenp_k"], t["leno_k"], t["lenp_b"], t["leno_b"]),
            "len_tr": _add(t["lenp_n"], t["lenp_k"]),
            "mn_p": t["mn_p"], "mn_o": t["mn_o"], "mp_p": t["mp_p"], "mp_o": t["mp_o"],
            "m": t["m"], "vv": t["vv"],
        })
    rows.sort(key=lambda r: (_nulls_last(r["heatsourceid"]), _nulls_last(r["typnet"]),
                             _nulls_last(r["diameterexternal"])))
    return rows


def sheet_month_temperatures(months, sources) -> list[dict[str, Any]]:
    """Начальные.sql: условия работы по месяцам + средние по сезонам и за год."""
    rows = []
    for hs, items in temp_view(months).items():
        for tv in items:
            # Начальные.sql нумерует сводные строки 14/15/16 (tempView — 15/16/17)
            r = {15: 14, 16: 15, 17: 16}.get(tv["r"], tv["r"]) if tv["m"] in (13, 14, 15) else tv["r"]
            sezon = tv["sezon"]
            rows.append({
                "heatsourceid": hs, "r": r, "m": tv["m"], "sourcename": (sources.get(hs) or {}).get("sourcename"),
                "m1": MONTH_NAMES.get(tv["m"], "???"),
                "sezon1": "Отопительный" if _eq(sezon, 1) else ("Летний" if _eq(sezon, 2) else ""),
                **{k: pg_round(tv[k], 1) for k in ("tn", "tpod", "tgr", "tgp", "tgo", "tx")},
                "workcount": tv["workcount"],
            })
    rows.sort(key=lambda r: (_nulls_last(r["heatsourceid"]), _nulls_last(r["r"]), r["m"] or 0))
    return rows


def _norms_sheet(nm_rows, sources, m: int) -> list[dict[str, Any]]:
    inner: dict[tuple, dict[str, list]] = {}
    for r in nm_rows:
        if not _eq(r["m"], m):
            continue
        key = (r["heatsourceid"], r["typnet"], r["tubingtypeid"], r["y_norm"], r["diameterinternal"],
               r["diametercondit"], r["signnumwork"], r["heattestscoeffp"], r["heattestscoeffo"],
               r["qp"], r["qo"], r["beta"])
        acc = inner.setdefault(key, {"potp": [], "poto": [], "lenp": [], "leno": []})
        acc["potp"].append(_mul(r["qp"], r["lenp"], r["beta"], r["heattestscoeffp"]))
        acc["poto"].append(_mul(r["qo"], r["leno"], r["beta"], r["heattestscoeffo"]))
        acc["lenp"].append(r["lenp"])
        acc["leno"].append(r["leno"])
    outer: dict[tuple, dict[str, list]] = {}
    for (hs, typnet, tt, y, di, dc, snw, cp, co, qp, qo, beta), acc in inner.items():
        potp, poto = sql_sum(acc["potp"]), sql_sum(acc["poto"])
        lenp, leno = sql_sum(acc["lenp"]), sql_sum(acc["leno"])
        o = outer.setdefault((hs, typnet, snw, y, dc), {})
        n = tt in (3, 4, 5)
        vals = {
            "lennp": lenp if n else 0, "lenno": leno if n else 0,
            "qnp": qp if n else 0, "qno": qo if n else 0,
            "potnp": potp if n else 0, "potno": poto if n else 0,
            "lenkp": lenp if tt == 1 else 0, "lenko": leno if tt == 1 else 0,
            "qk": _add(qp, qo) if tt == 1 else 0, "potkp": potp if tt == 1 else 0, "potko": poto if tt == 1 else 0,
            "lenbp": lenp if tt == 2 else 0, "lenbo": leno if tt == 2 else 0,
            "qb": _add(qp, qo) if tt == 2 else 0, "potbp": potp if tt == 2 else 0, "potbo": poto if tt == 2 else 0,
        }
        for k, v in vals.items():
            o.setdefault(k, []).append(v)
    rows = []
    for (hs, typnet, snw, y, dc), acc in outer.items():
        t = {k: (sql_max(v) if k in ("qnp", "qno", "qk", "qb") else sql_sum(v)) for k, v in acc.items()}
        if _eq(y, 1):
            a5000 = "Класс 1"
        else:
            work = "рабочий" if _ne(snw, 0) else "нерабочий"
            a5000 = f"Класс {'' if y is None else y}, {work} 5000 часов работы"
        rows.append({
            "heatsourceid": hs, "ist": (sources.get(hs) or {}).get("sourcename"),
            "typnet": typnet, "typnet1": TYPNET_NAMES.get(typnet, "Неизвестные тепловые сети"),
            "y_norm": y, "signnumwork": snw, "a5000": a5000, "diametercondit": dc,
            **{k: pg_round(t[k], 2) for k in ("lennp", "lenno", "qnp", "qno", "lenkp", "lenko", "qk",
                                              "lenbp", "lenbo", "qb")},
            "potnp": pg_round(t["potnp"], 1), "potno": pg_round(t["potno"], 1),
            "potp": pg_round(_add(t["potkp"], t["potbp"], t["potko"], t["potbo"]), 1),
        })
    rows.sort(key=lambda r: (_nulls_last(r["heatsourceid"]), _nulls_last(r["typnet"]),
                             _nulls_last(r["y_norm"]), _nulls_first_desc(r["signnumwork"]),
                             _nulls_last(r["diametercondit"])))
    return rows


def sheet_winter_norms(nm_rows, sources):
    """Потери.sql по normMon m=13: нормы и часовые потери за отопительный период по диаметрам."""
    return _norms_sheet(nm_rows, sources, 13)


def sheet_summer_norms(nm_rows, sources):
    """Потери_лето.sql по normMon m=14."""
    return _norms_sheet(nm_rows, sources, 14)


def _month_join(ahlm, months, sources, month_names):
    by_key: dict[tuple, list] = {}
    for hm in months:
        by_key.setdefault((hm.get("heatsourceid"), hm.get("r")), []).append(hm)
    joined = []
    for row in sorted(ahlm, key=lambda x: (_nulls_last(x["heatsourceid"]), _nulls_last(x["r"]))):
        for hm in by_key.get((row["heatsourceid"], row["r"]), [None]):
            joined.append((row, hm))
    return joined


def sheet_avg_month_loses(ahlm, months, sources, month_names) -> list[dict[str, Any]]:
    """Потери среднемесячные: Гкал/ч по месяцам и периодам."""
    out = []
    for row, _hm in _month_join(ahlm, months, sources, month_names):
        out.append({
            "heatsourceid": row["heatsourceid"], "r": row["r"], "m": row["m"], "sezon": row["sezon"],
            "name": (sources.get(row["heatsourceid"]) or {}).get("name"),
            "monthname": month_names.get(row["m"]),
            **{k: row[k] for k in ("potnp", "potno", "potpodz", "potall", "v1", "vall")},
        })
    return out


def sheet_avg_year_loses(ahlm, months, sources, month_names) -> list[dict[str, Any]]:
    """Потери годовые: Гкал за месяц = Гкал/ч × число суток работы × 24."""
    out = []
    for row, hm in _month_join(ahlm, months, sources, month_names):
        wc = hm.get("workcount") if hm else None
        out.append({
            "heatsourceid": row["heatsourceid"], "r": row["r"], "m": row["m"],
            "name": (sources.get(row["heatsourceid"]) or {}).get("name"),
            "monthname": month_names.get(row["m"]), "season": row["sezon"],
            **{k: pg_round(_mul(row[k], wc, 24), 2) for k in ("potnp", "potno", "potpodz", "potall", "v1", "vall")},
        })
    return out


def year_totals(year_rows: list[dict[str, Any]]) -> dict[int, dict[str, dict[str, float]]]:
    """Итоги листа ГодПотери: отопительный, летний период и год (первые 14 строк источника).

    Десктоп в «ИТОГО (лет.)» пишет последнюю летнюю строку, а не сумму (присваивание вместо +=);
    здесь — сумма.
    """
    keys = ("potnp", "potno", "potpodz", "potall", "v1", "vall")
    result: dict[int, dict[str, dict[str, float]]] = {}
    per_source: dict[int, list] = {}
    for r in year_rows:
        per_source.setdefault(r["heatsourceid"], []).append(r)
    for hs, rows in per_source.items():
        tot = {p: {k: 0.0 for k in keys} for p in ("heating", "summer", "year")}
        for r in rows[:14]:
            period = "heating" if _eq(r["season"], 1) else "summer"
            for k in keys:
                if r[k] is not None:
                    tot[period][k] += r[k]
                    tot["year"][k] += r[k]
        result[hs] = {p: {k: round(v, 6) for k, v in vals.items()} for p, vals in tot.items()}
    return result


# ---------------------------------------------------------------- удельные потери по участкам


def _month_values(per_r: list[tuple[dict[str, Any], Optional[float]]]) -> dict[str, Optional[float]]:
    out: dict[str, Optional[float]] = {}
    for month in range(1, 13):
        parts = [(tv, q) for tv, q in per_r if _eq(tv["m"], month) and tv["r"] is not None and tv["r"] <= 14]
        vals = [(tv, q) for tv, q in parts if q is not None]
        wsum = sum((tv.get("workcount") or 0) for tv, _ in vals)
        if not vals:
            val = None
        elif wsum > 0:
            val = sum(q * (tv.get("workcount") or 0) for tv, q in vals) / wsum
        else:
            val = sum(q for _, q in vals) / len(vals)
        out[f"q{month:02d}"] = val
    annual = [q for tv, q in per_r if _eq(tv["r"], 17)]
    out["q"] = annual[0] if annual else None
    return out


def section_results(sections, s39_rows, tview, s10) -> list[dict[str, Any]]:
    """Удельные нормативные потери участка по месяцам — строки ut_teplo_out (подача/обратка).

    q01…q12 — ккал/(ч·м) за месяц (апрель/октябрь — средние по числу суток отопительной и летней
    частей), q — среднегодовая (строка tempView r=17). Потери участка, Гкал/ч = q·длина·β·K/10⁶ —
    то же слагаемое, что в normMon/avgHeatLosesMonth. Если нормы подходят несколькими строками
    (Дн и Ду разных строк), десктоп считает каждую — здесь q суммируется так же.
    """
    out = []
    cache: dict[tuple, Optional[dict[int, dict[str, Optional[float]]]]] = {}
    for s in sections:
        key = (s.get("heatsourceid"), s.get("tubingtypeid"), s.get("y_norm"), s.get("signnumwork"),
               s.get("diameterexternal"), s.get("diametercondit"))
        if key not in cache:
            tv_rows = tview.get(s.get("heatsourceid")) or []
            matches = _s39_matches(s, s39_rows) if tv_rows else []
            if not matches:
                cache[key] = None
            else:
                by_po = {}
                for po in (1, 2):
                    per_r = [(tv, sql_sum(get_qq(s.get("tubingtypeid"), s.get("y_norm"), s.get("signnumwork"), po,
                                                 tv["tgp"], tv["tgo"], tv["tgr"], tv["tpod"], tv["tn"], n)
                                          for n in matches)) for tv in tv_rows]
                    by_po[po] = _month_values(per_r)
                cache[key] = by_po
        by_po = cache[key]
        if by_po is None:
            continue
        beta = ktp_beta(s.get("diametercondit"), s.get("tubingtypeid"), s10)
        for truba, length, coeff in ((1, s.get("lenp"), s.get("heattestscoeffp")),
                                     (2, s.get("leno"), s.get("heattestscoeffo"))):
            if not length:
                continue
            out.append({
                "section_id": s["section_id"], "lineid": s.get("lineid"),
                "externalsignlineid": s.get("externalsignlineid"), "truba": truba,
                "diametr": s.get("diameterinternal"), "tol": s.get("wallthickness"),
                "diametr_usl": s.get("diametercondit"), "dlina": length,
                "name_typ": TUBING_LETTERS.get(s.get("tubingtypeid")), "kti": coeff,
                "kolwork": s.get("signnumwork"), "kod_owner": s.get("org_id"), "year": s.get("y_norm"),
                "kod_ist": str(s.get("heatsourceid")), "beta": beta, "typnet": s.get("typnet"),
                "heatsourceid": s.get("heatsourceid"), **by_po[truba],
            })
    return out


# ---------------------------------------------------------------- «Условия работы» (heatLosesSourceMonths)


def temp_graph_maps(graph_rows: list[dict[str, Any]]):
    """MainController.init_temp_graph: развёрнутые графики deployedTempGraphs по источникам."""
    map_tg: dict[int, dict[float, dict]] = {}
    bounds: dict[int, dict[str, float]] = {}
    old = -1
    for row in sorted(graph_rows, key=lambda r: (r["hsourceid"], r["tn"])):
        hs = row["hsourceid"]
        if hs != old:
            bounds.setdefault(hs, {})["tn1"] = row["tn"]
            old = hs
        bounds[hs]["tn2"] = row["tn"]
        map_tg.setdefault(hs, {})[row["tn"]] = row
    return map_tg, bounds


def temp_graph_at(map_tg, bounds, hs: int, tn: float):
    """MainController.get_temp_graph: t1/t2 графика в первой точке сетки с tнв ≥ tn (без интерполяции)."""
    b = bounds.get(hs)
    if b is None:
        return None, None
    tn1, tn2 = b.get("tn1", -32), b.get("tn2", 8)
    if tn > tn2 + 0.001:
        tn = b["tn2"]
    if tn < tn1 - 0.001:
        tn = b["tn1"]
    for key, row in (map_tg.get(hs) or {}).items():
        if tn <= key:
            return row["t1"], row["t2"]
    return None, None


def _sredn1(t_a, t_b, days, month, year):
    d30 = calendar.monthrange(year, month)[1]
    return ((t_a + t_b) / 2 * days + t_b * (d30 - days)) / d30


def _sredn2(t_b, t_c, days, month, year):
    d30 = calendar.monthrange(year, month)[1]
    return ((t_b + t_c) / 2 * (d30 - days) + t_b * days) / d30


def work_condition_months(heat_source_id: int, climate: list[dict[str, Any]], start: date, end: date,
                          map_tg, bounds) -> list[dict[str, Any]]:
    """MainController.set_cond_env_temperatures: 14 строк heatLosesSourceMonths источника.

    climate — 12 месяцев (tn, tpod, tgr); месяцы начала и конца отопительного сезона делятся на
    отопительную (sezon=1) и летнюю (sezon=2) части с усреднением температур (sredn1/sredn2).
    ValueError, если температурный график источника не развёрнут (десктоп прерывает запись).
    """
    by_month = {int(c["m"]): c for c in climate}
    if sorted(by_month) != list(range(1, 13)):
        raise HeatLossInputError("Нужны климатические данные (tн, tподв, tгр) за все 12 месяцев")
    air = [float(by_month[m]["tn"]) for m in range(1, 13)]
    podv = [float(by_month[m]["tpod"]) for m in range(1, 13)]
    grnd = [float(by_month[m]["tgr"]) for m in range(1, 13)]
    rows: list[dict[str, Any]] = []
    number = 0

    def graph(tn):
        tp, to = temp_graph_at(map_tg, bounds, heat_source_id, tn)
        if tp is None or to is None:
            raise HeatLossInputError(f"Температурный график источника {heat_source_id} не развёрнут")
        return tp, to

    def add(number, month, sezon, tn, tpod, tgr, days):
        tp, to = graph(tn)
        rows.append({"heatsourceid": heat_source_id, "r": number, "m": month, "sezon": sezon, "tn": tn,
                     "tpod": tpod, "tgr": tgr, "tgp": tp, "tgo": to, "workcount": days})

    for month in range(1, 13):
        number += 1
        i = month - 1
        t2, t1, t3 = air[i], (air[i - 1] if month >= 2 else air[i]), (air[i + 1] if month < 12 else air[i])
        p2, p1, p3 = podv[i], (podv[i - 1] if month >= 2 else podv[i]), (podv[i + 1] if month < 12 else podv[i])
        g2, g1, g3 = grnd[i], (grnd[i - 1] if month >= 2 else grnd[i]), (grnd[i + 1] if month < 12 else grnd[i])
        md = calendar.monthrange(end.year, month)[1]
        if month == end.month:
            d = end.day
            add(number, month, 1, _sredn1(t1, t2, d, month, end.year), _sredn1(p1, p2, d, month, end.year),
                _sredn1(g1, g2, d, month, end.year), d)
            number += 1
            add(number, month, 2, _sredn2(t2, t3, d, month, end.year), _sredn2(p2, p3, d, month, end.year),
                _sredn2(g2, g3, d, month, end.year), md - d)
        elif month == start.month:
            d = start.day - 1
            add(number, month, 2, _sredn1(t1, t2, d, month, start.year), _sredn1(p1, p2, d, month, start.year),
                _sredn1(g1, g2, d, month, start.year), d)
            number += 1
            add(number, month, 1, _sredn2(t2, t3, d, month, start.year), _sredn2(p2, p3, d, month, start.year),
                _sredn2(g2, g3, d, month, start.year), md - start.day + 1)
        else:
            sezon = 2 if end.month < month < start.month else 1
            add(number, month, sezon, t2, p2, g2, md)
    return rows


# ---------------------------------------------------------------- загрузка данных


SECTIONS_SQL = """
SELECT * FROM (
    SELECT hps.id AS section_id, hps.lineid, l.externalsignlineid, l.organizationid AS org_id,
           l.fileid, ec2.objectid,
           CASE WHEN ec2.objectid <> 2 OR ecm.heatsourceid IS NULL THEN ec2.heatsourceid
                ELSE ecm.heatsourceid END AS heatsourceid,
           CASE WHEN EXTRACT(YEAR FROM hps.lasttransdate) < 1990 THEN 1
                WHEN EXTRACT(YEAR FROM hps.lasttransdate) < 1998 THEN 2
                WHEN EXTRACT(YEAR FROM hps.lasttransdate) <= 2003 THEN 3 ELSE 4 END AS y_norm,
           hps.diameterexternal, hps.diametercondit, hps.diameterinternal, hps.wallthickness,
           hps.tubingtypeid, hps.heattestscoeff, hps.piperemonttypeid, hls.coeffdefault,
           {coeffs},
           CASE WHEN hps.tubingtypeid = 3 THEN 20 WHEN hps.tubingtypeid = 5 THEN 30
                ELSE CASE ec2.objectid WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 10 THEN 3 WHEN 11 THEN 4
                     WHEN 12 THEN 5 WHEN 3 THEN 6 WHEN 4 THEN 7 WHEN 5 THEN 8 WHEN 6 THEN 9
                     WHEN 7 THEN 10 WHEN 8 THEN 11 WHEN 9 THEN 12 ELSE 40 END END AS typnet,
           CASE WHEN EXTRACT(YEAR FROM hps.lasttransdate) < 1990 THEN 1 ELSE hps.signnumwork END AS signnumwork,
           CASE WHEN l.externalsignlineid IN (1, 2, 4) THEN hps.pipesectlength ELSE 0 END AS lenp,
           CASE WHEN l.externalsignlineid IN (1, 3, 5) THEN hps.pipesectlength ELSE 0 END AS leno
      FROM heatpipesections hps
      LEFT JOIN linesobj l ON l.id = hps.lineid
      LEFT JOIN nodes n2 ON n2.id = l.nodeid2
      LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
      LEFT JOIN externalcodes ecm ON ec2.belongmagistral = ecm.id AND ec2.objectid = 2
      LEFT JOIN heatlosessource hls ON hls.heatsourceid =
                CASE WHEN ec2.objectid <> 2 OR ecm.heatsourceid IS NULL THEN ec2.heatsourceid
                     ELSE ecm.heatsourceid END
     WHERE n2.internalnodeid IS NULL AND l.removed = 0 {line_filter}
) hpsi
 WHERE {source_filter}
 ORDER BY hpsi.section_id
""".replace("{coeffs}", ", ".join(f"hls.{c}" for c in COEFF_COLUMNS))

# losesVolumesView, часть PR: объёмы воды систем потребителей (realConsumers2 = реальные + обобщённые)
CONSUMER_VOLUMES_SQL = """
WITH rc2 AS (
    SELECT nodeid, calchldep, calchlindep, calchlventil, avghlgvsopenflow, avghlgvsopenret,
           avghlgvscloseparall, avghlgvsclosemix, avghlgvscloseconseq, avghlgvsclosepreon,
           volwaterhs, volwatervs, buildingtypeid
      FROM realconsumers
    UNION ALL
    SELECT gc.nodeid, gc.calchldep + gc.calchlparall + gc.calchlconseq + gc.calchlmix + gc.calchlpreon,
           gc.calchlindep, gc.calchlventil, gc.avghlgvsopensysflow, gc.avghlgvsopensysret,
           gc.calchlgvsparall, gc.calchlgvsmix, gc.calchlgvsconseq, gc.calchlgvspreon,
           gc.volwaterhs, gc.volwatervs, 1
      FROM generalizedconsumers gc
      JOIN nodes n ON n.id = gc.nodeid
      JOIN externalcodes ec ON ec.id = n.externalcodeid
     WHERE ec.objectid <> 1 AND ec.objectid <> 9
)
SELECT t.heatsourceid, SUM(t.got_pr * t.volwaterhs) AS vot, SUM(t.gvent_pr * t.volwatervs) AS vvent,
       SUM(t.ggvs_pr * t.volwateropengvs) AS vgvs
  FROM (
    SELECT ec.heatsourceid,
           SUM(rc.calchldep + rc.calchlindep) AS got_pr,
           SUM(rc.calchlventil) AS gvent_pr,
           SUM(rc.avghlgvsopenflow + rc.avghlgvsopenret + rc.avghlgvscloseparall + rc.avghlgvsclosemix
               + rc.avghlgvscloseconseq + rc.avghlgvsclosepreon) AS ggvs_pr,
           COALESCE(rc.volwaterhs, 0) AS volwaterhs, COALESCE(rc.volwatervs, 0) AS volwatervs,
           hlm.volwateropengvs
      FROM rc2 rc
      JOIN nodes n ON n.id = rc.nodeid
      LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
      JOIN heatlosesmain hlm ON hlm.id = $1
     WHERE n.removed = 0 {node_filter}
     GROUP BY hlm.volwaterhs, hlm.volwatervs, hlm.volwateropengvs, rc.volwaterhs, rc.volwatervs,
              ec.heatsourceid
  ) t
 GROUP BY t.heatsourceid
"""


@dataclass
class HeatLossInputs:
    season: dict[str, Any]
    heat_source_ids: list[int]
    sources: dict[int, dict[str, Any]]
    sections: list[dict[str, Any]]
    months: list[dict[str, Any]]
    hls_rows: list[dict[str, Any]]
    consumers: list[dict[str, Any]]
    s39: list[dict[str, Any]]
    s10: dict[int, dict[str, Any]]
    month_names: dict[int, str] = field(default_factory=dict)
    fragment_id: Optional[int] = None
    line_ids: Optional[list[int]] = None


def sprav_db_config() -> dict[str, Any]:
    return {
        "user": os.getenv("SPRAV_DB_USER") or os.getenv("DB_USER"),
        "password": os.getenv("SPRAV_DB_PASSWORD") or os.getenv("DB_PASSWORD"),
        "host": os.getenv("SPRAV_DB_HOST") or os.getenv("DB_HOST"),
        "port": int(os.getenv("SPRAV_DB_PORT") or os.getenv("DB_PORT") or 5432),
        "database": os.getenv("SPRAV_DB_NAME", "sprav"),
    }


async def load_norms(sprav: Optional[asyncpg.Connection] = None) -> tuple[list[dict], dict[int, dict]]:
    """Нормы 39_normy_teplovyh_poter (DISTINCT, как в normMon) и 30_koeffitsienty_mestnyh_teplovyh_poter."""
    own = sprav is None
    if own:
        sprav = await asyncpg.connect(**sprav_db_config(), timeout=30)
    try:
        cols = ", ".join(f'"{c}"' for c in S39_COLUMNS)
        s39 = [dict(r) for r in await sprav.fetch(f'SELECT DISTINCT {cols} FROM public."39_normy_teplovyh_poter"')]
        s10 = {r["id"]: dict(r) for r in await sprav.fetch(
            'SELECT "id", "diametr", "beta_mag", "beta_rasp" FROM public."30_koeffitsienty_mestnyh_teplovyh_poter"')}
    finally:
        if own:
            await sprav.close()
    for n in s39:
        for k in ("tn", "date"):
            if n[k] is not None:
                n[k] = int(n[k])  # dblink десктопа читает эти колонки как INTEGER
        for k, v in list(n.items()):
            if isinstance(v, Decimal):
                n[k] = float(v)
    return s39, s10


def _floatify(row: dict[str, Any]) -> dict[str, Any]:
    return {k: (float(v) if isinstance(v, Decimal) else v) for k, v in row.items()}


async def load_inputs(conn: asyncpg.Connection, *, season_id: int, heat_source_ids: Optional[list[int]] = None,
                      fragment_id: Optional[int] = None, line_ids: Optional[list[int]] = None,
                      norms: Optional[tuple[list[dict], dict[int, dict]]] = None) -> HeatLossInputs:
    season = await conn.fetchrow("SELECT * FROM heatlosesmain WHERE id = $1", season_id)
    if season is None:
        raise HeatLossInputError(f"Сезон {season_id} не найден (heatlosesmain)")
    args: list[Any] = []
    line_filter = ""
    node_filter = ""
    if line_ids:
        line_filter = "AND l.id = ANY($2::int[])"
        args.append(list(line_ids))
    elif fragment_id is not None:
        line_filter = "AND l.fileid = $2"
        args.append(fragment_id)
    if fragment_id is not None:
        node_filter = "AND n.fileid = $2"
    if not heat_source_ids:
        # все источники, к которым приписаны участки (в пределах фрагмента/списка)
        q = SECTIONS_SQL.replace("{line_filter}", line_filter.replace("$2", "$1")).replace(
            "{source_filter}", "hpsi.heatsourceid IS NOT NULL")
        q = "SELECT DISTINCT heatsourceid FROM (" + q.replace("ORDER BY hpsi.section_id", "") + ") s"
        heat_source_ids = sorted(r["heatsourceid"] for r in await conn.fetch(q, *args))
    sections = [_floatify(dict(r)) for r in await conn.fetch(
        SECTIONS_SQL.replace("{line_filter}", line_filter).replace(
            "{source_filter}", "hpsi.heatsourceid = ANY($1::int[])"), list(heat_source_ids), *args)]
    section_coefficients(sections)
    months = [_floatify(dict(r)) for r in await conn.fetch(
        "SELECT heatsourceid, r, m, sezon, tn, tpod, tgr, tgp, tgo, tx, workcount "
        "FROM heatlosessourcemonths WHERE heatsourceid = ANY($1::int[]) ORDER BY heatsourceid, r, id",
        list(heat_source_ids))]
    hls_rows = [_floatify(dict(r)) for r in await conn.fetch(
        "SELECT heatsourceid, t_percent FROM heatlosessource WHERE heatsourceid = ANY($1::int[]) ORDER BY id",
        list(heat_source_ids))]
    cons_args: list[Any] = [season_id]
    if fragment_id is not None:
        cons_args.append(fragment_id)
    consumers = [_floatify(dict(r)) for r in await conn.fetch(
        CONSUMER_VOLUMES_SQL.replace("{node_filter}", node_filter), *cons_args)]
    sources = {r["id"]: dict(r) for r in await conn.fetch(
        "SELECT id, name, sourcename FROM heatsources WHERE id = ANY($1::int[])", list(heat_source_ids))}
    month_names = {r["id"]: r["name"] for r in await conn.fetch("SELECT id, name FROM months")}
    s39, s10 = norms if norms is not None else await load_norms()
    return HeatLossInputs(
        season=_floatify(dict(season)), heat_source_ids=list(heat_source_ids), sources=sources,
        sections=sections, months=months, hls_rows=hls_rows, consumers=consumers, s39=s39, s10=s10,
        month_names=month_names, fragment_id=fragment_id, line_ids=list(line_ids) if line_ids else None,
    )


def compute(inputs: HeatLossInputs) -> dict[str, Any]:
    """Все результаты модуля по загруженным данным (чистая функция)."""
    tview = temp_view(inputs.months)
    nm = norm_mon(inputs.sections, inputs.s39, tview, inputs.s10)
    ahlm = avg_heat_loses_month(nm, tview, inputs.sections, inputs.consumers, inputs.season, inputs.hls_rows)
    year = sheet_avg_year_loses(ahlm, inputs.months, inputs.sources, inputs.month_names)
    sections = section_results(inputs.sections, inputs.s39, tview, inputs.s10)
    ready = sorted(tview)
    return {
        "heat_source_ids": inputs.heat_source_ids,
        "sources": [{"id": hs, "name": (inputs.sources.get(hs) or {}).get("name"),
                     "sourcename": (inputs.sources.get(hs) or {}).get("sourcename"),
                     "has_months": hs in tview,
                     "sections": sum(1 for s in inputs.sections if s["heatsourceid"] == hs)}
                    for hs in inputs.heat_source_ids],
        "ready_source_ids": ready,
        "material_characteristics": sheet_material_characteristics(inputs.sections, inputs.sources),
        "month_temperatures": sheet_month_temperatures(inputs.months, inputs.sources),
        "winter_norms": sheet_winter_norms(nm, inputs.sources),
        "summer_norms": sheet_summer_norms(nm, inputs.sources),
        "avg_month_loses": sheet_avg_month_loses(ahlm, inputs.months, inputs.sources, inputs.month_names),
        "avg_year_loses": year,
        "year_totals": {str(k): v for k, v in year_totals(year).items()},
        "sections": sections,
    }


def summary_totals(result: dict[str, Any]) -> dict[str, Any]:
    """Итог по всем источникам расчёта (фрагмент): Гкал за периоды и год."""
    keys = ("potnp", "potno", "potpodz", "potall", "v1", "vall")
    total = {p: {k: 0.0 for k in keys} for p in ("heating", "summer", "year")}
    for per in (result.get("year_totals") or {}).values():
        for p in total:
            for k in keys:
                total[p][k] += per[p][k]
    return {p: {k: round(v, 6) for k, v in vals.items()} for p, vals in total.items()}


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
