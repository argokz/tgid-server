"""Трек бригады из полевого приложения (фаза 2): где бригада сейчас и где была.

Телефон снимает точку, пока на странице бригады включено «Передавать местоположение» (не чаще раза в минуту
или через 25 м), копит точки без связи и отправляет пачкой. Ключ точки — пользователь и время снятия: повтор
пачки не дублирует точки. Таблица веба tgid_field_track (sql/migrations/20261030_field_track.sql), точки
старше TRACK_KEEP_DAYS удаляются при записи новых — местоположение сотрудников дольше не нужно.

Геозона «бригада на месте»: точка бригады не дальше ARRIVAL_RADIUS_M от места её открытого наряда (у обхода —
от любого участка контура осмотра) отмечает в наряде время прибытия (arrived_at) и событие в истории — один раз.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

TRACK_KEEP_DAYS = 90
MAX_POINTS = 500                      # точек в одной отправке
MAX_CLOCK_AHEAD = timedelta(minutes=10)  # часы телефона могут спешить
POSITION_MAX_AGE_H = 12               # «где бригады сейчас» — последняя точка не старше
MAX_WINDOW = timedelta(days=7)        # трек — не больше недели за запрос
MAX_TRACK_POINTS = 20_000
TRACK_GAP = timedelta(minutes=15)     # перерыв дольше — новый отрезок трека (не тянуть линию через город)
ARRIVAL_RADIUS_M = 100.0              # бригада у места работ: GPS телефона в городе — 5–30 м
_ARRIVAL_STATUSES = ["assigned", "in_progress"]
_EARTH_R = 6_371_008.8


class TrackError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class TrackPoint(BaseModel):
    t: datetime = Field(..., description="Когда снята на телефоне")
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    accuracy: Optional[float] = Field(None, ge=0, le=100_000, description="Точность GPS, м")


class TrackIn(BaseModel):
    brigade_id: Optional[int] = Field(None, ge=1, description="Бригада, выбранная на телефоне")
    points: list[TrackPoint] = Field(..., min_length=1, max_length=MAX_POINTS)


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Расстояние по сфере между (lon, lat), м."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * _EARTH_R * math.asin(min(1.0, math.sqrt(h)))


def split_segments(points: list[dict[str, Any]], gap: timedelta = TRACK_GAP) -> list[list[dict[str, Any]]]:
    """Точки одного пользователя по времени → отрезки: перерыв дольше gap начинает новый."""
    segments: list[list[dict[str, Any]]] = []
    for p in points:
        if segments and p["recorded_at"] - segments[-1][-1]["recorded_at"] <= gap:
            segments[-1].append(p)
        else:
            segments.append([p])
    return segments


async def add_points(conn, body: TrackIn, user: str, now: Optional[datetime] = None) -> dict[str, int]:
    """Записать пачку; точки из будущего и старше срока хранения пропускаются (часы телефона, старая очередь)."""
    now = now or datetime.now(timezone.utc)
    keep_from = now - timedelta(days=TRACK_KEEP_DAYS)
    good = [p for p in body.points if keep_from <= _aware(p.t) <= now + MAX_CLOCK_AHEAD]
    brigade_id = body.brigade_id
    if brigade_id and not await conn.fetchval("SELECT EXISTS (SELECT 1 FROM brigades WHERE id = $1)", brigade_id):
        brigade_id = None  # бригаду удалили из справочника, пока телефон копил точки — точки всё равно нужны
    accepted = 0
    async with conn.transaction():
        if good:
            accepted = await conn.fetchval(
                """WITH ins AS (
                       INSERT INTO tgid_field_track (by_user, brigade_id, recorded_at, lon, lat, accuracy)
                       SELECT $1, $2, t.at, t.lon, t.lat, t.acc
                         FROM unnest($3::timestamptz[], $4::float8[], $5::float8[], $6::real[]) AS t(at, lon, lat, acc)
                       ON CONFLICT (by_user, recorded_at) DO NOTHING
                       RETURNING 1)
                   SELECT count(*) FROM ins""",
                user, brigade_id, [_aware(p.t) for p in good], [p.lon for p in good], [p.lat for p in good],
                [p.accuracy for p in good])
        await conn.execute("DELETE FROM tgid_field_track WHERE recorded_at < $1", keep_from)
        arrived = await mark_arrivals(conn, brigade_id, good, user) if brigade_id and good else []
    return {"accepted": int(accepted or 0), "skipped": len(body.points) - len(good), "arrived": arrived}


def _place_sql(with_contour: bool) -> str:
    """Место наряда для геозоны: участки контура осмотра (обход) или точка наряда."""
    point = "ST_SetSRID(ST_MakePoint(o.lon, o.lat), 4326)"
    if not with_contour:
        return point
    contour = (f"(SELECT ST_Collect(ST_Transform(l.shape, 4326)) FROM osmotrdeployed r JOIN linesobj l ON l.id = r.lineid"
               f" WHERE r.directionid = o.inspection_id AND l.shape IS NOT NULL)")
    return f"COALESCE({contour}, {point})"


async def mark_arrivals(conn, brigade_id: int, points: list[TrackPoint], user: str) -> list[str]:
    """Открытые наряды бригады, у места которых есть точка пачки: время прибытия и событие «Бригада на месте»."""
    with_contour = bool(await conn.fetchval("SELECT to_regclass('public.osmotrdeployed') IS NOT NULL"))
    good = [p for p in points if p.accuracy is None or p.accuracy <= ARRIVAL_RADIUS_M]
    if not good:
        return []
    rows = await conn.fetch(
        f'''WITH p AS (SELECT * FROM unnest($2::timestamptz[], $3::float8[], $4::float8[]) AS t(at, lon, lat)),
                 o AS (SELECT o.id, o.number, {_place_sql(with_contour)} AS g
                         FROM tgid_work_order o
                        WHERE o.brigade_id = $1 AND o.status = ANY($5::text[]) AND o.arrived_at IS NULL
                          AND (o.lon IS NOT NULL OR o.inspection_id IS NOT NULL))
            SELECT o.id, o.number, min(p.at) AS at, (array_agg(p.lon ORDER BY p.at))[1] AS lon,
                   (array_agg(p.lat ORDER BY p.at))[1] AS lat
              FROM o JOIN p ON ST_DWithin(o.g::geography, ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326)::geography, $6)
             WHERE o.g IS NOT NULL
             GROUP BY o.id, o.number''',
        brigade_id, [_aware(p.t) for p in good], [p.lon for p in good], [p.lat for p in good],
        _ARRIVAL_STATUSES, ARRIVAL_RADIUS_M)
    arrived = []
    for r in rows:
        status = await conn.execute(
            "UPDATE tgid_work_order SET arrived_at = $2 WHERE id = $1 AND arrived_at IS NULL", r["id"], r["at"])
        if not str(status).endswith(" 1"):
            continue
        local = r["at"].astimezone().strftime("%H:%M")
        await conn.execute(
            """INSERT INTO tgid_work_order_event (order_id, at, by_user, note, lon, lat)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            r["id"], r["at"], user, f"Бригада на месте в {local} (по треку телефона)", r["lon"], r["lat"])
        arrived.append(r["number"])
    return arrived


async def positions(conn, *, hours: int = POSITION_MAX_AGE_H, now: Optional[datetime] = None) -> dict[str, Any]:
    """Последняя точка каждого, кто передавал местоположение за последние hours часов."""
    now = now or datetime.now(timezone.utc)
    rows = await conn.fetch(
        """SELECT DISTINCT ON (t.by_user) t.by_user, t.brigade_id, b.name AS brigade_name, t.recorded_at,
                  t.lon, t.lat, t.accuracy
             FROM tgid_field_track t LEFT JOIN brigades b ON b.id = t.brigade_id
            WHERE t.recorded_at >= $1
            ORDER BY t.by_user, t.recorded_at DESC""", now - timedelta(hours=hours))
    features = []
    for r in rows:
        name = (r["brigade_name"] or "").strip() or (f"Бригада {r['brigade_id']}" if r["brigade_id"] else "")
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": {
                "kind": "brigade", "by_user": r["by_user"], "brigade_id": r["brigade_id"],
                "brigade_name": name or r["by_user"], "recorded_at": r["recorded_at"].isoformat(),
                "age_min": max(0, int((now - r["recorded_at"]).total_seconds() // 60)), "accuracy": r["accuracy"],
            },
        })
    return {"type": "FeatureCollection", "features": features}


async def track(conn, *, brigade_id: Optional[int] = None, by_user: Optional[str] = None,
                since: Optional[datetime] = None, until: Optional[datetime] = None,
                now: Optional[datetime] = None) -> dict[str, Any]:
    """Трек за период (по умолчанию — последние сутки) линиями: отрезок на каждый непрерывный кусок."""
    if not brigade_id and not by_user:
        raise TrackError(422, "Укажите бригаду или пользователя")
    now = now or datetime.now(timezone.utc)
    until = _aware(until) if until else now
    since = _aware(since) if since else until - timedelta(days=1)
    if since >= until:
        raise TrackError(422, "Начало периода позже конца")
    if until - since > MAX_WINDOW:
        raise TrackError(422, f"Период — не больше {MAX_WINDOW.days} дней")
    where, args = ["t.recorded_at >= $1", "t.recorded_at <= $2"], [since, until]
    if brigade_id:
        args.append(brigade_id)
        where.append(f"t.brigade_id = ${len(args)}")
    if by_user:
        args.append(by_user)
        where.append(f"t.by_user = ${len(args)}")
    rows = await conn.fetch(
        f"""SELECT t.by_user, t.brigade_id, t.recorded_at, t.lon, t.lat FROM tgid_field_track t
             WHERE {' AND '.join(where)} ORDER BY t.by_user, t.recorded_at LIMIT {MAX_TRACK_POINTS + 1}""", *args)
    truncated = len(rows) > MAX_TRACK_POINTS
    by_person: dict[str, list[dict[str, Any]]] = {}
    for r in rows[:MAX_TRACK_POINTS]:
        by_person.setdefault(r["by_user"], []).append(dict(r))
    features = []
    for person, points in by_person.items():
        for seg in split_segments(points):
            coords = [[p["lon"], p["lat"]] for p in seg]
            length = sum(distance_m(tuple(a), tuple(b)) for a, b in zip(coords, coords[1:]))
            features.append({
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords} if len(coords) > 1
                else {"type": "Point", "coordinates": coords[0]},
                "properties": {"kind": "track", "by_user": person, "brigade_id": seg[-1]["brigade_id"],
                               "from": seg[0]["recorded_at"].isoformat(), "to": seg[-1]["recorded_at"].isoformat(),
                               "points": len(seg), "length_m": round(length)},
            })
    return {"type": "FeatureCollection", "features": features, "truncated": truncated,
            "since": since.isoformat(), "until": until.isoformat()}
