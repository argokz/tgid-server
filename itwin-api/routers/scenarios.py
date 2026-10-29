"""Сценарии «что если» (фаза 1): копия фрагмента для варианта сети и сравнение её с основой.

Создание пишет в сеть (копия фрагмента, как импорт .tgid) — те же права и флаги записи, что у
импорта фрагмента; список и сравнение — чтение. Перенос в основу меняет чужие объекты — права как
у применения переноса фрагментов (перемещение и удаление всех узлов и участков).
Подробно: database/scenarios.py, scenario_compare.py, scenario_merge.py.
"""

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field, StringConstraints

from auth import AuthUser, require_permission, require_roles
from database.connect import acquire_conn
from database.outage_simulation import invalidate_outage_cache
from database.scenario_compare import ITEMS_LIMIT, ScenarioCompareError, compare_scenario_calculations
from database.scenario_merge import ScenarioMergeError, merge_scenario
from database.scenarios import (
    DIFF_LIMIT,
    ScenarioError,
    create_scenario,
    list_scenarios,
    scenario_diff,
    set_scenario_status,
)
from database.topology import _run
from database.topology_rules import check_area
from routers.piezometer import invalidate_topology_cache
from routers.fragment_transfer import _require_apply_rights
from routers.topology import _topology_http_error, require_topology_mutations_enabled

router = APIRouter(tags=["scenarios"])

Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
# копия фрагмента — те же права, что у импорта фрагмента (создание участков и узлов)
Creator = Annotated[AuthUser, Depends(require_permission("import", kind="line", action="create"))]
ScenarioId = Annotated[int, Path(ge=1)]


class ScenarioCreate(BaseModel):
    base_fileid: int = Field(..., ge=1, description="Фрагмент-основа (fragments.id)")
    # хотя бы один непробельный символ: имя станет названием фрагмента
    name: str = Field(..., min_length=1, max_length=60, pattern=r"\S", description="Название сценария и его фрагмента")
    note: Optional[str] = Field(None, max_length=2000)


# «таблица:id копии» — ключ конфликта из сравнения
ConflictKey = Annotated[str, StringConstraints(pattern=r"^[a-z_]+:[0-9]+$", max_length=80)]


class ScenarioMerge(BaseModel):
    dry_run: bool = True
    resolutions: dict[ConflictKey, Literal["scenario", "base"]] = Field(
        default_factory=dict, max_length=5000,
        description="Конфликты: scenario — взять значение сценария, base — оставить основу (по умолчанию)")


class ScenarioStatus(BaseModel):
    status: Literal["active", "archived"]


def _error(e: Exception, what: str) -> HTTPException:
    if isinstance(e, (ScenarioError, ScenarioCompareError, ScenarioMergeError)):
        return HTTPException(status_code=409, detail=str(e))
    if isinstance(e, LookupError):
        return HTTPException(status_code=404, detail=str(e))
    return _topology_http_error(e, what)


@router.get("/api/v1/scenarios")
async def api_list_scenarios(_: Viewer, include_archived: bool = Query(False)):
    """Сценарии: основа, копия, автор; exists=false — фрагмент-копию удалили (например, в десктопе)."""
    async with acquire_conn() as conn:
        return {"items": await list_scenarios(conn, include_archived)}


@router.post("/api/v1/scenarios")
async def api_create_scenario(body: ScenarioCreate, user: Creator):
    """Новый сценарий: копия фрагмента-основы (как «Копия фрагмента» десктопа) с соответствием
    объектов. Отменяется как операция топологии. Крупный фрагмент копируется до минуты."""
    require_topology_mutations_enabled()
    name = body.name.strip()

    async def run(conn, op):
        rep = await create_scenario(conn, op, body.base_fileid, name, (body.note or "").strip() or None)
        await op.audit("INSERT", "fragments", rep["fileid"],
                       {"operation": "scenario_create", "scenario_id": rep["scenario_id"],
                        "base_fileid": body.base_fileid})
        return rep

    try:
        result = await _run(False, run, operation="SCENARIO_CREATE", actor=user.username)
    except Exception as e:  # noqa: BLE001
        raise _error(e, "creating scenario")
    invalidate_topology_cache()
    invalidate_outage_cache()
    return result


@router.get("/api/v1/scenarios/{scenario_id}/diff")
async def api_scenario_diff(
    scenario_id: ScenarioId, _: Viewer,
    limit: int = Query(DIFF_LIMIT, ge=1, le=5000, description="Не больше стольких отличий в items"),
):
    """Отличия сценария от основы по полям: правки сценария, конфликты, правки основы после создания."""
    async with acquire_conn() as conn:
        result = await scenario_diff(conn, scenario_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Сценарий {scenario_id} не найден")
    return result


@router.get("/api/v1/scenarios/{scenario_id}/compare")
async def api_scenario_compare(
    scenario_id: ScenarioId, _: Viewer,
    base_calculation_id: int = Query(..., ge=1, description="Расчёт фрагмента-основы"),
    scenario_calculation_id: int = Query(..., ge=1, description="Расчёт фрагмента сценария"),
    limit: int = Query(ITEMS_LIMIT, ge=1, le=2000, description="Не больше стольких изменений в items"),
):
    """Режим сценария против основы: недотоп, напоры и расходы потребителей, перегрузка участков."""
    try:
        async with acquire_conn() as conn:
            result = await compare_scenario_calculations(
                conn, scenario_id, base_calculation_id, scenario_calculation_id, limit=limit)
    except (ScenarioCompareError, LookupError) as e:
        raise _error(e, "comparing scenario calculations")
    if result is None:
        raise HTTPException(status_code=404, detail=f"Сценарий {scenario_id} не найден")
    return result


@router.post("/api/v1/scenarios/{scenario_id}/merge")
async def api_scenario_merge(
    scenario_id: ScenarioId, body: ScenarioMerge,
    user: Annotated[AuthUser, Depends(require_permission("import", kind="line", action="create"))],
):
    """Перенос правок сценария в основу. dry_run (по умолчанию) — предпросмотр с откатом: что
    изменится, пропущенные конфликты и правила связности области; иначе — одна операция журнала
    отмены (отменяется как любая правка сети)."""
    _require_apply_rights(user, body.dry_run)

    async def run(conn, op):
        rep = await merge_scenario(conn, op, scenario_id, body.resolutions)
        rep["check"] = await check_area(conn, rep["touched_nodes"], rep["touched_lines"], in_transaction=True)
        await op.audit("UPDATE", "fragments", rep["base_fileid"],
                       {"operation": "scenario_merge", "scenario_id": scenario_id,
                        "updated": rep["updated"], "inserted": rep["inserted"], "removed": rep["removed"]})
        return rep

    try:
        result = await _run(body.dry_run, run, operation="SCENARIO_MERGE", actor=user.username)
    except Exception as e:  # noqa: BLE001
        raise _error(e, "merging scenario")
    if not body.dry_run:
        invalidate_topology_cache()
        invalidate_outage_cache()
    return result


@router.post("/api/v1/scenarios/{scenario_id}/status")
async def api_scenario_status(scenario_id: ScenarioId, body: ScenarioStatus, _: Creator):
    """В архив или обратно; фрагмент-копия остаётся (удалить его — отдельное действие)."""
    require_topology_mutations_enabled()
    async with acquire_conn() as conn:
        result = await set_scenario_status(conn, scenario_id, body.status)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Сценарий {scenario_id} не найден")
    return result
