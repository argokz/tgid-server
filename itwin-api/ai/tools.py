"""Помощник ИИ: поиск фразой, вопрос → выборка, объяснение качества данных, сопоставление колонок импорта (этап 6)."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ai import client as ai_client
from ai.prompts import load_prompt
from database import data_quality as dq
from database import network_select as ns
from database.consumer_load_diagnostics import get_consumer_load_diagnostics
from database.network_import import TARGET_FIELDS, suggest_mapping
from database.network_select import SelectSpec

# --- поиск фразой --------------------------------------------------------------------------

SEARCH_TOOL = "search"
TOOL_KEYS = ("defect", "shurf", "inspection", "repair", "pressureTest", "corrosionIndicator", "technicalCondition",
             "alseko", "electricalNetwork", "heatLoss", "temperatureGraph", "consumerLoad", "networkQueries",
             "regimeAnalysis", "outageSimulation", "throttlingCalculator", "hydraulicThematic", "wearIndex",
             "dataQuality", "excelReports", "pumpEquipment", "networkArmature", "networkRegulator", "networkBypass",
             "networkDiaphragm", "elevator")
MAX_RESULTS = 50


class SearchQuery(BaseModel):
    kind: Literal["node", "line", "consumer", "source", "tool", "unknown"]
    text: Optional[str] = None
    text2: Optional[str] = None
    fragment_id: Optional[int] = None
    diagnostic: Optional[Literal["zero_load", "closed", "disconnected", "not_calculated"]] = None
    consumer_type: Optional[Literal["generalized", "real"]] = None
    tool_key: Optional[str] = None
    scope_text: Optional[str] = None
    confidence: float = Field(0.0, ge=0, le=1)
    note: str = ""


_NODE_SQL = """
SELECT n.id, n.externalnodename AS name, n.fileid AS fragment_id, nt.name AS node_type,
       ST_X(ST_Transform(n.shape, 4326)) AS longitude, ST_Y(ST_Transform(n.shape, 4326)) AS latitude
  FROM nodes n LEFT JOIN nodetypes nt ON nt.id = n.nodetypeid
 WHERE n.removed = 0 AND n.internalnodeid IS NULL AND n.shape IS NOT NULL
   AND n.externalnodename ILIKE '%' || $1 || '%' AND ($2::int IS NULL OR n.fileid = $2)
 ORDER BY (LOWER(n.externalnodename) = LOWER($1)) DESC, LENGTH(n.externalnodename), n.externalnodename LIMIT $3
"""
_LINE_SQL = """
SELECT l.id, l.fileid AS fragment_id, n1.externalnodename AS node1, n2.externalnodename AS node2,
       h.diametercondit AS diameter,
       ST_X(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS longitude,
       ST_Y(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS latitude
  FROM linesobj l JOIN nodes n1 ON n1.id = l.nodeid1 JOIN nodes n2 ON n2.id = l.nodeid2
  LEFT JOIN heatpipesections h ON h.lineid = l.id
 WHERE l.removed = 0 AND l.shape IS NOT NULL AND ($3::int IS NULL OR l.fileid = $3)
   AND ((n1.externalnodename ILIKE '%' || $1 || '%' AND ($2::text IS NULL OR n2.externalnodename ILIKE '%' || $2 || '%'))
     OR (n2.externalnodename ILIKE '%' || $1 || '%' AND ($2::text IS NULL OR n1.externalnodename ILIKE '%' || $2 || '%')))
 ORDER BY l.fileid, l.id LIMIT $4
"""
_SOURCE_SQL = """
SELECT hs.id, COALESCE(hs.sourcename, hs.name) AS name, n.fileid AS fragment_id,
       ST_X(ST_Transform(n.shape, 4326)) AS longitude, ST_Y(ST_Transform(n.shape, 4326)) AS latitude
  FROM heatsources hs LEFT JOIN nodes n ON n.id = hs.nodeid
 WHERE COALESCE(hs.sourcename, hs.name) ILIKE '%' || $1 || '%' LIMIT $2
"""


async def execute_search(conn, q: SearchQuery) -> dict[str, Any]:
    """Выполнить разобранный запрос существующими выборками; LLM к SQL не допускается."""
    out: dict[str, Any] = {"query": q.model_dump(), "items": [], "open_tool": None}
    if q.kind == "node" and q.text:
        out["items"] = [dict(r) for r in await conn.fetch(_NODE_SQL, q.text.strip(), q.fragment_id, MAX_RESULTS)]
    elif q.kind == "line" and q.text:
        out["items"] = [dict(r) for r in await conn.fetch(_LINE_SQL, q.text.strip(), (q.text2 or "").strip() or None,
                                                          q.fragment_id, MAX_RESULTS)]
    elif q.kind == "source" and q.text:
        out["items"] = [dict(r) for r in await conn.fetch(_SOURCE_SQL, q.text.strip(), MAX_RESULTS)]
    elif q.kind == "consumer":
        data = await get_consumer_load_diagnostics(conn, page=1, page_size=MAX_RESULTS, diagnostic=q.diagnostic,
                                                   consumer_type=q.consumer_type, fragment_id=q.fragment_id,
                                                   search=q.text or None)
        out["items"] = data.get("items", [])
        out["total"] = data.get("total")
        out["open_tool"] = {"key": "consumerLoad", "scope": {"diagnostic": q.diagnostic, "fragment_id": q.fragment_id}}
    elif q.kind == "tool" and q.tool_key in TOOL_KEYS:
        out["open_tool"] = {"key": q.tool_key, "scope": {"text": q.scope_text, "fragment_id": q.fragment_id}}
    return out


async def search(conn, *, text: str, fragment_ids: Optional[list[int]] = None, username: Optional[str] = None) -> dict[str, Any]:
    user = f"Фраза: {text.strip()}"
    if fragment_ids:
        user += f"\nВидимые фрагменты карты: {fragment_ids[:20]}"
    q = await ai_client.ask_structured(tool=SEARCH_TOOL, system=load_prompt("search"), user=user, output_format=SearchQuery,
                                       effort="low", max_tokens=600, username=username)
    if q.tool_key and q.tool_key not in TOOL_KEYS:
        q.tool_key = None
    if q.fragment_id is None and fragment_ids and len(fragment_ids) == 1:
        q.fragment_id = fragment_ids[0]
    return await execute_search(conn, q)


# --- вопрос → выборка (database/network_select.py) ---------------------------------------------

SELECT_TOOL = "select"
MAX_CHOICES_IN_PROMPT = 40


class SelectPlan(BaseModel):
    spec: SelectSpec
    confidence: float = Field(0.0, ge=0, le=1)
    note: str = ""


def build_fields_text(payload: dict[str, Any]) -> str:
    """Справочник полей для модели: «ключ — подпись, единицы, вид; значения справочника»."""
    lines = []
    for target in payload["targets"]:
        lines.append(f"{target['key']} ({target['label']}):")
        for f in target["fields"]:
            units = f", {f['units']}" if f["units"] else ""
            line = f"- {f['key']} — {f['label']}{units}, {f['kind']}"
            if f["choices"]:
                shown = f["choices"][:MAX_CHOICES_IN_PROMPT]
                line += "; значения: " + ", ".join(f"{c['value']}={c['label']}" for c in shown)
            lines.append(line)
    return "\n".join(lines)


async def select_by_phrase(conn, *, text: str, fragment_ids: Optional[list[int]] = None,
                           bbox: Optional[tuple[float, float, float, float]] = None,
                           username: Optional[str] = None) -> dict[str, Any]:
    """Вопрос пользователя → SelectSpec (модель) → выборка сервером. Модель SQL не пишет; запрос
    проверяется тем же белым списком, что и в конструкторе, и показывается пользователю."""
    fields_text = build_fields_text(await ns.fields_payload(conn))
    user = f"Текущий год: {date.today().year}\nПоля:\n{fields_text}\n\nВопрос: {text.strip()}"
    if fragment_ids:
        user += f"\nВидимые фрагменты карты: {fragment_ids[:20]}"
    plan = await ai_client.ask_structured(tool=SELECT_TOOL, system=load_prompt("select"), user=user,
                                          output_format=SelectPlan, effort="low", max_tokens=1200,
                                          username=username)
    spec = plan.spec
    # фрагменты не названы — те, что на карте; у «рядом с узлом» место задаёт узел (он может быть в другом)
    if not spec.fragment_ids and fragment_ids and spec.near is None:
        spec = spec.model_copy(update={"fragment_ids": fragment_ids})
    if spec.in_view and not bbox:
        spec = spec.model_copy(update={"in_view": False})
    base = {"confidence": plan.confidence, "note": plan.note}
    if plan.confidence == 0 and not spec.conditions and not spec.near:
        return {**base, "spec": spec.model_dump(), "description": "", "items": [], "total": 0}
    try:
        result = await ns.run_select(conn, spec, bbox=bbox, user_key=username or "")
    except ns.SelectError as exc:
        # запрос модели не прошёл проверку — показать его, чтобы пользователь поправил в конструкторе
        return {**base, "spec": spec.model_dump(), "description": "", "items": [], "total": 0,
                "error": exc.message}
    return {**base, **result}


# --- качество данных: объяснение -----------------------------------------------------------

DQ_TOOL = "data_quality"
MAX_EXAMPLES = 5


class RuleAdvice(BaseModel):
    rule: str
    cause: str
    impact: str
    fix_tool: Literal["card", "group_setters", "topology", "alseko", "import"]
    fix_steps: list[str] = Field(default_factory=list)
    priority: Literal[1, 2, 3]


class DataQualityAdvice(BaseModel):
    summary: str
    rules: list[RuleAdvice] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def build_dq_input(summary: dict[str, Any], examples: dict[str, list[dict[str, Any]]]) -> str:
    lines = [f"Фрагмент: {summary.get('fragment_id') or 'вся сеть'}. Ошибок {summary.get('total_errors')}, "
             f"предупреждений {summary.get('total_warnings')}.", "Правила:"]
    for it in summary.get("items", []):
        n = "нет данных (ошибка запроса)" if it.get("count") is None else it["count"]
        extra = f", суммарно {it['sum_gcal_h']} Гкал/ч" if it.get("sum_gcal_h") is not None else ""
        lines.append(f"  - {it['rule']} [{it['severity']}] «{it['label']}»: {n}{extra}; исправлять: {it.get('fix_label')}")
        for ex in examples.get(it["rule"], [])[:MAX_EXAMPLES]:
            brief = {k: v for k, v in ex.items() if k not in ("longitude", "latitude") and v is not None}
            lines.append(f"      пример: {brief}")
    return "\n".join(lines)


async def explain_data_quality(conn, *, fragment_id: Optional[int] = None, username: Optional[str] = None) -> dict[str, Any]:
    summary = await dq.summary(conn, fragment_id=fragment_id)
    examples: dict[str, list[dict[str, Any]]] = {}
    for it in summary["items"]:
        if it.get("count"):
            try:
                examples[it["rule"]] = (await dq.issues(conn, it["rule"], fragment_id=fragment_id, limit=MAX_EXAMPLES))["items"]
            except Exception:  # noqa: BLE001
                examples[it["rule"]] = []
    advice = await ai_client.ask_structured(tool=DQ_TOOL, system=load_prompt("data_quality"),
                                            user=build_dq_input(summary, examples), output_format=DataQualityAdvice,
                                            effort="medium", username=username, details={"fragment_id": fragment_id})
    known = {it["rule"] for it in summary["items"]}
    advice.rules = [r for r in advice.rules if r.rule in known]
    return {"summary": summary, "advice": advice.model_dump()}


# --- импорт: сопоставление колонок ----------------------------------------------------------

IMPORT_TOOL = "import_mapping"


class ColumnMatch(BaseModel):
    target: str
    column: Optional[str] = None
    confidence: float = Field(0.0, ge=0, le=1)


class ImportMapping(BaseModel):
    matches: list[ColumnMatch] = Field(default_factory=list)
    note: str = ""


def build_import_input(mode: str, columns: list[str], samples: list[list[Any]], has_geometry: bool) -> str:
    targets = TARGET_FIELDS.get(mode, {})
    lines = [f"Режим импорта: {mode}; геометрия в файле: {'да' if has_geometry else 'нет'}", "Поля назначения:"]
    lines += [f"  - {k}: {label}{' (обязательное)' if req else ''}" for k, (label, req) in targets.items()]
    lines.append("Колонки файла: " + ", ".join(columns))
    for i, row in enumerate(samples[:5], start=1):
        lines.append(f"  строка {i}: " + "; ".join(f"{c}={str(v)[:40]}" for c, v in zip(columns, row)))
    return "\n".join(lines)


async def suggest_import_mapping(*, mode: str, columns: list[str], samples: list[list[Any]], has_geometry: bool,
                                 username: Optional[str] = None) -> dict[str, Any]:
    if mode not in TARGET_FIELDS:
        raise ai_client.AiError("bad_mode", f"Неизвестный режим импорта: {mode}", 400)
    heuristic = suggest_mapping(mode, columns, has_geometry)
    result = await ai_client.ask_structured(tool=IMPORT_TOOL, system=load_prompt("import_mapping"),
                                            user=build_import_input(mode, columns, samples, has_geometry),
                                            output_format=ImportMapping, effort="low", max_tokens=1500, username=username,
                                            details={"mode": mode, "columns": len(columns)})
    targets = set(TARGET_FIELDS[mode])
    cols = set(columns)
    mapping: dict[str, str] = {}
    confidence: dict[str, float] = {}
    used: set[str] = set()
    for m in sorted(result.matches, key=lambda x: -x.confidence):
        if m.target in targets and m.column in cols and m.column not in used and m.target not in mapping:
            mapping[m.target] = m.column
            confidence[m.target] = m.confidence
            used.add(m.column)
    # эвристика остаётся для полей, которые модель не заполнила
    for target, col in heuristic.items():
        if target not in mapping and col not in used:
            mapping[target] = col
            confidence[target] = 1.0
            used.add(col)
    return {"mapping": mapping, "confidence": confidence, "heuristic": heuristic, "note": result.note}
