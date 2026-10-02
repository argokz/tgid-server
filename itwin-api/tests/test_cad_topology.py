"""Тесты редактора топологии: оптимистичная блокировка, merge/reverse с dry-run, геометрия.

БД подменяется FakeConn: ответы выбираются по подстроке SQL, все вызовы записываются —
тесты проверяют и результат, и то, какие изменения реально ушли в БД.
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest

from database.topology import (
    TopologyConflictError,
    TopologyDependencyError,
    create_line,
    delete_line,
    merge_nodes,
    move_node,
    reverse_line,
    split_line,
    update_line_geometry,
    version_matches,
    version_token,
)

TS = datetime(2026, 9, 1, 12, 0, 0, 123456)
TOKEN = version_token(TS, "777")


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeConn:
    """Ответ — первое правило, чья подстрока есть в SQL: значение или callable(args)."""

    def __init__(self, rules=None):
        self.rules = list(rules or [])
        self.calls: list[tuple[str, str, tuple]] = []

    def transaction(self):
        return _Tx()

    def _answer(self, method, sql, args, default):
        self.calls.append((method, sql, args))
        for needle, value in self.rules:
            if needle in sql:
                return value(args) if callable(value) else value
        return default

    async def fetch(self, sql, *args):
        return self._answer("fetch", sql, args, [])

    async def fetchrow(self, sql, *args):
        return self._answer("fetchrow", sql, args, None)

    async def fetchval(self, sql, *args):
        return self._answer("fetchval", sql, args, 0)

    async def execute(self, sql, *args):
        return self._answer("execute", sql, args, "UPDATE 1")

    def executed(self, needle):
        return [c for c in self.calls if c[0] == "execute" and needle in c[1]]


class _Pool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _Acq:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *a):
                return False

        return _Acq()


def _lock_rule(rows_by_id):
    """Правило для SELECT … FOR UPDATE версий: rows_by_id {id: (removed, ts, xmin)}."""
    def answer(args):
        return [
            {"id": i, "removed": r[0], "archivechangedate": r[1], "xmin": r[2]}
            for i, r in rows_by_id.items() if i in args[0]
        ]
    return ("ORDER BY id FOR UPDATE", answer)


def _run(coro_factory, conn, **patches):
    audit = AsyncMock()

    async def _inner():
        with patch("database.topology.get_pool", return_value=_Pool(conn)), \
             patch("database.topology.invalidate_outage_cache") as invalidate, \
             patch("database.topology.write_audit_log", audit), \
             patch("database.topology.line_dependency_report", AsyncMock(return_value=patches.get("line_deps", {}))), \
             patch("database.topology.node_dependency_report", AsyncMock(return_value=patches.get("node_deps", {}))), \
             patch("database.topology.plan_line_reverse", AsyncMock(return_value=patches.get("reverse_plan", {
                 "directional": {}, "node_bound": {}, "neutral": {}, "diaphragm_locations": {}}))), \
             patch("database.topology.plan_node_merge", AsyncMock(return_value=patches.get("merge_plan", {
                 "transfer": {}, "results_skipped": {}, "conflicts": {}}))), \
             patch("database.topology.apply_node_merge", AsyncMock(return_value=patches.get("merged", {}))) as apply:
            result = await coro_factory()
            return result, invalidate, audit, apply
    return asyncio.run(_inner())


# --- версии ---------------------------------------------------------------

def test_version_token_and_matching():
    assert TOKEN == "2026-09-01T12:00:00.123456#777"
    assert version_matches(TOKEN, TS, "777")
    assert not version_matches(TOKEN, TS, "778")  # строку переписали, дата та же
    # голая дата из карточки объекта сравнивается только с archivechangedate
    assert version_matches("2026-09-01T12:00:00.123456", TS, "999")
    assert not version_matches("2026-09-01T12:00:00", TS, "777")
    assert version_matches("", None, "1")
    assert version_token(None, 5) == "#5"
    assert not version_matches("not-a-date", TS, "777")


# --- reverse ----------------------------------------------------------------

def _line_conn(sign=4, removed=0, ts=TS, xmin="777"):
    return FakeConn([
        _lock_rule({100: (removed, ts, xmin)}),
        ("SELECT nodeid1, nodeid2, externalsignlineid", {
            "nodeid1": 10, "nodeid2": 20, "externalsignlineid": sign, "points": 3, "length": 42.0}),
        ("SELECT id, archivechangedate, xmin::text", [{"id": 100, "archivechangedate": ts, "xmin": "900"}]),
    ])


def test_reverse_line_swaps_nodes_geometry_and_external_sign():
    conn = _line_conn(sign=4)
    res, invalidate, audit, _ = _run(lambda: reverse_line(100, expected_version=TOKEN, actor="u"), conn)
    assert res["success"] is True
    assert (res["nodeid1"], res["nodeid2"]) == (20, 10)
    assert res["after"]["externalsignlineid"] == 5  # подающий-обратный -> обратный-подающий
    (_, sql, args), = conn.executed("UPDATE linesobj")
    assert "ST_Reverse" in sql and args[:4] == (100, 20, 10, 5)
    assert res["versions"] == {"line:100": version_token(TS, "900")}
    audit.assert_awaited_once()
    assert audit.await_args.kwargs["conn"] is conn  # аудит — в той же транзакции
    invalidate.assert_called_once()


def test_reverse_dry_run_reports_without_writing():
    plan = {"directional": {}, "node_bound": {}, "neutral": {"diaphragms": 2},
            "diaphragm_locations": {"Подпорная": 2}}
    conn = _line_conn(sign=1)
    res, invalidate, audit, _ = _run(lambda: reverse_line(100, dry_run=True), conn, reverse_plan=plan)
    assert res["dry_run"] is True
    assert res["equipment"]["neutral"] == {"diaphragms": 2}
    assert res["requires_confirmation"] is False
    assert res["versions"] == {"line:100": TOKEN}
    assert not conn.executed("UPDATE linesobj")
    audit.assert_not_awaited()
    invalidate.assert_not_called()


def test_reverse_directional_equipment_needs_confirmation():
    plan = {"directional": {"pumps": 1}, "node_bound": {}, "neutral": {}, "diaphragm_locations": {}}
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: reverse_line(100), _line_conn(), reverse_plan=plan)
    assert exc.value.blockers == {"equipment": {"pumps": 1}, "requires_confirmation": True}

    conn = _line_conn()
    res, *_ = _run(lambda: reverse_line(100, accept_direction_change=True), conn, reverse_plan=plan)
    assert res["success"] is True and conn.executed("UPDATE linesobj")


def test_reverse_version_conflict_is_409_and_writes_nothing():
    conn = _line_conn(xmin="778")
    with pytest.raises(TopologyConflictError) as exc:
        _run(lambda: reverse_line(100, expected_version=TOKEN), conn)
    assert exc.value.conflicts["line:100"]["actual"] == version_token(TS, "778")
    assert not conn.executed("UPDATE")


def test_reverse_removed_line_with_version_is_conflict():
    with pytest.raises(TopologyConflictError) as exc:
        _run(lambda: reverse_line(100, expected_version=TOKEN), _line_conn(removed=1))
    assert exc.value.conflicts["line:100"]["removed"] is True


def test_reverse_line_not_found():
    with pytest.raises(ValueError, match="не найден"):
        _run(lambda: reverse_line(999), FakeConn())


# --- merge ------------------------------------------------------------------

def test_merge_nodes_same_node_error():
    with pytest.raises(ValueError, match="Невозможно объединить узел с самим собой"):
        asyncio.run(merge_nodes(5, 5))


def _merge_conn(source_fileid=7, target_shape=True, connecting=(), incident=(), source_removed=0):
    return FakeConn([
        _lock_rule({1: (0, TS, "11"), 2: (source_removed, TS, "22")}),
        ("SELECT id, fileid, internalnodeid", [
            {"id": 1, "fileid": 7, "internalnodeid": None, "x": 100.0, "y": -200.0,
             "has_shape": target_shape, "lng": 76.9, "lat": 43.2},
            {"id": 2, "fileid": source_fileid, "internalnodeid": None, "x": 0.0, "y": 0.0,
             "has_shape": True, "lng": 76.9, "lat": 43.2},
        ]),
        ("SELECT ST_Distance", 12.5),
        ("NOT (id = ANY($2::int[]))", [{"id": lid, "nodeid1": 2, "nodeid2": 90 + lid} for lid in incident]),
        ("(nodeid1 = $1 AND nodeid2 = $2)", [{"id": lid} for lid in connecting]),
        ("SELECT id, archivechangedate, xmin::text", lambda a: [
            {"id": i, "archivechangedate": TS, "xmin": "33"} for i in a[0]]),
    ])


def test_merge_dry_run_reports_transfer_and_writes_nothing():
    plan = {"transfer": {"pressregulators.nodeid": 1, "deployeddirections.nodeid": 2},
            "results_skipped": {"us_out.nodeid": 3}, "conflicts": {}}
    conn = _merge_conn(connecting=[50], incident=[10, 11])
    res, invalidate, audit, apply = _run(lambda: merge_nodes(1, 2, dry_run=True), conn, merge_plan=plan)
    assert res["dry_run"] is True
    assert res["transfer"] == plan["transfer"]
    assert res["results_skipped"] == {"us_out.nodeid": 3}
    assert res["removed_lines"] == [50] and res["relinked_lines"] == [10, 11]
    assert res["distance_m"] == 12.5 and res["blockers"] == {}
    assert res["versions"] == {"node:1": version_token(TS, "11"), "node:2": version_token(TS, "22")}
    assert not conn.executed("UPDATE")
    apply.assert_not_awaited()
    audit.assert_not_awaited()
    invalidate.assert_not_called()


def test_merge_success_transfers_all_references_in_one_transaction():
    plan = {"transfer": {"generalizedconsumers.nodeid": 3}, "results_skipped": {}, "conflicts": {}}
    conn = _merge_conn(connecting=[50], incident=[10])
    res, invalidate, audit, apply = _run(
        lambda: merge_nodes(1, 2, target_version=version_token(TS, "11"), actor="u"),
        conn, merge_plan=plan, merged={"generalizedconsumers.nodeid": 3},
    )
    assert res["success"] is True
    assert res["transferred"] == {"generalizedconsumers.nodeid": 3}
    assert res["merged_lines"] == 1 and res["removed_lines"] == [50]
    apply.assert_awaited_once()
    assert conn.executed("UPDATE linesobj SET removed = 1")  # safe-delete соединяющего участка
    assert conn.executed("SET nodeid1 = $1") and conn.executed("SET nodeid2 = $1")
    assert conn.executed("UPDATE nodes SET removed = 1")
    assert audit.await_args.kwargs["conn"] is conn and audit.await_args.kwargs["operation"] == "MERGE"
    invalidate.assert_called_once()


def test_merge_blockers_raise_on_apply_but_return_in_dry_run():
    plan = {"transfer": {}, "results_skipped": {},
            "conflicts": {"heatchambers.nodeid": {"source": 1, "target": 1}}}
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: merge_nodes(1, 2), _merge_conn(connecting=[50]), merge_plan=plan,
             line_deps={"dampers": 1})
    assert exc.value.blockers == {
        "connecting_lines": {"50": {"dampers": 1}},
        "conflicting_references": {"heatchambers.nodeid": {"source": 1, "target": 1}},
    }
    res, *_ = _run(lambda: merge_nodes(1, 2, dry_run=True), _merge_conn(connecting=[50]),
                   merge_plan=plan, line_deps={"dampers": 1})
    assert set(res["blockers"]) == {"connecting_lines", "conflicting_references"}


def test_merge_other_fragment_and_target_without_geometry_block():
    res, *_ = _run(lambda: merge_nodes(1, 2, dry_run=True), _merge_conn(source_fileid=8, target_shape=False))
    assert res["blockers"]["different_fragments"] == {"target": 7, "source": 8}
    assert res["blockers"]["target_without_geometry"] == {"x": 100.0, "y": -200.0}


def test_merge_removed_source_is_version_conflict():
    conn = _merge_conn(source_removed=1)
    with pytest.raises(TopologyConflictError) as exc:
        _run(lambda: merge_nodes(1, 2, source_version=version_token(TS, "22")), conn)
    assert exc.value.conflicts == {"node:2": {"expected": version_token(TS, "22"), "actual": None, "removed": True}}
    assert not conn.executed("UPDATE")


# --- move / create / delete / split ----------------------------------------

def test_move_node_checks_version_before_update():
    conn = FakeConn([_lock_rule({5: (0, TS, "1")})])
    with pytest.raises(TopologyConflictError):
        _run(lambda: move_node(5, 76.9, 43.2, expected_version=version_token(TS, "0")), conn)
    assert not conn.executed("UPDATE")

    conn = FakeConn([_lock_rule({5: (0, TS, "1")})])
    res, _, audit, _ = _run(lambda: move_node(5, 76.9, 43.2, expected_version=version_token(TS, "1"), actor="u"), conn)
    assert res["node_id"] == 5 and conn.executed("UPDATE nodes SET")
    assert audit.await_args.kwargs["operation"] == "MOVE"


def test_create_line_locks_both_nodes():
    conn = FakeConn([_lock_rule({1: (0, TS, "1"), 2: (0, TS, "2")}), ("SELECT count(*) FROM nodes", 2)])
    with pytest.raises(TopologyConflictError) as exc:
        _run(lambda: create_line(1, 2, nodeid1_version=version_token(TS, "1"),
                                 nodeid2_version=version_token(TS, "9")), conn)
    assert list(exc.value.conflicts) == ["node:2"]


def _ends_rule(rows):
    return ("SELECT id, fileid, externalcodeid, internalnodeid FROM nodes", [
        {"id": i, "fileid": f, "externalcodeid": c, "internalnodeid": inn} for i, f, c, inn in rows
    ])


def test_create_line_rejects_nodes_without_code():
    """Узел без externalcodeid: участок не увидят ни sety, ни слой карты — 400, без вставки."""
    conn = FakeConn([
        _lock_rule({1: (0, TS, "1"), 2: (0, TS, "2")}),
        ("SELECT count(*) FROM nodes", 2),
        _ends_rule([(1, 74, 25, None), (2, 74, None, None)]),
    ])
    with pytest.raises(ValueError, match="2"):
        _run(lambda: create_line(1, 2), conn)
    assert not conn.executed("INSERT")
    assert not [c for c in conn.calls if "INSERT INTO linesobj" in c[1]]

    conn = FakeConn([
        _lock_rule({1: (0, TS, "1"), 2: (0, TS, "2")}),
        ("SELECT count(*) FROM nodes", 2),
        _ends_rule([(1, 74, 25, None), (2, 5, 25, None)]),
    ])
    with pytest.raises(ValueError, match="разных фрагментов"):
        _run(lambda: create_line(1, 2), conn)


def test_create_line_copies_passport_from_adjacent_line():
    conn = FakeConn([
        _lock_rule({1: (0, TS, "1"), 2: (0, TS, "2")}),
        ("SELECT count(*) FROM nodes", 2),
        _ends_rule([(1, 74, 25, None), (2, 74, 25, None)]),
        ("INSERT INTO linesobj", 500),
        ("AS passport_id", {"passport_id": 70, "line_id": 42, "adjacent": True}),
    ])
    with patch("database.topology.table_columns",
               AsyncMock(return_value=("id", "lineid", "diametercondit", "diameterinternal", "damagenum"))):
        res, _, audit, _ = _run(lambda: create_line(1, 2, actor="u"), conn)
    assert res["id"] == 500
    assert res["passport"] == {"source": "adjacent_line", "template_line_id": 42}
    sql, args = conn.executed("INSERT INTO heatpipesections")[0][1:]
    # конструктив — от образца; повреждения и прочее — нет; длина — по новой геометрии
    assert '"diametercondit"' in sql and '"diameterinternal"' in sql and "damagenum" not in sql
    assert "ST_Length" in sql and args == (500, 70)
    assert audit.await_args.kwargs["new_data"]["passport"]["template_line_id"] == 42


def test_create_line_without_template_uses_table_defaults():
    conn = FakeConn([
        _lock_rule({1: (0, TS, "1"), 2: (0, TS, "2")}),
        ("SELECT count(*) FROM nodes", 2),
        _ends_rule([(1, 74, 25, None), (2, 74, 25, None)]),
        ("INSERT INTO linesobj", 501),
    ])
    res, _, _, _ = _run(lambda: create_line(1, 2), conn)
    assert res["passport"] == {"source": "defaults", "template_line_id": None}
    assert conn.executed("INSERT INTO heatpipesections (lineid, pipesectlength) VALUES")


def test_delete_line_conflict_on_stale_card_date():
    conn = FakeConn([_lock_rule({7: (0, TS, "1")})])
    with pytest.raises(TopologyConflictError):
        _run(lambda: delete_line(7, expected_version="2020-01-01T00:00:00"), conn)
    assert not conn.executed("UPDATE")


def test_split_dry_run_returns_version_and_clone_avoids_h_column():
    conn = FakeConn([
        _lock_rule({100: (0, TS, "5")}),
        ("ST_LineLocatePoint", {"nodeid1": 1, "nodeid2": 2, "split_fraction": 0.4}),
        ("FROM heatpipesections WHERE lineid", 1),  # участок — труба
        ("INSERT INTO nodes", 900),
        ("INSERT INTO linesobj", 901),
    ])
    with patch("database.topology.transfer_dependents", AsyncMock(return_value={"moved": {}, "review": {}, "skipped": []})):
        res, _, audit, _ = _run(lambda: split_line(100, 76.9, 43.2, dry_run=True), conn)
    assert res["dry_run"] is True and res["versions"] == {"line:100": version_token(TS, "5")}
    audit.assert_not_awaited()
    clone = conn.executed("INSERT INTO heatpipesections")[0][1]
    # у heatpipesections есть колонка «h»: to_jsonb(h) взял бы её вместо строки
    assert "to_jsonb(hps)" in clone and "FROM heatpipesections hps" in clone
    node_insert = [c for c in conn.calls if "INSERT INTO nodes" in c[1]][0][1]
    assert "fileid" in node_insert and "externalcodeid" in node_insert


# --- geometry ---------------------------------------------------------------

def test_update_line_geometry_validation():
    with pytest.raises(ValueError, match="как минимум 2 точки"):
        asyncio.run(update_line_geometry(1, [[76.9, 43.2]]))


def _geometry_conn(distance):
    return FakeConn([
        _lock_rule({10: (0, TS, "1")}),
        ("SELECT id, nodeid1, nodeid2 FROM linesobj", {"id": 10, "nodeid1": 1, "nodeid2": 2}),
        ("WITH g AS", {"d_start_node": distance, "d_end_node": 0.1, "d_start_old": distance, "d_end_old": 0.1}),
        ("RETURNING round(ST_Length", 142.50),
    ])


def test_update_line_geometry_success_snaps_ends_to_nodes():
    coords = [[76.90, 43.20], [76.91, 43.21], [76.92, 43.22]]
    conn = _geometry_conn(0.4)
    res, invalidate, _, _ = _run(lambda: update_line_geometry(10, coords, expected_version=version_token(TS, "1")), conn)
    assert res["success"] is True and res["new_length"] == 142.5
    assert any("ST_SetPoint" in c[1] for c in conn.calls if c[0] == "fetchval")
    invalidate.assert_called_once()


def test_update_line_geometry_rejects_detached_end():
    coords = [[76.90, 43.20], [76.92, 43.22]]
    with pytest.raises(ValueError, match="должны оставаться у его узлов"):
        _run(lambda: update_line_geometry(10, coords), _geometry_conn(80.0))


# --- HTTP-отображение ошибок ------------------------------------------------

def test_router_maps_conflicts_and_blockers_to_409():
    from routers.topology import _topology_http_error

    e = _topology_http_error(TopologyConflictError({"node:1": {"removed": True}}), "x")
    assert e.status_code == 409 and e.detail["code"] == "version_conflict"
    e = _topology_http_error(TopologyDependencyError("b", {"equipment": {}}), "x")
    assert e.status_code == 409 and e.detail["code"] == "blocked" and "blockers" in e.detail
    assert _topology_http_error(ValueError("bad"), "x").status_code == 400

def test_split_refuses_equipment_link_without_pipe_passport():
    """Звено-задвижка (нет heatpipesections): половина без объекта выпала бы из расчёта."""
    conn = FakeConn([
        _lock_rule({100: (0, TS, "5")}),
        ("ST_LineLocatePoint", {"nodeid1": 1, "nodeid2": 2, "split_fraction": 0.4}),
    ])
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: split_line(100, 76.9, 43.2, dry_run=True), conn, line_deps={"dampers": 2})
    assert exc.value.blockers == {"not_a_pipe": {"dampers": 2}}
    assert not [c for c in conn.calls if "INSERT" in c[1]]
