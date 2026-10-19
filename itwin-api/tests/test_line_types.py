"""Тип линии — участок ↔ оборудование (database/line_types) и поля новой карточки узла.

БД — FakeConn из test_cad_topology: ответы по подстроке SQL, все вызовы записываются.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from database.line_types import change_line_type, check_line_type, line_cards
from database.node_types import check_card_values
from database.topology_cad import normalize_points
from tests.test_cad_topology import TOKEN, TS, FakeConn, _lock_rule, _Pool

TABLES = ["heatpipesections", "pumps", "pressregulators", "consumptregulators", "dampers", "regularmatures",
          "bypass", "diaphragms", "pressdropregulators", "reversevalves", "elevators", "systemradiators",
          "heatexchangers", "airheaters"]


def _run(factory, conn):
    audit = AsyncMock()

    async def inner():
        with patch("database.topology.get_pool", return_value=_Pool(conn)), \
             patch("database.topology.write_audit_log", audit), \
             patch("database.topology.invalidate_outage_cache") as inv:
            return await factory(), inv

    (res, inv), = [asyncio.run(inner())]
    return res, audit, inv


def _line_conn(*, cards, pair=None, signs=None):
    """cards {line_id: {таблица: [id]}}; pair — id парной трубы линии 20."""
    signs = signs or {20: 1}

    def card_rows(table):
        return lambda args: [{"id": i} for i in cards.get(args[0], {}).get(table, [])]

    rules = [
        _lock_rule({20: (0, TS, "777"), 21: (0, TS, "778")}),
        ("information_schema.tables", lambda args: [{"table_name": t} for t in TABLES if t in args[0]]),
        ("FROM linesobj a", {"id": pair, "matched_by": "coords", "deviation": None} if pair else None),
        ("SELECT id, externalsignlineid FROM linesobj", [{"id": k, "externalsignlineid": v} for k, v in signs.items()]),
    ]
    for t in TABLES:
        rules.append((f"SELECT id FROM {t} WHERE lineid", card_rows(t)))
    rules.append(("INSERT INTO", 901))
    return FakeConn(rules)


def test_line_cards_detects_kind_and_conflict():
    conn = _line_conn(cards={20: {"heatpipesections": [5], "dampers": [8]}})
    info = asyncio.run(line_cards(conn, 20))
    assert info["kind"] == "line"
    assert info["conflict"] is True
    assert [c["table"] for c in info["cards"]] == ["heatpipesections", "dampers"]
    assert asyncio.run(line_cards(_line_conn(cards={}), 20))["kind"] == "none"


def test_section_to_damper_deletes_passport_and_creates_card():
    conn = _line_conn(cards={20: {"heatpipesections": [5]}})
    res, audit, inv = _run(lambda: change_line_type(20, "damper", expected_version=TOKEN, actor="u"), conn)
    assert (res["old_type"], res["new_type"]) == ("line", "damper")
    assert res["lines"][0]["removed_cards"] == [{"table": "heatpipesections", "kind": "line", "id": 5}]
    assert res["lines"][0]["created_card"] == {"table": "dampers", "kind": "damper", "id": 901, "line_id": 20}
    assert conn.executed("DELETE FROM heatpipesections WHERE id")
    ins = [c for c in conn.calls if c[1].startswith("INSERT INTO dampers")]
    assert ins and ins[0][2] == (20,)
    assert conn.executed("UPDATE linesobj SET archivechangedate")
    audit.assert_awaited_once()
    inv.assert_called_once()


def test_pair_changes_both_and_regulator_gets_pipeline_sign():
    conn = _line_conn(cards={20: {"heatpipesections": [5]}, 21: {"heatpipesections": [6]}}, pair=21,
                      signs={20: 2, 21: 3})
    res, _, _ = _run(lambda: change_line_type(20, "pressregulator", expected_version=TOKEN), conn)
    assert res["pair_line_id"] == 21
    assert [x["line_id"] for x in res["lines"]] == [20, 21]
    ins = [c[2] for c in conn.calls if c[1].startswith("INSERT INTO pressregulators")]
    assert ins == [(20, 1), (21, 2)]  # подача — 1, обратка — 2, как ch_type_line


def test_back_to_section_inserts_passport_with_length():
    conn = _line_conn(cards={20: {"dampers": [8]}})
    res, _, _ = _run(lambda: change_line_type(20, "line", expected_version=TOKEN), conn)
    assert res["new_type"] == "line"
    sql = next(c[1] for c in conn.calls if "INSERT INTO heatpipesections" in c[1])
    assert "pipesectlength" in sql and "COALESCE" in sql


def test_same_type_and_unknown_types_are_rejected():
    conn = _line_conn(cards={20: {"dampers": [8]}})
    with pytest.raises(ValueError, match="уже имеет тип"):
        _run(lambda: change_line_type(20, "damper", expected_version=TOKEN), conn)
    with pytest.raises(ValueError, match="не задаётся"):
        check_line_type("elevator")


def test_dry_run_does_not_invalidate_outages():
    conn = _line_conn(cards={20: {"heatpipesections": [5]}})
    res, _, inv = _run(lambda: change_line_type(20, "pump", dry_run=True, expected_version=TOKEN), conn)
    assert res["new_type"] == "pump"
    inv.assert_not_called()


def test_card_values_only_known_text_fields():
    assert check_card_values("PR", {"name": "  ул. Абая, 10 ", "housenumber": "10", }) == {
        "name": "ул. Абая, 10", "housenumber": "10"}
    assert check_card_values("PR", {"name": "", "housenumber": None}) == {}
    with pytest.raises(ValueError):
        check_card_values("PR", {"streetid": "5"})
    with pytest.raises(ValueError):
        check_card_values("US", {"name": "x"})


def test_chain_card_only_for_new_typed_node():
    pts = normalize_points([
        {"kind": "node", "node_id": 5},
        {"kind": "new", "lng": 76.9, "lat": 43.2, "node_type": "PR", "card": {"name": "Абая, 10"}},
    ])
    assert pts[-1]["card"] == {"name": "Абая, 10"}
    with pytest.raises(ValueError, match="только новому узлу"):
        normalize_points([
            {"kind": "node", "node_id": 5, "card": {"name": "x"}},
            {"kind": "new", "lng": 76.9, "lat": 43.2},
        ])
