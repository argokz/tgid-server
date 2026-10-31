"""Водопровод (database/water.py): модели EPANET, сеть на карте, расчёты отдельного движка (water_engine).

GET    /api/v1/water/status                     — движок доступен ли (версия WNTR)
GET    /api/v1/water/library                    — учебные сети EPANET движка
GET    /api/v1/water/models                     — модели водопровода города
POST   /api/v1/water/models                     — загрузить: учебная сеть {library} (право «Справочники»)
POST   /api/v1/water/models/upload              — загрузить файл .inp (srid — система координат файла)
DELETE /api/v1/water/models/{id}                — удалить модель с сетью и расчётами
POST   /api/v1/water/models/{id}/runs           — гидравлический расчёт (право «Расчёт»)
GET    /api/v1/water/models/{id}/runs           — расчёты модели
GET    /api/v1/water/models/{id}/geojson        — сеть для карты; run_id и step — значения на шаге расчёта
GET    /api/v1/water/models/{id}/runs/{run}/step — значения шага без геометрии (перемотка по времени)
GET    /api/v1/water/models/{id}/zones          — зоны водоучёта (DMA) между границами и расходомерами
PUT    /api/v1/water/models/{id}/meters         — расходомеры модели (трубы-вводы зон, право «Справочники»)
GET    /api/v1/water/models/{id}/runs/{run}/balance — баланс по зонам; сценарий утечки — против базового расчёта
GET    /api/v1/water/models/{id}/valves         — задвижки модели точками
POST   /api/v1/water/models/{id}/valves/generate — расставить задвижки «N−1» (право «Справочники»)
POST   /api/v1/water/models/{id}/isolation      — отключение трубы: задвижки, узлы без воды
POST   /api/v1/water/models/{id}/isolation/run  — то же с расчётом EPANET (отбор по давлению, право «Расчёт»)
POST   /api/v1/water/models/gis/inspect         — разбор файла ГИС: слои, поля, подсказки
POST   /api/v1/water/models/gis                 — сеть водоканала из ГИС (слой труб + задвижки) → модель EPANET
"""
from __future__ import annotations

import asyncio
import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, UploadFile
from pydantic import BaseModel, Field

from auth import AuthUser, require_mutations_enabled, require_permission, require_roles
from database import water, water_gis, water_isolation, water_zones
from database.network_import import parse_upload
from database.connect import acquire_conn

router = APIRouter(tags=["water"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Refs = Annotated[AuthUser, Depends(require_permission("refs"))]
Calc = Annotated[AuthUser, Depends(require_permission("calc_run"))]
WRITE = [Depends(require_mutations_enabled)]
ModelId = Annotated[int, Path(ge=1)]
MAX_INP_BYTES = 20_000_000


def _http(exc: water.WaterError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


class LibraryIn(BaseModel):
    library: str = Field(min_length=1, max_length=40)
    name: Optional[str] = Field(None, max_length=200)


class LeakIn(BaseModel):
    node: str = Field(min_length=1, max_length=64)
    area_cm2: float = Field(gt=0, le=500, description="Площадь отверстия, см²")


class RunIn(BaseModel):
    duration_h: Optional[float] = Field(None, ge=0, le=168)
    report_step_h: Optional[float] = Field(None, gt=0, le=24)
    leaks: list[LeakIn] = Field(default_factory=list, max_length=20, description="Сценарий утечек")


class IsolationIn(BaseModel):
    link_id: str = Field(min_length=1, max_length=64, description="Труба, которую отключают")


class MetersIn(BaseModel):
    links: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(max_length=water_zones.MAX_METERS)


@router.get("/api/v1/water/status")
async def water_status(_: Viewer) -> dict[str, Any]:
    try:
        health = await water.engine_call("GET", "/health")
        return {"available": True, "url": water.engine_url(), **health}
    except water.WaterError as exc:
        return {"available": False, "url": water.engine_url(), "error": exc.message}


@router.get("/api/v1/water/library")
async def water_library(_: Viewer) -> list[dict[str, Any]]:
    try:
        return await water.engine_call("GET", "/library")
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models")
async def water_models(_: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await water.list_models(conn)


@router.post("/api/v1/water/models", dependencies=WRITE)
async def water_import_library(body: LibraryIn, user: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water.import_model(conn, name=body.name, user=user.username, library=body.library)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/water/models/upload", dependencies=WRITE)
async def water_import_file(user: Refs, file: UploadFile = File(...), name: Optional[str] = Form(None),
                            srid: Optional[int] = Form(None, ge=1024, le=999999)) -> dict[str, Any]:
    data = await file.read(MAX_INP_BYTES + 1)
    if len(data) > MAX_INP_BYTES:
        raise HTTPException(status_code=413, detail="Файл больше 20 МБ")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("cp1251", errors="replace")
    try:
        async with acquire_conn() as conn:
            return await water.import_model(conn, name=name or file.filename, user=user.username, inp=text, srid=srid)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.delete("/api/v1/water/models/{model_id}", dependencies=WRITE)
async def water_delete(model_id: ModelId, _: Refs) -> dict[str, Any]:
    async with acquire_conn() as conn:
        if not await water.delete_model(conn, model_id):
            raise HTTPException(status_code=404, detail="Модель водопровода не найдена")
    return {"deleted": model_id}


@router.post("/api/v1/water/models/{model_id}/runs")
async def water_run(model_id: ModelId, body: RunIn, user: Calc) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water.run(conn, model_id, user=user.username, duration_h=body.duration_h,
                                    report_step_h=body.report_step_h,
                                    leaks=[leak.model_dump() for leak in body.leaks])
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models/{model_id}/runs")
async def water_runs(model_id: ModelId, _: Viewer) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await water.list_runs(conn, model_id)


@router.get("/api/v1/water/models/{model_id}/geojson")
async def water_geojson(model_id: ModelId, _: Viewer, run_id: Optional[int] = Query(None, ge=1),
                        step: int = Query(0, ge=0)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water.geojson(conn, model_id, run_id=run_id, step=step)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models/{model_id}/runs/{run_id}/step")
async def water_step(model_id: ModelId, run_id: Annotated[int, Path(ge=1)], _: Viewer,
                     step: int = Query(0, ge=0)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water.step_values(conn, model_id, run_id, step)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models/{model_id}/zones")
async def water_zones_get(model_id: ModelId, _: Viewer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_zones.zones(conn, model_id)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.put("/api/v1/water/models/{model_id}/meters", dependencies=WRITE)
async def water_meters_put(model_id: ModelId, body: MetersIn, _: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_zones.set_meters(conn, model_id, body.links)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models/{model_id}/runs/{run_id}/balance")
async def water_balance(model_id: ModelId, run_id: Annotated[int, Path(ge=1)], _: Viewer,
                        baseline: Optional[int] = Query(None, ge=1)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_zones.balance(conn, model_id, run_id, baseline)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.get("/api/v1/water/models/{model_id}/valves")
async def water_valves(model_id: ModelId, _: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        return await water_isolation.list_valves(conn, model_id)


@router.post("/api/v1/water/models/{model_id}/valves/generate", dependencies=WRITE)
async def water_valves_generate(model_id: ModelId, user: Refs) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_isolation.generate_valves(conn, model_id, user.username)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/water/models/{model_id}/isolation")
async def water_isolation_check(model_id: ModelId, body: IsolationIn, _: Viewer) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_isolation.isolation(conn, model_id, body.link_id)
    except water.WaterError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/water/models/{model_id}/isolation/run")
async def water_isolation_run(model_id: ModelId, body: IsolationIn, user: Calc) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await water_isolation.isolation_run(conn, model_id, body.link_id, user=user.username)
    except water.WaterError as exc:
        raise _http(exc) from exc


async def _files(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    out, total = [], 0
    for f in files:
        content = await f.read(MAX_INP_BYTES + 1)
        total += len(content)
        if total > MAX_INP_BYTES:
            raise HTTPException(status_code=413, detail="Загрузка больше 20 МБ")
        out.append((f.filename or "upload", content))
    return out


@router.post("/api/v1/water/models/gis/inspect")
async def water_gis_inspect(_: Refs, files: list[UploadFile] = File(...),
                            layer: Optional[str] = Form(None, max_length=200),
                            encoding: Optional[str] = Form(None, max_length=40)) -> dict[str, Any]:
    """Разбор файла ГИС для загрузки водопровода: слои, поля слоя труб, подсказки сопоставления."""
    try:
        src = await asyncio.to_thread(parse_upload, await _files(files), encoding=encoding or None,
                                      layer=layer or None, max_rows=water_gis.MAX_PIPES)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return water_gis.describe(src)


@router.post("/api/v1/water/models/gis", dependencies=WRITE)
async def water_import_gis(
    user: Refs,
    files: list[UploadFile] = File(..., description="слой труб: zip с shapefile, .gpkg, .geojson, .fgb, *.gdb в zip…"),
    valve_files: Optional[list[UploadFile]] = File(None, description="слой задвижек (точки), если отдельным файлом"),
    params: str = Form("{}", description="JSON: layer, valves_layer, diameter_field, material_field, id_field, "
                                         "status_field, default_diameter_mm, snap_m, total_demand_ls, elevation_m, "
                                         "source_head_m, source_lon, source_lat, valve_snap_m, encoding"),
    name: Optional[str] = Form(None, max_length=200),
    dry_run: bool = Form(True),
) -> dict[str, Any]:
    """Превью (dry_run: отчёт сборки, проверка движком) или загрузка сети водоканала из ГИС моделью EPANET."""
    try:
        raw = json.loads(params)
        if not isinstance(raw, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=400, detail="params — JSON-объект")
    encoding = str(raw.get("encoding") or "")[:40] or None
    pipe_files = await _files(files)
    try:
        pipes = await asyncio.to_thread(parse_upload, pipe_files, encoding=encoding,
                                        layer=str(raw.get("layer") or "")[:200] or None, max_rows=water_gis.MAX_PIPES)
        valves = None
        if valve_files:
            valves = await asyncio.to_thread(parse_upload, await _files(valve_files), encoding=encoding,
                                             max_rows=water_gis.MAX_PIPES)
        elif raw.get("valves_layer"):
            valves = await asyncio.to_thread(parse_upload, pipe_files, encoding=encoding,
                                             layer=str(raw["valves_layer"])[:200], max_rows=water_gis.MAX_PIPES)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        async with acquire_conn() as conn:
            return await water_gis.import_gis(conn, pipes_src=pipes, valves_src=valves, params=raw,
                                              name=name or (files[0].filename or None), user=user.username,
                                              dry_run=dry_run)
    except water.WaterError as exc:
        raise _http(exc) from exc
