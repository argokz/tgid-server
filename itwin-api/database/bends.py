"""Отводы участка по его геометрии → «Местные сопротивления» паспорта (heatPipeSections.mestn/localResSum).

Углы поворота считаются по вершинам линии (linesObj.shape) в метрах на земле (WGS84 → местная
равнопромежуточная проекция, одинаково для всех городов, в том числе для Шатуры с Меркатором под 9998).
Мелкие изломы не считаются отводами: вершины ближе MIN_SEGMENT_M к предыдущей сливаются, повороты меньше
MIN_ANGLE_DEG отбрасываются.

Угол поворота относится к ближайшему стандартному отводу справочника десктопа (sql/sp/s08.sql, MestSopr3):
22,5° / 30° / 45° / 60° / 90°; поворот больше 135° — два отвода 90°. Вид отвода (сварной, гнутый, число
швов) выбирает оператор, по умолчанию — сварные одношовные (90° — двухшовный). Коэффициент — минимальное
значение справочника, как пишет окно десктопа.

Запись — не здесь: клиент сохраняет mestn и localResSum обычной правкой карточки (PUT card-edit: версия
строки → 409, audit_log), формат mestn — «id|количество|коэффициент» через пробел.
"""

from __future__ import annotations

import math
from typing import Optional

MIN_ANGLE_DEG = 10.0
MIN_SEGMENT_M = 0.5
# класс отвода (стандартный угол) → id справочника s08: по умолчанию и допустимые
BEND_CLASSES: dict[int, dict] = {
    # 22 — «Колено 22.5 сварное (1 шов)»
    22: {"title": "22,5°", "default": 22, "options": [22]},
    # 53 — «Отводы сварные одношовные под углом 30 Град.»
    30: {"title": "30°", "default": 53, "options": [53]},
    45: {"title": "45°", "default": 54, "options": [54, 23, 24]},
    60: {"title": "60°", "default": 55, "options": [55, 25, 26, 27]},
    # 56 — «Отводы сварные двухшовные под углом 90 Град.»
    90: {"title": "90°", "default": 56, "options": [56, 57, 28, 29, 50, 51, 52, 48, 49, 18, 19, 20, 21]},
}
# все отводы и колена справочника — режим «заменить отводы» убирает их из списка перед записью
BEND_ITEM_IDS = frozenset(i for c in BEND_CLASSES.values() for i in c["options"])
# границы классов по углу поворота (середины между стандартными углами)
_CLASS_EDGES = ((26.25, 22), (37.5, 30), (52.5, 45), (75.0, 60))
EARTH_R = 6371008.8


def bend_class(angle: float) -> tuple[int, int]:
    """Угол поворота → (класс, число отводов)."""
    if angle > 135.0:
        return 90, 2
    for edge, cls in _CLASS_EDGES:
        if angle <= edge:
            return cls, 1
    return 90, 1


def _to_xy(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if not points:
        return []
    lat0 = math.radians(sum(p[1] for p in points) / len(points))
    k = math.cos(lat0)
    return [(math.radians(lng) * EARTH_R * k, math.radians(lat) * EARTH_R) for lng, lat in points]


def compute_bends(
    points: list[tuple[float, float]],
    min_angle: float = MIN_ANGLE_DEG,
    min_segment: float = MIN_SEGMENT_M,
) -> list[dict]:
    """Повороты линии (lng, lat) → [{vertex, angle, lng, lat, cls, count}] по ходу линии.

    vertex — номер вершины исходной линии (с 0); вершины ближе min_segment к предыдущей
    оставленной сливаются (концы линии не сдвигаются).
    """
    xy = _to_xy(points)
    if len(xy) < 3:
        return []
    kept = [0]
    for i in range(1, len(xy)):
        a = xy[kept[-1]]
        if math.hypot(xy[i][0] - a[0], xy[i][1] - a[1]) >= min_segment:
            kept.append(i)
        elif i == len(xy) - 1 and len(kept) > 1:
            kept[-1] = i  # последняя точка рядом с изломом — конец линии важнее
    if kept[-1] != len(xy) - 1:
        kept.append(len(xy) - 1)
    out = []
    for j in range(1, len(kept) - 1):
        p0, p1, p2 = xy[kept[j - 1]], xy[kept[j]], xy[kept[j + 1]]
        a1 = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
        a2 = math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        d = abs(math.degrees(a2 - a1)) % 360.0
        angle = 360.0 - d if d > 180.0 else d
        if angle < min_angle:
            continue
        cls, count = bend_class(angle)
        lng, lat = points[kept[j]]
        out.append({"vertex": kept[j], "angle": round(angle, 1), "lng": lng, "lat": lat, "cls": cls, "count": count})
    return out


def bend_counts(bends: list[dict]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for b in bends:
        counts[b["cls"]] = counts.get(b["cls"], 0) + b["count"]
    return counts


def parse_mestn(text: Optional[str]) -> list[tuple[int, float, float]]:
    """«id|k|v id|k|v» → [(id, k, v)] (MestSopr3::parse; битые части пропускаются)."""
    out = []
    for part in str(text or "").split():
        kv = part.split("|")
        if len(kv) != 3:
            continue
        try:
            out.append((int(kv[0]), float(kv[1]), float(kv[2])))
        except ValueError:
            continue
    return out


async def line_bends(conn, line_id: int) -> dict:
    """Отводы участка, паспорта (его и парной трубы) с текущими местными сопротивлениями, справочник."""
    from database.card_edit import local_resistances
    from database.topology import find_pair_line

    row = await conn.fetchrow(
        "SELECT id, shape IS NOT NULL AS has_shape FROM linesobj WHERE id = $1 AND COALESCE(removed, 0) = 0", line_id,
    )
    if row is None:
        raise LookupError(f"Участок {line_id} не найден или удалён")
    pts = [
        (float(r["lng"]), float(r["lat"]))
        for r in await conn.fetch(
            """
            SELECT ST_X(g) AS lng, ST_Y(g) AS lat FROM (
              SELECT (dp).path[1] AS i, ST_Transform((dp).geom, 4326) AS g
                FROM (SELECT ST_DumpPoints(shape) AS dp FROM linesobj WHERE id = $1) s
            ) p ORDER BY i
            """,
            line_id,
        )
    ] if row["has_shape"] else []
    bends = compute_bends(pts)
    pair = await find_pair_line(conn, line_id)
    ids = [line_id] + ([pair["line_id"]] if pair else [])
    passports = [
        {
            "line_id": r["lineid"], "id": r["id"], "mestn": r["mestn"] or "",
            "localressum": r["localressum"], "version": r["v"],
        }
        for r in await conn.fetch(
            "SELECT lineid, id, mestn, localressum, xmin::text AS v FROM heatpipesections "
            "WHERE lineid = ANY($1::int[]) ORDER BY array_position($1::int[], lineid), id",
            ids,
        )
    ]
    items = {i["id"]: i for i in await local_resistances(conn)}
    counts = bend_counts(bends)
    classes = [
        {
            "cls": cls, "title": c["title"], "count": counts.get(cls, 0), "default": c["default"],
            "options": [
                {"id": i, "name": items[i]["name"], "v": items[i]["min"]} for i in c["options"] if i in items
            ],
        }
        for cls, c in BEND_CLASSES.items()
    ]
    return {
        "line_id": line_id,
        "pair_line_id": pair["line_id"] if pair else None,
        "has_shape": bool(row["has_shape"]),
        "vertices": len(pts),
        "bends": bends,
        "classes": classes,
        "bend_item_ids": sorted(i for i in BEND_ITEM_IDS if i in items),
        "items": {str(i): {"name": v["name"], "v": v["min"]} for i, v in items.items()},
        "passports": passports,
        "thresholds": {"min_angle_deg": MIN_ANGLE_DEG, "min_segment_m": MIN_SEGMENT_M},
    }
