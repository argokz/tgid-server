"""Этап 11: фоновые файлы «задача → статус → скачать» (без Redis/Celery/БД — подмены)."""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
import worker  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import file_jobs  # noqa: E402


def _bearer(user: str, role: str = "viewer") -> dict[str, str]:
    return {"Authorization": "Bearer " + create_access_token(username=user, role=role)}


class FakeRedis:
    def __init__(self):
        self.data: dict[str, bytes] = {}
        self.ttl: dict[str, int] = {}

    def pipeline(self):
        return self

    def set(self, key, value, ex=None):
        self.data[key] = value.encode() if isinstance(value, str) else value
        self.ttl[key] = ex

    def get(self, key):
        return self.data.get(key)

    def execute(self):
        return []


@pytest.fixture()
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(file_jobs, "_client", fake)
    return fake


def test_validate_params_rejects_unknown_kind_and_bad_params():
    with pytest.raises(ValueError):
        file_jobs.validate_params("nope", {})
    with pytest.raises(ValueError):  # pydantic ValidationError — подкласс ValueError
        file_jobs.validate_params("passport", {"table": "users", "obj_id": 1})
    assert file_jobs.validate_params("passport", {"table": "nodes", "obj_id": "5"}) == {
        "table": "nodes", "obj_id": 5, "fragments": None}
    assert file_jobs.validate_params("passport", {"table": "uchastok_rs", "obj_id": 7, "fragments": [3, 2]})["fragments"] == [3, 2]
    with pytest.raises(ValueError):
        file_jobs.validate_params("passport", {"table": "uchastok_rs", "obj_id": 7, "fragments": [0]})
    assert set(file_jobs.KINDS) == set(file_jobs.BUILDERS)


def test_build_report_excel_unknown_type_is_400():
    with pytest.raises(file_jobs.FileJobError) as exc:
        asyncio.run(file_jobs.build("report_excel", {"doc_type": "no-such-sheet"}))
    assert exc.value.status_code == 400


def test_content_disposition_keeps_cyrillic_in_rfc5987():
    header = file_jobs.content_disposition("Отчёт ф5.xlsx")
    assert header.startswith('attachment; filename="')
    assert "filename*=UTF-8''%D0%9E" in header
    header.encode("latin-1")  # заголовок HTTP обязан быть latin-1


def test_store_and_load_roundtrip_with_ttl(fake_redis, monkeypatch):
    monkeypatch.setenv("FILE_JOBS_TTL", "120")
    meta = file_jobs.store_result("t1", file_jobs.FileResult(b"xlsx", "a.xlsx", headers={"X-Report-Rows": "3"}),
                                  owner="u1", kind="catalog_report")
    assert meta["size"] == 4 and meta["ttl"] == 120
    assert set(fake_redis.ttl.values()) == {120}
    loaded_meta, data = file_jobs.load_result("t1")
    assert data == b"xlsx" and loaded_meta["owner"] == "u1"
    assert file_jobs.load_result("missing") is None


def test_worker_task_stores_file_and_reports_errors(fake_redis, monkeypatch):
    async def fake_build(kind, params):
        if params.get("fail"):
            raise file_jobs.FileJobError(404, {"code": "x", "message": "нет данных"})
        return file_jobs.FileResult(b"abc", "f.xlsx")

    async def noop():
        return None

    import database.connect as connect
    monkeypatch.setattr(file_jobs, "build", fake_build)
    monkeypatch.setattr(connect, "init_db_pool", noop)
    monkeypatch.setattr(connect, "close_db_pool", noop)
    monkeypatch.setattr(worker.build_file_job, "update_state", lambda **kw: None)

    ok = worker.build_file_job.apply(kwargs={"kind": "passport", "params": {}, "user": "u1"}, task_id="job-ok").get()
    assert ok["status"] == "success" and ok["filename"] == "f.xlsx" and ok["size"] == 3
    assert file_jobs.load_result("job-ok")[1] == b"abc"

    err = worker.build_file_job.apply(kwargs={"kind": "passport", "params": {"fail": 1}}, task_id="job-err").get()
    assert err == {"status": "error", "kind": "passport", "status_code": 404, "message": "нет данных"}


def test_endpoints_queue_status_download_and_owner(fake_redis, monkeypatch):
    queued = {}

    def fake_apply_async(kwargs, queue=None):
        queued.update(kwargs=kwargs, queue=queue)
        return SimpleNamespace(id="job-1")

    monkeypatch.setattr(worker.build_file_job, "apply_async", fake_apply_async)
    monkeypatch.setenv("FILE_JOBS_QUEUE", "files")
    client = TestClient(main.app)

    r = client.post("/api/v1/file-jobs", json={"kind": "catalog_report", "params": {"report_id": "r1"}},
                    headers=_bearer("u1"))
    assert r.status_code == 422  # нет fragment_id
    r = client.post("/api/v1/file-jobs", json={"kind": "catalog_report",
                                               "params": {"report_id": "r1", "fragment_id": 5}},
                    headers=_bearer("u1"))
    assert r.status_code == 200 and r.json()["task_id"] == "job-1"
    assert queued["queue"] == "files" and queued["kwargs"]["user"] == "u1"
    assert queued["kwargs"]["params"] == {"report_id": "r1", "fragment_id": 5, "calculation_id": None}

    file_jobs.store_result("job-1", file_jobs.FileResult(b"PK..", "Отчёт.xlsx", headers={"X-Report-Rows": "7"}),
                           owner="u1", kind="catalog_report")

    class FakeAsyncResult:
        def __init__(self, task_id, app=None):
            self.status = "SUCCESS"
            self.result = {"status": "success", "kind": "catalog_report", "elapsed_s": 1.5}
            self.info = self.result

    import routers.file_jobs as fj_router
    monkeypatch.setattr(fj_router, "AsyncResult", FakeAsyncResult)

    st = client.get("/api/v1/file-jobs/job-1", headers=_bearer("u1")).json()
    assert st["ready"] and st["success"] and st["filename"] == "Отчёт.xlsx" and st["size"] == 4

    d = client.get("/api/v1/file-jobs/job-1/download", headers=_bearer("u1"))
    assert d.status_code == 200 and d.content == b"PK.."
    assert d.headers["x-report-rows"] == "7"
    assert "X-Report-Rows" in d.headers["access-control-expose-headers"]

    assert client.get("/api/v1/file-jobs/job-1/download", headers=_bearer("u2")).status_code == 403
    assert client.get("/api/v1/file-jobs/job-1/download", headers=_bearer("boss", "admin")).status_code == 200
    assert client.get("/api/v1/file-jobs/nope/download", headers=_bearer("u1")).status_code == 404


def test_status_reports_builder_error(monkeypatch, fake_redis):
    class ErrResult:
        def __init__(self, task_id, app=None):
            self.status = "SUCCESS"
            self.result = {"status": "error", "kind": "passport", "status_code": 404, "message": "Узел не найден"}
            self.info = self.result

    import routers.file_jobs as fj_router
    monkeypatch.setattr(fj_router, "AsyncResult", ErrResult)
    st = TestClient(main.app).get("/api/v1/file-jobs/j", headers=_bearer("u1")).json()
    assert st["ready"] and st["success"] is False and st["message"] == "Узел не найден" and st["status_code"] == 404
