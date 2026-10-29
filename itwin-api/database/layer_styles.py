"""Сохранённые стили тематических карт (Smart Mapping; JSON-стиль слоя по образцу Felt FSL).

Стиль — тема (database/thematic.py), способ классификации, границы классов и цвета, толщина и
прозрачность линий. Хранится в таблице tgid_layer_style базы города (sql/migrations/
20261029_layer_style.sql): личные видит автор, общие — все (создаёт и правит пользователь с правом
«Справочники и шаблоны»). revision растёт при каждом сохранении — веб видит, что стиль поменялся.
"""
from __future__ import annotations

import json
import re
from typing import Any, Optional

from database.thematic import THEMES

TABLE = "tgid_layer_style"
NAME_MAX = 200
STYLE_FORMAT = 1
METHODS = ("equal", "quantile", "jenks", "manual", "unique")
MIN_CLASSES, MAX_CLASSES = 2, 9
MAX_CATEGORIES = 50
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_COLUMNS = "id, name, style, revision, author, shared, updated_at"


class LayerStyleError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _color(value: Any, what: str) -> str:
    if not isinstance(value, str) or not _HEX.match(value):
        raise LayerStyleError(422, f"{what} — цвет вида #rrggbb")
    return value.lower()


def _number(value: Any, what: str, lo: float, hi: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise LayerStyleError(422, f"{what} — число от {lo:g} до {hi:g}")
    return float(value)


def clean_style(style: Any) -> dict[str, Any]:
    """Проверка стиля по белому списку полей; лишние поля отбрасываются."""
    if not isinstance(style, dict):
        raise LayerStyleError(422, "Стиль — объект JSON")
    theme = THEMES.get(style.get("theme"))
    if theme is None:
        raise LayerStyleError(422, f"theme — одна из: {', '.join(THEMES)}")
    method = style.get("method")
    if method not in METHODS:
        raise LayerStyleError(422, f"method — одно из: {', '.join(METHODS)}")
    if (method == "unique") != (theme.kind == "category"):
        raise LayerStyleError(422, "Уникальные значения — только у тем-справочников, классы — только у числовых")
    out: dict[str, Any] = {
        "format": STYLE_FORMAT, "theme": theme.key, "method": method,
        "width": _number(style.get("width", 3), "width", 1, 12),
        "opacity": _number(style.get("opacity", 0.9), "opacity", 0.1, 1),
        "show_nulls": bool(style.get("show_nulls", True)),
        "null_color": _color(style.get("null_color", "#9e9e9e"), "null_color"),
    }
    palette = style.get("palette")
    if palette is not None:
        if not isinstance(palette, str) or len(palette) > 40:
            raise LayerStyleError(422, "palette — название до 40 символов")
        out["palette"] = palette
    if method == "unique":
        cats = style.get("categories") or []
        if not isinstance(cats, list) or not 1 <= len(cats) <= MAX_CATEGORIES:
            raise LayerStyleError(422, f"categories — от 1 до {MAX_CATEGORIES} значений")
        seen: set[int] = set()
        out["categories"] = []
        for c in cats:
            value = c.get("value") if isinstance(c, dict) else None
            if isinstance(value, bool) or not isinstance(value, int) or value in seen:
                raise LayerStyleError(422, "categories — {value: целое без повторов, color}")
            seen.add(value)
            out["categories"].append({"value": value, "color": _color(c.get("color"), "Цвет категории")})
        return out
    classes = style.get("classes")
    if isinstance(classes, bool) or not isinstance(classes, int) or not MIN_CLASSES <= classes <= MAX_CLASSES:
        raise LayerStyleError(422, f"classes — целое от {MIN_CLASSES} до {MAX_CLASSES}")
    out["classes"] = classes
    colors = style.get("colors")
    if not isinstance(colors, list) or len(colors) != classes:
        raise LayerStyleError(422, "colors — по цвету на класс")
    out["colors"] = [_color(c, "Цвет класса") for c in colors]
    breaks = style.get("breaks")
    if method == "manual" or breaks is not None:
        # границы между классами: на одну меньше, чем классов, по возрастанию
        if not isinstance(breaks, list) or len(breaks) != classes - 1:
            raise LayerStyleError(422, "breaks — границы между классами (на одну меньше числа классов)")
        values = [_number(b, "Граница класса", -1e9, 1e9) for b in breaks]
        if any(a >= b for a, b in zip(values, values[1:])):
            raise LayerStyleError(422, "breaks — строго по возрастанию")
        out["breaks"] = values
    return out


def _row(r) -> dict[str, Any]:
    style = r["style"]
    return {"id": str(r["id"]), "name": r["name"], "style": json.loads(style) if isinstance(style, str) else style,
            "revision": r["revision"], "author": r["author"], "shared": r["shared"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None}


async def _table_ready(conn) -> bool:
    return bool(await conn.fetchval(f"SELECT to_regclass('public.{TABLE}') IS NOT NULL"))


async def list_styles(conn, user: str) -> list[dict[str, Any]]:
    if not await _table_ready(conn):
        return []
    rows = await conn.fetch(
        f"SELECT {_COLUMNS} FROM {TABLE} WHERE shared OR author = $1 ORDER BY lower(name), id", user)
    return [_row(r) for r in rows]


def _name(name: Any) -> str:
    text = str(name or "").strip()
    if not text or len(text) > NAME_MAX:
        raise LayerStyleError(422, f"Название — от 1 до {NAME_MAX} символов")
    return text


async def create_style(conn, *, name: str, style: Any, shared: bool, user: str) -> dict[str, Any]:
    if not await _table_ready(conn):
        raise LayerStyleError(503, "Таблица стилей ещё не создана: API доводит базу при запуске")
    row = await conn.fetchrow(
        f"INSERT INTO {TABLE} (name, style, author, shared) VALUES ($1, $2::jsonb, $3, $4) RETURNING {_COLUMNS}",
        _name(name), json.dumps(clean_style(style)), user, bool(shared))
    return _row(row)


async def _own_row(conn, style_id: str, user: str, can_shared: bool):
    """Строка для правки: своя или общая (общие правит пользователь с правом «Справочники»)."""
    row = None
    if style_id.isdigit() and await _table_ready(conn):
        row = await conn.fetchrow(f"SELECT id, author, shared, revision FROM {TABLE} WHERE id = $1", int(style_id))
    if row is None or (not row["shared"] and row["author"] != user):
        raise LayerStyleError(404, "Стиль не найден")
    if row["author"] != user and not can_shared:
        raise LayerStyleError(403, "Общий стиль правит его автор или пользователь с правом «Справочники»")
    return row


async def update_style(conn, style_id: str, *, name: Optional[str], style: Any, shared: Optional[bool],
                       revision: Optional[int], user: str, can_shared: bool) -> dict[str, Any]:
    """revision — версия, которую правили: стиль успели сохранить другим — 409."""
    row = await _own_row(conn, style_id, user, can_shared)
    if revision is not None and revision != row["revision"]:
        raise LayerStyleError(409, f"Стиль уже изменён (версия {row['revision']}) — откройте его заново")
    sets, args = ["updated_at = now()", "revision = revision + 1"], []
    if name is not None:
        args.append(_name(name))
        sets.append(f"name = ${len(args)}")
    if style is not None:
        args.append(json.dumps(clean_style(style)))
        sets.append(f"style = ${len(args)}::jsonb")
    if shared is not None:
        args.append(bool(shared))
        sets.append(f"shared = ${len(args)}")
    args.append(int(style_id))
    where = f"id = ${len(args)}"
    if revision is not None:
        args.append(revision)
        where += f" AND revision = ${len(args)}"
    updated = await conn.fetchrow(
        f"UPDATE {TABLE} SET {', '.join(sets)} WHERE {where} RETURNING {_COLUMNS}", *args)
    if updated is None:
        raise LayerStyleError(409, "Стиль уже изменён — откройте его заново")
    return _row(updated)


async def delete_style(conn, style_id: str, *, user: str, can_shared: bool) -> None:
    await _own_row(conn, style_id, user, can_shared)
    await conn.execute(f"DELETE FROM {TABLE} WHERE id = $1", int(style_id))
