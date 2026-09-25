"""P4: DXF export, очередь опрессовок (RO), Word stubs for ops journals."""

from __future__ import annotations

import io
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app_logging import get_logger
from database.connect import acquire_conn
from word_reports.word_generator import generate_ops_act_word

logger = get_logger(__name__)

router = APIRouter(tags=["exports-p4"])


@router.get("/api/export/dxf")
async def export_network_dxf(
    fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(5000, ge=1, le=50000),
):
    """Export active lines as DXF (lightweight 2D polyline dump)."""
    try:
        import ezdxf
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="ezdxf is not installed on the API host",
        ) from exc

    async with acquire_conn() as conn:
        if fragment_id:
            rows = await conn.fetch(
                """
                SELECT lo.id,
                       ST_AsText(ST_Transform(lo.shape, 4326)) AS wkt
                  FROM linesobj lo
                  JOIN nodes n1 ON n1.id = lo.nodeid1
                 WHERE coalesce(lo.removed, 0) = 0
                   AND n1.fileid = $1
                 LIMIT $2
                """,
                fragment_id,
                limit,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT lo.id,
                       ST_AsText(ST_Transform(lo.shape, 4326)) AS wkt
                  FROM linesobj lo
                 WHERE coalesce(lo.removed, 0) = 0
                 LIMIT $1
                """,
                limit,
            )

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for row in rows:
        wkt = row["wkt"] or ""
        # LINESTRING(x y, x y, ...)
        if not wkt.upper().startswith("LINESTRING"):
            continue
        inner = wkt[wkt.find("(") + 1 : wkt.rfind(")")]
        pts = []
        for part in inner.split(","):
            nums = part.strip().split()
            if len(nums) >= 2:
                pts.append((float(nums[0]), float(nums[1])))
        if len(pts) >= 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer": "HEATNET"})

    buf = io.StringIO()
    doc.write(buf)
    data = buf.getvalue().encode("utf-8")
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/dxf",
        headers={"Content-Disposition": 'attachment; filename="network.dxf"'},
    )


@router.get("/api/ochered-opressovok")
async def ochered_opressovok_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """RO stub for legacy ochered_opressovok (separate from opres journal)."""
    offset = (page - 1) * page_size
    async with acquire_conn() as conn:
        # Table names vary across dumps; try primary then fallback empty.
        for table in (
            "ochered_opressovok",
            "opressovki_uchastok_ocheredi",
            "ocheredopressovok",
        ):
            try:
                total = await conn.fetchval(f"SELECT count(*)::int FROM {table}")
                rows = await conn.fetch(
                    f"SELECT * FROM {table} ORDER BY 1 DESC LIMIT $1 OFFSET $2",
                    page_size,
                    offset,
                )
                return {
                    "items": [dict(r) for r in rows],
                    "total": total or 0,
                    "page": page,
                    "page_size": page_size,
                    "table": table,
                }
            except Exception:  # noqa: BLE001
                continue
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "table": None,
        "note": "Таблица очереди опрессовок не найдена в схеме — загрузка дампа отдельным срезом",
    }


@router.get("/reports/word/{journal}/{record_id}")
async def export_ops_word(journal: str, record_id: int):
    """Word acts for ops journals (defect keeps dedicated /reports/word/defect/{id})."""
    journal_l = journal.lower()
    if journal_l == "defect":
        raise HTTPException(status_code=400, detail="Use /reports/word/defect/{id}")
    table_map = {
        "shurf": "shurfy",
        "shurfy": "shurfy",
        "osmotr": "osmotr",
        "inspection": "osmotr",
        "remont": "remont2",
        "repair": "remont2",
        "opres": "opres",
        "pressure-test": "opres",
    }
    table = table_map.get(journal_l)
    if not table:
        raise HTTPException(status_code=404, detail="Unknown journal for Word export")

    async with acquire_conn() as conn:
        row = await conn.fetchrow(f"SELECT * FROM {table} WHERE id=$1", record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")

    from fastapi.concurrency import run_in_threadpool

    filepath = await run_in_threadpool(
        generate_ops_act_word, journal_l, record_id, dict(row), "files"
    )
    if not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Generated file not found")
    return FileResponse(
        path=filepath,
        filename=os.path.basename(filepath),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@router.get("/api/export/geojson")
async def export_network_geojson(
    fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(10000, ge=1, le=50000),
):
    """Экспорт сети в стандартный GeoJSON для QGIS."""
    import json
    async with acquire_conn() as conn:
        q = """
            SELECT 
                l.id,
                l.registnum as name,
                l.nodeid1,
                l.nodeid2,
                hps.pipesectlength as length,
                hps.diameterinternal as diameter,
                hps.tuberoughness as roughness,
                ST_AsGeoJSON(ST_Transform(l.shape, 4326)) as geometry
            FROM linesobj l
            LEFT JOIN LATERAL (
                SELECT pipesectlength, diameterinternal, tuberoughness FROM heatpipesections
                WHERE lineid = l.id ORDER BY id LIMIT 1
            ) hps ON true
            WHERE COALESCE(l.removed, 0) = 0
              AND ($1::int IS NULL OR l.fileid = $1)
              AND l.shape IS NOT NULL
            LIMIT $2
        """
        rows = await conn.fetch(q, fragment_id, limit)
        features = []
        for r in rows:
            if not r["geometry"]:
                continue
            features.append({
                "type": "Feature",
                "geometry": json.loads(r["geometry"]),
                "properties": {
                    "id": r["id"],
                    "name": r["name"] or "",
                    "nodeid1": r["nodeid1"],
                    "nodeid2": r["nodeid2"],
                    "length": float(r["length"] or 0),
                    "diameter": float(r["diameter"] or 0),
                    "roughness": float(r["roughness"] or 0.001),
                }
            })
        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }


@router.get("/api/export/zulugis")
async def export_network_zulugis(
    fragment_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(10000, ge=1, le=50000),
):
    """Экспорт сети в ZuluGIS GeoJSON формат (с атрибутами Sys, Type, L, D, K_E)."""
    import json
    async with acquire_conn() as conn:
        q = """
            SELECT 
                l.id,
                l.registnum as name,
                l.nodeid1,
                l.nodeid2,
                COALESCE(hps.pipesectlength, 10.0) as l_m,
                COALESCE(hps.diameterinternal, 200.0) as d_mm,
                COALESCE(hps.tuberoughness, 0.001) as k_e,
                ST_AsGeoJSON(ST_Transform(l.shape, 4326)) as geometry
            FROM linesobj l
            LEFT JOIN LATERAL (
                SELECT pipesectlength, diameterinternal, tuberoughness FROM heatpipesections
                WHERE lineid = l.id ORDER BY id LIMIT 1
            ) hps ON true
            WHERE COALESCE(l.removed, 0) = 0
              AND ($1::int IS NULL OR l.fileid = $1)
              AND l.shape IS NOT NULL
            LIMIT $2
        """
        rows = await conn.fetch(q, fragment_id, limit)
        features = []
        for r in rows:
            if not r["geometry"]:
                continue
            features.append({
                "type": "Feature",
                "geometry": json.loads(r["geometry"]),
                "properties": {
                    "Sys": r["id"],
                    "Type": 1,
                    "Name": r["name"] or f"Участок {r['id']}",
                    "Node1": r["nodeid1"],
                    "Node2": r["nodeid2"],
                    "L": float(r["l_m"]),
                    "D": float(r["d_mm"]) / 1000.0,
                    "K_E": float(r["k_e"]),
                    "Kst": 1.0,
                }
            })
        return {
            "type": "FeatureCollection",
            "crs": {
                "type": "name",
                "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
            },
            "features": features
        }

