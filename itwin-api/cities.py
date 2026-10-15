"""Города (базы ТГИД) и доступ к ним пользователей UsersDB.

Каждый город — свой экземпляр API со своей базой (DB_NAME), а база пользователей (UsersDB) общая.
Администратор задаёт пользователю список городов (users.cities); пусто — все города, в том числе
добавленные позже. Вход и каждый запрос в API города, которого нет в списке, отклоняются.

  TGID_CITIES="almaty:Алматы,astana:Астана"  — справочник: код:название[:путь веба], путь по умолчанию /tgid/<код>/
  TGID_CITY="astana"                         — код города этого API; без него — из DB_NAME
                                               (almatygid → almaty, astanagid_2026_09_22 → astana)
Мастер-учётке доступны все города. Пользователи PostgreSQL (AUTH_BACKEND=pg) городом не ограничиваются:
им доступ к базе города даёт сам PostgreSQL (GRANT CONNECT).
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Optional

DEFAULT_CITIES = "almaty:Алматы,astana:Астана"
_CODE_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")


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
    return m.group(1) if m else db


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
