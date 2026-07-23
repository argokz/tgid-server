# Р¤15.РћСЃРјРѕС‚СЂ

import psycopg2 as pyodbc
from openpyxl import Workbook
import logging

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
[Диаметр трубопровода, мм],
[Признак участка трубопровода],
[Дата осмотра],
[Внешний вид],
            
[Состояние оборудования],
[Состояние металла трубопровода],
[Состояние строительных конструкций],
[Состояние тепловой изоляции (обратный трубопровод)],
[Состояние тепловой изоляции (подающий трубопровод)],
[Состояние наружного покрытия (обратный трубопровод)],
[Состояние наружного покрытия (подающий трубопровод)],
[Состояние противокоррозионного покрытия (обратный трубопровод)],
[Состояние противокоррозионного покрытия (подающий трубопровод)],
[Отвественное лицо],
[Подразделение проводившее работу],
        
[Участок эксплуатации],
[Начальник участка]

    from getPts_osmotr({id},'{ms_rs}','{fragments}')
    '''


#    ws = wb.create_sheet(title="Ф15.Осмотр")
    row0 = write_header(ws)
    r2, c2 = excel.write_table(ws, conn, q, row0=row0)

    excel.adjust_table2_3(ws, row0 + 1, r2, [1, 2])


    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    '''
    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Диаметр трубопровода, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'Признак участка трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E4', 'Дата осмотра', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F4', 'Внешний вид ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G3:G4', 'Состояние оборудования', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H3:H4', 'Состояние металла трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I3:I4', 'Состояние строительных конструкций', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'J3:J4', 'Состояние тепловой изоляции (обратный трубопровод)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K3:K4', 'Состояние тепловой изоляции (подающий трубопровод)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'L3:L4', 'Состояние наружного покрытия (обратный трубопровод) ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M3:M4', 'Состояние наружного покрытия (подающий трубопровод) ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'N3:N4', 'Состояние противокоррозионного покрытия (обратный трубопровод)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O3:O4', 'Состояние противокоррозионного покрытия (подающий трубопровод)', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P3:Q3', 'Ответственное лицо структурного подразделения производившего работы по освидетельствованию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R3:S3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'P4', 'Ответственное лицо', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4', 'Подразделение проводившее работу', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S4', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    '''

    excel.write_text2(ws, 'A1:K1', 'Форма 15. Записи результатов осмотра трубопроводов', bold=True)

    excel.write_text2(ws, 'A3:B3', 'Участок трассы', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C5', 'Диаметр трубопровода, мм', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D5', 'Признак участка трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:E5', 'Дата осмотра', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F3:F5', 'Внешний вид ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    
    excel.write_text2(ws, 'G3:O3', 'Состояние', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'G4:G5', 'оборудования', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H4:H5', 'металла трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'I4:I5', 'строительных конструкций', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'J4:K4', 'тепловой изоляции', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'J5', 'обратка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'K5', 'подача', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'L4:M4', 'наружного покрытия', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'L5', 'обратка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'M5', 'подача', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'N4:O4', 'противокоррозионного покрытия', excel.thin_border, alignment=excel.center_alignment, bold=False)
    
    excel.write_text2(ws, 'N5', 'обратка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'O5', 'подача', excel.thin_border, alignment=excel.center_alignment, bold=False)
   
    excel.write_text2(ws, 'P3:Q3', 'Ответственное лицо структурного подразделения производившего работы по освидетельствованию', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R3:S3', 'Начальник участка', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'A4:A5', 'Начальный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B4:B5', 'Конечный узел', excel.thin_border, alignment=excel.center_alignment, bold=False)

    excel.write_text2(ws, 'P4:P5', 'Ответственное лицо', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'Q4:Q5', 'Подразделение проводившее работу', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'R4:R5', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'S4:S5', 'Р¤РРћ', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 20
    ws.row_dimensions[5].height = 20

#    print(ws.row_dimensions[5].height)
#    exit(0)

#    logging.info(f'ws.row_dimensions[5].height = {ws.row_dimensions[5].height}')
    

    return 6
