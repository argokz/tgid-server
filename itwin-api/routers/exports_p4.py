"""P4: DXF и GeoJSON экспорт, очередь опрессовок (RO), Word stubs for ops journals."""

from __future__ import annotations

import io
import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from app_logging import get_logger
from database.connect import acquire_conn
from database.fragment_filter import LINE_IN_FRAGMENTS_SQL, LIVE_LINE_SQL, parse_fragment_ids
from word_reports.word_generator import generate_ops_act_word

logger = get_logger(__name__)

router = APIRouter(tags=["exports-p4"])

# Участки фрагмента — по linesobj.fileid, как в SHP и GeoJSON (database.fragment_filter, QA F13)
_DXF_LINES_SQL = f"""
    SELECT lo.id,
           ST_AsText(ST_Transform(lo.shape, 4326)) AS wkt
      FROM linesobj lo
     WHERE {LIVE_LINE_SQL}
       AND {LINE_IN_FRAGMENTS_SQL}
       AND lo.shape IS NOT NULL
     ORDER BY lo.id
     LIMIT $2
"""


@router.get("/api/export/dxf")
async def export_network_dxf(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Фрагменты через запятую (fileid)"),
    limit: int = Query(50000, ge=1, le=200000),
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
        rows = await conn.fetch(_DXF_LINES_SQL, parse_fragment_ids(fragment_id, fragments), limit)

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


_LINES_WITH_PASSPORT_SQL = f"""
    SELECT
        lo.id,
        lo.registnum AS name,
        lo.nodeid1,
        lo.nodeid2,
        lo.fileid,
        hps.pipesectlength AS length,
        hps.diameterinternal AS diameter,
        hps.tuberoughness AS roughness,
        ST_AsGeoJSON(ST_Transform(lo.shape, 4326)) AS geometry
    FROM linesobj lo
    LEFT JOIN LATERAL (
        SELECT pipesectlength, diameterinternal, tuberoughness FROM heatpipesections
        WHERE lineid = lo.id ORDER BY id LIMIT 1
    ) hps ON true
    WHERE {LIVE_LINE_SQL}
      AND {LINE_IN_FRAGMENTS_SQL}
      AND lo.shape IS NOT NULL
    ORDER BY lo.id
    LIMIT $2
"""

_CRS84 = {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}


def _num(value) -> Optional[float]:
    return None if value is None else float(value)


async def _fetch_lines(fragment_ids: Optional[list[int]], limit: int):
    async with acquire_conn() as conn:
        return await conn.fetch(_LINES_WITH_PASSPORT_SQL, fragment_ids, limit)


@router.get("/api/export/geojson")
async def export_network_geojson(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Фрагменты через запятую (fileid)"),
    limit: int = Query(10000, ge=1, le=50000),
):
    """Экспорт участков сети в стандартный GeoJSON (WGS84) для QGIS: геометрия и паспорт трубы."""
    rows = await _fetch_lines(parse_fragment_ids(fragment_id, fragments), limit)
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
                "fileid": r["fileid"],
                "nodeid1": r["nodeid1"],
                "nodeid2": r["nodeid2"],
                "length": _num(r["length"]),
                "diameter": _num(r["diameter"]),
                "roughness": _num(r["roughness"]),
            },
        })
    return {"type": "FeatureCollection", "crs": _CRS84, "features": features}


@router.get("/api/export/geojson-attrs")
@router.get(
    "/api/export/zulugis",
    deprecated=True,
    summary="Устаревший адрес /api/export/geojson-attrs (это GeoJSON, не формат ZuluGIS)",
)
async def export_network_geojson_attrs(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Фрагменты через запятую (fileid)"),
    limit: int = Query(10000, ge=1, le=50000),
):
    """GeoJSON участков с расчётными атрибутами в коротких именах (Sys, Name, Node1, Node2, L, D, K_E).

    Это обычный GeoJSON (WGS84), не собственный формат ZuluGIS: короткие имена полей удобно
    сопоставлять при загрузке в ZuluGIS/QGIS. L — длина, м; D — внутренний диаметр, м;
    K_E — эквивалентная шероховатость. Нет паспорта трубы — поле null (раньше подставлялись
    выдуманные 10 м / 200 мм). Старый адрес /api/export/zulugis оставлен как алиас.
    """
    rows = await _fetch_lines(parse_fragment_ids(fragment_id, fragments), limit)
    features = []
    for r in rows:
        if not r["geometry"]:
            continue
        diameter_mm = _num(r["diameter"])
        features.append({
            "type": "Feature",
            "geometry": json.loads(r["geometry"]),
            "properties": {
                "Sys": r["id"],
                "Type": 1,
                "Name": r["name"] or f"Участок {r['id']}",
                "Fragment": r["fileid"],
                "Node1": r["nodeid1"],
                "Node2": r["nodeid2"],
                "L": _num(r["length"]),
                "D": None if diameter_mm is None else diameter_mm / 1000.0,
                "K_E": _num(r["roughness"]),
                "Kst": 1.0,
            },
        })
    return {"type": "FeatureCollection", "crs": _CRS84, "features": features}
