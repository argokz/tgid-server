"""Обход маршрутом (фаза 2, полевое приложение, шаг 4): наряд на осмотр по контуру осмотра десктопа.

Контур осмотра (osmotr) — участки, перечисленные в osmotrdeployed. Маршрут наряда — эти участки, точки обхода —
их узлы в порядке участков контура. Бригада отмечает узел «осмотрен» или «с дефектом» (tgid_work_order_check);
дефект узла пишется в журнал дефектов с osmotrid контура (work_orders.report_defect). Когда обход выполнен,
«Результаты осмотра» контура заполняются из результата наряда, если там ещё пусто (work_orders._sync_inspection).
"""
from __future__ import annotations

import json
from typing import Any

from database import work_orders as wo

MAX_ROUTE_LINES = 2000


async def _inspection_of(conn, order_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    order = await wo.get_order(conn, order_id)
    if not order.get("inspection_id"):
        raise wo.WorkOrderError(422, f"Наряд {order['number']} — не обход по контуру осмотра")
    inspection = await conn.fetchrow("SELECT id, name FROM osmotr WHERE id = $1", order["inspection_id"])
    if inspection is None:
        raise wo.WorkOrderError(404, f"Контура осмотра {order['inspection_id']} больше нет в журнале")
    return order, dict(inspection)


async def route(conn, order_id: int) -> dict[str, Any]:
    """Маршрут обхода: участки контура (линии), узлы по порядку участков с отметками и итог."""
    order, inspection = await _inspection_of(conn, order_id)
    lines = await conn.fetch(
        f"""SELECT l.id, l.nodeid1, l.nodeid2, ST_AsGeoJSON(ST_Transform(l.shape, 4326), 6) AS geom
              FROM osmotrdeployed r JOIN linesobj l ON l.id = r.lineid
             WHERE r.directionid = $1 AND COALESCE(l.removed, 0) = 0 AND l.shape IS NOT NULL
             ORDER BY r.id LIMIT {MAX_ROUTE_LINES}""", inspection["id"])
    node_ids: list[int] = []
    for line in lines:
        for node_id in (line["nodeid1"], line["nodeid2"]):
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
    nodes = {r["id"]: r for r in await conn.fetch(
        """SELECT n.id, COALESCE(NULLIF(n.nodename, ''), n.externalnodename) AS name, nt.name AS node_type,
                  ST_X(ST_Transform(n.shape, 4326)) AS lon, ST_Y(ST_Transform(n.shape, 4326)) AS lat
             FROM nodes n LEFT JOIN nodetypes nt ON nt.id = n.nodetypeid
            WHERE n.id = ANY($1::int[]) AND n.shape IS NOT NULL""", node_ids)}
    checks = {r["node_id"]: r for r in await conn.fetch(
        "SELECT node_id, state, note, defect_id, by_user, at FROM tgid_work_order_check WHERE order_id = $1",
        order_id)}
    points = []
    for node_id in node_ids:
        node = nodes.get(node_id)
        if node is None:
            continue
        check = checks.get(node_id)
        points.append({
            "node_id": node_id, "name": (node["name"] or "").strip() or f"Узел {node_id}",
            "node_type": node["node_type"], "lon": node["lon"], "lat": node["lat"],
            "state": check["state"] if check else None, "note": check["note"] if check else "",
            "defect_id": check["defect_id"] if check else None,
            "by_user": check["by_user"] if check else None, "at": check["at"].isoformat() if check else None,
        })
    return {
        "order_id": order_id,
        "inspection": {"id": inspection["id"], "name": (inspection["name"] or "").strip()},
        "lines": {"type": "FeatureCollection", "features": [
            {"type": "Feature", "id": r["id"], "geometry": json.loads(r["geom"]), "properties": {"id": r["id"]}}
            for r in lines]},
        "points": points,
        "progress": progress(points),
        "truncated": len(lines) >= MAX_ROUTE_LINES,
    }


def progress(points: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(points),
        "ok": sum(1 for p in points if p["state"] == "ok"),
        "defect": sum(1 for p in points if p["state"] == "defect"),
    }


async def add_check(conn, order_id: int, body: wo.CheckIn, user: str) -> dict[str, Any]:
    """Отметить узел маршрута; повтор с тем же ключом — без изменений; закрытый наряд — 409."""
    order, inspection = await _inspection_of(conn, order_id)
    if not await wo._already_done(conn, body):
        if order["status"] in wo.FINAL:
            raise wo.WorkOrderError(409, f"Наряд {order['number']} {order['status_label'].lower()} — отметки закрыты")
        on_route = await conn.fetchval(
            """SELECT EXISTS (SELECT 1 FROM osmotrdeployed r JOIN linesobj l ON l.id = r.lineid
                               WHERE r.directionid = $1 AND $2 IN (l.nodeid1, l.nodeid2))""",
            inspection["id"], body.node_id)
        if not on_route:
            raise wo.WorkOrderError(422, f"Узла {body.node_id} нет на маршруте обхода")
        await wo.upsert_check(conn, order_id, body.node_id, body.state, user, note=body.note.strip(), stamp=body)
    return await route(conn, order_id)
