"""Журнал действий пользователей (activity_log в UsersDB, общий для городов).

Пишется: входы (удачные и нет — без пароля), выходы, все запросы на изменение данных
(POST/PUT/PATCH/DELETE), расчёты и выгрузки. Что именно изменилось в данных — в audit_log
города (история правок); здесь — кто, когда, что делал, откуда и чем закончилось.

Запись не должна мешать работе: ошибка журнала — только в лог приложения, запрос
продолжается. Middleware ActivityMiddleware — чистый ASGI, пишет после ответа отдельной задачей.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from app_logging import get_logger

logger = get_logger(__name__)

ACTION_LABELS: dict[str, str] = {
    "LOGIN": "Вход",
    "LOGIN_FAIL": "Неудачный вход",
    "LOGOUT": "Выход",
    "PASSWORD": "Смена пароля",
    "USERS": "Управление пользователями",
    "NETWORK": "Правка сети",
    "UNDO": "Отмена / повтор",
    "CARD": "Правка свойств",
    "GROUP": "Групповая правка",
    "TEMPLATE": "Шаблоны карточек",
    "IMPORT": "Импорт",
    "CALC_RUN": "Расчёт",
    "CALC_SAVE": "Сохранение расчёта",
    "EXPORT": "Выгрузка",
    "JOURNAL": "Журналы",
    "REFS": "Справочники",
    "EDIT": "Изменение данных",
    "REQUEST": "Прочее действие",
    "AI": "Запрос к ИИ",
}

# (метод или *, регулярка пути) → действие; первое совпадение. Пути — без префикса /tgid/<город>/map-api.
_RULES: list[tuple[str, re.Pattern, str]] = [(m, re.compile(p), a) for m, p, a in (
    ("POST", r"^/(api/v1/)?auth/logout", "LOGOUT"),
    ("*", r"^/(api/v1/)?auth/password", "PASSWORD"),
    ("*", r"^/api/(v1/)?admin/users", "USERS"),
    ("*", r"^/api/(v1/)?topology/(undo|redo)", "UNDO"),
    ("*", r"^/(api/(v1/)?)?topology/", "NETWORK"),
    ("*", r"^/api/(v1/)?(split-line|reverse-line|merge-nodes)", "NETWORK"),
    ("*", r"^/api/v1/card-templates", "TEMPLATE"),
    ("*", r"^/api/v1/card-edit/batch", "GROUP"),
    ("*", r"^/api/v1/card-edit", "CARD"),
    ("*", r"^/api/v1/(equipment-edit|equipment)", "CARD"),
    ("*", r"^/api/v1/group-setters", "GROUP"),
    ("*", r"^/api/v1/dictionaries", "REFS"),
    ("*", r"^/api/(v1/)?(import|fragments/(import|merge))", "IMPORT"),
    ("DELETE", r"^/api/(v1/)?calculations/", "CALC_SAVE"),
    ("*", r"^/(api/(v1/)?)?(run-sety-cmd|calculations/run|heat-losses(/norm)?/run)", "CALC_RUN"),
    ("POST", r"^/api/ogc/processes/heat-hydraulic/execution$", "CALC_RUN"),
    ("*", r"^/(api/)?piezometer/directions", "CALC_SAVE"),
    ("*", r"/(export|excel)(/|$)|\.xlsx$|/download$|^/reports/word/|^/api/reports/html/|^/(api/)?piezometer/excel", "EXPORT"),
    ("*", r"^/api/v1/journals/|^/api/(v1/)?(technical-conditions|pts|alseko|electrical-network|v1/work-orders|v1/outages)", "JOURNAL"),
)]
# GET, которые не пишутся, хоть и похожи на выгрузку (справочники каталога отчётов)
_SKIP_GET = re.compile(r"^/api/reports/(catalog|excel-types)$")
# POST без изменения данных: расчётные калькуляторы, анализ, предпросмотры, разбор файла импорта
_READONLY_POST = re.compile(
    r"^/api/(v1/)?topology/(convert-point|versions)|^/(api/)?piezometer/route|^/api/analysis/|^/api/calc/"
    r"|^/api/v1/card-edit/batch/(card|preview)|^/api/v1/card-templates/\d+/preview|^/api/v1/group-setters/[^/]+/preview"
    r"|^/api/(v1/)?import/inspect|^/api/v1/calculations/protocols/locate|^/api/v1/file-jobs$"
    r"|^/api/v1/ai/"  # вызовы ИИ пишет ai/usage.py с токенами
    r"|^/api/v1/network-select$"  # выборка по условиям — только чтение
    r"|^/api/v1/forms/import-xlsform$"  # разбор XLSForm — без записи
    r"|^/api/ogc/processes/(?!heat-hydraulic/)[^/]+/execution$"  # процессы OGC, кроме расчёта, — только чтение
    r"|^/mcp$|^/api/v1/mcp/token$"  # MCP пишет сам: вызовы инструментов (MCP) и выдачу токена (MCP_TOKEN)
)
# предпросмотр: «"dry_run": true» в теле или dry_run=true в адресе — не действие
_DRY_RUN = re.compile(rb'"dry_run"\s*:\s*true')
_DRY_RUN_QS = re.compile(r"(^|&)dry_run=(true|1)(&|$)", re.IGNORECASE)
BODY_PEEK = 65536
# Не писать: вход (пишется явно, с логином), проверки GeoServer и служебное
# и живая карта (присутствие раз в 20 с от каждой вкладки, поток событий)
_SKIP = re.compile(r"^/(api/v1/)?auth/(login|check|config|me)|^/health|^/docs|^/openapi|^/api/v1/live/")
_PREFIX = re.compile(r"^/tgid/[a-z0-9_-]+/map-api")


def classify(method: str, path: str) -> Optional[str]:
    """Действие журнала по запросу; None — не писать (чтение, служебное)."""
    method = method.upper()
    path = _PREFIX.sub("", path) or "/"
    if method in ("OPTIONS", "HEAD") or _SKIP.search(path):
        return None
    if method == "GET" and _SKIP_GET.search(path):
        return None
    if method == "POST" and _READONLY_POST.search(path):
        return None
    for m, rx, action in _RULES:
        if (m == "*" or m == method) and rx.search(path):
            if method == "GET" and action != "EXPORT":
                return None  # чтение журналов, карточек, расчётов — не действие
            return action
    if method in ("PUT", "PATCH", "DELETE") or (method == "POST" and "/create/" in path):
        return "EDIT"
    return "REQUEST" if method == "POST" else None


def enabled() -> bool:
    return os.getenv("ACTIVITY_LOG_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def retention_days() -> int:
    try:
        return max(30, int(os.getenv("ACTIVITY_LOG_DAYS", "730")))
    except ValueError:
        return 730


_last_cleanup = 0.0


async def write(
    *,
    username: Optional[str],
    action: str,
    method: Optional[str] = None,
    path: Optional[str] = None,
    status: Optional[int] = None,
    duration_ms: Optional[int] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    city: Optional[str] = None,
) -> None:
    """Одна запись журнала действий; любые ошибки — в лог приложения (запрос не страдает)."""
    if not enabled():
        return
    try:
        import cities as city_access
        from database.connect import async_session
        from database.models import ActivityLog

        async with async_session() as session:
            session.add(ActivityLog(
                at=datetime.now(),
                username=(username or "")[:100] or None,
                city=(city if city is not None else city_access.current_city())[:20] or None,
                action=action[:20],
                method=(method or "")[:8] or None,
                path=(path or "")[:300] or None,
                status=status,
                duration_ms=duration_ms,
                ip=(ip or "")[:64] or None,
                user_agent=(user_agent or "")[:300] or None,
                details=json.dumps(details, ensure_ascii=False, default=str) if details else None,
            ))
            await session.commit()
        await _maybe_cleanup()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Журнал действий: запись не удалась (%s %s): %s", action, path, exc)


async def _maybe_cleanup() -> None:
    """Раз в сутки — удалить записи старше ACTIVITY_LOG_DAYS."""
    global _last_cleanup
    now = time.monotonic()
    if _last_cleanup and now - _last_cleanup < 86400:
        return
    _last_cleanup = now
    from sqlalchemy import delete

    from database.connect import async_session
    from database.models import ActivityLog

    async with async_session() as session:
        await session.execute(delete(ActivityLog).where(ActivityLog.at < datetime.now() - timedelta(days=retention_days())))
        await session.commit()


def _header(scope, name: bytes) -> str:
    for key, value in scope.get("headers") or ():
        if key == name:
            return value.decode("latin-1")
    return ""


def client_ip(scope) -> str:
    """Адрес клиента: за nginx — X-Real-IP / первый X-Forwarded-For."""
    real = _header(scope, b"x-real-ip").strip()
    if real:
        return real
    fwd = _header(scope, b"x-forwarded-for").split(",")[0].strip()
    if fwd:
        return fwd
    client = scope.get("client")
    return client[0] if client else ""


def _username(scope) -> Optional[str]:
    auth = _header(scope, b"authorization")
    if not auth[:7].lower() == "bearer ":
        return None
    try:
        from auth import decode_access_token

        # ключи с назначением (API v2, MCP, ArcGIS) — тоже автор действия
        return decode_access_token(auth[7:].strip(), allow_scopes=("api", "mcp", "arcgis")).username
    except Exception:  # noqa: BLE001 — неверный токен: запрос и так получит 401
        return None


_pending: set[asyncio.Task] = set()
# параметры адреса, которые не пишутся в журнал
_SECRET_QS = re.compile(r"((?:^|&)(?:token|access_token|password|key)[^=&]*)=[^&]*", re.IGNORECASE)


class ActivityMiddleware:
    """Чистый ASGI: после ответа — запись в activity_log (действие по classify, статус, время)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not enabled():
            await self.app(scope, receive, send)
            return
        action = classify(scope.get("method", "GET"), scope.get("path", "/"))
        if action is None:
            await self.app(scope, receive, send)
            return
        started = time.monotonic()
        status_holder: dict[str, int] = {}
        body = bytearray()

        async def receive_wrapper():
            message = await receive()
            if message.get("type") == "http.request" and len(body) < BODY_PEEK:
                body.extend(message.get("body", b"")[: BODY_PEEK - len(body)])
            return message

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = int(message.get("status", 0))
            await send(message)

        try:
            await self.app(scope, receive_wrapper, send_wrapper)
        finally:
            raw_query = scope.get("query_string", b"").decode("latin-1")
            # предпросмотр (dry_run) ничего не меняет — не действие
            if _DRY_RUN.search(bytes(body)) or _DRY_RUN_QS.search(raw_query):
                return
            query = _SECRET_QS.sub(r"\1=***", raw_query)
            task = asyncio.ensure_future(write(
                username=_username(scope),
                action=action,
                method=scope.get("method"),
                path=scope.get("path", "") + (f"?{query}" if query else ""),
                status=status_holder.get("status", 500),
                duration_ms=int((time.monotonic() - started) * 1000),
                ip=client_ip(scope),
                user_agent=_header(scope, b"user-agent"),
            ))
            _pending.add(task)
            task.add_done_callback(_pending.discard)
