"""Сеть водоканала из ГИС → модель EPANET (database/water_gis.py): сшивка, Т-примыкания, источник, отбор, .inp."""

import math

import pytest
from shapely.geometry import LineString, MultiLineString, Point

from database import water_gis as wg
from database.water import WaterError

LAT0, LON0 = 43.25, 76.9


def ll(x_m: float, y_m: float) -> tuple[float, float]:
    """Метры от точки (LON0, LAT0) → долгота, широта."""
    return LON0 + x_m / (111_320 * math.cos(math.radians(LAT0))), LAT0 + y_m / 110_540


def line(*pts):
    return LineString([ll(x, y) for x, y in pts])


# магистраль M 0→400 м (Ø300, сталь, тупик в 0 — ввод), ответвление B от середины магистрали на север: начало в 0,3 м
# от неё (Т-примыкание); продолжение C от конца M с зазором 0,2 м; кусок D в 2 км — отдельно; E — нулевая длина
GEOMS = [
    line((0, 0), (400, 0)),
    line((200, 0.3), (200, 150)),
    line((400.2, 0), (400.2, -120)),
    line((2000, 0), (2100, 0)),
    line((50, 50), (50.1, 50)),
    Point(ll(10, 10)),
]
ROWS = [
    {"id": "M-1", "dn": 300, "mat": "Сталь"},
    {"id": "B-1", "dn": 150, "mat": "ПЭ100"},
    {"id": "C-1", "dn": None, "mat": "чугун"},
    {"id": "D-1", "dn": 100, "mat": "ПВХ"},
    {"id": "E-1", "dn": 100, "mat": ""},
    {"id": "X", "dn": 50, "mat": ""},
]
PARAMS = wg.GisParams(diameter_field="dn", material_field="mat", id_field="id", snap_m=0.5, total_demand_ls=10,
                      elevation_m=700, source_head_m=50)


def test_material_c():
    assert [wg.material_c(v) for v in ("Сталь", "Ст.3", "ПЭ100", "ПЭ", "чугун", "ВЧШГ", "ж/б", "ПВХ", "стекло", None)] == \
        [100, 100, 140, 140, 100, 130, 120, 140, None, None]


def test_utm_zone():
    assert wg.utm_epsg(76.9, 43.25) == 32643 and wg.utm_epsg(37.6, 55.7) == 32637 and wg.utm_epsg(-58, -34) == 32721


def test_build_snaps_splits_tee_and_keeps_connected_part():
    net = wg.build_network(GEOMS, ROWS, PARAMS)
    r = net["report"]
    assert r["epsg"] == 32643 and r["rows_without_lines"] == 1
    assert r["t_splits"] == 1                          # магистраль M разрезана в точке ответвления
    assert r["zero_length_dropped"] == 1 and r["dropped_pipes"] == 1  # E (0,1 м < допуска) — нулевая, D — отдельно
    ids = sorted(q["id"] for q in net["pipes"])
    assert ids == ["B-1", "C-1", "M-1-1", "M-1-2"]
    assert r["components"] == 2
    assert r["length_km"] == pytest.approx(0.67, abs=0.005)  # 400 + 149,7 + 120 м
    # источник — тупик крупнейшей трубы (начало магистрали в 0 м)
    src = next(n for n in net["nodes"] if n["source"])
    assert src["id"] == "R1" and r["sources"][0]["auto"] and r["kept_components"] == 1
    assert r["sources"][0]["lon"] == pytest.approx(LON0, abs=1e-6) and r["source_head_m"] == 750
    # отбор: весь, без источника, пропорционально половине длины примыкающих труб
    assert sum(n["demand_ls"] for n in net["nodes"]) == pytest.approx(10)
    pipes = {q["id"]: q for q in net["pipes"]}
    assert pipes["C-1"]["diameter_mm"] == 100 and r["diameter"]["missing"] == 1  # нет Ø — по умолчанию
    assert pipes["M-1-1"]["c"] == 100 and pipes["B-1"]["c"] == 140


def test_source_point_and_errors():
    p = wg.GisParams(**{**PARAMS.__dict__, "source_lon": ll(400, -120)[0], "source_lat": ll(400, -120)[1]})
    net = wg.build_network(GEOMS, ROWS, p)
    s0 = net["report"]["sources"][0]
    assert not s0["auto"] and s0["lat"] == pytest.approx(ll(400, -120)[1], abs=1e-5)
    far = wg.GisParams(**{**PARAMS.__dict__, "source_lon": ll(5000, 0)[0], "source_lat": LAT0})
    with pytest.raises(WaterError):
        wg.build_network(GEOMS, ROWS, far)
    with pytest.raises(WaterError):
        wg.build_network([Point(LON0, LAT0)], [{}], PARAMS)


def test_each_component_gets_its_own_source():
    p = wg.GisParams(**{**PARAMS.__dict__, "components": "each"})
    net = wg.build_network(GEOMS, ROWS, p)
    r = net["report"]
    assert r["dropped_pipes"] == 0 and r["kept_components"] == 2 and [x["node"] for x in r["sources"]] == ["R1", "R2"]
    assert {q["id"] for q in net["pipes"]} >= {"D-1"}
    assert sum(n["demand_ls"] for n in net["nodes"]) == pytest.approx(10)
    assert net["nodes"][0]["id"] == "R1" and net["nodes"][1]["id"] == "R2"   # резервуары — первыми
    assert "R2  750.00" in wg.to_inp(net, "t", p)
    with pytest.raises(WaterError):
        wg.parse_params({"components": "all"})


def test_multilinestring_and_ids_without_field():
    geoms = [MultiLineString([[ll(0, 0), ll(100, 0)], [ll(100, 0), ll(100, 100)]])]
    net = wg.build_network(geoms, [{}], wg.GisParams())
    assert [q["id"] for q in net["pipes"]] == ["P1", "P2"]


def test_diameter_in_metres_detected():
    rows = [{**r, "dn": (r["dn"] or 0) / 1000 or None} for r in ROWS]
    net = wg.build_network(GEOMS, rows, PARAMS)
    assert net["report"]["diameter"]["field_in_metres"]
    assert {q["id"]: q["diameter_mm"] for q in net["pipes"]}["B-1"] == pytest.approx(150)


def test_inp_text_sections():
    net = wg.build_network(GEOMS, ROWS, PARAMS)
    text = wg.to_inp(net, "Тест", PARAMS)
    for section in ("[JUNCTIONS]", "[RESERVOIRS]", "[PIPES]", "[PATTERNS]", "[COORDINATES]", "[END]"):
        assert section in text
    assert " R1  750.00" in text and " Units LPS" in text
    assert sum(wg.DAILY_PATTERN) / 24 == pytest.approx(1.0, abs=0.01)


def test_match_valves_to_nearest_pipe_end():
    net = wg.build_network(GEOMS, ROWS, PARAMS)
    pairs, missed = wg.match_valves([Point(ll(201, 20)), Point(ll(195, 0.5)), Point(ll(1000, 1000)), None], net, 5)
    pipes = {q["id"]: q for q in net["pipes"]}
    assert missed == 2
    # у начала ответвления и у конца первой половины магистрали — оба у узла Т-примыкания
    assert pairs == sorted([("B-1", pipes["B-1"]["a"]), ("M-1-1", pipes["M-1-1"]["b"])])
    assert pipes["B-1"]["a"] == pipes["M-1-1"]["b"]


def test_parse_params_bounds():
    assert wg.parse_params({"snap_m": "1.5", "total_demand_ls": 20}).snap_m == 1.5
    with pytest.raises(WaterError):
        wg.parse_params({"snap_m": 100})
    with pytest.raises(WaterError):
        wg.parse_params({"source_lon": 76.9})


def test_suggest_fields_and_valves_layer():
    s = wg.suggest_fields(["FID", "Ду", "Материал", "Состояние", "name"])
    assert s == {"diameter_field": "Ду", "material_field": "Материал", "id_field": "FID", "status_field": "Состояние"}
    assert wg.suggest_fields(["ID_TR", "Ду"])["id_field"] == "ID_TR"
    layers = [{"name": "pipes", "geometry_type": "LineString"}, {"name": "hydrants", "geometry_type": "Point"},
              {"name": "Задвижки", "geometry_type": "Point"}]
    assert wg.suggest_valves_layer(layers, "pipes") == "Задвижки"
    assert wg.suggest_valves_layer(layers[:2], "pipes") == "hydrants"
    assert wg.suggest_valves_layer(layers[:1], "pipes") is None
