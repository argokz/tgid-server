"""База города (Астана, Шатура) после конвертации из десктопа: вернуть то, что нужно вебу.

Конвертер пересоздаёт базу, и пропадают правки, без которых карта и API Астаны не работают:
  - SRID 9998 описан как Алматы (ST_Transform уводит объекты под Алматы);
  - нет функций tg_format* — слои GeoServer uzel/heatpipesections падают, карта пустая;
  - нет индекса nodes_internalnodeid_idx (знак камеры на карте) и таблиц миграций API.

С 22.10.2026 это делает сам API (database/city_schema.py — при запуске и раз в 10 минут), отдельная
задача планировщика не нужна; скрипт — для ручной проверки (--check) и применения.

Скрипт проверяет базу и применяет SQL только недостающих пунктов (у каждого свой идемпотентный файл
из sql/) одной транзакцией. Пока конвертер работает — базы нет, нет таблиц сети или в ней идёт
запись, — ничего не делает и выходит с кодом 0: следующий запуск повторит.

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
sys.path.insert(0, str(ROOT))
from database.city_schema import BUSY_SQL, CITIES, city_items, ready_sql  # noqa: E402

# Пункты (проверка → SQL) и готовность базы — общие с API (database/city_schema.py): API доводит
# базу сам при запуске и раз в 10 минут; скрипт — для ручной проверки и применения.
ITEMS: list = []
CITY = 'astana'


def use_city(city: str) -> None:
    global CITY
    CITY = city
    ITEMS[:] = city_items(city)


BUSY = BUSY_SQL


def log(msg: str) -> None:
    print(f'{datetime.now():%Y-%m-%d %H:%M:%S} {msg}', flush=True)


def connect(db: str):
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'), port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'postgres'), password=os.getenv('DB_PASSWORD', ''),
        dbname=db, application_name='astana_after_reconvert', connect_timeout=15)
    conn.set_client_encoding('UTF8')
    return conn


def missing(cur) -> list:
    out = []
    for item in ITEMS:
        cur.execute(item.check)
        if not cur.fetchone()[0]:
            out.append(item)
    return out


def run(db: str, check_only: bool, dry_run: bool, quiet: bool) -> int:
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
        cur.execute(ready_sql(CITY))
        if not cur.fetchone()[0]:
            log(f'{db}: нет таблиц сети или системы координат — конвертация не закончена, повторю позже')
            return 0
        todo = missing(cur)
        if not todo:
            if not quiet:
                log(f'{db}: всё на месте')
            return 0
        log(f'{db}: нет — {", ".join(i.name for i in todo)}')
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
        # только недостающее: у каждого пункта свой идемпотентный SQL
        files = [path for item in todo for path in item.files]
        for path in files:
            cur.execute(path.read_text(encoding='utf-8-sig'))
        left = missing(cur)
        if left:
            conn.rollback()
            log(f'{db}: после применения всё ещё нет — {", ".join(i.name for i in left)}; откат')
            return 2
        if dry_run:
            conn.rollback()
            log(f'{db}: --dry-run — применилось бы без ошибок, откат')
            return 0
        conn.commit()
        log(f'{db}: применено ({len(files)} скриптов)')
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
    ap.add_argument('--city', choices=sorted(CITIES), default='astana', help='город базы (система координат)')
    args = ap.parse_args()
    load_dotenv(ROOT / '.env')
    use_city(args.city)
    return max(run(db, args.check, args.dry_run, args.quiet) for db in args.db)


if __name__ == '__main__':
    sys.exit(main())
