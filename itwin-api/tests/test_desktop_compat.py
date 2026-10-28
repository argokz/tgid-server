"""Совместимость с десктопом gid8: SQL веба не ломает то, что создаёт и читает десктоп.

Десктоп и веб работают в одной базе города одновременно. Десктоп при переконвертации пересоздаёт
базу целиком, веб возвращает свои добавки сам (database/city_schema.py). Поэтому правило одно:
веб может удалять и менять только СВОИ объекты (таблицы, которые создаёт его SQL, и схему
tgid_auth), а к таблицам десктопа — только добавлять (индекс, колонку без NOT NULL, функцию).
Всё остальное — только из списка ALLOWED с объяснением, почему десктоп это не заденет.
Подробно: docs/desktop-compat.md.
"""
import re
import sys
from pathlib import Path

import pytest

from database import city_schema

SQL_ROOT = Path(__file__).resolve().parent.parent / "sql"
# Скрипты, которые меняют базу города (reports/ и admissibility/ — только выборки)
SCANNED = ("migrations", "fixes", "astana", "shatura", "pg_auth")
WEB_SCHEMAS = ("tgid_auth",)

# (файл относительно sql/, вид, таблица) → почему это безопасно для десктопа
ALLOWED: dict[tuple[str, str, str], str] = {
    ("shatura/02_linesobj_internalnodeid.sql", "trigger", "linesobj"):
        "заполняет internalnodeid, которого конвертер Шатуры не создаёт; запись десктопа не отклоняет",
    ("shatura/02_linesobj_internalnodeid.sql", "update", "linesobj"):
        "заполняет колонку internalnodeid, которую добавил веб; данные десктопа не меняет",
    ("astana/01_srid_9998.sql", "update", "spatial_ref_sys"):
        "конвертер описал SRID 9998 системой Алматы; веб пишет систему Астаны, координаты в таблицах те же",
    ("shatura/01_srid_9998.sql", "update", "spatial_ref_sys"):
        "конвертер не описал местную систему Шатуры; веб дописывает её, координаты в таблицах те же",
    ("pg_auth/02_auth_schema.sql", "insert", "audit_log"):
        "запись о действии в журнал правок десктопа (только добавление строки)",
    ("fixes/20260927_nodes_without_externalcode.sql", "update", "nodes"):
        "разовая ручная починка узлов, созданных вебом до 27.09; city_schema её не применяет",
    ("pg_auth/04_rls.sql", "trigger", "%i"):
        "триггер территории tgid_territory: суперпользователь (десктоп ходит ролью tgid/postgres) "
        "проходит без проверок через tgid_auth.is_admin()",
    ("pg_auth/04_rls.sql", "alter", "%i"):
        "ENABLE ROW LEVEL SECURITY без FORCE: владелец и суперпользователь (десктоп) не ограничены",
    ("pg_auth/04_rls.sql", "alter", "audit_log"):
        "RLS на журнале правок десктопа без FORCE: десктоп-суперпользователь не ограничен",
    ("pg_auth/99_rollback.sql", "alter", "%i"):
        "откат RLS (DISABLE ROW LEVEL SECURITY) — возвращает таблицы десктопа к исходному виду",
}

_COMMENT_RE = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)
_NAME = r'((?:"?[\w%]+"?\.)?"?[\w%]+"?)'
_STATEMENTS = {
    "drop_table": re.compile(r"\bdrop\s+table\s+(?:if\s+exists\s+)?" + _NAME, re.I),
    "truncate": re.compile(r"\btruncate\s+(?:table\s+)?(?:only\s+)?" + _NAME, re.I),
    "trigger": re.compile(r"\bcreate\s+(?:or\s+replace\s+)?trigger\s+\w+.*?\bon\s+" + _NAME, re.I | re.S),
    "delete": re.compile(r"\bdelete\s+from\s+(?:only\s+)?" + _NAME, re.I),
    "update": re.compile(r"\bupdate\s+(?:only\s+)?" + _NAME + r"\s+(?:\w+\s+)?set\b", re.I),
    "insert": re.compile(r"\binsert\s+into\s+" + _NAME, re.I),
}
_ALTER_RE = re.compile(r"\balter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?" + _NAME + r"(.*?)(?:;|'\s*,|$)", re.I | re.S)
# Безопасные для десктопа изменения его таблиц: только добавить колонку без NOT NULL или сменить владельца
_SAFE_ALTER_RE = re.compile(r"^\s*(add\s+column\s+if\s+not\s+exists\s+\w+\s+[\w\s()]+?|owner\s+to\s+\w+)\s*$", re.I)


def _norm(name: str) -> str:
    return name.replace('"', "").lower().removeprefix("public.")


def _sql_files() -> list[Path]:
    return sorted(p for d in SCANNED for p in (SQL_ROOT / d).glob("*.sql"))


def _text(path: Path) -> str:
    return _COMMENT_RE.sub(" ", path.read_text(encoding="utf-8-sig"))


def _web_tables() -> set[str]:
    out = set()
    for path in _sql_files():
        for m in re.finditer(r"\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?" + _NAME, _text(path), re.I):
            out.add(_norm(m.group(1)))
    return out


def _is_web(table: str, web_tables: set[str]) -> bool:
    return table in web_tables or table.split(".", 1)[0] in WEB_SCHEMAS or table.startswith("pg_temp.")


def _findings() -> list[tuple[str, str, str, str]]:
    """(файл, вид, таблица, фрагмент) — изменения таблиц десктопа вне ALLOWED."""
    web = _web_tables()
    found = []
    for path in _sql_files():
        rel = path.relative_to(SQL_ROOT).as_posix()
        text = _text(path)
        for kind, rx in _STATEMENTS.items():
            for m in rx.finditer(text):
                table = _norm(m.group(1))
                if not _is_web(table, web):
                    found.append((rel, kind, table, " ".join(m.group(0).split())[:90]))
        for m in _ALTER_RE.finditer(text):
            table, rest = _norm(m.group(1)), m.group(2)
            if _is_web(table, web):
                continue
            clauses = [c for c in re.split(r",(?![^()]*\))", rest) if c.strip()]
            if clauses and all(_SAFE_ALTER_RE.match(c) and " not null" not in c.lower() for c in clauses):
                continue
            found.append((rel, "alter", table, " ".join(m.group(0).split())[:90]))
    return [f for f in found if f[:3] not in ALLOWED]


def test_web_sql_does_not_break_desktop_tables():
    bad = _findings()
    assert not bad, (
        "SQL веба меняет таблицы десктопа (удаление, переименование, NOT NULL, ограничения, триггеры, "
        "правка данных). Сделайте изменение добавлением или внесите его в ALLOWED с причиной, "
        "почему десктоп gid8 его не заметит:\n" + "\n".join(f"  {f[0]}: {f[1]} {f[2]} — {f[3]}" for f in bad)
    )


def test_allowed_entries_are_still_needed():
    """Разрешение без находки — устаревшее: убрать, чтобы список не разрастался."""
    web = _web_tables()
    seen = set()
    for path in _sql_files():
        rel = path.relative_to(SQL_ROOT).as_posix()
        text = _text(path)
        for kind, rx in _STATEMENTS.items():
            seen.update((rel, kind, _norm(m.group(1))) for m in rx.finditer(text))
        seen.update((rel, "alter", _norm(m.group(1))) for m in _ALTER_RE.finditer(text))
    stale = [k for k in ALLOWED if k not in seen or _is_web(k[2], web)]
    assert not stale, f"Устаревшие записи ALLOWED: {stale}"


def _city_schema_files() -> list[Path]:
    files = {p for city in [*city_schema.CITIES, "unknown"] for item in city_schema.city_items(city) for p in item.files}
    return sorted(files)


@pytest.mark.parametrize("path", _city_schema_files(), ids=lambda p: p.relative_to(SQL_ROOT).as_posix())
def test_city_schema_sql_is_rerunnable(path):
    """После переконвертации API применяет эти файлы заново — повторный запуск не должен падать."""
    text = _text(path)
    problems = []
    for rx, what in (
        (r"\bcreate\s+table\s+(?!if\s+not\s+exists)", "CREATE TABLE без IF NOT EXISTS"),
        (r"\bcreate\s+(?:unique\s+)?index\s+(?!if\s+not\s+exists|concurrently\s+if\s+not\s+exists)", "CREATE INDEX без IF NOT EXISTS"),
        (r"\bcreate\s+schema\s+(?!if\s+not\s+exists)", "CREATE SCHEMA без IF NOT EXISTS"),
        (r"\bcreate\s+function\b", "CREATE FUNCTION без OR REPLACE"),
        (r"\badd\s+column\s+(?!if\s+not\s+exists)", "ADD COLUMN без IF NOT EXISTS"),
    ):
        if re.search(rx, text, re.I):
            problems.append(what)
    for m in re.finditer(r"\bcreate\s+(?:or\s+replace\s+)?trigger\s+(\w+)", text, re.I):
        if not re.search(rf"\bdrop\s+trigger\s+if\s+exists\s+{m.group(1)}\b", text, re.I) and "or replace" not in m.group(0).lower():
            problems.append(f"триггер {m.group(1)} без DROP TRIGGER IF EXISTS")
    assert not problems, f"{path.name}: " + "; ".join(problems)


def test_guard_catches_destructive_sql(tmp_path, monkeypatch):
    """Страж ловит опасное для десктопа и пропускает добавления и правку своих таблиц."""
    (tmp_path / "migrations").mkdir()
    (tmp_path / "migrations" / "x.sql").write_text(
        "CREATE TABLE IF NOT EXISTS web_log (id int);\n"
        "ALTER TABLE web_log DROP COLUMN id;\n"                       # своя таблица — можно
        "ALTER TABLE nodes ADD COLUMN IF NOT EXISTS web_note text;\n"  # добавление — можно
        "CREATE INDEX IF NOT EXISTS nodes_x ON nodes (id);\n"          # индекс — можно
        "-- ALTER TABLE nodes DROP COLUMN name;\n"                     # в комментарии — не в счёт
        "ALTER TABLE nodes DROP COLUMN name;\n"
        "ALTER TABLE linesobj ALTER COLUMN typ SET NOT NULL;\n"
        "ALTER TABLE public.nodes ADD COLUMN IF NOT EXISTS flag int NOT NULL DEFAULT 0;\n"
        "ALTER TABLE heatpipesections ADD CONSTRAINT c CHECK (true);\n"
        "ALTER TABLE nodes RENAME TO nodes_old;\n"
        "DROP TABLE IF EXISTS fragments;\n"
        "DELETE FROM nodes WHERE id < 0;\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys.modules[__name__], "SQL_ROOT", tmp_path)
    found = {(kind, table, snippet.split()[-1]) for _, kind, table, snippet in _findings()}
    kinds = sorted((k, t) for k, t, _ in found)
    assert kinds == [
        ("alter", "heatpipesections"), ("alter", "linesobj"), ("alter", "nodes"), ("alter", "nodes"),
        ("alter", "nodes"), ("delete", "nodes"), ("drop_table", "fragments"),
    ], kinds
