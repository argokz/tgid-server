"""Функции тайлов для martin из слоёв GeoServer: тот же SQL, те же параметры, те же атрибуты.

martin (MapLibre, Apache-2.0/MIT) отдаёт векторные тайлы прямо из PostGIS. Источник — функция
`(z integer, x integer, y integer, query_params json) RETURNS bytea`: martin передаёт в неё параметры
адреса тайла. Веб уже передаёт GeoServer параметры SQL-представлений строкой
`viewparams=fragments:74_99;RAS:on;rev:123;` — функция разбирает её так же, как GeoServer, и
подставляет значения в SQL представления (проверка — регулярным выражением параметра; без своего —
выражением GeoServer по умолчанию ^[\\w\\d\\s]*$). Атрибуты тайла и имя слоя внутри тайла — как у
GeoServer, поэтому стили MapLibre и подписи работают без изменений.

Источник SQL — featuretype.xml рабочей области GeoServer города: SQL-представление (<virtualTable>)
или таблица (<nativeName> + <attributes>). Колонки представления узнаются у базы (LIMIT 0).

    venv/Scripts/python.exe scripts/martin/build_martin_functions.py ^
        --workspace-dir C:\\ProgramData\\GeoServer\\workspaces\\AlmatyGIS\\AlmatyGIS ^
        --out sql/martin/almaty.sql

Подключение к базе — как у API (.env, поверх него .env.copy, если есть и не задан --no-copy).
Результат — SQL-файл (CREATE OR REPLACE FUNCTION tgid_mvt_<слой>): применяется к базе города
скриптом выката; функции — объекты веба, таблицы десктопа не меняются.
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DEFAULT_LAYERS = ("heatpipesections", "uzel", "zdaniya_2", "zdaniya_tu")
GEOSERVER_DEFAULT_REGEX = r"^[\w\d\s]*$"
FUNCTION_PREFIX = "tgid_mvt_"
EXTENT = 4096
# Полоса вокруг тайла (из 4096). GeoServer считает её по размерам значков стиля: у узлов — до ~310,
# поэтому точкам с запасом 512 (значки и подписи у края тайла не обрезаются); линиям и полигонам
# хватает 64 — их соседний тайл дорисует сам
BUFFER_POINT = 512
BUFFER_OTHER = 64
# Масштаб GeoServer для сетки EPSG:900913 (тайл 256 px): 559082264 / 2^z
SCALE_Z0 = 559082264.0287178
# Типы, которые ST_AsMVT кодирует неверно (numeric читается как float8 по сырым байтам) — приводим
CAST_FLOAT8 = {"numeric"}


@dataclass
class Param:
    name: str
    default: str
    regex: str


@dataclass
class LayerSpec:
    name: str
    geometry: str
    srid: int
    sql: str                                   # подзапрос строк слоя (с %параметрами%)
    params: list[Param] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    geometry_type: str = ""                    # Point / LineString / MultiPolygon …
    column_types: dict[str, str] = field(default_factory=dict)
    minzoom: int = 0                           # мельче — слой не виден ни в одном правиле стиля

    @property
    def buffer(self) -> int:
        return BUFFER_POINT if "point" in self.geometry_type.lower() else BUFFER_OTHER


def _text(xml: str, tag: str) -> str | None:
    m = re.search(rf"<{tag}>(.*?)</{tag}>", xml, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def parse_featuretype(path: Path) -> LayerSpec:
    xml = path.read_text(encoding="utf-8")
    name = _text(xml, "name") or path.parent.name
    srs = _text(xml, "srs") or "EPSG:4326"
    srid = int(srs.split(":")[-1])
    vt = re.search(r"<virtualTable>(.*?)</virtualTable>", xml, re.S)
    if vt:
        body = vt.group(1)
        sql = _text(body, "sql") or ""
        geom = re.search(r"<geometry>\s*<name>(.*?)</name>.*?<srid>(\d+)</srid>", body, re.S)
        params = []
        for p in re.findall(r"<parameter>(.*?)</parameter>", body, re.S):
            params.append(Param(_text(p, "name") or "", _text(p, "defaultValue") or "",
                                _text(p, "regexpValidator") or GEOSERVER_DEFAULT_REGEX))
        gtype = re.search(r"<geometry>.*?<type>(.*?)</type>", body, re.S)
        return LayerSpec(name, geom.group(1) if geom else "shape",
                         int(geom.group(2)) if geom and geom.group(2) else srid, sql, params,
                         geometry_type=gtype.group(1) if gtype else "")
    table = _text(xml, "nativeName") or name
    attrs = re.findall(r"<attribute>\s*<name>(.*?)</name>\s*.*?<binding>(.*?)</binding>", xml, re.S)
    if not attrs:
        # список атрибутов не задан — GeoServer публикует все колонки; их и геометрию узнаем у базы
        return LayerSpec(name, "", srid, f'SELECT * FROM public."{table}"')
    geom = next((a for a, b in attrs if "jts.geom" in b), "shape")
    cols = [a for a, b in attrs if "jts.geom" not in b]
    select = ", ".join(f'"{c}"' for c in cols) + f', "{geom}"'
    gtype = next((b.rsplit(".", 1)[-1] for a, b in attrs if "jts.geom" in b), "")
    return LayerSpec(name, geom, srid, f'SELECT {select} FROM public."{table}"', [], cols, geometry_type=gtype)


def default_sql(spec: LayerSpec) -> str:
    sql = spec.sql
    for p in spec.params:
        sql = sql.replace(f"%{p.name}%", p.default)
    return sql


async def introspect_columns(conn, spec: LayerSpec) -> list[str]:
    """Колонки строк слоя без геометрии; геометрия не задана — первая колонка типа geometry.
    Типы колонок — в spec.column_types (numeric кодируется приведением к float8)."""
    stmt = await conn.prepare(f"SELECT * FROM ({default_sql(spec)}) q LIMIT 0")
    attrs = stmt.get_attributes()
    spec.column_types = {a.name: a.type.name for a in attrs}
    if not spec.geometry:
        spec.geometry = next(a.name for a in attrs if a.type.name == "geometry")
    if not spec.geometry_type:
        spec.geometry_type = await conn.fetchval(
            f'SELECT GeometryType("{spec.geometry}") FROM ({default_sql(spec)}) q WHERE "{spec.geometry}" IS NOT NULL LIMIT 1') or ""
    return [a.name for a in attrs if a.name != spec.geometry and a.type.name != "geometry"]


def zoom_for_scale(max_scale: float) -> int:
    """Наименьший зум, на котором масштаб не крупнее max_scale (правило стиля уже видно)."""
    return max(0, math.ceil(math.log2(SCALE_Z0 / max_scale) - 1e-6))


def style_minzoom(workspace_dir: Path, layer: str) -> int:
    """Минимальный зум слоя по стилю по умолчанию: SLD — по MaxScaleDenominator правил, MBStyle — по
    minzoom слоёв стиля. Правило без ограничения или стиль не найден — 0 (тайлы на всех зумах)."""
    layer_xml = (workspace_dir / layer / "layer.xml")
    if not layer_xml.exists():
        return 0
    m = re.search(r"<defaultStyle>\s*<id>(.*?)</id>", layer_xml.read_text(encoding="utf-8"), re.S)
    if not m:
        return 0
    style_id = m.group(1)
    dirs = [workspace_dir.parent / "styles", workspace_dir.parents[1].parent / "styles"]
    for d in dirs:
        for xml_path in d.glob("*.xml") if d.exists() else []:
            xml = xml_path.read_text(encoding="utf-8", errors="replace")
            if f"<id>{style_id}</id>" not in xml:
                continue
            fname = _text(xml, "filename")
            body_path = d / fname if fname else None
            if not body_path or not body_path.exists():
                return 0
            body = body_path.read_text(encoding="utf-8", errors="replace")
            if (_text(xml, "format") or "").lower() == "mbstyle":
                layers = json.loads(body).get("layers", [])
                zooms = [ly.get("minzoom") for ly in layers]
                return 0 if not zooms or any(z is None for z in zooms) else int(min(zooms))
            rules = re.findall(r"<(?:\w+:)?Rule>(.*?)</(?:\w+:)?Rule>", body, re.S)
            scales = [re.search(r"MaxScaleDenominator>\s*([0-9.]+)", r) for r in rules]
            if not rules or any(sc is None for sc in scales):
                return 0
            return min(zoom_for_scale(float(sc.group(1))) for sc in scales)
    return 0


def _dollar(text: str, tag: str) -> str:
    if f"${tag}$" in text:
        raise ValueError(f"В SQL слоя встречается ${tag}$ — нужен другой ограничитель")
    return f"${tag}${text}${tag}$"


def render_function(spec: LayerSpec) -> str:
    fn = f"{FUNCTION_PREFIX}{spec.name}"
    cols = ", ".join(
        f'v."{c}"::float8 AS "{c}"' if spec.column_types.get(c) in CAST_FLOAT8 else f'v."{c}"' for c in spec.columns)
    param_lines = []
    for p in spec.params:
        param_lines.append(
            f"    v := p ->> {_lit(p.name)};\n"
            f"    IF v IS NULL THEN v := {_lit(p.default)};\n"
            f"    ELSIF v !~ {_lit(p.regex)} THEN\n"
            f"        RAISE EXCEPTION 'Недопустимое значение параметра {p.name}: %', v USING ERRCODE = '22023';\n"
            f"    END IF;\n"
            f"    q := replace(q, {_lit('%' + p.name + '%')}, v);")
    params_block = "\n".join(param_lines) or "    -- у слоя нет параметров"
    tile_sql = (
        "SELECT ST_AsMVT(t, %L, " + str(EXTENT) + ", 'geom') FROM ("
        f"SELECT {cols}, ST_AsMVTGeom(ST_Transform(v.\"{spec.geometry}\", 3857), $1, {EXTENT}, {spec.buffer}, true) AS geom "
        # отбор — с полосой буфера вокруг тайла, как у GeoServer: точки и подписи у края не пропадают
        f"FROM (%s) v WHERE v.\"{spec.geometry}\" && ST_Transform(ST_TileEnvelope($2, $3, $4, margin => {spec.buffer / EXTENT}), {spec.srid})) t"
    )
    return f"""-- Слой GeoServer {spec.name}: {len(spec.columns)} атрибутов, параметров {len(spec.params)}, SRID {spec.srid}, {spec.geometry_type}, буфер {spec.buffer}, с зума {spec.minzoom}
CREATE OR REPLACE FUNCTION public.{fn}(z integer, x integer, y integer, query_params json DEFAULT '{{}}'::json)
RETURNS bytea LANGUAGE plpgsql STABLE PARALLEL SAFE AS $fn$
DECLARE
    q text := {_dollar(spec.sql, "sql")};
    p jsonb := '{{}}'::jsonb;
    item text;
    k text;
    v text;
    mvt bytea;
BEGIN
    IF z < {spec.minzoom} THEN
        RETURN NULL;  -- мельче слой не виден ни в одном правиле стиля GeoServer: пустой тайл
    END IF;
    -- viewparams=a:1;b:2; — как у GeoServer; отдельные параметры адреса — поверх
    FOREACH item IN ARRAY string_to_array(coalesce(query_params ->> 'viewparams', ''), ';') LOOP
        CONTINUE WHEN item = '' OR position(':' IN item) = 0;
        k := split_part(item, ':', 1);
        p := p || jsonb_build_object(k, substr(item, length(k) + 2));
    END LOOP;
    p := p || (coalesce(query_params, '{{}}'::json)::jsonb - 'viewparams');
{params_block}
    EXECUTE format({_lit(tile_sql)}, {_lit(spec.name)}, q) INTO mvt USING ST_TileEnvelope(z, x, y), z, x, y;
    RETURN mvt;
END
$fn$;
-- minzoom в описании нет намеренно: martin ответил бы 404 на мелкие зумы, а пустой тайл функции — 204
COMMENT ON FUNCTION public.{fn}(integer, integer, integer, json) IS
    {_lit('{"description": "ТГИД: слой ' + spec.name + ' (как GeoServer, виден с зума ' + str(spec.minzoom) + '), параметры — viewparams"}')};
"""


def _lit(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


async def build(workspace_dir: Path, layers: list[str], out: Path, use_copy: bool,
                db_name: str | None = None, apply: bool = False) -> list[LayerSpec]:
    """Функции слоёв в SQL-файл out; apply — сразу выполнить его в базе (одной транзакцией).
    Слоя нет в рабочей области (в Астане нет zdaniya_2) — пропускается."""
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    if use_copy and (ROOT / ".env.copy").exists():
        load_dotenv(ROOT / ".env.copy", override=True)
    if db_name:
        os.environ["DB_NAME"] = db_name
    import asyncpg

    conn = await asyncpg.connect(
        host=os.environ.get("DB_HOST", "localhost"), port=int(os.environ.get("DB_PORT", "5432")),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], database=os.environ["DB_NAME"])
    specs = []
    try:
        for name in layers:
            if not (workspace_dir / name / "featuretype.xml").exists():
                print(f"  слоя {name} нет в {workspace_dir} — пропущен")
                continue
            spec = parse_featuretype(workspace_dir / name / "featuretype.xml")
            columns = await introspect_columns(conn, spec)
            if not spec.columns:
                spec.columns = columns
            spec.minzoom = style_minzoom(workspace_dir, name)
            specs.append(spec)
        header = (f"-- Сгенерировано scripts/martin/build_martin_functions.py из {workspace_dir}\n"
                  f"-- База: {os.environ['DB_NAME']}. Не править руками — перегенерировать.\n\n")
        sql = header + "\n".join(render_function(s) for s in specs)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(sql, encoding="utf-8")
        if apply and specs:
            async with conn.transaction():
                await conn.execute(sql)
    finally:
        await conn.close()
    return specs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workspace-dir", required=True, type=Path, help="каталог рабочей области GeoServer (…/<ws>/<ws>)")
    ap.add_argument("--layers", default=",".join(DEFAULT_LAYERS), help="слои через запятую")
    ap.add_argument("--out", required=True, type=Path, help="SQL-файл результата")
    ap.add_argument("--no-copy", action="store_true", help="не подмешивать .env.copy")
    ap.add_argument("--db-name", help="база города (иначе DB_NAME из .env)")
    ap.add_argument("--apply", action="store_true", help="сразу создать функции в базе")
    args = ap.parse_args()
    specs = asyncio.run(build(args.workspace_dir, [s for s in args.layers.split(",") if s], args.out,
                              not args.no_copy, args.db_name, args.apply))
    for s in specs:
        print(f"{FUNCTION_PREFIX}{s.name}: атрибутов {len(s.columns)}, параметров {len(s.params)}, SRID {s.srid}, "
              f"{s.geometry_type}, буфер {s.buffer}, с зума {s.minzoom}")
    print(f"-> {args.out}" + (" (применено к базе)" if args.apply and specs else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
