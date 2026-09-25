"""Тесты CAD-редактирования топологии (реверс линий, слияние узлов, обновление геометрии).

Используют мокирование БД (asyncpg pool), проверяя логику, контракты и обработку ошибок.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from database.topology import (
    TopologyDependencyError,
    merge_nodes,
    reverse_line,
    update_line_geometry,
)


def _build_mock_pool(mock_conn):
    mock_tx = AsyncMock()
    mock_tx.__aenter__.return_value = mock_conn
    mock_tx.__aexit__.return_value = None
    mock_conn.transaction = MagicMock(return_value=mock_tx)

    mock_pool = MagicMock()
    mock_acquire = AsyncMock()
    mock_acquire.__aenter__.return_value = mock_conn
    mock_acquire.__aexit__.return_value = None
    mock_pool.acquire.return_value = mock_acquire
    return mock_pool


def _run(coro_factory, mock_conn, **patches):
    async def _inner():
        with patch("database.topology.get_pool", return_value=_build_mock_pool(mock_conn)), \
             patch("database.topology.invalidate_outage_cache") as invalidate, \
             patch("database.topology.line_dependency_report", AsyncMock(return_value=patches.get("line_deps", {}))), \
             patch("database.topology.node_dependency_report", AsyncMock(return_value=patches.get("node_deps", {}))):
            result = await coro_factory()
            return result, invalidate
    return asyncio.run(_inner())


def _line_conn():
    conn = AsyncMock()
    conn.fetchrow.return_value = {"id": 100, "nodeid1": 10, "nodeid2": 20, "shape": "LINESTRING(0 0, 10 10)"}
    conn.execute.return_value = "UPDATE 1"
    return conn


def test_reverse_line_success():
    res, invalidate = _run(lambda: reverse_line(100), _line_conn(), line_deps={"dampers": 2})
    assert res == {"success": True, "line_id": 100, "nodeid1": 20, "nodeid2": 10}
    invalidate.assert_called_once()


def test_reverse_line_blocked_by_directional_equipment():
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: reverse_line(100), _line_conn(), line_deps={"diaphragms": 1, "dampers": 2})
    assert exc.value.blockers == {"equipment": {"diaphragms": 1}}


def test_reverse_line_not_found():
    conn = AsyncMock()
    conn.fetchrow.return_value = None
    with pytest.raises(ValueError, match="не найдена"):
        _run(lambda: reverse_line(999), conn)


def test_merge_nodes_same_node_error():
    with pytest.raises(ValueError, match="Невозможно объединить узел с самим собой"):
        asyncio.run(merge_nodes(5, 5))


def _merge_conn(source_fileid=7, internal_lines=0, connecting=()):
    conn = AsyncMock()
    conn.fetchrow.side_effect = [
        {"id": 1, "shape": "POINT(0 0)", "fileid": 7},
        {"id": 2, "shape": "POINT(1 1)", "fileid": source_fileid},
    ]
    conn.fetchval.return_value = internal_lines
    conn.fetch.side_effect = [
        [{"id": lid} for lid in connecting],   # участки между узлами
        [{"id": 10}, {"id": 11}],               # nodeid1 = source
        [{"id": 12}],                           # nodeid2 = source
    ]
    conn.execute.return_value = "UPDATE 1"
    return conn


def test_merge_nodes_success_moves_consumers_and_ignores_results():
    conn = _merge_conn(connecting=[50])
    res, invalidate = _run(
        lambda: merge_nodes(1, 2), conn,
        node_deps={"generalizedconsumers.nodeid": 3, "us_out.nodeid": 2},
    )
    assert res["success"] is True
    assert res["merged_lines"] == 3
    assert res["removed_lines"] == [50]
    invalidate.assert_called_once()
    sql = " ".join(str(c.args[0]) for c in conn.execute.call_args_list)
    assert "UPDATE generalizedconsumers SET nodeid" in sql
    assert "UPDATE linesobj SET removed = 1" in sql


def test_merge_nodes_blocked_by_references():
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: merge_nodes(1, 2), _merge_conn(), node_deps={"pressregulators.nodeid": 1})
    assert exc.value.blockers == {"references": {"pressregulators.nodeid": 1}}


def test_merge_nodes_blocked_by_internal_scheme():
    with pytest.raises(TopologyDependencyError) as exc:
        _run(lambda: merge_nodes(1, 2), _merge_conn(internal_lines=4))
    assert exc.value.blockers == {"internal_scheme_lines": 4}


def test_merge_nodes_rejects_other_fragment():
    with pytest.raises(ValueError, match="разных фрагментов"):
        _run(lambda: merge_nodes(1, 2), _merge_conn(source_fileid=8))


def test_update_line_geometry_validation():
    with pytest.raises(ValueError, match="как минимум 2 точки"):
        asyncio.run(update_line_geometry(1, [[76.9, 43.2]]))


def _geometry_conn(distance):
    conn = AsyncMock()
    conn.fetchrow.side_effect = [
        {"id": 10, "nodeid1": 1, "nodeid2": 2},
        {"d_start_node": distance, "d_end_node": 0.1, "d_start_old": distance, "d_end_old": 0.1},
    ]
    conn.fetchval.return_value = 142.50
    conn.execute.return_value = "UPDATE 1"
    return conn


def test_update_line_geometry_success_snaps_ends_to_nodes():
    coords = [[76.90, 43.20], [76.91, 43.21], [76.92, 43.22]]
    conn = _geometry_conn(0.4)
    res, invalidate = _run(lambda: update_line_geometry(10, coords), conn)
    assert res == {"success": True, "line_id": 10, "new_length": 142.5}
    assert "ST_SetPoint" in conn.fetchval.call_args.args[0]
    invalidate.assert_called_once()


def test_update_line_geometry_rejects_detached_end():
    coords = [[76.90, 43.20], [76.92, 43.22]]
    with pytest.raises(ValueError, match="должны оставаться у его узлов"):
        _run(lambda: update_line_geometry(10, coords), _geometry_conn(80.0))
