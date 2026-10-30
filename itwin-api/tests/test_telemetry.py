"""Телеметрия: датчики, разбор выгрузок ОДПУ, приём показаний, расхождение с моделью."""

import asyncio
import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from auth import create_access_token, invalidate_user_status
from database import telemetry as tm


def test_sensor_validation():
    s = tm.SensorIn(code=" P-1 ", name="Давление", kind="pressure", unit="kgf_cm2", node_id=5, line_id=7)
    assert s.code == "P-1" and s.line_id is None  # датчик давления — в узле
    f = tm.SensorIn(code="G", name="Расход", kind="flow", unit="m3_h", line_id=7, node_id=5)
    assert f.node_id is None
    bad = [
        dict(code="x", name="x", kind="pressure", unit="c", node_id=1),  # единица не того вида
        dict(code="x", name="x", kind="pressure", unit="psi", node_id=1),  # нет такой единицы
        dict(code="x", name="x", kind="flow", unit="t_h", node_id=1),  # расход — на участке
        dict(code="x", name="x", kind="temperature", unit="c", line_id=1),  # температура — в узле
    ]
    for body in bad:
        with pytest.raises(ValueError):
            tm.SensorIn(**body)


def test_units_to_base():
    assert tm.UNITS["kgf_cm2"].to_base == 10.0 and tm.UNITS["mpa"].to_base == pytest.approx(101.97)
    assert {u.kind for u in tm.UNITS.values()} == {"pressure", "temperature", "flow"}


def test_deviation_thresholds():
    assert tm.deviation("pressure", 104, 100) == {"diff": 4, "pct": 4.0, "status": "ok"}
    assert tm.deviation("pressure", 92, 100)["status"] == "warn"
    assert tm.deviation("flow", 120, 100)["status"] == "bad"
    assert tm.deviation("temperature", 128.0, 130.0) == {"diff": -2.0, "pct": None, "status": "ok"}
    assert tm.deviation("temperature", 124.0, 130.0)["status"] == "bad"
    assert tm.deviation("flow", 0.0, 0.0)["status"] == "ok"


def test_parse_file_long_wide_and_encodings():
    long_csv = "time,code,value\n2026-10-30T10:00:00Z,P1,10.5\n2026-10-30T10:10:00Z,P1,\nbad,P1,1\n".encode()
    readings, notes = tm.parse_file(long_csv, "a.csv")
    assert readings == [("P1", datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc), 10.5)]
    assert notes == ["строк без времени или значения: 2"]
    wide = "Дата/время;P1;T1\n30.10.2026 18:00;10,61;130,2\n30.10.2026 18:10;;131\n".encode("cp1251")
    readings, notes = tm.parse_file(wide, "odpu.csv")
    assert readings == [("P1", datetime(2026, 10, 30, 18, 0), 10.61), ("T1", datetime(2026, 10, 30, 18, 0), 130.2),
                        ("T1", datetime(2026, 10, 30, 18, 10), 131.0)]
    assert notes == []
    wb = Workbook()
    ws = wb.active
    ws.append(["Время", "P1"])
    ws.append([datetime(2026, 10, 30, 9, 0), 10.2])
    buf = io.BytesIO()
    wb.save(buf)
    readings, _ = tm.parse_file(buf.getvalue(), "odpu.xlsx")
    assert readings == [("P1", datetime(2026, 10, 30, 9, 0), 10.2)]
    with pytest.raises(tm.TelemetryError):
        tm.parse_file("time;P1\n".encode(), "empty.csv")


def test_bucket_minutes():
    start = datetime(2026, 10, 30, tzinfo=timezone.utc)
    assert tm.bucket_minutes(start, start + timedelta(hours=6)) == 1
    assert tm.bucket_minutes(start, start + timedelta(days=1)) == 5
    assert tm.bucket_minutes(start, start + timedelta(days=30)) == 180
    assert tm.bucket_minutes(start, start + timedelta(days=3650)) == 1440


class Conn:
    def __init__(self):
        self.inserted = None

    async def fetch(self, sql, codes):
        known = {"P1": 1, "T1": 2}
        return [{"id": known[c], "code": c} for c in codes if c in known]

    async def execute(self, sql, *args):
        self.inserted = list(zip(*args))
        return "INSERT 0 1"


def test_ingest_dedupes_skips_unknown_and_future():
    conn = Conn()
    t = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
    out = asyncio.run(tm.ingest(conn, [
        ("P1", t, 1.0), ("P1", t, 2.0), ("T1", t, 130.0), ("X9", t, 5.0),
        ("P1", datetime.now(timezone.utc) + timedelta(days=3), 3.0),
    ]))
    assert out == {"accepted": 2, "skipped": 3, "unknown_codes": ["X9"], "future": 1}
    assert sorted(conn.inserted) == [(1, t, 2.0), (2, t, 130.0)]  # последнее значение побеждает


def test_geojson_status():
    sensors = [
        {"id": 1, "name": "a", "kind": "pressure", "pipe": "supply", "unit_label": "кгс/см²", "lon": 76.9, "lat": 43.2,
         "last": {"value": 10.0}, "stale": False, "deviation": {"status": "warn", "pct": 7.0, "diff": 0.7}},
        {"id": 2, "name": "b", "kind": "flow", "pipe": "supply", "unit_label": "т/ч", "lon": 76.9, "lat": 43.2,
         "last": None, "stale": True, "deviation": None},
        {"id": 3, "name": "c", "kind": "flow", "pipe": "supply", "unit_label": "т/ч", "lon": None, "lat": None},
    ]
    fc = tm.geojson(sensors)
    assert [f["properties"]["status"] for f in fc["features"]] == ["warn", "stale"]


def test_v2_readings_requires_key_and_permission(monkeypatch):
    import main

    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-123")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    invalidate_user_status()
    client = TestClient(main.app)
    body = {"readings": [{"sensor": "P1", "ts": "2026-10-30T10:00:00Z", "value": 1}]}
    assert client.post("/api/v2/telemetry/readings", json=body).status_code == 401
    viewer = create_access_token(username="petr", role="viewer", subject="petr", extra={"scope": "api"})
    r = client.post("/api/v2/telemetry/readings", json=body, headers={"Authorization": f"Bearer {viewer}"})
    assert r.status_code == 403
    bad = {"readings": [{"sensor": "P1", "ts": "2026-10-30T10:00:00Z", "value": "nan"}]}
    editor = create_access_token(username="ivan", role="editor", subject="ivan", extra={"scope": "api"})
    assert client.post("/api/v2/telemetry/readings", json=bad,
                       headers={"Authorization": f"Bearer {editor}"}).status_code == 422
    invalidate_user_status()


def test_alert_level():
    assert tm.alert_level({"stale": True, "deviation": {"status": "ok"}}) == "silent"
    assert tm.alert_level({"stale": False, "deviation": {"status": "bad"}}) == "bad"
    assert tm.alert_level({"stale": False, "deviation": {"status": "warn"}}) == "normal"
    assert tm.alert_level({"stale": False, "deviation": None}) is None  # нет расчёта — не тревога


class AlertConn:
    """Датчики с прошлым состоянием: обновления и тревоги — в списки."""

    def __init__(self, prev):
        self.prev = prev
        self.updates = []
        self.alerts = []

    async def fetch(self, sql, *args):
        assert "alert_status" in sql
        return [{"id": k, "alert_status": v} for k, v in self.prev.items()]

    async def execute(self, sql, *args):
        self.updates.append(args)

    async def fetchval(self, sql, *args):
        self.alerts.append(args)
        return len(self.alerts)


def test_check_alerts_transitions(monkeypatch):
    sensors = [
        {"id": 1, "stale": False, "deviation": {"status": "bad", "diff": 6.6, "pct": 12.6}, "last": {"value": 5.9},
         "model": 5.23},
        {"id": 2, "stale": True, "deviation": None, "last": {"value": 1.0}, "model": None},
        {"id": 3, "stale": False, "deviation": {"status": "ok", "diff": 0.1, "pct": 1.0}, "last": {"value": 10},
         "model": 10},
        {"id": 4, "stale": False, "deviation": {"status": "bad", "diff": 9, "pct": 20}, "last": {"value": 1}, "model": 1},
        {"id": 5, "stale": False, "deviation": None, "last": {"value": 1}, "model": None},
    ]

    async def overview(conn, only_active=False):
        return sensors

    monkeypatch.setattr(tm, "overview", overview)
    # 1: норма → расхождение; 2: норма → молчит; 3: расхождение → норма; 4: первая оценка — без тревоги; 5: нет модели
    conn = AlertConn({1: "normal", 2: "normal", 3: "bad", 4: None, 5: "normal"})
    ids = asyncio.run(tm.check_alerts(conn))
    assert ids == [1, 2, 3]
    assert [(a[0], a[1], a[2]) for a in conn.alerts] == [(1, "bad", "normal"), (2, "silent", "normal"), (3, "normal", "bad")]
    assert [u[:2] for u in conn.updates] == [(1, "bad"), (2, "silent"), (3, "normal"), (4, "bad")]
