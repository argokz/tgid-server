from typing import Any, List, Optional
import asyncpg
import io
import json
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

from database.ut_out_columns import (
    UT_AVAIL_HEAD_END_M,
    UT_DIAMETER_MM,
    UT_FLOW_TH,
    UT_LENGTH_M,
    UT_LOSS_TOTAL_M,
    UT_PIEZO_HEAD_END_M,
    UT_SIGN_RETURN,
    UT_SIGN_SUPPLY,
    UT_SPEC_LOSS_MM_M,
    UT_VELOCITY_MS,
    US_PIEZO_HEAD_M,
    US_SIGN_RETURN,
    US_SIGN_SUPPLY,
    US_TEMPERATURE_C,
    spec_loss_pa_per_m,
)

# Пороги раскраски тематической карты
SPEC_LOSS_LIMIT_PA_M = 80.0   # перегруженный по сопротивлению участок
VELOCITY_HIGH_MS = 1.5        # шум, эрозия
VELOCITY_LOW_MS = 0.3         # риск зашламления

# Одна строка на участок: подача (externalsignlineid=2) и обратка (=3) рядом.
_LINE_RESULTS_SQL = f"""
    WITH ids AS (SELECT DISTINCT lineid FROM ut_out WHERE calculationid = $1)
    SELECT
        l.id AS line_id,
        s.{UT_LENGTH_M} AS length_m,
        s.{UT_DIAMETER_MM} AS diameter_mm,
        s.{UT_FLOW_TH} AS flow,
        s.{UT_VELOCITY_MS} AS velocity,
        s.{UT_SPEC_LOSS_MM_M} AS spec_loss_mm_m,
        s.{UT_LOSS_TOTAL_M} AS loss_total,
        s.{UT_PIEZO_HEAD_END_M} AS head_end,
        s.{UT_AVAIL_HEAD_END_M} AS avail_head_end,
        r.{UT_LENGTH_M} AS length_return_m,
        r.{UT_DIAMETER_MM} AS diameter_return_mm,
        r.{UT_FLOW_TH} AS flow_return,
        r.{UT_VELOCITY_MS} AS velocity_return,
        r.{UT_SPEC_LOSS_MM_M} AS spec_loss_return_mm_m,
        r.{UT_LOSS_TOTAL_M} AS loss_total_return,
        r.{UT_PIEZO_HEAD_END_M} AS head_end_return
        {{geometry}}
    FROM ids
    JOIN linesobj l ON l.id = ids.lineid
    LEFT JOIN ut_out s ON s.calculationid = $1 AND s.lineid = ids.lineid
                      AND s.externalsignlineid = {UT_SIGN_SUPPLY}
    LEFT JOIN ut_out r ON r.calculationid = $1 AND r.lineid = ids.lineid
                      AND r.externalsignlineid = {UT_SIGN_RETURN}
    {{where}}
    ORDER BY l.id
"""


def _num(value: Any) -> Optional[float]:
    return float(value) if value is not None else None


def _rounded(value: Optional[float], digits: int) -> Optional[float]:
    return round(value, digits) if value is not None else None


async def get_latest_calculations(conn: asyncpg.Connection, limit: int = 20) -> List[dict[str, Any]]:
    rows = await conn.fetch("""
        SELECT id, name, date1 as calculated_at, fileid
        FROM calculation
        ORDER BY date1 DESC NULLS LAST, id DESC
        LIMIT $1
    """, limit)
    return [dict(row) for row in rows]

async def get_calculation_results_geojson(conn: asyncpg.Connection, calculation_id: int) -> dict[str, Any]:
    # 1. Линейные результаты (ut_out). Раскраска и стрелки — по подаче,
    #    для участков без подачи (только обратка) — по обратке.
    rows = await conn.fetch(
        _LINE_RESULTS_SQL.format(
            geometry=", ST_AsGeoJSON(ST_Transform(l.shape, 4326)) AS geometry",
            where="WHERE l.shape IS NOT NULL",
        ),
        calculation_id,
    )

    features = []
    high_velocity_count = 0
    over_resistance_count = 0

    for row in rows:
        geom = row["geometry"]
        if not geom:
            continue

        has_supply = row["flow"] is not None
        flow = _num(row["flow"] if has_supply else row["flow_return"])
        vel = _num(row["velocity"] if has_supply else row["velocity_return"])
        spec_mm = _num(row["spec_loss_mm_m"] if has_supply else row["spec_loss_return_mm_m"])
        loss_total = _num(row["loss_total"] if has_supply else row["loss_total_return"])
        spec_pa = spec_loss_pa_per_m(spec_mm) if spec_mm is not None else None

        flow_dir = -1 if (flow or 0.0) < 0 else 1
        is_over_res = spec_pa is not None and spec_pa > SPEC_LOSS_LIMIT_PA_M
        if vel is None:
            vel_status = "normal"
        elif vel > VELOCITY_HIGH_MS:
            vel_status = "high"
        elif 0 < vel < VELOCITY_LOW_MS:
            vel_status = "low"
        else:
            vel_status = "normal"

        if is_over_res:
            over_resistance_count += 1
        if vel_status == "high":
            high_velocity_count += 1

        features.append({
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": row["line_id"],
                "kind": "line",
                "label": f"Участок {row['line_id']}",
                "pipe": "supply" if has_supply else "return",
                "length_m": _rounded(_num(row["length_m"] if has_supply else row["length_return_m"]), 1),
                "diameter_mm": _rounded(_num(row["diameter_mm"] if has_supply else row["diameter_return_mm"]), 0),
                "flow": _rounded(flow, 2),
                "flow_return": _rounded(_num(row["flow_return"]), 2),
                "flow_dir": flow_dir,
                "velocity": _rounded(vel, 2),
                "velocity_status": vel_status,
                "pressure_drop": _rounded(loss_total, 3),
                "specific_pressure_drop": _rounded(spec_pa, 1),
                "spec_loss_mm_m": _rounded(spec_mm, 2),
                "is_over_resistance": is_over_res,
                "head_end": _rounded(_num(row["head_end"] if has_supply else row["head_end_return"]), 2),
                "avail_head_end": _rounded(_num(row["avail_head_end"]), 2),
            }
        })

    # 2. Узловые результаты (us_out)
    node_rows = await conn.fetch(f"""
        SELECT
            n.id as node_id,
            COALESCE(NULLIF(n.nodename, ''), NULLIF(n.externalnodename, '')) as label,
            u1.{US_PIEZO_HEAD_M} as h_pod,
            u2.{US_PIEZO_HEAD_M} as h_obr,
            u1.{US_TEMPERATURE_C} as t_pod,
            u2.{US_TEMPERATURE_C} as t_obr,
            ST_AsGeoJSON(ST_Transform(n.shape, 4326)) AS geometry
        FROM nodes n
        LEFT JOIN us_out u1 ON u1.nodeid = n.id AND u1.calculationid = $1 AND u1.externalsign = {US_SIGN_SUPPLY}
        LEFT JOIN us_out u2 ON u2.nodeid = n.id AND u2.calculationid = $1 AND u2.externalsign = {US_SIGN_RETURN}
        WHERE (u1.{US_PIEZO_HEAD_M} IS NOT NULL OR u2.{US_PIEZO_HEAD_M} IS NOT NULL) AND n.shape IS NOT NULL
    """, calculation_id)

    for nrow in node_rows:
        geom = nrow["geometry"]
        if not geom:
            continue
        h_pod = _num(nrow["h_pod"])
        h_obr = _num(nrow["h_obr"])
        # Располагаемый напор есть только там, где считались обе трубы
        delta_h = h_pod - h_obr if h_pod is not None and h_obr is not None else None

        features.append({
            "type": "Feature",
            "geometry": json.loads(geom),
            "properties": {
                "id": nrow["node_id"],
                "kind": "node",
                "label": nrow["label"] or f"Узел {nrow['node_id']}",
                "h_pod": _rounded(h_pod, 2),
                "h_obr": _rounded(h_obr, 2),
                "delta_h": _rounded(delta_h, 2),
                "t_pod": _rounded(_num(nrow["t_pod"]), 1),
                "t_obr": _rounded(_num(nrow["t_obr"]), 1),
            }
        })

    lines_count = len([f for f in features if f["properties"].get("kind") == "line"])
    nodes_count = len([f for f in features if f["properties"].get("kind") == "node"])

    return {
        "type": "FeatureCollection",
        "summary": {
            "calculation_id": calculation_id,
            "lines_count": lines_count,
            "nodes_count": nodes_count,
            "high_velocity_count": high_velocity_count,
            "over_resistance_count": over_resistance_count,
        },
        "features": features
    }

async def get_calculation_results_excel(conn: asyncpg.Connection, calculation_id: int) -> bytes:
    rows = await conn.fetch(
        _LINE_RESULTS_SQL.format(geometry="", where=""),
        calculation_id,
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Расчет #{calculation_id}"

    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")

    headers = [
        "ID участка", "Длина (м)", "Диаметр внутр. (мм)",
        "Расход под. (т/ч)", "Скорость под. (м/с)", "Уд. потери под. (мм/м)",
        "Потери под. (м)", "Пьез. напор в конце под. (м)", "Располаг. напор в конце (м)",
        "Расход обр. (т/ч)", "Скорость обр. (м/с)", "Уд. потери обр. (мм/м)",
        "Потери обр. (м)", "Пьез. напор в конце обр. (м)",
    ]
    ws.append(headers)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in rows:
        ws.append([
            r['line_id'],
            r['length_m'] if r['length_m'] is not None else r['length_return_m'],
            r['diameter_mm'] if r['diameter_mm'] is not None else r['diameter_return_mm'],
            r['flow'], r['velocity'], r['spec_loss_mm_m'],
            r['loss_total'], r['head_end'], r['avail_head_end'],
            r['flow_return'], r['velocity_return'], r['spec_loss_return_mm_m'],
            r['loss_total_return'], r['head_end_return'],
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()
