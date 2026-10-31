"""Индекс износа участков и приоритет ремонта (этап 5 ИИ-плана).

Формула износа — экспертная методика десктопа gid6 (gidr/remont_sql/tgid_iznos.sql):
  procent = (срок·0.15 + повреждаемость·0.2 + внешний вид·0.05 + состояние оборудования·0.2
             + категория нарушений·0.1 + внешняя коррозия·0.1 + внутренняя коррозия·0.1
             + состояние конструкций·0.1) × 20,   баллы 1..5, категория 1..5 по 20 %.
Срок: ≤7 лет — 1, ≤15 — 2, <20 — 3, <25 — 4, иначе 5. Повреждаемость (шт./100 м):
<1 — 1, <2 — 2, <4 — 3, <5 — 4, иначе 5.

Отличия от десктопа: строка — участок heatpipesections (в Алматы участков ПТС pipesections нет);
нарушения без участка (lineid) десктоп не считает — здесь они привязываются по месту к ближайшему участку не
дальше DEFECT_SNAP_M и его копиям в других фрагментах (snap_defects): в Астане участок указан у 106 из 1785
нарушений, без привязки 94 % аварий не попадали в повреждаемость;
незаполненные баллы (0/NULL) не считаются «новой трубой»: wear_pct — как в gid6 (нули), а
wear_pct_known нормирован на заполненные факторы, factors_filled показывает полноту данных.
Приоритет ремонта (в десктопе методика не реализована, tgid_iznos_remont.sql с «??»):
  priority = wear_pct_known/100 × (1 + последствия отключения) × (1 + 0.5·min(расход/1000, 1)),
последствия — справочники breakconsumvols, populdamages, infrastrdamages участка.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

# Веса факторов gid6 (сумма 1.0)
WEIGHTS: dict[str, float] = {
    "srok_ball": 0.15,
    "koef_povr_ball": 0.20,
    "vnesniivid": 0.05,
    "sostoborudovania": 0.20,
    "kategorii": 0.10,
    "vnesnkorrozia": 0.10,
    "vnunrenkorrozia": 0.10,
    "sostkonstrukz": 0.10,
}
FACTOR_LABELS: dict[str, str] = {
    "srok_ball": "Срок эксплуатации",
    "koef_povr_ball": "Повреждаемость",
    "vnesniivid": "Внешний вид",
    "sostoborudovania": "Состояние оборудования",
    "kategorii": "Категория нарушений",
    "vnesnkorrozia": "Внешняя коррозия",
    "vnunrenkorrozia": "Внутренняя коррозия",
    "sostkonstrukz": "Состояние конструкций",
}
CATEGORY_LABELS = {1: "до 20 % — хорошее", 2: "20–40 % — удовлетворительное", 3: "40–60 % — требует внимания",
                   4: "60–80 % — предремонтное", 5: "свыше 80 % — критическое"}
DESIGN_LIFE_YEARS = 25


def srok_ball(age_years: Optional[float]) -> Optional[int]:
    if age_years is None:
        return None
    if age_years <= 7:
        return 1
    if age_years <= 15:
        return 2
    if age_years < 20:
        return 3
    if age_years < 25:
        return 4
    return 5


def koef_povr_ball(per_100m: Optional[float]) -> Optional[int]:
    if per_100m is None:
        return None
    if per_100m < 1:
        return 1
    if per_100m < 2:
        return 2
    if per_100m < 4:
        return 3
    if per_100m < 5:
        return 4
    return 5


def wear_percent(scores: dict[str, Optional[int]]) -> tuple[float, Optional[float], int]:
    """(wear_pct как в gid6 — пропуски = 0; wear_pct_known — по заполненным; число заполненных)."""
    total = 0.0
    known_w = 0.0
    filled = 0
    for key, w in WEIGHTS.items():
        s = scores.get(key)
        if s:
            total += w * s
            known_w += w
            filled += 1
    pct = round(total * 20, 2)
    known = round(total / known_w * 20, 2) if known_w > 0 else None
    return pct, known, filled


def category(pct: Optional[float]) -> Optional[int]:
    if pct is None:
        return None
    if pct < 20:
        return 1
    if pct < 40:
        return 2
    if pct < 60:
        return 3
    if pct < 80:
        return 4
    return 5


def consequence(breakconsumvol: Optional[int], populdamage: Optional[int], infrastrdamage: Optional[int]) -> float:
    """Множитель последствий отключения 1..2.4: объём отключаемых потребителей, ущерб людям/инфраструктуре."""
    bcv = min(max(breakconsumvol or 0, 0), 3) / 3
    pop = min(max(populdamage or 0, 0), 4) / 4
    inf = min(max(infrastrdamage or 0, 0), 4) / 4
    return round(1 + 0.6 * bcv + 0.4 * pop + 0.4 * inf, 3)


def priority(wear_known: Optional[float], cons: float, flow_t_h: Optional[float]) -> Optional[float]:
    if wear_known is None:
        return None
    flow_factor = 1 + 0.5 * min(abs(flow_t_h or 0.0) / 1000.0, 1.0)
    return round(wear_known / 100.0 * cons * flow_factor, 4)


# --- выборка исходных данных участков ---

_SOURCE_SQL = """
WITH calc AS (
    SELECT fileid, MAX(id) AS cid FROM calculation WHERE fileid IS NOT NULL GROUP BY fileid
),
defects AS (
    SELECT lineid, COUNT(*)::int AS n FROM defect WHERE lineid IS NOT NULL GROUP BY lineid
),
flows AS (
    -- в ut_out по участку может быть несколько строк (подача/обратка): берём наибольший расход
    SELECT ut.calculationid, ut.lineid, MAX(ABS(ut.a13)) AS flow
      FROM ut_out ut JOIN calc c ON c.cid = ut.calculationid GROUP BY ut.calculationid, ut.lineid
)
SELECT DISTINCT ON (l.id)
       h.id AS hps_id, l.id AS lineid, h.pipesectionid, l.fileid,
       h.pipesectlength AS length_m, h.diametercondit AS diameter,
       h.firstpicdatehp, h.lasttransdate,
       COALESCE(d.n, 0) AS n_defects,
       h.vnesniivid, h.sostoborudovania, h.kategorii, h.vnesnkorrozia, h.vnunrenkorrozia, h.sostkonstrukz,
       h.breakconsumvolid, h.populdamageid, h.infrastrdamageid,
       fl.flow AS flow_t_h
  FROM heatpipesections h
  JOIN linesobj l ON l.id = h.lineid AND l.removed = 0
  LEFT JOIN defects d ON d.lineid = l.id
  LEFT JOIN calc c ON c.fileid = l.fileid
  LEFT JOIN flows fl ON fl.calculationid = c.cid AND fl.lineid = l.id
 WHERE ($1::int[] IS NULL OR l.fileid = ANY($1::int[]))
 ORDER BY l.id, h.pipesectlength DESC NULLS LAST, h.id DESC
"""

DEFECT_SNAP_M = 20.0

# Нарушения без участка → ближайший участок теплосети (KNN по индексу в проекции таблицы, точное расстояние — по
# геодезии) и все его копии с той же геометрией в других фрагментах (версии магистралей «2021–2022», «2023–2024»…
# — одна труба): каждая версия получает свои повреждения. Проверено на 106 нарушениях Астаны с участком в журнале:
# та же труба — 94 (89 %); предпочтение участка с Ду и трубой Т1/Т2 из текста точность снижало (87 %).
_SNAP_SQL = """
SELECT DISTINCT d.id AS defect_id, cp.id AS lineid, cp.fileid,
       ST_Distance(ST_Transform(snap.shape, 4326)::geography, ST_Transform(d.shape, 4326)::geography) AS distance_m
  FROM defect d
  CROSS JOIN LATERAL (
      SELECT l.id, l.shape
        FROM linesobj l
       WHERE coalesce(l.removed, 0) = 0 AND l.internalnodeid IS NULL AND l.shape IS NOT NULL
         AND EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id)
         AND ($1::int[] IS NULL OR l.fileid = ANY($1::int[]))
       ORDER BY l.shape <-> d.shape
       LIMIT 1) snap
  JOIN LATERAL (
      SELECT l2.id, l2.fileid FROM linesobj l2
       WHERE l2.shape && snap.shape AND ST_Equals(l2.shape, snap.shape)
         AND coalesce(l2.removed, 0) = 0 AND l2.internalnodeid IS NULL
         AND EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l2.id)
         AND ($1::int[] IS NULL OR l2.fileid = ANY($1::int[]))) cp ON true
 WHERE d.lineid IS NULL AND d.shape IS NOT NULL
   AND ST_DWithin(ST_Transform(snap.shape, 4326)::geography, ST_Transform(d.shape, 4326)::geography, $2)
"""


async def snap_defects(conn, fragment_ids: Optional[list[int]] = None) -> dict[str, Any]:
    """Нарушения без участка, привязанные по месту: {участок: число} и сколько привязано / не привязано."""
    srids = await conn.fetch(
        """SELECT (SELECT ST_SRID(shape) FROM defect WHERE shape IS NOT NULL LIMIT 1) AS d,
                  (SELECT ST_SRID(shape) FROM linesobj WHERE shape IS NOT NULL LIMIT 1) AS l""")
    unplaced = int(await conn.fetchval(
        "SELECT COUNT(*) FROM defect WHERE lineid IS NULL AND shape IS NOT NULL") or 0)
    if not unplaced or not srids or srids[0]["d"] != srids[0]["l"]:
        # разные проекции у нарушений и участков — KNN-оператор не работает, привязку не делать
        return {"by_line": {}, "snapped": 0, "unplaced": unplaced}
    rows = await conn.fetch(_SNAP_SQL, fragment_ids, DEFECT_SNAP_M)
    by_line: dict[int, int] = {}
    for r in rows:
        by_line[r["lineid"]] = by_line.get(r["lineid"], 0) + 1
    return {"by_line": by_line, "snapped": len({r["defect_id"] for r in rows}), "unplaced": unplaced}


_INSERT_SQL = """
INSERT INTO wear_out (calculationid, lineid, pipesectionid, fileid, age_years, age_source, srok_ball,
                      n_defects, koef_povr, koef_povr_ball, vnesniivid, sostoborudovania, kategorii,
                      vnesnkorrozia, vnunrenkorrozia, sostkonstrukz, factors_filled, wear_pct,
                      wear_pct_known, category, consequence, flow_t_h, priority)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
"""


def assess_row(r: dict[str, Any], at: datetime) -> dict[str, Any]:
    """Одна строка wear_out из строки _SOURCE_SQL."""
    laid = r.get("lasttransdate") or r.get("firstpicdatehp")
    age_source = "lasttrans" if r.get("lasttransdate") else ("firstpic" if r.get("firstpicdatehp") else "none")
    age = None
    if laid:
        laid_dt = laid if isinstance(laid, datetime) else datetime(laid.year, laid.month, laid.day)
        age = round((at - laid_dt).days / 365.25, 2)
    length = float(r.get("length_m") or 0)
    n_def = int(r.get("n_defects") or 0)
    kp = round(n_def * 100.0 / length, 3) if length > 0 and n_def > 0 else (0.0 if length > 0 else None)
    scores = {
        "srok_ball": srok_ball(age),
        # 0 повреждений при известной длине — балл 1 (как в gid6: IFNULL(n,0))
        "koef_povr_ball": koef_povr_ball(kp) if kp is not None else None,
        "vnesniivid": int(r.get("vnesniivid") or 0) or None,
        "sostoborudovania": int(r.get("sostoborudovania") or 0) or None,
        "kategorii": int(r.get("kategorii") or 0) or None,
        "vnesnkorrozia": int(r.get("vnesnkorrozia") or 0) or None,
        "vnunrenkorrozia": int(r.get("vnunrenkorrozia") or 0) or None,
        "sostkonstrukz": int(r.get("sostkonstrukz") or 0) or None,
    }
    pct, known, filled = wear_percent(scores)
    cons = consequence(r.get("breakconsumvolid"), r.get("populdamageid"), r.get("infrastrdamageid"))
    flow = float(r["flow_t_h"]) if r.get("flow_t_h") is not None else None
    return {
        "lineid": r["lineid"], "pipesectionid": r.get("pipesectionid"), "fileid": r.get("fileid"),
        "age_years": age, "age_source": age_source, "srok_ball": scores["srok_ball"],
        "n_defects": n_def, "koef_povr": kp, "koef_povr_ball": scores["koef_povr_ball"],
        "vnesniivid": scores["vnesniivid"] or 0, "sostoborudovania": scores["sostoborudovania"] or 0,
        "kategorii": scores["kategorii"] or 0, "vnesnkorrozia": scores["vnesnkorrozia"] or 0,
        "vnunrenkorrozia": scores["vnunrenkorrozia"] or 0, "sostkonstrukz": scores["sostkonstrukz"] or 0,
        "factors_filled": filled, "wear_pct": pct, "wear_pct_known": known, "category": category(known),
        "consequence": cons, "flow_t_h": flow, "priority": priority(known, cons, flow),
    }


_COLUMNS = ("lineid", "pipesectionid", "fileid", "age_years", "age_source", "srok_ball", "n_defects", "koef_povr",
            "koef_povr_ball", "vnesniivid", "sostoborudovania", "kategorii", "vnesnkorrozia", "vnunrenkorrozia",
            "sostkonstrukz", "factors_filled", "wear_pct", "wear_pct_known", "category", "consequence", "flow_t_h",
            "priority")


class WearError(Exception):
    pass


async def table_exists(conn) -> bool:
    return bool(await conn.fetchval("SELECT to_regclass('public.wear_out') IS NOT NULL"))


async def run(conn, *, fragment_ids: Optional[list[int]] = None, user: str = "", name: Optional[str] = None,
              at: Optional[datetime] = None) -> dict[str, Any]:
    """Расчёт по всем участкам (или по фрагментам): шапка в calculation_iznos, строки в wear_out."""
    if not await table_exists(conn):
        raise WearError("Нет таблицы wear_out: примените sql/migrations/20261023_wear_out.sql")
    at = at or datetime.now()
    rows = [dict(r) for r in await conn.fetch(_SOURCE_SQL, fragment_ids)]
    if not rows:
        raise WearError("Нет участков для расчёта износа (проверьте фрагменты)")
    snap = await snap_defects(conn, fragment_ids)
    for r in rows:
        r["n_defects"] = int(r.get("n_defects") or 0) + snap["by_line"].get(r["lineid"], 0)
    title = name or f"Износ участков {at:%d.%m.%Y %H:%M}" + (f", фрагменты {fragment_ids}" if fragment_ids else "")
    if user:
        title += f" ({user})"
    async with conn.transaction():
        calc_id = await conn.fetchval(
            "INSERT INTO calculation_iznos (tn, daterascheta, name) VALUES ($1, $2, $3) RETURNING id",
            None, at, title,
        )
        assessed = [assess_row(r, at) for r in rows]
        await conn.executemany(_INSERT_SQL, [(calc_id, *[a[c] for c in _COLUMNS]) for a in assessed])
    summary = _summarize(assessed, rows)
    if snap["unplaced"]:
        summary["notes"].append(
            f"Нарушений без участка: {snap['unplaced']} — привязано по месту (до {DEFECT_SNAP_M:g} м) {snap['snapped']}, "
            f"остальные дальше от сети{' или вне выбранных фрагментов' if fragment_ids else ''}")
    return {"calculation_id": calc_id, "name": title, "lines": len(assessed), "at": at.isoformat(timespec="seconds"),
            "defects_snapped": snap["snapped"], **summary}


def _summarize(assessed: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_cat: dict[int, int] = {}
    filled_hist: dict[int, int] = {}
    for a in assessed:
        if a["category"] is not None:
            by_cat[a["category"]] = by_cat.get(a["category"], 0) + 1
        filled_hist[a["factors_filled"]] = filled_hist.get(a["factors_filled"], 0) + 1
    n = len(assessed) or 1
    notes: list[str] = []
    no_date = sum(1 for a in assessed if a["age_source"] == "none")
    if no_date:
        notes.append(f"Без даты прокладки/перекладки: {no_date} участков из {n} — срок не оценён")
    dated = [r["firstpicdatehp"] for r in rows if r.get("firstpicdatehp")]
    if dated:
        years = sorted(d.year for d in dated)
        span = years[-1] - years[0]
        if span <= 6 and len(dated) > 1000:
            notes.append(f"Даты ввода {years[0]}–{years[-1]} у {len(dated)} участков — похоже на даты внесения в ГИС, "
                         "а не прокладки: срок эксплуатации занижен, нужна выверка firstpicdatehp")
    expert = sum(1 for a in assessed if any(a[k] for k in ("vnesniivid", "sostoborudovania", "kategorii",
                                                              "vnesnkorrozia", "vnunrenkorrozia", "sostkonstrukz")))
    if expert < n * 0.05:
        notes.append(f"Экспертные баллы (внешний вид, оборудование, коррозия, конструкции) заполнены у {expert} участков — "
                     "индекс в основном по сроку и повреждаемости")
    if not any(a["n_defects"] for a in assessed):
        notes.append("Журнал нарушений пуст — повреждаемость всех участков принята 0")
    return {
        "by_category": {k: by_cat.get(k, 0) for k in range(1, 6)},
        "category_labels": CATEGORY_LABELS,
        "factors_filled": dict(sorted(filled_hist.items())),
        "with_flow": sum(1 for a in assessed if a["flow_t_h"] is not None),
        "notes": notes,
    }


async def list_runs(conn, *, limit: int = 50) -> list[dict[str, Any]]:
    if not await table_exists(conn):
        return []
    rows = await conn.fetch(
        """SELECT c.id, c.daterascheta, c.name, COUNT(w.id)::int AS lines,
                  AVG(w.wear_pct_known) AS avg_wear, MAX(w.priority) AS max_priority
             FROM calculation_iznos c LEFT JOIN wear_out w ON w.calculationid = c.id
            GROUP BY c.id ORDER BY c.id DESC LIMIT $1""", limit)
    return [{**dict(r), "daterascheta": r["daterascheta"].isoformat() if r["daterascheta"] else None,
             "avg_wear": round(float(r["avg_wear"]), 2) if r["avg_wear"] is not None else None} for r in rows]


async def latest_id(conn) -> Optional[int]:
    if not await table_exists(conn):
        return None
    return await conn.fetchval("SELECT MAX(calculationid) FROM wear_out")


async def summary(conn, calculation_id: int) -> dict[str, Any]:
    head = await conn.fetchrow("SELECT id, daterascheta, name FROM calculation_iznos WHERE id = $1", calculation_id)
    if not head:
        raise WearError("Расчёт износа не найден")
    rows = [dict(r) for r in await conn.fetch(
        "SELECT category, factors_filled, age_source, n_defects, flow_t_h, wear_pct_known FROM wear_out WHERE calculationid = $1",
        calculation_id)]
    by_cat: dict[int, int] = {}
    filled: dict[int, int] = {}
    for r in rows:
        if r["category"] is not None:
            by_cat[r["category"]] = by_cat.get(r["category"], 0) + 1
        filled[r["factors_filled"]] = filled.get(r["factors_filled"], 0) + 1
    known = [r["wear_pct_known"] for r in rows if r["wear_pct_known"] is not None]
    return {
        "calculation_id": head["id"], "name": head["name"],
        "at": head["daterascheta"].isoformat() if head["daterascheta"] else None,
        "lines": len(rows),
        "avg_wear": round(sum(known) / len(known), 2) if known else None,
        "by_category": {k: by_cat.get(k, 0) for k in range(1, 6)},
        "category_labels": CATEGORY_LABELS,
        "factors_filled": dict(sorted(filled.items())),
        "no_date": sum(1 for r in rows if r["age_source"] == "none"),
        "with_defects": sum(1 for r in rows if r["n_defects"]),
        "with_flow": sum(1 for r in rows if r["flow_t_h"] is not None),
        "weights": WEIGHTS, "factor_labels": FACTOR_LABELS,
    }


_SECTION_SELECT = """
SELECT w.*, n1.externalnodename AS node1, n2.externalnodename AS node2, f.name AS fragment_name,
       h.diametercondit AS diameter, h.pipesectlength AS length_m, tt.name AS tubing
  FROM wear_out w
  JOIN linesobj l ON l.id = w.lineid
  LEFT JOIN nodes n1 ON n1.id = l.nodeid1
  LEFT JOIN nodes n2 ON n2.id = l.nodeid2
  LEFT JOIN fragments f ON f.id = w.fileid
  LEFT JOIN heatpipesections h ON h.lineid = l.id
  LEFT JOIN tubingtypes tt ON tt.id = h.tubingtypeid
 WHERE w.calculationid = $1 AND ($2::int IS NULL OR w.fileid = $2) AND ($3::int IS NULL OR w.category >= $3)
"""
ORDERS = {"priority": "w.priority DESC NULLS LAST", "wear": "w.wear_pct_known DESC NULLS LAST",
          "age": "w.age_years DESC NULLS LAST", "defects": "w.n_defects DESC"}


async def sections(conn, calculation_id: int, *, fragment_id: Optional[int] = None, min_category: Optional[int] = None,
                   order: str = "priority", limit: int = 100, offset: int = 0) -> dict[str, Any]:
    order_sql = ORDERS.get(order, ORDERS["priority"])
    total = await conn.fetchval(
        "SELECT COUNT(*) FROM wear_out w WHERE w.calculationid = $1 AND ($2::int IS NULL OR w.fileid = $2)"
        " AND ($3::int IS NULL OR w.category >= $3)", calculation_id, fragment_id, min_category)
    rows = await conn.fetch(f"{_SECTION_SELECT} ORDER BY {order_sql}, w.lineid LIMIT $4 OFFSET $5",
                            calculation_id, fragment_id, min_category, limit, offset)
    return {"total": int(total or 0), "items": [dict(r) for r in rows]}


async def geojson(conn, calculation_id: int, *, fragment_id: Optional[int] = None, min_category: Optional[int] = None,
                  limit: int = 20000) -> dict[str, Any]:
    rows = await conn.fetch(
        """SELECT w.lineid, w.fileid, w.category, w.wear_pct_known, w.priority, w.age_years, w.n_defects,
                  w.factors_filled, ST_AsGeoJSON(ST_Transform(l.shape, 4326))::json AS geometry
             FROM wear_out w JOIN linesobj l ON l.id = w.lineid
            WHERE w.calculationid = $1 AND ($2::int IS NULL OR w.fileid = $2)
              AND ($3::int IS NULL OR w.category >= $3) AND l.shape IS NOT NULL
            ORDER BY w.priority DESC NULLS LAST LIMIT $4""",
        calculation_id, fragment_id, min_category, limit)
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature", "id": r["lineid"], "geometry": r["geometry"],
            "properties": {k: r[k] for k in ("lineid", "fileid", "category", "wear_pct_known", "priority",
                                              "age_years", "n_defects", "factors_filled")},
        } for r in rows],
    }


async def delete_run(conn, calculation_id: int) -> int:
    async with conn.transaction():
        n = await conn.execute("DELETE FROM wear_out WHERE calculationid = $1", calculation_id)
        await conn.execute("DELETE FROM calculation_iznos WHERE id = $1", calculation_id)
    try:
        return int(n.split()[-1])
    except (ValueError, AttributeError):
        return 0
