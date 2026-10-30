"""FeatureServer по GeoServices REST (database/arcgis_features.py): слои сети для ArcGIS-клиентов, только чтение.

GET      /api/arcgis/rest/info                                   — версия, способ входа
GET      /api/arcgis/rest/services                               — каталог: один сервис TGID
GET      /api/arcgis/rest/services/TGID/FeatureServer            — сервис: слои, охват
GET      /api/arcgis/rest/services/TGID/FeatureServer/layers     — все слои с полями
GET      /api/arcgis/rest/services/TGID/FeatureServer/{n}        — слой: поля, тип геометрии, охват
GET/POST /api/arcgis/rest/services/TGID/FeatureServer/{n}/query  — объекты (Esri JSON или GeoJSON)
POST     /api/v1/arcgis/token                                    — ключ для ArcGIS-клиента (только чтение этих адресов)

Вход: ключ параметром token (так подключают ArcGIS Online, ArcGIS Pro, QGIS) или заголовком Bearer. Ключ ArcGIS
(scope arcgis) действует только здесь и закрывается сменой пароля; обычный токен входа тоже принимается.
Ошибки — как у ArcGIS Server: HTTP 200 и {"error": {"code", "message"}} (клиенты читают только тело).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

import activity
from auth import (
    AuthUser,
    apply_live_user_status,
    auth_disabled,
    bind_db_role,
    create_access_token,
    decode_access_token,
    get_current_user,
    jwt_algorithm,
    jwt_secret,
)
from cities import city_label
from database import arcgis_features as af
from database.connect import acquire_conn
from routers.mcp import PASSWORD_CLAIM, _password_fingerprint
from routers.ogc import _network_extent, _root

router = APIRouter(tags=["arcgis"])

ARCGIS_SCOPE = "arcgis"
DEFAULT_TOKEN_DAYS = 90
MAX_TOKEN_DAYS = 365
SERVICE = "/api/arcgis/rest/services/TGID/FeatureServer"


def token_days() -> int:
    try:
        days = int(os.getenv("ARCGIS_TOKEN_DAYS", str(DEFAULT_TOKEN_DAYS)))
    except ValueError:
        days = DEFAULT_TOKEN_DAYS
    return max(1, min(MAX_TOKEN_DAYS, days))


class _EsriError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _error(code: int, message: str) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, "details": []}})


async def _arcgis_user(request: Request) -> AuthUser:
    """Ключ из ?token= или Bearer; ключ ArcGIS — только здесь и пока не сменён пароль."""
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    token = request.query_params.get("token") or ""
    header = request.headers.get("authorization") or ""
    if not token and header.lower().startswith("bearer "):
        token = header.split(" ", 1)[1].strip()
    if not token and request.method == "POST":
        form = await request.form()
        token = str(form.get("token") or "")
    if not token:
        raise _EsriError(499, "Нужен ключ: параметр token (выдаётся в веб-приложении: Учётная запись → ArcGIS и QGIS)")
    try:
        user = await apply_live_user_status(decode_access_token(token, allow_scopes=(ARCGIS_SCOPE,)))
    except HTTPException as exc:
        raise _EsriError(498, f"Ключ не принят: {exc.detail}") from exc
    if user.scope == ARCGIS_SCOPE:
        claim = str(jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()]).get(PASSWORD_CLAIM) or "")
        try:
            current = await _password_fingerprint(user.sub)
        except Exception as exc:  # noqa: BLE001 — долгий ключ без проверки не пускаем
            raise _EsriError(498, "Не удалось проверить ключ — попробуйте позже") from exc
        if current is not None and claim != current:
            raise _EsriError(498, "Пароль сменён — выдайте новый ключ ArcGIS")
    bind_db_role(user)
    return user


async def _args(request: Request) -> dict[str, Any]:
    args: dict[str, Any] = dict(request.query_params)
    if request.method == "POST":
        args.update({k: v for k, v in (await request.form()).items() if isinstance(v, str)})
    return args


async def _guarded(request: Request, handler) -> JSONResponse:
    try:
        await _arcgis_user(request)
        return JSONResponse(await handler(await _args(request)))
    except _EsriError as exc:
        return _error(exc.code, exc.message)
    except af.ArcgisError as exc:
        return _error(exc.code, exc.message)


@router.get("/api/arcgis/rest/info")
async def arcgis_info(request: Request):
    return {
        "currentVersion": af.CURRENT_VERSION,
        "fullVersion": "10.8.1",
        "owningSystemUrl": _root(request),
        "authInfo": {"isTokenBasedSecurity": False},
    }


@router.get("/api/arcgis/rest/services")
async def arcgis_services(request: Request):
    async def build(_: dict[str, Any]) -> dict[str, Any]:
        return {"currentVersion": af.CURRENT_VERSION, "folders": [],
                "services": [{"name": "TGID", "type": "FeatureServer", "url": f"{_root(request)}{SERVICE}"}]}
    return await _guarded(request, build)


@router.get(SERVICE)
async def arcgis_service(request: Request):
    async def build(_: dict[str, Any]) -> dict[str, Any]:
        return af.service_info(await _network_extent(), f"Сеть теплоснабжения ТГИД: {city_label()}. Только чтение.")
    return await _guarded(request, build)


@router.get(SERVICE + "/layers")
async def arcgis_layers(request: Request):
    async def build(_: dict[str, Any]) -> dict[str, Any]:
        extent = await _network_extent()
        return {"layers": [af.layer_info(cid, extent) for cid in af.LAYERS], "tables": []}
    return await _guarded(request, build)


@router.get(SERVICE + "/{layer_id}")
async def arcgis_layer(request: Request, layer_id: int):
    async def build(_: dict[str, Any]) -> dict[str, Any]:
        return af.layer_info(af.collection_of(layer_id), await _network_extent())
    return await _guarded(request, build)


@router.api_route(SERVICE + "/{layer_id}/query", methods=["GET", "POST"])
async def arcgis_query(request: Request, layer_id: int):
    async def build(args: dict[str, Any]) -> dict[str, Any]:
        cid = af.collection_of(layer_id)
        fmt = str(args.get("f") or "json").lower()
        if fmt == "geojson":
            args = {**args, "outSR": "4326"}  # GeoJSON — всегда WGS84
        q = af.build_query(cid, args)
        async with acquire_conn() as conn:
            if str(args.get("returnCountOnly", "")).lower() == "true":
                return {"count": await af.count(conn, cid, q)}
            if str(args.get("returnIdsOnly", "")).lower() == "true":
                return {"objectIdFieldName": af.OID, "objectIds": await af.ids(conn, cid, q)}
            rows, more = await af.features(conn, cid, q)
        return af.to_geojson(rows, more) if fmt == "geojson" else af.to_esri_json(cid, q, rows, more)
    return await _guarded(request, build)


@router.post("/api/v1/arcgis/token")
async def arcgis_token(request: Request, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Ключ для ArcGIS-клиента на ARCGIS_TOKEN_DAYS дней: читает только слои FeatureServer, с правами пользователя;
    у пользователя UsersDB смена пароля закрывает ключ."""
    days = token_days()
    extra: dict[str, Any] = {"scope": ARCGIS_SCOPE}
    if user.mv:
        extra["mv"] = user.mv
    fingerprint = await _password_fingerprint(user.sub)
    if fingerprint:
        extra[PASSWORD_CLAIM] = fingerprint
    token = create_access_token(username=user.username, role=user.role, subject=user.sub,
                                expires_minutes=days * 24 * 60, extra=extra)
    await activity.write(username=user.username, action="ARCGIS_TOKEN", method="POST", path="/api/v1/arcgis/token",
                         status=200, details={"days": days}, ip=activity.client_ip(request.scope),
                         user_agent=request.headers.get("user-agent", "")[:300])
    return {
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds"),
        "days": days,
        "service_url": f"{_root(request)}{SERVICE}",
    }

