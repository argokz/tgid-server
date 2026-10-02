"""Анализ гидравлического режима по результатам расчёта — меню «Анализ» десктопа (gid6).

Только чтение. Результаты берутся из последнего расчёта фрагмента (calculation.id max по fileid)
или из явно указанного calculation_id.

| запрос               | десктоп (gid6)                          |
|----------------------|-----------------------------------------|
| negative_dp          | Отрицательные перепады (zap.cpp OnZapOtr)      |
| airlock              | Завоздушивание (OnZapZavozd)                   |
| low_temperature      | Низкие температуры (OnPtTempMin)               |
| closed_sections      | Закрытые / отключенные участки (UtZakr)        |
| hydrostatic_zones    | Гидростатические зоны (gidrView.cpp OnZona)    |
| admissibility 1..10  | Анализ режима (OutDialog.cpp, sql/admissibility) |

Напор и температура узла — как в десктопе (mysql.cpp setNodeOut): из us_out по признаку
(1 — подача, 2 — обратка) берётся строка с наибольшим напором; узел связи внутренней схемы
(connectnodes) передаёт свои значения внешнему узлу.
"""

from __future__ import annotations

from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Optional

import asyncpg

ADMISSIBILITY_DIR = Path(__file__).resolve().parents[1] / "sql" / "admissibility"

# gid6 OutDialog.cpp OnAnalizRezhima: название, объект (node/line), колонка режима
ADMISSIBILITY = {
    1: ("Узлы, подающий трубопровод. Анализ напора", "node", "Режим"),
    2: ("Узлы, обратный трубопровод. Анализ напора", "node", "Режим"),
    3: ("Потребители. Анализ располагаемого напора", "node", "Режим"),
    4: ("Потребители. Анализ располагаемого напора на выходе потребителя", "node", "Режим напора потребителя"),
    5: ("Потребители. Анализ теплообеспеченности", "node", "Режим (отд. потреб.)"),
    6: ("Потребители. Анализ теплового режима", "node", "Анализ режима"),
    7: ("Обобщённые потребители. Анализ теплообеспеченности", "node", "Режим"),
    8: ("Обобщённые потребители. Анализ располагаемого напора", "node", None),
    9: ("Обобщённые потребители. Анализ теплового режима", "node", "Анализ режима"),
    10: ("Участки трубопроводов. Анализ потерь напора", "line", None),
}

# Схемы присоединения с независимым подключением: не завоздушиваются (mysql.cpp setNodeCxema)
INDEPENDENT_SCHEME_SUFFIXES = (9, 10, 11, 12)
INDEPENDENT_SCHEMES = ("1.5", "1.6")

_NODE_RESULTS_CTE = """
    node_results AS (
        SELECT DISTINCT ON (k.node_id, u.externalsign)
               k.node_id, u.externalsign, u.pih::float AS pih, u.t::float AS t
          FROM us_out u
          JOIN nodes n ON n.id = u.nodeid
          CROSS JOIN LATERAL (
              SELECT CASE WHEN n.internalnodeid IS NOT NULL
                               AND EXISTS (SELECT 1 FROM connectnodes c WHERE c.nodeid = n.id)
                          THEN n.internalnodeid ELSE n.id END AS node_id
          ) k
         WHERE u.calculationid = $2
         ORDER BY k.node_id, u.externalsign, u.pih DESC NULLS LAST
    )
"""


async def resolve_calculation(
    conn: asyncpg.Connection, fragment_id: int, calculation_id: Optional[int] = None
) -> Optional[asyncpg.Record]:
    if calculation_id:
        return await conn.fetchrow(
            "SELECT id, fileid, tn::float AS tn, date1 FROM calculation WHERE id = $1 AND fileid = $2",
            calculation_id, fragment_id,
        )
    return await conn.fetchrow(
        "SELECT id, fileid, tn::float AS tn, date1 FROM calculation WHERE fileid = $1 ORDER BY id DESC LIMIT 1",
        fragment_id,
    )


def _envelope(key: str, title: str, fragment_id: int, calc, items: list[dict], **extra) -> dict[str, Any]:
    return {
        "query": key,
        "title": title,
        "fragment_id": fragment_id,
        "calculation_id": calc["id"] if calc else None,
        "calculation_date": calc["date1"].isoformat() if calc and calc["date1"] else None,
        "tn": calc["tn"] if calc else None,
        "count": len(items),
        "items": items,
        **extra,
    }


async def attach_coords(conn, items: list[dict], key: str = "node_id") -> list[dict]:
    """Дописывает longitude/latitude (WGS84) для показа на карте: узел — точка на объекте,
    участок (key="line_id") — середина линии."""
    ids = sorted({i[key] for i in items if i.get(key) is not None})
    if not ids:
        return items
    if key.endswith("line_id"):
        sql = """SELECT id, ST_X(p) AS lon, ST_Y(p) AS lat FROM (
                   SELECT id, ST_Transform(ST_LineInterpolatePoint(ST_LineMerge(shape), 0.5), 4326) AS p
                     FROM linesobj WHERE id = ANY($1::int[]) AND GeometryType(ST_LineMerge(shape)) = 'LINESTRING'
                 ) q"""
    else:
        sql = """SELECT id, ST_X(p) AS lon, ST_Y(p) AS lat FROM (
                   SELECT id, ST_Transform(ST_PointOnSurface(shape), 4326) AS p
                     FROM nodes WHERE id = ANY($1::int[]) AND shape IS NOT NULL
                 ) q"""
    coords = {r["id"]: (r["lon"], r["lat"]) for r in await conn.fetch(sql, ids)}
    for i in items:
        lon, lat = coords.get(i.get(key), (None, None))
        i["longitude"], i["latitude"] = lon, lat
    return items


def _no_calculation(key: str, title: str, fragment_id: int) -> dict[str, Any]:
    out = _envelope(key, title, fragment_id, None, [])
    out["note"] = "У фрагмента нет расчёта"
    return out


async def negative_dp(conn, fragment_id: int, calculation_id: Optional[int] = None) -> dict[str, Any]:
    """Узлы, где напор в обратке выше, чем в подаче (оба ненулевые)."""
    title = "Отрицательные перепады"
    calc = await resolve_calculation(conn, fragment_id, calculation_id)
    if not calc:
        return _no_calculation("negative_dp", title, fragment_id)
    rows = await conn.fetch(
        f"""
        WITH {_NODE_RESULTS_CTE}
        SELECT n.id AS node_id, ec.name AS code, n.externalnodename AS name,
               p.pih AS pih_supply, o.pih AS pih_return, (p.pih - o.pih) AS dp
          FROM nodes n
          JOIN node_results p ON p.node_id = n.id AND p.externalsign = 1
          JOIN node_results o ON o.node_id = n.id AND o.externalsign = 2
          LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
         WHERE n.fileid = $1 AND COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL
           AND p.pih < o.pih AND p.pih <> 0 AND o.pih <> 0
         ORDER BY (p.pih - o.pih), n.id
        """,
        fragment_id, calc["id"],
    )
    items = await attach_coords(conn, [dict(r) for r in rows])
    return _envelope("negative_dp", title, fragment_id, calc, items)


def _is_independent_scheme(scheme: Optional[str]) -> bool:
    s = (scheme or "").strip()
    if s in INDEPENDENT_SCHEMES:
        return True
    parts = s.split(".")
    if len(parts) == 2 and parts[1].isdigit():
        return int(parts[1]) in INDEPENDENT_SCHEME_SUFFIXES
    return False


async def airlock(conn, fragment_id: int, calculation_id: Optional[int] = None) -> dict[str, Any]:
    """Потребители с зависимой схемой, у которых напор в подаче ниже высоты здания."""
    title = "Завоздушивание"
    calc = await resolve_calculation(conn, fragment_id, calculation_id)
    if not calc:
        return _no_calculation("airlock", title, fragment_id)
    rows = await conn.fetch(
        f"""
        WITH {_NODE_RESULTS_CTE}
        SELECT n.id AS node_id, ec.name AS code, n.externalnodename AS name, rc.name AS consumer,
               rc.schemenum AS scheme, rc.buildheight::float AS building_height,
               p.pih AS pih_supply, (rc.buildheight - p.pih)::float AS shortfall
          FROM realconsumers rc
          JOIN nodes n ON n.id = rc.nodeid
          JOIN node_results p ON p.node_id = n.id AND p.externalsign = 1
          LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
         WHERE n.fileid = $1 AND COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL
           AND p.pih < rc.buildheight
         ORDER BY (rc.buildheight - p.pih) DESC, n.id
        """,
        fragment_id, calc["id"],
    )
    items = await attach_coords(conn, [dict(r) for r in rows if not _is_independent_scheme(r["scheme"])])
    return _envelope("airlock", title, fragment_id, calc, items,
                     note="Только потребители с результатом расчёта; независимые схемы не учитываются")


def graph_temperature(points: list[tuple[float, float]], tn: float,
                      summer: Optional[float] = None) -> Optional[float]:
    """t2 температурного графика при Tн. points — (tn, t2).
    Выше всей таблицы — летний режим (heatsources.temperdwflowsummer), как в gid6 tg.cpp getTG.
    В десктопе интерполяция без деления на шаг (верна при шаге 1 °C) — здесь честная линейная."""
    if not points:
        return None
    pts = sorted(points)
    if tn > pts[-1][0] and summer is not None:
        return summer
    if tn <= pts[0][0]:
        return pts[0][1]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= tn <= x2:
            return y1 if x2 == x1 else y1 + (y2 - y1) * (tn - x1) / (x2 - x1)
    return pts[-1][1]


async def low_temperature(conn, fragment_id: int, calculation_id: Optional[int] = None) -> dict[str, Any]:
    """Потребители, у которых температура в подаче ниже t2 графика источника при Tн расчёта.
    Отключённые по теплоносителю (нулевые расходы при ненулевой нагрузке) не показываются."""
    title = "Низкие температуры"
    calc = await resolve_calculation(conn, fragment_id, calculation_id)
    if not calc:
        return _no_calculation("low_temperature", title, fragment_id)
    rows = await conn.fetch(
        f"""
        WITH {_NODE_RESULTS_CTE},
        consumers AS (
            SELECT rc.nodeid, rc.name,
                   (COALESCE(rc.calchldep, 0) + COALESCE(rc.calchlindep, 0) + COALESCE(rc.calchlventil, 0)
                    + COALESCE(rc.avghlclosesys, 0) + COALESCE(rc.avghlopensysflow, 0)
                    + COALESCE(rc.avghlopensysret, 0))::float AS load
              FROM realconsumers rc
            UNION ALL
            SELECT gc.nodeid, gc.name,
                   (COALESCE(gc.calchldep, 0) + COALESCE(gc.calchlindep, 0) + COALESCE(gc.calchlparall, 0)
                    + COALESCE(gc.calchlmix, 0) + COALESCE(gc.calchlconseq, 0) + COALESCE(gc.calchlpreon, 0)
                    + COALESCE(gc.calchlventil, 0) + COALESCE(gc.calchlclosesys, 0)
                    + COALESCE(gc.calchlopensysflow, 0) + COALESCE(gc.calchlopensysret, 0))::float
              FROM generalizedconsumers gc
        )
        SELECT n.id AS node_id, ec.name AS code, n.externalnodename AS name, c.name AS consumer,
               ec.heatsourceid AS heat_source_id, p.t AS t_supply, c.load,
               pt.a15::float AS g_closed, pt.a16::float AS g_supply, pt.a17::float AS g_return
          FROM consumers c
          JOIN nodes n ON n.id = c.nodeid
          JOIN node_results p ON p.node_id = n.id AND p.externalsign = 1
          LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
          LEFT JOIN pt_out pt ON pt.nodeid = n.id AND pt.calculationid = $2
         WHERE n.fileid = $1 AND COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL
        """,
        fragment_id, calc["id"],
    )
    sources = sorted({r["heat_source_id"] for r in rows if r["heat_source_id"]})
    graphs: dict[int, list[tuple[float, float]]] = defaultdict(list)
    summer: dict[int, Optional[float]] = {}
    if sources:
        for g in await conn.fetch(
            "SELECT hsourceid, tn::float AS tn, t2::float AS t2 FROM deployedtempgraphs WHERE hsourceid = ANY($1::int[])",
            sources,
        ):
            graphs[g["hsourceid"]].append((g["tn"], g["t2"]))
        for s in await conn.fetch(
            "SELECT id, temperdwflowsummer::float AS t FROM heatsources WHERE id = ANY($1::int[])", sources
        ):
            summer[s["id"]] = s["t"]
    tn = calc["tn"]
    items = []
    for r in rows:
        t2 = graph_temperature(graphs.get(r["heat_source_id"], []), tn, summer.get(r["heat_source_id"]))
        if t2 is None or r["t_supply"] is None or r["t_supply"] >= t2:
            continue
        flows_zero = not any((r["g_closed"], r["g_supply"], r["g_return"]))
        if flows_zero and r["load"]:
            continue  # отключён по теплоносителю
        item = dict(r)
        item["t2_graph"] = round(t2, 2)
        item["no_flow"] = flows_zero  # нулевая нагрузка и нет расхода — в десктопе тоже в списке
        items.append(item)
    items.sort(key=lambda i: (i["t_supply"] - i["t2_graph"], i["node_id"]))
    await attach_coords(conn, items)
    return _envelope("low_temperature", title, fragment_id, calc, items,
                     note=f"Сравнение с t2 графика источника при Tн = {tn:g} °C")


async def closed_sections(conn, fragment_id: int, include_uncalculated: bool = False,
                          calculation_id: Optional[int] = None) -> dict[str, Any]:
    """Закрытые участки (состояние «закрыт» по подаче/обратке, без результата расчёта).
    include_uncalculated — «Отключенные участки»: все участки без результата расчёта."""
    key = "disconnected_sections" if include_uncalculated else "closed_sections"
    title = "Отключенные участки" if include_uncalculated else "Закрытые участки"
    calc = await resolve_calculation(conn, fragment_id, calculation_id)
    rows = await conn.fetch(
        """
        SELECT l.id AS line_id,
               CASE WHEN (hps.pipesectstateidflow = 2 AND l.externalsignlineid IN (1, 2, 4))
                      OR (hps.pipesectstateidret = 2 AND l.externalsignlineid IN (1, 3, 5))
                    THEN 'закр' ELSE '' END AS state,
               ec1.name AS code1, n1.externalnodename AS name1,
               ec2.name AS code2, n2.externalnodename AS name2,
               CASE l.externalsignlineid WHEN 2 THEN 'П' WHEN 3 THEN 'О' WHEN 4 THEN 'П' WHEN 5 THEN 'О' ELSE '' END AS sign,
               hps.pipesectlength::float AS length_m, hps.diameterinternal::float AS diameter_mm,
               hs.sourcename AS heat_source, org.name AS owner
          FROM linesobj l
          JOIN heatpipesections hps ON hps.lineid = l.id
          JOIN nodes n1 ON n1.id = l.nodeid1
          JOIN nodes n2 ON n2.id = l.nodeid2
          LEFT JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
          LEFT JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
          LEFT JOIN heatsources hs ON hs.id = ec1.heatsourceid
          LEFT JOIN organizations org ON org.id = l.organizationid
         WHERE n1.fileid = $1 AND COALESCE(l.removed, 0) = 0 AND n1.internalnodeid IS NULL
           AND NOT EXISTS (SELECT 1 FROM ut_out u WHERE u.lineid = l.id AND u.calculationid = $2)
           AND ($3 OR (hps.pipesectstateidflow = 2 AND l.externalsignlineid IN (1, 2, 4))
                   OR (hps.pipesectstateidret = 2 AND l.externalsignlineid IN (1, 3, 5)))
         ORDER BY l.id
        """,
        fragment_id, calc["id"] if calc else None, include_uncalculated,
    )
    items = await attach_coords(conn, [dict(r) for r in rows], "line_id")
    return _envelope(key, title, fragment_id, calc, items)


async def hydrostatic_zones(conn, fragment_id: int, zone_height_m: float = 60.0) -> dict[str, Any]:
    """Полный и пьезометрический статический напор фрагмента и узлы нижней зоны.
    gid6 OnZona: H = max(отметка верха трубы + высота здания) + 5; нижняя зона — обход от узла
    с минимальной отметкой, пока |отметка(min) − (отметка(u) + высота здания(u))| < 60 м."""
    nodes = await conn.fetch(
        """
        SELECT n.id, ec.name AS code, n.externalnodename AS name,
               n.geomarktoptube::float AS z,
               COALESCE(rc.buildheight, gc.maxbuildingheight, 0)::float AS hz
          FROM nodes n
          LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid
          LEFT JOIN realconsumers rc ON rc.nodeid = n.id
          LEFT JOIN generalizedconsumers gc ON gc.nodeid = n.id
         WHERE n.fileid = $1 AND COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL
           AND n.geomarktoptube > 0  -- 0 — отметка не заполнена
        """,
        fragment_id,
    )
    title = "Гидростатические зоны"
    if not nodes:
        return {"query": "hydrostatic_zones", "title": title, "fragment_id": fragment_id,
                "note": "Нет узлов с заполненной отметкой верха трубы", "items": [], "count": 0}
    info = {r["id"]: r for r in nodes}
    top = max(nodes, key=lambda r: r["z"] + r["hz"])
    low = min(nodes, key=lambda r: r["z"])
    h_max = top["z"] + top["hz"]
    h_min = low["z"]
    adj: dict[int, list[int]] = defaultdict(list)
    for e in await conn.fetch(
        """
        SELECT l.nodeid1, l.nodeid2 FROM linesobj l JOIN nodes n1 ON n1.id = l.nodeid1
         WHERE n1.fileid = $1 AND COALESCE(l.removed, 0) = 0
        """,
        fragment_id,
    ):
        adj[e["nodeid1"]].append(e["nodeid2"])
        adj[e["nodeid2"]].append(e["nodeid1"])
    zone = {low["id"]}
    queue = deque([low["id"]])
    while queue:
        for u in adj.get(queue.popleft(), ()):
            r = info.get(u)
            if r and u not in zone and abs(h_min - (r["z"] + r["hz"])) < zone_height_m:
                zone.add(u)
                queue.append(u)
    items = [{"node_id": i, "code": info[i]["code"], "name": info[i]["name"], "geo_mark": info[i]["z"],
              "building_height": info[i]["hz"]} for i in sorted(zone)]
    await attach_coords(conn, items)
    return {
        "query": "hydrostatic_zones",
        "title": title,
        "fragment_id": fragment_id,
        "full_static_head_m": round(h_max + 5, 2),
        "piezometric_static_head_m": round(h_max + 5 - h_min, 2),
        "min_geo_mark_m": h_min,
        "min_geo_node": {"node_id": low["id"], "code": low["code"], "name": low["name"]},
        "max_level_node": {"node_id": top["id"], "code": top["code"], "name": top["name"],
                           "level_m": h_max},
        "lower_zone_height_m": zone_height_m,
        "count": len(items),
        "items": items,
        "note": "Узлы нижней зоны (items) — как окрашенные зелёным в десктопе",
    }


def admissibility_catalog() -> list[dict[str, Any]]:
    return [{"id": k, "title": v[0], "object": v[1]} for k, v in ADMISSIBILITY.items()]


async def admissibility(conn, query_id: int, fragment_id: int,
                        calculation_id: Optional[int] = None) -> dict[str, Any]:
    """Анализ режима (контроль допустимости) — запросы gid6 sql/admissibility (PostgreSQL).

    Результаты берутся из calculation_id (если указан и принадлежит фрагменту), иначе из
    последнего расчёта фрагмента ($2 = NULL в SQL — MAX(id) по фрагменту)."""
    if query_id not in ADMISSIBILITY:
        raise ValueError(f"Нет запроса анализа режима №{query_id}")
    calc = await resolve_calculation(conn, fragment_id, calculation_id)
    if calculation_id and calc is None:
        raise LookupError(f"Расчёт {calculation_id} не найден для фрагмента {fragment_id}")
    title, obj, mode_column = ADMISSIBILITY[query_id]
    sql = (ADMISSIBILITY_DIR / f"{query_id:02d}.sql").read_text(encoding="utf-8")
    stmt = await conn.prepare(sql)
    columns = [a.name for a in stmt.get_attributes()]
    rows = await stmt.fetch(fragment_id, calculation_id)
    id_col = next((c for c in columns if c.lower() in ("id", "node_id", "id узла")), None)
    items = []
    for r in rows:
        item = {c: r[c] for c in columns}
        if id_col:
            item["_" + ("line_id" if obj == "line" else "node_id")] = r[id_col]
        items.append(item)
    await attach_coords(conn, items, "_line_id" if obj == "line" else "_node_id")
    summary: dict[str, int] = {}
    if mode_column and mode_column in columns:
        for r in rows:
            summary[str(r[mode_column])] = summary.get(str(r[mode_column]), 0) + 1
    return {
        "query": f"admissibility_{query_id}",
        "title": title,
        "object": obj,
        "fragment_id": fragment_id,
        "calculation_id": calc["id"] if calc else None,
        "calculation_date": calc["date1"].isoformat() if calc and calc["date1"] else None,
        "columns": columns,
        "mode_column": mode_column if mode_column in columns else None,
        "summary": summary,
        "count": len(items),
        "items": items,
    }
