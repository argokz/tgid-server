"""Excel-паспорт участка (перенос gid8 passport_module/p.py::passport) — общий код для синхронного
эндпоинта POST /api/db/object/{table}/{obj_id} и фоновой задачи Celery (file_jobs, kind=passport).

Синхронный код (psycopg2 + openpyxl + ThreadPoolExecutor форм f1…f15): из async-кода вызывать
через поток (run_in_threadpool / asyncio.to_thread).
"""

from __future__ import annotations

import io
import os
import sys

import psycopg2

PASSPORT_TABLES = ("linesobj", "nodes", "uchastok_ms", "uchastok_rs")
XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class PassportError(Exception):
    """Ошибка входных данных паспорта с HTTP-кодом для эндпоинта / сообщением для задачи."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _passport_modules():
    # passport_module — перенесённый из gid8 код с плоскими импортами
    # (import config, import connect …). Чтобы они разрешались, каталог
    # модуля должен быть на sys.path.
    module_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "passport_module")
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    from passport_module.p import async_do_passport, read_ms_rs
    import connect as passport_connect
    import db2 as passport_db2
    import ms1 as passport_ms1
    import rs1 as passport_rs1
    import sort_graph as passport_sort_graph
    import sql_pass as passport_sql_pass

    return (async_do_passport, read_ms_rs, passport_connect, passport_db2, passport_ms1, passport_rs1,
            passport_sort_graph, passport_sql_pass)


def resolve_passport_site(cur, table: str, obj_id: int) -> tuple[str, int]:
    """Участок (ms/rs, id) объекта: труба → узел 1, узел → belong*site или heatpipesections."""
    line_id = None
    if table == "linesobj":
        cur.execute("SELECT nodeid1 FROM linesobj WHERE id = %s", (obj_id,))
        res = cur.fetchone()
        if not res:
            raise PassportError(404, "Труба не найдена")
        node_id = res[0]
        line_id = obj_id
    elif table == "nodes":
        node_id = obj_id
    elif table == "uchastok_ms":
        return "ms", obj_id
    elif table == "uchastok_rs":
        return "rs", obj_id
    else:
        raise PassportError(400, "Неизвестная таблица")

    from database.passport_site import resolve_site_from_node_row, resolve_site_via_heatpipesections

    cur.execute("SELECT belongmagistralsite, belongdistsite FROM nodes WHERE id = %s", (node_id,))
    res = cur.fetchone()
    if not res:
        raise PassportError(404, "Узел не найден")
    resolved = resolve_site_from_node_row(res[0], res[1])
    if resolved is None:
        resolved = resolve_site_via_heatpipesections(cur, node_id, line_id=line_id)
    if resolved is None:
        raise PassportError(
            404,
            f"Узел {node_id} не привязан ни к магистральному, ни к распределительному "
            "участку — паспорт формируется только по участку. "
            "Запустите scripts/sql/backfill_belong_site.sql на копии БД "
            "или откройте паспорт по uchastok_ms / uchastok_rs.",
        )
    return resolved


def build_passport_xlsx(table: str, obj_id: int) -> tuple[bytes, str]:
    """Полный паспорт участка объекта: (содержимое .xlsx, имя файла). PassportError — ошибки данных."""
    import openpyxl

    (async_do_passport, read_ms_rs, passport_connect, passport_db2, passport_ms1, passport_rs1,
     passport_sort_graph, passport_sql_pass) = _passport_modules()

    # Формы паспорта (f1…f15) сами открывают соединение через
    # connect.connect(**c), поэтому им передаются ПАРАМЕТРЫ подключения,
    # а не готовый объект соединения (иначе TypeError на **c).
    passport_conn_params = {
        "rdbms": "postgreSQL",
        "server": os.getenv("DB_HOST"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "db": os.getenv("DB_NAME"),
        "port": os.getenv("DB_PORT"),
    }

    # Отдельное соединение для определения участка объекта
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
    )
    try:
        ms_rs, site_id = resolve_passport_site(conn.cursor(), table, obj_id)
    finally:
        conn.close()

    # Полный сценарий desktop-паспорта (passport_module/p.py::passport):
    # титульный лист участка → состав участка → граф участка (marked lines) →
    # 15 форм. Без make_graph формам приходил mark_line=0 и SQL падал.
    fragments = ""
    passport_conn = passport_connect.connect(**passport_conn_params)
    try:
        wb = openpyxl.Workbook()
        title_sheet = wb.active
        title_sheet.title = "Паспорт"

        head_rows = passport_db2.read_q(passport_conn, passport_sql_pass.passport(ms_rs, site_id))
        if ms_rs == "ms":
            passport_ms1.write_ms(title_sheet, head_rows)
        else:
            passport_rs1.write_rs(title_sheet, head_rows)

        site_rows = read_ms_rs(passport_conn, ms_rs, site_id)
        graph = passport_sort_graph.make_graph(passport_conn, fragments, ms_rs, site_id)
    finally:
        passport_conn.close()

    if not graph or not graph[0]:
        raise PassportError(
            404,
            f"Для участка {ms_rs}/{site_id} нет ни одного трубопровода. "
            "Привяжите трубы к участку (инструмент «Участки ПТС», "
            "heatpipesections.magistralSite / distSite) — без неё паспорт сформировать нельзя.",
        )

    mark_line, mark_node, mark_pts = graph

    # Формы f1…f15 открывают собственные соединения из параметров (ThreadPoolExecutor)
    async_do_passport(
        c=passport_conn_params,
        wb=wb,
        ms_rs=ms_rs,
        id=site_id,
        fragments=fragments,
        mark_line=mark_line,
        mark_pts=mark_pts,
        mark_node=mark_node,
        vals=site_rows,
    )

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue(), f"Passport_{ms_rs}_{site_id}.xlsx"
