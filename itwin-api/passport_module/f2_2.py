# Р¤2_2.РњРµС…Р°РЅРёС‡РµСЃРєРѕРµ РѕР±РѕСЂСѓРґРѕРІР°РЅРёРµ

import psycopg2 as pyodbc

import logging
from openpyxl import Workbook

import connect
import sql
import excel

def sql1():

    q = '''

select 'kolodtsy' AS 'tblName',
        kol.id,
        kol.shape,
        pt.name as 'purposeTypes',
        ch.name as 'characteristicTypes',
        ch_l.name as 'characteristicTypesLyuki',
        mt_l.name as 'materialTypesLyuki',
        ct_l.name as 'constructionTypesLyuki',
        kol.priznak_truboprovoda,
        NULL as 'diametr_truboprovoda',
        NULL as 'constructionTypes'
from kolodtsy kol
left join purposeTypes pt on pt.id = kol.purposeTypesID
left join characteristicTypes ch on ch.id = kol.characteristicTypesID
left join characteristicTypes ch_l on ch_l.id = kol.characteristicTypesIDlyuki
left join materialTypes mt_l on mt_l.id = kol.materialTypesIDlyuki
left join constructionTypes ct_l on ct_l.id = kol.constructionTypesIDlyuki
UNION ALL
select 'kompensator' AS 'tblName',
        k.id,
        k.shape,
        Null as 'purposeTypes',
        Null as 'characteristicTypes',
        NULL as 'characteristicTypesLyuki',
        NULL as 'materialTypesLyuki',
        NULL as 'constructionTypesLyuki',
        k.priznak_truboprovoda,
        k.diametr_truboprovoda,
        ct.name as 'constructionTypes'
from kompensator k
left join constructionTypes ct on ct.id = k.constructionTypesID



'''

    return q




#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)

    q = f'''
select 
    *
from 
    getPts_kompensator_kolodtsy({id},'{ms_rs}','{fragments}')
    '''

    q = '''

select 
--        priznak_truboprovoda,
        id,
        shape,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then constructionTypesID else null end as constructionTypesID_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then constructionTypesID else null end as constructionTypesID_O,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then diametr_truboprovoda else null end as diametr_truboprovoda_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then diametr_truboprovoda else null end as diametr_truboprovoda_O,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then 1 else 0 end as cnt_komp_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then 1 else 0 end as cnt_komp_O,

        null as purposeTypesID_A,
        null as purposeTypesID_P,
        null as purposeTypesID_O,

        null as characteristicTypesID_A,
        null as characteristicTypesID_P,
        null as characteristicTypesID_O,

        null as cnt_kanal_A,
        null as cnt_kanal_P,
        null as cnt_kanal_O




from kompensator k

UNION ALL

select 

id,
shape,
--priznak_truboprovoda,



null as constructionTypesID_P,
null as constructionTypesID_O,
null as diametr_truboprovoda_P,
null as diametr_truboprovoda_O,
null as cnt_komp_P,
null as cnt_komp_O,


case when coalesce(priznak_truboprovoda, 1) = 1 then purposeTypesID else 0 end as purposeTypesID_A,
case when coalesce(priznak_truboprovoda, 1) = 2 then purposeTypesID else 0 end as purposeTypesID_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then purposeTypesID else 0 end as purposeTypesID_O,

case when coalesce(priznak_truboprovoda, 1) = 1 then characteristicTypesID else 1 end as characteristicTypesID_A,
case when coalesce(priznak_truboprovoda, 1) = 2 then characteristicTypesID else 1 end as characteristicTypesID_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then characteristicTypesID else 1 end as characteristicTypesID_O,

case when coalesce(priznak_truboprovoda, 1) = 1 then 1 else 0 end as cnt_kanal_A,
case when coalesce(priznak_truboprovoda, 1) = 2 then 1 else 0 end as cnt_kanal_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then 1 else 0 end as cnt_kanal_O


from kolodtsy
    
    '''







    q = '''

select 
--        priznak_truboprovoda,
        id,
        shape,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then constructionTypesID else null end as constructionTypesID_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then constructionTypesID else null end as constructionTypesID_O,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then diametr_truboprovoda else null end as diametr_truboprovoda_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then diametr_truboprovoda else null end as diametr_truboprovoda_O,
        case when coalesce(priznak_truboprovoda, 1) <> 3 then 1 else 0 end as cnt_komp_P,
        case when coalesce(priznak_truboprovoda, 1) <> 2 then 1 else 0 end as cnt_komp_O,

-------------------------------------------------------------
-- Колодцы

        null as purposeTypesID_P,
        null as purposeTypesID_O,
        null as purposeTypesID_A,

        null as characteristicTypesID_P,
        null as characteristicTypesID_O,
        null as characteristicTypesID_A,

        null as materialTypesIDlyuki_P,
        null as materialTypesIDlyuki_O,
        null as materialTypesIDlyuki_A,

        null as constructionTypesIDlyuki_P,
        null as constructionTypesIDlyuki_O,
        null as constructionTypesIDlyuki_A,

        null as characteristicTypesIDlyuki_P,
        null as characteristicTypesIDlyuki_O,
        null as characteristicTypesIDlyuki_A,

        null as cnt_kanal_P,
        null as cnt_kanal_O,
        null as cnt_kanal_A


from kompensator k

UNION ALL

select 

id,
shape,
--priznak_truboprovoda,



null as constructionTypesID_P,
null as constructionTypesID_O,
null as diametr_truboprovoda_P,
null as diametr_truboprovoda_O,
null as cnt_komp_P,
null as cnt_komp_O,

-------------------------------------------------------------
-- Колодцы


case when coalesce(priznak_truboprovoda, 1) = 2 then purposeTypesID else 0 end as purposeTypesID_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then purposeTypesID else 0 end as purposeTypesID_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then purposeTypesID else 0 end as purposeTypesID_A,

case when coalesce(priznak_truboprovoda, 1) = 2 then characteristicTypesID else 1 end as characteristicTypesID_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then characteristicTypesID else 1 end as characteristicTypesID_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then characteristicTypesID else 1 end as characteristicTypesID_A,

-------------------------------------------------------------
-- Люки

case when coalesce(priznak_truboprovoda, 1) = 2 then materialTypesIDlyuki else 0 end as materialTypesIDlyuki_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then materialTypesIDlyuki else 0 end as materialTypesIDlyuki_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then materialTypesIDlyuki else 0 end as materialTypesIDlyuki_A,

case when coalesce(priznak_truboprovoda, 1) = 2 then constructionTypesIDlyuki else 0 end as constructionTypesIDlyuki_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then constructionTypesIDlyuki else 0 end as constructionTypesIDlyuki_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then constructionTypesIDlyuki else 0 end as constructionTypesIDlyuki_A,

case when coalesce(priznak_truboprovoda, 1) = 2 then characteristicTypesIDlyuki else 0 end as characteristicTypesIDlyuki_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then characteristicTypesIDlyuki else 0 end as characteristicTypesIDlyuki_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then characteristicTypesIDlyuki else 0 end as characteristicTypesIDlyuki_A,

case when coalesce(priznak_truboprovoda, 1) = 2 then 1 else 0 end as cnt_kanal_P,
case when coalesce(priznak_truboprovoda, 1) = 3 then 1 else 0 end as cnt_kanal_O,
case when coalesce(priznak_truboprovoda, 1) = 1 then 1 else 0 end as cnt_kanal_A


from kolodtsy
    
    '''

    obj = '(' + q + ')'

    cols = ['constructionTypesID_P','constructionTypesID_O','diametr_truboprovoda_P','diametr_truboprovoda_O','cnt_komp_P','cnt_komp_O',
            'purposeTypesID_P','purposeTypesID_O','purposeTypesID_A','characteristicTypesID_P','characteristicTypesID_O','characteristicTypesID_A',
#            Люки            
            'materialTypesIDlyuki_P','materialTypesIDlyuki_O','materialTypesIDlyuki_A',
            'constructionTypesIDlyuki_P','constructionTypesIDlyuki_O','constructionTypesIDlyuki_A',
            'characteristicTypesIDlyuki_P','characteristicTypesIDlyuki_O','characteristicTypesIDlyuki_A',
            'cnt_kanal_P','cnt_kanal_O','cnt_kanal_A'
            ]



    q = sql.get_obj_ps(mark_line, mark_pts, obj, cols)
    q = sql.group_ps1(q, cols)


    join_tabs = {

        "purposeTypesID_P": "purposeTypes",
        "purposeTypesID_O": "purposeTypes",
        "purposeTypesID_A": "purposeTypes",


        "characteristicTypesID_P": "characteristicTypes",
        "characteristicTypesID_O": "characteristicTypes",
        "characteristicTypesID_A": "characteristicTypes",
    }


    q = sql.ps_add(q, cols, join_tabs)

#    print(q)
#    exit(0)

#    logging.info("Ф2_2")
#    logging.debug(q)

#    ws = wb.create_sheet(title="Ф2_2.Механическое оборудование")
    excel.write_text2(ws, 'A1:K1', 'Форма 2. Механическое оборудование участка трубопровода. Компенсаторы. Колодцы')
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)
#    excel.adjust_table2_2(ws, row0, 1, r2, 2)
    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])


#-------------------------------------------------------------------------------------

def do_passport2(conn, wb, ms_rs, id, fragments, mark_line, mark_pts):
#    q = sql.get_f1_(mark_line)

    q = f'''
select 
    purposeTypes,characteristicTypes,characteristicTypesLyuki,materialTypesLyuki,constructionTypesLyuki,externalID,diametr_truboprovoda,constructionTypes
from 
    getPts_kompensator_kolodtsy({id},'{ms_rs}','{fragments}')
    '''



#    ws = wb.create_sheet(title="Ф2_2.Механическое оборудование")
    row0 = write_header(ws)
    excel.write_table(ws, conn, q, row0=row0)

    conn.close()


#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 2. Механическое оборудование участка трубопровода. Компенсаторы. Колодцы', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:I3', 'Компенсаторы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:O3', 'Колодцы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P3:AA3', 'Люки', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4:A5', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4:B5', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C5', 'Камера / павильон', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'D4:E4', 'Конструкция', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F4:G4', 'Диаметр условный, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H4:I4', 'Количество', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J4:L4', 'Назначение', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M4:O4', 'Характеристика', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4:R4', 'Материал', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S4:U4', 'Конструкция', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'V4:X4', 'Характеристика', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Y4:AA4', 'Количество', excel.thin_border, alignment=excel.center_alignment, bold=False)

    for ii in range(3):
        excel.write_text2(ws, 'D5', 'Подача', excel.thin_border, dx=ii*2, alignment=excel.center_alignment, bold=False)
        excel.write_text2(ws, 'E5', 'Обратка', excel.thin_border, dx=ii*2, alignment=excel.center_alignment, bold=False)

    for ii in range(6):
        excel.write_text2(ws, 'J5', 'Подача', excel.thin_border, dx=ii*3, alignment=excel.center_alignment, bold=False)
        excel.write_text2(ws, 'K5', 'Обратка', excel.thin_border, dx=ii*3, alignment=excel.center_alignment, bold=False)
        excel.write_text2(ws, 'L5', 'Общий', excel.thin_border, dx=ii*3, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 6


