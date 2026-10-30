"""Наряды и заявки (фаза 2): заявка или дефект → наряд → бригада → выполнение → закрытие.

Наряд — запись tgid_work_order (таблица веба, sql/migrations/20261030_work_orders.sql) со статусом,
бригадой (brigades) и ответственным (nachalniki_uchastkov), местом работ (дефект, участок, узел или точка)
и плановыми сроками. Каждая смена статуса и правка — строка истории tgid_work_order_event.

Связь с журналом дефектов десктопа: наряд по дефекту при начале работ ставит дефекту дату начала ремонта
и состояние «Ремонт», при выполнении — дату завершения и «После ремонта» (statedefect 2 и 3), как это
делает журнал дефектов. Остальные поля дефекта наряд не трогает.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from database.journal_specs import DEFECTS
from database.journal_write import JournalWriteError, create_record
from database.net_srid import line_inner_sql, net_srid

KINDS: dict[str, str] = {
    "repair": "Ремонт", "inspection": "Осмотр", "pressure_test": "Опрессовка", "excavation": "Шурфовка",
    "maintenance": "Обслуживание", "other": "Прочее",
}
PRIORITIES: dict[int, str] = {1: "Аварийный", 2: "Срочный", 3: "Плановый"}
STATUSES: dict[str, str] = {
    "new": "Заявка", "assigned": "Назначен", "in_progress": "В работе", "done": "Выполнен",
    "closed": "Закрыт", "cancelled": "Отменён",
}
# допустимые переходы: вперёд по цепочке, назад на шаг (вернуть в работу), отмена до выполнения
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "new": ("assigned", "cancelled"),
    "assigned": ("in_progress", "new", "cancelled"),
    "in_progress": ("done", "assigned", "cancelled"),
    "done": ("closed", "in_progress"),
    "closed": (),
    "cancelled": ("new",),
}
FINAL = frozenset({"closed", "cancelled"})
OPEN = ("new", "assigned", "in_progress")
DEFECT_STATE_FOUND = 1       # statedefect «Нарушение» — дефект только записан
DEFECT_STATE_REPAIR = 2      # statedefect «Ремонт»
DEFECT_STATE_AFTER = 3       # statedefect «После ремонта»
# дефект с места: участок под ним — ближайший к точке телефона не дальше этого (GPS телефона — 5–20 м)
FIELD_DEFECT_SNAP_M = 30.0
_SNAP_CANDIDATES = 5
MAX_LIST = 1000
# фото с места работ: уменьшаются на телефоне; в базе — до 2 МБ на фото и 30 фото на наряд
MAX_PHOTO_BYTES = 2_000_000
MAX_PHOTOS = 30
_IMAGE_SIGNATURES = (("image/jpeg", b"\xff\xd8\xff"), ("image/png", b"\x89PNG\r\n\x1a\n"))

Kind = Literal["repair", "inspection", "pressure_test", "excavation", "maintenance", "other"]
Status = Literal["new", "assigned", "in_progress", "done", "closed", "cancelled"]


class WorkOrderError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class WorkOrderIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    kind: Kind = "repair"
    priority: int = Field(3, ge=1, le=3)
    defect_id: Optional[int] = Field(None, ge=1)
    inspection_id: Optional[int] = Field(None, ge=1, description="Контур осмотра (osmotr): наряд на обход его участков")
    line_id: Optional[int] = Field(None, ge=1)
    node_id: Optional[int] = Field(None, ge=1)
    lon: Optional[float] = Field(None, ge=-180, le=180)
    lat: Optional[float] = Field(None, ge=-90, le=90)
    brigade_id: Optional[int] = Field(None, ge=1)
    responsible_id: Optional[int] = Field(None, ge=1)
    planned_start: Optional[datetime] = None
    planned_finish: Optional[datetime] = None
    description: str = Field("", max_length=5000)


class WorkOrderPatch(BaseModel):
    revision: int = Field(..., ge=1, description="Версия, которую правили (409, если наряд уже изменили)")
    title: Optional[str] = Field(None, min_length=1, max_length=300)
    kind: Optional[Kind] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    brigade_id: Optional[int] = Field(None, ge=0, description="0 — снять бригаду")
    responsible_id: Optional[int] = Field(None, ge=0, description="0 — снять ответственного")
    planned_start: Optional[datetime] = None
    planned_finish: Optional[datetime] = None
    description: Optional[str] = Field(None, max_length=5000)
    result: Optional[str] = Field(None, max_length=5000)


class FieldStamp(BaseModel):
    """Действие с устройства в поле: ключ (повтор без дублей) и где был телефон."""
    client_id: Optional[UUID] = Field(None, description="Ключ действия; повтор с тем же ключом — без изменений")
    lon: Optional[float] = Field(None, ge=-180, le=180)
    lat: Optional[float] = Field(None, ge=-90, le=90)


class TransitionIn(FieldStamp):
    to: Status
    revision: int = Field(..., ge=1)
    note: str = Field("", max_length=2000)
    result: Optional[str] = Field(None, max_length=5000, description="Что сделано — при выполнении")


class CommentIn(FieldStamp):
    note: str = Field(..., min_length=1, max_length=2000)


class FieldDefectIn(FieldStamp):
    """«Дефект одной кнопкой» с обхода: точка телефона, что увидели — запись в журнал дефектов и заявка."""
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    description: str = Field(..., min_length=1, max_length=2000)
    line_id: Optional[int] = Field(None, ge=1, description="Участок; нет — ближайший к точке (до 30 м)")
    source_id: Optional[int] = Field(None, ge=1, description="Источник (defecttypes), обычно «Осмотр»")
    category_id: Optional[int] = Field(None, ge=1, description="Категория (remontcat)")
    priority: int = Field(2, ge=1, le=3)
    found_at: Optional[datetime] = Field(None, description="Когда нашли (действие могло ждать связи)")
    order_id: Optional[int] = Field(None, ge=1, description="Наряд на обход, в котором нашли (дефект — в его контур осмотра)")
    node_id: Optional[int] = Field(None, ge=1, description="Узел маршрута обхода — отметка «с дефектом»")


class CheckIn(FieldStamp):
    """Отметка узла маршрута обхода."""
    node_id: int = Field(..., ge=1)
    state: Literal["ok", "defect"]
    note: str = Field("", max_length=500)


# --- чтение ---------------------------------------------------------------------------------

_SELECT = """
    SELECT o.*, b.name AS brigade_name, r.fio AS responsible_name, d.name AS defect_name,
           d.stateid AS defect_state_id,
           (o.planned_finish IS NOT NULL AND o.planned_finish < now() AND o.status IN ('new', 'assigned', 'in_progress'))
               AS overdue
      FROM tgid_work_order o
      LEFT JOIN brigades b ON b.id = o.brigade_id
      LEFT JOIN nachalniki_uchastkov r ON r.id = o.responsible_id
      LEFT JOIN defect d ON d.id = o.defect_id
"""


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (datetime, date)) else v


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Без часового пояса — UTC (сравнение плановых сроков из формы и из базы)."""
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _parse(v: Optional[str]) -> Optional[datetime]:
    return _aware(datetime.fromisoformat(v)) if v else None


def _row(r) -> dict[str, Any]:
    out = {k: _iso(v) for k, v in dict(r).items()}
    out["status_label"] = STATUSES.get(out["status"], out["status"])
    out["kind_label"] = KINDS.get(out["kind"], out["kind"])
    out["priority_label"] = PRIORITIES.get(out["priority"], str(out["priority"]))
    out["next"] = list(TRANSITIONS.get(out["status"], ()))
    return out


async def lookups(conn) -> dict[str, Any]:
    brigades = await conn.fetch("SELECT id, name FROM brigades ORDER BY name NULLS LAST, id")
    people = await conn.fetch("SELECT id, fio AS name FROM nachalniki_uchastkov ORDER BY fio NULLS LAST, id")
    return {
        "brigades": [{"id": r["id"], "name": (r["name"] or f"Бригада {r['id']}").strip()} for r in brigades],
        "responsibles": [{"id": r["id"], "name": (r["name"] or f"№{r['id']}").strip()} for r in people],
        "kinds": [{"value": k, "label": v} for k, v in KINDS.items()],
        "priorities": [{"value": k, "label": v} for k, v in PRIORITIES.items()],
        "statuses": [{"value": k, "label": v} for k, v in STATUSES.items()],
        "transitions": {k: list(v) for k, v in TRANSITIONS.items()},
    }


async def list_orders(conn, *, status: Optional[str] = None, brigade_id: Optional[int] = None,
                      fileid: Optional[int] = None, q: Optional[str] = None, open_only: bool = False,
                      limit: int = 500) -> dict[str, Any]:
    where, args = [], []

    def add(sql: str, value: Any) -> None:
        args.append(value)
        where.append(sql.replace("?", f"${len(args)}"))

    if status:
        if status not in STATUSES:
            raise WorkOrderError(422, f"Статус — один из: {', '.join(STATUSES)}")
        add("o.status = ?", status)
    elif open_only:
        add("o.status = ANY(?::text[])", list(OPEN))
    if brigade_id:
        add("o.brigade_id = ?", brigade_id)
    if fileid:
        add("o.fileid = ?", fileid)
    if q and q.strip():
        args.append(q.strip()[:100])
        n = f"${len(args)}"
        where.append(f"(o.title ILIKE '%' || {n} || '%' OR o.number ILIKE '%' || {n} || '%'"
                     f" OR o.description ILIKE '%' || {n} || '%')")
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    args.append(min(max(limit, 1), MAX_LIST))
    rows = await conn.fetch(
        f"""{_SELECT} {sql_where}
          ORDER BY (o.status IN ('closed', 'cancelled')), o.priority, o.planned_finish NULLS LAST, o.id DESC
          LIMIT ${len(args)}""", *args)
    counts = {r["status"]: r["n"] for r in await conn.fetch(
        "SELECT status, count(*) AS n FROM tgid_work_order GROUP BY status")}
    overdue = await conn.fetchval(
        "SELECT count(*) FROM tgid_work_order WHERE planned_finish < now() AND status = ANY($1::text[])", list(OPEN))
    return {"items": [_row(r) for r in rows], "counts": {k: counts.get(k, 0) for k in STATUSES},
            "overdue": overdue}


async def get_order(conn, order_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(f"{_SELECT} WHERE o.id = $1", order_id)
    if row is None:
        raise WorkOrderError(404, f"Наряд {order_id} не найден")
    out = _row(row)
    events = await conn.fetch(
        "SELECT at, by_user, from_status, to_status, note, lon, lat FROM tgid_work_order_event WHERE order_id = $1"
        " ORDER BY at, id", order_id)
    out["events"] = [{**{k: _iso(v) for k, v in dict(e).items()},
                      "to_label": STATUSES.get(e["to_status"]) if e["to_status"] else None} for e in events]
    photos = await conn.fetch(
        "SELECT id, caption, content_type, size, lon, lat, taken_at, by_user, created_at FROM tgid_work_order_photo"
        " WHERE order_id = $1 ORDER BY created_at, id", order_id)
    out["photos"] = [{k: _iso(v) for k, v in dict(p).items()} for p in photos]
    return out


async def geojson(conn, *, open_only: bool = True) -> dict[str, Any]:
    rows = await conn.fetch(
        """SELECT id, number, title, status, priority, kind, lon, lat FROM tgid_work_order
            WHERE lon IS NOT NULL AND lat IS NOT NULL AND ($1::bool IS FALSE OR status = ANY($2::text[]))""",
        open_only, list(OPEN))
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature", "id": r["id"],
        "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "properties": {"id": r["id"], "number": r["number"], "title": r["title"], "status": r["status"],
                       "priority": r["priority"], "kind": r["kind"]},
    } for r in rows]}


# --- место работ ----------------------------------------------------------------------------

async def _place_of_defect(conn, defect_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """SELECT d.id, d.name, d.lineid, d.defectdescription,
                  ST_X(ST_Transform(d.shape, 4326)) AS lon, ST_Y(ST_Transform(d.shape, 4326)) AS lat
             FROM defect d WHERE d.id = $1""", defect_id)
    if row is None:
        raise WorkOrderError(422, f"Дефекта {defect_id} нет в журнале")
    return dict(row)


async def _place_of_line(conn, line_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """SELECT fileid, ST_X(ST_Transform(ST_PointOnSurface(shape), 4326)) AS lon,
                  ST_Y(ST_Transform(ST_PointOnSurface(shape), 4326)) AS lat
             FROM linesobj WHERE id = $1 AND COALESCE(removed, 0) = 0""", line_id)
    if row is None:
        raise WorkOrderError(422, f"Участка {line_id} нет (или он удалён)")
    return dict(row)


async def _place_of_node(conn, node_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """SELECT fileid, ST_X(ST_Transform(shape, 4326)) AS lon, ST_Y(ST_Transform(shape, 4326)) AS lat
             FROM nodes WHERE id = $1 AND COALESCE(removed, 0) = 0""", node_id)
    if row is None:
        raise WorkOrderError(422, f"Узла {node_id} нет (или он удалён)")
    return dict(row)


async def _place_of_inspection(conn, inspection_id: int) -> dict[str, Any]:
    row = await conn.fetchrow(
        """SELECT i.id, i.name,
                  ST_X(ST_Centroid(ST_Collect(ST_Transform(l.shape, 4326)))) AS lon,
                  ST_Y(ST_Centroid(ST_Collect(ST_Transform(l.shape, 4326)))) AS lat
             FROM osmotr i
             LEFT JOIN osmotrdeployed r ON r.directionid = i.id
             LEFT JOIN linesobj l ON l.id = r.lineid AND COALESCE(l.removed, 0) = 0
            WHERE i.id = $1
            GROUP BY i.id, i.name""", inspection_id)
    if row is None:
        raise WorkOrderError(422, f"Контура осмотра {inspection_id} нет в журнале")
    if row["lon"] is None:
        raise WorkOrderError(422, f"В контуре осмотра «{row['name'] or inspection_id}» нет участков")
    return dict(row)


async def _check_people(conn, brigade_id: Optional[int], responsible_id: Optional[int]) -> None:
    if brigade_id and not await conn.fetchval("SELECT EXISTS (SELECT 1 FROM brigades WHERE id = $1)", brigade_id):
        raise WorkOrderError(422, f"Бригады {brigade_id} нет в справочнике")
    if responsible_id and not await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM nachalniki_uchastkov WHERE id = $1)", responsible_id):
        raise WorkOrderError(422, f"Ответственного {responsible_id} нет в справочнике")


async def _event(conn, order_id: int, user: str, note: str, from_status: Optional[str] = None,
                 to_status: Optional[str] = None, stamp: Optional[FieldStamp] = None) -> None:
    await conn.execute(
        """INSERT INTO tgid_work_order_event (order_id, by_user, from_status, to_status, note, client_id, lon, lat)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
        order_id, user, from_status, to_status, note, stamp.client_id if stamp else None,
        stamp.lon if stamp else None, stamp.lat if stamp else None)


async def _already_done(conn, stamp: Optional[FieldStamp]) -> bool:
    """Действие с этим ключом уже записано (повтор отправки из очереди устройства)."""
    if stamp is None or stamp.client_id is None:
        return False
    return bool(await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM tgid_work_order_event WHERE client_id = $1)"
        " OR EXISTS (SELECT 1 FROM tgid_work_order_photo WHERE client_id = $1)"
        " OR EXISTS (SELECT 1 FROM tgid_work_order_check WHERE client_id = $1)", stamp.client_id))


# --- запись ---------------------------------------------------------------------------------

async def create(conn, body: WorkOrderIn, user: str, stamp: Optional[FieldStamp] = None) -> dict[str, Any]:
    if body.planned_start and body.planned_finish and _aware(body.planned_finish) < _aware(body.planned_start):
        raise WorkOrderError(422, "Плановое окончание раньше начала")
    await _check_people(conn, body.brigade_id, body.responsible_id)
    line_id, node_id, fileid = body.line_id, body.node_id, None
    lon, lat, description = body.lon, body.lat, body.description
    created_note = f"Создан по дефекту №{body.defect_id}" if body.defect_id else "Создан"
    if body.inspection_id:
        inspection = await _place_of_inspection(conn, body.inspection_id)
        name = (inspection["name"] or f"№{body.inspection_id}").strip()
        if lon is None:
            lon, lat = inspection["lon"], inspection["lat"]
        description = description or f"Обход участков контура осмотра «{name}»"
        created_note = f"Создан по контуру осмотра «{name}»"
    if body.defect_id:
        defect = await _place_of_defect(conn, body.defect_id)
        line_id = line_id or defect["lineid"]
        if lon is None and defect["lon"] is not None:
            lon, lat = defect["lon"], defect["lat"]
        if not description and defect["defectdescription"]:
            description = defect["defectdescription"]
    if line_id:
        place = await _place_of_line(conn, line_id)
        fileid = place["fileid"]
        if lon is None:
            lon, lat = place["lon"], place["lat"]
    if node_id:
        place = await _place_of_node(conn, node_id)
        fileid = fileid or place["fileid"]
        if lon is None:
            lon, lat = place["lon"], place["lat"]
    status = "assigned" if body.brigade_id or body.responsible_id else "new"
    async with conn.transaction():
        order_id = await conn.fetchval(
            """INSERT INTO tgid_work_order (title, kind, priority, status, defect_id, line_id, node_id, fileid, lon, lat,
                                            brigade_id, responsible_id, planned_start, planned_finish, description,
                                            created_by, updated_by, inspection_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $16, $17) RETURNING id""",
            body.title.strip(), body.kind, body.priority, status, body.defect_id, line_id, node_id, fileid, lon, lat,
            body.brigade_id, body.responsible_id, body.planned_start, body.planned_finish, description, user,
            body.inspection_id)
        await conn.execute(
            "UPDATE tgid_work_order SET number = 'Н-' || to_char(created_at, 'YYYY') || '-' || lpad(id::text, 5, '0') "
            "WHERE id = $1", order_id)
        await _event(conn, order_id, user, created_note, None, status, stamp)
    return await get_order(conn, order_id)


# --- дефект с места -------------------------------------------------------------------------

async def nearest_line(conn, lon: float, lat: float, meters: float = FIELD_DEFECT_SNAP_M) -> Optional[int]:
    """Участок основной сети ближе всего к точке, не дальше meters; без участков внутренних схем узлов
    и копий-сценариев (у них та же геометрия, что у основы)."""
    rows = await conn.fetch(
        f"""WITH p AS (SELECT ST_SetSRID(ST_MakePoint($1, $2), 4326) AS g)
            SELECT l.id, ST_Distance(ST_Transform(l.shape, 4326)::geography, p.g::geography) AS m
              FROM linesobj l, p
             WHERE COALESCE(l.removed, 0) = 0 AND l.shape IS NOT NULL AND {line_inner_sql('l')} IS NULL
               AND NOT EXISTS (SELECT 1 FROM tgid_scenario s WHERE s.fileid = l.fileid)
             ORDER BY l.shape <-> ST_Transform(p.g, {net_srid()})
             LIMIT {_SNAP_CANDIDATES}""", lon, lat)
    # пары подачи и обратки и копии лежат на одной линии — при равном расстоянии меньший номер, без случайности
    best = min(rows, key=lambda r: (round(r["m"], 2), r["id"]), default=None)
    return best["id"] if best is not None and best["m"] <= meters else None


def _local(dt: Optional[datetime]) -> datetime:
    """Время журнала дефектов десктопа — местное, без пояса."""
    moment = _aware(dt) if dt else datetime.now(timezone.utc)
    return moment.astimezone().replace(tzinfo=None, microsecond=0)


async def order_of_action(conn, client_id: Optional[UUID]) -> Optional[dict[str, Any]]:
    """Наряд, в истории которого уже есть действие с этим ключом (повтор отправки из очереди)."""
    if client_id is None:
        return None
    order_id = await conn.fetchval("SELECT order_id FROM tgid_work_order_event WHERE client_id = $1", client_id)
    return await get_order(conn, order_id) if order_id is not None else None


async def report_defect(conn, body: FieldDefectIn, user: str) -> tuple[dict[str, Any], bool]:
    """Дефект с обхода: строка журнала дефектов десктопа (состояние «Нарушение», точка телефона, участок
    под ней) и заявка на ремонт по нему. Ключ действия — у события создания заявки: повтор из очереди
    телефона возвращает ту же заявку (второе значение — False), второй дефект не пишется.
    Вызывать в транзакции: дефект без заявки не остаётся."""
    existing = await order_of_action(conn, body.client_id)
    if existing is not None:
        return existing, False
    text = body.description.strip()
    if not text:
        raise WorkOrderError(422, "Опишите, что нашли")
    parent = await get_order(conn, body.order_id) if body.order_id else None
    line_id = body.line_id
    if not line_id and parent and parent.get("inspection_id") and body.node_id:
        # дефект с узла обхода — участок контура у этого узла (точка телефона может быть в стороне от трубы)
        line_id = await conn.fetchval(
            """SELECT l.id FROM osmotrdeployed r JOIN linesobj l ON l.id = r.lineid
                WHERE r.directionid = $1 AND $2 IN (l.nodeid1, l.nodeid2) ORDER BY r.id LIMIT 1""",
            parent["inspection_id"], body.node_id)
    line_id = line_id or await nearest_line(conn, body.lon, body.lat)
    found = _local(body.found_at)
    fields: dict[str, Any] = {
        "detected_at": found.isoformat(), "detected_time": found.strftime("%H:%M"),
        "description": text, "state_id": DEFECT_STATE_FOUND,
    }
    inspection_id = parent.get("inspection_id") if parent else None
    for key, value in (("line_id", line_id), ("source_id", body.source_id), ("category_id", body.category_id),
                       ("inspection_id", inspection_id)):
        if value is not None:
            fields[key] = value
    try:
        created = await create_record(conn, DEFECTS, fields, longitude=body.lon, latitude=body.lat)
    except JournalWriteError as exc:
        detail = exc.detail.get("message", str(exc.detail)) if isinstance(exc.detail, dict) else str(exc.detail)
        raise WorkOrderError(exc.status, f"Дефект не записан: {detail}") from exc
    title = f"Дефект: {text.splitlines()[0][:120]}"
    order = WorkOrderIn(title=title, kind="repair", priority=body.priority, defect_id=created["id"],
                        line_id=line_id, lon=body.lon, lat=body.lat, description=text)
    created_order = await create(conn, order, user, body)
    if parent and inspection_id and body.node_id:
        await upsert_check(conn, parent["id"], body.node_id, "defect", user, note=text[:500], defect_id=created["id"])
    return created_order, True


async def upsert_check(conn, order_id: int, node_id: int, state: str, user: str, *, note: str = "",
                       defect_id: Optional[int] = None, stamp: Optional[FieldStamp] = None) -> None:
    """Отметка узла маршрута обхода; повторная отметка узла заменяет прежнюю (дефект узла не теряется)."""
    await conn.execute(
        """INSERT INTO tgid_work_order_check (order_id, node_id, state, note, defect_id, client_id, lon, lat, by_user)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           ON CONFLICT (order_id, node_id) DO UPDATE
              SET state = EXCLUDED.state, note = EXCLUDED.note,
                  defect_id = COALESCE(EXCLUDED.defect_id, tgid_work_order_check.defect_id),
                  client_id = EXCLUDED.client_id, lon = EXCLUDED.lon, lat = EXCLUDED.lat,
                  by_user = EXCLUDED.by_user, at = now()""",
        order_id, node_id, state, note, defect_id, stamp.client_id if stamp else None,
        stamp.lon if stamp else None, stamp.lat if stamp else None, user)


_FIELD_LABELS = {"title": "название", "kind": "вид", "priority": "срочность", "brigade_id": "бригада",
                 "responsible_id": "ответственный", "planned_start": "плановое начало",
                 "planned_finish": "плановое окончание", "description": "описание", "result": "результат"}


async def update(conn, order_id: int, patch: WorkOrderPatch, user: str) -> dict[str, Any]:
    current = await get_order(conn, order_id)
    if current["status"] in FINAL:
        raise WorkOrderError(409, f"Наряд {current['number']} {current['status_label'].lower()} — правка закрыта")
    values = patch.model_dump(exclude_unset=True, exclude={"revision"})
    for key in ("brigade_id", "responsible_id"):
        if values.get(key) == 0:
            values[key] = None  # 0 — снять
    await _check_people(conn, values.get("brigade_id"), values.get("responsible_id"))
    start = _aware(values.get("planned_start")) or _parse(current["planned_start"])
    finish = _aware(values.get("planned_finish")) or _parse(current["planned_finish"])
    if start and finish and finish < start:
        raise WorkOrderError(422, "Плановое окончание раньше начала")
    if not values:
        return current
    sets = [f"{k} = ${i}" for i, k in enumerate(values, start=3)]  # ключи — поля WorkOrderPatch
    async with conn.transaction():
        ok = await conn.fetchval(
            f"""UPDATE tgid_work_order SET {', '.join(sets)}, revision = revision + 1, updated_at = now(),
                       updated_by = ${len(values) + 3}
                 WHERE id = $1 AND revision = $2 RETURNING id""",
            order_id, patch.revision, *values.values(), user)
        if ok is None:
            raise WorkOrderError(409, "Наряд уже изменили — обновите карточку")
        await _event(conn, order_id, user, "Изменено: " + ", ".join(_FIELD_LABELS[k] for k in values))
    return await get_order(conn, order_id)


async def _sync_defect(conn, defect_id: int, to: str) -> Optional[str]:
    """Дефект десктопа: начало работ — дата начала ремонта и «Ремонт», выполнение — дата завершения и
    «После ремонта». Уже заполненные даты не переписываются."""
    today = date.today()
    if to == "in_progress":
        await conn.execute(
            "UPDATE defect SET data_nachala_remonta = COALESCE(data_nachala_remonta, $2), stateid = $3 WHERE id = $1",
            defect_id, today, DEFECT_STATE_REPAIR)
        return "дефект — «Ремонт»"
    if to == "done":
        await conn.execute(
            """UPDATE defect SET data_nachala_remonta = COALESCE(data_nachala_remonta, $2),
                                 data_zaversheniya_remonta = COALESCE(data_zaversheniya_remonta, $2), stateid = $3
                WHERE id = $1""", defect_id, today, DEFECT_STATE_AFTER)
        return "дефект — «После ремонта»"
    return None


async def _sync_inspection(conn, inspection_id: int, result: str) -> Optional[str]:
    """Контур осмотра десктопа: «Результаты осмотра» — из выполненного обхода, если там ещё пусто."""
    status = await conn.execute(
        "UPDATE osmotr SET rezultaty_osmotra = $2 WHERE id = $1 AND COALESCE(rezultaty_osmotra, '') = ''",
        inspection_id, result[:4000])
    return "контур осмотра — результаты" if str(status).endswith(" 1") else None


async def transition(conn, order_id: int, body: TransitionIn, user: str) -> dict[str, Any]:
    current = await get_order(conn, order_id)
    if await _already_done(conn, body):
        return current
    allowed = TRANSITIONS.get(current["status"], ())
    if body.to not in allowed:
        names = ", ".join(STATUSES[s] for s in allowed) or "нет"
        raise WorkOrderError(409, f"Из «{current['status_label']}» нельзя в «{STATUSES[body.to]}» (можно: {names})")
    if body.to == "assigned" and not (current["brigade_id"] or current["responsible_id"]):
        raise WorkOrderError(422, "Назначьте бригаду или ответственного")
    if body.to == "done" and not (body.result or current["result"]).strip():
        raise WorkOrderError(422, "Опишите, что сделано (результат)")
    now = datetime.now(timezone.utc)
    stamps = {"in_progress": "started_at = COALESCE(started_at, $4)", "done": "finished_at = $4",
              "closed": "closed_at = $4"}
    extra = stamps.get(body.to, "")
    async with conn.transaction():
        ok = await conn.fetchval(
            f"""UPDATE tgid_work_order SET status = $3, revision = revision + 1, updated_at = $4, updated_by = $5,
                       result = COALESCE($6, result){', ' + extra if extra else ''}
                 WHERE id = $1 AND revision = $2 RETURNING id""",
            order_id, body.revision, body.to, now, user, body.result)
        if ok is None:
            raise WorkOrderError(409, "Наряд уже изменили — обновите карточку")
        note = body.note.strip()
        if current["defect_id"] and await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM defect WHERE id = $1)", current["defect_id"]):
            synced = await _sync_defect(conn, current["defect_id"], body.to)
            if synced:
                note = f"{note}; {synced}" if note else synced
        if current.get("inspection_id") and body.to == "done":
            synced = await _sync_inspection(conn, current["inspection_id"], (body.result or current["result"]).strip())
            if synced:
                note = f"{note}; {synced}" if note else synced
        await _event(conn, order_id, user, note, current["status"], body.to, body)
    return await get_order(conn, order_id)


async def add_comment(conn, order_id: int, body: CommentIn, user: str) -> dict[str, Any]:
    current = await get_order(conn, order_id)
    if await _already_done(conn, body):
        return current
    text = body.note.strip()
    if not text:
        raise WorkOrderError(422, "Пустой комментарий")
    await _event(conn, order_id, user, text[:2000], stamp=body)
    return await get_order(conn, order_id)


# --- фото с места работ ---------------------------------------------------------------------

def image_type(data: bytes) -> Optional[str]:
    """Тип изображения по первым байтам (а не по имени файла и заголовку клиента)."""
    for content_type, signature in _IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def add_photo(conn, order_id: int, data: bytes, user: str, *, caption: str = "",
                    taken_at: Optional[datetime] = None, stamp: Optional[FieldStamp] = None) -> dict[str, Any]:
    current = await get_order(conn, order_id)
    if await _already_done(conn, stamp):
        return current
    if not data:
        raise WorkOrderError(422, "Пустой файл")
    if len(data) > MAX_PHOTO_BYTES:
        raise WorkOrderError(413, f"Фото больше {MAX_PHOTO_BYTES // 1_000_000} МБ — уменьшите его")
    content_type = image_type(data)
    if content_type is None:
        raise WorkOrderError(415, "Это не фото (JPEG, PNG или WebP)")
    if len(current.get("photos") or []) >= MAX_PHOTOS:
        raise WorkOrderError(422, f"У наряда уже {MAX_PHOTOS} фото")
    async with conn.transaction():
        await conn.execute(
            """INSERT INTO tgid_work_order_photo (order_id, client_id, caption, content_type, size, data, lon, lat,
                                                   taken_at, by_user)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
            order_id, stamp.client_id if stamp else None, caption.strip()[:500], content_type, len(data), data,
            stamp.lon if stamp else None, stamp.lat if stamp else None, _aware(taken_at), user)
        await _event(conn, order_id, user, "Фото" + (f": {caption.strip()[:200]}" if caption.strip() else ""))
    return await get_order(conn, order_id)


async def get_photo(conn, photo_id: int) -> tuple[str, bytes]:
    row = await conn.fetchrow("SELECT content_type, data FROM tgid_work_order_photo WHERE id = $1", photo_id)
    if row is None:
        raise WorkOrderError(404, f"Фото {photo_id} нет")
    return row["content_type"], bytes(row["data"])
