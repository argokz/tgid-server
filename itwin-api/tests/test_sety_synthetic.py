"""Юнит-тесты расчётного движка sety на малой синтетической сети - без БД и без сети.

Граф собирается прямо в тесте в том виде, в каком его строит sety/read_gid.py:
узел - кортеж (id, po), po = 1 подача / 2 обратка; атрибуты узла typ, po, name, externalCodeID,
fileID, id, geoMarkTopTube, у источника p_zn (заданный напор), у потребителя G (отбор, т/ч:
+ на подаче, - на обратке); ветвь - typ, S (сопротивление, м/(т/ч)^2), po, у регулятора давления
nodeID/przu (узел импульса), Z (уставка, м), r1/r2 (границы S), delta (допуск, м).

Ограничения (движок не меняется, он синхронизируется с версиями автора):
- узлы без ist0 (источник не назначен) - тогда solve_G не пересчитывает потребителей по
  consumption.py и не идёт в check_ist3; тепловой расчёт (calc_teplo) печатает «нет источников
  тепла» и выходит - проверяется только гидравлика;
- потребители - обычные узлы с заданным отбором G, не realConsumers/generalizedConsumers
  (их отбор считает consumption.py по данным из БД);
- sety/read_gid.py импортирует соседний check_ec_hs.py без пакета, поэтому каталог sety
  добавляется в sys.path (так же, как при запуске w.py из этого каталога);
- старая модель регуляторов (-rd_old) при недостижимой уставке не доходит до границы [r1, r2]
  за config.args.iter проходов, поэтому для неё проверяется только достижимая уставка.
"""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pytest

SETY = Path(__file__).resolve().parents[1] / "sety"
if str(SETY) not in sys.path:
    sys.path.insert(0, str(SETY))

from sety import config  # noqa: E402
from sety import calc_nagr as calc_nagr_mod  # noqa: E402
from sety import sprav  # noqa: E402
from sety import w_calc  # noqa: E402
from sety.teplo import y_ut  # noqa: E402

SOURCE_HEAD_SUPPLY = 60.0   # м, заданный напор на подаче источника
SOURCE_HEAD_RETURN = 20.0   # м, заданный напор на обратке источника
Q_A = 12.5                  # т/ч, отбор потребителя A
Q_B = 7.5                   # т/ч, отбор потребителя B
TOL = 1e-6


# ------------------------------------------------------------------ config.args

def _init_args(*extra: str):
    """config.args как при запуске `python w.py -server ... -fileID 1 [extra]` (без обращения к БД)."""
    argv = sys.argv
    sys.argv = ["sety", "-server", "x", "-database", "x", "-user", "x", "-fileID", "1", *extra]
    try:
        return config.init()
    finally:
        sys.argv = argv


@pytest.fixture
def engine_args():
    """Подменяет глобальный config.args на время теста и возвращает прежний после."""
    saved = getattr(config, "args", None)
    args = _init_args()
    yield args
    if saved is None:
        del config.args
    else:
        config.args = saved


# ------------------------------------------------------------------ синтетический граф

def _add_node(graph: nx.MultiDiGraph, node_id: int, po: int, **attrs) -> None:
    graph.add_node((node_id, po), typ=attrs.pop("typ", "nodes"), po=po, name=f"n{node_id}",
               externalCodeID=node_id, fileID=1, id=node_id, geoMarkTopTube=0.0, **attrs)


def _add_pipe(G: nx.MultiDiGraph, n1: int, n2: int, po: int, S: float) -> None:
    key = G.number_of_edges() + 1
    G.add_edge((n1, po), (n2, po), key=key, typ="heatPipeSections", S=S, po=po)


def _tree_network(consumer_typ: str = "nodes") -> nx.MultiDiGraph:
    """Источник 1 -> 2 -> 3 -> потребитель A (4); 2 -> потребитель B (5); обратка зеркально.

    Сопротивления подачи: 1-2 0.01, 2-3 0.02, 3-4 0.03, 2-5 0.05; обратки те же.
    """
    G = nx.MultiDiGraph()
    _add_node(G, 1, 1, p_zn=SOURCE_HEAD_SUPPLY)
    _add_node(G, 1, 2, p_zn=SOURCE_HEAD_RETURN)
    for node_id in (2, 3):
        _add_node(G, node_id, 1)
        _add_node(G, node_id, 2)
    _add_node(G, 4, 1, typ=consumer_typ, G=Q_A, Gout=Q_A)
    _add_node(G, 4, 2, typ=consumer_typ, G=-Q_A, Gout=-Q_A)
    _add_node(G, 5, 1, typ=consumer_typ, G=Q_B, Gout=Q_B)
    _add_node(G, 5, 2, typ=consumer_typ, G=-Q_B, Gout=-Q_B)

    for n1, n2, S in ((1, 2, 0.01), (2, 3, 0.02), (3, 4, 0.03), (2, 5, 0.05)):
        _add_pipe(G, n1, n2, 1, S)
        _add_pipe(G, n2, n1, 2, S)

    return G


def _solve(G: nx.MultiDiGraph) -> np.ndarray:
    w_calc.set_G_num(G)
    root, n_n, n_l, n_zn = w_calc.init_root(G)
    result = w_calc.solve_G(G, root, n_n, n_l, n_zn)
    assert result is not None, "solve_G не нашёл решения"
    assert np.all(np.isfinite(result))
    return result


def _flow(G, root, n1, n2, po) -> float:
    (key,) = G[(n1, po)][(n2, po)]
    return float(root[G.edges[(n1, po), (n2, po), key]["num"]])


def _head(G, root, node_id, po) -> float:
    return float(root[G.nodes[(node_id, po)]["num"]])


# ------------------------------------------------------------------ 1. гидравлика

def test_tree_network_flows_and_heads(engine_args):
    """Расходы по участкам складываются из отборов потребителей, напор падает по потоку на S*G^2."""
    G = _tree_network()
    root = _solve(G)

    expected = {(1, 2): Q_A + Q_B, (2, 3): Q_A, (3, 4): Q_A, (2, 5): Q_B}
    for (n1, n2), q in expected.items():
        assert _flow(G, root, n1, n2, 1) == pytest.approx(q, abs=TOL), f"подача {n1}-{n2}"
        assert _flow(G, root, n2, n1, 2) == pytest.approx(q, abs=TOL), f"обратка {n2}-{n1}"

    assert _head(G, root, 1, 1) == pytest.approx(SOURCE_HEAD_SUPPLY, abs=TOL)
    assert _head(G, root, 1, 2) == pytest.approx(SOURCE_HEAD_RETURN, abs=TOL)

    # падение напора по направлению потока положительно и равно S*G^2 (ветвь - труба без арматуры)
    for n1, n2, key, e in G.edges(keys=True, data=True):
        q = root[e["num"]]
        drop = root[G.nodes[n1]["num"]] - root[G.nodes[n2]["num"]]
        assert q > 0
        assert drop > 0
        assert drop == pytest.approx(e["S"] * q * q, rel=1e-6)

    # на потребителе напор подачи выше обратки - располагаемый напор положителен
    for consumer in (4, 5):
        assert _head(G, root, consumer, 1) > _head(G, root, consumer, 2)

    # баланс: источник отдаёт в подачу ровно столько, сколько забирают потребители
    assert _head(G, root, 4, 1) == pytest.approx(
        SOURCE_HEAD_SUPPLY - 0.01 * (Q_A + Q_B) ** 2 - 0.02 * Q_A**2 - 0.03 * Q_A**2, abs=1e-6)


# ------------------------------------------------------------------ 2. регулятор давления

RD_R1 = 0.001   # полностью открыт
RD_R2 = 0.2     # полностью закрыт
RD_DELTA = 0.05  # м
RD_PIPE_S = 0.02


def _rd_network(setpoint: float) -> nx.MultiDiGraph:
    """Источник (1) -> РД -> узел импульса (2) -> потребитель (3); обратка 3 -> 2 -> 1."""
    G = nx.MultiDiGraph()
    _add_node(G, 1, 1, p_zn=SOURCE_HEAD_SUPPLY)
    _add_node(G, 1, 2, p_zn=SOURCE_HEAD_RETURN)
    _add_node(G, 2, 1)
    _add_node(G, 2, 2)
    _add_node(G, 3, 1, G=Q_A, Gout=Q_A)
    _add_node(G, 3, 2, G=-Q_A, Gout=-Q_A)

    G.add_edge((1, 1), (2, 1), key=1, typ="pressRegulators", S=RD_R1, po=1,
               nodeID=2, przu=1, Z=setpoint, r1=RD_R1, r2=RD_R2, delta=RD_DELTA)
    _add_pipe(G, 2, 3, 1, RD_PIPE_S)
    _add_pipe(G, 3, 2, 2, RD_PIPE_S)
    _add_pipe(G, 2, 1, 2, 0.01)
    return G


@pytest.mark.parametrize("model_flags", [(), ("-rd_old",)], ids=["rd_new", "rd_old"])
def test_pressure_regulator_holds_setpoint(engine_args, model_flags):
    """Достижимая уставка: напор в узле импульса равен уставке в пределах допуска, S внутри [r1, r2]."""
    config.args = _init_args(*model_flags)
    setpoint = 50.0
    G = _rd_network(setpoint)
    root = _solve(G)

    head = _head(G, root, 2, 1)
    assert abs(head - setpoint) <= RD_DELTA, head
    assert _flow(G, root, 1, 2, 1) == pytest.approx(Q_A, abs=TOL)

    # требуемое сопротивление (60-50)/12.5^2 = 0.064 внутри диапазона регулятора
    S = (SOURCE_HEAD_SUPPLY - head) / Q_A**2
    assert RD_R1 < S < RD_R2
    assert not G.graph.get("rd_msgs"), G.graph.get("rd_msgs")


@pytest.mark.parametrize("setpoint, bound, text", [
    (70.0, RD_R1, "полностью открыт"),
    (10.0, RD_R2, "полностью закрыт"),
], ids=["above_source", "below_reachable"])
def test_pressure_regulator_unreachable_setpoint(engine_args, setpoint, bound, text):
    """Недостижимая уставка (новая модель w_rd2): регулятор фиксируется на границе r1/r2 и даёт сообщение."""
    G = _rd_network(setpoint)
    root = _solve(G)

    assert G.edges[(1, 1), (2, 1), 1]["S"] == pytest.approx(bound)
    head = _head(G, root, 2, 1)
    assert head == pytest.approx(SOURCE_HEAD_SUPPLY - bound * Q_A**2, rel=1e-6)
    assert abs(head - setpoint) > RD_DELTA

    msgs = G.graph.get("rd_msgs") or {}
    assert len(msgs) == 1, msgs
    (msg,) = msgs.values()
    assert "напор не обеспечивается" in msg
    assert text in msg
    assert f"Задано {setpoint:.2f} м" in msg


# ------------------------------------------------------------------ 3. нагрузки по участкам

LOADS_A = {"Qot0": 100.0, "Qvent0": 20.0, "Qgvz0": 30.0, "Qgvp0": 5.0, "Qgvo0": 7.0}
LOADS_B = {"Qot0": 40.0, "Qvent0": 0.0, "Qgvz0": 10.0, "Qgvp0": 2.0, "Qgvo0": 1.0}
NAGR_BY_KEY = {"b102": "Qot0", "b103": "Qvent0", "b104": "Qgvz0", "b105": "Qgvp0", "b106": "Qgvo0"}


def test_calc_nagr_total_is_sum_of_kinds(engine_args):
    """b101 = b102 + ... + b106 на каждом участке; на магистрали - сумма нагрузок обоих потребителей."""
    G = _tree_network(consumer_typ="generalizedConsumers")
    G.nodes[(4, 1)].update(LOADS_A)
    G.nodes[(5, 1)].update(LOADS_B)

    # расходы известны (см. test_tree_network_flows_and_heads) - гидравлика не нужна
    w_calc.set_G_num(G)
    x = np.zeros(G.number_of_nodes() + G.number_of_edges())
    flows = {(1, 2): Q_A + Q_B, (2, 3): Q_A, (3, 4): Q_A, (2, 5): Q_B}
    for n1, n2, key, e in G.edges(keys=True, data=True):
        pair = (n1[0], n2[0]) if n1[1] == 1 else (n2[0], n1[0])
        x[e["num"]] = flows[pair]

    calc_nagr_mod.calc_nagr_all(G, x)

    for n1, n2, key, e in G.edges(keys=True, data=True):
        assert all(k in e for k in calc_nagr_mod.NAGR_KEYS), (n1, n2, e)
        assert e["b101"] == pytest.approx(sum(e[k] for k in NAGR_BY_KEY), abs=1e-6), (n1, n2)

    def loads_of(n1, n2, po):
        (key,) = G[(n1, po)][(n2, po)]
        return G.edges[(n1, po), (n2, po), key]

    for po, (trunk, branch_a, branch_b) in ((1, ((1, 2), (3, 4), (2, 5))), (2, ((2, 1), (4, 3), (5, 2)))):
        for b_key, q_key in NAGR_BY_KEY.items():
            assert loads_of(*trunk, po)[b_key] == pytest.approx(LOADS_A[q_key] + LOADS_B[q_key], abs=1e-6)
            assert loads_of(*branch_a, po)[b_key] == pytest.approx(LOADS_A[q_key], abs=1e-6)
            assert loads_of(*branch_b, po)[b_key] == pytest.approx(LOADS_B[q_key], abs=1e-6)
        assert loads_of(*trunk, po)["b101"] == pytest.approx(sum(LOADS_A.values()) + sum(LOADS_B.values()), abs=1e-6)


# ------------------------------------------------------------------ 4. диаметр больше максимального в справочнике 39

@pytest.fixture
def sprav_39(monkeypatch):
    """Справочник 39 из sety/sprav/*.csv (без БД); после теста словарь очищается."""
    monkeypatch.setattr(sprav, "get_gidr_path", lambda: str(SETY))
    sprav.map_s39.clear()
    sprav.read_csv_s39("39_normy_teplovyh_poter", sprav.map_s39)
    assert sprav.map_s39, "справочник 39 не прочитан"
    yield sprav.map_s39
    sprav.map_s39.clear()
    y_ut.warned_s39.clear()


def test_diameter_above_sprav_39_max_does_not_crash(engine_args, sprav_39, capsys):
    """REVIEW_2026-10-18.md п. 1.13: диаметр больше максимального в справочнике 39 раньше ронял расчёт
    (d1 == d2 -> деление на ноль -> UnboundLocalError в norma -> exit(1)); теперь норма экстраполируется
    по последнему отрезку с однократным предупреждением."""
    year, typ_pr, po = 1, 1, 1
    d_max = max(sprav_39[(year, "К")])
    big = d_max + 600.0

    def q(d):
        return y_ut.get_q_new(year, typ_pr, d, d, po, 150.0, 70.0, -30.0, 5.0, 0)

    q_max = q(d_max)
    q_big = q(big)
    q_big_again = q(big)

    assert np.isfinite(q_big) and q_big > q_max > 0
    assert q_big == q_big_again

    out = capsys.readouterr().out
    assert out.count(f"Диаметр {big} больше максимального в справочнике 39") == 1, out
