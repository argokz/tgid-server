"""GET /api/v1/topology/diagnostics (QA F35): проверки топологии фрагмента на фейковом соединении."""

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

import main
import routers.topology as topology_router


def _node(i, internal=None):
    return {"id": i, "internalnodeid": internal}


def _line(i, n1, n2, sign=1, n1_state="live", n2_state="live", f1=1, f2=1):
    def ends(state):
        return state != "missing", state == "removed"
    e1, r1 = ends(n1_state)
    e2, r2 = ends(n2_state)
    return {"id": i, "nodeid1": n1, "nodeid2": n2, "externalsignlineid": sign,
            "n1_exists": e1, "n1_removed": r1, "n1_fileid": f1,
            "n2_exists": e2, "n2_removed": r2, "n2_fileid": f2}


NODES = [_node(i) for i in (1, 2, 3, 4, 5, 6, 7, 8, 20, 21, 40, 41, 50, 51)]
LINES = [
    _line(10, 1, 2), _line(11, 2, 3), _line(12, 3, 4), _line(13, 2, 5),
    _line(14, 2, 9, n2_state="removed"),          # участок на снятый узел
    _line(15, 2, 1),                              # дубль 10 (та же пара и признак)
    _line(19, 1, 2, sign=2),                      # обратка той же пары — не дубль
    _line(16, 6, 6),                              # замкнутый
    _line(17, 7, 8),                              # часть сети без источника
    _line(18, 3, 30, f2=2),                       # конец в другом фрагменте
    _line(20, 40, 41),                            # питается от узла с заданным давлением
    _line(21, 50, 51, sign=None), _line(22, 51, 50, sign=None),  # дубль с NULL-признаком
    _line(23, 51, 52, f2=3),                      # 50–51 связана с фрагментом 3 — не «без источника»
]


class FakeConn:
    def __init__(self, fragment=True):
        self.fragment = fragment

    async def fetchrow(self, sql, *args):
        return {"id": args[0], "name": "Тест"} if self.fragment else None

    async def fetch(self, sql, *args):
        if "ST_Transform" in sql:  # attach_coords
            return [{"id": i, "lon": 76.9, "lat": 43.2} for i in args[0]]
        if "ST_Distance" in sql:
            return [{"id": 13}]
        if "n1_exists" in sql:
            return LINES
        if "connectnodes" in sql:
            return [{"nodeid": 21, "connectid": 99}]
        if "SELECT internalnodeid FROM nodes" in sql:
            return []
        if "heatsources" in sql:  # и setpressnodes
            return [{"nodeid": 1, "kind": "heat_source"}, {"nodeid": 5, "kind": "consumer"},
                    {"nodeid": 40, "kind": "set_pressure"}]
        if "SELECT id, internalnodeid FROM nodes" in sql:
            return NODES
        raise AssertionError(sql)


def _client(monkeypatch, conn):
    monkeypatch.setenv("AUTH_DISABLED", "true")

    @asynccontextmanager
    async def acquire():
        yield conn

    monkeypatch.setattr(topology_router, "acquire_conn", acquire)
    return TestClient(main.app)


def test_diagnostics_counts_by_type(monkeypatch):
    r = _client(monkeypatch, FakeConn()).get("/api/v1/topology/diagnostics", params={"fragment_id": 74})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["counts"] == {
        "dangling_line": 1, "zero_length_line": 1, "duplicate_line": 2, "cross_fragment_line": 2,
        "orphaned_node": 1, "no_source_component": 1, "dangling_node": 4, "geometry_mismatch": 1,
    }
    assert body["total"] == 13 and not body["truncated"]
    by_type = {}
    for f in body["faults"]:
        by_type.setdefault(f["type"], []).append(f["object_id"])
        assert f["lat"] == 43.2 and f["lng"] == 76.9
    assert by_type["dangling_line"] == [14]
    assert by_type["duplicate_line"] == [15, 22]
    assert by_type["orphaned_node"] == [20]          # 21 связан через connectnodes
    assert sorted(by_type["dangling_node"]) == [4, 7, 8, 41]  # 5 — потребитель, 40 — заданное давление
    assert by_type["no_source_component"] == [7]  # 40–41 питается от setPressNodes
    assert "снят" in body["faults"][0]["description"]


def test_diagnostics_limit_per_type_and_404(monkeypatch):
    client = _client(monkeypatch, FakeConn())
    body = client.get("/api/v1/topology/diagnostics", params={"fragment_id": 74, "limit": 1}).json()
    assert body["counts"]["dangling_node"] == 4 and body["truncated"]
    assert sum(1 for f in body["faults"] if f["type"] == "dangling_node") == 1
    assert client.get("/api/v1/topology/diagnostics").status_code == 422  # фрагмент обязателен

    client = _client(monkeypatch, FakeConn(fragment=False))
    assert client.get("/api/topology/diagnostics", params={"fragment_id": 74}).status_code == 404


def test_diagnostics_requires_viewer(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    r = TestClient(main.app).get("/api/v1/topology/diagnostics", params={"fragment_id": 74})
    assert r.status_code == 401
