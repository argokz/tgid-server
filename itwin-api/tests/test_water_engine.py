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


def test_leak_scenario_is_pressure_dependent_emitter():
    base = engine.simulate(engine.load(library_name="Net3"), duration_h=24, report_step_h=1)
    res = engine.simulate(engine.load(library_name="Net3"), duration_h=24, report_step_h=1,
                          leaks=[{"node": "123", "area_cm2": 10}])
    leak = res["summary"]["leaks"][0]
    assert leak["node"] == "123" and len(leak["flow_ls"]) == 25
    # Q = Cd·A·√(2g·P): при ~47 м и 10 см² — около 22–23 л/с
    p0 = res["node"]["pressure_m"]["123"][0]
    assert leak["flow_ls"][0] == pytest.approx(0.75 * 10e-4 * (2 * 9.81 * p0) ** 0.5 * 1000, rel=0.01)
    # отбор узла EPANET = потребление + утечка
    d_base, d_leak = base["node"]["demand_ls"]["123"][0], res["node"]["demand_ls"]["123"][0]
    assert d_leak - d_base == pytest.approx(leak["flow_ls"][0], rel=0.02)
    assert leak["avg_ls"] > 15 and leak["volume_m3"] > 1000


def test_leak_errors():
    for bad in ({"node": "River", "area_cm2": 5}, {"node": "123", "area_cm2": 0}, {"node": "123", "area_cm2": 900}):
        with pytest.raises(engine.EngineError) as e:
            engine.simulate(engine.load(library_name="Net3"), duration_h=1, leaks=[bad])
        assert e.value.status == 422


def test_closed_links_with_pdd_cut_off_node_gets_nothing():
    wn = engine.load(library_name="Net3")
    links = wn.get_links_for_node("121")
    res = engine.simulate(wn, duration_h=24, report_step_h=1, closed_links=links, demand_model="PDD")
    supply = res["summary"]["supply"]
    short = {s["node"]: s for s in supply["short"]}
    assert short["121"]["delivered_ls"] == pytest.approx(0, abs=1e-3) and short["121"]["expected_ls"] > 2.5
    assert supply["delivered_ls"] < supply["expected_ls"]
    assert all(v == pytest.approx(0, abs=1e-3) for v in res["link"]["flow_ls"][links[0]])
    assert max(res["node"]["pressure_m"]["121"]) < 1  # не −947 000 м, как в DDA


def test_closing_pump_removes_its_controls():
    res = engine.simulate(engine.load(library_name="Net3"), duration_h=24, closed_links=["10"], demand_model="PDD")
    assert "control 1" in res["summary"]["removed_controls"]
    assert all(v == pytest.approx(0, abs=1e-3) for v in res["link"]["flow_ls"]["10"])
    with pytest.raises(engine.EngineError):
        engine.simulate(engine.load(library_name="Net3"), duration_h=1, closed_links=["нет-такого"])


def test_halt_reason_from_epanet_report(tmp_path):
    rpt = tmp_path / "run.rpt"
    rpt.write_text("  WARNING: Pump P closed\n  WARNING: System unbalanced at 17:00:00 hrs. EXECUTION HALTED.\n")
    assert "17:00:00" in engine.halt_reason(rpt)
    rpt.write_text("  Error 110: cannot solve network hydraulic equations.\n")
    assert engine.halt_reason(rpt) == "ошибка EPANET 110: cannot solve network hydraulic equations."
    assert engine.halt_reason(tmp_path / "нет.rpt") is None


def test_shutting_main_pump_station_reports_halt():
    pumps = ["PUMP-3830", "PUMP-3831", "PUMP-3832", "PUMP-3833", "PUMP-3834"]
    with pytest.raises(engine.EngineError) as e:
        engine.simulate(engine.load(library_name="Net6"), duration_h=24, closed_links=["LINK-0", "LINK-1", "LINK-2", *pumps],
                        demand_model="PDD")
    assert "не сбалансирована" in e.value.message
