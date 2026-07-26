"""Pydantic models for /api/v1 auth endpoints."""

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
