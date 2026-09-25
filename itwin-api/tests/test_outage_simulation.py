"""Тесты для модуля моделирования аварийных отключений (Outage Simulation)."""

import asyncio
from unittest.mock import AsyncMock
import pytest
from database.outage_simulation import (
    invalidate_outage_cache,
    simulate_outage_isolation,
)


def test_outage_simulation_requires_target():
    """Тест: валидация обязательного указания line_id или node_id."""
    with pytest.raises(ValueError, match="Необходимо указать line_id или node_id"):
        asyncio.run(simulate_outage_isolation(None, line_id=None, node_id=None))


def test_outage_simulation_mock_bfs():
    """Тест изоляции участка с изолирующими задвижками на границах (Unit/Mock)."""
    invalidate_outage_cache()

    mock_conn = AsyncMock()

    # Схема:
    # Узел 1 --(Линия 10, повреждена)--> Узел 2
    # Узел 2 --(Линия 20, задвижка 101)--> Узел 3
    # Узел 1 --(Линия 30, без задвижки)--> Узел 4
    # Узел 4 --(Линия 40, задвижка 102)--> Узел 5

    mock_lines = [
        {
            "id": 10,
            "nodeid1": 1,
            "nodeid2": 2,
            "externalsignlineid": 1,
            "length": 50.0,
            "diameter": 200.0,
            "diameter_internal": 190.0,
            "state_flow": 1,
            "state_ret": 1,
        },
        {
            "id": 20,
            "nodeid1": 2,
            "nodeid2": 3,
            "externalsignlineid": 1,
            "length": 40.0,
            "diameter": 150.0,
            "diameter_internal": 140.0,
            "state_flow": 1,
            "state_ret": 1,
        },
        {
            "id": 30,
            "nodeid1": 1,
            "nodeid2": 4,
            "externalsignlineid": 1,
            "length": 30.0,
            "diameter": 100.0,
            "diameter_internal": 95.0,
            "state_flow": 1,
            "state_ret": 1,
        },
        {
            "id": 40,
            "nodeid1": 4,
            "nodeid2": 5,
            "externalsignlineid": 1,
            "length": 60.0,
            "diameter": 100.0,
            "diameter_internal": 95.0,
            "state_flow": 1,
            "state_ret": 1,
        },
    ]

    mock_dampers = [
        {
            "id": 101,
            "lineid": 20,
            "owner_node_id": None,
            "display_name": "Задвижка №101",
            "nominal_diameter": 150.0,
            "damperarmaturestateid": 1,
            "state_id": 1,
            "state_name": "Открыта",
            "lng": 76.915,
            "lat": 43.215,
        },
        {
            "id": 102,
            "lineid": 40,
            "owner_node_id": None,
            "display_name": "Задвижка №102",
            "nominal_diameter": 100.0,
            "damperarmaturestateid": 1,
            "state_id": 1,
            "state_name": "Открыта",
            "lng": 76.885,
            "lat": 43.185,
        },
    ]

    mock_nodes = [
        {"id": 1, "name": "Узел 1", "lng": 76.9, "lat": 43.2},
        {"id": 2, "name": "Узел 2", "lng": 76.91, "lat": 43.21},
        {"id": 4, "name": "Узел 4", "lng": 76.89, "lat": 43.19},
    ]

    mock_consumers = [
        {
            "ctype": "real",
            "id": 501,
            "nodeid": 2,
            "name": "Жилой дом ул. Абая 10",
            "heating_load": 0.85,
            "ventilation_load": 0.1,
            "hot_water_load": 0.35,
        },
        {
            "ctype": "generalized",
            "id": 502,
            "nodeid": 4,
            "name": "Школа №25",
            "heating_load": 1.2,
            "ventilation_load": 0.3,
            "hot_water_load": 0.5,
        },
    ]

    mock_geoms = [
        {"id": 10, "g": '{"type":"LineString","coordinates":[[76.9,43.2],[76.91,43.21]]}'},
        {"id": 20, "g": '{"type":"LineString","coordinates":[[76.91,43.21],[76.92,43.22]]}'},
        {"id": 30, "g": '{"type":"LineString","coordinates":[[76.9,43.2],[76.89,43.19]]}'},
        {"id": 40, "g": '{"type":"LineString","coordinates":[[76.89,43.19],[76.88,43.18]]}'},
    ]

    async def mock_fetch(query, *args):
        q = query.lower()
        if "linesobj" in q and "heatpipesections" in q:
            return mock_lines
        if "st_asgeojson" in q and "from linesobj" in q:
            return [g for g in mock_geoms if g["id"] in args[0]]
        if "dampers" in q and "damperarmaturestates" in q:
            return mock_dampers
        if "nodes" in q:
            return mock_nodes
        if "generalizedconsumers" in q or "realconsumers" in q:
            return mock_consumers
        return []

    mock_conn.fetch = mock_fetch

    result = asyncio.run(simulate_outage_isolation(mock_conn, line_id=10))

    assert result["success"] is True
    summary = result["summary"]
    # Линии 10 (авария) и 30 (без задвижки) попадают в изоляцию = 2 линии
    assert summary["isolated_lines_count"] == 2
    # Узлы 1, 2, 4 = 3 узла
    assert summary["isolated_nodes_count"] == 3
    # Отсекающие задвижки: 101 (на линии 20) и 102 (на линии 40) = 2 задвижки
    assert summary["valves_count"] == 2
    valves = result["valves_to_close"]
    valve_ids = {v["id"] for v in valves}
    assert valve_ids == {101, 102}

    # Потребители: 2 здания в изолированных узлах
    assert summary["consumers_count"] == 2
    assert summary["total_heating_load_gcal_h"] == pytest.approx(2.05, 0.01)
    assert summary["total_gvs_load_gcal_h"] == pytest.approx(0.85, 0.01)
    assert summary["total_load_gcal_h"] == pytest.approx(3.30, 0.01)

    # GeoJSON коллекции
    assert len(result["geojson"]["isolated_pipes"]["features"]) == 2
    assert len(result["geojson"]["valves_to_close"]["features"]) == 2
    assert len(result["geojson"]["affected_consumers"]["features"]) == 2


def _net_fetch(lines, dampers, consumers=()):
    async def fetch(query, *args):
        q = query.lower()
        if "linesobj" in q and "heatpipesections" in q:
            return lines
        if "dampers" in q and "damperarmaturestates" in q:
            return dampers
        if "st_asgeojson" in q and "from linesobj" in q:
            return []
        if "generalizedconsumers" in q or "realconsumers" in q:
            return [c for c in consumers if c["nodeid"] in args[0]]
        return []
    return fetch


def _line(lid, n1, n2, state_flow=1, state_ret=1, sign=1):
    return {"id": lid, "nodeid1": n1, "nodeid2": n2, "externalsignlineid": sign,
            "length": 10.0, "diameter": 100.0, "diameter_internal": 95.0,
            "state_flow": state_flow, "state_ret": state_ret}


def _damper(did, lineid, owner=None, state=1):
    return {"id": did, "lineid": lineid, "owner_node_id": owner, "display_name": f"Задвижка №{did}",
            "nominal_diameter": 100.0, "state_id": state, "state_name": "",
            "lng": None, "lat": None}


def test_outage_stops_at_chamber_with_internal_valves():
    """Узел с задвижками во внутренней схеме — граница зоны; закрытые задвижки отдельно;
    отключённая (обе трубы) линия не проводит отключение дальше."""
    invalidate_outage_cache()
    conn = AsyncMock()
    # 1 --L10 (авария)-- 2(камера) --L20-- 3 ;  1 --L30 (отключена)-- 4 ;  1 --L50-- 6
    lines = [_line(10, 1, 2), _line(20, 2, 3), _line(30, 1, 4, state_flow=2, state_ret=2), _line(50, 1, 6)]
    dampers = [_damper(201, 900, owner=2), _damper(202, 901, owner=2, state=2)]
    consumers = [
        {"ctype": "real", "id": 1, "nodeid": 3, "name": "за камерой", "heating_load": 1.0,
         "ventilation_load": 0.0, "hot_water_load": 0.0},
        {"ctype": "real", "id": 2, "nodeid": 6, "name": "в зоне", "heating_load": 0.5,
         "ventilation_load": 0.0, "hot_water_load": 0.0},
    ]
    conn.fetch = _net_fetch(lines, dampers, consumers)

    result = asyncio.run(simulate_outage_isolation(conn, line_id=10))

    assert {f["properties"]["id"] for f in result["geojson"]["isolated_pipes"]["features"]} == set()
    assert result["summary"]["isolated_lines_count"] == 2          # L10 и L50
    assert result["boundary_nodes"] == [2]
    assert [v["id"] for v in result["valves_to_close"]] == [201]
    assert [v["id"] for v in result["valves_already_closed"]] == [202]
    assert [c["id"] for c in result["affected_consumers"]] == [2]


def test_outage_rejects_line_of_internal_scheme():
    invalidate_outage_cache()
    conn = AsyncMock()
    conn.fetch = _net_fetch([_line(10, 1, 2)], [])
    conn.fetchrow = AsyncMock(return_value={"id": 77, "internalnodeid": 2})
    with pytest.raises(ValueError, match="внутреннюю схему узла 2"):
        asyncio.run(simulate_outage_isolation(conn, line_id=77))
