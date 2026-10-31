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
import tempfile
from pathlib import Path
from typing import Any, Optional

import wntr

MAX_INP_BYTES = 20_000_000
MAX_DURATION_H = 24 * 7
MAX_NODES = 50_000
LOW_PRESSURE_M = 10.0        # ниже — недостаточный напор у потребителя (СП 31.13330: не меньше 10 м на 1 этаж)
HIGH_VELOCITY_MS = 2.0


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


def describe(wn: wntr.network.WaterNetworkModel) -> dict[str, Any]:
    """Сеть модели: узлы (колодцы-узлы, резервуары, баки) и участки (трубы, насосы, арматура) с координатами модели."""
    nodes = []
    for name, n in wn.nodes():
        item: dict[str, Any] = {"id": name, "type": n.node_type, "x": _r(n.coordinates[0], 4), "y": _r(n.coordinates[1], 4),
                                "elevation": _r(getattr(n, "elevation", None), 2)}
        if n.node_type == "Junction":
            item["base_demand_ls"] = _r((n.base_demand or 0) * 1000, 4)
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


def simulate(wn: wntr.network.WaterNetworkModel, *, duration_h: Optional[float] = None,
             report_step_h: Optional[float] = None) -> dict[str, Any]:
    """Гидравлический расчёт EPANET 2.2 по периоду модели (или заданному): значения по узлам и участкам на каждый
    шаг отчёта и сводка — давление ниже LOW_PRESSURE_M, скорость выше HIGH_VELOCITY_MS, отрицательное давление."""
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
            raise EngineError(422, f"Расчёт EPANET не выполнен: {exc}") from exc
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
    return {
        "times_s": times,
        "node": {"pressure_m": table(pressure, 1, 2), "head_m": table(res.node["head"], 1, 2),
                 "demand_ls": table(res.node["demand"], 1000, 3)},
        "link": {"flow_ls": table(res.link["flowrate"], 1000, 3), "velocity_ms": table(velocity, 1, 3),
                 "headloss_m_km": table(res.link["headloss"], 1000, 3)},
        "summary": summary,
    }
