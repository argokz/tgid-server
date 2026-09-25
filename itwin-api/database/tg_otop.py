"""OTOP temperature graph (desktop poteriNew/sety CalculateOT1).

Linear seed is not a substitute: this is the Zinger-style iterative graph
with lower/upper cutoffs and optional wind correction.
"""

from __future__ import annotations

import math
from typing import Any, Mapping


class OtopError(ValueError):
    """Invalid heatsource inputs for OTOP."""


def _f(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _pow_safe(base: float, exp: float) -> float:
    return math.pow(max(base, 1e-6), exp)


def outdoor_range(tn_design: float, tn_end: float) -> list[float]:
    """Inclusive 1°C steps from design outdoor (cold) to heating-season end (warm)."""
    if tn_end < tn_design:
        tn_design, tn_end = tn_end, tn_design
    points = int(round(tn_end - tn_design)) + 1
    if points < 2 or points > 200:
        raise OtopError("Диапазон tn_5…tn_1 должен быть 2–200 точек")
    return [tn_design + i for i in range(points)]


def mixing_correction(params: Mapping[str, Any]) -> float:
    """Поправка коэффициента смешения uf — как задана (по умолчанию 0).

    Для графика отопления десктоп берёт KSR без подстановки (gid8 tg/tempgraph.cpp,
    CTempGraph::CalculateOT1: `uf = tg.KSR`; sety/tg/tg1.py); вычисление по температурам
    при KSR = 0 есть только в графиках ПОВ и СКК.
    """
    return _f(params.get("uf"), 0.0) or 0.0


def check_otop_inputs(params: Mapping[str, Any]) -> None:
    thor = _f(params.get("tn_5"))
    thk = _f(params.get("tn_1"))
    tvr = _f(params.get("tvn_r"))
    t1 = _f(params.get("t1_r"))
    t2 = _f(params.get("t2_r"))
    t3 = _f(params.get("t3_r"), t1)
    tb = _f(params.get("tvb_tr"), tvr)
    if None in (thor, thk, tvr, t1, t2, t3, tb):
        raise OtopError("Нужны tn_5, tn_1, tvn_r, t1_r, t2_r (и желательно t3_r, tvb_tr)")
    assert thor is not None and thk is not None and tvr is not None
    assert t1 is not None and t2 is not None and t3 is not None and tb is not None
    if thk <= thor:
        raise OtopError("tn_1 (конец сезона) должен быть выше tn_5 (расчётная наружная)")
    if tvr <= thk:
        raise OtopError("tvn_r должна быть выше tn_1")
    if tb < thk:
        raise OtopError("tvb_tr не может быть ниже tn_1")
    if t1 <= t2 or t1 <= t3:
        raise OtopError("t1_r должна быть выше t2_r и t3_r")
    if t3 <= t2:
        raise OtopError("t3_r должна быть выше t2_r")
    tsmin = _f(params.get("t1_2r"), 0.0) or 0.0
    tsmax = _f(params.get("t1_4r"), 200.0) or 200.0
    if tsmin and tsmin >= t1:
        raise OtopError("Нижняя срезка t1_2r должна быть ниже t1_r")
    if tsmin >= tsmax:
        raise OtopError("t1_2r должна быть ниже t1_4r")


def calculate_otop_point(
    *,
    tn: float,
    thor: float,
    tvr: float,
    taurp: float,
    tauro: float,
    taurs: float,
    tb: float,
    uf: float,
    tsmin: float,
    tsmax: float,
    t2min: float,
    qmax: float,
    wind: float,
    max_iter: int = 80,
) -> dict[str, float]:
    """One outdoor-temperature point of the OTOP curve (sety CalculateOT1)."""
    dtau = taurp - tauro
    teta_sum = taurs + tauro
    dtr = teta_sum / 2.0 - tvr
    teta = taurs - tauro
    denom_t = tvr - thor
    if abs(denom_t) < 1e-6:
        raise OtopError("tvn_r и tn_5 совпадают — нельзя посчитать относительную нагрузку")

    qopc = (tb - tn) / denom_t
    if qopc <= 0:
        # выше требуемой внутренней — график держит минимум нагрузки
        qopc = 0.01
    qq = qopc
    n = 100
    tau01 = tau02 = tau03 = tb_i = qocn = qopc
    ex = 0.01

    for _ in range(max_iter):
        tau01 = tn + qopc * (tvr - thor + (0.5 + uf) * dtau / (1 + uf) + dtr / _pow_safe(qopc, 0.2))
        qocn = qopc
        qoc = qocn
        tm = 1
        for _cut in range(max_iter):
            tau02 = tau01 - dtau * qopc
            tau03 = tau02 + teta * qopc
            for _room in range(max_iter):
                qoc = qocn
                tb_i = tn + (tb - tn) * qoc / qq
                inner = (0.5 + uf) / (1 + uf) * dtau + dtr / _pow_safe(qoc, 0.2)
                if abs(inner) < 1e-9:
                    break
                qocn = (tau01 - tb_i) / inner
                if abs(qoc) < 1e-9:
                    break
                if abs((qoc - qocn) / qoc) < ex:
                    break

            if tau01 < tsmin or tau01 > tsmax or tau02 < t2min:
                if tau01 < tsmin:
                    tm = 0
                    tau01 = tsmin
                if tau01 > tsmax:
                    tm = 0
                    tau01 = tsmax
                if tau02 < t2min:
                    tm = 0
                    if tau01 < tsmax:
                        tau01 = tau01 + 0.05
                    else:
                        tm = 1
                for _srez in range(max_iter):
                    inner = (0.5 + uf) / (1 + uf) * dtau + dtr / _pow_safe(qoc, 0.2)
                    if abs(inner) < 1e-9:
                        break
                    qocn = (tau01 - tb_i) / inner
                    eq = abs((qoc - qocn) / qoc) if abs(qoc) > 1e-9 else 0.0
                    qoc = qocn
                    tb_i = tn + (tb - tn) * qoc / qq
                    if eq < ex:
                        break
                qopc = qocn
            else:
                tm = 1
            if tm != 0:
                break

        if qoc > qmax and n >= 1:
            qopc = qmax
            tbn = tn + qopc * (tb - tn) / qq
            qopc = (tbn - tn) / denom_t
            dq = ex + 1
            n -= 1
        else:
            dq = ex - 1
        if dq < ex:
            break

    tau01v = tau01
    if wind > 3:
        tau01v = tau01 + (tau01 - tb) * (wind / 100.0)
        qocnv = qocn
        for _w in range(max_iter):
            qocv = qocnv
            tbv = tn + (tb - tn) * qocv / qq
            inner = (0.5 + uf) / (1 + uf) * dtau + dtr / _pow_safe(qocv, 0.2)
            if abs(inner) < 1e-9:
                break
            qocnv = (tau01v - tbv) / inner
            if abs(qocv) < 1e-9 or abs((qocv - qocnv) / qocv) < ex:
                break
        if qocnv > qmax:
            qocnv = qmax
            tbn = tn + qocnv * (tb - tn) / qq
            qocnv = (tbn - tn) / denom_t
            tau01v = tn + qocnv * (
                tvr - thor + (0.5 + uf) * dtau / (1 + uf) + dtr / _pow_safe(qocnv, 0.2)
            )
        if tau01 <= tsmin:
            tau01v = tsmin
        if tau01v > tsmax:
            tau01v = tsmax

    return {
        "tn": round(tn, 1),
        "t1": round(tau01, 1),
        "t2": round(tau02, 1),
        "t3": round(tau03, 1),
        "tv": round(tau01v, 1),
        "t_bn": round(tb_i, 2),
        "q_otn": round(qocn, 4),
    }


def calculate_otop_curve(params: Mapping[str, Any]) -> list[dict[str, float]]:
    """Full OTOP curve for a heatsources row (desktop «Расчёт TG»)."""
    check_otop_inputs(params)
    thor = float(params["tn_5"])
    thk = float(params["tn_1"])
    tvr = float(params["tvn_r"])
    taurp = float(params["t1_r"])
    tauro = float(params["t2_r"])
    taurs = float(params.get("t3_r") or taurp)
    tb = _f(params.get("tvb_tr"), tvr) or tvr
    uf = mixing_correction(params)
    tsmin = _f(params.get("t1_2r"), 0.0) or 0.0
    tsmax = _f(params.get("t1_4r"), 200.0) or 200.0
    t2min = _f(params.get("t2_2r"), 0.0) or 0.0
    qr = _f(params.get("q_r"), 1.0) or 1.0
    qmax = (_f(params.get("qmax"), 100.0) or 100.0) / qr
    wind = _f(params.get("v"), 0.0) or 0.0

    points = []
    for tn in outdoor_range(thor, thk):
        points.append(
            calculate_otop_point(
                tn=tn,
                thor=thor,
                tvr=tvr,
                taurp=taurp,
                tauro=tauro,
                taurs=taurs,
                tb=tb,
                uf=uf,
                tsmin=tsmin,
                tsmax=tsmax,
                t2min=t2min,
                qmax=qmax,
                wind=wind,
            )
        )
    return points
