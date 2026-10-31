"""Износ участков и приоритет ремонта (database/wear.py, routers/wear.py, ai/wear_plan.py). Без БД и сети."""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai import wear_plan  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import wear  # noqa: E402
from routers import ai as ai_router  # noqa: E402
from routers import wear as wear_router  # noqa: E402

AT = datetime(2026, 10, 23)


def test_balls_follow_gid6_thresholds():
    assert [wear.srok_ball(a) for a in (3, 7, 7.1, 15, 19.9, 20, 24.9, 25, 40)] == [1, 1, 2, 2, 3, 4, 4, 5, 5]
    assert wear.srok_ball(None) is None
    assert [wear.koef_povr_ball(k) for k in (0, 0.9, 1, 1.9, 2, 3.9, 4, 4.9, 5, 9)] == [1, 1, 2, 2, 3, 3, 4, 4, 5, 5]


def test_wear_percent_full_and_partial():
    full = {k: 5 for k in wear.WEIGHTS}
    assert wear.wear_percent(full) == (100.0, 100.0, 8)
    # как в gid6: срок 2, повреждаемость 1, остальное 0 → (0.3 + 0.2)·20 = 10 %
    partial = {"srok_ball": 2, "koef_povr_ball": 1}
    pct, known, filled = wear.wear_percent(partial)
    assert (pct, filled) == (10.0, 2) and known == pytest.approx(0.5 / 0.35 * 20, abs=0.01)
    assert wear.wear_percent({}) == (0.0, None, 0)
    assert [wear.category(p) for p in (0, 19.9, 20, 59.9, 60, 80, None)] == [1, 1, 2, 3, 4, 5, None]


def test_consequence_and_priority():
    assert wear.consequence(None, None, None) == 1.0
    assert wear.consequence(3, 4, 4) == 2.4
    assert wear.priority(50.0, 1.0, None) == 0.5
    assert wear.priority(50.0, 2.0, 2000) == pytest.approx(1.5)  # поток ограничен ×1.5
    assert wear.priority(None, 1.0, 10) is None


def _src(**kw):
    base = dict(hps_id=1, lineid=10, pipesectionid=None, fileid=74, length_m=100.0, diameter=200,
                firstpicdatehp=date(2000, 1, 1), lasttransdate=None, n_defects=0,
                vnesniivid=0, sostoborudovania=0, kategorii=0, vnesnkorrozia=0, vnunrenkorrozia=0, sostkonstrukz=0,
                breakconsumvolid=None, populdamageid=None, infrastrdamageid=None, flow_t_h=None)
    base.update(kw)
    return base


def test_assess_row_age_defects_and_relaying():
    a = wear.assess_row(_src(), AT)
    assert a["age_years"] == pytest.approx(26.8, abs=0.1) and a["srok_ball"] == 5 and a["age_source"] == "firstpic"
    assert a["koef_povr"] == 0.0 and a["koef_povr_ball"] == 1 and a["factors_filled"] == 2
    assert a["wear_pct"] == 19.0 and a["category"] == 3 and a["consequence"] == 1.0
    relaid = wear.assess_row(_src(lasttransdate=date(2024, 6, 1), n_defects=3, length_m=50.0,
                                  sostoborudovania=4, breakconsumvolid=3, flow_t_h=-900.0), AT)
    assert relaid["age_source"] == "lasttrans" and relaid["srok_ball"] == 1
    assert relaid["koef_povr"] == 6.0 and relaid["koef_povr_ball"] == 5 and relaid["factors_filled"] == 3
    assert relaid["consequence"] == 1.6 and relaid["flow_t_h"] == -900.0 and relaid["priority"] > a["priority"]
    none = wear.assess_row(_src(firstpicdatehp=None, length_m=0), AT)
    assert none["age_source"] == "none" and none["srok_ball"] is None and none["koef_povr"] is None
    assert none["wear_pct_known"] is None and none["category"] is None and none["priority"] is None


class FakeConn:
    def __init__(self, rows, exists=True, snapped=(), unplaced=0, srids=(9995, 9995)):
        self.rows, self.exists, self.inserted, self.executed = rows, exists, [], []
        self.next_id = 7
        self.snapped, self.unplaced, self.srids, self.snap_args = list(snapped), unplaced, srids, None

    async def fetchval(self, sql, *args):
        if "to_regclass" in sql:
            return self.exists
        if "INSERT INTO calculation_iznos" in sql:
            return self.next_id
        if "FROM defect WHERE lineid IS NULL" in sql:
            return self.unplaced
        if "COUNT(*)" in sql:
            return len(self.rows)
        if "MAX(calculationid)" in sql:
            return self.next_id
        raise AssertionError(sql)

    async def fetch(self, sql, *args):
        if "ST_SRID" in sql:
            return [{"d": self.srids[0], "l": self.srids[1]}]
        if "CROSS JOIN LATERAL" in sql:
            self.snap_args = args
            return [{"defect_id": d, "lineid": lid} for d, lid in self.snapped]
        if "FROM heatpipesections h" in sql:
            return self.rows
        if "FROM wear_out w" in sql or "FROM wear_out" in sql:
            return self.inserted_rows()
        if "FROM calculation_iznos c" in sql:
            return [{"id": self.next_id, "daterascheta": AT, "name": "t", "lines": len(self.inserted), "avg_wear": 10.0,
                     "max_priority": 0.2}]
        raise AssertionError(sql)

    async def fetchrow(self, sql, *args):
        return {"id": self.next_id, "daterascheta": AT, "name": "Износ"}

    async def executemany(self, sql, rows):
        self.inserted.extend(rows)

    async def execute(self, sql, *args):
        self.executed.append(sql)
        return "DELETE 3"

    def transaction(self):
        class _T:
            async def __aenter__(self_inner):
                return None

            async def __aexit__(self_inner, *a):
                return False
        return _T()

    def inserted_rows(self):
        out = []
        for r in self.inserted:
            d = dict(zip(("calculationid", *wear._COLUMNS), r))
            d.update(node1="A", node2="B", fragment_name="Ф", diameter=200, length_m=100.0, tubing="канал",
                     geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]})
            out.append(d)
        return out


def test_run_writes_header_and_rows_with_notes():
    rows = [_src(lineid=i, firstpicdatehp=date(2016, 1, 1)) for i in range(1, 1202)]
    conn = FakeConn(rows)
    out = asyncio.run(wear.run(conn, fragment_ids=[74], user="qa", at=AT))
    assert out["calculation_id"] == 7 and out["lines"] == 1201 and len(conn.inserted) == 1201
    assert out["by_category"][2] == 1201  # 10.8 лет: срок 2, повр. 1 → (0.3+0.2)/0.35·20 = 28.6 % → категория 2
    assert any("внесения в ГИС" in n for n in out["notes"]) and any("нарушений пуст" in n for n in out["notes"])
    with pytest.raises(wear.WearError):
        asyncio.run(wear.run(FakeConn([]), at=AT))
    with pytest.raises(wear.WearError):
        asyncio.run(wear.run(FakeConn(rows, exists=False), at=AT))


def test_summary_sections_geojson_delete():
    conn = FakeConn([_src(lineid=1), _src(lineid=2, n_defects=5, length_m=50.0)])
    asyncio.run(wear.run(conn, at=AT))
    s = asyncio.run(wear.summary(conn, 7))
    assert s["lines"] == 2 and s["with_defects"] == 1 and s["weights"] == wear.WEIGHTS
    sec = asyncio.run(wear.sections(conn, 7, limit=10))
    assert sec["total"] == 2 and sec["items"][0]["node1"] == "A"
    gj = asyncio.run(wear.geojson(conn, 7))
    assert gj["type"] == "FeatureCollection" and gj["features"][0]["properties"]["lineid"] == 1
    assert asyncio.run(wear.delete_run(conn, 7)) == 3


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='u', role=role)}"}


def test_endpoints_and_ai_plan(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    conn = FakeConn([_src(lineid=1), _src(lineid=2, n_defects=2)])
    asyncio.run(wear.run(conn, at=AT))

    class _Acquire:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(wear_router, "acquire_conn", lambda: _Acquire())
    monkeypatch.setattr(ai_router, "acquire_conn", lambda: _Acquire())
    calls = []

    async def fake_ask(**kw):
        calls.append(kw)
        return wear_plan.WearPlanNote(summary="ок", groups=[wear_plan.WearGroup(
            title="старые", reason="срок", line_ids=[1, 999], recommended_action="шурфовка", urgency=2)])

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    client = TestClient(main.app)
    assert client.get("/api/v1/wear/latest", headers=_auth("viewer")).json()["lines"] == 2
    assert client.get("/api/v1/wear/7/sections", params={"order": "wear"}, headers=_auth("viewer")).json()["total"] == 2
    assert client.get("/api/v1/wear/7/sections", params={"order": "bad"}, headers=_auth("viewer")).status_code == 422
    assert len(client.get("/api/v1/wear/7/geojson", headers=_auth("viewer")).json()["features"]) == 2
    assert client.get("/api/v1/wear/runs", headers=_auth("viewer")).json()["items"][0]["id"] == 7
    r = client.post("/api/v1/ai/wear/plan", json={}, headers=_auth())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["calculation_id"] == 7 and body["plan"]["groups"][0]["line_ids"] == [1]  # 999 отфильтрован
    assert "line#2" in calls[0]["user"] and calls[0]["tool"] == "wear_plan"
    assert client.post("/api/v1/ai/wear/plan", json={}, headers=_auth("viewer")).status_code == 403
    assert client.delete("/api/v1/wear/7", headers=_auth("viewer")).status_code == 403


def test_run_snaps_defects_without_line_by_place():
    rows = [_src(lineid=1, length_m=100.0, n_defects=1), _src(lineid=2, length_m=100.0)]
    # 4 нарушения без участка: 2 — к участку 2, 1 — к участку 1 и его копии 3 в другом фрагменте; одно далеко
    conn = FakeConn(rows + [_src(lineid=3, length_m=100.0)], snapped=[(10, 2), (11, 2), (12, 1), (12, 3)], unplaced=4)
    out = asyncio.run(wear.run(conn, fragment_ids=[74], at=AT))
    by_line = {r[1]: dict(zip(wear._COLUMNS, r[1:])) for r in conn.inserted}
    assert by_line[1]["n_defects"] == 2 and by_line[2]["n_defects"] == 2 and by_line[3]["n_defects"] == 1
    assert out["defects_snapped"] == 3 and conn.snap_args == ([74], wear.DEFECT_SNAP_M)
    assert any("привязано по месту (до 20 м) 3" in n for n in out["notes"])


def test_snap_skipped_when_projections_differ():
    conn = FakeConn([_src(lineid=1)], snapped=[(1, 1)], unplaced=2, srids=(9995, 3857))
    out = asyncio.run(wear.run(conn, at=AT))
    assert out["defects_snapped"] == 0 and conn.snap_args is None
