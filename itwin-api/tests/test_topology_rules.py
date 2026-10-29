"""Правила связности и проверка области правки (database/topology_rules.py) на фейковом соединении."""

import asyncio
import json
from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

import database.topology_journal as journal
import database.topology_rules as rules
import main
import routers.topology as topology_router


def _line(i, n1, n2, sign=1, n2_state="live", f1=1, f2=1):
    return {"id": i, "nodeid1": n1, "nodeid2": n2, "externalsignlineid": sign,
            "n1_exists": True, "n1_removed": False, "n1_fileid": f1,
            "n2_exists": n2_state != "missing", "n2_removed": n2_state == "removed", "n2_fileid": f2}


# 1 — источник; 2–3–4 тупик у чужого узла 9; 5 — потребитель и источник сразу; 6 — без связей;
# 7–8 — остров без питания, 8 у трубы 11 без врезки
NODES = {i: {"id": i, "fileid": 1, "internalnodeid": None, "has_shape": True} for i in range(1, 9)}
LINES = [
    _line(10, 1, 2), _line(11, 2, 3), _line(12, 3, 4), _line(13, 2, 5),
    _line(14, 2, 1),                       # дубль 10
    _line(15, 7, 8),
    _line(16, 3, 99, n2_state="removed"),  # конец на снятый узел
    _line(17, 3, 30, f2=2),                # другой фрагмент
]
GRAPH = {
    "adj": {1: [(10, 2)], 2: [(10, 1), (11, 3), (13, 5)], 3: [(11, 2), (12, 4)], 4: [(12, 3)],
            5: [(13, 2)], 7: [(15, 8)], 8: [(15, 7)]},
    "baseline_reachable": {1, 2, 3, 4, 5},
}
JOURNAL_ROW = {
    "summary": json.dumps({"node_id": 2}),
    "before_rows": json.dumps([
        {"t": "linesobj", "id": 16, "row": {"nodeid1": 3, "nodeid2": 99}},
        {"t": "nodes", "id": 4, "row": None},
        {"t": "realconsumers", "id": 500, "row": None},
    ]),
    "after_hashes": json.dumps({"nodes:4": "a", "linesobj:12": "b"}),
}


class FakeConn:
    def __init__(self, journal_row=JOURNAL_ROW):
        self.journal_row = journal_row

    async def fetchval(self, sql, *args):
        assert "to_regclass" in sql, sql
        return True

    async def fetchrow(self, sql, *args):
        assert "topology_undo_log" in sql, sql
        return self.journal_row

    async def fetch(self, sql, *args):
        if "information_schema" in sql:
            return [{"column_name": "id", "udt_name": "int4"}, {"column_name": "nodeid", "udt_name": "int4"}]
        if 'FROM "realconsumers" WHERE id' in sql:
            return [(5,)]
        if "ST_Transform" in sql:  # attach_coords
            return [{"id": i, "lon": 76.9, "lat": 43.2} for i in args[0]]
        if "SELECT nodeid1, nodeid2 FROM linesobj" in sql:
            return [{"nodeid1": 3, "nodeid2": 99}] if 16 in args[0] else []
        if "has_shape" in sql:
            return [NODES[i] for i in args[0] if i in NODES]
        if "n1_exists" in sql:
            return LINES
        if "DISTINCT nodeid" in sql:
            return [{"nodeid": 1, "t": "heatsources"}, {"nodeid": 5, "t": "realconsumers"},
                    {"nodeid": 5, "t": "heatsources"}]
        if "connectnodes" in sql:
            return []
        if "ST_DWithin(o.shape" in sql:
            return [{"a": 4, "o": 3, "d": 0.4}, {"a": 4, "o": 9, "d": 0.6}]
        if "ST_DWithin(l.shape" in sql:
            return [{"a": 4, "l": 11, "nodeid1": 2, "nodeid2": 3, "d": 0.3},
                    {"a": 8, "l": 11, "nodeid1": 2, "nodeid2": 3, "d": 0.5}]
        if "GeometryType" in sql:
            return [{"id": 13}]
        raise AssertionError(sql)


def _patch(monkeypatch):
    async def graph(conn):
        return GRAPH
    monkeypatch.setattr(rules, "get_outage_network_graph", graph)
    monkeypatch.setattr(journal, "_TABLE_COLUMNS", {})
    monkeypatch.setattr(journal, "_GEOMETRY_COLUMNS", {})


def _client(monkeypatch, conn):
    _patch(monkeypatch)
    monkeypatch.setenv("AUTH_DISABLED", "true")

    @asynccontextmanager
    async def acquire():
        yield conn

    monkeypatch.setattr(topology_router, "acquire_conn", acquire)
    return TestClient(main.app)


def test_check_area_rules(monkeypatch):
    _patch(monkeypatch)
    res = asyncio.run(rules.check_area(FakeConn(), [2, 4, 5, 6, 7, 8], [16]))
    assert {k: v for k, v in res["counts"].items() if v} == {
        "dangling_line": 1, "node_type_conflict": 1, "duplicate_line": 1, "unsnapped_end": 2,
        "orphaned_node": 1, "cross_fragment_line": 1, "geometry_mismatch": 1, "no_supply": 1,
    }
    assert res["area"] == {"nodes": 8 - 1, "lines": len(LINES)}  # 1 — не в области, 99 снят
    assert res["errors"] == 2 and res["total"] == 9 and not res["truncated"]
    by_type = {}
    for i in res["issues"]:
        by_type.setdefault(i["type"], []).append(i)
        assert i["lat"] == 43.2 and i["severity"] == rules.RULES[i["type"]]["severity"]
    assert res["issues"][0]["type"] == "dangling_line"  # ошибки — первыми
    snap = {i["object_id"]: i for i in by_type["unsnapped_end"]}
    assert snap[4]["related_ids"] == [9]  # соседний узел 3 и его труба 11 — не ошибка привязки
    assert snap[8]["related_ids"] == [11] and "врезка" in snap[8]["description"]
    assert by_type["node_type_conflict"][0]["object_id"] == 5
    assert by_type["orphaned_node"][0]["object_id"] == 6
    island = by_type["no_supply"][0]
    assert island["object_id"] == 7 and island["component_size"] == 2  # один остров на 7 и 8
    assert "2 узла" in island["description"]


def test_nodes_word():
    assert [rules._nodes_word(n) for n in (1, 2, 5, 11, 12, 21, 22, 115)] == [
        "узел", "узла", "узлов", "узлов", "узлов", "узел", "узла", "узлов"]


def test_operation_area_from_journal(monkeypatch):
    _patch(monkeypatch)
    nodes, lines = asyncio.run(rules.operation_area(FakeConn(), 125))
    # узел из summary, концы снятого участка из образа «до», узел созданной карточки потребителя
    assert nodes == {2, 3, 99, 4, 5}
    assert lines == {16, 12}
    assert asyncio.run(rules.operation_area(FakeConn(journal_row=None), 125)) is None


def test_check_endpoints(monkeypatch):
    client = _client(monkeypatch, FakeConn())
    r = client.get("/api/v1/topology/operations/125/check")
    assert r.status_code == 200, r.text
    assert r.json()["operation_id"] == 125 and r.json()["total"] > 0

    r = client.post("/api/v1/topology/check-area", json={"node_ids": [4], "line_ids": []})
    assert r.status_code == 200, r.text
    assert client.post("/api/v1/topology/check-area", json={"node_ids": [0]}).status_code == 422
    too_many = {"node_ids": list(range(1, rules.AREA_LIMIT + 2))}
    assert client.post("/api/v1/topology/check-area", json=too_many).status_code == 422

    client = _client(monkeypatch, FakeConn(journal_row=None))
    assert client.get("/api/v1/topology/operations/125/check").status_code == 404


def test_check_requires_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    assert TestClient(main.app).get("/api/v1/topology/operations/1/check").status_code == 401
