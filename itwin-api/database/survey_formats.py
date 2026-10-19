"""Трассы исполнительной съёмки: GPX (треки и маршруты) и DXF (линии и полилинии) → линии импорта.

Без внешних библиотек: GPX — XML (xml.etree с запретом сущностей), DXF — текстовый формат AutoCAD
(пары «код группы / значение»; двоичный DXF не поддерживается). Каждая линия — строка импорта
участков (database/network_import, режим lines): концы привязываются к узлам фрагмента в допуске.

GPX всегда в WGS84. Система DXF в файле не записана — её выбирает оператор (местная, десктоп, WGS84).
Дуги (bulge в полилиниях, ARC) не аппроксимируются: берутся вершины — для трассы это изломы.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from shapely.geometry import LineString

MAX_LINES = 5000

# --- GPX ---------------------------------------------------------------------------------------

_NS = re.compile(r"^\{[^}]*\}")


def _local(tag: str) -> str:
    return _NS.sub("", tag)


def parse_gpx(content: bytes) -> tuple[list[dict[str, Any]], list[LineString], list[str]]:
    """GPX → (атрибуты, линии, предупреждения): каждый trkseg трека и каждый маршрут rte — линия."""
    from xml.etree import ElementTree as ET

    if b"<!DOCTYPE" in content[:2048] or b"<!ENTITY" in content[:4096]:
        raise ValueError("GPX с DOCTYPE/ENTITY не принимается")
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Не удалось прочитать GPX: {e}") from e
    if _local(root.tag) != "gpx":
        raise ValueError("Это не GPX (корневой элемент не <gpx>)")

    def name_of(el) -> Optional[str]:
        for ch in el:
            if _local(ch.tag) == "name" and (ch.text or "").strip():
                return ch.text.strip()
        return None

    def points(parent, tag: str) -> list[tuple[float, float]]:
        out = []
        for p in parent:
            if _local(p.tag) != tag:
                continue
            try:
                out.append((float(p.attrib["lon"]), float(p.attrib["lat"])))
            except (KeyError, ValueError):
                continue
        return out

    rows: list[dict[str, Any]] = []
    geoms: list[LineString] = []
    warnings: list[str] = []
    short = 0
    for el in root:
        tag = _local(el.tag)
        if tag == "trk":
            segs = [s for s in el if _local(s.tag) == "trkseg"]
            for i, seg in enumerate(segs, start=1):
                pts = points(seg, "trkpt")
                if len(pts) < 2:
                    short += 1
                    continue
                rows.append({"name": name_of(el), "type": "трек", "part": i if len(segs) > 1 else None})
                geoms.append(LineString(pts))
        elif tag == "rte":
            pts = points(el, "rtept")
            if len(pts) < 2:
                short += 1
                continue
            rows.append({"name": name_of(el), "type": "маршрут", "part": None})
            geoms.append(LineString(pts))
        if len(rows) > MAX_LINES:
            raise ValueError(f"В GPX больше {MAX_LINES} линий — разбейте импорт на части")
    if short:
        warnings.append(f"Пропущено линий меньше чем из двух точек: {short}")
    if not rows:
        raise ValueError("В GPX нет треков и маршрутов (точки wpt — не трасса)")
    return rows, geoms, warnings


# --- DXF ---------------------------------------------------------------------------------------

def _dxf_pairs(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    pairs = []
    for i in range(0, len(lines) - 1, 2):
        try:
            code = int(lines[i].strip())
        except ValueError as e:
            raise ValueError(f"DXF повреждён: строка {i + 1} — не код группы") from e
        pairs.append((code, lines[i + 1].strip()))
    return pairs


def _decode_dxf(content: bytes) -> str:
    if content.startswith(b"AutoCAD Binary DXF"):
        raise ValueError("Двоичный DXF не поддерживается — сохраните как текстовый DXF (ASCII)")
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Не удалось определить кодировку DXF")


def parse_dxf(content: bytes) -> tuple[list[dict[str, Any]], list[LineString], list[str]]:
    """DXF → (атрибуты, линии, предупреждения): LINE, LWPOLYLINE, POLYLINE (2D) из ENTITIES."""
    pairs = _dxf_pairs(_decode_dxf(content))
    # только секция ENTITIES
    start = end = None
    for i in range(len(pairs) - 1):
        if pairs[i] == (0, "SECTION") and pairs[i + 1] == (2, "ENTITIES"):
            start = i + 2
        elif start is not None and pairs[i] == (0, "ENDSEC") and i >= start:
            end = i
            break
    if start is None:
        raise ValueError("В DXF нет секции ENTITIES")
    ents = pairs[start:end]

    # разбить на сущности: (тип, [пары])
    entities: list[tuple[str, list[tuple[int, str]]]] = []
    for code, value in ents:
        if code == 0:
            entities.append((value, []))
        elif entities:
            entities[-1][1].append((code, value))

    rows: list[dict[str, Any]] = []
    geoms: list[LineString] = []
    skipped: dict[str, int] = {}

    def num(v: str) -> float:
        return float(v.replace(",", "."))

    def add(kind: str, data: list[tuple[int, str]], pts: list[tuple[float, float]], closed: bool) -> None:
        if closed and len(pts) > 2 and pts[0] != pts[-1]:
            pts = pts + [pts[0]]
        if len(pts) < 2:
            skipped[kind] = skipped.get(kind, 0) + 1
            return
        attrs = dict(data)
        rows.append({"layer": attrs.get(8), "entity": kind, "handle": attrs.get(5)})
        geoms.append(LineString(pts))
        if len(rows) > MAX_LINES:
            raise ValueError(f"В DXF больше {MAX_LINES} линий — разбейте импорт на части")

    i = 0
    while i < len(entities):
        kind, data = entities[i]
        try:
            if kind == "LINE":
                d = dict(data)
                add(kind, data, [(num(d[10]), num(d[20])), (num(d[11]), num(d[21]))], False)
            elif kind == "LWPOLYLINE":
                pts: list[tuple[float, float]] = []
                x: Optional[float] = None
                flags = 0
                for code, value in data:
                    if code == 70:
                        flags = int(value)
                    elif code == 10:
                        x = num(value)
                    elif code == 20 and x is not None:
                        pts.append((x, num(value)))
                        x = None
                add(kind, data, pts, bool(flags & 1))
            elif kind == "POLYLINE":
                flags = int(dict(data).get(70, "0") or 0)
                pts = []
                j = i + 1
                while j < len(entities) and entities[j][0] == "VERTEX":
                    v = dict(entities[j][1])
                    if 10 in v and 20 in v:
                        pts.append((num(v[10]), num(v[20])))
                    j += 1
                if flags & (16 | 64):  # 3D-сеть / многогранная сеть — не линии
                    skipped["POLYLINE (сеть)"] = skipped.get("POLYLINE (сеть)", 0) + 1
                else:
                    add(kind, data, pts, bool(flags & 1))
                i = j  # SEQEND обработается как неизвестная сущность
                continue
            elif kind not in ("SEQEND", "VERTEX"):
                skipped[kind] = skipped.get(kind, 0) + 1
        except (KeyError, ValueError):
            skipped[f"{kind} (ошибка)"] = skipped.get(f"{kind} (ошибка)", 0) + 1
        i += 1

    warnings = []
    if skipped:
        warnings.append("Пропущены объекты DXF: " + ", ".join(f"{k} — {v}" for k, v in sorted(skipped.items())))
    if not rows:
        raise ValueError("В DXF нет линий (LINE, LWPOLYLINE, POLYLINE)")
    return rows, geoms, warnings
