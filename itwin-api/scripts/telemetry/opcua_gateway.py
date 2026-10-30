"""Шлюз телеметрии: теги сервера OPC UA (SCADA источника, ЦТП, вычислителя) → ТГИД /api/v2/telemetry/readings.

Раз в interval_s читает теги из настройки, берёт значения с хорошим качеством (плохое — датчик без связи — не
отправляется: в ТГИД он станет «молчит»), время — метка источника (SourceTimestamp), иначе время чтения. Пачка
уходит в ТГИД с ключом API (переменная окружения из api_key_env; ключ — «Учётная запись → Ключ API v2»
пользователя с правом «Журналы»). Нет связи с ТГИД — пачка ложится в buffer_dir и уходит при следующей удачной
отправке (до MAX_BUFFER_FILES пачек, старше — удаляются). Связь с OPC UA пропала — переподключение.

Запуск (Windows-служба — через NSSM, как службы API):
    pip install -r scripts/telemetry/requirements-telemetry.txt
    set TGID_API_KEY=<ключ>
    python scripts/telemetry/opcua_gateway.py scripts/telemetry/gateway.example.json

Шифрование OPC UA: "security": "Basic256Sha256,SignAndEncrypt,<сертификат шлюза>,<ключ шлюза>" (строка asyncua),
вход: "username" и пароль в переменной окружения из "password_env".
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("tgid-gateway")

MAX_BATCH = 10_000          # как в API (database/telemetry.py MAX_BATCH)
MAX_BUFFER_FILES = 2_000    # интервал 60 с — больше суток без связи
HTTP_TIMEOUT_S = 30
RECONNECT_S = 15


def load_config(path: str) -> dict[str, Any]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if not cfg.get("tags"):
        raise ValueError("В настройке нет тегов: tags = {\"ns=2;s=…\": \"код датчика в ТГИД\"}")
    cfg.setdefault("interval_s", 60)
    cfg.setdefault("buffer_dir", str(Path(path).with_suffix("")) + "-buffer")
    return cfg


def to_readings(values: list[tuple[str, Optional[float], bool, Optional[datetime]]], now: datetime) -> list[dict[str, Any]]:
    """(код датчика, значение, качество хорошее, время источника) → показания для ТГИД; плохие и пустые — мимо."""
    out = []
    for code, value, good, ts in values:
        if not good or value is None:
            continue
        stamp = ts if ts is not None else now
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)  # OPC UA отдаёт время в UTC
        out.append({"sensor": code, "ts": stamp.isoformat(timespec="seconds"), "value": float(value)})
    return out


class Buffer:
    """Пачки, не ушедшие в ТГИД: файл на пачку, отправка — от старых к новым."""

    def __init__(self, directory: str):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._seq = 0

    def put(self, readings: list[dict[str, Any]]) -> None:
        # счётчик в имени: time_ns на Windows шагает грубо, две пачки подряд иначе получат одно имя
        self._seq += 1
        name = f"{time.time_ns():020d}-{self._seq:06d}.json"
        (self.dir / name).write_text(json.dumps(readings, ensure_ascii=False), encoding="utf-8")
        files = sorted(self.dir.glob("*.json"))
        for old in files[:-MAX_BUFFER_FILES]:
            log.warning("Буфер полон — удалена старая пачка %s", old.name)
            old.unlink(missing_ok=True)

    def pending(self) -> list[Path]:
        return sorted(self.dir.glob("*.json"))


def post(url: str, api_key: str, readings: list[dict[str, Any]]) -> dict[str, Any]:
    body = json.dumps({"readings": readings}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "User-Agent": "TGID-OPCUA-Gateway/1"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:  # noqa: S310 — адрес из настройки службы
        return json.loads(resp.read() or b"{}")


def deliver(cfg: dict[str, Any], buffer: Buffer, readings: list[dict[str, Any]], api_key: str) -> None:
    """Сначала накопленное, затем новое; ошибка — новое в буфер, остальное ждёт следующего раза.

    4xx (кроме 408/429) — пачку не повторять: ключ или данные неверны, повтор не поможет (пишется в лог).
    """
    url = cfg["tgid"]["url"]
    for path in buffer.pending():
        try:
            out = post(url, api_key, json.loads(path.read_text(encoding="utf-8")))
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code not in (408, 429):
                log.error("ТГИД отказал пачке %s: %s %s — пачка удалена", path.name, exc.code, exc.read()[:300])
                path.unlink(missing_ok=True)
                continue
            log.warning("ТГИД недоступен (%s) — %s пачек ждут", exc.code, len(buffer.pending()))
            break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning("ТГИД недоступен (%s) — %s пачек ждут", exc, len(buffer.pending()))
            break
        log.info("Из буфера: %s", out)
        path.unlink(missing_ok=True)
    if not readings:
        return
    if buffer.pending():
        buffer.put(readings)  # очередь не разобрана — новое за ней, порядок сохраняется
        return
    for i in range(0, len(readings), MAX_BATCH):
        part = readings[i:i + MAX_BATCH]
        try:
            out = post(url, api_key, part)
            log.info("Отправлено: %s", out)
            if out.get("unknown_codes"):
                log.warning("В ТГИД нет датчиков с кодами: %s", ", ".join(out["unknown_codes"]))
        except urllib.error.HTTPError as exc:
            if 400 <= exc.code < 500 and exc.code not in (408, 429):
                log.error("ТГИД отказал: %s %s", exc.code, exc.read()[:300])
                continue
            buffer.put(part)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            log.warning("ТГИД недоступен (%s) — пачка в буфер", exc)
            buffer.put(part)


async def run(cfg: dict[str, Any]) -> None:
    from asyncua import Client, ua

    api_key = os.getenv(cfg["tgid"].get("api_key_env", "TGID_API_KEY"), "")
    if not api_key:
        log.warning("Ключ API не задан (переменная %s) — ТГИД с включённым входом ответит 401",
                    cfg["tgid"].get("api_key_env", "TGID_API_KEY"))
    buffer = Buffer(cfg["buffer_dir"])
    opc = cfg["opcua"]
    codes = cfg["tags"]
    while True:
        client = Client(url=opc["endpoint"], timeout=10)
        if opc.get("security"):
            await client.set_security_string(opc["security"])
        if opc.get("username"):
            client.set_user(opc["username"])
            client.set_password(os.getenv(opc.get("password_env", "OPCUA_PASSWORD"), ""))
        try:
            async with client:
                nodes = [client.get_node(node_id) for node_id in codes]
                log.info("OPC UA %s: тегов %s, отправка раз в %s с", opc["endpoint"], len(nodes), cfg["interval_s"])
                while True:
                    started = time.monotonic()
                    data = await client.read_attributes(nodes, ua.AttributeIds.Value)
                    values = []
                    for code, dv in zip(codes.values(), data):
                        value = dv.Value.Value if dv.Value is not None else None
                        values.append((code, value if isinstance(value, (int, float)) else None,
                                       dv.StatusCode.is_good(), dv.SourceTimestamp))
                    readings = to_readings(values, datetime.now(timezone.utc))
                    await asyncio.to_thread(deliver, cfg, buffer, readings, api_key)
                    await asyncio.sleep(max(1.0, cfg["interval_s"] - (time.monotonic() - started)))
        except (OSError, asyncio.TimeoutError, ua.UaError) as exc:
            log.warning("OPC UA недоступен (%s) — переподключение через %s с", exc, RECONNECT_S)
            await asyncio.sleep(RECONNECT_S)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    if len(sys.argv) != 2:
        sys.exit("python opcua_gateway.py <gateway.json>")
    asyncio.run(run(load_config(sys.argv[1])))


if __name__ == "__main__":
    main()
