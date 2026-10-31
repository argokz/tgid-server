"""Вызов Claude API со структурированным ответом и единой обработкой ошибок.

Один вход — ask_structured(): системный промпт (стабильный, кешируется), пользовательская
часть, pydantic-модель ответа. Ошибки SDK превращаются в AiError с кодом; наружу (HTTP)
уходит код и общее сообщение, текст исключения — только в лог.
"""

from __future__ import annotations

import time
from typing import Any, Optional, TypeVar

from fastapi import HTTPException
from pydantic import BaseModel

from ai import config, usage
from app_logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)

_client: Any = None


class AiError(Exception):
    """Ошибка помощника: code — машинный код, http — статус для клиента, message — текст пользователю."""

    def __init__(self, code: str, message: str, http: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http = http

    def to_http(self) -> HTTPException:
        return HTTPException(status_code=self.http, detail={"code": self.code, "message": self.message})


def require_ai() -> None:
    """FastAPI-зависимость: 503, если помощник выключен или нет ключа."""
    reason = config.disabled_reason()
    if reason:
        raise HTTPException(status_code=503, detail={"code": "ai_disabled", "message": reason})


def get_client():
    """Ленивый AsyncAnthropic (создаётся при первом вызове, ключ из окружения)."""
    global _client
    if _client is None:
        from anthropic import AsyncAnthropic

        _client = AsyncAnthropic(api_key=config.api_key(), timeout=config.timeout_s(), max_retries=2)
    return _client


def reset_client() -> None:
    """Для тестов и смены ключа."""
    global _client
    _client = None


def _system_blocks(system: str) -> list[dict[str, Any]]:
    # Системный промпт стабилен между вызовами одного инструмента — кешируем префикс
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


async def ask_structured(
    *,
    tool: str,
    system: str,
    user: str,
    output_format: type[T],
    effort: str = config.DEFAULT_EFFORT,
    max_tokens: Optional[int] = None,
    username: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    model: Optional[str] = None,
) -> T:
    """Запрос к модели с ответом по pydantic-схеме; usage пишется в журнал действий.

    tool — имя инструмента для журнала (calc_protocol, tu_recommend, …); details — что ещё
    записать (id расчёта, фрагмент). Текст user обрезке не подлежит: при превышении
    AI_MAX_INPUT_CHARS — AiError input_too_long (вызывающий код должен агрегировать сам).
    """
    reason = config.disabled_reason()
    if reason:
        raise AiError("ai_disabled", reason, 503)
    if effort not in config.EFFORT_LEVELS:
        raise AiError("bad_effort", f"Недопустимый уровень effort: {effort}", 400)
    if len(user) > config.max_input_chars():
        raise AiError(
            "input_too_long",
            f"Запрос к ИИ слишком длинный ({len(user)} символов, предел {config.max_input_chars()})",
            413,
        )

    import anthropic

    model = model or config.model()
    client = get_client()
    started = time.monotonic()
    try:
        response = await client.messages.parse(
            model=model,
            max_tokens=max_tokens or config.max_output_tokens(),
            system=_system_blocks(system),
            messages=[{"role": "user", "content": user}],
            output_format=output_format,
            output_config={"effort": effort},
        )
    except anthropic.AuthenticationError as exc:
        logger.error("ИИ %s: ключ отклонён (%s)", tool, exc.__class__.__name__)
        raise AiError("auth", "Ключ Claude API отклонён — проверьте ANTHROPIC_API_KEY", 503) from exc
    except anthropic.RateLimitError as exc:
        logger.warning("ИИ %s: лимит запросов (%s)", tool, exc.__class__.__name__)
        raise AiError("rate_limit", "Превышен лимит запросов к ИИ, повторите позже", 503) from exc
    except anthropic.APIStatusError as exc:
        logger.error("ИИ %s: ошибка API %s", tool, exc.status_code, exc_info=True)
        raise AiError("api_error", f"Ошибка Claude API ({exc.status_code})", 502) from exc
    except anthropic.APIConnectionError as exc:
        logger.error("ИИ %s: нет связи с Claude API (%s)", tool, exc.__class__.__name__)
        raise AiError("connection", "Нет связи с Claude API", 503) from exc

    duration_ms = int((time.monotonic() - started) * 1000)
    await usage.record(tool=tool, username=username, model=model, response=response,
                       duration_ms=duration_ms, details=details)

    if response.stop_reason == "refusal":
        raise AiError("refused", "Модель отказалась отвечать на этот запрос", 422)
    if response.stop_reason == "max_tokens":
        raise AiError("truncated", "Ответ ИИ не уместился в лимит токенов", 502)
    parsed = getattr(response, "parsed_output", None)
    if parsed is None:
        logger.error("ИИ %s: ответ без структурированных данных (stop_reason=%s)", tool, response.stop_reason)
        raise AiError("no_output", "ИИ не вернул структурированный ответ", 502)
    return parsed
