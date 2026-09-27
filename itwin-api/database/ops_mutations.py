"""Field allow-lists for ops journals in the legacy generic CRUD (/update, /create).

Источник правды — database/journal_specs.py (там же типы и проверки). Новый веб пишет
через /api/v1/journals/{journal}; этот фильтр оставлен для старых клиентов и принимает
как ключи журнала (detected_at), так и реальные имена колонок (data_osmotra).
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from database.journal_specs import JOURNALS

OPS_MUTABLE_FIELDS: dict[str, frozenset[str]] = {
    spec.table: frozenset(f.column for f in spec.fields.values()) for spec in JOURNALS.values()
}
_ALIASES: dict[str, dict[str, str]] = {
    spec.table: {key: f.column for key, f in spec.fields.items()} for spec in JOURNALS.values()
}


def filter_ops_fields(table: str, fields: dict[str, Any]) -> dict[str, Any]:
    key = table.lower()
    allow = OPS_MUTABLE_FIELDS.get(key)
    if allow is None:
        return fields
    aliases = _ALIASES[key]
    allow_lower = {f.lower(): f for f in allow}
    normalized: dict[str, Any] = {}
    for name, value in fields.items():
        canon = aliases.get(name) or allow_lower.get(str(name).lower())
        if canon:
            normalized[canon] = value
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail=f"No writable fields for {table}. Allowed sample: {sorted(allow)[:12]}",
        )
    return normalized
