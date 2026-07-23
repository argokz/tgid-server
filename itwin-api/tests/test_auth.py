"""Unit tests for P0 auth / RBAC / mutation gates (no live DB)."""

from __future__ import annotations

import os

import pytest
from fastapi import HTTPException

# Ensure auth module import works from package root
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ["AUTH_DISABLED"] = "false"
os.environ["MUTATIONS_ENABLED"] = "false"
os.environ["TOPOLOGY_MUTATIONS_ENABLED"] = "false"

from auth import (  # noqa: E402
    assert_mutable_table,
    create_access_token,
    decode_access_token,
    mutations_enabled,
    require_mutations_enabled,
)


def test_create_and_decode_token():
    token = create_access_token(username="alice", role="editor")
    user = decode_access_token(token)
    assert user.username == "alice"
    assert user.role == "editor"
    assert user.has_role("viewer")
    assert user.has_role("editor")
    assert not user.has_role("admin")


def test_mutations_kill_switch_default_off():
    assert mutations_enabled() is False
    with pytest.raises(HTTPException) as exc:
        require_mutations_enabled()
    assert exc.value.status_code == 503


def test_mutable_table_allow_list():
    assert assert_mutable_table("defect") == "defect"
    assert assert_mutable_table("tehnicheskie_usloviya") == "tehnicheskie_usloviya"
    with pytest.raises(HTTPException) as exc:
        assert_mutable_table("pg_shadow")
    assert exc.value.status_code == 403
    with pytest.raises(HTTPException):
        assert_mutable_table("evil;drop")


def test_mutations_enabled_when_flag_on(monkeypatch):
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    # Re-import behavior reads env each call
    assert mutations_enabled() is True
    require_mutations_enabled()  # should not raise
