# Р¤5.РџР°РІРёР»СЊРѕРЅС‹

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts, mark_node, vals):
    conn = connect.connect(**c)

    q = f'''
select 
    pavilion,
    locationType,
    constructionType,
    s,
    oborudovanie_pavilona,
    sredstva_pozharotushenija,
    signalizacija,
    nalichie_osveshhenija,
    nalichie_shem_truboprovodov,
    god_vvoda,
    naimenovanie_uchastka,
    fio,
    organizations,
    primechanie
from 
    getPts_pavilion({id},'{ms_rs}','{fragments}')
    '''

    obj = f'''
        SELECT
        id,
        shape,

        locationTypesID,
        constructionTypesID,
        (vnutr_shirina_kamery * vnutr_dlina_kamery) * 1e-6 as s,
        vnutr_vysota_kamery as height,      
        oborudovanie_pavilona,
        sredstva_pozharotushenija,

        signalizacija,

        nalichie_osveshhenija,
        nalichie_shem_truboprovodov,
        god_poslednego_vvoda_v_jekspluataciju as god_vvoda, 

        organizationID,
        primechanie

        FROM pavilion obj       

    '''

    obj = '(' + obj + ')'

    name = vals.get('name', '')
    nomer_uchastka = vals.get('nomer_uchastka', '')
    fio = vals.get('fio', '')

    cols = [
'locationTypesID',
'constructionTypesID',
's',
#'height',      
'oborudovanie_pavilona',
'sredstva_pozharotushenija',
'signalizacija',
'nalichie_osveshhenija',
'nalichie_shem_truboprovodov',
'god_vvoda', 

f'\'{nomer_uchastka}\' as nomer_uchastka',
f'\'{fio}\' as fio',

'organizationID',
'primechanie',

    ]

    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)

    set_gr = (
'locationTypesID',
'constructionTypesID',
's',
#'height',      
'oborudovanie_pavilona',
'sredstva_pozharotushenija',
'signalizacija',
'nalichie_osveshhenija',
'nalichie_shem_truboprovodov',
'god_vvoda', 
'organizationID',
'primechanie',
    )

    q = sql.group_ps1(q, cols, set_gr)
    q = q.replace('.STPointN(1)', '');

    join_tabs = {
        'organizationID': 'organizations',
        'constructionTypesID': 'constructionTypes',
    }

    q = sql.ps_add(q, cols, join_tabs, node=True, line=False)

#    ws = wb.create_sheet(title="Ф5.Павильоны")
    excel.write_text2(ws, 'A1:K1', 'Форма 5. Павильоны', bold=True)
    write_header(ws)
    excel.write_table(ws, conn, q, row0=5)

    conn.close()


#-------------------------------------------------------------------------------------

def write_header(ws):

    excel.write_text2(ws, 'A3:A4', 'Наименование павильона', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B3:B4', 'Место расположения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Конструкция стен здания ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Площадь, м2 ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Оборудование павильона', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Средства пожаротушения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Сигнализация', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Наличие освещения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Наличие схем трубопроводов', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Год ввода в эксплуатацию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:L3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:M4', 'Балансовая принадлежность', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N3:N4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    return 5
