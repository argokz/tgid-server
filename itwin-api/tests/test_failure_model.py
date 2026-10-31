"""Модели прогноза аварийности на numpy (database/failure_model.py): AUC, бустинг, логистическая регрессия."""

import numpy as np
import pytest

from database import failure_model as fm


def test_auc_known_values_and_ties():
    assert fm.auc(np.array([0, 0, 1, 1]), np.array([0.1, 0.4, 0.35, 0.8])) == 0.75
    assert fm.auc(np.array([0, 1]), np.array([0.5, 0.5])) == 0.5          # совпадение — половина
    assert fm.auc(np.array([1, 1]), np.array([0.1, 0.2])) is None


def _data(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 4))
    # взаимодействие: риск высок, когда x0 > 0 и x1 > 0; x2 — шум; пропуск в x3 — признак риска
    logit = 2.5 * ((x[:, 0] > 0) & (x[:, 1] > 0)) - 2.0
    miss = rng.random(n) < 0.2
    logit = logit + 1.5 * miss
    x[miss, 3] = np.nan
    y = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return x, y


def test_gbm_learns_interaction_and_missing():
    x, y = _data()
    xt, yt = _data(seed=1)
    m = fm.gbm_fit(x, y, rounds=60, depth=3)
    a = fm.auc(yt, fm.gbm_predict(m, xt))
    assert a > 0.78
    assert m.importance[2] < m.importance[0] and m.importance[2] < m.importance[3]  # шум — наименее важен
    lin = fm.logit_predict(fm.logit_fit(x, y), xt)
    assert a > fm.auc(yt, lin)                         # взаимодействие линейная модель не видит


def test_gbm_rare_events_with_negative_subsample():
    rng = np.random.default_rng(3)
    x = rng.normal(size=(20000, 2))
    y = (rng.random(20000) < 1 / (1 + np.exp(-(3 * x[:, 0] - 6)))).astype(int)   # ~1–2 % событий
    m = fm.gbm_fit(x, y, rounds=40, subsample_neg=3000)
    p = fm.gbm_predict(m, x)
    assert fm.auc(y, p) > 0.9
    assert p.mean() == pytest.approx(y.mean(), rel=0.5)   # веса отрицательных — вероятности не смещены сильно


def test_logit_linear_signal():
    rng = np.random.default_rng(5)
    x = rng.normal(size=(3000, 3))
    y = (rng.random(3000) < 1 / (1 + np.exp(-(2 * x[:, 0] - x[:, 1])))).astype(int)
    m = fm.logit_fit(x, y)
    assert m.coef[0] > 0 > m.coef[1]
    assert fm.auc(y, fm.logit_predict(m, x)) > 0.8
