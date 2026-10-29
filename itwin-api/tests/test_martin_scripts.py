"""Генераторы martin (scripts/martin): разбор слоёв GeoServer, функции тайлов, минимальный зум, конфиг."""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / "martin" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fn = _load("build_martin_functions")
cfg = _load("build_martin_config")

VIEW_XML = """<featureType>
  <name>heatpipesections</name>
  <srs>EPSG:9998</srs>
  <metadata><entry key="JDBC_VIRTUAL_TABLE"><virtualTable>
    <name>heatpipesections</name>
    <sql>select l.id, l.fileid, '%RAS%' as ras, %nach% as nach, l.shape from linesobj l
where (CASE WHEN '%fragments%' = '' THEN true ELSE l.fileid = ANY(string_to_array('%fragments%', '_')::int[]) END)</sql>
    <geometry><name>shape</name><type>LineString</type><srid>9998</srid></geometry>
    <parameter><name>RAS</name><defaultValue>off</defaultValue></parameter>
    <parameter><name>nach</name><defaultValue>0</defaultValue><regexpValidator>^[0-9]+$</regexpValidator></parameter>
    <parameter><name>fragments</name><defaultValue></defaultValue><regexpValidator>^[0-9_]+$</regexpValidator></parameter>
  </virtualTable></entry></metadata>
</featureType>"""

TABLE_XML = """<featureType>
  <name>zdaniya_2</name><nativeName>zdaniya_2</nativeName><srs>EPSG:9998</srs>
  <attributes>
    <attribute><name>shape</name><binding>org.locationtech.jts.geom.MultiPolygon</binding></attribute>
    <attribute><name>objectid</name><binding>java.lang.Long</binding></attribute>
    <attribute><name>otop</name><binding>java.math.BigDecimal</binding></attribute>
  </attributes>
</featureType>"""


def _write(tmp_path: Path, layer: str, xml: str) -> Path:
    d = tmp_path / "ws" / "ws" / layer
    d.mkdir(parents=True)
    (d / "featuretype.xml").write_text(xml, encoding="utf-8")
    return d / "featuretype.xml"


def test_parse_virtual_table(tmp_path):
    spec = fn.parse_featuretype(_write(tmp_path, "heatpipesections", VIEW_XML))
    assert (spec.name, spec.geometry, spec.srid, spec.geometry_type) == ("heatpipesections", "shape", 9998, "LineString")
    assert [(p.name, p.default, p.regex) for p in spec.params] == [
        ("RAS", "off", fn.GEOSERVER_DEFAULT_REGEX), ("nach", "0", "^[0-9]+$"), ("fragments", "", "^[0-9_]+$")]
    assert spec.buffer == fn.BUFFER_OTHER
    sql = fn.default_sql(spec)
    assert "'off' as ras" in sql and "0 as nach" in sql and "'%" not in sql


def test_parse_table_with_attributes(tmp_path):
    spec = fn.parse_featuretype(_write(tmp_path, "zdaniya_2", TABLE_XML))
    assert spec.columns == ["objectid", "otop"] and spec.geometry == "shape" and spec.geometry_type == "MultiPolygon"
    assert spec.sql == 'SELECT "objectid", "otop", "shape" FROM public."zdaniya_2"'


def test_render_function_mirrors_geoserver(tmp_path):
    spec = fn.parse_featuretype(_write(tmp_path, "heatpipesections", VIEW_XML))
    spec.columns, spec.column_types, spec.minzoom = ["id", "fileid", "ras", "nach"], {"fileid": "numeric"}, 9
    sql = fn.render_function(spec)
    assert "CREATE OR REPLACE FUNCTION public.tgid_mvt_heatpipesections(z integer, x integer, y integer" in sql
    assert "IF z < 9 THEN" in sql                                  # мельче слой не виден в стиле
    assert "query_params ->> 'viewparams'" in sql                  # строка viewparams, как у GeoServer
    assert "v ~ '^[0-9]+$'" not in sql and "v !~ '^[0-9]+$'" in sql  # проверка значения — как у GeoServer
    assert 'v."fileid"::float8 AS "fileid"' in sql                 # numeric → float8 для ST_AsMVT
    assert "margin => 0.015625" in sql                              # буфер линий 64/4096
    assert "$sql$" in sql and "%fragments%" in sql                  # SQL представления — без изменений


def test_zoom_for_scale():
    assert fn.zoom_for_scale(36000) == 14          # здания: 1:36 000
    assert fn.zoom_for_scale(1091957.55) == 9      # узлы gid8
    assert fn.zoom_for_scale(fn.SCALE_Z0 * 2) == 0


def test_style_minzoom_sld_and_mbstyle(tmp_path):
    ws = tmp_path / "Ws"
    (ws / "Ws" / "zd").mkdir(parents=True)
    (ws / "Ws" / "zd" / "layer.xml").write_text("<layer><defaultStyle><id>S1</id></defaultStyle></layer>", encoding="utf-8")
    (ws / "styles").mkdir()
    (ws / "styles" / "zd.xml").write_text("<style><id>S1</id><format>sld</format><filename>zd.sld</filename></style>",
                                          encoding="utf-8")
    (ws / "styles" / "zd.sld").write_text(
        "<sld:Rule><sld:MaxScaleDenominator>36000</sld:MaxScaleDenominator></sld:Rule>"
        "<sld:Rule><sld:MaxScaleDenominator>5000</sld:MaxScaleDenominator></sld:Rule>", encoding="utf-8")
    assert fn.style_minzoom(ws / "Ws", "zd") == 14
    # правило без ограничения масштаба — слой виден везде
    (ws / "styles" / "zd.sld").write_text("<Rule></Rule>", encoding="utf-8")
    assert fn.style_minzoom(ws / "Ws", "zd") == 0
    (ws / "styles" / "zd.xml").write_text(
        "<style><id>S1</id><format>mbstyle</format><filename>zd.json</filename></style>", encoding="utf-8")
    (ws / "styles" / "zd.json").write_text('{"layers": [{"minzoom": 12}, {"minzoom": 9}]}', encoding="utf-8")
    assert fn.style_minzoom(ws / "Ws", "zd") == 9
    assert fn.style_minzoom(ws / "Ws", "missing") == 0


def test_martin_config(monkeypatch):
    monkeypatch.setenv("DB_USER", "tgid")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:w/rd")
    monkeypatch.setenv("DB_HOST", "127.0.0.1")
    monkeypatch.setenv("DB_PORT", "5432")
    text = cfg.render_config([("almaty", "almatygid", ["uzel", "heatpipesections"]), ("astana", "astanagid", [])],
                             "127.0.0.1:3005", 8, 512)
    assert "postgres://tgid:p%40ss%3Aw%2Frd@127.0.0.1:5432/almatygid" in text   # пароль экранирован
    assert "almaty_uzel:" in text and "function: tgid_mvt_heatpipesections" in text
    assert "astana" not in text                                               # город без функций пропущен
    assert "auto_publish: false" in text


@pytest.mark.parametrize("bad", ["almaty", "=db", "1x=db"])
def test_martin_config_city_arg_validation(bad, monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["x", "--city", bad, "--out", str(tmp_path / "c.yaml"), "--env-file", str(tmp_path / ".env")])
    with pytest.raises(SystemExit):
        cfg.main()
