"""Pydantic models for /api/v1 auth endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    role: str = Field(default="editor", description="Dev-login role when AUTH_DISABLED or DEV_LOGIN_ENABLED")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class AuthConfigResponse(BaseModel):
    """Public auth/mutation flags for LoginDialog (no JWT required)."""

    auth_disabled: bool
    dev_login_enabled: bool
    strict_auth: bool
    mutations_enabled: bool
    topology_mutations_enabled: bool


class MeResponse(BaseModel):
    sub: str
    username: str
    role: str
    mutations_enabled: bool
    topology_mutations_enabled: bool
    auth_disabled: bool
    dev_login_enabled: bool = False
    strict_auth: bool = False
    # AUTH_BACKEND=pg: профиль из tgid_auth.me()
    auth_backend: str = "usersdb"
    display_name: Optional[str] = None
    caps: list[str] = Field(default_factory=list)
    fragments: Optional[list[int]] = None  # None — правка во всей сети
    must_change_password: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
