"""Публичный API v2 — стабильный набор адресов для внешних систем (ERP, биллинг, CRM, call-центр).

v1 — адреса веб-приложения: меняются вместе с ним. v2 обещает: поля только добавляются, имена и смысл
не меняются, удаление — только в v3. Описание — /api/v2/openapi.json (отдельно от адресов веба: по нему
генерируется клиент — openapi-generator, NSwag), руководство — docs/webhooks-api-v2.md.

Вход: заголовок Authorization: Bearer <ключ API> — ключ выдаёт пользователь себе в «Учётная запись → Ключ API»
(POST /api/v1/api-key, scope api, API_TOKEN_DAYS дней) или сессия веба. Права — этого пользователя: чтение —
вход, создание заявки — право «Журналы». Смена пароля закрывает ключ. ПДн маскируются как во всём API.

GET  /api/v2                       — версия и ссылки
GET  /api/v2/openapi.json          — описание v2
GET  /api/v2/events                — лента событий (те же, что у вебхуков) после курсора after
GET  /api/v2/work-orders           — наряды и заявки (status, updated_since, after_id, limit)
GET  /api/v2/work-orders/{id}      — наряд с историей статусов
POST /api/v2/work-orders           — заявка из внешней системы; Idempotency-Key — повтор без дубля
GET  /api/v2/outages               — отключения (status, updated_since, after_id, limit)
GET  /api/v2/outages/{id}          — отключение с зоной (GeoJSON)
GET  /api/v2/defects               — журнал дефектов (after_id, limit)
GET  /api/v2/defects/{id}          — дефект

Списки: {"data": [...], "next_after_id": <id последнего или null>} — по возрастанию id; следующая страница —
after_id=next_after_id. Ошибки — {"detail": "..."} с кодом HTTP. Время — ISO 8601 с часовым поясом.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, Literal, Optional

import asyncpg
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Path, Query, Request, Response
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel, Field

import activity
from auth import (
    AuthUser,
    apply_live_user_status,
    auth_disabled,
    bind_db_role,
    create_access_token,
    decode_access_token,
    get_current_user,
    jwt_algorithm,
    jwt_secret,
    mutations_enabled,
)
from cities import current_city
from database import api_events
from database import outages as og
from database import work_orders as wo
from database.connect import acquire_conn
from database.defects import DEFECT_SUMMARY_SELECT
from routers.mcp import PASSWORD_CLAIM, _password_fingerprint
from routers.ogc import _root

router = APIRouter(prefix="/api/v2", tags=["api-v2"])
key_router = APIRouter(tags=["api-v2"])

API_SCOPE = "api"
API_VERSION = "2.0.0"
DEFAULT_TOKEN_DAYS = 365
MAX_TOKEN_DAYS = 730
DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def token_days() -> int:
    try:
        days = int(os.getenv("API_TOKEN_DAYS", str(DEFAULT_TOKEN_DAYS)))
    except ValueError:
        days = DEFAULT_TOKEN_DAYS
    return max(1, min(MAX_TOKEN_DAYS, days))


async def api_user(request: Request) -> AuthUser:
    """Ключ API (scope api) или сессия веба; ключ — пока не сменён пароль."""
    if auth_disabled():
        return AuthUser(sub="dev", role="admin", username="dev")
    header = request.headers.get("authorization") or ""
    if not header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Нужен заголовок Authorization: Bearer <ключ API>",
                            headers={"WWW-Authenticate": "Bearer"})
    token = header.split(" ", 1)[1].strip()
    user = await apply_live_user_status(decode_access_token(token, allow_scopes=(API_SCOPE,)))
    if user.scope == API_SCOPE:
        claim = str(jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()]).get(PASSWORD_CLAIM) or "")
        try:
            current = await _password_fingerprint(user.sub)
        except Exception as exc:  # noqa: BLE001 — долгий ключ без проверки не пускаем
            raise HTTPException(status_code=401, detail="Не удалось проверить ключ — попробуйте позже") from exc
        if current is not None and not hmac.compare_digest(claim, current):
            raise HTTPException(status_code=401, detail="Пароль сменён — выдайте новый ключ API")
    bind_db_role(user)
    return user


User = Annotated[AuthUser, Depends(api_user)]
Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT, description="Сколько записей на странице")]
AfterId = Annotated[int, Query(ge=0, description="Курсор: записи с id больше этого")]
ObjId = Annotated[int, Path(ge=1)]


# --- модели ответа (описание для генераторов клиента) ------------------------------------------

class Event(BaseModel):
    id: str = Field(description="Ключ события; повтор доставки — с тем же ключом")
    seq: int = Field(description="Номер в ленте: курсор after")
    type: str
    occurred_at: str
    city: str
    data: dict[str, Any]


class EventPage(BaseModel):
    data: list[Event]
    next_after: int = Field(description="Передать как after в следующий запрос")
    has_more: bool


class StatusChange(BaseModel):
    at: datetime
    from_status: Optional[str] = None
    to_status: str
    note: str = ""


class WorkOrder(BaseModel):
    id: int
    number: str
    title: str
    kind: str
    priority: int = Field(description="1 — аварийный, 2 — срочный, 3 — плановый")
    status: str = Field(description="new, assigned, in_progress, done, closed, cancelled")
    defect_id: Optional[int] = None
    line_id: Optional[int] = None
    node_id: Optional[int] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    brigade_id: Optional[int] = None
    brigade_name: Optional[str] = None
    planned_start: Optional[datetime] = None
    planned_finish: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    arrived_at: Optional[datetime] = None
    description: str = ""
    result: str = ""
    overdue: bool = False
    created_at: datetime
    updated_at: datetime
    revision: int
    history: Optional[list[StatusChange]] = Field(None, description="Только в карточке: смены статуса")


class WorkOrderPage(BaseModel):
    data: list[WorkOrder]
    next_after_id: Optional[int]


class WorkOrderCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field("", max_length=5000)
    kind: Literal["repair", "inspection", "pressure_test", "excavation", "maintenance", "other"] = "repair"
    priority: int = Field(2, ge=1, le=3)
    line_id: Optional[int] = Field(None, ge=1, description="Участок, если известен")
    node_id: Optional[int] = Field(None, ge=1)
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Место заявки, WGS 84")
    lat: Optional[float] = Field(None, ge=-90, le=90)
    planned_finish: Optional[datetime] = None


class Outage(BaseModel):
    id: int
    number: str
    title: str
    kind: str = Field(description="planned, emergency")
    status: str = Field(description="planned, announced, active, finished, cancelled")
    line_id: Optional[int] = None
    node_id: Optional[int] = None
    work_order_id: Optional[int] = None
    lon: Optional[float] = None
    lat: Optional[float] = None
    planned_start: datetime
    planned_end: datetime
    actual_start: Optional[datetime] = None
    actual_end: Optional[datetime] = None
    reason: str = ""
    public: bool = False
    public_note: str = ""
    consumers_count: int = 0
    load_gcal_h: float = 0
    valves_count: int = 0
    computed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    revision: int
    area: Optional[dict[str, Any]] = Field(None, description="Только в карточке: зона отключения, GeoJSON (WGS 84)")
    history: Optional[list[StatusChange]] = None


class OutagePage(BaseModel):
    data: list[Outage]
    next_after_id: Optional[int]


class Defect(BaseModel):
    id: int
    line_id: Optional[int] = None
    detected_at: Optional[datetime] = Field(None, description="Дата и время осмотра (местное время города)")
    description: Optional[str] = None
    category: Optional[str] = None
    state: Optional[str] = None
    source: Optional[str] = None
    violation_type: Optional[str] = None
    address: Optional[str] = None
    repair_started_on: Optional[date] = None
    repair_finished_on: Optional[date] = None
    lon: Optional[float] = None
    lat: Optional[float] = None


class DefectPage(BaseModel):
    data: list[Defect]
    next_after_id: Optional[int]


# --- служебное ---------------------------------------------------------------------------------

def _page_filters(after_id: int, status: Optional[str], updated_since: Optional[datetime],
                  alias: str) -> tuple[str, list[Any]]:
    args: list[Any] = [after_id]
    where = [f"{alias}.id > $1"]
    if status:
        args.append(status)
        where.append(f"{alias}.status = ${len(args)}")
    if updated_since:
        if updated_since.tzinfo is None:
            updated_since = updated_since.replace(tzinfo=timezone.utc)
        args.append(updated_since)
        where.append(f"{alias}.updated_at >= ${len(args)}")
    return " AND ".join(where), args


def _next(items: list[Any], limit: int) -> Optional[int]:
    return items[-1]["id"] if len(items) == limit else None


def _history(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"at": e["at"], "from_status": e.get("from_status"), "to_status": e["to_status"], "note": e.get("note") or ""}
            for e in events if e.get("to_status")]


def _fields(model: type[BaseModel], row: dict[str, Any], skip: set[str]) -> dict[str, Any]:
    """Поля модели из строки базы; пустое значение поля со значением по умолчанию — значение по умолчанию."""
    out = {}
    for name, field in model.model_fields.items():
        if name in skip:
            continue
        value = row.get(name)
        out[name] = field.default if value is None and field.default is not None else value
    return out


def _work_order(row: dict[str, Any]) -> dict[str, Any]:
    return _fields(WorkOrder, row, {"history"}) | {"overdue": bool(row.get("overdue")),
                                                  "number": row.get("number") or ""}


def _outage(row: dict[str, Any]) -> dict[str, Any]:
    valves = row.get("valves")
    if isinstance(valves, str):
        valves = json.loads(valves)
    count = row["valves_count"] if "valves_count" in row else len(valves or [])
    return _fields(Outage, row, {"history", "area", "valves_count"}) | {"valves_count": count,
                                                                      "number": row.get("number") or ""}


# --- ключ API ----------------------------------------------------------------------------------

@key_router.post("/api/v1/api-key")
async def api_key(request: Request, user: Annotated[AuthUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Ключ API v2 на API_TOKEN_DAYS дней: действует только на /api/v2, с правами пользователя."""
    days = token_days()
    extra: dict[str, Any] = {"scope": API_SCOPE}
    if user.mv:
        extra["mv"] = user.mv
    fingerprint = await _password_fingerprint(user.sub)
    if fingerprint:
        extra[PASSWORD_CLAIM] = fingerprint
    token = create_access_token(username=user.username, role=user.role, subject=user.sub,
                                expires_minutes=days * 24 * 60, extra=extra)
    await activity.write(username=user.username, action="API_KEY", method="POST", path="/api/v1/api-key",
                         status=200, details={"days": days}, ip=activity.client_ip(request.scope),
                         user_agent=request.headers.get("user-agent", "")[:300])
    root = _root(request)
    return {
        "token": token,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=days)).isoformat(timespec="seconds"),
        "days": days,
        "api_url": f"{root}/api/v2",
        "openapi_url": f"{root}/api/v2/openapi.json",
    }


# --- v2 ----------------------------------------------------------------------------------------

@router.get("")
async def v2_index(request: Request, _: User) -> dict[str, Any]:
    root = _root(request)
    return {"version": API_VERSION, "city": current_city(), "openapi": f"{root}/api/v2/openapi.json",
            "event_types": api_events.EVENT_TYPES}


@router.get("/openapi.json", include_in_schema=False)
async def v2_openapi(request: Request) -> dict[str, Any]:
    routes = [r for r in request.app.routes if getattr(r, "path", "").startswith("/api/v2")]
    schema = get_openapi(title="ТГИД API v2", version=API_VERSION, routes=routes,
                         description="Стабильный API ТГИД для внешних систем: события, наряды, отключения, дефекты. "
                                     "Вход — Authorization: Bearer <ключ API>.")
    schema.setdefault("components", {})["securitySchemes"] = {"bearer": {"type": "http", "scheme": "bearer"}}
    schema["security"] = [{"bearer": []}]
    return schema


@router.get("/events", response_model=EventPage)
async def v2_events(_: User, after: Annotated[int, Query(ge=0, description="seq последнего полученного события")] = 0,
                    types: Annotated[Optional[str], Query(max_length=300, description="Типы через запятую")] = None,
                    limit: Limit = DEFAULT_LIMIT) -> dict[str, Any]:
    wanted = [t.strip() for t in (types or "").split(",") if t.strip()]
    unknown = [t for t in wanted if t not in api_events.EVENT_TYPES]
    if unknown:
        raise HTTPException(status_code=422, detail=f"Неизвестные типы событий: {', '.join(unknown)}")
    async with acquire_conn() as conn:
        return await api_events.feed(conn, current_city(), after=after, types=wanted or None, limit=limit)


@router.get("/work-orders", response_model=WorkOrderPage)
async def v2_work_orders(_: User, after_id: AfterId = 0, limit: Limit = DEFAULT_LIMIT,
                         status: Optional[Literal["new", "assigned", "in_progress", "done", "closed", "cancelled"]] = None,
                         updated_since: Optional[datetime] = None) -> dict[str, Any]:
    where, args = _page_filters(after_id, status, updated_since, "o")
    args.append(limit)
    async with acquire_conn() as conn:
        rows = await conn.fetch(f"{wo._SELECT} WHERE {where} ORDER BY o.id LIMIT ${len(args)}", *args)
    items = [_work_order(dict(r)) for r in rows]
    return {"data": items, "next_after_id": _next(items, limit)}


@router.get("/work-orders/{order_id}", response_model=WorkOrder)
async def v2_work_order(order_id: ObjId, _: User) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            order = await wo.get_order(conn, order_id)
    except wo.WorkOrderError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return _work_order(order) | {"history": _history(order.get("events") or [])}


@router.post("/work-orders", response_model=WorkOrder, status_code=201)
async def v2_work_order_create(
    body: WorkOrderCreate, response: Response, user: User,
    idempotency_key: Annotated[Optional[str], Header(max_length=100, description="Повтор с тем же ключом — тот же наряд")] = None,
) -> dict[str, Any]:
    if not mutations_enabled():
        raise HTTPException(status_code=503, detail="Правки выключены на сервере (MUTATIONS_ENABLED)")
    if not user.perms.has("journals"):
        raise HTTPException(status_code=403, detail="Нет права «Журналы»")
    if body.line_id is None and body.node_id is None and (body.lon is None or body.lat is None):
        raise HTTPException(status_code=422, detail="Нужно место: line_id, node_id или lon и lat")
    client_id = idempotency_id(user.sub, idempotency_key) if idempotency_key else None
    try:
        async with acquire_conn() as conn:
            order = await _replayed(conn, client_id, user.username, body.title)
            if order is None:
                try:
                    order = await wo.create(conn, wo.WorkOrderIn(**body.model_dump()), user.username,
                                            wo.FieldStamp(client_id=client_id))
                except asyncpg.UniqueViolationError:
                    # тот же ключ в параллельном запросе успел раньше
                    order = await _replayed(conn, client_id, user.username, body.title)
                    if order is None:
                        raise
            else:
                response.status_code = 200
                response.headers["Idempotent-Replayed"] = "true"
    except wo.WorkOrderError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return _work_order(order) | {"history": _history(order.get("events") or [])}


def idempotency_id(sub: str, key: str) -> uuid.UUID:
    """Ключ действия наряда из (пользователь, Idempotency-Key): HMAC с секретом сервера — не угадать заранее."""
    digest = hmac.new(jwt_secret().encode(), f"api-v2:{sub}:{key}".encode(), hashlib.sha256).digest()
    return uuid.UUID(bytes=digest[:16], version=4)


async def _replayed(conn, client_id: Optional[uuid.UUID], username: str, title: str) -> Optional[dict[str, Any]]:
    """Наряд, уже созданный этим пользователем с этим ключом; ключ с другой заявкой — 422."""
    if client_id is None:
        return None
    row = await conn.fetchrow("SELECT order_id, by_user FROM tgid_work_order_event WHERE client_id = $1", client_id)
    if row is None:
        return None
    order = await wo.get_order(conn, row["order_id"])
    if row["by_user"] != username or order.get("title") != title:
        raise HTTPException(status_code=422, detail="Idempotency-Key уже использован для другой заявки")
    return order


# список — без зоны и потребителей (jsonb до сотен КБ на отключение): только число задвижек
_OUTAGE_LIST = ", ".join(f"o.{c}" for c in Outage.model_fields if c not in ("area", "history", "valves_count")) +     ", jsonb_array_length(o.valves) AS valves_count"


@router.get("/outages", response_model=OutagePage)
async def v2_outages(_: User, after_id: AfterId = 0, limit: Limit = DEFAULT_LIMIT,
                     status: Optional[Literal["planned", "announced", "active", "finished", "cancelled"]] = None,
                     updated_since: Optional[datetime] = None) -> dict[str, Any]:
    where, args = _page_filters(after_id, status, updated_since, "o")
    args.append(limit)
    async with acquire_conn() as conn:
        rows = await conn.fetch(
            f"SELECT {_OUTAGE_LIST} FROM tgid_outage o WHERE {where} ORDER BY o.id LIMIT ${len(args)}", *args)
    items = [_outage(dict(r)) for r in rows]
    return {"data": items, "next_after_id": _next(items, limit)}


@router.get("/outages/{outage_id}", response_model=Outage)
async def v2_outage(outage_id: ObjId, _: User) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            outage = await og.get_outage(conn, outage_id)
    except og.OutageError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    return _outage(outage) | {"area": outage.get("area"), "history": _history(outage.get("events") or [])}


_DEFECT_V2 = f"""
    SELECT x.id, x.line_id, x.detected_at, x.description, x.category_name AS category,
           x.state_name AS state, x.source_name AS source, x.violation_type_name AS violation_type, x.address,
           x.repair_started_on, x.repair_finished_on, x.longitude AS lon, x.latitude AS lat
      FROM ({DEFECT_SUMMARY_SELECT}) x
"""


@router.get("/defects", response_model=DefectPage)
async def v2_defects(_: User, after_id: AfterId = 0, limit: Limit = DEFAULT_LIMIT) -> dict[str, Any]:
    async with acquire_conn() as conn:
        rows = await conn.fetch(f"{_DEFECT_V2} WHERE x.id > $1 ORDER BY x.id LIMIT $2", after_id, limit)
    items = [dict(r) for r in rows]
    return {"data": items, "next_after_id": _next(items, limit)}


@router.get("/defects/{defect_id}", response_model=Defect)
async def v2_defect(defect_id: ObjId, _: User) -> dict[str, Any]:
    async with acquire_conn() as conn:
        row = await conn.fetchrow(f"{_DEFECT_V2} WHERE x.id = $1", defect_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Дефект {defect_id} не найден")
    return dict(row)
