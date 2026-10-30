"""Маршруты API, разнесённые по предметным модулям.

Пути эндпоинтов сохранены 1:1 с прежним монолитным main.py;
префиксы роутерам не назначаются, поэтому include-порядок между
модулями не влияет на маршрутизацию (наборы путей не пересекаются).
"""

from routers.activity_log import router as activity_log_router
from routers.admin import router as admin_router
from routers.ai import router as ai_router
from routers.analysis import router as analysis_router
from routers.auth_routes import router as auth_router
from routers.calc import router as calc_router
from routers.core import router as core_router
from routers.crud import router as crud_router
from routers.data_quality import router as data_quality_router
from routers.equipment import router as equipment_router
from routers.alseko_binding import router as alseko_binding_router
from routers.electrical_binding import router as electrical_binding_router
from routers.card_edit import router as card_edit_router
from routers.equipment_edit import router as equipment_edit_router
from routers.exports_p4 import router as exports_p4_router
from routers.group_setters import router as group_setters_router
from routers.heat import router as heat_router
from routers.journals import router as journals_router
from routers.network_import import router as network_import_router
from routers.fragment_transfer import router as fragment_transfer_router
from routers.file_jobs import router as file_jobs_router
from routers.operations import router as operations_router
from routers.piezometer import router as piezometer_router
from routers.pts import router as pts_router
from routers.registries import router as registries_router
from routers.reports import router as reports_router
from routers.scenarios import router as scenarios_router
from routers.ogc import router as ogc_router
from routers.ogc_write import router as ogc_write_router
from routers.trace_configs import router as trace_configs_router
from routers.thematic import router as thematic_router
from routers.mcp import router as mcp_router
from routers.network_select import router as network_select_router
from routers.static_tiles import router as static_tiles_router
from routers.ogc_processes import router as ogc_processes_router
from routers.work_orders import router as work_orders_router
from routers.field_track import router as field_track_router
from routers.map_comments import router as map_comments_router
from routers.kpi import router as kpi_router
from routers.arcgis import router as arcgis_router
from routers.embed import router as embed_router
from routers.poi import router as poi_router
from routers.outages import router as outages_router
from routers.webhooks import router as webhooks_router
from routers.live import router as live_router
from routers.api_v2 import key_router as api_key_router, router as api_v2_router
from routers.topology import router as topology_router
from routers.wear import router as wear_router

all_routers = [
    core_router,
    calc_router,
    crud_router,
    auth_router,
    piezometer_router,
    heat_router,
    equipment_router,
    equipment_edit_router,
    card_edit_router,
    registries_router,
    alseko_binding_router,
    electrical_binding_router,
    operations_router,
    journals_router,
    group_setters_router,
    pts_router,
    topology_router,
    network_import_router,
    fragment_transfer_router,
    scenarios_router,
    ogc_router,
    ogc_write_router,
    trace_configs_router,
    thematic_router,
    mcp_router,
    network_select_router,
    static_tiles_router,
    ogc_processes_router,
    work_orders_router,
    field_track_router,
    map_comments_router,
    kpi_router,
    arcgis_router,
    embed_router,
    poi_router,
    outages_router,
    webhooks_router,
    live_router,
    api_key_router,
    api_v2_router,
    file_jobs_router,
    reports_router,
    exports_p4_router,
    analysis_router,
    admin_router,
    activity_log_router,
    ai_router,
    wear_router,
    data_quality_router,
]
