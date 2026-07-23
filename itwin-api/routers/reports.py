"""Отчёты и экспорт: Excel-паспорт, Word-карта нарушения, иерархия паспортов, SHP, формы."""

import io
import os
import sys

import openpyxl
import psycopg2
from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from typing import Optional

from app_logging import get_logger
from database.connect import acquire_conn
from database.export_shp import export_network_to_shp
from database.word_db import get_defect_info
from reports_generator import excel_report_types, generate_excel_report, generate_form_html
from word_reports.word_generator import generate_defect_map_word

logger = get_logger(__name__)

router = APIRouter(tags=["reports"])


@router.post("/api/db/object/{table}/{obj_id}")
def generate_passport_excel_query(table: str, obj_id: int):
    """
    Эндпоинт для генерации полного Excel паспорта по клику на трубу (linesobj) или узел (nodes).
    Определяет принадлежность к магистральной или распределительной сети и генерирует паспорт участка.

    Обычная (sync) функция: FastAPI выполняет её в thread pool, поэтому
    синхронные psycopg2/OpenPyXL не блокируют event loop остальных запросов.
    """
    try:
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
            port=os.getenv("DB_PORT")
        )
        cur = conn.cursor()

        ms_rs = None
        site_id = None

        # Находим к какому участку относится объект
        if table == "linesobj":
            cur.execute("SELECT nodeid1 FROM linesobj WHERE id = %s", (obj_id,))
            res = cur.fetchone()
            if not res:
                raise Exception("Труба не найдена")
            node_id = res[0]
        elif table == "nodes":
            node_id = obj_id
        elif table == "uchastok_ms":
            ms_rs = "ms"
            site_id = obj_id
        elif table == "uchastok_rs":
            ms_rs = "rs"
            site_id = obj_id
        else:
            raise Exception("Неизвестная таблица")

        if ms_rs is None:
            cur.execute("SELECT belongmagistralsite, belongdistsite FROM nodes WHERE id = %s", (node_id,))
            res = cur.fetchone()
            if not res:
                raise Exception("Узел не найден")
            bms, bds = res
            if bms and int(bms) > 0:
                ms_rs = "ms"
                site_id = int(bms)
            elif bds and int(bds) > 0:
                ms_rs = "rs"
                site_id = int(bds)
            else:
                conn.close()
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Узел {node_id} не привязан ни к магистральному, ни к распределительному "
                        "участку — паспорт формируется только по участку."
                    ),
                )

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
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Для участка {ms_rs}/{site_id} нет ни одного трубопровода. "
                    "Проверьте привязку узлов к участку (nodes.belongMagistralSite / "
                    "belongDistSite) — без неё паспорт сформировать нельзя."
                ),
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

        # Сохраняем в память
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        filename = f"Passport_{ms_rs}_{site_id}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Passport generation failed for {table}/{obj_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать паспорт: {e}")


@router.get("/reports/word/defect/{defect_id}")
async def export_defect_word(defect_id: int):
    try:
        async with acquire_conn() as conn:
            defect_data = await get_defect_info(conn, defect_id)
        if not defect_data:
            raise HTTPException(status_code=404, detail="Defect not found")

        # python-docx работает синхронно — уводим генерацию в thread pool
        filepath = await run_in_threadpool(
            generate_defect_map_word, defect_id, defect_data, out_dir="files"
        )

        # Ensure the file exists
        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Generated file not found")

        filename = os.path.basename(filepath)

        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/passports/hierarchy")
async def get_passports_hierarchy():
    async with acquire_conn() as conn:
        try:
            ms_nach_query = """
            SELECT
                nach.id AS nach_id,
                nach.fio AS nach_name,
                ms.id AS ms_id,
                ms.opisanie_uchastka_ms AS ms_name
            FROM uchastok_ms ms
            LEFT JOIN uchastki_ekspluatatsii ue ON ue.id=ms.nomer_uchastka
            LEFT JOIN nachalniki_uchastkov nach ON nach.id=ue.nachalnik_uchastka
            LEFT JOIN rayon_ekspluatatsii re ON re.id=ue.rayon_ekspluatatsii
            WHERE ms.opisanie_uchastka_ms IS NOT NULL
            ORDER BY nach.fio, nach.id, re.naimenovanie_rayona_ekspluatatsii_istochnika_tepla, re.id, ms.opisanie_uchastka_ms, ms.id
            """
            ms_nach_rows = await conn.fetch(ms_nach_query)

            rs_nach_query = """
            SELECT
                nach.id AS nach_id,
                nach.fio AS nach_name,
                ms.id AS ms_id,
                ms.naimenovanie_uchastka_rs AS ms_name
            FROM uchastok_rs ms
            LEFT JOIN uchastki_ekspluatatsii ue ON ue.id=ms.nomer_uchastka
            LEFT JOIN nachalniki_uchastkov nach ON nach.id=ue.nachalnik_uchastka
            LEFT JOIN rayon_ekspluatatsii re ON re.id=ue.rayon_ekspluatatsii
            WHERE ms.naimenovanie_uchastka_rs IS NOT NULL
            ORDER BY nach.fio, nach.id, re.naimenovanie_rayona_ekspluatatsii_istochnika_tepla, re.id, ms.naimenovanie_uchastka_rs, ms.id
            """
            rs_nach_rows = await conn.fetch(rs_nach_query)

            def build_tree(rows, root_name, ms_rs_type):
                tree = []
                nach_map = {}
                for r in rows:
                    n_id = r['nach_id'] if r['nach_id'] else 0
                    n_name = r['nach_name'] if r['nach_name'] else "Неизвестный начальник"
                    if n_id not in nach_map:
                        nach_map[n_id] = {
                            "id": f"nach_{ms_rs_type}_{n_id}",
                            "name": n_name,
                            "children": []
                        }
                        tree.append(nach_map[n_id])

                    if r['ms_id']:
                        nach_map[n_id]["children"].append({
                            "id": f"{ms_rs_type}_{r['ms_id']}",
                            "name": r['ms_name'],
                            "ms_rs": ms_rs_type,
                            "site_id": r['ms_id'],
                            "is_leaf": True
                        })
                return {
                    "id": f"root_{ms_rs_type}",
                    "name": root_name,
                    "children": tree
                }

            return [
                build_tree(ms_nach_rows, "Магистральные сети (по начальникам)", "ms"),
                build_tree(rs_nach_rows, "Распределительные сети (по начальникам)", "rs")
            ]
        except Exception as e:
            logger.error(f"Error fetching hierarchy: {e}")
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/export/shp")
async def export_shp_endpoint():
    zip_data = await export_network_to_shp()
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=network_export.zip"}
    )


@router.get("/api/reports/html/{form_id}")
async def get_report_html_endpoint(form_id: str, search: Optional[str] = Query(None)):
    html_content = await generate_form_html(form_id, search=search)
    return HTMLResponse(content=html_content)


@router.get("/api/reports/excel-types")
async def list_report_excel_types():
    """Доступные ведомости Excel — источник списка для UI."""
    return {"items": excel_report_types()}


@router.get("/api/reports/excel/{doc_type}")
async def get_report_excel_endpoint(doc_type: str):
    try:
        excel_bytes = await generate_excel_report(doc_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Excel report {doc_type} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать ведомость: {e}")
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=report_{doc_type}.xlsx"}
    )
