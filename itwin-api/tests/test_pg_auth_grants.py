"""Матрица прав sql/pg_auth/03_grants.sql покрывает все таблицы, в которые пишет API.

Права закрыты по умолчанию (DB_ROLE_SWITCH): таблица, забытая в 03_grants.sql, даст пользователю 403
(«ваша роль не может изменять …»). Так было с каскадом удаления шурфовки (vidy_elementov_for_shurfy).
Тест без БД: разбирает списки таблиц в SQL и сверяет с реестрами кода.
"""

import re
from pathlib import Path

from auth import MUTABLE_TABLES
from database.dictionaries import DICTIONARIES
from database.electrical_binding import ALLOWED_TABLES as ELECTRICAL_TABLES
from database.journal_specs import JOURNALS

SQL = (Path(__file__).resolve().parents[1] / "sql" / "pg_auth" / "03_grants.sql").read_text(encoding="utf-8")

# Таблицы, покрытые шаблоном/выборкой в 03_grants.sql (не перечислены явно)
CALC_PATTERNS = (re.compile(r".*_out$"), re.compile(r"^heatloses"), re.compile(r"^heatlosses"),
                 re.compile(r"^losesbyfilling"), re.compile(r"^heatpipesectionsharness"))


def _granted_tables() -> set[str]:
    names = set(re.findall(r"'([a-z_][a-z0-9_]*)'", SQL))
    return {n for n in names if n not in {"passwords", "password"}}


def _covered(table: str, granted: set[str]) -> bool:
    t = table.lower()
    return t in granted or any(p.match(t) for p in CALC_PATTERNS) or t in {"calculation", "temp_line", "temp_node"}


def _journal_tables() -> set[str]:
    out = set()
    for spec in JOURNALS.values():
        out.add(spec.table)
        for attr in ("documents_table", "deployed_table"):
            if getattr(spec, attr, None):
                out.add(getattr(spec, attr))
        for table, _col in tuple(spec.cascade) + tuple(spec.detach):
            out.add(table)
    return out


def test_journal_tables_and_cascades_are_granted():
    granted = _granted_tables()
    missing = sorted(t for t in _journal_tables() if not _covered(t, granted))
    assert not missing, f"нет в 03_grants.sql: {missing}"


def test_mutable_dictionary_and_electrical_tables_are_granted():
    granted = _granted_tables()
    tables = set(MUTABLE_TABLES) | {d.table for d in DICTIONARIES.values()} | set(ELECTRICAL_TABLES)
    missing = sorted(t for t in tables if not _covered(t, granted))
    assert not missing, f"нет в 03_grants.sql: {missing}"
