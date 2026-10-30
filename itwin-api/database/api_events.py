"""События для внешних систем (фаза 2: вебхуки и API v2): журнал tgid_api_event.

Источники — то, что уже пишут журналы, поэтому код нарядов и отключений не знает о вебхуках:
- история нарядов tgid_work_order_event: создание и смены статуса (комментарии — нет);
- история отключений tgid_outage_event: так же;
- журнал дефектов defect: новые записи — и веба, и десктопа (десктоп событий не пишет, поэтому журнал читается
  по возрастанию id).

Фоновая задача (database/webhooks.py) раз в WEBHOOK_POLL_S переносит новые записи источников в tgid_api_event.
Курсор — последний id источника; каждый проход заново смотрит RESCAN_IDS записей до курсора: транзакция, начатая
раньше, могла закоммитить меньший id позже. Уже перенесённые записи отсекаются до вставки (NOT EXISTS — иначе
каждый проход тратил бы номера событий), уникальность (source, source_id) — страховка. При первом
проходе курсор ставится на текущий максимум: история до включения событий наружу не уходит.

Данные события — короткие и без ПДн (номер, статус, сроки, число потребителей). Свободного текста (название и
описание наряда — туда call-центр может вписать телефон жителя) в событии нет: подробности внешняя система берёт
из API v2 своим ключом, с маскированием по её правам.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

EVENT_TYPES: dict[str, str] = {
    "defect.created": "Новый дефект (авария, нарушение) — из веба, с обхода или из десктопа",
    "work_order.created": "Новая заявка или наряд",
    "work_order.status_changed": "Статус наряда изменён (назначен, в работе, выполнен, закрыт, отменён)",
    "outage.created": "Запланировано отключение",
    "outage.status_changed": "Статус отключения изменён (объявлено, идёт, завершено, отменено)",
}
PING = "ping"
RESCAN_IDS = 200
RETENTION_DAYS = 30
MAX_FEED = 500


@dataclass(frozen=True)
class Source:
    name: str
    table: str
    # INSERT … SELECT новых событий источника: $1 — с какого id (не включая), $2 — нижняя граница (пол)
    insert_sql: str


_WORK_ORDER_SQL = """
    INSERT INTO tgid_api_event (type, object_id, occurred_at, data, source, source_id)
    SELECT CASE WHEN e.from_status IS NULL THEN 'work_order.created' ELSE 'work_order.status_changed' END,
           o.id, e.at,
           jsonb_strip_nulls(jsonb_build_object(
               'work_order_id', o.id, 'number', o.number, 'kind', o.kind, 'priority', o.priority,
               'status', e.to_status, 'from_status', e.from_status, 'defect_id', o.defect_id, 'line_id', o.line_id,
               'node_id', o.node_id, 'lon', o.lon, 'lat', o.lat, 'planned_finish', o.planned_finish)),
           'work_order', e.id
      FROM tgid_work_order_event e
      JOIN tgid_work_order o ON o.id = e.order_id
     WHERE e.id > $1 AND e.id > $2 AND e.to_status IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM tgid_api_event a WHERE a.source = 'work_order' AND a.source_id = e.id)
     ORDER BY e.id
    ON CONFLICT (source, source_id) DO NOTHING
    RETURNING id
"""

_OUTAGE_SQL = """
    INSERT INTO tgid_api_event (type, object_id, occurred_at, data, source, source_id)
    SELECT CASE WHEN e.from_status IS NULL THEN 'outage.created' ELSE 'outage.status_changed' END,
           o.id, e.at,
           jsonb_strip_nulls(jsonb_build_object(
               'outage_id', o.id, 'number', o.number, 'kind', o.kind, 'status', e.to_status,
               'from_status', e.from_status, 'planned_start', o.planned_start, 'planned_end', o.planned_end,
               'consumers_count', o.consumers_count, 'load_gcal_h', round(o.load_gcal_h::numeric, 4),
               'public', o.public, 'work_order_id', o.work_order_id, 'line_id', o.line_id, 'node_id', o.node_id)),
           'outage', e.id
      FROM tgid_outage_event e
      JOIN tgid_outage o ON o.id = e.outage_id
     WHERE e.id > $1 AND e.id > $2 AND e.to_status IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM tgid_api_event a WHERE a.source = 'outage' AND a.source_id = e.id)
     ORDER BY e.id
    ON CONFLICT (source, source_id) DO NOTHING
    RETURNING id
"""

# Журнал дефектов десктопа: времени записи нет — время события = время прохода (дата осмотра — в данных)
_DEFECT_SQL = """
    INSERT INTO tgid_api_event (type, object_id, occurred_at, data, source, source_id)
    SELECT 'defect.created', d.id, now(),
           jsonb_strip_nulls(jsonb_build_object(
               'defect_id', d.id, 'detected_at', d.data_osmotra, 'category', c.name, 'state', s.name,
               'source', t.name, 'line_id', d.lineid,
               'lon', CASE WHEN d.shape IS NULL THEN NULL ELSE round(ST_X(ST_Transform(d.shape, 4326))::numeric, 6) END,
               'lat', CASE WHEN d.shape IS NULL THEN NULL ELSE round(ST_Y(ST_Transform(d.shape, 4326))::numeric, 6) END)),
           'defect', d.id
      FROM defect d
      LEFT JOIN remontcat c ON c.id = d.remontcatid
      LEFT JOIN statedefect s ON s.id = d.stateid
      LEFT JOIN defecttypes t ON t.id = d.remonttypeid
     WHERE d.id > $1 AND d.id > $2
       AND NOT EXISTS (SELECT 1 FROM tgid_api_event a WHERE a.source = 'defect' AND a.source_id = d.id)
     ORDER BY d.id
    ON CONFLICT (source, source_id) DO NOTHING
    RETURNING id
"""

SOURCES: tuple[Source, ...] = (
    Source("defect", "defect", _DEFECT_SQL),
    Source("work_order", "tgid_work_order_event", _WORK_ORDER_SQL),
    Source("outage", "tgid_outage_event", _OUTAGE_SQL),
)


async def _max_id(conn, table: str) -> int:
    return int(await conn.fetchval(f"SELECT coalesce(max(id), 0) FROM {table}"))  # noqa: S608 — имя из SOURCES


async def collect(conn) -> list[int]:
    """Перенести новые записи источников в tgid_api_event; вернуть id новых событий.

    Вызывать в транзакции под замком (database/webhooks.py): два процесса API не должны собирать одновременно.
    """
    new_ids: list[int] = []
    for src in SOURCES:
        if not await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", src.table):
            continue
        cursor = await conn.fetchrow(
            "SELECT last_id, floor_id FROM tgid_api_event_cursor WHERE source = $1", src.name)
        top = await _max_id(conn, src.table)
        if cursor is None:
            # первый проход: история до включения событий наружу не уходит
            await conn.execute(
                "INSERT INTO tgid_api_event_cursor (source, last_id, floor_id) VALUES ($1, $2, $2)"
                " ON CONFLICT (source) DO NOTHING", src.name, top)
            continue
        last_id = int(cursor["last_id"])
        rows = await conn.fetch(src.insert_sql, max(last_id - RESCAN_IDS, 0), int(cursor["floor_id"]))
        new_ids.extend(int(r["id"]) for r in rows)
        if top > last_id:
            await conn.execute("UPDATE tgid_api_event_cursor SET last_id = $2 WHERE source = $1", src.name, top)
    return new_ids


async def prune(conn) -> int:
    """Удалить события старше RETENTION_DAYS (их доставки удаляются каскадом)."""
    status = await conn.execute(
        f"DELETE FROM tgid_api_event WHERE created_at < now() - interval '{RETENTION_DAYS} days'")
    return int(status.split()[-1]) if status.startswith("DELETE") else 0


def utc_iso(v: datetime) -> str:
    """Время события — UTC с «Z», как в теле вебхука (to_char в database/webhooks.py)."""
    return v.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def envelope(row, city: str) -> dict[str, Any]:
    """Событие наружу (тело вебхука и элемент ленты /api/v2/events)."""
    data = row["data"]
    return {
        "id": event_id(city, int(row["id"])),
        "type": row["type"],
        "occurred_at": utc_iso(row["occurred_at"]),
        "city": city,
        "data": json.loads(data) if isinstance(data, str) else data,
    }


def event_id(city: str, seq: int) -> str:
    """Ключ события для получателя: повтор доставки приходит с тем же ключом (дедупликация на стороне получателя)."""
    return f"evt_{city or 'city'}_{seq}"


async def feed(conn, city: str, *, after: int = 0, types: Optional[list[str]] = None,
               limit: int = 100) -> dict[str, Any]:
    """Лента событий для опроса: после курсора after (seq последнего полученного), по возрастанию."""
    limit = max(1, min(MAX_FEED, limit))
    args: list[Any] = [after, limit + 1]
    where = "id > $1"
    if types:
        args.append(types)
        where += f" AND type = ANY(${len(args)}::text[])"
    rows = await conn.fetch(
        f"SELECT id, type, occurred_at, data FROM tgid_api_event WHERE {where} ORDER BY id LIMIT $2", *args)
    more = len(rows) > limit
    rows = rows[:limit]
    return {
        "data": [{**envelope(r, city), "seq": int(r["id"])} for r in rows],
        "next_after": int(rows[-1]["id"]) if rows else after,
        "has_more": more,
    }
