"""Общая карта коммуникаций (database/utility_conflicts.py): расстояние в свету, вердикт, зона раскопок."""

import pytest

from database import utility_conflicts as uc


def test_clearance_subtracts_outer_radii():
    assert uc.clearance_m(2.0, 300, 530) == pytest.approx(2.0 - 0.415)
    assert uc.clearance_m(2.0, None, None) == 2.0


def test_verdict():
    assert uc.verdict(True, 0.0, 100, 100, 1.5) == "crossing"
    assert uc.verdict(False, 1.8, 300, 530, 1.5) == "close"      # 1,8 − 0,415 = 1,385 < 1,5
    assert uc.verdict(False, 2.0, 300, 530, 1.5) is None          # 1,585 ≥ 1,5
    assert uc.verdict(False, 0.5, 100, 100, None) is None         # нормы нет — сближение не оценивается
    assert uc.verdict(True, 0.0, 100, 100, None) == "crossing"


def test_pad_units():
    assert uc.pad_units(4, 9998) == 10
    assert uc.pad_units(111, 4326) == pytest.approx(0.0025)


def test_dig_geometry():
    point = {"type": "Point", "coordinates": [76.94, 43.25]}
    assert uc.dig_geometry(point) == point
    poly = {"type": "Polygon", "coordinates": [[[76.94, 43.25], [76.941, 43.25], [76.941, 43.251], [76.94, 43.25]]]}
    assert uc.dig_geometry({**poly, "properties": {}})["type"] == "Polygon"
    for bad in ({"type": "MultiPolygon", "coordinates": []}, {"type": "Point", "coordinates": [500, 43]},
                {"type": "LineString", "coordinates": [[76.0, 43.0], [77.0, 43.0]]},   # 80 км
                {"type": "Point", "coordinates": []}, "строка"):
        with pytest.raises(uc.UtilityError):
            uc.dig_geometry(bad)
