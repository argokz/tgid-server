"""Живая карта (database/live.py): поток событий и присутствие.

GET    /api/v1/live/stream                — поток событий (text/event-stream): hello, presence, network.changed,
                                            data_version, resync; закрывается через STREAM_MAX_S — переподключиться
POST   /api/v1/live/presence              — «я здесь»: вкладка, центр и масштаб вида, объект правки; раз в 20 с
DELETE /api/v1/live/presence/{session_id} — вкладка закрыта

Вход — как у всего API (Bearer); браузер читает поток через fetch, а не EventSource: EventSource не передаёт
заголовок Authorization.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from auth import AuthUser, require_roles
from cities import cache_key, current_city
from database import live
from database.connect import acquire_conn

router = APIRouter(tags=["live"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=str)


@router.get("/api/v1/live/stream")
async def live_stream(request: Request, user: Viewer) -> StreamingResponse:
    hub = live.hub(cache_key())
    try:
        async with acquire_conn() as conn:
            hello = await hub.snapshot(conn)
        sub = hub.subscribe()
    except OverflowError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    async def events():
        try:
            yield live.sse("hello", _dumps({**hello, "user": user.username, "city": current_city(),
                                            "reconnect_ms": int(live.TICK_S * 1000)}))
            deadline = time.monotonic() + live.STREAM_MAX_S
            while time.monotonic() < deadline:
                if sub.overflow:
                    yield live.sse("resync", "{}")
                    return
                try:
                    event, data = await asyncio.wait_for(sub.queue.get(), live.KEEPALIVE_S)
                except asyncio.TimeoutError:
                    if await request.is_disconnected():
                        return
                    yield b": ping\n\n"  # комментарий: nginx и прокси не закрывают «молчащее» соединение
                    continue
                yield live.sse(event, _dumps(data))
        finally:
            hub.unsubscribe(sub)

    return StreamingResponse(events(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",  # nginx: не копить поток в буфере
    })


@router.post("/api/v1/live/presence")
async def live_presence(body: live.PresenceIn, user: Viewer) -> dict[str, Any]:
    async with acquire_conn() as conn:
        key = await live.heartbeat(conn, body, user.username)
    return {"key": key, "ttl_s": live.PRESENCE_TTL_S}


@router.delete("/api/v1/live/presence/{session_id}")
async def live_leave(session_id: UUID, user: Viewer) -> dict[str, bool]:
    async with acquire_conn() as conn:
        await live.leave(conn, session_id, user.username)
    return {"ok": True}
