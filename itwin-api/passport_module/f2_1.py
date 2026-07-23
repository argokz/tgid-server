# Р¤2_1.РњРµС…Р°РЅРёС‡РµСЃРєРѕРµ РѕР±РѕСЂСѓРґРѕРІР°РЅРёРµ

import psycopg2 as pyodbc
from openpyxl import Workbook
import logging


import connect
import sql
import sql_obj
import excel

#-------------------------------------------------------------------------------------

def get_f2_1_q(mark_line, mark_pts):
    obj = '(' + sql_obj.mo1() + ')'

    cols = ['purposeTypesID_P','armatureTypesID_P','designTypesID_P','materialTypesID_P','constructionTypesID_P',
            'purposeTypesID_O','armatureTypesID_O','designTypesID_O','materialTypesID_O','constructionTypesID_O',
            'diam_reg_P','diam_reg_O','cnt_reg_P','cnt_reg_O',
            'diam_sec_P','diam_sec_O','cnt_sec_P','cnt_sec_O',
            'diam_v_P','diam_v_O','cnt_v_P','cnt_v_O',
            'diam_dr_P','diam_dr_O','cnt_dr_P','cnt_dr_O',
            'diam_dt_P','diam_dt_O','cnt_dt_P','cnt_dt_O',
            'diam_per_P','diam_per_O','cnt_per_P','cnt_per_O']


    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)


    gr_obj = (
    'purposeTypesID_P', 'purposeTypesID_O',
    'armatureTypesID_P', 'armatureTypesID_O', 
    'designTypesID_P', 'designTypesID_O',
    'materialTypesID_P', 'materialTypesID_O', 
    'materialTypesID_P', 'constructionTypesID_O',
    'diam_reg_P', 'diam_reg_O',
    'diam_sec_P', 'diam_sec_O',
    'diam_v_P', 'diam_v_O',
    'diam_dr_P', 'diam_dr_O',
    'diam_dt_P', 'diam_dt_O',
    'diam_per_P', 'diam_per_O',
    
    )

    
    q = sql.group_ps1(q, cols, gr_obj)

    join_tabs = {
        'purposeTypesID_P': 'purposeTypes',
        'purposeTypesID_O': 'purposeTypes',
    
        'armatureTypesID_P': 'armatureTypes',
        'designTypesID_P': 'designTypes',
        'materialTypesID_P': 'materialTypes',
        'constructionTypesID_P': 'constructionTypes',

        'armatureTypesID_O': 'armatureTypes',
        'designTypesID_O': 'designTypes',
        'materialTypesID_O': 'materialTypes',
        'constructionTypesID_O': 'constructionTypes',
    }

    q = sql.ps_add(q, cols, join_tabs)

    return q


#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):

    conn = connect.connect(**c)

    q = get_f2_1_q(mark_line, mark_pts)

#    print(q)
#    exit(0)

    
#    ws = wb.create_sheet(title="Ф2_1.Механическое оборудование")

    row0 = write_header(ws)
    
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)
#    excel.adjust_table2_2(ws, row0, 1, r2, 2)
    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])



#-------------------------------------------------------------------------------------

def do_passport2(conn, wb, ms_rs, id, fragments, mark_line, mark_pts):

#    q = sql.get_f2_1_q(mark_line)

    q = f'''select * from getPts({id},'{ms_rs}','{fragments}')'''


#    ws = wb.create_sheet(title="Ф2_1.Механическое оборудование")

    write_header(ws)
    row0, col0 = excel.write_table(ws, conn, q, row0=6)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 2. Механическое оборудование участка трубопровода. Запорная арматура', bold=True)

    excel.write_text2(ws, 'A3:B4', 'Участок трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A5:A5', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B5:B5', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C5', 'Камера / павильон', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D4:H4', 'Подающий трубопровод', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I4:M4', 'Обратный трубопровод', excel.thin_border, alignment=excel.center_alignment, bold=False)

    
    excel.write_text2(ws, 'D3:M3', 'Запорная арматура, дренажный кран, воздушник', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N3:Q3', 'Регулирующая арматура', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R3:U3', 'Секционирующая арматура', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'V3:Y3', 'Воздушник', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Z3:AC3', 'Дренажный кран', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'AD3:AG3', 'Дренажный трубопровод', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'AH3:AK3', 'Перемычка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    for ii in range(2):
        excel.write_text2(ws, 'D5', 'Назначение', excel.thin_border, alignment=excel.center_alignment, dx=ii*5, bold=True)
        excel.write_text2(ws, 'E5', 'Тип', excel.thin_border, alignment=excel.center_alignment, dx=ii*5, bold=True)
        excel.write_text2(ws, 'F5', 'РСЃРїРѕР»РЅРµРЅРёРµ', excel.thin_border, alignment=excel.center_alignment, dx=ii*5, bold=True)
        excel.write_text2(ws, 'G5', 'Материал', excel.thin_border, alignment=excel.center_alignment, dx=ii*5, bold=True)
        excel.write_text2(ws, 'H5', 'Конструкция', excel.thin_border, alignment=excel.center_alignment, dx=ii*5, bold=True)

    for ii in range(6):
        excel.write_text2(ws, 'N4:O4', 'Диаметр условный, мм', excel.thin_border, dx=ii*4, alignment=excel.center_alignment, bold=False)
        excel.write_text2(ws, 'P4:Q4', 'Количество, шт.', excel.thin_border, dx=ii*4, alignment=excel.center_alignment, bold=False)

    for ii in range(6*2):
        excel.write_text2(ws, 'N5', 'Подача', excel.thin_border, dx=ii*2, alignment=excel.center_alignment, bold=False)
        excel.write_text2(ws, 'O5', 'Обратка', excel.thin_border, dx=ii*2, alignment=excel.center_alignment, bold=False)
        

#    ws.row_dimensions[4].height = 40
    ws.row_dimensions[5].height = 25

    return 6
