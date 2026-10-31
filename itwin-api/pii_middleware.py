"""Маскирование персональных данных в JSON-ответах API (database/pii.py) для пользователей без права pii_view.

Чистый ASGI: ответ JSON копится, и, если в нём есть ключи полей ПДн (телефон, владелец, абонент, счёт…),
а у пользователя нет права «Персональные данные», значения маскируются до отправки. Остальные ответы
(GeoJSON сети, тайлы, файлы, без таких ключей) проходят без разбора. Пользователь узнаётся по Bearer-токену
с живой сверкой (кеш USER_STATUS_TTL); без токена или с неверным — маскировать.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from app_logging import get_logger
from database import pii

logger = get_logger(__name__)

# ответ больше — не разбирается (выборки сети, GeoJSON); списки с ПДн постраничные
MAX_BYTES = int(os.getenv("PII_MAX_BYTES", str(16 * 1024 * 1024)))
# вход, администрирование пользователей (там права и так полные) и MCP — без маскирования
_SKIP_PREFIXES = ("/api/v1/auth", "/auth", "/api/v1/admin", "/mcp", "/metrics", "/health", "/docs", "/openapi.json")


async def _user(scope) -> Optional[object]:
    from auth import AuthUser, apply_live_user_status, auth_disabled, decode_access_token

    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    token = None
    for name, value in scope.get("headers") or ():
        if name == b"authorization" and value[:7].lower() == b"bearer ":
            token = value[7:].decode("latin-1").strip()
            break
    if not token:
        return None
    try:
        # ключ API v2 (scope api) — права его пользователя; вход по нему проверяет сам маршрут /api/v2
        return await apply_live_user_status(decode_access_token(token, allow_scopes=("api",)))
    except Exception:  # noqa: BLE001 — неверный или закрытый токен: как аноним (маскировать)
        return None


class PiiMaskMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "") if scope["type"] == "http" else ""
        if scope["type"] != "http" or not pii.enabled() or path.startswith(_SKIP_PREFIXES):
            await self.app(scope, receive, send)
            return

        start: dict = {}
        chunks: list[bytes] = []
        size = 0
        passthrough = False

        async def send_wrapper(message):
            nonlocal passthrough, size
            if message["type"] == "http.response.start":
                headers = {k.lower(): v for k, v in message.get("headers") or ()}
                ctype = headers.get(b"content-type", b"")
                # поток NDJSON (помощник ИИ) не копить: он идёт по шагам, ПДн в нём закрыты инструментами
                if b"json" not in ctype or b"ndjson" in ctype or headers.get(b"content-encoding"):
                    passthrough = True
                    await send(message)
                    return
                start.update(message)
                return
            if message["type"] != "http.response.body" or passthrough:
                await send(message)
                return
            chunks.append(message.get("body", b""))
            size += len(chunks[-1])
            if size > MAX_BYTES:
                # большой ответ (сеть, GeoJSON): отдать как есть, дальше — без накопления
                logger.debug("PII: ответ %s больше %s байт — без маскирования", path, MAX_BYTES)
                passthrough = True
                await send(start)
                await send({"type": "http.response.body", "body": b"".join(chunks),
                            "more_body": message.get("more_body", False)})
                chunks.clear()
                return
            if message.get("more_body", False):
                return
            body = b"".join(chunks)
            body = await self._mask(scope, body)
            headers = [(k, v) for k, v in start.get("headers") or () if k.lower() != b"content-length"]
            headers.append((b"content-length", str(len(body)).encode()))
            await send({**start, "headers": headers})
            await send({"type": "http.response.body", "body": body})

        await self.app(scope, receive, send_wrapper)

    async def _mask(self, scope, body: bytes) -> bytes:
        if not body or not pii.may_contain(body):
            return body
        if pii.can_view(await _user(scope)):
            return body
        try:
            data = json.loads(body)
        except ValueError:
            return body
        masked, changed = pii.mask_json(data)
        if not changed:
            return body
        return json.dumps(masked, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
