"""Эталонные тесты формул без БД: веб против исходников десктопа gid8 (только чтение).

- элеватор и шайбы движка — gid8/python/sety/sety/dross/drsh1.py, drsh2.py, drsh3.py;
- бланк дроссельных устройств — формулы ячеек gid8/python/dross/dross.py (G17..G43),
  извлечённые из исходника и вычисленные маленьким интерпретатором Excel-формул;
- график ОТОП — gid8/python/sety/sety/tg/tg1.py (CalculateOT1, make_tg).

Эталон движка считается в отдельном процессе, где на sys.path стоит только
gid8/python/sety: `import sety` там — пакет десктопа, а не копия движка в API.
Без каталога gid8 (CI) модуль пропускается; путь можно задать переменной GID8_ROOT.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from database.tg_otop import calculate_otop_curve
from database.throttling_calc import (
    calculate_elevator_parameters,
    calculate_orifice_diameter,
    calculate_throttling_sheet,
)

GID8 = Path(os.environ.get("GID8_ROOT") or Path(__file__).resolve().parents[4] / "gid8")
SETY_ROOT = GID8 / "python" / "sety"
DROSS_PY = GID8 / "python" / "dross" / "dross.py"

pytestmark = pytest.mark.skipif(
    not (SETY_ROOT / "sety" / "dross" / "drsh2.py").exists() or not DROSS_PY.exists(),
    reason=f"нет эталонных исходников десктопа ({GID8})",
)

# ---------------------------------------------------------------- эталон в отдельном процессе

_REFERENCE = r'''
import ast, inspect, json, math, sys
sys.path.insert(0, sys.argv[1])
import sety
assert sety.__file__.startswith(sys.argv[1]), sety.__file__
import sety.dross.drsh1 as d1
import sety.dross.drsh2 as d2
import sety.dross.drsh3 as d3
import sety.tg.tg1 as tg1
d2.w_print = lambda *a, **k: None

# dg (диаметр горловины) drsh2 не возвращает: берём выражение прямо из исходника drsh2
tree = ast.parse(inspect.getsource(d2.drsh2))
dg_expr = next(n.value for n in ast.walk(tree)
               if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "dg")
dg_code = compile(ast.Expression(dg_expr), "drsh2", "eval")

cases = json.load(sys.stdin)
out = {"elevator": [], "drsh1": [], "drsh3": [], "otop": []}
for g, u, hc, h, diam_so in cases["elevator"]:
    ferr, hrc, dc, nal = d2.drsh2(g, diam_so, u, hc, h, "golden")
    dg = eval(dg_code, {"math": math}, {"ot": g, "k_smes": u, "nap_ras": hc})
    out["elevator"].append({"ferr": ferr, "hrc": hrc, "dc": dc, "nal": nal, "dg": dg})
for g, h in cases["orifice"]:
    out["drsh1"].append(d1.drsh1(g, h))
    out["drsh3"].append(list(d3.drsh3(g, 3.0, 0.0, h)))
for params, tns in cases["otop"]:
    tg = tg1.make_tg(params)
    tg.QMAX = 100.0  # make_tg берёт QMAX из пустого ключа; веб по умолчанию 100
    pts = []
    for tn in tns:
        t1, t2, t3, tb, qo, t1v = tg1.CalculateOT1(tg, tn, True)
        pts.append([tn, t1, t2, t3])
    out["otop"].append(pts)
json.dump(out, sys.stdout)
'''

ELEVATOR_CASES = [
    # G, u, h_c, H, мин. сопло
    (10.0, 1.4, 1.5, 20.0, 3.0),   # пример аудита: горловина 37.6 мм, элеватор №6
    *[(g, u, hc, h, 3.0)
      for g in (0.3, 1.0, 2.5, 6.0, 15.0, 30.0)
      for u in (1.2, 1.4, 2.2)
      for hc in (1.0, 1.5, 2.0)
      for h in (8.0, 20.0, 45.0)],
]
ORIFICE_CASES = [(g, h) for g in (0.05, 0.5, 2.0, 7.3, 15.0, 40.0, 120.0) for h in (1.0, 3.0, 8.0, 20.0, 45.0)]
OTOP_BASE = {"tn_5": -25, "tn_1": 8, "tvn_r": 18, "t1_r": 130, "t2_r": 70, "t3_r": 95, "tvb_tr": 18,
             "uf": 0, "t1_2r": 70, "t1_4r": 150, "t2_2r": 40, "q_r": 1, "v": 0}
OTOP_CASES = [
    dict(OTOP_BASE),
    dict(OTOP_BASE, uf=1.4),
    dict(OTOP_BASE, t1_2r=0, t1_4r=200, t2_2r=0),
    dict(OTOP_BASE, tn_5=-32, t1_r=150, t2_r=70, t3_r=95, t1_4r=150),
    dict(OTOP_BASE, tn_5=-20.1, tn_1=8, t1_r=115, t2_r=70, t3_r=95, t1_2r=65, t1_4r=115, t2_2r=0),
    dict(OTOP_BASE, tn_5=-21, tvn_r=20, tvb_tr=20, t1_r=105, t2_r=70, t3_r=95, uf=0.5),
]


@pytest.fixture(scope="module")
def reference() -> dict:
    # Точки графика — те, что выдаёт веб (шаг 1 °C от tn_5); при дробной tn_5 сетка десктопа
    # (sety/tg/tg_h.tg_range) другая — см. docs/acceptance-numeric.md.
    otop = [(params, [p["tn"] for p in calculate_otop_curve(params)]) for params in OTOP_CASES]
    cases = {"elevator": ELEVATOR_CASES, "orifice": ORIFICE_CASES, "otop": otop}
    proc = subprocess.run(
        [sys.executable, "-c", _REFERENCE, str(SETY_ROOT)],
        input=json.dumps(cases).encode(), capture_output=True, cwd=str(SETY_ROOT), timeout=120,
    )
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-2000:]
    return json.loads(proc.stdout)


# ---------------------------------------------------------------- элеватор (drsh2)

@pytest.mark.parametrize("i", range(len(ELEVATOR_CASES)))
def test_elevator_matches_desktop_drsh2(reference, i):
    g, u, hc, h, _ = ELEVATOR_CASES[i]
    ref = reference["elevator"][i]
    t1, t2 = 150.0, 70.0
    t3 = (t1 + u * t2) / (1 + u)                     # u = (t1 − t3) / (t3 − t2)
    res = calculate_elevator_parameters(flow_g=g, p1=6.0 + h / 10.0, p2=6.0, t1=t1, t2=t2, t3=t3,
                                        delta_h_system=hc)
    assert res["mixing_ratio_u"] == pytest.approx(u, abs=0.01)
    assert res["nozzle_diameter_mm"] == pytest.approx(ref["dc"], abs=0.051)
    assert res["mixing_chamber_diameter_mm"] == pytest.approx(ref["dg"], abs=0.051)
    # drsh2 выдаёт №0 при горловине ≤ 10 мм; стандартного элеватора №0 нет — у веба это №1
    assert res["elevator_number"] == max(1, ref["nal"])


def test_elevator_worked_example(reference):
    ref = reference["elevator"][0]
    assert ref["dg"] == pytest.approx(37.6, abs=0.05) and ref["nal"] == 6
    t3 = (150.0 + 1.4 * 70.0) / 2.4
    res = calculate_elevator_parameters(flow_g=10, p1=8.0, p2=6.0, t1=150, t2=70, t3=t3, delta_h_system=1.5)
    assert res["mixing_chamber_diameter_mm"] == pytest.approx(37.6, abs=0.05)
    assert res["elevator_number"] == 6


# ---------------------------------------------------------------- шайба движка (drsh1 / drsh3)

def _excel_round(x: float, digits: int) -> float:
    """ROUND из Excel: половина — от нуля."""
    q = 10 ** digits
    return math.copysign(math.floor(abs(x) * q + 0.5) / q, x)


@pytest.mark.parametrize("i", range(len(ORIFICE_CASES)))
def test_orifice_matches_desktop_drsh1_drsh3(reference, i):
    g, h = ORIFICE_CASES[i]
    d1 = reference["drsh1"][i]
    ferr, _, d3 = reference["drsh3"][i]
    assert d1 == pytest.approx(d3 if not ferr else d1)  # drsh1 и drsh3 — одна формула Дш
    web = calculate_orifice_diameter(flow_g=g, delta_h=h)
    assert web == pytest.approx(max(3.0, _excel_round(d1, 1)), abs=1e-9)
    if ferr:
        assert d3 == 3.0 and web == 3.0  # минимальный диаметр отверстия


# ---------------------------------------------------------------- бланк dross.py

def _dross_formulas() -> dict[str, str]:
    src = DROSS_PY.read_bytes().decode("utf-8")
    cells = dict(re.findall(r"write_text2\(ws,\s*'(G\d+)',\s*'(=[^']+)'", src))
    assert {"G17", "G20", "G21", "G22", "G23", "G26", "G29", "G32", "G35", "G38", "G41", "G43"} <= set(cells)
    return cells


def _excel_eval(formulas: dict[str, str], inputs: dict[str, float], cell: str) -> float:
    """Вычисляет ячейку по формулам бланка: IF / ROUND / POWER, арифметика, ссылки на ячейки."""
    if cell in inputs:
        return inputs[cell]
    expr = formulas[cell][1:]
    expr = re.sub(r"\b([A-Z]{1,2}\d+)\b", lambda m: f'_c("{m.group(1)}")', expr)
    expr = expr.replace("IF(", "_if(").replace("ROUND(", "_round(").replace("POWER(", "_power(")
    env = {
        "_c": lambda name: _excel_eval(formulas, inputs, name),
        "_if": lambda cond, a, b: a if cond else b,
        "_round": _excel_round,
        "_power": math.pow,
    }
    return float(eval(expr, {"__builtins__": {}}, env))  # формулы — из исходника десктопа в репозитории


SHEET_CASES = [
    # P1, P2 (атм), Qот, Qв, Qгвс max (Гкал/ч), t1, t2
    (7.0, 4.5, 0.8, 0.12, 0.3, 132, 70),
    (6.0, 4.0, 1.2, 0.2, 0.4, 150, 70),
    (5.5, 4.7, 0.05, 0.0, 0.02, 130, 70),
    (9.0, 6.0, 3.5, 0.9, 1.1, 115, 70),
    (6.3, 5.0, 0.35, 0.05, 0.15, 105, 70),
]


@pytest.mark.parametrize("p1, p2, q_ot, q_v, q_gvs, t1, t2", SHEET_CASES)
def test_throttling_sheet_matches_dross_blank(p1, p2, q_ot, q_v, q_gvs, t1, t2):
    formulas = _dross_formulas()
    kcal = lambda gcal: gcal * 1_000_000  # в бланке нагрузки в ккал/ч
    inputs = {"G14": kcal(q_ot), "G15": kcal(q_v), "G16": kcal(q_gvs), "E18": t1, "G18": t2, "H7": p1, "K7": p2}
    ref = lambda cell: _excel_eval(formulas, inputs, cell)
    web = calculate_throttling_sheet({"p1": p1, "p2": p2, "q_heating_gcal": q_ot, "q_vent_gcal": q_v,
                                      "q_gvs_gcal": q_gvs, "t1": t1, "t2": t2})
    assert web["g_ot"] == pytest.approx(ref("G20"))
    assert web["g_v"] == pytest.approx(ref("G21"))
    assert web["g_gvs"] == pytest.approx(ref("G22"))
    assert web["h_ras"] == pytest.approx(ref("G23"))
    diameters = {"d_bezelevator": "G26", "d_pump_mix": "G29", "d_pre_nozzle": "G32", "d_nozzle": "G35",
                 "d_ventilation": "G38", "d_heater": "G41", "d_gvs_circulation": "G43"}
    for key, cell in diameters.items():
        flow = {"G38": web["g_v"], "G43": web["g_gvs"]}.get(cell, web["g_ot"])
        if flow <= 0:
            continue  # в бланке 0 т/ч даёт минимальные 3 мм, веб такую шайбу не считает
        assert web[key] == pytest.approx(ref(cell), abs=1e-9), key


# ---------------------------------------------------------------- график ОТОП (tg1.py)

@pytest.mark.parametrize("i", range(len(OTOP_CASES)))
def test_otop_curve_matches_desktop_tg1(reference, i):
    ref = reference["otop"][i]
    web = calculate_otop_curve(OTOP_CASES[i])
    assert len(web) == len(ref)
    for point, (tn, t1, t2, t3) in zip(web, ref):
        assert point["tn"] == tn
        assert point["t1"] == pytest.approx(t1, abs=0.051), tn
        assert point["t2"] == pytest.approx(t2, abs=0.051), tn
        assert point["t3"] == pytest.approx(t3, abs=0.051), tn
