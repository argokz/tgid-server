"""Этап 9: инструменты ПТС (участки МС/РС, привязка труб) и типизированная правка — без живой БД."""

from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import group_setters as gs  # noqa: E402
from database import pts_sites as pts  # noqa: E402
from database import sql_ident  # noqa: E402
from database import typed_edit as te  # noqa: E402
from tests.test_group_setters import FakeConn  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _fresh_catalog_cache():
    sql_ident.reset_catalog_cache()
    yield
    sql_ident.reset_catalog_cache()


# --- установщики участков ----------------------------------------------------------

def test_site_setters_follow_desktop_onsave_ms_rs():
    ms, rs, clear = gs.SETTERS["pts_site_ms"], gs.SETTERS["pts_site_rs"], gs.SETTERS["pts_site_clear"]
    assert [(c.column, c.source) for c in ms.writes[0].columns] == [("magistralsite", "value"), ("distsite", "null")]
    assert [(c.column, c.source) for c in rs.writes[0].columns] == [("distsite", "value"), ("magistralsite", "null")]
    assert {c.source for c in clear.writes[0].columns} == {"null"} and clear.kind == "computed"
    assert ms.ref.table == "uchastok_ms" and rs.ref.table == "uchastok_rs"
    assert pts.KINDS["ms"].setter == "pts_site_ms" and pts.KINDS["rs"].setter == "pts_site_rs"
    # фильтр групповых установщиков получает поле «участок МС/РС», очистка — нет
    assert "pts_site_ms" in gs.filter_fields("pipes") and "pts_site_clear" not in gs.filter_fields("pipes")


class SiteConn(FakeConn):
    def __init__(self):
        super().__init__()
        for table in ("heatpipesections", "uchastok_ms", "uchastok_rs"):
            self.catalog.setdefault(table, [])
            self.catalog[table] += ["magistralsite", "distsite", "opisanie_uchastka_ms", "naimenovanie_uchastka_rs"]


def test_assign_rs_writes_site_and_clears_ms_in_one_update():
    conn = SiteConn()
    result = _run(gs.apply(conn, gs.SETTERS["pts_site_rs"], 7, {"mode": "ids", "ids": [10, 11]}, actor="t"))
    update_sql, args = next((s, a) for s, a in conn.sql if s.startswith("UPDATE"))
    assert '"distsite" = $2::' in update_sql and '"magistralsite" = NULL::' in update_sql
    assert args[0] == [10, 11] and args[1] == 7
    assert result["change_group_id"]


def test_clear_setter_has_no_value_and_no_guard():
    conn = SiteConn()
    _run(gs.apply(conn, gs.SETTERS["pts_site_clear"], None, {"mode": "ids", "ids": [10]}, actor="t"))
    update_sql, args = next((s, a) for s, a in conn.sql if s.startswith("UPDATE"))
    assert '"magistralsite" = NULL::' in update_sql and '"distsite" = NULL::' in update_sql
    assert "IS NOT NULL" not in update_sql and len(args) == 1


# --- цепочка узлов ------------------------------------------------------------------

def test_shortest_path_prefers_short_route_and_reports_missing():
    adj: dict[int, list[tuple[int, int, float]]] = {}

    def edge(a, b, line, w):
        adj.setdefault(a, []).append((b, line, w))
        adj.setdefault(b, []).append((a, line, w))

    edge(1, 2, 100, 10.0)
    edge(2, 3, 101, 10.0)
    edge(1, 3, 102, 50.0)
    edge(3, 4, 103, 1.0)
    edge(8, 9, 104, 1.0)
    assert pts.shortest_path(adj, 1, 4) == [100, 101, 103]
    assert pts.shortest_path(adj, 4, 1) == [103, 101, 100]
    assert pts.shortest_path(adj, 1, 1) == []
    assert pts.shortest_path(adj, 1, 9) is None


def test_chain_needs_two_nodes():
    with pytest.raises(pts.PtsError) as exc:
        _run(pts.resolve_chain(FakeConn(), [5]))
    assert exc.value.status == 422


# --- типизированная правка ------------------------------------------------------------

def test_coerce_value_by_column_type():
    f_int = te.FieldSpec("nomer", "Номер", "int")
    f_float = te.FieldSpec("dlina", "Длина", "float")
    f_str = te.FieldSpec("name", "Название", "str", max_length=5)
    f_date = te.FieldSpec("d", "Дата", "date")
    assert te.coerce_value(f_int, "12") == 12 and te.coerce_value(f_int, 3.0) == 3
    assert te.coerce_value(f_int, "") is None and te.coerce_value(f_float, "1,5") == 1.5
    assert te.coerce_value(f_str, "") == "" and te.coerce_value(f_date, "2026-09-28") == date(2026, 9, 28)
    for field, bad in ((f_int, "abc"), (f_int, "1.5"), (f_int, True), (f_float, "nan"), (f_str, "слишком"),
                       (f_date, "28.09")):
        with pytest.raises(te.TypedEditError) as exc:
            te.coerce_value(field, bad)
        assert exc.value.status == 422


def test_prepare_values_rejects_fields_outside_allow_list():
    fields = [te.FieldSpec("name", "Название", "str")]
    with pytest.raises(te.TypedEditError) as exc:
        te.prepare_values(fields, {"id": 5})
    assert exc.value.detail["code"] == "field_not_editable"
    assert te.prepare_values(fields, {"NAME": "x"})[1] == {"name": "x"}


class RowConn:
    """Строка с версией для update_record."""

    def __init__(self, version="100", name="old"):
        self.version, self.name = version, name
        self.sql: list[tuple[str, tuple]] = []

    async def fetch(self, sql, *args):
        self.sql.append((sql, args))
        if "information_schema.tables" in sql:
            return [{"table_name": "valves"}]
        return []

    async def fetchrow(self, sql, *args):
        self.sql.append((sql, args))
        if "FOR UPDATE" in sql:
            return {"_row_id": 5, "_version": self.version, "name": self.name, "dn": 100}
        return None

    async def fetchval(self, sql, *args):
        self.sql.append((sql, args))
        if sql.startswith("UPDATE"):
            return "101"
        return True

    async def execute(self, sql, *args):
        self.sql.append((sql, args))
        return "OK"


def test_update_record_checks_version_and_audits_only_changed():
    fields = [te.FieldSpec("name", "Название", "str"), te.FieldSpec("dn", "Ду", "int")]
    audits = []

    async def audit_row(conn, **kw):
        audits.append(kw)

    conn = RowConn()
    with pytest.raises(te.TypedEditError) as exc:
        _run(te.update_record(conn, "valves", "id", 5, fields, {"name": "new"}, expected_version="99",
                              audit_row=audit_row))
    assert exc.value.status == 409 and not audits
    result = _run(te.update_record(conn, "valves", "id", 5, fields, {"name": "new", "dn": "100"},
                                   expected_version="100", audit_row=audit_row))
    assert result["changed"] == {"name": {"old": "old", "new": "new"}} and result["version"] == "101"
    update_sql, args = next((s, a) for s, a in conn.sql if s.startswith("UPDATE"))
    assert '"name" = $2' in update_sql and '"dn"' not in update_sql and args == (5, "new")
    assert audits == [{"operation": "UPDATE", "table": "valves", "record_id": 5,
                       "old": {"name": "old"}, "new": {"name": "new"}, "group": result["change_group_id"]}]


# --- маршруты ------------------------------------------------------------------------

def test_pts_write_routes_need_editor_and_mutations(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    assert client.post("/api/v1/pts/sites/rs", json={"fields": {}}, headers=_bearer("viewer")).status_code == 403
    assert client.post("/api/v1/pts/sites/rs/1/pipes", json={"line_ids": [1]},
                       headers=_bearer("viewer")).status_code == 403
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    for method, path, payload in (
        ("post", "/api/v1/pts/sites/rs", {"fields": {}}),
        ("put", "/api/v1/pts/sites/rs/1", {"fields": {}}),
        ("delete", "/api/v1/pts/sites/rs/1", None),
        ("post", "/api/v1/pts/sites/rs/1/pipes", {"line_ids": [1], "dry_run": False}),
    ):
        kwargs = {"headers": _bearer("editor")}
        if payload is not None:
            kwargs["json"] = payload
        assert getattr(client, method)(path, **kwargs).status_code == 503, path


def test_pts_bad_kind_is_404(monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _acquire():
        yield FakeConn()

    monkeypatch.setattr("routers.pts.acquire_conn", _acquire)
    r = TestClient(main.app).get("/api/v1/pts/sites", params={"kind": "xx"})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "bad_kind"


def test_highlight_extent_matches_view_warning_and_reports_fragments():
    class Conn:
        def __init__(self):
            self.calls = []

        async def fetchrow(self, sql, *args):
            self.calls.append((sql, args))
            return {"pipes": 3, "fragment_ids": [5, 7], "x1": 71.1, "y1": 51.0, "x2": 71.5, "y2": 51.2}

    conn = Conn()
    res = _run(pts.highlight_extent(conn, "rs", 227))
    assert res == {"kind": "rs", "id": 227, "pipes": 3, "fragment_ids": [5, 7], "bbox": [71.1, 51.0, 71.5, 51.2]}
    sql, args = conn.calls[0]
    assert "h.distsite = $1" in sql and args == (227,)
    # как SQL-view: трубы вне внутренних схем, фрагмент по узлу 1
    assert "n1.internalnodeid IS NULL" in sql and "l.removed = 0" in sql
    _run(pts.highlight_extent(conn, "nach", 2))
    nach_sql = conn.calls[1][0]
    assert "ue.nachalnik_uchastka = $1" in nach_sql and "uchastok_ms" in nach_sql and "uchastok_rs" in nach_sql
    with pytest.raises(pts.PtsError) as err:
        _run(pts.highlight_extent(conn, "ue", 1))
    assert err.value.status == 404


def test_highlight_route_validates_id(monkeypatch):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _acquire():
        yield FakeConn()

    monkeypatch.setattr("routers.pts.acquire_conn", _acquire)
    client = TestClient(main.app)
    assert client.get("/api/v1/pts/highlight", params={"kind": "ms", "id": 0}).status_code == 422
    r = client.get("/api/v1/pts/highlight", params={"kind": "xx", "id": 1})
    assert r.status_code == 404 and r.json()["detail"]["code"] == "bad_kind"


# --- правка оборудования ----------------------------------------------------------------

def test_equipment_edit_allow_list_and_guards(monkeypatch):
    from routers import equipment_edit as ee

    assert {"dampers", "regularmatures", "pumps", "pressregulators", "consumptregulators",
            "pressdropregulators", "bypass", "diaphragms", "elevators"} <= set(ee.EQUIPMENT_TABLES)
    for table, extra in ee.EXTRA_FIELDS.items():
        assert table in ee.EQUIPMENT_TABLES and all(sql_ident.is_valid_ident(c) for c in extra)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    assert client.get("/api/v1/equipment-edit/users/1").status_code == 404
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    assert client.put("/api/v1/equipment-edit/dampers/1", json={"fields": {}},
                      headers=_bearer("viewer")).status_code == 403
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    assert client.put("/api/v1/equipment-edit/dampers/1", json={"fields": {"turncount": 1}},
                      headers=_bearer("editor")).status_code == 503
