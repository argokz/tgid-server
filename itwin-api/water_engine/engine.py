"""Расчётный движок водопровода (фаза 4): модель EPANET (.inp) → сеть и гидравлический расчёт через WNTR.

WNTR (Sandia, BSD) читает модель EPANET и считает её встроенным EPANET 2.2 (EpanetSimulator). Движок — отдельная
служба со своей средой (water_engine/requirements-water.txt): ТГИД (API) не тянет numpy / scipy / pandas и WNTR, а
обращается к ней по HTTP (water_engine/service.py, WATER_ENGINE_URL).

Единицы ответа — СИ, как принято в ТГИД: напор и давление — м вод. ст., расход и отбор — л/с, скорость — м/с,
удельные потери напора — м/км, длина и отметки — м, диаметр — мм. Модели в американских единицах (GPM, футы)
WNTR переводит сам при чтении.
"""
from __future__ import annotations

import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Optional

import wntr

MAX_INP_BYTES = 20_000_000
MAX_DURATION_H = 24 * 7
MAX_NODES = 50_000
LOW_PRESSURE_M = 10.0        # ниже — недостаточный напор у потребителя (СП 31.13330: не меньше 10 м на 1 этаж)
HIGH_VELOCITY_MS = 2.0
LEAK_CD = 0.75               # коэффициент расхода отверстия (свищ, раскрытие стыка)
MAX_LEAKS = 20
MAX_LEAK_AREA_CM2 = 500.0
MAX_CLOSED_LINKS = 2000
SHORT_SUPPLY_SHARE = 0.9     # подано меньше 90 % нужного — недоподача
MAX_SHORT_NODES = 500
G = 9.81
DEMAND_AVG_S = 24 * 3600


class EngineError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _r(v: Any, digits: int = 3) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f, digits) if math.isfinite(f) else None


def library() -> list[dict[str, Any]]:
    """Учебные сети, которые идут с WNTR (Net1–Net6 EPANET, ky4 / ky10 — сети Кентукки)."""
    from wntr.library import model_library

    out = []
    for name in model_library.model_name_list:
        out.append({"name": name, "file": Path(model_library.get_filepath(name)).name})
    return out


def load(inp_text: Optional[str] = None, library_name: Optional[str] = None) -> wntr.network.WaterNetworkModel:
    """Модель из текста .inp или из учебной библиотеки WNTR."""
    if library_name:
        from wntr.library import model_library

        if library_name not in model_library.model_name_list:
            raise EngineError(404, f"Нет учебной сети «{library_name}»: {', '.join(model_library.model_name_list)}")
        return model_library.get_model(library_name)
    if not inp_text:
        raise EngineError(422, "Нужен текст модели EPANET (.inp) или имя учебной сети")
    if len(inp_text.encode("utf-8")) > MAX_INP_BYTES:
        raise EngineError(413, "Модель больше 20 МБ")
    with tempfile.TemporaryDirectory(prefix="tgid-water-") as tmp:
        path = Path(tmp) / "model.inp"
        path.write_text(inp_text, encoding="utf-8")
        try:
            wn = wntr.network.WaterNetworkModel(str(path))
        except Exception as exc:  # noqa: BLE001 — ошибки разбора WNTR разнородны: ответ — текстом
            raise EngineError(422, f"Модель EPANET не читается: {exc}") from exc
    if wn.num_nodes > MAX_NODES:
        raise EngineError(413, f"Узлов больше {MAX_NODES}")
    return wn


def inp_text(wn: wntr.network.WaterNetworkModel) -> str:
    """Модель обратно в текст .inp (учебная сеть — чтобы ТГИД хранил ровно то, что считал)."""
    with tempfile.TemporaryDirectory(prefix="tgid-water-") as tmp:
        path = Path(tmp) / "model.inp"
        wntr.network.write_inpfile(wn, str(path))
        return path.read_text(encoding="utf-8")


def average_demand(wn: wntr.network.WaterNetworkModel) -> dict[str, Optional[float]]:
    """Средний за сутки отбор узлов по графикам отбора (все категории), л/с."""
    step = wn.options.time.pattern_timestep or 3600
    expected = wntr.metrics.expected_demand(wn, start_time=0, end_time=DEMAND_AVG_S, timestep=step)
    return {str(col): _r(float(expected[col].mean()) * 1000, 4) for col in expected.columns}


def describe(wn: wntr.network.WaterNetworkModel) -> dict[str, Any]:
    """Сеть модели: узлы (колодцы-узлы, резервуары, баки) и участки (трубы, насосы, арматура) с координатами модели.
    У узла — базовый отбор и средний за сутки по графикам (avg_demand_ls): базовый бывает условным — у Net3 узел 203
    задан как 1 GPM с множителем графика ~4500."""
    avg = average_demand(wn)
    nodes = []
    for name, n in wn.nodes():
        item: dict[str, Any] = {"id": name, "type": n.node_type, "x": _r(n.coordinates[0], 4), "y": _r(n.coordinates[1], 4),
                                "elevation": _r(getattr(n, "elevation", None), 2)}
        if n.node_type == "Junction":
            item["base_demand_ls"] = _r((n.base_demand or 0) * 1000, 4)
            item["avg_demand_ls"] = avg.get(name)
        elif n.node_type == "Reservoir":
            item["head"] = _r(n.base_head, 2)
        elif n.node_type == "Tank":
            item.update(init_level=_r(n.init_level, 2), min_level=_r(n.min_level, 2), max_level=_r(n.max_level, 2),
                        diameter_m=_r(n.diameter, 2))
        nodes.append(item)
    links = []
    for name, link in wn.links():
        item = {"id": name, "type": link.link_type, "start": link.start_node_name, "end": link.end_node_name,
                "vertices": [[_r(x, 4), _r(y, 4)] for x, y in link.vertices]}
        if link.link_type == "Pipe":
            item.update(length_m=_r(link.length, 2), diameter_mm=_r(link.diameter * 1000, 1),
                        roughness=_r(link.roughness, 3), status=str(link.initial_status))
        elif link.link_type == "Pump":
            item.update(pump_type=link.pump_type)
        else:
            item.update(valve_type=getattr(link, "valve_type", None), diameter_mm=_r(link.diameter * 1000, 1))
        links.append(item)
    t = wn.options.time
    return {
        "summary": wn.describe(),
        "units_in_file": wn.options.hydraulic.inpfile_units,
        "headloss_formula": wn.options.hydraulic.headloss,
        "duration_h": _r(t.duration / 3600, 3), "report_step_h": _r(t.report_timestep / 3600, 3),
        "nodes": nodes, "links": links,
    }


def add_leaks(wn: wntr.network.WaterNetworkModel, leaks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Утечки как истечение из отверстия в узле: Q = Cd·A·√(2g)·P^0,5 — излучатель (emitter) EPANET, расход зависит
    от давления. Излучатель узла, если был, сохраняется: коэффициент утечки прибавляется к нему."""
    if len(leaks) > MAX_LEAKS:
        raise EngineError(422, f"Утечек в сценарии — не больше {MAX_LEAKS}")
    junctions = set(wn.junction_name_list)
    out = []
    for leak in leaks:
        node, area = str(leak.get("node") or ""), float(leak.get("area_cm2") or 0)
        if node not in junctions:
            raise EngineError(422, f"Утечка — только в узле сети (Junction), «{node}» не узел")
        if not 0 < area <= MAX_LEAK_AREA_CM2:
            raise EngineError(422, f"Площадь отверстия — больше 0 и до {MAX_LEAK_AREA_CM2:g} см²")
        coef = LEAK_CD * area * 1e-4 * math.sqrt(2 * G)
        j = wn.get_node(node)
        j.emitter_coefficient = (j.emitter_coefficient or 0) + coef
        out.append({"node": node, "area_cm2": area, "coef": coef})
    return out


def _supply(wn: wntr.network.WaterNetworkModel, res, junctions: set[str]) -> dict[str, Any]:
    """Недоподача при отборе по давлению (PDD): нужно (по графикам отбора) против поданного, средние за период, л/с.
    Узлы с подачей меньше SHORT_SUPPLY_SHARE нужного — по убыванию недоподачи."""
    t = wn.options.time
    expected = wntr.metrics.expected_demand(wn, start_time=0, end_time=t.duration, timestep=t.report_timestep)
    delivered = res.node["demand"]
    cols = [c for c in delivered.columns if c in junctions and c in expected.columns]
    need = expected[cols].mean() * 1000
    got = delivered[cols].reindex(expected.index, method="nearest").mean() * 1000
    short = []
    for node in cols:
        n, g = float(need[node]), float(got[node])
        if n > 1e-6 and g < SHORT_SUPPLY_SHARE * n:
            short.append({"node": str(node), "expected_ls": _r(n, 3), "delivered_ls": _r(max(g, 0.0), 3)})
    short.sort(key=lambda s: (s["delivered_ls"] or 0) - (s["expected_ls"] or 0))
    return {"expected_ls": _r(float(need.sum()), 2), "delivered_ls": _r(float(got.clip(lower=0).sum()), 2),
            "short_nodes": len(short), "short": short[:MAX_SHORT_NODES],
            "required_pressure_m": LOW_PRESSURE_M}


_HALT = re.compile(r"System unbalanced at ([\d:]+) hrs\.\s*EXECUTION HALTED", re.I)
_ERROR = re.compile(r"Error (\d+):\s*(.+)")


def halt_reason(rpt: Path) -> Optional[str]:
    """Почему EPANET остановил расчёт — из его отчёта (.rpt): WNTR в этом случае падает уже на чтении пустых
    результатов, и его текст ни о чём не говорит."""
    try:
        text = rpt.read_text(encoding="latin-1")
    except OSError:
        return None
    if m := _HALT.search(text):
        return (f"система не сбалансирована в {m.group(1)} — расчёт остановлен: сеть в таком состоянии не может "
                "подать воду (насосы не дают напор, нет пути от источников)")
    if m := _ERROR.search(text):
        return f"ошибка EPANET {m.group(1)}: {m.group(2).strip()}"
    return None


def close_links(wn: wntr.network.WaterNetworkModel, links: list[str]) -> list[str]:
    """Закрыть участки (отключение): статус «закрыт» и снять правила управления, которые их затрагивают — иначе
    EPANET откроет участок снова (у Net3 насос 10 включается по времени). Возвращает имена снятых правил."""
    if len(links) > MAX_CLOSED_LINKS:
        raise EngineError(422, f"Закрываемых участков — не больше {MAX_CLOSED_LINKS}")
    names = set(wn.link_name_list)
    missing = [x for x in links if x not in names]
    if missing:
        raise EngineError(422, f"Нет участков в модели: {', '.join(missing[:10])}")
    closing = set(links)
    removed = []
    for cname, control in list(wn.controls()):
        if any(getattr(obj, "name", None) in closing for obj in control.requires()):
            wn.remove_control(cname)
            removed.append(cname)
    for name in links:
        wn.get_link(name).initial_status = wntr.network.LinkStatus.Closed
    return removed


def simulate(wn: wntr.network.WaterNetworkModel, *, duration_h: Optional[float] = None,
             report_step_h: Optional[float] = None, leaks: Optional[list[dict[str, Any]]] = None,
             closed_links: Optional[list[str]] = None, demand_model: str = "DDA") -> dict[str, Any]:
    """Гидравлический расчёт EPANET 2.2 по периоду модели (или заданному): значения по узлам и участкам на каждый
    шаг отчёта и сводка — давление ниже LOW_PRESSURE_M, скорость выше HIGH_VELOCITY_MS, отрицательное давление.
    leaks — сценарий утечек [{node, area_cm2}]: расход утечки по шагам — в summary.leaks.
    closed_links — закрытые участки (отключение). demand_model="PDD" — отбор зависит от давления (полный при
    LOW_PRESSURE_M и выше, нет при 0): отрезанные узлы получают ноль, а не бессмысленное давление, как в DDA;
    недоподача по узлам — в summary.supply."""
    if demand_model not in ("DDA", "PDD"):
        raise EngineError(422, "Режим отбора — DDA или PDD")
    leak_items = add_leaks(wn, leaks or [])
    removed_controls = close_links(wn, closed_links or [])
    if demand_model == "PDD":
        wn.options.hydraulic.demand_model = "PDD"
        wn.options.hydraulic.required_pressure = LOW_PRESSURE_M
        wn.options.hydraulic.minimum_pressure = 0.0
    if duration_h is not None:
        if not 0 <= duration_h <= MAX_DURATION_H:
            raise EngineError(422, f"Период расчёта — от 0 до {MAX_DURATION_H} ч")
        wn.options.time.duration = int(duration_h * 3600)
    if report_step_h is not None:
        if report_step_h <= 0:
            raise EngineError(422, "Шаг отчёта — больше нуля")
        wn.options.time.report_timestep = int(report_step_h * 3600)
        wn.options.time.hydraulic_timestep = min(wn.options.time.hydraulic_timestep, int(report_step_h * 3600))
    wn.options.quality.parameter = "NONE"  # только гидравлика: качество воды — следующий шаг
    with tempfile.TemporaryDirectory(prefix="tgid-water-") as tmp:
        try:
            res = wntr.sim.EpanetSimulator(wn).run_sim(file_prefix=os.path.join(tmp, "run"))
        except Exception as exc:  # noqa: BLE001 — ошибка EPANET (несвязная сеть, нет источника): ответ — текстом
            reason = halt_reason(Path(tmp) / "run.rpt")
            raise EngineError(422, f"Расчёт EPANET не выполнен: {reason or exc}") from exc
    times = [int(t) for t in res.node["pressure"].index]
    junctions = set(wn.junction_name_list)
    pipes = set(wn.pipe_name_list)

    def table(frame, scale: float = 1.0, digits: int = 3) -> dict[str, list[Optional[float]]]:
        return {str(col): [_r(v * scale, digits) for v in frame[col].tolist()] for col in frame.columns}

    pressure = res.node["pressure"]
    velocity = res.link["velocity"]
    junction_pressure = pressure[[c for c in pressure.columns if c in junctions]]
    pipe_velocity = velocity[[c for c in velocity.columns if c in pipes]]
    low = junction_pressure.lt(LOW_PRESSURE_M)
    negative = junction_pressure.lt(0)
    fast = pipe_velocity.gt(HIGH_VELOCITY_MS)
    summary = {
        "steps": len(times),
        "min_pressure_m": _r(junction_pressure.min().min(), 2),
        "max_pressure_m": _r(junction_pressure.max().max(), 2),
        "max_velocity_ms": _r(pipe_velocity.abs().max().max(), 2),
        "low_pressure_nodes": sorted(str(c) for c in low.columns[low.any()]),
        "negative_pressure_nodes": sorted(str(c) for c in negative.columns[negative.any()]),
        "high_velocity_pipes": sorted(str(c) for c in fast.columns[fast.any()]),
        "thresholds": {"low_pressure_m": LOW_PRESSURE_M, "high_velocity_ms": HIGH_VELOCITY_MS},
    }
    if removed_controls:
        summary["removed_controls"] = removed_controls
    if demand_model == "PDD":
        summary["supply"] = _supply(wn, res, junctions)
    if leak_items:
        exponent = wn.options.hydraulic.emitter_exponent or 0.5
        step_s = wn.options.time.report_timestep
        summary["leaks"] = []
        for item in leak_items:
            flow = [item["coef"] * max(float(p), 0.0) ** exponent * 1000 for p in pressure[item["node"]].tolist()]
            summary["leaks"].append({
                "node": item["node"], "area_cm2": item["area_cm2"], "flow_ls": [_r(q, 3) for q in flow],
                "avg_ls": _r(sum(flow) / len(flow), 3) if flow else None,
                "volume_m3": _r(sum(flow[:-1]) * step_s / 1000, 1) if len(flow) > 1 else 0.0,
            })
    return {
        "times_s": times,
        "node": {"pressure_m": table(pressure, 1, 2), "head_m": table(res.node["head"], 1, 2),
                 "demand_ls": table(res.node["demand"], 1000, 3)},
        "link": {"flow_ls": table(res.link["flowrate"], 1000, 3), "velocity_ms": table(velocity, 1, 3),
                 "headloss_m_km": table(res.link["headloss"], 1000, 3)},
        "summary": summary,
    }
