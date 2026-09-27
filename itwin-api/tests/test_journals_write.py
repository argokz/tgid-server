"""Этап 9: запись журналов (карточки, контуры, утверждение планов, документы) без живой БД."""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import sql_ident  # noqa: E402
from database.journal_specs import (  # noqa: E402
    JOURNAL_TABLES,
    JOURNALS,
    REPAIRS,
    SHURFS,
    FieldSpec,
    describe,
    spec_for_table,
)
from database.journal_write import (  # noqa: E402
    JournalWriteError,
    approve_records,
    check_rules,
    coerce_fields,
    coerce_value,
    create_record,
    normalize_ids,
    set_contour,
)
from database.ops_mutations import filter_ops_fields  # noqa: E402


def _bearer(role: str) -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def _run(coro):
    return asyncio.run(coro)


# --- описание журналов ---------------------------------------------------------

def test_specs_cover_five_journals_and_allow_list():
    assert set(JOURNALS) == {"defects", "shurfs", "inspections", "repairs", "pressure-tests"}
    for spec in JOURNALS.values():
        assert spec.table in JOURNAL_TABLES
        for field in spec.fields.values():
            assert sql_ident.is_valid_ident(field.column)
        # колонки утверждения пишет только эндпоинт утверждения
        if spec.approval:
            columns = {f.column for f in spec.fields.values()}
            assert spec.approval.flag_column not in columns
            assert spec.approval.date_column not in columns
    assert spec_for_table("REMONT2") is REPAIRS
    assert {"users", "audit_log"}.isdisjoint(JOURNAL_TABLES)


def test_describe_lists_contour_approval_documents():
    info = describe(REPAIRS)
    assert info["has_contour"] and info["has_documents"]
    assert info["approval"]["require_contour"] is True
    assert info["approval"]["sets_state"] == 2
    assert "plan" in info["create_modes"] and "current" in info["create_modes"]
    assert describe(SHURFS)["approval"]["signers"]["approver_position_id"]["ref"] == "dolzhnosti"
    assert describe(JOURNALS["defects"])["has_point_geometry"] is True


# --- значения и правила ----------------------------------------------------------

def test_coerce_value_types():
    assert coerce_value(FieldSpec("c", "int"), "12") == 12
    assert coerce_value(FieldSpec("c", "float"), "1,5") == 1.5
    assert coerce_value(FieldSpec("c", "money"), 10.456) == Decimal("10.46")
    assert coerce_value(FieldSpec("c", "date"), "2026-09-27T00:00:00") == date(2026, 9, 27)
    assert coerce_value(FieldSpec("c", "date"), "27.09.2026") == date(2026, 9, 27)
    assert coerce_value(FieldSpec("c", "timestamp"), "2026-09-27") == datetime(2026, 9, 27)
    assert coerce_value(FieldSpec("c", "time"), "9:30") == "9:30"
    assert coerce_value(FieldSpec("c", "str"), "  ") is None
    for kind, bad in (("int", "x"), ("int", 1.5), ("float", "abc"), ("date", "вчера"), ("time", "25:00")):
        with pytest.raises(ValueError):
            coerce_value(FieldSpec("c", kind), bad)
    with pytest.raises(ValueError):
        coerce_value(FieldSpec("c", "str", max_length=3), "abcd")


def test_coerce_fields_rejects_unknown_and_reports_all_errors():
    with pytest.raises(JournalWriteError) as exc:
        coerce_fields(REPAIRS, {"name": "x", "utverdit": 1, "shape": "POINT(0 0)"})
    assert exc.value.status == 422
    assert exc.value.detail["unknown_fields"] == ["shape", "utverdit"]
    with pytest.raises(JournalWriteError) as exc:
        coerce_fields(REPAIRS, {"planned_start": "bad", "planned_personnel": "many"})
    assert set(exc.value.detail["field_errors"]) == {"planned_start", "planned_personnel"}


def test_check_rules_required_order_and_pairs():
    errors = check_rules(REPAIRS, {"planned_start": date(2026, 5, 2), "planned_finish": date(2026, 5, 1)}, creating=True)
    assert errors["name"] == "обязательное поле"
    assert "planned_finish" in errors
    errors = check_rules(REPAIRS, {"name": "x", "commissioning_order_number": "17"})
    assert "commissioning_order_date" in errors
    assert check_rules(REPAIRS, {"name": "x", "commissioning_order_number": "17",
                                 "commissioning_order_date": date(2026, 1, 1)}) == {}


def test_normalize_ids():
    assert normalize_ids([3, "4", 3]) == [3, 4]
    for bad in (["x"], [0], [True], "1,2"):
        with pytest.raises(JournalWriteError):
            normalize_ids(bad)
    with pytest.raises(JournalWriteError):
        normalize_ids(range(1, 10), limit=5)


def test_legacy_crud_filter_maps_journal_keys_to_columns():
    fields = filter_ops_fields("defect", {"detected_at": "2026-01-01", "shape": "nope"})
    assert fields == {"data_osmotra": "2026-01-01"}
    assert filter_ops_fields("defect", {"DATA_OSMOTRA": "x"}) == {"data_osmotra": "x"}
    assert filter_ops_fields("remont2", {"name": "Контур"}) == {"otchet_po_defektu": "Контур"}


# --- SQL на фейковом соединении -----------------------------------------------------

def _catalog() -> dict[str, list[str]]:
    catalog: dict[str, list[str]] = {t: ["id"] for t in JOURNAL_TABLES}
    for spec in JOURNALS.values():
        cols = catalog[spec.table]
        cols += [f.column for f in spec.fields.values()]
        for mode in spec.create_modes.values():
            cols += list(mode)
        if spec.approval:
            cols += [spec.approval.flag_column, spec.approval.date_column]
            cols += [f.column for f in spec.approval.signer_columns.values()]
        if spec.point_geometry:
            cols.append("shape")
        if spec.deployed_table:
            catalog[spec.deployed_table] += ["directionid", "lineid"]
    catalog["linesobj"] += ["removed", "shape", "nodeid1", "nodeid2"]
    return catalog


class FakeConn:
    def __init__(self, *, record: dict | None = None, lines: dict[int, bool] | None = None, contour: int = 2):
        self.catalog = _catalog()
        self.sql: list[tuple[str, tuple]] = []
        self.record = record
        self.lines = lines or {}
        self.contour = contour

    async def fetch(self, sql, *args):
        self.sql.append((sql, args))
        if "information_schema.tables" in sql:
            return [{"table_name": t} for t in self.catalog]
        if "information_schema.columns" in sql:
            return [{"column_name": c} for c in self.catalog.get(args[0], [])]
        if "FROM linesobj WHERE id = ANY" in sql:
            return [{"id": i, "removed": r} for i, r in self.lines.items() if i in args[0]]
        return []

    async def fetchval(self, sql, *args):
        self.sql.append((sql, args))
        if "RETURNING id" in sql:
            return 101
        if "lower(trim(" in sql:
            return None
        if "count(*) FROM" in sql:
            return self.contour
        if "Find_SRID" in sql:
            return 9998
        return True

    async def fetchrow(self, sql, *args):
        self.sql.append((sql, args))
        if sql.lstrip().startswith("SELECT id,") and self.record is not None:
            return self.record
        if "ST_Extent" in sql:
            return {"xmin": None}
        return None

    async def execute(self, sql, *args):
        self.sql.append((sql, args))
        return "UPDATE 1"


@pytest.fixture(autouse=True)
def _fresh_catalog_cache():
    sql_ident.reset_catalog_cache()
    yield
    sql_ident.reset_catalog_cache()


def test_create_repair_plan_uses_gid6_defaults_and_quoted_columns():
    conn = FakeConn(record={"id": 101, "name": "Контур 1"})
    result = _run(create_record(conn, REPAIRS, {"name": "Контур 1", "planned_budget": "12,5"}, mode="plan"))
    assert result["id"] == 101
    insert = next((sql, args) for sql, args in conn.sql if sql.startswith("INSERT INTO"))
    assert insert[0].startswith('INSERT INTO "remont2" (')
    assert '"otchet_po_defektu"' in insert[0] and '"plan_flag"' in insert[0] and '"utverdit"' in insert[0]
    assert "Контур 1" in insert[1] and 12.5 in insert[1]
    with pytest.raises(JournalWriteError) as exc:
        _run(create_record(FakeConn(), REPAIRS, {"name": "x"}, mode="nonsense"))
    assert exc.value.status == 422


def test_set_contour_rejects_removed_and_missing_lines():
    conn = FakeConn(lines={1: False, 2: True})
    with pytest.raises(JournalWriteError) as exc:
        _run(set_contour(conn, REPAIRS, 5, [1, 2, 3], include_pairs=False))
    assert exc.value.detail["missing_lines"] == [3]
    assert exc.value.detail["removed_lines"] == [2]
    assert not any(sql.startswith("DELETE") for sql, _ in conn.sql)


def test_approve_rejects_incomplete_plan_and_current_repair():
    incomplete = {"id": 7, "name": "К", "__approval_flag": 0, "__approved_on": None, "__state": 1}
    conn = FakeConn(record=incomplete)
    result = _run(approve_records(conn, REPAIRS, [7], approved_on="2026-09-27"))
    assert result["approved"] == []
    assert "planned_start" in result["rejected"][7]["missing_fields"]
    assert not any(sql.startswith("UPDATE") for sql, _ in conn.sql)

    current = {**incomplete, "__approval_flag": 2}
    result = _run(approve_records(FakeConn(record=current), REPAIRS, [7]))
    assert "текущий" in result["rejected"][7]


def test_approve_complete_plan_sets_flag_date_and_state():
    record = {"id": 7, "__approval_flag": 0, "__approved_on": None, "__state": 1}
    for key in REPAIRS.approval.required_fields:
        record[key] = 1
    conn = FakeConn(record=record, contour=3)
    result = _run(approve_records(conn, REPAIRS, [7], approved_on="2026-09-27"))
    assert result["approved"] == [7]
    update = next((sql, args) for sql, args in conn.sql if sql.startswith("UPDATE"))
    assert '"utverdit" = 1' in update[0] and '"data_utverzhdeniya_plana" = $1' in update[0]
    assert '"stateid" = $2' in update[0]
    assert update[1] == (date(2026, 9, 27), 2, 7)
    empty_contour = FakeConn(record=record, contour=0)
    result = _run(approve_records(empty_contour, REPAIRS, [7]))
    assert "контур" in result["rejected"][7]


# --- маршруты: роль и флаг проверяются сервером ---------------------------------------

def test_journal_routes_require_editor_and_mutations_flag(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    client = TestClient(main.app)
    body = {"fields": {"name": "x"}}
    assert client.post("/api/v1/journals/repairs", json=body).status_code == 401
    assert client.post("/api/v1/journals/repairs", json=body, headers=_bearer("viewer")).status_code == 403
    assert client.post("/api/v1/journals/repairs", json=body, headers=_bearer("calculator")).status_code == 403
    assert client.put("/api/v1/journals/repairs/1/contour", json={"line_ids": [1]},
                      headers=_bearer("viewer")).status_code == 403
    assert client.post("/api/v1/journals/shurfs/1/approve", json={}, headers=_bearer("viewer")).status_code == 403
    assert client.delete("/api/v1/journals/defects/1/documents/2", headers=_bearer("viewer")).status_code == 403
    assert client.post("/api/v1/journals/users", json=body, headers=_bearer("editor")).status_code == 404
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    for method, path, payload in (
        ("post", "/api/v1/journals/repairs", body),
        ("patch", "/api/v1/journals/repairs/1", body),
        ("delete", "/api/v1/journals/repairs/1", None),
        ("put", "/api/v1/journals/pressure-tests/1/contour", {"line_ids": [1]}),
        ("post", "/api/v1/journals/repairs/1/approve", {}),
        ("post", "/api/v1/journals/repairs/1/unapprove", None),
        ("post", "/api/v1/journals/inspections/1/documents", {"fields": {"path": "a"}}),
    ):
        kwargs = {"headers": _bearer("editor")}
        if payload is not None:
            kwargs["json"] = payload
        assert getattr(client, method)(path, **kwargs).status_code == 503, path


def test_journal_route_maps_write_errors(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    fake = FakeConn()

    class _Tx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

    fake.transaction = lambda: _Tx()

    @asynccontextmanager
    async def _acquire():
        yield fake

    monkeypatch.setattr("routers.journals.acquire_conn", _acquire)
    client = TestClient(main.app)
    r = client.post("/api/v1/journals/repairs", json={"fields": {"utverdit": 1}}, headers=_bearer("editor"))
    assert r.status_code == 422
    assert r.json()["detail"]["unknown_fields"] == ["utverdit"]
    r = client.post("/api/v1/journals/repairs/approve", json={}, headers=_bearer("editor"))
    assert r.status_code == 422
    assert not any(sql.startswith(("INSERT", "UPDATE")) for sql, _ in fake.sql)
