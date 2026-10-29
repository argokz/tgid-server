"""Точка входа FastAPI-приложения ITwin API.

Маршруты разнесены по модулям пакета routers/ (пути сохранены 1:1).
Здесь остаются только: настройка логирования, lifespan (пул БД,
справочники, русские названия), CORS и сборка приложения.
"""

import asyncio
import os
from contextlib import asynccontextmanager

import asyncpg
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app_logging import configure_logging

# Логирование и переменные окружения — до импорта роутеров.
logger = configure_logging()
load_dotenv()

from auth import (  # noqa: E402
    PUBLIC_GET_PREFIXES,
    apply_live_user_status,
    assert_production_auth_safe,
    auth_disabled,
    auth_required_get,
    db_role_for,
    decode_access_token,
)
from database.db_errors import privilege_error_detail  # noqa: E402
from database.db_role import role_switch_enabled, set_db_role  # noqa: E402
from database.connect import (  # noqa: E402
    close_db_pool,
    close_users_db_pool,
    init_db_pool,
    init_users_db_pool,
)
from routers import all_routers  # noqa: E402
from utils.ini import storage  # noqa: E402
from utils.russian_names import russian_names_manager  # noqa: E402


def _start_db_upkeep() -> list[asyncio.Task]:
    """Доводка базы города (database/city_schema.py) — при запуске и периодически, в фоне.

    API на несколько городов доводит базу каждого города своей задачей (в контексте этого города).
    """
    from cities import city_databases, current_city, multi_city, use_city
    from database.city_schema import upkeep_interval_s, upkeep_loop
    from database.connect import get_pool

    interval = upkeep_interval_s()
    if not interval:
        logger.info("Доводка базы города выключена (DB_UPKEEP_INTERVAL_S=0)")
        return []
    if not multi_city():
        return [asyncio.create_task(upkeep_loop(get_pool(), current_city(), interval))]
    tasks = []
    for code in city_databases():
        with use_city(code):  # задача копирует контекст при создании
            tasks.append(asyncio.create_task(upkeep_loop(None, code, interval)))
    return tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт приложения...")
    assert_production_auth_safe()
    await init_db_pool()
    upkeep = _start_db_upkeep()
    try:
        await init_users_db_pool()
    except Exception as exc:  # noqa: BLE001
        logger.warning("UsersDB pool unavailable at startup: %s", exc)
    await storage.read_lookup("kls/gid.lookup")
    # встроенные списки справочников (десктоп: findLookup2) — выпадающие списки как в карточке gid8
    await storage.read_lookup2("kls/gid.lookup2")
    await storage.read_help("kls/gid.txt1")
    await storage.read_help("kls/gid.txt2")

    # Инициализируем русские названия
    try:
        russian_names_manager.init_column_rus_name("gid")
        logger.info("Русские названия успешно инициализированы")
    except Exception as e:
        logger.error(f"Ошибка при инициализации русских названий: {str(e)}")

    yield
    for task in upkeep:
        task.cancel()
    logger.info("Завершение приложения...")
    await close_users_db_pool()
    await close_db_pool()


app = FastAPI(lifespan=lifespan)

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "https://itwin.kz,http://localhost:3000,http://localhost:3007",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequiredGetMiddleware(BaseHTTPMiddleware):
    """Optional JWT gate for /api/* when AUTH_REQUIRED_GET=true.

    Covers every method, not only GET: compute POSTs (valve isolation,
    calculators, piezometer export) have no per-route auth dependency.
    CORS preflight (OPTIONS) and the login/config/health paths stay public.
    """

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() == "OPTIONS" or not auth_required_get():
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in PUBLIC_GET_PREFIXES):
            return await call_next(request)
        if path in {"/api/v1/auth/login", "/auth/login"} or path.startswith("/auth/login"):
            return await call_next(request)
        if path == "/mcp":
            # MCP проверяет вход сам: принимает и токен ИИ-клиента (scope mcp), который здесь отвергся бы
            return await call_next(request)
        # Закрыто всё, кроме списка выше: карточки /node и /line, /lookup, /task, /run-sety-cmd
        # и правки без /api/ тоже отдают данные сети
        auth_header = request.headers.get("authorization") or ""
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization Bearer token required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            user = decode_access_token(auth_header.split(" ", 1)[1].strip())
            # живая сверка: блокировка и доступ к городу запроса (users.cities) — для всех маршрутов,
            # а не только с зависимостью get_current_user: токен общий для городов
            await apply_live_user_status(user)
        except Exception as exc:  # noqa: BLE001
            detail = getattr(exc, "detail", str(exc))
            status_code = getattr(exc, "status_code", 401)
            return JSONResponse(status_code=status_code, content={"detail": detail})
        return await call_next(request)


app.add_middleware(AuthRequiredGetMiddleware)


class DbRoleMiddleware:
    """Роль PostgreSQL запроса из Bearer-токена (database/db_role.py), до зависимостей маршрута.

    Нужна маршрутам без зависимости авторизации (чтение): без неё они работали бы как tgid_anon.
    Зависимости get_current_user/get_optional_user после живой проверки уточняют роль.
    Чистый ASGI (не BaseHTTPMiddleware): contextvar виден обработчику в той же задаче.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and role_switch_enabled() and not auth_disabled():
            token_value = None
            for name, value in scope.get("headers") or ():
                if name == b"authorization" and value[:7].lower() == b"bearer ":
                    token_value = value[7:].decode("latin-1").strip()
                    break
            user = None
            if token_value:
                try:
                    user = decode_access_token(token_value)
                except Exception:  # noqa: BLE001 — неверный токен: аноним, 401 даст зависимость
                    user = None
            set_db_role(db_role_for(user))
        await self.app(scope, receive, send)


app.add_middleware(DbRoleMiddleware)

# Журнал действий пользователей (activity.py): правки, расчёты, выгрузки, выходы — после ответа
from activity import ActivityMiddleware  # noqa: E402

app.add_middleware(ActivityMiddleware)

# Метрики Prometheus (observability.py) — самый внешний слой: учитывает и отказы других слоёв.
# Скрипты выкатки не ставят зависимости: без prometheus-client API работает, метрик нет.
try:
    from observability import MetricsMiddleware, router as metrics_router  # noqa: E402
except ImportError as exc:
    logger.warning("Метрики /metrics выключены: %s (pip install -r requirements.txt)", exc)
else:
    app.add_middleware(MetricsMiddleware)
    app.include_router(metrics_router)

# API на несколько городов (TGID_CITY_DBS): город — по префиксу /city/<код>/ (city_context.py).
# Самый внешний слой: остальные слои и метрики видят путь уже без префикса и контекст города.
from city_context import CityPathMiddleware  # noqa: E402

app.add_middleware(CityPathMiddleware)


@app.exception_handler(asyncpg.exceptions.InsufficientPrivilegeError)
async def _pg_privilege_error(request: Request, exc: asyncpg.exceptions.InsufficientPrivilegeError):
    detail = privilege_error_detail(str(exc)) or "Недостаточно прав для этой операции"
    logger.info("403 %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=403, content={"detail": detail})


@app.exception_handler(StarletteHTTPException)
async def _http_error(request: Request, exc: StarletteHTTPException):
    # Роутеры, обернувшие отказ PostgreSQL в HTTPException(500, str(e)), отдают 403
    if exc.status_code >= 500 and isinstance(exc.detail, str):
        detail = privilege_error_detail(exc.detail)
        if detail:
            return JSONResponse(status_code=403, content={"detail": detail})
    return await http_exception_handler(request, exc)


for router in all_routers:
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8011, reload=True)
