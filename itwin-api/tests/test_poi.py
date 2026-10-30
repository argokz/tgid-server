"""Социальные объекты (database/poi.py) и выборка «в N м от» них (database/network_select.py)."""

import asyncio

import pytest

from database import network_select as ns
from database import poi


@pytest.mark.parametrize("name, category", [
    ("Тайбурыл 17 Школа 23", "school"),
    ("ул.Алтынсарина 9 *(17) СШ N 25", "school"),
    ("Карасай Батыра, 7, СШ№36", "school"),
    ("гимназия №12", "school"),
    ("Кошкарбаева,33 Д/С № 26 1эу", "kindergarten"),
    ("дс 100", "kindergarten"),
    ("Московская 28а (58), Ясли сад №51", "kindergarten"),
    ("Медеу 8/1, Детский сад \"Аруана\"", "kindergarten"),
    ("Молдагуловой,28 Роддом N1эу1", "hospital"),
    ("Детская больница №2", "hospital"),
    ("Сейфуллина 28, Поликлиника №1", "clinic"),
    ("Акжол 24, Медпункт", "clinic"),
    ("Мынарал 14, Интернат 1", "social"),
    ("Сарыбулак 25, приют для девочек", "social"),
    ("лицей-интернат «Білім»", "school"),
    ("автошкола", None),
    ("яз школа", None),
    ("ТОО Дастан, офис", None),
    ("ДСК-2 склад", None),
    ("", None),
])
def test_classify_by_consumer_name(name, category):
    assert poi.classify(name) == category


def test_group_consumers_one_object_per_node_and_category():
    recs = [
        {"type": "real", "id": 1, "name": "Роддом N1 эу1", "nodeid": 10, "lon": 71.4, "lat": 51.1},
        {"type": "real", "id": 2, "name": "Роддом  N1 эу1", "nodeid": 10, "lon": 71.4, "lat": 51.1},
        {"type": "real", "id": 3, "name": "Роддом N1 эу2", "nodeid": 10, "lon": 71.4, "lat": 51.1},
        {"type": "generalized", "id": 4, "name": "Школа 5", "nodeid": 10, "lon": 71.4, "lat": 51.1},
        {"type": "real", "id": 5, "name": "Магазин", "nodeid": 11, "lon": 71.5, "lat": 51.2},
        # то же здание на другом узле в 50 м — тот же объект; в 2 км — другой
        {"type": "real", "id": 6, "name": "роддом n1 эу1", "nodeid": 12, "lon": 71.4005, "lat": 51.1003},
        {"type": "real", "id": 7, "name": "Роддом N1 эу1", "nodeid": 13, "lon": 71.43, "lat": 51.1},
    ]
    out = poi.group_consumers(recs)
    assert [(o["category"], o["source_key"]) for o in out] == [
        ("hospital", "node:10:hospital"), ("school", "node:10:school"), ("hospital", "node:13:hospital")]
    hosp = out[0]
    assert hosp["name"] == "Роддом N1 эу1" and hosp["attrs"]["consumers_count"] == 4
    assert hosp["attrs"]["node_ids"] == [10, 12]
    assert hosp["attrs"]["consumers"][2] == {"type": "real", "id": 3, "name": "Роддом N1 эу2"}


def test_parse_file_features():
    body = poi.ImportIn(category="school", features=[
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [76.9, 43.2]},
         "properties": {"Наименование": "Н-ТЕСТ  школа 1", "Адрес": "ул. Вымышленная, 1", "id": 7}},
        {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[76, 43], [78, 43], [78, 45], [76, 45], [76, 43]]]},
         "properties": {"name": "Н-ТЕСТ больница", "category": "Больницы"}},
        {"type": "Feature", "geometry": None, "properties": {"name": "без точки"}},
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": [500, 43]}, "properties": {}},
    ])
    rows, notes = poi.parse_features(body)
    assert [(r["category"], r["name"], r["source_key"]) for r in rows] == [
        ("school", "Н-ТЕСТ школа 1", "school:7"), ("hospital", "Н-ТЕСТ больница", "hospital:1")]
    assert rows[0]["address"] == "ул. Вымышленная, 1" and rows[1]["lon"] == 77.0 and rows[1]["lat"] == 44.0
    assert notes == ["нет точки или неверные координаты: 2"]
    assert poi.outside_extent(rows, [76.8, 43.1, 77.1, 43.6]) == 0
    assert poi.outside_extent([{"lon": 43.2, "lat": 76.9}], [76.8, 43.1, 77.1, 43.4]) == 1  # широта и долгота наоборот
    with pytest.raises(poi.PoiError):
        poi.parse_features(poi.ImportIn(category="bank", features=[{"geometry": None}]))
    no_cat, _ = poi.parse_features(poi.ImportIn(features=[{"geometry": {"type": "Point", "coordinates": [1, 2]}}]))
    assert no_cat == []


def test_overpass_query_and_parse():
    q = poi.overpass_query([76.8, 43.1, 77.1, 43.4])
    assert "(43.10000,76.80000,43.40000,77.10000)" in q and "out center tags" in q and "kindergarten" in q
    rows = poi.parse_overpass({"elements": [
        {"type": "node", "id": 1, "lat": 43.2, "lon": 76.9,
         "tags": {"amenity": "school", "name": "School", "name:ru": "Школа", "addr:street": "Абая", "addr:housenumber": "1"}},
        {"type": "way", "id": 2, "center": {"lat": 43.3, "lon": 76.95}, "tags": {"amenity": "doctors", "name": "Врач"}},
        {"type": "node", "id": 3, "lat": 43.2, "lon": 76.9, "tags": {"amenity": "bank"}},
    ]})
    assert [(r["category"], r["name"], r["source_key"], r["address"]) for r in rows] == [
        ("school", "Школа", "node/1", "Абая 1"), ("clinic", "Врач", "way/2", None)]


def test_select_spec_near_poi_validated_described_and_in_sql():
    spec = ns.validate(ns.SelectSpec(target="lines", near_poi=ns.NearPoi(categories=["school", "kindergarten"], meters=500)))
    assert spec.near_poi.categories == ["school", "kindergarten"]
    assert "в 500 м от школ и детских садов" in ns.describe(spec, {})
    everything = ns.validate(ns.SelectSpec(near_poi=ns.NearPoi(meters=300)))
    assert everything.near_poi.categories == list(poi.CATEGORIES)
    assert "в 300 м от социальных объектов" in ns.describe(everything, {})
    with pytest.raises(ns.SelectError):
        ns.validate(ns.SelectSpec(near_poi=ns.NearPoi(categories=["bank"], meters=300)))

    p = ns._Params()
    sql, _ = asyncio.run(ns._nodes_sql(None, spec, p, None, None, False))
    assert "n.id IN (WITH z AS MATERIALIZED (SELECT ST_Transform(ST_Buffer(p.shape::geography" in sql
    assert "FROM z JOIN nodes t ON t.shape && z.zone AND ST_Intersects(t.shape, z.zone)" in sql
    assert ["school", "kindergarten"] in p.values and 500 in p.values


class FakeConn:
    def __init__(self, rows=None, val=None):
        self.rows, self.val = rows or [], val
        self.calls = []

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self.rows

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return self.val


def test_in_area_and_missing_table():
    assert asyncio.run(poi.in_area(FakeConn(val="tgid_poi"), None)) == []
    assert asyncio.run(poi.in_area(FakeConn(val=None), {"type": "Polygon", "coordinates": []})) == []
    row = {"id": 1, "category": "school", "name": "Н-ТЕСТ школа", "address": None, "source": "consumers",
           "hidden": False, "attrs": '{"consumers_count": 2}', "lon": 76.9, "lat": 43.2}
    out = asyncio.run(poi.in_area(FakeConn(rows=[row], val="tgid_poi"), {"type": "Polygon", "coordinates": []}))
    assert out == [{"id": 1, "category": "school", "category_label": "школа", "name": "Н-ТЕСТ школа", "address": None,
                    "source": "consumers", "hidden": False, "lon": 76.9, "lat": 43.2, "consumers_count": 2}]
