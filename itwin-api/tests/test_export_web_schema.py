"""Комплект схемы веба для конвертера десктопа совпадает с тем, что применяет API."""
import json
import sys
from pathlib import Path

from database import city_schema

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_web_schema  # noqa: E402


def test_export_matches_city_schema(tmp_path):
    export_web_schema.export(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    assert [i["name"] for i in manifest["common"]] == [i.name for i in city_schema.COMMON]
    assert set(manifest["cities"]) == set(city_schema.CITIES)
    for code, spec in city_schema.CITIES.items():
        assert manifest["cities"][code]["base_srid"] == spec.base_srid
        assert [i["check"] for i in manifest["cities"][code]["items"]] == [i.check for i in spec.items]
    # каждый файл скопирован байт в байт
    for item in [*manifest["common"], *(i for c in manifest["cities"].values() for i in c["items"])]:
        for rel in item["files"]:
            assert (tmp_path / "sql" / rel).read_bytes() == (city_schema.SQL_DIR / rel).read_bytes()
    assert manifest["db_city_aliases"]["shahtinsk"] == "shakhtinsk"


def test_reexport_removes_stale_files(tmp_path):
    stale = tmp_path / "sql" / "migrations" / "old.sql"
    stale.parent.mkdir(parents=True)
    stale.write_text("select 1;", encoding="utf-8")
    export_web_schema.export(tmp_path)
    assert not stale.exists()
