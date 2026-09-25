"""RO network analysis queries (desktop Zap1/2/3/7)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app_logging import get_logger
from database.connect import acquire_conn
from database.network_queries import (
    query_heat_consumption,
    query_length_by_diameter,
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
):
    frags = _parse_fragments(fragment_id, fragments)
    async with acquire_conn() as conn:
        return await query_heat_consumption(conn, fragment_ids=frags)


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
