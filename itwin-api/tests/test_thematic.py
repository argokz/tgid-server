"""Тематические карты участков (thematic) и сохранённые стили слоя (layer_styles)."""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from database import layer_styles as ls
from database import thematic as th


class _Conn:
    """Запросы темы: пишет SQL и аргументы, отдаёт заданные строки."""

    def __init__(self, rows=(), run=None, regclass=True):
        self.rows = list(rows)
        self.run = run
        self.regclass = regclass
        self.sql: list[tuple[str, tuple]] = []

    async def fetchval(self, sql, *args):
        return self.regclass

    async def fetchrow(self, sql, *args):
        return self.run

    async def fetch(self, sql, *args):
        self.sql.append((sql, args))
        return self.rows


def _line(i, v, label=None):
    return {"id": i, "fileid": 74, "v": v, "label": label,
            "geometry": json.dumps({"type": "LineString", "coordinates": [[76.9, 43.2], [76.91, 43.21]]})}


def test_themes_payload_has_defaults():
    themes = {t["key"]: t for t in th.themes_payload()}
    assert {"diameter", "year", "wear", "heat_loss", "available_head", "tubing_type"} <= set(themes)
    assert themes["diameter"]["method"] == "manual" and themes["diameter"]["breaks"] == [80, 150, 250, 400, 600, 800]
    assert themes["tubing_type"]["kind"] == "category"
    with pytest.raises(th.ThematicError):
        th.get_theme("colour")


def test_clean_bbox():
    assert th.clean_bbox("76.9,43.2,77,43.3") == (76.9, 43.2, 77.0, 43.3)
    assert th.clean_bbox(None) is None
    for bad in ("1,2,3", "a,b,c,d", "77,43,76,44", "0,-95,1,1"):
        with pytest.raises(th.ThematicError):
            th.clean_bbox(bad)


def test_number_theme_rounds_and_summarises():
    conn = _Conn([_line(1, 152.4), _line(2, None), _line(3, 49.6)])
    res = asyncio.run(th.theme_features(conn, "diameter", [74, 74]))
    assert [f["properties"]["v"] for f in res["geojson"]["features"]] == [152, None, 50]
    assert res["summary"] == {"count": 3, "with_value": 2, "min": 50, "max": 152}
    assert res["truncated"] is False and res["source_run"] is None
    sql, args = conn.sql[0]
    # паспортная тема: без расчёта, без лишних аргументов; участки внутренних схем — мимо
    assert "calc_ut" not in sql and "internalnodeid" in sql and args == ([74], th.MAX_FEATURES + 1)


def test_calc_theme_uses_latest_fragment_calc_and_bbox():
    conn = _Conn([_line(1, 12.345)])
    res = asyncio.run(th.theme_features(conn, "available_head", [74], bbox=(76.9, 43.2, 77.0, 43.3)))
    assert res["geojson"]["features"][0]["properties"]["v"] == 12.3
    sql, args = conn.sql[0]
    assert "MAX(id) AS cid FROM calculation" in sql and "calc_ut AS MATERIALIZED" in sql and "ut.a18" in sql
    assert "ST_MakeEnvelope($3, $4, $5, $6, 4326)" in sql and args[2:] == (76.9, 43.2, 77.0, 43.3)


def test_category_theme_lists_categories():
    conn = _Conn([_line(1, 1, "Подземная"), _line(2, 4, "Надземная"), _line(3, 1, "Подземная"), _line(4, None)])
    res = asyncio.run(th.theme_features(conn, "tubing_type", [74]))
    assert res["summary"]["categories"] == [{"value": 1, "label": "Подземная", "count": 2},
                                            {"value": 4, "label": "Надземная", "count": 1}]
    assert "LEFT JOIN tubingtypes ref" in conn.sql[0][0]


def test_wear_theme_needs_a_run():
    with pytest.raises(th.ThematicError) as e:
        asyncio.run(th.theme_features(_Conn(regclass=False), "wear", [74]))
    assert e.value.status == 404
    run = {"id": 3, "name": "Город", "daterascheta": datetime(2026, 10, 23)}
    conn = _Conn([_line(1, 27.55)], run=run)
    res = asyncio.run(th.theme_features(conn, "wear", [74]))
    assert res["source_run"] == {"id": 3, "label": "Износ #3 Город от 23.10.2026"}
    sql, args = conn.sql[0]
    assert "w.calculationid = $3" in sql and args[2] == 3


def test_truncation_and_fragment_limits():
    conn = _Conn([_line(i, 100) for i in range(4)])
    res = asyncio.run(th.theme_features(conn, "diameter", [74], limit=3))
    assert res["truncated"] is True and res["summary"]["count"] == 3
    with pytest.raises(th.ThematicError):
        asyncio.run(th.theme_features(conn, "diameter", []))
    with pytest.raises(th.ThematicError):
        asyncio.run(th.theme_features(conn, "diameter", list(range(th.MAX_FRAGMENTS + 1))))


def _classes(**over):
    return {"theme": "diameter", "method": "manual", "classes": 3, "breaks": [100, 300],
            "colors": ["#00FF00", "#ffff00", "#ff0000"], **over}


def test_clean_style_numbers():
    s = ls.clean_style({**_classes(), "junk": "<script>", "width": 4})
    assert s == {"format": 1, "theme": "diameter", "method": "manual", "width": 4.0, "opacity": 0.9,
                 "show_nulls": True, "null_color": "#9e9e9e", "classes": 3, "colors": ["#00ff00", "#ffff00", "#ff0000"],
                 "breaks": [100.0, 300.0]}
    assert "breaks" not in ls.clean_style(_classes(method="quantile", breaks=None))
    for bad in (_classes(theme="colour"), _classes(method="median"), _classes(breaks=[300, 100]),
                _classes(breaks=[100]), _classes(colors=["red", "#ffff00", "#ff0000"]), _classes(classes=12),
                _classes(width=40), _classes(method="unique"), "x"):
        with pytest.raises(ls.LayerStyleError) as e:
            ls.clean_style(bad)
        assert e.value.status == 422


def test_clean_style_categories():
    s = ls.clean_style({"theme": "tubing_type", "method": "unique",
                        "categories": [{"value": 1, "color": "#123456"}, {"value": 4, "color": "#abcdef"}]})
    assert s["categories"] == [{"value": 1, "color": "#123456"}, {"value": 4, "color": "#abcdef"}]
    for cats in ([], [{"value": 1, "color": "#123456"}, {"value": 1, "color": "#123456"}], [{"value": "1"}]):
        with pytest.raises(ls.LayerStyleError):
            ls.clean_style({"theme": "tubing_type", "method": "unique", "categories": cats})
    with pytest.raises(ls.LayerStyleError):
        ls.clean_style({"theme": "tubing_type", "method": "quantile", "classes": 2, "colors": ["#000000", "#ffffff"]})


class _StyleConn:
    def __init__(self, row):
        self.row = row
        self.updates: list[tuple[str, tuple]] = []

    async def fetchval(self, sql, *args):
        return True

    async def fetchrow(self, sql, *args):
        if sql.startswith("SELECT id, author"):
            return self.row
        self.updates.append((sql, args))
        return None if "revision = $" in sql and args[-1] != self.row["revision"] else {
            "id": 5, "name": "Ду", "style": "{}", "revision": self.row["revision"] + 1, "author": self.row["author"],
            "shared": self.row["shared"], "updated_at": datetime(2026, 10, 29)}


def test_update_style_checks_owner_and_revision():
    mine = {"id": 5, "author": "ivan", "shared": False, "revision": 2}
    out = asyncio.run(ls.update_style(_StyleConn(mine), "5", name="Ду", style=None, shared=None, revision=2,
                                      user="ivan", can_shared=False))
    assert out["revision"] == 3
    with pytest.raises(ls.LayerStyleError) as e:
        asyncio.run(ls.update_style(_StyleConn(mine), "5", name="Ду", style=None, shared=None, revision=1,
                                    user="ivan", can_shared=False))
    assert e.value.status == 409
    with pytest.raises(ls.LayerStyleError) as e:
        asyncio.run(ls.update_style(_StyleConn(mine), "5", name="x", style=None, shared=None, revision=None,
                                    user="petr", can_shared=True))
    assert e.value.status == 404  # чужой личный стиль не виден
    shared = {**mine, "shared": True}
    with pytest.raises(ls.LayerStyleError) as e:
        asyncio.run(ls.delete_style(_StyleConn(shared), "5", user="petr", can_shared=False))
    assert e.value.status == 403


def test_endpoints(monkeypatch):
    import main
    from auth import invalidate_user_status
    from routers import thematic

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield _Conn([_line(1, 200)])

    monkeypatch.setattr(thematic, "acquire_conn", acquire)
    client = TestClient(main.app)
    assert any(t["key"] == "diameter" for t in client.get("/api/v1/thematic/themes").json()["themes"])
    r = client.get("/api/v1/thematic/pipes", params={"theme": "diameter", "fragment_ids": "74,75"})
    assert r.status_code == 200 and r.json()["summary"]["max"] == 200
    assert client.get("/api/v1/thematic/pipes", params={"theme": "diameter", "fragment_ids": "x"}).status_code == 422
    assert client.get("/api/v1/thematic/pipes", params={"theme": "colour", "fragment_ids": "74"}).status_code == 422
    r = client.get("/api/v1/thematic/pipes", params={"theme": "diameter", "fragment_ids": "74", "bbox": "1,2"})
    assert r.status_code == 422
