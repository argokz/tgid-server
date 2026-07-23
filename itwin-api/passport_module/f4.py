# Р¤4.РљР°РјРµСЂС‹

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts, mark_node, vals):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)

    q = f'''
select 
--    tblName,
    pavilion,
    constructionType,
    height,
    lenKamera,
    width,
    overlapType,
    count_lyukov,
    nalichie_reshetok,
    god_vvoda,
    organizations,
    primechanie,
    naimenovanie_uchastka,
    fio
from 
    getPts_tkamera({id},'{ms_rs}','{fragments}')
    '''

    q = f'''

select 
    IIF (n.nodeName is NULL or n.nodeName = '' or n.nodeName = ' ',n.externalNodeName, n.nodeName) AS pavilion,  

    obj.constructionTypesID,
    obj.vnutr_vysota_kamery as height,
    obj.vnutr_dlina_kamery as lenKamera,
    obj.vnutr_shirina_kamery as width,
    obj.constructionOverlapTypesID,
    obj.fakticheskoe_kolichestvo_lyukov as count_lyukov,
    obj.nalichie_reshetok as nalichie_reshetok,
    obj.god_vvoda_v_jekspluataciju as god_vvoda,
    obj.organizationID,
    obj.primechanie,
    '' as naimenovanie_uchastka,
    '' as fio

from tkamera obj
join nodes n on n.shape.STDistance(obj.shape) = 0 and n.removed=0
join (
values 
{mark_node}
) mark_nodes(ord, id)
on mark_nodes.id=n.id
order by mark_nodes.ord

    '''

    obj = f'''

select 
--    IIF (n.nodeName is NULL or n.nodeName = '' or n.nodeName = ' ',n.externalNodeName, n.nodeName) AS pavilion,  
    id,
    shape,

    constructionTypesID,
    vnutr_vysota_kamery as height,
    vnutr_dlina_kamery as lenKamera,
    vnutr_shirina_kamery as width,
    constructionOverlapTypesID,
    fakticheskoe_kolichestvo_lyukov as count_lyukov,
    nalichie_reshetok as nalichie_reshetok,
    god_vvoda_v_jekspluataciju as god_vvoda,
    organizationID,
    primechanie
--    0 as naimenovanie_uchastka,
--    0 as fio

from tkamera
    '''

    obj = '(' + obj + ')'

    name = vals.get('name', '')
    nomer_uchastka = vals.get('nomer_uchastka', '')
    fio = vals.get('fio', '')

    cols = [
'constructionTypesID',
'height',
'lenKamera',
'width',
'constructionOverlapTypesID',
'count_lyukov',
'nalichie_reshetok',
'god_vvoda',
'organizationID',
'primechanie',

f'\'{nomer_uchastka}\' as nomer_uchastka',
f'\'{fio}\' as fio',
#'fio'
    ]


    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)


    set_gr = (
'constructionTypesID',
'height',
'lenKamera',
'width',
'constructionOverlapTypesID',
#'count_lyukov',
'nalichie_reshetok',
'god_vvoda',
'organizationID',
'primechanie',
#'naimenovanie_uchastka',
#'fio'
    )


    q = sql.group_ps1(q, cols, set_gr)
    q = q.replace('.STPointN(1)', '');

    join_tabs = {
        'organizationID': 'organizations',
        'constructionTypesID': 'constructionTypes',
        'constructionOverlapTypesID': 'constructionOverlapTypes',
    }

    q = sql.ps_add(q, cols, join_tabs, node=True, line=False)

#    print(q)

#    ws = wb.create_sheet(title="Ф4.Камеры")
    excel.write_text2(ws, 'A1:K1', 'Форма 4. Камеры', bold=True)
    write_header(ws)
    excel.write_table(ws, conn, q, row0=5)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A3:A4', 'Наименование узла', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B3:B4', 'Конструкция камеры', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:E3', 'Внутренние размеры, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Тип перекрытия камеры', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Количество люков, шт', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Наличие решеток ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Год ввода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Балансовая принадлежность', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:L4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:M4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C4', 'Высота, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D4', 'Ширина, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E4', 'Ширина, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
