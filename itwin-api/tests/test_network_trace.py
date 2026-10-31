"""Трассировки сети по топологии (database/network_trace.py) — на графах без базы."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from database.network_trace import (
    BlockTree,
    _simple_graph,
    run_trace,
    subnetworks,
    trace_connected,
    trace_downstream,
    trace_upstream,
    upstream_of_line,
)


def _adj(edges):
    """edges: [(line_id, n1, n2)] → смежность как в get_outage_network_graph."""
    adj = {}
    for lid, a, b in edges:
        adj.setdefault(a, []).append((lid, b))
        adj.setdefault(b, []).append((lid, a))
    return adj


# Источник 1. Магистраль 1-2-3, кольцо 3-4-5-3, тупик 5-6, ответвление 2-7.
#   1 ─10─ 2 ─20─ 3 ─30─ 4
#          │       └─50─ 5 ─40┘ (кольцо 3-4-5)
#          70       5 ─60─ 6
#          7
EDGES = [(10, 1, 2), (20, 2, 3), (30, 3, 4), (40, 4, 5), (50, 3, 5), (60, 5, 6), (70, 2, 7)]
ADJ = _adj(EDGES)
SOURCES = {1}


def test_connected_stops_at_barriers_and_stop_lines():
    full = trace_connected(ADJ, [6])
    assert full.nodes == {1, 2, 3, 4, 5, 6, 7}

    cut = trace_connected(ADJ, [6], blocked_lines={20})
    assert cut.nodes == {3, 4, 5, 6}

    # задвижка на участке 20: участок в результате, дальше не идём
    stop = trace_connected(ADJ, [6], stop_lines={20})
    assert 20 in stop.lines and 2 not in stop.nodes and 3 in stop.stopped_at

    # узел-камера 2 с задвижками внутри: попадает в результат, дальше не идём
    chamber = trace_connected(ADJ, [6], stop_nodes={2})
    assert 2 in chamber.nodes and 1 not in chamber.nodes and 7 not in chamber.nodes


def test_upstream_takes_all_ring_paths_but_not_side_branches():
    res = trace_upstream(ADJ, SOURCES, [6])
    assert res.nodes == {1, 2, 3, 4, 5, 6}  # оба пути по кольцу, без ответвления 7
    assert res.lines == {10, 20, 30, 40, 50, 60}
    assert res.sources == {1}


def test_upstream_of_dead_end_line_uses_near_end_only():
    res = upstream_of_line(ADJ, SOURCES, (70, 2, 7))
    assert res.nodes == {1, 2, 7}
    assert res.lines == {10, 70}


def test_upstream_of_ring_line_merges_both_ends():
    res = upstream_of_line(ADJ, SOURCES, (30, 3, 4))
    assert {3, 4, 5} <= res.nodes and 30 in res.lines and 6 not in res.nodes


def test_upstream_without_path_to_source_is_start_only():
    res = trace_upstream(ADJ, SOURCES, [6], blocked_lines={20})
    assert res.nodes == {6} and res.sources == frozenset()


def test_block_tree_paths_between_cut_vertices():
    tree = BlockTree.build(_simple_graph(ADJ, set(), set()))
    assert tree.nodes_on_paths(1, 3) == {1, 2, 3}
    assert tree.nodes_on_paths(3, 5) == {3, 4, 5}
    assert tree.nodes_on_paths(7, 7) == {7}


def test_downstream_respects_ring_bypass():
    # Участок 30 в кольце: обход по 50-40 сохраняет питание
    assert trace_downstream(ADJ, SOURCES, start_lines={30}).nodes == frozenset()
    # Узел 5 выводим: тупик 6 теряет питание, 4 питается через 30
    res = trace_downstream(ADJ, SOURCES, start_nodes={5})
    assert res.nodes == {5, 6}
    assert 60 in res.lines
    # Участок 20 — мост к кольцу: всё кольцо и тупик ниже
    assert trace_downstream(ADJ, SOURCES, start_lines={20}).nodes == {3, 4, 5, 6}


def test_subnetworks_finds_islands():
    adj = _adj(EDGES + [(80, 100, 101)])
    zones = subnetworks(adj, SOURCES)
    assert len(zones) == 2
    assert zones[0].sources == {1} and len(zones[0].nodes) == 7
    assert zones[1].nodes == {100, 101} and not zones[1].sources


def _net():
    line_info = {lid: {"id": lid, "nodeid1": a, "nodeid2": b, "externalsignlineid": 1,
                       "length": 100.0, "diameter": 200.0, "diameter_internal": 200.0} for lid, a, b in EDGES}
    return {"adj": ADJ, "line_info": line_info, "sources": SOURCES, "source_kinds": {1: "heat_source"}, "normally_closed_lines": set(),
            "dampers_by_line": {}, "dampers_by_node": {}, "baseline_reachable": set(ADJ)}


def _run(**kwargs):
    conn = AsyncMock()
    conn.fetch.return_value = []
    with patch("database.network_trace.get_outage_network_graph", AsyncMock(return_value=_net())):
        return asyncio.run(run_trace(conn, **kwargs))


def test_run_trace_summary_and_validation():
    out = _run(trace_type="downstream", start_line_ids=[20], start_node_ids=[])
    assert out["model"] == "topology"
    assert out["node_ids"] == [3, 4, 5, 6]
    assert out["summary"]["lines_count"] == len(out["line_ids"])
    # двухтрубный участок 100 м диаметром 200 мм: 2 трубы на участок
    assert out["summary"]["total_pipe_length_m"] == 200.0 * out["summary"]["lines_count"]

    up = _run(trace_type="upstream", start_line_ids=[], start_node_ids=[6])
    assert up["source_node_ids"] == [1] and up["consumers"] == []
    assert up["sources"] == [{"node_id": 1, "kind": "heat_source"}]

    with pytest.raises(ValueError, match="начальную точку"):
        _run(trace_type="connected", start_line_ids=[], start_node_ids=[])
    with pytest.raises(ValueError, match="не входят в расчётную схему"):
        _run(trace_type="connected", start_line_ids=[999], start_node_ids=[])
    with pytest.raises(ValueError, match="Неизвестный тип"):
        _run(trace_type="sideways", start_line_ids=[], start_node_ids=[1])


def test_trace_request_limits_and_independent_defaults():
    from pydantic import ValidationError
    from routers.analysis import TraceRequest

    a = TraceRequest(trace_type="upstream", start_node_ids=[1])
    b = TraceRequest(trace_type="upstream")
    a.barrier_line_ids.append(5)
    assert b.barrier_line_ids == []
    with pytest.raises(ValidationError):
        TraceRequest(trace_type="upstream", start_node_ids=list(range(1, 502)))
    with pytest.raises(ValidationError):
        TraceRequest(trace_type="upstream", start_node_ids=[0])


def test_sources_named_when_known():
    from database.network_trace import _source_names, _sources_out

    conn = AsyncMock()
    conn.fetch.return_value = [{"id": 7, "name": "ТЭЦ-2"}, {"id": 8, "name": None}]
    names = asyncio.run(_source_names(conn, {8, 7}))
    assert names == {7: "ТЭЦ-2"} and conn.fetch.call_args.args[1] == [7, 8]
    out = _sources_out({"source_kinds": {8: "set_pressure"}}, {7, 8}, names)
    assert out == [{"node_id": 7, "kind": "heat_source", "name": "ТЭЦ-2"}, {"node_id": 8, "kind": "set_pressure"}]
    assert asyncio.run(_source_names(conn, set())) == {}
