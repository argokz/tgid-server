# Р¤8.РР·РѕР»СЏС†РёСЏ С‚СЂСѓР±

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def get_f8(mark_line, mark_pts):

    cols = [
      'isolMaterialID',
      'isolThickness',
      'externMaterialID',
      'externCoverThick',
      'anticorrMaterialID',
      'primechanie',
    ]

#    q = sql.get_ps2(mark_line, cols, mark_pts)
#    obj_par = ',' + ','.join(cols)

    join_tabs = {
      'isolMaterialID': 'isolMaterials',
      'externMaterialID': 'externalMaterials',
      'anticorrMaterialID': 'anticorrMaterials',
    }

    obj_par, obj_par2, joins = sql.make_lookups('ps2', cols, join_tabs)

    q = f'''
select 

{sql.node_name('nn1')} as name1,
{sql.node_name('nn2')} as name2
{obj_par2}


from (
    select 
        ps2.id,
        max(ps2.nodeID1) as nodeID1,
        max(ps2.nodeID2) as nodeID2,
        ps_ord
        {obj_par}

    from ({sql.get_ps2(mark_line, mark_pts, cols)}) ps2
    group by ps2.id, ps_ord
        {obj_par}



) ps2

JOIN nodes nn1 on ps2.nodeID1=nn1.id
JOIN nodes nn2 on ps2.nodeID2=nn2.id
{joins}


'''

    return q


#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f8_(mark_line)

    print('-----------')

    q = f'''
select 
beginNode,
endNode,
isolMaterial,
isolThickness,
externalMaterial,
externCoverThick,
anticorrMaterial,
primechanie
from getIsolTubesPts({id},'{ms_rs}','{fragments}')
'''


    q0 = get_f8(mark_line, mark_pts)
    q = q0 +  '\norder by ps_ord'


#    ws = wb.create_sheet(title="Р¤8.РР·РѕР»СЏС†РёСЏ С‚СЂСѓР±")
    row0 = write_header(ws)

    r2, c2 = excel.write_table(ws, conn, q, row0=row0)
#    excel.adjust_table2_2(ws, row0, 1, r2, 2)
    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])


    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):

    excel.write_text2(ws, 'A1:K1', 'Р¤РѕСЂРјР° 8. РР·РѕР»СЏС†РёСЏ С‚СЂСѓР±', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:D3', 'Теплоизоляционный материал', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:F3', 'Наружное покрытие', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Материал антикоррозионного покрытия ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C4', 'Теплоизоляционный материал', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D4', 'Толщина тепловой изоляции, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E4', 'Материал', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F4', 'Толщина, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 
    
    return 5
