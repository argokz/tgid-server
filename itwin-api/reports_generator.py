import os
import io
from typing import Optional, List, Dict, Any
from jinja2 import Template
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from database.connect import acquire_conn
from database.repairs import get_repairs
from database.defects import get_defects
from database.shurfs import get_shurfs
from database.inspections import get_inspections
from database.pressure_tests import get_pressure_tests

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "report_templates")

def get_template_content(filename: str) -> str:
    path = os.path.join(TEMPLATE_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="windows-1251", errors="ignore") as f:
            return f.read()
    return "<html><body><h3>Template not found</h3></body></html>"

async def generate_form_html(form_id: str, search: Optional[str] = None) -> str:
    async with acquire_conn() as conn:
        if form_id == "f10_remont":
            data = await get_repairs(conn, page=1, page_size=1000, search=search)
            items = data.get("items", [])
            headers = ["Участок/Узел", "Тип ремонта", "Состояние", "Категория", "Дата начала", "Дата окончания", "Ответственный"]
            rows_html = ""
            for item in items:
                line_name = item.get("start_node_name", "") + " - " + item.get("end_node_name", "") if item.get("start_node_name") else f"Участок #{item.get('line_id', '')}"
                rows_html += f"""<tr>
                    <td>{line_name}</td>
                    <td>{item.get('repair_type_name') or ''}</td>
                    <td>{item.get('state_name') or ''}</td>
                    <td>{item.get('category_name') or ''}</td>
                    <td>{item.get('date_from') or ''}</td>
                    <td>{item.get('date_to') or ''}</td>
                    <td>{item.get('responsible_person_name') or ''}</td>
                </tr>"""
        elif form_id == "f11_defect":
            data = await get_defects(conn, page=1, page_size=1000, search=search)
            items = data.get("items", [])
            rows_html = ""
            for item in items:
                obj_name = f"Участок #{item.get('line_id')}" if item.get('line_id') else f"Узел #{item.get('node_id')}"
                rows_html += f"""<tr>
                    <td>{obj_name}</td>
                    <td>{item.get('defect_type_name') or ''}</td>
                    <td>{item.get('severity_name') or ''}</td>
                    <td>{item.get('defect_date') or ''}</td>
                    <td>{item.get('description') or ''}</td>
                    <td>{item.get('status_name') or ''}</td>
                </tr>"""
        elif form_id == "f12_pits":
            data = await get_shurfs(conn, page=1, page_size=1000, search=search)
            items = data.get("items", [])
            rows_html = ""
            for item in items:
                rows_html += f"""<tr>
                    <td>Участок #{item.get('line_id', '')}</td>
                    <td>{item.get('shurf_number') or ''}</td>
                    <td>{item.get('inspection_date') or ''}</td>
                    <td>{item.get('condition_name') or ''}</td>
                    <td>{item.get('comments') or ''}</td>
                </tr>"""
        else:
            rows_html = "<tr><td colspan='10'>Данные отсутствуют или формируются</td></tr>"

    base_html = get_template_content(f"{form_id}.html")
    if "</table>" in base_html:
        parts = base_html.split("</table>")
        return parts[0] + rows_html + "</table>" + parts[1]
    
    return f"""
    <html>
    <head><meta charset="utf-8"><title>Отчет {form_id}</title>
    <style>table {{ border-collapse: collapse; width: 100%; }} th, td {{ border: 1px solid #ccc; padding: 6px; font-family: sans-serif; font-size: 13px; }}</style>
    </head>
    <body>
    <h2>Отчет по форме: {form_id}</h2>
    <table>{rows_html}</table>
    </body>
    </html>
    """

async def generate_excel_report(doc_type: str) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = doc_type.upper()

    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    async with acquire_conn() as conn:
        if doc_type in ["ut", "pipelines"]:
            ws.append(["ID", "Узел 1", "Узел 2", "Длина (м)", "Диаметр (мм)", "Год прокладки", "Назначение"])
            rows = await conn.fetch("""
                SELECT L.id, L.nodeid1, L.nodeid2, HPS.pipesectlength, HPS.diameter, HPS.yearpipe, HPS.pipetype
                FROM linesobj L
                LEFT JOIN heatpipesections HPS ON HPS.lineid = L.id
                WHERE L.removed = 0 LIMIT 2000
            """)
            for r in rows:
                ws.append([r['id'], r['nodeid1'], r['nodeid2'], r['pipesectlength'], r['diameter'], r['yearpipe'], r['pipetype']])
        elif doc_type in ["zd", "valves"]:
            ws.append(["ID", "Узел ID", "Имя", "Тип арматуры", "Состояние"])
            rows = await conn.fetch("SELECT id, nodeid, name, type, state FROM networkarmatures LIMIT 2000")
            for r in rows:
                ws.append([r['id'], r['nodeid'], r['name'], r['type'], r['state']])
        else:
            ws.append(["ID", "Наименование", "Тип", "Примечание"])
            rows = await conn.fetch("SELECT id, name, type, '' FROM nodes LIMIT 1000")
            for r in rows:
                ws.append([r['id'], r['name'], r['type'], ''])

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
