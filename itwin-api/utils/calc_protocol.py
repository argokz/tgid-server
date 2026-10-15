"""Разбор протокола расчёта sety (stdout с -color) в записи для анализа в вебе.

sety печатает протокол HTML-фрагментами (sety/any/colors.py): красный — ошибка, коричневый
(yellow) — предупреждение, жирный — заголовки; ссылки на объекты (sety/w_print.py):
  <a name='node' id='<nodes.id>'>…</a>              — узел (для узлов внутренней схемы — узел-владелец);
  <a name='line' id='<linesobj.id>'>…</a>           — участок;
  <a name='line2' id1='<nodes.id>' id2='<nodes.id>'> — участок/устройство между двумя узлами.
Сообщение может занимать несколько строк (цветной span закрывается на следующей строке, строки
продолжения начинаются с отступа). Запись — одно сообщение: важность, текст, объекты, категория,
вид исправления (fix) — что открыть в вебе, чтобы поправить исходные данные.
"""

from __future__ import annotations

import html
import re
from typing import Any, Optional

_TOKEN_RE = re.compile(
    r"<span\s+style=\"color:(?P<color>[a-z]+)\">"
    r"|<span\s+style=\"font-weight:bold;\">"
    r"|<style=\"[^\"]*>"                       # u/i из colors.py (битый тег) — как span
    r"|(?P<close></span>)"
    r"|<a\s(?P<attrs>[^>]*)>(?P<label>.*?)</a>",
    re.S,
)
_ATTR_RE = re.compile(r"(\w+)='([^']*)'")
_TAG_RE = re.compile(r"<[^>]+>")

_SEVERITY_BY_COLOR = {"red": "error", "brown": "warning", "yellow": "warning"}
_SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}

# (категория, подпись, fix, шаблон) — первый подходящий; fix — что открыть в вебе для исправления:
#   calc_params — параметры расчёта; fixed_head — узел с заданным напором (карточка узла);
#   temp_graph — температурный график источника; rs — расчётные схемы (справочник);
#   object — карточка объекта из сообщения.
CATEGORIES: list[tuple[str, str, Optional[str], re.Pattern]] = [
    ("calc_params", "Параметры расчёта", "calc_params",
     re.compile(r"Температура наружного воздуха должна|Нет данных для расчета", re.I)),
    ("subnetwork", "Подсети без узла с ЗН", "fixed_head",
     re.compile(r"подсет\w* без узла с заданн", re.I)),
    ("divergence", "Расчёт не выполнен", "object",
     re.compile(r"система уравнений не решена|Ошибка расчета|Невязка", re.I)),
    ("fixed_head", "Узлы с заданным напором", "fixed_head",
     re.compile(r"узл\w* с заданн?ым напором|не задан узел с ЗН", re.I)),
    ("temp_graph", "Температурный график", "temp_graph",
     re.compile(r"температурн\w* график", re.I)),
    ("rs", "Расчётные схемы (РС)", "rs",
     re.compile(r"Расч[её]тн\w* схем|Код\w* РС\b|\bВ РС\b", re.I)),
    ("consumer_codes", "Коды потребителей", "object",
     re.compile(r"Не задан Код расч[её]тных температур|Не задан Код удельных расходов|не заданы Удельные расходы", re.I)),
    ("source", "Источники", "object",
     re.compile(r"источник|нет источников тепла", re.I)),
    ("pump", "Насосы", "object", re.compile(r"насос", re.I)),
    ("regulator", "Регуляторы и байпасы", "object", re.compile(r"регулятор|байпас", re.I)),
    ("valve", "Клапаны", "object", re.compile(r"клапан", re.I)),
    ("consumer_head", "Напоры у потребителей", "object",
     re.compile(r"располагаем\w* напор|напор в (подающем|обратном)|меньше высоты здания", re.I)),
    ("consumer", "Потребители", "object", re.compile(r"потребител", re.I)),
]
CATEGORY_LABELS = {c[0]: c[1] for c in CATEGORIES} | {"other": "Прочее"}

_FRAGMENT_LIST_RE = re.compile(r"^==== Фрагмент (\d+): (.*) ====$")
_COMPONENT_RE = re.compile(r"^Фрагмент (\d+)/(\d+)\b")
_DURATION_RE = re.compile(r"Время расчета\s+([\d.]+)")


def _plain(fragment: str) -> str:
    return html.unescape(_TAG_RE.sub("", fragment))


def _object(attrs: str, label: str) -> Optional[dict[str, Any]]:
    a = dict(_ATTR_RE.findall(attrs))
    text = _plain(label).strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    try:
        if a.get("name") == "line2":
            id1, id2 = int(a["id1"]), int(a["id2"])
            if id1 < 0 and id2 < 0:
                return None
            return {"kind": "line2", "id1": id1, "id2": id2, "label": text}
        if a.get("name") in ("node", "line"):
            oid = int(a["id"])
            if oid < 0:
                return None
            return {"kind": a["name"], "id": oid, "label": text}
    except (KeyError, ValueError):
        return None
    return None


def _scan_line(line: str, stack: list[str]) -> tuple[str, str, list[dict], bool]:
    """Текст строки, важность (по самому «сильному» цвету в строке), объекты; stack — открытые span."""
    if line.startswith('<span style="color:') and stack:
        # строка начинается с нового цветного сообщения: незакрытый span предыдущего (так бывает
        # в sety, напр. «работает в режиме реверса») не тянем дальше
        stack.clear()
    severity = "info"
    for kind in stack:
        severity = max(severity, _SEVERITY_BY_COLOR.get(kind, "info"), key=_SEVERITY_RANK.get)
    started_colored = any(k in _SEVERITY_BY_COLOR for k in stack)
    objects: list[dict] = []
    pos = 0
    text_parts: list[str] = []
    for m in _TOKEN_RE.finditer(line):
        text_parts.append(line[pos:m.start()])
        pos = m.end()
        if m.group("close"):
            if stack:
                stack.pop()
        elif m.group("attrs") is not None:
            obj = _object(m.group("attrs"), m.group("label"))
            if obj:
                objects.append(obj)
            text_parts.append(m.group("label"))
        elif m.group("color"):
            stack.append(m.group("color"))
            severity = max(severity, _SEVERITY_BY_COLOR.get(m.group("color"), "info"), key=_SEVERITY_RANK.get)
        else:
            stack.append("b")
    text_parts.append(line[pos:])
    return _plain("".join(text_parts)).rstrip(), severity, objects, started_colored


def categorize(text: str) -> tuple[str, Optional[str]]:
    for code, _label, fix, pattern in CATEGORIES:
        if pattern.search(text):
            return code, fix
    return "other", None


def parse_protocol(output: str) -> dict[str, Any]:
    """{'entries': [...], 'summary': {...}} — только ошибки и предупреждения, с контекстом."""
    entries: list[dict[str, Any]] = []
    header: list[str] = []
    stack: list[str] = []
    fragment_id: Optional[int] = None
    component: Optional[dict[str, Any]] = None
    current: Optional[dict[str, Any]] = None
    duration: Optional[float] = None
    seen: dict[tuple, dict] = {}
    started = False

    def close():
        nonlocal current
        if current is None:
            return
        cur, current = current, None
        cur["text"] = "\n".join(cur.pop("lines")).strip()
        cur["category"], cur["fix"] = categorize(cur["text"])
        if not cur["objects"] and cur["component"] and cur["component"].get("object"):
            # «Во фрагменте нет источников тепла» и т.п. — объект подсети (её узел с заданным напором)
            cur["objects"] = [dict(cur["component"]["object"], context=True)]
        if cur["fix"] == "object" and not cur["objects"]:
            cur["fix"] = None
        # повторы одного сообщения (sety печатает одно и то же для каждой итерации)
        key = (cur["severity"], cur["text"], cur["fragment_id"], (cur["component"] or {}).get("index"))
        if key in seen:
            seen[key]["count"] += 1
            return
        cur["count"] = 1
        seen[key] = cur
        entries.append(cur)

    for raw in (output or "").replace("\r\n", "\n").split("\n"):
        text, severity, objects, continued = _scan_line(raw, stack)
        stripped = text.strip()

        m = _FRAGMENT_LIST_RE.match(stripped)
        if m:
            close()
            fragment_id, component = int(m.group(1)), None
            continue
        m = _COMPONENT_RE.match(stripped)
        if m:
            close()
            started = True
            component = {"index": int(m.group(1)), "total": int(m.group(2)),
                         "object": objects[0] if objects else None}
            continue
        m = _DURATION_RE.search(stripped)
        if m:
            duration = float(m.group(1))
        if not started and severity == "info" and stripped and len(header) < 8 and not entries and current is None:
            if stripped.startswith(("Расчет начат",)):
                started = True
            elif "фрагментов" not in stripped:
                header.append(stripped)
            continue

        if not stripped or set(stripped) <= {"-", "=", "*"}:
            close()
            continue

        if current is not None and (
            continued
            or (text[:1].isspace() and (severity == current["severity"] or severity == "info"))
            or (current["lines"] == [current["lines"][0]] and current["lines"][0].startswith("Ошибка во фрагменте")
                and severity == "error" and not current["objects"])
        ):
            current["lines"].append(text)
            current["objects"].extend(objects)
            if _SEVERITY_RANK[severity] > _SEVERITY_RANK[current["severity"]]:
                current["severity"] = severity
            continue

        close()
        if severity == "info":
            continue
        current = {
            "seq": len(entries) + 1,
            "severity": severity,
            "lines": [text],
            "objects": list(objects),
            "fragment_id": fragment_id,
            "component": component,
        }
    close()

    for i, e in enumerate(entries, start=1):
        e["seq"] = i
        uniq, keys = [], set()
        for o in e["objects"]:
            k = (o["kind"], o.get("id"), o.get("id1"), o.get("id2"))
            if k not in keys:
                keys.add(k)
                uniq.append(o)
        e["objects"] = uniq

    by_category: dict[str, dict[str, int]] = {}
    for e in entries:
        c = by_category.setdefault(e["category"], {"error": 0, "warning": 0})
        c[e["severity"]] += 1
    return {
        "entries": entries,
        "summary": {
            "errors": sum(1 for e in entries if e["severity"] == "error"),
            "warnings": sum(1 for e in entries if e["severity"] == "warning"),
            "by_category": by_category,
            "category_labels": {k: CATEGORY_LABELS[k] for k in by_category},
            "header": header,
            "duration_s": duration,
        },
    }
