"""Именованные настройки трассировки (по образцу конфигураций трассировки ArcGIS Utility Network).

Настройка — тип трассировки и барьеры по условию (database/network_trace.py, ``stop_at``); начальные
точки и барьеры-объекты задаются при запуске. Встроенные настройки (BUILTIN, id «builtin:…») есть
в каждом городе; свои хранятся в таблице tgid_trace_config базы города (sql/migrations/
20261029_trace_config.sql): личные видит автор, общие — все (создаёт и правит пользователь с правом
«Справочники и шаблоны»).
"""
from __future__ import annotations

import json
from typing import Any, Optional

from database.network_trace import STOP_KINDS, STOP_TRACE_TYPES, TRACE_TYPES

TABLE = "tgid_trace_config"
NAME_MAX = 200
BUILTIN_PREFIX = "builtin:"

BUILTIN: tuple[dict[str, Any], ...] = (
    {"id": "builtin:upstream", "name": "Путь к источникам",
     "params": {"trace_type": "upstream", "stop_at": []}},
    {"id": "builtin:downstream", "name": "Что останется без питания",
     "params": {"trace_type": "downstream", "stop_at": []}},
    {"id": "builtin:valves", "name": "Участок между задвижками",
     "params": {"trace_type": "connected", "stop_at": ["valves"]}},
    {"id": "builtin:quarter", "name": "Квартальная сеть (до насосных и узлов заданного напора)",
     "params": {"trace_type": "connected", "stop_at": ["pumpstations", "setpress", "sources"]}},
    {"id": "builtin:zone", "name": "Зона сети",
     "params": {"trace_type": "subnetwork", "stop_at": []}},
)


class TraceConfigError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def clean_params(params: Any) -> dict[str, Any]:
    """Проверка настройки: тип из TRACE_TYPES, барьеры из STOP_KINDS (только у «связанных» и «зоны»)."""
    if not isinstance(params, dict):
        raise TraceConfigError(422, "Настройка — объект {trace_type, stop_at}")
    trace_type = params.get("trace_type")
    if trace_type not in TRACE_TYPES:
        raise TraceConfigError(422, f"trace_type — одно из {', '.join(TRACE_TYPES)}")
    stop_at = params.get("stop_at") or []
    if not isinstance(stop_at, list) or any(k not in STOP_KINDS for k in stop_at):
        raise TraceConfigError(422, f"stop_at — список из {', '.join(STOP_KINDS)}")
    if stop_at and trace_type not in STOP_TRACE_TYPES:
        raise TraceConfigError(422, "Барьеры по условию — только у трассировок «связанные» и «зона»")
    return {"trace_type": trace_type, "stop_at": [k for k in STOP_KINDS if k in stop_at]}


def _row(r) -> dict[str, Any]:
    params = r["params"]
    return {"id": str(r["id"]), "name": r["name"], "params": json.loads(params) if isinstance(params, str) else params,
            "author": r["author"], "shared": r["shared"], "builtin": False}


def _builtin() -> list[dict[str, Any]]:
    return [{**c, "author": None, "shared": True, "builtin": True} for c in BUILTIN]


async def _table_ready(conn) -> bool:
    return bool(await conn.fetchval(f"SELECT to_regclass('public.{TABLE}') IS NOT NULL"))


async def list_configs(conn, user: str) -> list[dict[str, Any]]:
    """Встроенные, затем общие и свои (по имени)."""
    out = _builtin()
    if await _table_ready(conn):
        rows = await conn.fetch(
            f"SELECT id, name, params, author, shared FROM {TABLE} WHERE shared OR author = $1 ORDER BY lower(name), id",
            user)
        out += [_row(r) for r in rows]
    return out


async def get_config(conn, config_id: str, user: str) -> dict[str, Any]:
    if config_id.startswith(BUILTIN_PREFIX):
        for c in _builtin():
            if c["id"] == config_id:
                return c
        raise TraceConfigError(404, "Настройка не найдена")
    row = None
    if config_id.isdigit() and await _table_ready(conn):
        row = await conn.fetchrow(
            f"SELECT id, name, params, author, shared FROM {TABLE} WHERE id = $1 AND (shared OR author = $2)",
            int(config_id), user)
    if row is None:
        raise TraceConfigError(404, "Настройка не найдена")
    return _row(row)


def _name(name: Any) -> str:
    text = str(name or "").strip()
    if not text or len(text) > NAME_MAX:
        raise TraceConfigError(422, f"Название — от 1 до {NAME_MAX} символов")
    return text


async def create_config(conn, *, name: str, params: Any, shared: bool, user: str) -> dict[str, Any]:
    if not await _table_ready(conn):
        raise TraceConfigError(503, "Таблица настроек ещё не создана: API доводит базу при запуске")
    row = await conn.fetchrow(
        f"INSERT INTO {TABLE} (name, params, author, shared) VALUES ($1, $2::jsonb, $3, $4) "
        f"RETURNING id, name, params, author, shared",
        _name(name), json.dumps(clean_params(params)), user, bool(shared))
    return _row(row)


async def _own_row(conn, config_id: str, user: str, can_shared: bool):
    """Строка для правки: своя или общая (общие правит пользователь с правом «Справочники»)."""
    if not config_id.isdigit():
        raise TraceConfigError(403 if config_id.startswith(BUILTIN_PREFIX) else 404,
                               "Встроенные настройки не меняются" if config_id.startswith(BUILTIN_PREFIX)
                               else "Настройка не найдена")
    row = await conn.fetchrow(f"SELECT id, author, shared FROM {TABLE} WHERE id = $1", int(config_id))
    if row is None or (not row["shared"] and row["author"] != user):
        raise TraceConfigError(404, "Настройка не найдена")
    if row["author"] != user and not can_shared:
        raise TraceConfigError(403, "Общую настройку правит её автор или пользователь с правом «Справочники»")
    return row


async def update_config(conn, config_id: str, *, name: Optional[str], params: Any, shared: Optional[bool],
                        user: str, can_shared: bool) -> dict[str, Any]:
    await _own_row(conn, config_id, user, can_shared)
    sets, args = ["updated_at = now()"], []
    if name is not None:
        args.append(_name(name))
        sets.append(f"name = ${len(args)}")
    if params is not None:
        args.append(json.dumps(clean_params(params)))
        sets.append(f"params = ${len(args)}::jsonb")
    if shared is not None:
        args.append(bool(shared))
        sets.append(f"shared = ${len(args)}")
    args.append(int(config_id))
    row = await conn.fetchrow(
        f"UPDATE {TABLE} SET {', '.join(sets)} WHERE id = ${len(args)} RETURNING id, name, params, author, shared", *args)
    return _row(row)


async def delete_config(conn, config_id: str, *, user: str, can_shared: bool) -> None:
    await _own_row(conn, config_id, user, can_shared)
    await conn.execute(f"DELETE FROM {TABLE} WHERE id = $1", int(config_id))
