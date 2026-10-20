"""SRID геометрии сети (nodes.shape, linesobj.shape) в базе города.

Местная метрическая система координат у городов под разными номерами: в Алматы и Шатуре колонки
shape — SRID 9998, в Астане — 9995 (9998 там описан той же системой, но колонки объявлены 9995,
и PostGIS не даёт записать в них геометрию с другим SRID: «Geometry SRID (9998) does not match
column SRID (9995)», а сравнение разных SRID — «Operation on mixed SRID geometries»).

Один процесс API работает с одной базой, поэтому SRID читается один раз при открытии пула
(Find_SRID) и подставляется во все запросы правки сети вместо прежнего жёсткого 9998.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

DEFAULT_NET_SRID = 9998

_net_srid = DEFAULT_NET_SRID
# есть ли linesobj.internalnodeid (в Шатуре конвертер её не создаёт; city_schema добавляет)
_lines_inner = True


def line_inner_sql(alias: str = "l") -> str:
    """SQL «схема участка» (узел-владелец внутренней схемы, NULL — основная сеть).

    Без колонки linesobj.internalnodeid — по начальному узлу участка, как её и заполняют
    (sql/shatura/02_linesobj_internalnodeid.sql): привязка и проверки трассы работают и в базе,
    которую ещё не довели.
    """
    if _lines_inner:
        return f"{alias}.internalnodeid"
    return f"(SELECT nn.internalnodeid FROM nodes nn WHERE nn.id = {alias}.nodeid1)"


def lines_have_inner() -> bool:
    """Есть ли колонка linesobj.internalnodeid (писать её в новые участки)."""
    return _lines_inner


def set_lines_inner(present: bool) -> None:
    global _lines_inner
    _lines_inner = bool(present)


def net_srid() -> int:
    """SRID колонок shape сети в текущей базе (до чтения из базы — 9998)."""
    return _net_srid


def set_net_srid(srid: int) -> None:
    global _net_srid
    _net_srid = int(srid)


async def load_net_srid(conn) -> int:
    """Прочитать SRID nodes.shape из geometry_columns; не вышло — остаётся прежний."""
    try:
        srid = await conn.fetchval("SELECT Find_SRID('public', 'nodes', 'shape')")
    except Exception as e:  # нет PostGIS/таблицы — база не городская, правки сети в ней нет
        logger.warning("SRID сети не прочитан (Find_SRID nodes.shape): %s — остаётся %s", e, _net_srid)
        return _net_srid
    if srid and int(srid) > 0:
        set_net_srid(int(srid))
        logger.info("SRID геометрии сети: %s", _net_srid)
    try:
        set_lines_inner(await conn.fetchval(
            "SELECT exists (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public'"
            " AND table_name = 'linesobj' AND column_name = 'internalnodeid')"))
        if not _lines_inner:
            logger.warning("В linesobj нет internalnodeid — схема участка берётся по начальному узлу")
    except Exception as e:  # noqa: BLE001
        logger.warning("Колонки linesobj не прочитаны: %s", e)
    return _net_srid
