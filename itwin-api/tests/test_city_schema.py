"""Доводка базы города самим API (database/city_schema.py) — без ручных скриптов после переконвертации."""

import asyncio
from contextlib import asynccontextmanager

from database import city_schema as cs


class _Conn:
    """Проверки пунктов отвечают по множеству `present`; применение SQL файла добавляет его пункт."""

    def __init__(self, city, present=None, ready=True, busy=0, lock=True, fail=False):
        self.items = {i.check: i for i in cs.city_items(city)}
        self.present = set(present if present is not None else self.items)
        self.ready, self.busy, self.lock, self.fail = ready, busy, lock, fail
        self.executed: list[str] = []
        self.committed = False

    async def fetchval(self, sql, *args):
        if sql.startswith("select to_regclass('public.nodes')"):
            return self.ready
        if sql == cs.BUSY_SQL:
            return self.busy
        if "pg_try_advisory_xact_lock" in sql:
            return self.lock
        return sql in self.present

    async def execute(self, sql, *args):
        if sql.startswith("set local"):
            return
        if self.fail:
            raise RuntimeError("boom")
        self.executed.append(sql)
        for check, item in self.items.items():
            if any(p.read_text(encoding="utf-8-sig") == sql for p in item.files):
                self.present.add(check)

    @asynccontextmanager
    async def transaction(self):
        before = set(self.present)
        try:
            yield
        except Exception:
            self.present = before
            raise
        self.committed = True


def run(coro):
    return asyncio.run(coro)


def test_all_present_is_ok_and_nothing_runs():
    conn = _Conn("almaty")
    assert run(cs.ensure(conn, "almaty")) == {"status": "ok", "missing": [], "applied": []}
    assert conn.executed == []


def test_applies_only_missing_items():
    # Алматы 22.10: нет только calculation_protocol — применяется его миграция, а не tg_format и т. п.
    conn = _Conn("almaty")
    item = next(i for i in cs.COMMON if i.name == "таблица calculation_protocol")
    conn.present.discard(item.check)
    res = run(cs.ensure(conn, "almaty"))
    assert res == {"status": "applied", "missing": [], "applied": ["таблица calculation_protocol"]}
    assert conn.executed == [item.files[0].read_text(encoding="utf-8-sig")] and conn.committed


def test_shatura_has_srid_and_lines_column_items():
    names = [i.name for i in cs.city_items("shatura")]
    assert names[0] == "SRID 9998 (Шатура)" and "колонка linesobj.internalnodeid" in names
    assert "колонка linesobj.internalnodeid" not in [i.name for i in cs.city_items("almaty")]
    # неизвестный город (новая карта) — общие пункты, без SRID и готовности по чужой системе
    assert [i.name for i in cs.city_items("omsk")] == [i.name for i in cs.COMMON]
    assert "spatial_ref_sys" not in cs.ready_sql("omsk") and "srid = 3857" in cs.ready_sql("shatura")


def test_not_ready_busy_and_check_only_change_nothing():
    conn = _Conn("astana", present=set(), ready=False)
    assert run(cs.ensure(conn, "astana"))["status"] == "not_ready"
    conn = _Conn("astana", present=set(), busy=2)
    assert run(cs.ensure(conn, "astana"))["status"] == "busy"
    conn = _Conn("astana", present=set(), lock=False)
    assert run(cs.ensure(conn, "astana"))["status"] == "busy"
    conn = _Conn("astana", present=set())
    res = run(cs.ensure(conn, "astana", apply=False))
    assert res["status"] == "missing" and res["missing"][0] == "SRID 9998 (Астана)"
    assert conn.executed == []


def test_error_rolls_back_and_reports():
    conn = _Conn("shatura", present=set(), fail=True)
    res = run(cs.ensure(conn, "shatura"))
    assert res["status"] == "error" and "boom" in res["error"] and conn.present == set()


def test_every_item_sql_file_exists():
    for city in (*cs.CITIES, "omsk"):
        for item in cs.city_items(city):
            for path in item.files:
                assert path.exists(), path


def test_mercator_kz_cities_need_no_own_srid():
    for city in ("taraz", "aktobe", "shymkent", "karaganda"):
        names = [i.name for i in cs.city_items(city)]
        assert not any("SRID" in n for n in names)
        assert "колонка linesobj.internalnodeid" not in names and "функции tg_format*" in names
        assert "srid = 3857" in cs.ready_sql(city)
