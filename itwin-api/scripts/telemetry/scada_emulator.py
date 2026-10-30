"""Имитатор SCADA: сервер OPC UA с тегами давления, температуры и расхода тепловой сети.

Для стенда и демонстраций, пока нет доступа к настоящей SCADA: шлюз (opcua_gateway.py) читает эти теги так же,
как читал бы теги настоящего сервера OPC UA источника или ЦТП. Значение тега = base × (1 + суточный ход) + шум;
сбои по расписанию:
- drift   — с минуты after_min значение умножается на factor (засор, неисправный регулятор, утечка);
- dropout — каждые every_min минут на for_min минут тег отдаёт плохое качество (BadCommunicationError):
            связь с датчиком пропала, шлюз такие значения не отправляет.

Запуск (нужен asyncua: pip install -r scripts/telemetry/requirements-telemetry.txt):
    python scripts/telemetry/scada_emulator.py scripts/telemetry/emulator.example.json
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("scada-emulator")


@dataclass
class Fault:
    kind: str  # drift | dropout
    after_min: float = 0.0
    factor: float = 1.0
    every_min: float = 0.0
    for_min: float = 0.0


@dataclass
class Tag:
    id: str
    name: str
    unit: str
    base: float
    daily: float = 0.0   # амплитуда суточного хода, доля base (0.02 — ±2 %)
    noise: float = 0.0   # шум, доля base (СКО)
    faults: list[Fault] = field(default_factory=list)


def load_config(path: str) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    tags = []
    for t in raw["tags"]:
        fields = {k: v for k, v in t.items() if not k.startswith("_") and k != "faults"}  # «_…» — пояснения
        tags.append(Tag(**fields, faults=[Fault(**f) for f in t.get("faults", [])]))
    raw["tags"] = tags
    return raw


def value_at(tag: Tag, now: datetime, started: float, mono: float, rng: random.Random) -> tuple[float, bool]:
    """(значение, качество хорошее) тега в момент now; started/mono — monotonic-время запуска и сейчас."""
    minutes = (mono - started) / 60
    hour = now.astimezone().hour + now.astimezone().minute / 60
    value = tag.base * (1 + tag.daily * math.sin((hour - 6) / 24 * 2 * math.pi)) + rng.gauss(0, tag.noise * tag.base)
    good = True
    for f in tag.faults:
        if f.kind == "drift" and minutes >= f.after_min:
            value *= f.factor
        elif f.kind == "dropout" and f.every_min > 0 and minutes >= f.after_min:
            phase = (minutes - f.after_min) % f.every_min
            if phase < f.for_min:
                good = False
    return round(value, 4), good


async def serve(config: dict[str, Any]) -> None:
    from asyncua import Server, ua

    server = Server()
    await server.init()
    server.set_endpoint(config["endpoint"])
    server.set_server_name("ТГИД: имитатор SCADA")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    ns = await server.register_namespace(config.get("namespace", "urn:tgid:scada-emulator"))
    folder = await server.nodes.objects.add_folder(ua.NodeId("Network", ns), "Network")
    variables = {}
    for tag in config["tags"]:
        var = await folder.add_variable(ua.NodeId(tag.id, ns), tag.name, 0.0, ua.VariantType.Double)
        variables[tag.id] = var
    period = float(config.get("period_s", 5))
    rng = random.Random(config.get("seed", 7))
    started = time.monotonic()
    log.info("OPC UA: %s, namespace %s, тегов %s, обновление раз в %s с", config["endpoint"], ns, len(variables), period)
    async with server:
        while True:
            now = datetime.now(timezone.utc)
            for tag in config["tags"]:
                value, good = value_at(tag, now, started, time.monotonic(), rng)
                status = ua.StatusCode(ua.StatusCodes.Good if good else ua.StatusCodes.BadCommunicationError)
                await variables[tag.id].write_value(ua.DataValue(
                    ua.Variant(value, ua.VariantType.Double), StatusCode_=status, SourceTimestamp=now))
            await asyncio.sleep(period)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    logging.getLogger("asyncua").setLevel(logging.WARNING)
    if len(sys.argv) != 2:
        sys.exit("python scada_emulator.py <emulator.json>")
    asyncio.run(serve(load_config(sys.argv[1])))


if __name__ == "__main__":
    main()
