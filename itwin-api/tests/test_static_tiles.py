"""PMTiles v3 (database/pmtiles.py), запекание статичных слоёв (database/static_tiles.py) и маршруты."""

import asyncio
import gzip
import json
import random
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from database import pmtiles
from database import static_tiles as st


# --- формат ------------------------------------------------------------------------------------

def test_tile_ids_follow_spec():
    # значения из спецификации PMTiles v3
    assert [pmtiles.zxy_to_tileid(*t) for t in ((0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0), (2, 0, 0))] \
        == [0, 1, 2, 3, 4, 5]
    assert pmtiles.zxy_to_tileid(12, 3423, 1763) == 19078479
    rnd = random.Random(7)
    for _ in range(500):
        z = rnd.randint(0, 22)
        x, y = rnd.randrange(1 << z), rnd.randrange(1 << z)
        assert pmtiles.tileid_to_zxy(pmtiles.zxy_to_tileid(z, x, y)) == (z, x, y)
    with pytest.raises(pmtiles.PMTilesError):
        pmtiles.zxy_to_tileid(2, 4, 0)


def test_directory_roundtrip():
    entries = [pmtiles.Entry(5, 0, 10, 1), pmtiles.Entry(6, 10, 7, 3), pmtiles.Entry(20, 0, 10, 1),
               pmtiles.Entry(21, 500, 1, 0)]
    assert pmtiles.deserialize_directory(pmtiles.serialize_directory(entries)) == entries


def test_writer_reader_roundtrip_dedup_and_runs(tmp_path):
    path = tmp_path / "a.pmtiles"
    w = pmtiles.Writer(path)
    same = b"same-tile"
    for x in range(4):
        w.add_tile(2, x, 0, same)  # одинаковые — одно содержимое; соседние по кривой — серией
    w.add_tile(3, 1, 1, b"other")
    with pytest.raises(pmtiles.PMTilesError):
        w.add_tile(3, 1, 1, b"again")
    summary = w.finish(metadata={"name": "t"}, bounds=(76.0, 43.0, 77.0, 44.0))
    assert summary["tiles"] == 5 and summary["contents"] == 2 and summary["min_zoom"] == 2 and summary["max_zoom"] == 3
    assert summary["entries"] < 5
    r = pmtiles.Reader(path)
    assert r.metadata == {"name": "t"} and r.header.bounds == (76.0, 43.0, 77.0, 44.0)
    assert r.header.tile_type == pmtiles.TILE_TYPE_MVT and r.header.tile_compression == pmtiles.COMPRESSION_GZIP
    assert [r.get(2, x, 0) for x in range(4)] == [same] * 4
    assert r.get(3, 1, 1) == b"other"
    assert r.get(2, 0, 1) is None and r.get(9, 0, 0) is None and r.get(3, 99, 0) is None
    assert not list(tmp_path.glob("*.tiles")) and not list(tmp_path.glob("*.part"))


def test_leaf_directories_when_root_is_too_big(tmp_path, monkeypatch):
    monkeypatch.setattr(pmtiles, "ROOT_MAX", 300)
    path = tmp_path / "big.pmtiles"
    w = pmtiles.Writer(path)
    for x in range(64):
        for y in range(64):
            w.add_tile(6, x, y, f"{x}:{y}".encode())
    w.finish(metadata={}, bounds=(0, 0, 1, 1))
    r = pmtiles.Reader(path)
    assert r.header.leaf_length > 0
    assert r.get(6, 17, 42) == b"17:42" and r.get(6, 63, 63) == b"63:63"


def test_bad_files(tmp_path):
    bad = tmp_path / "bad.pmtiles"
    bad.write_bytes(b"NotPMTiles" + b"\0" * 200)
    with pytest.raises(pmtiles.PMTilesError, match="не архив"):
        pmtiles.Reader(bad)
    w = pmtiles.Writer(tmp_path / "empty.pmtiles")
    with pytest.raises(pmtiles.PMTilesError, match="пуст"):
        w.finish(metadata={}, bounds=(0, 0, 1, 1))
    assert not (tmp_path / "empty.pmtiles").exists() and not list(tmp_path.glob("*.tiles"))


# --- запекание ---------------------------------------------------------------------------------

FUNC_STATIC = 'CREATE FUNCTION ... -- у слоя нет параметров\n FROM public."zdaniya_2"'
FUNC_NET = "CREATE FUNCTION ... p ->> 'fragments'"


class _Conn:
    """База города: функции тайлов, охват, тайлы — непустые только в заданном квадрате."""

    def __init__(self, filled=lambda z, x, y: True):
        self.filled = filled
        self.calls: list[tuple[int, int, int]] = []

    async def fetch(self, sql, *args):
        return [
            {"proname": "tgid_mvt_heatpipesections", "comment": '{"description": "виден с зума 9"}', "def": FUNC_NET},
            {"proname": "tgid_mvt_zdaniya_2", "comment": '{"description": "виден с зума 14"}', "def": FUNC_STATIC},
        ]

    async def fetchrow(self, sql, *args):
        return {"w": 76.90, "s": 43.20, "e": 76.92, "n": 43.21}

    async def fetchval(self, sql, *args):
        if "information_schema" in sql:
            return True
        z, x, y = args
        self.calls.append((z, x, y))
        return f"mvt {z}/{x}/{y}".encode() if self.filled(z, x, y) else None


@pytest.fixture
def tiles_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("STATIC_TILES_DIR", str(tmp_path))
    monkeypatch.setattr(st, "current_city", lambda: "almaty")
    st._readers.clear()
    return tmp_path


def test_bakeable_layers():
    layers = {x["layer"]: x for x in asyncio.run(st.bakeable_layers(_Conn()))}
    assert layers["zdaniya_2"] == {"layer": "zdaniya_2", "minzoom": 14, "static": True, "table": "zdaniya_2"}
    assert layers["heatpipesections"]["static"] is False and layers["heatpipesections"]["minzoom"] == 9


def test_tiles_in_bbox():
    tiles = st.tiles_in_bbox((76.90, 43.20, 76.92, 43.21), 14)
    xs, ys = {t[1] for t in tiles}, {t[2] for t in tiles}
    assert min(xs) == 11691 and len(xs) == 1 + max(xs) - min(xs) and all(t[0] == 14 for t in tiles)
    assert len(tiles) == len(xs) * len(ys)


def test_bake_descends_only_into_filled_tiles(tiles_dir):
    m = st.BBOX_MARGIN_DEG
    first = st.tiles_in_bbox((76.90 - m, 43.20 - m, 76.92 + m, 43.21 + m), 14)
    keep = first[0]

    def filled(z, x, y):  # непуст только один тайл z14 и его потомки
        shift = z - 14
        return (x >> shift, y >> shift) == (keep[1], keep[2])

    conns = [_Conn(filled), _Conn(filled)]
    messages = []
    res = asyncio.run(st.bake(conns, "zdaniya_2", maxzoom=16, progress=messages.append, user="ivan"))
    assert res["tiles_per_zoom"] == {14: 1, 15: 4, 16: 16} and res["tiles"] == 21
    calls = conns[0].calls + conns[1].calls
    assert len(calls) == len(first) + 4 + 16  # на z15–16 — только дочерние непустых
    assert messages[0].startswith("Зум 14") and messages[-1].startswith("Запись архива")
    r = st.reader("zdaniya_2")
    assert gzip.decompress(r.get(15, keep[1] * 2, keep[2] * 2 + 1)) == f"mvt 15/{keep[1] * 2}/{keep[2] * 2 + 1}".encode()
    assert r.metadata["tgid"]["built_by"] == "ivan" and r.metadata["vector_layers"][0]["id"] == "zdaniya_2"
    archives = st.list_archives()
    assert [a["layer"] for a in archives] == ["zdaniya_2"] and archives[0]["minzoom"] == 14
    assert (tiles_dir / "almaty" / "zdaniya_2.pmtiles").is_file()
    assert st.delete_archive("zdaniya_2") is True and st.list_archives() == [] and st.reader("zdaniya_2") is None


def test_bake_refuses_bad_requests(tiles_dir, monkeypatch):
    with pytest.raises(st.StaticTilesError, match="фрагментов"):
        asyncio.run(st.bake([_Conn()], "heatpipesections"))
    with pytest.raises(st.StaticTilesError) as e:
        asyncio.run(st.bake([_Conn()], "nosuch"))
    assert e.value.status == 404
    with pytest.raises(st.StaticTilesError, match="Зумы"):
        asyncio.run(st.bake([_Conn()], "zdaniya_2", minzoom=15, maxzoom=14))
    with pytest.raises(st.StaticTilesError, match="латиница"):
        st.archive_path("../x")
    with pytest.raises(st.StaticTilesError, match="пуст"):
        asyncio.run(st.bake([_Conn(lambda z, x, y: False)], "zdaniya_2", maxzoom=15))
    monkeypatch.setattr(st, "MAX_TILES", 3)
    with pytest.raises(st.StaticTilesError, match="тайлов"):
        asyncio.run(st.bake([_Conn()], "zdaniya_2", maxzoom=16))
    assert not list(tiles_dir.rglob("*.pmtiles")) and not list(tiles_dir.rglob("*.tiles"))


# --- маршруты ----------------------------------------------------------------------------------

def test_endpoints(tiles_dir, monkeypatch):
    import main
    from auth import invalidate_user_status
    from routers import static_tiles as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield _Conn()

    monkeypatch.setattr(router, "acquire_conn", acquire)

    async def no_audit(**kwargs):
        pass

    monkeypatch.setattr(router, "write_audit_log", no_audit)
    w = pmtiles.Writer(tiles_dir / "almaty" / "zdaniya_2.pmtiles")
    w.add_tile(14, 11692, 6006, gzip.compress(b"tile-bytes"))
    w.finish(metadata={"tgid": {"built_at": "2026-10-29T15:00:00+00:00"}}, bounds=(76.9, 43.2, 76.92, 43.21))
    client = TestClient(main.app)

    listed = client.get("/api/v1/static-tiles").json()
    assert listed["archives"][0]["layer"] == "zdaniya_2" and listed["can_build"] is True
    assert [x["layer"] for x in listed["layers"]] == ["zdaniya_2"]

    r = client.get("/api/v1/static-tiles/zdaniya_2/14/11692/6006.mvt?v=1")
    assert r.status_code == 200 and r.content == b"tile-bytes"  # клиент сам снял gzip по Content-Encoding
    assert r.headers["content-encoding"] == "gzip" and "max-age" in r.headers["cache-control"]
    assert client.get("/api/v1/static-tiles/zdaniya_2/14/0/0").status_code == 204
    assert client.get("/api/v1/static-tiles/nosuch/14/0/0").status_code == 404
    assert client.get("/api/v1/static-tiles/Bad-Name/14/0/0").status_code == 422
    assert client.get("/api/v1/static-tiles/zdaniya_2/14/0/abc").status_code == 422

    part = client.get("/api/v1/static-tiles/zdaniya_2.pmtiles", headers={"Range": "bytes=0-6"})
    assert part.status_code == 206 and part.content == b"PMTiles"

    calls = []

    class _Task:
        id = "task-1"

    def apply_async(kwargs, queue=None):
        calls.append((kwargs, queue))
        return _Task()

    import worker

    monkeypatch.setattr(worker.bake_static_tiles, "apply_async", apply_async)
    r = client.post("/api/v1/static-tiles/zdaniya_2/build", json={"maxzoom": 15})
    assert r.json() == {"task_id": "task-1", "status": "queued"}
    assert calls[0][0] == {"layer": "zdaniya_2", "minzoom": 14, "maxzoom": 15, "user": calls[0][0]["user"]}
    assert client.post("/api/v1/static-tiles/heatpipesections/build", json={}).status_code == 422
    assert client.post("/api/v1/static-tiles/nosuch/build", json={}).status_code == 404
    assert client.post("/api/v1/static-tiles/zdaniya_2/build", json={"minzoom": 16, "maxzoom": 15}).status_code == 422

    assert client.delete("/api/v1/static-tiles/zdaniya_2").json() == {"deleted": "zdaniya_2"}
    assert client.delete("/api/v1/static-tiles/zdaniya_2").status_code == 404
    assert json.loads(client.get("/api/v1/static-tiles").text)["archives"] == []
