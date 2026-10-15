"""База города (Астана, Шатура) после конвертации из десктопа: вернуть то, что нужно вебу.

Конвертер пересоздаёт базу, и пропадают правки, без которых карта и API Астаны не работают:
  - SRID 9998 описан как Алматы (ST_Transform уводит объекты под Алматы);
  - нет функций tg_format* — слои GeoServer uzel/heatpipesections падают, карта пустая;
  - нет индекса nodes_internalnodeid_idx (знак камеры на карте) и таблиц миграций API.

Скрипт проверяет базу и, если чего-то нет, применяет sql/astana/*.sql и sql/migrations/*.sql одной
транзакцией (все скрипты идемпотентные). Пока конвертер работает — базы нет, нет таблиц сети или в
ней идёт запись, — ничего не делает и выходит с кодом 0: следующий запуск из планировщика повторит.

  python scripts/astana_after_reconvert.py --db astanagid_2026_09_22            проверить и применить
  python scripts/astana_after_reconvert.py --db astanagid_2026_09_22 --check    только проверить
  python scripts/astana_after_reconvert.py --db astanagid_2026_09_22 --dry-run  применить и откатить
  python scripts/astana_after_reconvert.py --city shatura --db shatura            база Шатуры (SRID 9998 = 3857)

Коды выхода: 0 — всё на месте (или применено, или база ещё не готова), 1 — --check нашёл
недостающее, 2 — ошибка применения. Подключение — DB_HOST/DB_PORT/DB_USER/DB_PASSWORD из .env.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
# SRID 9998 по городам: (скрипт, проверка «описан правильно», система, без которой база не готова)
SRID_9998 = {
    'astana': (ROOT / 'sql' / 'astana' / '01_srid_9998.sql',
               "select coalesce((select proj4text like '%+lon_0=72 %' from spatial_ref_sys where srid = 9998), false)",
               9995),
    'shatura': (ROOT / 'sql' / 'shatura' / '01_srid_9998.sql',
                "select coalesce((select proj4text like '+proj=merc %' and srtext like '%Shatura%'"
                " from spatial_ref_sys where srid = 9998), false)",
                3857),
}
COMMON_SQL = [
    ROOT / 'sql' / 'astana' / '02_tg_format_functions.sql',
    ROOT / 'sql' / 'astana' / '03_nodes_internalnodeid_idx.sql',
    ROOT / 'sql' / 'migrations' / '20260927_topology_undo_log.sql',
    ROOT / 'sql' / 'migrations' / '20260928_heat_losses_report_out.sql',
    ROOT / 'sql' / 'migrations' / '20261015_calculation_protocol.sql',
]

# что должно быть в базе: название → запрос, возвращающий true
COMMON_CHECKS = {
    'функции tg_format*': (
        "select count(*) >= 8 from pg_proc where pronamespace = 'public'::regnamespace and proname like 'tg\\_format%'"),
    'индекс nodes_internalnodeid_idx': "select to_regclass('public.nodes_internalnodeid_idx') is not null",
    'таблица topology_undo_log': "select to_regclass('public.topology_undo_log') is not null",
    'таблица heatlosses_report_out': "select to_regclass('public.heatlosses_report_out') is not null",
    'таблица calculation_protocol': "select to_regclass('public.calculation_protocol') is not null",
}

# база готова: конвертер создал таблицы сети и систему координат Астаны
READY = (
    "select to_regclass('public.nodes') is not null and to_regclass('public.linesobj') is not null"
    " and to_regclass('public.heatpipesections') is not null and to_regclass('public.externalcodes') is not null"
    " and exists (select 1 from spatial_ref_sys where srid = {base})"
    " and exists (select 1 from spatial_ref_sys where srid = 9998)")

SQL_FILES: list[Path] = []
CHECKS: dict[str, str] = {}


def use_city(city: str) -> int:
    """Скрипты и проверки города; → SRID, который должен быть в базе (основа описания 9998)"""
    script, check, base = SRID_9998[city]
    SQL_FILES[:] = [script, *COMMON_SQL]
    CHECKS.clear()
    CHECKS[f'SRID 9998 ({city})'] = check
    CHECKS.update(COMMON_CHECKS)
    return base

# в базе идёт запись (конвертер ещё работает)
BUSY = r"""
select count(*) from pg_stat_activity
 where datname = current_database() and pid <> pg_backend_pid() and backend_type = 'client backend'
   and (state like 'idle in transaction%'
        or (state = 'active' and query ~* '^\s*(insert|copy|create|alter|update|delete|drop|truncate|vacuum)'))
"""


def log(msg: str) -> None:
    print(f'{datetime.now():%Y-%m-%d %H:%M:%S} {msg}', flush=True)


def connect(db: str):
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'), port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', ''),
        dbname=db, application_name='astana_after_reconvert', connect_timeout=15)
    conn.set_client_encoding('UTF8')
    return conn


def missing(cur) -> list[str]:
    out = []
    for name, sql in CHECKS.items():
        cur.execute(sql)
        if not cur.fetchone()[0]:
            out.append(name)
    return out


def run(db: str, check_only: bool, dry_run: bool, quiet: bool, base: int = 9995) -> int:
    try:
        conn = connect(db)
    except (psycopg2.OperationalError, UnicodeDecodeError) as e:
        # базы нет — конвертер её пересоздаёт. Текст ошибки до подключения сервер шлёт в cp1251.
        text = str(e).strip().splitlines()[0] if isinstance(e, psycopg2.Error) else 'база недоступна'
        log(f'{db}: нет подключения ({text}) — повторю позже')
        return 0
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(READY.format(base=base))
        if not cur.fetchone()[0]:
            log(f'{db}: нет таблиц сети или SRID {base}/9998 — конвертация не закончена, повторю позже')
            return 0
        todo = missing(cur)
        if not todo:
            if not quiet:
                log(f'{db}: всё на месте')
            return 0
        log(f'{db}: нет — {", ".join(todo)}')
        if check_only:
            return 1
        cur.execute(BUSY)
        busy = cur.fetchone()[0]
        if busy:
            log(f'{db}: в базе идёт запись ({busy} сеанс.) — конвертация не закончена, повторю позже')
            return 0

        conn.autocommit = False
        # не ждать долго блокировок (CREATE INDEX на nodes): лучше повторить при следующем запуске
        cur.execute("set local lock_timeout = '30s'")
        cur.execute("set local statement_timeout = '15min'")
        for path in SQL_FILES:
            cur.execute(path.read_text(encoding='utf-8-sig'))
        left = missing(cur)
        if left:
            conn.rollback()
            log(f'{db}: после применения всё ещё нет — {", ".join(left)}; откат')
            return 2
        if dry_run:
            conn.rollback()
            log(f'{db}: --dry-run — применилось бы без ошибок, откат')
            return 0
        conn.commit()
        log(f'{db}: применено ({len(SQL_FILES)} скриптов)')
        return 0
    except psycopg2.errors.LockNotAvailable:
        conn.rollback()
        log(f'{db}: таблица занята (lock_timeout) — повторю позже')
        return 0
    except psycopg2.Error as e:
        conn.rollback()
        log(f'{db}: ошибка — {str(e).strip()}')
        return 2
    finally:
        conn.close()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--db', action='append', required=True, help='база (можно несколько раз)')
    ap.add_argument('--check', action='store_true', help='только проверить, код 1 — чего-то нет')
    ap.add_argument('--dry-run', action='store_true', help='применить и откатить')
    ap.add_argument('--quiet', action='store_true', help='не писать «всё на месте» (для планировщика)')
    ap.add_argument('--city', choices=sorted(SRID_9998), default='astana', help='город базы (система координат)')
    args = ap.parse_args()
    load_dotenv(ROOT / '.env')
    base = use_city(args.city)
    return max(run(db, args.check, args.dry_run, args.quiet, base) for db in args.db)


if __name__ == '__main__':
    sys.exit(main())
