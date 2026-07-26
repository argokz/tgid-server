"""Точка входа FastAPI-приложения ITwin API.

Маршруты разнесены по модулям пакета routers/ (пути сохранены 1:1).
Здесь остаются только: настройка логирования, lifespan (пул БД,
справочники, русские названия), CORS и сборка приложения.
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app_logging import configure_logging

# Логирование и переменные окружения — до импорта роутеров.
logger = configure_logging()
load_dotenv()

from auth import (  # noqa: E402
    PUBLIC_GET_PREFIXES,
    assert_production_auth_safe,
    auth_required_get,
    decode_access_token,
)
from database.connect import (  # noqa: E402
    close_db_pool,
    close_users_db_pool,
    init_db_pool,
    init_users_db_pool,
)
from routers import all_routers  # noqa: E402
from utils.ini import storage  # noqa: E402
from utils.russian_names import russian_names_manager  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт приложения...")
    assert_production_auth_safe()
    await init_db_pool()
    try:
        await init_users_db_pool()
    except Exception as exc:  # noqa: BLE001
        logger.warning("UsersDB pool unavailable at startup: %s", exc)
    await storage.read_lookup("kls/gid.lookup")
    await storage.read_help("kls/gid.txt1")
    await storage.read_help("kls/gid.txt2")

    # Инициализируем русские названия
    try:
        russian_names_manager.init_column_rus_name("gid")
        logger.info("Русские названия успешно инициализированы")
    except Exception as e:
        logger.error(f"Ошибка при инициализации русских названий: {str(e)}")

    yield
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
    """Optional JWT gate for GET /api/* when AUTH_REQUIRED_GET=true."""

    async def dispatch(self, request: Request, call_next):
        if request.method.upper() != "GET" or not auth_required_get():
            return await call_next(request)
        path = request.url.path
        if any(path == p or path.startswith(p + "/") or path.startswith(p + "?") for p in PUBLIC_GET_PREFIXES):
            return await call_next(request)
        if path in {"/api/v1/auth/login", "/auth/login"} or path.startswith("/auth/login"):
            return await call_next(request)
        # Only gate /api* journal/data GETs — leave map tile proxies alone if any
        if not (path.startswith("/api/") or path.startswith("/piezometer") or path.startswith("/reports/")):
            return await call_next(request)
        auth_header = request.headers.get("authorization") or ""
        if not auth_header.lower().startswith("bearer "):
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization Bearer token required"},
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            decode_access_token(auth_header.split(" ", 1)[1].strip())
        except Exception as exc:  # noqa: BLE001
            detail = getattr(exc, "detail", str(exc))
            status_code = getattr(exc, "status_code", 401)
            return JSONResponse(status_code=status_code, content={"detail": detail})
        return await call_next(request)


app.add_middleware(AuthRequiredGetMiddleware)

for router in all_routers:
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8011, reload=True)
