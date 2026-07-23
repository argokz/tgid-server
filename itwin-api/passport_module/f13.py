# Р¤13.Р’С‹СЂРµР·РєРё

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
[Признак участка трубопровода],
[Диаметр трубопровода, мм],
[Назначение вскрытия],
[Адрес],
[Состояние],
[Дата начала],
[Дата окончания],
[Номер акта],
[Результаты осмотра],
[Состояние металла трубопровода],
[Cтепень внешней коррозии],
[Степень внутренней коррозии],
[Примечание],
[Р¤РРћ СѓС‚РІРµСЂР¶РґР°СЋС‰РµРіРѕ],
[Должность утверждающего],

[Служба утверждающего],
[Участок эксплуатации],
[Р¤РРћ РЅР°С‡Р°Р»СЊРЅРёРєР° СѓС‡Р°СЃС‚РєР°]
    

    from getPts_cut_out({id},'{ms_rs}','{fragments}')
    '''


#    ws = wb.create_sheet(title="Ф13.Вырезки")
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 13. Вырезки', bold=True)

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
    excel.write_text2(ws, 'L3:L4', 'Состояние металла трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:M4', 'Cтепень внешней коррозии', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N3:N4', 'Степень внутренней коррозии ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O3:O4', 'Примечание', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P3:R3', 'Ответственное лицо структурного подразделения производившего работы по вскрытию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S3:T3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4', 'Р¤РРћ СѓС‚РІРµСЂР¶РґР°СЋС‰РµРіРѕ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4', 'Должность утверждающего ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R4', 'Служба утверждающего', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'T4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
