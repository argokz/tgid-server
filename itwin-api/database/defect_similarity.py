"""Похожие аварии рядом и места повторных отказов (фаза 3): гибридный поиск по журналу дефектов.

Тексты дефектов короткие и профессиональные («Порыв на Т1 Ду 273», «Свищ 2Ду100 по Т2 на 7 часов»): похожесть в них
определяют вид повреждения, труба, диаметр и место, а не общий смысл фразы. Поэтому сходство — сумма признаков:
- вид повреждения по словарю (порыв, свищ, утечка, коррозия, изоляция, арматура, камера, реконструкция);
  порыв / свищ / утечка — одно семейство «потеря воды» (частичное совпадение);
- труба (Т1 — подача, Т2 — обратка) и условный диаметр (Ду…, … мм);
- расстояние (затухание exp(−d / DIST_SCALE_M));
- общие слова — полнотекстовый поиск PostgreSQL с русским стеммингом (без расширений).
Векторный поиск (pgvector) — когда будет выбрана модель эмбеддингов: расширение на сервере есть, тексты для модели
дают мало (короткие, терминологические).

Места повторных отказов — скопления дефектов семейства «потеря воды» за YEARS лет: ST_ClusterDBSCAN с радиусом
CLUSTER_EPS_M и не меньше CLUSTER_MIN дефектов; ближайший участок теплосети (в пределах LINE_SNAP_M) — Ду, год
прокладки. Дефекты в журнале часто без участка (lineid): в копии Астаны участок указан у 106 из 1785 — привязка по
месту закрывает этот пробел.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Any, Optional

DIST_SCALE_M = 300.0
DEFAULT_RADIUS_M = 1000.0
MAX_RADIUS_M = 20_000.0
MAX_CANDIDATES = 500
CLUSTER_EPS_M = 30.0
CLUSTER_MIN = 3
MIN_DAYS = 2      # отказы скопления — в разные дни
YEARS = 5
LINE_SNAP_M = 20.0
WEIGHTS = {"kind": 0.35, "pipe": 0.15, "diameter": 0.15, "distance": 0.2, "text": 0.15}

# (вид, семейство, подписи корней)
KINDS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("rupture", "water", ("порыв", "разрыв", "прорыв")),
    ("fistula", "water", ("свищ",)),
    ("leak", "water", ("утечк", "течь", "парит", "парени", "подтоп", "подпитк")),
    ("corrosion", "metal", ("корроз", "утонен", "ржав")),
    ("insulation", "insulation", ("изоляц", "ппу", "теплоизол")),
    ("valve", "equipment", ("задвиж", "кран", "сальник", "арматур", "компенсатор")),
    ("chamber", "structure", ("камер", "люк", "провал", "плит", "перекрыт", "колодц")),
    ("reconstruction", "works", ("реконструкц", "перекладк", "капремонт", "капитальн", "инвест", "замен")),
)
KIND_LABELS = {"rupture": "порыв", "fistula": "свищ", "leak": "утечка", "corrosion": "коррозия",
               "insulation": "изоляция", "valve": "арматура", "chamber": "камера", "reconstruction": "работы"}
WATER_KINDS = tuple(k for k, fam, _ in KINDS if fam == "water")
_FAMILY = {k: fam for k, fam, _ in KINDS}
_DIAM_RE = re.compile(r"(?:ду|dn|d)\s*[=:]?\s*(\d{2,4})|(\d{2,4})\s*мм", re.IGNORECASE)
_SUPPLY_RE = re.compile(r"\bт\s*-?\s*1\b|подающ|подач|под\.", re.IGNORECASE)
_RETURN_RE = re.compile(r"\bт\s*-?\s*2\b|обратн|обр\.", re.IGNORECASE)
_TWO_PIPES_RE = re.compile(r"\b2\s*-?\s*х?\s*ду", re.IGNORECASE)


def features(text: str) -> dict[str, Any]:
    """Вид повреждения, труба и наибольший условный диаметр из текста дефекта."""
    low = (text or "").lower().replace("ё", "е")
    kind = next((k for k, _, roots in KINDS if any(r in low for r in roots)), None)
    supply, ret = bool(_SUPPLY_RE.search(low)), bool(_RETURN_RE.search(low))
    pipe = "both" if (supply and ret) or _TWO_PIPES_RE.search(low) else "supply" if supply else "return" if ret else None
    diameters = [int(a or b) for a, b in _DIAM_RE.findall(low)]
    diameters = [d for d in diameters if 15 <= d <= 1600]
    return {"kind": kind, "pipe": pipe, "diameter": max(diameters) if diameters else None}


def _as_date(v: Any):
    return v.date() if isinstance(v, datetime) else v


def kind_score(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return 0.6 if _FAMILY[a] == _FAMILY[b] else 0.0


def pipe_score(a: Optional[str], b: Optional[str]) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    return 0.5 if "both" in (a, b) else 0.0


def diameter_score(a: Optional[int], b: Optional[int]) -> float:
    if not a or not b:
        return 0.0
    ratio = max(a, b) / min(a, b)
    return 1.0 if ratio <= 1.05 else 0.5 if ratio <= 1.35 else 0.0


def score(ref: dict[str, Any], cand: dict[str, Any], distance_m: Optional[float], text_rank: float,
          max_rank: float) -> dict[str, Any]:
    """Сходство кандидата с образцом (0…1) и причины — словами."""
    parts = {
        "kind": kind_score(ref["kind"], cand["kind"]),
        "pipe": pipe_score(ref["pipe"], cand["pipe"]),
        "diameter": diameter_score(ref["diameter"], cand["diameter"]),
        "distance": math.exp(-distance_m / DIST_SCALE_M) if distance_m is not None else 0.0,
        "text": text_rank / max_rank if max_rank > 0 else 0.0,
    }
    total = sum(WEIGHTS[k] * v for k, v in parts.items())
    reasons = []
    if parts["kind"] == 1.0:
        reasons.append(f"тот же вид — {KIND_LABELS[cand['kind']]}")
    elif parts["kind"] > 0:
        reasons.append(f"похожий вид — {KIND_LABELS[cand['kind']]}")
    if parts["pipe"] == 1.0:
        reasons.append({"supply": "Т1", "return": "Т2", "both": "обе трубы"}[cand["pipe"]])
    if parts["diameter"] == 1.0:
        reasons.append(f"Ду{cand['diameter']}")
    elif parts["diameter"] > 0:
        reasons.append(f"близкий Ду{cand['diameter']}")
    if distance_m is not None:
        reasons.append(f"{distance_m:.0f} м")
    if parts["text"] >= 0.5:
        reasons.append("общие слова")
    return {"score": round(total, 3), "parts": {k: round(v, 2) for k, v in parts.items()}, "reasons": reasons}


_TEXT = "concat_ws(' ', d.name, d.defectdescription, d.otchet_po_defektu, d.primechanie)"
_PARTS = "ARRAY[d.name, d.defectdescription, d.otchet_po_defektu, d.primechanie]"


def display_text(parts: list[Optional[str]]) -> str:
    """Части записи без повторов: описание, отчёт и примечание в журнале часто дословно совпадают."""
    seen: list[str] = []
    for part in parts:
        text = (part or "").strip()
        if text and not any(text.lower() in s.lower() for s in seen):
            seen = [s for s in seen if s.lower() not in text.lower()] + [text]
    return " · ".join(seen)
# Рамка поиска в проекции таблицы: квадрат радиуса r вокруг точки 4326 через 3857 (растяжение 1/cos широты, запас
# 10 %) — так работает GiST-индекс по shape при любых единицах местной проекции; точное расстояние — по геодезии.
_BOX = ("ST_Transform(ST_Expand(ST_Transform({pt}, 3857), {r} * 1.1 / cos(radians(ST_Y({pt})))), {srid})")


async def _srid(conn, table: str) -> Optional[int]:
    return await conn.fetchval(f"SELECT ST_SRID(shape) FROM {table} WHERE shape IS NOT NULL LIMIT 1")  # noqa: S608


async def _query_for(conn, text: str) -> Optional[str]:
    """Слова текста → запрос «любое из слов» для to_tsquery (лексемы — через стемминг PostgreSQL)."""
    return await conn.fetchval(
        """SELECT string_agg(quote_literal(lex), ' | ')
             FROM unnest(tsvector_to_array(to_tsvector('russian', $1))) lex
            WHERE length(lex) > 1""", text or "")


async def reference(conn, defect_id: int) -> Optional[dict[str, Any]]:
    row = await conn.fetchrow(
        f"""SELECT d.id, {_TEXT} AS text, {_PARTS} AS parts, d.data_osmotra AS detected_at, d.lineid,
                   CASE WHEN d.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(d.shape, 4326)) END AS lon,
                   CASE WHEN d.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(d.shape, 4326)) END AS lat
              FROM defect d WHERE d.id = $1""", defect_id)
    if not row:
        return None
    ref = dict(row)
    ref["parts"] = list(ref["parts"] or [])
    ref["detected_at"] = ref["detected_at"].isoformat() if ref["detected_at"] else None
    return ref


async def similar(conn, text: str, *, lon: Optional[float] = None, lat: Optional[float] = None,
                  radius_m: float = DEFAULT_RADIUS_M, exclude_id: Optional[int] = None,
                  limit: int = 20) -> dict[str, Any]:
    """Дефекты, похожие на текст (и место, если задано): кандидаты — в радиусе или по общим словам."""
    ref = features(text)
    query = await _query_for(conn, text)
    point = lon is not None and lat is not None
    srid = await _srid(conn, "defect")
    if srid is None:
        return {"reference": ref, "radius_m": None, "candidates": 0, "items": []}
    box = _BOX.format(pt="ST_SetSRID(ST_MakePoint($2, $3), 4326)", r="$5", srid=int(srid))
    rows = await conn.fetch(
        f"""WITH q AS (SELECT CASE WHEN $1::text IS NULL THEN NULL ELSE to_tsquery('russian', $1) END AS q),
                 p AS (SELECT CASE WHEN $2::float IS NULL THEN NULL
                                   ELSE ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography END AS g,
                              CASE WHEN $2::float IS NULL THEN NULL ELSE {box} END AS box)
            SELECT d.id, d.lineid, d.data_osmotra AS detected_at, {_TEXT} AS text, {_PARTS} AS parts,
                   ST_X(ST_Transform(d.shape, 4326)) AS lon, ST_Y(ST_Transform(d.shape, 4326)) AS lat,
                   CASE WHEN p.g IS NULL THEN NULL
                        ELSE ST_Distance(ST_Transform(d.shape, 4326)::geography, p.g) END AS distance_m,
                   CASE WHEN q.q IS NULL THEN 0 ELSE ts_rank_cd(to_tsvector('russian', {_TEXT}), q.q) END AS rank
              FROM defect d, q, p
             WHERE d.shape IS NOT NULL AND ($4::int IS NULL OR d.id <> $4)
               AND CASE WHEN p.g IS NOT NULL THEN d.shape && p.box
                                                  AND ST_DWithin(ST_Transform(d.shape, 4326)::geography, p.g, $5)
                        WHEN q.q IS NOT NULL THEN to_tsvector('russian', {_TEXT}) @@ q.q
                        ELSE false END
             ORDER BY distance_m NULLS LAST, rank DESC
             LIMIT {MAX_CANDIDATES}""",
        query, lon if point else None, lat if point else None, exclude_id, radius_m)
    max_rank = max((r["rank"] for r in rows), default=0.0)
    found = []
    for r in rows:
        cand = features(r["text"])
        s = score(ref, cand, r["distance_m"], r["rank"], max_rank)
        if s["score"] <= 0:
            continue
        found.append({"id": r["id"], "line_id": r["lineid"],
                      "detected_at": r["detected_at"].isoformat() if r["detected_at"] else None,
                      "text": display_text(r["parts"])[:400], "lon": r["lon"], "lat": r["lat"],
                      "distance_m": round(r["distance_m"], 1) if r["distance_m"] is not None else None,
                      "features": cand, **s})
    found.sort(key=lambda f: -f["score"])
    return {"reference": ref, "radius_m": radius_m if point else None, "candidates": len(rows),
            "items": found[:limit]}


async def hotspots(conn, *, years: int = YEARS, eps_m: float = CLUSTER_EPS_M, min_count: int = CLUSTER_MIN,
                   now: Optional[datetime] = None) -> list[dict[str, Any]]:
    """Скопления отказов «потеря воды» за years лет — кандидаты на перекладку, с ближайшим участком."""
    now = now or datetime.now()
    since = now.replace(year=now.year - years)
    rows = await conn.fetch(
        f"""SELECT d.id, d.lineid, d.data_osmotra AS at, {_TEXT} AS text,
                   ST_Transform(d.shape, 4326) AS g4326
              FROM defect d
             WHERE d.shape IS NOT NULL AND (d.data_osmotra IS NULL OR d.data_osmotra >= $1)""", since)
    water = [r for r in rows if features(r["text"])["kind"] in WATER_KINDS]
    if len(water) < min_count:
        return []
    ids = [r["id"] for r in water]
    # кластеризация в метрах: 3857 растянута на 1/cos(широты) — радиус масштабируется по широте центра
    clusters = await conn.fetch(
        """WITH pts AS (SELECT d.id, ST_Transform(d.shape, 3857) AS g FROM defect d WHERE d.id = ANY($1::int[])),
                k AS (SELECT 1 / cos(radians(ST_Y(ST_Transform(ST_Centroid(ST_Collect(g)), 4326)))) AS f FROM pts)
           SELECT pts.id, ST_ClusterDBSCAN(pts.g, eps := $2 * k.f, minpoints := $3) OVER () AS cid
             FROM pts, k""", ids, eps_m, min_count)
    by_cluster: dict[int, list[int]] = {}
    for c in clusters:
        if c["cid"] is not None:
            by_cluster.setdefault(c["cid"], []).append(c["id"])
    info = {r["id"]: r for r in water}
    line_srid = await _srid(conn, "linesobj")
    box = _BOX.format(pt="c.g4326", r="$2", srid=int(line_srid or 4326))
    out = []
    for members in by_cluster.values():
        line = None if line_srid is None else await conn.fetchrow(
            f"""WITH c AS (SELECT ST_Transform(ST_Centroid(ST_Collect(shape)), 4326) AS g4326
                           FROM defect WHERE id = ANY($1::int[]))
               SELECT l.id, h.diametercondit::float AS diameter, h.pipesectlength::float AS length_m,
                      coalesce(h.lasttransdate, h.firstpicdatehp) AS laid,
                      ST_Distance(ST_Transform(l.shape, 4326)::geography, c.g4326::geography) AS d
                 FROM c, linesobj l LEFT JOIN heatpipesections h ON h.lineid = l.id
                WHERE coalesce(l.removed, 0) = 0 AND l.shape && {box}
                  AND ST_DWithin(ST_Transform(l.shape, 4326)::geography, c.g4326::geography, $2)
                ORDER BY d LIMIT 1""", members, LINE_SNAP_M)
        center = await conn.fetchrow(
            """SELECT ST_X(c) AS lon, ST_Y(c) AS lat FROM (
                   SELECT ST_Transform(ST_Centroid(ST_Collect(shape)), 4326) AS c FROM defect WHERE id = ANY($1::int[])) q""",
            members)
        dates = sorted(info[i]["at"] for i in members if info[i]["at"])
        days = len({d.date() for d in dates})
        if days < MIN_DAYS:  # одна авария, записанная несколько раз, — не повторные отказы
            continue
        kinds: dict[str, int] = {}
        for i in members:
            k = features(info[i]["text"])["kind"]
            kinds[KIND_LABELS[k]] = kinds.get(KIND_LABELS[k], 0) + 1
        laid = line["laid"] if line else None
        last = dates[-1] if dates else None
        out.append({
            "defects": sorted(members), "count": len(members), "days": days, "kinds": kinds,
            # участок переложен уже после последнего отказа — скопление, скорее всего, снято перекладкой
            "replaced_after": bool(laid and last and _as_date(laid) > last.date()),
            "first": dates[0].isoformat() if dates else None, "last": dates[-1].isoformat() if dates else None,
            "lon": center["lon"], "lat": center["lat"],
            "line": None if line is None else {
                "id": line["id"], "diameter": line["diameter"], "length_m": line["length_m"],
                "laid": line["laid"].isoformat() if line["laid"] else None, "distance_m": round(line["d"], 1)},
            "linked_in_journal": sum(1 for i in members if info[i]["lineid"]),
        })
    out.sort(key=lambda h: (h["count"], h["last"] or ""), reverse=True)  # больше отказов, затем свежее
    return out
