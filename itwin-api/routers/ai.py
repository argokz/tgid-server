"""Помощник ИИ: статус и инструменты (/api/v1/ai/*). Инструменты — право calc_run (режимщик и выше)."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from ai import calc_protocol, config
from ai.client import AiError, require_ai
from ai.schemas import AiStatus
from auth import AuthUser, require_permission, require_roles
from database.connect import acquire_conn

router = APIRouter(tags=["ai"])

# Инструменты, которые уже есть в этом API (пополняются этапами 3–6 плана)
AI_TOOLS: list[str] = ["calc_protocol"]


@router.get("/api/v1/ai/status", response_model=AiStatus)
async def ai_status(_: Annotated[AuthUser, Depends(require_roles("viewer"))]):
    """Включён ли помощник и какая модель; без ключа и флага — enabled=false с причиной."""
    return AiStatus(
        enabled=config.enabled(),
        model=config.model(),
        reason=config.disabled_reason(),
        tools=list(AI_TOOLS) if config.enabled() else [],
    )


class ExplainProtocolRequest(BaseModel):
    """Что объяснять: строка calculation, запись протокола или запуск по списку (request_id)."""

    calculation_id: Optional[int] = Field(None, ge=1)
    protocol_id: Optional[int] = Field(None, ge=1)
    request_id: Optional[str] = Field(None, max_length=64)
    refresh: bool = Field(False, description="Не брать кеш ai_summary, спросить модель заново")

    @model_validator(mode="after")
    def _one_key(self):
        if not any((self.calculation_id, self.protocol_id, self.request_id)):
            raise ValueError("Укажите calculation_id, protocol_id или request_id")
        return self


@router.post("/api/v1/ai/calc-protocol/explain", dependencies=[Depends(require_ai)])
async def ai_explain_calc_protocol(
    body: ExplainProtocolRequest,
    user: Annotated[AuthUser, Depends(require_permission("calc_run"))],
):
    """Объяснение протокола расчёта: причины, что открыть, какие флаги попробовать; регуляторы с дефицитом."""
    try:
        async with acquire_conn() as conn:
            return await calc_protocol.explain(
                conn,
                calculation_id=body.calculation_id,
                protocol_id=body.protocol_id,
                request_id=body.request_id,
                username=user.username,
                refresh=body.refresh,
            )
    except AiError as exc:
        raise exc.to_http() from exc
