"""Анализ режима (gid6 «Анализ»): чистые функции и SQL запросов допустимости."""

import re

import pytest

from database import network_queries as nq
from database import regime_queries as R


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
              "/api/network-queries/length-by-diameter-laying"):
        assert p in paths, p
