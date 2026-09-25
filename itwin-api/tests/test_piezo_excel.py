"""Тесты экспорта пьезометра в Excel (openpyxl) и форматов обмена ZuluGIS/QGIS."""

import io
import openpyxl
from database.piezo_excel import generate_piezometer_excel
from routers.piezometer import PiezometerExcelRequest


def test_piezometer_excel_request_validation():
    req = PiezometerExcelRequest(waypoints=[1, 2, 3])
    assert req.target_nodes == [1, 2, 3]

    req_nodes = PiezometerExcelRequest(nodes=[10, 20])
    assert req_nodes.target_nodes == [10, 20]

    try:
        PiezometerExcelRequest(waypoints=[1]).target_nodes
        assert False, "Should raise ValueError for < 2 nodes"
    except ValueError:
        pass


def test_generate_piezometer_excel():
    path_data = [
        {"node_id": 1, "label": "Источник 1", "distance": 0.0, "z": 800.0, "h_pod": 860.0, "h_obr": 825.0},
        {"node_id": 2, "label": "Узел 2", "distance": 150.0, "z": 802.0, "h_pod": 858.0, "h_obr": 826.0},
        {"node_id": 3, "label": "ТП 3", "distance": 320.0, "z": 805.0, "h_pod": 855.0, "h_obr": 828.0},
    ]

    segment_details = [
        {
            "node1_id": 1,
            "node1_label": "Источник 1",
            "node2_id": 2,
            "node2_label": "Узел 2",
            "line_id": 101,
            "length": 150.0,
            "diameter": 300.0,
            "flow": 120.0,
            "velocity": 1.2,
            "pressure_drop": 2.0,
            "specific_pressure_drop": 65.0,
            "h_pod_start": 860.0,
            "h_pod_end": 858.0,
            "h_obr_start": 825.0,
            "h_obr_end": 826.0,
            "distance_to_end": 150.0,
        },
        {
            "node1_id": 2,
            "node1_label": "Узел 2",
            "node2_id": 3,
            "node2_label": "ТП 3",
            "line_id": 102,
            "length": 170.0,
            "diameter": 250.0,
            "flow": 95.0,
            "velocity": 1.1,
            "pressure_drop": 3.0,
            "specific_pressure_drop": 72.0,
            "h_pod_start": 858.0,
            "h_pod_end": 855.0,
            "h_obr_start": 826.0,
            "h_obr_end": 828.0,
            "distance_to_end": 320.0,
        },
    ]

    excel_bytes = generate_piezometer_excel(path_data, segment_details)
    assert len(excel_bytes) > 1000

    # Parse with openpyxl to verify content
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert "Техн.информация" in wb.sheetnames
    assert "Пьезометрический профиль" in wb.sheetnames

    ws_tech = wb["Техн.информация"]
    assert "ТЕХНОЛОГИЧЕСКАЯ ИНФОРМАЦИЯ" in str(ws_tech["A3"].value)
    # Check that row 15 has node 1 and "Подающий", row 16 has node 1 and "Обратный"
    assert ws_tech.cell(row=15, column=1).value == 1
    assert ws_tech.cell(row=15, column=3).value == "Подающий"
    assert ws_tech.cell(row=16, column=1).value == 1
    assert ws_tech.cell(row=16, column=3).value == "Обратный"

    ws_chart = wb["Пьезометрический профиль"]
    assert len(ws_chart._charts) == 1
