import logging
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
import os
from dotenv import load_dotenv
from database.models import Base
from database.connect import users_engine, USERS_DB_CONFIG
import asyncio
import asyncpg
import asyncpg.exceptions

# Настройка логирования для миграций
logger = logging.getLogger("alembic.env")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем конфигурацию Alembic
config = context.config

# Настраиваем логирование из файла конфигурации Alembic (если он есть)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Указываем метаданные для моделей
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Запуск миграций в оффлайн-режиме (без подключения к базе)."""
    url = config.get_main_option("sqlalchemy.url", USERS_DB_CONFIG["database"])
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection) -> None:
    """Выполнение миграций с активным подключением."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()

async def ensure_database_exists():
    """Проверка и создание базы данных UsersDB, если она не существует."""
    temp_config = USERS_DB_CONFIG.copy()
    temp_config["database"] = "postgres"  # Подключаемся к системной базе
    logger.info(f"Проверка существования базы {USERS_DB_CONFIG['database']} через системную базу: {temp_config}")
    
    try:
        pool = await asyncpg.create_pool(**temp_config, min_size=1, max_size=5)
        async with pool.acquire() as conn:
            # Проверяем существование базы
            result = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", USERS_DB_CONFIG["database"])
            if not result:
                logger.info(f"База {USERS_DB_CONFIG['database']} не существует, создаём...")
                # Проверяем активные подключения к template1
                active_connections = await conn.fetch(
                    "SELECT pid, usename, client_addr FROM pg_stat_activity WHERE datname = 'template1' AND state = 'active' AND pid != pg_backend_pid()"
                )
                if active_connections:
                    logger.warning(f"Найдено {len(active_connections)} активных подключений к template1:")
                    for row in active_connections:
                        logger.info(f"PID: {row['pid']}, User: {row['usename']}, Client: {row['client_addr']}")
                        await conn.execute("SELECT pg_terminate_backend($1)", row["pid"])
                        logger.info(f"Завершён процесс с PID {row['pid']}")
                    await asyncio.sleep(1)  # Ждём завершения

                # Создаём базу с template0
                await conn.execute(f"CREATE DATABASE {USERS_DB_CONFIG['database']} TEMPLATE template0")
                logger.info(f"База {USERS_DB_CONFIG['database']} успешно создана")
            else:
                logger.info(f"База {USERS_DB_CONFIG['database']} уже существует, пропускаем создание")
        await pool.close()
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"Ошибка подключения к системной базе: {e}")
        raise RuntimeError(f"Не удалось подключиться к системной базе PostgreSQL: {e}")
    except Exception as e:
        logger.error(f"Ошибка при проверке или создании базы: {e}", exc_info=True)
        raise RuntimeError(f"Не удалось обеспечить существование базы {USERS_DB_CONFIG['database']}: {e}")

async def run_migrations_online() -> None:
    """Запуск миграций в онлайн-режиме (асинхронно)."""
    # Проверяем и создаём базу, если нужно
    await ensure_database_exists()
    
    # Выполняем миграции в существующей базе
    try:
        logger.info(f"Подключение к базе {USERS_DB_CONFIG['database']} для выполнения миграций...")
        async with users_engine.connect() as connection:
            logger.info("Подключение успешно, выполнение миграций...")
            await connection.run_sync(do_run_migrations)
            logger.info("Миграции успешно выполнены")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"Соединение с базой {USERS_DB_CONFIG['database']} было разорвано: {e}")
        raise RuntimeError(f"Не удалось выполнить миграции: соединение с базой {USERS_DB_CONFIG['database']} было неожиданно закрыто")
    except Exception as e:
        # Если это ошибка "Target database is not up to date", это нормально для --autogenerate на пустой базе
        if "Target database is not up to date" in str(e):
            logger.warning(f"База {USERS_DB_CONFIG['database']} не синхронизирована с миграциями, это ожидаемо для первой миграции")
        else:
            logger.error(f"Ошибка при выполнении миграций: {e}", exc_info=True)
            raise RuntimeError(f"Не удалось выполнить миграции в базе {USERS_DB_CONFIG['database']}: {e}")

if context.is_offline_mode():
    run_migrations_offline()
else:
    try:
        asyncio.run(run_migrations_online())
    except RuntimeError as e:
        logger.error(f"Процесс миграций завершился с ошибкой: {e}")
        raise