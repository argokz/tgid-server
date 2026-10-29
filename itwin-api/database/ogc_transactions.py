"""OGC API — Features, часть 4 (Create, Replace, Update, Delete): правила записи коллекций.

Запись идёт теми же операциями, что окно свойств и редактор сети (routers/ogc_write.py): права по
видам объектов с охватом «только свои», журнал отмены, audit_log, проверка правил связности. Здесь —
что можно писать, версия объекта (ETag) и разбор тела запроса.

- Свойства (WRITABLE) пишутся окном свойств: имя, у участка — паспорт трубы (Ду, внутренний диаметр,
  состояние подачи и обратки), у задвижки — состояние (1 открыта, 2 закрыта).
- Геометрия: узел — перенос (участки следуют за ним), участок — промежуточные вершины (концы
  остаются у узлов). У задвижки и источника положение производное — его не меняют.
- Создание и удаление — узлы и участки. Потребители только читаются: реальные и обобщённые
  делят коллекцию, а id у них из разных таблиц.
- ETag — хеш версий строк объекта; If-Match с другим значением → 412.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any, Optional

from database.topology import version_token

# коллекция → свойство → (таблица, колонка)
WRITABLE: dict[str, dict[str, tuple[str, str]]] = {
    "pipes": {
        "name": ("linesobj", "registnum"),
        "diameter_mm": ("heatpipesections", "diametercondit"),
        "diameter_internal_mm": ("heatpipesections", "diameterinternal"),
        "state_supply": ("heatpipesections", "pipesectstateidflow"),
        "state_return": ("heatpipesections", "pipesectstateidret"),
    },
    "nodes": {"name": ("nodes", "nodename")},
    "valves": {"name": ("dampers", "name"), "state": ("dampers", "damperarmaturestateid")},
    "heat_sources": {"name": ("heatsources", "name")},
}
GEOMETRY_EDITABLE = frozenset({"nodes", "pipes"})
CREATABLE = frozenset({"nodes", "pipes"})
DELETABLE = frozenset({"nodes", "pipes"})
# Только при создании: вид узла (расчётный тип, routers/topology.NodeTypeField), фрагмент, концы участка
NODE_KINDS = ("US", "PR", "PO", "IS", "HS", "US2")
CREATE_ONLY: dict[str, frozenset[str]] = {
    "nodes": frozenset({"node_kind", "fileid"}),
    "pipes": frozenset({"node_start", "node_end"}),
}
# Совпадение координат с текущими (WGS84, градусы): ~1 см — геометрию не трогать
COORD_TOLERANCE = 1e-7
MAX_LINE_VERTICES = 5000


class OgcWriteError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def writable(cid: str) -> dict[str, tuple[str, str]]:
    return WRITABLE.get(cid, {})


# --- версия объекта ---------------------------------------------------------------------------

async def row_versions(conn, cid: str, fid: int) -> Optional[dict[str, str]]:
    """{"таблица:id": версия} строк объекта; None — объекта нет или удалён.

    Узел и участок — токен топологии (archivechangedate#xmin), остальные строки — xmin.
    """
    if cid in ("nodes", "pipes"):
        table = "nodes" if cid == "nodes" else "linesobj"
        row = await conn.fetchrow(
            f"SELECT archivechangedate, xmin::text AS xmin FROM {table} WHERE id = $1 AND COALESCE(removed, 0) = 0", fid)
        if row is None:
            return None
        versions = {f"{table}:{fid}": version_token(row["archivechangedate"], row["xmin"])}
        if cid == "pipes":
            for p in await conn.fetch("SELECT id, xmin::text AS xmin FROM heatpipesections WHERE lineid = $1", fid):
                versions[f"heatpipesections:{p['id']}"] = p["xmin"]
        return versions
    table = {"valves": "dampers", "heat_sources": "heatsources"}.get(cid)
    if table is None:
        return None
    xmin = await conn.fetchval(f"SELECT xmin::text FROM {table} WHERE id = $1", fid)
    return None if xmin is None else {f"{table}:{fid}": xmin}


def etag(versions: dict[str, str]) -> str:
    digest = hashlib.sha256(json.dumps(versions, sort_keys=True).encode("utf-8")).digest()
    return '"' + base64.urlsafe_b64encode(digest[:18]).decode("ascii") + '"'


def if_match_ok(header: Optional[str], current: str) -> bool:
    """If-Match: «*» или один из перечисленных ETag (слабые W/ для If-Match не годятся)."""
    if header is None:
        return True
    tags = [t.strip() for t in header.split(",") if t.strip()]
    return "*" in tags or current in tags


def row_xmin(version: str) -> str:
    """Версия для окна свойств — xmin (у узла и участка он после «#» в токене топологии)."""
    return version.rsplit("#", 1)[-1]


# --- тело запроса ------------------------------------------------------------------------------

def feature_parts(body: Any) -> tuple[Optional[dict], dict[str, Any]]:
    """GeoJSON Feature (или частичный — для PATCH) → (geometry, properties)."""
    if not isinstance(body, dict):
        raise OgcWriteError(400, "Тело запроса — GeoJSON Feature")
    if body.get("type") not in (None, "Feature"):
        raise OgcWriteError(400, "Ожидается GeoJSON Feature")
    props = body.get("properties") or {}
    if not isinstance(props, dict):
        raise OgcWriteError(400, "properties — объект")
    geometry = body.get("geometry")
    if geometry is not None and not isinstance(geometry, dict):
        raise OgcWriteError(400, "geometry — объект GeoJSON")
    return geometry, props


def _lon_lat(pair: Any) -> list[float]:
    if not isinstance(pair, (list, tuple)) or len(pair) < 2:
        raise OgcWriteError(400, "Координата — [долгота, широта]")
    try:
        lon, lat = float(pair[0]), float(pair[1])
    except (TypeError, ValueError):
        raise OgcWriteError(400, "Координаты — числа") from None
    if not (math.isfinite(lon) and math.isfinite(lat) and -180 <= lon <= 180 and -90 <= lat <= 90):
        raise OgcWriteError(400, "Координаты — WGS84 (CRS84): долгота −180…180, широта −90…90")
    return [lon, lat]


def point(geometry: dict) -> list[float]:
    if geometry.get("type") != "Point":
        raise OgcWriteError(400, "Геометрия узла — Point")
    return _lon_lat(geometry.get("coordinates"))


def line_coords(geometry: dict) -> list[list[float]]:
    if geometry.get("type") != "LineString":
        raise OgcWriteError(400, "Геометрия участка — LineString")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or not 2 <= len(coords) <= MAX_LINE_VERTICES:
        raise OgcWriteError(400, f"LineString: от 2 до {MAX_LINE_VERTICES} вершин")
    return [_lon_lat(c) for c in coords]


def same_geometry(cid: str, current: Optional[dict], geometry: dict) -> bool:
    """Геометрия не изменилась (клиент прислал объект целиком) — операцию правки сети не запускать."""
    if not current:
        return False
    if cid == "nodes":
        new, old = [point(geometry)], [current.get("coordinates") or []]
    else:
        if current.get("type") != "LineString":
            return False
        new, old = line_coords(geometry), current.get("coordinates") or []
    if len(new) != len(old):
        return False
    return all(abs(a[0] - b[0]) <= COORD_TOLERANCE and abs(a[1] - b[1]) <= COORD_TOLERANCE
               for a, b in zip(new, old))


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9)
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    return a == b


def property_changes(cid: str, current: dict[str, Any], given: dict[str, Any], *,
                     ignore: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Изменённые правимые свойства. Только читаемое свойство с другим значением или неизвестное — 422
    (клиент присылает объект целиком: совпадающие только читаемые свойства пропускаются)."""
    rules = writable(cid)
    changes: dict[str, Any] = {}
    for name, value in given.items():
        if name in ignore:
            continue
        if name in rules:
            if name not in current or not _same(value, current[name]):
                changes[name] = value
        elif name in current:
            if not _same(value, current[name]):
                raise OgcWriteError(422, f"Свойство {name} только для чтения")
        else:
            raise OgcWriteError(422, f"У коллекции {cid} нет свойства {name}")
    return changes


def card_changes(cid: str, fid: int, changes: dict[str, Any], versions: dict[str, str]) -> list[dict[str, Any]]:
    """Свойства → правки окна свойств [{table, id, field, value}]."""
    out = []
    for name, value in changes.items():
        table, column = writable(cid)[name]
        if table == "heatpipesections":
            passports = [k for k in versions if k.startswith("heatpipesections:")]
            if len(passports) != 1:
                raise OgcWriteError(409, f"У участка {fid} {len(passports)} паспортов трубы — правьте в окне свойств")
            row_id = int(passports[0].split(":", 1)[1])
        else:
            row_id = fid
        out.append({"table": table, "id": row_id, "field": column, "value": value})
    return out
