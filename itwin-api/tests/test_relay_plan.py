"""План перекладок (database/relay_plan.py): расценки, жадный отбор, объекты, сравнение «старые первыми»."""

import pytest

from database import relay_plan as rp
from database.wear import flow_factor, priority

PRICES = [{"dn_max_mm": 100, "price_per_m": 50.0}, {"dn_max_mm": 300, "price_per_m": 120.0},
          {"dn_max_mm": 700, "price_per_m": 300.0}]


def _item(lineid, benefit, cost, fileid=1, n1=None, n2=None, age=None, prob=None):
    return {"lineid": lineid, "benefit": benefit, "cost": cost, "fileid": fileid, "node1": n1, "node2": n2,
            "age": age, "prob": prob if prob is not None else benefit, "len_m": cost * 1000}


def test_price_for_classes():
    assert rp.price_for(80, PRICES) == 50 and rp.price_for(100, PRICES) == 50
    assert rp.price_for(250, PRICES) == 120 and rp.price_for(1000, PRICES) == 300
    assert rp.price_for(None, PRICES) == 120 and rp.price_for(80, []) is None


def test_select_by_benefit_per_cost_within_budget():
    items = [_item(1, 0.5, 2.0), _item(2, 0.3, 0.5), _item(3, 0.2, 0.5), _item(4, 0.9, 5.0), _item(5, 0.0, 0.1)]
    chosen = rp.select(items, 3.2)
    # на единицу стоимости: 2 (0,6), 3 (0,4), 1 (0,25), 4 (0,18); 4 не влезает; польза 0 — не берётся
    assert [x["lineid"] for x in chosen] == [2, 3, 1]
    # постоянные затраты объекта 1,0: 2 (0,3/1,5), 1 (0,5/3), 3 (0,2/1,5) — обрезок 3 теперь после 1
    assert [x["lineid"] for x in rp.select(items, 3.2, overhead=1.0)] == [2, 1, 3]


def test_build_runs_between_branches_with_supply_return_corridor():
    def line(i, n1, n2, dn=100, fileid=1, b=0.1):
        return {**_item(i, b, 0.1, fileid=fileid, n1=n1, n2=n2), "dn": dn}

    items = [
        line(1, 10, 11), line(2, 11, 10),                 # подача и обратка 10–11 — один коридор
        line(3, 11, 12), line(4, 12, 13),                 # 11 и 12 — проходные: трасса 10–13
        line(5, 13, 14), line(6, 13, 15),                 # 13 — развилка: 13–14 и 13–15 — отдельные трассы
        line(7, 15, 16, dn=200),                          # смена диаметра в 15 — граница трассы
        line(8, 16, 17, fileid=2),                        # другой фрагмент
        {**_item(9, 0.5, 0.2), "dn": None},              # без узлов
    ]
    runs = {tuple(sorted(x["lineid"] for x in r["lines"])) for r in rp.build_runs(items)}
    assert runs == {(1, 2, 3, 4), (5,), (6,), (7,), (8,), (9,)}
    r = next(r for r in rp.build_runs(items) if len(r["lines"]) == 4)
    assert r["benefit"] == pytest.approx(0.4) and r["cost"] == pytest.approx(0.4) and r["lineid"] == 1


def test_oldest_first_comparison():
    items = [_item(1, 0.1, 1, age=50), _item(2, 0.8, 1, age=5), _item(3, 0.2, 1, age=None)]
    assert [x["lineid"] for x in rp.oldest_first(items, 2)] == [1, 2]


def test_flow_factor_shared_with_wear():
    assert flow_factor(None) == 1 and flow_factor(500) == 1.25 and flow_factor(-3000) == 1.5
    assert priority(50.0, 1.4, 500) == round(0.5 * 1.4 * 1.25, 4)
