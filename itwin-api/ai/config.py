"""Настройки помощника ИИ из окружения (.env)."""

from __future__ import annotations

import os

DEFAULT_MODEL = "claude-opus-5-5"
# Пересортировка похожих аварий: короткие тексты, ответ за секунды на каждое «Найти» — Sonnet (выбор пользователя)
DEFAULT_RERANK_MODEL = "claude-sonnet-5-5"
# Эффорт по умолчанию: разбор и классификация — medium, объяснения протокола — high (задаёт вызов)
DEFAULT_EFFORT = "medium"
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def api_key() -> str:
    return (os.getenv("ANTHROPIC_API_KEY") or "").strip()


def flag_enabled() -> bool:
    """AI_ENABLED из окружения (без проверки ключа)."""
    return _env_bool("AI_ENABLED", "false")


def enabled() -> bool:
    """Помощник доступен: флаг включён и ключ задан."""
    return flag_enabled() and bool(api_key())


def disabled_reason() -> str | None:
    if not flag_enabled():
        return "Помощник ИИ выключен (AI_ENABLED)"
    if not api_key():
        return "Не задан ключ ANTHROPIC_API_KEY"
    return None


def model() -> str:
    return (os.getenv("AI_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL


def rerank_model() -> str:
    return (os.getenv("AI_RERANK_MODEL") or DEFAULT_RERANK_MODEL).strip() or DEFAULT_RERANK_MODEL


def timeout_s() -> float:
    return float(_env_int("AI_TIMEOUT_S", 120))


def max_input_chars() -> int:
    """Предел длины пользовательской части запроса (символов) — защита от случайной отправки дампов."""
    return _env_int("AI_MAX_INPUT_CHARS", 60_000)


def max_output_tokens() -> int:
    return _env_int("AI_MAX_OUTPUT_TOKENS", 8_000)
