"""Встраиваемые карты (фаза 2, п. 14): ключи встраивания и векторные тайлы слоёв сети для карты в iframe.

Карта ТГИД на портале акимата, ЕДДС или в кабинете потребителя открывается без входа — по ключу встраивания.
Ключ публичный по природе (он виден в коде страницы сайта), поэтому даёт только чтение выбранных слоёв:
- origins — сайты, которым веб разрешает показывать карту в iframe (frame-ancestors) и слать события;
- layers и fragments — какие слои и фрагменты видны; поля слоёв — без имён потребителей (ПДн);
- отзыв или срок действия закрывают ключ (кеш проверки — KEY_TTL_S).

Тайлы — те же запросы, что у OGC API Features и FeatureServer (database/ogc_features.py), в MVT
(ST_AsMVT, id объекта — id признака тайла). Мелкие участки на обзорных зумах не показываются.
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator

from cities import cache_key
from database.arcgis_features import _base_sql
from database.net_srid import line_inner_sql, net_srid
from database.ogc_features import COLLECTIONS

KEY_PREFIX = "tge_"
KEY_TTL_S = 60
TOUCH_EVERY_S = 600
MAX_ORIGINS = 20
MAX_FRAGMENTS = 200
MAX_ZOOM = 22

# Слои встраиваемой карты: поля тайла (без ПДн) и зум, с которого слой виден. Порядок — отрисовки снизу вверх:
# потребитель и источник стоят в точке узла и должны быть поверх него
LAYERS: dict[str, dict[str, Any]] = {
    "pipes": {"fields": ("name", "sign", "diameter_mm", "length_m", "state_supply", "state_return"), "minzoom": 10},
    "nodes": {"fields": ("name", "node_type"), "minzoom": 15},
    "valves": {"fields": ("name", "diameter_mm", "state"), "minzoom": 15},
    "consumers": {"fields": ("kind", "load_gcal_h"), "minzoom": 14},
    "heat_sources": {"fields": ("name",), "minzoom": 9},
}
# Обзорные зумы — без мелочи: тайл z10 Астаны — вся сеть (все участки — 3 с и 1,4 МБ). Ниже зума — от Ду
PIPES_OVERVIEW_DU: tuple[tuple[int, int], ...] = ((12, 500), (13, 300))
# Тайлы обзорных зумов (их на город — десятки, а строятся они дольше всех) держатся в памяти
CACHE_BELOW_ZOOM = 13
CACHE_TTL_S = 600
CACHE_MAX_TILES = 256

_ORIGIN = re.compile(r"^https?://[a-z0-9]([a-z0-9.-]*[a-z0-9])?(:\d{1,5})?$")


class EmbedError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def normalize_origin(raw: str) -> str:
    """«https://Akimat.kz/portal/» → «https://akimat.kz»: схема, хост и порт, как в заголовке Origin."""
    text = (raw or "").strip()
    parts = urlsplit(text)
    if parts.scheme not in ("http", "https") or not parts.netloc or "@" in parts.netloc:
        raise ValueError(f"Адрес сайта — http(s)://хост: «{text}»")
    origin = f"{parts.scheme}://{parts.netloc.lower()}"
    if not _ORIGIN.match(origin):
        raise ValueError(f"Адрес сайта — http(s)://хост[:порт]: «{text}»")
    return origin


class ViewIn(BaseModel):
    center: tuple[float, float]
    zoom: float = Field(ge=0, le=MAX_ZOOM)

    @field_validator("center")
    @classmethod
    def _lon_lat(cls, v: tuple[float, float]) -> tuple[float, float]:
        if not (-180 <= v[0] <= 180 and -90 <= v[1] <= 90):
            raise ValueError("центр — [долгота, широта]")
        return v


class KeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    origins: list[str] = Field(min_length=1, max_length=MAX_ORIGINS)
    layers: list[str] = Field(min_length=1)
    fragments: Optional[list[int]] = Field(default=None, max_length=MAX_FRAGMENTS)
    outages: bool = False
    view: Optional[ViewIn] = None
    days: Optional[int] = Field(default=None, ge=1, le=3650)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("название ключа пустое")
        return v

    @field_validator("origins")
    @classmethod
    def _origins(cls, v: list[str]) -> list[str]:
        return sorted({normalize_origin(o) for o in v})

    @field_validator("layers")
    @classmethod
    def _layers(cls, v: list[str]) -> list[str]:
        unknown = [x for x in v if x not in LAYERS]
        if unknown:
            raise ValueError(f"неизвестные слои: {', '.join(unknown)}")
        return [x for x in LAYERS if x in v]

    @field_validator("fragments")
    @classmethod
    def _fragments(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return None
        if any(f < 1 for f in v):
            raise ValueError("номер фрагмента — положительное число")
        return sorted(set(v)) or None


@dataclass(frozen=True)
class EmbedKey:
    id: int
    name: str
    origins: tuple[str, ...]
    layers: tuple[str, ...]
    fragments: Optional[tuple[int, ...]]
    outages: bool
    view: Optional[dict[str, Any]]


def hash_key(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(24)


# --- ключи (администратор) ------------------------------------------------------------------

_LIST_COLUMNS = ("id, name, key_prefix, origins, layers, fragments, outages, view, created_by, created_at,"
                 " expires_at, revoked_at, revoked_by, last_used_at")


def _row(r) -> dict[str, Any]:
    out = dict(r)
    for k in ("created_at", "expires_at", "revoked_at", "last_used_at"):
        out[k] = out[k].isoformat() if out[k] else None
    out["active"] = out["revoked_at"] is None and (r["expires_at"] is None or r["expires_at"] > datetime.now(timezone.utc))
    return out


async def list_keys(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(f"SELECT {_LIST_COLUMNS} FROM tgid_embed_key ORDER BY revoked_at IS NOT NULL, id DESC")
    return [_row(r) for r in rows]


async def create_key(conn, body: KeyIn, username: str) -> dict[str, Any]:
    """Новый ключ: сам ключ возвращается один раз (в базе — только хеш)."""
    token = new_token()
    expires = datetime.now(timezone.utc) + timedelta(days=body.days) if body.days else None
    view = body.view.model_dump(mode="json") if body.view else None
    row = await conn.fetchrow(
        f"""INSERT INTO tgid_embed_key (name, key_hash, key_prefix, origins, layers, fragments, outages, view,
                                       created_by, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9, $10) RETURNING {_LIST_COLUMNS}""",
        body.name, hash_key(token), token[:len(KEY_PREFIX) + 6], body.origins, body.layers, body.fragments,
        body.outages, _json(view), username, expires)
    return {**_row(row), "key": token}


async def revoke_key(conn, key_id: int, username: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        f"""UPDATE tgid_embed_key SET revoked_at = COALESCE(revoked_at, now()), revoked_by = COALESCE(revoked_by, $2)
             WHERE id = $1 RETURNING {_LIST_COLUMNS}""", key_id, username)
    if row is None:
        raise EmbedError(404, "Ключ встраивания не найден")
    _cache.clear()
    return _row(row)


def _json(value: Any) -> Optional[str]:
    return None if value is None else json.dumps(value)


# --- проверка ключа (без входа) -------------------------------------------------------------

_cache: dict[tuple[str, str], tuple[float, Optional[EmbedKey]]] = {}
_touched: dict[tuple[str, int], float] = {}


async def resolve(conn, token: Optional[str]) -> EmbedKey:
    """Ключ из адреса страницы или тайла → его ограничения; 403 — нет, отозван или истёк."""
    if not token or not token.startswith(KEY_PREFIX) or len(token) > 100:
        raise EmbedError(403, "Нужен ключ встраивания (параметр key)")
    cache = (cache_key(), hash_key(token))
    hit = _cache.get(cache)
    if hit and time.monotonic() - hit[0] < KEY_TTL_S:
        key = hit[1]
    else:
        r = await conn.fetchrow(
            """SELECT id, name, origins, layers, fragments, outages, view FROM tgid_embed_key
                WHERE key_hash = $1 AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())""", cache[1])
        key = None if r is None else EmbedKey(
            r["id"], r["name"], tuple(r["origins"]), tuple(r["layers"]),
            tuple(r["fragments"]) if r["fragments"] else None, r["outages"], _view(r["view"]))
        _cache[cache] = (time.monotonic(), key)
    if key is None:
        raise EmbedError(403, "Ключ встраивания не принят: отозван, истёк или из другого города")
    return key


def _view(raw: Any) -> Optional[dict[str, Any]]:
    if raw is None:
        return None
    return json.loads(raw) if isinstance(raw, str) else dict(raw)


async def touch(conn, key: EmbedKey) -> None:
    """Когда ключ последний раз использовали (не чаще раза в TOUCH_EVERY_S — запись на каждый тайл не нужна)."""
    mark = (cache_key(), key.id)
    now = time.monotonic()
    if now - _touched.get(mark, -TOUCH_EVERY_S) < TOUCH_EVERY_S:
        return
    _touched[mark] = now
    await conn.execute("UPDATE tgid_embed_key SET last_used_at = now() WHERE id = $1", key.id)


def public_config(key: EmbedKey, *, extent: list[float], city: str, outages_enabled: bool) -> dict[str, Any]:
    """Что нужно странице /embed: слои с зумами, вид, сайты для postMessage. Без хешей и автора."""
    return {
        "name": key.name,
        "city_label": city,
        "origins": list(key.origins),
        "layers": [{"id": cid, "title": COLLECTIONS[cid].title, "geometry": COLLECTIONS[cid].geometry,
                    "minzoom": LAYERS[cid]["minzoom"], "fields": list(LAYERS[cid]["fields"])} for cid in key.layers],
        "fragments": list(key.fragments) if key.fragments else None,
        "outages": key.outages and outages_enabled,
        "view": key.view,
        "extent": extent,
    }


# --- тайлы ----------------------------------------------------------------------------------

def tile_sql(cid: str, z: int) -> str:
    """MVT слоя: $1–$3 — z, x, y; $4 — фрагменты (NULL — все). Поля — только из LAYERS (без ПДн)."""
    source, key, geom, frag = _base_sql(cid)
    fields = LAYERS[cid]["fields"]
    props = ", ".join(f"{expr} AS {name}" for name, expr in COLLECTIONS[cid].props if name in fields)
    # отбор по индексу shape: середина участка задвижки (выражение) индекс не использует
    bbox = "lo.shape" if cid == "valves" else geom
    extra = ""
    if cid == "pipes":
        # линии внутренних схем узлов (камер, ЦТП) — не на местности
        extra = f" AND {line_inner_sql('lo')} IS NULL"
        du = next((d for below, d in PIPES_OVERVIEW_DU if z < below), None)
        extra += f" AND h.diametercondit >= {du}" if du else ""
    return (
        f"SELECT ST_AsMVT(t, '{cid}', 4096, 'geom', 'id') FROM ("
        f"SELECT {key} AS id, {props}, "
        f"ST_AsMVTGeom(ST_Transform({geom}, 3857), ST_TileEnvelope($1, $2, $3), 4096, 64, true) AS geom "
        f"FROM {source} AND {bbox} && ST_Transform(ST_TileEnvelope($1, $2, $3), {net_srid()}) "
        f"AND ($4::int[] IS NULL OR {frag} = ANY($4::int[])){extra}) t WHERE t.geom IS NOT NULL")


def check_tile(key: EmbedKey, cid: str, z: int, x: int, y: int) -> None:
    if cid not in key.layers:
        raise EmbedError(403, f"Слой {cid} этому ключу встраивания не открыт")
    n = 1 << z
    if not (0 <= x < n and 0 <= y < n):
        raise EmbedError(404, "Тайл вне сетки")


async def tile(conn, key: EmbedKey, cid: str, z: int, x: int, y: int) -> bytes:
    """Тайл слоя; ниже зума слоя — пусто (b"")."""
    check_tile(key, cid, z, x, y)
    if z < LAYERS[cid]["minzoom"]:
        return b""
    fragments = list(key.fragments) if key.fragments else None
    mark = (cache_key(), cid, z, x, y, key.fragments)
    if z < CACHE_BELOW_ZOOM:
        hit = _tiles.get(mark)
        if hit and time.monotonic() - hit[0] < CACHE_TTL_S:
            return hit[1]
    data = bytes(await conn.fetchval(tile_sql(cid, z), z, x, y, fragments) or b"")
    if z < CACHE_BELOW_ZOOM:
        _tiles[mark] = (time.monotonic(), data)
        _tiles.move_to_end(mark)
        while len(_tiles) > CACHE_MAX_TILES:
            _tiles.popitem(last=False)
    return data


_tiles: OrderedDict[tuple, tuple[float, bytes]] = OrderedDict()
