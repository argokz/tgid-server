# Р¤12.РЁСѓСЂС„РѕРІРєРё

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import sql2
import excel

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

#    q = sql.get_f1_(mark_line)

    q = f'''
    select 

[Наименование начального узла],
[Наименование конечного узла],
[Признак участка трубопровода],
[Диаметр трубопровода, мм],
[Назначение вскрытия],
[Адрес],
[Состояние],
[Дата начала],
[Дата окончания],
[Номер акта],
[Результаты осмотра],
[Примечание],
[Р¤РРћ СѓС‚РІРµСЂР¶РґР°СЋС‰РµРіРѕ],
[Должность утверждающего],

[Служба утверждающего],
[Участок эксплуатации],
[Р¤РРћ РЅР°С‡Р°Р»СЊРЅРёРєР° СѓС‡Р°СЃС‚РєР°]
    

    from getPts_shurf({id},'{ms_rs}','{fragments}')
    '''

#    shurfy

    cols = [
#        'l.externalSignLineID',
#        'hps.diameterExternal',
        'naznachenie_vskrID',
#        'Адрес as address',
        'sostoyanie_shurfaID',
        'data_nachala',
        'data_okonchaniya',
    ]

    q = sql.get_obj_ps2(mark_line, mark_pts, f'(select id, shape from shurfy)')

    ps2 = sql2.get_ps_obj(conn, q)

    join_tabs = {
        'l.externalSignLineID': 'externalSignLine',

        'sostoyanie_shurfaID': 'sostoyanie_shurfa',
        'naznachenie_vskrID': 'naznachenie_vskr',
#        'dolzhnost_utverzhdaemogoID': 'dolzhnosti',
        'dolzhnost_utverzhdaemogoID': '(select id, znachenie as name from dolzhnosti)',
        'sluzhba_utverzhdaemogoID': 'subdivisions',
    }


    join_dop = ''

    cols = [
        'l.externalSignLineID',
        'hps.diameterExternal',
        'naznachenie_vskrID',
        'CONCAT(st.name, \' \' ,nomer_doma) as address',
        'sostoyanie_shurfaID',
        'data_nachala',
        'data_okonchaniya',
        'nomer_akta',
        'rezultaty_osmotra',
        'primechanie',

         'dolzhnost_utverzhdaemogoID',
         'fio_utverzhdaemogo',
         'sluzhba_utverzhdaemogoID',
         'ue.nomer_uchastka',
         'nu.fio',

    ]


    ucharstok_ms = f'uchastok_{ms_rs}'


    join_dop = f'''
     left join {ucharstok_ms} ms on ms.id=hps.magistralSite
     left join uchastki_ekspluatatsii ue on ms.nomer_uchastka=ue.id
     left join nachalniki_uchastkov nu on nu.id=ue.nachalnik_uchastka
     left join dolzhnosti d on d.id=nu.dolzhnost
     left join ulitsy st ON st.id = z.ulicaID

     '''



    q = sql.ps_add2(ps2, 'shurfy', cols, join_tabs, join_dop=join_dop, node=False)

#    ws = wb.create_sheet(title="Ф12.Шурфовки")
    row0 = write_header(ws)

    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 12. Контрольные вскрытия (шурфовки)', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Признак участка трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Диаметр трубопровода, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Назначение вскрытия ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Адрес', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Состояние', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Дата начала ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Дата окончания', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Номер акта', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K4', 'Результаты осмотра', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:L4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:O3', 'Ответственное лицо структурного подразделения производившего работы по вскрытию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P3:Q3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M4', 'Р¤РРћ СѓС‚РІРµСЂР¶РґР°СЋС‰РµРіРѕ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N4', 'Должность утверждающего', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O4', 'Служба утверждающего', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
