"""Режимы расчёта sety (десктоп gid8 gidr_calc.cpp): сборка аргументов, белый список,
регистрация роутов списка/удаления расчётов."""

import shlex

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import main
from database.calculation_admin import _OUT_TABLE_RE, calculation_mode
from sety_modes import SetyRunRequest, args_to_params, build_sety_args
from worker import _sety_base_cmd, validate_sety_params


def _args(**kw):
    return build_sety_args(SetyRunRequest(**kw), "ivanov")


def test_plan_args_follow_desktop_getDoItDr():
    args = _args(fragment_ids=[74], name="Плановый тест", tn=-25, tg=True, teplopoter=False, dross_yes=True)
    s = " ".join(args)
    assert "-iter 20" in s and "-trtp 0" in s and "-Tn -25" in s
    assert "-tg" in args and "-no_teplopoter" in args and "-dross_yes" in args
    assert "-a" not in args and "-GWS" not in args and "-leto" not in args
    assert args[-2:] == ["-user_gid", "ivanov"]
    assert "-fileID" not in args and "-dross" not in args  # их добавляет воркер


def test_emergency_args_follow_desktop_getDoIt():
    args = _args(mode="emergency", fragment_ids=[74], tn=-20)
    s = " ".join(args)
    assert "-GWS 1 -GWS2 1" in s and "-Tn -20" in s
    assert "-a" in args  # эквивалентное сопротивление — умолчание десктопа (param/Detaliz=1)
    assert "-iter" not in args and "-tg" not in args and "-dross_yes" not in args
    detailed = _args(mode="emergency", fragment_ids=[74], consumer_resistance="detailed", leto=True, save_leto=True)
    assert "-a" not in detailed and "-leto" in detailed and "-save_po" in detailed


def test_worker_adds_dross_only_for_plan():
    assert "-dross" in _sety_base_cmd("out.txt", True)
    assert "-dross" not in _sety_base_cmd("out.txt", False)


@pytest.mark.parametrize("kw", [
    {"mode": "emergency", "fragment_ids": [74], "tg": True},
    {"mode": "emergency", "fragment_ids": [74], "dross_yes": True},
    {"mode": "emergency", "fragment_ids": [74], "save_leto": True},
    {"mode": "emergency", "fragment_ids": [74], "leto": True},  # летний — только детализированно
    {"mode": "plan", "fragment_ids": [74], "leto": True},
    {"mode": "plan", "fragment_ids": [74], "teplopoter": False},  # без -tg нет смысла
    {"fragment_ids": []},
    {"fragment_ids": [74, 74]},
    {"fragment_ids": [0]},
    {"fragment_ids": list(range(1, 60))},
    {"fragment_ids": [74], "tn": -100},
    {"fragment_ids": [74], "sopr": 9},
    {"fragment_ids": [74], "name": "-database other"},
    {"fragment_ids": [74], "name": "a\nb"},
    {"mode": "avar", "fragment_ids": [74]},
])
def test_invalid_requests_rejected(kw):
    with pytest.raises(ValidationError):
        SetyRunRequest(**kw)


def test_built_params_pass_whitelist_and_roundtrip():
    req = SetyRunRequest(mode="emergency", fragment_ids=[74, 75], name="Авария 'ул. Абая' \"тест\"")
    params = args_to_params(build_sety_args(req, "Администратор"))
    tokens = validate_sety_params(params)
    assert tokens[tokens.index("-name") + 1] == "Авария 'ул. Абая' \"тест\""
    assert shlex.split(params) == tokens
    assert req.is_list and not req.dross


@pytest.mark.parametrize("params", [
    "-fileID 1 -databas other",   # сокращение argparse → -database
    "-fileID 1 -out x",
    "-copy_calc -database2 other",
    "-fileID 1 --help",
    "-fileID 1 -unknown",
])
def test_whitelist_rejects_unknown_and_abbreviated_flags(params):
    with pytest.raises(ValueError):
        validate_sety_params(params)


def test_whitelist_accepts_current_web_plan_string():
    params = ('-name "Расчет планового режима 27.09.2026 10:00" -time "2026-09-27 10:00:00" -fileID 74 '
              '-tg -no_teplopoter -uf_calc -save_uf_new -trtp 0 -Tn -32 -veter -no_teplovyd -dross_yes '
              '-char_sety -mag_fragment -save_po -no_kv -user_gid 1 -Tn=-25.5')
    assert validate_sety_params(params)[0] == "-name"


def test_calculation_mode_from_params():
    assert calculation_mode({"g_is_avar": 1}) == "emergency"
    assert calculation_mode({"g_is_avar": 0}) == "plan"
    assert calculation_mode(None) is None and calculation_mode({}) is None
    assert _OUT_TABLE_RE.match("ut_teplo_out") and not _OUT_TABLE_RE.match("iznos")


def test_calculation_routes_registered():
    paths = main.app.openapi()["paths"]
    assert "post" in paths["/api/v1/calculations/run"]
    assert "get" in paths["/api/v1/calculations"]
    assert "delete" in paths["/api/v1/calculations/{calculation_id}"]
    assert "delete" in paths["/api/calculations/{calculation_id}"]


def test_delete_requires_mutations_flag(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("MUTATIONS_ENABLED", "false")
    client = TestClient(main.app)  # без lifespan: до БД запрос не доходит
    r = client.delete("/api/v1/calculations/999999")
    assert r.status_code == 503


def test_run_requires_calculator_role(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    client = TestClient(main.app)
    r = client.post("/api/v1/calculations/run", json={"fragment_ids": [74]})
    assert r.status_code in (401, 403)
