"""Прогноз нагрузки по погоде: температурный график, составляющие нагрузки, факт по датчикам, Open-Meteo."""

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from database import load_forecast as lf
from database import weather

GRAPH = [  # как deployedtempgraphs ТЭЦ Алматы: -25 → Q_отн 1, излом +5…+8
    {"tn": -25.0, "q_otn": 1.0, "t1": 132.0, "t2": 70.0},
    {"tn": -10.0, "q_otn": 0.666667, "t1": 98.19, "t2": 56.85},
    {"tn": 5.0, "q_otn": 0.333333, "t1": 62.45, "t2": 41.79},
    {"tn": 8.0, "q_otn": 0.298626, "t1": 60.0, "t2": 41.46},
]
BASE = {"tn": -25.0, "heating": 1000.0, "vent": 100.0, "hw": 300.0}
NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


def test_graph_interpolates_and_clamps():
    mid = lf.graph_at(GRAPH, -17.5)
    assert mid["q_otn"] == pytest.approx(0.8333335) and mid["t1"] == pytest.approx(115.095)
    assert lf.graph_at(GRAPH, -40)["q_otn"] == 1.0
    assert lf.graph_at(GRAPH, 14)["t1"] == 60.0  # теплее излома — крайняя точка


def test_load_scales_heating_and_vent_keeps_hot_water():
    at_design = lf.load_at(BASE, GRAPH, -25)
    assert at_design == {"heating": 1000.0, "vent": 100.0, "hw": 300.0, "total": 1400.0, "t1": 132.0, "t2": 70.0}
    warm = lf.load_at(BASE, GRAPH, 5)
    assert warm["heating"] == pytest.approx(333.33, abs=0.01) and warm["hw"] == 300.0
    assert lf.load_at(BASE, GRAPH, 20)["heating"] == pytest.approx(298.63, abs=0.01)  # сезон — по календарю
    # основа — расчёт при -10: пересчёт идёт через отношение Q_отн
    assert lf.load_at({**BASE, "tn": -10.0}, GRAPH, -25)["heating"] == pytest.approx(1500.0, abs=0.1)


def test_fact_heat_open_and_closed():
    assert lf.fact_heat(29500, 28000, 62.5, 41.8) == pytest.approx(665.85, abs=0.01)
    assert lf.fact_heat(10000, None, 100, 60) == 400.0  # без расхода обратки — закрытая схема
    assert lf.fact_heat(None, 1, 100, 60) is None and lf.fact_heat(1000, 900, 100, None) is None


def test_summary_next_day():
    src = {"base": BASE, "graph": GRAPH}
    hours = [{"ts": NOW + timedelta(hours=i), "t_air": -10.0 if i < 12 else 5.0} for i in range(-3, 30)]
    s = lf.summary(src, hours, NOW)
    assert s["hours"] == 24 and s["t_min"] == -10.0 and s["t_max"] == 5.0 and s["tn_calc"] == -10
    assert s["q_max"] == pytest.approx(lf.load_at(BASE, GRAPH, -10)["total"], abs=0.1)
    assert lf.summary(src, [], NOW) == {"hours": 0}


def test_parse_open_meteo_splits_fact_and_forecast():
    data = {"hourly": {"time": ["2026-10-30T10:00", "2026-10-30T11:00", "2026-10-30T12:00", "2026-10-30T13:00"],
                       "temperature_2m": [4.1, None, 5.2, 99.0]}}
    rows = weather.parse_open_meteo(data, NOW + timedelta(minutes=20))
    assert rows == [(datetime(2026, 10, 30, 10, tzinfo=timezone.utc), "fact", 4.1),
                    (datetime(2026, 10, 30, 12, tzinfo=timezone.utc), "forecast", 5.2)]
    with pytest.raises(ValueError):
        weather.parse_open_meteo({"hourly": {"time": ["2026-10-30T10:00"], "temperature_2m": []}}, NOW)


def test_rows_from_file_hourly_mean_single_column():
    t0 = datetime(2026, 10, 30, 10, 5, tzinfo=timezone.utc)
    rows = weather.rows_from_file([("T", t0, 4.0), ("T", t0 + timedelta(minutes=30), 5.0),
                                   ("T", t0 + timedelta(hours=1), -99.0)])
    assert rows == [(datetime(2026, 10, 30, 10, tzinfo=timezone.utc), 4.5)]
    with pytest.raises(weather.WeatherError):
        weather.rows_from_file([("T", t0, 1.0), ("P", t0, 2.0)])


def test_weather_row_validation():
    with pytest.raises(ValueError):
        weather.WeatherRow(ts=NOW, t_air=-80)
    assert weather.WeatherRow(ts=NOW.replace(minute=40), t_air=3).ts == NOW


class _Conn:
    def __init__(self, last=None):
        self.last, self.stored = last, []

    async def fetchval(self, q, *a):
        return self.last

    async def fetchrow(self, q, *a):
        return {"lat": 43.3, "lon": 76.9}

    async def executemany(self, q, rows):
        self.stored.extend(rows)


def test_refresh_fetches_when_stale_and_survives_errors(monkeypatch):
    monkeypatch.setattr(weather, "PROVIDER", "open-meteo")
    monkeypatch.setattr(weather, "_last_attempt", {})
    monkeypatch.setattr(weather, "_coords", {})
    monkeypatch.delenv("WEATHER_LAT", raising=False)
    calls = []

    async def fetch(lat, lon, client=None):
        calls.append((lat, lon))
        return {"hourly": {"time": ["2030-01-01T00:00"], "temperature_2m": [-5.0]}}

    monkeypatch.setattr(weather, "fetch_open_meteo", fetch)
    conn = _Conn(last=None)
    state = asyncio.run(weather.refresh(conn))
    assert calls == [(43.3, 76.9)] and state["rows"] == 1 and conn.stored[0][1:] == ("forecast", -5.0, "open-meteo")
    fresh = _Conn(last=datetime.now(timezone.utc))
    asyncio.run(weather.refresh(fresh))
    assert len(calls) == 1  # свежие данные — не спрашивать

    async def down(lat, lon, client=None):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(weather, "fetch_open_meteo", down)
    state = asyncio.run(weather.refresh(_Conn(), force=True))
    assert state["error"].startswith("Open-Meteo недоступен")
    monkeypatch.setattr(weather, "PROVIDER", "none")
    assert asyncio.run(weather.refresh(_Conn(), force=True))["provider"] == "none"


def test_regime_tn_now_clamped(monkeypatch):
    from database import telemetry_regime as rg

    class C:
        async def fetchval(self, q, *a):
            return True

    async def hourly(conn, start, end):
        return [{"ts": start, "kind": "fact", "t_air": 13.6, "source": "open-meteo"}]

    monkeypatch.setattr(weather, "hourly", hourly)
    assert asyncio.run(rg._tn_now(C(), -25.0, 8.0)) == 8.0  # выше конца графика sety откажет — Tн = t_vnew
    assert asyncio.run(rg._tn_now(C(), -25.0, 20.0)) == 14.0


def test_open_hot_water_follows_water_temperature_like_sety():
    # открытый водоразбор из подачи: на стенде sety при +6 °C (t1 62,3) дал 127 Гкал/ч против 277 при -25 (t1 132)
    base = {"tn": -25.0, "tx": 5.0, "heating": 1018.59, "vent": 107.97, "hw": 277.03,
            "hw_closed": 0.0, "hw_supply": 277.03, "hw_return": 0.0}
    graph = sorted(GRAPH + [{"tn": 6.0, "q_otn": 0.311357, "t1": 60.0, "t2": 40.69}], key=lambda g: g["tn"])
    at6 = lf.load_at(base, graph, 6.0)
    assert at6["hw"] == pytest.approx(277.03 * 55 / 127, abs=0.01)
    # сверка с движком (расчёт 713, -tg, Tн +6): 328,5 + 39,4 + 127,4 = 495,4 Гкал/ч — прогноз в пределах 6 %
    assert at6["total"] == pytest.approx(495.4, rel=0.06)
