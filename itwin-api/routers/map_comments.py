"""Комментарии на карте (database/map_comments.py).

GET    /api/v1/map-comments                 — ветки (status: open/resolved/all, scope: all/mine, q), счётчики, непрочитанное
GET    /api/v1/map-comments/geojson         — ветки точками для слоя карты
GET    /api/v1/map-comments/unread          — сколько веток с новыми сообщениями для меня
GET    /api/v1/map-comments/people          — кого можно упомянуть (@логин)
GET    /api/v1/map-comments/{id}            — ветка с сообщениями (отмечается прочитанной)
POST   /api/v1/map-comments                 — новая ветка в точке
POST   /api/v1/map-comments/{id}/comments   — ответ (в решённой ветке — открывает её снова)
POST   /api/v1/map-comments/{id}/resolve    — «решено»; /reopen — открыть снова
PATCH  /api/v1/map-comments/comments/{cid}  — править своё сообщение
DELETE /api/v1/map-comments/comments/{cid}  — удалить своё (администратор пользователей — любое)

Читать и писать может любой вошедший: это обсуждение, а не правка данных сети.
"""
from __future__ import annotations

import time
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query

import cities as city_access
from app_logging import get_logger
from auth import AuthUser, pg_auth_enabled, require_roles
from database import map_comments as mc
from database.connect import acquire_conn

logger = get_logger(__name__)

router = APIRouter(tags=["map-comments"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
ThreadId = Annotated[int, Path(ge=1)]
CommentId = Annotated[int, Path(ge=1)]
PEOPLE_TTL_S = 300
_people_cache: dict[str, tuple[float, list[dict[str, str]]]] = {}


def _http(exc: mc.CommentError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


async def _people(conn) -> list[dict[str, str]]:
    """Активные пользователи с доступом к городу (UsersDB); при входе через роли PostgreSQL — те, кто уже писал
    комментарии (список ролей видит только администратор)."""
    key = city_access.cache_key()
    cached = _people_cache.get(key)
    if cached and time.monotonic() - cached[0] < PEOPLE_TTL_S:
        return cached[1]
    people: list[dict[str, str]] = []
    if not pg_auth_enabled():
        try:
            from database.users_admin import list_users

            people = [{"login": u["username"], "role": u["role"]} for u in await list_users()
                      if u["is_active"] and city_access.allowed(u["cities"])]
        except Exception as exc:  # noqa: BLE001 — без UsersDB упоминания работают по авторам комментариев
            logger.warning("map comments: UsersDB недоступна для списка упоминаний: %s", exc)
    if not people:
        rows = await conn.fetch("SELECT DISTINCT author FROM tgid_map_comment WHERE author <> '' ORDER BY author")
        people = [{"login": r["author"], "role": ""} for r in rows]
    _people_cache[key] = (time.monotonic(), people)
    return people


async def _known(conn) -> Optional[set[str]]:
    people = await _people(conn)
    return {p["login"] for p in people} or None


def _is_admin(user: AuthUser) -> bool:
    return user.perms.has("users_admin")


@router.get("/api/v1/map-comments")
async def map_comments_list(
    user: Viewer,
    status: mc.Status = Query("open"),
    scope: mc.Scope = Query("all", description="mine — где я писал или меня упомянули"),
    q: Optional[str] = Query(None, max_length=100),
):
    async with acquire_conn() as conn:
        return await mc.list_threads(conn, user.username, status=status, scope=scope, q=q)


@router.get("/api/v1/map-comments/geojson")
async def map_comments_geojson(user: Viewer, status: mc.Status = Query("open")):
    async with acquire_conn() as conn:
        return await mc.geojson(conn, user.username, status=status)


@router.get("/api/v1/map-comments/unread")
async def map_comments_unread(user: Viewer):
    async with acquire_conn() as conn:
        return {"unread": await mc.unread_count(conn, user.username)}


@router.get("/api/v1/map-comments/people")
async def map_comments_people(_: Viewer):
    async with acquire_conn() as conn:
        return {"items": await _people(conn)}


@router.get("/api/v1/map-comments/{thread_id}")
async def map_comments_get(thread_id: ThreadId, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.get_thread(conn, thread_id, user.username)
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/map-comments")
async def map_comments_create(body: mc.ThreadIn, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.create_thread(conn, body, user.username, await _known(conn))
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/map-comments/{thread_id}/comments")
async def map_comments_reply(thread_id: ThreadId, body: mc.CommentIn, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.reply(conn, thread_id, body, user.username, await _known(conn))
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/map-comments/{thread_id}/resolve")
async def map_comments_resolve(thread_id: ThreadId, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.set_resolved(conn, thread_id, user.username, True)
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.post("/api/v1/map-comments/{thread_id}/reopen")
async def map_comments_reopen(thread_id: ThreadId, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.set_resolved(conn, thread_id, user.username, False)
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.patch("/api/v1/map-comments/comments/{comment_id}")
async def map_comments_edit(comment_id: CommentId, body: mc.CommentIn, user: Viewer):
    try:
        async with acquire_conn() as conn:
            return await mc.edit_comment(conn, comment_id, body, user.username, is_admin=_is_admin(user),
                                         known=await _known(conn))
    except mc.CommentError as exc:
        raise _http(exc) from exc


@router.delete("/api/v1/map-comments/comments/{comment_id}")
async def map_comments_delete(comment_id: CommentId, user: Viewer):
    try:
        async with acquire_conn() as conn:
            thread = await mc.delete_comment(conn, comment_id, user.username, is_admin=_is_admin(user))
    except mc.CommentError as exc:
        raise _http(exc) from exc
    return {"deleted": True, "thread": thread}
