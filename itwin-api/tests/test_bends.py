"""Отводы участка по геометрии (database/bends): углы, слияние мелких изломов, классы, mestn."""

import math

from database.bends import BEND_CLASSES, BEND_ITEM_IDS, bend_class, bend_counts, compute_bends, parse_mestn

O = (76.99839, 43.37722)


def at(x: float, y: float) -> tuple[float, float]:
    """Точка в x, y метрах от O (восток, север)."""
    r = 6371008.8
    return (O[0] + math.degrees(x / (r * math.cos(math.radians(O[1])))), O[1] + math.degrees(y / r))


def test_right_angle_and_straight_line():
    bends = compute_bends([at(0, 0), at(10, 0), at(10, 10)])
    assert len(bends) == 1
    assert bends[0]["vertex"] == 1
    assert abs(bends[0]["angle"] - 90) < 0.2
    assert (bends[0]["cls"], bends[0]["count"]) == (90, 1)
    assert compute_bends([at(0, 0), at(10, 0), at(20, 0.5)]) == []  # 2,9° — не отвод


def test_small_vertices_merge_and_angles_classify():
    # излом 45° из двух вершин в 0,2 м друг от друга считается одним отводом
    pts = [at(0, 0), at(10, 0), at(10.2, 0.0), at(10.2 + 7.07, 7.07)]
    bends = compute_bends(pts)
    assert len(bends) == 1 and bends[0]["cls"] == 45
    assert bend_class(20) == (22, 1)
    assert bend_class(33) == (30, 1)
    assert bend_class(70) == (60, 1)
    assert bend_class(100) == (90, 1)
    assert bend_class(170) == (90, 2)


def test_counts_and_defaults_are_bends():
    bends = compute_bends([at(0, 0), at(10, 0), at(10, 10), at(20, 10), at(20, 0)])
    assert bend_counts(bends) == {90: 3}
    for c in BEND_CLASSES.values():
        assert c["default"] in c["options"]
        assert set(c["options"]) <= BEND_ITEM_IDS


def test_parse_mestn_like_desktop():
    assert parse_mestn("15|2|0.3 41|3|0.2 bad 7|x|1") == [(15, 2.0, 0.3), (41, 3.0, 0.2)]
    assert parse_mestn(None) == []
