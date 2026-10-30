"""Баланс расхода по зонам: разрезание сети по расходомерам, направление, ночной расход, вывод."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from database import flow_balance as fb

# источник S(1) —[10, расходомеры]— 2 —[11]— 3 —[12, расходомеры]— 4 —[13]— 5 (потребитель)
#                                            \__[14, задвижка закрыта]__ 6
LINES = {10: (1, 2), 11: (2, 3), 12: (3, 4), 13: (4, 5), 14: (3, 6)}


def _net(closed=(14,)):
    adj = {}
    for lid, (a, b) in LINES.items():
        adj.setdefault(a, []).append((lid, b))
        adj.setdefault(b, []).append((lid, a))
    info = {lid: {"id": lid, "nodeid1": a, "nodeid2": b, "length": 100.0} for lid, (a, b) in LINES.items()}
    return {"adj": adj, "line_info": info, "normally_closed_lines": set(closed), "source_kinds": {1: "heat_source"}}


def test_split_zones_by_meters_and_closed_valves():
    zones = {z["key"]: z for z in fb.split_zones(_net(), {10, 12})}
    assert zones[1]["nodes"] == {1} and zones[1]["feeds"] == {1: "heat_source"} and zones[1]["boundary"] == [(10, "n1")]
    assert zones[2]["nodes"] == {2, 3} and sorted(zones[2]["boundary"]) == [(10, "n2"), (12, "n1")]
    assert zones[4]["nodes"] == {4, 5} and zones[4]["boundary"] == [(12, "n2")]
    assert 6 not in zones[2]["nodes"]  # за закрытой задвижкой — не зона расходомеров
    ring = fb.split_zones(_net(closed=()), {11})
    assert ring[0]["internal"] == [] and len(ring) == 2


def test_inflow_sign_and_kind():
    assert fb.inflow_sign(15000, "n2") == 1 and fb.inflow_sign(15000, "n1") == -1
    assert fb.inflow_sign(-14000, "n1") == 1 and fb.inflow_sign(0.0, "n1") is None and fb.inflow_sign(None, "n2") is None
    assert fb.zone_kind({"feeds": {}}, 10) == "zone"
    assert fb.zone_kind({"feeds": {1: "heat_source"}}, 0) == "source"
    assert fb.zone_kind({"feeds": {1: "heat_source"}}, 5) == "open"  # источник с сетью внутри — не закрыта
    assert fb.zone_kind({"feeds": {7: "set_pressure"}}, 0) == "open"


def _hours(values_by_night, hours=(2, 3, 4)):
    out = {}
    for day, v in values_by_night.items():
        for h in hours:
            out[datetime(2026, 10, day, h, 0).astimezone().astimezone(timezone.utc)] = v
    out[datetime(2026, 10, 29, 14, 0).astimezone().astimezone(timezone.utc)] = 9999.0  # день — не ночь
    return out


def test_night_values_and_trend():
    nights = fb.night_values(_hours({24: 1150, 25: 1152, 26: 1148, 27: 1151, 28: 1149, 29: 1230}))
    assert [n[0] for n in nights] == ["2026-10-24", "2026-10-25", "2026-10-26", "2026-10-27", "2026-10-28",
                                      "2026-10-29"] and nights[0][2] == 3
    trend = fb.night_trend(nights)
    assert trend["grew"] and trend["growth"] == pytest.approx(80.0) and trend["baseline"] == 1150.0
    assert fb.night_trend(nights[:3]) is None  # мало ночей для сравнения
    flat = fb.night_trend(fb.night_values(_hours({24: 1150, 25: 1170, 26: 1130, 27: 1160, 28: 1140})))
    assert not flat["grew"] and flat["threshold"] > 40  # шумные ночи — порог выше


def test_verdict():
    assert fb.verdict("open", 500, 10, None) == "open"
    assert fb.verdict("zone", None, None, None) == "no_data"
    assert fb.verdict("zone", 100, 30, None) == "leak"
    assert fb.verdict("zone", -100, 30, None) == "check"
    assert fb.verdict("zone", 10, 300, {"grew": True}) == "growth"
    assert fb.verdict("source", 300, 780, {"grew": False}) == "ok"


def test_balance_zone_and_source(monkeypatch):
    now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    sensors = [
        {"id": 1, "code": "G1", "name": "", "pipe": "supply", "unit": "t_h", "line_id": 10, "fileid": 74},
        {"id": 2, "code": "G2", "name": "", "pipe": "return", "unit": "t_h", "line_id": 10, "fileid": 74},
        {"id": 3, "code": "Z1", "name": "", "pipe": "supply", "unit": "t_h", "line_id": 12, "fileid": 74},
        {"id": 4, "code": "Z2", "name": "", "pipe": "return", "unit": "m3_h", "line_id": 12, "fileid": 74},
    ]
    model = {(10, 2): 1000.0, (10, 3): -900.0, (12, 2): 400.0, (12, 3): -380.0}
    window = {1: (1000.0, now), 2: (880.0, now), 3: (400.0, now), 4: (350.0 / 0.975, now)}

    async def flows(conn):
        return sensors

    async def model_flows(conn, used):
        return model

    async def window_avg(conn, ids, n):
        return window

    async def hourly(conn, ids, n):
        return {}

    async def consumers(conn):
        return {5}

    monkeypatch.setattr(fb, "_flow_sensors", flows)
    monkeypatch.setattr(fb, "_model_flows", model_flows)
    monkeypatch.setattr(fb, "_window_avg", window_avg)
    monkeypatch.setattr(fb, "_hourly", hourly)
    monkeypatch.setattr(fb, "_consumer_nodes", consumers)
    res = asyncio.run(fb.balance(None, _net(), now))
    zones = {z["key"]: z for z in res["zones"]}
    src = zones[1]  # подпитка: 1000 − 880 = 120 против 100 по модели
    assert src["kind"] == "source" and src["fact"] == 120.0 and src["model"] == 100.0 and src["excess"] == 20.0
    end = zones[4]  # зона за вторым расходомером: приток 400 − 350 = 50 против 20 по модели
    assert end["kind"] == "zone" and end["fact"] == 50.0 and end["excess"] == 30.0 and end["consumers"] == 1
    assert end["uncertainty"] == pytest.approx(((0.02 * 400) ** 2 + (0.02 * 350) ** 2) ** 0.5, abs=0.1)
    assert end["status"] == "leak"  # 30 > 2 × 10,6
    mid = zones[2]  # между расходомерами: приток с ТЭЦ минус уход дальше
    assert mid["fact"] == pytest.approx(120 - 50) and mid["status"] == "ok"

    window[4] = (350.0 / 0.975, now - timedelta(hours=5))
    res = asyncio.run(fb.balance(None, _net(), now))
    assert {z["key"]: z["status"] for z in res["zones"]}[4] == "no_data"


class _AlertConn:
    """Состояние зон и тревоги в памяти (как tgid_balance_zone / tgid_balance_alert)."""

    def __init__(self, prev=None):
        self.state = dict(prev or {})
        self.alerts = []

    async def fetch(self, q, *a):
        return [{"zone_key": k, "status": v} for k, v in self.state.items()]

    async def execute(self, q, key, status, boundary):
        self.state[key] = status

    async def fetchval(self, q, *a):
        self.alerts.append(a)
        return len(self.alerts)


def _zone(key, status, night=None):
    return {"key": key, "kind": "source", "status": status, "boundary": [324808], "excess": 301.0,
            "uncertainty": 764.0, "night": night}


def test_check_alerts_transitions(monkeypatch):
    night = {"night": "2026-10-30", "value": 1230.5, "baseline": 1149.7, "growth": 80.9, "threshold": 5.1,
             "nights": 7, "grew": True}
    zones = [_zone(1, "growth", night), _zone(2, "ok"), _zone(3, "open")]

    async def balance(conn, net, now=None):
        return {"zones": zones}

    monkeypatch.setattr(fb, "balance", balance)
    conn = _AlertConn()
    ids = asyncio.run(fb.check_alerts(conn, {}))
    # первая оценка: утечка — сразу тревога; норма — только запоминается; незакрытая — без состояния
    assert ids == [1] and conn.state == {1: "growth", 2: "normal"}
    key, kind, boundary, status, prev, night_date = conn.alerts[0][:6]
    assert (key, status, prev, str(night_date)) == (1, "growth", None, "2026-10-30") and conn.alerts[0][8] == 80.9
    assert asyncio.run(fb.check_alerts(conn, {})) == []  # без перехода — без тревоги
    zones[0] = _zone(1, "ok")
    zones[1] = _zone(2, "leak")
    ids = asyncio.run(fb.check_alerts(conn, {}))
    assert len(ids) == 2 and conn.state == {1: "normal", 2: "leak"}
    assert [a[3:5] for a in conn.alerts[1:]] == [("normal", "growth"), ("leak", "normal")]
