"""QA F40: свод ТУ баланс — договорные нагрузки ккал/ч → Гкал/ч (gid6 excel2/tu/tu.sql:32), без живой БД."""

from __future__ import annotations

import asyncio

import pytest

import reports_generator
from database import tu_balance as tb


def _run(coro):
    return asyncio.run(coro)


class FakeConn:
    """ТЭЦ-1: мощности в Гкал/ч, договорные (organizatsii + zhile) — суммы в ккал/ч, как в PG."""

    def __init__(self):
        self.sql: list[str] = []

    async def fetchval(self, sql, *args):
        self.sql.append(sql)
        if "FROM tehnicheskie_usloviya" in sql:
            return 2025
        if "FROM prisoedinennaya_nagruzka_istochnikov" in sql:
            return 2025
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        self.sql.append(sql)
        assert args == (2025, 2025)
        return [
            {
                "heat_source": "ТЭЦ-1",
                "tu_count": 3,
                "installed_power": 1000.0,
                "source_heating": 300.0,
                "source_ventilation": 50.0,
                "source_gvs": 100.0,
                "available_power": 900.0,
                "normative_losses": 40.0,
                # 120 + 30 + 60 Гкал/ч в ккал/ч
                "contract_heating_kcal": 120_000_000.0,
                "contract_ventilation_kcal": 30_000_000.0,
                "contract_gvs_kcal": 60_000_000.0,
                "contract_total_kcal": 210_000_000.0,
                "heating_increase": 5.0,
                "ventilation_increase": 1.0,
                "gvs_max_increase": 2.0,
                "load_increase_total": 8.0,
                "admitted_heating": 4.0,
                "admitted_ventilation": 0.5,
                "admitted_gvs_max": 1.5,
                "admitted_total": 6.0,
            },
            {
                # Источник только с договорной нагрузкой (жильё/организации без мощности)
                "heat_source": "Котельная-2",
                "tu_count": 0,
                "installed_power": 0.0,
                "source_heating": 0.0,
                "source_ventilation": 0.0,
                "source_gvs": 0.0,
                "available_power": 0.0,
                "normative_losses": 0.0,
                "contract_heating_kcal": 2_500_000.0,
                "contract_ventilation_kcal": 0.0,
                "contract_gvs_kcal": 500_000.0,
                "contract_total_kcal": 3_000_000.0,
                "heating_increase": 0.0,
                "ventilation_increase": 0.0,
                "gvs_max_increase": 0.0,
                "load_increase_total": 0.0,
                "admitted_heating": 0.0,
                "admitted_ventilation": 0.0,
                "admitted_gvs_max": 0.0,
                "admitted_total": 0.0,
            },
        ]


def test_contract_loads_converted_from_kcal_to_gcal():
    data = _run(tb.get_technical_condition_balance(FakeConn(), year=2025))
    tec, kot = data["items"]
    assert tec["heat_source"] == "ТЭЦ-1"
    assert tec["contract_heating"] == pytest.approx(120.0)
    assert tec["contract_ventilation"] == pytest.approx(30.0)
    assert tec["contract_gvs"] == pytest.approx(60.0)
    assert tec["contract_total"] == pytest.approx(210.0)
    assert kot["contract_total"] == pytest.approx(3.0)
    # Сырые ккал/ч наружу не уходят
    assert not any(k.endswith("_kcal") for k in tec)


def test_source_capacity_and_tu_are_not_rescaled():
    tec = _run(tb.get_technical_condition_balance(FakeConn(), year=2025))["items"][0]
    assert tec["available_power"] == 900.0
    assert tec["source_heating"] == 300.0
    assert tec["normative_losses"] == 40.0
    assert tec["load_increase_total"] == 8.0
    assert tec["admitted_total"] == 6.0


def test_balance_uses_converted_contract_loads():
    data = _run(tb.get_technical_condition_balance(FakeConn(), year=2025))
    tec, kot = data["items"]
    # 900 - 300 - 50 - 100 - 40 - 210 = 200 Гкал/ч; минус прирост ТУ 8 → 192
    assert tec["balance_connected"] == pytest.approx(200.0)
    assert tec["balance_with_prospective"] == pytest.approx(192.0)
    assert kot["balance_connected"] == pytest.approx(-3.0)
    assert data["totals"]["contract_total"] == pytest.approx(213.0)
    assert data["totals"]["balance_connected"] == pytest.approx(197.0)


def test_sql_sums_contract_loads_in_kcal_columns():
    conn = FakeConn()
    _run(tb.get_technical_condition_balance(conn, year=2025))
    main_sql = conn.sql[-1]
    for col in ("nagruzka__otoplenie_", "nagruzka__ventilyatsiya_", "nagruzka__gvs_", "nagruzka_otoplenie", "nagruzka_gvs"):
        assert col in main_sql
    assert "contract_total_kcal" in main_sql
    assert tb.KCAL_H_PER_GCAL_H == 1_000_000.0


def test_excel_tu_balance_rows_use_same_gcal_values():
    sheet = _run(reports_generator._rows_tu_balance(FakeConn(), reports_generator.ReportScope(year=2025)))
    tec = dict(zip(sheet.headers, sheet.rows[0]))
    assert tec["Всего договорная, Гкал/ч"] == pytest.approx(210.0)
    assert tec["Отопление договорное"] == pytest.approx(120.0)
    assert tec["Баланс по присоединённой нагрузке, Гкал/ч"] == pytest.approx(200.0)
    assert tec["Баланс по присоединённой и перспективной, Гкал/ч"] == pytest.approx(192.0)
