"""Пьезометр показывает ровно us_out одного расчёта (sety/out/us_out.py), а не измеренные давления."""

import asyncio
from unittest.mock import AsyncMock

import networkx as nx
import pytest

from routers.piezometer import _assemble_path_data, _route_calculation_id


def _node(node_id, z, pih_pod, pih_obr, meas_pod=None, meas_obr=None):
    return {"id": node_id, "geomarktoptube": z, "meas_pod": meas_pod, "meas_obr": meas_obr,
            "label": str(node_id), "lng": 76.9, "lat": 43.2, "t_pod": 130.0, "t_obr": 70.0,
            "pih_pod": pih_pod, "pih_obr": pih_obr}


def test_heads_come_from_us_out_not_measured_pressure():
    G = nx.Graph()
    G.add_edge(1, 2, weight=30.0)
    conn = AsyncMock()
    # у узла 1 есть измеренное давление 55 м — оно не должно подменять расчётные 62.2 м
    conn.fetch.return_value = [_node(1, 799.2, 62.2, 20.1, meas_pod=55.0), _node(2, 800.0, 61.0, 21.0)]

    path = asyncio.run(_assemble_path_data(conn, G, [1, 2], 9))

    sql, nodes, cid = conn.fetch.call_args.args
    assert nodes == [1, 2] and cid == 9
    # nodes.calcpress* по умолчанию 0 (gid8 baza.sql) — 0 означает «не измерено»
    assert "NULLIF(n.calcpressflow, 0)" in sql
    # pt_out и us_out — того же расчёта, что и весь маршрут
    assert "pt_out WHERE nodeid = n.id AND calculationid = $2" in sql
    assert "us1.calculationid = $2" in sql and "us2.calculationid = $2" in sql
    assert path[0]["h_pod"] == pytest.approx(799.2 + 62.2)
    assert path[0]["h_obr"] == pytest.approx(799.2 + 20.1)
    assert path[0]["h_pod_meas"] == pytest.approx(799.2 + 55.0)
    assert path[1]["h_pod_meas"] is None
    assert path[1]["distance"] == 30.0


def test_route_uses_one_calculation():
    conn = AsyncMock()
    assert asyncio.run(_route_calculation_id(conn, [1, 2], 5)) == 5
    conn.fetchval.assert_not_called()
    conn.fetchval.return_value = 9
    assert asyncio.run(_route_calculation_id(conn, [1, 2], None)) == 9
    assert "max(calculationid) FROM us_out" in conn.fetchval.call_args.args[0]
