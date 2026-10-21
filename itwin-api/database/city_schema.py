"""Схема базы города, без которой не работают API и карта: проверка и доводка без ручных скриптов.

База города приходит из десктопа (конвертер gid8) и после каждой переконвертации теряет то, что
добавлял веб: таблицы API (журнал отмены, протоколы расчёта, шаблоны карточек…), функции tg_format*
для слоёв GeoServer, индексы, а в Астане и Шатуре ещё и описание SRID 9998 (иначе объекты уезжают
под Алматы или в океан) и колонку linesobj.internalnodeid (в Шатуре её конвертер не создаёт).

API сам проверяет это при запуске и раз в DB_UPKEEP_INTERVAL_S секунд (по умолчанию 600; 0 — выкл.)
и применяет только недостающее — каждый пункт своим идемпотентным SQL из sql/, одной транзакцией.
Пока конвертер работает (нет таблиц сети, в базе идёт запись) — ничего не трогает, повторит позже.
Раньше то же делал scripts/astana_after_reconvert.py по задаче планировщика, которую пользователь
ставил для каждого города вручную; скрипт остаётся для ручной проверки (--check) и берёт пункты отсюда.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


@dataclass(frozen=True)
class Item:
    """Пункт схемы: проверка (запрос → true, если есть) и SQL, который его создаёт."""

    name: str
    check: str
    files: tuple[Path, ...]


@dataclass(frozen=True)
class City:
    # SRID, без которого база не готова (конвертер ещё не дописал spatial_ref_sys)
    base_srid: Optional[int]
    items: tuple[Item, ...] = field(default_factory=tuple)


def _m(name: str) -> Path:
    return SQL_DIR / "migrations" / name


# Порядок важен: повтор операций — после таблицы журнала
COMMON: tuple[Item, ...] = (
    Item("функции tg_format*",
         "select count(*) >= 8 from pg_proc where pronamespace = 'public'::regnamespace and proname like 'tg\\_format%'",
         (SQL_DIR / "astana" / "02_tg_format_functions.sql",)),
    Item("индекс nodes_internalnodeid_idx",
         "select to_regclass('public.nodes_internalnodeid_idx') is not null",
         (SQL_DIR / "astana" / "03_nodes_internalnodeid_idx.sql",)),
    Item("таблица topology_undo_log",
         "select to_regclass('public.topology_undo_log') is not null",
         (_m("20260927_topology_undo_log.sql"),)),
    Item("повтор операций топологии",
         "select exists (select 1 from information_schema.columns where table_schema = 'public'"
         " and table_name = 'topology_undo_log' and column_name = 'after_rows')",
         (_m("20261018_topology_redo.sql"),)),
    Item("таблица heatlosses_report_out",
         "select to_regclass('public.heatlosses_report_out') is not null",
         (_m("20260928_heat_losses_report_out.sql"),)),
    Item("таблица calculation_protocol",
         "select to_regclass('public.calculation_protocol') is not null",
         (_m("20261015_calculation_protocol.sql"),)),
    Item("таблица card_template",
         "select to_regclass('public.card_template') is not null",
         (_m("20261017_card_template.sql"),)),
    Item("таблица object_authorship",
         "select to_regclass('public.object_authorship') is not null",
         (_m("20261020_object_authorship.sql"),)),
    Item("колонка generalizedconsumers.name",
         "select to_regclass('public.generalizedconsumers') is null or exists (select 1 from information_schema.columns"
         " where table_schema = 'public' and table_name = 'generalizedconsumers' and column_name = 'name')",
         (SQL_DIR / "fixes" / "generalizedconsumers_name.sql",)),
)

_LINES_INNER = Item(
    "колонка linesobj.internalnodeid",
    "select exists (select 1 from information_schema.columns where table_schema = 'public'"
    " and table_name = 'linesobj' and column_name = 'internalnodeid')"
    " and exists (select 1 from pg_trigger where tgname = 'linesobj_internalnodeid'"
    " and tgrelid = 'public.linesobj'::regclass)",
    (SQL_DIR / "shatura" / "02_linesobj_internalnodeid.sql",),
)

CITIES: dict[str, City] = {
    "almaty": City(base_srid=None),
    "astana": City(base_srid=9995, items=(
        Item("SRID 9998 (Астана)",
             "select coalesce((select proj4text like '%+lon_0=72 %' from spatial_ref_sys where srid = 9998), false)",
             (SQL_DIR / "astana" / "01_srid_9998.sql",)),
    )),
    "shatura": City(base_srid=3857, items=(
        Item("SRID 9998 (Шатура)",
             "select coalesce((select proj4text like '+proj=merc %' and srtext like '%Shatura%'"
             " from spatial_ref_sys where srid = 9998), false)",
             (SQL_DIR / "shatura" / "01_srid_9998.sql",)),
        _LINES_INNER,
    )),
    # Конвертер записал сеть сразу в Web Mercator (колонки shape — SRID 3857): своя система не нужна,
    # длины — по эллипсоиду (topology.ground_length_sql); linesobj.internalnodeid есть, как в Алматы
    "taraz": City(base_srid=3857),
    "aktobe": City(base_srid=3857),
    "shymkent": City(base_srid=3857),
    "karaganda": City(base_srid=3857),
}


def city_items(city: str) -> list[Item]:
    """Пункты города: его особые (SRID — первым) и общие. Неизвестный город — только общие."""
    spec = CITIES.get(city, City(base_srid=None))
    return [*spec.items, *COMMON]


def ready_sql(city: str) -> str:
    """База готова: конвертер создал таблицы сети (и систему координат города)."""
    base = CITIES.get(city, City(base_srid=None)).base_srid
    sql = ("select to_regclass('public.nodes') is not null and to_regclass('public.linesobj') is not null"
           " and to_regclass('public.heatpipesections') is not null and to_regclass('public.externalcodes') is not null")
    if base is not None:
        sql += f" and exists (select 1 from spatial_ref_sys where srid = {int(base)})"
    return sql


# в базе идёт запись (конвертер ещё работает) — не мешать
BUSY_SQL = r"""
select count(*) from pg_stat_activity
 where datname = current_database() and pid <> pg_backend_pid() and backend_type = 'client backend'
   and (state like 'idle in transaction%'
        or (state = 'active' and query ~* '^\s*(insert|copy|create|alter|update|delete|drop|truncate|vacuum)'))
"""

# один процесс за раз (несколько API/воркеров на одной базе)
LOCK_KEY = 0x7467_6964  # 'tgid'


async def missing(conn, city: str) -> list[Item]:
    out = []
    for item in city_items(city):
        if not await conn.fetchval(item.check):
            out.append(item)
    return out


async def ensure(conn, city: str, apply: bool = True) -> dict:
    """Проверить и (apply) применить недостающее. → {status, missing, applied, error?}

    status: ok — всё на месте; applied — применено; missing — чего-то нет (apply=False);
    not_ready / busy — база ещё конвертируется или занята, повторить позже; error — не вышло.
    """
    if not await conn.fetchval(ready_sql(city)):
        return {"status": "not_ready", "missing": [], "applied": []}
    todo = await missing(conn, city)
    names = [i.name for i in todo]
    if not todo:
        return {"status": "ok", "missing": [], "applied": []}
    if not apply:
        return {"status": "missing", "missing": names, "applied": []}
    if await conn.fetchval(BUSY_SQL):
        return {"status": "busy", "missing": names, "applied": []}
    try:
        async with conn.transaction():
            if not await conn.fetchval("select pg_try_advisory_xact_lock($1)", LOCK_KEY):
                return {"status": "busy", "missing": names, "applied": []}
            # не ждать долго блокировок таблиц сети: лучше повторить в следующий раз
            await conn.execute("set local lock_timeout = '30s'")
            await conn.execute("set local statement_timeout = '15min'")
            for item in todo:
                for path in item.files:
                    await conn.execute(path.read_text(encoding="utf-8-sig"))
            left = [i.name for i in await missing(conn, city)]
            if left:
                raise RuntimeError("после применения всё ещё нет: " + ", ".join(left))
    except Exception as e:  # noqa: BLE001 — транзакция откатилась, база как была
        return {"status": "error", "missing": names, "applied": [], "error": str(e).strip()}
    return {"status": "applied", "missing": [], "applied": names}


def upkeep_interval_s() -> float:
    try:
        return max(0.0, float(os.getenv("DB_UPKEEP_INTERVAL_S", "600")))
    except ValueError:
        return 600.0


async def run_once(pool, city: str) -> dict:
    """Один проход для пула API; после применения — перечитать SRID и колонки сети."""
    from database.net_srid import load_net_srid

    async with pool.acquire() as conn:
        res = await ensure(conn, city)
        if res["status"] == "applied":
            await load_net_srid(conn)
    status = res["status"]
    if status == "applied":
        logger.info("База города %s доведена: %s", city, ", ".join(res["applied"]))
    elif status == "error":
        logger.error("База города %s: не удалось применить %s — %s", city, ", ".join(res["missing"]), res.get("error"))
    elif status in ("busy", "not_ready"):
        logger.info("База города %s: %s, повторю позже (нет: %s)", city, status, ", ".join(res["missing"]) or "—")
    return res


async def upkeep_loop(pool, city: str, interval_s: float) -> None:
    """Фоновая доводка: сразу при запуске и далее раз в interval_s (база могла быть переконвертирована)."""
    while True:
        try:
            await run_once(pool, city)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — нет подключения и т. п.: попробовать в следующий раз
            logger.warning("Проверка схемы базы города %s не удалась: %s", city, e)
        await asyncio.sleep(interval_s)
