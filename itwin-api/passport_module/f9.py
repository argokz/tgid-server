# Ф9.Ответств.лицо

import psycopg2 as pyodbc
from openpyxl import Workbook

import connect
import sql
import excel
import journals_pg

#-------------------------------------------------------------------------------------

def do_passport(c, ws, ms_rs, id, fragments, mark_line, mark_pts):
    conn = connect.connect(**c)

    q = f'''
    select 
    naimenovanie_uchastka,naimenovanie_rayona,nomer_uchastka,fio,nomer_prikaza_otv,data_prikaza_otv,otv_dolznost,otv_fio 
    from ({journals_pg.responsible_person(id, ms_rs)}) t
    '''

#    ws = wb.create_sheet(title="Ф9.Ответств.лицо")
    row0 = write_header(ws)
    excel.write_table(ws, conn, q, row0=row0)

    conn.close()

#-------------------------------------------------------------------------------------

def write_header(ws):
    excel.write_text2(ws, 'A1:K1', 'Форма 9. Лицо, ответственное за исправное состояние и безопасную эксплуатацию трубопровода', bold=True)

    excel.write_text2(ws, 'A3:A4', 'Наименование фрагмента тепловой сети ', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'B3:B4', 'Район эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'C3:C4', 'Участок эксплуатации', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'D3:D4', 'ФИО начальника участка', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E3:H3', 'Лицо, ответственное за исправное состояние и безопасную эксплуатацию трубопровода', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'E4', 'Номер приказа о назначении', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'F4', 'Дата приказа о назначении', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'G4', 'Должность', excel.thin_border, alignment=excel.center_alignment, bold=False)
    excel.write_text2(ws, 'H4', 'ФИО', excel.thin_border, alignment=excel.center_alignment, bold=False)

    ws.row_dimensions[4].height = 25 

    return 5
