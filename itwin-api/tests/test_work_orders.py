"""Наряды и заявки (database/work_orders.py): переходы, проверки, место работ, синхронизация дефекта."""

import asyncio
from datetime import datetime, timezone

import pytest

from database import work_orders as wo


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class FakeConn:
    """Ровно то, что нужно функциям модуля: справочники, место работ, обновления с ревизией."""

    def __init__(self, *, revision_ok=True, defect=None, line=None, brigades=(5,), people=(7,)):
        self.revision_ok = revision_ok
        self.defect = defect
        self.line = line
        self.brigades = set(brigades)
        self.people = set(people)
        self.executed: list[tuple[str, tuple]] = []
        self.inserted: tuple = ()

    def transaction(self):
        return _Tx()

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetchval(self, sql, *args):
        if "FROM brigades" in sql:
            return args[0] in self.brigades
        if "FROM nachalniki_uchastkov" in sql:
            return args[0] in self.people
        if "FROM defect WHERE id" in sql:
            return self.defect is not None
        if sql.lstrip().startswith("INSERT INTO tgid_work_order"):
            self.inserted = args
            return 11
        if "UPDATE tgid_work_order" in sql:
            self.executed.append((sql, args))
            return 11 if self.revision_ok else None
        return None

    async def fetchrow(self, sql, *args):
        if "FROM defect d" in sql:
            return self.defect
        if "FROM linesobj" in sql:
            return self.line
        return None


def _order(**kw):
    base = {"id": 11, "number": "Н-2026-00011", "status": "new", "status_label": "Заявка", "brigade_id": None,
            "responsible_id": None, "defect_id": None, "result": "", "revision": 3, "planned_start": None,
            "planned_finish": None}
    base.update(kw)
    return base


@pytest.fixture
def stub_get(monkeypatch):
    state = {"order": _order()}

    async def fake_get(conn, order_id):
        return dict(state["order"])

    monkeypatch.setattr(wo, "get_order", fake_get)
    return state


def test_transition_graph_is_consistent():
    assert set(wo.TRANSITIONS) == set(wo.STATUSES)
    for src, targets in wo.TRANSITIONS.items():
        assert all(t in wo.STATUSES and t != src for t in targets)
    assert wo.TRANSITIONS["closed"] == () and "closed" in wo.TRANSITIONS["done"]
    assert "cancelled" not in wo.TRANSITIONS["done"]  # выполненный не отменить — только вернуть в работу


def test_transition_rules(stub_get):
    conn = FakeConn()
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="done", revision=3), "ivan"))
    assert e.value.status == 409 and "можно" in e.value.message
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="assigned", revision=3), "ivan"))
    assert e.value.status == 422 and "бригаду" in e.value.message
    stub_get["order"] = _order(status="in_progress", status_label="В работе", brigade_id=5)
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="done", revision=3), "ivan"))
    assert e.value.status == 422 and "что сделано" in e.value.message
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="done", revision=3, result="Заменено 6 м"), "ivan"))
    update_sql, args = next((s, a) for s, a in conn.executed if "UPDATE tgid_work_order" in s)
    assert "finished_at = $4" in update_sql and args[2] == "done" and args[5] == "Заменено 6 м"
    assert any("INSERT INTO tgid_work_order_event" in s and a[2:4] == ("in_progress", "done") for s, a in conn.executed)


def test_stale_revision_is_409(stub_get):
    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5)
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wo.transition(FakeConn(revision_ok=False), 11, wo.TransitionIn(to="in_progress", revision=1), "x"))
    assert e.value.status == 409 and "уже изменили" in e.value.message


def test_defect_is_synced_on_start_and_finish(stub_get):
    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5, defect_id=4853)
    conn = FakeConn(defect={"id": 4853})
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="in_progress", revision=3), "x"))
    defect_sql = [(s, a) for s, a in conn.executed if s.startswith("UPDATE defect")]
    assert defect_sql and defect_sql[0][1][0] == 4853 and defect_sql[0][1][2] == wo.DEFECT_STATE_REPAIR
    assert "COALESCE(data_nachala_remonta" in defect_sql[0][0]  # заполненную дату не переписываем
    event = next(a for s, a in conn.executed if "tgid_work_order_event" in s)
    assert "Ремонт" in event[4]

    stub_get["order"] = _order(status="in_progress", status_label="В работе", brigade_id=5, defect_id=4853,
                               result="Сварка")
    conn = FakeConn(defect={"id": 4853})
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="done", revision=3), "x"))
    defect_sql = [a for s, a in conn.executed if s.lstrip().startswith("UPDATE defect")]
    assert defect_sql[0][2] == wo.DEFECT_STATE_AFTER

    conn = FakeConn(defect=None)  # дефект удалили в десктопе — наряд всё равно переходит
    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5, defect_id=1)
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="in_progress", revision=3), "x"))
    assert not [s for s, _ in conn.executed if s.startswith("UPDATE defect")]


def test_create_takes_place_from_defect_and_line(stub_get):
    conn = FakeConn(defect={"id": 9, "name": None, "lineid": 77, "defectdescription": "Порыв подачи",
                            "lon": 71.49, "lat": 51.14},
                    line={"fileid": 3179, "lon": 71.5, "lat": 51.2})
    asyncio.run(wo.create(conn, wo.WorkOrderIn(title="Устранить порыв", defect_id=9, brigade_id=5), "ivan"))
    args = conn.inserted
    # title, kind, priority, status, defect, line, node, fileid, lon, lat, brigade, responsible, start, finish, descr
    assert args[3] == "assigned" and args[4:8] == (9, 77, None, 3179) and args[8:10] == (71.49, 51.14)
    assert args[14] == "Порыв подачи"
    assert any("Создан по дефекту №9" in a[4] for s, a in conn.executed if "tgid_work_order_event" in s)


def test_create_validates_references_and_dates():
    with pytest.raises(wo.WorkOrderError, match="Бригады 99"):
        asyncio.run(wo.create(FakeConn(), wo.WorkOrderIn(title="x", brigade_id=99), "u"))
    with pytest.raises(wo.WorkOrderError, match="Дефекта 9"):
        asyncio.run(wo.create(FakeConn(), wo.WorkOrderIn(title="x", defect_id=9), "u"))
    with pytest.raises(wo.WorkOrderError, match="раньше начала"):
        asyncio.run(wo.create(FakeConn(), wo.WorkOrderIn(
            title="x", planned_start=datetime(2026, 11, 2, tzinfo=timezone.utc),
            planned_finish=datetime(2026, 11, 1)), "u"))


def test_closed_order_is_read_only(stub_get):
    stub_get["order"] = _order(status="closed", status_label="Закрыт")
    with pytest.raises(wo.WorkOrderError) as e:
        asyncio.run(wo.update(FakeConn(), 11, wo.WorkOrderPatch(revision=3, title="y"), "u"))
    assert e.value.status == 409


def test_update_sets_only_given_fields_and_clears_brigade(stub_get):
    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5)
    conn = FakeConn()
    asyncio.run(wo.update(conn, 11, wo.WorkOrderPatch(revision=3, brigade_id=0, priority=1), "u"))
    sql, args = next((s, a) for s, a in conn.executed if "UPDATE tgid_work_order" in s)
    assert "priority = $3" in sql and "brigade_id = $4" in sql and args[2:4] == (1, None)
    event = next(a for s, a in conn.executed if "tgid_work_order_event" in s)
    assert event[4] == "Изменено: срочность, бригада"


def test_endpoints_and_mutation_flag(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from auth import invalidate_user_status
    from routers import work_orders as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield FakeConn()

    async def fake_create(conn, body, user):
        return {"id": 1, "title": body.title, "status": "new"}

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(wo, "create", fake_create)
    client = TestClient(main.app)
    r = client.post("/api/v1/work-orders", json={"title": "Проверка"})
    assert r.status_code == 200 and r.json()["title"] == "Проверка"
    assert client.post("/api/v1/work-orders", json={"title": ""}).status_code == 422
    assert client.post("/api/v1/work-orders", json={"title": "x", "kind": "magic"}).status_code == 422
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.post("/api/v1/work-orders", json={"title": "Проверка"}).status_code == 503


class FieldConn(FakeConn):
    """Плюс ключи действий с устройства (client_id) и фото."""

    def __init__(self, seen=(), **kw):
        super().__init__(**kw)
        self.seen = set(seen)

    async def fetchval(self, sql, *args):
        if "client_id = $1" in sql:
            return args[0] in self.seen
        return await super().fetchval(sql, *args)


JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 100
KEY = "6f1c1c4e-2b7a-4c55-9a51-0d3e2f8a7b10"


def test_repeat_with_same_client_id_changes_nothing(stub_get):
    from uuid import UUID

    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5)
    conn = FieldConn(seen={UUID(KEY)})
    out = asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="in_progress", revision=1, client_id=KEY), "x"))
    assert out["status"] == "assigned" and conn.executed == []  # ни 409 по старой ревизии, ни второго перехода
    asyncio.run(wo.add_comment(conn, 11, wo.CommentIn(note="на месте", client_id=KEY), "x"))
    asyncio.run(wo.add_photo(conn, 11, JPEG, "x", stamp=wo.FieldStamp(client_id=KEY)))
    assert conn.executed == []


def test_field_action_stores_key_and_coordinates(stub_get):
    stub_get["order"] = _order(status="assigned", status_label="Назначен", brigade_id=5)
    conn = FieldConn()
    asyncio.run(wo.transition(conn, 11, wo.TransitionIn(to="in_progress", revision=3, client_id=KEY,
                                                         lon=76.95, lat=43.25), "x"))
    event = next(a for s, a in conn.executed if "tgid_work_order_event" in s)
    assert str(event[5]) == KEY and event[6:8] == (76.95, 43.25)
    with pytest.raises(ValueError):
        wo.FieldStamp(lat=91)


def test_photo_checks_type_size_and_limit(stub_get):
    conn = FieldConn()
    assert wo.image_type(JPEG) == "image/jpeg" and wo.image_type(b"\x89PNG\r\n\x1a\n...") == "image/png"
    assert wo.image_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp" and wo.image_type(b"<svg") is None
    for data, status in ((b"", 422), (b"<html>" * 10, 415), (JPEG + b"\x00" * wo.MAX_PHOTO_BYTES, 413)):
        with pytest.raises(wo.WorkOrderError) as e:
            asyncio.run(wo.add_photo(conn, 11, data, "x"))
        assert e.value.status == status
    stub_get["order"] = _order(photos=[{"id": i} for i in range(wo.MAX_PHOTOS)])
    with pytest.raises(wo.WorkOrderError, match="уже"):
        asyncio.run(wo.add_photo(conn, 11, JPEG, "x"))
    stub_get["order"] = _order(photos=[])
    asyncio.run(wo.add_photo(conn, 11, JPEG, "x", caption=" Шурф ", stamp=wo.FieldStamp(lon=76.9, lat=43.2)))
    photo = next(a for s, a in conn.executed if "tgid_work_order_photo" in s)
    assert photo[2:5] == ("Шурф", "image/jpeg", len(JPEG)) and photo[6:8] == (76.9, 43.2)
    assert any("Фото: Шурф" in a[4] for s, a in conn.executed if "tgid_work_order_event" in s)


def test_photo_endpoints(monkeypatch):
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
        yield FakeConn()

    async def fake_add(conn, order_id, data, user, *, caption, taken_at, stamp):
        calls.update(data=data, caption=caption, stamp=stamp, taken_at=taken_at)
        return {"id": order_id, "photos": [{"id": 1}]}

    async def fake_get(conn, photo_id):
        return "image/jpeg", JPEG

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(wo, "add_photo", fake_add)
    monkeypatch.setattr(wo, "get_photo", fake_get)
    client = TestClient(main.app)
    r = client.post("/api/v1/work-orders/11/photos", files={"file": ("a.jpg", JPEG, "image/jpeg")},
                    data={"caption": "Шурф", "lon": "76.9", "lat": "43.2", "client_id": KEY,
                          "taken_at": "2026-10-30T09:15:00+05:00"})
    assert r.status_code == 200 and calls["data"] == JPEG and str(calls["stamp"].client_id) == KEY
    assert calls["taken_at"].tzinfo is not None
    bad = client.post("/api/v1/work-orders/11/photos", files={"file": ("a.jpg", JPEG)}, data={"lat": "95"})
    assert bad.status_code == 422
    r = client.get("/api/v1/work-orders/photos/1")
    assert r.content == JPEG and r.headers["content-type"] == "image/jpeg" and "private" in r.headers["cache-control"]
