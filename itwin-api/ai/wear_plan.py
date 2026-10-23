"""Помощник ИИ: пояснительная записка к плану ремонтов по расчёту износа (этап 5 плана)."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ai import client as ai_client
from ai.prompts import load_prompt
from database import wear

TOOL = "wear_plan"
MAX_SECTIONS = 40


class WearGroup(BaseModel):
    title: str
    reason: str
    line_ids: list[int] = Field(default_factory=list)
    recommended_action: str
    urgency: Literal[1, 2, 3]


class WearPlanNote(BaseModel):
    summary: str
    groups: list[WearGroup] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


def _n(v: Any, d: int = 1) -> str:
    return "—" if v is None else (f"{v:.{d}f}" if isinstance(v, float) else str(v))


def build_user_input(summary: dict[str, Any], items: list[dict[str, Any]], notes: list[str]) -> str:
    lines = [f"Расчёт износа «{summary.get('name')}» от {summary.get('at')}: участков {summary.get('lines')},"
             f" средний износ {_n(summary.get('avg_wear'))} %."]
    cats = summary.get("by_category") or {}
    labels = summary.get("category_labels") or {}
    lines.append("По категориям: " + "; ".join(f"{k} ({labels.get(k) or labels.get(str(k), '')}): {v}" for k, v in cats.items()))
    lines.append(f"Полнота данных (заполнено факторов из 8 → участков): {summary.get('factors_filled')}; "
                 f"без даты прокладки: {summary.get('no_date')}; с повреждениями: {summary.get('with_defects')}; "
                 f"с расходом по расчёту: {summary.get('with_flow')}")
    for n in notes:
        lines.append(f"Замечание: {n}")
    lines.append("\nУчастки с наибольшим приоритетом:")
    for it in items[:MAX_SECTIONS]:
        lines.append(
            f"  - line#{it['lineid']} «{it.get('node1') or '?'} — {it.get('node2') or '?'}», фрагмент {it.get('fragment_name') or it.get('fileid')},"
            f" Ø{_n(it.get('diameter'), 0)} мм, {_n(it.get('length_m'), 0)} м, {it.get('tubing') or ''};"
            f" срок {_n(it.get('age_years'))} лет ({it.get('age_source')}), повреждений {it.get('n_defects')},"
            f" баллы: срок {it.get('srok_ball')}, повр. {it.get('koef_povr_ball')}, вид {it.get('vnesniivid')},"
            f" обор. {it.get('sostoborudovania')}, кат. {it.get('kategorii')}, корр. {it.get('vnesnkorrozia')}/{it.get('vnunrenkorrozia')},"
            f" констр. {it.get('sostkonstrukz')} (заполнено {it.get('factors_filled')}/8);"
            f" износ {_n(it.get('wear_pct_known'))} %, кат. {it.get('category')}, последствия ×{_n(it.get('consequence'), 2)},"
            f" расход {_n(it.get('flow_t_h'))} т/ч, приоритет {_n(it.get('priority'), 3)}"
        )
    return "\n".join(lines)


def _sanitize(note: WearPlanNote, items: list[dict[str, Any]]) -> WearPlanNote:
    allowed = {it["lineid"] for it in items}
    for g in note.groups:
        g.line_ids = [i for i in g.line_ids if i in allowed]
    return note


async def plan(conn, *, calculation_id: Optional[int] = None, fragment_id: Optional[int] = None,
               top: int = MAX_SECTIONS, username: Optional[str] = None) -> dict[str, Any]:
    cid = calculation_id or await wear.latest_id(conn)
    if cid is None:
        raise ai_client.AiError("not_found", "Расчёт износа ещё не выполнялся", 404)
    try:
        summary = await wear.summary(conn, cid)
    except wear.WearError as exc:
        raise ai_client.AiError("not_found", str(exc), 404) from exc
    items = (await wear.sections(conn, cid, fragment_id=fragment_id, order="priority", limit=min(top, MAX_SECTIONS)))["items"]
    notes = _data_notes(summary)
    note = await ai_client.ask_structured(
        tool=TOOL, system=load_prompt("wear_plan"), user=build_user_input(summary, items, notes),
        output_format=WearPlanNote, effort="medium", username=username,
        details={"calculation_id": cid, "fragment_id": fragment_id, "sections": len(items)},
    )
    return {"calculation_id": cid, "summary": summary, "sections": items, "notes": notes,
            "plan": _sanitize(note, items).model_dump()}


def _data_notes(summary: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    lines = summary.get("lines") or 0
    filled = summary.get("factors_filled") or {}
    low = sum(v for k, v in filled.items() if int(k) <= 2)
    if lines and low > lines * 0.8:
        notes.append(f"У {low} из {lines} участков заполнено не более 2 факторов из 8 — индекс опирается на срок и повреждаемость")
    if lines and (summary.get("with_defects") or 0) == 0:
        notes.append("Журнал нарушений не содержит привязанных к участкам записей — повреждаемость везде 0")
    if lines and (summary.get("no_date") or 0) > lines * 0.1:
        notes.append(f"Без даты прокладки {summary.get('no_date')} участков")
    return notes
