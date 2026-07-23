# Р¤3.РљР°РЅР°Р»С‹

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def get_f3_q(mark_line, mark_pts):

    obj = '''

select 
id,
shape,
channelTypeID,
overlapTypesID,
shirina__mm__out,
vysota__mm__out,
diametr_truby__uslovnyy__mm,
constructionTypesID,
dlina__mm,
god_vvoda_v_ekspluatatsiyu,
0 as one,
0 as two,
0 as three,

primechanie

from kanal'''

    obj = '(' + obj + ')'

    cols = ['channelTypeID','overlapTypesID','shirina__mm__out','vysota__mm__out','diametr_truby__uslovnyy__mm',
    'constructionTypesID','dlina__mm','god_vvoda_v_ekspluatatsiyu',
    'one','two','three',
    'primechanie']

    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)

    q = sql.group_ps1(q, cols, set(cols))

    join_tabs = {}

    q = sql.ps_add(q, cols, join_tabs, node=False)


    return q

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

    q = get_f3_q(mark_line, mark_pts)

#    ws = wb.create_sheet(title="Ф3.Каналы")
    write_header(ws)
    excel.write_table(ws, conn, q, row0=5)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 3. Каналы', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Тип канала', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Тип перекрытия / Материал ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:F3', 'Размеры канала', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Диаметр трубы, условный, мм ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Конструкция канала', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Длина канала, м ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Год ввода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K4', 'Год последнего ремонта', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:L4', 'Элементы канала (замена при ремонте)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:M4', 'Длина участка ремонта, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N3:N4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E4', 'Ширина, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F4', 'Высота, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 
