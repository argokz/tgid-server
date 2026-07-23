"""Точка входа FastAPI-приложения ITwin API.

Маршруты разнесены по модулям пакета routers/ (пути сохранены 1:1).
Здесь остаются только: настройка логирования, lifespan (пул БД,
справочники, русские названия), CORS и сборка приложения.
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_logging import configure_logging

# Логирование и переменные окружения — до импорта роутеров.
logger = configure_logging()
load_dotenv()

from database.connect import close_db_pool, init_db_pool  # noqa: E402
from routers import all_routers  # noqa: E402
from utils.ini import storage  # noqa: E402
from utils.russian_names import russian_names_manager  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт приложения...")
    await init_db_pool()
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

for router in all_routers:
    app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8011, reload=True)
