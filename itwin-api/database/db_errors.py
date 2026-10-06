"""Ошибки прав PostgreSQL (SQLSTATE 42501) → понятный текст для пользователя (HTTP 403).

Источники: GRANT (нет права на таблицу), триггер территории tgid_auth.enforce_territory
(«Объект вне вашей территории: фрагмент N»), RLS WITH CHECK (новая строка вне территории).
Многие роутеры оборачивают исключения в HTTPException(500, str(e)) — такие ответы распознаются
по тексту сообщения PostgreSQL (русская и английская локали сервера).
"""

from __future__ import annotations

import re
from typing import Optional

_TERRITORY_RE = re.compile(r"вне вашей территории[^\n]*", re.IGNORECASE)
_TABLE_RE = re.compile(
    r"(?:нет доступа к (?:таблице|отношению|последовательности|схеме|функции)|"
    r"permission denied for (?:table|relation|sequence|schema|function))\s+\"?([\w.]+)\"?",
    re.IGNORECASE,
)
_RLS_RE = re.compile(r"(?:row-level security|защиты на уровне строк)[^\n]*?(?:table|таблицы|отношения)\s+\"?([\w.]+)\"?",
                     re.IGNORECASE)
_ADMIN_RE = re.compile(r"Требуется роль администратора|Нельзя (?:снять с себя|заблокировать себя)[^\n]*")


def privilege_error_detail(message: str) -> Optional[str]:
    """Текст для пользователя, если message — отказ в правах PostgreSQL; иначе None."""
    if not message:
        return None
    m = _TERRITORY_RE.search(message)
    if m:
        return "Объект " + m.group(0).strip().rstrip(".")
    m = _ADMIN_RE.search(message)
    if m:
        return m.group(0)
    m = _TABLE_RE.search(message)
    if m:
        return f"Недостаточно прав: ваша роль не может изменять «{m.group(1)}»"
    m = _RLS_RE.search(message)
    if m:
        return f"Недостаточно прав: запись в «{m.group(1)}» вне вашей территории"
    return None
