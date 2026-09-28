"""Пьезометрический график: путь по графу сети и данные узлов.

Как в десктопе (cxema/graph2.cpp): маршрут задаётся последовательностью узлов
(waypoints). Между соседними точками строится кратчайший путь, что позволяет
направить трассу через нужные участки, а не только «старт → финиш».

Паритет с gid8/gid8/pjezo (этап 10):
- двойной пьезометр (CPjezo::onDouble): тот же маршрут, второй расчёт (выбор из последних
  расчётов фрагмента) — его напоры подачи/обратки рисуются на том же графике;
- статика (m_stat): горизонталь H = max(отметка верха трубы + высота здания) + 5 м по узлам
  схемы (как regime_queries.hydrostatic_zones / gid6 OnZona);
- сохранённые направления (GidWidget::savePjezo / onListPjezo): таблицы десктопа
  directions(id, name, fileid) и deployeddirections(directionid, nodeid) — хранятся опорные
  узлы (list_pjezo_min), путь между ними строится заново.
"""

import io
import time
from typing import Annotated, Optional

import networkx as nx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app_logging import get_logger
from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database.connect import get_pool
from database.piezo_excel import generate_piezometer_excel
from database.ut_out_columns import (
    US_PIEZO_HEAD_M,
    US_SIGN_RETURN,
    US_SIGN_SUPPLY,
    US_TEMPERATURE_C,
    UT_DIAMETER_MM,
    UT_FLOW_TH,
    UT_LENGTH_M,
    UT_LOSS_LINEAR_M,
    UT_LOSS_LOCAL_M,
    UT_LOSS_TOTAL_M,
    UT_SIGN_RETURN,
    UT_SIGN_SUPPLY,
    UT_SPEC_LOSS_MM_M,
    UT_VELOCITY_MS,
)

logger = get_logger(__name__)

router = APIRouter(tags=["piezometer"])

# Каждая пара соседних точек — отдельный поиск пути и запросы к БД
MAX_WAYPOINTS = 200

_piezo_cached_graph = None
_piezo_cached_graph_time = 0.0


async def _get_topology_graph(conn):
    global _piezo_cached_graph, _piezo_cached_graph_time
    now = time.time()
    if _piezo_cached_graph is not None and (now - _piezo_cached_graph_time) < 60.0:
        return _piezo_cached_graph

    q_lines = '''
        SELECT L.id, L.nodeid1, L.nodeid2, COALESCE(HPS.pipesectlength, 10.0) as length
        FROM linesobj L
        LEFT JOIN heatpipesections HPS ON HPS.lineid = L.id
        WHERE L.nodeid1 IS NOT NULL AND L.nodeid2 IS NOT NULL AND COALESCE(L.removed, 0) = 0
    '''
    lines = await conn.fetch(q_lines)
    G = nx.Graph()
    for row in lines:
        # При параллельных рёбрах оставляем самое короткое
        prev = G.get_edge_data(row['nodeid1'], row['nodeid2'])
        if prev is None or row['length'] < prev.get('weight', 1e18):
            G.add_edge(row['nodeid1'], row['nodeid2'], id=row['id'], weight=row['length'])

    _piezo_cached_graph = G
    _piezo_cached_graph_time = now
    return G


def invalidate_topology_cache():
    global _piezo_cached_graph
    _piezo_cached_graph = None


def _build_route(G: nx.Graph, waypoints: list[int]) -> list[int]:
    """Кратчайший путь, проходящий через все waypoints по порядку."""
    for node in waypoints:
        if node not in G:
            raise HTTPException(status_code=404, detail=f"Узел {node} не найден в графе сети.")

    full_path: list[int] = []
    for i in range(len(waypoints) - 1):
        try:
            segment = nx.shortest_path(G, source=waypoints[i], target=waypoints[i + 1], weight='weight')
        except nx.NetworkXNoPath:
            raise HTTPException(
                status_code=404,
                detail=f"Нет пути между узлами {waypoints[i]} и {waypoints[i + 1]}.",
            )
        # Стыкуем сегменты, не дублируя общий узел
        full_path.extend(segment if i == 0 else segment[1:])
    return full_path


async def _route_calculation_id(conn, path_nodes: list[int], calculation_id: Optional[int]) -> Optional[int]:
    """Один расчёт на весь маршрут: заданный или последний, в котором есть узлы маршрута.

    Раньше для каждого узла и участка брался свой последний расчёт, и на одном графике
    смешивались разные расчёты.
    """
    if calculation_id is not None:
        return calculation_id
    return await conn.fetchval(
        "SELECT max(calculationid) FROM us_out WHERE nodeid = ANY($1::int[])", path_nodes
    )


async def _assemble_path_data(conn, G: nx.Graph, path_nodes: list[int],
                              calculation_id: Optional[int] = None) -> list[dict]:
    """Собирает по узлам пути: расстояние, отметку, напоры, температуры, координаты.

    Напоры и температуры — ровно us_out выбранного расчёта (sety/out/us_out.py: pih —
    напор над отметкой, t — температура сетевой воды), пьезометрический напор = z + pih.
    nodes.calcpressflow/calcpressret — ИЗМЕРЕННЫЕ давления (gid8 new_baza/baza.sql, pP_fact),
    по умолчанию 0; они отдаются отдельно (h_pod_meas/h_obr_meas) и расчёт не подменяют.
    """
    q_nodes = f"""
        SELECT
            n.id,
            n.geomarktoptube,
            NULLIF(n.calcpressflow, 0) AS meas_pod,
            NULLIF(n.calcpressret, 0) AS meas_obr,
            COALESCE(NULLIF(n.nodename, ''), NULLIF(n.externalnodename, ''), n.id::text) AS label,
            CASE WHEN n.shape IS NULL THEN NULL
                 ELSE ST_X(ST_Transform(n.shape, 4326)) END AS lng,
            CASE WHEN n.shape IS NULL THEN NULL
                 ELSE ST_Y(ST_Transform(n.shape, 4326)) END AS lat,
            COALESCE(us1.{US_TEMPERATURE_C}, pt.t1) AS t_pod,
            COALESCE(us2.{US_TEMPERATURE_C}, pt.t2) AS t_obr,
            us1.{US_PIEZO_HEAD_M} AS pih_pod,
            us2.{US_PIEZO_HEAD_M} AS pih_obr
        FROM nodes n
        LEFT JOIN us_out us1 ON us1.nodeid = n.id AND us1.calculationid = $2
                            AND us1.externalsign = {US_SIGN_SUPPLY}
        LEFT JOIN us_out us2 ON us2.nodeid = n.id AND us2.calculationid = $2
                            AND us2.externalsign = {US_SIGN_RETURN}
        LEFT JOIN LATERAL (
            SELECT t1, t2 FROM pt_out WHERE nodeid = n.id AND calculationid = $2
            ORDER BY id LIMIT 1
        ) pt ON true
        WHERE n.id = ANY($1::int[])
    """
    rows = await conn.fetch(q_nodes, path_nodes, calculation_id)
    attrs_map = {r['id']: r for r in rows}

    def head(z: float, pressure) -> Optional[float]:
        return z + float(pressure) if pressure is not None else None

    path_data: list[dict] = []
    cum_dist = 0.0
    for i, n_id in enumerate(path_nodes):
        if i > 0:
            edge = G.get_edge_data(path_nodes[i - 1], n_id)
            cum_dist += float(edge.get('weight', 0.0)) if edge else 0.0

        attrs = attrs_map.get(n_id)
        item: dict = {"node_id": n_id, "distance": round(cum_dist, 2)}
        if attrs:
            z = float(attrs['geomarktoptube'] or 0.0)
            item.update({
                "label": attrs['label'],
                "z": z,
                # Пьезометрический напор = отметка + напор us_out; None если расчёта нет
                "h_pod": head(z, attrs['pih_pod']),
                "h_obr": head(z, attrs['pih_obr']),
                "h_pod_meas": head(z, attrs['meas_pod']),
                "h_obr_meas": head(z, attrs['meas_obr']),
                "t_pod": float(attrs['t_pod']) if attrs['t_pod'] is not None else None,
                "t_obr": float(attrs['t_obr']) if attrs['t_obr'] is not None else None,
                "lng": float(attrs['lng']) if attrs['lng'] is not None else None,
                "lat": float(attrs['lat']) if attrs['lat'] is not None else None,
            })
        else:
            item.update({"label": str(n_id), "z": 0.0, "h_pod": None, "h_obr": None,
                         "h_pod_meas": None, "h_obr_meas": None,
                         "t_pod": None, "t_obr": None, "lng": None, "lat": None})
        path_data.append(item)
    return path_data


def _has_calc(path_data: list[dict], suffix: str = "") -> bool:
    return any(i.get("h_pod" + suffix) is not None or i.get("h_obr" + suffix) is not None for i in path_data)


# Запас над самым высоким зданием (gid8 Pjezo.cpp: h_max + 5; gid6 OnZona)
STATIC_RESERVE_M = 5.0


async def _route_fragments(conn, path_nodes: list[int]) -> list[int]:
    rows = await conn.fetch(
        "SELECT DISTINCT fileid FROM nodes WHERE id = ANY($1::int[]) AND fileid IS NOT NULL ORDER BY fileid",
        path_nodes,
    )
    return [r["fileid"] for r in rows]


async def _static_head(conn, fragment_ids: list[int]) -> Optional[dict]:
    """Статический напор схемы: max(z + высота здания) + 5 м по узлам фрагментов маршрута.

    В десктопе максимум берётся по всей открытой схеме (m_graph), здесь — по фрагментам, через
    которые проходит маршрут. Узлы с отметкой 0 (не заполнена) пропускаются, как в
    hydrostatic_zones. Высота здания — realconsumers.buildheight или
    generalizedconsumers.maxbuildingheight (gid8 sql3/us.sql, колонка hz).
    """
    if not fragment_ids:
        return None
    row = await conn.fetchrow(
        """
        SELECT n.id, COALESCE(NULLIF(n.nodename, ''), NULLIF(n.externalnodename, ''), n.id::text) AS label,
               n.geomarktoptube::float AS z,
               COALESCE(rc.buildheight, gc.maxbuildingheight, 0)::float AS hz
          FROM nodes n
          LEFT JOIN realconsumers rc ON rc.nodeid = n.id
          LEFT JOIN generalizedconsumers gc ON gc.nodeid = n.id
         WHERE n.fileid = ANY($1::int[]) AND COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL
           AND n.geomarktoptube > 0
         ORDER BY n.geomarktoptube + COALESCE(rc.buildheight, gc.maxbuildingheight, 0) DESC, n.id
         LIMIT 1
        """,
        fragment_ids,
    )
    if row is None:
        return None
    top = row["z"] + row["hz"]
    return {
        "value": round(top + STATIC_RESERVE_M, 2),
        "reserve_m": STATIC_RESERVE_M,
        "node_id": row["id"],
        "label": row["label"],
        "z": row["z"],
        "building_height": row["hz"],
        "fragment_ids": fragment_ids,
    }


async def _attach_second_calc(conn, path_data: list[dict], calculation_id: int) -> None:
    """Двойной пьезометр: напоры второго расчёта на тех же узлах (h_pod_2 / h_obr_2)."""
    rows = await conn.fetch(
        f"""
        SELECT nodeid, externalsign, {US_PIEZO_HEAD_M} AS pih FROM us_out
         WHERE calculationid = $2 AND nodeid = ANY($1::int[])
           AND externalsign IN ({US_SIGN_SUPPLY}, {US_SIGN_RETURN})
        """,
        [p["node_id"] for p in path_data], calculation_id,
    )
    heads: dict[tuple[int, int], float] = {}
    for r in rows:
        if r["pih"] is not None:
            heads.setdefault((r["nodeid"], r["externalsign"]), float(r["pih"]))
    for p in path_data:
        z = float(p.get("z") or 0.0)
        pod = heads.get((p["node_id"], US_SIGN_SUPPLY))
        obr = heads.get((p["node_id"], US_SIGN_RETURN))
        p["h_pod_2"] = z + pod if pod is not None else None
        p["h_obr_2"] = z + obr if obr is not None else None


async def _check_calculation(conn, calculation_id: Optional[int]) -> None:
    if calculation_id is not None and not await conn.fetchval(
        "SELECT 1 FROM calculation WHERE id = $1", calculation_id
    ):
        raise HTTPException(status_code=404, detail=f"Расчёт {calculation_id} не найден")


@router.get("/piezometer/path")
async def get_piezometer_path(start: int, end: int, calculation_id: Optional[int] = Query(None, ge=1)):
    """Кратчайший путь между двумя узлами (обратная совместимость)."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)
            path_nodes = _build_route(G, [start, end])
            cid = await _route_calculation_id(conn, path_nodes, calculation_id)
            path_data = await _assemble_path_data(conn, G, path_nodes, cid)
            return {"path": path_data, "calculation_id": cid}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching piezometer path: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class RouteRequest(BaseModel):
    nodes: list[int] = Field(..., min_length=2, max_length=MAX_WAYPOINTS, description="Последовательность узлов маршрута")
    calculation_id: Optional[int] = Field(None, ge=1, description="Расчёт; по умолчанию последний, где есть узлы маршрута")
    calculation_id_2: Optional[int] = Field(None, ge=1, description="Второй расчёт — двойной пьезометр")


@router.post("/piezometer/route")
async def build_piezometer_route(body: RouteRequest):
    """Маршрут через последовательность узлов (waypoints), как выделение направления в десктопе."""
    pool = get_pool()
    try:
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)
            path_nodes = _build_route(G, body.nodes)
            await _check_calculation(conn, body.calculation_id_2)
            cid = await _route_calculation_id(conn, path_nodes, body.calculation_id)
            path_data = await _assemble_path_data(conn, G, path_nodes, cid)
            if body.calculation_id_2 is not None:
                await _attach_second_calc(conn, path_data, body.calculation_id_2)
            fragment_ids = await _route_fragments(conn, path_nodes)
            total_length = path_data[-1]["distance"] if path_data else 0.0
            return {
                "path": path_data,
                "calculation_id": cid,
                "calculation_id_2": body.calculation_id_2,
                "waypoints": body.nodes,
                "node_count": len(path_data),
                "total_length": total_length,
                "has_calculation": _has_calc(path_data),
                "has_calculation_2": _has_calc(path_data, "_2") if body.calculation_id_2 else False,
                "fragment_ids": fragment_ids,
                "static_head": await _static_head(conn, fragment_ids),
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building piezometer route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class PiezometerExcelRequest(BaseModel):
    waypoints: Optional[list[int]] = None
    nodes: Optional[list[int]] = None
    calculation_id: Optional[int] = Field(None, ge=1)
    calculation_id_2: Optional[int] = Field(None, ge=1, description="Второй расчёт (двойной пьезометр)")
    include_static: bool = Field(True, description="Колонка/линия статического напора")

    @property
    def target_nodes(self) -> list[int]:
        res = self.waypoints or self.nodes or []
        if len(res) < 2:
            raise ValueError("Необходимо указать минимум 2 узла для построения профиля.")
        if len(res) > MAX_WAYPOINTS:
            raise ValueError(f"Слишком много узлов маршрута (максимум {MAX_WAYPOINTS}).")
        return res


@router.post("/api/piezometer/excel")
@router.post("/piezometer/excel")
async def api_download_piezometer_excel(body: PiezometerExcelRequest):
    """Экспорт пьезометрического профиля и технологической таблицы в Excel (openpyxl)."""
    pool = get_pool()
    try:
        nodes = body.target_nodes
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        async with pool.acquire() as conn:
            G = await _get_topology_graph(conn)
            path_nodes = _build_route(G, nodes)
            await _check_calculation(conn, body.calculation_id_2)
            cid = await _route_calculation_id(conn, path_nodes, body.calculation_id)
            path_data = await _assemble_path_data(conn, G, path_nodes, cid)
            if body.calculation_id_2 is not None:
                await _attach_second_calc(conn, path_data, body.calculation_id_2)
            static = None
            if body.include_static:
                static = await _static_head(conn, await _route_fragments(conn, path_nodes))

            # Собираем данные по сегментам (трубопроводам) между последовательными узлами пути
            segment_details = []
            cum_dist = 0.0

            # Подача и обратка участка из того же расчёта, что и узлы маршрута
            q_edge = f"""
                SELECT
                    l.id as line_id,
                    COALESCE(hps.pipesectlength, s.{UT_LENGTH_M}, r.{UT_LENGTH_M}, 10.0) as length,
                    COALESCE(hps.diameterinternal, s.{UT_DIAMETER_MM}, r.{UT_DIAMETER_MM}, 200.0) as diameter,
                    s.{UT_FLOW_TH} as flow,
                    s.{UT_VELOCITY_MS} as velocity,
                    s.{UT_SPEC_LOSS_MM_M} as spec_loss,
                    s.{UT_LOSS_LINEAR_M} as loss_linear,
                    s.{UT_LOSS_LOCAL_M} as loss_local,
                    s.{UT_LOSS_TOTAL_M} as loss_total,
                    r.{UT_FLOW_TH} as flow_return,
                    r.{UT_VELOCITY_MS} as velocity_return,
                    r.{UT_SPEC_LOSS_MM_M} as spec_loss_return,
                    r.{UT_LOSS_LINEAR_M} as loss_linear_return,
                    r.{UT_LOSS_LOCAL_M} as loss_local_return,
                    r.{UT_LOSS_TOTAL_M} as loss_total_return
                FROM linesobj l
                LEFT JOIN LATERAL (
                    SELECT pipesectlength, diameterinternal FROM heatpipesections
                    WHERE lineid = l.id ORDER BY id LIMIT 1
                ) hps ON true
                LEFT JOIN ut_out s ON s.lineid = l.id AND s.calculationid = $3
                                  AND s.externalsignlineid = {UT_SIGN_SUPPLY}
                LEFT JOIN ut_out r ON r.lineid = l.id AND r.calculationid = $3
                                  AND r.externalsignlineid = {UT_SIGN_RETURN}
                WHERE ((l.nodeid1 = $1 AND l.nodeid2 = $2) OR (l.nodeid1 = $2 AND l.nodeid2 = $1))
                  AND COALESCE(l.removed, 0) = 0
                LIMIT 1
            """

            node_dict = {p["node_id"]: p for p in path_data}

            for i in range(len(path_nodes) - 1):
                n1_id = path_nodes[i]
                n2_id = path_nodes[i + 1]
                edge_row = await conn.fetchrow(q_edge, n1_id, n2_id, cid)
                n1_info = node_dict.get(n1_id, {})
                n2_info = node_dict.get(n2_id, {})

                seg_len = float(edge_row["length"]) if edge_row and edge_row["length"] else 10.0
                cum_dist += seg_len

                def val(key: str) -> Optional[float]:
                    return float(edge_row[key]) if edge_row and edge_row[key] is not None else None

                segment_details.append({
                    "node1_id": n1_id,
                    "node1_label": n1_info.get("label") or f"Узел {n1_id}",
                    "node2_id": n2_id,
                    "node2_label": n2_info.get("label") or f"Узел {n2_id}",
                    "line_id": edge_row["line_id"] if edge_row else None,
                    "length": seg_len,
                    "diameter": float(edge_row["diameter"]) if edge_row and edge_row["diameter"] else 200.0,
                    "supply": {
                        "flow": val("flow"), "velocity": val("velocity"), "spec_loss": val("spec_loss"),
                        "loss_linear": val("loss_linear"), "loss_local": val("loss_local"),
                        "loss_total": val("loss_total"),
                    },
                    "return": {
                        "flow": val("flow_return"), "velocity": val("velocity_return"),
                        "spec_loss": val("spec_loss_return"), "loss_linear": val("loss_linear_return"),
                        "loss_local": val("loss_local_return"), "loss_total": val("loss_total_return"),
                    },
                    "h_pod_start": n1_info.get("h_pod"),
                    "h_pod_end": n2_info.get("h_pod"),
                    "h_obr_start": n1_info.get("h_obr"),
                    "h_obr_end": n2_info.get("h_obr"),
                    "distance_to_end": cum_dist,
                })

            excel_bytes = generate_piezometer_excel(
                path_data, segment_details,
                static_head=static["value"] if static else None,
                second_calculation_id=body.calculation_id_2,
            )

            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": "attachment; filename=piezometer_profile.xlsx"}
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating piezometer excel: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Сохранённые направления (gid8 GidWidget::savePjezo / onListPjezo)
# ---------------------------------------------------------------------------

class DirectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Название направления")
    nodes: list[int] = Field(..., min_length=2, max_length=MAX_WAYPOINTS, description="Опорные узлы маршрута по порядку")
    fileid: Optional[int] = Field(None, ge=1, description="Фрагмент; по умолчанию — фрагмент первого узла (как в десктопе)")
    replace: bool = Field(False, description="Заменить направление с тем же названием во фрагменте")


async def _direction_nodes(conn, direction_id: int) -> list[int]:
    rows = await conn.fetch(
        "SELECT nodeid FROM deployeddirections WHERE directionid = $1 AND nodeid IS NOT NULL ORDER BY id",
        direction_id,
    )
    return [r["nodeid"] for r in rows]


@router.get("/piezometer/directions")
async def list_directions(fileid: Optional[list[int]] = Query(None, description="Фрагменты (повторяемый параметр)")):
    """Список сохранённых направлений (десктоп: WHERE fileID in (открытые фрагменты))."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT d.id, d.name, d.fileid, f.name AS fragment_name,
                   count(dd.id) AS node_count,
                   count(dd.id) FILTER (WHERE n.id IS NULL OR COALESCE(n.removed, 0) <> 0) AS missing_nodes
              FROM directions d
              LEFT JOIN fragments f ON f.id = d.fileid
              LEFT JOIN deployeddirections dd ON dd.directionid = d.id
              LEFT JOIN nodes n ON n.id = dd.nodeid
             WHERE ($1::int[] IS NULL OR d.fileid = ANY($1::int[]))
             GROUP BY d.id, f.name
             ORDER BY d.fileid, d.name, d.id
            """,
            fileid or None,
        )
        return {"items": [dict(r) for r in rows], "count": len(rows)}


@router.get("/piezometer/directions/{direction_id}")
async def get_direction(direction_id: int):
    """Опорные узлы направления (порядок — deployeddirections.id, как вставлял десктоп)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT id, name, fileid FROM directions WHERE id = $1", direction_id)
        if row is None:
            raise HTTPException(status_code=404, detail=f"Направление {direction_id} не найдено")
        nodes = await _direction_nodes(conn, direction_id)
        alive = {
            r["id"] for r in await conn.fetch(
                "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0", nodes
            )
        }
        return {**dict(row), "nodes": nodes, "missing_nodes": [n for n in nodes if n not in alive]}


@router.post("/piezometer/directions", dependencies=[Depends(require_mutations_enabled)])
async def create_direction(body: DirectionCreate, user: Annotated[AuthUser, Depends(require_roles("editor"))]):
    """Сохранить направление: строка directions + опорные узлы в deployeddirections."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Пустое название направления")
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            found = {
                r["id"]: r["fileid"] for r in await conn.fetch(
                    "SELECT id, fileid FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0",
                    body.nodes,
                )
            }
            missing = [n for n in body.nodes if n not in found]
            if missing:
                raise HTTPException(status_code=404, detail=f"Узлы не найдены или удалены: {missing[:10]}")
            fileid = body.fileid or found[body.nodes[0]]
            if fileid is None:
                raise HTTPException(status_code=400, detail="У первого узла нет фрагмента — укажите fileid")
            existing = await conn.fetch(
                "SELECT id FROM directions WHERE fileid = $1 AND name = $2 FOR UPDATE", fileid, name
            )
            replaced = []
            if existing:
                if not body.replace:
                    raise HTTPException(
                        status_code=409,
                        detail={"message": f"Направление «{name}» уже существует", "ids": [r["id"] for r in existing]},
                    )
                for r in existing:
                    old_nodes = await _direction_nodes(conn, r["id"])
                    await conn.execute("DELETE FROM deployeddirections WHERE directionid = $1", r["id"])
                    await conn.execute("DELETE FROM directions WHERE id = $1", r["id"])
                    await write_audit_log(
                        changed_by=user.username, operation="DELETE", table_name="directions",
                        record_id=r["id"], old_data={"name": name, "fileid": fileid, "nodes": old_nodes}, conn=conn,
                    )
                    replaced.append(r["id"])
            direction_id = await conn.fetchval(
                "INSERT INTO directions (name, fileid) VALUES ($1, $2) RETURNING id", name, fileid
            )
            await conn.executemany(
                "INSERT INTO deployeddirections (directionid, nodeid) VALUES ($1, $2)",
                [(direction_id, n) for n in body.nodes],
            )
            await write_audit_log(
                changed_by=user.username, operation="INSERT", table_name="directions", record_id=direction_id,
                new_data={"name": name, "fileid": fileid, "nodes": body.nodes}, conn=conn,
            )
    return {"id": direction_id, "name": name, "fileid": fileid, "nodes": body.nodes, "replaced": replaced}


@router.delete("/piezometer/directions/{direction_id}", dependencies=[Depends(require_mutations_enabled)])
async def delete_direction(direction_id: int, user: Annotated[AuthUser, Depends(require_roles("editor"))]):
    """Удалить направление (как кнопка «Удалить» в списке направлений десктопа)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "SELECT id, name, fileid FROM directions WHERE id = $1 FOR UPDATE", direction_id
            )
            if row is None:
                raise HTTPException(status_code=404, detail=f"Направление {direction_id} не найдено")
            nodes = await _direction_nodes(conn, direction_id)
            await conn.execute("DELETE FROM deployeddirections WHERE directionid = $1", direction_id)
            await conn.execute("DELETE FROM directions WHERE id = $1", direction_id)
            await write_audit_log(
                changed_by=user.username, operation="DELETE", table_name="directions", record_id=direction_id,
                old_data={"name": row["name"], "fileid": row["fileid"], "nodes": nodes}, conn=conn,
            )
    return {"deleted": direction_id}
