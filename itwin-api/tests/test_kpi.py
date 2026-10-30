"""Показатели эксплуатации (database/kpi.py, routers/kpi.py)."""

import asyncio
from datetime import date

import pytest

from database import kpi


def test_pure_rules():
    assert kpi.parse_bbox(None) is None
    assert kpi.parse_bbox("71.4,51.1,71.5,51.2") == (71.4, 51.1, 71.5, 51.2)
    for bad in ("1,2,3", "a,b,c,d", "71.5,51.1,71.4,51.2", "0,95,1,96"):
        with pytest.raises(kpi.KpiError):
            kpi.parse_bbox(bad)
    assert [kpi.diameter_bucket(d) for d in (None, 0, 57, 100, 150, 530, 1020)] == [
        "нет данных", "нет данных", "до 100", "до 100", "101–200", "501–700", "свыше 700"]
    assert kpi.per_100km_year(35, 7151.8, 364) == 0.49
    assert kpi.per_100km_year(5, 0, 365) is None
    assert kpi.month_keys(date(2025, 11, 15), date(2026, 2, 1)) == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert kpi.default_period(date(2026, 10, 30)) == (date(2025, 10, 1), date(2026, 10, 30))
    with pytest.raises(kpi.KpiError, match="позже"):
        kpi.check_period(date(2026, 2, 1), date(2026, 1, 1))
    with pytest.raises(kpi.KpiError, match="10 лет"):
        kpi.check_period(date(2000, 1, 1), date(2026, 1, 1))


class DefectConn:
    def __init__(self, rows, open_now=4, repairs=None):
        self.rows = rows
        self.open_now = open_now
        self.repairs = repairs or {"done": 3, "avg_days": 4.25}
        self.calls: list[tuple[str, tuple]] = []

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        if "Find_SRID" in sql:
            return 9995
        return self.open_now

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self.rows

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self.repairs


def test_defects_grouped_by_month_category_state():
    rows = [
        {"month": "2026-01", "category_id": 6, "category": "Порыв", "state_id": 1, "state": "Нарушение", "source_id": 1, "source": "Эксплуатация", "n": 3},
        {"month": "2026-01", "category_id": None, "category": None, "state_id": 3, "state": "После ремонта", "source_id": 1, "source": "Эксплуатация", "n": 1},
        {"month": "2026-03", "category_id": 6, "category": "Порыв", "state_id": 3, "state": "После ремонта", "source_id": 6, "source": "Осмотр", "n": 2},
    ]
    conn = DefectConn(rows)
    out = asyncio.run(kpi.defects(conn, date(2026, 1, 1), date(2026, 3, 31), fileid=74, bbox=(71.4, 51.1, 71.5, 51.2)))
    assert out["total"] == 6 and out["open_now"] == 4
    assert out["by_month"] == [{"month": "2026-01", "count": 4}, {"month": "2026-02", "count": 0}, {"month": "2026-03", "count": 2}]
    assert out["by_category"] == [{"id": 6, "name": "Порыв", "count": 5}, {"id": None, "name": "не указано", "count": 1}]
    assert out["by_state"] == [{"id": 1, "name": "Нарушение", "count": 3}, {"id": 3, "name": "После ремонта", "count": 3}]
    assert out["repairs_done"] == 3 and out["repair_avg_days"] == 4.2
    sql, args = next(c for c in conn.calls if "GROUP BY 1, 2" in c[0])
    assert "ST_MakeEnvelope" in sql and "9995" in sql and "fileid" in sql
    assert args[:3] == (date(2026, 1, 1), date(2026, 3, 31), 74)  # период и фильтры — свои параметры запроса
    open_sql, open_args = next(c for c in conn.calls if "ANY(" in c[0])
    assert open_args[0] == list(kpi.DEFECT_OPEN_STATES) and len(open_args) == 6


class NetConn:
    def __init__(self):
        self.fetches = 0

    async def fetch(self, sql, *args):
        self.fetches += 1
        assert "tgid_scenario" in sql and "removed" in sql
        return [{"diameter": 150, "decade": 2010, "km": 1200.0, "n": 10},
                {"diameter": 120, "decade": None, "km": 300.0, "n": 3},
                {"diameter": 800, "decade": 1980, "km": 50.0, "n": 1}]


def test_network_buckets_and_cache():
    kpi._network_cache.clear()
    conn = NetConn()
    out = asyncio.run(kpi.network(conn, cache_key="t"))
    assert out["km"] == 1550.0 and out["lines"] == 14
    assert out["by_diameter"] == [{"name": "101–200", "km": 1500.0}, {"name": "свыше 700", "km": 50.0}]
    assert out["by_decade"] == [{"name": "1980-е", "km": 50.0}, {"name": "2010-е", "km": 1200.0}, {"name": "нет даты", "km": 300.0}]
    asyncio.run(kpi.network(conn, cache_key="t"))
    assert conn.fetches == 1  # второй раз — из кэша
    asyncio.run(kpi.network(conn, cache_key="t", fileid=74))
    assert conn.fetches == 2
    kpi._network_cache.clear()


def test_endpoints(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from auth import invalidate_user_status
    from routers import kpi as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()
    calls = {}

    @asynccontextmanager
    async def acquire():
        yield None

    async def fake_dashboard(conn, start, end, *, fileid, bbox, cache_key):
        calls["dash"] = (start, end, fileid, bbox)
        return {"ok": True}

    async def fake_points(conn, start, end, **kw):
        calls["points"] = kw
        return {"type": "FeatureCollection", "features": []}

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(kpi, "dashboard", fake_dashboard)
    monkeypatch.setattr(kpi, "defect_points", fake_points)
    client = TestClient(main.app)
    r = client.get("/api/v1/kpi/dashboard", params={"date_from": "2026-01-01", "date_to": "2026-06-30", "bbox": "71.4,51.1,71.5,51.2"})
    assert r.status_code == 200 and calls["dash"] == (date(2026, 1, 1), date(2026, 6, 30), None, (71.4, 51.1, 71.5, 51.2))
    client.get("/api/v1/kpi/dashboard")
    assert calls["dash"][1] == date.today()
    assert client.get("/api/v1/kpi/dashboard", params={"bbox": "1,2"}).status_code == 422
    client.get("/api/v1/kpi/defects/geojson", params={"month": "2026-05", "category_id": 0})
    assert calls["points"]["month"] == "2026-05" and calls["points"]["category_id"] == 0
    assert client.get("/api/v1/kpi/defects/geojson", params={"month": "май"}).status_code == 422
