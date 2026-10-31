"""Последствия аварий участков (database/outage_consequence.py): один обход графа отсеков против изоляции по участку."""

import random

import pytest

from database import outage_consequence as oc
from database.outage_simulation import downstream_without_supply, reachable_from_sources


def _net(lines, sources, valve_lines=(), valve_nodes=(), closed=()):
    """Граф в форме get_outage_network_graph: lines — {id: (n1, n2)}."""
    adj, info = {}, {}
    for lid, (a, b) in lines.items():
        info[lid] = {"id": lid, "nodeid1": a, "nodeid2": b}
        adj.setdefault(a, []).append((lid, b))
        adj.setdefault(b, []).append((lid, a))
    dampers_by_line = {lid: [{"id": lid, "state_id": 2 if lid in closed else 1}] for lid in valve_lines}
    normally_closed = set(closed)
    src = {s for s in sources if s in adj}
    return {"adj": adj, "line_info": info, "sources": src, "normally_closed_lines": normally_closed,
            "dampers_by_line": dampers_by_line, "dampers_by_node": {n: [{"id": n}] for n in valve_nodes},
            "baseline_reachable": reachable_from_sources(adj, src, blocked_lines=normally_closed)}


def _brute(net, lid):
    """Изоляция одного участка — как simulate_outage_isolation (без неисправных задвижек)."""
    adj, valve_lines, valve_nodes = net["adj"], net["dampers_by_line"], net["dampers_by_node"]
    iso_lines, iso_nodes, boundary, done, closed_valves = {lid}, set(), set(), {lid}, set()
    queue = []

    def reach(n):
        if n in iso_nodes or n in boundary:
            return
        if n in valve_nodes:
            boundary.add(n)
            return
        iso_nodes.add(n)
        queue.append(n)

    for n in (net["line_info"][lid]["nodeid1"], net["line_info"][lid]["nodeid2"]):
        reach(n)
    while queue:
        cur = queue.pop(0)
        for other_lid, nb in adj.get(cur, []):
            if other_lid in done:
                continue
            done.add(other_lid)
            if other_lid in valve_lines:
                closed_valves.add(other_lid)
            else:
                iso_lines.add(other_lid)
                reach(nb)
    lost, _ = downstream_without_supply(net, isolated_lines=iso_lines, isolated_nodes=iso_nodes,
                                        closed_valve_lines=closed_valves)
    return iso_nodes, lost


def _loads(nodes, rnd):
    out = {}
    for n in nodes:
        if rnd.random() < 0.6:
            x = oc.Loads()
            x.consumers = rnd.randint(1, 3)
            x.load = round(rnd.random(), 3)
            x.social = int(rnd.random() < 0.2)
            out[n] = x
    return out


def _sum(nodes, loads, attr):
    return sum(getattr(loads[n], attr) for n in nodes if n in loads)


def test_simple_chain_with_valves_and_ring():
    # источник 1 — 2 — 3 [камера] — 4 — 5, кольцо 2–6–4 обходит камеру; 4–7 — тупик за задвижкой на 7–8
    lines = {10: (1, 2), 11: (2, 3), 12: (3, 4), 13: (4, 5), 14: (2, 6), 15: (6, 4), 16: (4, 7), 17: (7, 8)}
    net = _net(lines, sources=[1], valve_lines=[17], valve_nodes=[3])
    loads = {n: oc.Loads() for n in range(1, 9)}
    for n in loads:
        loads[n].consumers = 1
    res = oc.line_consequences(net, loads)
    # авария 1–2: зона — всё до камеры 3 и задвижки 17 (2, 6, 4, 5, 7 и источник); источник в зоне — без питания
    # остаются камера 3 и узел 8 за задвижкой
    assert res[10]["zone_consumers"] == 6 and res[10]["down_consumers"] == 2
    # авария 2–3: зона 2,6,4,5,7 + 1 — камера 3 граница, тот же отсек
    assert res[11] == res[10]
    # участок с задвижкой 7–8: зона — отсек узла 7 (весь отсек источника) и узел 8; без питания — камера 3
    assert res[17]["zone_consumers"] == 7 and res[17]["down_consumers"] == 1


@pytest.mark.parametrize("seed", range(25))
def test_matches_isolation_per_line_on_random_networks(seed):
    rnd = random.Random(seed)
    n_nodes = rnd.randint(8, 40)
    lines, lid = {}, 100
    for n in range(2, n_nodes + 1):                     # остов — дерево
        lines[lid] = (rnd.randint(1, n - 1), n)
        lid += 1
    for _ in range(rnd.randint(0, n_nodes // 3)):       # кольца
        a, b = rnd.sample(range(1, n_nodes + 1), 2)
        lines[lid] = (a, b)
        lid += 1
    valve_lines = [x for x in lines if rnd.random() < 0.25]
    closed = [x for x in valve_lines if rnd.random() < 0.15]
    valve_nodes = [n for n in range(1, n_nodes + 1) if rnd.random() < 0.2]
    sources = rnd.sample(range(1, n_nodes + 1), rnd.randint(1, 3))
    net = _net(lines, sources, valve_lines, valve_nodes, closed)
    loads = _loads(range(1, n_nodes + 1), rnd)
    res = oc.line_consequences(net, loads)
    assert set(res) == set(lines)
    for x in lines:
        zone, lost = _brute(net, x)
        r = res[x]
        assert r["zone_consumers"] == _sum(zone, loads, "consumers"), (seed, x)
        assert r["down_consumers"] == _sum(lost, loads, "consumers"), (seed, x)
        assert r["down_load"] == pytest.approx(_sum(lost, loads, "load")), (seed, x)
        assert r["down_social"] == _sum(lost, loads, "social"), (seed, x)


def test_long_chain_no_recursion_limit():
    n = 20_000
    lines = {i: (i, i + 1) for i in range(1, n)}
    net = _net(lines, sources=[1], valve_lines=list(range(2, n, 100)))
    loads = {i: oc.Loads() for i in range(1, n + 1)}
    for x in loads.values():
        x.consumers = 1
    res = oc.line_consequences(net, loads)
    # авария в первом отсеке (узлы 1–2) отключает всё ниже задвижки на 2–3
    assert res[1]["zone_consumers"] == 2 and res[1]["down_consumers"] == n - 2
