"""Pydantic-модели ответов помощника ИИ (общие; предметные — рядом с инструментами)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AiStatus(BaseModel):
    enabled: bool
    model: str
    reason: Optional[str] = Field(None, description="Почему выключен (если выключен)")
    tools: list[str] = Field(default_factory=list, description="Доступные инструменты ИИ")


class ObjectRef(BaseModel):
    """Ссылка на объект сети из ответа модели (id — только из входных данных)."""

    kind: str = Field(description="node | line | line2 | consumer | source")
    id: Optional[int] = None
    id1: Optional[int] = None
    id2: Optional[int] = None
    label: str = ""
