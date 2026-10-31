"""Прогноз аварийности участков теплосети (фаза 5, шаг 1): вероятность повреждения участка в ближайшие H лет.

Данные — журнал повреждений города (defect: участок, дата осмотра, точка) и паспорт участка (heatpipesections).
Признаки участка считаются на дату среза T только по прошлому:

- длина, диаметр, тип прокладки, материал и тип изоляции, вид сети, глубина (tgid_heat_depth);
- возраст на T (перекладка до T, иначе первая прокладка; позже T — не знаем), лет с капремонта до T;
- повреждения участка до T: всего, за 3 года, лет с последнего; повреждения в 50 и 200 м от участка (соседние
  участки той же трассы, коридор) — всего и за 3 года; частота повреждений фрагмента на км.

Метка — повреждение участка в [T, T+H).

Утечки, найденные на Астане и закрытые:
- журнал ведётся по участкам с заполненным паспортом: у 95 % повреждённых участков заполнен материал изоляции, у всех —
  у 21 %, и сам факт заполненности давал ROC-AUC 0,87 — модель училась «участок в журнале», а не риску. Население —
  участки с паспортом не хуже порога: число заполненных полей PASSPORT_FIELDS не меньше, чем у 90 % участков,
  повреждённых до среза обучения (Астана — 6 из 8);
- материал и тип изоляции и состояние участка (pipesectstateid*) обновляют при ремонте после повреждения — в признаки
  не берутся (на Астане изоляция и так ничего не добавляла: 0,920 с ней и без неё).

Проверка — по времени: модель учится на срезе T_train и проверяется на срезе T_test = T_train + H, данных которого
не видела (ROC-AUC, доля повреждений в 10 % участков с наибольшим риском, ориентиры: логистическая регрессия,
«повреждения рядом», длина). Срезы — 1 января; T_test — последний, у которого в окне [T, T+H) не меньше
MIN_EVENTS повреждений (журнал в последние годы бывает неполным). Итоговая модель учится на T_test и даёт риск
на сегодня (срез — дата последней записи журнала).
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional

import numpy as np
import pandas as pd

from database import failure_model as fm

HORIZON_YEARS = 2
MIN_EVENTS = 100
NEAR_RADII_M = (50, 200)
TOP_SHARE = 0.10
GBM_PARAMS = {"rounds": 150, "depth": 3, "lr": 0.05, "subsample_neg": 20000, "min_leaf_hessian": 2.0}
FEATURES: list[tuple[str, str]] = [
    ("len_m", "длина, м"),
    ("dn", "условный диаметр, мм"),
    ("age", "возраст, лет"),
    ("since_rc", "лет с капремонта"),
    ("tt", "тип прокладки"),
    ("nt", "вид сети"),
    ("depth", "глубина верха трубы, м"),
    ("hist_all", "повреждений участка до среза"),
    ("hist_3y", "повреждений участка за 3 года"),
    ("since_last", "лет с последнего повреждения участка"),
    ("near50", "повреждений в 50 м"),
    ("near50_3y", "повреждений в 50 м за 3 года"),
    ("near200", "повреждений в 200 м"),
    ("near200_3y", "повреждений в 200 м за 3 года"),
    ("frag_rate", "повреждений фрагмента на км"),
]
COLS = [c for c, _ in FEATURES]
HISTORY_COLS = ["len_m", "hist_all", "hist_3y", "since_last", "near50", "near50_3y", "near200", "near200_3y",
                "frag_rate"]
PASSPORT_FIELDS = ["dn", "tt", "im", "it", "nt", "dt", "d0", "rc"]
DAMAGED_KEPT = 0.90                # порог заполненности паспорта — как у 90 % повреждённых участков


class ForecastError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


# --- данные --------------------------------------------------------------------------------------

async def load(conn) -> tuple[pd.DataFrame, pd.DataFrame, dict[int, pd.DataFrame]]:
    """Участки с паспортом и глубиной, повреждения с участком и датой, повреждения рядом с участками."""
    lines = pd.DataFrame([dict(r) for r in await conn.fetch("""
        SELECT l.id, l.fileid, ST_Length(ST_Transform(l.shape, 4326)::geography) AS len_m,
               h.diametercondit AS dn, h.firstpicdatehp AS d0, h.lasttransdate AS dt, h.tubingtypeid AS tt,
               h.isolmaterialid AS im, h.isolationtypeid AS it, h.nettype AS nt, h.repairdatecapital AS rc,
               coalesce((hd.depth_start + hd.depth_end) / 2, hd.depth_start, hd.depth_end) AS depth
          FROM linesobj l
          LEFT JOIN LATERAL (SELECT * FROM heatpipesections WHERE lineid = l.id ORDER BY id LIMIT 1) h ON true
          LEFT JOIN tgid_heat_depth hd ON hd.lineid = l.id
         WHERE l.shape IS NOT NULL""")])
    defects = pd.DataFrame([dict(r) for r in await conn.fetch(
        """SELECT id, lineid, data_osmotra::date AS t FROM defect
            WHERE lineid IS NOT NULL AND data_osmotra IS NOT NULL""")], columns=["id", "lineid", "t"])
    srid = await conn.fetchval("SELECT ST_SRID(shape) FROM linesobj WHERE shape IS NOT NULL LIMIT 1")
    near: dict[int, pd.DataFrame] = {}
    for radius in NEAR_RADII_M:
        # радиус зависит только от повреждения (3857 растягивает метры в 1/cos широты) — индекс участков работает
        near[radius] = pd.DataFrame([dict(r) for r in await conn.fetch("""
            WITH d AS (SELECT data_osmotra::date AS t, shape,
                              $1 * CASE WHEN $2 = 3857 THEN 1 / cos(radians(ST_Y(ST_Transform(shape, 4326))))
                                        ELSE 1 END AS r
                         FROM defect WHERE shape IS NOT NULL AND data_osmotra IS NOT NULL)
            SELECT l.id AS line, d.t FROM d JOIN linesobj l ON ST_DWithin(l.shape, d.shape, d.r)""",
            float(radius), srid)], columns=["line", "t"])
    if lines.empty:
        raise ForecastError(422, "В базе нет участков с геометрией")
    for col in ("d0", "dt", "rc"):
        lines[col] = pd.to_datetime(lines[col], errors="coerce")
    lines["fill"] = lines[PASSPORT_FIELDS].notna().sum(axis=1)
    defects["t"] = pd.to_datetime(defects["t"])
    for nd in near.values():
        nd["t"] = pd.to_datetime(nd["t"])
    return lines, defects, near


def features(lines: pd.DataFrame, defects: pd.DataFrame, near: dict[int, pd.DataFrame], cutoff: pd.Timestamp,
             horizon: int = HORIZON_YEARS) -> pd.DataFrame:
    """Признаки участков на срез cutoff только по прошлому и метка — повреждение в [cutoff, cutoff + horizon)."""
    before = defects[defects.t < cutoff]
    covered = lines.loc[lines.id.isin(before.lineid), "fileid"].unique()
    pop = lines[lines.fileid.isin(covered)].copy()
    laid = pop.dt.where(pop.dt < cutoff, pop.d0)
    laid = laid.where(laid < cutoff)
    pop["age"] = (cutoff - laid).dt.days / 365.25
    pop["since_rc"] = ((cutoff - pop.rc).dt.days / 365.25).where(pop.rc < cutoff)
    by_line = before.groupby("lineid")
    pop["hist_all"] = pop.id.map(by_line.size()).fillna(0)
    three = cutoff - pd.DateOffset(years=3)
    pop["hist_3y"] = pop.id.map(before[before.t >= three].groupby("lineid").size()).fillna(0)
    pop["since_last"] = pop.id.map((cutoff - by_line.t.max()).dt.days / 365.25)
    for radius, nd in near.items():
        nb = nd[nd.t < cutoff]
        pop[f"near{radius}"] = pop.id.map(nb.groupby("line").size()).fillna(0)
        pop[f"near{radius}_3y"] = pop.id.map(nb[nb.t >= three].groupby("line").size()).fillna(0)
    km = pop.groupby("fileid").len_m.sum() / 1000
    per_frag = before.merge(lines[["id", "fileid"]], left_on="lineid", right_on="id").groupby("fileid").size()
    pop["frag_rate"] = pop.fileid.map(per_frag / km).fillna(0)
    after = defects[(defects.t >= cutoff) & (defects.t < cutoff + pd.DateOffset(years=horizon))]
    pop["y"] = pop.id.isin(after.lineid).astype(int)
    return pop


def pick_cutoffs(defects: pd.DataFrame, horizon: int = HORIZON_YEARS,
                 min_events: int = MIN_EVENTS) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Срезы проверки (1 января): T_test — последний с полным окном [T, T+H) до последней записи журнала и не
    меньше min_events повреждений в нём; T_train = T_test − H, и в его окне тоже не меньше min_events."""
    if defects.empty:
        raise ForecastError(422, "В журнале повреждений нет записей с участком и датой")
    last = defects.t.max()
    for year in range(last.year - horizon, defects.t.min().year + horizon, -1):
        t_test = pd.Timestamp(year=year, month=1, day=1)
        t_train = pd.Timestamp(year=year - horizon, month=1, day=1)

        def events(t: pd.Timestamp) -> int:
            return int(((defects.t >= t) & (defects.t < t + pd.DateOffset(years=horizon))).sum())

        if t_test + pd.DateOffset(years=horizon) <= last + pd.Timedelta(days=1) and \
                events(t_test) >= min_events and events(t_train) >= min_events and (defects.t < t_train).any():
            return t_train, t_test
    raise ForecastError(422, f"Мало истории: нужно два окна по {horizon} г. с {min_events}+ повреждениями")


def passport_threshold(lines: pd.DataFrame, defects: pd.DataFrame, before: pd.Timestamp) -> int:
    """Порог заполненности паспорта: не меньше, чем у DAMAGED_KEPT участков, повреждённых до среза before."""
    damaged = lines.loc[lines.id.isin(defects.loc[defects.t < before, "lineid"]), "fill"]
    if damaged.empty:
        return 0
    return int(np.floor(np.quantile(damaged, 1 - DAMAGED_KEPT)))


# --- обучение и проверка ------------------------------------------------------------------------

def _x(df: pd.DataFrame) -> np.ndarray:
    return df[COLS].to_numpy(dtype=float)


def evaluate(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, Any]:
    """Модель на срезе train, проверка на test: AUC, доля повреждений в верхних 10 % риска, ориентиры."""
    y_test = test.y.to_numpy()
    model = fm.gbm_fit(_x(train), train.y.to_numpy(), **GBM_PARAMS)
    p = fm.gbm_predict(model, _x(test))
    logit = fm.logit_predict(fm.logit_fit(_x(train), train.y.to_numpy(), l2=10.0), _x(test))
    hist = fm.gbm_predict(fm.gbm_fit(train[HISTORY_COLS].to_numpy(float), train.y.to_numpy(), **GBM_PARAMS),
                          test[HISTORY_COLS].to_numpy(float))
    top = np.argsort(-p)[: max(1, int(len(p) * TOP_SHARE))]
    baselines = {c: _round(fm.auc(y_test, test[c].fillna(-1).to_numpy())) for c in ("near200", "hist_all", "len_m")}
    return {
        "auc": _round(fm.auc(y_test, p)), "auc_logit": _round(fm.auc(y_test, logit)),
        "auc_history_only": _round(fm.auc(y_test, hist)), "baselines_auc": baselines,
        "top_share": TOP_SHARE, "top_capture": _round(float(y_test[top].sum() / max(y_test.sum(), 1))),
        "train": {"lines": len(train), "events": int(train.y.sum())},
        "test": {"lines": len(test), "events": int(y_test.sum())},
    }


def _round(v: Optional[float], digits: int = 3) -> Optional[float]:
    return None if v is None else round(float(v), digits)


def fit_and_score(lines, defects, near, horizon: int = HORIZON_YEARS) -> dict[str, Any]:
    """Проверка по времени, итоговая модель на последнем полном срезе, риск участков на сегодня."""
    t_train, t_test = pick_cutoffs(defects, horizon)
    threshold = passport_threshold(lines, defects, t_train)
    damaged_ids = lines.id.isin(defects.lineid)
    population = {"passport_fields": PASSPORT_FIELDS, "min_filled": threshold,
                  "lines": int((lines.fill >= threshold).sum()), "lines_all": len(lines),
                  "damaged_kept": _round(float((lines.loc[damaged_ids, "fill"] >= threshold).mean()))}
    lines = lines[lines.fill >= threshold]
    train, test = features(lines, defects, near, t_train, horizon), features(lines, defects, near, t_test, horizon)
    metrics = {**evaluate(train, test), "population_rule": population}
    final = fm.gbm_fit(_x(test), test.y.to_numpy(), **GBM_PARAMS)
    now = defects.t.max().normalize() + pd.Timedelta(days=1)
    current = features(lines, defects, near, now, horizon)
    prob = fm.gbm_predict(final, _x(current))
    imp = final.importance / max(final.importance.sum(), 1e-12)
    importance = sorted(({"feature": c, "label": label, "share": round(float(v), 3)}
                         for (c, label), v in zip(FEATURES, imp)), key=lambda x: -x["share"])
    rank = pd.Series(prob).rank(pct=True, method="max").to_numpy()
    risk = pd.DataFrame({"lineid": current.id.to_numpy(), "prob": prob, "rank_pct": rank,
                         "hist_all": current.hist_all.to_numpy(), "near200": current.near200.to_numpy(),
                         "age": current.age.to_numpy(), "len_m": current.len_m.to_numpy()})
    return {"cutoffs": {"train": t_train.date().isoformat(), "test": t_test.date().isoformat(),
                        "final": t_test.date().isoformat(), "now": now.date().isoformat()},
            "horizon_years": horizon, "metrics": metrics, "importance": importance,
            "population": len(current), "expected_events": round(float(prob.sum()), 1), "risk": risk}


# --- база ----------------------------------------------------------------------------------------

async def run(conn, *, user: str, horizon: int = HORIZON_YEARS) -> dict[str, Any]:
    """Обучить, проверить и записать риск участков (tgid_failure_run / tgid_failure_risk)."""
    t0 = time.perf_counter()
    lines, defects, near = await load(conn)
    result = await asyncio.to_thread(fit_and_score, lines, defects, near, horizon)
    risk = result.pop("risk")
    took = round(time.perf_counter() - t0, 1)
    async with conn.transaction():
        run_id = await conn.fetchval(
            """INSERT INTO tgid_failure_run (horizon_years, cutoffs, metrics, importance, population, expected_events,
                                             took_s, created_by)
               VALUES ($1, $2::jsonb, $3::jsonb, $4::jsonb, $5, $6, $7, $8) RETURNING id""",
            horizon, json.dumps(result["cutoffs"]), json.dumps(result["metrics"]), json.dumps(result["importance"]),
            result["population"], result["expected_events"], took, user)
        await conn.copy_records_to_table(
            "tgid_failure_risk", columns=["run_id", "lineid", "prob", "rank_pct", "hist_all", "near200", "age", "len_m"],
            records=[(run_id, int(r.lineid), float(r.prob), float(r.rank_pct), int(r.hist_all), int(r.near200),
                      None if pd.isna(r.age) else float(r.age), float(r.len_m)) for r in risk.itertuples()])
    return {"id": run_id, **result, "took_s": took}


def _run_row(r) -> dict[str, Any]:
    return {"id": r["id"], "horizon_years": r["horizon_years"], "cutoffs": json.loads(r["cutoffs"]),
            "metrics": json.loads(r["metrics"]), "importance": json.loads(r["importance"]),
            "population": r["population"], "expected_events": r["expected_events"], "took_s": r["took_s"],
            "created_by": r["created_by"], "created_at": r["created_at"].isoformat()}


async def list_runs(conn, limit: int = 20) -> list[dict[str, Any]]:
    return [_run_row(r) for r in await conn.fetch("SELECT * FROM tgid_failure_run ORDER BY id DESC LIMIT $1", limit)]


async def top_risk(conn, run_id: int, limit: int = 200, fileid: Optional[int] = None) -> dict[str, Any]:
    """Участки с наибольшим риском: вероятность, место в рейтинге, фрагмент, диаметр, история, геометрия."""
    if await conn.fetchval("SELECT 1 FROM tgid_failure_run WHERE id = $1", run_id) is None:
        raise ForecastError(404, "Расчёт прогноза не найден")
    rows = await conn.fetch(
        """SELECT r.lineid, r.prob, r.rank_pct, r.hist_all, r.near200, r.age, r.len_m, l.fileid, f.name AS fragment,
                  h.diametercondit AS dn, ST_AsGeoJSON(ST_Transform(l.shape, 4326), 7) AS geom
             FROM tgid_failure_risk r JOIN linesobj l ON l.id = r.lineid
             LEFT JOIN fragments f ON f.id = l.fileid
             LEFT JOIN LATERAL (SELECT diametercondit FROM heatpipesections WHERE lineid = l.id ORDER BY id LIMIT 1) h
                    ON true
            WHERE r.run_id = $1 AND ($3::int IS NULL OR l.fileid = $3)
            ORDER BY r.prob DESC LIMIT $2""", run_id, limit, fileid)
    items = [{k: r[k] for k in ("lineid", "prob", "rank_pct", "hist_all", "near200", "age", "len_m", "fileid",
                                "fragment", "dn")} for r in rows]
    geo = [{"type": "Feature", "geometry": json.loads(r["geom"]),
                  "properties": {"lineid": r["lineid"], "prob": r["prob"], "rank_pct": r["rank_pct"]}}
                 for r in rows if r["geom"]]
    return {"run_id": run_id, "items": items, "geojson": {"type": "FeatureCollection", "features": geo}}
