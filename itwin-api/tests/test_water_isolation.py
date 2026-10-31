"""Отключение участка водопровода (database/water_isolation.py): задвижки «N−1», сегмент, отрезанные узлы."""

import pytest

from database import water_isolation as wi
from database.water import WaterError

#  R —p1— A —p2— B —p3— C —p4— D (тупик)
#         A —p5— E —p6— C          (кольцо A-B-C-E)
#         B ==насос PU== F —p7— G
NODES = [
    {"id": "R", "type": "Reservoir"},
    {"id": "A", "type": "Junction", "demand_ls": 1},
    {"id": "B", "type": "Junction", "demand_ls": 2},
    {"id": "C", "type": "Junction", "demand_ls": 3},
    {"id": "D", "type": "Junction", "demand_ls": 4},
    {"id": "E", "type": "Junction", "demand_ls": 1},
    {"id": "F", "type": "Junction", "demand_ls": 0},
    {"id": "G", "type": "Junction", "demand_ls": 2},
]


def _pipe(i, a, b, d, status="Open"):
    return {"id": i, "type": "Pipe", "start": a, "end": b, "diameter_mm": d, "length_m": 100, "status": status}


LINKS = [
    _pipe("p1", "R", "A", 300), _pipe("p2", "A", "B", 200), _pipe("p3", "B", "C", 200), _pipe("p4", "C", "D", 100),
    _pipe("p5", "A", "E", 150), _pipe("p6", "E", "C", 150), _pipe("p7", "F", "G", 100),
    {"id": "PU", "type": "Pump", "start": "B", "end": "F"},
]


def test_strategic_valves_n_minus_one():
    v = set(wi.strategic_valves(NODES, LINKS))
    assert ("p1", "R") in v                                   # у источника — на всех трубах
    assert {("p2", "A"), ("p5", "A")} <= v and ("p1", "A") not in v  # магистраль p1 (300 мм) без задвижки
    assert ("p3", "B") in v and ("p2", "B") not in v          # равные диаметры — без задвижки меньшее имя
    assert {("p4", "C"), ("p6", "C")} <= v and ("p3", "C") not in v
    assert not any(node in ("D", "F", "G") for _, node in v)  # тупики
    assert len(v) == 7


def test_segment_closes_boundary_valves_and_cuts_off_dead_end():
    valves = {pair: i for i, pair in enumerate(wi.strategic_valves(NODES, LINKS), start=1)}
    r = wi.analyse("p3", NODES, LINKS, valves)
    assert r["segment"]["links"] == ["p3"] and r["segment"]["nodes"] == ["C"]
    assert {(v["link"], v["node"]) for v in r["close_valves"]} == {("p3", "B"), ("p4", "C"), ("p6", "C")}
    assert r["no_water"] == {"segment_nodes": ["C"], "cut_off_nodes": ["D"], "demand_ls": 7}
    assert r["closed_links"] == ["p3", "p4", "p6"]


def test_segment_stops_at_pump_and_without_valves_spreads():
    r = wi.analyse("p7", NODES, LINKS, {("p1", "R"): 1})
    assert r["close_devices"] == ["PU"] and r["segment"]["nodes"] == ["F", "G"] and r["close_valves"] == []
    assert r["no_water"]["demand_ls"] == 2
    # одна задвижка — на трубе p1 у резервуара: сегмент трубы p2 — вся сеть от этой задвижки до насоса
    whole = wi.analyse("p2", NODES, LINKS, {("p1", "R"): 1})
    assert set(whole["segment"]["links"]) == {"p1", "p2", "p3", "p4", "p5", "p6"} and whole["close_devices"] == ["PU"]
    assert [(v["link"], v["node"]) for v in whole["close_valves"]] == [("p1", "R")]
    # насос закрыт — F и G за ним тоже без воды
    assert whole["no_water"]["cut_off_nodes"] == ["F", "G"] and whole["no_water"]["demand_ls"] == 13


def test_cut_off_ignores_closed_pipes():
    links = [*LINKS[:5], _pipe("p6", "E", "C", 150, "Closed"), *LINKS[6:]]
    assert wi.cut_off(NODES, links, {"p5"}) == {"E"}


def test_errors():
    with pytest.raises(WaterError) as e:
        wi.analyse("PU", NODES, LINKS, {})
    assert e.value.status == 422
    with pytest.raises(WaterError) as e:
        wi.analyse("нет", NODES, LINKS, {})
    assert e.value.status == 404
    closed = [*LINKS[:6], _pipe("p7", "F", "G", 100, "Closed"), LINKS[7]]
    with pytest.raises(WaterError):
        wi.analyse("p7", NODES, closed, {})


def test_worse_than_base_ignores_chronic_low_pressure():
    short = [
        {"node": "A", "expected_ls": 1.0, "delivered_ls": 0.56},   # и без отключения 0,56 — хроническая недоподача
        {"node": "B", "expected_ls": 1.0, "delivered_ls": 0.40},   # было 0,56 — упало заметно
        {"node": "C", "expected_ls": 2.0, "delivered_ls": 1.50},   # без отключения подача полная
        {"node": "D", "expected_ls": 1.0, "delivered_ls": 0.0},    # на отключаемом участке
    ]
    out = wi.worse_than_base(short, {"A": 0.56, "B": 0.56}, {"D"})
    assert [x["node"] for x in out] == ["B", "C"]
    assert out[0]["base_delivered_ls"] == 0.56 and out[1]["base_delivered_ls"] is None
