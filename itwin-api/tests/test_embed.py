"""Встраиваемые карты: ключи и тайлы (database/embed.py, routers/embed.py)."""

import asyncio
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from auth import create_access_token, invalidate_user_status
from database import embed as em

SECRET = "test-secret-test-secret-test-secret-123"


def test_origins_layers_and_fragments_are_normalized():
    body = em.KeyIn(name="  Портал акимата ", origins=["https://Akimat.kz/portal/", "https://akimat.kz", "http://localhost:8080"],
                    layers=["valves", "pipes"], fragments=[74, 3, 74])
    assert body.name == "Портал акимата"
    assert body.origins == ["http://localhost:8080", "https://akimat.kz"]
    assert body.layers == ["pipes", "valves"]  # порядок слоёв — как в LAYERS (участки под точками)
    assert body.fragments == [3, 74]
    for bad in ("javascript:alert(1)", "akimat.kz", "https://user@akimat.kz", "ftp://akimat.kz", "https://"):
        with pytest.raises(ValidationError):
            em.KeyIn(name="x", origins=[bad], layers=["pipes"])
    with pytest.raises(ValidationError):
        em.KeyIn(name="x", origins=["https://a.kz"], layers=["buildings"])
    with pytest.raises(ValidationError):
        em.KeyIn(name="x", origins=["https://a.kz"], layers=["pipes"], view={"center": [200, 0], "zoom": 12})


def test_tile_sql_fields_have_no_pii_and_overview_filter():
    sql = em.tile_sql("consumers", 15)
    assert "AS load_gcal_h" in sql and "AS name" not in sql  # имена потребителей — ПДн
    assert "ST_AsMVT(t, 'consumers', 4096, 'geom', 'id')" in sql and "$4::int[] IS NULL" in sql
    assert "diametercondit >= 500" in em.tile_sql("pipes", 10)
    assert "diametercondit >= 300" in em.tile_sql("pipes", 12)
    assert "diametercondit >=" not in em.tile_sql("pipes", 14)
    assert f"{em.line_inner_sql('lo')} IS NULL" in em.tile_sql("pipes", 14)  # без линий внутренних схем
    assert "AND lo.shape && ST_Transform(ST_TileEnvelope" in em.tile_sql("valves", 16)


KEY = em.EmbedKey(5, "Портал", ("https://akimat.kz",), ("pipes", "nodes"), (74,), True, None)


class FakeConn:
    def __init__(self, row=None, tile=b"\x1a\x02"):
        self.row, self.tile_bytes = row, tile
        self.calls = []

    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args))
        return self.row

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return self.tile_bytes

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return []

    async def execute(self, sql, *args):
        self.calls.append((sql, args))


def test_tile_checks_layer_zoom_grid_and_caches_overview():
    em._tiles.clear()
    conn = FakeConn()
    with pytest.raises(em.EmbedError, match="не открыт"):
        asyncio.run(em.tile(conn, KEY, "valves", 16, 0, 0))
    with pytest.raises(em.EmbedError):
        asyncio.run(em.tile(conn, KEY, "pipes", 10, 1024, 0))
    assert asyncio.run(em.tile(conn, KEY, "nodes", 14, 1, 1)) == b""  # ниже зума слоя — без запроса
    assert conn.calls == []
    assert asyncio.run(em.tile(conn, KEY, "pipes", 11, 1, 1)) == b"\x1a\x02"
    assert conn.calls[0][1] == (11, 1, 1, [74])
    asyncio.run(em.tile(conn, KEY, "pipes", 11, 1, 1))
    assert len(conn.calls) == 1  # обзорный тайл — из памяти
    asyncio.run(em.tile(conn, KEY, "pipes", 16, 1, 1))
    asyncio.run(em.tile(conn, KEY, "pipes", 16, 1, 1))
    assert len(conn.calls) == 3  # подробные — каждый раз из базы


def test_resolve_rejects_unknown_and_caches():
    em._cache.clear()
    with pytest.raises(em.EmbedError, match="Нужен ключ"):
        asyncio.run(em.resolve(FakeConn(), "abc"))
    with pytest.raises(em.EmbedError, match="не принят"):
        asyncio.run(em.resolve(FakeConn(row=None), "tge_missing"))
    row = {"id": 5, "name": "Портал", "origins": ["https://akimat.kz"], "layers": ["pipes"], "fragments": None,
           "outages": False, "view": '{"center": [71.4, 51.1], "zoom": 12}'}
    conn = FakeConn(row=row)
    key = asyncio.run(em.resolve(conn, "tge_good"))
    assert key.layers == ("pipes",) and key.fragments is None and key.view == {"center": [71.4, 51.1], "zoom": 12}
    asyncio.run(em.resolve(conn, "tge_good"))
    assert len(conn.calls) == 1
    assert conn.calls[0][1] == (em.hash_key("tge_good"),)  # в базе — только хеш


def test_public_config_hides_internals():
    cfg = em.public_config(KEY, extent=[71.0, 51.0, 72.0, 52.0], city="Астана", outages_enabled=False)
    assert cfg["origins"] == ["https://akimat.kz"] and cfg["fragments"] == [74]
    assert [l["id"] for l in cfg["layers"]] == ["pipes", "nodes"] and cfg["layers"][1]["minzoom"] == 15
    assert cfg["outages"] is False  # ключ просит, но служба ленту не включила
    assert "key_hash" not in cfg and "created_by" not in cfg


@pytest.fixture
def client(monkeypatch):
    from contextlib import asynccontextmanager

    from fastapi.testclient import TestClient

    import main
    from routers import embed as router

    monkeypatch.setenv("JWT_SECRET", SECRET)
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_REQUIRED_GET", "true")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    invalidate_user_status()
    em._cache.clear()
    em._tiles.clear()
    now = datetime.now(timezone.utc)
    stored = {"id": 5, "name": "Портал", "key_prefix": "tge_abcdef", "origins": ["https://akimat.kz"],
              "layers": ["pipes"], "fragments": None, "outages": False, "view": None, "created_by": "admin",
              "created_at": now, "expires_at": None, "revoked_at": None, "revoked_by": None, "last_used_at": None}
    audit = []

    class Conn(FakeConn):
        async def fetchrow(self, sql, *args):
            if sql.lstrip().startswith("SELECT id, name, origins"):
                return stored if args[0] == em.hash_key("tge_valid") else None
            return stored

    @asynccontextmanager
    async def acquire():
        yield Conn()

    async def extent():
        return [71.0, 51.0, 72.0, 52.0]

    async def write(**kwargs):
        audit.append(kwargs["action"])

    monkeypatch.setattr(router, "acquire_conn", acquire)
    monkeypatch.setattr(router, "_network_extent", extent)
    monkeypatch.setattr(router.activity, "write", write)
    c = TestClient(main.app)
    c.audit = audit
    yield c
    invalidate_user_status()


def test_keys_admin_only_and_public_tiles(client):
    admin = {"Authorization": f"Bearer {create_access_token(username='boss', role='admin', subject='1')}"}
    viewer = {"Authorization": f"Bearer {create_access_token(username='ivan', role='viewer', subject='2')}"}
    body = {"name": "Портал", "origins": ["https://akimat.kz"], "layers": ["pipes"]}
    assert client.post("/api/v1/embed/keys", json=body, headers=viewer).status_code == 403
    created = client.post("/api/v1/embed/keys", json=body, headers=admin).json()
    assert created["key"].startswith("tge_") and created["active"] and "EMBED_KEY_CREATE" in client.audit
    assert client.delete("/api/v1/embed/keys/5", headers=admin).status_code == 200

    # без входа, но только с ключом
    assert client.get("/api/v1/embed/config").status_code == 403
    assert client.get("/api/v1/embed/config", params={"key": "tge_other"}).status_code == 403
    cfg = client.get("/api/v1/embed/config", params={"key": "tge_valid"})
    assert cfg.status_code == 200 and cfg.json()["layers"][0]["id"] == "pipes"
    tile = client.get("/api/v1/embed/tiles/pipes/16/44000/22000", params={"key": "tge_valid"})
    assert tile.status_code == 200 and tile.headers["content-type"] == em_mvt() and "max-age" in tile.headers["cache-control"]
    assert client.get("/api/v1/embed/tiles/nodes/16/1/1", params={"key": "tge_valid"}).status_code == 403
    assert client.get("/api/v1/embed/tiles/pipes/5/1/1", params={"key": "tge_valid"}).status_code == 204
    assert client.get("/api/v1/embed/keys").status_code == 401  # список ключей — не открыт


def em_mvt() -> str:
    from routers.embed import MVT

    return MVT
