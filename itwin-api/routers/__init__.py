"""Маршруты API, разнесённые по предметным модулям.

Пути эндпоинтов сохранены 1:1 с прежним монолитным main.py;
префиксы роутерам не назначаются, поэтому include-порядок между
модулями не влияет на маршрутизацию (наборы путей не пересекаются).
"""

from routers.auth_routes import router as auth_router
from routers.calc import router as calc_router
from routers.core import router as core_router
from routers.crud import router as crud_router
from routers.equipment import router as equipment_router
from routers.heat import router as heat_router
from routers.operations import router as operations_router
from routers.piezometer import router as piezometer_router
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
    registries_router,
    operations_router,
    topology_router,
    reports_router,
]
