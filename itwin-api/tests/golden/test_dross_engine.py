"""Эталон диафрагм движка: веб (throttling_calc.calculate_gvs_circulation_diaphragm,
calculate_elevator_engine) против gid8 `python/sety/sety/dross/drvary1.py` (режимы 1 и 6).

drvary1 считается в отдельном процессе, где `import sety` — пакет десктопа gid8 (только чтение).
Сравниваются поля dr_out: циркуляционная диафрагма ГВС b39/b40/b41, сопло элеватора b7/b8/b11,
диафрагма перед соплом (на входе СО) b21/b22/b23, дворовый фасад b24/b25/b26 и подогреватель
ГВС последовательной схемы b30/b31/b32. Без каталога gid8 тест пропускается (GID8_ROOT).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from database.throttling_calc import calculate_elevator_engine, calculate_gvs_circulation_diaphragm

GID8 = Path(os.environ.get("GID8_ROOT") or Path(__file__).resolve().parents[4] / "gid8")
SETY_ROOT = GID8 / "python" / "sety"

pytestmark = pytest.mark.skipif(not (SETY_ROOT / "sety" / "dross" / "drvary1.py").exists(),
                                reason=f"нет исходников sety десктопа ({GID8})")

_REFERENCE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import sety
assert sety.__file__.startswith(sys.argv[1]), sety.__file__
import sety.dross.drvary1 as dv
import sety.dross.drsh2 as d2
dv.w_print = d2.w_print = lambda *a, **k: None
out = []
for case in json.load(sys.stdin):
    drs = {k: 0.0 for k in ("a6", "a7", "a10", "a11", "a12", "a14", "a15", "a16", "a17", "a22", "a23")}
    drs.update(case["drs"])
    dr_out = {f"b{i}": 0.0 for i in range(1, 44)}
    dr_out.update(case.get("dr_out") or {})
    fss = case["fss"]
    a = case["args"]
    dv.drvary1(drs, dr_out, a["rasp"], a["pihP"], a["pihO"], a.get("Gz", 0.0), a["otopl"], a.get("otn_fs", 1.0),
               0.0, 0.0, 0.0, a.get("gvps", 0.0), 0.0, a.get("gvop", 0.0), a.get("gvoo", 0.0), a.get("rez", 0.0),
               fss, a.get("ho", 0.0), 0.0, a.get("hgv", 0.0), "golden", a.get("rezh", 1), message=False)
    out.append(dr_out)
json.dump(out, sys.stdout)
'''


def _reference(cases: list[dict]) -> list[dict]:
    proc = subprocess.run([sys.executable, "-c", _REFERENCE, str(SETY_ROOT)], input=json.dumps(cases).encode(),
                          capture_output=True, cwd=str(SETY_ROOT), timeout=120)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")[-2000:]
    return json.loads(proc.stdout)


# ---------------------------------------------------------------- циркуляционная линия ГВС

CIRC = [
    # rez, a12, a11, pihO, a15
    (0.8, 60.0, 3.0, 35.0, 3.0),
    (0.05, 60.0, 3.0, 35.0, 3.0),     # маленький расход — шайбы минимального диаметра, несколько штук
    (2.5, 70.0, 5.0, 40.0, 3.0),
    (0.3, 45.0, 2.0, 30.0, 4.0),
    (1.2, 50.0, 1.0, 20.0, 3.0),
    (0.4, 30.0, 3.0, 35.0, 3.0),      # напора нет — диафрагма не считается
]


def _circ_case(rez, a12, a11, pih_o, a15, draw_from):
    if draw_from == "supply":
        fss = [0, 0, 0, 0, 0, 0, 1, 0]
        args = {"rasp": 30.0, "pihP": pih_o + 30.0, "pihO": pih_o, "otopl": 0.0, "gvop": 1.0, "rez": rez}
    else:
        fss = [3, 0, 0, 0, 0, 0, 0, 1]
        args = {"rasp": 30.0, "pihP": pih_o + 30.0, "pihO": pih_o, "otopl": 5.0, "gvoo": 1.0, "rez": rez,
                "ho": 1.0}
    return {"drs": {"a10": 2.0, "a11": a11, "a12": a12, "a15": a15, "a7": 1.0}, "fss": fss, "args": args}


@pytest.mark.parametrize("draw_from", ["supply", "return"])
def test_gvs_circulation_matches_drvary1(draw_from):
    ref = _reference([_circ_case(*c, draw_from) for c in CIRC])
    for (rez, a12, a11, pih_o, a15), d in zip(CIRC, ref):
        web = calculate_gvs_circulation_diaphragm(circulation_flow=rez, required_head=a12, circulation_loss=a11,
                                                  return_head=pih_o, draw_from=draw_from, min_diameter=a15)
        if a12 - a11 - pih_o <= 0:
            assert web["diameter_mm"] is None and d["b39"] == 0.0
            continue
        assert web["diameter_mm"] == pytest.approx(d["b39"], abs=0.005)
        assert web["head_dissipated_m"] == pytest.approx(d["b40"], rel=1e-9)
        if draw_from == "supply":
            assert d["b41"] == pytest.approx(rez)  # в ветке обратки десктоп пишет в b41 расход на отопление


# ---------------------------------------------------------------- элеватор и диафрагма перед соплом

ELEV = [
    # rasp, otopl, u, hc, a14, rezh, b37, street_share, gvps, a23
    (20.0, 10.0, 1.4, 1.5, 3.0, 1, 0.0, 1.0, 0.0, 0.0),
    (45.0, 6.0, 1.4, 1.5, 3.0, 6, 0.0, 1.0, 0.0, 0.0),     # режим 6, > 40 м: половина — на диафрагму
    (60.0, 0.3, 1.4, 1.5, 5.0, 1, 0.0, 1.0, 0.0, 0.0),     # сопло упёрлось в минимум — диафрагма
    (60.0, 0.3, 1.4, 1.5, 5.0, 1, 0.0, 0.6, 0.0, 0.0),     # два фасада
    (35.0, 0.8, 2.2, 1.0, 6.0, 1, 4.0, 1.0, 0.0, 0.0),     # подпорно-циркуляционная диафрагма b37
    (50.0, 0.4, 1.4, 1.5, 6.0, 1, 0.0, 1.0, 0.2, 3.0),     # последовательная ГВС — диафрагма подогревателя
    (80.0, 2.0, 1.4, 1.5, 3.0, 6, 0.0, 1.0, 0.0, 0.0),
    (5.0, 3.0, 1.4, 1.5, 3.0, 1, 0.0, 1.0, 0.0, 0.0),
]


def _elev_case(rasp, otopl, u, hc, a14, rezh, b37, share, gvps, a23):
    fss = [1, 0, 0, 0, 0, 1 if gvps > 0 else 0, 0, 0]
    return {
        "drs": {"a6": u, "a7": hc, "a14": a14, "a15": 3.0, "a23": a23, "a17": 0},
        "dr_out": {"b37": b37}, "fss": fss,
        "args": {"rasp": rasp, "pihP": 60.0 + rasp, "pihO": 60.0, "otopl": otopl, "otn_fs": share, "gvps": gvps,
                 "ho": 1.4 * hc * (1 + u) ** 2, "rezh": rezh},
    }


@pytest.mark.parametrize("i", range(len(ELEV)))
def test_elevator_engine_matches_drvary1(i):
    rasp, otopl, u, hc, a14, rezh, b37, share, gvps, a23 = ELEV[i]
    d = _reference([_elev_case(*ELEV[i])])[0]
    web = calculate_elevator_engine(available_head=rasp, heating_flow=otopl, mixing_ratio=u, system_loss=hc,
                                    min_nozzle_diameter=a14, regime=rezh, circulation_head=b37,
                                    gvs_heater_loss=a23, gvs_sequential_flow=gvps, street_share=share)
    if web["nozzle_diameter_mm"] is None:
        assert d["b7"] == 0.0
        return
    assert web["nozzle_diameter_mm"] == pytest.approx(d["b7"], abs=0.005)
    assert web["elevator_number"] == d["b11"]
    assert web["nozzle_head_m"] == pytest.approx(d["b8"], rel=1e-9)
    pre = web["pre_nozzle"]
    assert (pre is not None) == (d["b21"] != 0.0)
    if pre is not None:
        assert pre["diameter_mm"] == pytest.approx(d["b21"], abs=0.005)
        if d["b23"]:  # в режиме 6 (пополам) десктоп b22/b23 не пишет
            assert pre["head_one_m"] == pytest.approx(d["b22"], rel=1e-9)
            assert pre["flow_t_h"] == pytest.approx(d["b23"], rel=1e-9)
    yard = web["yard_facade"]
    assert (yard is not None) == (d["b24"] != 0.0)
    if yard is not None:
        assert yard["diameter_mm"] == pytest.approx(d["b24"], abs=0.005)
        assert yard["head_one_m"] == pytest.approx(d["b25"], rel=1e-9)
        assert yard["flow_t_h"] == pytest.approx(d["b26"], rel=1e-9)
    heater = web["gvs_heater"]
    assert (heater is not None) == (d["b30"] != 0.0)
    if heater is not None:
        assert heater["diameter_mm"] == pytest.approx(d["b30"], abs=0.005)
        assert heater["head_one_m"] == pytest.approx(d["b31"], rel=1e-9)
