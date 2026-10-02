"""Выгрузки сети (DXF, GeoJSON, SHP): общий DXF-построитель и заголовки полноты выгрузки.

Выгрузки ограничены числом строк (limit). Раньше обрезка была молчаливой (QA F84): теперь
запрашивается limit + 1 строка, лишняя отбрасывается, а в ответ уходят заголовки
X-Export-Rows / X-Export-Limit / X-Export-Truncated — web показывает предупреждение, как у
ведомостей (X-Report-Truncated). DXF строится и синхронно, и фоновой задачей file-job
(QA F77: по фрагменту — десятки секунд без индикации).
"""

from __future__ import annotations

import asyncio
import io
from typing import Any, Optional, Sequence

from database.fragment_filter import LINE_IN_FRAGMENTS_SQL, LIVE_LINE_SQL

# Участки фрагмента — по linesobj.fileid, как в SHP и GeoJSON (database.fragment_filter, QA F13)
DXF_LINES_SQL = f"""
    SELECT lo.id,
           ST_AsText(ST_Transform(lo.shape, 4326)) AS wkt
      FROM linesobj lo
     WHERE {LIVE_LINE_SQL}
       AND {LINE_IN_FRAGMENTS_SQL}
       AND lo.shape IS NOT NULL
     ORDER BY lo.id
     LIMIT $2
"""

EXPORT_HEADER_NAMES = ("X-Export-Rows", "X-Export-Limit", "X-Export-Truncated")


class DxfUnavailable(RuntimeError):
    """На хосте нет ezdxf (опциональная зависимость из requirements.txt)."""


def split_limited(rows: Sequence[Any], limit: int) -> tuple[list[Any], bool]:
    """Строки запроса с LIMIT limit + 1 → (не больше limit строк, была ли обрезка)."""
    rows = list(rows)
    return rows[:limit], len(rows) > limit


def export_headers(rows: int, limit: int, truncated: bool, *, expose: Sequence[str] = ()) -> dict[str, str]:
    headers = {
        "X-Export-Rows": str(rows),
        "X-Export-Limit": str(limit),
        "X-Export-Truncated": "1" if truncated else "0",
    }
    headers["Access-Control-Expose-Headers"] = ", ".join([*expose, *EXPORT_HEADER_NAMES])
    return headers


def export_suffix(fragment_ids: Optional[Sequence[int]]) -> str:
    if not fragment_ids:
        return ""
    return f"_f{fragment_ids[0]}" if len(fragment_ids) == 1 else "_frag"


def _wkt_points(wkt: str) -> list[tuple[float, float]]:
    # LINESTRING(x y, x y, ...)
    if not wkt.upper().startswith("LINESTRING"):
        return []
    inner = wkt[wkt.find("(") + 1: wkt.rfind(")")]
    pts = []
    for part in inner.split(","):
        nums = part.strip().split()
        if len(nums) >= 2:
            pts.append((float(nums[0]), float(nums[1])))
    return pts


def render_dxf(wkts: Sequence[str]) -> bytes:
    try:
        import ezdxf
    except ImportError as exc:
        raise DxfUnavailable("ezdxf is not installed on the API host") from exc
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    for wkt in wkts:
        pts = _wkt_points(wkt or "")
        if len(pts) >= 2:
            msp.add_lwpolyline(pts, dxfattribs={"layer": "HEATNET"})
    buf = io.StringIO()
    doc.write(buf)
    return buf.getvalue().encode("utf-8")


async def build_network_dxf(conn, fragment_ids: Optional[list[int]], limit: int) -> tuple[bytes, dict[str, str]]:
    """DXF участков (2D-полилинии, WGS84) и заголовки полноты выгрузки."""
    rows, truncated = split_limited(await conn.fetch(DXF_LINES_SQL, fragment_ids, limit + 1), limit)
    data = await asyncio.to_thread(render_dxf, [r["wkt"] for r in rows])
    return data, export_headers(len(rows), limit, truncated)
