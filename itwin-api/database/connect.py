import asyncpg
from typing import Optional
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
import time
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
import socket

logger = logging.getLogger(__name__) 
load_dotenv()

# Конфигурация для текущей базы (схемы)
DATABASE_CONFIG = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME")
}

# Конфигурация для базы пользователей
USERS_DB_CONFIG = {
    "user": os.getenv("USERS_DB_USER"),
    "password": os.getenv("USERS_DB_PASSWORD"),
    "host": os.getenv("USERS_DB_HOST"),
    "port": int(os.getenv("USERS_DB_PORT", 5432)),
    "database": os.getenv("USERS_DB_NAME")
}

pool: Optional[asyncpg.Pool] = None
users_pool: Optional[asyncpg.Pool] = None

# Асинхронный движок SQLAlchemy для UsersDB
USERS_DB_URL = f"postgresql+asyncpg://{USERS_DB_CONFIG['user']}:{USERS_DB_CONFIG['password']}@{USERS_DB_CONFIG['host']}:{USERS_DB_CONFIG['port']}/{USERS_DB_CONFIG['database']}"
users_engine = create_async_engine(USERS_DB_URL, echo=True)
async_session = sessionmaker(users_engine, class_=AsyncSession, expire_on_commit=False)

class DatabaseConnectionError(Exception):
    """Пользовательское исключение для ошибок подключения к базе данных."""
    pass

async def init_db_pool():
    """Инициализация пула соединений для основной базы."""
    global pool
    if pool is not None:
        logger.warning("Пул уже инициализирован, пропускаем повторную инициализацию")
        return
    try:
        # Размер пула и таймаут запроса — из окружения: под нагрузкой 10 соединений
        # мало, а «вечный» запрос удерживает соединение и копит очередь.
        min_size = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
        max_size = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
        command_timeout = float(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        logger.info(
            f"🔄 Инициализация пула для основной базы (min={min_size}, max={max_size}, "
            f"command_timeout={command_timeout}s)..."
        )
        pool = await asyncpg.create_pool(
            **DATABASE_CONFIG,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
            max_inactive_connection_lifetime=float(
                os.getenv("DB_POOL_MAX_INACTIVE_LIFETIME", "300")
            ),
        )
        logger.info("✅ Пул успешно инициализирован")
    except socket.gaierror as e:
        logger.error(f"❌ Не удалось разрешить хост {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}: {e}")
        raise DatabaseConnectionError(f"Не удалось подключиться к основной базе данных: хост {DATABASE_CONFIG['host']} недоступен")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение с основной базой было разорвано: {e}")
        raise DatabaseConnectionError(f"Соединение с основной базой данных было неожиданно закрыто: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации пула: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Ошибка подключения к основной базе данных: {e}")

async def init_users_db_pool():
    """Инициализация пула соединений для базы пользователей и создание базы, если её нет."""
    global users_pool
    if users_pool is not None:
        logger.warning("Пул пользователей уже инициализирован, пропускаем повторную инициализацию")
        return
    try:
        # Проверяем существование базы и создаём, если её нет
        temp_config = USERS_DB_CONFIG.copy()
        temp_config["database"] = "postgres"
        logger.info(f"Попытка подключения к системной базе: {temp_config}")
        try:
            temp_pool = await asyncpg.create_pool(**temp_config, min_size=1, max_size=10)
        except socket.gaierror as e:
            logger.error(f"❌ Не удалось разрешить хост {temp_config['host']}:{temp_config['port']}: {e}")
            raise DatabaseConnectionError(f"Не удалось подключиться к системной базе PostgreSQL: хост {temp_config['host']} недоступен")
        except asyncpg.exceptions.ConnectionDoesNotExistError as e:
            logger.error(f"❌ Соединение с системной базой было разорвано: {e}")
            raise DatabaseConnectionError(f"Соединение с системной базой PostgreSQL было неожиданно закрыто: {e}")
        
        async with temp_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", USERS_DB_CONFIG["database"])
            if not result:
                logger.info(f"База {USERS_DB_CONFIG['database']} не существует, создаём...")
                await conn.execute(f"CREATE DATABASE {USERS_DB_CONFIG['database']}")
        await temp_pool.close()

        # Инициализируем пул для UsersDB
        logger.info(f"Инициализация пула для UsersDB: {USERS_DB_CONFIG}")
        try:
            users_pool = await asyncpg.create_pool(**USERS_DB_CONFIG, min_size=1, max_size=10)
        except socket.gaierror as e:
            logger.error(f"❌ Не удалось разрешить хост {USERS_DB_CONFIG['host']}:{USERS_DB_CONFIG['port']}: {e}")
            raise DatabaseConnectionError(f"Не удалось подключиться к базе пользователей: хост {USERS_DB_CONFIG['host']} недоступен")
        except asyncpg.exceptions.ConnectionDoesNotExistError as e:
            logger.error(f"❌ Соединение с UsersDB было разорвано: {e}")
            raise DatabaseConnectionError(f"Соединение с базой пользователей было неожиданно закрыто: {e}")
        logger.info("✅ Пул пользователей успешно инициализирован")
    except DatabaseConnectionError:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации пула пользователей: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Ошибка подключения к базе пользователей: {e}")

async def close_db_pool():
    """Закрытие пула соединений для основной базы."""
    global pool
    if pool:
        await pool.close()
        logger.info("✅ Пул соединений основной базы закрыт")
        pool = None

async def close_users_db_pool():
    """Закрытие пула для БД пользователей."""
    global users_pool
    if users_pool:
        await users_pool.close()
        logger.info("✅ Пул БД пользователей закрыт")
        users_pool = None

def get_pool():
    global pool
    return pool

async def get_connection() -> asyncpg.Connection:
    """Получение соединения из пула основной базы."""
    global pool
    if not pool:
        raise DatabaseConnectionError("Пул основной базы данных не инициализирован")
    logger.debug("Acquiring connection from main pool")
    try:
        return await pool.acquire()
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение в пуле основной базы было разорвано: {e}")
        raise DatabaseConnectionError(f"Соединение с основной базой было неожиданно закрыто во время операции")

@asynccontextmanager
async def acquire_conn():
    """Контекстный менеджер для основной базы."""
    conn = await get_connection()
    try:
        logger.debug("Main connection acquired")
        yield conn
    finally:
        await pool.release(conn)
        logger.debug("Main connection released")

async def get_users_connection() -> asyncpg.Connection:
    """Получение соединения из пула базы пользователей."""
    global users_pool
    if not users_pool:
        raise DatabaseConnectionError("Пул базы пользователей не инициализирован")
    logger.debug("Acquiring connection from users pool")
    try:
        return await users_pool.acquire()
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение в пуле UsersDB было разорвано: {e}")
        raise DatabaseConnectionError(f"Соединение с базой пользователей было неожиданно закрыто во время операции")

@asynccontextmanager
async def acquire_users_conn():
    """Контекстный менеджер для базы пользователей."""
    conn = await get_users_connection()
    try:
        logger.debug("Users connection acquired")
        yield conn
    finally:
        await users_pool.release(conn)
        logger.debug("Users connection released")

async def query_log(conn: asyncpg.Connection, sql: str, *args):
    """Выполняет SQL-запрос и логирует его."""
    start = time.perf_counter()
    try:
        result = await conn.fetch(sql, *args)
        return result
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение разорвано во время выполнения запроса: {e}")
        raise DatabaseConnectionError(f"Соединение с базой данных было неожиданно закрыто во время запроса: {sql}")
    finally:
        duration = (time.perf_counter() - start) * 1000
        arg_str = ', '.join(repr(a) for a in args)
        logger.debug(f"📝 SQL: {sql.strip()}")
        logger.debug(f"📦 Args: ({arg_str})")
        logger.debug(f"⏱️ Duration: {duration:.2f} ms")

async def get_users_db():
    """Асинхронная сессия SQLAlchemy для UsersDB."""
    async with async_session() as session:
        yield session