"""Пересортировка похожих аварий Claude: маскирование перед отправкой, слияние ответа, порядок кода без ИИ."""

from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret-123")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai import config  # noqa: E402
from ai import defect_rerank as dr  # noqa: E402
from auth import create_access_token, invalidate_user_status  # noqa: E402
from database import defect_similarity as ds  # noqa: E402
from routers import ai as ai_router  # noqa: E402

REF = {"id": 153, "text": "Свищ 2Ду100 по Т2", "parts": ["Свищ 2Ду100 по Т2", "Свищ 2Ду100 по Т2", None],
       "detected_at": "2021-11-25T00:00:00", "lon": 71.4, "lat": 51.1, "lineid": None}


def _cand(i, score, text, dist=100.0):
    return {"id": i, "line_id": None, "detected_at": "2020-01-0%dT00:00:00" % i, "text": text, "lon": 71.4,
            "lat": 51.1, "distance_m": dist, "features": {}, "score": score, "parts": {}, "reasons": ["Ду100"]}


def test_input_masks_personal_data_always():
    text = dr.build_input(REF, [_cand(1, 0.6, "Утечка, сообщил Иванов Пётр Сергеевич, тел. 87011234567")])
    assert "Иванов" not in text and "1234567" not in text
    assert text.count("Свищ 2Ду100 по Т2") == 1  # повтор описания и отчёта — один раз
    assert "id 1; 2020-01-01; 100 м; оценка кода 60 (Ду100)" in text


def test_merge_orders_by_model_and_drops_unknown_ids():
    cands = [_cand(1, 0.7, "a"), _cand(2, 0.5, "b"), _cand(3, 0.4, "c")]
    ranked = dr.RerankOut(items=[dr.RankedItem(id=3, relevance=90, reason="тот же отвод"),
                                 dr.RankedItem(id=1, relevance=20, reason="плановая замена"),
                                 dr.RankedItem(id=99, relevance=100, reason="выдумка")])
    out = dr.merge(cands, ranked)
    assert [c["id"] for c in out] == [3, 1, 2]
    assert out[0]["ai_reason"] == "тот же отвод" and out[2]["ai_relevance"] is None


def test_endpoint_reranks_and_falls_back(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("PII_MASKING", "true")
    invalidate_user_status()

    class _Acquire:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *a):
            return False

    async def reference(conn, defect_id):
        return dict(REF) if defect_id == 153 else None

    async def similar(conn, text, **kw):
        return {"reference": ds.features(text), "radius_m": kw["radius_m"], "candidates": 3,
                "items": [_cand(1, 0.7, "Порыв Ду100 Т2, Иванов Пётр Сергеевич"), _cand(2, 0.5, "Замена участка Ду100")]}

    calls = []

    async def fake_ask(**kw):
        calls.append(kw)
        return dr.RerankOut(items=[dr.RankedItem(id=2, relevance=80, reason="замена после этой аварии"),
                                   dr.RankedItem(id=1, relevance=40, reason="другой участок")])

    monkeypatch.setattr(ai_router, "acquire_conn", lambda: _Acquire())
    monkeypatch.setattr(ds, "reference", reference)
    monkeypatch.setattr(ds, "similar", similar)
    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    client = TestClient(main.app)
    calc = {"Authorization": f"Bearer {create_access_token(username='u', role='calculator')}"}
    r = client.post("/api/v1/ai/defects/153/similar", json={"limit": 5}, headers=calc)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ranking"] == "ai" and [i["id"] for i in body["items"]] == [2, 1]
    assert calls[0]["model"] == config.rerank_model() == "claude-sonnet-5-5" and calls[0]["effort"] == "low"
    assert "Иванов" not in calls[0]["user"]  # в Claude — только замаскированные тексты
    viewer = {"Authorization": f"Bearer {create_access_token(username='v', role='viewer')}"}
    assert client.post("/api/v1/ai/defects/153/similar", json={}, headers=viewer).status_code == 403
    assert client.post("/api/v1/ai/defects/9/similar", json={}, headers=calc).status_code == 404

    async def refused(**kw):
        raise ai_client.AiError("refused", "Модель отказалась отвечать на этот запрос", 422)

    monkeypatch.setattr(ai_client, "ask_structured", refused)
    body = client.post("/api/v1/ai/defects/153/similar", json={}, headers=calc).json()
    assert body["ranking"] == "features" and body["ai_error"].startswith("Модель отказалась")
    assert [i["id"] for i in body["items"]] == [1, 2]
    invalidate_user_status()
