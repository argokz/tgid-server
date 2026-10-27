"""Помощник ИИ: рекомендация точки подключения и черновик ТУ (этап 4 плана).

Кандидаты и оценку нагрузки считает database/tu_connection.py; модель разбирает текст заявки,
выбирает кандидата из переданных (индекс проверяется), объясняет и собирает черновик полей ТУ.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from ai import client as ai_client
from ai.prompts import load_prompt
from database.tu_connection import connection_candidates, estimate_load

TOOL = "tu_recommend"
MAX_CANDIDATES = 8


class ParsedRequest(BaseModel):
    address: Optional[str] = None
    purpose: Optional[str] = Field(None, description="жильё | офис | торговля | производство | …")
    floors: Optional[int] = None
    area_m2: Optional[float] = None
    load_gcal_h: Optional[float] = None


class Alternative(BaseModel):
    index: int
    note: str


class TuDraft(BaseModel):
    istochnik: Optional[str] = None
    kamera: Optional[str] = None
    prirost_nagruzki: Optional[float] = None
    otoplenie: Optional[float] = None
    ventilyatsiya: Optional[float] = None
    gvs: Optional[float] = None


class TuRecommendation(BaseModel):
    request: ParsedRequest
    # Обязательное (номер или null): с умолчанием модель поле опускала, хотя в тексте называла выбранного
    chosen_index: Optional[int]
    explanation: str
    alternatives: list[Alternative] = Field(default_factory=list)
    draft: TuDraft
    risks: list[str] = Field(default_factory=list)


def _fmt(v: Any, digits: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{digits}f}" if isinstance(v, float) else str(v)


def build_user_input(request_text: str, candidates: dict[str, Any], load_estimate: dict[str, Any],
                     load_gcal_h: Optional[float]) -> str:
    lines = ["Заявка на ТУ:", f"  {request_text.strip() or '(текста нет)'}"]
    if load_gcal_h:
        lines.append(f"Запрошенная нагрузка: {load_gcal_h} Гкал/ч")
    if load_estimate.get("load_gcal_h") is not None:
        lines.append(f"Оценка нагрузки по аналогам: {load_estimate['load_gcal_h']} Гкал/ч ({load_estimate['basis']})")
    else:
        lines.append(f"Оценка по аналогам: нет ({load_estimate.get('basis')})")
    th = candidates.get("thresholds") or {}
    lines.append(f"Пороги: скорость {th.get('v_min')}–{th.get('v_max')} м/с, располагаемый напор ≥ {th.get('min_available_head')} м")
    lines.append(f"\nКандидаты (радиус {candidates.get('radius_m')} м, расход для прироста считался по нагрузке"
                 f" {candidates.get('load_gcal_h') or 'не задана'} Гкал/ч):")
    for i, c in enumerate(candidates.get("items") or []):
        lines.append(
            f"  [{i}] узел «{c['name']}» (node#{c['node_id']}, фрагмент {c.get('fragment_name') or c.get('fragment_id')}),"
            f" {c['distance_m']} м; участок line#{c.get('line_id')} Ø{_fmt(c.get('diameter_mm'), 0)} мм,"
            f" прокладка {c.get('laid_at') or '—'}, {c.get('tubing') or ''};"
            f" напоры П/О {_fmt(c.get('head_supply'))}/{_fmt(c.get('head_return'))} м,"
            f" располагаемый {_fmt(c.get('available_head'))} м; скорость {_fmt(c.get('velocity'))} →"
            f" {_fmt(c.get('velocity_after'))} м/с, расход {_fmt(c.get('flow_t_h'))} т/ч"
            f" (+{_fmt(c.get('extra_flow_t_h'))}); источник {c.get('source_name') or '—'};"
            f" балл {c['score']}; {'; '.join(c['reasons'])}"
        )
    if not candidates.get("items"):
        lines.append("  (кандидатов нет)")
    return "\n".join(lines)


# «Выбран кандидат [0]» в объяснении — выбор, если номер не пришёл полем
_CHOSEN_IN_TEXT_RE = re.compile(r"^\s*Выбран\w*\s+кандидат\s*\[(\d+)\]", re.I)


def _sanitize(rec: TuRecommendation, candidates: list[dict[str, Any]]) -> TuRecommendation:
    n = len(candidates)
    if rec.chosen_index is None:
        m = _CHOSEN_IN_TEXT_RE.match(rec.explanation or "")
        if m:
            rec.chosen_index = int(m.group(1))
    if rec.chosen_index is not None and not (0 <= rec.chosen_index < n):
        rec.chosen_index = None
    rec.alternatives = [a for a in rec.alternatives if 0 <= a.index < n and a.index != rec.chosen_index]
    if rec.chosen_index is not None:
        chosen = candidates[rec.chosen_index]
        # имена — только из выбранного кандидата, модель могла «уточнить» их
        rec.draft.kamera = chosen.get("name") or rec.draft.kamera
        if chosen.get("source_name"):
            rec.draft.istochnik = chosen["source_name"]
    return rec


async def recommend(
    conn,
    *,
    lon: float,
    lat: float,
    request_text: str = "",
    load_gcal_h: Optional[float] = None,
    floors: Optional[int] = None,
    area_m2: Optional[float] = None,
    radius_m: int = 300,
    username: Optional[str] = None,
) -> dict[str, Any]:
    load_estimate = await estimate_load(conn, floors=floors, area_m2=area_m2)
    effective_load = load_gcal_h or load_estimate.get("load_gcal_h")
    candidates = await connection_candidates(conn, lon=lon, lat=lat, load_gcal_h=effective_load,
                                             radius_m=radius_m, limit=MAX_CANDIDATES)
    rec = await ai_client.ask_structured(
        tool=TOOL,
        system=load_prompt("tu_recommend"),
        user=build_user_input(request_text, candidates, load_estimate, load_gcal_h),
        output_format=TuRecommendation,
        effort="medium",
        username=username,
        details={"candidates": len(candidates["items"]), "load_gcal_h": effective_load},
    )
    rec = _sanitize(rec, candidates["items"])
    return {
        "candidates": candidates,
        "load_estimate": load_estimate,
        "recommendation": rec.model_dump(),
        "chosen": candidates["items"][rec.chosen_index] if rec.chosen_index is not None else None,
    }
