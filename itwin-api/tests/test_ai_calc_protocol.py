"""Объяснение протокола расчёта помощником ИИ (ai/calc_protocol.py): разбор регуляторов,
сборка входа для модели, фильтрация ответа, кеш ai_summary, эндпоинт. Без сети и без БД."""

from __future__ import annotations

import asyncio
import json
import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import main  # noqa: E402
from ai import calc_protocol as cp  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai.schemas import ObjectRef  # noqa: E402
from auth import create_access_token  # noqa: E402
from routers import ai as ai_router  # noqa: E402

REG_TEXT = ("Регулятор давления [(6-8 УР2ЧАП) М2 1КЗ-22А О - М2 1КЗ-22Б О] не может обеспечить давление "
            "в узле [(6-8 УР2ЧАП) М2 1КЗ-22А О]\n    Задано 59.0 м. получено 49.66 м., расход 69.96 т/ч")
REG_TEXT2 = ("Регулятор давления [(6-8 НС-14) 6-8 МТК 13ДЖ-3 О - 6-8 мтк13-30 О] не может обеспечить давление "
             "в узле [X]\n    Задано 33.0 м. получено 38.90 м., расход 585.87 т/ч")


def _entry(seq, category, severity, text, objects, fix="object", count=1):
    return {"seq": seq, "category": category, "severity": severity, "text": text, "objects": objects,
            "fix": fix, "count": count, "fragment_id": None,
            "component": {"index": 1, "total": 1, "object": {"kind": "node", "id": 535303, "label": "РС1"}}}


def _records():
    entries = [
        _entry(1, "regulator", "warning", REG_TEXT,
               [{"kind": "line2", "id1": 535330, "id2": 535330, "label": "РД-22А"},
                {"kind": "node", "id": 535330, "label": "(6-8 УР2ЧАП) М2 1КЗ-22А О"}]),
        _entry(2, "regulator", "warning", REG_TEXT2,
               [{"kind": "line2", "id1": 535332, "id2": 535332, "label": "РД-13ДЖ"}]),
        _entry(3, "rs", "error", "Код РС 7 не найден в справочнике", [], fix="rs"),
        _entry(4, "subnetwork", "warning", "Подсеть без узла с заданным напором", [], fix="fixed_head", count=3),
    ]
    return [{
        "id": 5, "request_id": "r5", "calculationid": 37, "fileid": 74, "status": "success",
        "params": "-Tn -25 -iter 20 -fileID 74",
        "summary": {"header": ["БД: almatygid_copy Фрагмент: Маг. сети", "Температура наружного воздуха -25.0"]},
        "entries": entries,
    }]


def test_regulators_from_entries_parses_setpoint_and_deficit():
    regs = cp.regulators_from_entries(_records()[0]["entries"])
    assert [r["label"] for r in regs] == ["РД-22А", "РД-13ДЖ"]  # по модулю отклонения
    first = regs[0]
    assert first["kind"] == "РД" and first["setpoint"] == 59.0 and first["actual"] == 49.66
    assert first["flow"] == 69.96 and first["deficit"] == 9.34 and first["state"] == "недобор напора"
    assert regs[1]["deficit"] == -5.9 and regs[1]["state"] == "перебор напора"


def test_build_user_input_groups_and_limits(monkeypatch):
    monkeypatch.setattr(cp, "MAX_ENTRIES_PER_CATEGORY", 1)
    text = cp.build_user_input(_records())
    assert "Температура наружного воздуха -25.0" in text and "-Tn -25" in text
    assert "ошибок 1, предупреждений 3" in text
    assert text.index("[rs]") < text.index("[regulator]")  # ошибки первыми
    assert "… и ещё 1 сообщ. этой категории" in text
    assert "×3" in text and "line2#535330-535330" in text
    assert "отклонение +9.34 м (недобор напора)" in text


def test_sanitize_drops_unknown_objects_and_flags():
    expl = cp.ProtocolExplanation(
        summary="s",
        root_causes=[cp.RootCause(category="regulator", title="t", why="w", action="a", fix="object", objects=[
            ObjectRef(kind="node", id=535330, label="ok"), ObjectRef(kind="node", id=1, label="выдуман"),
            ObjectRef(kind="line2", id1=535332, id2=535332, label="ok2"),
        ])],
        next_run=[cp.NextRunFlag(flag="-rd_old", reason="r"), cp.NextRunFlag(flag="-password x", reason="нет")],
    )
    out = cp._sanitize(expl, _records())
    assert [o.label for o in out.root_causes[0].objects] == ["ok", "ok2"]
    assert [f.flag for f in out.next_run] == ["-rd_old"]


class FakeConn:
    def __init__(self, records, column=True, cached=None):
        self.records, self.column, self.cached, self.updates = records, column, cached, []

    async def fetchval(self, sql, *args):
        if "information_schema.columns" in sql:
            return self.column
        if "to_regclass" in sql:
            return True
        raise AssertionError(sql)

    async def fetchrow(self, sql, *args):
        return {"ai_summary": self.cached, "ai_summary_at": None} if self.cached else None

    async def fetch(self, sql, *args):
        import asyncpg  # noqa: F401 — asyncpg.Record не нужен: get_protocols отдаёт dict(r)

        protocol_id, request_id, calculation_id = args[:3]
        return [r for r in self.records if (protocol_id is None or r["id"] == protocol_id)
                and (request_id is None or r["request_id"] == request_id)
                and (calculation_id is None or r["calculationid"] == calculation_id)]

    async def execute(self, sql, *args):
        self.updates.append(args)


def _fake_ask(monkeypatch, expl):
    calls = []

    async def fake(**kw):
        calls.append(kw)
        return expl

    monkeypatch.setattr(ai_client, "ask_structured", fake)
    return calls


def test_explain_calls_model_and_caches(monkeypatch):
    expl = cp.ProtocolExplanation(summary="Главное — код РС", root_causes=[
        cp.RootCause(category="rs", title="РС", why="нет кода", action="добавить", fix="rs")])
    calls = _fake_ask(monkeypatch, expl)
    conn = FakeConn(_records())
    out = asyncio.run(cp.explain(conn, calculation_id=37, username="ivan"))
    assert out["cached"] is False and out["protocol_ids"] == [5] and out["calculation_ids"] == [37]
    assert out["explanation"]["summary"] == "Главное — код РС"
    assert out["regulators"][0]["deficit"] == 9.34
    assert calls[0]["tool"] == "calc_protocol" and calls[0]["effort"] == "high" and calls[0]["username"] == "ivan"
    assert "Задано 59.0" in calls[0]["user"] and "ТГИД" in calls[0]["system"]
    assert conn.updates and conn.updates[0][0] == 5
    saved = json.loads(conn.updates[0][1])
    assert saved["protocol_ids"] == [5] and "cached" not in saved


def test_explain_returns_cache_without_model(monkeypatch):
    calls = _fake_ask(monkeypatch, cp.ProtocolExplanation(summary="новое"))
    cached = {"protocol_ids": [5], "calculation_ids": [37], "regulators": [], "explanation": {"summary": "из кеша"}}
    conn = FakeConn(_records(), cached=json.dumps(cached))
    out = asyncio.run(cp.explain(conn, protocol_id=5))
    assert out["cached"] is True and out["explanation"]["summary"] == "из кеша" and not calls
    out = asyncio.run(cp.explain(conn, protocol_id=5, refresh=True))
    assert out["cached"] is False and out["explanation"]["summary"] == "новое" and len(calls) == 1


def test_explain_without_entries_skips_model(monkeypatch):
    calls = _fake_ask(monkeypatch, cp.ProtocolExplanation(summary="x"))
    rec = dict(_records()[0], entries=[])
    out = asyncio.run(cp.explain(FakeConn([rec], column=False), protocol_id=5))
    assert not calls and "без замечаний" in out["explanation"]["summary"] and out["regulators"] == []


def test_explain_not_found():
    with pytest.raises(ai_client.AiError) as exc:
        asyncio.run(cp.explain(FakeConn([]), protocol_id=99))
    assert exc.value.http == 404


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='u', role=role)}"}


def test_endpoint_requires_ai_and_permission(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.delenv("AI_ENABLED", raising=False)
    client = TestClient(main.app)
    r = client.post("/api/v1/ai/calc-protocol/explain", json={"calculation_id": 37}, headers=_auth())
    assert r.status_code == 503 and r.json()["detail"]["code"] == "ai_disabled"
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    r = client.post("/api/v1/ai/calc-protocol/explain", json={"calculation_id": 37}, headers=_auth("viewer"))
    assert r.status_code == 403
    r = client.post("/api/v1/ai/calc-protocol/explain", json={}, headers=_auth())
    assert r.status_code == 422


def test_endpoint_returns_explanation(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    conn = FakeConn(_records())

    class _Acquire:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(ai_router, "acquire_conn", lambda: _Acquire())
    _fake_ask(monkeypatch, cp.ProtocolExplanation(summary="ок"))
    client = TestClient(main.app)
    r = client.post("/api/v1/ai/calc-protocol/explain", json={"protocol_id": 5}, headers=_auth())
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["explanation"]["summary"] == "ок" and len(body["regulators"]) == 2
    status = client.get("/api/v1/ai/status", headers=_auth("viewer")).json()
    assert "calc_protocol" in status["tools"]
