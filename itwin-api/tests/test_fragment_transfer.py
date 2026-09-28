"""Формат .tgid (gid8/python/unite) и права маршрутов импорта/слияния фрагментов."""

import io
import os
import zipfile

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import fragment_transfer as ft  # noqa: E402

SAMPLE = (
    "=========================\r\nVersion: 2.0\r\nCodePage: utf-8\r\nServer: s\r\nDatabase: d\r\nUser: u\r\nDate: x\r\n"
    "-------------------------\r\nheatsystem\r\n\"id\",\"name\"\r\n1,\"ТС\"\r\n"
    "-------------------------\r\nfragments\r\n\"id\",\"name\"\r\n42,\"Фрагмент, \"\"М1\"\"\"\r\n"
    "-------------------------\r\nnodes\r\n\"id\",\"fileid\",\"nodename\",\"x\",\"y\"\r\n"
    "7,42,\"ТК-1¶стр.2\",100,-200\r\n8,42,\"\",,\r\n"
    "=========================\r\nLookups\r\n-------------------------\r\nnodetypes\r\n\"id\"\r\n1\r\n"
)


def test_parse_sections_until_lookups_and_restores_newlines():
    s = ft.parse_tgid(SAMPLE.encode("utf-8"))
    assert set(s) == {"heatsystem", "fragments", "nodes"}
    assert s["fragments"]["rows"][0] == ["42", 'Фрагмент, "М1"']
    assert s["nodes"]["columns"] == ["id", "fileid", "nodename", "x", "y"]
    assert s["nodes"]["rows"][0][2] == "ТК-1\nстр.2"
    assert s["nodes"]["rows"][1] == ["8", "42", "", "", ""]


def test_parse_zip_and_old_cp1251_file():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("tgid.txt", SAMPLE.encode("utf-8"))
    assert "nodes" in ft.parse_tgid(buf.getvalue())
    old = SAMPLE.replace("Version: 2.0\r\nCodePage: utf-8\r\n", "").encode("cp1251")
    assert ft.parse_tgid(old)["fragments"]["rows"][0][1].startswith("Фрагмент")
    with pytest.raises(ft.FragmentFileError):
        ft.parse_tgid(b"not a tgid")
    with pytest.raises(ft.FragmentFileError):
        ft.parse_tgid(SAMPLE.replace("fragments", "fragmentz").encode("utf-8"))


def test_value_conversion_like_desktop_ispr2():
    assert ft._value("", "integer") is None
    assert ft._value("", "text") == ""
    assert ft._value("TRUE", "integer") == "1" and ft._value("FALSE", "smallint") == "0"
    assert ft._value("20240131", "date") == "20240131"


def test_export_rules_follow_print_tab0():
    cols = {"id": "integer", "fileid": "integer", "internalnodeid": "integer", "shape": "USER-DEFINED",
            "removed": "integer", "coords": "text", "archivechangedate": "timestamp without time zone"}
    q, names = ft._export_query("linesobj", cols)
    assert names == ["id", "coords", "archivechangedate"]  # без fileid/internalnodeid/shape/removed
    assert "JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.fileid = $1" in q and "::date" in q
    q, _ = ft._export_query("nodes", {"id": "integer", "fileid": "integer", "removed": "integer"})
    assert "o.fileid = $1 AND COALESCE(o.removed, 0) = 0" in q
    q, _ = ft._export_query("dampers", {"id": "integer", "lineid": "integer"})
    assert "JOIN linesobj l ON l.id = o.lineid" in q
    # pipesections — до участков, чтобы pipesectionid heatpipesections перенумеровывался
    assert ft.IMPORT_ORDER.index("pipesections") < ft.IMPORT_ORDER.index("heatpipesections")
    assert ft.REF_COLUMNS["hsourceid"] == "heatsources"


def _bearer(role):
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role)}


def test_import_and_merge_need_flags_and_admin(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    files = {"file": ("f.tgid", SAMPLE.encode("utf-8"))}
    merge = {"fragment_ids": [1, 2], "dry_run": False}
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "false")
    assert client.post("/api/v1/fragments/import", files=files, data={"dry_run": "true"},
                       headers=_bearer("editor")).status_code == 503
    assert client.post("/api/v1/fragments/merge", json=merge, headers=_bearer("admin")).status_code == 503
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "true")
    assert client.post("/api/v1/fragments/import", files=files, data={"dry_run": "false"},
                       headers=_bearer("editor")).status_code == 403
    assert client.post("/api/v1/fragments/merge", json=merge, headers=_bearer("editor")).status_code == 403
    assert client.post("/api/v1/fragments/import", files=files, headers=_bearer("viewer")).status_code == 403
    assert client.post("/api/v1/fragments/merge", json={"fragment_ids": [1]},
                       headers=_bearer("admin")).status_code == 422
    assert client.get("/api/v1/fragments/1/export").status_code == 401
