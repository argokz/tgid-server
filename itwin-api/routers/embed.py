"""Встраиваемые карты (database/embed.py).

GET    /api/v1/embed/keys                       — ключи встраивания города (администратор)
POST   /api/v1/embed/keys                       — новый ключ: сайты, слои, фрагменты, вид; ключ показывается один раз
DELETE /api/v1/embed/keys/{id}                  — отозвать ключ
GET    /api/v1/embed/config?key=                — без входа: слои, вид и сайты ключа для страницы веба /embed
GET    /api/v1/embed/tiles/{layer}/{z}/{x}/{y}?key= — без входа: MVT слоя сети (только поля без ПДн)

Ключ проверяется под собственной ролью пула API (таблицу ключей роль анонима не читает); тайлы — под ролью
анонима, как остальное открытое чтение.
"""
from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import Response

import activity
from auth import AuthUser, require_roles
from cities import city_label
from database import embed as em
from database.connect import acquire_conn
from database.db_role import NO_ROLE, reset_db_role, set_db_role
from routers.ogc import _network_extent
from routers.outages import public_enabled

router = APIRouter(tags=["embed"])
Admin = Annotated[AuthUser, Depends(require_roles("admin"))]
KeyId = Annotated[int, Path(ge=1)]
KeyParam = Annotated[Optional[str], Query(max_length=100)]
MVT = "application/vnd.mapbox-vector-tile"
TILE_MAX_AGE_S = 300


def _http(exc: em.EmbedError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


async def _audit(request: Request, user: AuthUser, action: str, details: dict[str, Any]) -> None:
    await activity.write(username=user.username, action=action, method=request.method, path=request.url.path,
                         status=200, details=details, ip=activity.client_ip(request.scope),
                         user_agent=request.headers.get("user-agent", "")[:300])


async def _embed_key(token: Optional[str]) -> em.EmbedKey:
    role = set_db_role(NO_ROLE)
    try:
        async with acquire_conn() as conn:
            key = await em.resolve(conn, token)
            await em.touch(conn, key)
            return key
    except em.EmbedError as exc:
        raise _http(exc) from exc
    finally:
        reset_db_role(role)


@router.get("/api/v1/embed/keys")
async def embed_keys(_: Admin) -> list[dict[str, Any]]:
    async with acquire_conn() as conn:
        return await em.list_keys(conn)


@router.post("/api/v1/embed/keys")
async def embed_key_create(body: em.KeyIn, request: Request, user: Admin) -> dict[str, Any]:
    async with acquire_conn() as conn:
        out = await em.create_key(conn, body, user.username)
    await _audit(request, user, "EMBED_KEY_CREATE", {"id": out["id"], "name": out["name"], "origins": out["origins"],
                                                     "layers": out["layers"]})
    return out


@router.delete("/api/v1/embed/keys/{key_id}")
async def embed_key_revoke(key_id: KeyId, request: Request, user: Admin) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            out = await em.revoke_key(conn, key_id, user.username)
    except em.EmbedError as exc:
        raise _http(exc) from exc
    await _audit(request, user, "EMBED_KEY_REVOKE", {"id": key_id, "name": out["name"]})
    return out


@router.get("/api/v1/embed/config")
async def embed_config(key: KeyParam = None) -> Response:
    k = await _embed_key(key)
    body = em.public_config(k, extent=await _network_extent(), city=city_label(), outages_enabled=public_enabled())
    return Response(json.dumps(body, ensure_ascii=False), media_type="application/json",
                    headers={"Cache-Control": "private, max-age=60"})


@router.get("/api/v1/embed/tiles/{layer}/{z}/{x}/{y}")
async def embed_tile(layer: Annotated[str, Path(max_length=20)], z: Annotated[int, Path(ge=0, le=em.MAX_ZOOM)],
                     x: Annotated[int, Path(ge=0)], y: Annotated[int, Path(ge=0)], key: KeyParam = None) -> Response:
    k = await _embed_key(key)
    try:
        async with acquire_conn() as conn:
            data = await em.tile(conn, k, layer, z, x, y)
    except em.EmbedError as exc:
        raise _http(exc) from exc
    cache = {"Cache-Control": f"public, max-age={TILE_MAX_AGE_S}"}
    if not data:
        return Response(status_code=204, headers=cache)
    return Response(data, media_type=MVT, headers=cache)
