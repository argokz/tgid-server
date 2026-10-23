"""Помощник ИИ: статус и инструменты (/api/v1/ai/*). Инструменты — право calc_run (режимщик и выше)."""

from __future__ import annotations

from typing import Annotated, Optional

from database.tu_connection import DEFAULT_RADIUS_M, MAX_RADIUS_M

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, model_validator

from ai import calc_protocol, config, tu_recommend
from ai.client import AiError, require_ai
from ai.schemas import AiStatus
from auth import AuthUser, require_permission, require_roles
from database.connect import acquire_conn

router = APIRouter(tags=["ai"])

# Инструменты, которые уже есть в этом API (пополняются этапами 3–6 плана)
AI_TOOLS: list[str] = ["calc_protocol", "tu_recommend"]


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


class TuRecommendRequest(BaseModel):
    """Точка объекта (WGS84), текст заявки и то, что известно о здании."""

    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    request_text: str = Field("", max_length=4000)
    load_gcal_h: Optional[float] = Field(None, ge=0, le=1000)
    floors: Optional[int] = Field(None, ge=1, le=100)
    area_m2: Optional[float] = Field(None, gt=0, le=1_000_000)
    radius_m: int = Field(DEFAULT_RADIUS_M, ge=20, le=MAX_RADIUS_M)


@router.post("/api/v1/ai/tu/recommend", dependencies=[Depends(require_ai)])
async def ai_tu_recommend(
    body: TuRecommendRequest,
    user: Annotated[AuthUser, Depends(require_permission("calc_run"))],
):
    """Рекомендация точки подключения по заявке на ТУ и черновик полей ТУ (кандидаты считает код)."""
    try:
        async with acquire_conn() as conn:
            return await tu_recommend.recommend(
                conn, lon=body.lon, lat=body.lat, request_text=body.request_text,
                load_gcal_h=body.load_gcal_h, floors=body.floors, area_m2=body.area_m2,
                radius_m=body.radius_m, username=user.username,
            )
    except AiError as exc:
        raise exc.to_http() from exc
