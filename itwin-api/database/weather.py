"""Температура наружного воздуха по часам для прогноза нагрузки (фаза 3): прогноз и факт (tgid_weather).

Источники:
- Open-Meteo (open-meteo.com, без ключа) — WEATHER_PROVIDER=open-meteo (по умолчанию; none — выключить).
  Сервер запрашивает почасовую температуру на 2 м по координатам города (WEATHER_LAT / WEATHER_LON, иначе —
  центр источников тепла города): прошедшие часы (WEATHER_PAST_DAYS) пишутся как факт (модельный анализ
  Open-Meteo, не метеостанция), будущие (WEATHER_FORECAST_DAYS) — как прогноз. Обновление — при запросе прогноза,
  если данным больше WEATHER_REFRESH_MIN; нет связи — работает с тем, что уже записано.
- вручную и файлом (CSV / Excel «время; температура») — значения диспетчера важнее Open-Meteo: не перезаписываются.
"""
from __future__ import annotations

import logging
import math
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

import httpx
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)

Kind = Literal["forecast", "fact"]
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
PROVIDER = (os.getenv("WEATHER_PROVIDER", "open-meteo") or "none").strip().lower()
REFRESH_MIN = max(10, int(os.getenv("WEATHER_REFRESH_MIN", "60") or 60))
PAST_DAYS = min(92, max(0, int(os.getenv("WEATHER_PAST_DAYS", "3") or 3)))
FORECAST_DAYS = min(16, max(1, int(os.getenv("WEATHER_FORECAST_DAYS", "3") or 3)))
HTTP_TIMEOUT_S = 15
RETRY_AFTER_FAIL_S = 300   # нет связи с Open-Meteo — не спрашивать на каждом открытии окна
T_AIR_RANGE = (-70.0, 60.0)
MAX_ROWS = 20_000

_last_attempt: dict[str, float] = {}   # город → monotonic последней попытки (неудачной тоже)
_coords: dict[str, tuple[float, float]] = {}


class WeatherError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class WeatherRow(BaseModel):
    ts: datetime
    t_air: float = Field(ge=T_AIR_RANGE[0], le=T_AIR_RANGE[1])

    @field_validator("ts")
    @classmethod
    def _hour(cls, v: datetime) -> datetime:
        return hour_utc(v)


class WeatherIn(BaseModel):
    kind: Kind = "forecast"
    rows: list[WeatherRow] = Field(min_length=1, max_length=MAX_ROWS)


def hour_utc(ts: datetime) -> datetime:
    """Начало часа в UTC; время без пояса — местное время сервера города (как выгрузки ОДПУ в телеметрии)."""
    if ts.tzinfo is None:
        ts = ts.astimezone()
    return ts.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)


def _city() -> str:
    try:
        from cities import current_city
        return current_city() or ""
    except Exception:  # noqa: BLE001 — один город без cities: ключ кеша пустой
        return ""


async def coordinates(conn) -> Optional[tuple[float, float]]:
    """(широта, долгота) города: WEATHER_LAT / WEATHER_LON или центр узлов источников тепла."""
    lat, lon = os.getenv("WEATHER_LAT"), os.getenv("WEATHER_LON")
    if lat and lon:
        return float(lat), float(lon)
    city = _city()
    if city in _coords:
        return _coords[city]
    row = await conn.fetchrow(
        """SELECT ST_Y(c) AS lat, ST_X(c) AS lon FROM (
               SELECT ST_Transform(ST_Centroid(ST_Collect(n.shape)), 4326) AS c
                 FROM heatsources hs JOIN nodes n ON n.id = hs.nodeid
                WHERE coalesce(n.removed, 0) = 0 AND n.shape IS NOT NULL) q""")
    if not row or row["lat"] is None:
        return None
    _coords[city] = (round(row["lat"], 4), round(row["lon"], 4))
    return _coords[city]


def parse_open_meteo(data: dict[str, Any], now: datetime) -> list[tuple[datetime, str, float]]:
    """Ответ Open-Meteo (timezone=UTC) → (час, вид, температура); прошедшие часы — факт, будущие — прогноз."""
    hourly = data.get("hourly") or {}
    times, temps = hourly.get("time") or [], hourly.get("temperature_2m") or []
    if len(times) != len(temps):
        raise ValueError("Open-Meteo: разная длина time и temperature_2m")
    current = hour_utc(now)
    out = []
    for t, v in zip(times, temps):
        if v is None or not isinstance(v, (int, float)) or not math.isfinite(v):
            continue
        if not (T_AIR_RANGE[0] <= v <= T_AIR_RANGE[1]):
            continue
        ts = hour_utc(datetime.fromisoformat(t).replace(tzinfo=timezone.utc))  # timezone=UTC в запросе
        out.append((ts, "fact" if ts < current else "forecast", float(v)))
    return out


async def fetch_open_meteo(lat: float, lon: float, client: Optional[httpx.AsyncClient] = None) -> dict[str, Any]:
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m", "timezone": "UTC",
              "past_days": PAST_DAYS, "forecast_days": FORECAST_DAYS}
    own = client is None
    http = client or httpx.AsyncClient(timeout=HTTP_TIMEOUT_S, follow_redirects=False)
    try:
        resp = await http.get(OPEN_METEO_URL, params=params)
        resp.raise_for_status()
        return resp.json()
    finally:
        if own:
            await http.aclose()


async def store(conn, rows: list[tuple[datetime, str, float]], source: str) -> int:
    """Запись по часам; значения диспетчера (manual, file) Open-Meteo не перезаписывает."""
    if not rows:
        return 0
    await conn.executemany(
        """INSERT INTO tgid_weather (ts, kind, t_air, source, issued_at) VALUES ($1, $2, $3, $4, now())
           ON CONFLICT (ts, kind) DO UPDATE SET t_air = excluded.t_air, source = excluded.source,
                                                issued_at = excluded.issued_at
            WHERE tgid_weather.source = 'open-meteo' OR excluded.source <> 'open-meteo'""",
        [(ts, kind, t, source) for ts, kind, t in rows])
    return len(rows)


async def last_update(conn) -> Optional[datetime]:
    return await conn.fetchval("SELECT max(issued_at) FROM tgid_weather WHERE source = 'open-meteo'")


async def refresh(conn, *, force: bool = False) -> dict[str, Any]:
    """Обновить из Open-Meteo, если данные старше REFRESH_MIN (или force); ошибки — в ответ, не исключением."""
    state: dict[str, Any] = {"provider": PROVIDER, "updated_at": None, "error": None, "lat": None, "lon": None}
    if PROVIDER != "open-meteo":
        return state
    coords = await coordinates(conn)
    if coords is None:
        state["error"] = "нет координат города: задайте WEATHER_LAT и WEATHER_LON"
        return state
    state["lat"], state["lon"] = coords
    last = await last_update(conn)
    state["updated_at"] = last.isoformat() if last else None
    fresh = last is not None and last > datetime.now(timezone.utc) - timedelta(minutes=REFRESH_MIN)
    city = _city()
    recently_tried = time.monotonic() - _last_attempt.get(city, -1e9) < RETRY_AFTER_FAIL_S
    if not force and (fresh or recently_tried):
        return state
    _last_attempt[city] = time.monotonic()
    try:
        rows = parse_open_meteo(await fetch_open_meteo(*coords), datetime.now(timezone.utc))
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Open-Meteo: %s", exc)
        state["error"] = f"Open-Meteo недоступен: {type(exc).__name__}"
        return state
    await store(conn, rows, "open-meteo")
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["rows"] = len(rows)
    return state


async def hourly(conn, start: datetime, end: datetime) -> list[dict[str, Any]]:
    """По часам [start, end): факт там, где он есть, иначе прогноз."""
    rows = await conn.fetch(
        """SELECT DISTINCT ON (ts) ts, kind, t_air, source FROM tgid_weather
            WHERE ts >= $1 AND ts < $2 ORDER BY ts, (kind = 'fact') DESC""", start, end)
    return [{"ts": r["ts"], "kind": r["kind"], "t_air": r["t_air"], "source": r["source"]} for r in rows]


def rows_from_file(readings: list[tuple[str, datetime, float]]) -> list[tuple[datetime, float]]:
    """Показания из выгрузки (telemetry.parse_file) → (час, температура): одна колонка температуры, среднее за час."""
    codes = {code for code, _, _ in readings}
    if len(codes) > 1:
        raise WeatherError(422, f"В файле несколько колонок значений ({', '.join(sorted(codes)[:5])}) — "
                                "нужна одна: «время; температура»")
    acc: dict[datetime, list[float]] = {}
    for _, ts, v in readings:
        if T_AIR_RANGE[0] <= v <= T_AIR_RANGE[1]:
            acc.setdefault(hour_utc(ts), []).append(v)
    return [(ts, round(sum(vs) / len(vs), 2)) for ts, vs in sorted(acc.items())]
