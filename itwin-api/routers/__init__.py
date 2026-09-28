"""Маршруты API, разнесённые по предметным модулям.

Пути эндпоинтов сохранены 1:1 с прежним монолитным main.py;
префиксы роутерам не назначаются, поэтому include-порядок между
модулями не влияет на маршрутизацию (наборы путей не пересекаются).
"""

from routers.admin import router as admin_router
from routers.analysis import router as analysis_router
from routers.auth_routes import router as auth_router
from routers.calc import router as calc_router
from routers.core import router as core_router
from routers.crud import router as crud_router
from routers.equipment import router as equipment_router
from routers.alseko_binding import router as alseko_binding_router
from routers.electrical_binding import router as electrical_binding_router
from routers.equipment_edit import router as equipment_edit_router
from routers.exports_p4 import router as exports_p4_router
from routers.group_setters import router as group_setters_router
from routers.heat import router as heat_router
from routers.journals import router as journals_router
from routers.network_import import router as network_import_router
from routers.fragment_transfer import router as fragment_transfer_router
from routers.operations import router as operations_router
from routers.piezometer import router as piezometer_router
from routers.pts import router as pts_router
from routers.registries import router as registries_router
from routers.reports import router as reports_router
from routers.topology import router as topology_router

all_routers = [
    core_router,
    calc_router,
    crud_router,
    auth_router,
    piezometer_router,
    heat_router,
    equipment_router,
    equipment_edit_router,
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
    reports_router,
    exports_p4_router,
    analysis_router,
    admin_router,
]
