"""Паспорт участка (passport_module) на PostgreSQL.

Десктопный паспорт написан под MS SQL: STPointN/STDistance, IIF, [алиасы], FOR XML PATH,
табличные функции getPts_*. В PostgreSQL это синтаксические ошибки, а excel.write_table
раньше делал exit(3), и падал весь паспорт. Здесь SQL каждой формы собирается без БД
(соединение и запись в Excel подменены) и проверяется на остатки диалекта MS SQL.
Живая проверка — scripts/golden/passport_forms.py на базе с участками (Астана).
"""

import re
import sys
from pathlib import Path

import pytest

PM = Path(__file__).resolve().parents[1] / "passport_module"
sys.path.insert(0, str(PM))

import connect  # noqa: E402
import excel  # noqa: E402
import journals_pg  # noqa: E402
import sql  # noqa: E402
import sql2  # noqa: E402

MARK_LINE = "(1, 101, 1, 7),(2, 102, 0, 7),(3, 103, 1, 8)"
MARK_PTS = "(1, 7, 11, 12),(2, 8, 12, 13)"
MARK_NODE = "(1, 11),(2, 12),(3, 13)"
VALS = {"name": "Участок", "nomer_uchastka": "1", "fio": "Иванов"}

MSSQL = [
    (r"\.ST[A-Z][A-Za-z]+\(", "метод геометрии MS SQL"),
    (r"\bIIF\s*\(", "IIF"),
    (r"FOR\s+XML", "FOR XML PATH"),
    (r"\bgetPts\w*\s*\(", "табличная функция getPts_*"),
    (r"(?i)\bas\s+'[^']+'", "алиас в одинарных кавычках"),
    (r"\[[^\]\n]*[А-Яа-я][^\]\n]*\]", "[алиас]"),
    (r"\bfn_split_string\b", "fn_split_string"),
    (r"(?i)\btop\s+\d+", "TOP n"),
    (r"(?i)\bisnull\s*\(", "ISNULL"),
    (r"\bin\s*\(\s*\)", "пустой IN ()"),
]


def _mssql_leftovers(q):
    code = "\n".join(line.split("--", 1)[0] for line in q.splitlines())
    return [name for rx, name in MSSQL if re.search(rx, code)]


class _Cursor:
    def execute(self, q):
        pass

    def fetchone(self):
        return None


class _Conn:
    def cursor(self):
        return _Cursor()

    def close(self):
        pass


@pytest.fixture
def captured(monkeypatch):
    queries = []

    def write_table(ws, conn, q, row0=1, **kw):
        queries.append(q)
        return row0, 1

    monkeypatch.setattr(connect, "connect", lambda **c: _Conn())
    monkeypatch.setattr(excel, "write_table", write_table)
    for helper in ("adjust_table2_3", "adjust_table2_2", "adjust_table"):
        if hasattr(excel, helper):
            monkeypatch.setattr(excel, helper, lambda *a, **k: None)
    monkeypatch.setattr(sql2, "get_ps_obj", lambda conn, q: queries.append(q) or "(1, 2, 101, 7, 11, 12, 1, 1)")
    return queries


FORMS = ["f1", "f2_1", "f2_2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "f13", "f14", "f15"]


@pytest.mark.parametrize("name", FORMS)
@pytest.mark.parametrize("ms_rs", ["ms", "rs"])
def test_form_sql_is_postgresql(name, ms_rs, captured):
    import openpyxl

    mod = __import__(name)
    ws = openpyxl.Workbook().active
    args = [{}, ws, ms_rs, 19, "", MARK_LINE, MARK_PTS]
    if name in ("f4", "f5"):
        args += [MARK_NODE, VALS]
    mod.do_passport(*args)
    assert captured, f"{name}: форма не выполнила ни одного запроса"
    for q in captured:
        assert not _mssql_leftovers(q), (name, _mssql_leftovers(q))


def test_object_binding_uses_index_friendly_postgis():
    q = sql.get_obj_ps(MARK_LINE, MARK_PTS, "(select id, shape from zapornaya_armatura)", ["id"])
    assert "ST_DWithin(z.shape, l.shape, 0.3)" in q  # по колонке — работает GiST-индекс
    assert "ST_PointN(" in q  # точная привязка по первой точке, как STPointN(1)
    # одна нумерация «труба, затем узел»: при двух независимых объект выпадал из формы
    assert "1 AS rn2" in q and "ORDER BY ST_Distance(" in q
    whole = sql.get_obj_ps(MARK_LINE, MARK_PTS, "(select id, shape from tkamera)", ["id"], use_first_point=False)
    assert "ST_PointN(" not in whole


def test_first_point_handles_point_line_polygon():
    expr = sql.first_point("g")
    assert "ST_PointN(ST_GeometryN(g, 1), 1)" in expr  # линия
    assert "ST_ExteriorRing" in expr  # полигон
    assert expr.rstrip(")").endswith("ST_GeometryN(g, 1")  # точка


def test_fragment_filter():
    assert journals_pg.fragment_filter("n1", "") == "(1=1)"
    assert journals_pg.fragment_filter("n1", "74, 75") == "n1.fileID in (74,75)"
    with pytest.raises(ValueError):
        journals_pg.fragment_filter("n1", "1; drop table x")


def test_journal_args_are_validated():
    with pytest.raises(ValueError):
        journals_pg.cut_out(1, "ms'; --", "")
    with pytest.raises(ValueError):
        journals_pg.inspection("1 or 1=1", "ms", "")


def test_pg_identifiers_fit_63_bytes_without_collisions():
    for fn in (journals_pg.cut_out, journals_pg.pressure_test, journals_pg.inspection):
        aliases = re.findall(r'AS "([^"]+)"', fn(1, "ms", ""))
        cut = [a.encode()[:63] for a in aliases]
        assert len(cut) == len(set(cut)), fn.__name__


def test_values_list_nulls_are_typed():
    class Cur(_Cursor):
        rows = [(1, None, 101, 7, 11, 12, 1, 1)]

        def fetchone(self):
            return self.rows.pop() if self.rows else None

    class Conn(_Conn):
        def cursor(self):
            return Cur()

    ps2 = sql2.get_ps_obj(Conn(), "select")
    assert "null::int" in ps2 and ", null," not in ps2
    assert "null::int" in sql2.get_ps_obj(_Conn(), "select")


def test_write_table_raises_instead_of_exit():
    import openpyxl
    import psycopg2

    class Bad(_Cursor):
        def execute(self, q):
            raise psycopg2.ProgrammingError("syntax error")

    class Conn(_Conn):
        def cursor(self):
            return Bad()

    with pytest.raises(RuntimeError):
        excel.write_table(openpyxl.Workbook().active, Conn(), "select")


def test_no_mojibake_in_sources():
    rx = re.compile(r"[РС][\u0080-¿\u0098Ђ-Џђ-џ‐-›№Ґґ]")
    bad = []
    for f in PM.glob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
            if rx.search(line):
                bad.append(f"{f.name}:{i}")
    assert not bad, bad
