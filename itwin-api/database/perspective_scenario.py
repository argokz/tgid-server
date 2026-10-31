"""Перспективный режим (фаза 5): сценарий-копия фрагмента с приростом нагрузки на N лет — для расчёта и сравнения.

Сколько — прирост города за N лет по тренду подключений (database/load_perspective.py). Где — ожидающие ТУ с
зданием на карте: вес ТУ = прирост × вероятность подключения за N лет (сроки по данным реестра), доля города
распределяется по ТУ пропорционально весу. ТУ привязывается к ближайшему потребителю сети модели (фрагменты без
сценариев и копий, database/em_chapter.py) не дальше радиуса — 90-го процентиля расстояния от зданий уже
подключённых ТУ до ближайшего потребителя (из данных, Алматы — ~120 м); дальше — новый район без сети, такая
нагрузка в сценарий не попадает и показывается отдельно, как и ТУ без здания.

Сценарий — обычная копия фрагмента (database/scenarios.py): у потребителя узла с наибольшей нагрузкой все поля
нагрузки (те, из которых складывается нагрузка в изоляции и балансах) умножаются на 1 + прибавка / нагрузка. Расчёт
sety и сравнение с основой — как у любого сценария. Перспективные поля паспорта (persp*) расчёт sety не читает.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Optional

from database import load_perspective as lp

RADIUS_QUANTILE = 0.9
GEN_COLUMNS = ("calchldep", "calchlindep", "calchlparall", "calchlmix", "calchlconseq", "calchlpreon",
               "calchlventil", "avghlgvsopensysflow", "avghlgvsopensysret", "calchlgvsparall", "calchlgvsmix",
               "calchlgvsconseq", "calchlgvspreon", "calchlclosesys", "calchlopensysflow", "calchlopensysret")
REAL_COLUMNS = ("calchldep", "calchlindep", "calchlventil", "avghlgvsopenflow", "avghlgvsopenret",
                "avghlgvscloseparall", "avghlgvsclosemix", "avghlgvscloseconseq", "avghlgvsclosepreon",
                "avghlclosesys", "avghlopensysflow", "avghlopensysret")
TABLES = {"generalized": ("generalizedconsumers", GEN_COLUMNS), "real": ("realconsumers", REAL_COLUMNS)}


def quantile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    v = sorted(values)
    pos = (len(v) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def allocate(growth: float, waiting: list[dict[str, Any]], radius: float, fileid: int) -> dict[str, Any]:
    """Прирост города growth — по ожидающим ТУ пропорционально весу; в сценарий — ТУ, чей ближайший потребитель в
    радиусе и во фрагменте fileid. waiting: id, weight, node, node_fileid, dist (node/dist — None без здания)."""
    total_w = sum(t["weight"] for t in waiting)
    by_node: dict[int, float] = defaultdict(float)
    parts = {"fragment": 0.0, "other_fragments": 0.0, "new_areas": 0.0, "no_location": 0.0}
    for t in waiting:
        g = growth * t["weight"] / total_w if total_w else 0.0
        if t["node"] is None:
            parts["no_location"] += g
        elif t["dist"] > radius:
            parts["new_areas"] += g
        elif t["node_fileid"] == fileid:
            parts["fragment"] += g
            by_node[t["node"]] += g
        else:
            parts["other_fragments"] += g
    return {"by_node": dict(by_node), "parts": {k: round(v, 2) for k, v in parts.items()}}


# --- база ----------------------------------------------------------------------------------------

_CONSUMER_NODES = """
    SELECT n.id, n.shape, n.fileid FROM nodes n
     WHERE n.shape IS NOT NULL AND coalesce(n.removed, 0) = 0 AND n.fileid = ANY($1::int[])
       AND (EXISTS (SELECT 1 FROM generalizedconsumers g WHERE g.nodeid = n.id AND coalesce(g.consumerstateid, 1) = 1)
            OR EXISTS (SELECT 1 FROM realconsumers r WHERE r.nodeid = n.id AND coalesce(r.consumerstateid, 1) = 1))
"""


async def _nearest(conn, ids: list[int], model: list[int]) -> dict[int, tuple[int, int, float]]:
    """ТУ с зданием → ближайший узел с включённым потребителем во фрагментах модели: {ТУ: (узел, фрагмент, м)}."""
    rows = await conn.fetch(
        f"""WITH cons AS ({_CONSUMER_NODES}),
                 tu AS (SELECT tu.id, ST_PointOnSurface(b.shape) AS p FROM tehnicheskie_usloviya tu
                          JOIN zdaniya_tu b ON b.id = tu.zdanie
                         WHERE tu.id = ANY($2::int[]) AND b.shape IS NOT NULL)
            SELECT tu.id, c.id AS node, c.fileid, ST_Distance(tu.p, c.shape) AS dist
              FROM tu CROSS JOIN LATERAL (SELECT id, fileid, shape FROM cons ORDER BY cons.shape <-> tu.p LIMIT 1) c""",
        model, ids)
    return {r["id"]: (r["node"], r["fileid"], float(r["dist"])) for r in rows}


async def plan(conn, *, fileid: int, horizon: int, today: Optional[date] = None) -> dict[str, Any]:
    """Сколько нагрузки и у каких потребителей фрагмента добавит перспектива на horizon лет (без записи)."""
    from database import em_chapter

    today = today or date.today()
    p = await lp.perspective(conn, horizon=horizon, today=today)
    growth = p["cumulative"][-1]
    rows, _ = lp.clean(await lp.load_rows(conn), today)
    complete = date.fromisoformat(p["acts_complete_until"])
    this_year = date(today.year, 1, 1)
    probs = lp.connect_within(rows, complete, this_year, horizon, lp.hazards(rows, complete))
    model, copies = await em_chapter._fileids(conn, None)
    if fileid not in model:
        raise lp.PerspectiveError(422, "Фрагмент — сценарий или копия другого фрагмента: выберите основной")
    by_id = {r["id"]: r for r in rows}
    near = await _nearest(conn, [r["id"] for r in rows], model)
    # радиус — по уже подключённым ТУ: насколько их здания далеки от ближайшего потребителя сети
    radius = quantile([near[r["id"]][2] for r in rows if r["act"] is not None and r["id"] in near], RADIUS_QUANTILE)
    if radius is None:
        raise lp.PerspectiveError(422, "У подключённых ТУ нет зданий на карте — места прироста не определить")
    waiting = []
    for tu_id, prob in probs.items():
        n = near.get(tu_id)
        waiting.append({"id": tu_id, "weight": by_id[tu_id]["increment"] * prob,
                        "node": n[0] if n else None, "node_fileid": n[1] if n else None, "dist": n[2] if n else None})
    alloc = allocate(growth, waiting, radius, fileid)
    consumers = await _consumers_at(conn, list(alloc["by_node"]))
    changes, skipped = [], 0.0
    for node, add in alloc["by_node"].items():
        c = consumers.get(node)
        if c is None or c["load"] <= 0:
            skipped += add
            continue
        changes.append({**c, "add": round(add, 4), "factor": round(1 + add / c["load"], 6)})
    changes.sort(key=lambda c: -c["add"])
    return {
        "fileid": fileid, "horizon": horizon, "years": [p["years"][0], p["years"][-1]],
        "city_growth": growth, "radius_m": round(radius, 1), "parts": alloc["parts"],
        "fragment_growth": round(sum(c["add"] for c in changes), 2), "skipped_zero_load": round(skipped, 2),
        "fragment_load": round(await _fragment_load(conn, fileid), 1),
        "consumers": changes, "copies_excluded": len(copies),
    }


async def _consumers_at(conn, nodes: list[int]) -> dict[int, dict[str, Any]]:
    """У каждого узла — включённый потребитель с наибольшей нагрузкой (как в изоляции)."""
    from database.outage_simulation import _Q_CONSUMERS

    best: dict[int, dict[str, Any]] = {}
    for r in await conn.fetch(_Q_CONSUMERS, nodes):
        load = sum(float(r[k] or 0) for k in ("heating_load", "ventilation_load", "hot_water_load", "technology_load"))
        if r["nodeid"] not in best or load > best[r["nodeid"]]["load"]:
            best[r["nodeid"]] = {"node": r["nodeid"], "type": r["ctype"], "id": r["id"], "name": r["name"],
                                 "load": round(load, 4)}
    return best


async def _fragment_load(conn, fileid: int) -> float:
    from database.outage_simulation import _Q_CONSUMERS

    nodes = [r[0] for r in await conn.fetch(
        "SELECT id FROM nodes WHERE fileid = $1 AND coalesce(removed, 0) = 0", fileid)]
    return sum(sum(float(r[k] or 0) for k in ("heating_load", "ventilation_load", "hot_water_load", "technology_load"))
               for r in await conn.fetch(_Q_CONSUMERS, nodes))


async def apply_to_scenario(conn, scenario_id: int, changes: list[dict[str, Any]]) -> int:
    """Умножить поля нагрузки копий потребителей сценария на factor. Возвращает число изменённых потребителей."""
    done = 0
    for kind, (table, columns) in TABLES.items():
        items = [c for c in changes if c["type"] == kind]
        if not items:
            continue
        mapping = {r["base_id"]: r["copy_id"] for r in await conn.fetch(
            "SELECT base_id, copy_id FROM tgid_scenario_object WHERE scenario_id = $1 AND table_name = $2",
            scenario_id, table)}
        pairs = [(mapping[c["id"]], c["factor"]) for c in items if c["id"] in mapping]
        if not pairs:
            continue
        sets = ", ".join(f"{col} = {col} * m.f" for col in columns)
        status = await conn.execute(
            f"""UPDATE {table} t SET {sets}
                  FROM unnest($1::int[], $2::float8[]) AS m(id, f) WHERE t.id = m.id""",
            [x[0] for x in pairs], [x[1] for x in pairs])
        done += int(status.split()[-1])
    return done
