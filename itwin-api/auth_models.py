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
    auth_required_get: bool = False  # без входа данные карты не отдаются
    dev_login_enabled: bool
    strict_auth: bool
    mutations_enabled: bool
    topology_mutations_enabled: bool
    city: str = ""  # код города этого API (cities.py)
    city_label: str = ""


class CityItem(BaseModel):
    code: str
    label: str
    path: str  # путь веба города, напр. /tgid/astana/


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
    is_master: bool = False  # мастер-учётка владельца (MASTER_LOGIN)
    display_name: Optional[str] = None
    caps: list[str] = Field(default_factory=list)
    fragments: Optional[list[int]] = None  # None — правка во всей сети
    must_change_password: bool = False
    city: str = ""
    city_label: str = ""
    cities: list[CityItem] = Field(default_factory=list)  # города, доступные пользователю
    all_cities: bool = True  # доступ ко всем городам (и будущим)
    # действующие права (permissions.py): {"matrix": {вид: {действие: none|own|all}}, "general": [...]}
    permissions: dict = Field(default_factory=dict)
    role_label: str = ""


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)
