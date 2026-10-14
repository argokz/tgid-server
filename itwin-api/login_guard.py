"""Защита входа от перебора паролей: после серии неудач логин с этого адреса временно закрыт.

Счётчики в памяти процесса (у каждого воркера uvicorn свои) — для перебора через интернет этого
достаточно: на 5 попыток за 10 минут на пару «адрес + логин» и 30 — на адрес.
"""

from __future__ import annotations

import os
import time
from collections import deque
from typing import Optional

from fastapi import HTTPException, Request


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def window_seconds() -> int:
    return _env_int("LOGIN_FAIL_WINDOW_SECONDS", 600)


def max_per_login() -> int:
    return _env_int("LOGIN_MAX_FAILS", 5)


def max_per_ip() -> int:
    return _env_int("LOGIN_MAX_FAILS_PER_IP", 30)


_fails: dict[tuple[str, str], deque] = {}


def client_ip(request: Optional[Request]) -> str:
    """Адрес клиента за Cloudflare и nginx (API слушает только 127.0.0.1 — заголовки ставит nginx)."""
    if request is None:
        return "-"
    for header in ("cf-connecting-ip", "x-real-ip"):
        value = (request.headers.get(header) or "").strip()
        if value:
            return value
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "-"


def _recent(key: tuple[str, str], now: float) -> deque:
    q = _fails.setdefault(key, deque())
    while q and now - q[0] > window_seconds():
        q.popleft()
    return q


def check(ip: str, login: str) -> None:
    """429, если с адреса уже слишком много неудачных попыток."""
    now = time.monotonic()
    for key, limit in (((ip, login.casefold()), max_per_login()), ((ip, ""), max_per_ip())):
        q = _recent(key, now)
        if len(q) >= limit:
            wait = max(1, int(window_seconds() - (now - q[0])) // 60 + 1)
            raise HTTPException(
                status_code=429,
                detail=f"Слишком много неудачных попыток входа. Повторите через {wait} мин.",
            )


def record_failure(ip: str, login: str) -> None:
    now = time.monotonic()
    for key in ((ip, login.casefold()), (ip, "")):
        _recent(key, now).append(now)
    if len(_fails) > 10_000:  # не копить память на переборе с множества адресов
        for key in [k for k, q in _fails.items() if not q or now - q[-1] > window_seconds()]:
            _fails.pop(key, None)


def record_success(ip: str, login: str) -> None:
    _fails.pop((ip, login.casefold()), None)


def reset() -> None:
    _fails.clear()
