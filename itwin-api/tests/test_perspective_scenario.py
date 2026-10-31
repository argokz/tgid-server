"""Перспективный режим (database/perspective_scenario.py): радиус по данным и распределение прироста по ТУ."""
import pytest

from database import perspective_scenario as ps


def test_quantile_linear():
    assert ps.quantile([], 0.9) is None
    assert ps.quantile([10.0], 0.9) == 10.0
    assert ps.quantile([0.0, 10.0, 20.0, 30.0, 40.0], 0.9) == pytest.approx(36.0)


def test_allocate_parts_and_nodes():
    waiting = [
        {"id": 1, "weight": 2.0, "node": 100, "node_fileid": 7, "dist": 50.0},    # во фрагменте
        {"id": 2, "weight": 1.0, "node": 100, "node_fileid": 7, "dist": 20.0},    # тот же узел
        {"id": 3, "weight": 1.0, "node": 200, "node_fileid": 8, "dist": 30.0},    # другой фрагмент
        {"id": 4, "weight": 3.0, "node": 300, "node_fileid": 7, "dist": 500.0},   # дальше радиуса — новый район
        {"id": 5, "weight": 3.0, "node": None, "node_fileid": None, "dist": None},  # без здания
    ]
    out = ps.allocate(100.0, waiting, radius=120.0, fileid=7)
    assert out["by_node"] == {100: pytest.approx(30.0)}
    assert out["parts"] == {"fragment": 30.0, "other_fragments": 10.0, "new_areas": 30.0, "no_location": 30.0}


def test_allocate_no_weights():
    out = ps.allocate(50.0, [{"id": 1, "weight": 0.0, "node": 1, "node_fileid": 1, "dist": 1.0}], 10.0, 1)
    assert out["by_node"] == {1: 0.0} and out["parts"]["fragment"] == 0.0


def test_scaled_columns_match_isolation_loads():
    # поля, которые масштабируются, — ровно те, из которых изоляция складывает нагрузку потребителя
    from database.outage_simulation import _Q_CONSUMERS

    for col in ps.GEN_COLUMNS + ps.REAL_COLUMNS:
        assert f"c.{col}" in _Q_CONSUMERS, col
