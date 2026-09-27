"""Excel-отчёты десктопа (gid6 «Excel» → меню таблиц excel2/*.lst).

Десктоп (excel_cxema.cpp, CCxema::Excel2List) берёт .lst-файл: шаблон .xls и список
пар «SQL-файл, строка шапки, номер листа», подставляет $fileID$/$calculationID$ и
выводит результат запроса в лист шаблона начиная со строки под шапкой, колонка A.
Здесь то же: шаблоны переведены в .xlsx один к одному (report_templates/excel2),
SQL переписан на PostgreSQL (sql/reports, параметры $1 — фрагмент, $2 — расчёт).

Правила SQL-файлов:
- только параметры $1 (фрагмент) и $2 (расчёт); значения в текст запроса не вставляются;
- {{имя}} подставляет текст sql/reports/имя.sql (общие подзапросы, например _consumerview);
- колонки с именем на «_» служебные и в Excel не пишутся.
"""

from __future__ import annotations

import datetime as dt
import io
import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql" / "reports"
TEMPLATE_DIR = ROOT / "report_templates" / "excel2"

MAX_ROWS = 100_000
STATEMENT_TIMEOUT_MS = 60_000

_INCLUDE_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")
_PARAM_RE = re.compile(r"\$(\d+)")


@dataclass(frozen=True)
class Sheet:
    sql: str                      # имя файла в sql/reports без .sql
    sheet: int                    # номер листа шаблона, с 1
    header_row: int               # последняя строка шапки (строка номеров колонок); данные — ниже
    title: str                    # название листа (как в шаблоне)
    dop: tuple[tuple[str, str], ...] = ()   # DOP-ячейки .lst: (адрес, $out_rezhim|$out_date|$out_time|$TnZ)


@dataclass(frozen=True)
class Report:
    id: str
    title: str
    group: str
    template: Optional[str]       # имя .xlsx в report_templates/excel2; None — шапка из headers
    sheets: tuple[Sheet, ...]
    desktop: str                  # источник в gid6
    headers: tuple[str, ...] = ()  # только для отчётов без шаблона
    note: str = ""


GROUP_INPUT = "Исходные данные"
GROUP_RESULTS = "Результаты расчёта"
GROUP_SYSTEM = "Система теплоснабжения"

_DOP_PT = {
    4: (("G4", "$out_rezhim"), ("I4", "$out_date"), ("K4", "$out_time"), ("O4", "$TnZ")),
    5: (("I4", "$out_rezhim"), ("K4", "$out_date"), ("M4", "$out_time"), ("Q4", "$TnZ")),
    6: (("J4", "$out_rezhim"), ("L4", "$out_date"), ("O4", "$out_time"), ("R4", "$TnZ")),
    7: (("F4", "$out_rezhim"), ("H4", "$out_date"), ("J4", "$out_time"), ("L4", "$TnZ")),
}

REPORTS: tuple[Report, ...] = (
    # --- «OUT_*.lst»: вход + результаты расчёта в одной книге -----------------------------
    Report("out_ut", "Участки теплопроводов", GROUP_RESULTS, "G_UT", (
        Sheet("vh_uchastki", 1, 12, "Вх.Участки"),
        Sheet("out_uchastki", 2, 14, "Гидравлика"),
        Sheet("out_uchastki_teplogidravlika", 3, 14, "ТеплоГидравлика"),
        Sheet("out_uchastki_otklyuchennye", 4, 14, "Отключенные"),
    ), "excel2/OUT_Участки теплопроводов.lst"),
    Report("out_pt", "Потребители", GROUP_RESULTS, "G_PT", (
        Sheet("vh_potrebiteli_realnye", 1, 14, "Вх.Реальные"),
        Sheet("vh_potrebiteli_obobshennye", 2, 14, "Вх.Обобщенные"),
        Sheet("out_pt_raschetnye_nagruzki", 3, 13, "Расч.Нагрузки"),
        Sheet("out_potrebiteli_gidravlika", 4, 15, "Гидравлика", _DOP_PT[4]),
        Sheet("out_pt_teplo", 5, 15, "Тепло", _DOP_PT[5]),
        Sheet("out_pt_teplogidravlika", 6, 15, "ТеплоГидравл.", _DOP_PT[6]),
        Sheet("out_pt_otklyuchennye", 7, 14, "Отключенные", _DOP_PT[7]),
    ), "excel2/OUT_Потребители.lst"),
    Report("out_zd", "Задвижки", GROUP_RESULTS, "G_ZD", (
        Sheet("vh_zadvizhki", 1, 12, "Вх.Задвижки"),
        Sheet("out_zadvizhki", 2, 15, "Все"),
        Sheet("out_zadvizhki_upr", 3, 15, "Управляющие"),
        Sheet("out_zadvizhki_sekc", 4, 15, "Секционирующие"),
        Sheet("out_zadvizhki_ns", 5, 15, "Насосные станции"),
        Sheet("out_zadvizhki_tp", 6, 15, "Тепловые пункты"),
    ), "excel2/OUT_Задвижки.lst"),
    Report("out_dr", "Дроссельные органы потребителей", GROUP_RESULTS, "G_DR", (
        Sheet("vh_drosseli", 1, 19, "Вх.Дроссели"),
        Sheet("out_drosselnye_organy", 2, 17, "Дроссели"),
        Sheet("out_pt_otklyuchennye_realnye", 3, 14, "Отключенные"),
    ), "excel2/OUT_Дроссельные органы потребителей.lst"),
    Report("out_nsa", "Насосные агрегаты", GROUP_RESULTS, "G_NSA", (
        Sheet("out_nasosnye_agregaty", 1, 15, "Насосы"),
    ), "excel2/OUT_Насосные агрегаты.lst"),
    Report("out_rs", "Сетевые регуляторы", GROUP_RESULTS, "G_RS", (
        Sheet("out_regulyatory", 1, 15, "Регуляторы"),
    ), "excel2/OUT_Сетевые регуляторы.lst"),
    Report("out_bp", "Байпасы", GROUP_RESULTS, "G_BP", (
        Sheet("vh_baipasy", 1, 12, "Вх.Байпасы"),
        Sheet("out_baipasy", 2, 14, "Вых.Байпасы"),
    ), "excel2/OUT_Байпасы.lst"),
    Report("out_ra", "Регулирующая арматура", GROUP_RESULTS, "G_ZD", (
        Sheet("vh_reguliruyushaya_armatura", 1, 12, "Вх.Задвижки"),
    ), "excel2/OUT_Регулирующая арматура.lst"),
    # --- Система теплоснабжения (HS_*.lst) ---------------------------------------------------
    Report("hs", "Система теплоснабжения", GROUP_SYSTEM, "gst", (
        Sheet("vh_teplosnabzhayushaya_sistema", 1, 10, "Вх.СистемаТеплоснабжения"),
        Sheet("vh_raschetnye_shemy", 3, 8, "Вх.РасчетныеСхемы"),
        Sheet("vh_organizacii", 4, 7, "Вх.Организации_владельцы"),
    ), "excel2/HS_Система теплоснабжения.lst",
        note="Лист «Районы эксплуатации» в десктопе отключён (строка .lst закомментирована)."),
    # --- Одиночные входные таблицы (*.lst без OUT_) ------------------------------------------
    Report("gut", "Участки", GROUP_INPUT, "gut", (Sheet("vh_uchastki", 1, 12, "Вх.Участки"),),
           "excel2/Участки.lst"),
    Report("gzd", "Задвижки (вход)", GROUP_INPUT, "gzd", (Sheet("vh_zadvizhki", 1, 12, "Вх.Задвижки"),),
           "excel2/Задвижки.lst"),
    Report("gra", "Регулирующая арматура (вход)", GROUP_INPUT, "gzd",
           (Sheet("vh_reguliruyushaya_armatura", 1, 12, "Вх.Задвижки"),), "excel2/Регулирующая арматура.lst"),
    Report("gbp", "Байпасы наружных теплопроводов", GROUP_INPUT, "gbp", (Sheet("vh_baipasy", 1, 12, "Вх.Байпасы"),),
           "excel2/Байпасы наружных теплопроводов.lst"),
    Report("gkv", "Коэффициенты вариации", GROUP_INPUT, "gkv",
           (Sheet("vh_koef_variacii", 1, 13, "Вх.Коэфф.вариации"),), "excel2/Коэффициенты вариации.lst"),
    Report("gnc", "Насосная станция", GROUP_INPUT, "gnc",
           (Sheet("vh_nasosnaya_stanciya", 1, 12, "Вх.Насосная станция"),), "excel2/Насосная станция.lst"),
    Report("gns", "Насосный агрегат", GROUP_INPUT, "gns", (Sheet("vh_nasosny_agregat", 1, 12, "Вх.Насосы"),),
           "excel2/Насосный агрегат.lst",
           note="Десктопный запрос брал NS_OUT и не совпадал с шапкой; здесь — исходная таблица pumps."),
    Report("gpo", "Потребители обобщенные", GROUP_INPUT, "gpo",
           (Sheet("vh_potrebiteli_obobshennye", 1, 14, "Вх.Обобщенные"),), "excel2/Потребители обобщенные.lst"),
    Report("gpt", "Потребители реальные", GROUP_INPUT, "gpt", (
        Sheet("vh_potrebiteli_realnye", 1, 13, "Вх.Реальные"),
        Sheet("vh_drosseli", 2, 19, "Вх.Дроссели"),
    ), "excel2/Потребители реальные.lst"),
    Report("grd", "Регулятор давления", GROUP_INPUT, "grd",
           (Sheet("vh_regulyator_davleniya", 1, 12, "Вх.РегуляторыДавления"),), "excel2/Регулятор давления.lst"),
    Report("gre", "Регулятор перепада", GROUP_INPUT, "gre",
           (Sheet("vh_regulyator_perepada", 1, 12, "Вх.РегуляторыПерепадаДавления"),), "excel2/Регулятор перепада.lst"),
    Report("grr", "Регуляторы расхода", GROUP_INPUT, "grr",
           (Sheet("vh_regulyatory_rashoda", 1, 12, "Вх.РегуляторыРасхода"),), "excel2/Регуляторы расхода.lst"),
    Report("gur", "Удельные расходы", GROUP_INPUT, "gur",
           (Sheet("vh_udelnye_rashody", 1, 9, "Вх.УдельныеРасходы"),), "excel2/Удельные расходы.lst"),
    Report("gup", "Узел подпитки", GROUP_INPUT, "gup",
           (Sheet("vh_uzel_podpitki", 1, 12, "Вх.УзлыПодпитки_Утечки"),), "excel2/Узел подпитки.lst"),
    Report("gzn", "Узлы с заданным напором", GROUP_INPUT, "gzn",
           (Sheet("vh_uzly_zadannyi_napor", 1, 9, "Вх.УзлыЗаданнымНапором"),), "excel2/Узлы с заданным напором.lst"),
    Report("gus", "Узлы", GROUP_INPUT, "gus", (Sheet("vh_uzly", 1, 9, "Вх.НенагруженныеУзлы"),),
           "excel2/Узлы.lst"),
    Report("mat_char", "Материальная характеристика", GROUP_INPUT, None,
           (Sheet("materialnaya_harakteristika", 1, 2, "Материальная характеристика"),),
           "excel2/sql2/Материальная характеристика.sql (без шаблона и пункта меню)",
           headers=(
               "Состояние участка", "Код нач. узла", "Начальный узел", "Признак", "Код кон. узла",
               "Конечный узел", "Признак", "Тип прокладки", "Год ввода", "Дата кап. ремонта",
               "Dнар, мм", "Длина, м", "Мат. хар. подающего (канал), м²", "Мат. хар. обратного (канал), м²",
               "Мат. хар. подземная/надземная, м²", "Ёмкость, м³", "Балансовая принадлежность",
           )),
)

REPORTS_BY_ID = {r.id: r for r in REPORTS}

# 44 SQL десктопа (excel2/sql2), которые сознательно не перенесены, и почему
NOT_PORTED = {
    "IT_Основные характеристики системы.sql": "в .!lst (отключён в десктопе), таблицы старой dBase-схемы ([Расчетная схема], US_OUT.kod)",
    "OUT_Шайбы.sql": "не в меню; DR_OUT.kod/uzel и PT_OUT.kod в PostgreSQL нет",
    "Район эксплуатации.sql": "строка закомментирована в HS_Система теплоснабжения.lst; таблицы exploitReg нет",
    "OUT_PT_Отключенные2.sql": "не в меню; дубль OUT_PT_Отключенные без обобщённых потребителей",
    "OUT_Насосные_станции.sql": "не в меню (.lst нет); NST_OUT пустая",
}


def _read(name: str) -> str:
    path = SQL_DIR / f"{name}.sql"
    if not path.is_file() or path.parent != SQL_DIR:
        raise ValueError(f"Нет SQL отчёта: {name}")
    return path.read_text(encoding="utf-8")


def _strip_comments(sql: str) -> str:
    return "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--"))


@lru_cache(maxsize=None)
def load_sql(name: str) -> str:
    """Текст запроса с подставленными {{включениями}} (без строк-комментариев)."""
    def expand(text: str, depth: int) -> str:
        if depth > 3:
            raise ValueError("Слишком глубокая вложенность {{...}}")
        return _INCLUDE_RE.sub(lambda m: expand(_strip_comments(_read(m.group(1))), depth + 1), text)

    return expand(_strip_comments(_read(name)), 0).strip()


def sql_params(sql: str) -> int:
    """Число позиционных параметров ($1..$n) в запросе."""
    nums = [int(n) for n in _PARAM_RE.findall(sql)]
    return max(nums) if nums else 0


def report_uses_calculation(report: Report) -> bool:
    return any(sql_params(load_sql(s.sql)) >= 2 for s in report.sheets)


def catalog() -> list[dict[str, Any]]:
    """Каталог для UI: группа, название, параметры, листы, источник в десктопе."""
    out = []
    for r in REPORTS:
        uses_calc = report_uses_calculation(r)
        out.append({
            "id": r.id,
            "title": r.title,
            "group": r.group,
            "desktop": r.desktop,
            "note": r.note or None,
            "params": {
                "fragment_id": "required",
                "calculation_id": "optional" if uses_calc else None,
            },
            "uses_calculation": uses_calc,
            "sheets": [{"title": s.title, "sql": s.sql} for s in r.sheets],
        })
    return out


# --- формирование книги ----------------------------------------------------------------------

_THIN = Side(style="thin", color="808080")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _number_format(value: Any) -> Optional[str]:
    # как CExcel::set_typ2: даты — ДД.ММ.ГГГГ, числа — General; строки и так текст
    if isinstance(value, dt.datetime):
        return "DD.MM.YYYY HH:MM" if (value.hour or value.minute) else "DD.MM.YYYY"
    if isinstance(value, dt.date):
        return "DD.MM.YYYY"
    return None


def dop_value(key: str, calc: Optional[dict[str, Any]]) -> str:
    """Подстановки DOP из .lst (excel_cxema.cpp): режим, дата и время расчёта, Tнаруж."""
    if not calc:
        return ""
    date1 = calc.get("date1")
    tn = calc.get("tn")
    if key == "$out_rezhim":
        return "Фактический" if "фактического" in (calc.get("name") or "") else "Плановый"
    if key == "$out_date":
        return date1.strftime("%d.%m.%Y") if date1 else ""
    if key == "$out_time":
        return date1.strftime("%H:%M") if date1 else ""
    if key == "$TnZ":
        return f"Tнаруж {tn:g}°С" if tn is not None else ""
    if key == "$Tn":
        return f"{tn:g}" if tn is not None else ""
    if key == "$out_name":
        return calc.get("name") or ""
    return ""


def labeled_columns(ws, header_row: int) -> int:
    """Число колонок шапки шаблона: последняя колонка с текстом в строках 1..header_row."""
    last = 0
    for row in ws.iter_rows(min_row=1, max_row=header_row):
        for cell in row:
            if cell.value is not None and str(cell.value).strip():
                last = max(last, cell.column)
    return last


def write_rows(ws, header_row: int, columns: list[str], rows: list[tuple]) -> None:
    """Строки запроса под шапкой шаблона с колонки A; служебные «_»-колонки пропускаются."""
    keep = [i for i, c in enumerate(columns) if not c.startswith("_")]
    template_cols = labeled_columns(ws, header_row)
    for out_col, src_idx in enumerate(keep, start=1):
        if out_col > template_cols:
            # колонок запроса больше, чем в шапке шаблона: подписываем именем поля
            cell = ws.cell(header_row, out_col, columns[src_idx])
            cell.font = Font(bold=True, size=9)
            cell.border = _BORDER
    # Как десктоп (ExcelQ2): только значения и формат колонки, без рамок — так быстрее
    # на десятках тысяч строк; стиль ячейки ставится лишь для строк и дат.
    for r_idx, row in enumerate(rows, start=header_row + 1):
        for out_col, src_idx in enumerate(keep, start=1):
            value = row[src_idx]
            if value is None:
                continue
            if isinstance(value, Decimal):
                value = float(value)
            elif isinstance(value, str):
                # управляющие символы в именах узлов (встречаются в данных) Excel не принимает
                value = ILLEGAL_CHARACTERS_RE.sub("", value)
            cell = ws.cell(r_idx, out_col, value)
            fmt = _number_format(value)
            if fmt:
                cell.number_format = fmt
    ws.freeze_panes = ws.cell(header_row + 1, 1)


def _headers_sheet(ws, title: str, headers: tuple[str, ...], columns: list[str]) -> int:
    ws.cell(1, 1, title).font = Font(bold=True, size=12)
    names = list(headers) + [c for c in columns[len(headers):] if not c.startswith("_")]
    fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    for i, name in enumerate(names, start=1):
        cell = ws.cell(2, i, name)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(i)].width = max(12, min(len(name) + 2, 40))
    return 2


async def resolve_calculation(conn, fragment_id: int, calculation_id: Optional[int]) -> Optional[dict[str, Any]]:
    """Расчёт фрагмента: заданный или последний (десктоп getOutID — последний по фрагменту)."""
    if calculation_id:
        row = await conn.fetchrow(
            "SELECT id, fileid, name, date1, tn::float AS tn FROM calculation WHERE id = $1 AND fileid = $2",
            calculation_id, fragment_id,
        )
        if row is None:
            raise LookupError(f"Расчёт {calculation_id} не относится к фрагменту {fragment_id}")
        return dict(row)
    row = await conn.fetchrow(
        "SELECT id, fileid, name, date1, tn::float AS tn FROM calculation WHERE fileid = $1 ORDER BY id DESC LIMIT 1",
        fragment_id,
    )
    return dict(row) if row else None


async def fetch_sheet(conn, sheet: Sheet, fragment_id: int, calculation_id: Optional[int]) -> tuple[list[str], list[tuple]]:
    sql = load_sql(sheet.sql)
    n = sql_params(sql)
    stmt = await conn.prepare(sql)
    columns = [a.name for a in stmt.get_attributes()]
    if n >= 2 and calculation_id is None:
        return columns, []  # у фрагмента нет расчёта: лист результатов остаётся с одной шапкой
    records = await stmt.fetch(*[fragment_id, calculation_id][:n])
    return columns, [tuple(r.values()) for r in records[:MAX_ROWS]]


async def fetch_report(conn, report: Report, fragment_id: int, calculation_id: Optional[int] = None
                       ) -> tuple[Optional[dict[str, Any]], list[tuple[Sheet, list[str], list[tuple]]]]:
    """Данные всех листов отчёта: одна read-only транзакция с таймаутом запроса."""
    calc = None
    if report_uses_calculation(report):
        calc = await resolve_calculation(conn, fragment_id, calculation_id)
    results: list[tuple[Sheet, list[str], list[tuple]]] = []
    async with conn.transaction(readonly=True):
        await conn.execute(f"SET LOCAL statement_timeout = {int(STATEMENT_TIMEOUT_MS)}")
        for sheet in report.sheets:
            columns, rows = await fetch_sheet(conn, sheet, fragment_id, calc["id"] if calc else None)
            results.append((sheet, columns, rows))
    return calc, results


def render_report(report: Report, calc: Optional[dict[str, Any]],
                  results: list[tuple[Sheet, list[str], list[tuple]]]) -> bytes:
    """Книга Excel (синхронно, для run_in_threadpool): шаблон десктопа + строки запросов."""
    if report.template:
        wb = openpyxl.load_workbook(TEMPLATE_DIR / f"{report.template}.xlsx")
        used = {s.sheet for s in report.sheets}
        targets = {s.sheet: wb.worksheets[s.sheet - 1] for s in report.sheets}
        for idx in sorted(range(1, len(wb.worksheets) + 1), reverse=True):
            if idx not in used:
                wb.remove(wb.worksheets[idx - 1])
        for sheet, columns, rows in results:
            ws = targets[sheet.sheet]
            for addr, key in sheet.dop:
                ws[addr] = dop_value(key, calc)
            write_rows(ws, sheet.header_row, columns, rows)
        wb.active = 0
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        sheet, columns, rows = results[0]
        ws.title = sheet.title[:31]
        header_row = _headers_sheet(ws, report.title, report.headers, columns)
        write_rows(ws, header_row, columns, rows)
        if rows:
            ws.auto_filter.ref = f"A{header_row}:{get_column_letter(len(report.headers))}{header_row + len(rows)}"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def report_summary(report: Report, fragment_id: int, calc: Optional[dict[str, Any]],
                   results: list[tuple[Sheet, list[str], list[tuple]]]) -> dict[str, Any]:
    return {
        "report": report.id,
        "fragment_id": fragment_id,
        "calculation_id": calc["id"] if calc else None,
        "sheets": [{"title": s.title, "rows": len(rows)} for s, _, rows in results],
    }


def get_report(report_id: str) -> Report:
    report = REPORTS_BY_ID.get(report_id)
    if report is None:
        raise KeyError(report_id)
    return report


async def build_report(conn, report_id: str, fragment_id: int,
                       calculation_id: Optional[int] = None) -> tuple[bytes, dict[str, Any]]:
    """Книга Excel отчёта и сводка (число строк по листам, расчёт). Для скриптов."""
    report = get_report(report_id)
    calc, results = await fetch_report(conn, report, fragment_id, calculation_id)
    return render_report(report, calc, results), report_summary(report, fragment_id, calc, results)
