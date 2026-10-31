"""Помощник ИИ: пересортировка похожих аварий (журнал нарушений).

Кандидатов находит код (database/defect_similarity.py: вид, труба, Ду, место, слова) — модель их не ищет, а
читает тексты как инженер: та же ли это авария, та же ли причина, не плановые ли это работы. Модель —
AI_RERANK_MODEL (по умолчанию Claude Sonnet: короткие тексты, ответ за секунды на каждое нажатие).

Тексты уходят в Claude API — ФИО и номера в них маскируются всегда, независимо от прав пользователя
(database/pii.py). Если модель недоступна или отказалась — остаётся порядок по признакам (вызывающий код).
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from ai import client as ai_client
from ai import config
from ai.prompts import load_prompt
from database import defect_similarity as ds
from database import pii

TOOL = "defect_rerank"
MAX_CANDIDATES = 15   # ответ — около 6 с: время уходит на пояснения (≈40 токенов на кандидата)
TEXT_CHARS = 400
RERANK_EFFORT = "low"   # ранжирование коротких текстов — классификация, а не рассуждение
MAX_OUTPUT_TOKENS = 4000


class RankedItem(BaseModel):
    id: int
    relevance: int = Field(ge=0, le=100)
    reason: str = Field(max_length=200)


class RerankOut(BaseModel):
    items: list[RankedItem]


def _line(item: dict[str, Any]) -> str:
    date = (item.get("detected_at") or "")[:10] or "без даты"
    dist = f"{item['distance_m']:.0f} м" if item.get("distance_m") is not None else "место не задано"
    line = f", участок {item['line_id']}" if item.get("line_id") else ""
    text = pii.mask_person_text(item["text"])[:TEXT_CHARS]
    return (f"- id {item['id']}; {date}; {dist}{line}; оценка кода {round(item['score'] * 100)} "
            f"({', '.join(item['reasons'])})\n  {text}")


def build_input(reference: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    """Пользовательская часть запроса: образец и кандидаты (тексты — с маскированием ПДн)."""
    ref_date = (reference.get("detected_at") or "")[:10] or "без даты"
    ref_text = pii.mask_person_text(ds.display_text(reference.get("parts") or [reference.get("text")]))[:TEXT_CHARS]
    lines = "\n".join(_line(c) for c in candidates)
    return f"Образец ({ref_date}):\n{ref_text}\n\nКандидаты ({len(candidates)}):\n{lines}"


def merge(candidates: list[dict[str, Any]], ranked: RerankOut) -> list[dict[str, Any]]:
    """Оценка модели к кандидатам; id не из входа отбрасываются, пропущенные — в конец по оценке кода."""
    by_id = {r.id: r for r in ranked.items}
    out = []
    for c in candidates:
        r = by_id.get(c["id"])
        out.append({**c, "ai_relevance": r.relevance if r else None, "ai_reason": r.reason if r else None})
    out.sort(key=lambda c: (c["ai_relevance"] is None, -(c["ai_relevance"] or 0), -c["score"]))
    return out


async def rerank(reference: dict[str, Any], result: dict[str, Any], *, username: Optional[str] = None,
                 defect_id: Optional[int] = None) -> dict[str, Any]:
    """Пересортировать кандидатов поиска по признакам; AiError — пусть вызывающий оставит порядок кода."""
    candidates = result["items"][:MAX_CANDIDATES]
    if not candidates:
        return {**result, "ranking": "features"}
    ranked = await ai_client.ask_structured(
        tool=TOOL, system=load_prompt(TOOL), user=build_input(reference, candidates), output_format=RerankOut,
        effort=RERANK_EFFORT, max_tokens=MAX_OUTPUT_TOKENS, username=username, model=config.rerank_model(),
        details={"defect_id": defect_id, "candidates": len(candidates)},
    )
    return {**result, "items": merge(candidates, ranked), "ranking": "ai", "model": config.rerank_model()}
