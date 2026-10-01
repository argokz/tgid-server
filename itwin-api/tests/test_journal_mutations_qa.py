"""QA 30.09 (F43, F44): запись ТУ и универсальный CRUD отвечают 4xx на ошибки клиента.

Без живой БД: соединение — фейк с каталогом колонок и типами из information_schema;
audit_log подменяется заглушкой (тесты не должны писать в настоящую БД).
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date

import asyncpg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import sql_ident  # noqa: E402
from database.tu_mutations import TU_FIELD_ALIASES, TU_MUTABLE_FIELDS, filter_tu_fields  # noqa: E402

# Колонки tehnicheskie_usloviya (information_schema, almatygid_copy 02.10.2026), кроме
# повторяющихся блоков продлений *_1…*_7 — их веб не правит.
TU_TABLE_COLUMNS = {
    "id": "integer", "sostoyanie_dogovora": "integer", "dogovor": "text", "akt": "text",
    "data_annulirovaniya": "date", "nomer": "integer", "god": "integer", "nomer_tu": "character varying",
    "data_vydachi_tu": "date", "naimenovanie_organizatsii__zaprashivayuschey_tu": "character varying",
    "naimenovanie_obekta": "character varying", "adres_obekta": "character varying",
    "istochnik": "character varying", "rayon_ekspluatatsii": "character varying",
    "teplovye_potoki__gkal_ch": "double precision", "v_tom_chisle_otoplenie": "double precision",
    "v_tom_chisle_ventilyatsiya": "double precision", "v_tom_chisle_gvs_maks": "double precision",
    "prirost_nagruzki": "double precision", "v_tom_chisle_prirost_otoplenie": "double precision",
    "v_tom_chisle_prirost_ventilyatsiya": "double precision", "v_tom_chisle_prirost_gvs_maks": "double precision",
    "kamera": "character varying", "dopolnitelnye_tehnicheskie_meropriyatiya": "text",
    "srok_deystviya_tu": "character varying", "nomer_soglasovaniya_ts": "character varying",
    "data_soglasovaniya_ts": "date", "nomer_soglasovaniya_ov": "character varying", "data_soglasovaniya_ov": "date",
    "nomer_soglasovaniya_tp": "character varying", "data_soglasovaniya_tp": "date",
    "ispolnenie_dop_tehn_i_energ_meropriyatiy_v_ramkah_tu": "character varying",
    "stadiya_stroitelstva_obektov": "character varying", "nomer_vydachi_akta_dopuska": "character varying",
    "data_vydachi_akta_dopuska": "date", "teplovaya_nagruzka_po_aktu_dopuska__proektu__gkal_ch": "double precision",
    "v_tom_chisle_otoplenie_po_aktu": "double precision", "v_tom_chisle_ventilyatsiya_po_aktu": "double precision",
    "v_tom_chisle_gvs_maks_po_aktu": "double precision", "nomer_dogovora": "character varying",
    "data_dogovora": "date", "zdanie": "integer", "truba": "integer",
    "kod1": "character varying", "uzel1": "character varying", "protsent_nagruzki_1": "double precision",
    "kod2": "character varying", "uzel2": "character varying", "protsent_nagruzki_2": "double precision",
    "kod3": "character varying", "uzel3": "character varying", "protsent_nagruzki_3": "double precision",
    "tehnicheskie_usloviya": "text", "tehnicheskie_usloviya_2": "text", "tehnicheskie_usloviya_3": "text",
    "tehnicheskie_usloviya_4": "text", "tehnicheskie_usloviya_5": "text",
    "v_tom_chisle_gvs_sredn": "double precision", "v_tom_chisle_prirost_gvs_sredn": "double precision",
    "v_tom_chisle_gvs_sredn_po_aktu": "double precision",
}

CATALOG = {
    "tehnicheskie_usloviya": TU_TABLE_COLUMNS,
    "indikator_korrozii": {"id": "integer", "mesto_ustanovki": "character varying", "data_ustanovki": "date",
                           "kolichestvo_plastin_v_sborke": "integer", "shape": "USER-DEFINED"},
}


class FakeConn:
    def __init__(self):
        self.calls: list[tuple[str, tuple]] = []
        self.fail_with: Exception | None = None

    async def fetch(self, sql, *args):
        if "information_schema.tables" in sql:
            return [{"table_name": t} for t in CATALOG]
        if "information_schema.columns" in sql:
            return [{"column_name": c, "data_type": t, "character_maximum_length": None}
                    for c, t in CATALOG.get(args[0], {}).items()]
        return []

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        if self.fail_with:
            raise self.fail_with
        return 77

    async def execute(self, sql, *args):
        self.calls.append((sql, args))
        if self.fail_with:
            raise self.fail_with
        return "UPDATE 1"


@pytest.fixture
def fake_conn(monkeypatch):
    conn = FakeConn()

    @asynccontextmanager
    async def _acquire():
        yield conn

    async def _no_audit(**_kwargs):
        return "test"

    import database.db as db
    import routers.crud as crud
    import routers.registries as registries

    monkeypatch.setattr(db, "acquire_conn", _acquire)
    monkeypatch.setattr(crud, "write_audit_log", _no_audit)
    monkeypatch.setattr(registries, "write_audit_log", _no_audit)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    sql_ident.reset_catalog_cache()
    yield conn
    sql_ident.reset_catalog_cache()


def _editor() -> dict:
    return {"Authorization": f"Bearer {create_access_token(username='qa', role='editor')}"}


# ---------------------------------------------------------------- F43: allow-list ТУ


def test_tu_allow_list_matches_real_table_columns():
    missing = sorted(TU_MUTABLE_FIELDS - set(TU_TABLE_COLUMNS))
    assert missing == [], f"нет в tehnicheskie_usloviya: {missing}"
    for bogus in ("adres", "obekt", "organizatsiya", "sostoyanie"):
        assert bogus not in TU_MUTABLE_FIELDS


def test_tu_filter_maps_api_keys_and_rejects_unknown():
    assert filter_tu_fields({"organization_name": "ТОО", "issued_on": "2026-01-02", "nomer_tu": "7"}) == {
        "naimenovanie_organizatsii__zaprashivayuschey_tu": "ТОО",
        "data_vydachi_tu": "2026-01-02",
        "nomer_tu": "7",
    }
    assert set(TU_FIELD_ALIASES.values()) <= TU_MUTABLE_FIELDS
    with pytest.raises(HTTPException) as exc:
        filter_tu_fields({"adres": "x", "nomer_tu": "1"})
    assert exc.value.status_code == 422 and exc.value.detail["fields"] == ["adres"]
    with pytest.raises(HTTPException) as exc:
        filter_tu_fields({})
    assert exc.value.status_code == 400


def test_tu_update_coerces_dates_and_numbers(fake_conn):
    client = TestClient(main.app)
    r = client.put(
        "/api/v1/technical-conditions/5",
        json={"fields": {"issued_on": "2026-03-04", "total_heat_load": "1,5", "state_id": "2", "annulled_on": ""}},
        headers=_editor(),
    )
    assert r.status_code == 200, r.text
    sql, args = fake_conn.calls[-1]
    assert sql.startswith('UPDATE "tehnicheskie_usloviya"')
    assert args == (date(2026, 3, 4), 1.5, 2, None, 5)


def test_tu_bad_values_and_unknown_fields_are_4xx(fake_conn):
    client = TestClient(main.app)
    r = client.put("/api/v1/technical-conditions/5", json={"fields": {"issued_on": "04.03.2026x"}}, headers=_editor())
    assert r.status_code == 422
    r = client.put("/api/v1/technical-conditions/5", json={"fields": {"obekt": "x"}}, headers=_editor())
    assert r.status_code == 422
    r = client.post("/api/v1/technical-conditions", json={"fields": {}}, headers=_editor())
    assert r.status_code == 400
    assert fake_conn.calls == []


def test_tu_create_returns_id(fake_conn):
    client = TestClient(main.app)
    r = client.post("/api/v1/technical-conditions", json={"fields": {"number": "QA", "contract_date": "2026-01-31"}},
                    headers=_editor())
    assert r.status_code == 200 and r.json()["id"] == 77
    assert fake_conn.calls[-1][1] == ("QA", date(2026, 1, 31))


# ---------------------------------------------------------------- F44: универсальный CRUD


def test_crud_empty_create_is_400_without_sql(fake_conn):
    client = TestClient(main.app)
    r = client.post("/api/v1/create/indikator_korrozii", json={"fields": {}}, headers=_editor())
    assert r.status_code == 400
    assert fake_conn.calls == []


def test_crud_create_coerces_date_strings(fake_conn):
    client = TestClient(main.app)
    r = client.post(
        "/api/v1/create/indikator_korrozii",
        json={"fields": {"mesto_ustanovki": "QA", "data_ustanovki": "2026-05-06", "kolichestvo_plastin_v_sborke": ""}},
        headers=_editor(),
    )
    assert r.status_code == 200, r.text
    assert fake_conn.calls[-1][1] == ("QA", date(2026, 5, 6), None)


def test_crud_client_errors_are_4xx(fake_conn):
    client = TestClient(main.app)
    # ключ API вместо колонки (F42) — 400, не 500
    r = client.put("/api/v1/update/indikator_korrozii/1", json={"fields": {"installation_place": "x"}}, headers=_editor())
    assert r.status_code == 400
    r = client.put("/api/v1/update/indikator_korrozii/1", json={"fields": {"data_ustanovki": "завтра"}}, headers=_editor())
    assert r.status_code == 422
    fake_conn.fail_with = asyncpg.exceptions.NotNullViolationError("null value")
    r = client.post("/api/v1/create/indikator_korrozii", json={"fields": {"mesto_ustanovki": "x"}}, headers=_editor())
    assert r.status_code == 409
