"""Прогноз нагрузки по погоде (database/load_forecast.py) и температура воздуха (database/weather.py).

GET    /api/v1/forecast/load                 — погода по часам и сводка прогноза по источникам на сутки
GET    /api/v1/forecast/load/{source_id}     — источник по часам: нагрузка, температуры графика, факт по датчикам
POST   /api/v1/forecast/weather              — температура вручную (прогноз или факт) (право «Журналы»)
POST   /api/v1/forecast/weather/import       — файл «время; температура» (CSV / Excel) (право «Журналы»)
POST   /api/v1/forecast/weather/refresh      — обновить из Open-Meteo сейчас (право «Журналы»)
"""
from __future__ import annotations

from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import load_forecast, weather
from database import telemetry as tm
from database.connect import acquire_conn

router = APIRouter(tags=["forecast"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
WRITE = [Depends(require_mutations_enabled)]
MAX_FILE_BYTES = 5_000_000
NOT_READY = "Таблица погоды ещё создаётся (доводка базы города) — повторите через минуту"


@router.get("/api/v1/forecast/load")
async def forecast_overview(_: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        try:
            return await load_forecast.overview(conn)
        except asyncpg.UndefinedTableError as exc:
            raise HTTPException(status_code=503, detail=NOT_READY) from exc


@router.get("/api/v1/forecast/load/{source_id}")
async def forecast_source(
    _: Viewer,
    source_id: Annotated[int, Path(ge=1)],
    past_hours: Annotated[int, Query(ge=0, le=load_forecast.MAX_PAST_HOURS)] = 48,
    hours: Annotated[int, Query(ge=1, le=load_forecast.MAX_HOURS)] = 72,
) -> dict[str, Any]:
    async with acquire_conn() as conn:
        try:
            result = await load_forecast.detail(conn, source_id, past_hours=past_hours, hours=hours)
        except asyncpg.UndefinedTableError as exc:
            raise HTTPException(status_code=503, detail=NOT_READY) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Нет источника с расчётом нагрузок и температурным графиком")
    return result


@router.post("/api/v1/forecast/weather", dependencies=WRITE)
async def forecast_weather_manual(body: weather.WeatherIn, _: Writer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        stored = await weather.store(conn, [(r.ts, body.kind, r.t_air) for r in body.rows], "manual")
    return {"stored": stored, "kind": body.kind}


@router.post("/api/v1/forecast/weather/import", dependencies=WRITE)
async def forecast_weather_import(
    _: Writer,
    file: UploadFile = File(...),
    kind: Annotated[weather.Kind, Query()] = "forecast",
) -> dict[str, Any]:
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 5 МБ")
    try:
        readings, notes = tm.parse_file(data, file.filename or "weather.csv")
        rows = weather.rows_from_file(readings)
    except tm.TelemetryError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    except weather.WeatherError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    if not rows:
        raise HTTPException(status_code=422, detail="В файле нет строк «время; температура» от −70 до 60 °C")
    async with acquire_conn() as conn:
        stored = await weather.store(conn, [(ts, kind, t) for ts, t in rows], "file")
    return {"stored": stored, "kind": kind, "notes": notes,
            "from": rows[0][0].isoformat(), "to": rows[-1][0].isoformat()}


@router.post("/api/v1/forecast/weather/refresh", dependencies=WRITE)
async def forecast_weather_refresh(_: Writer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await weather.refresh(conn, force=True)
