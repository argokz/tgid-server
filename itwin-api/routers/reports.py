"""Отчёты и экспорт: Excel-паспорт, Word-карта нарушения, иерархия паспортов, SHP, формы."""

import io
import os

from urllib.parse import quote

import asyncpg
from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from typing import Optional

from app_logging import get_logger
from database import excel_reports
from database.connect import acquire_conn
from database.export_shp import export_network_to_shp
from database.passport_diagnostics import get_passport_site_diagnostics
from database.passport_excel import XLSX_MEDIA_TYPE, PassportError, build_passport_xlsx
from database.word_db import get_defect_info
from database.fragment_filter import parse_fragment_ids
from reports_generator import build_excel_report, excel_report_types, generate_form_html, report_filename
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
    Паспорт строится 10–15 с; фоновый вариант — POST /api/v1/file-jobs (kind=passport).
    """
    try:
        content, filename = build_passport_xlsx(table, obj_id)
    except PassportError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        logger.error(f"Passport generation failed for {table}/{obj_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать паспорт: {e}")
    return StreamingResponse(
        io.BytesIO(content),
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


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


@router.get("/api/passports/diagnostics")
async def passport_site_diagnostics():
    """Почему Excel-паспорт может вернуть 404 «нет трубопроводов»."""
    try:
        async with acquire_conn() as conn:
            return await get_passport_site_diagnostics(conn)
    except Exception as e:
        logger.exception("passport diagnostics failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
async def export_shp_endpoint(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
    limit: int = Query(50000, ge=1, le=200000),
):
    frags = parse_fragment_ids(fragment_id, fragments)
    zip_data = await export_network_to_shp(frags, limit=limit)
    suffix = f"_f{frags[0]}" if frags and len(frags) == 1 else ("_frag" if frags else "")
    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=network_export{suffix}.zip"},
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
async def get_report_excel_endpoint(
    doc_type: str,
    year: Optional[int] = Query(None, ge=1990, le=2200),
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Фрагменты через запятую (fileid); пусто — вся сеть"),
):
    frags = parse_fragment_ids(fragment_id, fragments)
    try:
        report = await build_excel_report(doc_type, year=year, fragment_ids=frags)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Excel report {doc_type} failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Не удалось сформировать ведомость: {e}")
    filename = report_filename(doc_type, year=year, fragment_ids=frags)
    headers = {"Content-Disposition": f"attachment; filename={filename}", **report.headers()}
    headers["Access-Control-Expose-Headers"] = ", ".join(["Content-Disposition", *report.headers()])
    return StreamingResponse(
        io.BytesIO(report.content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/api/reports/catalog")
async def get_reports_catalog():
    """Каталог Excel-отчётов: отчёты десктопа gid6 (excel2/*.lst, шаблоны и SQL) и сводные
    ведомости веба (/api/reports/excel/{doc_type}). Источник списка для диалога «Отчёты»."""
    desktop = [{**item, "kind": "desktop"} for item in excel_reports.catalog()]
    summary = [
        {
            "id": t["code"], "title": t["title"], "group": "Сводные ведомости", "kind": "summary",
            "desktop": None, "note": None, "uses_calculation": False,
            "params": {"fragment_id": None, "calculation_id": None,
                       "year": "optional" if t["code"] in ("tu-balance", "tu_balance") else None},
            "sheets": [{"title": t["title"], "sql": None}],
        }
        for t in excel_report_types()
    ]
    return {
        "items": desktop + summary,
        "not_ported": [{"sql": k, "reason": v} for k, v in excel_reports.NOT_PORTED.items()],
    }


@router.get("/api/reports/catalog/{report_id}/excel")
async def get_catalog_report_excel(
    report_id: str,
    fragment_id: int = Query(..., ge=1, description="Фрагмент (nodes.fileid)"),
    calculation_id: Optional[int] = Query(None, ge=1, description="Расчёт; по умолчанию последний расчёт фрагмента"),
):
    """Excel-отчёт десктопа: шаблон excel2 + строки SQL под шапкой (gid6 CCxema::Excel2List)."""
    try:
        report = excel_reports.get_report(report_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Нет отчёта {report_id}")
    try:
        async with acquire_conn() as conn:
            calc, results = await excel_reports.fetch_report(conn, report, fragment_id, calculation_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except asyncpg.QueryCanceledError:
        raise HTTPException(status_code=504, detail="Отчёт не уложился в таймаут запроса")
    data = await run_in_threadpool(excel_reports.render_report, report, calc, results)
    summary = excel_reports.report_summary(report, fragment_id, calc, results)
    filename = f"{report.title} ф{fragment_id}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f"attachment; filename=report_{report.id}_f{fragment_id}.xlsx; "
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "X-Report-Rows": ",".join(str(s["rows"]) for s in summary["sheets"]),
            "X-Report-Calculation": str(summary["calculation_id"] or ""),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Report-Rows, X-Report-Calculation",
        },
    )
