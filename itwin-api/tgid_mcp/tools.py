"""Инструменты MCP-сервера ТГИД: те же функции, что у веба, с правами пользователя токена.

Входные параметры — pydantic-модели (из них же inputSchema для tools/list). Ответ — JSON одной текстовой
частью и structuredContent; геометрия из ответов убирается, длинные списки обрезаются (ИИ-клиенту нужны
числа и id, карта — в вебе). Ошибка инструмента (нет права, нет расчёта, неверный id) — результат с
isError, а не ошибка JSON-RPC: модель видит причину и может исправить вызов.
"""
from __future__ import annotations

import html
import json
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, Field, ValidationError

import activity
from app_logging import get_logger
from auth import AuthUser
from database.connect import acquire_conn
from database.network_select import SelectSpec

logger = get_logger(__name__)

ACTION = "MCP"
MAX_LIST_ITEMS = 200
# частота вызовов на пользователя (в процессе API): (вызовов, за секунд); расчёт — отдельно и строже
RATE_LIMIT = (60, 60)
CALC_RATE_LIMIT = (5, 600)
MAX_RESULT_CHARS = 120_000
# поля с геометрией и тяжёлыми слоями — ИИ-клиенту не нужны
_DROP_KEYS = frozenset({"geojson", "geometry", "features", "shape", "coordinates", "bounds_geojson"})

FragmentIds = list[int]
_TAG = re.compile(r"<[^>]+>")


def _compact(value: Any, depth: int = 0) -> Any:
    """Ответ без геометрии, списки — не длиннее MAX_LIST_ITEMS (с пометкой, сколько было)."""
    if isinstance(value, dict):
        return {k: _compact(v, depth + 1) for k, v in value.items() if k not in _DROP_KEYS}
    if isinstance(value, (list, tuple)):
        items = [_compact(v, depth + 1) for v in value[:MAX_LIST_ITEMS]]
        if len(value) > MAX_LIST_ITEMS:
            items.append(f"… ещё {len(value) - MAX_LIST_ITEMS} (показаны первые {MAX_LIST_ITEMS})")
        return items
    return value


class ToolError(Exception):
    """Ошибка для модели: текст уходит в результат с isError."""

    status = 400


class ToolForbidden(ToolError):
    """Нет права на инструмент."""

    status = 403


class ToolRateLimited(ToolError):
    """Слишком частые вызовы."""

    status = 429


@dataclass(frozen=True)
class Tool:
    name: str
    title: str
    description: str
    params: type[BaseModel]
    run: Callable[[Any, AuthUser], Awaitable[Any]]
    # общее право permissions.py (None — любой вошедший пользователь)
    permission: Optional[str] = None
    read_only: bool = True


_calls: dict[tuple[str, str], deque] = defaultdict(deque)


def _rate_ok(key: tuple[str, str], limit: tuple[int, int], now: float) -> bool:
    """Скользящее окно: не больше limit[0] вызовов за limit[1] секунд."""
    count, window = limit
    q = _calls[key]
    while q and now - q[0] >= window:
        q.popleft()
    if len(q) >= count:
        return False
    q.append(now)
    return True


def _check_rate(user: AuthUser, tool: "Tool") -> None:
    now = time.monotonic()
    if not _rate_ok((user.username, "*"), RATE_LIMIT, now):
        raise ToolRateLimited(f"Слишком часто: не больше {RATE_LIMIT[0]} вызовов в минуту — подождите")
    if not tool.read_only and not _rate_ok((user.username, tool.name), CALC_RATE_LIMIT, now):
        raise ToolRateLimited(f"Не больше {CALC_RATE_LIMIT[0]} запусков за {CALC_RATE_LIMIT[1] // 60} минут — дождитесь "
                        f"прежних (task_status)")


def _require(user: AuthUser, permission: Optional[str]) -> None:
    if not permission:
        return
    from permissions import GENERAL

    if not user.perms.has(permission):
        raise ToolForbidden(f"Нет права «{GENERAL.get(permission, permission)}»")


# --------------------------------------------------------------------- параметры


class NoParams(BaseModel):
    pass


class SearchParams(BaseModel):
    kind: Literal["node", "line", "source", "consumer"] = Field(
        ..., description="node — узел (камера, ТК), line — участок между двумя узлами, source — источник, "
                         "consumer — потребитель")
    text: str = Field(..., min_length=1, max_length=200, description="Название или номер (часть)")
    text2: Optional[str] = Field(None, max_length=200, description="Для line — второй узел участка")
    fragment_id: Optional[int] = Field(None, ge=1, description="Ограничить фрагментом")


class TraceParams(BaseModel):
    trace_type: Optional[Literal["connected", "upstream", "downstream", "subnetwork"]] = Field(
        None, description="connected — связанные, upstream — путь к источникам, downstream — что ниже по потоку "
                          "(останется без питания), subnetwork — зона сети. Или config_id")
    config_id: Optional[str] = Field(None, max_length=64, description="Именованная настройка (list_trace_configs)")
    stop_at: list[Literal["valves", "pumpstations", "setpress", "sources"]] = Field(
        default_factory=list, max_length=4, description="Барьеры по условию (у connected и subnetwork)")
    start_node_ids: list[int] = Field(default_factory=list, max_length=100)
    start_line_ids: list[int] = Field(default_factory=list, max_length=100)
    barrier_node_ids: list[int] = Field(default_factory=list, max_length=200)
    barrier_line_ids: list[int] = Field(default_factory=list, max_length=200)


class IsolationParams(BaseModel):
    line_id: Optional[int] = Field(None, ge=1, description="Аварийный участок")
    node_id: Optional[int] = Field(None, ge=1, description="Аварийный узел")
    failed_valve_ids: list[int] = Field(default_factory=list, max_length=100,
                                        description="Задвижки, которые не держат (зона расширяется)")


class FragmentsParams(BaseModel):
    fragment_ids: FragmentIds = Field(default_factory=list, max_length=500,
                                      description="Фрагменты; пусто — вся сеть")


class NetworkStatsParams(FragmentsParams):
    query: Literal["length", "volume", "length_by_diameter", "length_by_diameter_laying", "heat_consumption",
                   "closed_consumers"] = Field(..., description="Какой запрос по сети (как «Запросы по сети» в вебе)")


class RegimeParams(BaseModel):
    fragment_id: int = Field(..., ge=1)
    kind: Literal["negative_dp", "airlock", "low_temperature", "closed_sections", "hydrostatic_zones"] = Field(
        ..., description="negative_dp — обратка выше подачи, airlock — завоздушивание, low_temperature — низкая "
                         "температура, closed_sections — закрытые участки, hydrostatic_zones — гидростатические зоны")
    calculation_id: Optional[int] = Field(None, ge=1, description="Расчёт; по умолчанию последний фрагмента")


class ThemeParams(BaseModel):
    theme: str = Field(..., max_length=40, description="Тема (список — в описании инструмента)")
    fragment_ids: FragmentIds = Field(..., min_length=1, max_length=500)
    top: int = Field(10, ge=0, le=50, description="Сколько участков с наибольшим значением вернуть")


class WearParams(BaseModel):
    fragment_id: Optional[int] = Field(None, ge=1)
    min_category: Optional[int] = Field(None, ge=1, le=4, description="Категория износа от (1–4)")
    limit: int = Field(20, ge=1, le=100)


class DataQualityParams(BaseModel):
    fragment_id: Optional[int] = Field(None, ge=1)


class CalcParams(BaseModel):
    fragment_ids: FragmentIds = Field(..., min_length=1, max_length=50)
    mode: Literal["plan", "emergency"] = "plan"
    tn: Optional[float] = Field(None, ge=-60, le=50,
                                description="Температура наружного воздуха, °C; пусто — расчётная для отопления "
                                            "(«Система теплоснабжения» города)")
    name: Optional[str] = Field(None, max_length=200, description="Название расчёта")


class TaskParams(BaseModel):
    task_id: str = Field(..., min_length=1, max_length=100)


class SelectParams(SelectSpec):
    limit: int = Field(100, ge=1, le=200, description="Сколько объектов вернуть (итог — в total)")
    in_view: bool = Field(False, description="Не используется в MCP: охвата карты нет")


# --------------------------------------------------------------------- инструменты


async def _list_fragments(p: NoParams, user: AuthUser) -> Any:
    async with acquire_conn() as conn:
        rows = await conn.fetch("SELECT id, name FROM fragments WHERE COALESCE(removed, 0) = 0 ORDER BY name")
    return {"fragments": [dict(r) for r in rows]}


async def _search(p: SearchParams, user: AuthUser) -> Any:
    from ai.tools import SearchQuery, execute_search

    q = SearchQuery(kind=p.kind, text=p.text, text2=p.text2, fragment_id=p.fragment_id, confidence=1)
    async with acquire_conn() as conn:
        res = await execute_search(conn, q)
    return {"items": res["items"], "total": res.get("total", len(res["items"]))}


async def _trace(p: TraceParams, user: AuthUser) -> Any:
    from routers.analysis import TraceRequest, api_network_trace

    if not (p.start_node_ids or p.start_line_ids):
        raise ToolError("Нужна хотя бы одна начальная точка: start_node_ids или start_line_ids")
    req = TraceRequest(**p.model_dump(), include_geometry=False)
    res = await api_network_trace(req, user)
    return res


async def _trace_configs(p: NoParams, user: AuthUser) -> Any:
    from database import trace_configs

    async with acquire_conn() as conn:
        return {"configs": await trace_configs.list_configs(conn, user.username)}


async def _isolation(p: IsolationParams, user: AuthUser) -> Any:
    from database.outage_simulation import simulate_outage_isolation

    if (p.line_id is None) == (p.node_id is None):
        raise ToolError("Укажите ровно одно: line_id или node_id")
    async with acquire_conn() as conn:
        try:
            return await simulate_outage_isolation(conn, line_id=p.line_id, node_id=p.node_id,
                                                   failed_valve_ids=p.failed_valve_ids)
        except ValueError as exc:
            raise ToolError(str(exc)) from exc


async def _network_stats(p: NetworkStatsParams, user: AuthUser) -> Any:
    from database import network_queries as nq
    from database import regime_queries

    frags = sorted(set(p.fragment_ids)) or None
    async with acquire_conn() as conn:
        if p.query == "length":
            return await nq.query_network_length(conn, fragment_ids=frags)
        if p.query == "volume":
            return await nq.query_network_volume(conn, fragment_ids=frags)
        if p.query == "length_by_diameter":
            return await nq.query_length_by_diameter(conn, fragment_ids=frags, limit=200)
        if p.query == "length_by_diameter_laying":
            return await nq.query_length_by_diameter_and_laying(conn, fragment_ids=frags)
        if p.query == "heat_consumption":
            return await nq.query_heat_consumption(conn, fragment_ids=frags, system=None)
        items = await nq.query_closed_consumers(conn, fragment_ids=frags)
        await regime_queries.attach_coords(conn, items["items"])
        return items


async def _regime(p: RegimeParams, user: AuthUser) -> Any:
    from database import regime_queries as rq

    async with acquire_conn() as conn:
        if p.kind == "closed_sections":
            return await rq.closed_sections(conn, p.fragment_id, False, p.calculation_id)
        if p.kind == "hydrostatic_zones":
            return await rq.hydrostatic_zones(conn, p.fragment_id)
        fn = {"negative_dp": rq.negative_dp, "airlock": rq.airlock, "low_temperature": rq.low_temperature}[p.kind]
        return await fn(conn, p.fragment_id, p.calculation_id)


async def _theme(p: ThemeParams, user: AuthUser) -> Any:
    from database import thematic as th

    async with acquire_conn() as conn:
        try:
            res = await th.theme_features(conn, p.theme, p.fragment_ids, with_geometry=False)
        except th.ThematicError as exc:
            raise ToolError(exc.message) from exc
    theme = res["theme"]
    rows = [f["properties"] for f in res["geojson"]["features"]]
    out: dict[str, Any] = {"theme": theme, "source_run": res["source_run"], "summary": res["summary"],
                           "truncated": res["truncated"]}
    values = sorted(r["v"] for r in rows if r["v"] is not None)
    if theme["kind"] == "number" and values:
        # классы темы по умолчанию (границы темы или квинтили) — распределение участков
        breaks = theme["breaks"] or sorted({values[int(i * len(values) / 5)] for i in range(1, 5)})
        counts = [0] * (len(breaks) + 1)
        for v in values:
            counts[sum(1 for b in breaks if v >= b)] += 1
        out["classes"] = [{"from": breaks[i - 1] if i else None, "to": breaks[i] if i < len(breaks) else None,
                           "count": n} for i, n in enumerate(counts)]
        out["median"] = values[len(values) // 2]
        if p.top:
            top = sorted((r for r in rows if r["v"] is not None), key=lambda r: r["v"], reverse=True)[:p.top]
            out["top"] = [{"line_id": r["id"], "fragment_id": r["fileid"], "value": r["v"]} for r in top]
    return out


async def _wear(p: WearParams, user: AuthUser) -> Any:
    from database import wear

    async with acquire_conn() as conn:
        run_id = await wear.latest_id(conn)
        if not run_id:
            raise ToolError("Расчёта износа ещё нет — его запускают в вебе (Износ и план ремонтов)")
        res = await wear.sections(conn, run_id, fragment_id=p.fragment_id, min_category=p.min_category,
                                  order="priority", limit=p.limit)
        return {"calculation_id": run_id, **res}


async def _data_quality(p: DataQualityParams, user: AuthUser) -> Any:
    from database import data_quality as dq

    async with acquire_conn() as conn:
        return await dq.summary(conn, fragment_id=p.fragment_id)


async def _run_calc(p: CalcParams, user: AuthUser) -> Any:
    from routers.calc import run_sety_mode
    from sety_modes import SetyRunRequest

    tn = p.tn
    if tn is None:
        from routers.calc import _heat_system_tn_range

        async with acquire_conn() as conn:
            tn = (await _heat_system_tn_range(conn))["t_or"]
        if tn is None:
            raise ToolError("В «Системе теплоснабжения» города нет расчётной температуры — задайте tn")
    body = SetyRunRequest(mode=p.mode, fragment_ids=sorted(set(p.fragment_ids)), tn=tn, name=p.name)
    res = await run_sety_mode(body, user)
    return {**res, "next": "Состояние — task_status с этим task_id (расчёт идёт от секунд до минут)"}


async def _task_status(p: TaskParams, user: AuthUser) -> Any:
    from routers.calc import get_task_status

    res = await get_task_status(p.task_id)
    result = res.get("result")
    if isinstance(result, dict) and isinstance(result.get("output"), str):
        # журнал sety приходит HTML-разметкой окна протокола — модели нужен текст
        text = html.unescape(_TAG.sub("", result["output"].replace("<br>", "\n")))
        res = {**res, "result": {**result, "output": text}}
    return res


async def _select(p: SelectParams, user: AuthUser) -> Any:
    from database import network_select as ns

    async with acquire_conn() as conn:
        try:
            return await ns.run_select(conn, p, with_geometry=False, user_key=user.username or user.sub or "")
        except ns.SelectError as exc:
            raise ToolError(exc.message) from exc


def _select_fields() -> str:
    from database.network_select import CARD_TYPES, TARGETS

    parts = []
    for key, (label, fields) in TARGETS.items():
        names = "; ".join(f"{f.key} — {f.label}{f', {f.units}' if f.units else ''} ({f.kind})" for f in fields.values())
        parts.append(f"{key} ({label.lower()}): {names}")
    cards = ", ".join(f"{v}={label}" for v, label in CARD_TYPES)
    return ". ".join(parts) + f". Коды card_type: {cards}"


def _theme_list() -> str:
    from database.thematic import THEMES

    return "; ".join(f"{t.key} — {t.label}{f', {t.units}' if t.units else ''}" for t in THEMES.values())


TOOLS: dict[str, Tool] = {t.name: t for t in (
    Tool("list_fragments", "Фрагменты сети", "Фрагменты (районы, магистрали) сети города: id и название.",
         NoParams, _list_fragments),
    Tool("search_network", "Поиск объектов сети",
         "Найти узлы, участки (по паре узлов), источники или потребителей по названию/номеру. Возвращает id, "
         "фрагмент и координаты WGS 84.", SearchParams, _search),
    Tool("select_network", "Выборка объектов по условиям",
         "Участки или узлы по условиям на поля (числа: lt, le, gt, ge, eq, ne, between, is_null, not_null; "
         "справочники: in, not_in по кодам; текст: contains, eq), «в meters м от узла» (near), «в meters м от социальных объектов» (near_poi: categories из school, "
         "kindergarten, hospital, clinic, social; пусто — все), фрагменты, "
         "порядок и предел. Возвращает описание запроса, total, суммарную длину участков и строки со значениями "
         "полей. Поля: " + _select_fields() + ". Коды справочников (tubing_type, node_type) — в ошибке или "
         "GET /api/v1/network-select/fields.", SelectParams, _select),
    Tool("network_trace", "Трассировка сети",
         "Трассировка по топологии от начальных узлов/участков: связанные, путь к источникам, ниже по потоку, "
         "зона; барьеры — объекты и по условию (задвижки, насосные, узлы заданного напора, источники). "
         "Возвращает сводку и id узлов, участков и потребителей.", TraceParams, _trace),
    Tool("list_trace_configs", "Настройки трассировки", "Встроенные, общие и свои именованные настройки трассировки.",
         NoParams, _trace_configs),
    Tool("valve_isolation", "Локализация аварии",
         "Какие задвижки закрыть при аварии на участке или в узле и кто останется без тепла (потребители, "
         "нагрузка).", IsolationParams, _isolation),
    Tool("network_statistics", "Запросы по сети",
         "Длина, объём, длина по диаметрам и способам прокладки, теплопотребление, закрытые потребители — по "
         "фрагментам или всей сети.", NetworkStatsParams, _network_stats),
    Tool("regime_analysis", "Анализ режима",
         "Проблемы гидравлического режима фрагмента по расчёту: отрицательные перепады, завоздушивание, низкие "
         "температуры, закрытые участки, гидростатические зоны.", RegimeParams, _regime),
    Tool("thematic_summary", "Сводка по теме участков",
         "Распределение участков фрагментов по теме и участки с наибольшим значением. Темы: " + _theme_list(),
         ThemeParams, _theme),
    Tool("wear_priorities", "Износ и приоритет ремонта",
         "Участки по приоритету ремонта из последнего расчёта износа (износ %, возраст, повреждения).",
         WearParams, _wear),
    Tool("data_quality", "Качество исходных данных",
         "Нарушения правил качества данных (без координат, без нагрузки, разрывы…) по фрагменту или всей сети.",
         DataQualityParams, _data_quality),
    Tool("run_calculation", "Запустить гидравлический расчёт",
         "Поставить в очередь расчёт sety (плановый или аварийный) фрагментов при температуре наружного воздуха "
         "tn. Пишет только результаты расчёта, исходные данные не меняет. Нужно право «Запуск расчётов».",
         CalcParams, _run_calc, permission="calc_run", read_only=False),
    Tool("task_status", "Состояние расчёта", "Состояние задачи расчёта по task_id из run_calculation.",
         TaskParams, _task_status),
)}


def _input_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    schema.pop("title", None)
    schema.setdefault("properties", {})
    return schema


def describe_tools() -> list[dict[str, Any]]:
    return [{
        "name": t.name,
        "title": t.title,
        "description": t.description,
        "inputSchema": _input_schema(t.params),
        "annotations": {"title": t.title, "readOnlyHint": t.read_only, "destructiveHint": False,
                        "idempotentHint": t.read_only, "openWorldHint": False},
    } for t in TOOLS.values()]


def _text_result(payload: Any, *, is_error: bool = False) -> dict[str, Any]:
    if is_error:
        return {"content": [{"type": "text", "text": str(payload)}], "isError": True}
    data = _compact(payload)
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + " …[ответ обрезан — сузьте запрос: фрагмент, фильтр, лимит]"
        return {"content": [{"type": "text", "text": text}], "isError": False}
    result: dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": False}
    if isinstance(data, dict):
        result["structuredContent"] = json.loads(text)
    return result


async def execute(name: str, arguments: dict[str, Any], user: AuthUser) -> Any:
    """Вызов инструмента без обёртки MCP (OGC API — Processes): проверка параметров, права и частоты.

    Ошибки — исключениями: ValidationError, ToolError (ToolForbidden, ToolRateLimited), HTTPException."""
    tool = TOOLS[name]
    params = tool.params.model_validate(arguments)
    _require(user, tool.permission)
    _check_rate(user, tool)
    return await tool.run(params, user)


async def call_tool(name: str, arguments: dict[str, Any], user: AuthUser,
                    client: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """client — ip и user_agent запроса (журнал действий)."""
    tool = TOOLS[name]
    started = time.perf_counter()
    status = 200
    try:
        result = _text_result(await execute(name, arguments, user))
    except ValidationError as exc:
        status = 422
        result = _text_result("Неверные параметры: " + "; ".join(
            f"{'.'.join(map(str, e['loc'])) or 'arguments'} — {e['msg']}" for e in exc.errors()), is_error=True)
    except ToolError as exc:
        status = exc.status
        result = _text_result(str(exc), is_error=True)
    except HTTPException as exc:
        status = exc.status_code
        # 5xx: текст ошибки сервера (бывает str(исключения БД)) модели не нужен — он в логе
        detail = exc.detail if exc.status_code < 500 else "Внутренняя ошибка сервера при выполнении инструмента"
        if exc.status_code >= 500:
            logger.error("MCP %s: HTTP %s %s", name, exc.status_code, exc.detail)
        result = _text_result(detail, is_error=True)
    except Exception as exc:  # noqa: BLE001 — модель видит общую причину, подробности — в логе сервера
        logger.error("MCP %s: %s", name, exc, exc_info=True)
        status = 500
        result = _text_result("Внутренняя ошибка сервера при выполнении инструмента", is_error=True)
    duration_ms = int((time.perf_counter() - started) * 1000)
    details: dict[str, Any] = {"tool": name}
    if not tool.read_only:
        details["arguments"] = arguments  # действие с последствиями — с параметрами
    await activity.write(username=user.username, action=ACTION, method="POST", path=f"/mcp/{name}",
                         status=status, duration_ms=duration_ms, details=details,
                         ip=(client or {}).get("ip"), user_agent=(client or {}).get("user_agent"))
    return result
