"""Этап 9: групповые установщики (aSet*) и редактируемые справочники — без живой БД."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import dictionaries as dicts  # noqa: E402
from database import group_setters as gs  # noqa: E402
from database import sql_ident  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture(autouse=True)
def _fresh_catalog_cache():
    sql_ident.reset_catalog_cache()
    yield
    sql_ident.reset_catalog_cache()


# --- описание -------------------------------------------------------------------

def test_setters_cover_desktop_menu_and_use_valid_identifiers():
    desktop = {"aSetOtv", "aSetTr", "aSetUr", "aSetKvPt", "aSetUf", "aSetUdobVent", "aSetUdobOt", "aSetOpenKoef",
               "aSetOpenRez", "aSetOpenRezT", "aSetOpenGvsT", "aSetDiams", "aSetLosesShare", "aSetKolChas",
               "aSetKvUt", "aSetKti", "aSetOrg", "aSetPipeRemontType", "aSetTubingType", "aSetSher", "aSetKodRs",
               "aSetPodpOn", "aSetLength"}
    mentioned = " ".join(s.desktop for s in gs.SETTERS.values())
    assert all(a in mentioned for a in desktop)
    for spec in gs.SETTERS.values():
        assert spec.target in gs.TARGETS
        assert spec.writes
        for write in spec.writes:
            assert write.table in gs.SETTER_TABLES
            assert sql_ident.is_valid_ident(write.key)
            for col in write.columns:
                assert sql_ident.is_valid_ident(col.column)
                if col.source.startswith("ref:"):
                    assert spec.ref and col.source[4:] in spec.ref.columns
                if col.source.startswith("expr:"):
                    assert col.source[5:] in gs.EXPRESSIONS
        if spec.kind == "ref":
            assert spec.ref is not None
        if spec.kind == "choice":
            assert spec.choices
    assert {"users", "audit_log"}.isdisjoint(gs.SETTER_TABLES)
    # как gid8 setSomething + setValue: реальные и обобщённые потребители
    tr = gs.SETTERS["calc_temperature"]
    assert [w.table for w in tr.writes] == ["realconsumers", "generalizedconsumers"]
    koef = gs.SETTERS["open_hour_coeff"]
    assert [c.column for w in koef.writes for c in w.columns] == ["hourirregcoeff", "hourirregcoeffopen"]
    assert [c.column for c in gs.SETTERS["var_coeff_pipes"].writes[0].columns] == ["varcoeffidflow", "varcoeffidret"]
    assert gs.SETTERS["organization"].writes[0].table == "linesobj"


def test_coerce_setter_value():
    sher = gs.SETTERS["roughness"]
    assert gs.coerce_setter_value(sher, "0,5") == 0.5
    for bad in (None, "", "abc", -1, 11, True):
        with pytest.raises(gs.GroupSetterError) as exc:
            gs.coerce_setter_value(sher, bad)
        assert exc.value.status == 422
    assert gs.coerce_setter_value(gs.SETTERS["work_hours"], "0") == 0  # signnumworks.id = 0 — допустимо
    with pytest.raises(gs.GroupSetterError):
        gs.coerce_setter_value(gs.SETTERS["spec_expend"], 1.5)
    assert str(gs.coerce_setter_value(gs.SETTERS["date_last_relay"], "27.09.2026")) == "2026-09-27"
    assert gs.coerce_setter_value(gs.SETTERS["line_labels"], 1) == 1
    with pytest.raises(gs.GroupSetterError):
        gs.coerce_setter_value(gs.SETTERS["line_labels"], 5)
    assert gs.coerce_setter_value(gs.SETTERS["length"], None) is None


def test_parse_selection_modes_and_limits():
    assert gs.parse_selection({"mode": "ids", "ids": [3, "4", 3]}).ids == [3, 4]
    assert gs.parse_selection({"mode": "fragment", "fragment_ids": [74]}).fragment_ids == [74]
    sel = gs.parse_selection({"mode": "filter", "bbox": [76.8, 43.2, 77.0, 43.3],
                              "where": [{"field": "roughness", "op": "eq", "value": 2}]})
    assert sel.bbox == (76.8, 43.2, 77.0, 43.3) and sel.where[0]["op"] == "eq"
    for bad in (None, {"mode": "all"}, {"mode": "ids", "ids": []}, {"mode": "ids", "ids": [0]},
                {"mode": "fragment"}, {"mode": "filter"}, {"mode": "filter", "bbox": [1, 2, 0, 3]},
                {"mode": "filter", "fragment_ids": [1], "where": [{"field": "x", "op": "like"}]}):
        with pytest.raises(gs.GroupSetterError):
            gs.parse_selection(bad)
    with pytest.raises(gs.GroupSetterError):
        gs.parse_selection({"mode": "ids", "ids": list(range(1, gs.MAX_OBJECTS + 2))})


# --- SQL на фейковом соединении ---------------------------------------------------

_TYPES = {"tuberoughness": "double precision", "varcoeffidflow": "integer", "varcoeffidret": "integer",
          "lineid": "integer", "diametercondit": "double precision"}


class FakeConn:
    def __init__(self):
        self.sql: list[tuple[str, tuple]] = []
        self.catalog = {t: ["id", "fileid", "removed", "shape", "nodeid", "lineid", "nodeid1", "nodeid2", "name",
                            "kodkv", "varcoeffid"] + list(_TYPES) for t in gs.SETTER_TABLES | dicts.DICTIONARY_TABLES}

    async def fetch(self, sql, *args):
        self.sql.append((sql, args))
        if "information_schema.tables" in sql:
            return [{"table_name": t} for t in self.catalog]
        if "information_schema.columns" in sql and "column_name FROM" in sql and "data_type" not in sql:
            return [{"column_name": c} for c in self.catalog.get(args[0], [])]
        if sql.startswith("SELECT b.id FROM"):
            return [{"id": 10}, {"id": 11}]
        if sql.startswith("UPDATE"):
            return [{"row_id": 1, "n0": 0.5}]
        return []

    async def fetchval(self, sql, *args):
        self.sql.append((sql, args))
        if "data_type FROM information_schema.columns" in sql:
            return _TYPES.get(args[1], "integer")
        if "Find_SRID" in sql:
            return 9998
        if "pg_trigger" in sql:
            return True
        return 0

    async def fetchrow(self, sql, *args):
        self.sql.append((sql, args))
        if "count(*) AS rows" in sql:
            return {"rows": 2, "changes": 1}
        if "AS label" in sql:
            return {"id": args[0], "label": "КВ_1", "fileid": 74}
        return None

    async def execute(self, sql, *args):
        self.sql.append((sql, args))
        return "OK"


def test_preview_uses_quoted_identifiers_and_filters_by_fragment_and_bbox():
    conn = FakeConn()
    report = _run(gs.preview(conn, gs.SETTERS["roughness"], 0.5,
                             {"mode": "filter", "fragment_ids": [74], "bbox": [76.8, 43.2, 77.0, 43.3],
                              "where": [{"field": "roughness", "op": "eq", "value": "2"}]}))
    assert report["objects"] == 2 and report["changes"] == 1
    objects_sql, objects_args = next((s, a) for s, a in conn.sql if s.startswith("SELECT b.id FROM"))
    assert '"linesobj" b' in objects_sql and "b.fileid = ANY($1::int[])" in objects_sql
    assert "ST_MakeEnvelope" in objects_sql and "9998" in objects_sql
    assert 'f."tuberoughness" = $6::float8' in objects_sql and objects_args[5] == 2.0
    count_sql, count_args = next((s, a) for s, a in conn.sql if "count(*) AS rows" in s)
    assert '"heatpipesections" t' in count_sql and 't."lineid" = ANY($1::int[])' in count_sql
    assert 't."tuberoughness" IS DISTINCT FROM $2::float8' in count_sql
    assert count_args == ([10, 11], 0.5)
    assert any("affects" in w or "расчёт" in w for w in report["warnings"])


def test_apply_sets_group_and_checks_stale_preview():
    conn = FakeConn()
    with pytest.raises(gs.GroupSetterError) as exc:
        _run(gs.apply(conn, gs.SETTERS["var_coeff_pipes"], 5, {"mode": "ids", "ids": [10, 11]},
                      actor="t", expected_changes=7))
    assert exc.value.status == 409
    assert not any(s.startswith("UPDATE") for s, _ in conn.sql)

    conn = FakeConn()
    audit: list[dict] = []

    async def audit_row(_conn, **kw):
        audit.append(kw)

    result = _run(gs.apply(conn, gs.SETTERS["var_coeff_pipes"], 5, {"mode": "ids", "ids": [10, 11, 99]},
                           actor="t", expected_changes=1, audit_row=audit_row))
    assert result["missing_ids"] == [99]
    assert any("tgid.current_group_id" in s for s, _ in conn.sql)
    update, args = next((s, a) for s, a in conn.sql if s.startswith("UPDATE"))
    assert update.startswith('UPDATE "heatpipesections" AS t SET "varcoeffidflow" = $2::int4, "varcoeffidret" = $3::int4')
    assert args == ([10, 11], 5, 5)
    # триггер log_changes есть → построчный аудит пишет он, API — только сводку
    assert [a["operation"] for a in audit] == ["GROUP_SET"]
    assert audit[0]["group"] == result["change_group_id"]


def test_filter_rejects_field_of_other_target():
    with pytest.raises(gs.GroupSetterError):
        _run(gs.preview(FakeConn(), gs.SETTERS["roughness"], 0.5,
                        {"mode": "filter", "fragment_ids": [1], "where": [{"field": "spec_expend", "op": "null"}]}))


# --- справочники ---------------------------------------------------------------------

def test_dictionaries_specs():
    assert {"spec-expends", "var-coefficients", "calc-temperatures", "gvs-load-graphs", "organizations",
            "exploitation-districts", "administrative-districts"} <= set(dicts.DICTIONARIES)
    kv = dicts.DICTIONARIES["var-coefficients"]
    assert kv.affects_calc and kv.fragment_scoped
    assert {f"{u.table}.{u.column}" for u in kv.usages} >= {
        "realconsumers.varcoeffid", "generalizedconsumers.varcoeffid",
        "heatpipesections.varcoeffidflow", "heatpipesections.varcoeffidret"}
    for spec in dicts.DICTIONARIES.values():
        assert sql_ident.is_valid_ident(spec.table) and sql_ident.is_valid_ident(spec.label_column)
        for u in spec.usages:
            assert sql_ident.is_valid_ident(u.column) and u.match in ("id", "name")
    assert "audit_log" not in dicts.DICTIONARY_TABLES and "users" not in dicts.DICTIONARY_TABLES


def test_dictionary_coerce():
    assert dicts.coerce("float", "1,25") == 1.25
    assert dicts.coerce("int", "3") == 3
    assert dicts.coerce("str", "  ") is None
    for kind, bad in (("int", "x"), ("float", "nan"), ("int", 1.5)):
        with pytest.raises(ValueError):
            dicts.coerce(kind, bad)
    with pytest.raises(ValueError):
        dicts.coerce("str", "abcd", 3)


class DictConn(FakeConn):
    def __init__(self, used: int):
        super().__init__()
        self.used = used

    async def fetch(self, sql, *args):
        if "character_maximum_length" in sql:
            self.sql.append((sql, args))
            return [{"column_name": c, "data_type": t, "character_maximum_length": None}
                    for c, t in (("id", "integer"), ("kodkv", "character varying"), ("otoplz", "double precision"),
                                 ("fileid", "integer"), ("id_old", "integer"))]
        return await super().fetch(sql, *args)

    async def fetchrow(self, sql, *args):
        self.sql.append((sql, args))
        if "WHERE id = $1" in sql:
            return {"id": args[0], "kodkv": "КВ_1", "otoplz": 0.69, "fileid": 74}
        return None

    async def fetchval(self, sql, *args):
        self.sql.append((sql, args))
        if "count(*)" in sql:
            return self.used
        return await super().fetchval(sql, *args)


def test_dictionary_delete_in_use_is_409_and_free_deletes():
    spec = dicts.DICTIONARIES["var-coefficients"]
    conn = DictConn(used=3)
    with pytest.raises(dicts.DictionaryError) as exc:
        _run(dicts.delete_row(conn, spec, 143))
    assert exc.value.status == 409 and exc.value.detail["usage"]["total"] == 12
    assert not any(s.startswith("DELETE") for s, _ in conn.sql)
    conn = DictConn(used=0)
    _run(dicts.delete_row(conn, spec, 143))
    assert any(s == 'DELETE FROM "varcoefficients" WHERE id = $1' for s, _ in conn.sql)


def test_dictionary_fields_hide_service_columns_and_require_fragment():
    spec = dicts.DICTIONARIES["var-coefficients"]
    fields = _run(dicts.fields(DictConn(0), spec))
    assert [f["column"] for f in fields] == ["kodkv", "otoplz", "fileid"]
    with pytest.raises(dicts.DictionaryError) as exc:
        _run(dicts.coerce_fields(DictConn(0), spec, {"kodkv": "X"}, creating=True))
    assert "fileid" in exc.value.detail["field_errors"]
    with pytest.raises(dicts.DictionaryError) as exc:
        _run(dicts.coerce_fields(DictConn(0), spec, {"id": 5, "kodkv": "X"}, creating=True))
    assert exc.value.detail["unknown_fields"] == ["id"]


# --- маршруты: роль и флаг ------------------------------------------------------------

def test_routes_require_editor_and_mutations(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    client = TestClient(main.app)
    body = {"selection": {"mode": "ids", "ids": [1]}, "value": 0.5}
    assert client.post("/api/v1/group-setters/roughness/apply", json=body).status_code == 401
    for role in ("viewer", "calculator"):
        h = _bearer(role)
        assert client.post("/api/v1/group-setters/roughness/apply", json=body, headers=h).status_code == 403
        assert client.post("/api/v1/group-setters/roughness/preview", json=body, headers=h).status_code == 403
        assert client.post("/api/v1/dictionaries/organizations", json={"fields": {}}, headers=h).status_code == 403
        assert client.delete("/api/v1/dictionaries/organizations/1", headers=h).status_code == 403
    h = _bearer("editor")
    assert client.post("/api/v1/group-setters/nope/apply", json=body, headers=h).status_code == 404
    assert client.post("/api/v1/dictionaries/users", json={"fields": {}}, headers=h).status_code == 404
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    for method, path, payload in (
        ("post", "/api/v1/group-setters/roughness/apply", body),
        ("post", "/api/v1/group-setters/undo", {"change_group_id": "00000000-0000-0000-0000-000000000000",
                                                 "dry_run": False}),
        ("post", "/api/v1/dictionaries/organizations", {"fields": {"name": "x"}}),
        ("put", "/api/v1/dictionaries/organizations/1", {"fields": {"name": "x"}}),
        ("delete", "/api/v1/dictionaries/organizations/1", None),
    ):
        kwargs = {"headers": h}
        if payload is not None:
            kwargs["json"] = payload
        assert getattr(client, method)(path, **kwargs).status_code == 503, path


def test_preview_route_maps_errors(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    fake = FakeConn()

    @asynccontextmanager
    async def _acquire():
        yield fake

    monkeypatch.setattr("routers.group_setters.acquire_conn", _acquire)
    client = TestClient(main.app)
    r = client.post("/api/v1/group-setters/roughness/preview",
                    json={"selection": {"mode": "filter"}, "value": 0.5}, headers=_bearer("editor"))
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_selection"
    r = client.post("/api/v1/group-setters/roughness/preview",
                    json={"selection": {"mode": "ids", "ids": [10]}, "value": 0.5}, headers=_bearer("editor"))
    assert r.status_code == 200 and r.json()["changes"] == 1
