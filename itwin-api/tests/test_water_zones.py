"""Зоны водоучёта (DMA) и баланс (database/water_zones.py): границы, подача и МНР, обнаружение утечки."""

import pytest

from database import water_zones as wz

# Резервуар R → насос P → узлы A–B–C; труба B–C с расходомером M делит сеть на две зоны водоучёта;
# труба X (A–D) закрыта — D отдельно.
NODES = [
    {"id": "R", "type": "Reservoir"},
    {"id": "S", "type": "Junction", "demand_ls": 0},
    {"id": "A", "type": "Junction", "demand_ls": 2},
    {"id": "B", "type": "Junction", "demand_ls": 3},
    {"id": "C", "type": "Junction", "demand_ls": 1},
    {"id": "D", "type": "Junction", "demand_ls": 0},
]
LINKS = [
    {"id": "1", "type": "Pipe", "start": "R", "end": "S", "status": "Open"},
    {"id": "P", "type": "Pump", "start": "S", "end": "A"},
    {"id": "2", "type": "Pipe", "start": "A", "end": "B", "status": "Open"},
    {"id": "M", "type": "Pipe", "start": "C", "end": "B", "status": "Open"},  # расход течёт B → C: отрицательный
    {"id": "X", "type": "Pipe", "start": "A", "end": "D", "status": "Closed"},
]


def test_boundary_reasons():
    assert wz.boundary_reason(LINKS[1], set()) == "pump"
    assert wz.boundary_reason(LINKS[4], set()) == "closed"
    assert wz.boundary_reason(LINKS[3], {"M"}) == "meter"
    assert wz.boundary_reason(LINKS[2], set()) is None
    assert wz.boundary_reason({"id": "V", "type": "Valve"}, set()) == "valve"


def test_split_zones_by_pump_closed_pipe_and_meter():
    without = wz.split_zones(NODES, LINKS, set())
    assert [z["junctions"] for z in without["zones"]] == [3, 1, 1]  # A-B-C, затем по имени: D, S(+R)
    split = wz.split_zones(NODES, LINKS, {"M"})
    z = {zz["name"]: zz for zz in split["zones"]}
    assert split["node_zone"]["A"] == split["node_zone"]["B"] == 1 and split["node_zone"]["C"] != 1
    assert z["Зона 1"]["kind"] == "dma" and z["Зона 1"]["demand_ls"] == 5
    source = next(zz for zz in split["zones"] if zz["sources"] == ["R"])
    assert source["kind"] == "source" and source["inlets"] == ["P"]
    assert next(zz for zz in split["zones"] if zz["nodes"] == 1 and not zz["sources"] and zz["junctions"] == 1
                and zz["demand_ls"] == 0)["kind"] == "transit"
    assert "M" not in split["link_zone"] and split["link_zone"]["2"] == 1
    assert sorted(z["Зона 1"]["inlets"]) == ["M", "P", "X"]


def _results(leak_c=0.0):
    times = [0, 3600, 7200]
    use = {"A": [2, 1, 2], "B": [3, 1.5, 3], "C": [1, 0.5, 1 + leak_c]}
    total = [sum(v[i] for v in use.values()) for i in range(3)]
    demand = {**use, "S": [0, 0, 0], "D": [0, 0, 0], "R": [-t for t in total]}
    flow = {"1": total, "P": total, "2": [use["B"][i] + use["C"][i] for i in range(3)],
            "M": [-use["C"][i] for i in range(3)], "X": [0, 0, 0]}
    return times, demand, flow


def test_zone_balance_supply_equals_use_and_mnf():
    split = wz.split_zones(NODES, LINKS, {"M"})
    types = {n["id"]: n["type"] for n in NODES}
    times, demand, flow = _results()
    zones = {z["index"]: z for z in wz.zone_balance(split, types, times, demand, flow)}
    dma1 = zones[1]
    assert dma1["supply_ls"] == [5.0, 2.5, 5.0]  # насос P внутрь (6) минус расходомер M наружу (1)
    assert dma1["imbalance_ls"] == 0 and dma1["mnf_ls"] == 2.5 and dma1["mnf_time_s"] == 3600
    assert dma1["mnf_share"] == pytest.approx(2.5 / (12.5 / 3), abs=1e-3)
    c_zone = zones[split["node_zone"]["C"]]
    assert c_zone["supply_ls"] == [1.0, 0.5, 1.0] and c_zone["imbalance_ls"] == 0
    source = zones[split["node_zone"]["R"]]
    assert source["supply_avg_ls"] == 0  # резервуар отдаёт ровно то, что уходит через насос


def test_detect_leak_in_zone_behind_meter():
    split = wz.split_zones(NODES, LINKS, {"M"})
    types = {n["id"]: n["type"] for n in NODES}
    base = wz.zone_balance(split, types, *_results())
    times, demand, flow = _results()
    # утечка в C — 0,4 л/с всё время: отбор C и расход через расходомер M растут
    for key in ("C",):
        demand[key] = [v + 0.4 for v in demand[key]]
    flow["M"] = [v - 0.4 for v in flow["M"]]
    flow["2"] = [v + 0.4 for v in flow["2"]]
    flow["P"] = [v + 0.4 for v in flow["P"]]
    flow["1"] = [v + 0.4 for v in flow["1"]]
    demand["R"] = [v - 0.4 for v in demand["R"]]
    leaks = [{"node": "C", "flow_ls": [0.4, 0.4, 0.4]}]
    scen = wz.zone_balance(split, types, times, demand, flow, leaks)
    found = {d["index"]: d for d in wz.detect(base, scen)}
    c = split["node_zone"]["C"]
    assert found[c]["detected"] and found[c]["d_mnf_ls"] == pytest.approx(0.4)
    assert not found[1]["detected"] and found[1]["d_mnf_ls"] == pytest.approx(0)  # зона 1 — транзит утечки
    assert next(z for z in scen if z["index"] == c)["leak_avg_ls"] == pytest.approx(0.4)
    meters = wz.meter_changes(split, _results()[2], flow, 3)
    assert meters == [{"link": "M", "from_zone": c, "to_zone": 1, "avg_ls": pytest.approx(-1.233, abs=1e-3),
                       "d_avg_ls": pytest.approx(-0.4)}]


def test_small_leak_below_threshold_not_detected():
    base = [{"index": 1, "kind": "dma", "mnf_ls": 40.0, "supply_avg_ls": 60.0}]
    scen = [{"index": 1, "kind": "dma", "mnf_ls": 41.0, "supply_avg_ls": 61.0}]
    d = wz.detect(base, scen)[0]
    assert d["threshold_ls"] == 2.0 and not d["detected"]  # +1 л/с при пороге 5 % от 40


def test_mnf_share_only_for_dma():
    split = wz.split_zones(NODES, LINKS, {"M"})
    types = {n["id"]: n["type"] for n in NODES}
    times, demand, flow = _results()
    flow["P"] = [v - 0.001 for v in flow["P"]]  # источник: подача около нуля, знак скачет
    zones = {z["index"]: z for z in wz.zone_balance(split, types, times, demand, flow)}
    assert zones[split["node_zone"]["R"]]["mnf_share"] is None
    assert zones[1]["mnf_share"] is not None
