"""Хранилище файлов API (готовые выгрузки, позже — фото из поля, сканы, PMTiles): байты по ключу со сроком жизни.

FILE_STORAGE выбирает, где лежат данные:
  redis  — как раньше: в Redis воркера (по умолчанию; файлы занимают память Redis);
  local  — каталог FILE_STORAGE_DIR на диске, общий для API и воркера (на одном сервере);
  s3     — MinIO или любое S3-совместимое: FILE_S3_ENDPOINT (host:port), FILE_S3_BUCKET,
           FILE_S3_ACCESS_KEY, FILE_S3_SECRET_KEY, FILE_S3_SECURE (true/false), пакет minio.
Срок жизни: в redis — TTL ключа; в local и s3 просроченные файлы удаляются при следующих записях
(раз в FILE_STORAGE_SWEEP_S секунд, по умолчанию 300).
"""
from __future__ import annotations

import io
import os
import re
import time
from pathlib import Path
from typing import Optional, Protocol

from app_logging import get_logger

logger = get_logger(__name__)

_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,200}$")
_DEFAULT_SWEEP_S = 300


class StorageError(RuntimeError):
    pass


def _check_key(key: str) -> str:
    """Ключ — без путей и спецсимволов: из него строится имя файла и объекта."""
    if not _KEY_RE.match(key):
        raise StorageError(f"Недопустимый ключ хранилища: {key!r}")
    return key


class FileStorage(Protocol):
    def put(self, key: str, data: bytes, ttl_seconds: int) -> None: ...
    def get(self, key: str) -> Optional[bytes]: ...
    def delete(self, key: str) -> None: ...


def _sweep_interval() -> float:
    try:
        return max(0.0, float(os.getenv("FILE_STORAGE_SWEEP_S", _DEFAULT_SWEEP_S)))
    except ValueError:
        return float(_DEFAULT_SWEEP_S)


class RedisStorage:
    """Данные в Redis с TTL (прежнее поведение file_jobs)."""

    def __init__(self, client, prefix: str = "") -> None:
        self._client = client
        self._prefix = prefix

    def put(self, key: str, data: bytes, ttl_seconds: int) -> None:
        self._client.set(self._prefix + _check_key(key), data, ex=ttl_seconds)

    def get(self, key: str) -> Optional[bytes]:
        return self._client.get(self._prefix + _check_key(key))

    def delete(self, key: str) -> None:
        self._client.delete(self._prefix + _check_key(key))


class LocalStorage:
    """Каталог на диске: файл <ключ> и рядом <ключ>.expires со сроком (unix-время)."""

    def __init__(self, root: Path, clock=time.time) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._last_sweep = 0.0

    def _path(self, key: str) -> Path:
        # «:» в имени файла Windows запрещено; «=» в ключах не бывает — имена не совпадут
        return self.root / _check_key(key).replace(":", "=")

    def put(self, key: str, data: bytes, ttl_seconds: int) -> None:
        path = self._path(key)
        tmp = path.with_name(path.name + ".part")
        tmp.write_bytes(data)
        os.replace(tmp, path)  # читатель не увидит недописанный файл
        path.with_name(path.name + ".expires").write_text(str(self._clock() + ttl_seconds), encoding="ascii")
        self.sweep()

    def _expired(self, path: Path) -> bool:
        marker = path.with_name(path.name + ".expires")
        try:
            return float(marker.read_text(encoding="ascii")) <= self._clock()
        except (OSError, ValueError):
            return True  # без срока — считаем мусором

    def get(self, key: str) -> Optional[bytes]:
        path = self._path(key)
        if not path.exists() or self._expired(path):
            return None
        try:
            return path.read_bytes()
        except OSError:
            return None

    def delete(self, key: str) -> None:
        path = self._path(key)
        for p in (path, path.with_name(path.name + ".expires")):
            p.unlink(missing_ok=True)

    def sweep(self, force: bool = False) -> int:
        """Удалить просроченные файлы. → сколько удалено."""
        now = self._clock()
        if not force and now - self._last_sweep < _sweep_interval():
            return 0
        self._last_sweep = now
        removed = 0
        for path in self.root.iterdir():
            if path.suffix in (".expires", ".part") or not path.is_file():
                continue
            if self._expired(path):
                try:
                    self.delete(path.name.replace("=", ":"))
                    removed += 1
                except (OSError, StorageError) as e:
                    logger.warning("Хранилище файлов: не удалось удалить %s: %s", path.name, e)
        if removed:
            logger.info("Хранилище файлов: удалено просроченных %d", removed)
        return removed


class S3Storage:
    """S3-совместимое (SeaweedFS, MinIO, облако): объект <ключ с «=» вместо «:»>, срок — x-amz-meta-expires."""

    def __init__(self, client, bucket: str, clock=time.time) -> None:
        self._client = client
        self._bucket = bucket
        self._clock = clock
        self._last_sweep = 0.0
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    @staticmethod
    def _name(key: str) -> str:
        # SeaweedFS молча не сохраняет имена с «:»; «=» в ключах не бывает — имена не совпадут
        return _check_key(key).replace(":", "=")

    def put(self, key: str, data: bytes, ttl_seconds: int) -> None:
        self._client.put_object(
            self._bucket, self._name(key), io.BytesIO(data), length=len(data),
            metadata={"expires": str(self._clock() + ttl_seconds)},
        )
        self.sweep()

    def _expires(self, key: str) -> Optional[float]:
        try:
            stat = self._client.stat_object(self._bucket, key)
        except Exception:  # noqa: BLE001 — нет объекта
            return None
        meta = {k.lower(): v for k, v in (stat.metadata or {}).items()}
        try:
            return float(meta.get("x-amz-meta-expires", ""))
        except ValueError:
            return None

    def get(self, key: str) -> Optional[bytes]:
        name = self._name(key)
        expires = self._expires(name)
        if expires is None or expires <= self._clock():
            return None
        resp = self._client.get_object(self._bucket, name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, self._name(key))

    def sweep(self, force: bool = False) -> int:
        now = self._clock()
        if not force and now - self._last_sweep < _sweep_interval():
            return 0
        self._last_sweep = now
        removed = 0
        for obj in self._client.list_objects(self._bucket):
            expires = self._expires(obj.object_name)
            if expires is not None and expires <= now:
                self._client.remove_object(self._bucket, obj.object_name)
                removed += 1
        return removed


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def from_env(redis_client_factory) -> FileStorage:
    """Хранилище по FILE_STORAGE; redis_client_factory() — клиент Redis для режима redis."""
    kind = (os.getenv("FILE_STORAGE") or "redis").strip().lower()
    if kind == "redis":
        return RedisStorage(redis_client_factory())
    if kind == "local":
        root = (os.getenv("FILE_STORAGE_DIR") or "").strip()
        if not root:
            raise StorageError("FILE_STORAGE=local: задайте FILE_STORAGE_DIR — каталог, общий для API и воркера")
        return LocalStorage(Path(root))
    if kind == "s3":
        try:
            from minio import Minio
        except ImportError as e:
            raise StorageError("FILE_STORAGE=s3: нужен пакет minio (pip install -r requirements.txt)") from e
        endpoint = (os.getenv("FILE_S3_ENDPOINT") or "").strip()
        bucket = (os.getenv("FILE_S3_BUCKET") or "tgid-files").strip()
        if not endpoint:
            raise StorageError("FILE_STORAGE=s3: задайте FILE_S3_ENDPOINT (host:port)")
        client = Minio(
            endpoint,
            access_key=os.getenv("FILE_S3_ACCESS_KEY", ""),
            secret_key=os.getenv("FILE_S3_SECRET_KEY", ""),
            secure=_truthy(os.getenv("FILE_S3_SECURE", "false")),
        )
        return S3Storage(client, bucket)
    raise StorageError(f"FILE_STORAGE={kind!r}: допустимо redis, local или s3")
