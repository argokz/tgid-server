"""Вебхуки (фаза 2): подписки внешних систем на события ТГИД и доставка с подписью и повторами.

Подписка — адрес (https), типы событий (database/api_events.EVENT_TYPES) и секрет. Каждое новое событие
подходящего типа становится доставкой: POST JSON на адрес с заголовками по спецификации Standard Webhooks
(https://www.standardwebhooks.com): webhook-id, webhook-timestamp, webhook-signature = «v1,» + base64
HMAC-SHA256(секрет, «id.timestamp.тело»). Ответ 2xx — доставлено; иначе — повтор через RETRY_DELAYS_S
(8 попыток за сутки с небольшим), затем «не доставлено». Подписка, которая не принимает ничего FAIL_DISABLE_DAYS
дней, выключается.

Адрес подписки — запрос с сервера API наружу, поэтому:
- только https (http — если WEBHOOK_ALLOW_HTTP=1: 1С или ERP во внутренней сети без сертификата);
- адрес хоста проверяется при каждой доставке, запрос идёт на проверенный IP (подмена DNS между проверкой и
  запросом не проходит); перенаправления не выполняются;
- никогда — link-local (169.254.0.0/16, адреса метаданных облака), multicast, 0.0.0.0; внутренние сети и
  localhost — только при WEBHOOK_ALLOW_PRIVATE=1.

Фоновая задача (webhook_loop) на каждый город: собрать события (api_events.collect), разложить по подпискам,
отправить подошедшие доставки. Несколько процессов API не мешают друг другу: сбор — под advisory-замком,
доставки забираются FOR UPDATE SKIP LOCKED с «арендой» на время отправки.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import httpx
from pydantic import BaseModel, Field, field_validator

from database import api_events

logger = logging.getLogger(__name__)

SECRET_PREFIX = "whsec_"
RETRY_DELAYS_S: tuple[int, ...] = (60, 300, 1800, 7200, 18000, 36000, 36000)
MAX_ATTEMPTS = len(RETRY_DELAYS_S) + 1
FAIL_DISABLE_DAYS = 3
SEND_TIMEOUT_S = 10.0
SEND_DEADLINE_S = SEND_TIMEOUT_S + 5
LEASE_S = 60
BATCH = 20
MAX_HOOKS = 50
DEFAULT_POLL_S = 10
PRUNE_EVERY_S = 3600
USER_AGENT = "TGID-Webhooks/1"
# всегда закрыты, даже с WEBHOOK_ALLOW_PRIVATE: CGNAT (в нём адрес метаданных Alibaba Cloud 100.100.100.200)
_ALWAYS_BLOCKED = (ipaddress.ip_network("100.64.0.0/10"),)
_NAT64 = ipaddress.ip_network("64:ff9b::/96")
# ключ advisory-замка сбора событий (в своей базе города)
_COLLECT_LOCK = 0x7467_6964_7768  # «tgidwh»
_ALERT_LOCK = 0x7467_6964_616C  # «tgidal»
ALERT_EVERY_S = 60
# баланс расхода: граф сети города тяжелее, а ночной расход меняется раз в сутки (на стенде — чаще)
BALANCE_EVERY_S = max(60, int(os.getenv("TELEMETRY_BALANCE_EVERY_S", "900") or 900))
_last_balance: dict[str, float] = {}  # город → monotonic последней проверки баланса


class WebhookError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def poll_interval_s() -> float:
    try:
        return max(0.0, float(os.getenv("WEBHOOK_POLL_S", str(DEFAULT_POLL_S))))
    except ValueError:
        return float(DEFAULT_POLL_S)


# --- адрес подписки ----------------------------------------------------------------------------

def check_url(raw: str) -> str:
    """Проверить адрес подписки (схема, хост, без логина в адресе); IP-литерал — сразу по сетям."""
    url = (raw or "").strip()
    parts = urlsplit(url)
    allowed = ("https", "http") if _env_flag("WEBHOOK_ALLOW_HTTP") else ("https",)
    if parts.scheme not in allowed:
        raise ValueError("Адрес — https://… (http — только если служба включила WEBHOOK_ALLOW_HTTP)")
    if not parts.hostname or "@" in parts.netloc:
        raise ValueError("Адрес — https://хост/путь, без логина и пароля в адресе")
    if parts.fragment:
        raise ValueError("Адрес без #фрагмента")
    try:
        parts.port  # noqa: B018 — проверка порта: ValueError на «:99999»
    except ValueError as exc:
        raise ValueError("Неверный порт в адресе") from exc
    try:
        ip = ipaddress.ip_address(parts.hostname)
    except ValueError:
        return url
    reason = blocked_reason(ip)
    if reason:
        raise ValueError(reason)
    return url


def blocked_reason(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Optional[str]:
    """Почему на этот адрес нельзя слать; None — можно."""
    if isinstance(ip, ipaddress.IPv6Address):
        # IPv4 внутри IPv6 (::ffff:a.b.c.d, 6to4, NAT64) проверяется как IPv4
        embedded = ip.ipv4_mapped or ip.sixtofour or (
            ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF) if ip in _NAT64 else None)
        if embedded is not None:
            ip = embedded
    if ip.is_link_local or ip.is_multicast or ip.is_unspecified or any(ip in net for net in _ALWAYS_BLOCKED):
        return f"Адрес {ip} закрыт для вебхуков (служебная сеть)"
    # ::1 Python считает и зарезервированным — внутренние сети проверяются раньше
    if ip.is_private or ip.is_loopback:
        if _env_flag("WEBHOOK_ALLOW_PRIVATE"):
            return None
        return f"Адрес {ip} — внутренняя сеть: разрешает служба (WEBHOOK_ALLOW_PRIVATE=1)"
    if not ip.is_global:
        # зарезервированные, NAT64, 6to4 и прочие не публичные адреса
        return f"Адрес {ip} закрыт для вебхуков (служебная сеть)"
    return None


async def _resolve(host: str, port: int) -> str:
    """IP хоста для запроса: все адреса хоста должны быть разрешены (иначе подмена через второй адрес)."""
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise WebhookError(502, f"Хост {host} не найден") from exc
        addresses = [ipaddress.ip_address(info[4][0].split("%", 1)[0]) for info in infos]
        if not addresses:
            raise WebhookError(502, f"Хост {host} не найден")
    else:
        addresses = [ip]
    for addr in addresses:
        reason = blocked_reason(addr)
        if reason:
            raise WebhookError(403, reason)
    return str(addresses[0])


# --- подпись -----------------------------------------------------------------------------------

def new_secret() -> str:
    return SECRET_PREFIX + base64.b64encode(secrets.token_bytes(32)).decode()


def sign(secret: str, msg_id: str, timestamp: int, body: bytes) -> str:
    """Подпись Standard Webhooks: «v1,» + base64(HMAC-SHA256(ключ, «id.timestamp.тело»))."""
    key = base64.b64decode(secret.removeprefix(SECRET_PREFIX))
    digest = hmac.new(key, f"{msg_id}.{timestamp}.".encode() + body, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def body_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# --- подписки ----------------------------------------------------------------------------------

def _check_events(v: list[str]) -> list[str]:
    unknown = [x for x in v if x not in api_events.EVENT_TYPES]
    if unknown:
        raise ValueError(f"неизвестные события: {', '.join(unknown)}")
    return [x for x in api_events.EVENT_TYPES if x in v]


class WebhookIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=8, max_length=500)
    events: list[str] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("название пустое")
        return v

    @field_validator("url")
    @classmethod
    def _url(cls, v: str) -> str:
        return check_url(v)

    @field_validator("events")
    @classmethod
    def _events(cls, v: list[str]) -> list[str]:
        return _check_events(v)


class WebhookPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=8, max_length=500)
    events: Optional[list[str]] = Field(None, min_length=1)
    active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def _url(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else check_url(v)

    @field_validator("events")
    @classmethod
    def _events(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        return None if v is None else _check_events(v)


_HOOK_COLUMNS = ("id, name, url, events, active, created_by, created_at, updated_at, last_ok_at, failing_since, "
                 "disabled_note")
_STATS = """
    SELECT webhook_id,
           count(*) FILTER (WHERE status = 'pending') AS pending,
           count(*) FILTER (WHERE status = 'failed') AS failed,
           count(*) FILTER (WHERE status = 'ok') AS ok
      FROM tgid_webhook_delivery WHERE webhook_id = ANY($1::int[]) GROUP BY webhook_id
"""


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else v


def _hook(row, stats: Optional[dict[str, int]] = None) -> dict[str, Any]:
    out = {k: _iso(row[k]) for k in row.keys() if k != "secret"}
    out["events"] = list(row["events"] or [])
    out["deliveries"] = stats or {"pending": 0, "failed": 0, "ok": 0}
    return out


async def list_hooks(conn) -> list[dict[str, Any]]:
    rows = await conn.fetch(f"SELECT {_HOOK_COLUMNS} FROM tgid_webhook ORDER BY id")
    stats = {r["webhook_id"]: {"pending": r["pending"], "failed": r["failed"], "ok": r["ok"]}
             for r in await conn.fetch(_STATS, [r["id"] for r in rows])}
    return [_hook(r, stats.get(r["id"])) for r in rows]


async def _get(conn, hook_id: int, *, with_secret: bool = False):
    cols = _HOOK_COLUMNS + (", secret" if with_secret else "")
    row = await conn.fetchrow(f"SELECT {cols} FROM tgid_webhook WHERE id = $1", hook_id)
    if row is None:
        raise WebhookError(404, f"Подписка {hook_id} не найдена")
    return row


async def create_hook(conn, body: WebhookIn, user: str) -> dict[str, Any]:
    if await conn.fetchval("SELECT count(*) FROM tgid_webhook") >= MAX_HOOKS:
        raise WebhookError(409, f"Подписок не больше {MAX_HOOKS}")
    secret = new_secret()
    row = await conn.fetchrow(
        f"""INSERT INTO tgid_webhook (name, url, events, secret, created_by) VALUES ($1, $2, $3, $4, $5)
            RETURNING {_HOOK_COLUMNS}""", body.name, body.url, body.events, secret, user)
    return {**_hook(row), "secret": secret}


async def update_hook(conn, hook_id: int, patch: WebhookPatch) -> dict[str, Any]:
    await _get(conn, hook_id)
    values = patch.model_dump(exclude_none=True)
    if not values:
        raise WebhookError(422, "Нечего менять")
    sets = [f"{k} = ${i}" for i, k in enumerate(values, start=2)]
    if values.get("active"):
        # включили снова — счёт неудач с нуля
        sets += ["failing_since = NULL", "disabled_note = NULL"]
    row = await conn.fetchrow(
        f"UPDATE tgid_webhook SET {', '.join(sets)}, updated_at = now() WHERE id = $1 RETURNING {_HOOK_COLUMNS}",
        hook_id, *values.values())
    return _hook(row)


async def rotate_secret(conn, hook_id: int) -> dict[str, Any]:
    await _get(conn, hook_id)
    secret = new_secret()
    row = await conn.fetchrow(
        f"UPDATE tgid_webhook SET secret = $2, updated_at = now() WHERE id = $1 RETURNING {_HOOK_COLUMNS}",
        hook_id, secret)
    return {**_hook(row), "secret": secret}


async def delete_hook(conn, hook_id: int) -> dict[str, Any]:
    row = await _get(conn, hook_id)
    await conn.execute("DELETE FROM tgid_webhook WHERE id = $1", hook_id)
    return {"id": hook_id, "name": row["name"]}


async def deliveries(conn, hook_id: int, *, status: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
    await _get(conn, hook_id)
    args: list[Any] = [hook_id, max(1, min(500, limit))]
    where = "webhook_id = $1"
    if status:
        args.append(status)
        where += " AND status = $3"
    rows = await conn.fetch(
        f"""SELECT id, event_id, event_type, payload->>'id' AS event_key, status, attempts, next_at, last_code,
                   last_error, created_at, delivered_at
              FROM tgid_webhook_delivery WHERE {where} ORDER BY id DESC LIMIT $2""", *args)
    return [{k: _iso(r[k]) for k in r.keys()} for r in rows]


async def retry_delivery(conn, delivery_id: int) -> dict[str, Any]:
    # отправляемая сейчас (аренда до LEASE_S) и ждущая первого повтора — не трогаются: уйдут сами
    row = await conn.fetchrow(
        f"""UPDATE tgid_webhook_delivery SET status = 'pending', next_at = now(), attempts = 0
            WHERE id = $1
              AND (status = 'failed' OR (status = 'pending' AND next_at > now() + interval '{LEASE_S} seconds'))
            RETURNING id, webhook_id""", delivery_id)
    if row is None:
        raise WebhookError(409, f"Доставка {delivery_id} не найдена, уже доставлена или отправляется сейчас")
    return {"id": row["id"], "webhook_id": row["webhook_id"], "status": "pending"}


# --- доставка ----------------------------------------------------------------------------------

@dataclass
class Result:
    ok: bool
    code: Optional[int]
    error: Optional[str]
    ms: int


async def send(url: str, secret: str, payload: dict[str, Any], *, client: Optional[httpx.AsyncClient] = None) -> Result:
    """Один POST: тело, подпись, запрос на проверенный IP хоста (SNI и Host — имя хоста)."""
    started = time.monotonic()
    body = body_bytes(payload)
    timestamp = int(time.time())
    headers = {
        "content-type": "application/json",
        "user-agent": USER_AGENT,
        "webhook-id": str(payload["id"]),
        "webhook-timestamp": str(timestamp),
        "webhook-signature": sign(secret, str(payload["id"]), timestamp, body),
    }
    parts = urlsplit(url)
    host = parts.hostname or ""
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        ip = await _resolve(host, port)
    except WebhookError as exc:
        return Result(False, None, exc.message, int((time.monotonic() - started) * 1000))
    ip_host = f"[{ip}]" if ":" in ip else ip
    target = urlunsplit((parts.scheme, f"{ip_host}:{port}", parts.path or "/", parts.query, ""))
    headers["host"] = parts.netloc.rsplit("@", 1)[-1]
    own = client is None
    http = client or new_client()

    async def post() -> int:
        # тело ответа не читается: медленный или бесконечный ответ не держит доставку и память
        async with http.stream("POST", target, content=body, headers=headers,
                               extensions={"sni_hostname": host} if parts.scheme == "https" else None) as response:
            return response.status_code

    try:
        # общий срок: таймаут httpx — на каждое чтение, ответ по байту в 9 с его не превысил бы
        code = await asyncio.wait_for(post(), SEND_DEADLINE_S)
        ok = 200 <= code < 300
        return Result(ok, code, None if ok else f"Ответ {code}", int((time.monotonic() - started) * 1000))
    except (httpx.TimeoutException, asyncio.TimeoutError):
        return Result(False, None, f"Нет ответа за {SEND_TIMEOUT_S:.0f} с", int((time.monotonic() - started) * 1000))
    except httpx.HTTPError as exc:
        return Result(False, None, f"{type(exc).__name__}: {exc}"[:300], int((time.monotonic() - started) * 1000))
    finally:
        if own:
            await http.aclose()


def new_client() -> httpx.AsyncClient:
    # trust_env=False: HTTP(S)_PROXY службы не должен уводить запрос на проверенный IP в прокси
    return httpx.AsyncClient(timeout=SEND_TIMEOUT_S, follow_redirects=False, trust_env=False)


def ping_payload(city: str, hook_id: int) -> dict[str, Any]:
    return {
        "id": f"evt_{city or 'city'}_ping_{uuid.uuid4().hex[:12]}",
        "type": api_events.PING,
        "occurred_at": api_events.utc_iso(datetime.now(timezone.utc)),
        "city": city,
        "data": {"webhook_id": hook_id, "message": "Проверка подписки ТГИД"},
    }


async def test_hook(conn, hook_id: int, city: str) -> dict[str, Any]:
    """«Проверить»: событие ping сразу, без очереди и повторов; результат — в журнал доставок."""
    row = await _get(conn, hook_id, with_secret=True)
    payload = ping_payload(city, hook_id)
    result = await send(row["url"], row["secret"], payload)
    await conn.execute(
        """INSERT INTO tgid_webhook_delivery (webhook_id, event_type, payload, status, attempts, last_code, last_error,
                                              delivered_at)
           VALUES ($1, $2, $3::jsonb, $4::varchar, 1, $5, $6, CASE WHEN $4::varchar = 'ok' THEN now() END)""",
        hook_id, api_events.PING, json.dumps(payload, ensure_ascii=False), "ok" if result.ok else "failed",
        result.code, result.error)
    if result.ok:
        # адрес принимает — отметка в списке; сбои реальных доставок снимает только их успешная доставка
        await conn.execute("UPDATE tgid_webhook SET last_ok_at = now() WHERE id = $1", hook_id)
    return {"ok": result.ok, "code": result.code, "error": result.error, "ms": result.ms, "event_id": payload["id"]}


_FAN_OUT = """
    INSERT INTO tgid_webhook_delivery (webhook_id, event_id, event_type, payload)
    SELECT w.id, e.id, e.type,
           jsonb_build_object('id', 'evt_' || $2::text || '_' || e.id, 'type', e.type,
                              'occurred_at', to_char(e.occurred_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
                              'city', $2::text, 'data', e.data)
      FROM tgid_api_event e
      JOIN tgid_webhook w ON w.active AND e.type = ANY(w.events)
     WHERE e.id = ANY($1::bigint[])
    ON CONFLICT (webhook_id, event_id) DO NOTHING
"""

_CLAIM = f"""
    WITH due AS (
        SELECT d.id FROM tgid_webhook_delivery d JOIN tgid_webhook w ON w.id = d.webhook_id AND w.active
         WHERE d.status = 'pending' AND d.next_at <= now()
         ORDER BY d.next_at, d.id LIMIT $1
           FOR UPDATE OF d SKIP LOCKED)
    UPDATE tgid_webhook_delivery d SET attempts = d.attempts + 1, next_at = now() + interval '{LEASE_S} seconds'
      FROM due, tgid_webhook w
     WHERE d.id = due.id AND w.id = d.webhook_id
    RETURNING d.id, d.webhook_id, d.payload, d.attempts, w.url, w.secret
"""


async def collect_and_fan_out(conn, city: str) -> int:
    """Собрать события источников и разложить по подпискам; 0 — замок у другого процесса или нет нового."""
    async with conn.transaction():
        if not await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", _COLLECT_LOCK):
            return 0
        new_ids = await api_events.collect(conn)
        if new_ids:
            await conn.execute(_FAN_OUT, new_ids, city or "city")
    return len(new_ids)


async def _finish(conn, delivery: dict[str, Any], result: Result) -> None:
    hook_id = delivery["webhook_id"]
    if result.ok:
        await conn.execute(
            """UPDATE tgid_webhook_delivery SET status = 'ok', delivered_at = now(), last_code = $2, last_error = NULL
                WHERE id = $1""", delivery["id"], result.code)
        await conn.execute("UPDATE tgid_webhook SET last_ok_at = now(), failing_since = NULL WHERE id = $1", hook_id)
        return
    attempts = int(delivery["attempts"])
    final = attempts >= MAX_ATTEMPTS
    delay = 0 if final else RETRY_DELAYS_S[attempts - 1]
    await conn.execute(
        f"""UPDATE tgid_webhook_delivery
               SET status = $2, last_code = $3, last_error = $4, next_at = now() + interval '{delay} seconds'
             WHERE id = $1""", delivery["id"], "failed" if final else "pending", result.code, result.error)
    await conn.execute(
        f"""UPDATE tgid_webhook
               SET failing_since = coalesce(failing_since, now()),
                   active = CASE WHEN failing_since < now() - interval '{FAIL_DISABLE_DAYS} days' THEN false
                                 ELSE active END,
                   disabled_note = CASE WHEN failing_since < now() - interval '{FAIL_DISABLE_DAYS} days'
                                        THEN 'Выключена: адрес не принимает события {FAIL_DISABLE_DAYS} дн.'
                                        ELSE disabled_note END
             WHERE id = $1""", hook_id)


async def deliver_due(conn, *, client: Optional[httpx.AsyncClient] = None) -> int:
    """Отправить подошедшие доставки (до BATCH за раз, параллельно); вернуть сколько отправлено."""
    rows = await conn.fetch(_CLAIM, BATCH)
    if not rows:
        return 0
    batch = [dict(r) for r in rows]
    own = client is None
    http = client or new_client()
    try:
        results = await asyncio.gather(*(send(
            d["url"], d["secret"], json.loads(d["payload"]) if isinstance(d["payload"], str) else d["payload"],
            client=http) for d in batch))
    finally:
        if own:
            await http.aclose()
    for delivery, result in zip(batch, results):
        await _finish(conn, delivery, result)
    return len(batch)


async def run_once(conn, city: str) -> tuple[int, int]:
    collected = await collect_and_fan_out(conn, city)
    sent = await deliver_due(conn)
    return collected, sent


async def check_sensor_alerts(conn) -> int:
    """Тревоги телеметрии (database/telemetry.py) и перерасчёт по факту (database/telemetry_regime.py,
    TELEMETRY_REGIME_AUTO=1) — под своим замком: один процесс на город."""
    from database import telemetry, telemetry_regime

    async with conn.transaction():
        if not await conn.fetchval("SELECT pg_try_advisory_xact_lock($1)", _ALERT_LOCK):
            return 0
        if not await conn.fetchval("SELECT to_regclass('public.tgid_sensor_alert') IS NOT NULL"):
            return 0
        alerts = len(await telemetry.check_alerts(conn))
        try:
            async with conn.transaction():  # точка сохранения: сбой очереди расчётов не откатывает тревоги
                await telemetry_regime.auto_recalc(conn)
        except Exception as exc:  # noqa: BLE001 — брокер Celery недоступен и т. п.: следующий проход
            logger.warning("Перерасчёт по факту: %s", exc)
        try:
            async with conn.transaction():
                alerts += len(await check_balance_alerts(conn))
        except Exception as exc:  # noqa: BLE001 — таблица ещё создаётся и т. п.: следующий проход
            logger.warning("Баланс расхода: %s", exc)
        return alerts


async def check_balance_alerts(conn) -> list[int]:
    """Тревоги баланса расхода по зонам (database/flow_balance.py) — не чаще BALANCE_EVERY_S на город."""
    from cities import current_city
    from database import flow_balance
    from database.outage_simulation import get_outage_network_graph

    city = current_city() or ""
    if time.monotonic() - _last_balance.get(city, -1e9) < BALANCE_EVERY_S:
        return []
    if not await conn.fetchval("SELECT to_regclass('public.tgid_balance_alert') IS NOT NULL"):
        return []  # таблицу ещё создаёт доводка базы — проверить на следующем проходе
    _last_balance[city] = time.monotonic()
    if not await conn.fetchval("SELECT EXISTS (SELECT 1 FROM tgid_sensor WHERE active AND kind = 'flow')"):
        return []
    return await flow_balance.check_alerts(conn, await get_outage_network_graph(conn))


async def webhook_loop(city: str, interval_s: float) -> None:
    """Фоновая задача города: события и доставки раз в interval_s, тревоги телеметрии — раз в ALERT_EVERY_S;
    ошибки базы — в лог и дальше."""
    from database.connect import acquire_conn

    last_prune = 0.0
    last_alerts = 0.0
    while True:
        try:
            async with acquire_conn() as conn:
                # сначала сбор событий: у нового источника курсор встаёт на текущий максимум до первых тревог,
                # иначе первая тревога после выкатки (утечка, что уже идёт) наружу бы не ушла
                await run_once(conn, city)
                if time.monotonic() - last_alerts >= ALERT_EVERY_S:
                    last_alerts = time.monotonic()
                    await check_sensor_alerts(conn)
                if time.monotonic() - last_prune > PRUNE_EVERY_S:
                    await api_events.prune(conn)
                    await conn.execute(
                        f"DELETE FROM tgid_webhook_delivery WHERE event_id IS NULL "
                        f"AND created_at < now() - interval '{api_events.RETENTION_DAYS} days'")
                    last_prune = time.monotonic()
        except asyncio.CancelledError:
            raise
        except asyncpg.UndefinedTableError as exc:  # таблицы ещё создаёт доводка базы (city_schema)
            logger.debug("Вебхуки города %s: %s", city or "-", exc)
        except Exception as exc:  # noqa: BLE001 — база недоступна: следующий проход
            logger.warning("Вебхуки города %s: %s", city or "-", exc)
        await asyncio.sleep(interval_s)
