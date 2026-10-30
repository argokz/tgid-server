"""Баланс расхода по зонам (фаза 3): утечки по расходомерам — факт против модели и ночной расход.

Зона — часть сети между участками с расходомерами: сеть режется по участкам, где стоят расходомеры подачи и
обратки (и по закрытым задвижкам), связные куски — зоны. Вода в зоне сохраняется: сумма притоков через
расходомеры границы = водоразбор открытой системы + утечки. Направление каждого расходомера — по модели
(знак ut_out.a13 последнего расчёта: + от nodeid1 к nodeid2), сам расходомер даёт модуль.

- **Небаланс** — приток по факту (среднее за WINDOW_MIN) против притока по модели на тех же трубах: модель уже
  содержит водоразбор открытой системы, остаток — утечка (или неучтённый водоразбор). Погрешность — расходомеры
  (FLOW_ACCURACY_PCT от расхода каждого, сумма в квадратах): у магистрали 15 000 т/ч это ±300 т/ч, поэтому
  по среднему уровню видны только большие утечки.
- **Ночной расход** — приток зоны в часы NIGHT_HOURS (местное время, водоразбор минимален) за последнюю ночь
  против медианы предыдущих ночей. Постоянная ошибка расходомера в разности ночей сокращается: рост ночного
  притока на десятки т/ч на фоне 15 000 т/ч заметен — признак новой утечки.
- Зона с питающей точкой внутри (источник, узел заданного напора) по расходомерам не закрыта: её не оценить,
  кроме зоны источника — там приток с обратным знаком есть отпуск в сеть (подпитка), сверх модели — потери сети.
"""
from __future__ import annotations

import json
import os
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from database.telemetry import STALE_MIN, UNITS
from database.ut_out_columns import UT_FLOW_TH, UT_SIGN_RETURN, UT_SIGN_SUPPLY

FLOW_ACCURACY_PCT = float(os.getenv("TELEMETRY_FLOW_ACCURACY_PCT", "2.0") or 2.0)
WINDOW_MIN = max(5, int(os.getenv("TELEMETRY_BALANCE_WINDOW_MIN", "60") or 60))
NIGHT_HOURS = (2, 5)          # [2; 5) по местному времени
NIGHTS = 7
NIGHT_GROWTH_MIN_TH = float(os.getenv("TELEMETRY_NIGHT_GROWTH_TH", "5") or 5)  # т/ч
NIGHT_MIN_HOURS = 2
MIN_PRIOR_NIGHTS = 3
MAX_GEOMETRY_LINES = 5000
PIPES = {"supply": UT_SIGN_SUPPLY, "return": UT_SIGN_RETURN}

STATUS_TEXT = {
    "ok": "баланс сходится",
    "leak": "приток больше модели — утечка или неучтённый водоразбор",
    "growth": "ночной расход вырос — признак новой утечки",
    "check": "приток меньше модели — проверьте расходомеры и водоразбор в модели",
    "open": "зона не закрыта расходомерами — не оценивается",
    "no_data": "нет свежих показаний расходомеров",
}


# --- зоны ----------------------------------------------------------------------------------------

def split_zones(net: dict[str, Any], metered: set[int]) -> list[dict[str, Any]]:
    """Связные куски сети без участков с расходомерами и закрытых задвижек; только куски у расходомеров."""
    adj, info = net["adj"], net["line_info"]
    blocked = set(metered) | set(net.get("normally_closed_lines", ()))
    seen: dict[int, int] = {}
    zones: list[dict[str, Any]] = []
    for lid in sorted(metered):
        line = info.get(lid)
        if line is None:
            continue
        for start in (line["nodeid1"], line["nodeid2"]):
            if start in seen:
                continue
            idx = len(zones)
            nodes = {start}
            seen[start] = idx
            stack = [start]
            while stack:
                node = stack.pop()
                for edge, other in adj.get(node, ()):
                    if edge in blocked or other in seen:
                        continue
                    seen[other] = idx
                    nodes.add(other)
                    stack.append(other)
            zones.append({"key": min(nodes), "nodes": nodes})
    for z in zones:
        z["boundary"], z["internal"] = [], []
    for lid in sorted(metered):
        line = info.get(lid)
        if line is None:
            continue
        z1, z2 = seen.get(line["nodeid1"]), seen.get(line["nodeid2"])
        if z1 == z2:  # расходомер внутри кольца зоны: приток и отток через него сокращаются
            zones[z1]["internal"].append(lid)
            continue
        zones[z1]["boundary"].append((lid, "n1"))
        zones[z2]["boundary"].append((lid, "n2"))
    sources = net.get("source_kinds", {})
    for z in zones:
        z["feeds"] = {n: sources[n] for n in z["nodes"] if n in sources}
    return zones


def inflow_sign(model_flow: Optional[float], side: str) -> Optional[int]:
    """+1 — вода по модели входит в зону через этот участок, −1 — выходит; None — направления нет."""
    if model_flow is None or abs(model_flow) < 1e-6:
        return None
    toward_n2 = model_flow > 0
    return 1 if toward_n2 == (side == "n2") else -1


def zone_kind(zone: dict[str, Any], consumers: int) -> str:
    """zone — закрыта расходомерами; source — только источник (без потребителей: всё, что он отдаёт, проходит
    через расходомеры выводов — баланс = подпитка); open — внутри питающая точка без расходомера."""
    if not zone["feeds"]:
        return "zone"
    return "source" if consumers == 0 and set(zone["feeds"].values()) == {"heat_source"} else "open"


# --- факт ------------------------------------------------------------------------------------------

def night_values(hourly: dict[datetime, float]) -> list[tuple[str, float, int]]:
    """Часовой приток → (ночь, средний приток в NIGHT_HOURS, часов) по местному времени, от старых к новым."""
    acc: dict[str, list[float]] = defaultdict(list)
    for ts, v in hourly.items():
        local = ts.astimezone()
        if NIGHT_HOURS[0] <= local.hour < NIGHT_HOURS[1]:
            acc[local.date().isoformat()].append(v)
    return [(d, sum(vs) / len(vs), len(vs)) for d, vs in sorted(acc.items()) if len(vs) >= NIGHT_MIN_HOURS]


def night_trend(nights: list[tuple[str, float, int]]) -> Optional[dict[str, Any]]:
    """Последняя ночь против медианы предыдущих: рост и порог (3 СКО предыдущих ночей, не меньше порога т/ч)."""
    if len(nights) < MIN_PRIOR_NIGHTS + 1:
        return None
    *prior, last = nights[-(NIGHTS + 1):]
    values = [v for _, v, _ in prior]
    base = statistics.median(values)
    noise = statistics.stdev(values) if len(values) > 1 else 0.0
    threshold = max(3 * noise, NIGHT_GROWTH_MIN_TH)
    growth = last[1] - base
    return {"night": last[0], "value": round(last[1], 1), "baseline": round(base, 1), "growth": round(growth, 1),
            "threshold": round(threshold, 1), "nights": len(prior), "grew": growth > threshold}


def verdict(kind: str, excess: Optional[float], unc: Optional[float], trend: Optional[dict[str, Any]]) -> str:
    if kind == "open":
        return "open"
    if excess is None:
        return "no_data"
    if trend and trend["grew"]:
        return "growth"
    if excess > 2 * unc:
        return "leak"
    if excess < -2 * unc:
        return "check"
    return "ok"


async def _flow_sensors(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """SELECT s.id, s.code, s.name, s.pipe, s.unit, s.line_id, l.fileid
             FROM tgid_sensor s JOIN linesobj l ON l.id = s.line_id
            WHERE s.active AND s.kind = 'flow' AND s.line_id IS NOT NULL ORDER BY s.id""")
    return [dict(r) for r in rows if r["unit"] in UNITS]


async def _model_flows(conn, sensors: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
    """(участок, знак трубы) → расход модели со знаком, т/ч — последний расчёт фрагмента участка."""
    lines = sorted({s["line_id"] for s in sensors})
    rows = await conn.fetch(
        f"""WITH calc AS (SELECT DISTINCT ON (fileid) fileid, id FROM calculation
                           WHERE fileid IN (SELECT fileid FROM linesobj WHERE id = ANY($1::int[]))
                           ORDER BY fileid, id DESC)
            SELECT u.lineid, u.externalsignlineid AS sign, u.{UT_FLOW_TH}::float AS flow
              FROM linesobj l JOIN calc c ON c.fileid = l.fileid
              JOIN ut_out u ON u.lineid = l.id AND u.calculationid = c.id
             WHERE l.id = ANY($1::int[])""", lines)
    return {(r["lineid"], r["sign"]): r["flow"] for r in rows if r["flow"] is not None}


async def _window_avg(conn, ids: list[int], now: datetime) -> dict[int, tuple[float, datetime]]:
    rows = await conn.fetch(
        """SELECT sensor_id, avg(value)::float AS v, max(ts) AS last_ts FROM tgid_sensor_reading
            WHERE sensor_id = ANY($1::int[]) AND ts > $2 GROUP BY sensor_id""",
        ids, now - timedelta(minutes=WINDOW_MIN))
    return {r["sensor_id"]: (r["v"], r["last_ts"]) for r in rows}


async def _hourly(conn, ids: list[int], now: datetime) -> dict[int, dict[datetime, float]]:
    rows = await conn.fetch(
        """SELECT sensor_id, date_trunc('hour', ts) AS h, avg(value)::float AS v FROM tgid_sensor_reading
            WHERE sensor_id = ANY($1::int[]) AND ts > $2 GROUP BY 1, 2""",
        ids, now - timedelta(days=NIGHTS + 1, hours=12))
    out: dict[int, dict[datetime, float]] = defaultdict(dict)
    for r in rows:
        out[r["sensor_id"]][r["h"]] = r["v"]
    return out


async def _consumer_nodes(conn) -> set[int]:
    rows = await conn.fetch(
        """SELECT nodeid FROM realconsumers WHERE nodeid IS NOT NULL
           UNION SELECT nodeid FROM generalizedconsumers WHERE nodeid IS NOT NULL""")
    return {r["nodeid"] for r in rows}


def _zone_length(net: dict[str, Any], nodes: set[int]) -> float:
    return sum(l["length"] for l in net["line_info"].values() if l["nodeid1"] in nodes and l["nodeid2"] in nodes)


async def balance(conn, net: dict[str, Any], now: Optional[datetime] = None) -> dict[str, Any]:
    """Зоны между расходомерами: приток факт / модель, небаланс с погрешностью, ночной расход, вывод."""
    now = now or datetime.now(timezone.utc)
    sensors = await _flow_sensors(conn)
    if not sensors:
        return {"zones": [], "skipped": [], "accuracy_pct": FLOW_ACCURACY_PCT, "window_min": WINDOW_MIN}
    by_line: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for s in sensors:
        by_line[s["line_id"]].setdefault(s["pipe"], s)  # два расходомера одной трубы — первый по id
    skipped = []
    metered = set()
    for lid, pipes in sorted(by_line.items()):
        if lid not in net["line_info"]:
            skipped.append(f"участок {lid}: не в сети (удалён, отключён или во внутренней схеме)")
        elif set(pipes) != set(PIPES):
            # сеть режется только по участку, где известен расход обеих труб: иначе баланс зоны не закрыт
            skipped.append(f"участок {lid}: расходомер только на {'подаче' if 'supply' in pipes else 'обратке'}")
        else:
            metered.add(lid)
    zones = split_zones(net, metered)
    used = [s for lid in metered for s in by_line[lid].values()]
    model = await _model_flows(conn, used)
    ids = [s["id"] for s in used]
    window = await _window_avg(conn, ids, now)
    hourly = await _hourly(conn, ids, now)
    consumers = await _consumer_nodes(conn)
    stale_before = now - timedelta(minutes=STALE_MIN)
    result = []
    for z in zones:
        if not z["boundary"]:
            continue
        zone_consumers = len(z["nodes"] & consumers)
        kind = zone_kind(z, zone_consumers)
        meters, missing = [], []
        fact = model_net = 0.0
        variance = 0.0
        hour_sets: list[dict[datetime, float]] = []
        for lid, side in z["boundary"]:
            for pipe, sign_code in PIPES.items():
                s = by_line[lid][pipe]
                k = UNITS[s["unit"]].to_base
                m = model.get((lid, sign_code))
                sign = inflow_sign(m, side)
                w = window.get(s["id"])
                if sign is None:
                    missing.append(f"{s['code']}: нет расхода в модели — направление неизвестно")
                    continue
                if w is None or w[1] < stale_before:
                    missing.append(f"{s['code']}: молчит")
                    continue
                g = w[0] * k
                fact += sign * g
                model_net += sign * abs(m)
                variance += (FLOW_ACCURACY_PCT / 100 * g) ** 2
                hour_sets.append({h: sign * v * k for h, v in hourly.get(s["id"], {}).items()})
                meters.append({"sensor_id": s["id"], "code": s["code"], "line_id": lid, "pipe": pipe,
                               "direction": "in" if sign > 0 else "out", "fact": round(g, 1),
                               "model": round(abs(m), 1)})
        complete = kind != "open" and not missing and bool(meters)  # незакрытую зону не оценивать вовсе
        flip = -1 if kind == "source" else 1  # зона источника: отпуск в сеть = отток
        excess = round(flip * (fact - model_net), 1) if complete else None
        unc = round(variance ** 0.5, 1) if complete else None
        trend = None
        if complete and hour_sets:
            common = set.intersection(*(set(h) for h in hour_sets))
            trend = night_trend(night_values({h: flip * sum(hs[h] for hs in hour_sets) for h in common}))
        status = verdict(kind, excess, unc, trend)
        result.append({
            "key": z["key"], "kind": kind, "status": status, "text": STATUS_TEXT[status],
            "nodes": len(z["nodes"]), "consumers": zone_consumers,
            "length_km": round(_zone_length(net, z["nodes"]) / 1000, 2),
            "feeds": sorted(z["feeds"]), "boundary": sorted({lid for lid, _ in z["boundary"]}),
            "internal": z["internal"], "meters": meters, "missing": missing,
            "fact": round(flip * fact, 1) if complete else None,
            "model": round(flip * model_net, 1) if complete else None,
            "excess": excess, "uncertainty": unc, "night": trend,
        })
    order = {"growth": 0, "leak": 1, "check": 2, "no_data": 3, "ok": 4, "open": 5}
    result.sort(key=lambda r: (order[r["status"]], -r["nodes"]))
    return {"zones": result, "skipped": skipped, "accuracy_pct": FLOW_ACCURACY_PCT, "window_min": WINDOW_MIN,
            "night_hours": list(NIGHT_HOURS)}


async def zone_geometry(conn, net: dict[str, Any], key: int) -> Optional[dict[str, Any]]:
    """Участки зоны для карты (GeoJSON в 4326); крупная зона — выпуклой оболочкой."""
    sensors = await _flow_sensors(conn)
    by_line: dict[int, set[str]] = defaultdict(set)
    for s in sensors:
        by_line[s["line_id"]].add(s["pipe"])
    metered = {lid for lid, pipes in by_line.items() if pipes == set(PIPES) and lid in net["line_info"]}
    zone = next((z for z in split_zones(net, metered) if z["key"] == key), None)
    if zone is None:
        return None
    nodes = zone["nodes"]
    lines = [lid for lid, l in net["line_info"].items() if l["nodeid1"] in nodes and l["nodeid2"] in nodes]
    if not lines:
        return None
    hull = len(lines) > MAX_GEOMETRY_LINES
    geom = await conn.fetchval(
        f"""SELECT ST_AsGeoJSON(ST_Transform({'ST_ConvexHull(ST_Collect(shape))' if hull else
                                             'ST_Simplify(ST_Collect(shape), 2)'}, 4326), 6)
              FROM linesobj WHERE id = ANY($1::int[]) AND shape IS NOT NULL""", lines)
    return {"key": key, "lines": len(lines), "hull": hull, "geometry": json.loads(geom) if geom else None}


# --- тревоги -----------------------------------------------------------------------------------

ALERT_LEVELS = {"growth": "growth", "leak": "leak", "ok": "normal", "check": "normal"}  # open / no_data — без перехода


async def check_alerts(conn, net: dict[str, Any], now: Optional[datetime] = None) -> list[int]:
    """Сверить вывод по зонам с прошлым состоянием и записать тревоги о переходах; вернуть id новых.

    В отличие от датчиков, первая оценка зоны с утечкой тревогу даёт: зон мало, а утечка — повод действовать.
    Вызывать под замком (database/webhooks.py): два процесса не должны записать одну тревогу дважды.
    """
    state = await balance(conn, net, now)
    prev = {r["zone_key"]: r["status"] for r in await conn.fetch("SELECT zone_key, status FROM tgid_balance_zone")}
    new_ids: list[int] = []
    for z in state["zones"]:
        level = ALERT_LEVELS.get(z["status"])
        before = prev.get(z["key"])
        if level is None or level == before:
            continue
        await conn.execute(
            """INSERT INTO tgid_balance_zone (zone_key, status, since, boundary) VALUES ($1, $2, now(), $3)
               ON CONFLICT (zone_key) DO UPDATE SET status = excluded.status, since = now(),
                                                    boundary = excluded.boundary""",
            z["key"], level, z["boundary"])
        if before is None and level == "normal":
            continue
        night = z["night"] or {}
        new_ids.append(await conn.fetchval(
            """INSERT INTO tgid_balance_alert (zone_key, zone_kind, boundary, status, prev_status, night, night_value,
                                               night_baseline, night_growth, excess, uncertainty)
               VALUES ($1, $2, $3, $4, $5, $6::date, $7, $8, $9, $10, $11) RETURNING id""",
            z["key"], z["kind"], z["boundary"], level, before,
            datetime.fromisoformat(night["night"]).date() if night.get("night") else None,
            night.get("value"), night.get("baseline"), night.get("growth"), z["excess"], z["uncertainty"]))
    return new_ids


async def list_alerts(conn, *, limit: int = 100, open_only: bool = False) -> list[dict[str, Any]]:
    """Тревоги зон; открытая — не принята, не «норма» и не перекрыта более новой тревогой той же зоны."""
    where = ("""WHERE a.acknowledged_at IS NULL AND a.status <> 'normal'
                  AND NOT EXISTS (SELECT 1 FROM tgid_balance_alert b WHERE b.zone_key = a.zone_key AND b.id > a.id)"""
             if open_only else "")
    rows = await conn.fetch(f"SELECT a.* FROM tgid_balance_alert a {where} ORDER BY a.id DESC LIMIT $1", limit)
    out = []
    for r in rows:
        d = dict(r)
        d["at"] = d["at"].isoformat()
        d["night"] = d["night"].isoformat() if d["night"] else None
        d["acknowledged_at"] = d["acknowledged_at"].isoformat() if d["acknowledged_at"] else None
        out.append(d)
    return out


async def acknowledge(conn, alert_id: int, user: str) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        """UPDATE tgid_balance_alert SET acknowledged_by = $2, acknowledged_at = now()
            WHERE id = $1 AND acknowledged_at IS NULL RETURNING id, acknowledged_by, acknowledged_at""",
        alert_id, user)
    if row is None:
        exists = await conn.fetchval("SELECT 1 FROM tgid_balance_alert WHERE id = $1", alert_id)
        return {"id": alert_id, "already": True} if exists else None
    return {"id": row["id"], "acknowledged_by": row["acknowledged_by"],
            "acknowledged_at": row["acknowledged_at"].isoformat()}
