# Р¤7.РЎРїРµС†.РєРѕРЅСЃС‚СЂ.

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)

    q = f'''
select 
beginNode,
endNode,
length,
description,
nomer_chertezha,
1 as kvo,
primechanie
from getPts_duker_shield_bridge({id},'{ms_rs}','{fragments}')
    '''

    q = '''

select 
        d.id,
        d.shape,
        d.length,
        'Дюкер' AS description,
        d.nomer_chertezha,
        1 as cnt,
        d.primechanie
from duker d
UNION ALL
select 
        b.id,
        b.shape,
        b.length,
        'Мостовой переход' AS description,
        b.nomer_chertezha,
        1 as cnt,
        b.primechanie
from bridge_crossing b
UNION ALL
select 
        s.id,
        s.shape,
        s.length,
        'Щит' AS description,
        s.nomer_chertezha,
        1 as cnt,
        s.primechanie
from shield s
    '''

    obj = '(' + q + ')'


    cols = [
'length',
'description',
'nomer_chertezha',
'cnt',
'primechanie',
    ]


    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)

    set_gr = (
'length',
'description',
'nomer_chertezha',
'primechanie',
    )
    
    q = sql.group_ps1(q, cols, set_gr)
    q = q.replace('.STPointN(1)', '');


    join_tabs = {
        'organizationID': 'organizations',
        'constructionTypesID': 'constructionTypes',
        'constructionOverlapTypesID': 'constructionOverlapTypes',
    }

    q = sql.ps_add(q, cols, join_tabs, node=False, line=True)

    join_tabs = {
    }

#    ws = wb.create_sheet(title="Ф7.Спец.констр.")
    excel.write_text2(ws, 'A1:K1', 'Форма 7. Специальные строительные конструкции (щиты, дюкеры, мостовые переходы)', bold=True)
    write_header(ws)
    excel.write_table(ws, conn, q, row0=5)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Длина, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Описание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Номер типового чертежа', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Количество, шт', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
