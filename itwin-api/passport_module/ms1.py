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

#------------------------------------------------------------------------------------------

def write_ms(ws, vals):

    ws.title = 'Общая хар-ка'

    ws.sheet_view.showGridLines = False    

#    for k, v in vals.items():
#        print(k, v)

    small_font = excel.small_font
    height_small = small_font.sz / 0.75

    alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)


    cell = excel.write_text2(ws, 'D3:E3', vals.get('data_zapolneniya', ''), border=underline_border)  # Дата заполнения
    cell = excel.write_text2(ws, 'B5:K5', vals.get('energosistema', ''), border=underline_border)  # название энергосистемы
    cell = excel.write_text2(ws, 'C7:F7', vals.get('naimenovanie_magistrali', ''), border=underline_border)  # Магистраль №
    cell = excel.write_text2(ws, 'I7:K7', vals.get('nomer_pasporta', ''), border=underline_border)  # Паспорт №
    cell = excel.write_text2(ws, 'C8:K8', vals.get('vid_seti', ''), border=underline_border)  # Вид сети
    cell = excel.write_text2(ws, 'D10:K10', vals.get('naimenovanie_istochnika', ''), border=underline_border)  # РСЃС‚РѕС‡РЅРёРє С‚РµРїР»РѕСЃРЅР°Р±Р¶РµРЅРёСЏ
    cell = excel.write_text2(ws, 'G12:K12', vals.get('', ''), border=underline_border)  # Название проектной организации и номер проекта

    cell = excel.write_text2(ws, 'A13:K13', vals.get('proektnaya_organizatsiya', ''), border=underline_border)  # -------//------------

    cell = excel.write_text2(ws, 'D14:E14', vals.get('obschaya_dlina_trassy', ''), border=underline_border)  # Общая длина трассы
    cell = excel.write_text2(ws, 'H14:K14', vals.get('vid_seti', ''), border=underline_border)  # Теплоноситель
    cell = excel.write_text2(ws, 'E15:F15', vals.get('rabochee_davlenie', ''), border=underline_border)  # давление
    cell = excel.write_text2(ws, 'J15', vals.get('rabochaya_temperatura', ''), border=underline_border)      # температура
    cell = excel.write_text2(ws, 'C16:D16', vals.get('god_postroyki', ''), border=underline_border)  # Год постройки
    cell = excel.write_text2(ws, 'H16:K16', vals.get('god_vvoda_v_ekspluatatsiyu', ''), border=underline_border)  # Год ввода в эксплуатацию
    cell = excel.write_text2(ws, 'E21:G21', vals.get('', ''), border=underline_border)  #

    cell = excel.write_text2(ws, 'A1:K1', 'РўР•РҐРќРР§Р•РЎРљРР™ РџРђРЎРџРћР Рў', bold=True)
    cell.alignment = alignment

    cell = excel.write_text2(ws, 'A3:C3', 'Дата заполнения')
    cell = excel.write_text2(ws, 'A5', 'ТС')

    cell = excel.write_text2(ws, 'B6:K6', '(название энергосистемы)')
    cell.font = small_font
    cell.alignment = small_alignment
    ws.row_dimensions[6].height = height_small  # Устанавливаем высоту 10 (уменьшенная)

    cell = excel.write_text2(ws, 'A7:B7', 'Магистраль №')

    cell = excel.write_text2(ws, 'G7', 'Паспорт №')
    cell = excel.write_text2(ws, 'A8:B8', 'Вид сети')

    cell = excel.write_text2(ws, 'C9:K9', '(водяная, паровая)')
    cell.font = small_font

    cell.alignment = small_alignment
    ws.row_dimensions[9].height = height_small  # Устанавливаем высоту 10 (уменьшенная)

    cell = excel.write_text2(ws, 'A10:C10', 'РСЃС‚РѕС‡РЅРёРє С‚РµРїР»РѕСЃРЅР°Р±Р¶РµРЅРёСЏ')
    cell = excel.write_text2(ws, 'E11:K11', '(ТЭЦ, ГРЭС)')
    cell.font = small_font
    cell.alignment = small_alignment

    ws.row_dimensions[11].height = height_small  # Устанавливаем высоту 10 (уменьшенная)

    cell = excel.write_text2(ws, 'A12:F12', 'Название проектной организации и номер проекта')
    cell = excel.write_text2(ws, 'A14:C14', 'Общая длина трассы')
    cell = excel.write_text2(ws, 'F14:G14', 'м. Теплоноситель')
    cell = excel.write_text2(ws, 'A15:D15', 'Расчетные параметры: давление')
    cell = excel.write_text2(ws, 'G15:I15', 'МПа (кгс/м2), температура')
    cell = excel.write_text2(ws, 'K15', '°C')

    cell = excel.write_text2(ws, 'A16:B16', 'Год постройки')
    cell = excel.write_text2(ws, 'E16:G16', 'Год ввода в эксплуатацию')
    cell = excel.write_text2(ws, 'E17:I17', '( по ценам 20____г.)')
    ws.row_dimensions[17].height = height_small  # Устанавливаем высоту 10 (уменьшенная)
    cell.font = small_font
    cell.alignment = small_alignment

    cell = excel.write_text2(ws, 'B19', 'МП')
    cell = excel.write_text2(ws, 'A21:C21', 'Зам.председателя')
    cell = excel.write_text2(ws, 'A22:C22', 'правления по эксплуатации')

    excel.set_default_font(ws)

#------------------------------------------------------------------------------------------

if __name__ == "__main__":

    wb = Workbook()

    ws = wb.active

    write_ms(ws, {})

    wb.save("1/sample_ms.xlsx")
