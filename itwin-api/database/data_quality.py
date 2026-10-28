"""Качество исходных данных сети: детерминированные проверки (этап 6 ИИ-плана).

Правила — SQL поверх таблиц города; считаются на лету (таблица проблем не нужна: данные правятся,
список должен отражать текущее состояние). Каждое правило: код, подпись, важность, что исправлять
(fix: инструмент веба), запрос на подсчёт и на список с координатами для карты.
Пороги вынесены в константы; источники: QA 30.09 (выбросы нагрузок 711 и 456 565 Гкал/ч,
участки фрагмента 74 с узлами во фрагменте 99, отметки узлов 0/1 м, нагрузки без источника).
"""

from __future__ import annotations

from typing import Any, Optional

# Нагрузка одного потребителя больше этого — скорее всего неверные единицы (ккал/ч вместо Гкал/ч)
CONSUMER_LOAD_MAX_GCAL_H = 50.0
# Отметка земли/верха трубы не больше этого — не заполнена (Алматы 600–1000 м)
LOW_ELEVATION_M = 1.0
# Длина участка отличается от геометрии больше чем на эту долю
LENGTH_MISMATCH_RATIO = 0.5
# Стандартные условные диаметры, мм (ГОСТ 28338 + типовые для теплосетей)
STANDARD_DN = (15, 20, 25, 32, 40, 50, 65, 70, 80, 100, 125, 150, 175, 200, 250, 300, 350, 400, 450, 500, 600, 700,
               800, 900, 1000, 1200, 1400)

_LOAD_SUM = ("COALESCE(c.calchldep,0)+COALESCE(c.calchlindep,0)+COALESCE(c.calchlventil,0)+COALESCE(c.calchlgvsparall,0)"
             "+COALESCE(c.calchlgvsmix,0)+COALESCE(c.calchlgvsconseq,0)+COALESCE(c.calchlgvspreon,0)"
             "+COALESCE(c.calchlopensysflow,0)+COALESCE(c.calchlclosesys,0)")

_NODE_GEOM = "ST_X(ST_Transform(n.shape, 4326)) AS longitude, ST_Y(ST_Transform(n.shape, 4326)) AS latitude"
_LINE_GEOM = ("ST_X(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS longitude,"
              " ST_Y(ST_Transform(ST_PointOnSurface(l.shape), 4326)) AS latitude")

# Каждое правило: sql — тело FROM … WHERE (без SELECT), с $1 — фрагмент (NULL = все);
# select — список полей для списка; order — сортировка; kind — объект для карточки.
RULES: dict[str, dict[str, Any]] = {
    "consumer_load_outlier": {
        "label": "Нагрузка потребителя больше %.0f Гкал/ч (неверные единицы?)" % CONSUMER_LOAD_MAX_GCAL_H,
        "severity": "error", "kind": "consumer", "fix": "card",
        "select": f"c.id, c.name, c.nodeid AS node_id, n.fileid AS fragment_id, ({_LOAD_SUM}) AS value, 'generalized' AS consumer_type, {_NODE_GEOM}",
        "sql": f"FROM generalizedconsumers c JOIN nodes n ON n.id = c.nodeid WHERE ({_LOAD_SUM}) > {CONSUMER_LOAD_MAX_GCAL_H}"
               " AND ($1::int IS NULL OR n.fileid = $1)",
        "order": "value DESC",
    },
    "line_node_fragment_mismatch": {
        "label": "Участок и его узлы в разных фрагментах",
        "severity": "error", "kind": "line", "fix": "topology",
        "select": "l.id, l.fileid AS fragment_id, n1.fileid AS node1_fragment, n2.fileid AS node2_fragment, "
                  f"n1.externalnodename AS node1, n2.externalnodename AS node2, {_LINE_GEOM}",
        "sql": "FROM linesobj l JOIN nodes n1 ON n1.id = l.nodeid1 JOIN nodes n2 ON n2.id = l.nodeid2"
               " WHERE l.removed = 0 AND (n1.fileid <> l.fileid OR n2.fileid <> l.fileid)"
               " AND ($1::int IS NULL OR l.fileid = $1)",
        "order": "l.fileid, l.id",
    },
    "dangling_node": {
        "label": "Узел без участков",
        "severity": "warning", "kind": "node", "fix": "topology",
        "select": f"n.id, n.externalnodename AS name, n.fileid AS fragment_id, {_NODE_GEOM}",
        "sql": "FROM nodes n WHERE n.removed = 0 AND n.internalnodeid IS NULL AND n.shape IS NOT NULL"
               " AND NOT EXISTS (SELECT 1 FROM linesobj l WHERE l.removed = 0 AND (l.nodeid1 = n.id OR l.nodeid2 = n.id))"
               " AND ($1::int IS NULL OR n.fileid = $1)",
        "order": "n.fileid, n.id",
    },
    "node_low_elevation": {
        "label": "Отметка узла не заполнена (≤ %.0f м)" % LOW_ELEVATION_M,
        "severity": "warning", "kind": "node", "fix": "card",
        "select": f"n.id, n.externalnodename AS name, n.fileid AS fragment_id, n.geomarktoptube AS value, {_NODE_GEOM}",
        "sql": f"FROM nodes n WHERE n.removed = 0 AND n.internalnodeid IS NULL AND COALESCE(n.geomarktoptube, 0) <= {LOW_ELEVATION_M}"
               " AND n.shape IS NOT NULL AND ($1::int IS NULL OR n.fileid = $1)",
        "order": "n.fileid, n.id",
    },
    "line_length_mismatch": {
        "label": "Длина участка расходится с геометрией больше чем на %d %%" % int(LENGTH_MISMATCH_RATIO * 100),
        "severity": "warning", "kind": "line", "fix": "card",
        "select": "l.id, l.fileid AS fragment_id, h.pipesectlength AS value, ST_Length(l.shape) AS geometry_length, "
                  f"{_LINE_GEOM}",
        "sql": "FROM heatpipesections h JOIN linesobj l ON l.id = h.lineid WHERE l.removed = 0 AND l.shape IS NOT NULL"
               f" AND h.pipesectlength > 0 AND ABS(ST_Length(l.shape) - h.pipesectlength) / h.pipesectlength > {LENGTH_MISMATCH_RATIO}"
               " AND ($1::int IS NULL OR l.fileid = $1)",
        "order": "ABS(ST_Length(l.shape) - h.pipesectlength) DESC",
    },
    "diameter_nonstandard": {
        "label": "Условный диаметр вне стандартного ряда",
        "severity": "warning", "kind": "line", "fix": "card",
        "select": f"l.id, l.fileid AS fragment_id, h.diametercondit AS value, {_LINE_GEOM}",
        "sql": "FROM heatpipesections h JOIN linesobj l ON l.id = h.lineid WHERE l.removed = 0"
               f" AND h.diametercondit IS NOT NULL AND h.diametercondit NOT IN ({', '.join(str(d) for d in STANDARD_DN)})"
               " AND ($1::int IS NULL OR l.fileid = $1)",
        "order": "h.diametercondit DESC",
    },
    "line_no_laid_date": {
        "label": "Нет даты прокладки участка",
        "severity": "info", "kind": "line", "fix": "card",
        "select": f"l.id, l.fileid AS fragment_id, {_LINE_GEOM}",
        "sql": "FROM heatpipesections h JOIN linesobj l ON l.id = h.lineid WHERE l.removed = 0 AND l.shape IS NOT NULL"
               " AND h.firstpicdatehp IS NULL AND h.lasttransdate IS NULL AND ($1::int IS NULL OR l.fileid = $1)",
        "order": "l.fileid, l.id",
    },
    # Задвижка на линии без узлов расчётной схемы не видна графу сети: изоляция (mincut) идёт сквозь
    # это место. В копии Алматы 28.10 таких 11,8 тыс. из 12,1 тыс. — линии без геометрии и узлов.
    "valve_outside_network": {
        "label": "Задвижка на участке без узлов расчётной схемы (в локализации аварий не участвует)",
        "severity": "info", "kind": "line", "fix": "topology",
        # без геометрии координаты NULL — строка есть в списке, на карте точки нет
        "select": f"l.id, d.id AS valve_id, d.name, l.fileid AS fragment_id, {_LINE_GEOM}",
        "sql": "FROM dampers d JOIN linesobj l ON l.id = d.lineid WHERE COALESCE(l.removed, 0) = 0"
               " AND l.internalnodeid IS NULL AND (l.nodeid1 IS NULL OR l.nodeid2 IS NULL)"
               " AND ($1::int IS NULL OR l.fileid = $1)",
        "order": "(l.shape IS NULL), l.fileid, d.id",
    },
    "contract_load_without_source": {
        "label": "Договорная нагрузка без источника тепла (АЛСЕКО: организации и жильё)",
        "severity": "info", "kind": "contract", "fix": "alseko",
        "select": "q.id, q.kind, q.name, q.value",
        "sql": "FROM (SELECT o.id, 'organizatsii' AS kind, o.naimenovanie_obekta AS name,"
               " (COALESCE(o.nagruzka__otoplenie_,0)+COALESCE(o.nagruzka__ventilyatsiya_,0)+COALESCE(o.nagruzka__gvs_,0))/1e6 AS value"
               " FROM organizatsii o WHERE o.istochnik_tepla IS NULL OR BTRIM(o.istochnik_tepla) = ''"
               " UNION ALL SELECT z.id, 'zhile', z.adres, (COALESCE(z.nagruzka_otoplenie,0)+COALESCE(z.nagruzka_gvs,0))/1e6"
               " FROM zhile z WHERE z.istochnik_tepla IS NULL OR BTRIM(z.istochnik_tepla) = '') q WHERE $1::int IS NULL",
        "order": "q.value DESC NULLS LAST",
        "sum": True,
    },
}
FIX_LABELS = {"card": "Карточка объекта / групповые установщики", "topology": "Редактор топологии / диагностика топологии",
              "alseko": "АЛСЕКО: сверка и привязка"}


def rule_specs() -> list[dict[str, Any]]:
    return [{"rule": k, "label": v["label"], "severity": v["severity"], "kind": v["kind"], "fix": v["fix"],
             "fix_label": FIX_LABELS.get(v["fix"], v["fix"])} for k, v in RULES.items()]


async def _safe_count(conn, rule: dict[str, Any], fragment_id: Optional[int]) -> tuple[Optional[int], Optional[float], Optional[str]]:
    try:
        if rule.get("sum"):
            row = await conn.fetchrow(f"SELECT COUNT(*) AS n, SUM(q.value) AS s FROM (SELECT {rule['select']} {rule['sql']}) q", fragment_id)
            return int(row["n"] or 0), float(row["s"] or 0), None
        n = await conn.fetchval(f"SELECT COUNT(*) {rule['sql']}", fragment_id)
        return int(n or 0), None, None
    except Exception as exc:  # noqa: BLE001 — нет таблицы/колонки в базе этого города
        return None, None, f"{exc.__class__.__name__}"


async def summary(conn, *, fragment_id: Optional[int] = None) -> dict[str, Any]:
    items = []
    for key, rule in RULES.items():
        n, total, err = await _safe_count(conn, rule, fragment_id)
        items.append({"rule": key, "label": rule["label"], "severity": rule["severity"], "kind": rule["kind"],
                      "fix": rule["fix"], "fix_label": FIX_LABELS.get(rule["fix"], rule["fix"]),
                      "count": n, "sum_gcal_h": round(total, 2) if total is not None else None,
                      "error": err})
    return {"fragment_id": fragment_id, "items": items,
            "total_errors": sum(i["count"] or 0 for i in items if i["severity"] == "error"),
            "total_warnings": sum(i["count"] or 0 for i in items if i["severity"] == "warning")}


async def issues(conn, rule_key: str, *, fragment_id: Optional[int] = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    rule = RULES.get(rule_key)
    if not rule:
        raise KeyError(rule_key)
    total = await conn.fetchval(f"SELECT COUNT(*) {rule['sql']}", fragment_id)
    rows = await conn.fetch(f"SELECT {rule['select']} {rule['sql']} ORDER BY {rule['order']} LIMIT $2 OFFSET $3",
                            fragment_id, limit, offset)
    return {"rule": rule_key, "label": rule["label"], "severity": rule["severity"], "kind": rule["kind"], "fix": rule["fix"],
            "total": int(total or 0), "items": [dict(r) for r in rows]}


async def geojson(conn, rule_key: str, *, fragment_id: Optional[int] = None, limit: int = 5000) -> dict[str, Any]:
    data = await issues(conn, rule_key, fragment_id=fragment_id, limit=limit)
    features = []
    for it in data["items"]:
        lon, lat = it.get("longitude"), it.get("latitude")
        if lon is None or lat is None:
            continue
        props = {k: v for k, v in it.items() if k not in ("longitude", "latitude")}
        props["rule"] = rule_key
        features.append({"type": "Feature", "id": it.get("id"), "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": props})
    return {"type": "FeatureCollection", "features": features, "total": data["total"]}
