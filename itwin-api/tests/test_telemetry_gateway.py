"""Шлюз OPC UA → ТГИД и имитатор SCADA (scripts/telemetry): правила без сервера OPC UA (asyncua не нужен)."""

import importlib.util
import json
import random
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "telemetry"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass ищет свой модуль в sys.modules
    spec.loader.exec_module(module)
    return module


gw = _load("opcua_gateway")
em = _load("scada_emulator")


def test_to_readings_skips_bad_quality_and_uses_source_time():
    now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    src = datetime(2026, 10, 30, 11, 59, 30)  # OPC UA — UTC без пояса
    out = gw.to_readings([("P1", 10.2, True, src), ("P2", 5.1, False, src), ("T1", None, True, src),
                          ("G1", 15000, True, None)], now)
    assert out == [{"sensor": "P1", "ts": "2026-10-30T11:59:30+00:00", "value": 10.2},
                   {"sensor": "G1", "ts": "2026-10-30T12:00:00+00:00", "value": 15000.0}]


@pytest.fixture
def cfg(tmp_path):
    return {"tgid": {"url": "http://tgid/api/v2/telemetry/readings"}, "buffer_dir": str(tmp_path / "buf")}


def test_deliver_buffers_when_tgid_down_and_flushes_in_order(cfg, monkeypatch):
    buffer = gw.Buffer(cfg["buffer_dir"])
    sent = []
    state = {"up": False}

    def post(url, key, readings):
        if not state["up"]:
            raise urllib.error.URLError("connection refused")
        sent.append([r["value"] for r in readings])
        return {"accepted": len(readings)}

    monkeypatch.setattr(gw, "post", post)
    gw.deliver(cfg, buffer, [{"sensor": "P1", "ts": "t1", "value": 1}], "key")
    gw.deliver(cfg, buffer, [{"sensor": "P1", "ts": "t2", "value": 2}], "key")
    assert len(buffer.pending()) == 2 and sent == []
    state["up"] = True
    gw.deliver(cfg, buffer, [{"sensor": "P1", "ts": "t3", "value": 3}], "key")
    assert sent == [[1], [2], [3]] and buffer.pending() == []


def test_deliver_drops_rejected_batch(cfg, monkeypatch):
    buffer = gw.Buffer(cfg["buffer_dir"])
    buffer.put([{"sensor": "P1", "ts": "t0", "value": 0}])

    def post(url, key, readings):
        raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(gw, "post", post)
    gw.deliver(cfg, buffer, [{"sensor": "P1", "ts": "t1", "value": 1}], "bad-key")
    # ключ неверен — повтор не поможет: пачки не копятся бесконечно
    assert buffer.pending() == []


def test_buffer_keeps_newest(cfg, monkeypatch):
    monkeypatch.setattr(gw, "MAX_BUFFER_FILES", 3)
    buffer = gw.Buffer(cfg["buffer_dir"])
    for i in range(5):
        buffer.put([{"sensor": "P1", "ts": f"t{i}", "value": i}])
    values = [json.loads(p.read_text(encoding="utf-8"))[0]["value"] for p in buffer.pending()]
    assert values == [2, 3, 4]


def test_load_config_requires_tags(tmp_path):
    path = tmp_path / "gw.json"
    path.write_text(json.dumps({"opcua": {"endpoint": "opc.tcp://x"}, "tgid": {"url": "u"}, "tags": {}}), encoding="utf-8")
    with pytest.raises(ValueError):
        gw.load_config(str(path))
    path.write_text(json.dumps({"opcua": {"endpoint": "opc.tcp://x"}, "tgid": {"url": "u"},
                                "tags": {"ns=2;s=A": "P1"}}), encoding="utf-8")
    cfg = gw.load_config(str(path))
    assert cfg["interval_s"] == 60 and cfg["buffer_dir"].endswith("gw-buffer")


def test_emulator_faults():
    now = datetime(2026, 10, 30, 12, 0, tzinfo=timezone.utc)
    rng = random.Random(1)
    drift = em.Tag("P", "p", "kgf_cm2", 10.0, faults=[em.Fault("drift", after_min=10, factor=0.88)])
    assert em.value_at(drift, now, 0, 5 * 60, rng) == (10.0, True)
    assert em.value_at(drift, now, 0, 11 * 60, rng) == (8.8, True)
    drop = em.Tag("Q", "q", "kgf_cm2", 5.0, faults=[em.Fault("dropout", after_min=3, every_min=20, for_min=5)])
    assert em.value_at(drop, now, 0, 2 * 60, rng)[1] is True
    assert em.value_at(drop, now, 0, 4 * 60, rng)[1] is False
    assert em.value_at(drop, now, 0, 9 * 60, rng)[1] is True
    assert em.value_at(drop, now, 0, 24 * 60, rng)[1] is False


def test_example_configs_are_consistent():
    emulator = em.load_config(str(SCRIPTS / "emulator.example.json"))
    gateway = gw.load_config(str(SCRIPTS / "gateway.example.json"))
    tag_ids = {f"ns=2;s={t.id}" for t in emulator["tags"]}
    assert set(gateway["tags"]) == tag_ids  # шлюз читает ровно теги имитатора
