import asyncio
import asyncpg
from typing import Optional
from dotenv import load_dotenv
import os
from contextlib import asynccontextmanager
import time
import logging
from sqlalchemy.engine import URL
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
# API на несколько городов (TGID_CITY_DBS): пул на базу каждого города
city_pools: dict[str, asyncpg.Pool] = {}
_pool_locks: dict[str, asyncio.Lock] = {}


def safe_db_config(config: dict) -> dict:
    """Копия конфига подключения для логов: пароль не выводится никогда."""
    return {k: ("***" if k == "password" and v else v) for k, v in config.items()}


# Асинхронный движок SQLAlchemy для UsersDB. URL.create экранирует спецсимволы пароля,
# а str(URL) маскирует пароль (***), если URL попадёт в лог/исключение.
USERS_DB_URL = URL.create(
    "postgresql+asyncpg",
    username=USERS_DB_CONFIG["user"],
    password=USERS_DB_CONFIG["password"],
    host=USERS_DB_CONFIG["host"],
    port=USERS_DB_CONFIG["port"],
    database=USERS_DB_CONFIG["database"],
)
# echo пишет в лог каждый SQL с параметрами (логины и т.п.) — только по явному флагу.
users_engine = create_async_engine(
    USERS_DB_URL, echo=os.getenv("USERS_DB_ECHO", "").lower() in ("1", "true", "yes")
)
async_session = sessionmaker(users_engine, class_=AsyncSession, expire_on_commit=False)

class DatabaseConnectionError(Exception):
    """Пользовательское исключение для ошибок подключения к базе данных."""
    pass

def city_db_config(code: Optional[str] = None) -> dict:
    """Подключение к базе города (по умолчанию — города запроса): общие хост и учётка, своя база."""
    from cities import city_db_name

    return {**DATABASE_CONFIG, "database": city_db_name(code)}


def _pool_key() -> str:
    """Ключ пула: код города запроса в API на несколько городов, пустой — API одного города."""
    from cities import cache_key

    return cache_key()


async def _open_pool(config: dict) -> asyncpg.Pool:
    """Пул базы и SRID её сети; ошибки подключения — DatabaseConnectionError."""
    try:
        # Размер пула и таймаут запроса — из окружения: под нагрузкой 10 соединений
        # мало, а «вечный» запрос удерживает соединение и копит очередь.
        min_size = int(os.getenv("DB_POOL_MIN_SIZE", "2"))
        max_size = int(os.getenv("DB_POOL_MAX_SIZE", "20"))
        command_timeout = float(os.getenv("DB_COMMAND_TIMEOUT", "60"))
        logger.info(
            f"🔄 Инициализация пула для базы {config['database']} (min={min_size}, max={max_size}, "
            f"command_timeout={command_timeout}s)..."
        )
        from database.db_role import apply_db_role

        created = await asyncpg.create_pool(
            **config,
            min_size=min_size,
            max_size=max_size,
            command_timeout=command_timeout,
            # DB_ROLE_SWITCH: SET ROLE пользователя при каждой выдаче соединения (database/db_role.py)
            setup=apply_db_role,
            max_inactive_connection_lifetime=float(
                os.getenv("DB_POOL_MAX_INACTIVE_LIFETIME", "300")
            ),
        )
        logger.info("✅ Пул успешно инициализирован")
        # SRID колонок shape сети (9998 в Алматы и Шатуре, 9995 в Астане) — для запросов правки сети
        from database.net_srid import load_net_srid
        async with created.acquire() as conn:
            await load_net_srid(conn)
        return created
    except socket.gaierror as e:
        logger.error(f"❌ Не удалось разрешить хост {config['host']}:{config['port']}: {e}")
        raise DatabaseConnectionError(f"Не удалось подключиться к основной базе данных: хост {config['host']} недоступен")
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение с основной базой было разорвано: {e}")
        raise DatabaseConnectionError(f"Соединение с основной базой данных было неожиданно закрыто: {e}")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации пула базы {config['database']}: {e}", exc_info=True)
        raise DatabaseConnectionError(f"Ошибка подключения к базе {config['database']}: {e}")


async def ensure_city_pool(code: str) -> asyncpg.Pool:
    """Пул базы города (API на несколько городов); открывается при первом обращении."""
    from cities import use_city

    existing = city_pools.get(code)
    if existing is not None:
        return existing
    lock = _pool_locks.setdefault(code, asyncio.Lock())
    async with lock:
        existing = city_pools.get(code)
        if existing is None:
            with use_city(code):  # SRID сети запоминается за этим городом
                existing = await _open_pool(city_db_config(code))
            city_pools[code] = existing
    return existing


async def init_db_pool():
    """Пул основной базы; у API на несколько городов — пулы всех городов (недоступная база не мешает остальным)."""
    global pool
    from cities import city_databases, multi_city

    if multi_city():
        for code in city_databases():
            try:
                await ensure_city_pool(code)
            except DatabaseConnectionError as e:
                logger.error("Город %s: база недоступна при запуске (%s), повторю при первом запросе", code, e)
        return
    if pool is not None:
        logger.warning("Пул уже инициализирован, пропускаем повторную инициализацию")
        return
    pool = await _open_pool(DATABASE_CONFIG)


@asynccontextmanager
async def task_db_pool():
    """Пул базы на время фоновой задачи воркера (свой цикл asyncio): основной базы или города задачи."""
    from cities import multi_city

    key = _pool_key()
    if not key and multi_city():
        raise DatabaseConnectionError("Задача без города: базу не выбрать")
    if not key:
        await init_db_pool()
        try:
            yield get_pool()
        finally:
            await close_db_pool()
        return
    opened = await _open_pool(city_db_config(key))
    city_pools[key] = opened
    try:
        yield opened
    finally:
        city_pools.pop(key, None)
        _pool_locks.pop(key, None)  # замок привязан к циклу этой задачи
        await opened.close()


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
        logger.info(f"Попытка подключения к системной базе: {safe_db_config(temp_config)}")
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
        logger.info(f"Инициализация пула для UsersDB: {safe_db_config(USERS_DB_CONFIG)}")
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
    for code in list(city_pools):
        await city_pools.pop(code).close()
        logger.info("✅ Пул базы города %s закрыт", code)

async def close_users_db_pool():
    """Закрытие пула для БД пользователей."""
    global users_pool
    if users_pool:
        await users_pool.close()
        logger.info("✅ Пул БД пользователей закрыт")
        users_pool = None

def get_pool():
    """Пул базы города запроса (API на несколько городов) или основной базы."""
    key = _pool_key()
    if not key:
        from cities import multi_city

        if multi_city():
            raise DatabaseConnectionError("Город запроса не определён: путь API должен начинаться с /city/<код>/")
        return pool
    found = city_pools.get(key)
    if found is None:
        raise DatabaseConnectionError(f"База города {key} недоступна")
    return found


async def _current_pool() -> asyncpg.Pool:
    key = _pool_key()
    current = await ensure_city_pool(key) if key else get_pool()
    if not current:
        raise DatabaseConnectionError("Пул основной базы данных не инициализирован")
    return current


@asynccontextmanager
async def acquire_conn():
    """Контекстный менеджер для основной базы (базы города запроса)."""
    current = await _current_pool()
    logger.debug("Acquiring connection from main pool")
    try:
        conn = await current.acquire()
    except asyncpg.exceptions.ConnectionDoesNotExistError as e:
        logger.error(f"❌ Соединение в пуле основной базы было разорвано: {e}")
        raise DatabaseConnectionError(f"Соединение с основной базой было неожиданно закрыто во время операции")
    try:
        logger.debug("Main connection acquired")
        yield conn
    finally:
        await current.release(conn)
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