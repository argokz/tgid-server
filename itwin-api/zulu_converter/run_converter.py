"""Запуск конвертера Zulu → ТГИД (копия gid8 python/zulu2, см. README.md) отдельным процессом API.

Аргументы — как у z.py: -name, -path (слой без расширения), -Tn, -reset, -path_out. Рабочий каталог — этот
(standardpumps.csv и GID.lookup читаются по относительному пути), TMP/TEMP — каталог задачи: промежуточная база
baza.sqlite создаётся в tempfile.gettempdir().

Отличия от запуска z.py в gid8 — только окружение, код конвертера не меняется:
  * SQLite — встроенный sqlite3 в обёртке с интерфейсом pyodbc вместо ODBC-драйвера «SQLite3 ODBC Driver»
    (на сервере его нет; строки — списки, как изменяемые строки pyodbc; cursor.tables());
  * sqlparse не нужен: ispr_sql переписывает только «(SELECT алиас)», а в full_tgid.sql таких нет;
  * pypxlib (базы Paradox .db старых слоёв) не поддерживается — нужна база слоя в SQLite.
Перед конвертацией пишется report.json: объекты графического слоя по типам и строки баз слоя.
"""
from __future__ import annotations

import json
import os
import runpy
import sqlite3
import sys
import types
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def _install_stubs() -> None:
    try:
        import sqlparse  # noqa: F401
    except ImportError:
        sqlparse = types.ModuleType("sqlparse")
        sqlparse.parse = lambda sql: []
        tokens = types.ModuleType("sqlparse.tokens")
        tokens.Keyword = tokens.DML = tokens.Name = object()
        sqlparse.tokens = tokens
        sys.modules["sqlparse"] = sqlparse
        sys.modules["sqlparse.tokens"] = tokens
    try:
        import pypxlib  # noqa: F401
    except ImportError:
        pypxlib = types.ModuleType("pypxlib")

        class _NoParadox:
            def __init__(self, *a, **k):
                raise RuntimeError("Базы Paradox (.db) не поддерживаются — нужна база слоя в SQLite")

        pypxlib.Table = _NoParadox
        sys.modules["pypxlib"] = pypxlib


def _install_sqlite_adapter() -> None:
    import pyodbc

    import connect

    class Cursor:
        def __init__(self, cur):
            self._cur = cur

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self._cur.close()
            return False

        def execute(self, sql, *params):
            args = params[0] if len(params) == 1 and isinstance(params[0], (list, tuple)) else params
            try:
                self._cur.execute(sql, args)
            except sqlite3.Error as e:
                # конвертер ловит pyodbc.Error и читает str(e.args[1], "utf8")
                raise pyodbc.Error("HY000", str(e).encode("utf8")) from e
            return self

        def tables(self):
            # pyodbc: (catalog, schema, table_name, table_type, remarks)
            rows = self._cur.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
            return [(None, None, r[0], "TABLE", None) for r in rows]

        def __getattr__(self, name):
            return getattr(self._cur, name)

        def __iter__(self):
            return iter(self._cur)

    class Conn:
        def __init__(self, fn):
            self._conn = sqlite3.connect(fn)
            self._conn.row_factory = lambda cursor, row: list(row)

        def cursor(self):
            return Cursor(self._conn.cursor())

        def execute(self, sql, *params):
            return self.cursor().execute(sql, *params)

        def add_output_converter(self, *a):
            pass

        def __getattr__(self, name):
            return getattr(self._conn, name)

    connect.connect_sqlite = lambda fn: Conn(fn)


def layer_report(base: str) -> dict:
    """Объекты графического слоя по типам (индекс .b00/.b01, разбор как в z.py) и строки баз слоя (.sqlite)."""
    from auxiliary import read_char, read_long, read_short, read_string_zero, read_xy

    types_by_id: dict[int, str] = {}
    with open(base + ".b02", "rb") as f:
        f.seek(4)
        count = read_long(f) or 0
        off = 0x2016
        for _ in range(count):
            f.seek(off)
            n1 = read_long(f)
            if n1 is None:
                break
            read_short(f)
            types_by_id[n1] = read_string_zero(f, 40)
            off += 0x137
    blocks = []
    with open(base + ".b00", "rb") as f:
        f.seek(0x55E)
        while True:
            try:
                n1 = read_short(f)
                if not n1:
                    break
                read_short(f)
                read_long(f)
                off = read_long(f)
            except EOFError:
                break
            if n1 > 0:
                blocks.append(off)
    objects: dict[int, tuple[int, int]] = {}
    with open(base + ".b01", "rb") as f:
        for block in blocks:
            f.seek(block)
            read_xy(f)
            read_xy(f)
            for _ in range(read_short(f) or 0):
                oid = read_long(f)
                read_long(f)
                loc = read_char(f)
                typ = read_char(f)
                read_char(f)
                read_char(f)
                read_short(f)
                read_long(f)
                read_long(f)
                objects[oid] = (loc, typ)
    layer = Counter(types_by_id.get(typ, f"тип {typ}") for _, typ in objects.values())
    tables: dict[str, int] = {}
    if os.path.isfile(base + ".sqlite"):
        db = sqlite3.connect(f"file:{base}.sqlite?mode=ro", uri=True)
        try:
            for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'"):
                tables[name] = db.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
        finally:
            db.close()
    return {"layer": dict(sorted(layer.items())), "db_tables": tables, "has_sqlite": bool(tables)}


def main(argv: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.path.insert(0, HERE)
    os.chdir(HERE)
    if argv[:1] == ["--report"]:
        # только сводка слоя (проверка загрузки): run_converter.py --report <слой без расширения>
        print(json.dumps(layer_report(argv[1]), ensure_ascii=False))
        return
    _install_stubs()
    _install_sqlite_adapter()
    def value(flag: str) -> str:
        return argv[argv.index(flag) + 1] if flag in argv[:-1] else ""

    base, out = value("-path"), value("-path_out")
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(layer_report(base), f, ensure_ascii=False)
    sys.argv = ["z.py", *argv]
    runpy.run_path(os.path.join(HERE, "z.py"), run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
