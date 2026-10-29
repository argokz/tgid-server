"""Базовые маршруты: фрагменты, русские названия, карточки линий/узлов, справочники."""

import json
from contextlib import nullcontext
import time
from typing import Optional

from asyncpg.exceptions import UndefinedColumnError
from fastapi import APIRouter, HTTPException, Query

from app_logging import get_logger
from database.connect import acquire_conn
from database.db import (
    create_select_line,
    create_select_node,
    get_all_fragments,
    get_lookup_data,
)
from database.fragment_filter import parse_fragment_ids
from database.sql_ident import UnknownIdentifierError
from utils.russian_names import russian_names_manager

logger = get_logger(__name__)

router = APIRouter(tags=["core"])


def _identifier_http_error(exc: UnknownIdentifierError) -> HTTPException:
    """Неизвестная таблица → 404, неизвестная колонка/идентификатор → 400 (без SQL в ответе)."""
    if exc.kind == "table":
        return HTTPException(status_code=404, detail="Неизвестная таблица")
    return HTTPException(status_code=400, detail=f"Недопустимый идентификатор ({exc.kind})")


async def _add_russian_names_to_response(data: dict, table: str) -> dict:
    """Добавляет русские названия к полям в ответе API."""
    try:
        if "tabs" not in data:
            return data

        for tab in data["tabs"]:
            if "subsections" not in tab:
                continue

            for subsection in tab["subsections"]:
                if "fields" not in subsection:
                    continue

                for field in subsection["fields"]:
                    if "field" in field:
                        # Получаем русское название для поля
                        field_name = field["field"]
                        russian_name, description = russian_names_manager.get_russian_name(f"{table}|{field_name}")

                        # Добавляем русское название и описание к полю
                        field["russian_name"] = russian_name
                        if description:
                            field["description"] = description

                        # Если русское название отличается от английского, обновляем label
                        if russian_name != field_name and russian_name != field_name.lower():
                            field["label"] = russian_name

        return data
    except Exception as e:
        logger.error(f"Ошибка при добавлении русских названий: {str(e)}")
        return data


async def _db_check() -> tuple[bool, Optional[str]]:
    from database.connect import acquire_conn

    try:
        async with acquire_conn() as conn:
            await conn.fetchval("SELECT 1")
        return True, None
    except Exception as e:  # noqa: BLE001
        return False, str(e)


@router.get("/health")
@router.get("/api/health")
async def health():
    """Проверка живости: БД, Redis/Celery broker, число маршрутов."""
    import os

    from cities import city_databases, current_city, multi_city, use_city
    from database.city_schema import state as city_schema_state

    started = time.monotonic()
    # API на несколько городов без префикса города (/health процесса) — проверка базы каждого города
    every_city = multi_city() and not current_city()
    per_city: dict[str, dict] = {}
    for code in (city_databases() if every_city else [current_city()]):
        with use_city(code) if every_city else nullcontext():
            ok, error = await _db_check()
            schema = {k: v for k, v in city_schema_state().items() if k not in ("db_oid", "reset_pending")}
        per_city[code] = {"ok": ok, "error": error, "city_schema": schema}
    db_ok = all(c["ok"] for c in per_city.values())
    db_error = next((f"{code}: {c['error']}" if every_city else c["error"]
                     for code, c in per_city.items() if c["error"]), None)

    redis_ok = False
    redis_error = None
    redis_started = time.monotonic()
    try:
        import redis as redis_lib

        addr = os.getenv("REDIS_ADDR", "127.0.0.1:6379")
        password = os.getenv("REDIS_PASSWORD", "").strip() or None
        host, _, port_s = addr.partition(":")
        client = redis_lib.Redis(
            host=host or "127.0.0.1",
            port=int(port_s or "6379"),
            password=password,
            db=int(os.getenv("REDIS_DB", "").strip() or "0"),
            socket_connect_timeout=1.5,
            socket_timeout=1.5,
        )
        redis_ok = bool(client.ping())
        client.close()
    except Exception as e:  # noqa: BLE001
        redis_error = str(e)

    status = "ok" if db_ok else "degraded"
    if db_ok and not redis_ok:
        status = "degraded"
    # Схема базы города (database/city_schema.py): веб-добавки на месте, была ли переконвертация
    schemas = [c["city_schema"] for c in per_city.values()]
    if any(s["status"] == "error" for s in schemas):
        status = "degraded"
    city_schema = schemas[0] if not every_city else {
        "status": "error" if any(s["status"] == "error" for s in schemas) else "ok",
        "cities": {code: c["city_schema"] for code, c in per_city.items()},
    }

    database = {
        "ok": db_ok,
        "latency_ms": round((time.monotonic() - started) * 1000, 1),
        "error": db_error,
    }
    if every_city:
        database["cities"] = {code: {"ok": c["ok"], "error": c["error"]} for code, c in per_city.items()}
    return {
        "status": status,
        "database": database,
        "redis": {
            "ok": redis_ok,
            "latency_ms": round((time.monotonic() - redis_started) * 1000, 1),
            "error": redis_error,
            "note": None if redis_ok else "sety / heat-loss run требуют Redis + Celery worker",
        },
        "city_schema": city_schema,
        "routes": len(_route_paths()),
        "russian_names_initialized": russian_names_manager.initialized,
        "flags": {
            "auth_disabled": os.getenv("AUTH_DISABLED", "true").strip().lower()
            in {"1", "true", "yes", "on"},
            "dev_login_enabled": os.getenv("DEV_LOGIN_ENABLED", "false")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
            "strict_auth": os.getenv("STRICT_AUTH", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            "mutations_enabled": os.getenv("MUTATIONS_ENABLED", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            "topology_mutations_enabled": os.getenv(
                "TOPOLOGY_MUTATIONS_ENABLED", "false"
            )
            .strip()
            .lower()
            in {"1", "true", "yes", "on"},
        },
    }


def _route_paths() -> set:
    try:
        from main import app

        return {getattr(r, "path", "") for r in app.routes if getattr(r, "path", "")}
    except Exception:
        return set()


@router.get("/fragments")
async def get_fragments():
    """Получить список фрагментов."""
    try:
        data = await get_all_fragments()
        return {"data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении фрагментов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении фрагментов")


# Охват фрагментов (WGS84) по действующим узлам — выбор фрагмента и «Домой» центрируют карту (QA F25).
# Узлы внутренних схем не в счёт: их координаты условные, охват уходил бы за город.
# Охват — по каждому фрагменту отдельно и без случайных далёких узлов (узел без координат у 0°, 0°:
# в Шатуре у «Петербурга» их 28 — карта уходила бы на пол-Земли): «ядро» фрагмента — 2–98 % узлов
# по долготе и широте, к нему — все узлы не дальше трёх размеров ядра (и не меньше ~20 км) от его краёв.
# Охват выбранных фрагментов — объединение охватов фрагментов (Шатура и Москва — обе на экране).
FRAGMENTS_EXTENT_SQL = """
    WITH p AS (
      SELECT n.fileid, ST_X(t.g) AS x, ST_Y(t.g) AS y
        FROM nodes n, LATERAL (SELECT ST_Transform(n.shape, 4326) AS g) t
       WHERE n.fileid = ANY($1::int[]) AND COALESCE(n.removed, 0) = 0 AND n.shape IS NOT NULL
         AND n.internalnodeid IS NULL
    ), core AS (
      SELECT fileid,
             percentile_cont(0.02) WITHIN GROUP (ORDER BY x) AS x0, percentile_cont(0.98) WITHIN GROUP (ORDER BY x) AS x1,
             percentile_cont(0.02) WITHIN GROUP (ORDER BY y) AS y0, percentile_cont(0.98) WITHIN GROUP (ORDER BY y) AS y1
        FROM p GROUP BY fileid
    ), kept AS (
      SELECT p.x, p.y
        FROM p JOIN core c USING (fileid)
       WHERE p.x BETWEEN c.x0 - greatest(3 * (c.x1 - c.x0), 0.3) AND c.x1 + greatest(3 * (c.x1 - c.x0), 0.3)
         AND p.y BETWEEN c.y0 - greatest(3 * (c.y1 - c.y0), 0.2) AND c.y1 + greatest(3 * (c.y1 - c.y0), 0.2)
    )
    SELECT min(x) AS min_lng, min(y) AS min_lat, max(x) AS max_lng, max(y) AS max_lat FROM kept
"""


@router.get("/api/fragments/extent")
@router.get("/api/v1/fragments/extent")
async def get_fragments_extent(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Фрагменты через запятую (fileid)"),
):
    """Охват фрагментов [min_lng, min_lat, max_lng, max_lat]; bbox = null — у фрагментов нет узлов."""
    ids = parse_fragment_ids(fragment_id, fragments)
    if not ids:
        raise HTTPException(status_code=422, detail="Укажите fragment_id или fragments")
    async with acquire_conn() as conn:
        row = await conn.fetchrow(FRAGMENTS_EXTENT_SQL, ids)
    bbox = None
    if row and row["min_lng"] is not None:
        bbox = [row["min_lng"], row["min_lat"], row["max_lng"], row["max_lat"]]
    return {"fragments": ids, "bbox": bbox}


# Версия данных карты: сумма счётчиков вставок/изменений/удалений строк по таблицам базы города.
# Меняется при любой записи — правка сети в вебе, в десктопе (он пишет прямо в базу), расчёт, импорт.
# Веб подставляет её в адрес тайлов (rev в VIEWPARAMS): новая версия — новые адреса мимо кешей
# GWC/nginx/браузера, одна версия — общие закешированные тайлы у всех пользователей.
DATA_VERSION_SQL = """
SELECT COALESCE(SUM(n_tup_ins + n_tup_upd + n_tup_del), 0)::bigint
FROM pg_stat_user_tables WHERE schemaname = 'public'
"""
DATA_VERSION_TTL_S = 10.0
# по городам (cities.cache_key): {"value", "at"}
_data_version_cache: dict[str, dict] = {}


@router.get("/api/v1/map/data-version")
async def get_map_data_version():
    """Версия данных для сброса кеша тайлов: {"version": "<число>"}; опрос раз в 30–60 с."""
    from cities import cache_key

    now = time.monotonic()
    entry = _data_version_cache.setdefault(cache_key(), {"value": None, "at": 0.0})
    if entry["value"] is None or now - entry["at"] >= DATA_VERSION_TTL_S:
        async with acquire_conn() as conn:
            entry["value"] = str(await conn.fetchval(DATA_VERSION_SQL))
        entry["at"] = now
    return {"version": entry["value"]}


@router.get("/russian-names")
async def get_russian_names():
    """Получить все русские названия колонок."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        data = russian_names_manager.get_all_mappings()
        return {"data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении русских названий: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении русских названий")


@router.get("/russian-names/{table}")
async def get_table_russian_names(table: str):
    """Получить русские названия колонок для указанной таблицы."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        data = russian_names_manager.get_table_mappings(table)
        return {"table": table, "data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении русских названий для таблицы {table}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении русских названий для таблицы {table}")


@router.get("/russian-names/column/{column}")
async def get_column_russian_name(column: str):
    """Получить русское название для указанной колонки."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        russian_name, description = russian_names_manager.get_russian_name(column)
        return {
            "column": column,
            "russian_name": russian_name,
            "description": description
        }
    except Exception as e:
        logger.error(f"Ошибка при получении русского названия для колонки {column}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении русского названия для колонки {column}")


@router.get("/line/{table}/{id}")
async def get_line(table: str, id: int, include_russian_names: bool = False):
    """Получить данные для линейного объекта."""
    try:
        logger.debug(f"Fetching line data for table={table}, id={id}")
        result = await create_select_line(table, id)
        logger.debug(f"Line data fetched: {result[:100]}...")

        data = json.loads(result)

        # Добавляем русские названия если запрошено
        if include_russian_names and russian_names_manager.initialized:
            data = await _add_russian_names_to_response(data, table)

        return {"data": data}
    except UnknownIdentifierError as e:
        raise _identifier_http_error(e)
    except UndefinedColumnError:
        # Таблица не относится к линейным объектам (нет lineID) — это ошибка
        # запроса клиента, а не сбой сервера
        raise HTTPException(
            status_code=400,
            detail=f"Таблица «{table}» не является линейным объектом (нет колонки lineID). "
                   f"Для точечных объектов используйте /node/{table}/{id}.",
        )
    except Exception as e:
        logger.error(f"Error fetching line data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении данных линейного объекта")


@router.get("/node/{table}/{id}")
async def get_node(table: str, id: int, include_russian_names: bool = False):
    """Получить данные для точечного объекта."""
    try:
        logger.debug(f"Fetching node data for table={table}, id={id}")
        result = await create_select_node(table, id)
        logger.debug(f"Node data fetched: {result[:100]}...")

        data = json.loads(result)

        # Добавляем русские названия если запрошено
        if include_russian_names and russian_names_manager.initialized:
            data = await _add_russian_names_to_response(data, table)

        return {"data": data}
    except UnknownIdentifierError as e:
        raise _identifier_http_error(e)
    except UndefinedColumnError:
        raise HTTPException(
            status_code=400,
            detail=f"Таблица «{table}» не является точечным объектом (нет колонки nodeID). "
                   f"Для линейных объектов используйте /line/{table}/{id}.",
        )
    except Exception as e:
        logger.error(f"Error fetching node data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении данных точечного объекта")


@router.get("/lookup")
@router.get("/api/v1/lookup")
async def get_lookup(table: str, id_col: str, name_col: str, sort_col: str = 'none'):
    """Получает справочные данные (Select Options)."""
    try:
        data = await get_lookup_data(table, id_col, name_col, sort_col)
        return {"data": data}
    except UnknownIdentifierError as e:
        raise _identifier_http_error(e)
    except Exception as e:
        logger.error(f"Error getting lookup for {table!r}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении справочника")
