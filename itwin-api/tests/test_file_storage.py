"""Хранилище файлов (file_storage.py): Redis, каталог на диске, S3/MinIO — срок жизни, очистка, ключи."""
import io
from types import SimpleNamespace

import pytest

import file_storage
from database import file_jobs


class Clock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t


def test_local_roundtrip_expiry_and_sweep(tmp_path, monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_SWEEP_S", "0")
    clock = Clock()
    st = file_storage.LocalStorage(tmp_path / "files", clock=clock)
    st.put("job-1:data", b"PK\x03\x04", ttl_seconds=60)
    assert st.get("job-1:data") == b"PK\x03\x04"
    assert not list((tmp_path / "files").glob("*.part"))  # запись атомарная
    clock.t += 61
    assert st.get("job-1:data") is None  # просрочено — не отдаётся
    st.put("job-2:data", b"x", ttl_seconds=60)  # очистка при записи
    names = sorted(p.name for p in (tmp_path / "files").iterdir())
    assert names == ["job-2=data", "job-2=data.expires"]


@pytest.mark.parametrize("key", ["../etc/passwd", "a/b", "", ".hidden", "x" * 300])
def test_keys_cannot_escape_storage(tmp_path, key):
    st = file_storage.LocalStorage(tmp_path)
    with pytest.raises(file_storage.StorageError):
        st.put(key, b"x", 60)


class FakeMinio:
    def __init__(self):
        self.objects: dict[str, tuple[bytes, dict]] = {}
        self.buckets: set[str] = set()

    def bucket_exists(self, b):
        return b in self.buckets

    def make_bucket(self, b):
        self.buckets.add(b)

    def put_object(self, bucket, name, data, length, metadata):
        self.objects[name] = (data.read(length), {f"x-amz-meta-{k}": v for k, v in metadata.items()})

    def stat_object(self, bucket, name):
        if name not in self.objects:
            raise KeyError(name)
        return SimpleNamespace(metadata=self.objects[name][1])

    def get_object(self, bucket, name):
        body = io.BytesIO(self.objects[name][0])
        body.release_conn = lambda: None
        return body

    def remove_object(self, bucket, name):
        self.objects.pop(name, None)

    def list_objects(self, bucket):
        return [SimpleNamespace(object_name=n) for n in list(self.objects)]


def test_s3_roundtrip_expiry_and_sweep(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE_SWEEP_S", "0")
    clock = Clock()
    client = FakeMinio()
    st = file_storage.S3Storage(client, "tgid-files", clock=clock)
    assert "tgid-files" in client.buckets
    st.put("job-1:data", b"abc", ttl_seconds=60)
    assert st.get("job-1:data") == b"abc"
    assert st.get("missing") is None
    clock.t += 61
    assert st.get("job-1:data") is None
    st.put("job-2:data", b"z", ttl_seconds=60)
    assert set(client.objects) == {"job-2=data"}


def test_from_env_reports_missing_settings(monkeypatch):
    monkeypatch.setenv("FILE_STORAGE", "local")
    monkeypatch.delenv("FILE_STORAGE_DIR", raising=False)
    with pytest.raises(file_storage.StorageError, match="FILE_STORAGE_DIR"):
        file_storage.from_env(lambda: None)
    monkeypatch.setenv("FILE_STORAGE", "ftp")
    with pytest.raises(file_storage.StorageError, match="redis, local или s3"):
        file_storage.from_env(lambda: None)


class MetaOnlyRedis:
    """Redis, где лежит только описание: данные в режиме local туда попадать не должны."""

    def __init__(self):
        self.data = {}

    def set(self, key, value, ex=None):
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


def test_file_jobs_keep_bytes_out_of_redis_in_local_mode(tmp_path, monkeypatch):
    fake = MetaOnlyRedis()
    monkeypatch.setattr(file_jobs, "_client", fake)
    monkeypatch.setattr(file_jobs, "_storage_cache", {})
    monkeypatch.setenv("FILE_STORAGE", "local")
    monkeypatch.setenv("FILE_STORAGE_DIR", str(tmp_path / "jobs"))
    big = b"x" * 2_000_000
    file_jobs.store_result("job-9", file_jobs.FileResult(big, "network.dxf"), owner="u1", kind="network_dxf")
    assert list(fake.data) == ["tgid:filejob:job-9:meta"]  # в Redis — только описание
    meta, data = file_jobs.load_result("job-9")
    assert data == big and meta["size"] == len(big)
