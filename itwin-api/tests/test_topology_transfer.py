"""Тесты карты правил переноса зависимых объектов при разрезании участка.

Проверяют чистую логику (структуру правил и генерацию SQL) без БД. Валидация SQL
на реальной схеме делается отдельно через PREPARE (scripts), здесь — контракт.
"""

import pytest

from database.topology_transfer import (
    SPLIT_TRANSFER_RULES,
    TransferKind,
    TransferRule,
    geometry_transfer_sql,
    node_transfer_sql,
    review_count_sql,
)


def test_rules_are_unique_tables():
    tables = [r.table for r in SPLIT_TRANSFER_RULES]
    assert len(tables) == len(set(tables)), "дублирующиеся таблицы в карте правил"


def test_node_rules_have_node_column():
    for r in SPLIT_TRANSFER_RULES:
        if r.kind is TransferKind.NODE:
            assert r.node_column, f"{r.table}: NODE-правило без node_column"
        else:
            assert r.node_column is None, f"{r.table}: node_column задан не для NODE"


def test_no_geometric_tables_in_map():
    # По факту схемы у геом.таблиц lineid всегда NULL — их не должно быть в карте
    forbidden = {"lyuki", "opora", "ugol_povorota_truboprovoda", "vvody_v_zdanie", "vvod_v_zdanie"}
    tables = {r.table for r in SPLIT_TRANSFER_RULES}
    assert not (tables & forbidden), "геометрические таблицы не переносятся по lineid"


def test_heatpipesections_not_in_map():
    # Паспорт 1:1 клонируется отдельно, в карте его быть не должно
    assert all(r.table != "heatpipesections" for r in SPLIT_TRANSFER_RULES)


def test_expected_equipment_flagged_for_review():
    review = {r.table for r in SPLIT_TRANSFER_RULES if r.kind is TransferKind.REVIEW}
    # Оборудование с реальным FK на линию, но без узла/позиции — должно флагироваться
    assert {"dampers", "diaphragms", "elevators", "pumps"} <= review


def test_regulators_are_node_transfer():
    node = {r.table for r in SPLIT_TRANSFER_RULES if r.kind is TransferKind.NODE}
    assert {"pressregulators", "consumptregulators", "pressdropregulators"} <= node


def test_node_sql_uses_params_and_columns():
    sql = node_transfer_sql("pressregulators", "nodeid")
    assert '"pressregulators"' in sql
    assert '"nodeid" = $3' in sql
    assert "SET lineid = $2" in sql
    assert "WHERE d.lineid = $1" in sql


def test_geometry_sql_projects_point():
    sql = geometry_transfer_sql("opora")
    assert "ST_LineLocatePoint" in sql
    assert ">= $3" in sql  # доля >= split_fraction → на новую половину


def test_review_sql_counts_only():
    sql = review_count_sql("dampers")
    assert sql.strip().lower().startswith("select count(*)")
    assert '"dampers"' in sql
    assert "$1" in sql


def test_identifier_escaping_rejects_injection():
    with pytest.raises(ValueError):
        node_transfer_sql("dampers; DROP TABLE nodes;--", "nodeid")
    with pytest.raises(ValueError):
        review_count_sql("bad name")


def test_transfer_rule_is_frozen():
    r = TransferRule("dampers", TransferKind.REVIEW)
    with pytest.raises(Exception):
        r.table = "other"  # dataclass(frozen=True)


def test_dependency_report_helpers_exist():
    # safe-delete опирается на эти отчёты — контракт модуля
    from database.topology_transfer import line_dependency_report, node_dependency_report

    assert callable(node_dependency_report)
    assert callable(line_dependency_report)


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False


class _CountConn:
    """count(*) по {(table, column, node_id): n}; execute возвращает 'UPDATE n'."""

    def __init__(self, counts, tables=(), columns=(), rows=None):
        self.counts = counts
        self.tables = set(tables)
        self.columns = set(columns)
        self.rows = rows or {}
        self.executed = []

    def transaction(self):
        return _Tx()

    async def fetchval(self, sql, *args):
        if "information_schema.tables" in sql:
            return 1 if args[0] in self.tables else None
        if "information_schema.columns" in sql:
            return 1 if (args[0], args[1]) in self.columns else None
        for (table, col, node), n in self.counts.items():
            if f'"{table}"' in sql and (not col or f'"{col}"' in sql) and args[0] == node:
                return n
        return 0

    async def fetch(self, sql, *args):
        for table, rows in self.rows.items():
            if f'"{table}"' in sql or f" {table} " in sql:
                return rows
        return []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))
        return "UPDATE 2"


def test_node_ref_columns_filter():
    from database.topology_transfer import _is_node_ref_column

    assert not _is_node_ref_column("linesobj", "nodeid1")  # инцидентные линии — отдельно
    assert _is_node_ref_column("linesobj", "internalnodeid")
    assert _is_node_ref_column("pressregulators", "nodeid")
    assert _is_node_ref_column("defect", "remontnodeid")
    assert not _is_node_ref_column("defect", "remontlineid")


def test_merge_ref_kinds():
    from database.topology_transfer import MergeRefKind, merge_ref_kind

    assert merge_ref_kind("us_out", "nodeid") is MergeRefKind.RESULT
    assert merge_ref_kind("heatchambers", "nodeid") is MergeRefKind.SINGLETON
    assert merge_ref_kind("nodes", "internalnodeid") is MergeRefKind.INTERNAL
    assert merge_ref_kind("realconsumers", "nodeid") is MergeRefKind.MULTI
    assert merge_ref_kind("pressregulators", "nodeid") is MergeRefKind.MULTI


def test_node_ref_transfer_sql_params_and_escaping():
    from database.topology_transfer import node_ref_transfer_sql

    assert node_ref_transfer_sql("realconsumers", "nodeid") == (
        'UPDATE "realconsumers" SET "nodeid" = $2 WHERE "nodeid" = $1'
    )
    with pytest.raises(ValueError):
        node_ref_transfer_sql("realconsumers; DROP", "nodeid")


def test_plan_node_merge_classifies_transfer_conflicts_and_results(monkeypatch):
    import asyncio

    import database.topology_transfer as tt

    monkeypatch.setattr(tt, "_NODE_REF_CACHE", [
        ("realconsumers", "nodeid"),
        ("heatchambers", "nodeid"),
        ("setpressnodes", "nodeid"),
        ("nodes", "internalnodeid"),
        ("us_out", "nodeid"),
        ("wdodevices", "nodeid"),
    ])
    conn = _CountConn({
        ("realconsumers", "nodeid", 2): 1,
        ("heatchambers", "nodeid", 2): 1,
        ("heatchambers", "nodeid", 1): 1,   # у цели тоже камера — конфликт
        ("setpressnodes", "nodeid", 2): 1,  # у цели нет — переносится
        ("nodes", "internalnodeid", 2): 4,
        ("us_out", "nodeid", 2): 6,
    })
    plan = asyncio.run(tt.plan_node_merge(conn, 2, 1))
    assert plan["transfer"] == {"realconsumers.nodeid": 1, "setpressnodes.nodeid": 1, "nodes.internalnodeid": 4}
    assert plan["conflicts"] == {"heatchambers.nodeid": {"source": 1, "target": 1}}
    assert plan["results_skipped"] == {"us_out.nodeid": 6}

    moved = asyncio.run(tt.apply_node_merge(conn, 2, 1, plan))
    assert moved == {k: 2 for k in plan["transfer"]}
    assert all(args == (2, 1) for _, args in conn.executed)


def test_reverse_plan_classes_and_external_sign():
    import asyncio

    from database.topology_transfer import plan_line_reverse, reversed_external_sign

    assert reversed_external_sign(4) == 5 and reversed_external_sign(5) == 4
    assert reversed_external_sign(2) == 2 and reversed_external_sign(None) is None

    conn = _CountConn(
        {("pumps", "", 100): 1, ("diaphragms", "", 100): 2},
        tables={"pumps", "diaphragms", "pressregulators"},
        columns={("pressregulators", "nodeid"), ("diaphragms", "throtdiaphloc")},
        rows={
            "pressregulators": [{"id": 11, "nodeid": 20}],
            "diaphragms": [{"loc": "Подпорная", "n": 2}],
        },
    )
    plan = asyncio.run(plan_line_reverse(conn, 100, 10, 20))
    assert plan["directional"] == {"pumps": 1, "pressregulators": 1}
    assert plan["neutral"] == {"diaphragms": 2}
    assert plan["node_bound"]["pressregulators"] == [
        {"id": 11, "nodeid": 20, "position_before": "end", "position_after": "start"}
    ]
    assert plan["diaphragm_locations"] == {"Подпорная": 2}


def test_topology_dependency_error_carries_blockers():
    from database.topology import TopologyDependencyError

    err = TopologyDependencyError("blocked", blockers={"incident_lines": [1, 2]})
    assert err.blockers["incident_lines"] == [1, 2]
    assert "blocked" in str(err)
