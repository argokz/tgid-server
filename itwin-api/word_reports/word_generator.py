import os
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

def generate_defect_map_word(defect_id: int, defect_data: dict, out_dir: str = "files") -> str:
    """Генерирует .docx Карту повреждаемости (аналог KartaPovrezhdaemosti2.cpp)"""
    os.makedirs(out_dir, exist_ok=True)
    doc = Document()
    
    # Стили
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("КАРТА НАРУШЕНИЯ")
    run.bold = True
    run.font.size = Pt(12)

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run2 = p2.add_run("Заявка №________\nДата заявки №________")
    run2.bold = True
    run2.font.size = Pt(12)

    # Таблица
    table = doc.add_table(rows=0, cols=2)
    table.style = 'Table Grid'

    rows_data = [
        ("Дата обнаружения:", str(defect_data.get('data_osmotra', ''))),
        ("Повреждение:", str(defect_data.get('tip_povrezhdenia', ''))),
        ("Место расположения на трубопроводе, часов:", str(defect_data.get('tsentr_povrezhdenia', ''))),
        ("Характер повреждения:", str(defect_data.get('harakter_povrezhdenia', ''))),
        ("Поврежденный трубопровод:", str(defect_data.get('povrezhdennyi_truboprovod', ''))),
        ("Состояние наружной поверхности трубопровода:", str(defect_data.get('sost_naruzhnoy', ''))),
        ("Расстояние до нарушения от ближайшей камеры, м:", str(defect_data.get('rasstoyanie', ''))),
        ("Начало времени работ:", str(defect_data.get('vremya_nachala_rabot', ''))),
        ("Окончание времени работ:", str(defect_data.get('vremya_okonchaniya_rabot', ''))),
        ("Ширина повреждения:", str(defect_data.get('shirina_povrezhdenia', ''))),
        ("Высота повреждения:", str(defect_data.get('vysota_povrezhdenia', ''))),
        ("Причины нарушения:", str(defect_data.get('prichiny', ''))),
    ]

    for label, val in rows_data:
        row = table.add_row().cells
        run_l = row[0].paragraphs[0].add_run(label)
        run_l.bold = True
        row[1].text = val

    filename = f"defect_map_{defect_id}.docx"
    filepath = os.path.join(out_dir, filename)
    doc.save(filepath)
    return filepath
