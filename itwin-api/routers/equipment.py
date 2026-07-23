"""Оборудование сети (read-only): насосы, арматура, регуляторы, байпасы, диафрагмы, элеваторы."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from database.connect import acquire_conn
from database.elevators import get_elevator, get_elevator_lookups, get_elevators
from database.network_armatures import (
    get_network_armature,
    get_network_armature_lookups,
    get_network_armatures,
    get_standard_damper,
    get_standard_dampers,
)
from database.network_bypasses import (
    get_network_bypass,
    get_network_bypass_lookups,
    get_network_bypasses,
    get_standard_tube,
    get_standard_tubes,
)
from database.network_diaphragms import (
    get_network_diaphragm,
    get_network_diaphragm_lookups,
    get_network_diaphragms,
)
from database.network_regulators import (
    get_network_regulator,
    get_network_regulator_lookups,
    get_network_regulators,
    get_regulator_catalog,
    get_regulator_catalog_item,
)
from database.pump_equipment import (
    get_installed_pump,
    get_installed_pumps,
    get_pump_catalog,
    get_pump_equipment_lookups,
    get_standard_pump,
)

router = APIRouter(tags=["equipment"])


@router.get("/api/pump-equipment/lookups")
async def pump_equipment_lookups():
    async with acquire_conn() as conn:
        return await get_pump_equipment_lookups(conn)


@router.get("/api/pump-equipment/pumps")
async def installed_pump_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    configuration_status: Optional[str] = Query(
        None, pattern="^(configured|missing_model|coefficients_missing|line_missing)$"
    ),
    fragment_id: Optional[int] = Query(None, ge=1),
    state_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_installed_pumps(
            conn, page=page, page_size=page_size,
            configuration_status=configuration_status, fragment_id=fragment_id,
            state_id=state_id, line_id=line_id, search=search,
        )


@router.get("/api/pump-equipment/pumps/{pump_id}")
async def installed_pump_card(pump_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_installed_pump(conn, pump_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pump not found")
    return result


@router.get("/api/pump-equipment/catalog")
async def standard_pump_catalog(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    quality_status: Optional[str] = Query(
        None, pattern="^(ready|non_monotonic|incomplete)$"
    ),
    pump_type: Optional[str] = Query(None, max_length=200),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_pump_catalog(
            conn, page=page, page_size=page_size,
            quality_status=quality_status, pump_type=pump_type, search=search,
        )


@router.get("/api/pump-equipment/catalog/{standard_pump_id}")
async def standard_pump_card(standard_pump_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_standard_pump(conn, standard_pump_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Standard pump not found")
    return result


@router.get("/api/network-armatures/lookups")
async def network_armature_lookups():
    async with acquire_conn() as conn:
        return await get_network_armature_lookups(conn)


@router.get("/api/network-armatures/items")
async def network_armature_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    equipment_type: Optional[str] = Query(None, pattern="^(damper|regulating)$"),
    quality_status: Optional[str] = Query(
        None,
        pattern="^(ready|line_missing|line_removed|purpose_unknown|diameter_suspicious)$",
    ),
    state_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    purpose: Optional[str] = Query(None, max_length=200),
    line_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_network_armatures(
            conn,
            page=page,
            page_size=page_size,
            equipment_type=equipment_type,
            quality_status=quality_status,
            state_id=state_id,
            fragment_id=fragment_id,
            purpose=purpose,
            line_id=line_id,
            search=search,
        )


@router.get("/api/network-armatures/items/{equipment_type}/{armature_id}")
async def network_armature_card(
    equipment_type: str = Path(..., pattern="^(damper|regulating)$"),
    armature_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        result = await get_network_armature(conn, equipment_type, armature_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Network armature not found")
    return result


@router.get("/api/network-armatures/catalog")
async def standard_damper_catalog(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_standard_dampers(
            conn, page=page, page_size=page_size, search=search
        )


@router.get("/api/network-armatures/catalog/{standard_id}")
async def standard_damper_card(standard_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_standard_damper(conn, standard_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Standard damper not found")
    return result


@router.get("/api/network-regulators/lookups")
async def network_regulator_lookups():
    async with acquire_conn() as conn:
        return await get_network_regulator_lookups(conn)


@router.get("/api/network-regulators/items")
async def network_regulator_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    regulator_type: Optional[str] = Query(
        None, pattern="^(pressure|flow|differential)$"
    ),
    quality_status: Optional[str] = Query(
        None,
        pattern="^(ready|line_missing|line_removed|control_node_missing|setpoint_missing|capacity_missing)$",
    ),
    state_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    work_attribute_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_network_regulators(
            conn,
            page=page,
            page_size=page_size,
            regulator_type=regulator_type,
            quality_status=quality_status,
            state_id=state_id,
            fragment_id=fragment_id,
            work_attribute_id=work_attribute_id,
            line_id=line_id,
            search=search,
        )


@router.get("/api/network-regulators/items/{regulator_type}/{regulator_id}")
async def network_regulator_card(
    regulator_type: str = Path(..., pattern="^(pressure|flow|differential)$"),
    regulator_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        result = await get_network_regulator(conn, regulator_type, regulator_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Network regulator not found")
    return result


@router.get("/api/network-regulators/catalog")
async def network_regulator_catalog(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    catalog_type: Optional[str] = Query(
        None, pattern="^(pressure|flow|differential)$"
    ),
    quality_status: Optional[str] = Query(None, pattern="^(ready|incomplete)$"),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_regulator_catalog(
            conn,
            page=page,
            page_size=page_size,
            catalog_type=catalog_type,
            quality_status=quality_status,
            search=search,
        )


@router.get("/api/network-regulators/catalog/{catalog_type}/{catalog_id}")
async def network_regulator_catalog_card(
    catalog_type: str = Path(..., pattern="^(pressure|flow|differential)$"),
    catalog_id: int = Path(..., ge=1),
):
    async with acquire_conn() as conn:
        result = await get_regulator_catalog_item(conn, catalog_type, catalog_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Standard regulator not found")
    return result


@router.get("/api/network-bypasses/lookups")
async def network_bypass_lookups():
    async with acquire_conn() as conn:
        return await get_network_bypass_lookups(conn)


@router.get("/api/network-bypasses/items")
async def network_bypass_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    quality_status: Optional[str] = Query(
        None,
        pattern="^(ready|line_missing|line_removed|connection_node_missing|setpoint_missing|geometry_parameters_invalid)$",
    ),
    state_id: Optional[int] = Query(None, ge=1),
    pipeline_sign_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_network_bypasses(
            conn,
            page=page,
            page_size=page_size,
            quality_status=quality_status,
            state_id=state_id,
            pipeline_sign_id=pipeline_sign_id,
            fragment_id=fragment_id,
            line_id=line_id,
            search=search,
        )


@router.get("/api/network-bypasses/items/{bypass_id}")
async def network_bypass_card(bypass_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_network_bypass(conn, bypass_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Network bypass not found")
    return result


@router.get("/api/network-bypasses/tubes")
async def standard_tube_catalog(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    standard: Optional[str] = Query(None, max_length=100),
    quality_status: Optional[str] = Query(None, pattern="^(ready|incomplete)$"),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_standard_tubes(
            conn,
            page=page,
            page_size=page_size,
            standard=standard,
            quality_status=quality_status,
            search=search,
        )


@router.get("/api/network-bypasses/tubes/{standard_tube_id}")
async def standard_tube_card(standard_tube_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_standard_tube(conn, standard_tube_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Standard tube not found")
    return result


@router.get("/api/network-diaphragms/lookups")
async def network_diaphragm_lookups():
    async with acquire_conn() as conn:
        return await get_network_diaphragm_lookups(conn)


@router.get("/api/network-diaphragms/items")
async def network_diaphragm_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    quality_status: Optional[str] = Query(
        None,
        pattern="^(ready|line_missing|line_removed|topology_missing|state_missing|count_invalid|diameter_unresolved)$",
    ),
    diameter_mode: Optional[str] = Query(
        None, pattern="^(available|pending_calculation|unresolved)$"
    ),
    state_id: Optional[int] = Query(None, ge=1),
    external_sign_line_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    installation_place: Optional[str] = Query(None, max_length=100),
    search: Optional[str] = Query(None, max_length=200),
):
    async with acquire_conn() as conn:
        return await get_network_diaphragms(
            conn,
            page=page,
            page_size=page_size,
            quality_status=quality_status,
            diameter_mode=diameter_mode,
            state_id=state_id,
            external_sign_line_id=external_sign_line_id,
            fragment_id=fragment_id,
            line_id=line_id,
            installation_place=installation_place,
            search=search,
        )


@router.get("/api/network-diaphragms/items/{diaphragm_id}")
async def network_diaphragm_card(diaphragm_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_network_diaphragm(conn, diaphragm_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Network diaphragm not found")
    return result


@router.get("/api/elevators/lookups")
async def elevator_lookups():
    async with acquire_conn() as conn:
        return await get_elevator_lookups(conn)


@router.get("/api/elevators")
async def elevator_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = Query(None, max_length=200),
    quality_status: Optional[str] = Query(
        None,
        pattern="^(ready|line_missing|line_removed|topology_missing|state_missing|nozzle_unresolved|pending_calculation)$",
    ),
    state_id: Optional[int] = Query(None, ge=1),
    fragment_id: Optional[int] = Query(None, ge=1),
    line_id: Optional[int] = Query(None, ge=1),
    node_id: Optional[int] = Query(None, ge=1),
):
    async with acquire_conn() as conn:
        return await get_elevators(
            conn,
            page=page,
            page_size=page_size,
            search=search,
            quality_status=quality_status,
            state_id=state_id,
            fragment_id=fragment_id,
            line_id=line_id,
            node_id=node_id,
        )


@router.get("/api/elevators/{elevator_id}")
async def elevator_card(elevator_id: int = Path(..., ge=1)):
    async with acquire_conn() as conn:
        result = await get_elevator(conn, elevator_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Elevator not found")
    return result
