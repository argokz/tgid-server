"""Перспективный прирост нагрузки (database/load_perspective.py): очистка реестра ТУ, полнота актов, сроки, тренд."""
from datetime import date

import pytest

from database import load_perspective as lp


def tu(i, issued, inc=1.0, act=None, ann=None, label="ТЭЦ", name=None, total=None):
    return {"id": i, "issued": issued, "act": act, "annulled": ann, "prirost": inc, "total": total, "increment": inc,
            "label": label,
            "name": name or f"объект {i}"}


def test_increment_not_above_total():
    assert lp.increment(0.52, 5216.0) == 0.52          # ошибка единиц в полной нагрузке
    assert lp.increment(16113.0, 1.61) == 1.61         # ошибка единиц в приросте
    assert lp.increment(None, 2.0) == 2.0 and lp.increment(1.0, None) == 1.0


def test_clean_drops_bad_and_duplicates():
    today = date(2026, 10, 31)
    rows = [tu(1, date(2020, 1, 1)), tu(2, None), tu(3, date(2020, 1, 1), inc=0.0),
            tu(4, date(2020, 5, 1), act=date(2019, 1, 1)), tu(5, date(2020, 5, 1), act=date(2029, 1, 1)),
            tu(6, date(2021, 1, 1), name="ЖК"), tu(7, date(2021, 1, 1), name="жк", act=date(2022, 1, 1))]
    out, dropped = lp.clean(rows, today)
    assert sorted(r["id"] for r in out) == [1, 7]        # из повторов 6/7 остаётся запись с актом
    assert dropped == {"нет даты выдачи": 1, "нет прироста нагрузки": 1, "акт допуска раньше выдачи": 1,
                       "акт допуска в будущем": 1, "повторная запись ТУ": 1}
    assert out[0]["label"] == "ТЭЦ"


def test_acts_complete_until_finds_drop():
    today = date(2026, 10, 31)
    rows = []
    i = 0
    for year, n in {2016: 100, 2017: 110, 2018: 120, 2019: 100, 2020: 105, 2021: 115, 2022: 100, 2023: 110,
                    2024: 15, 2025: 20}.items():
        for _ in range(n):
            i += 1
            rows.append(tu(i, date(year - 1, 6, 1), act=date(year, 6, 1)))
    assert lp.acts_complete_until(rows, today) == date(2024, 1, 1)
    full = [r for r in rows if r["act"].year < 2024]
    assert lp.acts_complete_until(full, date(2024, 3, 1)) == date(2024, 1, 1)   # текущий год не считается


def test_hazards_and_curve():
    cutoff = date(2024, 1, 1)
    # 4 ТУ 2020 г.: подключились на 0-м и 1-м году, одно аннулировано на 1-м, одно ждёт
    rows = [tu(1, date(2020, 1, 1), act=date(2020, 6, 1)), tu(2, date(2020, 1, 1), act=date(2021, 6, 1)),
            tu(3, date(2020, 1, 1), ann=date(2021, 3, 1)), tu(4, date(2020, 1, 1))]
    h = lp.hazards(rows, cutoff, window=10)
    assert h["connect"][0] == pytest.approx(0.25) and h["connect"][1] == pytest.approx(1 / 3)
    assert h["annul"][1] == pytest.approx(1 / 3) and h["at_risk"][2] == 1.0
    curve = lp.connect_curve(h, 0, 2)
    assert curve[0] == pytest.approx(0.25) and curve[1] == pytest.approx(0.75 * 1 / 3)


def test_trend_and_backtest():
    rows = [tu(i, date(y - 1, 1, 1), inc=10.0, act=date(y, 3, 1)) for i, y in enumerate(range(2014, 2024))]
    rate, shares = lp.trend(rows, date(2024, 1, 1))
    assert rate == pytest.approx(10.0) and shares == {"ТЭЦ": pytest.approx(1.0)}
    bt = lp.trend_backtest(rows, date(2024, 1, 1))
    assert bt["cutoff"] == "2019-01-01" and bt["error_share"] == pytest.approx(0.0)
