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
