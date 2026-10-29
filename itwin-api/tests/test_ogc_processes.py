"""OGC API — Processes (routers/ogc_processes.py): список, описание, синхронный запуск, задание расчёта."""

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from routers import ogc_processes as op
from tgid_mcp import tools as mcp


@pytest.fixture
def client(monkeypatch):
    import main
    from auth import invalidate_user_status

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()
    return TestClient(main.app)


def test_processes_list_and_conformance(client):
    procs = client.get("/api/ogc/processes").json()["processes"]
    by_id = {p["id"]: p for p in procs}
    assert set(by_id) == set(op.PROCESSES)
    assert by_id["heat-hydraulic"]["jobControlOptions"] == ["async-execute"]
    assert by_id["network-select"]["jobControlOptions"] == ["sync-execute"]
    assert any(link["rel"].endswith("/execute") for link in by_id["network-select"]["links"])
    conf = client.get("/api/ogc/conformance").json()["conformsTo"]
    assert "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/core" in conf
    assert any(link["rel"].endswith("/processes") for link in client.get("/api/ogc").json()["links"])


def test_description_inlines_schemas(client):
    desc = client.get("/api/ogc/processes/network-select").json()
    assert "$ref" not in str(desc)
    assert desc["inputs"]["target"]["minOccurs"] == 0 and desc["inputs"]["target"]["schema"]["enum"] == ["lines", "nodes"]
    assert desc["inputs"]["conditions"]["schema"]["items"]["properties"]["op"]["enum"][0] == "lt"
    calc = client.get("/api/ogc/processes/heat-hydraulic").json()
    assert calc["inputs"]["fragment_ids"]["minOccurs"] == 1 and calc["inputs"]["tn"]["minOccurs"] == 0
    r = client.get("/api/ogc/processes/nope")
    assert r.status_code == 404 and r.json()["type"].endswith("/no-such-process")


def test_sync_execution_raw_document_and_errors(client, monkeypatch):
    calls = []

    async def fake_execute(name, arguments, user):
        calls.append((name, arguments))
        if arguments.get("boom") == "forbidden":
            raise mcp.ToolForbidden("Нет права «Запуск расчётов»")
        if arguments.get("boom") == "500":
            raise HTTPException(status_code=500, detail="SQL: secret table")
        return {"total": 3, "geometry": {"type": "Point"}, "items": [1, 2, 3]}

    monkeypatch.setattr(mcp, "execute", fake_execute)
    r = client.post("/api/ogc/processes/network-select/execution", json={"inputs": {"target": "lines"}})
    assert r.status_code == 200 and r.json() == {"total": 3, "items": [1, 2, 3]}  # геометрия убрана, как у MCP
    assert calls[0] == ("select_network", {"target": "lines"})
    r = client.post("/api/ogc/processes/network-select/execution", json={"inputs": {}, "response": "document"})
    assert r.json() == {"result": {"total": 3, "items": [1, 2, 3]}}
    r = client.post("/api/ogc/processes/network-select/execution", json={"inputs": {"boom": "forbidden"}})
    assert r.status_code == 403 and "Нет права" in r.json()["title"]
    r = client.post("/api/ogc/processes/network-select/execution", json={"inputs": {"boom": "500"}})
    assert r.status_code == 500 and "secret" not in r.text
    assert client.post("/api/ogc/processes/nope/execution", json={"inputs": {}}).status_code == 404


def test_invalid_inputs_use_real_validation(client):
    r = client.post("/api/ogc/processes/network-select/execution", json={"inputs": {"target": "pipes"}})
    body = r.json()
    assert r.status_code == 400 and body["type"].endswith("/invalid-parameter-value") and "target" in body["detail"]


def test_async_calculation_job(client, monkeypatch):
    async def fake_execute(name, arguments, user):
        assert name == "run_calculation"
        return {"task_id": "task-42", "status": "queued"}

    states = {"task-42": {"status": "PROGRESS", "meta": {"message": "Расчёт фрагмента 74"}}}

    async def fake_task(job_id):
        if job_id not in states:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        return states[job_id]

    async def fake_status_run(params, user):
        return {"status": "SUCCESS", "result": {"status": "success", "message": "Расчет окончен", "geometry": "x"}}

    monkeypatch.setattr(mcp, "execute", fake_execute)
    monkeypatch.setattr(op, "_task", fake_task)
    monkeypatch.setitem(mcp.TOOLS, "task_status", mcp.Tool("task_status", "t", "d", mcp.TaskParams, fake_status_run))

    r = client.post("/api/ogc/processes/heat-hydraulic/execution", json={"inputs": {"fragment_ids": [74]}})
    assert r.status_code == 201 and r.headers["location"].endswith("/api/ogc/jobs/task-42")
    assert r.json()["status"] == "accepted" and r.json()["jobID"] == "task-42"

    info = client.get("/api/ogc/jobs/task-42").json()
    assert info["status"] == "running" and info["message"] == "Расчёт фрагмента 74"
    assert client.get("/api/ogc/jobs/task-42/results").json()["type"].endswith("/result-not-ready")

    states["task-42"] = {"status": "SUCCESS", "result": {"status": "error", "message": "Нет источника"}}
    assert client.get("/api/ogc/jobs/task-42").json()["status"] == "failed"
    assert client.get("/api/ogc/jobs/task-42/results").status_code == 500

    states["task-42"] = {"status": "SUCCESS", "result": {"status": "success", "message": "Расчет окончен"}}
    info = client.get("/api/ogc/jobs/task-42").json()
    assert info["status"] == "successful" and any(link["rel"].endswith("/results") for link in info["links"])
    assert client.get("/api/ogc/jobs/task-42/results").json() == {
        "result": {"status": "success", "message": "Расчет окончен"}}
    assert client.get("/api/ogc/jobs/unknown").json()["type"].endswith("/no-such-job")


def test_calculation_is_logged_other_processes_are_read_only():
    import activity

    assert activity.classify("POST", "/api/ogc/processes/heat-hydraulic/execution") == "CALC_RUN"
    assert activity.classify("POST", "/api/ogc/processes/network-trace/execution") is None
