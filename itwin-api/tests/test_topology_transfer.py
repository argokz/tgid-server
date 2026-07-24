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


def test_topology_dependency_error_carries_blockers():
    from database.topology import TopologyDependencyError

    err = TopologyDependencyError("blocked", blockers={"incident_lines": [1, 2]})
    assert err.blockers["incident_lines"] == [1, 2]
    assert "blocked" in str(err)
