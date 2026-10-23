"""Помощник ИИ: объяснение протокола расчёта sety (этап 3 плана).

Вход — записи calculation_protocol (уже разобранные utils/calc_protocol.py: категория, важность,
объекты, fix). Детерминированно: сводка, регуляторы с «задано/получено» и дефицитом; LLM —
корневые причины, что открыть и какие флаги попробовать. Результат кешируется в
calculation_protocol.ai_summary (колонка — пункт схемы database/city_schema.py).
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ai import client as ai_client
from ai.prompts import load_prompt
from ai.schemas import ObjectRef
from database.calc_protocols import get_protocols
from utils.calc_protocol import CATEGORY_LABELS

TOOL = "calc_protocol"
# Сколько сообщений одной категории показывать модели целиком; остальные — счётчиком
MAX_ENTRIES_PER_CATEGORY = 8
MAX_ENTRY_TEXT = 400
MAX_OBJECTS_PER_ENTRY = 4

Fix = Literal["calc_params", "fixed_head", "temp_graph", "rs", "object"]
NEXT_RUN_FLAGS = ("-Tn", "-iter", "-no_kv", "-rd_old", "-rr_old", "-ok_old", "-tg", "-leto", "-dross_yes",
                  "-mag_fragment")


class RootCause(BaseModel):
    category: str = Field(description="Категория из входа (rs, regulator, subnetwork, …)")
    title: str
    why: str
    action: str
    fix: Optional[Fix] = None
    objects: list[ObjectRef] = Field(default_factory=list)


class NextRunFlag(BaseModel):
    flag: str = Field(description="Флаг запуска sety из разрешённого списка")
    reason: str


class ProtocolExplanation(BaseModel):
    summary: str
    root_causes: list[RootCause] = Field(default_factory=list)
    regulators_note: str = ""
    next_run: list[NextRunFlag] = Field(default_factory=list)
    data_quality: list[str] = Field(default_factory=list)


# «Регулятор давления [..] не может обеспечить давление в узле [..]\n Задано 59.0 м. получено 49.66 м., расход 69.96 т/ч»
_SETPOINT_RE = re.compile(
    r"Задано\s+(?P<set>-?[\d.,]+)\s*м\.?\s*получено\s+(?P<got>-?[\d.,]+)\s*м\.?(?:,\s*расход\s+(?P<flow>-?[\d.,]+)\s*т/ч)?",
    re.I,
)
_KIND_RE = re.compile(r"Регулятор\s+(давления|расхода|перепада)", re.I)


def _num(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def regulators_from_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Регуляторы, не удержавшие уставку: задано/получено/расход и дефицит (детерминированно).

    deficit > 0 — напора не хватает (получено меньше заданного: клапан открыт, причина выше по сети);
    deficit < 0 — получено больше заданного (клапан закрыт до предела или уставка ниже достижимой).
    """
    out: list[dict[str, Any]] = []
    for e in entries:
        if e.get("category") != "regulator":
            continue
        m = _SETPOINT_RE.search(e.get("text") or "")
        if not m:
            continue
        setpoint, got = _num(m.group("set")), _num(m.group("got"))
        if setpoint is None or got is None:
            continue
        kind_m = _KIND_RE.search(e.get("text") or "")
        kind = {"давления": "РД", "расхода": "РР", "перепада": "РПД"}.get((kind_m.group(1) if kind_m else "").lower(), "РД")
        deficit = round(setpoint - got, 2)
        out.append({
            "seq": e.get("seq"),
            "kind": kind,
            "label": (e.get("objects") or [{}])[0].get("label") or "",
            "objects": e.get("objects") or [],
            "setpoint": setpoint,
            "actual": got,
            "flow": _num(m.group("flow")),
            "deficit": deficit,
            "state": "недобор напора" if deficit > 0 else "перебор напора",
            "severity": e.get("severity"),
            "count": e.get("count", 1),
        })
    out.sort(key=lambda r: -abs(r["deficit"]))
    return out


def _object_line(o: dict[str, Any]) -> str:
    kind = o.get("kind")
    if kind == "line2":
        return f"line2#{o.get('id1')}-{o.get('id2')} «{o.get('label', '')}»"
    return f"{kind}#{o.get('id')} «{o.get('label', '')}»"


def build_user_input(records: list[dict[str, Any]]) -> str:
    """Компактный текст протокола для модели: заголовок, параметры, сводка, сообщения по категориям."""
    lines: list[str] = []
    first = records[0] if records else {}
    summary = (first.get("summary") or {}) if first else {}
    header = summary.get("header") or []
    if header:
        lines.append("Заголовок протокола:")
        lines.extend(f"  {h}" for h in header)
    params = first.get("params") if first else None
    if params:
        lines.append(f"Параметры запуска: {params}")
    lines.append(f"Запусков (фрагментов) в протоколе: {len(records)}; "
                 f"статусы: {', '.join(str(r.get('status')) for r in records)}")

    entries: list[dict[str, Any]] = []
    for r in records:
        entries.extend(r.get("entries") or [])
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for e in entries:
        by_cat.setdefault(e.get("category") or "other", []).append(e)
    errors = sum(1 for e in entries if e.get("severity") == "error")
    warnings = len(entries) - errors
    lines.append(f"Всего сообщений: ошибок {errors}, предупреждений {warnings}.")

    # ошибки первыми, затем категории по числу сообщений
    order = sorted(by_cat.items(), key=lambda kv: (-sum(1 for e in kv[1] if e.get("severity") == "error"), -len(kv[1])))
    for cat, items in order:
        label = CATEGORY_LABELS.get(cat, cat)
        fix = next((e.get("fix") for e in items if e.get("fix")), None)
        lines.append(f"\n[{cat}] {label} — {len(items)} сообщ." + (f", fix={fix}" if fix else ""))
        for e in items[:MAX_ENTRIES_PER_CATEGORY]:
            text = " ".join((e.get("text") or "").split())[:MAX_ENTRY_TEXT]
            cnt = f" ×{e['count']}" if e.get("count", 1) > 1 else ""
            lines.append(f"  - ({e.get('severity')}){cnt} {text}")
            objs = e.get("objects") or []
            if objs:
                shown = ", ".join(_object_line(o) for o in objs[:MAX_OBJECTS_PER_ENTRY])
                more = f" … ещё {len(objs) - MAX_OBJECTS_PER_ENTRY}" if len(objs) > MAX_OBJECTS_PER_ENTRY else ""
                lines.append(f"    объекты: {shown}{more}")
        if len(items) > MAX_ENTRIES_PER_CATEGORY:
            lines.append(f"  … и ещё {len(items) - MAX_ENTRIES_PER_CATEGORY} сообщ. этой категории")

    regs = regulators_from_entries(entries)
    if regs:
        lines.append("\nРегуляторы с отклонением от уставки (посчитано заранее):")
        for r in regs[:12]:
            flow = f", расход {r['flow']} т/ч" if r["flow"] is not None else ""
            lines.append(f"  - {r['kind']} «{r['label']}»: задано {r['setpoint']} м, получено {r['actual']} м, "
                         f"отклонение {r['deficit']:+} м ({r['state']}){flow}")
    return "\n".join(lines)


def _allowed_objects(records: list[dict[str, Any]]) -> set[tuple]:
    keys: set[tuple] = set()
    for r in records:
        for e in r.get("entries") or []:
            for o in e.get("objects") or []:
                keys.add((o.get("kind"), o.get("id"), o.get("id1"), o.get("id2")))
            comp = (e.get("component") or {}).get("object")
            if comp:
                keys.add((comp.get("kind"), comp.get("id"), comp.get("id1"), comp.get("id2")))
    return keys


def _sanitize(expl: ProtocolExplanation, records: list[dict[str, Any]]) -> ProtocolExplanation:
    """Объекты — только из входа; флаги — только из разрешённого списка."""
    allowed = _allowed_objects(records)
    for cause in expl.root_causes:
        cause.objects = [o for o in cause.objects if (o.kind, o.id, o.id1, o.id2) in allowed]
    expl.next_run = [f for f in expl.next_run if f.flag.split("=")[0].split()[0] in NEXT_RUN_FLAGS]
    return expl


async def _column_exists(conn) -> bool:
    return bool(await conn.fetchval(
        "select exists (select 1 from information_schema.columns where table_schema = 'public'"
        " and table_name = 'calculation_protocol' and column_name = 'ai_summary')"
    ))


async def explain(
    conn,
    *,
    calculation_id: Optional[int] = None,
    protocol_id: Optional[int] = None,
    request_id: Optional[str] = None,
    username: Optional[str] = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Объяснение протокола: кеш из ai_summary первой записи, иначе запрос к модели и запись кеша."""
    records = await get_protocols(conn, protocol_id=protocol_id, request_id=request_id,
                                  calculation_id=calculation_id)
    if not records:
        raise ai_client.AiError("not_found", "Протокол расчёта не найден", 404)
    # расчёт по списку: все фрагменты запроса — один разбор
    if request_id is None and records[0].get("request_id") and len(records) == 1:
        siblings = await get_protocols(conn, request_id=records[0]["request_id"])
        if len(siblings) > 1:
            records = siblings
    ids = [r["id"] for r in records]
    cacheable = await _column_exists(conn)

    if cacheable and not refresh:
        row = await conn.fetchrow(
            "select ai_summary, ai_summary_at from calculation_protocol where id = $1 and ai_summary is not null",
            ids[0],
        )
        if row:
            cached = row["ai_summary"]
            cached = json.loads(cached) if isinstance(cached, str) else cached
            if isinstance(cached, dict) and cached.get("protocol_ids") == ids:
                return {**cached, "cached": True}

    entries: list[dict[str, Any]] = []
    for r in records:
        entries.extend(r.get("entries") or [])
    regulators = regulators_from_entries(entries)
    result: dict[str, Any] = {
        "protocol_ids": ids,
        "calculation_ids": [r.get("calculationid") for r in records],
        "regulators": regulators,
        "explanation": None,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cached": False,
    }
    if not entries:
        result["explanation"] = ProtocolExplanation(
            summary="В протоколе нет ошибок и предупреждений — расчёт прошёл без замечаний.",
        ).model_dump()
    else:
        expl = await ai_client.ask_structured(
            tool=TOOL,
            system=load_prompt("calc_protocol"),
            user=build_user_input(records),
            output_format=ProtocolExplanation,
            effort="high",
            username=username,
            details={"protocol_ids": ids, "calculation_id": records[0].get("calculationid")},
        )
        result["explanation"] = _sanitize(expl, records).model_dump()

    if cacheable:
        try:
            await conn.execute(
                "update calculation_protocol set ai_summary = $2::jsonb, ai_summary_at = now() where id = $1",
                ids[0], json.dumps({k: v for k, v in result.items() if k != "cached"}, ensure_ascii=False),
            )
        except Exception:  # noqa: BLE001 — кеш не обязателен (нет права на UPDATE)
            pass
    return result
