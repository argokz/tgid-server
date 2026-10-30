"""Живая карта (фаза 2, п. 11): присутствие пользователей и рассылка правок сети по открытым картам.

Браузер держит поток событий GET /api/v1/live/stream (Server-Sent Events: обычный HTTP, без WebSocket — серверу
не нужна ещё одна библиотека, nginx пропускает его как есть) и раз в 20 с сообщает, где смотрит и какой объект
правит (POST /api/v1/live/presence → tgid_live_presence).

События потока:
- presence — кто сейчас на карте города: пользователь, центр и масштаб вида, объект правки;
- network.changed — правки сети и журналов из audit_log (его пишут триггеры базы — видны и правки из десктопа):
  таблица, кто, сколько объектов, их id (до MAX_IDS) и охват на карте (участки и узлы);
- data_version — новая версия данных (как /api/v1/map/data-version): веб сразу берёт тайлы по новому адресу;
- resync — браузер не успевал читать: переподключиться.

Один процесс API — один «узел рассылки» на город (Hub): пока есть подписчики, раз в TICK_S читает audit_log
после своего курсора, присутствие и версию данных. Каждый процесс читает базу сам — между процессами ничего
передавать не нужно. Поток закрывается через STREAM_MAX_S: при переподключении вход проверяется заново
(заблокированный пользователь или истёкший токен поток не продлят).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

TICK_S = 2.0
PRESENCE_TTL_S = 60
PRESENCE_EVERY_TICKS = 3
KEEPALIVE_S = 15.0
STREAM_MAX_S = 600
QUEUE_SIZE = 200
MAX_SUBSCRIBERS = 500
MAX_IDS = 50
RESCAN_IDS = 200
MAX_ROWS = 2000

# Какие таблицы audit_log рассылаются (учётные записи и служебные — нет): подпись во множественном числе
TABLE_LABELS: dict[str, str] = {
    "linesobj": "участки",
    "heatpipesections": "свойства участков",
    "nodes": "узлы",
    "connectnodes": "узлы присоединения",
    "realconsumers": "потребители",
    "generalizedconsumers": "обобщённые потребители",
    "heatsources": "источники",
    "pumpstations": "насосные станции",
    "pumps": "насосы",
    "pressregulators": "регуляторы давления",
    "dampers": "задвижки",
    "defect": "дефекты",
    "shurfy": "шурфы",
    "remont2": "ремонты",
    "opres": "опрессовки",
    "osmotr": "осмотры",
}
# охват на карте — по геометрии самих объектов
_SHAPE_TABLES = ("linesobj", "nodes")

DATA_VERSION_SQL = """
SELECT COALESCE(SUM(n_tup_ins + n_tup_upd + n_tup_del), 0)::bigint
FROM pg_stat_user_tables WHERE schemaname = 'public'
"""


# --- присутствие -------------------------------------------------------------------------------

class EditingIn(BaseModel):
    kind: str = Field(min_length=1, max_length=20, pattern=r"^[a-z_]+$")
    id: int = Field(ge=1)
    label: str = Field("", max_length=200)


class PresenceIn(BaseModel):
    session_id: UUID = Field(description="Ключ вкладки браузера (crypto.randomUUID)")
    center: Optional[tuple[float, float]] = Field(None, description="[долгота, широта] центра вида")
    zoom: Optional[float] = Field(None, ge=0, le=24)
    editing: Optional[EditingIn] = None


def session_key(session_id: UUID | str) -> str:
    """Ключ вкладки для других: сам session_id не рассылается (по нему можно было бы писать за чужую вкладку)."""
    return hashlib.sha256(str(session_id).encode()).hexdigest()[:12]


async def heartbeat(conn, body: PresenceIn, username: str) -> str:
    center = body.center
    if center and not (-180 <= center[0] <= 180 and -90 <= center[1] <= 90):
        center = None
    e = body.editing
    # чужую вкладку (тот же session_id у другого пользователя) не перезаписать
    await conn.execute(
        """INSERT INTO tgid_live_presence (session_id, username, center_lon, center_lat, zoom, editing_kind,
                                           editing_id, editing_label)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
           ON CONFLICT (session_id) DO UPDATE
              SET center_lon = EXCLUDED.center_lon, center_lat = EXCLUDED.center_lat, zoom = EXCLUDED.zoom,
                  editing_kind = EXCLUDED.editing_kind, editing_id = EXCLUDED.editing_id,
                  editing_label = EXCLUDED.editing_label, seen_at = now()
            WHERE tgid_live_presence.username = EXCLUDED.username""",
        body.session_id, username, center[0] if center else None, center[1] if center else None, body.zoom,
        e.kind if e else None, e.id if e else None, (e.label.strip() or None) if e else None)
    return session_key(body.session_id)


async def leave(conn, session_id: UUID, username: str) -> None:
    await conn.execute("DELETE FROM tgid_live_presence WHERE session_id = $1 AND username = $2", session_id, username)


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, datetime) else v


async def online(conn) -> list[dict[str, Any]]:
    """Кто на карте: вкладки, отметившиеся за PRESENCE_TTL_S; ушедшие давно — удаляются."""
    await conn.execute(
        f"DELETE FROM tgid_live_presence WHERE seen_at < now() - interval '{PRESENCE_TTL_S * 5} seconds'")
    rows = await conn.fetch(
        f"""SELECT session_id, username, center_lon, center_lat, zoom, editing_kind, editing_id, editing_label,
                   started_at
              FROM tgid_live_presence WHERE seen_at > now() - interval '{PRESENCE_TTL_S} seconds'
             ORDER BY username, started_at""")
    out = []
    for r in rows:
        item: dict[str, Any] = {"key": session_key(r["session_id"]), "username": r["username"],
                                "since": _iso(r["started_at"])}
        if r["center_lon"] is not None:
            item["center"] = [round(r["center_lon"], 5), round(r["center_lat"], 5)]
            item["zoom"] = round(r["zoom"], 1) if r["zoom"] is not None else None
        if r["editing_kind"]:
            item["editing"] = {"kind": r["editing_kind"], "id": r["editing_id"], "label": r["editing_label"] or ""}
        out.append(item)
    return out


# --- правки ------------------------------------------------------------------------------------

@dataclass
class ChangeCursor:
    last_id: Optional[int] = None
    # номер на момент подписки: история до него не рассылается (иначе первый проход повторил бы RESCAN_IDS старых)
    floor: int = 0
    # роли PostgreSQL: строки триггеров пишут changed_by = роль базы, строки API — пользователя веба
    db_roles: frozenset = frozenset()
    seen: deque = field(default_factory=lambda: deque(maxlen=RESCAN_IDS * 10))


async def _bbox(conn, table: str, ids: list[int]) -> Optional[list[float]]:
    row = await conn.fetchrow(
        f"""SELECT ST_XMin(e) x1, ST_YMin(e) y1, ST_XMax(e) x2, ST_YMax(e) y2
              FROM (SELECT ST_Extent(ST_Transform(shape, 4326)) e FROM {table}
                     WHERE id = ANY($1::int[]) AND shape IS NOT NULL) s""", ids)  # noqa: S608 — из _SHAPE_TABLES
    if row is None or row["x1"] is None:
        return None
    return [round(row[k], 6) for k in ("x1", "y1", "x2", "y2")]


async def _group_authors(conn, rows, db_roles: frozenset) -> dict[Any, str]:
    """Пользователь веба для групп правок (change_group_id): строки триггеров группы пишут роль базы,
    а строка API той же группы — того, кто правил."""
    gids = list({r["change_group_id"] for r in rows if r["change_group_id"] is not None})
    if not gids:
        return {}
    found = await conn.fetch(
        "SELECT DISTINCT ON (change_group_id) change_group_id, changed_by FROM audit_log"
        " WHERE change_group_id = ANY($1::uuid[]) AND changed_by <> ALL($2::text[]) ORDER BY change_group_id, log_id",
        gids, list(db_roles))
    return {r["change_group_id"]: r["changed_by"] for r in found}


async def collect_changes(conn, cursor: ChangeCursor) -> list[dict[str, Any]]:
    """Новые строки audit_log по таблицам TABLE_LABELS, сгруппированные по таблице и автору.

    Каждый проход заново смотрит RESCAN_IDS номеров до курсора (запись с меньшим номером могла закоммититься позже),
    уже разосланные отсеиваются по cursor.seen. Первый проход только ставит курсор.
    """
    if cursor.last_id is None:
        cursor.last_id = cursor.floor = int(await conn.fetchval("SELECT coalesce(max(log_id), 0) FROM audit_log"))
        cursor.db_roles = frozenset(r["rolname"] for r in await conn.fetch("SELECT rolname FROM pg_roles"))
        return []
    rows = await conn.fetch(
        """SELECT log_id, operation, table_name, record_id, changed_by, change_group_id FROM audit_log
            WHERE log_id > $1 AND table_name = ANY($2::text[]) ORDER BY log_id LIMIT $3""",
        max(cursor.last_id - RESCAN_IDS, cursor.floor), list(TABLE_LABELS), MAX_ROWS)
    # время правки — когда её увидел сервер (±TICK_S): changed_at в audit_log без часового пояса, и пояс у десктопа
    # и API может быть разный
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    seen = set(cursor.seen)
    authors = await _group_authors(conn, rows, cursor.db_roles)
    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for r in rows:
        log_id = int(r["log_id"])
        cursor.last_id = max(cursor.last_id, log_id)
        if log_id in seen:
            continue
        cursor.seen.append(log_id)
        by = authors.get(r["change_group_id"]) or r["changed_by"] or ""
        key = (r["table_name"], by)
        g = groups.setdefault(key, {"table": key[0], "label": TABLE_LABELS[key[0]], "by": key[1], "ids": set(),
                                    "ops": set()})
        if r["record_id"] is not None:
            g["ids"].add(int(r["record_id"]))
        g["ops"].add(r["operation"])
    out = []
    for g in groups.values():
        ids = sorted(g["ids"])
        item = {"table": g["table"], "label": g["label"], "by": g["by"], "count": len(ids), "ids": ids[:MAX_IDS],
                "ops": sorted(g["ops"]), "at": now,
                # автор — роль базы без строки API в группе: правка мимо веба (десктоп, скрипт)
                "direct": g["by"] in cursor.db_roles}
        if g["table"] in _SHAPE_TABLES and ids:
            item["bbox"] = await _bbox(conn, g["table"], ids[:MAX_ROWS])
        out.append(item)
    return out


# --- рассылка ----------------------------------------------------------------------------------

@dataclass(eq=False)  # в множестве подписчиков — по идентичности
class Subscriber:
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=QUEUE_SIZE))
    overflow: bool = False


class Hub:
    """Рассылка одного города в одном процессе: задача опроса живёт, пока есть подписчики."""

    def __init__(self, city: str):
        self.city = city
        self.subscribers: set[Subscriber] = set()
        self.task: Optional[asyncio.Task] = None
        self.cursor = ChangeCursor()
        self.presence: list[dict[str, Any]] = []
        self.version: Optional[str] = None

    def subscribe(self) -> Subscriber:
        if len(self.subscribers) >= MAX_SUBSCRIBERS:
            raise OverflowError("Слишком много открытых карт на этом сервере")
        sub = Subscriber()
        self.subscribers.add(sub)
        if self.task is None or self.task.done():
            # рассылка начинается с «сейчас»: накопленное, пока карт не было открыто, не рассылается
            self.cursor = ChangeCursor()
            # задача копирует контекст запроса — город и пул базы этого города
            self.task = asyncio.create_task(self._run())
        return sub

    def unsubscribe(self, sub: Subscriber) -> None:
        self.subscribers.discard(sub)

    def broadcast(self, event: str, data: Any) -> None:
        for sub in list(self.subscribers):
            try:
                sub.queue.put_nowait((event, data))
            except asyncio.QueueFull:
                sub.overflow = True

    async def tick(self, conn, n: int) -> None:
        for change in await collect_changes(conn, self.cursor):
            self.broadcast("network.changed", change)
        version = str(await conn.fetchval(DATA_VERSION_SQL))
        if version != self.version:
            first = self.version is None
            self.version = version
            if not first:
                self.broadcast("data_version", {"version": version})
        if n % PRESENCE_EVERY_TICKS == 0:
            presence = await online(conn)
            if presence != self.presence:
                self.presence = presence
                self.broadcast("presence", presence)

    async def _run(self) -> None:
        from database.connect import acquire_conn

        n = 0
        while self.subscribers:
            try:
                async with acquire_conn() as conn:
                    await self.tick(conn, n)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — база недоступна или ещё без таблицы: следующий проход
                logger.warning("Живая карта %s: %s", self.city or "-", exc)
            n += 1
            await asyncio.sleep(TICK_S)

    async def snapshot(self, conn) -> dict[str, Any]:
        """Первое сообщение нового подписчика: присутствие и версия сейчас."""
        self.presence = await online(conn)
        self.version = self.version or str(await conn.fetchval(DATA_VERSION_SQL))
        return {"presence": self.presence, "version": self.version}


_hubs: dict[str, Hub] = {}


def hub(city_key: str) -> Hub:
    found = _hubs.get(city_key)
    if found is None:
        found = _hubs[city_key] = Hub(city_key)
    return found


def sse(event: str, data: str) -> bytes:
    """Сообщение потока событий: многострочные данные — каждая строка с «data: »."""
    lines = "".join(f"data: {line}\n" for line in data.split("\n"))
    return f"event: {event}\n{lines}\n".encode("utf-8")
