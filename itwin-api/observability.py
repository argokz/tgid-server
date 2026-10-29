"""Метрики Prometheus: запросы API, пул БД, очередь расчётов.

GET /metrics открыт только по токену: METRICS_TOKEN в окружении и заголовок
`Authorization: Bearer <токен>` (в Prometheus — `authorization: credentials: …`).
Без METRICS_TOKEN маршрут отвечает 404: метрики не публикуются наружу через nginx.

Uvicorn с несколькими процессами (--workers N): задайте PROMETHEUS_MULTIPROC_DIR —
пустой каталог, который очищается перед стартом службы. Тогда счётчики всех процессов
складываются; без него каждый процесс отдаёт только свои.
"""

import asyncio
import hmac
import os
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from prometheus_client.core import GaugeMetricFamily

from app_logging import get_logger

logger = get_logger(__name__)

_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "").strip()
_UNMATCHED_ROUTE = "<unmatched>"
_QUEUE_CHECK_TIMEOUT_S = 2
# Секунды: от быстрых чтений карточек до долгих выгрузок и отчётов
_LATENCY_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120)

HTTP_REQUESTS = Counter(
    "tgid_http_requests_total",
    "Запросы к API по шаблону маршрута и коду ответа",
    ["method", "route", "status"],
)
HTTP_LATENCY = Histogram(
    "tgid_http_request_duration_seconds",
    "Время ответа API по шаблону маршрута",
    ["method", "route"],
    buckets=_LATENCY_BUCKETS,
)


def _route_label(scope) -> str:
    """Шаблон пути (/api/node/{node_id}), а не сам путь — иначе метрик столько же, сколько объектов."""
    route = scope.get("route")
    return getattr(route, "path", None) or _UNMATCHED_ROUTE


class MetricsMiddleware:
    """Чистый ASGI: считает каждый HTTP-запрос, включая ответы с ошибкой."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") == "/metrics":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            method = scope.get("method", "GET")
            route = _route_label(scope)
            HTTP_REQUESTS.labels(method, route, str(status["code"])).inc()
            HTTP_LATENCY.labels(method, route).observe(time.perf_counter() - started)


def _celery_queue_length() -> int | None:
    """Ожидающие задачи в очереди Celery (расчёты, выгрузки) — список `celery` в Redis воркера;
    у API на несколько городов — сумма очередей городов tgid.<город>."""
    import redis as redis_lib

    from cities import city_task_queues, multi_city

    addr = os.getenv("REDIS_ADDR", "127.0.0.1:6379")
    host, _, port_s = addr.partition(":")
    client = redis_lib.Redis(
        host=host or "127.0.0.1",
        port=int(port_s or "6379"),
        password=os.getenv("REDIS_PASSWORD", "").strip() or None,
        db=int(os.getenv("REDIS_DB", "").strip() or "0"),
        socket_timeout=_QUEUE_CHECK_TIMEOUT_S,
        socket_connect_timeout=_QUEUE_CHECK_TIMEOUT_S,
    )
    try:
        queues = city_task_queues() if multi_city() else ["celery"]
        return sum(int(client.llen(q)) for q in queues)
    finally:
        client.close()


class _StateCollector:
    """Состояние на момент опроса: город, пул БД этого процесса, очередь расчётов."""

    def __init__(self, queue_length: int | None):
        self.queue_length = queue_length

    @staticmethod
    def _cities() -> list[tuple[str, str, object, dict]]:
        """(город, база, пул, состояние доводки) — один город API или все города TGID_CITY_DBS."""
        from cities import city_databases, current_city, multi_city
        from database import city_schema, connect

        if not multi_city():
            return [(current_city(), os.getenv("DB_NAME", ""), connect.pool, city_schema.STATE)]
        return [
            (code, db, connect.city_pools.get(code), city_schema.STATES.get(code) or city_schema._new_state())
            for code, db in city_databases().items()
        ]

    def collect(self):
        cities = self._cities()
        info = GaugeMetricFamily("tgid_info", "Город и база этого API", labels=["city", "database"])
        size = GaugeMetricFamily(
            "tgid_db_pool_connections", "Соединения пула базы города", labels=["city", "state"]
        )
        ok = GaugeMetricFamily(
            "tgid_city_schema_ok", "Веб-добавки в базе города на месте (1) или нет (0)", labels=["city", "status"]
        )
        missing = GaugeMetricFamily(
            "tgid_city_schema_missing", "Недостающие пункты схемы базы города", labels=["city"]
        )
        recreated = GaugeMetricFamily(
            "tgid_city_db_recreated", "Сколько раз база пересоздана десктопом с запуска процесса", labels=["city"]
        )
        for city, db, pool, schema in cities:
            info.add_metric([city, db], 1)
            if pool is not None:
                total = pool.get_size()
                idle = pool.get_idle_size()
                size.add_metric([city, "busy"], total - idle)
                size.add_metric([city, "idle"], idle)
            ok.add_metric([city, schema["status"]], 1 if schema["status"] in ("ok", "applied") else 0)
            missing.add_metric([city], len(schema["missing"]))
            recreated.add_metric([city], schema["recreated"])
        yield from (info, size, ok, missing, recreated)

        up = GaugeMetricFamily("tgid_celery_queue_up", "Очередь расчётов доступна (1) или нет (0)")
        up.add_metric([], 0 if self.queue_length is None else 1)
        yield up
        if self.queue_length is not None:
            yield GaugeMetricFamily(
                "tgid_celery_queue_length", "Задачи, ждущие воркера", value=self.queue_length
            )


def _check_token(request: Request) -> None:
    expected = os.getenv("METRICS_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=404, detail="Not Found")
    header = request.headers.get("authorization") or ""
    supplied = header[7:].strip() if header[:7].lower() == "bearer " else ""
    if not hmac.compare_digest(supplied.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Неверный токен метрик", headers={"WWW-Authenticate": "Bearer"})


def _build_registry(queue_length: int | None) -> CollectorRegistry:
    registry = CollectorRegistry()
    if _MULTIPROC_DIR:
        from prometheus_client import multiprocess

        multiprocess.MultiProcessCollector(registry)
    else:
        registry.register(HTTP_REQUESTS)
        registry.register(HTTP_LATENCY)
    registry.register(_StateCollector(queue_length))
    return registry


router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    _check_token(request)
    try:
        queue_length = await asyncio.to_thread(_celery_queue_length)
    except Exception as exc:  # noqa: BLE001 — Redis недоступен: метрика up=0, остальное отдаём
        logger.warning("Метрики: очередь Celery недоступна: %s", exc)
        queue_length = None
    payload = generate_latest(_build_registry(queue_length))
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
