"""Помощник-собеседник (ai/assistant.py): цикл модель → инструменты → ответ с подменённым клиентом, сбор id для
карты, проверка беседы, поток NDJSON и новые инструменты сценариев. Без сети и без БД."""

from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-secret")

import activity  # noqa: E402
import main  # noqa: E402
from ai import assistant  # noqa: E402
from ai import client as ai_client  # noqa: E402
from auth import AuthUser, create_access_token  # noqa: E402
from tgid_mcp import tools as mcp_tools  # noqa: E402

USER = AuthUser(sub="anna", role="calculator", username="anna")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    for name in [k for k in os.environ if k.startswith("AI_")]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(mcp_tools, "_calls", mcp_tools.defaultdict(mcp_tools.deque))
    ai_client.reset_client()
    yield
    ai_client.reset_client()


@pytest.fixture
def log(monkeypatch):
    rows = []

    async def fake_write(**kw):
        rows.append(kw)

    monkeypatch.setattr(activity, "write", fake_write)
    return rows


def _usage(i=100, o=20):
    return SimpleNamespace(input_tokens=i, output_tokens=o, cache_read_input_tokens=0, cache_creation_input_tokens=0)


def _tool_use(name, args, uid="tu_1"):
    return SimpleNamespace(type="tool_use", id=uid, name=name, input=args)


def _text(text):
    return SimpleNamespace(type="text", text=text)


class FakeMessages:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    async def create(self, **kwargs):
        # копия сообщений: цикл дописывает в тот же список
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


def _install(monkeypatch, responses):
    messages = FakeMessages(responses)
    monkeypatch.setattr(ai_client, "get_client", lambda: SimpleNamespace(messages=messages))
    return messages


def _no_db(monkeypatch, features=None):
    @asynccontextmanager
    async def acquire():
        yield None

    async def fake_map(conn, nodes, lines):
        return {"type": "FeatureCollection", "features": features or [
            {"type": "Feature", "id": i, "properties": {"kind": "line"}} for i in sorted(lines)]}

    import database.connect

    monkeypatch.setattr(database.connect, "acquire_conn", acquire)
    monkeypatch.setattr(assistant, "map_features", fake_map)


def _collect(gen):
    async def go():
        return [e async for e in gen]

    return asyncio.run(go())


def test_history_must_alternate():
    T = assistant.AssistantTurn
    assistant.check_history([])
    assistant.check_history([T(role="user", text="а"), T(role="assistant", text="б")])
    with pytest.raises(assistant.AssistantInputError):
        assistant.check_history([T(role="assistant", text="б")])
    with pytest.raises(assistant.AssistantInputError):
        assistant.check_history([T(role="user", text="а")])
    with pytest.raises(assistant.AssistantInputError):
        assistant.check_history([T(role="user", text="а"), T(role="user", text="б")])


def test_messages_with_visible_fragments():
    req = assistant.AssistantRequest(question=" Где ТК-12? ", fragment_ids=[74, 3, 74],
                                     history=[{"role": "user", "text": "Привет"}, {"role": "assistant", "text": "Да"}])
    msgs = assistant.build_messages(req)
    assert [m["role"] for m in msgs] == ["user", "assistant", "user"]
    assert msgs[-1]["content"].startswith("(На карте открыты фрагменты: 3, 74)") and msgs[-1]["content"].endswith("Где ТК-12?")


def test_tool_specs_from_registry_with_cache_mark():
    specs = assistant.tool_specs()
    names = [s["name"] for s in specs]
    assert {"network_trace", "valve_isolation", "select_network", "scenario_compare", "list_scenarios"} <= set(names)
    assert specs[-1]["cache_control"] == {"type": "ephemeral"}
    assert all("cache_control" not in s for s in specs[:-1])
    trace = next(s for s in specs if s["name"] == "network_trace")
    assert trace["description"].startswith("Трассировка сети.") and "start_node_ids" in trace["input_schema"]["properties"]


def test_collect_ids_from_tools():
    nodes, lines = set(), set()
    assistant.collect_ids("network_trace", {}, {"node_ids": [1, 2], "line_ids": [10, True]}, nodes, lines)
    assistant.collect_ids("select_network", {}, {"target": "lines", "items": [{"id": 11}, {"id": 12}]}, nodes, lines)
    assistant.collect_ids("search_network", {"kind": "node"}, {"items": [{"id": 3}]}, nodes, lines)
    assistant.collect_ids("valve_isolation", {}, {
        "geojson": {"isolated_pipes": {"features": [{"properties": {"id": 13}}]},
                    "downstream_pipes": {"features": [{"properties": {"id": 14}}]}},
        "affected_consumers": [{"node_id": 4}], "downstream_consumers": [{"node_id": 5}]}, nodes, lines)
    assistant.collect_ids("wear_priorities", {}, {"items": [{"line_id": 15}]}, nodes, lines)
    assistant.collect_ids("scenario_compare", {}, {"items": [{"anchor_type": "line", "anchor_id": 16},
                                                             {"anchor_type": "node", "anchor_id": 6}]}, nodes, lines)
    assistant.collect_ids("list_fragments", {}, "не словарь", nodes, lines)
    assert nodes == {1, 2, 3, 4, 5, 6} and lines == {10, 11, 12, 13, 14, 15, 16}


def test_loop_runs_tool_then_answers(monkeypatch, log):
    _no_db(monkeypatch)
    fake = _install(monkeypatch, [
        SimpleNamespace(stop_reason="tool_use", usage=_usage(), content=[
            _text("Смотрю трассировку."), _tool_use("network_trace", {"trace_type": "upstream", "start_node_ids": [5]})]),
        SimpleNamespace(stop_reason="end_turn", usage=_usage(300, 40), content=[_text("Питается от ТЭЦ-2 (узел 9).")]),
    ])
    seen = []

    async def fake_call(name, args, user, client=None, path_prefix="/mcp"):
        seen.append((name, args, user.username, path_prefix))
        return ({"node_ids": [5, 9], "line_ids": [70, 71]},
                {"content": [{"type": "text", "text": '{"node_ids": [5, 9]}'}], "isError": False})

    monkeypatch.setattr(mcp_tools, "call_tool_raw", fake_call)
    events = _collect(assistant.run(assistant.AssistantRequest(question="Откуда питается узел 5?"), USER))
    assert [e["type"] for e in events] == ["note", "step", "step_done", "answer"]
    assert events[1]["title"] == "Трассировка сети" and events[2]["ok"] is True
    answer = events[-1]
    assert answer["text"] == "Питается от ТЭЦ-2 (узел 9)." and answer["tool_calls"] == 1
    assert answer["highlight"] == {"nodes": 2, "lines": 2} and len(answer["geojson"]["features"]) == 2
    assert answer["tokens"]["input_tokens"] == 400 and answer["tokens"]["output_tokens"] == 60
    assert seen == [("network_trace", {"trace_type": "upstream", "start_node_ids": [5]}, "anna", "/ai/assistant")]
    # второй вызов модели получил результат инструмента с тем же id
    second = fake.calls[1]["messages"]
    assert second[-1]["role"] == "user" and second[-1]["content"][0]["tool_use_id"] == "tu_1"
    assert fake.calls[0]["tool_choice"] == {"type": "auto"}
    ai_rows = [r for r in log if r["action"] == "AI"]
    assert len(ai_rows) == 1 and ai_rows[0]["details"]["tool"] == "assistant" and ai_rows[0]["details"]["tool_calls"] == 1


def test_tool_error_goes_back_to_model(monkeypatch, log):
    _no_db(monkeypatch)
    fake = _install(monkeypatch, [
        SimpleNamespace(stop_reason="tool_use", usage=_usage(), content=[_tool_use("run_calculation", {"fragment_ids": [1]})]),
        SimpleNamespace(stop_reason="end_turn", usage=_usage(), content=[_text("Нет права на расчёт.")]),
    ])
    viewer = AuthUser(sub="petr", role="viewer", username="petr")
    events = _collect(assistant.run(assistant.AssistantRequest(question="Посчитай фрагмент 1"), viewer))
    done = next(e for e in events if e["type"] == "step_done")
    assert done["ok"] is False and "Нет права" in done["error"]
    result = fake.calls[1]["messages"][-1]["content"][0]
    assert result["is_error"] is True and "Нет права" in result["content"]
    assert events[-1]["type"] == "answer" and events[-1]["geojson"] is None


def test_last_step_forces_answer_without_tools(monkeypatch, log):
    _no_db(monkeypatch)
    monkeypatch.setattr(assistant, "MAX_STEPS", 1)
    fake = _install(monkeypatch, [SimpleNamespace(stop_reason="end_turn", usage=_usage(), content=[_text("Итог.")])])
    events = _collect(assistant.run(assistant.AssistantRequest(question="?"), USER))
    assert fake.calls[0]["tool_choice"] == {"type": "none"} and events[-1]["text"] == "Итог."


def test_model_errors_become_error_event(monkeypatch, log):
    _no_db(monkeypatch)
    _install(monkeypatch, [SimpleNamespace(stop_reason="max_tokens", usage=_usage(), content=[])])
    events = _collect(assistant.run(assistant.AssistantRequest(question="?"), USER))
    assert events == [{"type": "error", "code": "truncated",
                       "message": "Ответ ИИ не уместился в лимит токенов — сузьте вопрос"}]
    assert [r["details"]["error"] for r in log if r["action"] == "AI"] == ["truncated"]


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='anna', role=role)}"}


def test_endpoint_disabled_and_validation(monkeypatch, log):
    client = TestClient(main.app)
    body = {"question": "Где ТК-12?"}
    assert client.post("/api/v1/ai/assistant", json=body, headers=_auth()).status_code == 503
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    bad = {"question": "?", "history": [{"role": "assistant", "text": "Да"}]}
    r = client.post("/api/v1/ai/assistant", json=bad, headers=_auth())
    assert r.status_code == 422 and "чередоваться" in r.json()["detail"]
    assert client.post("/api/v1/ai/assistant", json=body, headers=_auth("viewer")).status_code == 403


def test_endpoint_streams_ndjson(monkeypatch, log):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _no_db(monkeypatch)
    _install(monkeypatch, [SimpleNamespace(stop_reason="end_turn", usage=_usage(), content=[_text("Готово.")])])
    client = TestClient(main.app)
    r = client.post("/api/v1/ai/assistant", json={"question": "Сколько км сети?"}, headers=_auth())
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    assert r.headers["x-accel-buffering"] == "no"
    events = [json.loads(line) for line in r.text.splitlines() if line]
    assert events[-1]["type"] == "answer" and events[-1]["text"] == "Готово."


def test_question_rate_limit(monkeypatch, log):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setattr(assistant, "QUESTION_RATE", (1, 600))
    _no_db(monkeypatch)
    _install(monkeypatch, [SimpleNamespace(stop_reason="end_turn", usage=_usage(), content=[_text("Да.")])])
    client = TestClient(main.app)
    assert client.post("/api/v1/ai/assistant", json={"question": "1"}, headers=_auth()).status_code == 200
    r = client.post("/api/v1/ai/assistant", json={"question": "2"}, headers=_auth())
    assert r.status_code == 429 and "вопросов" in r.json()["detail"]


def test_scenario_compare_needs_calculations(monkeypatch, log):
    import database.scenarios as sc

    class Conn:
        async def fetchrow(self, sql, *args):
            return {"base_fileid": 74, "fileid": 900}

        async def fetchval(self, sql, *args):
            return 501 if args[0] == 74 else None

    @asynccontextmanager
    async def acquire():
        yield Conn()

    async def available(conn):
        return True

    monkeypatch.setattr(mcp_tools, "acquire_conn", acquire)
    monkeypatch.setattr(sc, "scenarios_available", available)
    res = asyncio.run(mcp_tools.call_tool("scenario_compare", {"scenario_id": 3}, USER))
    assert res["isError"] and "сценария #900 нет расчёта" in res["content"][0]["text"]


def test_calculations_tool(monkeypatch, log):
    from datetime import datetime

    class Conn:
        async def fetch(self, sql, *args):
            assert args == ([3, 74], 2)
            return [{"id": 9, "fileid": 74, "tn": -20.0, "date1": datetime(2026, 10, 30, 12), "name": "",
                     "calc_params": '{"g_is_avar": 1}'}]

    @asynccontextmanager
    async def acquire():
        yield Conn()

    monkeypatch.setattr(mcp_tools, "acquire_conn", acquire)
    res = asyncio.run(mcp_tools.call_tool("list_calculations", {"fragment_ids": [74, 3, 74], "limit": 2}, USER))
    assert res["structuredContent"]["calculations"] == [
        {"id": 9, "fragment_id": 74, "tn": -20.0, "name": None, "date": "2026-10-30T12:00:00", "emergency": True}]


def test_tool_results_masked_without_pii_right(monkeypatch, log):
    async def fake_list(p, user):
        return {"fragments": [{"id": 1, "name": "ТК", "phone": "+7 701 123 45 67"}]}

    tool = mcp_tools.TOOLS["list_fragments"]
    monkeypatch.setitem(mcp_tools.TOOLS, "list_fragments", tool.__class__(**{**tool.__dict__, "run": fake_list}))
    viewer = AuthUser(sub="petr", role="viewer", username="petr")
    payload, res = asyncio.run(mcp_tools.call_tool_raw("list_fragments", {}, viewer))
    assert "123 45 67" not in res["content"][0]["text"] and payload["fragments"][0]["phone"].endswith("67")
    admin = AuthUser(sub="ivan", role="admin", username="ivan")
    _, res = asyncio.run(mcp_tools.call_tool_raw("list_fragments", {}, admin))
    assert "+7 701 123 45 67" in res["content"][0]["text"]


def test_pii_middleware_does_not_buffer_ndjson():
    from pii_middleware import PiiMaskMiddleware

    sent = []

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200,
                    "headers": [(b"content-type", b"application/x-ndjson")]})
        await send({"type": "http.response.body", "body": b'{"type":"step"}\n', "more_body": True})
        assert len(sent) == 2  # шаг ушёл клиенту до конца ответа
        await send({"type": "http.response.body", "body": b'{"type":"answer"}\n'})

    async def send(message):
        sent.append(message)

    asyncio.run(PiiMaskMiddleware(app)({"type": "http", "path": "/api/v1/ai/assistant", "headers": []}, None, send))
    assert len(sent) == 3
