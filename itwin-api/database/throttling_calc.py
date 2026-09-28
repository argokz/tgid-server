"""Инженерные расчеты дросселирования: расчет шайб (диафрагм) и элеваторов.

Эталоны десктопа:
- gid8/python/dross/dross.py — бланк расчёта диафрагм теплового ввода (формулы ячеек G20..G43);
- sety/dross/drsh2.py — сопло и горловина элеватора, номер элеватора по диаметру горловины;
- sety/dross/drvary1.py — предупреждения о недостаточном/повышенном напоре на элеваторе.

Расходы считаются в т/ч, напоры — в м вод. ст., нагрузки — в Гкал/ч
(на десктопе нагрузки в ккал/ч: Gо = Qо / ((T1 - T2) * 1000) — то же самое).
"""

from __future__ import annotations

import io
import math
from typing import Any, Optional

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.protection import SheetProtection

# Номер элеватора по диаметру горловины, мм (drsh2.py: <=15 №1 … <=47 №6, <=59 №7).
# drsh2 при dg <= 10 выдаёт «№0»; стандартного элеватора №0 нет — такой ввод получает №1.
ELEVATOR_NECKS: tuple[tuple[int, float], ...] = (
    (1, 15.0), (2, 20.0), (3, 25.0), (4, 30.0), (5, 35.0), (6, 47.0), (7, 59.0),
)

MIN_ORIFICE_MM = 3.0

# Схемы шайб бланка dross.py: (коэффициент формулы, поправка к располагаемому напору, м)
ORIFICE_SCHEMES: dict[str, tuple[float, float]] = {
    "bezelevator": (10.0, -5.0),      # диафрагма безэлеваторного ввода, G26: Нгас = Нрас - 5
    "pump_mix": (10.0, -2.0),         # перед насосами смешения, G29: Нгас = Нрас - 2
    "pre_nozzle": (10.0, 0.0),        # перед соплом элеватора, G32: Нгас = Нрас
    "nozzle": (9.6, 0.0),             # сопло элеватора, G35: Нрас
    "ventilation": (10.0, -5.0),      # на вентиляцию, G38: Нрас - 5
    "heater": (10.0, -5.0),           # перед водоводяным подогревателем, G41: Нрас - 5 (расход отопления)
    "gvs_circulation": (10.0, -5.0),  # на циркуляционную линию ГВС, G43: Нрас - 5 (расход ГВС)
    "gvs": (10.0, -5.0),              # прежнее имя циркуляционной схемы
}


def flow_from_load(q_gcal: float, t_supply: float, t_return: float) -> float:
    """Расход сетевой воды, т/ч, по нагрузке Гкал/ч и перепаду температур."""
    if t_supply <= t_return:
        raise ValueError("Температура подачи должна быть выше температуры обратки.")
    return q_gcal * 1000.0 / (t_supply - t_return)


def gvs_flow_from_max_load(q_gvs_max_gcal: float) -> float:
    """Расход на ГВС, т/ч: Qгвс.ср = Qгвс.max / 2.4; G = Qгвс.ср / 60000 (ккал/ч), dross.py G17/G22."""
    return q_gvs_max_gcal * 1_000_000.0 / 2.4 / 60000.0


def calculate_orifice_diameter(
    *,
    flow_g: float,
    delta_h: float,
    coeff: float = 10.0,
    min_diameter: float = MIN_ORIFICE_MM,
) -> Optional[float]:
    """Диаметр отверстия шайбы (сопла), мм: d = coeff * (G² / Н)^(1/4), не меньше 3 мм.

    None — если гасимого напора нет (Н <= 0): на десктопе формула в этом случае не считается.
    """
    if delta_h <= 0:
        return None
    if flow_g <= 0:
        return min_diameter
    val = round(coeff * math.pow((flow_g * flow_g) / delta_h, 0.25), 1)
    return max(min_diameter, val)


def _resolve_flow(flow_g, q_heating_gcal, q_heating_kcal, t_supply, t_return) -> float:
    if flow_g is not None and flow_g > 0:
        return flow_g
    if q_heating_gcal is not None and q_heating_gcal > 0:
        return flow_from_load(q_heating_gcal, t_supply, t_return)
    if q_heating_kcal is not None and q_heating_kcal > 0:
        return flow_from_load(q_heating_kcal / 1_000_000.0, t_supply, t_return)
    raise ValueError("Укажите расход G или тепловую нагрузку Q.")


def _resolve_head(delta_h, p1, p2) -> float:
    if delta_h is not None and delta_h > 0:
        return delta_h
    if p1 is not None and p2 is not None:
        head = (p1 - p2) * 10.0
        if head <= 0:
            raise ValueError("Располагаемый напор (P1 - P2) должен быть больше нуля.")
        return head
    raise ValueError("Укажите располагаемый напор ΔH или давления P1 и P2.")


def calculate_orifice_plate_full(
    *,
    flow_g: Optional[float] = None,
    delta_h: Optional[float] = None,
    p1: Optional[float] = None,
    p2: Optional[float] = None,
    q_heating_gcal: Optional[float] = None,
    q_heating_kcal: Optional[float] = None,
    t_supply: float = 130.0,
    t_return: float = 70.0,
    scheme: str = "bezelevator",
) -> dict[str, Any]:
    """Расчёт одной шайбы по схеме установки (см. ORIFICE_SCHEMES)."""
    if scheme not in ORIFICE_SCHEMES:
        raise ValueError(f"Неизвестная схема шайбы: {scheme}")
    flow = _resolve_flow(flow_g, q_heating_gcal, q_heating_kcal, t_supply, t_return)
    head = _resolve_head(delta_h, p1, p2)
    coeff, correction = ORIFICE_SCHEMES[scheme]
    h_dissipated = head + correction

    d_orifice = calculate_orifice_diameter(flow_g=flow, delta_h=h_dissipated, coeff=coeff)
    warning = None
    if d_orifice is None:
        warning = (f"Недостаточный располагаемый напор ({head:.1f} м): "
                   f"для этой схемы нужно больше {-correction:g} м, шайба не рассчитывается.")
    elif scheme == "pre_nozzle" and h_dissipated <= 35.0:
        warning = "Диафрагма перед соплом устанавливается при гасимом напоре более 35 м."

    return {
        "diameter_orifice_mm": d_orifice,
        "recommended_standard_diameter": (round(d_orifice * 2.0) / 2.0) if d_orifice is not None else None,
        "flow_g": round(flow, 2),
        "available_head_m": round(head, 2),
        "head_loss_dissipated": round(h_dissipated, 2),
        "scheme": scheme,
        "warning": warning,
    }


def select_elevator_number(neck_mm: float) -> int:
    for number, max_neck in ELEVATOR_NECKS:
        if neck_mm <= max_neck:
            return number
    return 7


def calculate_elevator_parameters(
    *,
    q_heating_gcal: Optional[float] = None,
    flow_g: Optional[float] = None,
    p1: float = 6.0,
    p2: float = 4.0,
    t1: float = 130.0,
    t2: float = 70.0,
    t3: float = 95.0,
    delta_h_system: float = 1.5,
) -> dict[str, Any]:
    """Элеватор: коэффициент смешения, сопло и горловина (drsh2.py), номер по горловине."""
    if not (t1 > t3 > t2):
        raise ValueError("Нужно T1 > T3 > T2 (подача, после смешения, обратка).")
    if delta_h_system <= 0:
        raise ValueError("Потери напора в системе отопления hс должны быть больше нуля.")
    # Коэффициент смешения u = (T1 - T3) / (T3 - T2)
    u = (t1 - t3) / (t3 - t2)
    flow = _resolve_flow(flow_g, q_heating_gcal, None, t1, t2)
    h_avail = _resolve_head(None, p1, p2)

    # Сопло: dc = 9.6 * sqrt(G / sqrt(Нрас)) — полный располагаемый напор, как в drsh2
    dc = max(MIN_ORIFICE_MM, round(9.6 * math.sqrt(flow / math.sqrt(h_avail)), 1))
    # Горловина: dg = 8.5 * sqrt(G * (1 + u) / sqrt(hс)) — Апарцев 7.2
    d_neck = round(8.5 * math.sqrt(flow * (1.0 + u) / math.sqrt(delta_h_system)), 1)
    number = select_elevator_number(d_neck)

    # Требуемый напор перед элеватором ≈ 1.4 * hс * (1 + u)²
    h_required = 1.4 * delta_h_system * (1.0 + u) ** 2
    warnings: list[str] = []
    if d_neck > ELEVATOR_NECKS[-1][1]:
        warnings.append("Горловина больше, чем у элеватора №7: элеваторное смешение "
                        "должно быть заменено на насосное.")
    if h_avail < h_required:
        warnings.append(f"Располагаемый напор {h_avail:.1f} м меньше требуемого "
                        f"{h_required:.1f} м: элеватор не обеспечит смешение.")
    elif h_avail > 2 * h_required:
        warnings.append("Элеватор работает при повышенном напоре: возможны вибрация и шум "
                        "(избыток погасить диафрагмой перед соплом).")

    return {
        "mixing_ratio_u": round(u, 2),
        "nozzle_diameter_mm": dc,
        "mixing_chamber_diameter_mm": d_neck,
        "elevator_number": number,
        "available_head_m": round(h_avail, 2),
        "dissipated_head_m": round(h_avail, 2),
        "required_head_m": round(h_required, 2),
        "flow_g": round(flow, 2),
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "warnings": warnings,
    }


def calculate_throttling_sheet(data: dict[str, Any]) -> dict[str, Any]:
    """Все величины бланка dross.py по исходным данным ввода."""
    t1 = float(data.get("t1") or 130.0)
    t2 = float(data.get("t2") or 70.0)
    q_ot = float(data.get("q_heating_gcal") or 0.0)
    q_v = float(data.get("q_vent_gcal") or 0.0)
    q_gvs_max = float(data.get("q_gvs_gcal") or 0.0)
    if q_ot <= 0 and q_v <= 0 and q_gvs_max <= 0:
        raise ValueError("Укажите хотя бы одну тепловую нагрузку (отопление, вентиляция или ГВС).")
    g_ot = flow_from_load(q_ot, t1, t2)
    g_v = flow_from_load(q_v, t1, t2)
    g_gvs = gvs_flow_from_max_load(q_gvs_max)
    h_ras = _resolve_head(None, data.get("p1"), data.get("p2"))

    def orifice(flow: float, scheme: str) -> Optional[float]:
        coeff, correction = ORIFICE_SCHEMES[scheme]
        return calculate_orifice_diameter(flow_g=flow, delta_h=h_ras + correction, coeff=coeff)

    return {
        "g_ot": g_ot, "g_v": g_v, "g_gvs": g_gvs, "q_gvs_avg": q_gvs_max / 2.4, "h_ras": h_ras,
        "d_bezelevator": orifice(g_ot, "bezelevator"),
        "d_pump_mix": orifice(g_ot, "pump_mix"),
        "d_pre_nozzle": orifice(g_ot, "pre_nozzle"),
        "d_nozzle": orifice(g_ot, "nozzle"),
        "d_ventilation": orifice(g_v, "ventilation"),
        "d_heater": orifice(g_ot, "heater"),
        "d_gvs_circulation": orifice(g_gvs, "gvs_circulation"),
    }


def generate_throttling_excel(data: dict[str, Any]) -> bytes:
    """Бланк расчёта дроссельных устройств теплового ввода (структура gid8/python/dross/dross.py)."""
    calc = calculate_throttling_sheet(data)

    wb = Workbook()
    ws = wb.active
    ws.title = "Расчет диафрагм"

    bold_font = Font(name="Arial", size=10, bold=True)
    regular_font = Font(name="Arial", size=10, bold=False)
    title_font = Font(name="Arial", size=12, bold=True, underline="single")
    fill_input = PatternFill("solid", fgColor="FFF9B1")  # исходные данные
    fill_calc = PatternFill("solid", fgColor="E8F5E9")   # расчётные величины

    for col, width in {"A": 4, "B": 50, "C": 14, "D": 10, "E": 12, "F": 6, "G": 14,
                       "H": 8, "I": 8, "J": 8, "K": 8, "L": 10}.items():
        ws.column_dimensions[col].width = width

    ws.merge_cells("B2:L2")
    ws["B2"] = "РАСЧЕТ ДИАМЕТРОВ ОТВЕРСТИЙ ДРОССЕЛЬНЫХ УСТРОЙСТВ"
    ws["B2"].font = title_font
    ws["B2"].alignment = Alignment(horizontal="center", vertical="center")
    ws.merge_cells("B3:L3")
    ws["B3"] = "ДЛЯ ТЕПЛОВОГО ВВОДА ПОТРЕБИТЕЛЯ"
    ws["B3"].font = title_font
    ws["B3"].alignment = Alignment(horizontal="center", vertical="center")

    def put(cell: str, value: Any, *, font=regular_font, fill=None) -> None:
        ws[cell] = value
        ws[cell].font = font
        if fill is not None:
            ws[cell].fill = fill

    put("B5", "Район:", font=bold_font)
    put("C5", data.get("district") or "", fill=fill_input)
    put("G5", "Участок / ТК:", font=bold_font)
    put("H5", data.get("site_name") or "", fill=fill_input)
    put("B7", "Давление P1 (подача):")
    put("D7", data.get("p1"), fill=fill_input)
    put("E7", "атм")
    put("G7", "Давление P2 (обратка):")
    put("I7", data.get("p2"), fill=fill_input)
    put("J7", "атм")
    put("B9", "Потребитель:", font=bold_font)
    put("C9", data.get("consumer_name") or "", fill=fill_input)
    put("B11", "Адрес:")
    put("C11", data.get("address") or "", fill=fill_input)

    put("B13", "Тепловые нагрузки:", font=bold_font)
    put("B14", "а) на отопление (Qо):")
    put("G14", data.get("q_heating_gcal") or 0.0, fill=fill_input)
    put("L14", "Гкал/ч")
    put("B15", "б) на вентиляцию (Qв):")
    put("G15", data.get("q_vent_gcal") or 0.0, fill=fill_input)
    put("L15", "Гкал/ч")
    put("B16", "в) на ГВС: максимальная (Qгвс.max)")
    put("G16", data.get("q_gvs_gcal") or 0.0, fill=fill_input)
    put("L16", "Гкал/ч")
    put("B17", "                   среднечасовая (Qгвс.ср = Qгвс.max / 2.4)")
    put("G17", round(calc["q_gvs_avg"], 4), fill=fill_calc)
    put("L17", "Гкал/ч")
    put("B18", "Температурный график T1 / T2:", font=bold_font)
    put("G18", f"{data.get('t1', 130)} / {data.get('t2', 70)}", fill=fill_input)
    put("L18", "°С")

    put("B19", "Расходы воды:", font=bold_font)
    rows: list[tuple[str, str, Any, str]] = [
        ("B20", "а) на отопление (Gо):", round(calc["g_ot"], 3), "т/ч"),
        ("B21", "б) на вентиляцию (Gв):", round(calc["g_v"], 3), "т/ч"),
        ("B22", "в) на ГВС (Gгвс):", round(calc["g_gvs"], 3), "т/ч"),
        ("B23", "Располагаемый напор (Нрас):", round(calc["h_ras"], 2), "м"),
    ]
    diaphragms = [
        (24, "Диафрагма безэлеваторного ввода:", calc["h_ras"] - 5, calc["d_bezelevator"],
         "напор после шайбы 5 м", False),
        (27, "Диафрагма перед насосами смешения:", calc["h_ras"] - 2, calc["d_pump_mix"], "", False),
        (30, "Дроссельная диафрагма перед соплом элеватора:", calc["h_ras"], calc["d_pre_nozzle"],
         "устанавливается при гасимом напоре более 35 м", False),
        (33, "Элеватор (сопло):", calc["h_ras"], calc["d_nozzle"], "", True),
        (36, "Дроссельная диафрагма на вентиляцию:", calc["h_ras"] - 5, calc["d_ventilation"], "", False),
        (39, "Дроссельная диафрагма перед водоводяным подогревателем:", calc["h_ras"] - 5,
         calc["d_heater"], "", False),
        (42, "Дроссельная диафрагма на циркуляционную линию г.в.с.:", calc["h_ras"] - 5,
         calc["d_gvs_circulation"], "всегда одна шайба", False),
    ]
    for cell, label, value, unit in rows:
        put(cell, label)
        put("G" + cell[1:], value, fill=fill_calc)
        put("L" + cell[1:], unit)
    for row, title, head, diameter, note, is_nozzle in diaphragms:
        put(f"B{row}", title, font=bold_font)
        put(f"B{row + 1}", "Располагаемый напор (Нрас):" if is_nozzle else "Гасимый напор (Нгас):")
        put(f"G{row + 1}", round(head, 2), fill=fill_calc)
        put(f"L{row + 1}", "м")
        put(f"B{row + 2}", "Диаметр отверстия (Дс):" if is_nozzle else "Диаметр отверстия (Дш):")
        put(f"G{row + 2}", diameter if diameter is not None else "не рассчитывается",
            font=bold_font, fill=fill_calc)
        put(f"L{row + 2}", "мм" if diameter is not None else "")
        if note:
            put(f"N{row + 1}", note)

    ws.merge_cells("B46:L47")
    ws["B46"] = (
        "Примечание: диаметры отверстий дроссельных устройств могут быть скорректированы в "
        "зависимости от параметров теплоносителя на тепловом вводе, при изменении тепловой нагрузки "
        "на отопление и вентиляцию, либо при обосновании необходимости корректировки дроссельных "
        "устройств в акте обследования."
    )
    ws["B46"].font = Font(name="Arial", size=9, italic=True)
    ws["B46"].alignment = Alignment(horizontal="left", vertical="top", wrap_text=True)

    # Подписи — из запроса; по умолчанию пустые строки для заполнения от руки
    signers = data.get("signers") or []
    for i, row in enumerate((50, 52)):
        signer = signers[i] if i < len(signers) else {}
        position = signer.get("position") or "Должность"
        name = signer.get("name") or ""
        put(f"B{row}", f"{position} ______________________ / {name:<20} /")
    if data.get("organization"):
        put("B54", data["organization"])

    # Защита листа с разрешением менять ширину колонок (как в dross.py)
    ws.protection = SheetProtection(sheet=True, formatColumns=False)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------- диафрагмы движка sety (drvary1)
#
# Бланк dross.py считает диафрагмы по формулам ячеек (выше). Движок sety (sety/dross/drvary1.py,
# режимы 1 и 6) считает те же устройства по напорам в узле: шайба drsh3 не меньше минимального
# диаметра, а если меньше — ставится диафрагма минимального диаметра, гасящая 10000·G²/d⁴, и их
# число n = int(Нгас / Н1), но не больше 3 (остаток напора не погашен).


def drsh3(flow: float, min_diameter: float, head: float) -> tuple[bool, float, float]:
    """sety drsh3: (ferr, гасимый напор, диаметр). ferr — диаметр меньше минимального."""
    d = 10.0 * math.sqrt(abs(flow) / math.sqrt(abs(head)))
    if d < min_diameter:
        d = min_diameter
        head = 10000.0 * flow * flow / math.pow(d, 4)
        return True, head, d
    return False, head, d


def _diaphragm_series(flow: float, head: float, min_diameter: float,
                      total_head: Optional[float] = None) -> dict[str, Any]:
    """Одна шайба или цепочка шайб минимального диаметра на гасимый напор head (drvary1).

    head_one_m — напор на одной шайбе (у десктопа это и пишется в dr_out: b22, b25, b31);
    total_head — напор, по которому считается число шайб (по умолчанию head).
    """
    h_total = head if total_head is None else total_head
    ferr, h_one, d = drsh3(flow, min_diameter, head)
    count = 1
    if ferr:
        count = min(int(h_total / h_one), 3)
    return {
        "diameter_mm": round(d, 2),
        "count": count,
        "head_one_m": h_one,
        "head_dissipated_m": h_one * count,
        "head_residual_m": (h_total - count * h_one) if ferr else 0.0,
        "min_diameter_limited": ferr,
        "flow_t_h": flow,
    }


def calculate_gvs_circulation_diaphragm(
    *,
    circulation_flow: float,
    required_head: float,
    circulation_loss: float,
    return_head: float,
    draw_from: str = "supply",
    min_diameter: float = MIN_ORIFICE_MM,
) -> dict[str, Any]:
    """Ограничительная диафрагма в циркуляционной линии открытой ГВС (drvary1: dr_out b39/b40/b41).

    Гасимый напор Нгас = a12 − a11 − Hобр: a12 — расчётный напор на входе водоразборных приборов,
    a11 — потери в циркуляционном трубопроводе, Hобр — пьезометрический напор в обратном
    трубопроводе узла (м). draw_from: «supply» — водоразбор из подающего (ветка fss[6]),
    «return» — из обратного (fss[7]; десктоп в этой ветке пишет гасимый напор одной шайбы без
    умножения на их число, а в b41 — расход на отопление; здесь расход — циркуляционный).
    """
    if circulation_flow <= 0:
        raise ValueError("Укажите расход в циркуляционной линии (рециркуляция) больше нуля.")
    if draw_from not in ("supply", "return"):
        raise ValueError("draw_from: supply или return")
    head = required_head - circulation_loss - return_head
    result: dict[str, Any] = {"available_head_m": head, "draw_from": draw_from, "diameter_mm": None,
                              "count": 0, "head_dissipated_m": None, "flow_t_h": circulation_flow, "warnings": []}
    if head <= 0:
        result["warnings"].append(
            "Не обеспечено заданное значение напора в циркуляционной сети ГВС: расчёт ограничительной "
            "диафрагмы не выполняется.")
        return result
    series = _diaphragm_series(circulation_flow, head, min_diameter)
    if draw_from == "return":
        series["head_dissipated_m"] = series["head_one_m"]
    result.update(series)
    if series["min_diameter_limited"]:
        result["warnings"].append(
            f"Необходимо установить {series['count']} диафрагмы диаметром {min_diameter:g} мм; остаток "
            f"непогашенного напора {series['head_residual_m']:.1f} м.")
        if series["count"] > 1:
            result["warnings"].append(
                "Из практики эксплуатации устанавливается не более одного дросселя диаметром 3 мм.")
    return result


def calculate_elevator_engine(
    *,
    available_head: float,
    heating_flow: float,
    mixing_ratio: float,
    system_loss: float,
    min_nozzle_diameter: float = MIN_ORIFICE_MM,
    min_diameter: float = MIN_ORIFICE_MM,
    regime: int = 1,
    circulation_head: float = 0.0,
    gvs_heater_loss: float = 0.0,
    gvs_sequential_flow: float = 0.0,
    graph_otop: bool = False,
    street_share: float = 1.0,
) -> dict[str, Any]:
    """Элеватор с диафрагмой перед соплом по движку sety (drvary1, элеваторный ввод fss[0] = 1).

    available_head — располагаемый напор узла Нп − Но, м; heating_flow — расход на отопление, т/ч;
    mixing_ratio — коэффициент смешения u (a6); system_loss — потери в системе отопления hс (a7);
    min_nozzle_diameter — a14; min_diameter — минимальная шайба a15; regime — режим расчёта (a13):
    в режиме 6 при напоре > 40 м половину гасит диафрагма перед соплом; circulation_head — напор,
    погашенный подпорно-циркуляционной диафрагмой (b37); gvs_heater_loss — потери в подогревателе
    ГВС 2-й ступени (a23) при последовательной схеме, gvs_sequential_flow — расход ГВС
    последовательной схемы (gvps + gvpw); graph_otop — отопительный график «О» (расход ГВС
    последовательной схемы добавляется к отоплению); street_share — доля уличного фасада.

    Если напор на сопле больше, чем даёт минимальное сопло, избыток гасит диафрагма перед соплом
    (b21, для двух фасадов — b21 и b24; при последовательной ГВС — диафрагма подогревателя b30).
    """
    if heating_flow <= 0:
        raise ValueError("Укажите расход на отопление больше нуля.")
    if system_loss <= 0 or mixing_ratio <= 0:
        raise ValueError("Нужны потери напора в системе отопления и коэффициент смешения элеватора.")
    ho = 1.4 * system_loss * (1.0 + mixing_ratio) ** 2
    hrc = available_head
    if gvs_sequential_flow > 0:
        hrc -= gvs_heater_loss
    hrc -= circulation_head
    otopl = heating_flow + (gvs_sequential_flow if graph_otop else 0.0)
    result: dict[str, Any] = {"required_head_m": ho, "flow_t_h": otopl, "warnings": [], "nozzle_diameter_mm": None,
                              "elevator_number": None, "nozzle_head_m": None, "pre_nozzle": None,
                              "yard_facade": None, "gvs_heater": None}
    if hrc <= 0:
        result["warnings"].append(
            "Не обеспечено заданное значение напора на входе системы отопления: расчёт сопла и "
            "ограничительной диафрагмы не выполняется.")
        return result
    split = False
    if hrc > 40 and regime == 6:
        hrc /= 2
        split = True
    if hrc > 2 * ho:
        result["warnings"].append("Элеватор работает при повышенном напоре. Возможны вибрация и шум.")
    hoost = hrc
    if split:
        lim, h1, d1 = drsh3(otopl, min_diameter, hrc)
        result["pre_nozzle"] = {"diameter_mm": round(d1, 2), "count": 1, "head_one_m": h1, "head_dissipated_m": h1,
                                "head_residual_m": 0.0, "min_diameter_limited": lim, "flow_t_h": otopl,
                                "reason": "режим 6: половина напора > 40 м"}
        hrc = hrc * 2 - h1
    # drsh2: сопло не меньше минимального; горловина и номер элеватора — по потерям системы
    dc = 9.6 * math.sqrt(abs(otopl) / math.sqrt(hrc))
    nozzle_limited = False
    if dc < min_nozzle_diameter:
        dc = min_nozzle_diameter
        hrc = 8493.47 * otopl * otopl / math.pow(dc, 4)
        nozzle_limited = True
    dg = 8.5 * math.sqrt(abs(otopl) * (1.0 + mixing_ratio) / math.sqrt(system_loss))
    result.update({"nozzle_diameter_mm": round(dc, 2), "nozzle_head_m": hrc,
                   "mixing_chamber_diameter_mm": round(dg, 1),
                   "elevator_number": min(7, max(1, select_elevator_number(dg))) if dg > 10 else 0})
    if dg > ELEVATOR_NECKS[-1][1]:
        result["warnings"].append("Диаметр горловины больше, чем у элеватора №7: элеваторное смешение "
                                  "должно быть заменено на насосное.")
    if nozzle_limited:
        excess = hoost - hrc
        if gvs_sequential_flow == 0:
            street = otopl * street_share
            if street != 0:
                s = _diaphragm_series(street, excess, min_diameter)
                s["reason"] = "избыток напора при минимальном сопле"
                result["pre_nozzle"] = s
                excess = s["head_one_m"]  # drvary1: дальше считается от напора одной шайбы (hoost)
            yard = otopl * (1.0 - street_share)
            if yard != 0:
                result["yard_facade"] = _diaphragm_series(yard, excess, min_diameter, total_head=hoost - hrc)
        else:
            s = _diaphragm_series(otopl, excess, min_diameter)
            result["gvs_heater"] = s
    return result
