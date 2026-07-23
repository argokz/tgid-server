# Р¤1.РўСЂСѓР±С‹

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def get_f1(mark_line, mark_pts):

    cols = []


    q = f'''
select 
--ps2.id,

--{sql.node_name_sw('l_napr','nn1','nn2')} as name1,
--{sql.node_name_sw('l_napr','nn2','nn1')} as name2,

{sql.node_name('nn1')} as name1,
{sql.node_name('nn2')} as name2,


ps2.diamP,
lenP,

ps2.diamO,
lenO,

ps2.tolP,
ps2.tolO,
--ROUND(vP,2) as vP,
--ROUND(vO,2) as vO,
vP as vP,
vO as vO,


--l_napr,

tubingTypes.name as tubingTypes_name,
tubeTypes.name as tubeTypes_name

from (
    select 
        ps2.id,
        max(ps2.nodeID1) as nodeID1,
        max(ps2.nodeID2) as nodeID2,
        ps_ord,

--        min(l_napr) as l_napr,

        max(tubingTypeID) as tubingTypeID,
        max(tubeTypeID) as tubeTypeID,

        max(ps2.diamP) as diamP,
        max(ps2.diamO) as diamO,
        max(ps2.tolP) as tolP,
        max(ps2.tolO) as tolO,
        sum(lenP) as lenP,
        sum(lenO) as lenO,
        sum(vP) as vP,
        sum(vO) as vO

    from ({sql.get_ps2(mark_line, mark_pts, cols)}) ps2
    group by ps2.id, ps_ord


) ps2

--join pipeSections ps1 on ps1.id=ps2.id

JOIN nodes nn1 on ps2.nodeID1=nn1.id
JOIN nodes nn2 on ps2.nodeID2=nn2.id
left join tubingTypes on tubingTypes.id=ps2.tubingTypeID
left join tubeTypes on tubeTypes.id=ps2.tubeTypeID

--order by ps_ord

'''

    return q


#-------------------------------------------------------------------------------------


def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):

    conn = connect.connect(**c)

    q0 = get_f1(mark_line, mark_pts)

#    ws = wb.create_sheet(title="Ф1.Трубы")

    row0 = write_header(ws)

    q = q0 +  '\norder by ps_ord'
#    print(q)


    row0, col0 = excel.write_table(ws, conn, q0, row0=row0)

    q = f'''select 'По диаметру:', '', diamP, ROUND(sum(lenP), 2), diamO, ROUND(sum(lenO), 2) FROM ({q0}) T group by diamP, diamO order by diamP, diamO'''
    q = f'''select 'По диаметру:', '', diamP, sum(lenP), diamO, sum(lenO) FROM ({q0}) T group by diamP, diamO order by diamP, diamO'''

    row0, col0 = excel.write_table(ws, conn, q, row0=row0, numbers=False, freez=False)
    
    q = f'''select 'РС‚РѕРіРѕ:', '', '', sum(lenP), '', sum(lenO) FROM ({q0}) T'''

    row0, col0 = excel.write_table(ws, conn, q, row0=row0, numbers=False, freez=False)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws, bold=True):
    excel.write_text2(ws, 'A1:K1', 'Форма А.1.Трубы', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Наименование участка трубопровода трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:D3', 'Подающая труба', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:F3', 'Обратная труба', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:H3', 'Толщина стенки трубы, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:J3', 'Объем трубы, м3', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:L3', 'Тип прокладки', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'C4', 'Наружный диаметр, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D4', 'Длина, м', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E4', 'Наружный диаметр, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F4', 'Длина, м', excel.thin_border, alignment=excel.center_alignment, bold=False)

    
    excel.write_text2(ws, 'G4', 'Подающая', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H4', 'Обратная', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'I4', 'Подающая', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J4', 'Обратная', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'K4', 'Тип прокладки', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L4', 'Вид трубы', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[3].height = 40
    ws.row_dimensions[4].height = 40

    ws.column_dimensions['A'].width = 20
    ws.column_dimensions['B'].width = 20


    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['E'].width = 10

    ws.column_dimensions['I'].width = 10
    ws.column_dimensions['J'].width = 10
    ws.column_dimensions['K'].width = 15
    ws.column_dimensions['L'].width = 20

    return 5

