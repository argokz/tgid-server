"""Исполнительная съёмка в импорте участков: GPX, DXF, таблица точек (database/survey_formats, network_import)."""

import pytest

from database import network_import as ni
from database.survey_formats import parse_dxf, parse_gpx

GPX = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="t" xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="43.1" lon="76.9"><name>point</name></wpt>
  <trk><name>Ввод 1</name>
    <trkseg><trkpt lat="43.20" lon="76.90"/><trkpt lat="43.21" lon="76.91"/><trkpt lat="43.22" lon="76.91"/></trkseg>
    <trkseg><trkpt lat="43.30" lon="76.90"/></trkseg>
  </trk>
  <rte><name>R</name><rtept lat="43.4" lon="76.8"/><rtept lat="43.41" lon="76.81"/></rte>
</gpx>""".encode("utf-8")


def _dxf(*entities: str) -> bytes:
    body = "".join(entities)
    return f"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nSECTION\n2\nENTITIES\n{body}0\nENDSEC\n0\nEOF\n".encode("cp1251")


LINE = "0\nLINE\n5\n1A\n8\nТрасса\n10\n100.5\n20\n200.0\n30\n0\n11\n110.5\n21\n200.0\n31\n0\n"
LWPOLY = "0\nLWPOLYLINE\n8\nТрасса\n90\n3\n70\n0\n10\n0\n20\n0\n10\n10\n20\n0\n10\n10\n20\n10\n"
POLY = ("0\nPOLYLINE\n8\nЗдания\n66\n1\n70\n1\n10\n0\n20\n0\n"
        "0\nVERTEX\n8\nЗдания\n10\n0\n20\n0\n0\nVERTEX\n8\nЗдания\n10\n5\n20\n0\n0\nVERTEX\n8\nЗдания\n10\n5\n20\n5\n0\nSEQEND\n")
CIRCLE = "0\nCIRCLE\n8\n0\n10\n0\n20\n0\n40\n1\n"


def test_gpx_tracks_segments_and_routes():
    rows, geoms, warnings = parse_gpx(GPX)
    assert [r["type"] for r in rows] == ["трек", "маршрут"]
    assert rows[0]["name"] == "Ввод 1"
    assert list(geoms[0].coords)[0] == (76.90, 43.20)
    assert "меньше чем из двух точек: 1" in warnings[0]
    with pytest.raises(ValueError, match="DOCTYPE"):
        parse_gpx(b'<!DOCTYPE x [<!ENTITY a "b">]><gpx/>')


def test_dxf_lines_polylines_closed_and_skipped():
    rows, geoms, warnings = parse_dxf(_dxf(LINE, LWPOLY, POLY, CIRCLE))
    assert [r["entity"] for r in rows] == ["LINE", "LWPOLYLINE", "POLYLINE"]
    assert rows[0]["layer"] == "Трасса" and rows[0]["handle"] == "1A"
    assert list(geoms[0].coords) == [(100.5, 200.0), (110.5, 200.0)]
    assert len(geoms[1].coords) == 3
    assert list(geoms[2].coords)[-1] == (0.0, 0.0)  # замкнутая полилиния
    assert "CIRCLE — 1" in warnings[0]
    with pytest.raises(ValueError, match="Двоичный"):
        parse_dxf(b"AutoCAD Binary DXF\r\n\x1a\x00")


def test_dxf_upload_needs_crs_layers_filter_and_desktop_scale():
    src = ni.parse_upload([("s.dxf", _dxf(LINE, LWPOLY, POLY))])
    info = ni.describe_source(src, "lines")
    assert info["layers"] == [{"layer": "Здания", "count": 1}, {"layer": "Трасса", "count": 2}]
    assert not any(t["key"] in ("x", "y") for t in info["targets"])
    with pytest.raises(ValueError, match="нет системы координат"):
        ni.prepare_items(src, {"mode": "lines", "mapping": {}})
    with pytest.raises(ValueError, match="режим «Участки»"):
        ni.prepare_items(src, {"mode": "nodes", "mapping": {}, "source_crs": "local"})
    items = ni.prepare_items(src, {"mode": "lines", "mapping": {}, "source_crs": "desktop", "layers": ["Трасса"]})
    assert len(items) == 2 and items[0].srid == 9998
    assert items[0].wkt.startswith("LINESTRING (1.005 -2")


def test_gpx_upload_is_wgs84():
    src = ni.parse_upload([("t.gpx", GPX)])
    items = ni.prepare_items(src, {"mode": "lines", "mapping": {}})
    assert [it.srid for it in items] == [4326, 4326] and all(it.error is None for it in items)


def test_table_survey_points_grouped_by_trace():
    csv = "Трасса;X;Y;Ду\n1;100;200;150\n1;110;200;\n1;110;200;\n1;110;210;\n2;0;0;100\n2;bad;1;\n3;5;5;\n".encode("cp1251")
    src = ni.parse_upload([("s.csv", csv)])
    assert ni.describe_source(src, "lines")["suggested_mapping"] == {"x": "X", "y": "Y", "trace": "Трасса", "diameter": "Ду"}
    items = ni.prepare_items(src, {"mode": "lines", "mapping": {"x": "X", "y": "Y", "trace": "Трасса", "diameter": "Ду"},
                                   "source_crs": "local"})
    assert [it.row for it in items] == [2, 6, 8]
    assert items[0].wkt == "LINESTRING(100.0 200.0, 110.0 200.0, 110.0 210.0)"  # повтор точки убран
    assert items[0].attrs["diameter"] == 150.0 and items[0].srid == 9998
    assert "строка 7" in items[1].error
    assert "меньше двух" in items[2].error


def test_convert_point_desktop_is_cm_with_inverted_y():
    import asyncio

    from database.topology_cad import convert_point
    from tests.test_cad_topology import FakeConn

    conn = FakeConn([("ST_Transform(g, 4326)", lambda a: {"lng": 76.9, "lat": 43.3, "lx": a[0], "ly": a[1]})])
    res = asyncio.run(convert_point(conn, 365289.6, -1315539.2, "desktop"))
    assert conn.calls[0][2] == pytest.approx((3652.896, 13155.392, 9998))
    assert res["local"] == {"x": 3652.896, "y": 13155.392}
    assert res["desktop"] == {"x": 365289.6, "y": -1315539.2}
    with pytest.raises(ValueError, match="одна из"):
        asyncio.run(convert_point(conn, 1, 2, "utm"))
