"""Перспективный прирост тепловой нагрузки на 5–15 лет (фаза 5) по реестру технических условий на подключение.

Схеме теплоснабжения нужны перспективные балансы: какая нагрузка добавится к источникам по годам. В ТГИД есть
реестр ТУ (tehnicheskie_usloviya: дата выдачи, акт допуска — подключён, аннулирование, прирост нагрузки, источник).
Прирост по годам — из самих данных, без нормативов, двумя способами, каждый с проверкой на прошлом:

**Основной — тренд подключений:** средний прирост по актам допуска за TREND_YEARS полных лет до границы полноты
реестра, по источникам — в долях этих подключений. На Алматы проверка (тренд 2014–2018 → 2019–2023) точнее способа
по выданным ТУ: реализация ТУ упала с 50–70 % нагрузки (выданы в 2012–2015) до 5–27 % (2016–2023), 40–60 %
аннулируют массово и поздно — модель по срокам этого заранее не видит.

**Верхняя оценка — по выданным ТУ:**

- **полнота реестра** — акты допуска вносят не всегда: год, с которого актов вдвое меньше обычного (медиана пяти
  предыдущих лет) и так до конца, — граница наблюдения (Алматы: 14 и 18 актов в 2024–2025 против ~105 в год). Акты
  с датой позже сегодняшней — ошибка ввода, такие ТУ не учитываются;
- **сроки подключения** — дискретная выживаемость по годам с выдачи по последним HAZARD_WINDOW годам до границы,
  с весом по нагрузке (крупные комплексы подключаются реже мелких, а прогнозируется нагрузка): h(k) = нагрузка ТУ,
  подключившихся на k-м году / нагрузка ждавших в начале k-го года; аннулированные выбывают в год аннулирования;
- **выданные ТУ** (не подключены и не аннулированы) — ожидаемое подключение в году y: S·h(k), k — возраст ТУ;
- **ТУ, которые ещё выдадут** — средний прирост выданных за ISSUE_YEARS полных лет, с теми же сроками.

Прирост — поле prirost_nagruzki (для реконструкции — прибавка к существующей нагрузке), но не больше полной
нагрузки ТУ: в обоих полях встречаются ошибки единиц (дом на 5 216 Гкал/ч при приросте 0,52; центр с приростом
16 113 при полной 1,6). Повторные записи одного ТУ (объект, прирост, источник, дата выдачи) считаются один раз.
Проверка — на прошлом: всё то же по данным до границы минус BACKTEST_YEARS, прогноз подключений против актов.
Снос и отключения не учитываются.
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date
from typing import Any, Optional

import asyncpg

MAX_LAG = 15            # лет с выдачи ТУ, дальше подключений не ждём
HAZARD_WINDOW = 6       # сроки подключения — по стольким последним годам наблюдения (поведение меняется)
ISSUE_YEARS = 5         # средний ежегодный выпуск ТУ — по стольким последним полным годам
TREND_YEARS = 5         # тренд подключений — по стольким последним полным годам с полными актами
BACKTEST_YEARS = 5
COMPLETE_SHARE = 0.5    # год с актами меньше этой доли от медианы пяти предыдущих — реестр актов неполон
HORIZONS = (5, 10, 15)
NO_SOURCE = "источник не указан"


class PerspectiveError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def years_between(a: date, b: date) -> int:
    """Полных лет от a до b."""
    return b.year - a.year - ((b.month, b.day) < (a.month, a.day))


def add_years(d: date, n: int) -> date:
    try:
        return d.replace(year=d.year + n)
    except ValueError:                       # 29 февраля
        return d.replace(year=d.year + n, day=28)


def increment(prirost: Optional[float], total: Optional[float]) -> Optional[float]:
    """Прирост нагрузки ТУ: поле прироста, но не больше полной нагрузки (ошибка единиц в одном из полей)."""
    if prirost is None:
        return total
    if total is not None and total > 0 and prirost > total:
        return total
    return prirost


def clean(rows: list[dict[str, Any]], today: date) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """ТУ, пригодные для расчёта: дата выдачи, прирост > 0, акт не раньше выдачи и не позже сегодня, без повторных
    записей. Отброшенные — по причинам."""
    out, dropped = [], defaultdict(int)
    seen: set[tuple] = set()
    for r in sorted(rows, key=lambda r: (r["act"] is None, r["id"])):     # из повторов остаётся запись с актом
        r = {**r, "increment": increment(r.get("prirost"), r.get("total"))}
        key = (" ".join((r.get("name") or "").lower().split()), round(r["increment"] or 0, 4),
               (r["label"] or "").strip(), r["issued"])
        if r["issued"] is None or r["issued"] > today:
            dropped["нет даты выдачи"] += 1
        elif not r["increment"] or r["increment"] <= 0:
            dropped["нет прироста нагрузки"] += 1
        elif r["act"] is not None and r["act"] < r["issued"]:
            dropped["акт допуска раньше выдачи"] += 1
        elif r["act"] is not None and r["act"] > today:
            dropped["акт допуска в будущем"] += 1
        elif key in seen:
            dropped["повторная запись ТУ"] += 1
        else:
            seen.add(key)
            out.append({**r, "label": (r["label"] or "").strip() or NO_SOURCE})
    return out, dict(dropped)


def acts_complete_until(rows: list[dict[str, Any]], today: date) -> date:
    """Граница полноты актов допуска: 1 января первого года, с которого и до конца актов меньше COMPLETE_SHARE от
    медианы пяти предыдущих лет. Без провала — начало текущего года."""
    counts: dict[int, int] = defaultdict(int)
    for r in rows:
        if r["act"] is not None:
            counts[r["act"].year] += 1
    end = today.year
    for y in range(today.year - 1, min(counts, default=today.year) + 5, -1):
        base = statistics.median(counts.get(y - i, 0) for i in range(1, 6))
        if base and counts.get(y, 0) < COMPLETE_SHARE * base:
            end = y
        else:
            break
    return date(end, 1, 1)


def hazards(rows: list[dict[str, Any]], cutoff: date, window: int = HAZARD_WINDOW) -> dict[str, list[float]]:
    """По годам с выдачи k = 0…MAX_LAG: доля нагрузки подключившихся (connect) и аннулированных (annul) ТУ среди
    ждавших в начале года. Считаются только годы ожидания, начавшиеся в последние window лет до среза, и события до среза."""
    start = date(cutoff.year - window, 1, 1)
    at_risk = [0.0] * (MAX_LAG + 1)
    conn = [0.0] * (MAX_LAG + 1)
    ann = [0.0] * (MAX_LAG + 1)
    for r in rows:
        if r["issued"] >= cutoff:
            continue
        w = r["increment"]
        end_lag, event = years_between(r["issued"], cutoff), None
        if r["act"] is not None and r["act"] < cutoff:
            end_lag, event = years_between(r["issued"], r["act"]), "act"
        elif r["annulled"] is not None and r["annulled"] < cutoff:
            end_lag, event = years_between(r["issued"], r["annulled"]), "ann"
        for k in range(min(end_lag, MAX_LAG) + 1):
            if k == end_lag and event is None:
                break                                          # год ожидания не закончен к срезу
            if add_years(r["issued"], k) < start:
                continue
            at_risk[k] += w
            if k == end_lag and event:
                (conn if event == "act" else ann)[k] += w
    return {"connect": [conn[k] / at_risk[k] if at_risk[k] else 0.0 for k in range(MAX_LAG + 1)],
            "annul": [ann[k] / at_risk[k] if at_risk[k] else 0.0 for k in range(MAX_LAG + 1)],
            "at_risk": [round(v, 1) for v in at_risk]}


def connect_curve(h: dict[str, list[float]], age: int, years: int) -> list[float]:
    """Вероятность подключения ТУ возраста age (полных лет, ещё ждёт) в каждом из следующих years лет."""
    alive, out = 1.0, []
    for i in range(years):
        k = age + i
        if k > MAX_LAG:
            out.append(0.0)
            continue
        out.append(alive * h["connect"][k])
        alive *= max(0.0, 1.0 - h["connect"][k] - h["annul"][k])
    return out


def issue_rate(rows: list[dict[str, Any]], before_year: int) -> tuple[float, dict[str, float]]:
    """Средний прирост выданных ТУ в год за ISSUE_YEARS полных лет до before_year и доли источников в нём."""
    recent = [r for r in rows if before_year - ISSUE_YEARS <= r["issued"].year < before_year]
    total = sum(r["increment"] for r in recent)
    shares: dict[str, float] = defaultdict(float)
    for r in recent:
        shares[r["label"]] += r["increment"] / total if total else 0.0
    return total / ISSUE_YEARS, dict(shares)


def forecast(rows: list[dict[str, Any]], cutoff: date, known_until: date, years: int,
             h: dict[str, list[float]]) -> dict[str, Any]:
    """Ожидаемый прирост подключённой нагрузки по годам с года среза (подключения известны до cutoff, выдачи и
    аннулирования — до known_until): выданные ТУ и ТУ, которые ещё выдадут после known_until."""
    by_label: dict[str, list[float]] = defaultdict(lambda: [0.0] * years)
    issued_part = [0.0] * years
    waiting = 0
    for r in rows:
        if r["issued"] >= known_until:
            continue
        if r["act"] is not None and r["act"] < cutoff:
            continue
        if r["annulled"] is not None and r["annulled"] < known_until:
            continue
        waiting += 1
        offset = max(0, r["issued"].year - cutoff.year)        # выданные после среза начинают ждать позже
        age = years_between(r["issued"], cutoff) if r["issued"] < cutoff else 0
        for i, p in enumerate(connect_curve(h, age, years - offset)):
            by_label[r["label"]][offset + i] += p * r["increment"]
            issued_part[offset + i] += p * r["increment"]
    rate, shares = issue_rate(rows, known_until.year)
    future = [0.0] * years
    curve0 = connect_curve(h, 0, years)
    for start in range(known_until.year - cutoff.year, years):
        for i in range(start, years):
            future[i] += rate * curve0[i - start]
    for label, s in shares.items():
        for i in range(years):
            by_label[label][i] += s * future[i]
    return {"years": [cutoff.year + i for i in range(years)], "issued": issued_part, "future": future,
            "by_label": dict(by_label), "waiting": waiting, "issue_rate": rate}


def actual_connected(rows: list[dict[str, Any]], cutoff: date, years: int) -> list[float]:
    """Фактически подключённый прирост (акты допуска) по годам после среза."""
    out = [0.0] * years
    for r in rows:
        if r["act"] is not None and r["act"] >= cutoff:
            i = r["act"].year - cutoff.year
            if 0 <= i < years:
                out[i] += r["increment"]
    return out


def trend(rows: list[dict[str, Any]], until: date) -> tuple[float, dict[str, float]]:
    """Средний подключённый прирост в год (акты допуска за TREND_YEARS лет до until) и доли источников в нём."""
    start = date(until.year - TREND_YEARS, 1, 1)
    recent = [r for r in rows if r["act"] is not None and start <= r["act"] < until]
    total = sum(r["increment"] for r in recent)
    shares: dict[str, float] = defaultdict(float)
    for r in recent:
        shares[r["label"]] += r["increment"] / total if total else 0.0
    return total / TREND_YEARS, dict(shares)


def check(predicted: list[float], actual: list[float], cutoff: date) -> dict[str, Any]:
    total_p, total_a = sum(predicted), sum(actual)
    return {"cutoff": cutoff.isoformat(), "years": [cutoff.year + i for i in range(len(actual))],
            "predicted": [round(v, 1) for v in predicted], "actual": [round(v, 1) for v in actual],
            "predicted_total": round(total_p, 1), "actual_total": round(total_a, 1),
            "error_share": round((total_p - total_a) / total_a, 3) if total_a else None}


def trend_backtest(rows: list[dict[str, Any]], complete: date) -> Optional[dict[str, Any]]:
    """Тренд за TREND_YEARS лет до среза (граница полноты минус BACKTEST_YEARS) против актов после среза."""
    cutoff = date(complete.year - BACKTEST_YEARS, 1, 1)
    rate, _ = trend(rows, cutoff)
    if not rate:
        return None
    return check([rate] * BACKTEST_YEARS, actual_connected(rows, cutoff, BACKTEST_YEARS), cutoff)


def backtest(rows: list[dict[str, Any]], complete: date) -> Optional[dict[str, Any]]:
    """Всё по данным до среза (граница полноты минус BACKTEST_YEARS) — прогноз подключений против актов."""
    cutoff = date(complete.year - BACKTEST_YEARS, 1, 1)
    past = [r for r in rows if r["issued"] < cutoff]
    if not past:
        return None
    # срез: будущего не знаем — ни актов, ни аннулирований, ни выдач после него
    blind = [{**r, "act": r["act"] if r["act"] and r["act"] < cutoff else None,
              "annulled": r["annulled"] if r["annulled"] and r["annulled"] < cutoff else None} for r in past]
    f = forecast(blind, cutoff, cutoff, BACKTEST_YEARS, hazards(blind, cutoff))
    predicted = [a + b for a, b in zip(f["issued"], f["future"])]
    return check(predicted, actual_connected(rows, cutoff, BACKTEST_YEARS), cutoff)


def cumulative(values: list[float]) -> list[float]:
    out, acc = [], 0.0
    for v in values:
        acc += v
        out.append(round(acc, 1))
    return out


# --- база ----------------------------------------------------------------------------------------

async def load_rows(conn) -> list[dict[str, Any]]:
    try:
        rows = await conn.fetch(
            """SELECT id, data_vydachi_tu AS issued, data_vydachi_akta_dopuska AS act,
                      data_annulirovaniya AS annulled, prirost_nagruzki::float8 AS prirost,
                      teplovye_potoki__gkal_ch::float8 AS total, istochnik AS label, naimenovanie_obekta AS name
                 FROM tehnicheskie_usloviya""")
    except asyncpg.UndefinedTableError as exc:
        raise PerspectiveError(422, "В базе нет реестра технических условий") from exc
    return [dict(r) for r in rows]


async def perspective(conn, *, horizon: int = 15, today: Optional[date] = None) -> dict[str, Any]:
    if not 1 <= horizon <= MAX_LAG:
        raise PerspectiveError(422, f"Горизонт — от 1 до {MAX_LAG} лет")
    today = today or date.today()
    raw = await load_rows(conn)
    if not raw:
        raise PerspectiveError(422, "Реестр технических условий пуст — прирост нагрузки не из чего считать")
    rows, dropped = clean(raw, today)
    if not rows:
        raise PerspectiveError(422, "В реестре ТУ нет записей с датой выдачи и приростом нагрузки")
    complete = acts_complete_until(rows, today)
    this_year = date(today.year, 1, 1)
    lag_years = this_year.year - complete.year            # годы между границей полноты и текущим годом
    h = hazards(rows, complete)
    f = forecast(rows, complete, this_year, lag_years + horizon, h)
    total = [a + b for a, b in zip(f["issued"], f["future"])]
    upper = cumulative(total[lag_years:])
    rate, shares = trend(rows, complete)
    cum = cumulative([rate] * horizon)
    by_source = sorted(({"label": label, "share": round(share, 3), "cumulative": cumulative([rate * share] * horizon)}
                        for label, share in shares.items()), key=lambda s: -s["share"])
    waiting = [r for r in rows if (r["act"] is None or r["act"] >= complete)
               and (r["annulled"] is None or r["annulled"] >= this_year)]
    acts_by_year: dict[int, int] = defaultdict(int)
    for r in rows:
        if r["act"] is not None:
            acts_by_year[r["act"].year] += 1
    return {
        "today": today.isoformat(), "horizon": horizon, "years": f["years"][lag_years:],
        "registry": {"rows": len(raw), "used": len(rows), "dropped": dropped,
                     "connected": sum(1 for r in rows if r["act"] is not None and r["act"] < complete),
                     "annulled": sum(1 for r in rows if r["annulled"] is not None and r["act"] is None),
                     "waiting": f["waiting"]},
        "acts_complete_until": complete.isoformat(),
        "acts_by_year": {str(y): n for y, n in sorted(acts_by_year.items()) if y >= complete.year - 5},
        # между границей полноты и текущим годом подключения шли, но актов в реестре нет — по тренду
        "unrecorded": round(rate * lag_years, 1), "unrecorded_years": f["years"][:lag_years],
        "trend_rate": round(rate, 1), "trend_years": [complete.year - TREND_YEARS, complete.year - 1],
        "cumulative": cum,
        "milestones": {str(y): cum[y - 1] for y in HORIZONS if y <= horizon},
        "by_source": by_source,
        "trend_backtest": trend_backtest(rows, complete),
        "upper": {"cumulative": upper, "milestones": {str(y): upper[y - 1] for y in HORIZONS if y <= horizon},
                  "issued_part": [round(v, 1) for v in f["issued"][lag_years:]],
                  "future_part": [round(v, 1) for v in f["future"][lag_years:]],
                  "issue_rate": round(f["issue_rate"], 1),
                  "connect_by_lag": [round(v, 3) for v in h["connect"]],
                  "annul_by_lag": [round(v, 3) for v in h["annul"]]},
        "largest_waiting": [{"id": r["id"], "name": r["name"], "label": r["label"],
                             "increment": round(r["increment"], 3), "issued": r["issued"].isoformat()}
                            for r in sorted(waiting, key=lambda r: -r["increment"])[:10]],
        "upper_backtest": backtest(rows, complete),
    }
