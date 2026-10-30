"""Калибровка модели по телеметрии (фаза 3): потери напора между соседними датчиками давления — факт против модели.

Пара — два действующих датчика давления на одной трубе (подача или обратка), соседние по сети: кратчайший путь
между ними (граф пьезометра) не проходит через третий датчик. Направление — от большего напора модели к меньшему;
пары через насосную станцию не сравниваются. Потери напора:
- модель: H = отметка + напор над отметкой (us_out.pih) последнего расчёта, ΔH = H(выше) − H(ниже);
- факт:   H = отметка + давление датчика в м вод. ст. (среднее за CAL_WINDOW_MIN), ΔH так же.
Отношение r = ΔH факт / ΔH модели:
- |r − 1| ≤ 10 % — модель согласована; в пределах двух погрешностей датчиков (PRESSURE_ACCURACY_M × √2 / ΔH
  модели) — «в пределах погрешности»: сначала поверка манометров, модель не трогать;
- r в пределах 0,5…1,5 — расхождение похоже на шероховатость (или расход, отличный от модели): при том же
  расходе ΔH ∝ λ, а λ ∝ k^0,25 (Шифринсон, квадратичная область) → эквивалентная шероховатость × r⁴;
- r > 1,5 — так много шероховатость не даёт: местное сопротивление — прикрытая задвижка, засор, неверный диаметр;
- r < 0,5 — проверить датчики и диаметры (или реальный расход сильно меньше модели).
Модель не меняется: участки пары и предлагаемая шероховатость — для проверки инженером (групповые установщики,
сценарий «что если»).
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

import networkx as nx

from database.telemetry import UNITS, _iso
from database.ut_out_columns import US_PIEZO_HEAD_M, US_SIGN_RETURN, US_SIGN_SUPPLY

CAL_WINDOW_MIN = max(5, int(os.getenv("TELEMETRY_CAL_WINDOW_MIN", "30") or 30))
# Погрешность датчика давления, м вод. ст.: манометр класса 0,25 на 16 кгс/см² — ±0,4 м; разность двух датчиков —
# × √2. Расхождение в пределах двух погрешностей — не повод менять модель (сначала поверка датчиков)
PRESSURE_ACCURACY_M = float(os.getenv("TELEMETRY_PRESSURE_ACCURACY_M", "0.5") or 0.5)
MIN_MODEL_DH_M = 1.0      # меньше — отношение неустойчиво (шум датчиков сравним с потерями)
MAX_PATH_M = 20_000       # дальше — датчики не «соседи», пару не строить
OK_RATIO = 0.10
ROUGH_RANGE = (0.5, 1.5)
ROUGHNESS_LIMITS_MM = (0.05, 5.0)


def uncertainty(dh_model: float, accuracy_m: float = PRESSURE_ACCURACY_M) -> float:
    """Относительная погрешность отношения потерь от погрешности двух датчиков."""
    return (2 ** 0.5) * accuracy_m / dh_model if dh_model > 0 else float("inf")


def verdict(ratio: float, unc: float = 0.0) -> dict[str, str]:
    if abs(ratio - 1) <= OK_RATIO:
        return {"status": "ok", "text": "модель согласована"}
    if abs(ratio - 1) <= 2 * unc:
        return {"status": "noise", "text": "в пределах погрешности датчиков — сначала проверьте поверку манометров"}
    if ratio > ROUGH_RANGE[1]:
        return {"status": "local", "text": "потери намного больше модели: местное сопротивление — "
                                           "прикрытая задвижка, засор, меньший диаметр"}
    if ratio < ROUGH_RANGE[0]:
        return {"status": "check", "text": "потери намного меньше модели: проверьте датчики, диаметры и расход"}
    if ratio > 1:
        return {"status": "rough", "text": "потери больше модели: шероховатость выше (отложения) или расход больше"}
    return {"status": "rough", "text": "потери меньше модели: шероховатость ниже или расход меньше"}


def roughness_factor(ratio: float, unc: float = 0.0) -> Optional[float]:
    """Множитель эквивалентной шероховатости: ΔH ∝ λ ∝ k^0,25 → k × r⁴ (только в области «шероховатость»
    и за пределами погрешности датчиков)."""
    if not (ROUGH_RANGE[0] <= ratio <= ROUGH_RANGE[1]) or abs(ratio - 1) <= max(OK_RATIO, 2 * unc):
        return None
    return round(ratio ** 4, 2)


async def _sensor_points(conn) -> list[dict[str, Any]]:
    """Датчики давления в узлах: среднее показание за окно, отметка, напор модели последнего расчёта фрагмента."""
    rows = await conn.fetch(
        f"""WITH s AS (
                SELECT s.id, s.code, s.name, s.pipe, s.unit, s.node_id, n.fileid, n.geomarktoptube::float AS z,
                       coalesce(nullif(n.nodename, ''), n.externalnodename) AS node_name
                  FROM tgid_sensor s JOIN nodes n ON n.id = s.node_id
                 WHERE s.active AND s.kind = 'pressure'),
            calc AS (SELECT DISTINCT ON (fileid) fileid, id FROM calculation
                      WHERE fileid IN (SELECT fileid FROM s) ORDER BY fileid, id DESC)
            SELECT s.*, c.id AS calculation_id, u.{US_PIEZO_HEAD_M}::float AS pih,
                   r.avg_value, r.n, r.last_ts
              FROM s
              JOIN calc c ON c.fileid = s.fileid
              JOIN us_out u ON u.nodeid = s.node_id AND u.calculationid = c.id
                           AND u.externalsign = CASE WHEN s.pipe = 'supply' THEN {US_SIGN_SUPPLY} ELSE {US_SIGN_RETURN} END
              JOIN LATERAL (
                  SELECT avg(value) AS avg_value, count(*) AS n, max(ts) AS last_ts FROM tgid_sensor_reading
                   WHERE sensor_id = s.id
                     AND ts > (SELECT max(ts) FROM tgid_sensor_reading WHERE sensor_id = s.id)
                              - interval '{CAL_WINDOW_MIN} minutes'
              ) r ON r.n > 0""")
    out = []
    for r in rows:
        unit = UNITS.get(r["unit"])
        if unit is None or r["z"] is None:
            continue
        out.append({
            "sensor_id": r["id"], "code": r["code"], "name": r["name"], "pipe": r["pipe"], "node_id": r["node_id"],
            "node_name": r["node_name"], "fileid": r["fileid"], "calculation_id": r["calculation_id"],
            "z": r["z"], "h_model": r["z"] + r["pih"], "h_fact": r["z"] + r["avg_value"] * unit.to_base,
            "readings": r["n"], "last_ts": _iso(r["last_ts"]),
        })
    return out


async def _path_lines(conn, line_ids: list[int]) -> dict[str, Any]:
    row = await conn.fetchrow(
        """SELECT count(*) AS n, sum(coalesce(h.pipesectlength, 0))::float AS length_m,
                  avg(nullif(h.tuberoughness, 0))::float AS roughness_mm,
                  min(nullif(h.diameterinternal, 0))::float AS d_min, max(h.diameterinternal)::float AS d_max,
                  ST_AsGeoJSON(ST_Transform(ST_Simplify(ST_Collect(l.shape), 2), 4326), 6) AS geometry
             FROM linesobj l LEFT JOIN heatpipesections h ON h.lineid = l.id
            WHERE l.id = ANY($1::int[])""", line_ids)
    return {"lines": row["n"], "length_m": round(row["length_m"] or 0, 1),
            "roughness_mm": round(row["roughness_mm"], 3) if row["roughness_mm"] is not None else None,
            "d_min": row["d_min"], "d_max": row["d_max"],
            "geometry": json.loads(row["geometry"]) if row["geometry"] else None}


def neighbor_pairs(graph: nx.Graph, points: list[dict[str, Any]]) -> list[tuple[dict, dict, list[int]]]:
    """Соседние датчики одной трубы: кратчайший путь между ними не проходит через узел третьего датчика."""
    pairs = []
    for pipe in ("supply", "return"):
        pts = [p for p in points if p["pipe"] == pipe and p["node_id"] in graph]
        nodes = {p["node_id"] for p in pts}
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                if a["node_id"] == b["node_id"]:
                    continue
                try:
                    path = nx.shortest_path(graph, a["node_id"], b["node_id"], weight="weight")
                except nx.NetworkXNoPath:
                    continue
                if any(n in nodes for n in path[1:-1]):
                    continue
                pairs.append((a, b, path))
    return pairs


async def _pump_nodes(conn, nodes: list[int]) -> set[int]:
    if not await conn.fetchval("SELECT to_regclass('public.pumpstations') IS NOT NULL"):
        return set()
    return {r["nodeid"] for r in await conn.fetch(
        "SELECT nodeid FROM pumpstations WHERE nodeid = ANY($1::int[])", nodes)}


async def segments(conn, graph: nx.Graph) -> dict[str, Any]:
    """Пары соседних датчиков давления с потерями напора факт / модель и выводом.

    Направление — от большего напора модели к меньшему: вода течёт так, если между датчиками нет насоса (пары через
    насосную станцию пропускаются).
    """
    points = await _sensor_points(conn)
    pairs = neighbor_pairs(graph, points)
    pumps = await _pump_nodes(conn, sorted({n for _, _, path in pairs for n in path}))
    result: list[dict[str, Any]] = []
    skipped: list[str] = []
    for a, b, path in pairs:
        if b["h_model"] > a["h_model"]:
            a, b, path = b, a, path[::-1]
        label = f"{a['node_name'] or a['node_id']} → {b['node_name'] or b['node_id']}"
        if pumps.intersection(path):
            skipped.append(f"{label}: на пути насосная станция — напор не только теряется")
            continue
        dh_model = a["h_model"] - b["h_model"]
        dh_fact = a["h_fact"] - b["h_fact"]
        if dh_model < MIN_MODEL_DH_M:
            skipped.append(f"{label}: потери по модели {dh_model:.1f} м — меньше {MIN_MODEL_DH_M:g} м, "
                           "сравнение неустойчиво")
            continue
        line_ids = [graph.edges[u, v]["id"] for u, v in zip(path, path[1:])]
        lines = await _path_lines(conn, line_ids)
        if lines["length_m"] > MAX_PATH_M:
            skipped.append(f"{label}: {lines['length_m'] / 1000:.1f} км — слишком далеко для сравнения")
            continue
        ratio = dh_fact / dh_model
        unc = uncertainty(dh_model)
        factor = roughness_factor(ratio, unc)
        roughness = lines["roughness_mm"]
        suggested = None
        if factor is not None and roughness:
            lo, hi = ROUGHNESS_LIMITS_MM
            suggested = round(min(hi, max(lo, roughness * factor)), 3)
        result.append({
            "pipe": a["pipe"], "label": label,
            "from": {k: a[k] for k in ("sensor_id", "code", "node_id", "node_name")},
            "to": {k: b[k] for k in ("sensor_id", "code", "node_id", "node_name")},
            "calculation_id": a["calculation_id"],
            "dh_model": round(dh_model, 2), "dh_fact": round(dh_fact, 2), "ratio": round(ratio, 3),
            "uncertainty": round(unc, 3), **verdict(ratio, unc), "roughness_factor": factor, "roughness_mm": roughness,
            "roughness_suggested_mm": suggested, "line_ids": line_ids, **lines,
        })
    result.sort(key=lambda r: (r["status"] == "ok", -abs(r["ratio"] - 1)))
    return {"window_min": CAL_WINDOW_MIN, "accuracy_m": PRESSURE_ACCURACY_M, "segments": result, "skipped": skipped}
