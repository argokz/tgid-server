"""Время прохождения потока по выделенному направлению — gid6 zap.cpp OnTimePr / gid8 zaprosy.cpp onTimePr.

Десктоп идёт по списку узлов пьезометрического маршрута (list_pjezo) и для каждой пары соседних
узлов берёт линию подачи (externalsignlineid 1, 2, 4) и обратки (1, 3, 5), затем:

    подача:  если q·napr·timeP < 0 → timeP = 1e80 (нет движения), иначе timeP += time1·napr
    обратка: если q·napr·timeO > 0 → timeO = 1e80,                  иначе timeO += time1·napr

napr = +1, если линия ориентирована от текущего узла к следующему (nodeid1 → nodeid2), иначе −1;
time1 — ut_out.a11 (мин, sety w_out.py: длина / скорость / 60, всегда ≥ 0; у не-трубопроводов 0);
q — расход из *_out той же линии (ut.sql: ut a13, ns a14, rs a11, bp a13, zd/zd2 a9, dro/any/ok ras).
Итог — |t| в часах/минутах/секундах (getTime), > 1e70 — «Нет движения воды по выбранному маршруту».
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import asyncpg

from database.ut_out_columns import UT_FLOW_TH, UT_LENGTH_M, UT_TRAVEL_MIN

NO_FLOW = 1e80
NO_FLOW_TEXT = "Нет движения воды по выбранному маршруту"

SUPPLY_LINE_SIGNS = (1, 2, 4)
RETURN_LINE_SIGNS = (1, 3, 5)
SUPPLY_OUT_SIGNS = (2, 4)
RETURN_OUT_SIGNS = (3, 5)

# Расход линии по типу элемента — как CASE pod_q/obr_q в gid8 python/wms/sql3/ut.sql
_FLOW_SOURCES = (
    ("ut_out", UT_FLOW_TH),
    ("ns_out", "a14"),
    ("rs_out", "a11"),
    ("bp_out", "a13"),
    ("zd_out", "a9"),
    ("zd2_out", "a9"),
    ("dro_out", "ras"),
    ("any_out", "ras"),
    ("ok_out", "ras"),
)


def format_travel_time(t: float) -> str:
    """gid6 getTime: минуты → «H часов M минут S секунд» (с отбрасыванием дробной части)."""
    if t > 1e70:
        return NO_FLOW_TEXT
    t = abs(t) / 60
    h = int(t)
    m = int((t - h) * 60)
    s = int(((t - h) * 60 - m) * 60)
    return f"{h} часов {m} минут {s} секунд"


def accumulate_travel_time(segments: Sequence[Optional[dict]], supply: bool) -> tuple[float, list[Optional[float]]]:
    """Накопление времени по десктопу. segments — по паре узлов: {"q", "time_min", "napr"} или None
    (линии нет — пара пропускается, как `if (LP)`). Возвращает (итоговый аккумулятор, значения после
    каждого сегмента)."""
    acc = 0.0
    trace: list[Optional[float]] = []
    for seg in segments:
        if seg is not None:
            q = seg.get("q") or 0.0
            napr = seg["napr"]
            check = q * napr * acc
            if (check < 0) if supply else (check > 0):
                acc = NO_FLOW
            else:
                acc += (seg.get("time_min") or 0.0) * napr
        trace.append(acc)
    return acc, trace


def _line_query(line_signs: tuple[int, ...], out_signs: tuple[int, ...]) -> str:
    flow_joins = []
    flow_cols = []
    for i, (table, col) in enumerate(_FLOW_SOURCES):
        flow_joins.append(
            f"LEFT JOIN {table} f{i} ON f{i}.lineid = cand.id AND f{i}.calculationid = c.cid"
            f" AND f{i}.externalsignlineid IN ({', '.join(map(str, out_signs))})"
        )
        flow_cols.append(f"f{i}.{col}")
    return f"""
        WITH pairs AS (
            SELECT p.ord, p.n1, p.n2 FROM unnest($1::int[], $2::int[], $3::int[]) AS p(ord, n1, n2)
        ),
        cand AS (
            SELECT DISTINCT ON (pairs.ord) pairs.ord, pairs.n1, l.id, l.nodeid1, n1.fileid
              FROM pairs
              JOIN linesobj l ON (l.nodeid1 = pairs.n1 AND l.nodeid2 = pairs.n2)
                              OR (l.nodeid1 = pairs.n2 AND l.nodeid2 = pairs.n1)
              JOIN nodes n1 ON n1.id = l.nodeid1
             WHERE COALESCE(l.removed, 0) = 0
               AND l.externalsignlineid IN ({', '.join(map(str, line_signs))})
             ORDER BY pairs.ord, l.id
        )
        SELECT cand.ord, cand.id AS line_id, cand.nodeid1, cand.n1, c.cid AS calculation_id,
               COALESCE({', '.join(flow_cols)})::float AS q,
               f0.{UT_TRAVEL_MIN}::float AS time_min,
               f0.{UT_LENGTH_M}::float AS length_m
          FROM cand
          LEFT JOIN LATERAL (
              SELECT COALESCE($4::int, (SELECT max(id) FROM calculation WHERE fileid = cand.fileid)) AS cid
          ) c ON true
          {' '.join(flow_joins)}
    """


async def _fetch_side(conn, path: list[int], supply: bool, calculation_id: Optional[int]) -> list[Optional[dict]]:
    n = len(path) - 1
    sql = _line_query(SUPPLY_LINE_SIGNS if supply else RETURN_LINE_SIGNS,
                      SUPPLY_OUT_SIGNS if supply else RETURN_OUT_SIGNS)
    rows = await conn.fetch(sql, list(range(n)), path[:-1], path[1:], calculation_id)
    out: list[Optional[dict]] = [None] * n
    for r in rows:
        out[r["ord"]] = {
            "line_id": r["line_id"],
            "napr": 1 if r["nodeid1"] == r["n1"] else -1,
            "q": r["q"],
            "time_min": r["time_min"],
            "length_m": r["length_m"],
            "calculation_id": r["calculation_id"],
        }
    return out


def _side_summary(acc: float, segs: list[Optional[dict]]) -> dict[str, Any]:
    no_flow = acc > 1e70
    used = [s for s in segs if s is not None]
    naprs = {s["napr"] for s in used if (s.get("time_min") or 0) > 0}
    return {
        "total_min": None if no_flow else abs(acc),
        "text": format_travel_time(acc),
        "no_flow": no_flow,
        "lines": len(used),
        "sum_segments_min": sum(s.get("time_min") or 0.0 for s in used),
        "mixed_orientation": len(naprs) > 1,
    }


async def travel_time(conn: asyncpg.Connection, path: list[int],
                      calculation_id: Optional[int] = None) -> dict[str, Any]:
    """path — полный список узлов маршрута (соседние узлы связаны линией)."""
    supply = await _fetch_side(conn, path, True, calculation_id)
    ret = await _fetch_side(conn, path, False, calculation_id)
    acc_p, trace_p = accumulate_travel_time(supply, True)
    acc_o, trace_o = accumulate_travel_time(ret, False)

    labels = {
        r["id"]: r["label"]
        for r in await conn.fetch(
            """SELECT n.id, COALESCE(NULLIF(ec.name, ''), NULLIF(n.externalnodename, ''), n.id::text) AS label
                 FROM nodes n LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
                WHERE n.id = ANY($1::int[])""",
            path,
        )
    }

    def side(seg: Optional[dict], acc: float) -> Optional[dict]:
        if seg is None:
            return None
        return {**seg, "cumulative_min": None if acc > 1e70 else abs(acc)}

    items = []
    for i in range(len(path) - 1):
        items.append({
            "index": i + 1,
            "node1_id": path[i], "node1_label": labels.get(path[i], str(path[i])),
            "node2_id": path[i + 1], "node2_label": labels.get(path[i + 1], str(path[i + 1])),
            "supply": side(supply[i], trace_p[i]),
            "return": side(ret[i], trace_o[i]),
        })

    calc_ids = sorted({s["calculation_id"] for s in supply + ret if s and s["calculation_id"]})
    sp, rs = _side_summary(acc_p, supply), _side_summary(acc_o, ret)
    notes = []
    if not calc_ids:
        notes.append("Для линий маршрута нет расчёта")
    if sp["mixed_orientation"] or rs["mixed_orientation"]:
        notes.append("Линии маршрута ориентированы в разные стороны: как в десктопе, время участка "
                     "суммируется со знаком направления линии (sum_segments_min — простая сумма)")
    return {
        "query": "travel_time",
        "title": "Время прохождения потока",
        "calculation_ids": calc_ids,
        "node_count": len(path),
        "supply": sp,
        "return": rs,
        "count": len(items),
        "items": items,
        "note": "; ".join(notes) or None,
    }
