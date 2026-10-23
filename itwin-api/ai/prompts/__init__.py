"""Системные промпты — файлами рядом (ai/prompts/<name>.md), чтобы править без кода.

Текст промпта стабилен между вызовами (кешируемый префикс): переменные данные
(протокол, записи) всегда идут в пользовательскую часть, а не сюда.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).resolve().parent


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    path = _DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Нет промпта ai/prompts/{name}.md")
    base = (_DIR / "tgid_base.md").read_text(encoding="utf-8").strip()
    body = path.read_text(encoding="utf-8").strip()
    return f"{base}\n\n{body}" if name != "tgid_base" else base
