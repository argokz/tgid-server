"""Комплект схемы веба для конвертера десктопа gid8: те же пункты, что применяет API (city_schema).

Конвертер (gid8/python/pg/pg.py) пересоздаёт базу города, и пропадает всё, что добавлял веб.
Чтобы база была готова сразу после конвертации, конвертер применяет этот комплект сам:
manifest.json (пункты: проверка + SQL-файлы, по городам) и копии SQL-файлов из sql/.

  python scripts/export_web_schema.py --out H:\\projects\\tgid-app\\gid8\\python\\pg\\web

Запускать после каждого нового пункта в database/city_schema.py и пересылать каталог
разработчику десктопа. API по-прежнему доводит базу сам — комплект только убирает окно,
когда карта после переконвертации не работает.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cities import _DB_CITY_ALIASES  # noqa: E402
from database import city_schema  # noqa: E402


def _rel(path: Path) -> str:
    return path.relative_to(city_schema.SQL_DIR).as_posix()


def _item(item: city_schema.Item) -> dict:
    return {"name": item.name, "check": item.check, "files": [_rel(p) for p in item.files]}


def _api_revision() -> str:
    try:
        out = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=10, check=True)
        return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build_manifest() -> dict:
    return {
        "about": "Схема веба ТГИД для базы города: пункты database/city_schema.py itwin-api",
        "api_revision": _api_revision(),
        "db_city_aliases": dict(_DB_CITY_ALIASES),
        "ready_sql": city_schema.ready_sql("unknown"),
        "common": [_item(i) for i in city_schema.COMMON],
        "cities": {
            code: {"base_srid": spec.base_srid, "items": [_item(i) for i in spec.items]}
            for code, spec in city_schema.CITIES.items()
        },
    }


def export(out: Path) -> dict:
    manifest = build_manifest()
    files = {f for item in manifest["common"] for f in item["files"]}
    files |= {f for city in manifest["cities"].values() for item in city["items"] for f in item["files"]}
    sql_out = out / "sql"
    if sql_out.exists():
        shutil.rmtree(sql_out)  # только наш каталог комплекта: старые файлы не должны остаться
    for rel in sorted(files):
        target = sql_out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(city_schema.SQL_DIR / rel, target)
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path, help="каталог комплекта (gid8/python/pg/web)")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    manifest = export(args.out)
    n = len(manifest["common"]) + sum(len(c["items"]) for c in manifest["cities"].values())
    print(f"Комплект схемы веба: {n} пунктов, API {manifest['api_revision']} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
