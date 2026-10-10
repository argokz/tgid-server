"""Паспорта по начальнику участка: архив паспортов его участков МС/РС в формате десктопа
(database/passport_excel.py) и фоновая задача passport_chief — без БД, подменами."""

from __future__ import annotations

import asyncio
import io
import os
import zipfile

import openpyxl
import pytest

os.environ.setdefault("JWT_SECRET", "test-secret")

from database import file_jobs  # noqa: E402
from database import passport_excel as pe  # noqa: E402


class _Conn:
    def cursor(self):
        return self

    def close(self):
        pass


@pytest.fixture()
def fake_db(monkeypatch):
    monkeypatch.setattr(pe.psycopg2, "connect", lambda **kw: _Conn())


def _index(data: bytes):
    z = zipfile.ZipFile(io.BytesIO(data))
    ws = openpyxl.load_workbook(io.BytesIO(z.read("Перечень участков.xlsx"))).active
    return z.namelist(), [r for r in ws.iter_rows(min_row=5, values_only=True)]


def test_chief_zip_has_passport_per_site_and_index(fake_db, monkeypatch):
    sites = [("ms", 119, "ТМ-49 от П-1(52)", 23), ("rs", 633, "УТ 12(42)", 0), ("rs", 2992, 'п № т/тр "д.4"', 24),
             ("rs", 5, "", 3)]
    monkeypatch.setattr(pe, "chief_sites", lambda cur, nid, kinds, frags: ("Бейсенбаев К.Е.", sites))
    calls, progress = [], []

    def fake_build(table, obj_id, fragments=None):
        calls.append((table, obj_id, fragments))
        if obj_id == 5:
            raise pe.PassportError(404, "нет ни одного трубопровода")
        return f"xlsx {obj_id}".encode(), f"Passport_{obj_id}.xlsx"

    monkeypatch.setattr(pe, "build_passport_xlsx", fake_build)
    data, name = pe.build_chief_passports_zip(2, ("ms", "rs"), [3, 2], progress=progress.append)

    assert name == "Паспорта участков — Бейсенбаев К.Е.zip"  # точка в конце имени срезается
    # фрагменты карты передаются в паспорт каждого участка; участок без труб не строится
    assert calls == [("uchastok_ms", 119, [3, 2]), ("uchastok_rs", 2992, [3, 2]), ("uchastok_rs", 5, [3, 2])]
    assert progress == ["Участок 1 из 4: МС 119", "Участок 3 из 4: РС 2992", "Участок 4 из 4: РС 5"]
    files, rows = _index(data)
    assert files == ["МС 119 — ТМ-49 от П-1(52).xlsx", "РС 2992 — п № т_тр _д.4_.xlsx", "Перечень участков.xlsx"]
    assert [r[1:3] + (r[5],) for r in rows] == [
        ("МС", 119, "МС 119 — ТМ-49 от П-1(52).xlsx"),
        ("РС", 633, "пропущен: нет труб в выбранных фрагментах"),
        ("РС", 2992, "РС 2992 — п № т_тр _д.4_.xlsx"),
        ("РС", 5, "не сформирован: нет ни одного трубопровода"),
    ]


def test_chief_without_pipes_is_404(fake_db, monkeypatch):
    monkeypatch.setattr(pe, "chief_sites", lambda *a: ("Иванов", [("rs", 1, "x", 0)]))
    with pytest.raises(pe.PassportError) as exc:
        pe.build_chief_passports_zip(3, ("rs",), None)
    assert exc.value.status_code == 404 and "нет труб" in exc.value.detail
    monkeypatch.setattr(pe, "chief_sites", lambda *a: ("Иванов", []))
    with pytest.raises(pe.PassportError) as exc:
        pe.build_chief_passports_zip(3, ("ms",), None)
    assert "нет участков МС" in exc.value.detail


def test_fragments_arg_like_desktop():
    assert pe.fragments_arg(None) == ""
    assert pe.fragments_arg([55, 2, 3179, 2]) == "2,55,3179"


def test_safe_filename():
    assert pe.safe_filename('РС 1 — a/b:c*d?"e<f>g|h  .') == "РС 1 — a_b_c_d__e_f_g_h"
    assert pe.safe_filename("") == "file"
    assert len(pe.safe_filename("я" * 300)) == 120


def test_passport_chief_job_params_and_progress(monkeypatch):
    params = file_jobs.validate_params("passport_chief", {"nach_id": "2", "fragments": [5]})
    assert params == {"nach_id": 2, "kinds": ["ms", "rs"], "fragments": [5]}
    with pytest.raises(ValueError):
        file_jobs.validate_params("passport_chief", {"nach_id": 2, "kinds": ["ue"]})

    def fake_zip(nach_id, kinds, fragments, progress):
        progress("Участок 1 из 1: РС 7")
        return b"PK", "a.zip"

    monkeypatch.setattr(pe, "build_chief_passports_zip", fake_zip)
    seen: list[str] = []
    token = file_jobs.set_progress(seen.append)
    try:
        result = asyncio.run(file_jobs.build("passport_chief", params))
    finally:
        file_jobs.reset_progress(token)
    # ход работы из потока построителя доходит до статуса задачи
    assert seen == ["Участок 1 из 1: РС 7"]
    assert result.media_type == "application/zip" and result.filename == "a.zip"
    file_jobs.report_progress("без подписчика — без ошибки")


def test_worker_reports_builder_progress_from_thread_with_task_id(monkeypatch):
    """Построитель сообщает ход работы из своего потока: у Celery self.request свой в каждом потоке,
    поэтому id задачи берётся заранее — иначе update_state шёл без id и сообщения терялись."""
    import worker
    import database.connect as connect

    async def noop():
        return None

    async def fake_build(kind, params):
        await asyncio.to_thread(file_jobs.report_progress, "Участок 2 из 5: РС 9")
        return file_jobs.FileResult(b"PK", "a.zip", media_type="application/zip")

    states = []
    monkeypatch.setattr(file_jobs, "build", fake_build)
    monkeypatch.setattr(file_jobs, "store_result", lambda tid, res, **kw: {"filename": res.filename, "size": 2,
                                                                            "media_type": res.media_type, "ttl": 60})
    monkeypatch.setattr(connect, "init_db_pool", noop)
    monkeypatch.setattr(connect, "close_db_pool", noop)
    monkeypatch.setattr(worker.build_file_job, "update_state", lambda **kw: states.append(kw))

    out = worker.build_file_job.apply(kwargs={"kind": "passport_chief", "params": {}}, task_id="job-p").get()
    assert out["status"] == "success"
    assert {"task_id": "job-p", "state": "PROGRESS",
            "meta": {"message": "Участок 2 из 5: РС 9", "kind": "passport_chief"}} in states
    file_jobs.report_progress("после задачи подписчика нет")
