"""Реестры: технические условия (RO + CRUD), индикаторы коррозии, АЛСЕКО, электрическая сеть."""

from datetime import date
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel

from audit import write_audit_log
from auth import AuthUser, require_mutations_enabled, require_roles
from database.alseko import (
    get_alseko_building,
    get_alseko_load,
    get_alseko_load_lookups,
    get_alseko_loads,
    get_unassigned_alseko_buildings,
)
from database.connect import acquire_conn
from database.corrosion_indicators import (
    get_corrosion_indicator,
    get_corrosion_indicator_lookups,
    get_corrosion_indicators,
    get_corrosion_indicators_geojson,
)
from database.db import create_object, delete_object, update_object_attributes
from database.electrical_network import (
    get_electrical_lookups,
    get_electrical_object,
    get_electrical_objects,
)
from database.technical_conditions import (
    get_technical_condition,
    get_technical_condition_lookups,
    get_technical_conditions,
)
from database.tu_balance import get_technical_condition_balance
from database.tu_mutations import TU_TABLE, filter_tu_fields

router = APIRouter(tags=["registries"])


@router.get("/api/electrical-network/lookups")
async def electrical_network_lookups():
    async with acquire_conn() as conn:
        return await get_electrical_lookups(conn)


@router.get("/api/electrical-network/objects")
async def electrical_network_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    object_type: Optional[str] = Query(
        None, pattern="^(source|line|receiver|channel|coupling|support|sleeve)$"
    ),
    owner_id: Optional[int] = Query(None, ge=1),
    parent_line_id: Optional[int] = Query(None, ge=1),
    voltage_kv: Optional[float] = Query(None, gt=0),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_electrical_objects(
            conn, page=page, page_size=page_size, object_type=object_type,
            owner_id=owner_id, parent_line_id=parent_line_id,
            voltage_kv=voltage_kv, search=search,
        )


@router.get("/api/electrical-network/objects/{object_type}/{object_id}")
async def electrical_network_card(
    object_type: str = Path(
        ..., pattern="^(source|line|receiver|channel|coupling|support|sleeve)$"
    ),
    object_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        result = await get_electrical_object(conn, object_type, object_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Electrical network object not found")
    return result


@router.get("/api/alseko/lookups")
async def alseko_journal_lookups():
    async with acquire_conn() as conn:
        return await get_alseko_load_lookups(conn)


@router.get("/api/alseko/loads")
async def alseko_load_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    match_status: Optional[str] = Query(None, pattern="^(matched|unmatched)$"),
    customer_group: Optional[str] = Query(None, pattern="^(apartment|other)$"),
    operation_district: Optional[str] = Query(None, max_length=200),
    administrative_district: Optional[str] = Query(None, max_length=200),
    heat_source: Optional[str] = Query(None, max_length=300),
    temperature_graph: Optional[str] = Query(None, max_length=300),
    building_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_alseko_loads(
            conn, page=page, page_size=page_size,
            match_status=match_status, customer_group=customer_group,
            operation_district=operation_district,
            administrative_district=administrative_district,
            heat_source=heat_source, temperature_graph=temperature_graph,
            building_id=building_id, search=search,
        )


@router.get("/api/alseko/loads/{load_id}")
async def alseko_load_card(load_id: int):
    async with acquire_conn() as conn:
        result = await get_alseko_load(conn, load_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ALSEKO load not found")
    return result


@router.get("/api/alseko/buildings/unassigned")
async def alseko_unassigned_buildings(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_unassigned_alseko_buildings(
            conn, page=page, page_size=page_size, search=search
        )


@router.get("/api/alseko/buildings/{building_id}")
async def alseko_building_card(building_id: int):
    async with acquire_conn() as conn:
        result = await get_alseko_building(conn, building_id)
    if result is None:
        raise HTTPException(status_code=404, detail="ALSEKO building not found")
    return result


@router.get("/api/corrosion-indicators/lookups")
async def corrosion_indicator_journal_lookups():
    async with acquire_conn() as conn:
        return await get_corrosion_indicator_lookups(conn)


@router.get("/api/corrosion-indicators")
async def corrosion_indicator_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    phase_id: Optional[int] = Query(None, ge=1),
    rod_state_id: Optional[int] = Query(None, ge=1),
    process_mark_id: Optional[int] = Query(None, ge=1),
    water_aggressiveness_id: Optional[int] = Query(None, ge=1),
    season_year: Optional[int] = Query(None, ge=1900, le=2200),
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1),
    node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_corrosion_indicators(
            conn, page=page, page_size=page_size, phase_id=phase_id,
            rod_state_id=rod_state_id, process_mark_id=process_mark_id,
            water_aggressiveness_id=water_aggressiveness_id,
            season_year=season_year, date_from=date_from, date_to=date_to,
            line_id=line_id, node_id=node_id, search=search,
        )


@router.get("/api/corrosion-indicators/geojson")
async def corrosion_indicators_geojson():
    async with acquire_conn() as conn:
        return await get_corrosion_indicators_geojson(conn)


@router.get("/api/corrosion-indicators/{indicator_id}")
async def corrosion_indicator_card(indicator_id: int):
    async with acquire_conn() as conn:
        result = await get_corrosion_indicator(conn, indicator_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Corrosion indicator not found")
    return result


@router.get("/api/technical-conditions/lookups")
async def technical_condition_journal_lookups():
    async with acquire_conn() as conn:
        return await get_technical_condition_lookups(conn)


@router.get("/api/technical-conditions/balance")
async def technical_condition_balance(year: Optional[int] = Query(None, ge=1990, le=2200)):
    """Свод/баланс ТУ по источникам за год (эталон gid6 tu.sql, упрощённый PG)."""
    async with acquire_conn() as conn:
        return await get_technical_condition_balance(conn, year=year)


@router.get("/api/technical-conditions")
async def technical_condition_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    state_id: Optional[int] = Query(None, ge=1),
    issue_year: Optional[int] = Query(None, ge=1900, le=2200),
    heat_source: Optional[str] = Query(None, max_length=200),
    district: Optional[str] = Query(None, max_length=200),
    linked: Optional[bool] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    building_id: Optional[int] = Query(None, ge=1),
    pipe_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_technical_conditions(
            conn, page=page, page_size=page_size, state_id=state_id,
            issue_year=issue_year, heat_source=heat_source, district=district,
            linked=linked, date_from=date_from, date_to=date_to,
            building_id=building_id, pipe_id=pipe_id, search=search,
        )


@router.get("/api/technical-conditions/{condition_id}")
async def technical_condition_card(condition_id: int):
    async with acquire_conn() as conn:
        result = await get_technical_condition(conn, condition_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Technical condition not found")
    return result


class TuFieldsBody(BaseModel):
    fields: Dict[str, Any]


@router.post("/api/technical-conditions")
@router.post("/api/v1/technical-conditions")
async def create_technical_condition(
    body: TuFieldsBody,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
):
    """Vertical CRUD create for ТУ (gid6 etalon)."""
    require_mutations_enabled()
    fields = filter_tu_fields(body.fields)
    new_id = await create_object(TU_TABLE, fields)
    await write_audit_log(
        changed_by=user.username,
        operation="INSERT",
        table_name=TU_TABLE,
        record_id=new_id,
        new_data=fields,
    )
    return {"success": True, "id": new_id}


@router.put("/api/technical-conditions/{condition_id}")
@router.put("/api/v1/technical-conditions/{condition_id}")
async def update_technical_condition(
    condition_id: int,
    body: TuFieldsBody,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
):
    require_mutations_enabled()
    fields = filter_tu_fields(body.fields)
    ok = await update_object_attributes(TU_TABLE, condition_id, fields)
    await write_audit_log(
        changed_by=user.username,
        operation="UPDATE",
        table_name=TU_TABLE,
        record_id=condition_id,
        new_data=fields,
    )
    return {"success": ok}


@router.delete("/api/technical-conditions/{condition_id}")
@router.delete("/api/v1/technical-conditions/{condition_id}")
async def delete_technical_condition(
    condition_id: int,
    user: Annotated[AuthUser, Depends(require_roles("editor"))],
):
    require_mutations_enabled()
    ok = await delete_object(TU_TABLE, condition_id)
    await write_audit_log(
        changed_by=user.username,
        operation="DELETE",
        table_name=TU_TABLE,
        record_id=condition_id,
    )
    return {"success": ok}
