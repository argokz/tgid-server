"""Модели прогноза аварийности (фаза 5) на numpy — без scikit-learn и бустинговых библиотек в среде API.

- gbm_fit / gbm_predict — градиентный бустинг деревьев на гистограммах признаков (как HistGradientBoosting):
  логистическая функция потерь, признаки разбиты на ≤ MAX_BINS квантильных корзин, пропуск — своя корзина,
  деревья глубины depth, L2-регуляризация листьев, минимальный вес листа; важность признака — суммарный выигрыш.
- logit_fit / logit_predict — логистическая регрессия с L2 (scipy L-BFGS) — простой ориентир.
- auc — ROC-AUC (Манна — Уитни, с учётом совпадающих оценок).

Признаки — числовая матрица float (NaN — пропуск); категориальные признаки кодируются числами заранее, у деревьев
порядок кодов не мешает при достаточной глубине.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

MAX_BINS = 32


def auc(y: np.ndarray, score: np.ndarray) -> Optional[float]:
    """ROC-AUC: доля пар (положительный, отрицательный), где положительный выше; None — один класс."""
    y = np.asarray(y).astype(bool)
    n_pos, n_neg = int(y.sum()), int((~y).sum())
    if n_pos == 0 or n_neg == 0:
        return None
    order = np.argsort(score, kind="mergesort")
    s = np.asarray(score)[order]
    ranks = np.empty(len(s))
    i = 0
    while i < len(s):                      # средний ранг у совпадающих оценок
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        ranks[i:j + 1] = (i + j) / 2 + 1
        i = j + 1
    r = np.empty(len(s))
    r[order] = ranks
    return float((r[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


# --- гистограммы признаков ----------------------------------------------------------------------

@dataclass
class Binner:
    edges: list[np.ndarray] = field(default_factory=list)

    def fit(self, x: np.ndarray) -> "Binner":
        self.edges = []
        for j in range(x.shape[1]):
            col = x[:, j]
            col = col[~np.isnan(col)]
            if len(col) == 0:
                self.edges.append(np.array([]))
                continue
            qs = np.unique(np.quantile(col, np.linspace(0, 1, MAX_BINS + 1)[1:-1]))
            self.edges.append(qs)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        """Номера корзин: 0…len(edges); пропуск — MAX_BINS (своя корзина)."""
        out = np.empty(x.shape, dtype=np.int16)
        for j, e in enumerate(self.edges):
            col = x[:, j]
            b = np.searchsorted(e, col, side="right").astype(np.int16)
            b[np.isnan(col)] = MAX_BINS
            out[:, j] = b
        return out


# --- деревья ------------------------------------------------------------------------------------

@dataclass
class Tree:
    # узел: (признак, порог-корзина: ≤ — влево, корзина пропуска влево?, левый, правый) или лист (-1, значение)
    nodes: list[tuple] = field(default_factory=list)

    def predict(self, xb: np.ndarray) -> np.ndarray:
        out = np.zeros(len(xb))
        idx = np.arange(len(xb))
        stack = [(0, idx)]
        while stack:
            k, rows = stack.pop()
            node = self.nodes[k]
            if node[0] == -1:
                out[rows] = node[1]
                continue
            j, thr, nan_left, left, right = node
            v = xb[rows, j]
            go_left = np.where(v == MAX_BINS, nan_left, v <= thr)
            stack.append((left, rows[go_left]))
            stack.append((right, rows[~go_left]))
        return out


def _best_split(xb: np.ndarray, g: np.ndarray, h: np.ndarray, lam: float, min_h: float):
    """Лучший разрез по гистограммам: (выигрыш, признак, порог, пропуск влево)."""
    G, H = g.sum(), h.sum()
    parent = G * G / (H + lam)
    best = (0.0, -1, 0, True)
    for j in range(xb.shape[1]):
        gb = np.bincount(xb[:, j], weights=g, minlength=MAX_BINS + 1)
        hb = np.bincount(xb[:, j], weights=h, minlength=MAX_BINS + 1)
        g_nan, h_nan = gb[MAX_BINS], hb[MAX_BINS]
        gl, hl = np.cumsum(gb[:MAX_BINS]), np.cumsum(hb[:MAX_BINS])
        for nan_left in (True, False):
            GL = gl + (g_nan if nan_left else 0.0)
            HL = hl + (h_nan if nan_left else 0.0)
            GR, HR = G - GL, H - HL
            ok = (HL >= min_h) & (HR >= min_h)
            if not ok.any():
                continue
            gain = np.where(ok, GL * GL / (HL + lam) + GR * GR / (HR + lam) - parent, -np.inf)
            t = int(np.argmax(gain))
            if gain[t] > best[0]:
                best = (float(gain[t]), j, t, nan_left)
    return best


def _grow(xb, g, h, depth, lam, min_h, importance) -> Tree:
    tree = Tree()

    def build(rows: np.ndarray, d: int) -> int:
        k = len(tree.nodes)
        tree.nodes.append(None)
        gs, hs = g[rows], h[rows]
        leaf = -gs.sum() / (hs.sum() + lam)
        if d == depth or len(rows) < 2:
            tree.nodes[k] = (-1, leaf)
            return k
        gain, j, thr, nan_left = _best_split(xb[rows], gs, hs, lam, min_h)
        if j < 0:
            tree.nodes[k] = (-1, leaf)
            return k
        importance[j] += gain
        v = xb[rows, j]
        go_left = np.where(v == MAX_BINS, nan_left, v <= thr)
        left = build(rows[go_left], d + 1)
        right = build(rows[~go_left], d + 1)
        tree.nodes[k] = (j, thr, nan_left, left, right)
        return k

    build(np.arange(len(xb)), 0)
    return tree


@dataclass
class GBM:
    binner: Binner
    base: float
    trees: list[Tree]
    lr: float
    importance: np.ndarray


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


def gbm_fit(x: np.ndarray, y: np.ndarray, *, rounds: int = 150, depth: int = 3, lr: float = 0.1, lam: float = 1.0,
            min_leaf_hessian: float = 1.0, subsample_neg: Optional[int] = None, seed: int = 1) -> GBM:
    """Бустинг на логистических потерях. subsample_neg — для редких событий: на каждом шаге берётся не больше
    стольких отрицательных примеров (все положительные остаются), ускоряет обучение на сотнях тысяч участков."""
    y = np.asarray(y, dtype=float)
    binner = Binner().fit(x)
    xb = binner.transform(x)
    p0 = min(max(y.mean(), 1e-6), 1 - 1e-6)
    base = float(np.log(p0 / (1 - p0)))
    f = np.full(len(y), base)
    rng = np.random.default_rng(seed)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    importance = np.zeros(x.shape[1])
    trees = []
    for _ in range(rounds):
        p = _sigmoid(f)
        g, h = p - y, p * (1 - p)
        rows = np.arange(len(y))
        weight = None
        if subsample_neg and len(neg) > subsample_neg:
            pick = rng.choice(neg, subsample_neg, replace=False)
            rows = np.concatenate([pos, pick])
            weight = np.ones(len(rows))
            weight[len(pos):] = len(neg) / subsample_neg   # отрицательные — с весом, суммы не смещаются
        gs, hs = g[rows], h[rows]
        if weight is not None:
            gs, hs = gs * weight, hs * weight
        tree = _grow(xb[rows], gs, hs, depth, lam, min_leaf_hessian, importance)
        trees.append(tree)
        f += lr * tree.predict(xb)
    return GBM(binner, base, trees, lr, importance)


def gbm_predict(model: GBM, x: np.ndarray) -> np.ndarray:
    xb = model.binner.transform(x)
    f = np.full(len(x), model.base)
    for t in model.trees:
        f += model.lr * t.predict(xb)
    return _sigmoid(f)


# --- логистическая регрессия -------------------------------------------------------------------

@dataclass
class Logit:
    mean: np.ndarray
    std: np.ndarray
    coef: np.ndarray
    intercept: float


def _prep(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    z = (np.where(np.isnan(x), mean, x) - mean) / std
    return np.hstack([z, np.isnan(x).astype(float)])          # пропуск — отдельный признак


def logit_fit(x: np.ndarray, y: np.ndarray, *, l2: float = 1.0) -> Logit:
    from scipy.optimize import minimize

    mean = np.nanmean(np.where(np.isnan(x), np.nan, x), axis=0)
    mean = np.where(np.isnan(mean), 0.0, mean)
    std = np.nanstd(x, axis=0)
    std = np.where((std == 0) | np.isnan(std), 1.0, std)
    z = _prep(x, mean, std)
    y = np.asarray(y, dtype=float)

    def loss(w: np.ndarray) -> tuple[float, np.ndarray]:
        b, c = w[0], w[1:]
        f = b + z @ c
        p = _sigmoid(f)
        eps = 1e-12
        val = -np.mean(y * np.log(p + eps) + (1 - y) * np.log(1 - p + eps)) + l2 * np.sum(c * c) / (2 * len(y))
        grad_f = (p - y) / len(y)
        return val, np.concatenate([[grad_f.sum()], z.T @ grad_f + l2 * c / len(y)])

    res = minimize(loss, np.zeros(z.shape[1] + 1), jac=True, method="L-BFGS-B")
    return Logit(mean, std, res.x[1:], float(res.x[0]))


def logit_predict(model: Logit, x: np.ndarray) -> np.ndarray:
    return _sigmoid(model.intercept + _prep(x, model.mean, model.std) @ model.coef)
