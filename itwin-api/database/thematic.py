"""Тематические карты участков сети (Smart Mapping, по образцу ArcGIS Online и Felt).

Тема — значение участка из паспорта или из результатов расчётов: диаметр, год прокладки, износ,
нормативные теплопотери, режим последнего гидравлического расчёта фрагмента, тип прокладки.
API отдаёт значения с геометрией участков видимых фрагментов; классы, палитру и легенду строит веб
(utils/thematicStyle.ts) — стиль хранится JSON-ом (database/layer_styles.py).

Значения только читаются: таблицы десктопа (heatpipesections, ut_out) и веба (wear_out, ut_teplo_out)
не меняются. Участки внутренних схем узлов (условные координаты) на карту не идут.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional

from database.net_srid import line_inner_sql, net_srid
from database.ut_out_columns import (MM_WATER_TO_PA, UT_AVAIL_HEAD_END_M, UT_FLOW_TH, UT_PIEZO_HEAD_END_M,
                                     UT_SIGN_SUPPLY, UT_SPEC_LOSS_MM_M, UT_VELOCITY_MS)

MAX_FEATURES = 60000
MAX_FRAGMENTS = 500
COORD_DIGITS = 6  # ~0,1 м — для карты достаточно, ответ вдвое меньше


class ThematicError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


@dataclass(frozen=True)
class Theme:
    key: str
    label: str
    units: str
    # number — числовая шкала (классы); category — уникальные значения справочника
    kind: str
    # откуда значение: passport — паспорт участка; calc — последний гидравлический расчёт фрагмента;
    # wear — последний расчёт износа; heat_losses — последний расчёт нормативных теплопотерь
    source: str
    value_sql: str
    hint: str = ""
    # классификация по умолчанию (веб): equal | quantile | jenks | manual (+ breaks)
    method: str = "quantile"
    breaks: tuple[float, ...] = ()
    palette: str = "sequential"
    digits: int = 0
    # справочник категорий: (таблица, колонка подписи)
    ref: Optional[tuple[str, str]] = None


_UT = "ut"  # строка ut_out подачи последнего расчёта фрагмента

THEMES: dict[str, Theme] = {t.key: t for t in (
    Theme("diameter", "Условный диаметр", "мм", "number", "passport", "NULLIF(h.diametercondit, 0)",
          hint="Ду из паспорта участка", method="manual", breaks=(80, 150, 250, 400, 600, 800), digits=0),
    Theme("year", "Год прокладки (перекладки)", "", "number", "passport",
          "EXTRACT(YEAR FROM COALESCE(h.lasttransdate, h.firstpicdatehp))::float",
          hint="Дата последней перекладки, иначе дата ввода из паспорта", method="equal", palette="sequential_reverse"),
    Theme("wear", "Износ", "%", "number", "wear", "w.wear_pct_known",
          hint="Последний расчёт износа (Анализ → Индекс износа)", method="manual", breaks=(20, 40, 60, 80),
          digits=1),
    Theme("heat_loss", "Нормативные теплопотери (среднегодовые)", "ккал/(ч·м)", "number", "heat_losses", "tl.q",
          hint="Подача + обратка, последний расчёт нормативных теплопотерь", digits=1),
    Theme("available_head", "Располагаемый напор в конце участка", "м", "number", "calc",
          f"{_UT}.{UT_AVAIL_HEAD_END_M}", hint="Последний гидравлический расчёт фрагмента", method="manual",
          breaks=(5, 10, 15, 25, 40), palette="sequential_reverse", digits=1),
    Theme("piezo_head", "Напор подачи в конце участка", "м", "number", "calc", f"{_UT}.{UT_PIEZO_HEAD_END_M}",
          hint="Пьезометрический напор, последний гидравлический расчёт фрагмента", digits=1),
    Theme("velocity", "Скорость воды (подача)", "м/с", "number", "calc", f"abs({_UT}.{UT_VELOCITY_MS})",
          hint="Последний гидравлический расчёт фрагмента", method="manual", breaks=(0.3, 0.8, 1.5, 2.5),
          digits=2),
    Theme("spec_loss", "Удельные потери напора (подача)", "Па/м", "number", "calc",
          f"abs({_UT}.{UT_SPEC_LOSS_MM_M}) * {MM_WATER_TO_PA}",
          hint="Последний гидравлический расчёт фрагмента; норма — до 80 Па/м", method="manual",
          breaks=(20, 50, 80, 150), digits=0),
    Theme("flow", "Расход сетевой воды (подача)", "т/ч", "number", "calc", f"abs({_UT}.{UT_FLOW_TH})",
          hint="Последний гидравлический расчёт фрагмента", method="jenks", digits=1),
    Theme("tubing_type", "Тип прокладки", "", "category", "passport", "h.tubingtypeid",
          hint="Справочник типов прокладки", ref=("tubingtypes", "name")),
)}


def _source_join(source: str, run_param: str) -> str:
    """JOIN значения темы к участку l; run_param — $N расчёта-источника (износ, теплопотери)."""
    if source == "calc":
        return f"LEFT JOIN calc_ut {_UT} ON {_UT}.lineid = l.id"
    if source == "wear":
        return f"LEFT JOIN wear_out w ON w.calculationid = {run_param} AND w.lineid = l.id"
    if source == "heat_losses":
        return f"""
      LEFT JOIN (SELECT lineid, SUM(q) AS q FROM ut_teplo_out WHERE calculationid = {run_param}
                  GROUP BY lineid) tl ON tl.lineid = l.id"""
    return ""


# последний гидравлический расчёт фрагмента — как в слое участков GeoServer (max(calculation.id)); строки
# подачи ut_out отдельно (MATERIALIZED): иначе планировщик соединяет их вложенным циклом — секунды вместо долей
_CALC_CTE = f"""calc AS (SELECT fileid, MAX(id) AS cid FROM calculation
                          WHERE fileid = ANY($1::int[]) GROUP BY fileid),
    calc_ut AS MATERIALIZED (SELECT u.* FROM calc c JOIN ut_out u ON u.calculationid = c.cid
                              AND u.externalsignlineid = {UT_SIGN_SUPPLY}),"""


def themes_payload() -> list[dict[str, Any]]:
    return [{
        "key": t.key, "label": t.label, "units": t.units, "kind": t.kind, "source": t.source, "hint": t.hint,
        "method": t.method, "breaks": list(t.breaks), "palette": t.palette, "digits": t.digits,
    } for t in THEMES.values()]


def get_theme(key: str) -> Theme:
    theme = THEMES.get(key)
    if theme is None:
        raise ThematicError(422, f"Тема — одна из: {', '.join(THEMES)}")
    return theme


def clean_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    """«запад,юг,восток,север» в градусах WGS 84 → кортеж; пусто — без ограничения."""
    if not bbox:
        return None
    try:
        w, s, e, n = (float(v) for v in bbox.split(","))
    except ValueError as exc:
        raise ThematicError(422, "bbox — четыре числа «запад,юг,восток,север»") from exc
    if not (-180 <= w < e <= 180 and -90 <= s < n <= 90):
        raise ThematicError(422, "bbox вне допустимых границ")
    return w, s, e, n


async def _source_run(conn, source: str) -> tuple[Optional[int], Optional[str]]:
    """Расчёт-источник темы: id и подпись (для легенды). Нет расчёта — (None, None)."""
    if source == "wear":
        if not await conn.fetchval("SELECT to_regclass('public.wear_out') IS NOT NULL"):
            return None, None
        row = await conn.fetchrow(
            "SELECT c.id, c.name, c.daterascheta FROM calculation_iznos c"
            " WHERE c.id = (SELECT MAX(calculationid) FROM wear_out)")
        if row is None:
            return None, None
        return row["id"], f"Износ #{row['id']} {row['name'] or ''} от {row['daterascheta']:%d.%m.%Y}".replace("  ", " ")
    if source == "heat_losses":
        if not await conn.fetchval("SELECT to_regclass('public.ut_teplo_out') IS NOT NULL"):
            return None, None
        row = await conn.fetchrow(
            "SELECT c.id, c.name, c.date1 FROM calculation c"
            " WHERE c.id = (SELECT MAX(calculationid) FROM ut_teplo_out)")
        if row is None:
            return None, None
        date = f" от {row['date1']:%d.%m.%Y}" if row["date1"] else ""
        return row["id"], f"Теплопотери #{row['id']} {row['name'] or ''}{date}".replace("  ", " ")
    return None, None


def _round(value: Any, digits: int) -> Optional[float]:
    if value is None:
        return None
    v = float(value)
    return round(v, digits) if digits > 0 else round(v)


async def theme_features(conn, theme_key: str, fragment_ids: list[int], *,
                         bbox: Optional[tuple[float, float, float, float]] = None,
                         limit: int = MAX_FEATURES, with_geometry: bool = True) -> dict[str, Any]:
    """Участки фрагментов со значением темы: GeoJSON (properties: id, fileid, v) и сводка.

    with_geometry=False — без геометрии (сводки для MCP): geometry у объектов — null."""
    theme = get_theme(theme_key)
    ids = sorted({int(f) for f in fragment_ids})
    if not ids:
        raise ThematicError(422, "Выберите хотя бы один фрагмент")
    if len(ids) > MAX_FRAGMENTS:
        raise ThematicError(422, f"Не больше {MAX_FRAGMENTS} фрагментов за раз")

    run_id, run_label = await _source_run(conn, theme.source)
    if theme.source in ("wear", "heat_losses") and run_id is None:
        what = "износа" if theme.source == "wear" else "нормативных теплопотерь"
        raise ThematicError(404, f"Расчёта {what} ещё нет — запустите его, затем постройте тему")

    args: list[Any] = [ids, limit + 1]
    run_param = ""
    if run_id is not None:
        args.append(run_id)
        run_param = f"${len(args)}"
    bbox_sql = ""
    if bbox:
        args += list(bbox)
        n = len(args)
        bbox_sql = (f"AND l.shape && ST_Transform(ST_MakeEnvelope(${n - 3}, ${n - 2}, ${n - 1}, ${n}, 4326), "
                    f"{net_srid()})")
    label_join = label_sql = ""
    if theme.ref:
        table, column = theme.ref
        label_join = f"LEFT JOIN {table} ref ON ref.id = ({theme.value_sql})"
        label_sql = f", ref.{column}::text AS label"
    value_type = "int" if theme.kind == "category" else "float"
    # паспорт участка — самый длинный (как в расчёте износа), участков с несколькими паспортами единицы
    sql = f"""
    WITH {_CALC_CTE if theme.source == "calc" else ""}
    pipes AS (
      SELECT DISTINCT ON (l.id) l.id AS lid, h.id AS hid
        FROM linesobj l JOIN heatpipesections h ON h.lineid = l.id
       WHERE l.removed = 0 AND l.fileid = ANY($1::int[]) AND l.shape IS NOT NULL
         AND {line_inner_sql("l")} IS NULL {bbox_sql}
       ORDER BY l.id, h.pipesectlength DESC NULLS LAST, h.id DESC
       LIMIT $2
    )
    SELECT l.id, l.fileid, ({theme.value_sql})::{value_type} AS v{label_sql},
           {f"ST_AsGeoJSON(ST_Transform(l.shape, 4326), {COORD_DIGITS})" if with_geometry else "NULL"} AS geometry
      FROM pipes p
      JOIN linesobj l ON l.id = p.lid
      JOIN heatpipesections h ON h.id = p.hid
      {_source_join(theme.source, run_param)}
      {label_join}"""
    rows = await conn.fetch(sql, *args)

    truncated = len(rows) > limit
    rows = rows[:limit]
    features = []
    values: list[float] = []
    labels: dict[int, str] = {}
    for r in rows:
        v = r["v"]
        if theme.kind == "number":
            v = _round(v, theme.digits)
            if v is not None:
                values.append(v)
        elif v is not None:
            labels.setdefault(int(v), (r["label"] or f"код {v}").strip())
        geometry = json.loads(r["geometry"]) if r["geometry"] else None
        features.append({"type": "Feature", "id": r["id"], "geometry": geometry,
                         "properties": {"id": r["id"], "fileid": r["fileid"], "v": v}})
    summary: dict[str, Any] = {"count": len(features), "with_value": len(values) if theme.kind == "number"
                               else sum(1 for f in features if f["properties"]["v"] is not None)}
    if values:
        summary.update(min=min(values), max=max(values))
    if theme.kind == "category":
        counts: dict[int, int] = {}
        for f in features:
            v = f["properties"]["v"]
            if v is not None:
                counts[v] = counts.get(v, 0) + 1
        summary["categories"] = [{"value": k, "label": labels[k], "count": n}
                                 for k, n in sorted(counts.items(), key=lambda kv: -kv[1])]
    return {
        "theme": next(t for t in themes_payload() if t["key"] == theme.key),
        "source_run": {"id": run_id, "label": run_label} if run_id else None,
        "summary": summary,
        "truncated": truncated,
        "geojson": {"type": "FeatureCollection", "features": features},
    }
