"""Помощник ИИ: статус и инструменты (/api/v1/ai/*). Доступ — право calc_run (режимщик и выше)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ai import config
from ai.schemas import AiStatus
from auth import AuthUser, require_roles

router = APIRouter(tags=["ai"])

# Инструменты, которые уже есть в этом API (пополняются этапами 3–6 плана)
AI_TOOLS: list[str] = []


@router.get("/api/v1/ai/status", response_model=AiStatus)
async def ai_status(_: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    """Включён ли помощник и какая модель; без ключа и флага — enabled=false с причиной."""
    return AiStatus(
        enabled=config.enabled(),
        model=config.model(),
        reason=config.disabled_reason(),
        tools=list(AI_TOOLS) if config.enabled() else [],
    )
