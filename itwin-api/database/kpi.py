"""Показатели эксплуатации (фаза 2, дашборды KPI): одна сводка для окна «Показатели» веба.

Разделы:
- аварийность — журнал дефектов десктопа (defect): за период по месяцам, категориям, состояниям, источникам;
  открытые сейчас; повреждений на 100 км сети в год (число за период, приведённое к году);
- ремонты — дефекты, ремонт которых завершён в периоде, и средний срок от обнаружения до завершения;
- наряды (tgid_work_order) — по статусам сейчас, просрочка, созданы и выполнены за период, среднее время выполнения,
  доля прибытий по треку;
- отключения (tgid_outage) — за период по видам, потребители, средняя длительность, идущие сейчас;
- сеть — длина основной сети, по десятилетиям прокладки (перекладки) и по диаметрам;
- износ — последний расчёт износа (database/wear.py).

Фильтры — как у карты: период, фрагмент, видимая область карты (bbox в WGS84). Сеть — основная: без участков
внутренних схем узлов, удалённых и копий-сценариев. Сводка сети дорогая (сотни тысяч участков) — кэш на 10 минут.
"""
from __future__ import annotations

import time
from datetime import date, datetime, timezone
from typing import Any, Optional

from database.net_srid import line_inner_sql, net_srid

BBox = tuple[float, float, float, float]
NETWORK_CACHE_S = 600
MAX_PERIOD_DAYS = 3660
MAX_POINTS = 5000
DIAMETER_BUCKETS = (100, 200, 300, 500, 700)  # мм: до 100, 101–200, …, свыше 700
DEFECT_OPEN_STATES = (1, 2)                    # statedefect: «Нарушение», «Ремонт»
MIN_YEAR = 1900                                # раньше — ошибка в дате прокладки
_network_cache: dict[tuple, tuple[float, dict[str, Any]]] = {}


class KpiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def check_period(date_from: date, date_to: date) -> None:
    if date_from > date_to:
        raise KpiError(422, "Начало периода позже конца")
    if (date_to - date_from).days > MAX_PERIOD_DAYS:
        raise KpiError(422, "Период — не больше 10 лет")


def parse_bbox(raw: Optional[str]) -> Optional[BBox]:
    """«минДолгота,минШирота,максДолгота,максШирота» → кортеж; неверное — 422."""
    if not raw:
        return None
    try:
        parts = tuple(float(x) for x in raw.split(","))
    except ValueError as exc:
        raise KpiError(422, "bbox: четыре числа через запятую") from exc
    if len(parts) != 4:
        raise KpiError(422, "bbox: четыре числа через запятую")
    x1, y1, x2, y2 = parts
    if not (-180 <= x1 < x2 <= 180 and -90 <= y1 < y2 <= 90):
        raise KpiError(422, "bbox: границы вне WGS84 или перепутаны")
    return x1, y1, x2, y2


def diameter_bucket(d: Optional[float]) -> str:
    if d is None or d <= 0:
        return "нет данных"
    low = 0
    for top in DIAMETER_BUCKETS:
        if d <= top:
            return f"до {top}" if low == 0 else f"{low + 1}–{top}"
        low = top
    return f"свыше {DIAMETER_BUCKETS[-1]}"


def per_100km_year(count: int, km: float, days: int) -> Optional[float]:
    """Число событий за период → на 100 км сети в год."""
    if km <= 0 or days <= 0:
        return None
    return round(count / km * 100 * 365.25 / days, 2)


def month_keys(date_from: date, date_to: date) -> list[str]:
    """Все месяцы периода «ГГГГ-ММ» — нулевые месяцы тоже на графике."""
    out, y, m = [], date_from.year, date_from.month
    while (y, m) <= (date_to.year, date_to.month):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


class _Args:
    """Параметры SQL по порядку ($1, $2, …)."""

    def __init__(self) -> None:
        self.values: list[Any] = []

    def add(self, value: Any) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


async def _defect_srid(conn) -> int:
    srid = await conn.fetchval("SELECT Find_SRID('public', 'defect', 'shape')")
    return int(srid) if srid and int(srid) > 0 else net_srid()


def _defect_where(a: _Args, *, srid: int, fileid: Optional[int], bbox: Optional[BBox]) -> list[str]:
    where = []
    if fileid:
        where.append(f"d.lineid IN (SELECT id FROM linesobj WHERE fileid = {a.add(fileid)})")
    if bbox:
        env = f"ST_Transform(ST_MakeEnvelope({a.add(bbox[0])}, {a.add(bbox[1])}, {a.add(bbox[2])}, {a.add(bbox[3])}, 4326), {srid})"
        where.append(f"d.shape && {env}")
    return where


def _point_where(a: _Args, *, fileid: Optional[int], bbox: Optional[BBox], alias: str) -> list[str]:
    where = []
    if fileid:
        where.append(f"{alias}.fileid = {a.add(fileid)}")
    if bbox:
        where.append(f"{alias}.lon BETWEEN {a.add(bbox[0])} AND {a.add(bbox[2])}"
                     f" AND {alias}.lat BETWEEN {a.add(bbox[1])} AND {a.add(bbox[3])}")
    return where


def _and(where: list[str]) -> str:
    return " AND ".join(where) if where else "TRUE"


async def defects(conn, date_from: date, date_to: date, *, fileid=None, bbox=None) -> dict[str, Any]:
    srid = await _defect_srid(conn)

    def scoped() -> tuple[_Args, str, str, str]:
        """Свой список параметров на запрос: период ($1, $2) и фильтры карты."""
        a = _Args()
        p_from, p_to = a.add(date_from), a.add(date_to)
        return a, p_from, p_to, _and(_defect_where(a, srid=srid, fileid=fileid, bbox=bbox))

    a, p_from, p_to, base = scoped()
    in_period = f"d.data_osmotra::date BETWEEN {p_from} AND {p_to}"
    rows = await conn.fetch(
        f"""SELECT to_char(d.data_osmotra, 'YYYY-MM') AS month, d.remontcatid AS category_id, cat.name AS category,
                   d.stateid AS state_id, st.name AS state, d.remonttypeid AS source_id, src.name AS source,
                   count(*)::int AS n
              FROM defect d
              LEFT JOIN remontcat cat ON cat.id = d.remontcatid
              LEFT JOIN statedefect st ON st.id = d.stateid
              LEFT JOIN defecttypes src ON src.id = d.remonttypeid
             WHERE {in_period} AND {base}
             GROUP BY 1, 2, 3, 4, 5, 6, 7""", *a.values)
    a = _Args()
    states = a.add(list(DEFECT_OPEN_STATES))
    open_now = await conn.fetchval(
        f"SELECT count(*) FROM defect d WHERE d.stateid = ANY({states}::int[])"
        f" AND {_and(_defect_where(a, srid=srid, fileid=fileid, bbox=bbox))}", *a.values)
    a, p_from, p_to, base = scoped()
    repairs = await conn.fetchrow(
        f"""SELECT count(*)::int AS done,
                   avg(d.data_zaversheniya_remonta - d.data_osmotra::date)
                       FILTER (WHERE d.data_osmotra IS NOT NULL
                               AND d.data_zaversheniya_remonta >= d.data_osmotra::date) AS avg_days
              FROM defect d
             WHERE d.data_zaversheniya_remonta BETWEEN {p_from} AND {p_to} AND {base}""", *a.values)
    months = {k: 0 for k in month_keys(date_from, date_to)}

    def group(key_id: str, key_name: str) -> list[dict[str, Any]]:
        acc: dict[Any, dict[str, Any]] = {}
        for r in rows:
            item = acc.setdefault(r[key_id], {"id": r[key_id], "name": (r[key_name] or "").strip() or "не указано", "count": 0})
            item["count"] += r["n"]
        return sorted(acc.values(), key=lambda x: -x["count"])

    for r in rows:
        if r["month"] in months:
            months[r["month"]] += r["n"]
    return {
        "total": sum(r["n"] for r in rows),
        "open_now": int(open_now or 0),
        "by_month": [{"month": k, "count": v} for k, v in months.items()],
        "by_category": group("category_id", "category"),
        "by_state": group("state_id", "state"),
        "by_source": group("source_id", "source"),
        "repairs_done": repairs["done"] if repairs else 0,
        "repair_avg_days": round(float(repairs["avg_days"]), 1) if repairs and repairs["avg_days"] is not None else None,
    }


async def work_orders(conn, date_from: date, date_to: date, *, fileid=None, bbox=None) -> dict[str, Any]:
    if not await conn.fetchval("SELECT to_regclass('public.tgid_work_order') IS NOT NULL"):
        return {"by_status": {}, "overdue": 0, "created": 0, "done": 0, "avg_hours_to_done": None, "arrived_share": None}
    a = _Args()
    p_from, p_to = a.add(date_from), a.add(date_to)
    base = _and(_point_where(a, fileid=fileid, bbox=bbox, alias="o"))
    s_args = _Args()
    s_base = _and(_point_where(s_args, fileid=fileid, bbox=bbox, alias="o"))
    by_status = {r["status"]: r["n"] for r in await conn.fetch(
        f"SELECT o.status, count(*)::int AS n FROM tgid_work_order o WHERE {s_base} GROUP BY 1", *s_args.values)}
    row = await conn.fetchrow(
        f"""SELECT count(*) FILTER (WHERE o.created_at::date BETWEEN {p_from} AND {p_to})::int AS created,
                   count(*) FILTER (WHERE o.finished_at::date BETWEEN {p_from} AND {p_to})::int AS done,
                   avg(EXTRACT(EPOCH FROM o.finished_at - o.created_at) / 3600)
                       FILTER (WHERE o.finished_at::date BETWEEN {p_from} AND {p_to}) AS avg_hours,
                   count(*) FILTER (WHERE o.status IN ('new', 'assigned', 'in_progress')
                                    AND o.planned_finish < now())::int AS overdue,
                   count(*) FILTER (WHERE o.finished_at::date BETWEEN {p_from} AND {p_to}
                                    AND o.arrived_at IS NOT NULL)::int AS arrived
              FROM tgid_work_order o WHERE {base}""", *a.values)
    done = row["done"] or 0
    return {
        "by_status": by_status,
        "overdue": row["overdue"] or 0,
        "created": row["created"] or 0,
        "done": done,
        "avg_hours_to_done": round(float(row["avg_hours"]), 1) if row["avg_hours"] is not None else None,
        "arrived_share": round(row["arrived"] / done, 2) if done else None,
    }


async def outages(conn, date_from: date, date_to: date, *, fileid=None, bbox=None) -> dict[str, Any]:
    if not await conn.fetchval("SELECT to_regclass('public.tgid_outage') IS NOT NULL"):
        return {"total": 0, "by_kind": {}, "consumers": 0, "avg_hours": None, "active_now": 0}
    a = _Args()
    p_from, p_to = a.add(date_from), a.add(date_to)
    base = _and(_point_where(a, fileid=fileid, bbox=bbox, alias="t"))
    rows = await conn.fetch(
        f"""SELECT t.kind, count(*)::int AS n, sum(t.consumers_count)::int AS consumers,
                   avg(EXTRACT(EPOCH FROM COALESCE(t.actual_end, t.planned_end)
                                          - COALESCE(t.actual_start, t.planned_start)) / 3600) AS hours
              FROM tgid_outage t
             WHERE t.status <> 'cancelled'
               AND COALESCE(t.actual_start, t.planned_start)::date <= {p_to}
               AND COALESCE(t.actual_end, t.planned_end)::date >= {p_from}
               AND {base}
             GROUP BY 1""", *a.values)
    act_args = _Args()
    act_base = _and(_point_where(act_args, fileid=fileid, bbox=bbox, alias="t"))
    active = await conn.fetchval(
        f"SELECT count(*) FROM tgid_outage t WHERE t.status = 'active' AND {act_base}", *act_args.values)
    total = sum(r["n"] for r in rows)
    hours = [(r["hours"], r["n"]) for r in rows if r["hours"] is not None]
    return {
        "total": total,
        "by_kind": {r["kind"]: r["n"] for r in rows},
        "consumers": sum(r["consumers"] or 0 for r in rows),
        "avg_hours": round(sum(float(h) * n for h, n in hours) / sum(n for _, n in hours), 1) if hours else None,
        "active_now": int(active or 0),
    }


async def network(conn, *, fileid=None, bbox=None, cache_key: str = "") -> dict[str, Any]:
    key = (cache_key, fileid, bbox)
    cached = _network_cache.get(key)
    if cached and time.monotonic() - cached[0] < NETWORK_CACHE_S:
        return cached[1]
    a = _Args()
    where = [f"COALESCE(l.removed, 0) = 0", f"{line_inner_sql('l')} IS NULL",
             "NOT EXISTS (SELECT 1 FROM tgid_scenario s WHERE s.fileid = l.fileid)"]
    if fileid:
        where.append(f"l.fileid = {a.add(fileid)}")
    if bbox:
        where.append(f"l.shape && ST_Transform(ST_MakeEnvelope({a.add(bbox[0])}, {a.add(bbox[1])}, {a.add(bbox[2])},"
                     f" {a.add(bbox[3])}, 4326), {net_srid()})")
    rows = await conn.fetch(
        f"""SELECT h.diametercondit AS diameter,
                   -- год вне 1900…текущего — ошибка ввода (в Астане есть 4890), считать «нет даты»
                   CASE WHEN EXTRACT(YEAR FROM COALESCE(h.lasttransdate, h.firstpicdatehp))
                             BETWEEN {MIN_YEAR} AND EXTRACT(YEAR FROM now())
                        THEN (EXTRACT(YEAR FROM COALESCE(h.lasttransdate, h.firstpicdatehp))::int / 10) * 10 END AS decade,
                   sum(h.pipesectlength) / 1000.0 AS km, count(*)::int AS n
              FROM linesobj l
              JOIN LATERAL (SELECT hp.diametercondit, hp.pipesectlength, hp.lasttransdate, hp.firstpicdatehp
                              FROM heatpipesections hp WHERE hp.lineid = l.id
                             ORDER BY hp.pipesectlength DESC NULLS LAST, hp.id DESC LIMIT 1) h ON TRUE
             WHERE {' AND '.join(where)}
             GROUP BY 1, 2""", *a.values)
    by_diameter: dict[str, float] = {}
    by_decade: dict[str, float] = {}
    for r in rows:
        km = float(r["km"] or 0)
        bucket = diameter_bucket(float(r["diameter"]) if r["diameter"] is not None else None)
        by_diameter[bucket] = by_diameter.get(bucket, 0) + km
        decade = f"{r['decade']}-е" if r["decade"] else "нет даты"
        by_decade[decade] = by_decade.get(decade, 0) + km
    order = [diameter_bucket(d) for d in DIAMETER_BUCKETS] + [f"свыше {DIAMETER_BUCKETS[-1]}", "нет данных"]
    result = {
        "km": round(sum(float(r["km"] or 0) for r in rows), 1),
        "lines": sum(r["n"] for r in rows),
        "by_diameter": [{"name": k, "km": round(by_diameter[k], 1)} for k in order if k in by_diameter],
        "by_decade": [{"name": k, "km": round(v, 1)} for k, v in sorted(by_decade.items(),
                                                                         key=lambda kv: (kv[0] == "нет даты", kv[0]))],
    }
    _network_cache[key] = (time.monotonic(), result)
    return result


async def wear(conn) -> Optional[dict[str, Any]]:
    from database import wear as wear_mod

    calc_id = await wear_mod.latest_id(conn)
    if not calc_id:
        return None
    s = await wear_mod.summary(conn, calc_id)
    return {k: s[k] for k in ("calculation_id", "name", "at", "lines", "avg_wear", "by_category", "category_labels")}


async def dashboard(conn, date_from: date, date_to: date, *, fileid: Optional[int] = None,
                    bbox: Optional[BBox] = None, cache_key: str = "") -> dict[str, Any]:
    check_period(date_from, date_to)
    net = await network(conn, fileid=fileid, bbox=bbox, cache_key=cache_key)
    d = await defects(conn, date_from, date_to, fileid=fileid, bbox=bbox)
    days = (date_to - date_from).days + 1
    return {
        "period": {"from": date_from.isoformat(), "to": date_to.isoformat(), "days": days},
        "filters": {"fileid": fileid, "bbox": list(bbox) if bbox else None},
        "defects": {**d, "per_100km_year": per_100km_year(d["total"], net["km"], days)},
        "work_orders": await work_orders(conn, date_from, date_to, fileid=fileid, bbox=bbox),
        "outages": await outages(conn, date_from, date_to, fileid=fileid, bbox=bbox),
        "network": net,
        # износ — по всей сети последнего расчёта (фильтры карты к нему не применяются)
        "wear": await wear(conn),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def defect_points(conn, date_from: date, date_to: date, *, month: Optional[str] = None,
                        category_id: Optional[int] = None, state_id: Optional[int] = None,
                        fileid: Optional[int] = None, bbox: Optional[BBox] = None) -> dict[str, Any]:
    """Дефекты периода точками — показать на карте то, что выбрано на графике."""
    check_period(date_from, date_to)
    srid = await _defect_srid(conn)
    a = _Args()
    where = [f"d.data_osmotra::date BETWEEN {a.add(date_from)} AND {a.add(date_to)}", "d.shape IS NOT NULL",
             *_defect_where(a, srid=srid, fileid=fileid, bbox=bbox)]
    if month:
        where.append(f"to_char(d.data_osmotra, 'YYYY-MM') = {a.add(month)}")
    if category_id is not None:
        where.append(f"d.remontcatid IS NOT DISTINCT FROM {a.add(category_id or None)}")
    if state_id is not None:
        where.append(f"d.stateid IS NOT DISTINCT FROM {a.add(state_id or None)}")
    rows = await conn.fetch(
        f"""SELECT d.id, d.data_osmotra, d.defectdescription, d.stateid, cat.name AS category,
                   ST_X(ST_Transform(d.shape, 4326)) AS lon, ST_Y(ST_Transform(d.shape, 4326)) AS lat
              FROM defect d LEFT JOIN remontcat cat ON cat.id = d.remontcatid
             WHERE {' AND '.join(where)}
             ORDER BY d.data_osmotra DESC LIMIT {MAX_POINTS + 1}""", *a.values)
    return {"type": "FeatureCollection", "truncated": len(rows) > MAX_POINTS, "features": [{
        "type": "Feature", "id": r["id"],
        "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "properties": {"id": r["id"], "date": r["data_osmotra"].date().isoformat() if r["data_osmotra"] else None,
                       "description": (r["defectdescription"] or "")[:200], "state_id": r["stateid"],
                       "category": r["category"]},
    } for r in rows[:MAX_POINTS]]}


def default_period(today: Optional[date] = None) -> tuple[date, date]:
    """Последние 12 месяцев: с первого числа месяца год назад по сегодня."""
    today = today or date.today()
    return date(today.year - 1, today.month, 1), today
