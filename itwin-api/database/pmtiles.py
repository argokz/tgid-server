"""Архив PMTiles v3: запись и чтение тайлов одним файлом (https://github.com/protomaps/PMTiles, spec v3).

Свой код вместо пакета pmtiles: формат простой (заголовок 127 байт, каталоги varint, тайлы подряд), а новая
зависимость в API не нужна. Писатель — для запекания статичных слоёв (database/static_tiles.py), читатель —
для отдачи тайлов z/x/y из архива. Каталоги и метаданные сжаты gzip; тайлы — как их передали (static_tiles
кладёт MVT в gzip, тип и сжатие — в заголовке).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import struct
import tempfile
from bisect import bisect_right
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Optional

MAGIC = b"PMTiles"
VERSION = 3
HEADER_LEN = 127
# корневой каталог вместе с заголовком — в первых 16 КБ (читатель берёт их одним запросом)
ROOT_MAX = 16384 - HEADER_LEN
MAX_ZOOM = 26

COMPRESSION_NONE = 1
COMPRESSION_GZIP = 2
TILE_TYPE_MVT = 1

_HEADER = struct.Struct("<7sB QQ QQ QQ QQ QQQ BBBB BB iiii B ii")


class PMTilesError(Exception):
    pass


# --- номер тайла: кривая Гильберта внутри уровня -------------------------------------------------

def zxy_to_tileid(z: int, x: int, y: int) -> int:
    if not 0 <= z <= MAX_ZOOM:
        raise PMTilesError(f"Уровень {z} вне 0…{MAX_ZOOM}")
    n = 1 << z
    if not (0 <= x < n and 0 <= y < n):
        raise PMTilesError(f"Тайл {z}/{x}/{y} вне сетки уровня")
    acc = ((1 << (2 * z)) - 1) // 3  # тайлов на уровнях ниже z
    d = 0
    s = n >> 1
    while s > 0:
        rx = 1 if x & s else 0
        ry = 1 if y & s else 0
        d += s * s * ((3 * rx) ^ ry)
        if ry == 0:
            if rx == 1:
                # старшие биты дальше не читаются: важны только младшие, а у s - 1 - x они инвертированы
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        s >>= 1
    return acc + d


def tileid_to_zxy(tile_id: int) -> tuple[int, int, int]:
    acc = 0
    for z in range(MAX_ZOOM + 1):
        count = 1 << (2 * z)
        if tile_id < acc + count:
            return (z, *_d_to_xy(z, tile_id - acc))
        acc += count
    raise PMTilesError(f"Номер тайла {tile_id} слишком велик")


def _d_to_xy(z: int, d: int) -> tuple[int, int]:
    n = 1 << z
    x = y = 0
    s = 1
    t = d
    while s < n:
        rx = 1 & (t // 2)
        ry = 1 & (t ^ rx)
        if ry == 0:
            if rx == 1:
                x = s - 1 - x
                y = s - 1 - y
            x, y = y, x
        x += s * rx
        y += s * ry
        t //= 4
        s *= 2
    return x, y


# --- каталоги ----------------------------------------------------------------------------------

@dataclass(frozen=True)
class Entry:
    tile_id: int
    offset: int
    length: int
    # 0 — ссылка на листовой каталог (offset/length — в разделе листьев); иначе — тайлов подряд с этим содержимым
    run_length: int


def _write_varint(out: bytearray, value: int) -> None:
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)


def _read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        if pos >= len(buf):
            raise PMTilesError("Каталог обрезан")
        b = buf[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if b < 0x80:
            return value, pos
        shift += 7
        if shift > 63:
            raise PMTilesError("Слишком длинное число в каталоге")


def serialize_directory(entries: list[Entry]) -> bytes:
    out = bytearray()
    _write_varint(out, len(entries))
    last = 0
    for e in entries:
        _write_varint(out, e.tile_id - last)
        last = e.tile_id
    for e in entries:
        _write_varint(out, e.run_length)
    for e in entries:
        _write_varint(out, e.length)
    for i, e in enumerate(entries):
        prev = entries[i - 1] if i else None
        if prev is not None and e.offset == prev.offset + prev.length:
            _write_varint(out, 0)
        else:
            _write_varint(out, e.offset + 1)
    return gzip.compress(bytes(out), mtime=0)


def deserialize_directory(data: bytes) -> list[Entry]:
    buf = gzip.decompress(data)
    n, pos = _read_varint(buf, 0)
    ids, runs, lengths = [0] * n, [0] * n, [0] * n
    last = 0
    for i in range(n):
        delta, pos = _read_varint(buf, pos)
        last += delta
        ids[i] = last
    for i in range(n):
        runs[i], pos = _read_varint(buf, pos)
    for i in range(n):
        lengths[i], pos = _read_varint(buf, pos)
    entries: list[Entry] = []
    for i in range(n):
        raw, pos = _read_varint(buf, pos)
        if raw == 0 and i > 0:
            offset = entries[-1].offset + entries[-1].length
        else:
            offset = raw - 1
        entries.append(Entry(ids[i], offset, lengths[i], runs[i]))
    return entries


def _build_directories(entries: list[Entry]) -> tuple[bytes, bytes]:
    """Корневой каталог и листья: корень обязан уместиться в ROOT_MAX — иначе записи уходят в листья."""
    root = serialize_directory(entries)
    if len(root) <= ROOT_MAX:
        return root, b""
    leaf_size = 4096
    while True:
        leaves = bytearray()
        root_entries = []
        for i in range(0, len(entries), leaf_size):
            chunk = entries[i:i + leaf_size]
            data = serialize_directory(chunk)
            root_entries.append(Entry(chunk[0].tile_id, len(leaves), len(data), 0))
            leaves += data
        root = serialize_directory(root_entries)
        if len(root) <= ROOT_MAX:
            return root, bytes(leaves)
        leaf_size *= 2


# --- запись ------------------------------------------------------------------------------------

class Writer:
    """Тайлы складываются во временный файл по мере получения (одинаковые — один раз), finish() пишет архив.

    Порядок add_tile любой; повтор одного тайла — ошибка."""

    def __init__(self, path: Path, *, tile_type: int = TILE_TYPE_MVT, tile_compression: int = COMPRESSION_GZIP):
        self.path = Path(path)
        self.tile_type = tile_type
        self.tile_compression = tile_compression
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=self.path.stem + ".", suffix=".tiles", dir=self.path.parent)
        self._tiles_path = Path(tmp)
        self._tiles: BinaryIO = os.fdopen(fd, "wb")
        self._size = 0
        self._by_hash: dict[bytes, tuple[int, int]] = {}
        self._index: dict[int, tuple[int, int]] = {}
        self.zooms: set[int] = set()

    def add_tile(self, z: int, x: int, y: int, data: bytes) -> None:
        tile_id = zxy_to_tileid(z, x, y)
        if tile_id in self._index:
            raise PMTilesError(f"Тайл {z}/{x}/{y} уже записан")
        key = hashlib.sha256(data).digest()
        found = self._by_hash.get(key)
        if found is None:
            found = (self._size, len(data))
            self._tiles.write(data)
            self._size += len(data)
            self._by_hash[key] = found
        self._index[tile_id] = found
        self.zooms.add(z)

    @property
    def tile_count(self) -> int:
        return len(self._index)

    @property
    def contents_count(self) -> int:
        return len(self._by_hash)

    def abort(self) -> None:
        self._tiles.close()
        self._tiles_path.unlink(missing_ok=True)

    def finish(self, *, metadata: dict[str, Any], bounds: tuple[float, float, float, float],
               center: Optional[tuple[float, float, int]] = None) -> dict[str, Any]:
        """Записать архив (через временный файл и замену — читатели старого не видят полузаписанный)."""
        self._tiles.close()
        try:
            if not self._index:
                raise PMTilesError("Нет ни одного тайла — архив пуст")
            entries: list[Entry] = []
            for tile_id in sorted(self._index):
                offset, length = self._index[tile_id]
                last = entries[-1] if entries else None
                if last and last.offset == offset and last.length == length \
                        and last.tile_id + last.run_length == tile_id:
                    entries[-1] = Entry(last.tile_id, offset, length, last.run_length + 1)
                else:
                    entries.append(Entry(tile_id, offset, length, 1))
            root, leaves = _build_directories(entries)
            meta = gzip.compress(json.dumps(metadata, ensure_ascii=False).encode("utf-8"), mtime=0)
            min_zoom, max_zoom = min(self.zooms), max(self.zooms)
            w, s, e, n = bounds
            cx, cy, cz = center or ((w + e) / 2, (s + n) / 2, min_zoom)
            root_off = HEADER_LEN
            meta_off = root_off + len(root)
            leaves_off = meta_off + len(meta)
            data_off = leaves_off + len(leaves)
            header = _HEADER.pack(
                MAGIC, VERSION, root_off, len(root), meta_off, len(meta), leaves_off, len(leaves),
                data_off, self._size, len(self._index), len(entries), len(self._by_hash),
                0, COMPRESSION_GZIP, self.tile_compression, self.tile_type, min_zoom, max_zoom,
                _e7(w), _e7(s), _e7(e), _e7(n), int(cz), _e7(cx), _e7(cy))
            fd, tmp = tempfile.mkstemp(prefix=self.path.stem + ".", suffix=".part", dir=self.path.parent)
            try:
                with os.fdopen(fd, "wb") as out:
                    out.write(header)
                    out.write(root)
                    out.write(meta)
                    out.write(leaves)
                    with open(self._tiles_path, "rb") as tiles:
                        shutil.copyfileobj(tiles, out, 1024 * 1024)
                os.replace(tmp, self.path)
            except BaseException:
                Path(tmp).unlink(missing_ok=True)
                raise
            return {"tiles": len(self._index), "contents": len(self._by_hash), "entries": len(entries),
                    "size": self.path.stat().st_size, "min_zoom": min_zoom, "max_zoom": max_zoom}
        finally:
            self._tiles_path.unlink(missing_ok=True)


def _e7(v: float) -> int:
    return int(round(v * 10_000_000))


# --- чтение ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Header:
    root_offset: int
    root_length: int
    metadata_offset: int
    metadata_length: int
    leaf_offset: int
    leaf_length: int
    data_offset: int
    data_length: int
    addressed_tiles: int
    tile_entries: int
    tile_contents: int
    internal_compression: int
    tile_compression: int
    tile_type: int
    min_zoom: int
    max_zoom: int
    bounds: tuple[float, float, float, float]
    center: tuple[float, float, int]


def parse_header(raw: bytes) -> Header:
    if len(raw) < HEADER_LEN:
        raise PMTilesError("Файл короче заголовка PMTiles")
    f = _HEADER.unpack(raw[:HEADER_LEN])
    if f[0] != MAGIC:
        raise PMTilesError("Это не архив PMTiles")
    if f[1] != VERSION:
        raise PMTilesError(f"Версия PMTiles {f[1]} не поддерживается (нужна 3)")
    if f[14] != COMPRESSION_GZIP:
        raise PMTilesError("Каталоги архива сжаты не gzip — не поддерживается")
    return Header(f[2], f[3], f[4], f[5], f[6], f[7], f[8], f[9], f[10], f[11], f[12], f[14], f[15], f[16],
                  f[17], f[18], (f[19] / 1e7, f[20] / 1e7, f[21] / 1e7, f[22] / 1e7), (f[24] / 1e7, f[25] / 1e7, f[23]))


class Reader:
    """Чтение тайлов из файла архива; корневой каталог и прочитанные листья держатся в памяти."""

    def __init__(self, path: Path):
        self.path = Path(path)
        with open(self.path, "rb") as fh:
            self.header = parse_header(fh.read(HEADER_LEN))
            fh.seek(self.header.root_offset)
            self._root = deserialize_directory(fh.read(self.header.root_length))
            fh.seek(self.header.metadata_offset)
            raw_meta = fh.read(self.header.metadata_length)
        self.metadata: dict[str, Any] = json.loads(gzip.decompress(raw_meta)) if raw_meta else {}
        self._leaves: dict[int, list[Entry]] = {}

    def _leaf(self, fh: BinaryIO, entry: Entry) -> list[Entry]:
        cached = self._leaves.get(entry.offset)
        if cached is None:
            fh.seek(self.header.leaf_offset + entry.offset)
            cached = deserialize_directory(fh.read(entry.length))
            self._leaves[entry.offset] = cached
        return cached

    def get(self, z: int, x: int, y: int) -> Optional[bytes]:
        """Тайл как он лежит в архиве (сжатие — header.tile_compression); нет тайла — None."""
        if z < self.header.min_zoom or z > self.header.max_zoom:
            return None
        try:
            tile_id = zxy_to_tileid(z, x, y)
        except PMTilesError:
            return None
        entries = self._root
        with open(self.path, "rb") as fh:
            for _ in range(4):  # глубина каталогов в архивах — 1–2 уровня
                i = bisect_right(entries, tile_id, key=lambda e: e.tile_id) - 1
                if i < 0:
                    return None
                e = entries[i]
                if e.run_length == 0:
                    entries = self._leaf(fh, e)
                    continue
                if tile_id >= e.tile_id + e.run_length:
                    return None
                fh.seek(self.header.data_offset + e.offset)
                return fh.read(e.length)
        raise PMTilesError("Слишком глубокие каталоги архива")
