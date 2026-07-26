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


def test_password_hash_roundtrip():
    from auth import hash_password, verify_password

    hashed = hash_password("secret")
    assert hashed.startswith("{bcrypt}")
    assert verify_password("secret", hashed)
    assert not verify_password("wrong", hashed)
    assert verify_password("plain", "{noop}plain")


def test_tu_and_ops_field_filters():
    from database.tu_mutations import filter_tu_fields
    from database.ops_mutations import filter_ops_fields

    tu = filter_tu_fields({"nomer_tu": "1", "evil": "x"})
    assert tu == {"nomer_tu": "1"}
    defect = filter_ops_fields("defect", {"data_osmotra": "2020-01-01", "shape": "nope"})
    assert "data_osmotra" in defect
    assert "shape" not in defect


def test_strict_auth_rejects_defaults(monkeypatch):
    from auth import assert_production_auth_safe

    monkeypatch.setenv("STRICT_AUTH", "true")
    monkeypatch.setenv("AUTH_DISABLED", "true")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-not-default-0123456789")
    with pytest.raises(RuntimeError):
        assert_production_auth_safe()


def test_strict_auth_rejects_dev_login(monkeypatch):
    from auth import assert_production_auth_safe

    monkeypatch.setenv("STRICT_AUTH", "true")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "true")
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-not-default-0123456789")
    with pytest.raises(RuntimeError, match="DEV_LOGIN"):
        assert_production_auth_safe()


def test_strict_auth_ok_when_hardened(monkeypatch):
    from auth import assert_production_auth_safe

    monkeypatch.setenv("STRICT_AUTH", "true")
    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("DEV_LOGIN_ENABLED", "false")
    monkeypatch.setenv("JWT_SECRET", "unit-test-secret-not-default-0123456789")
    assert_production_auth_safe()


def test_mutations_enabled_when_flag_on(monkeypatch):
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    assert mutations_enabled() is True
    require_mutations_enabled()  # should not raise
