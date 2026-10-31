"""Расчётный движок водопровода (water_engine): нужен WNTR — запускается в среде движка, в среде API пропускается.

    <water-venv>/python -m pytest tests/test_water_engine.py
"""

import pytest

wntr = pytest.importorskip("wntr")

from water_engine import engine  # noqa: E402


def test_library_and_describe_net3():
    assert {"Net1", "Net3", "Net6"} <= {m["name"] for m in engine.library()}
    d = engine.describe(engine.load(library_name="Net3"))
    assert d["summary"]["Nodes"] == 97 and d["summary"]["Links"] == 119 and d["units_in_file"] == "GPM"
    types = {n["type"] for n in d["nodes"]}
    assert types == {"Junction", "Reservoir", "Tank"}
    pipe = next(link for link in d["links"] if link["type"] == "Pipe")
    assert pipe["diameter_mm"] > 0 and pipe["length_m"] > 0  # американские единицы переведены в СИ


def test_inp_roundtrip_and_simulate():
    wn = engine.load(library_name="Net3")
    text = engine.inp_text(wn)
    res = engine.simulate(engine.load(inp_text=text), duration_h=24, report_step_h=1)
    assert res["summary"]["steps"] == 25 and len(res["times_s"]) == 25
    assert set(res["node"]) == {"pressure_m", "head_m", "demand_ls"}
    assert set(res["link"]) == {"flow_ls", "velocity_ms", "headloss_m_km"}
    s = res["summary"]
    # учебная сеть Net3: у узла 10 у насосной давление отрицательное, на трубе 60 скорость выше 2 м/с
    assert "10" in s["negative_pressure_nodes"] and "60" in s["high_velocity_pipes"]
    assert s["max_pressure_m"] > s["min_pressure_m"]


def test_errors():
    with pytest.raises(engine.EngineError) as e:
        engine.load(library_name="NetX")
    assert e.value.status == 404
    with pytest.raises(engine.EngineError) as e:
        engine.load(inp_text="[JUNCTIONS]\n bad line here without enough fields\n[END]")
    assert e.value.status == 422
    with pytest.raises(engine.EngineError):
        engine.simulate(engine.load(library_name="Net1"), duration_h=1000)
