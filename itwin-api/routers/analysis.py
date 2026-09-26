"""RO network analysis queries (desktop «Запросы» Zap1–7 and «Анализ»: режим, допустимость, зоны)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app_logging import get_logger
from database.connect import acquire_conn
from database import regime_queries
from database.network_queries import (
    query_heat_consumption,
    query_length_by_diameter,
    query_length_by_diameter_and_laying,
    query_network_length,
    query_network_volume,
)
from database.outage_simulation import simulate_outage_isolation

logger = get_logger(__name__)
router = APIRouter(tags=["analysis"])


class ValveIsolationRequest(BaseModel):
    line_id: Optional[int] = None
    node_id: Optional[int] = None


def _parse_fragments(
    fragment_id: Optional[int],
    fragments: Optional[str],
) -> Optional[list[int]]:
    ids: list[int] = []
    if fragments:
        for part in fragments.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
    if fragment_id is not None:
        ids.append(int(fragment_id))
    uniq = sorted(set(ids))
    return uniq or None


@router.get("/api/network-queries/volume")
async def network_query_volume(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
):
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_network_volume(conn, fragment_ids=frags)


@router.get("/api/network-queries/length")
async def network_query_length(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
):
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_network_length(conn, fragment_ids=frags)


@router.get("/api/network-queries/length-by-diameter")
async def network_query_length_by_diameter(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
    limit: int = Query(200, ge=1, le=1000),
):
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_length_by_diameter(conn, fragment_ids=frags, limit=limit)


@router.get("/api/network-queries/heat-consumption")
async def network_query_heat_consumption(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
    system: Optional[str] = Query(None, pattern="^(closed|open)$",
                                  description="Zap4: closed — закрытые системы, Zap5: open — открытые"),
):
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_heat_consumption(conn, fragment_ids=frags, system=system)


@router.get("/api/network-queries/length-by-diameter-laying")
async def network_query_length_by_diameter_laying(
    fragment_id: Optional[int] = Query(None, ge=1),
    fragments: Optional[str] = Query(None, description="Comma-separated fileIDs"),
):
    """Zap7_1: длина по условным диаметрам и способам прокладки."""
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_length_by_diameter_and_laying(conn, fragment_ids=frags)


# --- Анализ режима по результатам расчёта (gid6 «Анализ») ---------------------------------

@router.get("/api/analysis/regime/negative-dp")
async def regime_negative_dp(fragment_id: int = Query(..., ge=1), calculation_id: Optional[int] = Query(None, ge=1)):
    """Отрицательные перепады: напор в обратке выше, чем в подаче."""
    async with acquire_conn() as conn:
        return await regime_queries.negative_dp(conn, fragment_id, calculation_id)


@router.get("/api/analysis/regime/airlock")
async def regime_airlock(fragment_id: int = Query(..., ge=1), calculation_id: Optional[int] = Query(None, ge=1)):
    """Завоздушивание: напор в подаче у потребителя ниже высоты здания (зависимые схемы)."""
    async with acquire_conn() as conn:
        return await regime_queries.airlock(conn, fragment_id, calculation_id)


@router.get("/api/analysis/regime/low-temperature")
async def regime_low_temperature(fragment_id: int = Query(..., ge=1), calculation_id: Optional[int] = Query(None, ge=1)):
    """Низкие температуры: t в подаче у потребителя ниже t2 температурного графика при Tн."""
    async with acquire_conn() as conn:
        return await regime_queries.low_temperature(conn, fragment_id, calculation_id)


@router.get("/api/analysis/regime/closed-sections")
async def regime_closed_sections(
    fragment_id: int = Query(..., ge=1),
    include_uncalculated: bool = Query(False, description="true — «Отключенные участки»: все без результата расчёта"),
    calculation_id: Optional[int] = Query(None, ge=1),
):
    async with acquire_conn() as conn:
        return await regime_queries.closed_sections(conn, fragment_id, include_uncalculated, calculation_id)


@router.get("/api/analysis/regime/hydrostatic-zones")
async def regime_hydrostatic_zones(
    fragment_id: int = Query(..., ge=1),
    zone_height_m: float = Query(60.0, gt=0, le=500),
):
    async with acquire_conn() as conn:
        return await regime_queries.hydrostatic_zones(conn, fragment_id, zone_height_m)


@router.get("/api/analysis/admissibility")
async def admissibility_catalog():
    """Анализ режима (контроль допустимых значений): список запросов."""
    return regime_queries.admissibility_catalog()


@router.get("/api/analysis/admissibility/{query_id}")
async def admissibility_query(query_id: int, fragment_id: int = Query(..., ge=1)):
    if query_id not in regime_queries.ADMISSIBILITY:
        raise HTTPException(status_code=404, detail=f"Нет запроса анализа режима №{query_id}")
    async with acquire_conn() as conn:
        return await regime_queries.admissibility(conn, query_id, fragment_id)


@router.post("/api/analysis/valve-isolation")
async def api_valve_isolation(req: ValveIsolationRequest):
    async with acquire_conn() as conn:
        try:
            return await simulate_outage_isolation(conn, line_id=req.line_id, node_id=req.node_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        except Exception as exc:
            logger.error(f"Error in valve isolation: {exc}")
            raise HTTPException(status_code=500, detail=str(exc))
