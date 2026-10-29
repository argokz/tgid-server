"""Сравнение расчёта сценария с расчётом основы (сценарии «что если», шаг 2).

Сценарий считается как любой фрагмент (database/scenarios.py: копия фрагмента) — у него свой
calculationid. Здесь два расчёта сводятся по соответствию объектов tgid_scenario_object:
потребитель (pt_out) — по узлу присоединения, участок (ut_out, строка подачи) — по участку.

Потребитель:
  * располагаемый напор в узле присоединения — pt_out.a23, м;
  * теплообеспеченность — pt_out.q_obesp_min, % (ниже 100 — недотоп);
  * расход сетевой воды — a15 (закрытая система) + a16 (из подачи в открытой), т/ч.
  Необходимый напор (gneob) sety в плановом расчёте не заполняет (в Алматы 0 у всех) — по нему
  дефицит не определяется.
Участок: расход a13 (по модулю), скорость a10, удельные потери a14 (мм/м → Па/м), пороги — как
у тематической карты расчёта (database/calculations.py).

Объект есть в результатах основы, но не сценария — «не рассчитан»: sety не пишет результат
отключённой части сети. Только чтение.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from database.calculations import SPEC_LOSS_LIMIT_PA_M, VELOCITY_HIGH_MS
from database.regime_queries import attach_coords
from database.scenarios import OBJECT_TABLE, SCENARIO_TABLE
from database.ut_out_columns import (
    UT_FLOW_TH,
    UT_SIGN_SUPPLY,
    UT_SPEC_LOSS_MM_M,
    UT_VELOCITY_MS,
    spec_loss_pa_per_m,
)

UNDERHEAT_PCT = 100.0     # теплообеспеченность ниже — недотоп
HEAD_DELTA_M = 0.5        # заметное изменение располагаемого напора, м
SUPPLY_DELTA_PCT = 1.0    # заметное изменение теплообеспеченности, п.п.
FLOW_DELTA_TH = 1.0       # заметное изменение расхода на участке, т/ч ...
FLOW_DELTA_REL = 0.05     # ... и не меньше 5 % от расхода основы
ITEMS_LIMIT = 300

# Порядок важности изменений в списке
CHANGE_KINDS = {
    "became_underheated": "Стал недотоп",
    "lost": "Не рассчитан в сценарии (отключён)",
    "became_overloaded": "Участок перегружен",
    "became_fast": "Скорость выше нормы",
    "recovered": "Недотоп устранён",
    "relieved": "Перегрузка снята",
    "new": "Новый в сценарии",
    "changed": "Изменился режим",
}


class ScenarioCompareError(ValueError):
    """Расчёты нельзя сравнить (понятная пользователю причина)."""


async def _calculation(conn, calculation_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        "SELECT id, fileid, tn::float AS tn, date1, name, calc_params FROM calculation WHERE id = $1",
        calculation_id)
    if row is None:
        return None
    params = row["calc_params"]
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except ValueError:
            params = {}
    return {"id": row["id"], "fileid": row["fileid"], "tn": row["tn"], "name": row["name"] or None,
            "date": row["date1"].isoformat() if row["date1"] else None,
            "emergency": bool((params or {}).get("g_is_avar"))}


def _f(v: Any) -> Optional[float]:
    return None if v is None else float(v)


def _delta(a: Optional[float], b: Optional[float]) -> Optional[float]:
    return None if a is None or b is None else round(b - a, 3)


def consumer_change(base: Optional[dict], scen: Optional[dict]) -> Optional[str]:
    """Вид изменения потребителя; None — несущественно."""
    if scen is None:
        return "lost"
    if base is None:
        return "new"
    b_under = base["supply"] is not None and base["supply"] < UNDERHEAT_PCT
    s_under = scen["supply"] is not None and scen["supply"] < UNDERHEAT_PCT
    if s_under and not b_under:
        return "became_underheated"
    if b_under and not s_under:
        return "recovered"
    dh = _delta(base["head"], scen["head"])
    ds = _delta(base["supply"], scen["supply"])
    if (dh is not None and abs(dh) >= HEAD_DELTA_M) or (ds is not None and abs(ds) >= SUPPLY_DELTA_PCT):
        return "changed"
    return None


def line_change(base: Optional[dict], scen: Optional[dict]) -> Optional[str]:
    """Вид изменения участка; None — несущественно."""
    if scen is None:
        return "lost"
    if base is None:
        return "new"
    if scen["loss"] > SPEC_LOSS_LIMIT_PA_M >= base["loss"]:
        return "became_overloaded"
    if scen["velocity"] > VELOCITY_HIGH_MS >= base["velocity"]:
        return "became_fast"
    if base["loss"] > SPEC_LOSS_LIMIT_PA_M >= scen["loss"]:
        return "relieved"
    df = abs(scen["flow"] - base["flow"])
    if df >= FLOW_DELTA_TH and df >= FLOW_DELTA_REL * max(base["flow"], 1e-9):
        return "changed"
    return None


async def _consumers(conn, calculation_id: int) -> dict[int, dict]:
    rows = await conn.fetch(
        """SELECT DISTINCT ON (nodeid) nodeid, a23, q_obesp_min, a15, a16, qfact
             FROM pt_out WHERE calculationid = $1 ORDER BY nodeid, id""", calculation_id)
    return {r["nodeid"]: {"head": _f(r["a23"]), "supply": _f(r["q_obesp_min"]),
                          "flow": (_f(r["a15"]) or 0.0) + (_f(r["a16"]) or 0.0), "load": _f(r["qfact"]) or 0.0}
            for r in rows}


async def _lines(conn, calculation_id: int) -> dict[int, dict]:
    rows = await conn.fetch(
        f"""SELECT DISTINCT ON (lineid) lineid, {UT_FLOW_TH} AS flow, {UT_VELOCITY_MS} AS velocity,
                   {UT_SPEC_LOSS_MM_M} AS spec_loss
              FROM ut_out WHERE calculationid = $1 AND externalsignlineid = $2 ORDER BY lineid, id""",
        calculation_id, UT_SIGN_SUPPLY)
    return {r["lineid"]: {"flow": abs(_f(r["flow"]) or 0.0), "velocity": abs(_f(r["velocity"]) or 0.0),
                          "loss": spec_loss_pa_per_m(abs(_f(r["spec_loss"]) or 0.0))}
            for r in rows}


def _pair(base: dict[int, dict], scen: dict[int, dict], copy_to_base: dict[int, int]):
    """(id основы | None, id в сценарии | None, строка основы, строка сценария) для всех объектов."""
    base_to_copy = {b: c for c, b in copy_to_base.items()}
    for base_id, row in base.items():
        copy_id = base_to_copy.get(base_id)
        yield base_id, copy_id, row, scen.get(copy_id) if copy_id is not None else None
    for copy_id, row in scen.items():
        if copy_to_base.get(copy_id) not in base:
            yield copy_to_base.get(copy_id), copy_id, None, row


async def compare_scenario_calculations(
    conn, scenario_id: int, base_calculation_id: int, scenario_calculation_id: int, limit: int = ITEMS_LIMIT,
) -> Optional[dict[str, Any]]:
    """Сводка и список существенных изменений режима. None — сценария нет."""
    sc = await conn.fetchrow(
        f"SELECT id, name, base_fileid, fileid FROM {SCENARIO_TABLE} WHERE id = $1", scenario_id)
    if sc is None:
        return None
    base_calc = await _calculation(conn, base_calculation_id)
    scen_calc = await _calculation(conn, scenario_calculation_id)
    if base_calc is None or scen_calc is None:
        raise LookupError("Расчёт не найден")
    if base_calc["fileid"] != sc["base_fileid"]:
        raise ScenarioCompareError(f"Расчёт {base_calculation_id} — не по фрагменту-основе #{sc['base_fileid']}")
    if scen_calc["fileid"] != sc["fileid"]:
        raise ScenarioCompareError(f"Расчёт {scenario_calculation_id} — не по фрагменту сценария #{sc['fileid']}")
    warnings = []
    if base_calc["tn"] != scen_calc["tn"]:
        warnings.append(f"Разная температура наружного воздуха: {base_calc['tn']:g} и {scen_calc['tn']:g} °C")
    if base_calc["emergency"] != scen_calc["emergency"]:
        warnings.append("Разные режимы расчёта: плановый и аварийный (фактический)")

    maps: dict[str, dict[int, int]] = {"nodes": {}, "linesobj": {}}
    for r in await conn.fetch(
            f"""SELECT table_name, base_id, copy_id FROM {OBJECT_TABLE}
                 WHERE scenario_id = $1 AND table_name IN ('nodes', 'linesobj')""", scenario_id):
        maps[r["table_name"]][r["copy_id"]] = r["base_id"]

    base_cons, scen_cons = await _consumers(conn, base_calc["id"]), await _consumers(conn, scen_calc["id"])
    base_lines, scen_lines = await _lines(conn, base_calc["id"]), await _lines(conn, scen_calc["id"])

    items: list[dict[str, Any]] = []
    cons_counts = {k: 0 for k in ("became_underheated", "recovered", "lost", "new", "changed")}
    for base_id, copy_id, b, s in _pair(base_cons, scen_cons, maps["nodes"]):
        kind = consumer_change(b, s)
        if kind is None:
            continue
        cons_counts[kind] += 1
        items.append({
            "object": "consumer", "kind": kind, "base_id": base_id, "copy_id": copy_id,
            "anchor_type": "node", "anchor_id": copy_id or base_id,
            "head": [b and b["head"], s and s["head"]], "supply": [b and b["supply"], s and s["supply"]],
            "flow": [b and round(b["flow"], 3), s and round(s["flow"], 3)],
        })
    line_counts = {k: 0 for k in ("became_overloaded", "became_fast", "relieved", "lost", "new", "changed")}
    for base_id, copy_id, b, s in _pair(base_lines, scen_lines, maps["linesobj"]):
        kind = line_change(b, s)
        if kind is None:
            continue
        line_counts[kind] += 1
        items.append({
            "object": "line", "kind": kind, "base_id": base_id, "copy_id": copy_id,
            "anchor_type": "line", "anchor_id": copy_id or base_id,
            "flow": [b and round(b["flow"], 3), s and round(s["flow"], 3)],
            "velocity": [b and round(b["velocity"], 3), s and round(s["velocity"], 3)],
            "loss": [b and round(b["loss"], 1), s and round(s["loss"], 1)],
        })

    order = {k: i for i, k in enumerate(CHANGE_KINDS)}

    def magnitude(i: dict) -> float:
        pair = i.get("head") if i["object"] == "consumer" else i.get("flow")
        a, b = pair if pair else (None, None)
        return abs((b or 0) - (a or 0))

    # внутри вида — сначала потребители: последствия для людей важнее участков
    items.sort(key=lambda i: (order[i["kind"]], i["object"] != "consumer", -magnitude(i), i["anchor_id"] or 0))
    total = len(items)
    items = items[:limit]
    await _attach(conn, items)

    def underheated(rows: dict[int, dict]) -> int:
        return sum(1 for r in rows.values() if r["supply"] is not None and r["supply"] < UNDERHEAT_PCT)

    return {
        "scenario_id": sc["id"],
        "name": sc["name"],
        "base_calculation": base_calc,
        "scenario_calculation": scen_calc,
        "warnings": warnings,
        "consumers": {
            "base": len(base_cons), "scenario": len(scen_cons),
            "underheated_base": underheated(base_cons), "underheated_scenario": underheated(scen_cons),
            "load_base": round(sum(r["load"] for r in base_cons.values()), 3),
            "load_scenario": round(sum(r["load"] for r in scen_cons.values()), 3),
            "flow_base": round(sum(r["flow"] for r in base_cons.values()), 1),
            "flow_scenario": round(sum(r["flow"] for r in scen_cons.values()), 1),
            **cons_counts,
        },
        "lines": {
            "base": len(base_lines), "scenario": len(scen_lines),
            "overloaded_base": sum(1 for r in base_lines.values() if r["loss"] > SPEC_LOSS_LIMIT_PA_M),
            "overloaded_scenario": sum(1 for r in scen_lines.values() if r["loss"] > SPEC_LOSS_LIMIT_PA_M),
            **line_counts,
        },
        "thresholds": {"underheat_pct": UNDERHEAT_PCT, "head_delta_m": HEAD_DELTA_M,
                       "spec_loss_pa_m": SPEC_LOSS_LIMIT_PA_M, "velocity_ms": VELOCITY_HIGH_MS},
        "kinds": CHANGE_KINDS,
        "total": total,
        "truncated": total > len(items),
        "items": items,
    }


async def _attach(conn, items: list[dict[str, Any]]) -> None:
    """Название узла и координаты (узел — точка, участок — середина)."""
    node_ids = sorted({i["anchor_id"] for i in items if i["anchor_type"] == "node" and i["anchor_id"]})
    names = {r["id"]: (r["externalnodename"] or "").strip() or None for r in await conn.fetch(
        "SELECT id, externalnodename FROM nodes WHERE id = ANY($1::int[])", node_ids)}
    nodes = [{"node_id": i["anchor_id"]} for i in items if i["anchor_type"] == "node"]
    lines = [{"line_id": i["anchor_id"]} for i in items if i["anchor_type"] == "line"]
    await attach_coords(conn, nodes, key="node_id")
    await attach_coords(conn, lines, key="line_id")
    coords = {("node", n["node_id"]): n for n in nodes}
    coords.update({("line", ln["line_id"]): ln for ln in lines})
    for i in items:
        c = coords.get((i["anchor_type"], i["anchor_id"]), {})
        i["lat"], i["lng"] = c.get("latitude"), c.get("longitude")
        i["name"] = names.get(i["anchor_id"]) if i["anchor_type"] == "node" else None
