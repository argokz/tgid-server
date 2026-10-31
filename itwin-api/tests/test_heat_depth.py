"""Глубина теплосети из отметок узлов (database/heat_depth.py): отметки, участки, оценка по соседям, holdout."""

import pytest

from database import heat_depth as hd

B = hd.plausible_range(650.0, 930.0)


def test_node_depth_filters_unfilled_and_garbage():
    assert B == (550.0, 1030.0)
    assert hd.node_depth(820.4, 818.9, B) == 1.5
    assert hd.node_depth(820.0, 820.0, B) is None          # отметку земли скопировали в отметку трубы
    assert hd.node_depth(820.0, 821.2, B) == -1.2          # надземная прокладка
    assert hd.node_depth(876130.0, 818.0, B) is None       # не отметка (координата в поле)
    assert hd.node_depth(820.0, 805.0, B) is None          # 15 м — не глубина теплосети
    assert hd.node_depth(None, 818.0, B) is None
    assert hd.node_depth(820.0, 818.0, None) is None


# цепочка узлов 1-2-3-4-5, глубины известны у 1 (1,0) и 5 (2,0); участки: (id, узел1, узел2, узел1 у начала)
LINES = [(10, 1, 2, True), (11, 2, 3, True), (12, 4, 3, False), (13, 4, 5, True), (14, 6, 7, True)]
DEPTH = {1: 1.0, 5: 2.0}


def test_line_depths_sources_and_orientation():
    rows = {r[0]: r for r in hd.line_depths(LINES, DEPTH)}
    assert rows[10] == (10, 1.0, None, "node", None)
    assert rows[13] == (13, None, 2.0, "node", None)
    # 11 (2-3): соседи через 1 участок — узел 1 (у 2), узел 4 без глубины → среднее найденных на 1-м шаге
    assert rows[11][3] == "neighbors" and rows[11][1] == 1.0 and rows[11][4] == 1
    # 12 (4-3, узел 4 у конца геометрии): ближайшие — 5 через 1 участок от 4
    assert rows[12][3] == "neighbors" and rows[12][1] == rows[12][2] == 2.0
    assert 14 not in rows                                   # отдельный кусок без отметок — глубины нет


def test_line_depth_both_ends_and_reversed_geometry():
    rows = {r[0]: r for r in hd.line_depths([(20, 1, 5, False)], DEPTH)}
    assert rows[20] == (20, 2.0, 1.0, "nodes", None)        # узел 1 у конца геометрии


def test_holdout_estimates_from_neighbors():
    lines = [(i, i, i + 1, True) for i in range(1, 6)]
    depth = {1: 1.0, 2: 1.2, 3: 1.4, 4: 1.6, 5: 1.8, 6: 2.0}
    h = hd.holdout(lines, depth)
    assert h["checked"] == 6 and h["mae_m"] == pytest.approx(0.067, abs=0.001)  # концы ошибаются на 0,2, середина — 0
    assert hd.holdout(lines, {}) == {"checked": 0}
