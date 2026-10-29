"""Именованные настройки трассировки сети (database/trace_configs.py).

GET    /api/v1/trace-configs        — встроенные, общие и свои
POST   /api/v1/trace-configs        — сохранить (общую — с правом «Справочники и шаблоны»)
PUT    /api/v1/trace-configs/{id}   — изменить свою (общую — с правом «Справочники»)
DELETE /api/v1/trace-configs/{id}
Запуск — POST /api/analysis/trace с config_id.
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import AuthUser, require_roles
from database import trace_configs as tc
from database.connect import acquire_conn

router = APIRouter(tags=["analysis"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]


class ConfigBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=tc.NAME_MAX)
    params: dict[str, Any]
    shared: bool = False


class ConfigPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=tc.NAME_MAX)
    params: Optional[dict[str, Any]] = None
    shared: Optional[bool] = None


def _can_shared(user: AuthUser) -> bool:
    return user.perms.has("refs")


def _http(exc: tc.TraceConfigError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@router.get("/api/v1/trace-configs")
async def list_trace_configs(user: Viewer):
    async with acquire_conn() as conn:
        return {"configs": await tc.list_configs(conn, user.username), "can_shared": _can_shared(user)}


@router.post("/api/v1/trace-configs", status_code=201)
async def create_trace_config(body: ConfigBody, user: Viewer):
    if body.shared and not _can_shared(user):
        raise HTTPException(status_code=403, detail="Общие настройки — с правом «Справочники и шаблоны»")
    try:
        async with acquire_conn() as conn:
            return await tc.create_config(conn, name=body.name, params=body.params, shared=body.shared,
                                          user=user.username)
    except tc.TraceConfigError as exc:
        raise _http(exc)


@router.put("/api/v1/trace-configs/{config_id}")
async def update_trace_config(config_id: str, body: ConfigPatch, user: Viewer):
    if body.shared and not _can_shared(user):
        raise HTTPException(status_code=403, detail="Общие настройки — с правом «Справочники и шаблоны»")
    try:
        async with acquire_conn() as conn:
            return await tc.update_config(conn, config_id, name=body.name, params=body.params, shared=body.shared,
                                          user=user.username, can_shared=_can_shared(user))
    except tc.TraceConfigError as exc:
        raise _http(exc)


@router.delete("/api/v1/trace-configs/{config_id}", status_code=204)
async def delete_trace_config(config_id: str, user: Viewer):
    try:
        async with acquire_conn() as conn:
            await tc.delete_config(conn, config_id, user=user.username, can_shared=_can_shared(user))
    except tc.TraceConfigError as exc:
        raise _http(exc)
