"""Переход с ZuluGIS (database/zulu_import.py, routers/zulu_import.py): поиск слоя, проверка загрузки, фоновая
конвертация с подменённым процессом конвертера и хранилищем, права и владелец загрузки. Без Redis, БД и сети.

Живой прогон на примере ZuluGIS — ZULU_EXAMPLE_LAYER=<путь к слою без расширения> (иначе пропускается)."""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import zipfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import file_jobs, zulu_import  # noqa: E402

REPORT = {"layer": {"Участки": 3, "Узел": 2}, "db_tables": {"Net_uch": 5, "Net_kamera": 2}, "has_sqlite": True}


def _tgid(name="Сеть", nodes=2, lines=3) -> bytes:
    sec = "-------------------------"
    text = ["=========================", "Version: 2.0", "CodePage: utf-8", sec, "fragments",
            '"id","name"', f'2,"{name}"', sec, "nodes", '"id","externalNodeName"',
            *[f'{i},"У{i}"' for i in range(nodes)], sec, "linesobj", '"id"', *[str(i) for i in range(lines)]]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("tgid.txt", "\r\n".join(text).encode("utf-8"))
    return buf.getvalue()


def _layer_zip(name="Net", ext_case=".b00") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for ext in (ext_case, ".b01", ".b02", ".zx", ".sqlite"):
            z.writestr(f"Слой/{name}{ext}", b"x")
    return buf.getvalue()


@pytest.fixture
def blobs(monkeypatch):
    store: dict[str, tuple[dict, bytes]] = {}

    def put(key, data, meta):
        store[key] = (meta, data)
        return 3600

    monkeypatch.setattr(zulu_import, "put_blob", put)
    monkeypatch.setattr(zulu_import, "load_blob", lambda key: store.get(key))
    monkeypatch.setattr(zulu_import, "layer_report", lambda base, workdir: dict(REPORT))
    return store


def test_find_layers_needs_all_index_files(tmp_path):
    for name in ("Net.b00", "Net.B01", "Net.b02", "Half.b00", "Half.b01"):
        (tmp_path / name).write_bytes(b"x")
    assert [os.path.basename(b) for b in zulu_import.find_layers(str(tmp_path))] == ["Net"]


def test_upload_stores_one_layer_with_owner(blobs):
    res = zulu_import.upload([("layer.zip", _layer_zip())], "anna")
    assert res["layer"] == "Net" and res["report"]["layer"] == {"Участки": 3, "Узел": 2}
    meta, data = blobs[zulu_import.UPLOAD_PREFIX + res["upload_id"]]
    assert meta["owner"] == "anna"
    assert sorted(zipfile.ZipFile(io.BytesIO(data)).namelist()) == ["Net.b00", "Net.b01", "Net.b02", "Net.sqlite", "Net.zx"]
    assert zulu_import.upload_meta(res["upload_id"])["layer"] == "Net"


def test_upload_errors(blobs, monkeypatch):
    with pytest.raises(zulu_import.ZuluImportError, match="Нет слоя Zulu"):
        zulu_import.upload([("readme.txt", b"x")], "anna")
    two = io.BytesIO()
    with zipfile.ZipFile(two, "w") as z:
        for name in ("A", "B"):
            for ext in (".b00", ".b01", ".b02"):
                z.writestr(name + ext, b"x")
    with pytest.raises(zulu_import.ZuluImportError, match="несколько слоёв"):
        zulu_import.upload([("two.zip", two.getvalue())], "anna")
    assert zulu_import.upload([("two.zip", two.getvalue())], "anna", layer="B")["layer"] == "B"
    monkeypatch.setattr(zulu_import, "layer_report", lambda base, workdir: {**REPORT, "has_sqlite": False})
    with pytest.raises(zulu_import.ZuluImportError, match="Paradox"):
        zulu_import.upload([("layer.zip", _layer_zip())], "anna")


def _fake_run(itwin: dict[str, bytes], returncode=0, out=b"", calls=None):
    def run(args, *, workdir, timeout):
        if calls is not None:
            calls.append((args, workdir, timeout))
        path_out = args[args.index("-path_out") + 1]
        assert os.path.isfile(args[args.index("-path") + 1] + ".b00")
        for fname, content in itwin.items():
            with open(os.path.join(path_out, fname), "wb") as f:
                f.write(content)
        return subprocess.CompletedProcess(args, returncode, out, b"")

    return run


def test_convert_one_fragment_with_summary(blobs, monkeypatch):
    up = zulu_import.upload([("layer.zip", _layer_zip())], "anna")
    calls = []
    monkeypatch.setattr(zulu_import, "_run", _fake_run({"Сеть_2.itwin": _tgid()}, calls=calls))
    res = asyncio.run(zulu_import.convert(up["upload_id"], "Магистраль", -24.0))
    assert res.filename == "Магистраль.itwin" and res.content[:2] == b"PK"
    args, workdir, _ = calls[0]
    assert args[args.index("-Tn") + 1] == "-24" and args[args.index("-name") + 1] == "Магистраль"
    assert workdir != os.path.dirname(args[args.index("-path_out") + 1])
    report = json.loads(res.headers["X-Zulu-Report"])
    assert report["objects"] == {"Участки": 3, "Узел": 2}
    assert report["fragments"] == [{"name": "Сеть", "rows": {"nodes": 2, "linesobj": 3}}]


def test_convert_several_fragments_zip_and_failures(blobs, monkeypatch):
    up = zulu_import.upload([("layer.zip", _layer_zip())], "anna")
    monkeypatch.setattr(zulu_import, "_run", _fake_run({"A_2.itwin": _tgid("A"), "B_3.itwin": _tgid("B")}))
    res = asyncio.run(zulu_import.convert(up["upload_id"], "Город", -24))
    assert res.filename == "Город.zip" and sorted(zipfile.ZipFile(io.BytesIO(res.content)).namelist()) == [
        "A_2.itwin", "B_3.itwin"]
    monkeypatch.setattr(zulu_import, "_run", _fake_run({}, returncode=0, out="Неизвестный файл\n".encode()))
    with pytest.raises(file_jobs.FileJobError, match="Неизвестный файл"):
        asyncio.run(zulu_import.convert(up["upload_id"], "Город", -24))

    def slow(args, *, workdir, timeout):
        raise subprocess.TimeoutExpired(args, timeout)

    monkeypatch.setattr(zulu_import, "_run", slow)
    with pytest.raises(file_jobs.FileJobError, match="ZULU_TIMEOUT_S"):
        asyncio.run(zulu_import.convert(up["upload_id"], "Город", -24))
    with pytest.raises(file_jobs.FileJobError, match="срок хранения"):
        asyncio.run(zulu_import.convert("0" * 32, "Город", -24))


def _auth(role="admin", name="anna"):
    return {"Authorization": f"Bearer {create_access_token(username=name, role=role)}"}


def test_routes_owner_and_dedicated_kind(blobs, monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    r = client.post("/api/v1/zulu/upload", files=[("files", ("layer.zip", _layer_zip(), "application/zip"))],
                    headers=_auth())
    assert r.status_code == 200, r.text
    upload_id = r.json()["upload_id"]
    sent = []
    import worker

    monkeypatch.setattr(worker.build_file_job, "apply_async",
                        lambda kwargs, queue=None: sent.append(kwargs) or SimpleNamespace(id="t1"))
    body = {"upload_id": upload_id, "name": "Магистраль", "tn": -24}
    assert client.post("/api/v1/zulu/convert", json=body, headers=_auth(name="petr")).status_code == 403
    r = client.post("/api/v1/zulu/convert", json=body, headers=_auth())
    assert r.status_code == 200 and r.json()["task_id"] == "t1"
    assert sent[0]["kind"] == "zulu_convert" and sent[0]["user"] == "anna"
    missing = {**body, "upload_id": "f" * 32}
    assert client.post("/api/v1/zulu/convert", json=missing, headers=_auth()).status_code == 404
    r = client.post("/api/v1/file-jobs", json={"kind": "zulu_convert", "params": body}, headers=_auth())
    assert r.status_code == 422 and "своим эндпоинтом" in r.json()["detail"]
    assert client.post("/api/v1/zulu/upload", files=[("files", ("a.zip", _layer_zip(), "application/zip"))],
                       headers=_auth("viewer")).status_code == 403


@pytest.mark.skipif(not os.getenv("ZULU_EXAMPLE_LAYER"), reason="нужен слой ZuluGIS: ZULU_EXAMPLE_LAYER")
def test_real_example_layer(tmp_path):
    """Живой прогон конвертера на слое ZuluGIS (например, Examples\\Thermo\\Magistral\\Teplo)."""
    base = os.environ["ZULU_EXAMPLE_LAYER"]
    report = zulu_import.layer_report(base, str(tmp_path))
    assert report["has_sqlite"] and sum(report["layer"].values()) > 0
