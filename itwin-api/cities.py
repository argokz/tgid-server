"""Города (базы ТГИД) и доступ к ним пользователей UsersDB.

Каждый город — свой экземпляр API со своей базой (DB_NAME), а база пользователей (UsersDB) общая.
Администратор задаёт пользователю список городов (users.cities); пусто — все города, в том числе
добавленные позже. Вход и каждый запрос в API города, которого нет в списке, отклоняются.

  TGID_CITIES="almaty:Алматы,astana:Астана,shatura:Шатура" — справочник: код:название[:путь веба], путь по умолчанию /tgid/<код>/
  TGID_CITY="astana"                         — код города этого API; без него — из DB_NAME
                                               (almatygid → almaty, astanagid_2026_09_22 → astana, shatura → shatura, tarazgid → taraz)
  TGID_CITY_DBS="almaty=almatygid,astana=astanagid_2026_09_22" — один API на несколько городов: город запроса —
                                               по префиксу пути /city/<код>/ (city_context.py), база — из этого списка
Мастер-учётке доступны все города. Пользователи PostgreSQL (AUTH_BACKEND=pg) городом не ограничиваются:
им доступ к базе города даёт сам PostgreSQL (GRANT CONNECT).
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterable, Iterator, Optional

DEFAULT_CITIES = "almaty:Алматы,astana:Астана,shatura:Шатура,taraz:Тараз,aktobe:Актобе,shymkent:Шымкент,karaganda:Караганда,ekibastuz:Экибастуз,atbasar:Атбасар,kokshetau:Кокшетау,shakhtinsk:Шахтинск"
_CODE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")
_DB_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")
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


# Город запроса или задачи в API на несколько городов (TGID_CITY_DBS); задаёт city_context.py и воркер
_city_var: ContextVar[Optional[str]] = ContextVar("tgid_city", default=None)


def city_databases() -> dict[str, str]:
    """TGID_CITY_DBS → {код: база}; пусто — API одного города (DB_NAME)."""
    raw = os.getenv("TGID_CITY_DBS", "").strip()
    result: dict[str, str] = {}
    for part in raw.split(","):
        code, sep, db = (b.strip() for b in part.partition("="))
        code = code.lower()
        if not sep or not _CODE_RE.match(code) or not _DB_RE.match(db):
            if part.strip():
                raise CityError(f"TGID_CITY_DBS: неверный элемент «{part.strip()}» (нужно код=база)")
            continue
        if code in result:
            raise CityError(f"TGID_CITY_DBS: город {code} указан дважды")
        result[code] = db
    return result


def multi_city() -> bool:
    return bool(os.getenv("TGID_CITY_DBS", "").strip())


def city_db_name(code: Optional[str] = None) -> str:
    """База города (по умолчанию — города запроса); у API одного города — DB_NAME."""
    if not multi_city():
        return os.getenv("DB_NAME", "")
    code = current_city() if code is None else code
    db = city_databases().get(code)
    if not db:
        raise CityError(f"Город «{code or '—'}» не обслуживается этим API")
    return db


def cache_key() -> str:
    """Ключ кешей процесса, построенных по базе: город запроса в API на несколько городов, иначе ''."""
    return current_city() if multi_city() else ""


# Очереди Celery API на несколько городов: tgid.<город> (FILE_JOBS_QUEUE и т. п. — <очередь>.<город>).
# Воркер слушает очереди своих городов: общий — все, отдельный для крупного города — одну.
TASK_QUEUE = "tgid"


def task_queue(explicit: Optional[str] = None) -> Optional[str]:
    """Очередь задачи Celery: у API одного города — заданная (None — по умолчанию), иначе — очередь города."""
    if not multi_city():
        return explicit
    city = current_city()
    if not city:
        raise CityError("Задача вне запроса города: не определить очередь")
    return f"{explicit or TASK_QUEUE}.{city}"


def city_task_queues() -> list[str]:
    """Очереди задач всех городов TGID_CITY_DBS (воркер, метрики)."""
    return [f"{TASK_QUEUE}.{code}" for code in city_databases()]


@contextmanager
def use_city(code: str) -> Iterator[str]:
    """Выполнить блок от имени города (фоновые задачи, воркер, доводка базы)."""
    token = _city_var.set(code)
    try:
        yield code
    finally:
        _city_var.reset(token)


def set_request_city(code: Optional[str]) -> None:
    """Город текущей задачи asyncio (middleware и сигналы воркера — до обработчика, в той же задаче/потоке)."""
    _city_var.set(code)


def current_city() -> str:
    """Код города: города запроса (API на несколько городов), иначе TGID_CITY или по имени базы (almatygid_copy → almaty)."""
    scoped = _city_var.get()
    if scoped:
        return scoped
    if multi_city():
        return ""  # вне запроса города нет: молча брать DB_NAME значило бы читать чужую базу
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
    """Доступен ли город пользователю. Город API одного города не из справочника (стенд, тесты) — без ограничения."""
    if cities is None:
        return True
    city = current_city() if city is None else city
    if city not in city_codes():
        # API на несколько городов: город вне справочника открыт только пользователям «все города»
        return not multi_city()
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
