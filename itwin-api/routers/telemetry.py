"""Телеметрия (database/telemetry.py): датчики, показания, «факт против модели».

GET    /api/v1/telemetry/units                — единицы и виды датчиков
GET    /api/v1/telemetry/sensors              — датчики с последним показанием, моделью и расхождением
GET    /api/v1/telemetry/sensors.geojson      — то же точками для карты
GET    /api/v1/telemetry/sensors/{id}/series  — показания за период (from, to) по интервалам
POST   /api/v1/telemetry/sensors              — добавить датчик (право «Справочники»)
PUT    /api/v1/telemetry/sensors/{id}         — изменить
DELETE /api/v1/telemetry/sensors/{id}         — удалить вместе с показаниями
POST   /api/v1/telemetry/import               — файл выгрузки ОДПУ (CSV / Excel) (право «Журналы»)
GET    /api/v1/telemetry/alerts               — тревоги: расхождение, молчит, вернулся в норму (open=true — непринятые
                                                и не закрытые возвратом в норму)
POST   /api/v1/telemetry/alerts/{id}/ack      — «принято» (право «Журналы»)
POST   /api/v2/telemetry/readings             — показания от шлюза SCADA пачкой (ключ API, право «Журналы»)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, Query, UploadFile

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import telemetry as tm
from database.connect import acquire_conn
from routers.api_v2 import api_user

router = APIRouter(tags=["telemetry"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Refs = Annotated[AuthUser, Depends(require_permission("refs"))]
Writer = Annotated[AuthUser, Depends(require_permission("journals"))]
WRITE = [Depends(require_mutations_enabled)]
SensorId = Annotated[int, Path(ge=1)]
MAX_FILE_BYTES = 20_000_000
DEFAULT_SERIES_HOURS = 24


def _http(exc: tm.TelemetryError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/telemetry/units")
async def telemetry_units(_: Viewer) -> dict[str, Any]:
    return {
        "kinds": [{"value": k, "label": v, "base_unit": tm.BASE_UNITS[k]} for k, v in tm.KIND_LABELS.items()],
        "pipes": [{"value": k, "label": v} for k, v in tm.PIPE_LABELS.items()],
        "units": [{"value": k, "kind": u.kind, "label": u.label} for k, u in tm.UNITS.items()],
        "thresholds": {"ok_pct": tm.OK_PCT, "warn_pct": tm.WARN_PCT, "ok_deg": tm.OK_DEG, "warn_deg": tm.WARN_DEG,
                       "stale_min": tm.STALE_MIN},
    }


@router.get("/api/v1/telemetry/sensors")
async def telemetry_sensors(_: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await tm.overview(conn)


@router.get("/api/v1/telemetry/sensors.geojson")
async def telemetry_geojson(_: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return tm.geojson(await tm.overview(conn, only_active=True))


@router.get("/api/v1/telemetry/sensors/{sensor_id}/series")
async def telemetry_series(sensor_id: SensorId, _: Viewer, start: Optional[datetime] = Query(None, alias="from"),
                           end: Optional[datetime] = Query(None, alias="to")) -> dict[str, Any]:
    end = end or datetime.now(timezone.utc)
    start = start or end - timedelta(hours=DEFAULT_SERIES_HOURS)
    try:
        async with acquire_conn() as conn:
            return await tm.series(conn, sensor_id, start, end)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/telemetry/sensors", dependencies=WRITE)
async def telemetry_sensor_create(body: tm.SensorIn, user: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await tm.create_sensor(conn, body, user.username)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc


@router.put("/api/v1/telemetry/sensors/{sensor_id}", dependencies=WRITE)
async def telemetry_sensor_update(sensor_id: SensorId, body: tm.SensorIn, _: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await tm.update_sensor(conn, sensor_id, body)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc


@router.delete("/api/v1/telemetry/sensors/{sensor_id}", dependencies=WRITE)
async def telemetry_sensor_delete(sensor_id: SensorId, _: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await tm.delete_sensor(conn, sensor_id)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/telemetry/import", dependencies=WRITE)
async def telemetry_import(_: Writer, file: UploadFile = File(...)) -> dict[str, Any]:
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 20 МБ — разбейте выгрузку")
    try:
        readings, notes = tm.parse_file(data, file.filename or "")
        async with acquire_conn() as conn:
            out = await tm.ingest(conn, readings)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc
    return {**out, "notes": notes}


@router.get("/api/v1/telemetry/alerts")
async def telemetry_alerts(_: Viewer, open: bool = False,  # noqa: A002 — имя параметра адреса
                           limit: int = Query(100, ge=1, le=tm.MAX_ALERTS)) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await tm.list_alerts(conn, limit=limit, open_only=open)


@router.post("/api/v1/telemetry/alerts/{alert_id}/ack", dependencies=WRITE)
async def telemetry_alert_ack(alert_id: Annotated[int, Path(ge=1)], user: Writer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await tm.acknowledge(conn, alert_id, user.username)
    except tm.TelemetryError as exc:
        raise _http(exc) from exc


@router.post("/api/v2/telemetry/readings", dependencies=WRITE, tags=["api-v2"])
async def telemetry_readings(body: tm.ReadingsIn, user: Annotated[AuthUser, Depends(api_user)]) -> dict[str, Any]:
    """Показания от шлюза SCADA: [{sensor: код, ts, value}] до 10 000 за запрос; время без пояса — местное."""
    if not user.perms.has("journals"):
        raise HTTPException(status_code=403, detail="Нет права «Журналы»")
    async with acquire_conn() as conn:
        return await tm.ingest(conn, [(r.sensor, r.ts, r.value) for r in body.readings])
