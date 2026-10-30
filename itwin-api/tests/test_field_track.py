"""Трек бригады (database/field_track.py): приём пачек, срок хранения, позиции, трек отрезками."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from database import field_track as ft

NOW = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class TrackConn:
    def __init__(self, *, brigades=(5,), rows=()):
        self.brigades = set(brigades)
        self.rows = list(rows)
        self.inserted: tuple = ()
        self.executed: list[tuple[str, tuple]] = []
        self.fetched: list[tuple[str, tuple]] = []

    def transaction(self):
        return _Tx()

    async def fetchval(self, sql, *args):
        if "FROM brigades" in sql:
            return args[0] in self.brigades
        if "INSERT INTO tgid_field_track" in sql:
            self.inserted = args
            return len(args[2])
        return None

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetch(self, sql, *args):
        self.fetched.append((sql, args))
        return self.rows


def _pt(minutes_ago, lon=76.9, lat=43.2, **kw):
    return ft.TrackPoint(t=NOW - timedelta(minutes=minutes_ago), lon=lon, lat=lat, **kw)


def test_batch_skips_future_and_expired_points_and_purges_old():
    conn = TrackConn()
    body = ft.TrackIn(brigade_id=5, points=[
        _pt(5, accuracy=8), _pt(-60), _pt(60 * 24 * (ft.TRACK_KEEP_DAYS + 1)), _pt(-5)])
    out = asyncio.run(ft.add_points(conn, body, "brig", now=NOW))
    assert out == {"accepted": 2, "skipped": 2}  # час вперёд и старше срока — нет; 5 минут вперёд — часы спешат
    user, brigade, times, lons, lats, acc = conn.inserted
    assert (user, brigade) == ("brig", 5) and len(times) == 2 and acc == [8, None]
    purge = conn.executed[-1]
    assert "DELETE FROM tgid_field_track" in purge[0] and purge[1][0] == NOW - timedelta(days=ft.TRACK_KEEP_DAYS)


def test_deleted_brigade_does_not_block_the_queue():
    conn = TrackConn(brigades=())
    asyncio.run(ft.add_points(conn, ft.TrackIn(brigade_id=9, points=[_pt(1)]), "brig", now=NOW))
    assert conn.inserted[1] is None
    with pytest.raises(ValueError):
        ft.TrackIn(points=[])
    with pytest.raises(ValueError):
        ft.TrackIn(points=[{"t": NOW.isoformat(), "lon": 200, "lat": 0}])


def test_segments_split_on_long_breaks():
    pts = [{"recorded_at": NOW + timedelta(minutes=m)} for m in (0, 1, 2, 30, 31, 90)]
    assert [len(s) for s in ft.split_segments(pts)] == [3, 2, 1]
    assert ft.split_segments([]) == []
    assert round(ft.distance_m((76.9, 43.2), (76.9, 43.201))) == 111


def test_positions_show_last_point_with_age():
    rows = [{"by_user": "brig", "brigade_id": 5, "brigade_name": " Бригада Север ", "recorded_at": NOW - timedelta(minutes=7),
             "lon": 76.9, "lat": 43.2, "accuracy": 12.0},
            {"by_user": "solo", "brigade_id": None, "brigade_name": None, "recorded_at": NOW,
             "lon": 76.8, "lat": 43.1, "accuracy": None}]
    conn = TrackConn(rows=rows)
    fc = asyncio.run(ft.positions(conn, hours=12, now=NOW))
    a, b = (f["properties"] for f in fc["features"])
    assert a["brigade_name"] == "Бригада Север" and a["age_min"] == 7 and a["kind"] == "brigade"
    assert b["brigade_name"] == "solo"  # без бригады — подписан входом
    assert conn.fetched[0][1][0] == NOW - timedelta(hours=12)


def test_track_lines_by_person_and_validation():
    rows = [{"by_user": "brig", "brigade_id": 5, "recorded_at": NOW + timedelta(minutes=m), "lon": 76.9, "lat": 43.2 + m / 10000}
            for m in (0, 1, 2, 40)]
    conn = TrackConn(rows=rows)
    fc = asyncio.run(ft.track(conn, brigade_id=5, now=NOW + timedelta(hours=1)))
    line, point = fc["features"]
    assert line["geometry"]["type"] == "LineString" and line["properties"]["points"] == 3
    assert line["properties"]["length_m"] == 22 and point["geometry"]["type"] == "Point"
    sql, args = conn.fetched[0]
    assert "t.brigade_id = $3" in sql and args[2] == 5 and args[1] - args[0] == timedelta(days=1)
    for kw, msg in (({}, "бригаду"), ({"brigade_id": 5, "since": NOW, "until": NOW - timedelta(hours=1)}, "позже"),
                    ({"by_user": "brig", "since": NOW - timedelta(days=8), "until": NOW}, "не больше")):
        with pytest.raises(ft.TrackError, match=msg):
            asyncio.run(ft.track(TrackConn(), now=NOW, **kw))


def test_endpoints(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from auth import invalidate_user_status
    from routers import field_track as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()
    conn = TrackConn()

    @asynccontextmanager
    async def acquire():
        yield conn

    monkeypatch.setattr(router, "acquire_conn", acquire)
    client = TestClient(main.app)
    t = datetime.now(timezone.utc).isoformat()
    r = client.post("/api/v1/field/track", json={"brigade_id": 5, "points": [{"t": t, "lon": 76.9, "lat": 43.2}]})
    assert r.status_code == 200 and r.json() == {"accepted": 1, "skipped": 0}
    assert client.get("/api/v1/field/positions").json()["type"] == "FeatureCollection"
    assert client.get("/api/v1/field/track").status_code == 422
    assert client.get("/api/v1/field/track", params={"brigade_id": 5}).status_code == 200
