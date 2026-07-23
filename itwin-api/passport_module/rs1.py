from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, Border, Side
from openpyxl.utils import column_index_from_string
from openpyxl.utils.cell import coordinate_from_string

import psycopg2 as pyodbc
import excel


# Определение стиля границы (тонкая черная линия)
thin_border = Border(
    left=Side(style='thin', color='000000'),
    right=Side(style='thin', color='000000'),
    top=Side(style='thin', color='000000'),
    bottom=Side(style='thin', color='000000')
)

underline_border = Border(
    bottom=Side(style='hair', color='000000')
)

no_border = Border()

custom_font = Font(name='Arial', size=14, bold=True, italic=False, color="FF0000")
small_alignment = Alignment(horizontal='center', vertical='bottom', wrap_text=False)


def write_rs(ws, vals):
    ws.title = 'Общая хар-ка'

    ws.sheet_view.showGridLines = False    

    alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

    cell = excel.write_text2(ws, 'A1:K1', 'РўР•РҐРќРР§Р•РЎРљРР™ РџРђРЎРџРћР Рў')
    cell.alignment = alignment
   
    cell = excel.write_text2(ws, 'A4:C4', 'Дата заполнения')
    cell = excel.write_text2(ws, 'A6:C6', 'Регистрационный №')
    cell = excel.write_text2(ws, 'F6:H6', 'распределительной сети')
    cell = excel.write_text2(ws, 'A8:G8', 'Наименование и адрес предприятия-владельца трубопровода')
    cell = excel.write_text2(ws, 'A10:D10', 'Назначение распределительной сети')
    cell = excel.write_text2(ws, 'A11:B11', 'Рабочая среда')
    cell = excel.write_text2(ws, 'A12:E12', 'Рабочие параметры среды:')
    cell = excel.write_text2(ws, 'B13:D13', 'давление, МПа (кгс/см2)')
    cell = excel.write_text2(ws, 'B14:D14', 'температура, °C')
    cell = excel.write_text2(ws, 'A16:K16', 'Перечень схем, чертежей, свидетельств и других документов на изготовление и')
    cell = excel.write_text2(ws, 'A17:F17', 'монтаж трубопровода, представляемых при регистрации')
    cell = excel.write_text2(ws, 'B21', 'МП')
    cell = excel.write_text2(ws, 'A23:C23', 'Зам.председателя')
    cell = excel.write_text2(ws, 'A24:E24', 'правления по эксплуатации')
    

#naimenovanie АО "Астана-Теплотранзит"

 
    cell = excel.write_text2(ws, 'D4:E4', vals.get('data_zapolneniya',''), border=underline_border)   # Дата заполнения
    cell = excel.write_text2(ws, 'D6:E6', vals.get('registratsionnyy_nomer',''), border=underline_border)   # Регистрационный №
    cell = excel.write_text2(ws, 'I6:K6', vals.get('uzel_podklyucheniya',''), border=underline_border)   # распределительной сети

    cell = excel.write_text2(ws, 'H8:K8', vals.get('',''), border=underline_border)   #
    cell = excel.write_text2(ws, 'A9:K9', vals.get('adres_predpriyatiya_vladeltsa',''), border=underline_border)   #  Наименование и адрес предприятия-владельца трубопровода
    cell = excel.write_text2(ws, 'E10:K10', vals.get('naznachenie_rs',''), border=underline_border)   # Назначение распределительной сети
    cell = excel.write_text2(ws, 'C11:K11', vals.get('rabochaya_sreda',''), border=underline_border)   # Рабочая среда
    cell = excel.write_text2(ws, 'E13:K13', vals.get('rabochee_davlenie',''), border=underline_border)   # давление, МПа (кгс/см2)
    cell = excel.write_text2(ws, 'E14:K14', vals.get('rabochaya_temperatura',''), border=underline_border)   # температура, °C
    cell = excel.write_text2(ws, 'G17:K17', vals.get('',''), border=underline_border)   # Перечень схем, чертежей
    cell = excel.write_text2(ws, 'A18:K18', vals.get('',''), border=underline_border)   # ----//------
    cell = excel.write_text2(ws, 'A19:K19', vals.get('',''), border=underline_border)   # ----//------
    cell = excel.write_text2(ws, 'D23:G23', vals.get('',''), border=underline_border)   #

    excel.set_default_font(ws)


if __name__ == "__main__":

    wb = Workbook()

    ws = wb.active

    write_rs(ws)

    wb.save("1/sample_rs.xlsx")
