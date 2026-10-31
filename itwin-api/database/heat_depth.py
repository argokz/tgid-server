"""Глубина заложения теплосети из отметок узлов (фаза 4, шаг 6).

Поле паспорта heatpipesections.pipelinelayingdepth в базах городов не заполнено (в Алматы 1,0 м у 99,9 % —
значение по умолчанию), а отметки узлов есть: nodes.geomarknodearea — отметка земли, nodes.geomarktoptube — отметка
верха трубы. Глубина в узле = земля − верх трубы (минус — труба над землёй, надземная прокладка). Отметка считается
заполненной, если она в пределах отметок города (1-й…99-й процентиль ± 100 м — отсекает координаты и сантиметры,
записанные в поле отметки) и разность не нулевая (ноль — отметку земли скопировали в отметку трубы).

Участок: глубины у начала и конца геометрии — по его узлам (source nodes / node); оба конца неизвестны — оценка по
ближайшим узлам сети с глубиной, до MAX_HOPS участков (source neighbors, hops). Точность оценки проверяется на узлах
с известной глубиной: глубина узла восстанавливается по соседям без него (holdout).

Пересчёт — refresh (таблица tgid_heat_depth целиком); сближения и раскопки (utility_conflicts) берут глубину отсюда,
в точке участка — интерполяцией между концами.
"""
from __future__ import annotations

import json
import random
import statistics
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Optional

MIN_DIFF_M = 0.05          # меньше — отметка трубы не заполнена (копия отметки земли)
MAX_DEPTH_M = 10.0
MAX_ABOVE_M = 10.0         # надземная прокладка — до 10 м над землёй
ELEVATION_MARGIN_M = 100.0
MAX_HOPS = 2               # через 3 участка ошибка 1,2–2,5 м (holdout Алматы и Астаны) — не оценивать
HOLDOUT_SAMPLE = 5000
LOCK_KEY = 0x7467_6864     # «tghd»: один пересчёт на базу


def plausible_range(q01: Optional[float], q99: Optional[float]) -> Optional[tuple[float, float]]:
    """Допустимые отметки города: 1-й…99-й процентиль отметок земли ± ELEVATION_MARGIN_M."""
    if q01 is None or q99 is None:
        return None
    return q01 - ELEVATION_MARGIN_M, q99 + ELEVATION_MARGIN_M


def node_depth(ground: Optional[float], top: Optional[float], bounds: Optional[tuple[float, float]]) -> Optional[float]:
    """Глубина до верха трубы в узле, м; None — отметки не заполнены или не похожи на отметки города."""
    if bounds is None or ground is None or top is None:
        return None
    lo, hi = bounds
    if not (lo <= ground <= hi and lo <= top <= hi):
        return None
    d = ground - top
    if abs(d) < MIN_DIFF_M or not -MAX_ABOVE_M <= d <= MAX_DEPTH_M:
        return None
    return round(d, 3)


def _adjacency(lines: list[tuple[int, int, int, bool]]) -> dict[int, set[int]]:
    adj: dict[int, set[int]] = defaultdict(set)
    for _, a, b, _ in lines:
        if a is not None and b is not None and a != b:
            adj[a].add(b)
            adj[b].add(a)
    return adj


def nearest_depth(start: set[int], adj: dict[int, set[int]], depth: dict[int, float],
                  skip: Optional[int] = None) -> Optional[tuple[float, int]]:
    """Медиана глубин ближайших по сети узлов с глубиной (не дальше MAX_HOPS участков) → (глубина, шагов).
    Медиана, а не среднее: рядом бывают подземные и надземные участки, их среднее — бессмысленная «почти ноль»."""
    seen = set(start)
    level = list(start)
    for hops in range(1, MAX_HOPS + 1):
        nxt = []
        for n in level:
            for m in adj.get(n, ()):
                if m not in seen:
                    seen.add(m)
                    nxt.append(m)
        found = [depth[m] for m in nxt if m in depth and m != skip]
        if found:
            return statistics.median(found), hops
        level = nxt
        if not level:
            break
    return None


def line_depths(lines: list[tuple[int, int, int, bool]], depth: dict[int, float]) -> list[tuple]:
    """Участки (id, узел 1, узел 2, узел 1 — у начала геометрии) → строки tgid_heat_depth:
    (lineid, глубина у начала, у конца, источник, шагов)."""
    adj = _adjacency(lines)
    out = []
    for lid, a, b, a_at_start in lines:
        da, db = depth.get(a), depth.get(b)
        if da is not None or db is not None:
            start, end = (da, db) if a_at_start else (db, da)
            out.append((lid, start, end, "nodes" if da is not None and db is not None else "node", None))
            continue
        est = nearest_depth({n for n in (a, b) if n is not None}, adj, depth)
        if est is not None:
            d = round(est[0], 3)
            out.append((lid, d, d, "neighbors", est[1]))
    return out


def holdout(lines: list[tuple[int, int, int, bool]], depth: dict[int, float], sample: int = HOLDOUT_SAMPLE,
            seed: int = 1) -> dict[str, Any]:
    """Точность оценки по соседям: у случайных узлов с известной глубиной она восстанавливается без них самих;
    итог и по числу шагов до найденных соседей."""
    adj = _adjacency(lines)
    nodes = sorted(n for n in depth if n in adj)
    random.Random(seed).shuffle(nodes)
    errors: list[tuple[float, int]] = []
    for n in nodes[:sample]:
        est = nearest_depth({n}, adj, depth, skip=n)
        if est is not None:
            errors.append((abs(est[0] - depth[n]), est[1]))
    if not errors:
        return {"checked": 0}

    def stats(errs: list[float]) -> dict[str, Any]:
        return {"checked": len(errs), "mae_m": round(statistics.fmean(errs), 3),
                "median_m": round(statistics.median(errs), 3),
                "within_0_5_m": round(sum(e <= 0.5 for e in errs) / len(errs), 3)}

    by_hops = {str(h): stats([e for e, k in errors if k == h]) for h in sorted({k for _, k in errors})}
    return {**stats([e for e, _ in errors]), "by_hops": by_hops}


async def refresh(conn, user: Optional[str] = None) -> dict[str, Any]:
    """Пересчитать tgid_heat_depth целиком из отметок узлов; отчёт: сколько узлов и участков с глубиной, точность."""
    t0 = time.perf_counter()
    async with conn.transaction():
        if not await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", LOCK_KEY):
            return {"busy": True}
        q = await conn.fetchrow(
            """SELECT percentile_cont(0.01) WITHIN GROUP (ORDER BY geomarknodearea) AS q01,
                      percentile_cont(0.99) WITHIN GROUP (ORDER BY geomarknodearea) AS q99
                 FROM nodes WHERE geomarknodearea > 0""")
        bounds = plausible_range(q["q01"], q["q99"])
        depth: dict[int, float] = {}
        for r in await conn.fetch("SELECT id, geomarknodearea AS g, geomarktoptube AS t FROM nodes"):
            d = node_depth(r["g"], r["t"], bounds)
            if d is not None:
                depth[r["id"]] = d
        lines = [(r["id"], r["n1"], r["n2"], r["n1_start"]) for r in await conn.fetch(
            """SELECT l.id, l.nodeid1 AS n1, l.nodeid2 AS n2,
                      coalesce(ST_Distance(ST_StartPoint(l.shape), a.shape)
                               <= ST_Distance(ST_StartPoint(l.shape), b.shape), true) AS n1_start
                 FROM linesobj l
                 LEFT JOIN nodes a ON a.id = l.nodeid1
                 LEFT JOIN nodes b ON b.id = l.nodeid2
                WHERE l.shape IS NOT NULL""")]
        rows = line_depths(lines, depth)
        await conn.execute("TRUNCATE tgid_heat_depth")
        now = datetime.now(timezone.utc)
        await conn.copy_records_to_table(
            "tgid_heat_depth", records=[(*r, now) for r in rows],
            columns=["lineid", "depth_start", "depth_end", "source", "hops", "updated_at"])
    by_source: dict[str, int] = defaultdict(int)
    for r in rows:
        by_source[r[3]] += 1
    report = {"bounds_m": bounds and [round(b, 1) for b in bounds], "nodes_with_depth": len(depth),
              "lines": len(lines), "lines_by_source": dict(by_source), "lines_unknown": len(lines) - len(rows),
              "holdout": holdout(lines, depth), "took_s": round(time.perf_counter() - t0, 2)}
    await conn.execute("INSERT INTO tgid_heat_depth_run (report, created_by) VALUES ($1::jsonb, $2)",
                       json.dumps(report), user)
    return {"busy": False, **report}


async def status(conn) -> dict[str, Any]:
    """Последний пересчёт: участки по источнику глубины и точность оценки по соседям."""
    row = await conn.fetchrow("SELECT report, created_by, created_at FROM tgid_heat_depth_run ORDER BY id DESC LIMIT 1")
    if row is None:
        return {"report": None, "updated_at": None}
    return {"report": json.loads(row["report"]), "updated_by": row["created_by"],
            "updated_at": row["created_at"].isoformat()}


_ensured: set[str] = set()


async def ensure(conn) -> None:
    """Глубины ещё не считались в этой базе — посчитать (первое обращение к сближениям или раскопкам). Раз на базу
    за процесс: в городе без отметок таблица остаётся пустой, и пересчёт при каждом запросе не нужен."""
    db = await conn.fetchval("SELECT current_database()")
    if db in _ensured:
        return
    if await conn.fetchval("SELECT NOT EXISTS (SELECT 1 FROM tgid_heat_depth)"):
        await refresh(conn)
    _ensured.add(db)
