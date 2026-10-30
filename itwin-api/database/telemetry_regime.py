"""Расчёт по фактическому режиму (фаза 3): напоры и температура источника из телеметрии → расчёт sety.

Граничные условия модели — узлы заданного напора (setpressnodes: источники, подкачки, вводы квартальных
фрагментов): напор подачи и обратки над отметкой, м; температура подачи — по температурному графику от Tн.
Датчики давления подачи / обратки и температуры подачи в таком узле дают фактический режим: расчёт с ними
(-zn_fakt, sety/read_gid.read_zn) показывает, как сеть работает сейчас, и остальные датчики сравниваются уже
с ним («факт против модели», калибровка).

Режим «изменился», когда факт отличается от граничных условий последнего расчёта фрагмента больше порога
(REGIME_DH_M, REGIME_DT_C) — окно «Телеметрия» предлагает перерасчёт; с TELEMETRY_REGIME_AUTO=1 перерасчёт
запускается сам (проверка — вместе с тревогами, раз в минуту), не чаще AUTO_EVERY_MIN на фрагмент.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from database.telemetry import STALE_MIN, UNITS, TelemetryError, _latest_calcs
from database.ut_out_columns import US_PIEZO_HEAD_M, US_SIGN_RETURN, US_SIGN_SUPPLY, US_TEMPERATURE_C

# Среднее за окно сглаживает шум и пульсации насосов
WINDOW_MIN = max(1, int(os.getenv("TELEMETRY_REGIME_WINDOW_MIN", "15") or 15))
# Порог «режим изменился»: больше погрешности пары датчиков (±0,5 м каждый) и шага регулирования на источнике
REGIME_DH_M = 2.0
REGIME_DT_C = 2.0
AUTO = os.getenv("TELEMETRY_REGIME_AUTO", "0") == "1"
AUTO_EVERY_MIN = max(15, int(os.getenv("TELEMETRY_REGIME_AUTO_MIN", "60") or 60))
AUTO_USER = "telemetry"
AUDIT_MARK = "fact"  # new_data.regime в журнале действий: запуски расчёта по факту
MAX_HEAD_M = 9999.0   # как в -zn_fakt (worker.SETY_PATTERN_FLAGS): до 4 знаков целой части
MAX_TEMP_C = 999.0


async def _points(conn) -> list[dict[str, Any]]:
    """Датчики в узлах заданного напора: давление подачи / обратки, температура подачи; среднее за окно."""
    if not await conn.fetchval("SELECT to_regclass('public.setpressnodes') IS NOT NULL"):
        return []
    rows = await conn.fetch(
        f"""SELECT s.id, s.code, s.kind, s.pipe, s.unit, s.node_id, n.fileid,
                   coalesce(nullif(n.nodename, ''), n.externalnodename) AS node_name,
                   sp.pressflow::float AS set_p1, sp.pressret::float AS set_p2,
                   r.avg_value, r.last_ts
              FROM tgid_sensor s
              JOIN setpressnodes sp ON sp.nodeid = s.node_id
              JOIN nodes n ON n.id = s.node_id AND coalesce(n.removed, 0) = 0
              LEFT JOIN LATERAL (
                  SELECT avg(value) AS avg_value, max(ts) AS last_ts FROM tgid_sensor_reading
                   WHERE sensor_id = s.id
                     AND ts > (SELECT max(ts) FROM tgid_sensor_reading WHERE sensor_id = s.id)
                              - interval '{WINDOW_MIN} minutes'
              ) r ON true
             WHERE s.active AND n.fileid IS NOT NULL
               AND (s.kind = 'pressure' OR (s.kind = 'temperature' AND s.pipe = 'supply'))
             ORDER BY n.fileid, s.node_id, s.id""")
    return [dict(r) for r in rows]


def group_nodes(rows: list[dict[str, Any]], now: datetime) -> list[dict[str, Any]]:
    """Строки датчиков → узлы с фактом (м над отметкой, °C); молчащие датчики факта не дают."""
    stale_before = now - timedelta(minutes=STALE_MIN)
    nodes: dict[int, dict[str, Any]] = {}
    for r in rows:
        node = nodes.setdefault(r["node_id"], {
            "node_id": r["node_id"], "fileid": r["fileid"], "node_name": r["node_name"],
            "set": {"p1": r["set_p1"], "p2": r["set_p2"]},
            "fact": {"p1": None, "p2": None, "t1": None}, "sensors": [], "silent": []})
        key = "t1" if r["kind"] == "temperature" else ("p1" if r["pipe"] == "supply" else "p2")
        node["sensors"].append(r["code"])
        unit = UNITS.get(r["unit"])
        if unit is None or r["avg_value"] is None or r["last_ts"] is None or r["last_ts"] < stale_before:
            node["silent"].append(r["code"])
            continue
        if node["fact"][key] is None:  # два датчика на одной трубе — первый по id
            node["fact"][key] = round(r["avg_value"] * unit.to_base, 2)
    return list(nodes.values())


def node_problem(fact: dict[str, Optional[float]]) -> Optional[str]:
    """Факт, который нельзя подавать в расчёт: перепутаны датчики или значение вне разумного."""
    p1, p2, t1 = fact["p1"], fact["p2"], fact["t1"]
    if all(v is None for v in (p1, p2, t1)):
        return "нет свежих показаний"
    if any(v is not None and not (0 <= v <= MAX_HEAD_M) for v in (p1, p2)):
        return "напор вне 0…9999 м — проверьте единицы датчика"
    if t1 is not None and not (0 <= t1 <= MAX_TEMP_C):
        return "температура вне 0…999 °C"
    if p1 is not None and p2 is not None and p1 <= p2:
        return "напор подачи не выше обратки — проверьте, не перепутаны ли датчики"
    return None


def changes(node: dict[str, Any]) -> list[str]:
    """Отличия факта от граничных условий последнего расчёта сверх порога — текстом."""
    out = []
    model, fact = node.get("model") or {}, node["fact"]
    for key, label, limit, unit in (("p1", "напор подачи", REGIME_DH_M, "м"), ("p2", "напор обратки", REGIME_DH_M, "м"),
                                    ("t1", "температура подачи", REGIME_DT_C, "°C")):
        if fact[key] is None or model.get(key) is None:
            continue
        if abs(fact[key] - model[key]) > limit:
            out.append(f"{label} {model[key]:g} → {fact[key]:g} {unit}".replace(".", ","))
    return out


def zn_spec(nodes: list[dict[str, Any]]) -> str:
    """Узлы с годным фактом → значение -zn_fakt: «узел:pP:pO:t1;…» (пустое — из базы)."""
    def num(v: Optional[float], digits: int) -> str:
        return "" if v is None else f"{round(v, digits):g}"

    items = [f"{n['node_id']}:{num(n['fact']['p1'], 2)}:{num(n['fact']['p2'], 2)}:{num(n['fact']['t1'], 1)}"
             for n in nodes if not n.get("problem")]
    return ";".join(items)


def _by_fact(calc_params: Optional[str]) -> bool:
    try:
        return bool(json.loads(calc_params or "{}").get("zn_fakt"))
    except (TypeError, ValueError):
        return False


async def _model_at(conn, nodes: list[dict[str, Any]], calcs: dict[int, dict[str, Any]]) -> None:
    pairs = [(n["node_id"], calcs[n["fileid"]]["id"]) for n in nodes if n["fileid"] in calcs]
    if not pairs:
        return
    rows = await conn.fetch(
        f"""SELECT u.nodeid, u.externalsign, u.{US_PIEZO_HEAD_M}::float AS head, u.{US_TEMPERATURE_C}::float AS t
              FROM us_out u JOIN unnest($1::int[], $2::int[]) AS q(node, calc)
                ON u.nodeid = q.node AND u.calculationid = q.calc""",
        [p[0] for p in pairs], [p[1] for p in pairs])
    model: dict[int, dict[str, Optional[float]]] = {}
    for r in rows:
        m = model.setdefault(r["nodeid"], {"p1": None, "p2": None, "t1": None})
        if r["externalsign"] == US_SIGN_SUPPLY:
            m["p1"] = round(r["head"], 2) if r["head"] is not None else None
            m["t1"] = round(r["t"], 1) if r["t"] is not None else None
        elif r["externalsign"] == US_SIGN_RETURN:
            m["p2"] = round(r["head"], 2) if r["head"] is not None else None
    for n in nodes:
        n["model"] = model.get(n["node_id"])


async def regime(conn) -> dict[str, Any]:
    """Фрагменты с датчиками в узлах заданного напора: граничные условия последнего расчёта против факта."""
    nodes = group_nodes(await _points(conn), datetime.now(timezone.utc))
    fileids = sorted({n["fileid"] for n in nodes})
    calcs = await _latest_calcs(conn, fileids) if fileids else {}
    await _model_at(conn, nodes, calcs)
    info = {r["id"]: r for r in await conn.fetch(
        "SELECT id, tn, name, user_gid, calc_params FROM calculation WHERE id = ANY($1::int[])",
        [c["id"] for c in calcs.values()])} if calcs else {}
    names = {r["id"]: r["name"] for r in await conn.fetch(
        "SELECT id, name FROM fragments WHERE id = ANY($1::int[])", fileids)} if fileids else {}
    fragments = []
    for fileid in fileids:
        own = [n for n in nodes if n["fileid"] == fileid]
        for n in own:
            n["problem"] = node_problem(n["fact"])
            n["changes"] = [] if n["problem"] else changes(n)
        calc = calcs.get(fileid)
        row = info.get(calc["id"]) if calc else None
        usable = [n for n in own if not n["problem"]]
        fragments.append({
            "fileid": fileid, "name": names.get(fileid),
            "calculation": None if calc is None else {
                **calc, "tn": row["tn"] if row else None, "name": row["name"] if row else None,
                "user": row["user_gid"] if row else None, "by_fact": _by_fact(row["calc_params"] if row else None)},
            "nodes": own,
            "can_run": bool(usable),
            "recalc_needed": bool(usable) and (calc is None or any(n["changes"] for n in usable)),
        })
    return {"window_min": WINDOW_MIN, "thresholds": {"head_m": REGIME_DH_M, "temp_c": REGIME_DT_C},
            "auto": AUTO, "auto_every_min": AUTO_EVERY_MIN, "fragments": fragments}


# --- запуск ------------------------------------------------------------------------------------

async def _tn_range(conn) -> tuple[Optional[float], Optional[float]]:
    row = await conn.fetchrow("SELECT t_or, t_vnew FROM heatsystem ORDER BY id LIMIT 1")
    if not row:
        return None, None
    return (float(row["t_or"]) if row["t_or"] is not None else None,
            float(row["t_vnew"]) if row["t_vnew"] is not None else None)


async def _tn_now(conn, t_or: Optional[float], t_vnew: Optional[float]) -> Optional[float]:
    """Температура воздуха текущего часа (database/weather.py), округлённая и зажатая в диапазон графика."""
    from database import weather

    if not await conn.fetchval("SELECT to_regclass('public.tgid_weather') IS NOT NULL"):
        return None
    now = weather.hour_utc(datetime.now(timezone.utc))
    rows = await weather.hourly(conn, now, now + timedelta(hours=1))
    if not rows:
        return None
    tn = float(round(rows[0]["t_air"]))
    if t_or is not None:
        tn = max(tn, t_or)
    if t_vnew is not None:
        tn = min(tn, t_vnew)
    return tn


async def prepare(conn, fileid: int, *, tn: Optional[float], mode: Literal["plan", "emergency"],
                  user: str) -> dict[str, Any]:
    """Строка параметров sety для расчёта фрагмента по факту; TelemetryError — нечего подавать или Tн вне графика.

    Tн по умолчанию — температура воздуха текущего часа (tgid_weather: факт, иначе прогноз) в пределах графика
    [t_or; t_vnew], без погоды — Tн последнего расчёта фрагмента (иначе расчётная t_or).
    """
    from sety_modes import SetyRunRequest, args_to_params, build_sety_args, tn_range_error
    from worker import validate_sety_params

    state = await regime(conn)
    fragment = next((f for f in state["fragments"] if f["fileid"] == fileid), None)
    if fragment is None:
        raise TelemetryError(404, "В узлах заданного напора фрагмента нет датчиков давления или температуры")
    if not fragment["can_run"]:
        problems = "; ".join(f"{n['node_name'] or n['node_id']}: {n['problem']}" for n in fragment["nodes"])
        raise TelemetryError(409, f"Нет годных показаний для расчёта — {problems}")
    t_or, t_vnew = await _tn_range(conn)
    if tn is None:
        tn = await _tn_now(conn, t_or, t_vnew)
    if tn is None:
        last_tn = (fragment["calculation"] or {}).get("tn")
        tn = last_tn if last_tn is not None else (t_or if t_or is not None else -25.0)
    error = tn_range_error(tn, t_or, t_vnew, leto=False)
    if error:
        raise TelemetryError(422, error)
    # плановый — с расходами по температурному графику (-tg): при Tн не расчётной «по удельным» оставляет
    # расходы расчётными и даёт неправдоподобную обратку (на стенде при +6 °C — 18 °C вместо 41 °C по графику)
    req = SetyRunRequest(mode=mode, fragment_ids=[fileid], tn=tn, tg=mode == "plan",
                         name=f"По факту {datetime.now().astimezone():%d.%m.%Y %H:%M}")
    spec = zn_spec(fragment["nodes"])
    params = args_to_params(build_sety_args(req, user) + ["-zn_fakt", spec])
    try:
        validate_sety_params(params)
    except ValueError as exc:  # билдер и белый список воркера разошлись — не ставить в очередь
        raise TelemetryError(400, str(exc)) from exc
    return {"fileid": fileid, "mode": mode, "tn": tn, "params": params, "zn_fakt": spec,
            "nodes": [n for n in fragment["nodes"] if not n["problem"]]}


def dispatch(prepared: dict[str, Any]) -> dict[str, Any]:
    """В очередь Celery так же, как «Расчёт» (routers/calc.run_sety_mode, один фрагмент)."""
    from worker import run_sety_calculation

    request_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
    params = f"{prepared['params']} -fileID {prepared['fileid']}"
    if prepared["mode"] == "plan":
        task = run_sety_calculation.delay(params, request_id)
    else:
        task = run_sety_calculation.delay(params, request_id, dross=False)
    return {"task_id": task.id, "request_id": request_id}


def audit_data(prepared: dict[str, Any], queued: dict[str, Any], *, auto: bool) -> dict[str, Any]:
    return {"regime": AUDIT_MARK, "auto": auto, "fileid": prepared["fileid"], "mode": prepared["mode"],
            "tn": prepared["tn"], "zn_fakt": prepared["zn_fakt"], "params": prepared["params"], **queued}


async def _recent_launch(conn, fileid: int) -> bool:
    return bool(await conn.fetchval(
        """SELECT 1 FROM audit_log
            WHERE operation = 'RUN_SETY' AND table_name = 'calculation'
              AND new_data->>'regime' = $1 AND new_data->>'fileid' = $2
              AND changed_at > localtimestamp - make_interval(mins => $3) LIMIT 1""",
        AUDIT_MARK, str(fileid), AUTO_EVERY_MIN))


async def auto_recalc(conn) -> list[int]:
    """Оперативный перерасчёт по событию «режим источника изменился» (TELEMETRY_REGIME_AUTO=1).

    Вызывается под замком тревог (database/webhooks.check_sensor_alerts): один процесс на город. Не чаще
    AUTO_EVERY_MIN на фрагмент — считая и ручные запуски по факту (журнал действий).
    """
    if not AUTO:
        return []
    from audit import write_audit_log

    launched = []
    for fragment in (await regime(conn))["fragments"]:
        if not fragment["recalc_needed"] or await _recent_launch(conn, fragment["fileid"]):
            continue
        try:
            prepared = await prepare(conn, fragment["fileid"], tn=None, mode="plan", user=AUTO_USER)
        except TelemetryError:
            continue  # Tн вне графика и т. п. — ждать ручного запуска
        queued = dispatch(prepared)
        await write_audit_log(changed_by=AUTO_USER, operation="RUN_SETY", table_name="calculation",
                              new_data=audit_data(prepared, queued, auto=True))
        launched.append(fragment["fileid"])
    return launched

