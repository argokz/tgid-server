"""Города (базы ТГИД) и доступ к ним пользователей UsersDB.

Каждый город — свой экземпляр API со своей базой (DB_NAME), а база пользователей (UsersDB) общая.
Администратор задаёт пользователю список городов (users.cities); пусто — все города, в том числе
добавленные позже. Вход и каждый запрос в API города, которого нет в списке, отклоняются.

  TGID_CITIES="almaty:Алматы,astana:Астана,shatura:Шатура" — справочник: код:название[:путь веба], путь по умолчанию /tgid/<код>/
  TGID_CITY="astana"                         — код города этого API; без него — из DB_NAME
                                               (almatygid → almaty, astanagid_2026_09_22 → astana, shatura → shatura, tarazgid → taraz)
Мастер-учётке доступны все города. Пользователи PostgreSQL (AUTH_BACKEND=pg) городом не ограничиваются:
им доступ к базе города даёт сам PostgreSQL (GRANT CONNECT).
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Optional

DEFAULT_CITIES = "almaty:Алматы,astana:Астана,shatura:Шатура,taraz:Тараз,aktobe:Актобе,shymkent:Шымкент,karaganda:Караганда,ekibastuz:Экибастуз,atbasar:Атбасар,kokshetau:Кокшетау,shakhtinsk:Шахтинск"
_CODE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")
# база названа иначе, чем код города: shahtinskgid → shakhtinsk
_DB_CITY_ALIASES = {"shahtinsk": "shakhtinsk"}


class CityError(ValueError):
    pass


def cities_catalog() -> list[dict[str, str]]:
    """Справочник городов: [{code, label, path}] в порядке TGID_CITIES."""
    raw = os.getenv("TGID_CITIES", "").strip() or DEFAULT_CITIES
    items: list[dict[str, str]] = []
    seen: set[str] = set()
    for part in raw.split(","):
        bits = [b.strip() for b in part.split(":", 2)]
        code = bits[0].lower()
        if not _CODE_RE.match(code) or code in seen:
            continue
        seen.add(code)
        label = bits[1] if len(bits) > 1 and bits[1] else code
        path = bits[2] if len(bits) > 2 and bits[2] else f"/tgid/{code}/"
        items.append({"code": code, "label": label, "path": path})
    return items


def city_codes() -> list[str]:
    return [c["code"] for c in cities_catalog()]


def current_city() -> str:
    """Код города этого API: TGID_CITY, иначе по имени базы (almatygid_copy → almaty)."""
    explicit = os.getenv("TGID_CITY", "").strip().lower()
    if explicit:
        return explicit
    db = os.getenv("DB_NAME", "").strip().lower()
    m = re.match(r"^([a-z]+?)gid", db)
    code = m.group(1) if m else db
    return _DB_CITY_ALIASES.get(code, code)


def city_label(code: Optional[str] = None) -> str:
    code = current_city() if code is None else code
    for c in cities_catalog():
        if c["code"] == code:
            return c["label"]
    return code


def parse_stored(value: Optional[str]) -> Optional[list[str]]:
    """users.cities → список кодов; NULL/пусто — все города."""
    if value is None or not str(value).strip():
        return None
    return [c for c in (p.strip().lower() for p in str(value).split(",")) if c]


def normalize(codes: Optional[Iterable[str]]) -> Optional[list[str]]:
    """Проверка списка от администратора: None — все города; иначе известные коды в порядке справочника."""
    if codes is None:
        return None
    wanted = {str(c).strip().lower() for c in codes if str(c).strip()}
    known = city_codes()
    unknown = sorted(wanted - set(known))
    if unknown:
        raise CityError(f"Неизвестный город: {', '.join(unknown)}")
    if not wanted:
        raise CityError("Выберите хотя бы один город или «все города»")
    return [c for c in known if c in wanted]


def to_stored(codes: Optional[list[str]]) -> Optional[str]:
    return ",".join(codes) if codes else None


def allowed(cities: Optional[list[str]], city: Optional[str] = None) -> bool:
    """Доступен ли город пользователю. Город API не из справочника (стенд, тесты) — без ограничения."""
    if cities is None:
        return True
    city = current_city() if city is None else city
    if city not in city_codes():
        return True
    return city in cities


def visible_catalog(cities: Optional[list[str]]) -> list[dict[str, str]]:
    """Города, куда пользователь может перейти (для меню и личного кабинета)."""
    catalog = cities_catalog()
    return catalog if cities is None else [c for c in catalog if c["code"] in cities]


def denied_detail(city: Optional[str] = None) -> str:
    return f"Нет доступа к городу «{city_label(city)}». Доступ выдаёт администратор"


# --- GeoServer: город по рабочей области ---
# GeoServer общий для всех городов; рабочая область города начинается с его кода
# (AlmatyGIS, Almaty1, Almaty2 → almaty; AstanaGIS, Astana1, Astana2 → astana; ShaturaGIS → shatura;
# TarazGIS, AktobeGIS, ShymkentGIS — по коду). Рабочие области других
# проектов (не начинаются с кода города) городом не ограничиваются — нужен только вход.
# Сервисы без рабочей области в пути (/geoserver/wms, /geoserver/gwc/...): город — по слоям в параметрах.
GEOSERVER_GLOBAL_SEGMENTS = frozenset({
    "gwc", "wms", "wfs", "wcs", "wps", "ows", "wmts", "tms", "kml", "styles", "schemas", "i18n",
    "openlayers", "openlayers3", "pdf", "www", "web", "rest", "index.html",
})
# Тайлы martin опубликованы под /geoserver/tiles/ — там действует cookie сессии GeoServer (Path=/geoserver)
MARTIN_SEGMENT = "tiles"
MARTIN_GLOBAL_SEGMENTS = frozenset({"catalog", "health", "metrics", "_"})
_LAYER_PARAMS = frozenset({"layer", "layers", "typename", "typenames", "query_layers", "coverageid", "identifier"})
_READ_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def workspace_city(workspace: str) -> Optional[str]:
    """Город рабочей области GeoServer по префиксу имени; None — не город (другой проект)."""
    ws = (workspace or "").strip().lower()
    for code in sorted(city_codes(), key=len, reverse=True):
        if ws.startswith(code):
            return code
    return None


def geoserver_request_cities(uri: str) -> tuple[set[str], bool]:
    """Города, данные которых затрагивает запрос к GeoServer, и признак общего сервиса (без рабочей области)."""
    from urllib.parse import parse_qsl, unquote, urlsplit

    parts = urlsplit(uri or "")
    segments = [unquote(s) for s in parts.path.split("/") if s]
    if segments and segments[0].lower() == "geoserver":
        segments = segments[1:]
    found: set[str] = set()
    if segments and segments[0].lower() == MARTIN_SEGMENT:
        # martin (/geoserver/tiles/almaty_uzel/{z}/{x}/{y}): город — по префиксу источника, как у рабочей области;
        # каталог источников (/geoserver/tiles/catalog) — общий
        is_global = len(segments) < 2 or segments[1].lower() in MARTIN_GLOBAL_SEGMENTS
        if not is_global:
            found.add(segments[1])
        return {c for c in (workspace_city(ws) for ws in found) if c}, is_global
    is_global = not segments or segments[0].lower() in GEOSERVER_GLOBAL_SEGMENTS
    if not is_global:
        found.add(segments[0])
    # слой в пути: TMS /gwc/service/tms/1.0.0/AlmatyGIS:heatpipesections@EPSG:900913@pbf/...
    for seg in segments:
        if ":" in seg:
            found.add(seg.split(":", 1)[0])
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in _LAYER_PARAMS:
            for item in value.split(","):
                if ":" in item:
                    found.add(item.split(":", 1)[0])
    cities = {c for c in (workspace_city(ws) for ws in found) if c}
    return cities, is_global


def geoserver_denied(user_cities: Optional[Iterable[str]], uri: str, method: str = "GET") -> Optional[str]:
    """Причина отказа в запросе к GeoServer (None — можно). user_cities None — все города."""
    if user_cities is None:
        return None
    allowed_set = set(user_cities)
    needed, is_global = geoserver_request_cities(uri)
    missing = sorted(needed - allowed_set)
    if missing:
        return f"Нет доступа к данным города «{city_label(missing[0])}»"
    # тело POST (WFS-запрос с typeName внутри XML) nginx не видит: общим сервисам — только чтение по адресу
    if is_global and (method or "GET").upper() not in _READ_METHODS:
        return "Запросы с телом к общим сервисам GeoServer — только при доступе ко всем городам"
    return None
