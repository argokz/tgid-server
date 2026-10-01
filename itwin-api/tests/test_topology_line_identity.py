"""QA F12/F54: участок карточки — linesobj.id, а не heatpipesections.id.

Слой GeoServer `id_heatpipesections` отдаёт id паспорта трубы; клиент передаёт его как
expected_section_id, сервер сверяет с паспортом участка и при расхождении отказывает (409),
не трогая чужой участок. GET /topology/line-ref переводит heatpipesections.id → linesobj.id.
"""

import asyncio

import pytest
from fastapi import HTTPException

from database.topology import (
    TopologyObjectMismatch,
    delete_line,
    get_line_ref,
    reverse_line,
)
from routers.topology import _topology_http_error
from tests.test_cad_topology import TS, FakeConn, _lock_rule, _run

# Прод/копия: участок 324386 ↔ паспорт 141949; id 141949 — другой живой участок.
LINE, SECTION = 324386, 141949
OTHER_LINE, OTHER_SECTION = 141949, 55555


def _ref(line_id, section_id):
    return {"line_id": line_id, "section_id": section_id, "fileid": 74,
            "nodeid1": 1, "nodeid2": 2, "removed": False}


def _refs():
    by_line = {LINE: _ref(LINE, SECTION), OTHER_LINE: _ref(OTHER_LINE, OTHER_SECTION)}
    by_section = {SECTION: _ref(LINE, SECTION), OTHER_SECTION: _ref(OTHER_LINE, OTHER_SECTION)}
    return [
        ("WHERE l.id = $1", lambda args: by_line.get(args[0])),
        ("WHERE h.id = $1", lambda args: by_section.get(args[0])),
    ]


def test_delete_line_refuses_when_card_section_belongs_to_other_line():
    # карточка несла heatpipesections.id (141949) как id участка — это чужой живой участок
    conn = FakeConn([_lock_rule({OTHER_LINE: (0, TS, "1")}), *_refs()])
    with pytest.raises(TopologyObjectMismatch) as exc:
        _run(lambda: delete_line(OTHER_LINE, expected_section_id=SECTION), conn)
    assert exc.value.details == {
        "line_id": OTHER_LINE, "expected_section_id": SECTION,
        "actual_section_id": OTHER_SECTION, "section_line_id": LINE,
    }
    assert f"относится к участку {LINE}" in str(exc.value)
    assert not conn.executed("UPDATE")


def test_delete_line_proceeds_when_section_matches():
    conn = FakeConn([_lock_rule({LINE: (0, TS, "1")}), *_refs()])
    res, *_ = _run(lambda: delete_line(LINE, expected_section_id=SECTION), conn)
    assert res["line_id"] == LINE
    assert [c[2][0] for c in conn.executed("UPDATE linesobj")] == [LINE]


def test_delete_line_without_expectation_keeps_old_behaviour():
    conn = FakeConn([_lock_rule({LINE: (0, TS, "1")})])
    _run(lambda: delete_line(LINE), conn)
    assert not any("heatpipesections WHERE lineid = l.id" in c[1] for c in conn.calls)


def test_reverse_dry_run_refuses_on_mismatch_before_touching_anything():
    conn = FakeConn([*_refs()])
    with pytest.raises(TopologyObjectMismatch):
        _run(lambda: reverse_line(OTHER_LINE, dry_run=True, expected_section_id=SECTION), conn)
    assert not conn.executed("UPDATE")
    assert not any("FOR UPDATE" in c[1] for c in conn.calls)


def test_mismatch_maps_to_409_object_mismatch():
    err = _topology_http_error(
        TopologyObjectMismatch("x", {"line_id": 1, "expected_section_id": 2}), "deleting line 1"
    )
    assert isinstance(err, HTTPException) and err.status_code == 409
    assert err.detail["code"] == "object_mismatch" and err.detail["expected_section_id"] == 2


def test_get_line_ref_resolves_section_to_line_and_validates_args():
    conn = FakeConn(_refs())
    res, *_ = _run(lambda: get_line_ref(section_id=SECTION), conn)
    assert res["line_id"] == LINE and res["section_id"] == SECTION
    missing, *_ = _run(lambda: get_line_ref(section_id=1), conn)
    assert missing is None
    with pytest.raises(ValueError):
        asyncio.run(get_line_ref())
    with pytest.raises(ValueError):
        asyncio.run(get_line_ref(line_id=1, section_id=2))
