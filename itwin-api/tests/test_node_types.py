"""Тип узла, заданный напор и подпитка (database/node_types) и вид/имя новых узлов.

БД — FakeConn из test_cad_topology: ответы по подстроке SQL, все вызовы записываются.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from database.node_types import change_node_type, node_cards, set_node_flag
from database.topology import create_node
from database.topology_cad import normalize_points
from tests.test_cad_topology import TOKEN, TS, FakeConn, _lock_rule, _Pool

ALL_TABLES = ["realconsumers", "generalizedconsumers", "heatsources", "pumpstations", "connectnodes",
              "setpressnodes", "refillnodes"]


def _tables_rule(tables=ALL_TABLES):
    return ("information_schema.tables", lambda args: [{"table_name": t} for t in tables if t in args[0]])


def _run(factory, conn):
    audit = AsyncMock()

    async def inner():
        with patch("database.topology.get_pool", return_value=_Pool(conn)), \
             patch("database.topology.write_audit_log", audit):
            return await factory()

    return asyncio.run(inner()), audit


def _node_conn(*, cards=None, inner_nodes=(), inner_lines=(), flags=None, extra=()):
    """Узел 10: cards {таблица: [(id, name)]}, внутренняя схема, flags {таблица: id}."""
    cards = cards or {}
    flags = flags or {}
    rules = [
        _lock_rule({10: (0, TS, "777")}),
        _tables_rule(),
        ("FROM nodes WHERE internalnodeid", [{"id": i} for i in inner_nodes]),
        ("FROM linesobj WHERE internalnodeid", [{"id": i} for i in inner_lines]),
        *extra,
    ]
    for table, rows in cards.items():
        rules.append((f"FROM {table} WHERE nodeid = $1 ORDER BY id\"", None))  # заглушка, не совпадёт
        rules.append((f"AS name FROM {table} WHERE nodeid", [{"id": i, "name": n} for i, n in rows]))
    for table, row_id in flags.items():
        rules.append((f"SELECT id FROM {table} WHERE nodeid = $1 ORDER BY id LIMIT 1", row_id))
        rules.append((f"SELECT id FROM {table} WHERE nodeid = $1 ORDER BY id", [{"id": row_id}]))
    rules.append(("WHERE nodeid = $1 ORDER BY id LIMIT 1", None))
    rules.append(("INSERT INTO", 501))
    return FakeConn(rules)


def test_node_cards_type_flags_and_conflict():
    conn = _node_conn(cards={"realconsumers": [(7, "Дом 1")], "heatsources": [(3, "ТЭЦ")]},
                      flags={"setpressnodes": 44})

    async def go():
        return await node_cards(conn, 10)

    info = asyncio.run(go())
    assert info["type"] == "PR"  # приоритет потребителя
    assert info["conflict"] is True
    assert [c["table"] for c in info["cards"]] == ["realconsumers", "heatsources"]
    assert info["flags"] == {"setpress": 44, "refill": None}


def test_change_us_to_consumer_creates_card_with_desktop_scheme():
    conn = _node_conn()
    res, audit = _run(lambda: change_node_type(10, "PR", expected_version=TOKEN, actor="u"), conn)
    assert (res["old_type"], res["new_type"]) == ("US", "PR")
    assert res["created_card"] == {"table": "realconsumers", "type": "PR", "id": 501}
    ins = [c for c in conn.calls if c[1].startswith("INSERT INTO realconsumers")]
    assert ins and "schemenum" in ins[0][1] and ins[0][2] == (10, "1.3")
    assert conn.executed("UPDATE nodes SET archivechangedate")
    assert not conn.executed("DELETE FROM")
    audit.assert_awaited_once()


def test_change_consumer_to_us_removes_card_and_inner_scheme():
    conn = _node_conn(cards={"realconsumers": [(7, "Дом 1")]}, inner_nodes=(30, 31), inner_lines=(40,))
    res, _ = _run(lambda: change_node_type(10, "US", actor="u"), conn)
    assert res["removed_cards"][0]["id"] == 7 and res["created_card"] is None
    assert res["removed_scheme"] == {"nodes": 2, "lines": 1}
    (_, _, args), = conn.executed("DELETE FROM realconsumers")
    assert args == (7,)
    (_, _, largs), = conn.executed("UPDATE linesobj SET removed = 1")
    assert largs[0] == [40]
    (_, _, nargs), = conn.executed("UPDATE nodes SET removed = 1")
    assert nargs[0] == [30, 31]


def test_node_with_inner_scheme_cannot_become_consumer():
    conn = _node_conn(cards={"heatsources": [(3, "Котельная")]}, inner_nodes=(30,))
    with pytest.raises(ValueError, match="внутренней схемой"):
        _run(lambda: change_node_type(10, "PO"), conn)
    assert not conn.executed("DELETE FROM")


def test_same_type_is_error_and_dry_run_writes_nothing():
    conn = _node_conn(cards={"pumpstations": [(5, "НС-1")]})
    with pytest.raises(ValueError, match="уже имеет тип"):
        _run(lambda: change_node_type(10, "HS"), conn)
    conn = _node_conn(cards={"pumpstations": [(5, "НС-1")]})
    res, _ = _run(lambda: change_node_type(10, "IS", dry_run=True), conn)
    assert res["dry_run"] is True
    assert res["removed_cards"][0]["table"] == "pumpstations"
    assert res["created_card"]["table"] == "heatsources"


def test_change_type_version_conflict():
    from database.topology import TopologyConflictError
    conn = _node_conn()
    with pytest.raises(TopologyConflictError):
        _run(lambda: change_node_type(10, "PR", expected_version="stale"), conn)


def test_set_flag_on_off_and_errors():
    conn = _node_conn()
    res, _ = _run(lambda: set_node_flag(10, "setpress", True, actor="u"), conn)
    assert {k: res[k] for k in ("node_id", "flag", "on", "id")} == {"node_id": 10, "flag": "setpress", "on": True, "id": 501}
    assert any(c[1].startswith("INSERT INTO setpressnodes (nodeid)") for c in conn.calls)

    conn = _node_conn(flags={"refillnodes": 9})
    res, _ = _run(lambda: set_node_flag(10, "refill", False), conn)
    assert res["removed"] == [9]
    assert conn.executed("DELETE FROM refillnodes")

    with pytest.raises(ValueError, match="уже задан"):
        _run(lambda: set_node_flag(10, "refill", True), _node_conn(flags={"refillnodes": 9}))
    with pytest.raises(ValueError, match="не задан"):
        _run(lambda: set_node_flag(10, "setpress", False), _node_conn())
    with pytest.raises(ValueError, match="Неизвестное"):
        _run(lambda: set_node_flag(10, "zzz", True), _node_conn())


def test_create_node_desktop_kind_name_and_type_card():
    ref = {"fileid": 42, "externalcodeid": 2, "externalsignid": 1, "internalnodeid": None,
           "source": "nearest", "reference_node_id": 5}
    conn = FakeConn([_tables_rule(), ("INSERT INTO nodes", 900), ("INSERT INTO", 501)])

    async def go():
        with patch("database.topology.get_pool", return_value=_Pool(conn)), \
             patch("database.topology.write_audit_log", AsyncMock()), \
             patch("database.topology._new_node_reference", AsyncMock(return_value=ref)):
            return await create_node(76.9, 43.3, actor="u", node_type="IS")

    res = asyncio.run(go())
    assert res["id"] == 900 and res["node_type"] == "IS"
    assert res["card"] == {"table": "heatsources", "type": "IS", "id": 501}
    ins = next(c for c in conn.calls if "INSERT INTO nodes" in c[1])
    assert "THEN 13 END" in ins[1]  # вид «неустановленный узел», как addNodeUS десктопа
    (_, sql, args), = conn.executed("externalnodename = 'Узел_' || id")
    assert args == ([900],)
    card = next(c for c in conn.calls if c[1].startswith("INSERT INTO heatsources"))
    assert card[2] == (900, 8.0, -32.0)


def test_create_node_unknown_type():
    with pytest.raises(ValueError, match="Неизвестный тип"):
        asyncio.run(create_node(76.9, 43.3, node_type="XX"))


def test_chain_point_node_type_only_for_new_node():
    pts = normalize_points([
        {"kind": "node", "node_id": 1},
        {"kind": "new", "lng": 76.9, "lat": 43.3, "node_type": "pr"},
    ])
    assert pts[1]["node_type"] == "PR"
    with pytest.raises(ValueError, match="только новому узлу"):
        normalize_points([
            {"kind": "node", "node_id": 1, "node_type": "PR"},
            {"kind": "new", "lng": 76.9, "lat": 43.3},
        ])
