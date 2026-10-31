"""Перспективный режим: сценарий-копия фрагмента с приростом нагрузки на N лет (database/perspective_scenario.py).

GET  /api/v1/perspective/scenario-plan?fileid=&horizon=  — сколько и у каких потребителей прибавится (без записи)
POST /api/v1/perspective/scenario                       — создать сценарий с этим приростом (права — как у сценария)

Расчёт и сравнение с основой — как у любого сценария (/api/v1/scenarios/{id}/compare).
"""
from __future__ import annotations

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth import AuthUser, require_permission, require_roles
from database import load_perspective as lp
from database import perspective_scenario as ps
from database.connect import acquire_conn
from database.outage_simulation import invalidate_outage_cache
from database.scenarios import create_scenario
from database.topology import _run
from routers.piezometer import invalidate_topology_cache
from routers.scenarios import _error
from routers.topology import require_topology_mutations_enabled

router = APIRouter(tags=["perspective-scenario"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Creator = Annotated[AuthUser, Depends(require_permission("import", kind="line", action="create"))]
CONSUMERS_SHOWN = 200


class PerspectiveScenarioIn(BaseModel):
    fileid: int = Field(..., ge=1, description="Фрагмент-основа")
    horizon: int = Field(10, ge=1, le=lp.MAX_LAG, description="Лет вперёд")
    name: Optional[str] = Field(None, max_length=60, pattern=r"\S")


def _shown(plan: dict[str, Any]) -> dict[str, Any]:
    return {**plan, "consumers_count": len(plan["consumers"]), "consumers": plan["consumers"][:CONSUMERS_SHOWN]}


@router.get("/api/v1/perspective/scenario-plan")
async def perspective_scenario_plan(_: Viewer, fileid: int = Query(..., ge=1),
                                    horizon: int = Query(10, ge=1, le=lp.MAX_LAG)) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return _shown(await ps.plan(conn, fileid=fileid, horizon=horizon))
    except lp.PerspectiveError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.post("/api/v1/perspective/scenario")
async def perspective_scenario_create(body: PerspectiveScenarioIn, user: Creator) -> dict[str, Any]:
    """Сценарий «перспектива на N лет»: копия фрагмента, нагрузка потребителей увеличена на прирост по ТУ."""
    require_topology_mutations_enabled()

    async def run(conn, op):
        p = await ps.plan(conn, fileid=body.fileid, horizon=body.horizon)
        if not p["consumers"]:
            raise lp.PerspectiveError(422, "Во фрагменте нет потребителей рядом с ожидающими ТУ — прирост не к чему добавить")
        name = (body.name or "").strip() or f"Перспектива {p['years'][1]} (+{p['fragment_growth']:g} Гкал/ч)"
        note = (f"Прирост нагрузки на {body.horizon} лет по реестру ТУ: {p['fragment_growth']:g} Гкал/ч у "
                f"{len(p['consumers'])} потребителей (тренд города {p['city_growth']:g} Гкал/ч, радиус {p['radius_m']:g} м)")
        rep = await create_scenario(conn, op, body.fileid, name[:60], note)
        changed = await ps.apply_to_scenario(conn, rep["scenario_id"], p["consumers"])
        await op.audit("INSERT", "fragments", rep["fileid"],
                       {"operation": "perspective_scenario", "scenario_id": rep["scenario_id"],
                        "base_fileid": body.fileid, "horizon": body.horizon, "consumers_changed": changed,
                        "growth_gcal_h": p["fragment_growth"]})
        return {**rep, "consumers_changed": changed, "plan": _shown(p)}

    try:
        result = await _run(False, run, operation="SCENARIO_CREATE", actor=user.username)
    except lp.PerspectiveError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc
    except Exception as e:  # noqa: BLE001 — те же ответы, что у создания сценария
        raise _error(e, "creating perspective scenario")
    invalidate_topology_cache()
    invalidate_outage_cache()
    return result
