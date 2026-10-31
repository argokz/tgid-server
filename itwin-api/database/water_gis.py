"""Сеть водоканала из ГИС (SHP, GeoPackage и другие форматы GDAL) → модель EPANET (фаза 4, шаг 4).

В ГИС водоканала обычно есть трассы труб с диаметром и материалом, иногда задвижки точками — гидравлики нет. Модель
строится так:

- координаты — в метрах: зона UTM по центру сети (EPSG 326xx / 327xx), она же — система координат модели;
- узлы — концы труб, сшитые в пределах допуска (snap_m); конец трубы, лёгший на середину другой трубы в пределах
  допуска (Т-примыкание, частое в ГИС), режет её на две;
- связные части: components="largest" — в модель идёт часть с источником (по умолчанию — самая протяжённая),
  остальные отбрасываются (EPANET с узлами без источника не считает); components="each" — у каждой части свой
  источник: насосные в ГИС — точки, трубы через них не проходят, и зоны давления распадаются на части;
- источник — резервуар с напором: в заданной точке или на тупике самой крупной трубы части (ввод от водозабора,
  насосной); напор = отметка + source_head_m;
- диаметр — из поля (мм; значения меньше 5 — метры), нет — default_diameter_mm; шероховатость Хазена — Вильямса —
  по материалу (сталь, чугун — 100, ВЧШГ — 130, ПЭ и ПВХ — 140, асбестоцемент, бетон — 120, иначе 110);
- отбор — общий отбор сети (total_demand_ls), разнесённый по узлам пропорционально половине длины примыкающих
  труб, с типовым суточным графиком (условный, заменяется своим); отметки — одна на сеть (elevation_m): рельефа
  в ГИС нет, давления тогда — над этой отметкой;
- задвижки — точки второго слоя: на ближайшей трубе в пределах valve_snap_m у ближнего к точке конца.

Модель затем загружается как своя сеть (water.import_model, srid — зона UTM): узлы и трубы — на карту.
"""
from __future__ import annotations

import asyncio
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional

from database.water import WaterError, engine_call, import_model

MAX_PIPES = 50_000
SOURCE_SEARCH_M = 500.0
SMALL_DIAMETER_AS_METRES = 5.0   # диаметры меньше — в метрах (0,15 → 150 мм)
DEFAULT_C = 110
# (начала слов значения поля «материал», C Хазена — Вильямса); порядок важен: ВЧШГ раньше чугуна
MATERIAL_C: list[tuple[tuple[str, ...], int]] = [
    (("вчшг", "ductile"), 130),
    (("пэ", "pe", "hdpe", "полиэт", "pvc", "пвх", "нпвх", "пласт"), 140),
    (("чуг", "cast", "ci"), 100),
    (("асб", "asbest", "ac"), 120),
    (("бетон", "жб", "concrete"), 120),
    (("стал", "сталь", "ст", "steel"), 100),
]
CLOSED_VALUES = {"closed", "close", "закрыт", "закрыта", "закрыто", "off", "0", "false", "нет"}
# типовой бытовой суточный график отбора, 0–23 ч (условный, среднее 1,0)
DAILY_PATTERN = [0.55, 0.45, 0.4, 0.4, 0.45, 0.6, 0.9, 1.3, 1.45, 1.35, 1.2, 1.15,
                 1.1, 1.1, 1.05, 1.05, 1.1, 1.25, 1.45, 1.5, 1.35, 1.15, 0.9, 0.7]


@dataclass
class GisParams:
    diameter_field: Optional[str] = None
    material_field: Optional[str] = None
    id_field: Optional[str] = None
    status_field: Optional[str] = None
    default_diameter_mm: float = 100.0
    snap_m: float = 0.5
    total_demand_ls: float = 0.0
    elevation_m: float = 0.0
    source_head_m: float = 60.0
    source_lon: Optional[float] = None
    source_lat: Optional[float] = None
    valve_snap_m: float = 5.0
    components: str = "largest"     # largest — связная часть с источником; each — каждая часть со своим источником


def parse_params(raw: dict[str, Any]) -> GisParams:
    """Параметры загрузки с проверкой границ (ошибка — WaterError 422)."""
    def num(key: str, lo: float, hi: float, default: Optional[float]) -> Optional[float]:
        v = raw.get(key)
        if v in (None, ""):
            return default
        try:
            f = float(v)
        except (TypeError, ValueError) as exc:
            raise WaterError(422, f"{key} — число") from exc
        if not (lo <= f <= hi and math.isfinite(f)):
            raise WaterError(422, f"{key} — от {lo:g} до {hi:g}")
        return f

    def field(key: str) -> Optional[str]:
        v = raw.get(key)
        return str(v)[:200] if v not in (None, "") else None

    components = str(raw.get("components") or "largest")
    if components not in ("largest", "each"):
        raise WaterError(422, "components — largest или each")
    lon, lat = num("source_lon", -180, 180, None), num("source_lat", -90, 90, None)
    if (lon is None) != (lat is None):
        raise WaterError(422, "Точка источника — долгота и широта вместе")
    return GisParams(
        diameter_field=field("diameter_field"), material_field=field("material_field"), id_field=field("id_field"),
        status_field=field("status_field"),
        default_diameter_mm=num("default_diameter_mm", 10, 3000, 100.0),
        snap_m=num("snap_m", 0, 20, 0.5), total_demand_ls=num("total_demand_ls", 0, 1e6, 0.0),
        elevation_m=num("elevation_m", -500, 9000, 0.0), source_head_m=num("source_head_m", 1, 500, 60.0),
        source_lon=lon, source_lat=lat, valve_snap_m=num("valve_snap_m", 0, 50, 5.0), components=components)


# --- разбор файла: подсказки ------------------------------------------------------------------------

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "diameter_field": ("dn", "du", "ду", "d", "dmm", "dnmm", "diameter", "diametermm", "diam", "dia", "диаметр"),
    "material_field": ("material", "mat", "matl", "pipemat", "материал", "матер"),
    "id_field": ("id", "gid", "fid", "linkid", "pipeid", "номер", "код"),
    "status_field": ("status", "статус", "состояние", "state"),
}
VALVE_LAYER_WORDS = ("valve", "задв", "арм", "zadv", "gate")


def _key(name: str) -> str:
    return re.sub(r"[^0-9a-zа-яё]", "", str(name).lower())


def suggest_fields(columns: list[str]) -> dict[str, Optional[str]]:
    """Поля слоя труб по типичным именам: диаметр, материал, номер, состояние."""
    keys = {c: _key(c) for c in columns}
    out = {target: next((c for c in columns if keys[c] in aliases), None) for target, aliases in FIELD_ALIASES.items()}
    if out["id_field"] is None:  # ID_TR, PIPEID, TRUB_ID
        out["id_field"] = next((c for c in columns if keys[c].startswith("id") or keys[c].endswith("id")), None)
    return out


def suggest_valves_layer(layers: list[dict[str, Any]], pipes_layer: Optional[str]) -> Optional[str]:
    """Слой задвижек: точечный, по имени («valve», «задвижки», «арматура»), иначе единственный точечный."""
    points = [l["name"] for l in layers if l["name"] != pipes_layer and "point" in str(l.get("geometry_type")).lower()]
    named = [n for n in points if any(w in n.lower() for w in VALVE_LAYER_WORDS)]
    return named[0] if named else (points[0] if len(points) == 1 else None)


def describe(src) -> dict[str, Any]:
    """Разбор слоя для формы загрузки: слои файла, поля, образец, подсказки сопоставления."""
    return {
        "format": src.format, "layer": src.layer, "layers": src.source_layers, "columns": src.columns,
        "geometry_type": src.geometry_type, "crs": src.crs, "count": len(src.rows), "sample": src.rows[:3],
        "warnings": src.warnings, "suggested": {**suggest_fields(src.columns),
                                                "valves_layer": suggest_valves_layer(src.source_layers, src.layer)},
    }


# --- геометрия -----------------------------------------------------------------------------------

def utm_epsg(lon: float, lat: float) -> int:
    zone = min(60, max(1, int((lon + 180) // 6) + 1))
    return (32600 if lat >= 0 else 32700) + zone


def _lines(geom) -> list[list[tuple[float, float]]]:
    """Линии геометрии (LineString, MultiLineString); прочее — пусто."""
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [list(geom.coords)]
    if geom.geom_type == "MultiLineString":
        return [list(g.coords) for g in geom.geoms]
    return []


def material_c(value: Any) -> Optional[int]:
    """C Хазена — Вильямса по названию материала (None — материал не распознан)."""
    if value in (None, ""):
        return None
    tokens = [t for t in re.split(r"[^0-9a-zа-яё]+", str(value).lower().replace("/", "")) if t]
    for prefixes, c in MATERIAL_C:
        if any(_token_is(t, prefix) for t in tokens for prefix in prefixes):
            return c
    return None


def _token_is(token: str, prefix: str) -> bool:
    """Слово — материал: длинное начало («стал» → «стальная»); короткое (ПЭ, Ст) — целиком или с маркой (ПЭ100)."""
    if not token.startswith(prefix):
        return False
    rest = token[len(prefix):]
    return len(prefix) > 2 or not rest or rest.isdigit()


class _Snapper:
    """Узлы — концы труб, сшитые в пределах tol: сетка с шагом tol, поиск в соседних ячейках."""

    def __init__(self, tol: float):
        self.tol = max(tol, 1e-6)
        self.cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        self.xy: list[tuple[float, float]] = []

    def node(self, x: float, y: float) -> int:
        cx, cy = int(math.floor(x / self.tol)), int(math.floor(y / self.tol))
        best, best_d = None, self.tol
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for i in self.cells.get((cx + dx, cy + dy), ()):
                    d = math.dist(self.xy[i], (x, y))
                    if d <= best_d:
                        best, best_d = i, d
        if best is not None:
            return best
        self.xy.append((x, y))
        self.cells[(cx, cy)].append(len(self.xy) - 1)
        return len(self.xy) - 1


def build_network(geoms: list[Any], rows: list[dict[str, Any]], p: GisParams) -> dict[str, Any]:
    """Трубы ГИС (геометрии в WGS84 и атрибуты) → узлы и трубы модели в метрах UTM и отчёт о сборке."""
    from pyproj import Transformer
    from shapely import STRtree
    from shapely.geometry import LineString, Point
    from shapely.ops import substring

    raw = [(i, line) for i, g in enumerate(geoms) for line in _lines(g) if len(line) >= 2]
    skipped = sum(1 for g in geoms if not _lines(g))
    if not raw:
        raise WaterError(422, "В слое нет линий — нужен слой труб")
    if len(raw) > MAX_PIPES:
        raise WaterError(413, f"Труб больше {MAX_PIPES}")
    lons = [x for _, line in raw for x, _ in line]
    lats = [y for _, line in raw for _, y in line]
    lon0, lat0 = (min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2
    epsg = utm_epsg(lon0, lat0)
    to_m = Transformer.from_crs(4326, epsg, always_xy=True)

    # трубы в метрах с атрибутами строки
    pipes: list[dict[str, Any]] = []
    diam_values = [_float(rows[i].get(p.diameter_field)) for i, _ in raw] if p.diameter_field else []
    known = sorted(v for v in diam_values if v and v > 0)
    in_metres = bool(known) and known[len(known) // 2] < SMALL_DIAMETER_AS_METRES
    ids = [str(rows[i].get(p.id_field) or "").strip() for i, _ in raw] if p.id_field else []
    ids_ok = bool(ids) and all(ids) and len(set(ids)) == len(ids)
    missing_d, materials = 0, defaultdict(int)
    for k, (i, line) in enumerate(raw):
        xs, ys = to_m.transform([x for x, _ in line], [y for _, y in line])
        d = diam_values[k] if diam_values else None
        if not d or d <= 0:
            d, missing_d = p.default_diameter_mm, missing_d + 1
        elif in_metres:
            d *= 1000
        mat = rows[i].get(p.material_field) if p.material_field else None
        c = material_c(mat)
        materials[str(mat) if mat not in (None, "") else "—"] += 1
        status = str(rows[i].get(p.status_field) or "").strip().lower() if p.status_field else ""
        pipes.append({"name": _epanet_id(ids[k]) if ids_ok else f"P{k + 1}", "coords": list(zip(xs, ys)),
                      "diameter_mm": d, "c": c or DEFAULT_C, "closed": status in CLOSED_VALUES})

    # Т-примыкания: конец трубы на середине другой — режем ту трубу в точке проекции
    ends: dict[tuple[float, float], int] = defaultdict(int)
    snap = _Snapper(p.snap_m)
    for pipe in pipes:
        for xy in (pipe["coords"][0], pipe["coords"][-1]):
            ends[snap.xy[snap.node(*xy)]] += 1
    lines = [LineString(pipe["coords"]) for pipe in pipes]
    tree = STRtree(lines)
    cuts: dict[int, list[float]] = defaultdict(list)
    for xy, degree in ends.items():
        if degree != 1 or p.snap_m <= 0:
            continue
        pt = Point(xy)
        for j in tree.query(pt.buffer(p.snap_m)):
            line = lines[int(j)]
            if line.distance(pt) > p.snap_m:
                continue
            at = line.project(pt)
            if p.snap_m < at < line.length - p.snap_m:
                cuts[int(j)].append(at)
    split_count = 0
    if cuts:
        out = []
        for j, pipe in enumerate(pipes):
            if j not in cuts:
                out.append(pipe)
                continue
            marks = [0.0, *sorted(set(cuts[j])), lines[j].length]
            for n, (a, b) in enumerate(zip(marks, marks[1:]), start=1):
                piece = substring(lines[j], a, b)
                out.append({**pipe, "name": _epanet_id(f"{pipe['name']}-{n}"), "coords": list(piece.coords)})
            split_count += len(marks) - 2
        pipes = out

    # узлы и трубы; нулевые (оба конца — один узел) — в сторону
    snap = _Snapper(p.snap_m)
    zero = 0
    built = []
    for pipe in pipes:
        a, b = snap.node(*pipe["coords"][0]), snap.node(*pipe["coords"][-1])
        if a == b:
            zero += 1
            continue
        length = LineString(pipe["coords"]).length
        built.append({**pipe, "a": a, "b": b, "length_m": max(length, 0.01)})
    if not built:
        raise WaterError(422, "После сшивки концов не осталось труб — проверьте допуск")
    names = _unique([pipe["name"] for pipe in built])
    for pipe, name in zip(built, names):
        pipe["name"] = name

    # связные части (закрытые трубы связи не дают) и их источники
    comp = _component_of(built)
    by_comp: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for pipe in built:
        by_comp[comp[pipe["a"]]].append(pipe)
    order = sorted(by_comp, key=lambda c: -sum(q["length_m"] for q in by_comp[c]))
    sources: list[tuple[int, bool]] = []          # (узел, выбран сам)
    if p.source_lon is not None:
        sx, sy = to_m.transform(p.source_lon, p.source_lat)
        node, dist = min(((n, math.dist(snap.xy[n], (sx, sy))) for n in comp), key=lambda t: t[1])
        if dist > SOURCE_SEARCH_M:
            raise WaterError(422, f"Точка источника дальше {SOURCE_SEARCH_M:g} м от сети ({dist:.0f} м)")
        sources.append((node, False))
    taken = {comp[n] for n, _ in sources}
    wanted = order if p.components == "each" else order[:1]
    for c in wanted:
        if c not in taken:
            sources.append((_auto_source(by_comp[c]), True))
            taken.add(c)
    kept = [q for c in order if c in taken for q in by_comp[c]]
    dropped = len(built) - len(kept)

    # отбор по половине длины примыкающих труб
    source_nodes = {n for n, _ in sources}
    half: dict[int, float] = defaultdict(float)
    for pipe in kept:
        half[pipe["a"]] += pipe["length_m"] / 2
        half[pipe["b"]] += pipe["length_m"] / 2
    for n in source_nodes:
        half.pop(n, None)
    share_total = sum(half.values()) or 1.0
    node_ids = {n: f"J{k}" for k, n in enumerate(sorted({x for q in kept for x in (q["a"], q["b"])}), start=1)}
    for k, (n, _) in enumerate(sources, start=1):
        node_ids[n] = f"R{k}"
    from_m = Transformer.from_crs(epsg, 4326, always_xy=True)
    source_report = []
    for n, auto in sources:
        lon, lat = from_m.transform(*snap.xy[n])
        source_report.append({"node": node_ids[n], "auto": auto, "lon": round(lon, 7), "lat": round(lat, 7)})
    return {
        "epsg": epsg,
        "nodes": [{"id": node_ids[n], "x": snap.xy[n][0], "y": snap.xy[n][1],
                   "demand_ls": 0.0 if n in source_nodes else p.total_demand_ls * half[n] / share_total,
                   "source": n in source_nodes} for n in sorted(node_ids, key=lambda n: (n not in source_nodes, n))],
        "pipes": [{"id": q["name"], "a": node_ids[q["a"]], "b": node_ids[q["b"]], "length_m": q["length_m"],
                   "diameter_mm": q["diameter_mm"], "c": q["c"], "closed": q["closed"],
                   "vertices": q["coords"][1:-1]} for q in kept],
        "report": {
            "epsg": epsg, "lines_in": len(raw), "rows_without_lines": skipped, "t_splits": split_count,
            "zero_length_dropped": zero, "components": len(order), "kept_components": len(taken),
            "pipes": len(kept), "junctions": len(node_ids) - len(sources), "dropped_pipes": dropped,
            "length_km": round(sum(q["length_m"] for q in kept) / 1000, 3),
            "diameter": {"field_in_metres": in_metres, "missing": missing_d},
            "materials": dict(sorted(materials.items(), key=lambda kv: -kv[1])[:20]),
            "sources": source_report, "source_head_m": p.elevation_m + p.source_head_m, "components_mode": p.components,
            "total_demand_ls": p.total_demand_ls, "elevation_m": p.elevation_m,
        },
    }


def _component_of(pipes: list[dict[str, Any]]) -> dict[int, int]:
    """Узел → его связная часть (по открытым трубам; узел только с закрытыми трубами — часть сам по себе)."""
    parent: dict[int, int] = {}

    def find(x: int) -> int:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for q in pipes:
        a, b = find(q["a"]), find(q["b"])
        if not q["closed"] and a != b:
            parent[a] = b
    return {x: find(x) for x in list(parent)}


def _auto_source(pipes: list[dict[str, Any]]) -> int:
    """Источник части сети: тупик с самой крупной трубой (ввод от водозабора, насосной); тупиков нет — начало
    крупнейшей трубы."""
    degree: dict[int, int] = defaultdict(int)
    for q in pipes:
        degree[q["a"]] += 1
        degree[q["b"]] += 1
    dead_ends = [(q["diameter_mm"], q["length_m"], -n, n) for q in pipes for n in (q["a"], q["b"]) if degree[n] == 1]
    if dead_ends:
        return max(dead_ends)[3]
    return max(pipes, key=lambda q: (q["diameter_mm"], q["length_m"]))["a"]


def _float(v: Any) -> Optional[float]:
    try:
        f = float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _epanet_id(name: str) -> str:
    """Имя EPANET: без пробелов и «;», до 31 знака."""
    return re.sub(r"[\s;]+", "_", name)[:31] or "P"


def _unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for n in names:
        if n in seen:
            seen[n] += 1
            n = _epanet_id(f"{n[:26]}_{seen[n]}")
        seen.setdefault(n, 0)
        out.append(n)
    return out


# --- .inp ----------------------------------------------------------------------------------------

def to_inp(net: dict[str, Any], title: str, p: GisParams) -> str:
    """Модель EPANET (.inp): единицы — л/с и метры, потери — Хазен — Вильямс, сутки с шагом час."""
    out = ["[TITLE]", title[:79], "", "[JUNCTIONS]", ";ID  Elev  Demand  Pattern"]
    for n in net["nodes"]:
        if not n["source"]:
            out.append(f" {n['id']}  {p.elevation_m:.2f}  {n['demand_ls']:.5f}  1")
    out += ["", "[RESERVOIRS]", ";ID  Head"]
    out += [f" {n['id']}  {p.elevation_m + p.source_head_m:.2f}" for n in net["nodes"] if n["source"]]
    out += ["", "[PIPES]", ";ID  Node1  Node2  Length  Diameter  Roughness  MinorLoss  Status"]
    for q in net["pipes"]:
        status = "Closed" if q["closed"] else "Open"
        out.append(f" {q['id']}  {q['a']}  {q['b']}  {q['length_m']:.2f}  {q['diameter_mm']:.1f}  {q['c']}  0  {status}")
    out += ["", "[PATTERNS]", ";ID  Multipliers"]
    for k in range(0, len(DAILY_PATTERN), 6):
        out.append(" 1  " + "  ".join(f"{v:.2f}" for v in DAILY_PATTERN[k:k + 6]))
    out += ["", "[TIMES]", " Duration 24:00", " Hydraulic Timestep 1:00", " Pattern Timestep 1:00",
            " Report Timestep 1:00", "", "[OPTIONS]", " Units LPS", " Headloss H-W", "",
            "[COORDINATES]", ";Node  X  Y"]
    out += [f" {n['id']}  {n['x']:.3f}  {n['y']:.3f}" for n in net["nodes"]]
    out += ["", "[VERTICES]", ";Link  X  Y"]
    for q in net["pipes"]:
        out += [f" {q['id']}  {x:.3f}  {y:.3f}" for x, y in q["vertices"]]
    out += ["", "[END]", ""]
    return "\n".join(out)


# --- задвижки ------------------------------------------------------------------------------------

def match_valves(points: list[Any], net: dict[str, Any], snap_m: float) -> tuple[list[tuple[str, str]], int]:
    """Точки задвижек (WGS84) → (труба, узел): ближайшая труба в пределах snap_m, узел — её ближний к точке
    конец. → (пары, число не привязанных)."""
    from pyproj import Transformer
    from shapely import STRtree
    from shapely.geometry import LineString, Point

    to_m = Transformer.from_crs(4326, net["epsg"], always_xy=True)
    xy = {n["id"]: (n["x"], n["y"]) for n in net["nodes"]}
    lines = [LineString([xy[q["a"]], *q["vertices"], xy[q["b"]]]) for q in net["pipes"]]
    tree = STRtree(lines)
    pairs, missed = set(), 0
    for g in points:
        if g is None or g.is_empty or g.geom_type not in ("Point", "MultiPoint"):
            missed += 1
            continue
        pt0 = g if g.geom_type == "Point" else g.geoms[0]
        pt = Point(*to_m.transform(pt0.x, pt0.y))
        j = tree.nearest(pt)
        if j is None or lines[int(j)].distance(pt) > snap_m:
            missed += 1
            continue
        q, line = net["pipes"][int(j)], lines[int(j)]
        node = q["a"] if line.project(pt) <= line.length / 2 else q["b"]
        pairs.add((q["id"], node))
    return sorted(pairs), missed


# --- загрузка ------------------------------------------------------------------------------------

async def import_gis(conn, *, pipes_src, valves_src, params: dict[str, Any], name: Optional[str], user: str,
                     dry_run: bool) -> dict[str, Any]:
    """Слой труб (+ слой задвижек) → модель EPANET: проверка движком; dry_run — только отчёт."""
    if pipes_src.geometry_srid != 4326:
        raise WaterError(422, "В файле не указана система координат (.prj) — без неё трассы не перевести")
    p = parse_params(params)
    net = await asyncio.to_thread(build_network, pipes_src.geometries, pipes_src.rows, p)
    report = net["report"]
    pairs: list[tuple[str, str]] = []
    if valves_src is not None:
        if valves_src.geometry_srid != 4326:
            raise WaterError(422, "У слоя задвижек не указана система координат")
        pairs, missed = await asyncio.to_thread(match_valves, valves_src.geometries, net, p.valve_snap_m)
        report["valves"] = {"points": len(valves_src.geometries), "matched": len(pairs), "missed": missed}
    title = (name or "Сеть водоканала из ГИС")[:200]
    inp = to_inp(net, title, p)
    parsed = await engine_call("POST", "/parse", {"inp": inp})  # проверка: EPANET читает модель
    report["engine"] = {k: parsed["summary"].get(k) for k in ("Nodes", "Links", "Patterns")}
    if dry_run:
        return {"dry_run": True, "report": report}
    model = await import_model(conn, name=title, user=user, inp=inp, srid=net["epsg"])
    if pairs:
        from database.water_isolation import insert_valves

        await insert_valves(conn, model["id"], pairs, "gis", user)
    await conn.execute(
        "UPDATE tgid_water_model SET source = 'gis', summary = summary || jsonb_build_object('gis_import', $2::jsonb)"
        " WHERE id = $1", model["id"], json.dumps(report))
    return {"dry_run": False, "report": report, "model": model}
