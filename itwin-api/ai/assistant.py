"""Помощник-собеседник (фаза 5): вопрос инженера → модель сама вызывает инструменты ТГИД → ответ текстом и
найденные объекты для карты.

Инструменты — общий реестр MCP (tgid_mcp/tools.py): права пользователя, частота вызовов и журнал действий те же
(путь /ai/assistant/<инструмент>). Токены всех шагов одного вопроса — одной записью AI (tool=assistant).
Беседу сервер не хранит: клиент присылает прежние вопросы и ответы текстом (без результатов инструментов).

run() — асинхронный генератор событий для потока NDJSON: step (вызов инструмента), step_done, note (текст
модели между вызовами), answer (ответ, GeoJSON подсветки, токены) или error.
"""
from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Literal, Optional

from pydantic import BaseModel, Field

from ai import config, usage
from ai.prompts import load_prompt
from app_logging import get_logger
from auth import AuthUser

logger = get_logger(__name__)

TOOL_NAME = "assistant"
MAX_STEPS = 12                  # вызовов модели на вопрос; последний — без инструментов, только ответ
MAX_TOTAL_S = 300               # весь вопрос (инструменты + модель), дальше — ответ по собранному
MAX_HISTORY = 20                # реплик прежней беседы
MAX_QUESTION_CHARS = 4000
MAX_REPLY_CHARS = 8000          # одна прежняя реплика
MAX_RESULT_CHARS = 30_000       # ответ инструмента в контекст модели (MCP-клиенту — до 120 тыс.)
MAX_HIGHLIGHT = 3000            # объектов на карте каждого вида
MAX_CONTEXT_FRAGMENTS = 50
# вопросов на пользователя: (сколько, за секунд) — каждый вопрос стоит денег
QUESTION_RATE = (30, 600)


class AssistantTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(..., min_length=1, max_length=MAX_REPLY_CHARS)


class AssistantRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=MAX_QUESTION_CHARS)
    history: list[AssistantTurn] = Field(default_factory=list, max_length=MAX_HISTORY)
    fragment_ids: list[int] = Field(default_factory=list, max_length=MAX_CONTEXT_FRAGMENTS,
                                    description="Фрагменты, открытые на карте (подсказка модели)")


class AssistantInputError(ValueError):
    pass


def check_history(history: list[AssistantTurn]) -> None:
    """Реплики чередуются, первая — вопрос, последняя — ответ (новый вопрос идёт следом)."""
    for i, turn in enumerate(history):
        expected = "user" if i % 2 == 0 else "assistant"
        if turn.role != expected:
            raise AssistantInputError("История беседы: вопросы и ответы должны чередоваться, начиная с вопроса")
    if history and history[-1].role != "assistant":
        raise AssistantInputError("История беседы должна заканчиваться ответом помощника")


def tool_specs() -> list[dict[str, Any]]:
    """Инструменты для Claude API из реестра MCP; последний помечен для кеша (инструменты + система — префикс)."""
    from tgid_mcp.tools import TOOLS, _input_schema

    specs = [{"name": t.name, "description": f"{t.title}. {t.description}", "input_schema": _input_schema(t.params)}
             for t in TOOLS.values()]
    specs[-1]["cache_control"] = {"type": "ephemeral"}
    return specs


def build_messages(req: AssistantRequest) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{"role": t.role, "content": t.text} for t in req.history]
    question = req.question.strip()
    if req.fragment_ids:
        ids = ", ".join(str(i) for i in sorted(set(req.fragment_ids)))
        question = f"(На карте открыты фрагменты: {ids})\n\n{question}"
    messages.append({"role": "user", "content": question})
    return messages


def input_chars(req: AssistantRequest) -> int:
    return len(req.question) + sum(len(t.text) for t in req.history)


def _ints(values: Any) -> list[int]:
    return [v for v in values if isinstance(v, int) and not isinstance(v, bool)] if isinstance(values, list) else []


def collect_ids(tool: str, arguments: dict[str, Any], payload: Any, nodes: set[int], lines: set[int]) -> None:
    """id участков и узлов из ответа инструмента — для подсветки на карте."""
    if not isinstance(payload, dict):
        return
    nodes.update(_ints(payload.get("node_ids")))
    lines.update(_ints(payload.get("line_ids")))
    items = payload.get("items")
    if tool == "select_network" and isinstance(items, list):
        target = lines if payload.get("target") == "lines" else nodes
        target.update(_ints([i.get("id") for i in items if isinstance(i, dict)]))
    elif tool == "search_network" and isinstance(items, list):
        target = lines if arguments.get("kind") == "line" else nodes
        target.update(_ints([i.get("id") for i in items if isinstance(i, dict)]))
    elif tool == "valve_isolation":
        for layer in ("isolated_pipes", "downstream_pipes"):
            features = ((payload.get("geojson") or {}).get(layer) or {}).get("features") or []
            lines.update(_ints([(f.get("properties") or {}).get("id") for f in features]))
        for key in ("affected_consumers", "downstream_consumers"):
            nodes.update(_ints([c.get("node_id") for c in payload.get(key) or [] if isinstance(c, dict)]))
    # списки строк с line_id / node_id (износ, темы, отказы) и anchor_type/anchor_id (сравнение сценария)
    for value in payload.values():
        if isinstance(value, list):
            for row in value[:MAX_HIGHLIGHT]:
                if isinstance(row, dict):
                    lines.update(_ints([row.get("line_id")]))
                    nodes.update(_ints([row.get("node_id")]))
                    anchor = {"line": lines, "node": nodes}.get(row.get("anchor_type"))
                    if anchor is not None:
                        anchor.update(_ints([row.get("anchor_id")]))


async def map_features(conn, nodes: set[int], lines: set[int]) -> dict[str, Any]:
    """GeoJSON подсветки в WGS 84: участки — линии, узлы — точки (не больше MAX_HIGHLIGHT каждого вида)."""
    features: list[dict[str, Any]] = []
    if lines:
        for r in await conn.fetch(
                "SELECT id, fileid, ST_AsGeoJSON(ST_Transform(shape, 4326), 6) AS g FROM linesobj "
                "WHERE id = ANY($1::int[]) AND shape IS NOT NULL", sorted(lines)[:MAX_HIGHLIGHT]):
            features.append({"type": "Feature", "id": r["id"], "geometry": json.loads(r["g"]),
                             "properties": {"id": r["id"], "fileid": r["fileid"], "kind": "line"}})
    if nodes:
        for r in await conn.fetch(
                "SELECT id, fileid, ST_AsGeoJSON(ST_Transform(shape, 4326), 6) AS g FROM nodes "
                "WHERE id = ANY($1::int[]) AND shape IS NOT NULL", sorted(nodes)[:MAX_HIGHLIGHT]):
            features.append({"type": "Feature", "id": r["id"], "geometry": json.loads(r["g"]),
                             "properties": {"id": r["id"], "fileid": r["fileid"], "kind": "node"}})
    return {"type": "FeatureCollection", "features": features}


def _short(arguments: dict[str, Any]) -> dict[str, Any]:
    """Параметры вызова для показа в окне: без длинных списков."""
    out: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, list) and len(value) > 10:
            out[key] = value[:10] + [f"… ещё {len(value) - 10}"]
        elif isinstance(value, str) and len(value) > 200:
            out[key] = value[:200] + "…"
        else:
            out[key] = value
    return out


def _result_text(result: dict[str, Any]) -> str:
    text = "".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
    if len(text) > MAX_RESULT_CHARS:
        text = text[:MAX_RESULT_CHARS] + " …[ответ обрезан — сузьте запрос: фрагмент, фильтр, limit]"
    return text


def _text_of(response: Any) -> str:
    return "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text").strip()


async def run(req: AssistantRequest, user: AuthUser, client: Optional[dict[str, str]] = None) -> AsyncIterator[dict[str, Any]]:
    import anthropic

    from ai.client import AiError, get_client
    from database.connect import acquire_conn
    from tgid_mcp.tools import TOOLS, call_tool_raw

    model = config.model()
    system = [{"type": "text", "text": load_prompt("assistant", with_base=False), "cache_control": {"type": "ephemeral"}}]
    tools = tool_specs()
    messages = build_messages(req)
    tokens: dict[str, int] = {}
    nodes: set[int] = set()
    lines: set[int] = set()
    started = time.monotonic()
    calls = 0
    answer = ""
    error: Optional[AiError] = None
    try:
        for step in range(MAX_STEPS):
            last = step == MAX_STEPS - 1 or time.monotonic() - started > MAX_TOTAL_S
            try:
                response = await get_client().messages.create(
                    model=model,
                    max_tokens=config.max_output_tokens(),
                    system=system,
                    tools=tools,
                    # последний шаг — только ответ по собранному
                    tool_choice={"type": "none"} if last else {"type": "auto"},
                    messages=messages,
                    output_config={"effort": config.DEFAULT_EFFORT},
                )
            except anthropic.AuthenticationError as exc:
                raise AiError("auth", "Ключ Claude API отклонён — проверьте ANTHROPIC_API_KEY", 503) from exc
            except anthropic.RateLimitError as exc:
                raise AiError("rate_limit", "Превышен лимит запросов к ИИ, повторите позже", 503) from exc
            except anthropic.APIStatusError as exc:
                logger.error("Помощник: ошибка API %s", exc.status_code, exc_info=True)
                raise AiError("api_error", f"Ошибка Claude API ({exc.status_code})", 502) from exc
            except anthropic.APIConnectionError as exc:
                raise AiError("connection", "Нет связи с Claude API", 503) from exc
            usage.add_usage(tokens, response)
            if response.stop_reason == "refusal":
                raise AiError("refused", "Модель отказалась отвечать на этот запрос", 422)
            if response.stop_reason == "max_tokens":
                raise AiError("truncated", "Ответ ИИ не уместился в лимит токенов — сузьте вопрос", 502)
            uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            if response.stop_reason != "tool_use" or not uses:
                answer = _text_of(response)
                break
            note = _text_of(response)
            if note:
                yield {"type": "note", "text": note}
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for use in uses:
                calls += 1
                tool = TOOLS.get(use.name)
                args = use.input if isinstance(use.input, dict) else {}
                yield {"type": "step", "index": calls, "tool": use.name, "title": tool.title if tool else use.name,
                       "input": _short(args)}
                t0 = time.monotonic()
                if tool is None:
                    payload, result = None, {"content": [{"type": "text", "text": f"Нет инструмента {use.name}"}],
                                             "isError": True}
                else:
                    payload, result = await call_tool_raw(use.name, args, user, client, path_prefix="/ai/assistant")
                is_error = bool(result.get("isError"))
                if not is_error:
                    collect_ids(use.name, args, payload, nodes, lines)
                text = _result_text(result)
                done: dict[str, Any] = {"type": "step_done", "index": calls, "tool": use.name, "ok": not is_error,
                                        "ms": int((time.monotonic() - t0) * 1000)}
                if is_error:
                    done["error"] = text[:500]
                yield done
                results.append({"type": "tool_result", "tool_use_id": use.id, "content": text, "is_error": is_error})
            messages.append({"role": "user", "content": results})
    except AiError as exc:
        error = exc
    finally:
        duration_ms = int((time.monotonic() - started) * 1000)
        if tokens:
            await usage.record_tokens(tool=TOOL_NAME, username=user.username, model=model, tokens=tokens,
                                      duration_ms=duration_ms, details={"tool_calls": calls,
                                                                        "error": error.code if error else None})
    if error is not None:
        yield {"type": "error", "code": error.code, "message": error.message}
        return
    geojson = None
    if nodes or lines:
        try:
            async with acquire_conn() as conn:
                geojson = await map_features(conn, nodes, lines)
        except Exception as exc:  # noqa: BLE001 — ответ важнее подсветки; причина — в логе
            logger.error("Помощник: подсветка на карте не собрана: %s", exc, exc_info=True)
    yield {"type": "answer", "text": answer or "Не получилось сформулировать ответ — переформулируйте вопрос.",
           "model": model, "tool_calls": calls, "tokens": tokens,
           "highlight": {"nodes": len(nodes), "lines": len(lines)}, "geojson": geojson,
           "duration_ms": int((time.monotonic() - started) * 1000)}
