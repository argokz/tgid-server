"""Фундамент помощника ИИ (ai/): флаг, статус, структурированный вызов с подменённым клиентом,
маппинг ошибок SDK, учёт в журнале, ключ не утекает. Без сети и без БД."""

from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

os.environ.setdefault("JWT_SECRET", "test-secret")

import activity  # noqa: E402
import main  # noqa: E402
from ai import client as ai_client  # noqa: E402
from ai import config  # noqa: E402
from ai.prompts import load_prompt  # noqa: E402
from auth import create_access_token  # noqa: E402


class Answer(BaseModel):
    summary: str
    score: int


def _auth(role="calculator"):
    return {"Authorization": f"Bearer {create_access_token(username='u', role=role)}"}


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "false")
    # Все настройки помощника — как без .env: у разработчика в .env включён ИИ, своя модель и лимиты
    for name in [k for k in os.environ if k.startswith("AI_")]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ai_client.reset_client()
    yield
    ai_client.reset_client()


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


def _fake_response(parsed, stop_reason="end_turn"):
    return SimpleNamespace(
        parsed_output=parsed,
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=120, output_tokens=30, cache_read_input_tokens=100,
                              cache_creation_input_tokens=0),
    )


def _install(monkeypatch, messages):
    monkeypatch.setattr(ai_client, "get_client", lambda: SimpleNamespace(messages=messages))


def _capture_log(monkeypatch):
    rows = []

    async def fake_write(**kw):
        rows.append(kw)

    monkeypatch.setattr(activity, "write", fake_write)
    return rows


def test_disabled_by_default_and_reasons(monkeypatch):
    assert config.enabled() is False
    assert "AI_ENABLED" in config.disabled_reason()
    monkeypatch.setenv("AI_ENABLED", "true")
    assert "ANTHROPIC_API_KEY" in config.disabled_reason()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert config.enabled() is True and config.disabled_reason() is None
    assert config.model() == "claude-opus-5-5"


def test_status_and_auth_config_report_flag(monkeypatch):
    client = TestClient(main.app)
    r = client.get("/api/v1/ai/status", headers=_auth("viewer"))
    assert r.status_code == 200 and r.json()["enabled"] is False and r.json()["reason"]
    assert client.get("/auth/config").json()["ai_enabled"] is False
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert client.get("/auth/config").json()["ai_enabled"] is True
    body = client.get("/api/v1/ai/status", headers=_auth("viewer")).json()
    assert body["enabled"] is True and body["model"] == "claude-opus-5-5" and body["reason"] is None
    assert client.get("/api/v1/ai/status").status_code == 401


def test_ask_structured_disabled_raises_503():
    with pytest.raises(ai_client.AiError) as exc:
        asyncio.run(ai_client.ask_structured(tool="t", system="s", user="u", output_format=Answer))
    assert exc.value.code == "ai_disabled" and exc.value.to_http().status_code == 503


def test_ask_structured_returns_parsed_and_logs_usage(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    messages = FakeMessages(_fake_response(Answer(summary="ок", score=3)))
    _install(monkeypatch, messages)
    rows = _capture_log(monkeypatch)
    out = asyncio.run(ai_client.ask_structured(
        tool="calc_protocol", system="SYS", user="DATA", output_format=Answer,
        effort="high", username="ivan", details={"calculation_id": 33},
    ))
    assert out == Answer(summary="ок", score=3)
    call = messages.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["output_format"] is Answer
    assert call["output_config"] == {"effort": "high"}
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"} and call["system"][0]["text"] == "SYS"
    assert call["messages"] == [{"role": "user", "content": "DATA"}]
    assert "thinking" not in call
    assert len(rows) == 1 and rows[0]["action"] == "AI" and rows[0]["username"] == "ivan"
    details = rows[0]["details"]
    assert details["tool"] == "calc_protocol" and details["input_tokens"] == 120 and details["calculation_id"] == 33
    assert "sk-ant-secret" not in repr(rows)


@pytest.mark.parametrize("stop_reason, code, http", [("refusal", "refused", 422), ("max_tokens", "truncated", 502)])
def test_ask_structured_stop_reasons(monkeypatch, stop_reason, code, http):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _install(monkeypatch, FakeMessages(_fake_response(None, stop_reason)))
    _capture_log(monkeypatch)
    with pytest.raises(ai_client.AiError) as exc:
        asyncio.run(ai_client.ask_structured(tool="t", system="s", user="u", output_format=Answer))
    assert (exc.value.code, exc.value.http) == (code, http)


def test_ask_structured_maps_sdk_errors(monkeypatch):
    import anthropic
    import httpx2 as httpx

    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret")
    _capture_log(monkeypatch)
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")

    def status_error(cls, status):
        return cls("boom sk-ant-secret", response=httpx.Response(status, request=req), body=None)

    cases = [
        (status_error(anthropic.RateLimitError, 429), "rate_limit", 503),
        (status_error(anthropic.AuthenticationError, 401), "auth", 503),
        (status_error(anthropic.InternalServerError, 500), "api_error", 502),
        (anthropic.APIConnectionError(request=req), "connection", 503),
    ]
    for error, code, http in cases:
        _install(monkeypatch, FakeMessages(error=error))
        with pytest.raises(ai_client.AiError) as exc:
            asyncio.run(ai_client.ask_structured(tool="t", system="s", user="u", output_format=Answer))
        assert (exc.value.code, exc.value.http) == (code, http), code
        assert "sk-ant-secret" not in exc.value.message
        assert "sk-ant-secret" not in str(exc.value.to_http().detail)


def test_ask_structured_rejects_too_long_input(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("AI_MAX_INPUT_CHARS", "10")
    _install(monkeypatch, FakeMessages(_fake_response(Answer(summary="", score=0))))
    with pytest.raises(ai_client.AiError) as exc:
        asyncio.run(ai_client.ask_structured(tool="t", system="s", user="x" * 11, output_format=Answer))
    assert exc.value.code == "input_too_long" and exc.value.http == 413


def test_prompts_have_stable_base_prefix():
    base = load_prompt("tgid_base")
    assert "ТГИД" in base and "JSON" in base
    with pytest.raises(FileNotFoundError):
        load_prompt("no_such_prompt")


def test_activity_skips_ai_posts_in_middleware():
    # вызовы ИИ пишет ai/usage.py с токенами, middleware их не дублирует
    assert activity.classify("POST", "/api/v1/ai/calc-protocol/explain") is None
    assert activity.ACTION_LABELS["AI"]
