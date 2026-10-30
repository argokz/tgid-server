"""Обход маршрутом (database/work_order_route.py) и прибытие бригады по треку (field_track.mark_arrivals)."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from database import field_track as ft
from database import work_order_route as wr
from database import work_orders as wo

KEY = "6f1c1c4e-2b7a-4c55-9a51-0d3e2f8a7b10"
NOW = datetime(2026, 10, 30, 9, 0, tzinfo=timezone.utc)


def _order(**kw):
    base = {"id": 11, "number": "Н-2026-00011", "status": "assigned", "status_label": "Назначен", "inspection_id": 7,
            "result": "", "defect_id": None}
    base.update(kw)
    return base


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class RouteConn:
    """Контур 7: участки 1 (узлы 10→20) и 2 (20→30); узел 30 без геометрии; отметка узла 20."""

    def __init__(self, *, inspection=True, on_route=True, seen=False):
        self.inspection = inspection
        self.on_route = on_route
        self.seen = seen
        self.executed: list[tuple[str, tuple]] = []

    def transaction(self):
        return _Tx()

    async def fetchrow(self, sql, *args):
        if "FROM osmotr WHERE id" in sql:
            return {"id": 7, "name": " Контур 7 "} if self.inspection else None
        return None

    async def fetchval(self, sql, *args):
        if "client_id = $1" in sql:
            return self.seen
        if "FROM osmotrdeployed" in sql:
            return self.on_route
        return None

    async def fetch(self, sql, *args):
        if "FROM osmotrdeployed r JOIN linesobj" in sql:
            return [{"id": 1, "nodeid1": 10, "nodeid2": 20, "geom": '{"type":"LineString","coordinates":[[1,2],[3,4]]}'},
                    {"id": 2, "nodeid1": 20, "nodeid2": 30, "geom": '{"type":"LineString","coordinates":[[3,4],[5,6]]}'}]
        if "FROM nodes n" in sql:
            assert args[0] == [10, 20, 30]  # порядок участков контура
            return [{"id": 10, "name": "ТК-1", "node_type": "Камера", "lon": 1, "lat": 2},
                    {"id": 20, "name": None, "node_type": None, "lon": 3, "lat": 4}]
        if "tgid_work_order_check" in sql:
            return [{"node_id": 20, "state": "defect", "note": "течь", "defect_id": 45, "by_user": "brig", "at": NOW}]
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return "UPDATE 1"


@pytest.fixture
def stub_order(monkeypatch):
    state = {"order": _order()}

    async def fake_get(conn, order_id):
        return dict(state["order"])

    monkeypatch.setattr(wo, "get_order", fake_get)
    return state


def test_route_lists_nodes_in_contour_order_with_checks(stub_order):
    out = asyncio.run(wr.route(RouteConn(), 11))
    assert out["inspection"] == {"id": 7, "name": "Контур 7"}
    assert [p["node_id"] for p in out["points"]] == [10, 20]  # узла без геометрии на маршруте нет
    a, b = out["points"]
    assert a["name"] == "ТК-1" and a["state"] is None and b["name"] == "Узел 20"
    assert b["state"] == "defect" and b["defect_id"] == 45 and b["at"] == NOW.isoformat()
    assert out["progress"] == {"total": 2, "ok": 0, "defect": 1}
    assert len(out["lines"]["features"]) == 2 and out["lines"]["features"][0]["geometry"]["type"] == "LineString"


def test_route_needs_inspection_order(stub_order):
    stub_order["order"] = _order(inspection_id=None)
    with pytest.raises(wo.WorkOrderError, match="не обход"):
        asyncio.run(wr.route(RouteConn(), 11))
    stub_order["order"] = _order()
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wr.route(RouteConn(inspection=False), 11))
    assert e.value.status == 404


def test_check_validates_route_status_and_repeat(stub_order):
    conn = RouteConn()
    asyncio.run(wr.add_check(conn, 11, wo.CheckIn(node_id=10, state="ok", note=" чисто ", client_id=KEY, lon=1, lat=2), "brig"))
    sql, args = next(x for x in conn.executed if "INSERT INTO tgid_work_order_check" in x[0])
    assert "ON CONFLICT (order_id, node_id)" in sql and args[:4] == (11, 10, "ok", "чисто") and str(args[5]) == KEY
    with pytest.raises(wo.WorkOrderError, match="нет на маршруте"):
        asyncio.run(wr.add_check(RouteConn(on_route=False), 11, wo.CheckIn(node_id=99, state="ok"), "brig"))
    stub_order["order"] = _order(status="closed", status_label="Закрыт")
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wr.add_check(RouteConn(), 11, wo.CheckIn(node_id=10, state="ok"), "brig"))
    assert e.value.status == 409
    repeat = RouteConn(seen=True)  # повтор из очереди после закрытия — без ошибки и без записи
    asyncio.run(wr.add_check(repeat, 11, wo.CheckIn(node_id=10, state="ok", client_id=KEY), "brig"))
    assert not any("INSERT" in s for s, _ in repeat.executed)
    with pytest.raises(ValueError):
        wo.CheckIn(node_id=10, state="maybe")


class CreateConn:
    def __init__(self):
        self.inserted: tuple = ()
        self.events: list[tuple] = []

    def transaction(self):
        return _Tx()

    async def fetchrow(self, sql, *args):
        if "FROM osmotr i" in sql:
            return {"id": 7, "name": "Контур 7", "lon": 76.9, "lat": 43.2}
        return None

    async def fetchval(self, sql, *args):
        if sql.lstrip().startswith("INSERT INTO tgid_work_order"):
            self.inserted = args
            return 11
        return True

    async def execute(self, sql, *args):
        if "tgid_work_order_event" in sql:
            self.events.append(args)


def test_create_by_inspection_takes_place_and_description(stub_order):
    conn = CreateConn()
    asyncio.run(wo.create(conn, wo.WorkOrderIn(title="Обход", kind="inspection", inspection_id=7), "disp"))
    args = conn.inserted
    assert args[8:10] == (76.9, 43.2) and args[14] == "Обход участков контура осмотра «Контур 7»" and args[16] == 7
    assert conn.events[0][4] == "Создан по контуру осмотра «Контур 7»"


def test_done_inspection_fills_contour_results(stub_order):
    stub_order["order"] = _order(status="in_progress", status_label="В работе", revision=3)

    class Conn(RouteConn):
        async def fetchval(self, sql, *args):
            if "UPDATE tgid_work_order" in sql:
                return 11
            return await super().fetchval(sql, *args)

    conn = Conn()
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="done", revision=3, result="Осмотрено 2 из 2"), "brig"))
    sync = next(a for s, a in conn.executed if "UPDATE osmotr" in s)
    assert sync == (7, "Осмотрено 2 из 2")
    event = next(a for s, a in conn.executed if "tgid_work_order_event" in s)
    assert "контур осмотра — результаты" in event[4]


def test_defect_on_route_goes_to_contour_and_marks_node(monkeypatch, stub_order):
    calls: dict = {}

    async def fake_record(conn, spec, fields, *, longitude, latitude):
        calls["fields"] = fields
        return {"id": 46}

    async def fake_create(conn, body, user, stamp=None):
        return {"id": 12, "defect_id": body.defect_id}

    async def fake_nearest(conn, lon, lat, meters=wo.FIELD_DEFECT_SNAP_M):
        return 1

    async def fake_check(conn, order_id, node_id, state, user, **kw):
        calls["check"] = (order_id, node_id, state, kw["defect_id"])

    for name, fn in (("create_record", fake_record), ("create", fake_create), ("nearest_line", fake_nearest),
                     ("upsert_check", fake_check)):
        monkeypatch.setattr(wo, name, fn)
    class Conn(RouteConn):
        async def fetchval(self, sql, *args):
            if sql.lstrip().startswith("SELECT l.id FROM osmotrdeployed"):
                return 2 if args == (7, 20) else None  # участок контура у узла 20
            return await super().fetchval(sql, *args)

    body = wo.FieldDefectIn(lon=76.9, lat=43.2, description="Течь", order_id=11, node_id=20)
    asyncio.run(wo.report_defect(Conn(), body, "brig"))
    assert calls["fields"]["inspection_id"] == 7 and calls["check"] == (11, 20, "defect", 46)
    assert calls["fields"]["line_id"] == 2  # не ближайший к телефону, а участок контура у узла


class ArrivalConn:
    def __init__(self, rows, contour=True):
        self.rows = rows
        self.contour = contour
        self.executed: list[tuple[str, tuple]] = []
        self.sql = ""

    async def fetchval(self, sql, *args):
        return self.contour

    async def fetch(self, sql, *args):
        self.sql, self.args = sql, args
        return self.rows

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return "UPDATE 1"


def test_arrival_marks_order_once_with_point_time():
    at = NOW - timedelta(minutes=3)
    conn = ArrivalConn([{"id": 11, "number": "Н-2026-00011", "at": at, "lon": 76.9, "lat": 43.2}])
    points = [ft.TrackPoint(t=at, lon=76.9, lat=43.2, accuracy=8), ft.TrackPoint(t=NOW, lon=76.9, lat=43.2, accuracy=500)]
    out = asyncio.run(ft.mark_arrivals(conn, 5, points, "brig"))
    assert out == ["Н-2026-00011"]
    assert len(conn.args[1]) == 1  # точка с точностью 500 м — не в счёт
    assert "osmotrdeployed" in conn.sql and conn.args[5] == ft.ARRIVAL_RADIUS_M
    update, event = conn.executed
    assert "arrived_at IS NULL" in update[0] and update[1] == (11, at)
    assert event[1][0] == 11 and event[1][1] == at and "Бригада на месте" in event[1][3]
    plain = ArrivalConn([], contour=False)
    asyncio.run(ft.mark_arrivals(plain, 5, points, "brig"))
    assert "osmotrdeployed" not in plain.sql  # в базе без журнала осмотров — только точка наряда
    assert asyncio.run(ft.mark_arrivals(plain, 5, [points[1]], "brig")) == []


def test_route_endpoints(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from auth import invalidate_user_status
    from routers import work_orders as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    invalidate_user_status()
    calls = {}

    @asynccontextmanager
    async def acquire():
        yield RouteConn()

    async def fake_route(conn, order_id):
        if order_id == 404:
            raise wo.WorkOrderError(422, "не обход")
        return {"order_id": order_id, "points": []}

    async def fake_check(conn, order_id, body, user):
        calls["check"] = (order_id, body.node_id, body.state)
        return {"order_id": order_id}

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(wr, "route", fake_route)
    monkeypatch.setattr(wr, "add_check", fake_check)
    client = TestClient(main.app)
    assert client.get("/api/v1/work-orders/11/route").json()["order_id"] == 11
    assert client.get("/api/v1/work-orders/404/route").status_code == 422
    r = client.post("/api/v1/work-orders/11/checks", json={"node_id": 10, "state": "ok", "client_id": KEY})
    assert r.status_code == 200 and calls["check"] == (11, 10, "ok")
    assert client.post("/api/v1/work-orders/11/checks", json={"node_id": 10, "state": "x"}).status_code == 422
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.post("/api/v1/work-orders/11/checks", json={"node_id": 10, "state": "ok"}).status_code == 503
