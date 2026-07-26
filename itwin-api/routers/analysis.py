"""RO network analysis queries (desktop Zap1/2/3/7)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from database.connect import acquire_conn
from database.network_queries import (
    query_heat_consumption,
    query_length_by_diameter,
    query_network_length,
    query_network_volume,
)

router = APIRouter(tags=["analysis"])


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
