"""scripts/golden/compare_calc.py: сравнение ut_out двух расчётов по ключу и допускам (без БД)."""

import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "compare_calc", Path(__file__).resolve().parents[2] / "scripts" / "golden" / "compare_calc.py")
cc = importlib.util.module_from_spec(_spec)
sys.modules["compare_calc"] = cc  # dataclasses ищут модуль по имени
_spec.loader.exec_module(cc)


def _row(**kw):
    base = {c.column: 0.0 for c in cc.UT.columns}
    base.update(kw)
    return base


def test_identical_calculations_pass():
    rows = {(1, 2): _row(a13=100.0, a19=60.0), (1, 3): _row(a13=-98.0, a19=60.0)}
    res = cc.compare_rows(cc.UT, rows, dict(rows))
    lines, ok = cc.render_table(cc.UT, res)
    assert ok and res["n_bad_values"] == 0 and res["n_common"] == 2
    assert "Все значения в допуске." in lines


def test_tolerance_abs_or_rel_and_worst_rows():
    base = {(1, 2): _row(a13=1000.0), (2, 2): _row(a13=5.0), (3, 2): _row(a13=5.0)}
    new = {(1, 2): _row(a13=1000.5),          # 0.05 % — в относительном допуске
           (2, 2): _row(a13=5.005),           # 0.005 т/ч — в абсолютном допуске
           (4, 2): _row(a13=1.0)}             # участок только в кандидате
    res = cc.compare_rows(cc.UT, base, new)
    assert res["n_bad_values"] == 0 and res["only_base"] == 1 and res["only_new"] == 1
    _, ok = cc.render_table(cc.UT, res)
    assert not ok  # наборы участков разные

    new[(2, 2)] = _row(a13=7.0)
    new[(1, 2)] = _row(a13=1030.0)
    res = cc.compare_rows(cc.UT, base, new, top=5)
    flow = next(s for s in res["stats"] if s["col"].column == "a13")
    assert flow["bad"] == 2 and flow["max_abs"] == 30.0
    # худшие упорядочены по превышению допуска: 2 т/ч на 5 т/ч хуже, чем 30 т/ч на 1000 т/ч
    assert [w[1] for w in res["worst"]] == [(2, 2), (1, 2)]


def test_none_values_are_zero():
    res = cc.compare_rows(cc.UT, {(1, 2): _row(a13=None)}, {(1, 2): _row(a13=0.0)})
    assert res["n_bad_values"] == 0
