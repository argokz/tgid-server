"""Температурные графики ПОВ и СКК — перенос gid8 `gid8/tg/tempgraph.cpp` (CTempGraph).

- ПОВ — «Повышенный» график (heatsources.graphTypeID = 3, «П»): отопительно-бытовой график для
  закрытых систем с двухступенчатыми подогревателями ГВС; CheckInputPOV / CalculatePOV.
- СКК — «Скорректированный» график по совмещённой нагрузке отопления и ГВС (открытые системы):
  повышенный «СВ» (graphTypeID = 2) и пониженный «СН» (graphTypeID = 4); CheckInputSK / CalculateSK.
  Способ водоразбора — heatsources.pr: 1 с переключением, 2 только из подающего, 3 только из
  обратного, 4 с узлом смешения.
- ОТОП (graphTypeID 0/1) — database/tg_otop.py.

В sety/tg десктопа есть только ОТОП (tg1.py, tg2.py); ПОВ и СКК считает C++ gid8 (кнопка пересчёта
температурного графика источника, CTempGraph::defaultLoadTempGraph) и пишет в deployedTempGraphs:
ПОВ — (tn, t1, t2, tv, t_bn, tg), СКК — (tn, t1, t2, t3, tv).

Отличия от C++ (неопределённое поведение десктопа): в СКК массив точек на одну длиннее, и
последний элемент — «точка излома» режима с переключением (pr = 1): её tнв берётся из точки, где
обратная вода достигла t2_gv. В других режимах (и если излома нет) десктоп считает этот элемент
по неинициализированной памяти и тоже пишет его в БД — здесь такая точка не выводится.
Бесконечные циклы C++ ограничены (MAX_LOOP) — при превышении ошибка.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Optional

MAX_LOOP = 100_000

ERRORS = {
    501: "Значения 'Расчетной температуры наружного воздуха' и 'Температуры наружного воздуха в конце отопительного периода' совпадают.",
    502: "Значение 'Расчетной температуры воздуха внутри помещения' ниже значения 'Температуры наружного воздуха в конце отопительного периода'.",
    503: "Значение 'Требуемой температуры воздуха внутри помещения' ниже значения 'Температуры наружного воздуха в конце отопительного периода'.",
    504: "Значение 'Требуемой температуры воздуха внутри помещения' больше значения 'Расчетной температуры воздуха внутри помещения' на 50%.",
    505: "Значение 'Расчетной температуры сетевой воды в подающем трубопроводе' ниже 'Расчетной температуры сетевой воды в обратном тр-де или узла смешения'.",
    506: "Значение 'Расчетной температуры сетевой воды после узла смешения' ниже значения'Расчетной температуры сетевой воды в обратном трубопроводе'.",
    507: "Значение 'Температуры нижней срезки температурного графика' выше значения 'Расчетной температуры сетевой воды в подающем трубопроводе'.",
    508: "Значение 'Температуры нижней срезки температурного графика' выше значения 'Температуры верхней срезки температурного графика'.",
    509: "Значение 'Расчетной тепловой нагрузки отопления' и значение 'Располагаемой тепловой мощности источника тепла'различны больше чем на 50%.",
    510: "Значение 'Температуры горячей воды в местах водоразбора' ниже значения 'Температуры холодной воды'.",
    511: "Значение 'Среднечасовой нагрузки в системе горячего водоснабжения' велико.",
    512: "Значение 'Расчетная тепловая нагрузка на отопление' не задано.",
    513: "Значение 'Расчетная тепловая нагрузка на горячее водоснабжение' не задано.",
    514: "Значения 'Расчетной температуры наружного воздуха' и 'Температуры наружного воздуха в конце отопительного периода' совпадают.",
    515: "Значение 'Расчетной температуры воздуха внутри помещения' ниже значения 'Температуры наружного воздуха в конце отопительного периода'.",
    516: "Значение 'Требуемой температуры воздуха внутри помещения' ниже значения 'Температуры наружного воздуха в конце отопительного периода'.",
    517: "Значение 'Требуемой температуры воздуха внутри помещения' больше значения 'Расчетной температуры воздуха внутри помещения' на 50%.",
    518: "Значение 'Расчетной температуры сетевой воды в подающем трубопроводе' ниже 'Расчетной температуры сетевой воды в обратном тр-де или узла смешения'.",
    519: "Значение 'Расчетной температуры сетевой воды после узла смешения' ниже значения 'Расчетной температуры сетевой воды в обратном трубопроводе'.",
    520: "Значение 'Температуры нижней срезки температурного графика' выше значения 'Расчетной температуры сетевой воды в подающем трубопроводе'.",
    521: "Значение 'Температуры нижней срезки температурного графика' выше значения 'Температуры верхней срезки температурного графика'.",
    522: "Значение 'Температура нижней срезки обратной воды' выше значения 'Расчетной температуры сетевой воды в обратном трубопроводе'.",
    523: "Значение 'Расчетной тепловой нагрузки отопления' и значение 'Располагаемой тепловой мощности источника тепла'различны больше чем на 50%.",
    524: "Значение 'Температуры горячей воды в местах водоразбора' ниже значения 'Температуры холодной воды'.",
    525: "Значение 'Коэффициента,характеризующего гидравлическую устойчивость' подающего трубопровода' велико.",
    526: "Значение 'Среднечасовой нагрузки в системе горячего водоснабжения' велико.",
    527: "Значение 'Температура воды в обpатном трубопроводе для переключения водоразбора' ниже минимально возможной в обратном трубопроводе.",
    528: "Значение 'Расчетная тепловая нагрузка на отопление' не задано.",
    529: "Значение 'Расчетная тепловая нагрузка на горячее водоснабжение' не задано.",
    530: "Значение 'Признак способа водоразбора горячей воды' не задано.",
}

GRAPH_TYPES = {0: "otop", 1: "otop", 2: "skk_pov", 3: "pov", 4: "skk_pon"}
GRAPH_NAMES = {"otop": "Отопительный", "pov": "Повышенный", "skk_pov": "Скорректированный повышенный",
               "skk_pon": "Скорректированный пониженный"}


class TgInputError(ValueError):
    def __init__(self, codes: list[int]):
        self.codes = codes
        super().__init__("; ".join(f"Код ошибки {c} {ERRORS.get(c, '')}".strip() for c in codes))


def _f(v: Any) -> float:
    if v is None or v == "":
        return 0.0
    return float(v)  # QSqlQuery.value(...).toDouble(): NULL → 0


def _pow(x: float, y: float) -> float:
    """pow из C: отрицательное основание с дробной степенью — NaN, а не комплексное число."""
    if x < 0 and not float(y).is_integer():
        return math.nan
    try:
        return math.pow(x, y)
    except (OverflowError, ValueError):
        return math.nan


def _div(a: float, b: float) -> float:
    if b == 0:
        if a == 0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a) * (1 if math.copysign(1, b) > 0 else -1)
    return a / b


def init_tn_obr(t1: float, t2: float) -> list[float]:
    """init_tn_obr: tнв от конца сезона (t2) к расчётной (t1) с шагом 1 °C."""
    tt1, tt2 = math.floor(t1), math.floor(t2)
    tn: list[float] = []
    if tt2 < t2:
        tn.append(t2)
    t = float(tt2)
    while t > tt1:
        tn.append(t)
        t -= 1
    tn.append(t1)
    return tn


# ---------------------------------------------------------------- исходные данные (Init*TempStructure)


def pov_params(src: Mapping[str, Any]) -> dict[str, float]:
    """InitPovTempStructure: нижней срезки у повышенного графика нет (TSMIN = 0)."""
    return {
        "THOR": _f(src.get("tn_5")), "THK": _f(src.get("tn_1")), "TVR": _f(src.get("tvn_r")),
        "TAURP": _f(src.get("t1_r")), "TAURO": _f(src.get("t2_r")), "TAURS": _f(src.get("t3_r")),
        "QOR": _f(src.get("q_r")), "QGW": _f(src.get("q_gv")), "TSMIN": 0.0, "TSMAX": _f(src.get("t1_4r")),
        "TVRO": _f(src.get("tg_r")), "TV": _f(src.get("tx_r")), "TB": _f(src.get("tvb_tr")),
        "NEDOG": _f(src.get("t_gv1")), "KSR": _f(src.get("uf")), "V": _f(src.get("v")),
        "QMAX": _f(src.get("hsourcepower")),  # у ПОВ без подстановки 100
    }


def skk_params(src: Mapping[str, Any], pov: bool) -> dict[str, float]:
    """InitSKTempStructure: IsPov — повышенный (СВ) / пониженный (СН); TSMIN = 0."""
    pr = int(_f(src.get("pr")))
    qmax = _f(src.get("hsourcepower")) or 100.0
    return {
        "IsPov": 1 if pov else 0,
        "THOR": _f(src.get("tn_5")), "THK": _f(src.get("tn_1")), "TVR": _f(src.get("tvn_r")),
        "TAURP": _f(src.get("t1_r")), "TAURO": _f(src.get("t2_r")), "TAURS": _f(src.get("t3_r")),
        "QOR": _f(src.get("q_r")), "QGW": _f(src.get("q_gv")), "TSMIN": 0.0,
        "TSMAX": _f(src.get("t1_4r")), "T2MIN": _f(src.get("t2_2r")),
        "KGUP": _f(src.get("g1")), "KGUO": _f(src.get("g2")),
        "PSN": 1 if pr == 1 else 0, "PSP": 1 if pr == 2 else 0, "PSO": 1 if pr == 3 else 0,
        "PSY": 1 if pr == 4 else 0,
        "T2GW": _f(src.get("t2_gv")), "TV": _f(src.get("tx_r")), "TB": _f(src.get("tvb_tr")),
        "TVRO": _f(src.get("tg_r")), "KSR": _f(src.get("uf")), "V": _f(src.get("v")), "QMAX": qmax,
    }


def _norm_variant(p: dict[str, float]) -> dict[str, float]:
    q = dict(p)
    q["TSMIN"], q["TSMAX"] = 0.0, 200.0
    if "T2MIN" in q:
        q["T2MIN"] = 0.0
    return q


# ---------------------------------------------------------------- ПОВ


def check_input_pov(tg: Mapping[str, float]) -> list[int]:
    err = []
    a3 = tg["TB"] if tg["TVR"] == 0 else _div(tg["TB"], tg["TVR"])
    if tg["THOR"] == 0 and tg["THK"] == 0:
        err.append(501)
    if tg["TVR"] <= tg["THK"]:
        err.append(502)
    if tg["TB"] < tg["THK"]:
        err.append(503)
    if a3 > 2:
        err.append(504)
    if tg["TAURP"] <= tg["TAURO"] or tg["TAURP"] <= tg["TAURS"]:
        err.append(505)
    if tg["TAURS"] <= tg["TAURO"]:
        err.append(506)
    if tg["TSMIN"] >= tg["TAURP"]:
        err.append(507)
    if tg["TSMIN"] >= tg["TSMAX"]:
        err.append(508)
    if _div(tg["QOR"] - tg["QMAX"], tg["QOR"]) > 0.5:
        err.append(509)
    if tg["TVRO"] <= tg["TV"]:
        err.append(510)
    if _div(tg["QGW"], tg["QOR"]) > 0.7:
        err.append(511)
    if tg["QGW"] <= 0:
        err.append(512)
    if tg["QOR"] <= 0:
        err.append(513)
    return err


def calculate_pov(p: Mapping[str, float]) -> list[dict[str, float]]:
    """CalculatePOV: точки (tn, t1=τ01, t2=τ02, tv=τ01 с ветром, t_bn=tв, tg=tгв)."""
    tg = dict(p)
    QMAX = _div(tg["QMAX"], tg["QOR"])
    THOR, THK, TVR, TB, TV, TVRO = tg["THOR"], tg["THK"], tg["TVR"], tg["TB"], tg["TV"], tg["TVRO"]
    TSMIN, TSMAX = tg["TSMIN"], tg["TSMAX"]
    tn = init_tn_obr(THOR, THK)
    kol = len(tn) - 1
    u = _div(tg["TAURP"] - tg["TAURS"], tg["TAURS"] - tg["TAURO"])
    if tg["KSR"] != 0.0:
        u = tg["KSR"]
    DTAU = tg["TAURP"] - tg["TAURO"]
    TETA = tg["TAURS"] + tg["TAURO"]
    DTR = TETA / 2.0 - TVR
    NC = _div(tg["QGW"], tg["QOR"])
    dlt = 1.2 * NC * DTAU
    ex = 0.001
    tis = THK
    isr = 0
    t02is = 0.0
    qq = [0.0] * (kol + 1)
    t01 = [0.0] * (kol + 1)
    t02 = [0.0] * (kol + 1)

    def heat(t, q):
        return t + q * (TVR - THOR + (0.5 + u) * DTAU / (1 + u) + _div(DTR, _pow(q, 0.2)))

    for i in range(kol + 1):
        t = tn[i]
        qq[i] = qopc = _div(TB - t, TVR - THOR)
        t01[i] = heat(t, qopc)
        t02[i] = t01[i] - qopc * DTAU
        if t01[i] >= TVRO and isr == 0:
            isr = 1
            tis = t
            t02is = t02[i]
    if tis == THK:
        t02is = t02[0]
    twis = t02is - tg["NEDOG"]
    dlt2is = _div(dlt * (twis - TV), TVRO - TV)

    out = []
    for i in range(kol + 1):
        t = tn[i]
        nn = 1000
        tbn = TB
        qopc = qq[i]
        psr = 0
        loops = 0
        while True:
            loops += 1
            if loops > MAX_LOOP:
                raise ValueError("ПОВ: расчёт по дефициту мощности не сходится")
            if nn < 1000:
                t01[i] = heat(t, qopc)
                t02[i] = t01[i] - qopc * DTAU
            dlt2 = _div(dlt2is * (t02[i] - TV), t02is - TV)
            dlt1 = dlt - dlt2
            if dlt2 > dlt:
                dlt1 = 0
            tau01 = t01[i] + dlt1
            tau02 = t02[i] - dlt2
            if tau01 < TSMIN or tau01 > TSMAX:
                if tau01 < TSMIN:
                    ts = TSMIN
                if tau01 > TSMAX:
                    ts = TSMAX
                tau02 = ts - _div((ts - t) * (tau01 - tau02), tau01 - t)
                if tau01 < TSMIN:
                    tau01 = TSMIN
                if tau01 > TSMAX:
                    tau01 = TSMAX
            if t01[i] < TSMIN or t01[i] > TSMAX:  # срезка отопительного графика
                if t01[i] < TSMIN:
                    ts = TSMIN
                if t01[i] > TSMAX:
                    ts = TSMAX
                t02[i] = ts - _div((ts - t) * (t01[i] - t02[i]), t01[i] - t)
                if t01[i] < TSMIN:
                    t01[i] = TSMIN
                if t01[i] > TSMAX:
                    t01[i] = TSMAX
            tgv = _div(tg["QOR"] / DTAU * (dlt1 + dlt2), _div(1.2 * tg["QGW"], TVRO - TV)) + TV
            gg = dlt / DTAU
            go = (t01[i] - t02[i]) / DTAU
            qoc = go + gg
            if qoc > QMAX and nn >= 1:
                tbn -= 0.05
                qopc = _div(tbn - t, TVR - THOR)
                dq = abs(_div(QMAX - qoc, QMAX))
                psr = 1
                nn -= 1
            else:
                dq = ex
            if not dq > ex:
                break
        tb = tbn
        if tg["V"] > 3:
            tau01v = tau01 + (tau01 - tbn) * (tg["V"] / 100.0)
            if psr == 1:
                tau01v = tau01
            else:
                qocnv = qoc
                loops = 0
                while True:
                    loops += 1
                    if loops > MAX_LOOP:
                        raise ValueError("ПОВ: учёт ветра не сходится")
                    qocv = qocnv
                    tbv = t + _div((tbn - t) * qocv, qopc)
                    qocnv = _div(tau01v - tbv, (0.5 + u) / (1 + u) * DTAU + _div(DTR, _pow(qocv, 0.2)))
                    eq = abs(_div(qocv - qocnv, qocv))
                    if not eq > ex:
                        break
                if qocnv > QMAX:
                    qocnv = QMAX
                    tbn = t + _div(qocnv * (TB - t), qq[i])
                    qocnv = _div(tbn - t, TVR - THOR)
                    tau01v = heat(t, qocnv)
            if tau01 <= TSMIN:
                tau01v = TSMIN
            if tau01v > TSMAX:
                tau01v = TSMAX
        else:
            tau01v = tau01
        out.append({"tn": t, "t1": tau01, "t2": tau02, "tv": tau01v, "t_bn": tb, "tg": tgv})
    return out


# ---------------------------------------------------------------- СКК


def check_input_sk(p: Mapping[str, float]) -> list[int]:
    tg = dict(p)
    err = []
    thor = -tg["THOR"]  # CheckInputSK меняет знак THOR на время проверки
    a6 = tg["TB"] if tg["TVR"] == 0 else _div(tg["TB"], tg["TVR"])
    a1 = _div(tg["QOR"] - tg["QMAX"], tg["QOR"])
    a4 = 1.95 * tg["KGUO"] + 1
    a5 = _div(tg["QGW"], tg["QOR"])
    t02 = 0.0
    if tg["PSN"] == 1:
        ur = _div(tg["TAURP"] - tg["TAURS"], tg["TAURS"] - tg["TAURO"])
        DTAU = tg["TAURP"] - tg["TAURO"]
        DTR = (tg["TAURS"] + tg["TAURO"]) / 2.0 - tg["TVR"]
        t = tg["THK"]
        qopc = _div(tg["TB"] - t, tg["TVR"] + thor)
        t01 = t + qopc * (tg["TVR"] - thor + (0.5 + ur) * DTAU / (1 + ur) + _div(DTR, _pow(qopc, 0.2)))
        t02 = t01 - qopc * DTAU + 10.0
        if t01 < tg["TSMIN"]:
            t01 = tg["TSMIN"]
            t02 = t01 - qopc * DTAU - 5
    if thor == 0 and tg["THK"] == 0:
        err.append(514)
    if tg["TVR"] <= tg["THK"]:
        err.append(515)
    if tg["TB"] < tg["THK"]:
        err.append(516)
    if a6 > 2:
        err.append(517)
    if tg["TAURP"] <= tg["TAURO"] or tg["TAURP"] <= tg["TAURS"]:
        err.append(518)
    if tg["TAURS"] <= tg["TAURO"]:
        err.append(519)
    if tg["TSMIN"] >= tg["TAURP"]:
        err.append(520)
    if tg["TSMIN"] >= tg["TSMAX"]:
        err.append(521)
    if tg["T2MIN"] >= tg["TAURO"]:
        err.append(522)
    if a1 > 0.5:
        err.append(523)
    if tg["TVRO"] <= tg["TV"]:
        err.append(524)
    if tg["KGUP"] > a4:
        err.append(525)
    if a5 > 4:
        err.append(526)
    if tg["T2GW"] <= t02:
        err.append(527)
    if tg["QGW"] <= 0:
        err.append(528)
    if tg["QOR"] <= 0:
        err.append(529)
    if tg["PSN"] == 0 and tg["PSY"] == 0 and tg["PSP"] == 0 and tg["PSO"] == 0:
        err.append(530)
    return err


def calculate_sk(p: Mapping[str, float]) -> list[dict[str, float]]:
    """CalculateSK: точки (tn, t1=τ01, t2=τ02, t3=τ03 после смешения, tv=τ01 с ветром)."""
    tg = dict(p)
    QMAX = _div(tg["QMAX"], tg["QOR"])
    THOR, THK, TVR, TB, TV, TVRO = tg["THOR"], tg["THK"], tg["TVR"], tg["TB"], tg["TV"], tg["TVRO"]
    TSMIN, TSMAX, T2MIN, T2GW = tg["TSMIN"], tg["TSMAX"], tg["T2MIN"], tg["T2GW"]
    PSN, PSP, PSO, PSY = tg["PSN"], tg["PSP"], tg["PSO"], tg["PSY"]
    KGUP, KGUO = tg["KGUP"], tg["KGUO"]
    tn: list[Optional[float]] = list(init_tn_obr(THOR, THK))
    KOL = len(tn) - 1
    kl = KOL + 1
    tn.append(None)  # элемент kl — «точка излома»
    ur = _div(tg["TAURP"] - tg["TAURS"], tg["TAURS"] - tg["TAURO"])
    uf = tg["KSR"] if tg["KSR"] != 0.0 else ur
    DTAU = tg["TAURP"] - tg["TAURO"]
    DTR = (tg["TAURS"] + tg["TAURO"]) / 2.0 - TVR
    NC = _div(tg["QGW"], tg["QOR"])
    cn = NC * (1 - KGUP) * (TVRO - TV)
    co = NC * KGUO * (1 + 2 * uf) * (TVRO - TV)
    if tg["IsPov"]:
        m, n = 1 + NC * (1 - KGUP), 0.0
    else:
        m, n = 1.0, NC * (1 - KGUP)
    dn = TV
    ex = 0.001
    iww = 0
    iw = kl
    ntm = 0
    qoc = 0.0
    fi = 0.0
    tb = 0.0
    tau01 = tau02 = 0.0
    res: list[Optional[dict[str, float]]] = [None] * (kl + 1)

    def guard(counter: list[int], what: str) -> None:
        counter[0] += 1
        if counter[0] > MAX_LOOP:
            raise ValueError(f"СКК: {what} не сходится")

    for i in range(kl + 1):
        nn = 100
        if i == kl:
            if iw >= kl or iw < 0:
                break  # у десктопа — неинициализированная память, точка не выводится
            tn[i] = tn[iw]
        t = tn[i]
        qopc = _div(TB - t, TVR - THOR)
        tbn = TB
        qq = qopc
        psr = 0
        c_dq = [0]
        while True:
            guard(c_dq, "расчёт по дефициту мощности")
            t01 = t + qopc * (TVR - THOR + (0.5 + ur) * DTAU / (1 + ur) + _div(DTR, _pow(qopc, 0.2)))
            t02 = t01 - qopc * DTAU
            to1, to2 = t01, t02
            qocn = qopc
            c_tm = [0]
            while True:
                guard(c_tm, "срезка")
                tm = 1
                a = (t01 + (1 + 2 * ur) * t02) / (2 * (1 + ur))
                b = (t01 - t02) * (1 + 2 * uf) / (2 * (1 + uf))
                tau02n = t02
                c_dt = [0]
                while True:
                    guard(c_dt, "температура обратной воды")
                    tau02 = tau02n
                    dt = 0.0
                    if (PSN == 1 and tau02 < T2GW) or PSP == 1:
                        aa = (cn + b) / (2 * m) + (a - dn) / 2
                        aa *= aa
                        aa = aa - cn * (a - dn) / m
                        tau01 = dn + (cn + b) / (2 * m) + (a - dn) / 2 + _pow(aa, 0.5)
                        fi = m - _div(cn, tau01 - dn)
                        tau02n = (2 * a * (1 + uf) - tau01) / (1 + 2 * uf)
                        dt = abs(_div(tau02 - tau02n, tau02))
                    if (PSN == 1 and tau02 >= T2GW) or (PSN == 1 and i == kl):
                        if iww == 0:
                            iw = i - 1
                            iww = 1
                        d0 = a + (1 + 2 * uf) * (a - TV)
                        aa = (co + b) / (2 * m) + (a - d0) / 2
                        bb = aa * aa - co * (a - d0) / m
                        bb = _pow(bb, 0.5)
                        tau01 = d0 + aa - bb
                        fi = m - _div(co, tau01 - d0)
                        tau02n = (2 * a * (1 + uf) - tau01) / (1 + 2 * uf)
                        dt = abs(_div(tau02 - tau02n, tau02))
                    if PSO == 1:
                        d0 = a + (1 + 2 * uf) * (a - TV)
                        aa = (co + b) / (2 * m) + (a - d0) / 2
                        bb = aa * aa - co * (a - d0) / m
                        bb = 0.0 if bb < 0 else _pow(bb, 0.5)
                        tau01 = d0 + aa - bb
                        fi = m - _div(co, tau01 - d0)
                        tau02n = (2 * a * (1 + uf) - tau01) / (1 + 2 * uf)
                        dt = abs(_div(tau02 - tau02n, tau02))
                    if PSY == 1:
                        aa = 1 + NC * (1 - KGUP + KGUO) * ((1 + 2 * uf) / (2 * (1 + uf))) - n
                        tau01 = TVRO + _div(t01 - TVRO - n * (a - TVRO), aa)
                        aa = _div(TVRO - a + (tau01 - TVRO) / (2 * (1 + uf)), tau01 - a)
                        if tg["IsPov"]:
                            fi = 1 + NC * KGUO - NC * (1 - KGUP + KGUO) * aa
                        else:
                            fi = 1 + NC * (1 - KGUP + KGUO) - NC * (1 - KGUP + KGUO) * aa
                        tau02n = (2 * a * (1 + uf) - tau01) / (1 + 2 * uf)
                        dt = abs(_div(tau02 - tau02n, tau02))
                    c_eq = [0]
                    while True:
                        guard(c_eq, "температура внутри помещения")
                        qoc = qocn
                        tb = t + _div((TB - t) * qoc, qq)
                        qocn = _div(tau01 - tb, _div((0.5 + uf) / (1 + uf) * DTAU, fi) + _div(DTR, _pow(qoc, 0.2)))
                        eq = abs(_div(qoc - qocn, qoc))
                        if not eq > ex:
                            break
                    if not dt > ex:
                        break
                if tau01 < TSMIN or tau01 > TSMAX or tau02 < T2MIN:
                    if tau01 < TSMIN:
                        tm = 0
                        t01 += 0.2
                    if tau01 > TSMAX:
                        tm = 0
                        t01 -= 0.2
                    if tau02 < T2MIN:
                        ntm += 1
                        tm = 1 if ntm == 400 else 0
                        if tau01 < TSMAX:
                            t01 = t01 + 0.05
                        else:
                            tm = 1
                    c_eq = [0]
                    while True:
                        guard(c_eq, "срезка: температура внутри помещения")
                        qoc = qocn
                        tb = t + _div((TB - t) * qoc, qq)
                        qocn = _div(t01 - tb, (0.5 + uf) / (1 + uf) * DTAU + _div(DTR, _pow(qoc, 0.2)))
                        eq = abs(_div(qoc - qocn, qoc))
                        if not eq > 0.0001:
                            break
                    t02 = t01 - qocn * DTAU
                if tm != 0:
                    break
            ntm = 0
            if (qocn + NC) > QMAX and nn > 2:
                nn -= 1
                qopc = qopc - qopc / 100
                tbn = t + _div(qopc * (tb - t), qocn)
                dq = abs(_div(QMAX - qocn - NC, QMAX))
                psr = 1
            else:
                dq = ex
            if not dq > ex:
                break
        if tg["V"] > 3:
            tau01v = tau01 + (tau01 - tb) * (tg["V"] / 100.0)
            if psr == 1:
                tau01v = tau01
            else:
                qocnv = qoc
                c_eq = [0]
                while True:
                    guard(c_eq, "учёт ветра")
                    qocv = qocnv
                    tbv = t + _div((TB - t) * qocv, qq)
                    qocnv = _div(tau01v - tbv, _div((0.5 + uf) / (1 + uf) * DTAU, fi) + _div(DTR, _pow(qocv, 0.2)))
                    eq = abs(_div(qocv - qocnv, qocv))
                    if not eq > ex:
                        break
                if qocnv > QMAX:
                    qocnv = QMAX
                    tbn = t + _div(qocnv * (TB - t), qq)
                    qocnv = _div(tbn - t, TVR - THOR)
                    tau01v = t + qocnv * (TVR - THOR + _div((0.5 + uf) * DTAU / (1 + uf), fi)
                                          + _div(DTR, _pow(qocnv, 0.2)))
            if (tau01 - 1) <= TSMIN:
                tau01v = TSMIN
            if tau01v > TSMAX:
                tau01v = TSMAX
        else:
            tau01v = tau01
        tau03 = (tau01 + uf * tau02) / (1 + uf)
        res[i] = {"tn": t, "t1": tau01, "t2": tau02, "t3": tau03, "tv": tau01v}

    points = [r for r in res[:kl] if r is not None]
    brk = res[kl]
    i = iw + 1
    if brk is not None and i < kl:
        points.insert(i, brk)  # memmove: точка излома встаёт после iw
        # data.n: если tn[KOL] (после сдвига) равна 0 или вне сезона, последняя точка не выводится
        last_tn = points[KOL]["tn"]
        if not (last_tn != 0 and THOR <= last_tn <= THK):
            points = points[:KOL + 1]
    return points


# ---------------------------------------------------------------- общий вход


def graph_mode(src: Mapping[str, Any]) -> str:
    return GRAPH_TYPES.get(int(_f(src.get("graphtypeid"))), "otop")


def calculate_graph(src: Mapping[str, Any], mode: Optional[str] = None) -> dict[str, Any]:
    """Расчёт графика источника как CTempGraph::defaultLoadTempGraph: сначала проверка варианта
    без срезок (tempstruct_norm), затем фактического; ошибки проверки — TgInputError."""
    mode = mode or graph_mode(src)
    if mode == "pov":
        p = pov_params(src)
        errors = check_input_pov(_norm_variant(p)) or check_input_pov(p)
        if errors:
            raise TgInputError(errors)
        points = calculate_pov(p)
    elif mode in ("skk_pov", "skk_pon"):
        p = skk_params(src, mode == "skk_pov")
        errors = check_input_sk(_norm_variant(p)) or check_input_sk(p)
        if errors:
            raise TgInputError(errors)
        points = calculate_sk(p)
    else:
        raise ValueError(f"Режим {mode}: график ОТОП считает database/tg_otop.py")
    return {"mode": mode, "name": GRAPH_NAMES[mode], "points": points}
