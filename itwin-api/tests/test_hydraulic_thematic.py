"""Тесты для тематических гидравлических карт и результатов расчетов."""

import asyncio
from unittest.mock import AsyncMock
import pytest

from database.calculations import get_calculation_results_geojson


def _line(line_id, flow, velocity, spec_mm, *, supply=True):
    """Строка запроса участка: подача (externalsignlineid=2) и обратка (=3)."""
    empty = {"length_m": None, "diameter_mm": None, "flow": None, "velocity": None,
             "spec_loss_mm_m": None, "loss_total": None, "head_end": None, "avail_head_end": None}
    row = {
        "line_id": line_id,
        "length_return_m": 50.0, "diameter_return_mm": 207.0,
        "flow_return": -flow, "velocity_return": velocity, "spec_loss_return_mm_m": spec_mm,
        "loss_total_return": 0.3, "head_end_return": 30.0,
        "geometry": '{"type":"LineString","coordinates":[[76.9,43.2],[76.91,43.21]]}',
    }
    row.update({"length_m": 50.0, "diameter_mm": 207.0, "flow": flow, "velocity": velocity,
                "spec_loss_mm_m": spec_mm, "loss_total": 0.45, "head_end": 75.5,
                "avail_head_end": 40.0} if supply else empty)
    return row


def test_get_calculation_results_geojson_thematic():
    async def _run():
        mock_conn = AsyncMock()
        mock_conn.fetch.side_effect = [
            [
                _line(1, 120.5, 1.8, 9.8),        # 9.8 мм/м = 96.1 Па/м > 80; v > 1.5
                _line(2, -15.0, 0.2, 2.5),        # обратное направление, v < 0.3
                _line(3, 40.0, 0.8, 3.0, supply=False),  # только обратка
            ],
            [
                {"node_id": 10, "label": "Узел 10", "h_pod": 80.0, "h_obr": 35.0,
                 "t_pod": 115.0, "t_obr": 65.0,
                 "geometry": '{"type":"Point","coordinates":[76.9,43.2]}'},
                {"node_id": 11, "label": None, "h_pod": 70.0, "h_obr": None,
                 "t_pod": 110.0, "t_obr": None,
                 "geometry": '{"type":"Point","coordinates":[76.91,43.21]}'},
            ],
        ]

        result = await get_calculation_results_geojson(mock_conn, 42)

        line_sql = mock_conn.fetch.call_args_list[0].args[0]
        # Колонки по смыслу sety/out/ut_out.py, а не a7..a10
        assert "s.a13 AS flow" in line_sql
        assert "s.a10 AS velocity" in line_sql
        assert "s.a14 AS spec_loss_mm_m" in line_sql
        assert "externalsignlineid = 2" in line_sql and "externalsignlineid = 3" in line_sql

        summary = result["summary"]
        assert summary == {"calculation_id": 42, "lines_count": 3, "nodes_count": 2,
                           "high_velocity_count": 1, "over_resistance_count": 1}

        lines = [f["properties"] for f in result["features"] if f["properties"]["kind"] == "line"]
        assert lines[0]["flow_dir"] == 1 and lines[0]["velocity_status"] == "high"
        assert lines[0]["is_over_resistance"] is True
        assert lines[0]["specific_pressure_drop"] == pytest.approx(96.1, abs=0.1)
        assert lines[1]["flow_dir"] == -1 and lines[1]["velocity_status"] == "low"
        assert lines[1]["is_over_resistance"] is False
        # Участок без подачи раскрашивается по обратке
        assert lines[2]["pipe"] == "return" and lines[2]["flow"] == -40.0 and lines[2]["flow_dir"] == -1

        nodes = [f["properties"] for f in result["features"] if f["properties"]["kind"] == "node"]
        assert nodes[0]["delta_h"] == 45.0
        # Располагаемый напор только при обеих трубах
        assert nodes[1]["delta_h"] is None and nodes[1]["label"] == "Узел 11"

    asyncio.run(_run())
