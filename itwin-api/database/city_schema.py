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
import re
import time
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
    Item("колонка calculation_protocol.ai_summary",
         "select to_regclass('public.calculation_protocol') is null or exists (select 1 from information_schema.columns"
         " where table_schema = 'public' and table_name = 'calculation_protocol' and column_name = 'ai_summary')",
         (_m("20261023_calculation_protocol_ai_summary.sql"),)),
    Item("таблицы calculation_iznos и wear_out",
         "select to_regclass('public.wear_out') is not null and to_regclass('public.calculation_iznos') is not null",
         (_m("20261023_wear_out.sql"),)),
    Item("таблица card_template",
         "select to_regclass('public.card_template') is not null",
         (_m("20261017_card_template.sql"),)),
    Item("таблица object_authorship",
         "select to_regclass('public.object_authorship') is not null",
         (_m("20261020_object_authorship.sql"),)),
    Item("таблицы сценариев tgid_scenario",
         "select to_regclass('public.tgid_scenario_object') is not null",
         (_m("20261029_scenarios.sql"),)),
    Item("колонка tgid_scenario_object.merge_group_id",
         "select to_regclass('public.tgid_scenario_object') is null or exists (select 1 from information_schema.columns"
         " where table_schema = 'public' and table_name = 'tgid_scenario_object' and column_name = 'merge_group_id')",
         (_m("20261029_scenario_merge.sql"),)),
    Item("таблица tgid_trace_config",
         "select to_regclass('public.tgid_trace_config') is not null",
         (_m("20261029_trace_config.sql"),)),
    Item("таблица tgid_layer_style",
         "select to_regclass('public.tgid_layer_style') is not null",
         (_m("20261029_layer_style.sql"),)),
    Item("таблицы нарядов tgid_work_order",
         "select to_regclass('public.tgid_work_order_event') is not null",
         (_m("20261030_work_orders.sql"),)),
    Item("пространственные индексы зданий",
         "select not exists (select 1 from information_schema.columns c where c.table_schema = 'public'"
         " and c.table_name in ('zdaniya_2', 'zdaniya_tu') and c.column_name = 'shape'"
         " and not exists (select 1 from pg_indexes i where i.schemaname = 'public' and i.tablename = c.table_name"
         " and i.indexdef ilike '%using gist (shape)%'))",
         (_m("20261029_buildings_gist.sql"),)),
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
    "ekibastuz": City(base_srid=3857),
    "atbasar": City(base_srid=3857),
    "kokshetau": City(base_srid=3857),
    "shakhtinsk": City(base_srid=3857),
}


def martin_sql_path(city: str) -> Path:
    """Файл функций тайлов города: MARTIN_SQL_FILE (API одного города) или MARTIN_SQL_DIR/<город>.sql."""
    explicit = os.getenv("MARTIN_SQL_FILE", "").strip()
    if explicit:
        return Path(explicit)
    folder = os.getenv("MARTIN_SQL_DIR", "").strip()
    return Path(folder) / f"{city}.sql" if folder and city else Path("-")


def martin_item(city: str = "") -> Optional[Item]:
    """Функции тайлов martin (scripts/martin): SQL сгенерирован на сервере из рабочей области GeoServer города
    и лежит вне репозитория — путь задаёт MARTIN_SQL_FILE службы API или каталог MARTIN_SQL_DIR у API на
    несколько городов (ставит install-martin.ps1). После переконвертации базы функции возвращаются, как
    остальные объекты веба. В комплект конвертера десктопа (scripts/export_web_schema.py, только COMMON и
    CITIES) не входит."""
    path = martin_sql_path(city)
    if not path.is_file():
        return None
    names = sorted(set(re.findall(r"FUNCTION public\.(tgid_mvt_\w+)\(", path.read_text(encoding="utf-8-sig"))))
    if not names:
        return None
    sigs = ", ".join(f"'public.{n}(integer,integer,integer,json)'" for n in names)
    return Item("функции тайлов martin",
                f"select bool_and(to_regprocedure(f) is not null) from unnest(array[{sigs}]) f", (path,))


def city_items(city: str) -> list[Item]:
    """Пункты города: его особые (SRID — первым), общие и функции тайлов martin (если заданы).
    Неизвестный город — только общие."""
    spec = CITIES.get(city, City(base_srid=None))
    local = martin_item(city)
    return [*spec.items, *COMMON, *([local] if local else [])]


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
            # Проверять каждый пункт заново перед применением, по порядку: пункт может зависеть от
            # предыдущего (колонка ai_summary «есть», пока нет самой таблицы calculation_protocol)
            applied = []
            for item in city_items(city):
                if await conn.fetchval(item.check):
                    continue
                for path in item.files:
                    await conn.execute(path.read_text(encoding="utf-8-sig"))
                applied.append(item.name)
            left = [i.name for i in await missing(conn, city)]
            if left:
                raise RuntimeError("после применения всё ещё нет: " + ", ".join(left))
    except Exception as e:  # noqa: BLE001 — транзакция откатилась, база как была
        return {"status": "error", "missing": names, "applied": [], "error": str(e).strip()}
    return {"status": "applied", "missing": [], "applied": applied}


def upkeep_interval_s() -> float:
    try:
        return max(0.0, float(os.getenv("DB_UPKEEP_INTERVAL_S", "600")))
    except ValueError:
        return 600.0


def _new_state() -> dict:
    return {
        "status": "unknown", "checked_at": None, "missing": [], "applied": [], "error": None,
        "db_oid": None, "recreated": 0, "recreated_at": None, "reset_pending": False,
    }


# Последняя проверка в этом процессе — для /health и метрик (observability.py).
# STATE — API одного города; API на несколько городов ведёт состояние каждого (STATES, cities.cache_key)
STATE: dict = _new_state()
STATES: dict[str, dict] = {}


def state() -> dict:
    """Состояние доводки базы города запроса (или единственного города API — STATE)."""
    from cities import cache_key

    key = cache_key()
    return STATES.setdefault(key, _new_state()) if key else STATE


def reset_city_caches() -> None:
    """Кеши API, построенные по прежней базе: граф отключений, каталог таблиц, ссылки на узлы."""
    from database.outage_simulation import invalidate_outage_cache
    from database.sql_ident import reset_catalog_cache
    from database.topology_transfer import reset_node_ref_cache

    invalidate_outage_cache()
    reset_catalog_cache()
    reset_node_ref_cache()


async def _note_db_identity(conn, city: str) -> bool:
    """True, если база пересоздана с прошлой проверки (переконвертация в десктопе: DROP + CREATE DATABASE).

    oid базы в pg_database меняется при пересоздании, имя — нет.
    """
    oid = await conn.fetchval("select oid from pg_database where datname = current_database()")
    st = state()
    prev = st["db_oid"]
    st["db_oid"] = oid
    if prev is None or prev == oid:
        return False
    st["recreated"] += 1
    st["recreated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    logger.warning("База города %s пересоздана (переконвертация из десктопа): сбрасываю кеши API", city)
    return True


async def run_once(pool, city: str) -> dict:
    """Один проход для пула API; после применения или пересоздания базы — перечитать SRID и кеши."""
    from database.net_srid import load_net_srid

    st = state()
    async with pool.acquire() as conn:
        if await _note_db_identity(conn, city):
            reset_city_caches()  # не отдавать данные прежней базы
            st["reset_pending"] = True
        res = await ensure(conn, city)
        ready = res["status"] in ("ok", "applied")
        # конвертер мог ещё дописывать базу, пока кеши заново строились, — сбросить, когда готова
        if ready and st.get("reset_pending"):
            reset_city_caches()
            st["reset_pending"] = False
            await load_net_srid(conn)
        elif res["status"] == "applied":
            await load_net_srid(conn)
    st.update(
        status=res["status"], checked_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        missing=res["missing"], applied=res["applied"], error=res.get("error"),
    )
    status = res["status"]
    if status == "applied":
        logger.info("База города %s доведена: %s", city, ", ".join(res["applied"]))
    elif status == "error":
        logger.error("База города %s: не удалось применить %s — %s", city, ", ".join(res["missing"]), res.get("error"))
    elif status in ("busy", "not_ready"):
        logger.info("База города %s: %s, повторю позже (нет: %s)", city, status, ", ".join(res["missing"]) or "—")
    return res


async def upkeep_loop(pool, city: str, interval_s: float) -> None:
    """Фоновая доводка: сразу при запуске и далее раз в interval_s (база могла быть переконвертирована).

    pool=None — API на несколько городов: пул города берётся (и при недоступной базе — открывается
    заново) на каждом проходе; задача должна выполняться в контексте города (cities.use_city).
    """
    from database.connect import ensure_city_pool

    while True:
        try:
            await run_once(pool if pool is not None else await ensure_city_pool(city), city)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — нет подключения и т. п.: попробовать в следующий раз
            logger.warning("Проверка схемы базы города %s не удалась: %s", city, e)
        await asyncio.sleep(interval_s)
