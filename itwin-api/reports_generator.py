"""Генерация печатных форм (HTML) и ведомостей (Excel).

Данные берутся из тех же проверенных read-only функций, что и журналы web-UI,
поэтому имена полей всегда соответствуют реальной схеме БД. Прямой SQL здесь
раньше ссылался на несуществующие колонки (nodes.name, networkarmatures) и
падал с 500 — теперь источник данных один на журнал и на отчёт.
"""

import asyncio
import io
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import openpyxl
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from database.connect import acquire_conn
from database.fragment_filter import LINE_IN_FRAGMENTS_SQL, LIVE_LINE_SQL
from database.consumer_load_diagnostics import get_consumer_load_diagnostics
from database.defects import get_defects
from database.inspections import get_inspections
from database.network_armatures import get_network_armatures
from database.network_bypasses import get_network_bypasses
from database.pressure_tests import get_pressure_tests
from database.pump_equipment import get_installed_pumps
from database.repairs import get_repairs
from database import ut_out_columns as UT
from database.shurfs import get_shurfs

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "report_templates")


def get_template_content(filename: str) -> str:
    path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="windows-1251", errors="ignore") as f:
            return f.read()
    return ""


def _esc(value: Any) -> str:
    """Экранирование значения для вставки в HTML-таблицу."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _object_title(item: Dict[str, Any]) -> str:
    if item.get("line_id"):
        return f"Участок #{item['line_id']}"
    if item.get("node_id"):
        return f"Узел #{item['node_id']}"
    return "—"


# --- HTML-формы -------------------------------------------------------------

FORM_TITLES = {
    "f10_remont": "Форма 10. Журнал ремонтов",
    "f11_defect": "Форма 11. Журнал нарушений",
    "f12_pits": "Форма 12. Журнал шурфовок",
    "f13_inspection": "Форма 13. Журнал осмотров",
    "f14_pressure": "Форма 14. Журнал опрессовок",
}

FORM_COLUMNS: Dict[str, List[str]] = {
    "f10_remont": ["Объект", "Название", "Вид ремонта", "Состояние", "Категория",
                   "План: начало", "План: окончание", "Ответственный"],
    "f11_defect": ["Объект", "Название", "Источник", "Состояние", "Категория",
                   "Дата обнаружения", "Описание"],
    "f12_pits": ["Объект", "Название", "Назначение", "Состояние", "Дата вскрытия", "Утверждение"],
    "f13_inspection": ["Название", "Дата", "Ответственный", "Подразделение", "Акт"],
    "f14_pressure": ["Название", "Состояние", "Вид испытания", "Источник тепла",
                     "План: начало", "Ответственный"],
}


def _form_rows(form_id: str, items: List[Dict[str, Any]]) -> List[List[Any]]:
    if form_id == "f10_remont":
        return [[
            _object_title(i), i.get("name"), i.get("repair_type_name"), i.get("state_name"),
            i.get("category_name"), i.get("planned_start"), i.get("planned_finish"),
            i.get("responsible_name"),
        ] for i in items]
    if form_id == "f11_defect":
        return [[
            _object_title(i), i.get("name"), i.get("source_name"), i.get("state_name"),
            i.get("category_name"), i.get("detected_at"), i.get("description"),
        ] for i in items]
    if form_id == "f12_pits":
        return [[
            _object_title(i), i.get("name"), i.get("purpose_name"), i.get("state_name"),
            i.get("opening_date") or i.get("detected_at"), i.get("approval_name"),
        ] for i in items]
    if form_id == "f13_inspection":
        return [[
            i.get("name"), i.get("inspection_date") or i.get("detected_at"),
            i.get("responsible_name"), i.get("subdivision_name"), i.get("act_number"),
        ] for i in items]
    if form_id == "f14_pressure":
        return [[
            i.get("name"), i.get("state_name"), i.get("test_type_name"),
            i.get("heat_source_name"), i.get("planned_start"), i.get("responsible_name"),
        ] for i in items]
    return []


FORM_LOADERS: Dict[str, Callable] = {
    "f10_remont": get_repairs,
    "f11_defect": get_defects,
    "f12_pits": get_shurfs,
    "f13_inspection": get_inspections,
    "f14_pressure": get_pressure_tests,
}


async def generate_form_html(form_id: str, search: Optional[str] = None) -> str:
    title = FORM_TITLES.get(form_id, f"Отчёт {form_id}")
    loader = FORM_LOADERS.get(form_id)

    if loader is None:
        return _render_html(title, [], [], note=f"Неизвестная форма отчёта: {form_id}")

    async with acquire_conn() as conn:
        data = await loader(conn, page=1, page_size=1000, search=search)

    items = data.get("items", []) if isinstance(data, dict) else []
    columns = FORM_COLUMNS.get(form_id, [])
    rows = _form_rows(form_id, items)

    note = None
    if not rows:
        note = "По заданным условиям записей не найдено."

    body = _render_html(title, columns, rows, note=note, total=data.get("total") if isinstance(data, dict) else None)

    # Если для формы есть legacy-шаблон с таблицей — вставляем строки в него
    base_html = get_template_content(f"{form_id}.html")
    if base_html and "</table>" in base_html:
        rows_html = "".join(
            "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>" for row in rows
        )
        head, _, tail = base_html.partition("</table>")
        return head + rows_html + "</table>" + tail

    return body


def _render_html(
    title: str,
    columns: List[str],
    rows: List[List[Any]],
    note: Optional[str] = None,
    total: Optional[int] = None,
) -> str:
    head_html = "".join(f"<th>{_esc(c)}</th>" for c in columns)
    rows_html = "".join(
        "<tr>" + "".join(f"<td>{_esc(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    note_html = f'<p class="note">{_esc(note)}</p>' if note else ""
    total_html = f'<p class="meta">Всего записей: {total}</p>' if total is not None else ""
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>{_esc(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; color: #1a1a1a; }}
    h2 {{ font-size: 18px; margin: 0 0 4px; }}
    .meta, .note {{ color: #555; font-size: 13px; margin: 4px 0 12px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; font-size: 13px; text-align: left; vertical-align: top; }}
    th {{ background: #1f497d; color: #fff; position: sticky; top: 0; }}
    tr:nth-child(even) td {{ background: #fafafa; }}
    @media print {{ body {{ margin: 0; }} th {{ position: static; }} }}
  </style>
</head>
<body>
  <h2>{_esc(title)}</h2>
  {total_html}
  {note_html}
  <table><thead><tr>{head_html}</tr></thead><tbody>{rows_html}</tbody></table>
</body>
</html>"""


# --- Excel-ведомости --------------------------------------------------------
#
# Отбор по фрагменту — единое правило database.fragment_filter: участок по linesobj.fileid,
# арматура/байпасы/насосы — по fileid своего участка, потребители — по fileid узла.
# Лимит строк (QA F14): раньше молча 5000. Теперь по фрагменту выгружается всё (до предела
# листа Excel), по всей сети — до MAX_NETWORK_REPORT_ROWS (с запасом больше всех ведомостей
# Алматы: участков 121 тыс.). Если строк больше — файл не режется молча: лист «Примечание»,
# заголовки X-Report-Rows/X-Report-Total/X-Report-Truncated и предупреждение в UI.

EXCEL_MAX_DATA_ROWS = 1_048_575  # 1 048 576 строк листа минус шапка
MAX_NETWORK_REPORT_ROWS = 200_000


@dataclass
class ReportScope:
    fragment_ids: Optional[List[int]] = None
    limit: int = MAX_NETWORK_REPORT_ROWS
    year: Optional[int] = None


@dataclass
class SheetData:
    headers: List[str]
    rows: List[List[Any]]
    total: int
    # Дополнительные листы книги (как в шаблонах десктопа: «Вх.Участки» + «Гидравлика»)
    extra_sheets: List[Tuple[str, "SheetData"]] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class ExcelReport:
    content: bytes
    rows: int
    total: int
    fragment_ids: Optional[List[int]] = None
    fragment_filter_applied: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def truncated(self) -> bool:
        return self.total > self.rows

    def headers(self) -> Dict[str, str]:
        return {
            "X-Report-Rows": str(self.rows),
            "X-Report-Total": str(self.total),
            "X-Report-Truncated": "1" if self.truncated else "0",
            "X-Report-Fragments": ",".join(str(f) for f in self.fragment_ids or []) if self.fragment_filter_applied else "",
        }


def report_limit(fragment_ids: Optional[List[int]]) -> int:
    return EXCEL_MAX_DATA_ROWS if fragment_ids else MAX_NETWORK_REPORT_ROWS


def report_filename(doc_type: str, *, year: Optional[int] = None, fragment_ids: Optional[List[int]] = None) -> str:
    suffix = f"_{year}" if year else ""
    if fragment_ids:
        suffix += f"_f{fragment_ids[0]}" if len(fragment_ids) == 1 else "_frag"
    return f"report_{doc_type}{suffix}.xlsx"


async def _paged_items(fetch: Callable, conn, scope: ReportScope, *, by_fragment: bool = True, **filters):
    """Все записи журнала (одна страница размером с лимит) — по фрагментам или по всей сети.

    Возвращает (items, total); total — сколько записей есть в БД, items — не больше scope.limit.
    """
    targets: List[Optional[int]] = list(scope.fragment_ids) if (by_fragment and scope.fragment_ids) else [None]
    items: List[Dict[str, Any]] = []
    total = 0
    for fragment_id in targets:
        remaining = scope.limit - len(items)
        extra = {"fragment_id": fragment_id} if fragment_id is not None else {}
        data = await fetch(conn, page=1, page_size=max(remaining, 1), **extra, **filters)
        total += int(data.get("total") or 0)
        if remaining > 0:
            items.extend(data.get("items", [])[:remaining])
    return items, total


_PIPELINES_WHERE = f"WHERE {LIVE_LINE_SQL} AND {LINE_IN_FRAGMENTS_SQL}"

# --- Ведомости по шаблонам десктопа (QA F15) --------------------------------------------
# Состав и порядок колонок — как в gid6 excel2: G_UT (sql2/Участки.sql + OUT_Участки.sql) и
# G_ZD (sql2/Задвижки.sql + OUT_Задвижки1.sql). Отбор по фрагменту и лимит — правила веба
# (участок по linesobj.fileid, a0abf5c). Результаты расчёта — последний расчёт фрагмента участка
# (как getOutID десктопа); если расчётов нет, листы результатов содержат только шапку.

_SIGN1 = ("CASE {e} WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' "
          "WHEN 4 THEN 'П' WHEN 5 THEN 'О' END")
_SIGN2 = ("CASE {e} WHEN 1 THEN ' ' WHEN 2 THEN 'П' WHEN 3 THEN 'О' "
          "WHEN 4 THEN 'О' WHEN 5 THEN 'П' END")

# Последний расчёт каждого фрагмента ($1 — фрагменты или NULL)
_LAST_CALC_CTE = """
    WITH calc AS (
        SELECT fileid, MAX(id) AS cid FROM calculation
         WHERE ($1::int[] IS NULL OR fileid = ANY($1::int[]))
         GROUP BY fileid
    )"""

UT_HEADERS = [
    "Код записи", "Состояние участка: подающего", "Состояние участка: обратного",
    "Начальный узел: код расчётной схемы", "Начальный узел: наименование", "Начальный узел: признак трубопровода",
    "Конечный узел: код расчётной схемы", "Конечный узел: наименование", "Конечный узел: признак трубопровода",
    "Тип трубы", "Количество труб", "Длина участка, м", "Внутр. диаметр, мм",
    "Эквивал. шероховатость, мм", "Сумма коэффициентов местных сопротивлений", "Доля местных потерь",
    "Код группы Kv: подающий", "Код группы Kv: обратный", "Гидравлич. сопротивление участка, м·ч²/т²",
    "Тип прокладки", "Толщина стенки, мм", "Коэффициент тепловых испытаний", "Код источника тепла",
    "Балансовая принадлежность",
]

UT_RESULT_HEADERS = [
    "Код записи", "Состояние участка",
    "Начальный узел: код расчётной схемы", "Начальный узел: наименование", "Начальный узел: признак трубопровода",
    "Конечный узел: код расчётной схемы", "Конечный узел: наименование", "Конечный узел: признак трубопровода",
    "Длина участка, м", "Внутр. диаметр, мм", "Скорость потока, м/с", "Время прохождения потока, мин",
    "Полное гидравлическое сопротивление, м·ч²/т²", "Расход воды, т/ч",
    "Потери напора: удельные, мм/м", "Потери напора: местные, м", "Потери напора: линейные, м",
    "Потери напора: общие, м", "Конечный узел: располагаемый напор, м", "Конечный узел: пьезометрический напор, м",
    "Конечный узел: геодезическая отметка, м", "Конечный узел: полный напор, м", "Код источника тепла",
    "Расчёт",
]
# Колонки ut_out в порядке листа «Гидравлика» G_UT (удельные, местные, линейные, общие)
UT_RESULT_COLUMNS = [
    UT.UT_LENGTH_M, UT.UT_DIAMETER_MM, UT.UT_VELOCITY_MS, UT.UT_TRAVEL_MIN, UT.UT_RESISTANCE,
    UT.UT_FLOW_TH, UT.UT_SPEC_LOSS_MM_M, UT.UT_LOSS_LOCAL_M, UT.UT_LOSS_LINEAR_M, UT.UT_LOSS_TOTAL_M,
    UT.UT_AVAIL_HEAD_END_M, UT.UT_PIEZO_HEAD_END_M, UT.UT_GROUND_END_M, UT.UT_FULL_HEAD_END_M,
]

_UT_ROWS_SQL = f"""
    SELECT lo.id,
           CASE WHEN hps.pipesectstateidflow = 1 THEN '' ELSE 'закр' END AS key_ut_p,
           CASE WHEN hps.pipesectstateidret = 1 THEN '' ELSE 'закр' END AS key_ut_o,
           ec1.name AS kod1, n1.externalnodename AS uzel1, {_SIGN1.format(e="lo.externalsignlineid")} AS pr1,
           ec2.name AS kod2, n2.externalnodename AS uzel2, {_SIGN2.format(e="lo.externalsignlineid")} AS pr2,
           s.name AS standard, hps.tubescount, hps.pipesectlength, hps.diameterinternal,
           hps.tuberoughness, hps.localressum, hps.locallosesshare,
           vcf.kodkv AS kodkvp, vcr.kodkv AS kodkvo, lo.hydrores,
           tt.name AS name_typ, hps.wallthickness, hps.heattestscoeff,
           hs.sourcename, org.name AS org_name
      FROM linesobj lo
      LEFT JOIN LATERAL (
          SELECT * FROM heatpipesections WHERE lineid = lo.id ORDER BY id LIMIT 1
      ) hps ON true
      LEFT JOIN nodes n1 ON n1.id = lo.nodeid1
      LEFT JOIN nodes n2 ON n2.id = lo.nodeid2
      LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
      LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
      LEFT JOIN standards s ON s.id = hps.standardid
      LEFT JOIN varcoefficients vcf ON vcf.id = hps.varcoeffidflow
      LEFT JOIN varcoefficients vcr ON vcr.id = hps.varcoeffidret
      LEFT JOIN tubingtypes tt ON tt.id = hps.tubingtypeid
      LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
      LEFT JOIN organizations org ON org.id = lo.organizationid
    {_PIPELINES_WHERE}
     ORDER BY lo.id
     LIMIT $2
"""

_UT_RESULTS_JOIN = """
      FROM ut_out u
      JOIN calc ON calc.cid = u.calculationid
      JOIN linesobj lo ON lo.id = u.lineid AND lo.fileid = calc.fileid"""

_UT_RESULTS_SQL = _LAST_CALC_CTE + f"""
    SELECT lo.id,
           CASE WHEN (u.externalsignlineid IN (1, 2, 4) AND hps.pipesectstateidflow = 2)
                  OR (u.externalsignlineid IN (1, 3, 5) AND hps.pipesectstateidret = 2)
                THEN 'закр' ELSE '' END AS sost,
           ec1.name AS kod1, n1.externalnodename AS uzel1, {_SIGN1.format(e="u.externalsignlineid")} AS pr1,
           ec2.name AS kod2, n2.externalnodename AS uzel2, {_SIGN2.format(e="u.externalsignlineid")} AS pr2,
           {", ".join(f"u.{c}" for c in UT_RESULT_COLUMNS)},
           hs.sourcename, u.calculationid
    {_UT_RESULTS_JOIN}
      LEFT JOIN LATERAL (
          SELECT pipesectstateidflow, pipesectstateidret FROM heatpipesections
           WHERE lineid = lo.id ORDER BY id LIMIT 1
      ) hps ON true
      LEFT JOIN nodes n1 ON n1.id = lo.nodeid1
      LEFT JOIN nodes n2 ON n2.id = lo.nodeid2
      LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
      LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
      LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
    {_PIPELINES_WHERE}
     ORDER BY lo.id, u.externalsignlineid
     LIMIT $2
"""


def _values(rows) -> List[List[Any]]:
    return [list(r.values()) for r in rows]


async def _result_sheet(conn, scope: ReportScope, title: str, headers: List[str],
                        count_sql: str, rows_sql: str) -> Tuple[str, SheetData]:
    total = int(await conn.fetchval(count_sql, scope.fragment_ids) or 0)
    rows = await conn.fetch(rows_sql, scope.fragment_ids, scope.limit) if total else []
    return title, SheetData(headers, _values(rows), total)


def _result_notes(data: SheetData) -> List[str]:
    notes = []
    for title, sheet in data.extra_sheets:
        if not sheet.total:
            notes.append(f"Лист «{title}»: результатов расчёта нет (для фрагментов участков "
                         "расчёт не выполнен) — лист содержит только шапку.")
        elif sheet.total > len(sheet.rows):
            notes.append(f"Лист «{title}» неполный: выгружено {len(sheet.rows)} строк из {sheet.total}.")
    return notes


async def _rows_pipelines(conn, scope: ReportScope) -> SheetData:
    """G_UT: «Вх.Участки» (одна строка на участок) + «Гидравлика» (ut_out, подача/обратка)."""
    total = await conn.fetchval(f"SELECT count(*) FROM linesobj lo {_PIPELINES_WHERE}", scope.fragment_ids)
    rows = await conn.fetch(_UT_ROWS_SQL, scope.fragment_ids, scope.limit)
    data = SheetData(list(UT_HEADERS), _values(rows), int(total or 0))
    data.extra_sheets.append(await _result_sheet(
        conn, scope, "Гидравлика", list(UT_RESULT_HEADERS),
        _LAST_CALC_CTE + f"\n    SELECT count(*) {_UT_RESULTS_JOIN}\n    {_PIPELINES_WHERE}", _UT_RESULTS_SQL,
    ))
    data.notes.extend(_result_notes(data))
    return data


ZD_HEADERS = [
    "Код записи", "Состояние задвижки", "Место установки",
    "Узел присоединения: код расчётной схемы", "Узел присоединения: наименование",
    "Узел присоединения: признак трубопровода",
    "Узел на входе: код расчётной схемы", "Узел на входе: наименование", "Узел на входе: признак трубопровода",
    "Узел на выходе: код расчётной схемы", "Узел на выходе: наименование", "Узел на выходе: признак трубопровода",
    "Диаметр условный, мм", "Относительная протечка, % от Kv", "Частичное открытие, % от Kv",
    "Гидравлич. сопротивление, м·ч²/т²", "Тип задвижки", "Содержательное наименование задвижки",
    "Код источника тепла",
]

ZD_RESULT_HEADERS = [
    "Узел присоединения: код расчётной схемы", "Узел присоединения: наименование",
    "Узел присоединения: признак трубопровода", "Содержательное наименование узла",
    "Узел на входе: код расчётной схемы", "Узел на входе: наименование", "Узел на входе: признак трубопровода",
    "Узел на выходе: код расчётной схемы", "Узел на выходе: наименование", "Узел на выходе: признак трубопровода",
    "Содержательное наименование (номер) задвижки", "Место установки", "Состояние",
    "Степень открытия от Kv, %", "Расход через задвижку, т/ч", "Потеря напора на задвижке, м",
    "Полное гидравл. сопротивление, м·ч²/т²", "Конечный узел: располагаемый напор, м",
    "Конечный узел: пьезометрический напор, м", "Конечный узел: геодезическая отметка, м",
    "Конечный узел: полный напор, м", "Расчёт",
]

_ZD_WHERE = f"WHERE {LIVE_LINE_SQL} AND {LINE_IN_FRAGMENTS_SQL}"
_ZD_NODES_JOIN = """
      LEFT JOIN nodes n1 ON n1.id = lo.nodeid1
      LEFT JOIN nodes n2 ON n2.id = lo.nodeid2
      LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
      LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
      LEFT JOIN nodes ni ON ni.id = n1.internalnodeid
      LEFT JOIN externalcodes eci ON eci.id = ni.externalcodeid
      LEFT JOIN externalsigns esi ON esi.id = ni.externalsignid
      LEFT JOIN damperarmaturestates das ON das.id = d.damperarmaturestateid"""

_ZD_ROWS_SQL = f"""
    SELECT lo.id, das.name AS sost, d.dispatcherswitch AS name_zd,
           eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p,
           ec1.name AS kod1, n1.externalnodename AS uzel1, {_SIGN1.format(e="lo.externalsignlineid")} AS pr1,
           ec2.name AS kod2, n2.externalnodename AS uzel2, {_SIGN2.format(e="lo.externalsignlineid")} AS pr2,
           d.diametercondit, d.relatleakage, d.partdempopen, lo.hydrores,
           sd.name_zc AS standard_mark, d.name AS damper_name, hs.sourcename
      FROM dampers d
      JOIN linesobj lo ON lo.id = d.lineid
      {_ZD_NODES_JOIN}
      LEFT JOIN standarddampers sd ON sd.id = NULLIF(d.standarddamplink, 0)
      LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
    {_ZD_WHERE}
     ORDER BY lo.id, d.id
     LIMIT $2
"""

_ZD_RESULTS_JOIN = """
      FROM zd_out z
      JOIN calc ON calc.cid = z.calculationid
      JOIN linesobj lo ON lo.id = z.lineid AND lo.fileid = calc.fileid
      JOIN dampers d ON d.lineid = lo.id"""

_ZD_RESULTS_SQL = _LAST_CALC_CTE + f"""
    SELECT eci.name AS kod_p, ni.externalnodename AS uzel_p, esi.name AS pr_p, '' AS name_soder,
           ec1.name AS kod1, n1.externalnodename AS uzel1, {_SIGN1.format(e="z.externalsignlineid")} AS pr1,
           ec2.name AS kod2, n2.externalnodename AS uzel2, {_SIGN2.format(e="z.externalsignlineid")} AS pr2,
           z.a8 AS name_soder_zd, d.dispatcherswitch AS name_zd, das.name AS sost, d.partdempopen,
           z.a9, z.a10, z.a11, z.a12, z.a13, z.a14, z.a15, z.calculationid
    {_ZD_RESULTS_JOIN}
      {_ZD_NODES_JOIN}
    {_ZD_WHERE}
     ORDER BY lo.id, z.externalsignlineid
     LIMIT $2
"""


async def _rows_dampers(conn, scope: ReportScope) -> SheetData:
    """G_ZD: «Вх.Задвижки» (dampers) + «Все» (zd_out последнего расчёта)."""
    total = await conn.fetchval(
        f"SELECT count(*) FROM dampers d JOIN linesobj lo ON lo.id = d.lineid {_ZD_WHERE}", scope.fragment_ids
    )
    rows = await conn.fetch(_ZD_ROWS_SQL, scope.fragment_ids, scope.limit)
    data = SheetData(list(ZD_HEADERS), _values(rows), int(total or 0))
    data.extra_sheets.append(await _result_sheet(
        conn, scope, "Все", list(ZD_RESULT_HEADERS),
        _LAST_CALC_CTE + f"\n    SELECT count(*) {_ZD_RESULTS_JOIN}\n    {_ZD_WHERE}", _ZD_RESULTS_SQL,
    ))
    data.notes.extend(_result_notes(data))
    return data


async def _rows_armatures(conn, scope: ReportScope) -> SheetData:
    items, total = await _paged_items(get_network_armatures, conn, scope)
    headers = ["ID", "Участок", "Наименование", "Назначение", "Ø условный, мм",
               "Состояние", "Открытие, %", "Число оборотов", "Типоразмер"]
    return SheetData(headers, [
        [i.get("id"), i.get("line_id"), i.get("display_name"), i.get("purpose_name"),
         i.get("nominal_diameter"), i.get("state_name"), i.get("opening_percent"),
         i.get("turn_count"), i.get("standard_mark")]
        for i in items
    ], total)


async def _rows_bypasses(conn, scope: ReportScope) -> SheetData:
    items, total = await _paged_items(get_network_bypasses, conn, scope)
    headers = ["ID", "Участок", "Наименование", "Узел подключения", "Состояние",
               "Трубопровод", "Длина, м", "Ø внутр., мм", "Расход (задание)", "Напор (задание)"]
    return SheetData(headers, [
        [i.get("id"), i.get("line_id"), i.get("display_name"), i.get("connection_node_id"),
         i.get("state_name"), i.get("pipeline_sign_name"), i.get("length"),
         i.get("internal_diameter"), i.get("set_flow"), i.get("set_head")]
        for i in items
    ], total)


async def _rows_pumps(conn, scope: ReportScope) -> SheetData:
    items, total = await _paged_items(get_installed_pumps, conn, scope)
    headers = ["ID", "Участок", "Номер", "Насосная станция", "Модель", "Тип",
               "Кол-во агрегатов", "Тип привода", "Состояние", "Фрагмент"]
    return SheetData(headers, [
        [i.get("id"), i.get("line_id"), i.get("number"), i.get("station_name"),
         i.get("model_name"), i.get("model_type"), i.get("parallel_count"),
         i.get("drive_type_name"), i.get("state_name"), i.get("fragment_name")]
        for i in items
    ], total)


async def _rows_consumers(conn, scope: ReportScope) -> SheetData:
    items, total = await _paged_items(get_consumer_load_diagnostics, conn, scope)
    headers = ["Тип", "ID", "Узел", "Наименование", "Состояние", "Отопление, Гкал/ч",
               "Вентиляция, Гкал/ч", "ГВС, Гкал/ч", "Итого, Гкал/ч", "Фрагмент"]
    type_names = {"generalized": "Обобщённый", "real": "Реальный"}
    return SheetData(headers, [
        [type_names.get(i.get("consumer_type"), i.get("consumer_type")), i.get("id"),
         i.get("node_id"), i.get("name"), i.get("state_name"), i.get("heating_load"),
         i.get("ventilation_load"), i.get("hot_water_load"), i.get("total_load"),
         i.get("fragment_name")]
        for i in items
    ], total)


async def _rows_technical_conditions(conn, scope: ReportScope) -> SheetData:
    from database.technical_conditions import get_technical_conditions

    items, total = await _paged_items(get_technical_conditions, conn, scope, by_fragment=False)
    headers = [
        "ID",
        "Номер",
        "Дата",
        "Организация",
        "Объект",
        "Адрес",
        "Источник",
        "Район",
        "Состояние",
    ]
    return SheetData(headers, [
        [
            i.get("id"),
            i.get("number") or i.get("nomer_tu"),
            i.get("issue_date") or i.get("data_vydachi_tu"),
            i.get("organization") or i.get("organizatsiya"),
            i.get("object_name") or i.get("obekt"),
            i.get("address") or i.get("adres"),
            i.get("heat_source") or i.get("istochnik"),
            i.get("district") or i.get("rayon_ekspluatatsii"),
            i.get("state_name") or i.get("state"),
        ]
        for i in items
    ], total)


async def _rows_tu_balance(conn, scope: ReportScope) -> SheetData:
    from database.tu_balance import get_technical_condition_balance

    data = await get_technical_condition_balance(conn, year=scope.year)
    headers = [
        "Источник",
        "ТУ, шт",
        "Установленная мощность, Гкал/ч",
        "Отопление источника",
        "Вентиляция источника",
        "ГВС источника",
        "Располагаемая мощность, Гкал/ч",
        "Нормативные тепловые потери, Гкал/ч",
        "Отопление договорное",
        "Вентиляция договорная",
        "ГВС договорная",
        "Всего договорная, Гкал/ч",
        "Прирост отопления",
        "Прирост вентиляции",
        "Прирост ГВС",
        "Прирост всего, Гкал/ч",
        "Отопление подключенное",
        "Вентиляция подключенная",
        "ГВС подключенное",
        "Подключенная нагрузка всего, Гкал/ч",
        "Баланс по присоединённой нагрузке, Гкал/ч",
        "Баланс по присоединённой и перспективной, Гкал/ч",
    ]
    rows = [
        [
            i.get("heat_source"),
            i.get("tu_count"),
            i.get("installed_power"),
            i.get("source_heating"),
            i.get("source_ventilation"),
            i.get("source_gvs"),
            i.get("available_power"),
            i.get("normative_losses"),
            i.get("contract_heating"),
            i.get("contract_ventilation"),
            i.get("contract_gvs"),
            i.get("contract_total"),
            i.get("heating_increase"),
            i.get("ventilation_increase"),
            i.get("gvs_max_increase"),
            i.get("load_increase_total"),
            i.get("admitted_heating"),
            i.get("admitted_ventilation"),
            i.get("admitted_gvs_max"),
            i.get("admitted_total"),
            i.get("balance_connected"),
            i.get("balance_with_prospective"),
        ]
        for i in data.get("items", [])
    ]
    return SheetData(headers, rows, len(rows))


async def _rows_heat_loss_seasons(conn, scope: ReportScope) -> SheetData:
    from database.heat_losses import get_heat_loss_seasons

    items, total = await _paged_items(get_heat_loss_seasons, conn, scope, by_fragment=False)
    headers = [
        "ID",
        "Название",
        "Город",
        "Начало",
        "Конец",
        "t отопление",
        "t вентиляция",
        "Текущий",
        "Объём МС",
        "Объём РС",
    ]
    return SheetData(headers, [
        [
            i.get("id"),
            i.get("name"),
            i.get("city"),
            i.get("d1"),
            i.get("d2"),
            i.get("t_ot"),
            i.get("t_vent"),
            "да" if i.get("is_current") else "",
            i.get("volwaterhs"),
            i.get("volwatervs"),
        ]
        for i in items
    ], total)


async def _rows_heat_loss_sources(conn, scope: ReportScope) -> SheetData:
    from database.heat_losses import get_heat_loss_sources

    items, total = await _paged_items(get_heat_loss_sources, conn, scope, by_fragment=False)
    headers = [
        "ID",
        "Источник",
        "Фрагмент",
        "Готов к расчёту",
        "Параметры источника",
        "Месяцы",
        "Заполнение / обвязка",
    ]
    return SheetData(headers, [
        [
            i.get("id"),
            i.get("name"),
            i.get("fragment_name"),
            "да" if i.get("ready_to_calculate") else "нет",
            "да" if i.get("has_source_parameters") else "нет",
            "да" if i.get("has_month_parameters") else "нет",
            "да" if (i.get("has_filling_parameters") or i.get("has_harness")) else "нет",
        ]
        for i in items
    ], total)


EXCEL_SHEETS: Dict[str, tuple[str, Callable]] = {
    "ut": ("Участки теплопроводов", _rows_pipelines),
    "pipelines": ("Участки теплопроводов", _rows_pipelines),
    "zd": ("Задвижки", _rows_dampers),
    "valves": ("Задвижки", _rows_dampers),
    "armatures": ("Задвижки и арматура (реестр)", _rows_armatures),
    "bp": ("Байпасы", _rows_bypasses),
    "bypasses": ("Байпасы", _rows_bypasses),
    "ns": ("Насосные агрегаты", _rows_pumps),
    "pumps": ("Насосные агрегаты", _rows_pumps),
    "pt": ("Потребители", _rows_consumers),
    "consumers": ("Потребители", _rows_consumers),
    "tu": ("Технические условия", _rows_technical_conditions),
    "technical-conditions": ("Технические условия", _rows_technical_conditions),
    "tu-balance": ("Свод ТУ баланс", _rows_tu_balance),
    "tu_balance": ("Свод ТУ баланс", _rows_tu_balance),
    "heat-loss-seasons": ("Сезоны теплопотерь", _rows_heat_loss_seasons),
    "heat-loss-sources": ("Источники теплопотерь", _rows_heat_loss_sources),
}


def excel_report_types() -> List[Dict[str, str]]:
    """Уникальные ведомости для UI: код + название листа."""
    seen: Dict[str, str] = {}
    for code, (title, _) in EXCEL_SHEETS.items():
        seen.setdefault(title, code)
    return [{"code": code, "title": title} for title, code in seen.items()]


# Ведомости, где есть отбор по фрагменту (через участок или узел). ТУ, баланс ТУ и сезоны
# теплопотерь к фрагментам сети не привязаны — выгружаются целиком, с пометкой в «Примечании».
FRAGMENT_AWARE_LOADERS = {
    _rows_pipelines, _rows_dampers, _rows_armatures, _rows_bypasses, _rows_pumps, _rows_consumers,
}


def _report_notes(
    sheet_title: str, data: SheetData, scope: ReportScope, requested: Optional[List[int]]
) -> List[str]:
    notes: List[str] = []
    if requested:
        frags = ", ".join(str(f) for f in requested)
        if scope.fragment_ids:
            notes.append(f"Отбор по фрагментам: {frags}.")
        else:
            notes.append(
                f"Ведомость «{sheet_title}» не привязана к фрагментам сети: выгружены все записи "
                f"(выбранные фрагменты {frags} не применяются)."
            )
    if data.total > len(data.rows):
        if scope.fragment_ids:
            hint = "Сузьте выбор фрагментов."
        elif not requested:
            hint = "Выберите фрагмент на карте, чтобы выгрузить ведомость полностью."
        else:
            hint = ""
        notes.append(
            f"Ведомость неполная: выгружено {len(data.rows)} строк из {data.total} "
            f"(предел {scope.limit} строк). {hint}"
        )
    return notes


def _write_sheet(ws, headers: List[str], rows: List[List[Any]]) -> None:
    # Ширина колонок по содержимому первых строк + фиксация шапки и автофильтр
    for idx, header in enumerate(headers, start=1):
        width = min(len(str(header)), 40)
        for row in rows[:200]:
            value = row[idx - 1] if idx - 1 < len(row) else None
            if value is not None:
                width = max(width, min(len(str(value)), 60))
        ws.column_dimensions[get_column_letter(idx)].width = width + 3
    ws.freeze_panes = "A2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"

    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    header_cells = []
    for header in headers:
        cell = WriteOnlyCell(ws, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        header_cells.append(cell)
    ws.append(header_cells)
    for row in rows:
        ws.append(row)


def _render_workbook(sheet_title: str, data: SheetData, notes: List[str]) -> bytes:
    # write_only: ведомость всей сети (сотни тысяч строк) пишется потоком, без модели ячеек в памяти
    wb = openpyxl.Workbook(write_only=True)
    _write_sheet(wb.create_sheet(sheet_title[:31]), data.headers, data.rows)
    for title, extra in data.extra_sheets:
        _write_sheet(wb.create_sheet(title[:31]), extra.headers, extra.rows)

    if notes:
        note_ws = wb.create_sheet("Примечание")
        note_ws.column_dimensions["A"].width = 120
        for note in notes:
            note_ws.append([note])

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


async def build_excel_report(
    doc_type: str,
    *,
    year: Optional[int] = None,
    fragment_ids: Optional[List[int]] = None,
) -> ExcelReport:
    entry = EXCEL_SHEETS.get(doc_type.lower())
    if entry is None:
        raise ValueError(
            f"Неизвестный тип ведомости: {doc_type}. Доступны: {', '.join(sorted(EXCEL_SHEETS))}"
        )
    sheet_title, loader = entry
    frags = sorted({int(f) for f in fragment_ids}) if fragment_ids else None
    fragment_applied = bool(frags) and loader in FRAGMENT_AWARE_LOADERS
    scope = ReportScope(
        fragment_ids=frags if fragment_applied else None,
        limit=report_limit(frags if fragment_applied else None),
        year=year,
    )

    async with acquire_conn() as conn:
        data = await loader(conn, scope)

    notes = _report_notes(sheet_title, data, scope, frags) + data.notes
    content = await asyncio.to_thread(_render_workbook, sheet_title, data, notes)
    return ExcelReport(
        content=content,
        rows=len(data.rows),
        total=max(data.total, len(data.rows)),
        fragment_ids=frags,
        fragment_filter_applied=fragment_applied,
        notes=notes,
    )


async def generate_excel_report(
    doc_type: str,
    *,
    year: Optional[int] = None,
    fragment_ids: Optional[List[int]] = None,
) -> bytes:
    """Совместимость: только байты xlsx (сведения о полноте — в build_excel_report)."""
    return (await build_excel_report(doc_type, year=year, fragment_ids=fragment_ids)).content
