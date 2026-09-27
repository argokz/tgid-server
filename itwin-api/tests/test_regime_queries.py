"""Анализ режима (gid6 «Анализ»): чистые функции и SQL запросов допустимости."""

import re

import pytest

from database import network_queries as nq
from database import regime_queries as R
from database import travel_time as TT


def test_graph_temperature_interpolates_and_switches_to_summer():
    pts = [(-25.0, 70.0), (-24.0, 69.0), (8.0, 40.0)]
    assert R.graph_temperature(pts, -25.0) == 70.0
    assert R.graph_temperature(pts, -24.5) == pytest.approx(69.5)
    assert R.graph_temperature(pts, 0.0) == pytest.approx(69.0 + (40.0 - 69.0) * 24 / 32)
    assert R.graph_temperature(pts, -40.0) == 70.0  # ниже таблицы — крайняя точка
    assert R.graph_temperature(pts, 10.0, summer=65.0) == 65.0  # выше таблицы — летний режим
    assert R.graph_temperature([], -25.0) is None


@pytest.mark.parametrize("scheme,independent", [
    ("1.5", True), ("1.6", True), ("2.9", True), ("3.12", True),
    ("1.1", False), ("2.5", False), ("", False), (None, False), ("abc", False),
])
def test_independent_schemes_do_not_airlock(scheme, independent):
    assert R._is_independent_scheme(scheme) is independent


def test_admissibility_sql_files_are_postgresql_and_parameterized():
    for qid in R.ADMISSIBILITY:
        sql = (R.ADMISSIBILITY_DIR / f"{qid:02d}.sql").read_text(encoding="utf-8")
        assert "$1" in sql and "$fileID$" not in sql, qid
        assert not re.search(r"\[[^\]]*[А-Яа-я]", sql), qid  # [алиасы] MS SQL
        assert "OUTER APPLY" not in sql.upper() and "ISNULL(" not in sql.upper(), qid


def test_admissibility_lower_head_limit_is_consistent():
    sql = (R.ADMISSIBILITY_DIR / "01.sql").read_text(encoding="utf-8")
    assert "0.524" not in sql  # одна формула нижней границы: 0.535·t − 49.2


def test_heat_consumption_system_filters():
    assert set(nq.SYSTEM_FILTERS) == {"closed", "open"}
    assert "= 0" in nq.SYSTEM_FILTERS["closed"] and "> 0" in nq.SYSTEM_FILTERS["open"]


def test_regime_routes_registered():
    import main

    paths = main.app.openapi()["paths"]
    for p in ("/api/analysis/regime/negative-dp", "/api/analysis/regime/airlock",
              "/api/analysis/regime/low-temperature", "/api/analysis/regime/closed-sections",
              "/api/analysis/regime/hydrostatic-zones", "/api/analysis/admissibility/{query_id}",
              "/api/network-queries/length-by-diameter-laying", "/api/network-queries/closed-consumers",
              "/api/analysis/travel-time"):
        assert p in paths, p
    assert "post" in paths["/api/analysis/travel-time"]


def test_format_travel_time_like_desktop():
    assert TT.format_travel_time(0) == "0 часов 0 минут 0 секунд"
    assert TT.format_travel_time(90) == "1 часов 30 минут 0 секунд"
    assert TT.format_travel_time(-150) == "2 часов 30 минут 0 секунд"  # fabs
    assert TT.format_travel_time(7.5) == "0 часов 7 минут 30 секунд"
    assert TT.format_travel_time(TT.NO_FLOW) == TT.NO_FLOW_TEXT


def test_travel_time_supply_along_flow_accumulates():
    segs = [{"q": 10, "time_min": 5, "napr": 1}, None, {"q": 8, "time_min": 3, "napr": 1}]
    acc, trace = TT.accumulate_travel_time(segs, supply=True)
    assert acc == 8 and trace == [5, 5, 8]


def test_travel_time_supply_against_flow_is_no_flow():
    # первый участок не проверяется (timeP = 0), второй — против накопленного направления
    segs = [{"q": 10, "time_min": 5, "napr": 1}, {"q": -4, "time_min": 2, "napr": 1},
            {"q": 10, "time_min": 1, "napr": 1}]
    acc, trace = TT.accumulate_travel_time(segs, supply=True)
    assert acc > 1e70 and trace[0] == 5 and trace[1] > 1e70
    assert TT.format_travel_time(acc) == TT.NO_FLOW_TEXT


def test_travel_time_return_expects_counter_flow():
    # обратка: расход против направления маршрута — нормально (условие десктопа q·napr·t > 0)
    ok = [{"q": -10, "time_min": 4, "napr": 1}, {"q": -3, "time_min": 6, "napr": 1}]
    assert TT.accumulate_travel_time(ok, supply=False)[0] == 10
    bad = [{"q": -10, "time_min": 4, "napr": 1}, {"q": 3, "time_min": 6, "napr": 1}]
    assert TT.accumulate_travel_time(bad, supply=False)[0] > 1e70


def test_travel_time_reverse_oriented_lines_accumulate_negative():
    # маршрут против ориентации линий: napr = −1, накопление со знаком, итог — |t|.
    # a11 ≥ 0, поэтому проверка десктопа фактически сверяет знак q с ориентацией линий
    # (подача q ≥ 0), а не с направлением обхода: обход против потока даёт то же время.
    segs = [{"q": 10, "time_min": 5, "napr": -1}, {"q": 10, "time_min": 2, "napr": -1}]
    acc, _ = TT.accumulate_travel_time(segs, supply=True)
    assert acc == -7 and TT.format_travel_time(acc) == "0 часов 7 минут 0 секунд"
    rev = [{"q": -10, "time_min": 5, "napr": -1}, {"q": -10, "time_min": 2, "napr": -1}]
    assert TT.accumulate_travel_time(rev, supply=True)[0] > 1e70


def test_travel_time_missing_results_count_as_zero():
    segs = [{"q": None, "time_min": None, "napr": 1}, {"q": 5, "time_min": 2, "napr": 1}]
    assert TT.accumulate_travel_time(segs, supply=True)[0] == 2
