"""Прогноз аварийности (database/failure_forecast.py): признаки только по прошлому, срезы, порог паспорта."""

import pandas as pd
import pytest

from database import failure_forecast as ff

T = pd.Timestamp


def _lines():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4], "fileid": [10, 10, 10, 20], "len_m": [100.0, 50.0, 200.0, 80.0],
        "dn": [100, 200, None, 50], "d0": [T("1990-01-01"), None, None, None],
        "dt": [T("2018-06-01"), T("2000-01-01"), None, None], "tt": [1, 2, None, 1], "im": [None] * 4,
        "it": [None] * 4, "nt": [None] * 4, "rc": [T("2012-01-01"), T("2019-01-01"), None, None],
        "depth": [1.5, None, None, None]})
    df["fill"] = df[ff.PASSPORT_FIELDS].notna().sum(axis=1)
    return df


DEFECTS = pd.DataFrame({"id": [1, 2, 3, 4], "lineid": [1, 1, 2, 3],
                        "t": [T("2015-03-01"), T("2017-05-01"), T("2017-08-01"), T("2018-02-01")]})
NEAR = {50: pd.DataFrame({"line": [1, 2, 1], "t": [T("2015-03-01"), T("2015-03-01"), T("2017-05-01")]}),
        200: pd.DataFrame({"line": [1, 2, 3], "t": [T("2015-03-01"), T("2015-03-01"), T("2015-03-01")]})}


def test_features_use_only_the_past():
    f = ff.features(_lines(), DEFECTS, NEAR, T("2017-01-01")).set_index("id")
    assert list(f.index) == [1, 2, 3]                # фрагмент 20 — журнал до среза не вёлся
    assert f.loc[1, "hist_all"] == 1 and f.loc[1, "hist_3y"] == 1 and f.loc[1, "since_last"] == pytest.approx(1.84, abs=0.01)
    # перекладка 2018 — после среза: возраст от первой прокладки 1990
    assert f.loc[1, "age"] == pytest.approx(27, abs=0.01)
    assert f.loc[2, "age"] == pytest.approx(17, abs=0.01)
    assert pd.isna(f.loc[2, "since_rc"])             # капремонт 2019 — после среза
    assert f.loc[1, "since_rc"] == pytest.approx(5, abs=0.01)
    assert f.loc[2, "near50"] == 1 and f.loc[1, "near50"] == 1      # повреждение 2017-05 рядом — ещё будущее
    # метка: повреждение в [2017, 2019)
    assert dict(f.y) == {1: 1, 2: 1, 3: 1}
    assert f.loc[1, "frag_rate"] == pytest.approx(1 / 0.35)        # 1 повреждение до среза на 0,35 км


def test_pick_cutoffs_needs_full_windows_with_enough_events():
    days = pd.date_range("2010-01-01", "2021-01-10", freq="7D")   # последняя запись — 08.01.2021
    d = pd.DataFrame({"id": range(len(days)), "lineid": 1, "t": days})
    t_train, t_test = ff.pick_cutoffs(d, horizon=2, min_events=50)
    assert (t_train, t_test) == (T("2017-01-01"), T("2019-01-01"))  # окно 2019–2020 — последнее полное
    with pytest.raises(ff.ForecastError):
        ff.pick_cutoffs(d, horizon=2, min_events=500)
    with pytest.raises(ff.ForecastError):
        ff.pick_cutoffs(d.iloc[0:0], horizon=2)


def test_passport_threshold_keeps_most_damaged_lines():
    lines = _lines()                                  # заполненность: 1 — 5, 2 — 5, 3 — 0
    assert ff.passport_threshold(lines, DEFECTS, T("2019-01-01")) == 0   # 10-й процентиль из (5, 5, 5, 0)
    assert ff.passport_threshold(lines, DEFECTS, T("2017-07-01")) == 5   # до среза повреждены только 1 и 2
    assert ff.passport_threshold(lines, DEFECTS, T("2000-01-01")) == 0


def test_capture_by_length_budget_in_km():
    import numpy as np

    y = np.array([1, 0, 1, 0, 1])
    score = np.array([0.9, 0.8, np.nan, 0.1, 0.5])
    length = np.array([500.0, 600.0, 100.0, 2000.0, 400.0])
    c = ff.capture_by_length(y, score, length, (0.4, 1, 1.5, 4))
    # очередь: 0 (0,5 км), 1 (1,1), 4 (1,5), 3 (3,5), 2 (пропуск, 3,6)
    assert c == {"0.4": 0.0, "1": 0.333, "1.5": 0.667, "4": 1.0}
    assert ff.capture_by_length(np.zeros(3), np.ones(3), np.ones(3) * 1000, (1,)) == {"1": None}
