"""Meaning of the sety result columns in ut_out / us_out.

Source of truth: sety/out/ut_out.py (column comments) and sety/w_out.py
(where the values are computed). Every reader of ut_out must go through
these names instead of hard-coding a7..a21.
"""

# ut_out: one row per (calculationid, lineid, externalsignlineid)
UT_LENGTH_M = "a7"            # Длина участка теплопровода, м
UT_DIAMETER_MM = "a8"         # Внутренний диаметр трубы, мм
UT_VOLUME_M3 = "a9"           # Объём воды на участке, м3
UT_VELOCITY_MS = "a10"        # Скорость потока, м/с
UT_TRAVEL_MIN = "a11"         # Время прохождения потока, мин
UT_RESISTANCE = "a12"         # Полное гидравлическое сопротивление участка (S)
UT_FLOW_TH = "a13"            # Расход сетевой воды, т/ч (знак — направление относительно линии)
UT_SPEC_LOSS_MM_M = "a14"     # Удельные линейные потери напора, мм вод. ст./м
UT_LOSS_LINEAR_M = "a15"      # Линейные потери напора, м
UT_LOSS_LOCAL_M = "a16"       # Местные потери напора, м
UT_LOSS_TOTAL_M = "a17"       # Общие потери напора, м
UT_AVAIL_HEAD_END_M = "a18"   # Располагаемый напор в конечном узле, м
UT_PIEZO_HEAD_END_M = "a19"   # Пьезометрический напор в конечном узле, м
UT_GROUND_END_M = "a20"       # Геодезическая отметка в конечном узле, м
UT_FULL_HEAD_END_M = "a21"    # Полный напор в конечном узле, м

# ut_out.externalsignlineid = po + 1 (sety/out/ut_out.py)
UT_SIGN_SUPPLY = 2
UT_SIGN_RETURN = 3

# us_out: one row per (calculationid, nodeid, externalsign); externalsign = po
US_SIGN_SUPPLY = 1
US_SIGN_RETURN = 2
US_PIEZO_HEAD_M = "pih"       # Пьезометрический напор, м
US_TEMPERATURE_C = "t"        # Температура сетевой воды, °C

MM_WATER_TO_PA = 9.80665      # 1 мм вод. ст. = 9.80665 Па


def spec_loss_pa_per_m(spec_loss_mm_per_m: float) -> float:
    """Удельные потери из ut_out (мм вод. ст./м) в Па/м."""
    return spec_loss_mm_per_m * MM_WATER_TO_PA
