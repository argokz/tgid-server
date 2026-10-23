"""Учёт вызовов ИИ: запись в activity_log (действие AI) с токенами — для контроля расходов."""

from __future__ import annotations

from typing import Any, Optional

import activity
from app_logging import get_logger

logger = get_logger(__name__)

ACTION = "AI"


def usage_dict(response: Any) -> dict[str, int]:
    u = getattr(response, "usage", None)
    out: dict[str, int] = {}
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        value = getattr(u, key, None)
        if isinstance(value, int):
            out[key] = value
    return out


async def record(
    *,
    tool: str,
    username: Optional[str],
    model: str,
    response: Any,
    duration_ms: int,
    details: Optional[dict[str, Any]] = None,
) -> None:
    tokens = usage_dict(response)
    payload: dict[str, Any] = {"tool": tool, "model": model, **tokens}
    if details:
        payload.update(details)
    logger.info("ИИ %s: %s за %d мс", tool, tokens or "без usage", duration_ms)
    await activity.write(
        username=username,
        action=ACTION,
        method="POST",
        path=f"/ai/{tool}",
        status=200,
        duration_ms=duration_ms,
        details=payload,
    )
