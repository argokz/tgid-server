"""Этап 8.5–8.7: журнал отмены (before-image), отмена, узел с фрагментом, разворот пары,
разрешение оборудования «на ручную проверку» при разрезании."""

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from database.topology import (
    TopologyConflictError,
    TopologyDependencyError,
    TopologyNothingToUndo,
    create_node,
    reverse_line,
    split_line,
    undo_last_operation,
    version_token,
)
from database.topology_journal import (
    OperationJournal,
    changed_since,
    restore_rows,
    restore_sql,
    row_image_sql,
)
from database.topology_transfer import transfer_dependents
from database import topology_journal
from tests.test_cad_topology import TS, FakeConn, _lock_rule, _run


@pytest.fixture(autouse=True)
def _fresh_column_cache():
    """Кэш колонок журнала — на процесс; тесты подсовывают разные схемы."""
    topology_journal._TABLE_COLUMNS.clear()
    topology_journal._GEOMETRY_COLUMNS.clear()
    yield
    topology_journal._TABLE_COLUMNS.clear()
    topology_journal._GEOMETRY_COLUMNS.clear()


# --- журнал ------------------------------------------------------------------

def test_row_image_keeps_geometry_as_hex_ewkb_and_uses_alias():
    sql = row_image_sql("linesobj", ["shape"])
    assert "to_jsonb(_r)" in sql
    assert "encode(ST_AsEWKB(_r.\"shape\"), 'hex')" in sql
    assert row_image_sql("heatpipesections", []) == "to_jsonb(_r)"


def test_restore_sql_updates_every_column_but_id():
    sql = restore_sql("nodes", ["id", "x", "shape"])
    assert 'SET ("x", "shape") =' in sql
    assert "jsonb_populate_record(NULL::\"nodes\", $1::jsonb)" in sql
    assert sql.endswith("WHERE _t.id = $2")


def test_changed_since_reports_changed_and_missing_rows():
    after = {"nodes:1": "a", "linesobj:2": "b", "nodes:3": "c"}
    current = {"nodes:1": "a", "linesobj:2": "x", "nodes:3": None}
    assert changed_since(after, current) == {
        "linesobj:2": {"expected": "b", "actual": "x"},
        "nodes:3": {"expected": "c", "actual": None},
    }


def test_disabled_journal_makes_no_queries():
    conn = FakeConn()
    j = OperationJournal(enabled=False)

    async def go():
        await j.capture_ids(conn, "nodes", [1])
        j.created("nodes", 2)
        return await j.commit(conn, actor="u", operation="MOVE", group_id="g", summary={})

    assert asyncio.run(go()) is None
    assert conn.calls == []


def test_journal_commit_keeps_postgres_row_text_and_hashes_after():
    img = '{"id": 5, "x": 0.1000000000000000055511151231257827, "shape": "0101"}'
    conn = FakeConn([
        ("information_schema.columns", [
            {"column_name": "id", "udt_name": "int4"},
            {"column_name": "x", "udt_name": "float8"},
            {"column_name": "shape", "udt_name": "geometry"},
        ]),
        ("::text AS img", [{"id": 5, "img": img}]),
        ("md5(", lambda a: [{"id": i, "h": f"h{i}"} for i in a[0] if i != 9]),
        ("INSERT INTO topology_undo_log", 77),
    ])
    j = OperationJournal(enabled=True)

    async def go():
        await j.capture_ids(conn, "nodes", [5])
        j.created("nodes", 9)
        return await j.commit(conn, actor="u", operation="MOVE", group_id="g", summary={"node_id": 5})

    assert asyncio.run(go()) == 77
    insert = [c for c in conn.calls if "INSERT INTO topology_undo_log" in c[1]][0][2]
    before = insert[4]
    # образ вставлен текстом PostgreSQL как есть — numeric не проходит через float Python
    assert img in before and '"row": null' in before
    assert json.loads(insert[5]) == {"nodes:5": "h5", "nodes:9": None}


def test_restore_rows_deletes_created_and_updates_others():
    conn = FakeConn([("information_schema.columns", [
        {"column_name": "id", "udt_name": "int4"}, {"column_name": "x", "udt_name": "float8"}])])
    items = [{"t": "nodes", "id": 1, "row": '{"id": 1, "x": 2}'}, {"t": "linesobj", "id": 7, "row": None}]
    report = asyncio.run(restore_rows(conn, items))
    assert report == {"restored": {"nodes": 1}, "deleted": {"linesobj": [7]}}
    assert conn.executed('DELETE FROM "linesobj" WHERE id = $1')[0][2] == (7,)
    assert conn.executed('UPDATE "nodes" AS _t SET ("x")')[0][2] == ('{"id": 1, "x": 2}', 1)


# --- отмена ------------------------------------------------------------------

def _undo_conn(row_id=12, hashes_now=None, after=None):
    after = after or {"nodes:5": "h5"}
    hashes_now = hashes_now if hashes_now is not None else {5: "h5"}
    return FakeConn([
        ("to_regclass", True),
        ("FROM topology_undo_log\n            WHERE actor", {
            "id": row_id, "operation": "MOVE", "created_at": TS, "summary": '{"node_id": 5}',
            "unsupported": None, "group_id": "00000000-0000-0000-0000-000000000001",
            "after_hashes": json.dumps(after), "objects": 1,
        }),
        ("information_schema.columns", [{"column_name": "id", "udt_name": "int4"},
                                        {"column_name": "x", "udt_name": "float8"}]),
        ("md5(", lambda a: [{"id": i, "h": hashes_now[i]} for i in a[0] if i in hashes_now]),
        ("jsonb_array_elements", [{"t": "nodes", "id": 5, "img": '{"id": 5, "x": 1}'}]),
    ])


def _run_undo(conn, **kw):
    return _run(lambda: undo_last_operation("u", **kw), conn)


def test_undo_restores_before_image_and_marks_entry():
    conn = _undo_conn()
    res, invalidate, audit, _ = _run_undo(conn, operation_id=12)
    assert res["success"] is True and res["operation_id"] == 12
    assert res["restored"] == {"nodes": 1}
    assert conn.executed('UPDATE "nodes" AS _t')
    assert conn.executed("SET undone_at = now()")
    assert audit.await_args.kwargs["operation"] == "UNDO"
    invalidate.assert_called_once()


def test_undo_conflicts_when_objects_changed_after_operation():
    conn = _undo_conn(hashes_now={5: "other"})
    with pytest.raises(TopologyConflictError) as exc:
        _run_undo(conn)
    assert exc.value.conflicts == {"nodes:5": {"expected": "h5", "actual": "other", "removed": False}}
    assert not conn.executed("UPDATE")


def test_undo_conflicts_when_last_operation_is_another():
    with pytest.raises(TopologyConflictError) as exc:
        _run_undo(_undo_conn(row_id=13), operation_id=12)
    assert exc.value.conflicts == {"operation": {"expected": 12, "actual": 13}}


def test_undo_nothing_to_undo():
    with pytest.raises(TopologyNothingToUndo):
        _run_undo(FakeConn([("to_regclass", True)]))
    with pytest.raises(TopologyNothingToUndo):
        _run_undo(FakeConn())  # журнал не установлен


# --- create_node: фрагмент ---------------------------------------------------

def test_create_node_takes_fragment_code_and_sign_from_nearest_node():
    ref = {"id": 40, "fileid": 41, "externalcodeid": 883, "externalsignid": 1,
           "internalnodeid": None, "distance": 12.0}
    conn = FakeConn([("ORDER BY n.shape <-> p.g", ref), ("INSERT INTO nodes", 900)])
    res, *_ = _run(lambda: create_node(76.9, 43.2, actor="u"), conn)
    assert res["id"] == 900 and res["fileid"] == 41 and res["reference"] == {"source": "nearest_node", "node_id": 40}
    insert = [c for c in conn.calls if "INSERT INTO nodes" in c[1]][0]
    assert "fileid, externalcodeid, externalsignid, internalnodeid" in insert[1]
    assert insert[2][3:] == (41, 883, 1, None)


def test_create_node_without_reference_is_rejected():
    with pytest.raises(ValueError, match="фрагмент"):
        _run(lambda: create_node(76.9, 43.2), FakeConn())


def test_create_node_explicit_fileid_uses_fragment_code():
    conn = FakeConn([("FROM externalcodes", 1119), ("INSERT INTO nodes", 901)])
    res, *_ = _run(lambda: create_node(76.9, 43.2, fileid=95), conn)
    assert (res["fileid"], res["externalcodeid"], res["reference"]["source"]) == (95, 1119, "fileid")


def test_create_node_from_near_line_uses_its_start_node():
    ref = {"id": 3, "fileid": 7, "externalcodeid": 5, "externalsignid": 2, "internalnodeid": 44}
    conn = FakeConn([("FROM linesobj l LEFT JOIN nodes n1", ref), ("INSERT INTO nodes", 902)])
    res, *_ = _run(lambda: create_node(76.9, 43.2, near_line_id=10), conn)
    assert (res["fileid"], res["externalsignid"], res["internalnodeid"]) == (7, 2, 44)


# --- разворот пары -----------------------------------------------------------

def _pair_conn(pair=True):
    return FakeConn([
        ("AS matched_by", {"id": 101, "matched_by": "coords", "deviation": 0.0} if pair else None),
        _lock_rule({100: (0, TS, "7"), 101: (0, TS, "8")}),
        ("SELECT nodeid1, nodeid2, externalsignlineid", lambda a: {
            "nodeid1": 10, "nodeid2": 20, "externalsignlineid": 2 if a[0] == 100 else 3,
            "points": 2, "length": 5.0}),
        ("SELECT id, archivechangedate, xmin::text", lambda a: [
            {"id": i, "archivechangedate": TS, "xmin": "9"} for i in a[0]]),
    ])


def test_reverse_dry_run_reports_pair_and_both_versions():
    res, *_ = _run(lambda: reverse_line(100, dry_run=True), _pair_conn())
    assert res["pair"]["line_id"] == 101 and res["pair"]["matched_by"] == "coords"
    assert res["pair"]["after"] == {"nodeid1": 20, "nodeid2": 10, "externalsignlineid": 3}
    assert res["versions"] == {"line:100": version_token(TS, "7"), "line:101": version_token(TS, "8")}


def test_reverse_applies_to_both_lines_of_pair():
    conn = _pair_conn()
    res, *_ = _run(lambda: reverse_line(100, pair_line_id=101, pair_version=version_token(TS, "8")), conn)
    updated = [c[2][0] for c in conn.executed("UPDATE linesobj")]
    assert updated == [100, 101] and res["pair_line_id"] == 101


def test_reverse_pair_version_conflict_and_lost_pair():
    with pytest.raises(TopologyConflictError):
        _run(lambda: reverse_line(100, pair_line_id=101, pair_version=version_token(TS, "1")), _pair_conn())
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: reverse_line(100, pair_line_id=101), _pair_conn(pair=False))
    assert exc.value.blockers == {"pair": {"line_id": 101, "valid": False}}


def test_reverse_without_pair_touches_one_line():
    conn = _pair_conn()
    _run(lambda: reverse_line(100, include_pair=False), conn)
    assert [c[2][0] for c in conn.executed("UPDATE linesobj")] == [100]


# --- B2: оборудование «на ручную проверку» при разрезании ----------------------

def _transfer_conn(review_rows):
    return FakeConn([
        ("information_schema.tables", 1),
        ("information_schema.columns", 1),
        ('FROM "dampers" WHERE lineid = $1 ORDER BY id', review_rows),
        ('UPDATE "dampers" SET lineid = $2', lambda a: [{"id": i} for i in a[2]]),
    ])


def test_transfer_lists_review_items_and_moves_operator_choice():
    rows = [{"id": 1, "name": "З-1", "diametercondit": 100.0, "damperarmaturestateid": 1},
            {"id": 2, "name": None, "diametercondit": 80.0, "damperarmaturestateid": 1}]
    conn = _transfer_conn(rows)
    rep = asyncio.run(transfer_dependents(conn, 10, 11, 0.5, 20, review_to_new={"dampers": [2]}))
    assert rep["review"]["dampers"] == 2
    assert rep["review_items"]["dampers"][0] == {
        "id": 1, "attrs": {"name": "З-1", "diametercondit": 100.0, "damperarmaturestateid": 1}}
    assert rep["review_moved"] == {"dampers": [2]} and rep["moved"]["dampers"] == 1


def test_transfer_rejects_foreign_ids_and_tables():
    conn = _transfer_conn([{"id": 1, "name": "x", "diametercondit": 1, "damperarmaturestateid": 1}])
    with pytest.raises(ValueError, match="не на участке"):
        asyncio.run(transfer_dependents(conn, 10, 11, 0.5, 20, review_to_new={"dampers": [99]}))
    with pytest.raises(ValueError, match="вне ручной проверки"):
        asyncio.run(transfer_dependents(conn, 10, 11, 0.5, 20, review_to_new={"nodes": [1]}))


def test_split_with_review_equipment_requires_resolution():
    report = {"moved": {}, "review": {"dampers": 1}, "skipped": [],
              "review_items": {"dampers": [{"id": 1, "attrs": {}}]}, "review_moved": {}}
    conn = FakeConn([
        _lock_rule({100: (0, TS, "5")}),
        ("ST_LineLocatePoint", {"nodeid1": 1, "nodeid2": 2, "split_fraction": 0.4}),
        ("FROM heatpipesections WHERE lineid", 1),  # участок — труба
        ("INSERT INTO nodes", 900),
        ("INSERT INTO linesobj", 901),
    ])
    with patch("database.topology.transfer_dependents", AsyncMock(return_value=report)) as td:
        with pytest.raises(TopologyDependencyError) as exc:
            _run(lambda: split_line(100, 76.9, 43.2), conn)
        assert exc.value.blockers["requires_resolution"] is True
        assert exc.value.blockers["review"] == {"dampers": [{"id": 1, "attrs": {}}]}
        # решение оператора передаётся в перенос; {} — «всё остаётся на первой половине»
        res, *_ = _run(lambda: split_line(100, 76.9, 43.2, review_to_new={}), conn)
        assert res["new_line_id"] == 901 and td.await_args.kwargs["review_to_new"] == {}


# --- HTTP --------------------------------------------------------------------

def test_router_maps_nothing_to_undo_to_404_and_exposes_paths():
    import main
    from routers.topology import _topology_http_error

    e = _topology_http_error(TopologyNothingToUndo("нет"), "x")
    assert e.status_code == 404 and e.detail["code"] == "nothing_to_undo"
    paths = main.app.openapi()["paths"]
    assert "post" in paths["/api/v1/topology/undo"] and "get" in paths["/api/v1/topology/undo"]
    assert "get" in paths["/api/v1/topology/line/{line_id}/geometry"]
