# Р¤14.РћРїСЂРµСЃСЃРѕРІРєРё

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

[Наименование начального узла],
[Наименование конечного узла],

[Описание контура],
[Вид испытания],
[Дата проведения опрессовки],
[Давление опрессовки 1 этапа, кгс/см2],
[Давление опрессовки 2 этапа, кгс/см2],
[Решение комиссии],
[Адрес нарушения],
[Описание повреждения],
[Способ ликвидации нарушения],

[Р¤РРћ СЂСѓРєРѕРІРѕРґРёС‚РµР»СЏ РёСЃРїС‹С‚Р°РЅРёР№],
[Должность руководителя испытаний],
[Подразделение руководителя испытаний],
            
            
[Участок эксплуатации],
[Р¤РРћ РЅР°С‡Р°Р»СЊРЅРёРєР° СѓС‡Р°СЃС‚РєР°]

    from getPts_test({id},'{ms_rs}','{fragments}')
    '''

#    ws = wb.create_sheet(title="Ф14.Опрессовки")
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

#    print(row0, 3, r2, c2)

#    excel.adjust_table2(ws, row0, 3, r2, c2)
    excel.adjust_table2_3(ws, row0 + 1, r2, list(range(3, 16+1)))

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 14. Эксплуатационные испытания', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Описание контура', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Вид испытания', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Дата проведения опрессовки', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Давление опрессовки 1 этапа, кгс/см2', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Давление опрессовки 2 этапа, кгс/см2', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Решение комиссии', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Адрес нарушения ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Описание повреждения', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K4', 'Способ ликвидации нарушения ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:N3', 'Ответственное лицо структурного подразделения производившего испытания', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O3:P3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L4', 'Подразделение производившего работы ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M4', 'Должность ответственного', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N4', 'Р¤РРћ РѕС‚РІРµС‚СЃС‚РІРµРЅРЅРѕРіРѕ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
