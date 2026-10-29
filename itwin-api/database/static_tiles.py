"""Статичные слои в PMTiles (п. 13 фазы 1): тайлы большого редко меняющегося слоя запекаются один раз.

Источник — функция тайлов martin tgid_mvt_<слой> в базе города (scripts/martin, city_schema): тайлы архива
те же, что отдаёт martin, и подходят к стилю слоя GeoServer. Запекаются только слои без параметров
SQL-представления (здания и т. п.) — у слоёв сети тайл зависит от фрагментов и подписей.

Обход — по дереву тайлов: с нижнего уровня слоя по охвату сети города (+ запас), дочерние тайлы —
только у непустых. Тайлы — MVT в gzip; архив — <STATIC_TILES_DIR>/<город>/<слой>.pmtiles. API отдаёт из
него тайлы z/x/y (routers/static_tiles.py) и файл целиком (офлайн, фаза 2).
"""
from __future__ import annotations

import asyncio
import gzip
import math
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from cities import current_city
from database import pmtiles

LAYER_RE = re.compile(r"^[a-z][a-z0-9_]{0,59}$")
FUNC_PREFIX = "tgid_mvt_"
# в функции слоя без параметров SQL-представления генератор пишет этот комментарий (scripts/martin)
NO_PARAMS_MARK = "у слоя нет параметров"
_VISIBLE_FROM = re.compile(r"виден с зума (\d+)")
# таблица слоя в SQL функции (FROM public."zdaniya_2") — охват запекания
_FROM_TABLE = re.compile(r'FROM public\."([a-z][a-z0-9_]*)"')
DEFAULT_MAXZOOM = 16
MAX_MAXZOOM = 18
MAX_TILES = 200_000
# запас вокруг охвата сети: здания и подложки шире трасс
BBOX_MARGIN_DEG = 0.05
PARALLEL = 4
GZIP_LEVEL = 6


class StaticTilesError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def base_dir() -> Path:
    root = os.getenv("STATIC_TILES_DIR", "").strip()
    if root:
        return Path(root)
    return Path(__file__).resolve().parent.parent / "files" / "static_tiles"


def city_dir() -> Path:
    return base_dir() / (current_city() or "default")


def check_layer(layer: str) -> str:
    if not LAYER_RE.match(layer or ""):
        raise StaticTilesError(422, "Имя слоя — латиница, цифры и «_»")
    return layer


def archive_path(layer: str) -> Path:
    return city_dir() / f"{check_layer(layer)}.pmtiles"


# --- какие слои можно запечь ----------------------------------------------------------------

async def bakeable_layers(conn) -> list[dict[str, Any]]:
    """Функции тайлов martin в базе города: слой, с какого зума виден, можно ли запечь (нет параметров)."""
    rows = await conn.fetch(
        "SELECT p.proname, obj_description(p.oid, 'pg_proc') AS comment, pg_get_functiondef(p.oid) AS def"
        "  FROM pg_proc p WHERE p.pronamespace = 'public'::regnamespace AND p.proname LIKE 'tgid\\_mvt\\_%'"
        " ORDER BY p.proname")
    out = []
    for r in rows:
        m = _VISIBLE_FROM.search(r["comment"] or "")
        table = _FROM_TABLE.search(r["def"] or "")
        out.append({"layer": r["proname"][len(FUNC_PREFIX):], "minzoom": int(m.group(1)) if m else 0,
                    "static": NO_PARAMS_MARK in (r["def"] or ""), "table": table.group(1) if table else None})
    return out


async def _layer_info(conn, layer: str) -> dict[str, Any]:
    for info in await bakeable_layers(conn):
        if info["layer"] == layer:
            if not info["static"]:
                raise StaticTilesError(422, f"Слой {layer} зависит от фрагментов и подписей — запечь нельзя")
            return info
    raise StaticTilesError(404, f"В базе города нет функции тайлов {FUNC_PREFIX}{layer} (martin)")


# --- запекание ------------------------------------------------------------------------------

def _lon_to_x(lon: float, z: int) -> int:
    n = 1 << z
    return min(n - 1, max(0, int((lon + 180.0) / 360.0 * n)))


def _lat_to_y(lat: float, z: int) -> int:
    n = 1 << z
    lat = max(min(lat, 85.0511), -85.0511)
    r = math.radians(lat)
    return min(n - 1, max(0, int((1.0 - math.asinh(math.tan(r)) / math.pi) / 2.0 * n)))


def tiles_in_bbox(bbox: tuple[float, float, float, float], z: int) -> list[tuple[int, int, int]]:
    w, s, e, n = bbox
    x0, x1 = _lon_to_x(w, z), _lon_to_x(e, z)
    y0, y1 = _lat_to_y(n, z), _lat_to_y(s, z)
    return [(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


async def layer_bbox(conn, table: Optional[str]) -> tuple[float, float, float, float]:
    """Охват запекания: таблица слоя (если есть колонка shape) вместе с сетью города, с запасом."""
    parts = ["SELECT ST_Extent(ST_Transform(shape, 4326)) AS b FROM nodes"
             " WHERE removed = 0 AND internalnodeid IS NULL AND shape IS NOT NULL"]
    if table and await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'"
            " AND table_name = $1 AND column_name = 'shape')", table):
        parts.append(f'SELECT ST_Extent(ST_Transform(shape, 4326)) AS b FROM public."{table}"')
    row = await conn.fetchrow(
        "SELECT ST_XMin(b) AS w, ST_YMin(b) AS s, ST_XMax(b) AS e, ST_YMax(b) AS n FROM ("
        f"  SELECT ST_Extent(b) AS b FROM ({' UNION ALL '.join(parts)}) u) t")
    if row is None or row["w"] is None:
        raise StaticTilesError(422, "Нет ни объектов слоя, ни узлов сети с координатами — охват не определить")
    m = BBOX_MARGIN_DEG
    return (max(row["w"] - m, -180.0), max(row["s"] - m, -85.0), min(row["e"] + m, 180.0), min(row["n"] + m, 85.0))


Progress = Callable[[str], None]


async def bake(conns: list, layer: str, *, minzoom: Optional[int] = None, maxzoom: int = DEFAULT_MAXZOOM,
               progress: Optional[Progress] = None, user: str = "") -> dict[str, Any]:
    """Запечь слой в PMTiles: conns — соединения с базой города (тайлы строятся параллельно по одному на каждом)."""
    check_layer(layer)
    if not conns:
        raise StaticTilesError(500, "Нет соединения с базой")
    info = await _layer_info(conns[0], layer)
    lo = info["minzoom"] if minzoom is None else minzoom
    if not 0 <= lo <= maxzoom <= MAX_MAXZOOM:
        raise StaticTilesError(422, f"Зумы: от 0 до {MAX_MAXZOOM}, нижний не больше верхнего")
    bbox = await layer_bbox(conns[0], info["table"])
    func = f"public.{FUNC_PREFIX}{layer}"
    sql = f"SELECT {func}($1, $2, $3)"
    started = time.monotonic()
    writer = pmtiles.Writer(archive_path(layer))
    pool: asyncio.Queue = asyncio.Queue()
    for c in conns:
        pool.put_nowait(c)

    async def one(z: int, x: int, y: int) -> Optional[bytes]:
        conn = await pool.get()
        try:
            return await conn.fetchval(sql, z, x, y)
        finally:
            pool.put_nowait(conn)

    raw_bytes = 0
    per_zoom: dict[int, int] = {}
    try:
        level = tiles_in_bbox(bbox, lo)
        for z in range(lo, maxzoom + 1):
            if writer.tile_count + len(level) > MAX_TILES:
                raise StaticTilesError(422, f"Больше {MAX_TILES} тайлов — уменьшите верхний зум")
            if progress:
                progress(f"Зум {z}: {len(level)} тайлов, записано {writer.tile_count}")
            results = await asyncio.gather(*(one(*t) for t in level))
            filled = []
            for (tz, tx, ty), data in zip(level, results):
                if not data:
                    continue
                raw_bytes += len(data)
                writer.add_tile(tz, tx, ty, gzip.compress(bytes(data), compresslevel=GZIP_LEVEL, mtime=0))
                filled.append((tz, tx, ty))
            per_zoom[z] = len(filled)
            level = [(z + 1, 2 * x + dx, 2 * y + dy) for _, x, y in filled for dx in (0, 1) for dy in (0, 1)]
            if not level:
                break
        if not writer.tile_count:
            raise StaticTilesError(422, f"Слой {layer} пуст в охвате сети города — запекать нечего")
        built_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        metadata = {
            "name": layer,
            "format": "pbf",
            "vector_layers": [{"id": layer, "minzoom": lo, "maxzoom": max(per_zoom), "fields": {}}],
            "tgid": {"layer": layer, "source": func, "built_at": built_at, "built_by": user, "city": current_city(),
                     "bbox": list(bbox), "tiles_per_zoom": per_zoom, "raw_bytes": raw_bytes},
        }
        if progress:
            progress(f"Запись архива: {writer.tile_count} тайлов")
        summary = writer.finish(metadata=metadata, bounds=bbox)
    except BaseException:
        writer.abort()
        raise
    _readers.pop(str(archive_path(layer)), None)
    return {**summary, "layer": layer, "built_at": built_at, "tiles_per_zoom": per_zoom,
            "elapsed_s": round(time.monotonic() - started, 1)}


# --- архивы и чтение ------------------------------------------------------------------------

_readers: dict[str, tuple[float, pmtiles.Reader]] = {}


def reader(layer: str) -> Optional[pmtiles.Reader]:
    """Читатель архива слоя (пересоздаётся, если файл заменили); архива нет — None."""
    path = archive_path(layer)
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        _readers.pop(str(path), None)
        return None
    cached = _readers.get(str(path))
    if cached and cached[0] == mtime:
        return cached[1]
    r = pmtiles.Reader(path)
    _readers[str(path)] = (mtime, r)
    return r


def describe(layer: str, r: pmtiles.Reader) -> dict[str, Any]:
    tgid = r.metadata.get("tgid", {})
    path = archive_path(layer)
    return {
        "layer": layer,
        "minzoom": r.header.min_zoom,
        "maxzoom": r.header.max_zoom,
        "bounds": list(r.header.bounds),
        "tiles": r.header.addressed_tiles,
        "size": path.stat().st_size,
        "built_at": tgid.get("built_at"),
        "built_by": tgid.get("built_by") or None,
        # версия в адресе тайлов: новый архив — новые адреса, старые тайлы в кеше браузера не мешают
        "version": int(path.stat().st_mtime),
    }


def list_archives() -> list[dict[str, Any]]:
    folder = city_dir()
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.pmtiles")):
        layer = path.stem
        if not LAYER_RE.match(layer):
            continue
        try:
            r = reader(layer)
        except (pmtiles.PMTilesError, OSError):
            continue  # повреждённый файл не мешает остальным
        if r is not None:
            out.append(describe(layer, r))
    return out


def delete_archive(layer: str) -> bool:
    path = archive_path(layer)
    _readers.pop(str(path), None)
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    return True

