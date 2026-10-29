"""Город запроса в API на несколько городов (TGID_CITY_DBS).

nginx отдаёт API города по его пути: /tgid/<код>/map-api/… → http://127.0.0.1:<порт>/city/<код>/…
Middleware снимает префикс /city/<код>, запоминает город (cities.set_request_city) и передаёт запрос
дальше с прежним путём, поэтому маршруты, ссылки OGC и проверки путей не меняются. Пул базы, кеши,
доводка базы и проверка «город доступен пользователю» берут город из этого контекста.

API одного города (без TGID_CITY_DBS) работает как раньше; префикс /city/<код>/ ему не нужен.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from cities import city_databases, multi_city, set_request_city

CITY_PREFIX = "/city/"
_PATH_RE = re.compile(r"^/city/([a-z][a-z0-9_-]{1,30})(/.*)?$")
# Пути без города в API на несколько городов: проверка живости процесса, метрики и проверка входа
# GeoServer для nginx (город там — по рабочей области в адресе запроса, а не по API)
SHARED_PATHS = frozenset({"/health", "/api/health", "/metrics", "/auth/check"})


def split_city_path(path: str) -> tuple[Optional[str], str]:
    """'/city/almaty/api/v1/x' → ('almaty', '/api/v1/x'); путь без префикса → (None, path)."""
    m = _PATH_RE.match(path or "")
    if not m:
        return None, path
    return m.group(1), m.group(2) or "/"


async def _reject(send, status: int, detail: str) -> None:
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start", "status": status,
        "headers": [(b"content-type", b"application/json; charset=utf-8"),
                    (b"content-length", str(len(body)).encode("ascii"))],
    })
    await send({"type": "http.response.body", "body": body})


class CityPathMiddleware:
    """Чистый ASGI (не BaseHTTPMiddleware): контекст города виден обработчику и вложенным слоям."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket") or not multi_city():
            await self.app(scope, receive, send)
            return
        code, rest = split_city_path(scope.get("path", ""))
        if code is None:
            if scope.get("path") in SHARED_PATHS:
                await self.app(scope, receive, send)
                return
            if scope["type"] == "http":
                await _reject(send, 404, "Город не указан: путь API — /city/<код города>/…")
            return
        if code not in city_databases():
            if scope["type"] == "http":
                await _reject(send, 404, f"Город «{code}» не обслуживается этим API")
            return
        inner = dict(scope)
        inner["path"] = rest
        raw = scope.get("raw_path")
        if raw:
            inner["raw_path"] = raw[len(CITY_PREFIX) + len(code):] or b"/"
        set_request_city(code)
        await self.app(inner, receive, send)
