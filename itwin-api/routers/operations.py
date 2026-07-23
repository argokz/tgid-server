"""Эксплуатационные журналы (read-only): нарушения, шурфы, осмотры, ремонты, опрессовки."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database.connect import acquire_conn
from database.defects import get_defect, get_defect_lookups, get_defects, get_defects_geojson
from database.inspections import get_inspection, get_inspection_lookups, get_inspections
from database.pressure_tests import (
    get_pressure_test,
    get_pressure_test_lookups,
    get_pressure_tests,
)
from database.repairs import get_repair, get_repair_lookups, get_repairs
from database.shurfs import get_shurf, get_shurf_lookups, get_shurfs

router = APIRouter(tags=["operations"])


@router.get("/api/pressure-tests/lookups")
async def pressure_test_journal_lookups():
    async with acquire_conn() as conn:
        return await get_pressure_test_lookups(conn)


@router.get("/api/pressure-tests")
async def pressure_test_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    state_id: Optional[int] = Query(None, ge=1),
    test_type_id: Optional[int] = Query(None, ge=1),
    heat_source_id: Optional[int] = Query(None, ge=1),
    responsible_id: Optional[int] = Query(None, ge=1),
    approved: Optional[bool] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1), node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_pressure_tests(
            conn, page=page, page_size=page_size, state_id=state_id,
            test_type_id=test_type_id, heat_source_id=heat_source_id,
            responsible_id=responsible_id, approved=approved,
            date_from=date_from, date_to=date_to, line_id=line_id,
            node_id=node_id, search=search,
        )


@router.get("/api/pressure-tests/{test_id}")
async def pressure_test_card(test_id: int):
    async with acquire_conn() as conn:
        result = await get_pressure_test(conn, test_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Pressure test not found")
    return result


@router.get("/api/repairs/lookups")
async def repair_journal_lookups():
    async with acquire_conn() as conn:
        return await get_repair_lookups(conn)


@router.get("/api/repairs")
async def repair_journal(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    state_id: Optional[int] = Query(None, ge=1),
    repair_type_id: Optional[int] = Query(None, ge=1),
    category_id: Optional[int] = Query(None, ge=1),
    responsible_id: Optional[int] = Query(None, ge=1),
    approved: Optional[bool] = None,
    date_from: Optional[date] = None, date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1), node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_repairs(
            conn, page=page, page_size=page_size, state_id=state_id,
            repair_type_id=repair_type_id, category_id=category_id,
            responsible_id=responsible_id, approved=approved,
            date_from=date_from, date_to=date_to, line_id=line_id,
            node_id=node_id, search=search,
        )


@router.get("/api/repairs/{repair_id}")
async def repair_card(repair_id: int):
    async with acquire_conn() as conn:
        result = await get_repair(conn, repair_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Repair not found")
    return result


@router.get("/api/inspections/lookups")
async def inspection_journal_lookups():
    async with acquire_conn() as conn:
        return await get_inspection_lookups(conn)


@router.get("/api/inspections")
async def inspection_journal(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    responsible_id: Optional[int] = Query(None, ge=1),
    has_defects: Optional[bool] = None,
    has_inspected_sections: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1),
    node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_inspections(
            conn,
            page=page,
            page_size=page_size,
            responsible_id=responsible_id,
            has_defects=has_defects,
            has_inspected_sections=has_inspected_sections,
            date_from=date_from,
            date_to=date_to,
            line_id=line_id,
            node_id=node_id,
            search=search,
        )


@router.get("/api/inspections/{inspection_id}")
async def inspection_card(inspection_id: int):
    async with acquire_conn() as conn:
        result = await get_inspection(conn, inspection_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return result


@router.get("/api/shurfs/lookups")
async def shurf_journal_lookups():
    async with acquire_conn() as conn:
        return await get_shurf_lookups(conn)


@router.get("/api/shurfs")
async def shurf_journal(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    purpose_id: Optional[int] = Query(None, ge=1),
    state_id: Optional[int] = Query(None, ge=1),
    approved: Optional[bool] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1),
    node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")
    async with acquire_conn() as conn:
        return await get_shurfs(
            conn,
            page=page,
            page_size=page_size,
            purpose_id=purpose_id,
            state_id=state_id,
            approved=approved,
            date_from=date_from,
            date_to=date_to,
            line_id=line_id,
            node_id=node_id,
            search=search,
        )


@router.get("/api/shurfs/{shurf_id}")
async def shurf_card(shurf_id: int):
    async with acquire_conn() as conn:
        result = await get_shurf(conn, shurf_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Shurf not found")
    return result


@router.get("/api/defects/lookups")
async def defect_journal_lookups():
    async with acquire_conn() as conn:
        return await get_defect_lookups(conn)


@router.get("/api/defects")
async def defect_journal(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    source_id: Optional[int] = Query(None, ge=1),
    state_id: Optional[int] = Query(None, ge=1),
    category_id: Optional[int] = Query(None, ge=1),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    line_id: Optional[int] = Query(None, ge=1),
    node_id: Optional[int] = Query(None, ge=1),
    search: Optional[str] = Query(None, max_length=200),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")

    async with acquire_conn() as conn:
        return await get_defects(
            conn,
            page=page,
            page_size=page_size,
            source_id=source_id,
            state_id=state_id,
            category_id=category_id,
            date_from=date_from,
            date_to=date_to,
            line_id=line_id,
            node_id=node_id,
            search=search,
        )


@router.get("/api/defects/geojson")
async def defects_geojson():
    async with acquire_conn() as conn:
        return await get_defects_geojson(conn)


@router.get("/api/defects/{defect_id}")
async def defect_card(defect_id: int):
    async with acquire_conn() as conn:
        result = await get_defect(conn, defect_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Defect not found")
    return result
