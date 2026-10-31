"""Теплосеть в 3D (database/network3d.py): проверка области, пары П/О одной трубой, разбор WKT."""
import pytest

from database import network3d as n3


def test_check_bbox():
    n3.check_bbox((76.9, 43.2, 77.0, 43.3))
    with pytest.raises(n3.Network3dError, match="приблизьте"):
        n3.check_bbox((76.0, 43.0, 77.0, 44.0))
    with pytest.raises(n3.Network3dError, match="перепутаны"):
        n3.check_bbox((77.0, 43.0, 76.9, 43.1))


def test_merge_pairs_supply_return_one_pipe():
    rows = [
        {"id": 1, "fileid": 1, "dn": 300.0, "d0": None, "d1": None, "coords": "1,2,3,4"},
        {"id": 2, "fileid": 1, "dn": 400.0, "d0": 1.5, "d1": 1.7, "coords": "1,2,3,4"},
        {"id": 3, "fileid": 1, "dn": 100.0, "d0": 2.0, "d1": 2.0, "coords": "5,6,7,8"},
    ]
    out = {x["id"]: x for x in n3.merge_pairs(rows)}
    assert set(out) == {1, 3}
    assert out[1]["pipes"] == 2 and out[1]["dn"] == 400.0 and (out[1]["d0"], out[1]["d1"]) == (1.5, 1.7)
    assert out[3]["pipes"] == 1


def test_coords_from_wkt():
    assert n3._coords("LINESTRING(76.1 43.2,76.3 43.4)") == [76.1, 43.2, 76.3, 43.4]
    assert n3._coords("MULTILINESTRING((1 2,3 4),(5 6,7 8))") == [1, 2, 3, 4, 5, 6, 7, 8]
    assert n3._coords(None) == []


def test_chamber_size_units_by_magnitude():
    from database.network3d import chamber_size_m

    assert chamber_size_m(1.8) == 1.8          # метры
    assert chamber_size_m(262) == 2.62         # сантиметры
    assert chamber_size_m(2400) == 2.4         # миллиметры — как подписано в десктопе
    assert chamber_size_m(0.14) is None        # не размер камеры
    assert chamber_size_m(0) is None and chamber_size_m(None) is None
    assert chamber_size_m(90000) is None       # 90 м


def test_merge_pairs_keeps_largest_outer_diameter():
    rows = [{"id": 1, "dn": 500.0, "de": 530.0, "d0": None, "d1": None, "coords": "1,2,3,4"},
            {"id": 2, "dn": 500.0, "de": 529.0, "d0": 1.0, "d1": 1.5, "coords": "1,2,3,4"}]
    (pipe,) = n3.merge_pairs(rows)
    assert pipe["de"] == 530.0 and pipe["d0"] == 1.0 and pipe["pipes"] == 2
