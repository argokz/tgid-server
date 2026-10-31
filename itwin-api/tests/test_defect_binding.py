"""Запись участка в журнал нарушений: выбор копии трубы, предпросмотр, запись одной операцией, отмена."""

import asyncio
import json
from collections import Counter

import pytest

from database import defect_binding as db


def test_choose_prefers_frequent_fragment_then_lowest_id():
    copies = [{"lineid": 30, "fileid": 58}, {"lineid": 20, "fileid": 3151}, {"lineid": 10, "fileid": 2149}]
    assert db.choose(copies, Counter({3151: 14, 2149: 6}))["lineid"] == 20
    assert db.choose(copies, Counter())["lineid"] == 10  # журнал пуст — наименьший id


class FakeConn:
    def __init__(self, audit_ok=True):
        self.updates, self.audit, self.audit_ok = [], [], audit_ok

    async def fetchval(self, sql, *args):
        if "shape IS NOT NULL" in sql:
            return 4
        if "shape IS NULL" in sql:
            return 1
        if "EXISTS (SELECT 1 FROM audit_log" in sql:
            return self.audit_ok
        if "FROM audit_log" in sql:
            return json.dumps({"action": "bind_lines", "count": 2, "items": [[1, 20], [2, 40]]})
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if "CROSS JOIN LATERAL" in sql:  # поиск копий (wear._SNAP_SQL)
            return [{"defect_id": 1, "lineid": 30, "fileid": 58, "distance_m": 0.0},
                    {"defect_id": 1, "lineid": 20, "fileid": 3151, "distance_m": 0.0},
                    {"defect_id": 2, "lineid": 40, "fileid": 17, "distance_m": 6.25},
                    {"defect_id": 3, "lineid": 50, "fileid": 17, "distance_m": 12.0}]
        if "GROUP BY l.fileid" in sql:
            return [{"fileid": 3151, "n": 14}, {"fileid": 17, "n": 3}]
        if "FROM fragments" in sql:
            return [{"id": 3151, "name": "Магистрали 2023–2024"}, {"id": 17, "name": "Район 17"}]
        if sql.lstrip().startswith("UPDATE defect d SET lineid = q.line_id"):
            ids, lines = args
            self.updates.append(list(zip(ids, lines)))
            return [{"id": i, "lineid": l} for i, l in zip(ids, lines) if i != 3]  # у 3 участок уже вписан руками
        if sql.lstrip().startswith("UPDATE defect d SET lineid = NULL"):
            return [{"id": 1}]  # у 2 участок поменяли после записи — не трогаем
        raise AssertionError(sql)

    def transaction(self):
        class _T:
            async def __aenter__(self_inner):
                return None

            async def __aexit__(self_inner, *a):
                return False
        return _T()


def test_preview_apply_undo(monkeypatch):
    calls = []

    async def audit(**kw):
        calls.append(kw)
        return "group-0001"

    monkeypatch.setattr("audit.write_audit_log", audit)
    conn = FakeConn()
    plan = asyncio.run(db.preview(conn))
    assert plan["unplaced"] == 4 and plan["to_bind"] == 3 and plan["far"] == 1 and plan["without_place"] == 1
    assert plan["items"][0] == {"defect_id": 1, "line_id": 20, "fileid": 3151, "fragment": "Магистрали 2023–2024",
                                "distance_m": 0.0, "copies": 2}
    assert plan["with_copies"] == 1

    out = asyncio.run(db.apply(conn, "ivan", exclude={2}))
    assert conn.updates[-1] == [(1, 20), (3, 50)]  # снятое пользователем не пишется
    assert out == {"bound": 1, "skipped": 1, "far": 1, "change_group_id": "group-0001"}
    assert calls[0]["operation"] == "UPDATE" and len(calls[0]["operation"]) <= 10  # audit_log.operation — varchar(10)
    assert calls[0]["new_data"] == {"action": "bind_lines", "count": 1, "items": [[1, 20]]}

    res = asyncio.run(db.undo(conn, "group-0001", "ivan"))
    assert res == {"unbound": 1, "changed_since": 1} and calls[-1]["new_data"]["action"] == "unbind_lines"

    # журнал действий не принял запись — привязка не проходит (иначе её нельзя отменить)
    with pytest.raises(db.BindingError):
        asyncio.run(db.apply(FakeConn(audit_ok=False), "ivan"))
