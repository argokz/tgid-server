"""Контракты приложения: OpenAPI собирается, параметры sety проверяются,
JWT-шлюз при AUTH_REQUIRED_GET закрывает и POST-расчёты."""

import pytest
from fastapi.testclient import TestClient

import main
from worker import validate_sety_params


def test_openapi_builds_with_key_paths():
    paths = main.app.openapi()["paths"]
    for p in (
        "/api/analysis/valve-isolation",
        "/api/network-queries/volume",
        "/api/calculations/{calculation_id}/results/geojson",
        "/api/piezometer/excel",
        "/api/topology/merge-nodes",
        "/api/export/geojson",
    ):
        assert p in paths, p


def test_sety_params_accept_calculation_flags():
    assert validate_sety_params("-fileID 74 -tg -Tn -25") == ["-fileID", "74", "-tg", "-Tn", "-25"]


@pytest.mark.parametrize("params", [
    "-fileID 1 -database other",
    "-out_file=C:/x.txt",
    "--server 10.0.0.1",
    "-PASSWORD x",
])
def test_sety_params_reject_connection_and_output_flags(params):
    with pytest.raises(ValueError, match="задаётся сервером"):
        validate_sety_params(params)


def test_auth_gate_covers_post_when_enabled(monkeypatch):
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    client = TestClient(main.app)  # без lifespan: до БД запрос не доходит
    r = client.post("/api/calc/orifice-plate", json={"flow_g": 10, "delta_h": 20})
    assert r.status_code == 401
    # preflight CORS не требует токена
    r = client.options("/api/calc/orifice-plate", headers={
        "Origin": "http://localhost:3007", "Access-Control-Request-Method": "POST"})
    assert r.status_code != 401
