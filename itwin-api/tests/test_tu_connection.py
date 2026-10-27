"""ТУ: подбор точки подключения и оценка нагрузки (database/tu_connection.py), рекомендация ИИ
(ai/tu_recommend.py), эндпоинты. Без БД и без сети."""

from __future__ import annotations

import asyncio
import os
from datetime import date

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai import tu_recommend as tr  # noqa: E402
from auth import create_access_token  # noqa: E402
from database import tu_connection as tc  # noqa: E402
from routers import ai as ai_router  # noqa: E402
from routers import registries  # noqa: E402


def _row(**kw):
    base = dict(node_id=1, name="ТК 15а", fileid=74, nodetypeid=1, dist=32.0, lon=76.9, lat=43.2, rx=1.0, ry=2.0,
                fragment_name="Маг. сети", calculation_id=12, line_id=10, diameter=200.0, length=100.0,
                laid_at=date(2016, 4, 22), tubing="канал", head_supply=82.0, head_return=47.0,
                t_supply=131.8, t_return=68.3, source_name="АТЭЦ-1", source_id=177,
                calc_diameter=207.0, velocity=0.82, flow=99.1, dp_per_m=6.1, piezo_head=82.0)
    base.update(kw)
    return base


def test_extra_flow_and_velocity():
    assert tc.extra_flow_t_h(0.5, 63.5) == pytest.approx(7.874, abs=0.01)
    assert tc.extra_flow_t_h(0.5, None) == pytest.approx(500 / 60)  # перепад по умолчанию
    assert tc.extra_flow_t_h(None, 60) == 0
    assert tc.velocity_after(0.82, 99.1, 7.874) == pytest.approx(0.885, abs=0.001)
    assert tc.velocity_after(0.82, 0, 5) is None
    assert tc.velocity_after(0.67, -81.44, 7.87) == pytest.approx(0.735, abs=0.001)  # обратный поток


def test_assess_scores_head_velocity_diameter():
    good = tc.assess(_row(), 0.5)
    assert good["available_head"] == 35.0 and good["velocity_after"] == pytest.approx(0.885, abs=0.001)
    assert any("располагаемый напор 35.0 м" in r for r in good["reasons"])
    assert good["laid_at"] == "2016-04-22" and good["source_name"] == "АТЭЦ-1"

    no_calc = tc.assess(_row(calculation_id=None, head_supply=None, head_return=None, velocity=None, flow=None), 0.5)
    assert no_calc["available_head"] is None and no_calc["score"] < good["score"]
    assert any("нет расчёта" in r for r in no_calc["reasons"])

    overloaded = tc.assess(_row(velocity=3.4, flow=20.0), 2.0)
    assert overloaded["velocity_after"] > tc.V_MAX and overloaded["score"] < good["score"]
    low_head = tc.assess(_row(head_supply=50.0, head_return=45.0, diameter=80.0), 0.1)
    assert low_head["score"] < good["score"] and any("малый" in r for r in low_head["reasons"])


def test_dedupe_keeps_variant_with_latest_calculation():
    rows = [_row(fileid=91, calculation_id=None, dist=32.0), _row(fileid=73, calculation_id=10, dist=32.0),
            _row(fileid=97, calculation_id=12, dist=32.0), _row(name="ТК 15", rx=5.0, ry=5.0, dist=88.0)]
    out = tc.dedupe(rows)
    assert [(r["name"], r["fileid"]) for r in out] == [("ТК 15а", 97), ("ТК 15", 74)]


class FakeConn:
    def __init__(self, rows=None, analogs=None, has_buildings=True):
        self.rows, self.analogs, self.calls = rows or [], analogs or [], []
        self.has_buildings = has_buildings

    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        assert "to_regclass('zdaniya_2')" in sql
        return self.has_buildings

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self.analogs if "zdaniya_2" in sql else self.rows


def test_connection_candidates_ranks_and_limits():
    rows = [_row(node_id=1, dist=32.0), _row(node_id=2, name="ТК 15", rx=5.0, ry=5.0, dist=88.0, velocity=3.4, flow=20.0),
            _row(node_id=3, name="ТК 16", rx=9.0, ry=9.0, dist=250.0, calculation_id=None)]
    conn = FakeConn(rows)
    out = asyncio.run(tc.connection_candidates(conn, lon=76.9, lat=43.2, load_gcal_h=1.0, radius_m=5000, limit=2))
    assert out["radius_m"] == tc.MAX_RADIUS_M and len(out["items"]) == 2
    assert [i["node_id"] for i in out["items"]] == [1, 2]
    assert conn.calls[0][1][2] == tc.MAX_RADIUS_M and conn.calls[0][1][5] is None
    empty = asyncio.run(tc.connection_candidates(FakeConn([]), lon=0, lat=0))
    assert empty["items"] == [] and "нет узлов" in empty["note"]


def test_estimate_load_by_floors_and_area():
    analogs = [{"nagr": 0.3, "shape_area": 600.0, "floor": 9}, {"nagr": 0.4, "shape_area": 800.0, "floor": 9},
               {"nagr": 0.5, "shape_area": 1000.0, "floor": 10}]
    conn = FakeConn(analogs=analogs)
    by_floor = asyncio.run(tc.estimate_load(conn, floors=9))
    assert by_floor["load_gcal_h"] == 0.4 and by_floor["analogs"] == 3 and conn.calls[-1][1] == (8, 10)
    by_area = asyncio.run(tc.estimate_load(conn, floors=9, area_m2=2000))
    assert by_area["per_1000m2"] == 0.5 and by_area["load_gcal_h"] == 1.0
    assert asyncio.run(tc.estimate_load(conn))["load_gcal_h"] is None
    assert asyncio.run(tc.estimate_load(FakeConn(), floors=30))["analogs"] == 0


def test_estimate_load_without_buildings_layer():
    """База без zdaniya_2 (Астана): понятный ответ без запроса к таблице, а не 500."""
    conn = FakeConn(analogs=[{"nagr": 0.3, "shape_area": 600.0, "floor": 9}], has_buildings=False)
    out = asyncio.run(tc.estimate_load(conn, floors=9, area_m2=1000))
    assert out["load_gcal_h"] is None and out["analogs"] == 0 and "нет слоя зданий" in out["basis"]
    assert not any("FROM zdaniya_2" in sql for sql, _ in conn.calls)


def _candidates():
    return {"radius_m": 300, "load_gcal_h": 0.5, "thresholds": {"v_min": 1.5, "v_max": 3.5, "min_available_head": 15},
            "items": [tc.assess(_row(), 0.5), tc.assess(_row(node_id=2, name="ТК 15", dist=88.0), 0.5)]}


def test_build_user_input_lists_candidates():
    text = tr.build_user_input("Жилой дом 9 этажей, Абая 10", _candidates(),
                               {"load_gcal_h": 0.34, "basis": "медиана 1142 зданий"}, 0.5)
    assert "Абая 10" in text and "Запрошенная нагрузка: 0.5" in text and "0.34 Гкал/ч" in text
    assert "[0] узел «ТК 15а» (node#1" in text and "[1] узел «ТК 15»" in text and "Ø200 мм" in text


def test_sanitize_fixes_index_and_names():
    rec = tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=7, explanation="x", draft=tr.TuDraft(kamera="выдумка"))
    out = tr._sanitize(rec, _candidates()["items"])
    assert out.chosen_index is None and out.draft.kamera == "выдумка"
    rec = tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=1, explanation="x",
                              alternatives=[tr.Alternative(index=1, note="сам"), tr.Alternative(index=0, note="ок"),
                                            tr.Alternative(index=9, note="нет")],
                              draft=tr.TuDraft(kamera="ТК 15-бис", istochnik="другой"))
    out = tr._sanitize(rec, _candidates()["items"])
    assert out.draft.kamera == "ТК 15" and out.draft.istochnik == "АТЭЦ-1"
    assert [a.index for a in out.alternatives] == [0]


def test_sanitize_takes_choice_from_explanation_when_index_missing():
    # живой ответ 27.10: «Выбран кандидат [0] …», а chosen_index = null
    rec = tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=None,
                              explanation="Выбран кандидат [1] — узел «ТК 15»: располагаемый напор …", draft=tr.TuDraft())
    assert tr._sanitize(rec, _candidates()["items"]).chosen_index == 1
    # номер вне списка — выбора нет; «не выбран» — тоже
    rec = tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=None, explanation="Выбран кандидат [9]", draft=tr.TuDraft())
    assert tr._sanitize(rec, _candidates()["items"]).chosen_index is None
    rec = tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=None,
                              explanation="Подходящего кандидата нет: у [0] нет расчёта", draft=tr.TuDraft())
    assert tr._sanitize(rec, _candidates()["items"]).chosen_index is None


def test_recommend_uses_estimate_when_no_load(monkeypatch):
    calls = []

    async def fake_ask(**kw):
        calls.append(kw)
        return tr.TuRecommendation(request=tr.ParsedRequest(floors=9), chosen_index=0, explanation="ок",
                                   draft=tr.TuDraft(prirost_nagruzki=0.4))

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    conn = FakeConn(rows=[_row()], analogs=[{"nagr": 0.4, "shape_area": 800.0, "floor": 9}])
    out = asyncio.run(tr.recommend(conn, lon=76.9, lat=43.2, request_text="дом 9 этажей", floors=9))
    assert out["load_estimate"]["load_gcal_h"] == 0.4 and out["candidates"]["load_gcal_h"] == 0.4
    assert out["chosen"]["node_id"] == 1 and out["recommendation"]["draft"]["kamera"] == "ТК 15а"
    assert calls[0]["tool"] == "tu_recommend" and calls[0]["details"]["candidates"] == 1


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='u', role=role)}"}


def test_endpoints(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    conn = FakeConn(rows=[_row()], analogs=[{"nagr": 0.4, "shape_area": 800.0, "floor": 9}])

    class _Acquire:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(registries, "acquire_conn", lambda: _Acquire())
    monkeypatch.setattr(ai_router, "acquire_conn", lambda: _Acquire())

    async def fake_ask(**kw):
        return tr.TuRecommendation(request=tr.ParsedRequest(), chosen_index=0, explanation="ок", draft=tr.TuDraft())

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    client = TestClient(main.app)
    r = client.get("/api/v1/technical-conditions/connection-candidates",
                   params={"lon": 76.9, "lat": 43.2, "load_gcal_h": 0.5}, headers=_auth("viewer"))
    assert r.status_code == 200 and r.json()["items"][0]["name"] == "ТК 15а"
    r = client.get("/api/v1/technical-conditions/load-estimate", params={"floors": 9}, headers=_auth("viewer"))
    assert r.status_code == 200 and r.json()["load_gcal_h"] == 0.4
    r = client.post("/api/v1/ai/tu/recommend", json={"lon": 76.9, "lat": 43.2, "request_text": "дом"}, headers=_auth())
    assert r.status_code == 200 and r.json()["chosen"]["node_id"] == 1
    assert client.post("/api/v1/ai/tu/recommend", json={"lon": 76.9, "lat": 43.2}, headers=_auth("viewer")).status_code == 403
    assert client.get("/api/v1/technical-conditions/connection-candidates", params={"lon": 500, "lat": 0},
                      headers=_auth("viewer")).status_code == 422
