# Р¤6.РћРїРѕСЂС‹

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def get_f6(mark_line, mark_pts):


    obj = '''

select 
    id,
    shape,

vid_opory,
constructionTypesID,

kolichestvo_uporov,
primechanie

from opora
'''



    obj = '(' + obj + ')'

    cols = ['diameterCondit', 'vid_opory','constructionTypesID','kolichestvo_uporov','primechanie']
    cols_gr = ('diameterCondit', 'vid_opory','constructionTypesID','kolichestvo_uporov','primechanie')

    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols, ('diameterCondit'))

    q = sql.group_ps1(q, cols, cols_gr)

    join_tabs = {}

    q = sql.ps_add(q, cols, join_tabs, node=False)

    return q

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = get_f6(mark_line)

#    q = f'select * from getPts_opora(%d,'%s','%s') order by orderID", id, table, fragments);

    q = f'''
    select 
        beginNode,endNode,diameterCondit,oporaType,constructionType,kolichestvo_uporov,primechanie 
    from getPts_opora({id},'{ms_rs}','{fragments}')
    '''

    q = get_f6(mark_line, mark_pts)

#    ws = wb.create_sheet(title="Ф6.Опоры")
    excel.write_text2(ws, 'A1:K1', 'Форма 6. Опоры', bold=True)
    row0 = write_header(ws)

    r2, c2 = excel.write_table(ws, conn, q, row0=row0)
#    excel.adjust_table2_2(ws, row0, 1, r2, 2)
    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])



    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Диаметр трубопровода, условный, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Тип опоры', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Конструкция ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Количество опор, шт ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
