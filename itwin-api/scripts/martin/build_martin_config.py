"""Конфигурация martin для всех городов: один процесс, у каждого города своя база и свои источники.

Источник `<префикс города><слой>` (almaty_heatpipesections) — функция tgid_mvt_<слой> в базе города
(её создаёт build_martin_functions.py). Префикс начинается с кода города: по нему проверка доступа
(/auth/check, cities.geoserver_request_cities) узнаёт город тайла, как по рабочей области GeoServer.

    venv/Scripts/python.exe scripts/martin/build_martin_config.py ^
        --city almaty=almatygid --city astana=astanagid_2026_09_22 ^
        --out C:\\tgid\\martin\\config.yaml

Учётные данные PostgreSQL — из .env API (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD); база — у каждого
города своя. Файл содержит пароль: класть вне репозитория, доступ — только службе и администраторам.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

FUNCTION_PREFIX = "tgid_mvt_"


def connection_string(db: str) -> str:
    user = quote(os.environ["DB_USER"], safe="")
    password = quote(os.environ.get("DB_PASSWORD", ""), safe="")
    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "5432")
    return f"postgres://{user}:{password}@{host}:{port}/{quote(db, safe='')}"


async def existing_layers(db: str) -> list[str]:
    """Слои, для которых в базе города есть функция tgid_mvt_<слой> (её создаёт build_martin_functions.py)."""
    import asyncpg

    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "localhost"), port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ["DB_USER"], password=os.environ.get("DB_PASSWORD", ""), database=db)
    try:
        rows = await conn.fetch(
            r"""SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                 WHERE n.nspname = 'public' AND p.proname LIKE 'tgid\_mvt\_%' ORDER BY p.proname""")
    finally:
        await conn.close()
    return [r["proname"][len(FUNCTION_PREFIX):] for r in rows]


def render_config(cities: list[tuple[str, str, list[str]]], listen: str, pool_size: int, cache_mb: int) -> str:
    lines = [
        "# Сгенерировано itwin-api scripts/martin/build_martin_config.py — не править руками.",
        f"listen_addresses: '{listen}'",
        "# тайлы меняются после правки сети и расчёта: веб добавляет к адресу версию данных (rev:N в viewparams),",
        "# новый адрес — новый ключ кеша",
        f"cache_size_mb: {cache_mb}",
        "postgres:",
    ]
    for code, db, layers in cities:
        if not layers:
            continue
        lines += [
            f"  - connection_string: '{connection_string(db)}'",
            "    auto_publish: false",
            f"    pool_size: {pool_size}",
            "    functions:",
        ]
        for layer in layers:
            lines += [
                f"      {code}_{layer}:",
                "        schema: public",
                f"        function: {FUNCTION_PREFIX}{layer}",
            ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--city", action="append", required=True, metavar="КОД=БАЗА",
                    help="город и его база, например almaty=almatygid (можно несколько)")
    ap.add_argument("--listen", default="127.0.0.1:3005")
    ap.add_argument("--pool-size", type=int, default=8, help="соединений с базой на город")
    ap.add_argument("--cache-mb", type=int, default=512)
    ap.add_argument("--env-file", type=Path, default=ROOT / ".env")
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    from dotenv import load_dotenv

    load_dotenv(args.env_file)
    cities = []
    for item in args.city:
        code, sep, db = item.partition("=")
        if not sep or not code.isidentifier() or not db:
            ap.error(f"--city {item!r}: нужно КОД=БАЗА")
        layers = asyncio.run(existing_layers(db))
        print(f"  {code}: база {db}, слоёв с функциями {len(layers)}" + (f" ({', '.join(layers)})" if layers else
                                                                       " — город пропущен, сначала build_martin_functions.py --apply"))
        cities.append((code.lower(), db, layers))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_config(cities, args.listen, args.pool_size, args.cache_mb), encoding="utf-8")
    sources = sum(len(c[2]) for c in cities)
    print(f"martin: городов {sum(1 for c in cities if c[2])}, источников {sources} -> {args.out}")
    return 0 if sources else 1


if __name__ == "__main__":
    sys.exit(main())
