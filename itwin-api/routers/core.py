"""Базовые маршруты: фрагменты, русские названия, карточки линий/узлов, справочники."""

import json

from fastapi import APIRouter, HTTPException

from app_logging import get_logger
from database.db import (
    create_select_line,
    create_select_node,
    get_all_fragments,
    get_lookup_data,
)
from utils.russian_names import russian_names_manager

logger = get_logger(__name__)

router = APIRouter(tags=["core"])


async def _add_russian_names_to_response(data: dict, table: str) -> dict:
    """Добавляет русские названия к полям в ответе API."""
    try:
        if "tabs" not in data:
            return data

        for tab in data["tabs"]:
            if "subsections" not in tab:
                continue

            for subsection in tab["subsections"]:
                if "fields" not in subsection:
                    continue

                for field in subsection["fields"]:
                    if "field" in field:
                        # Получаем русское название для поля
                        field_name = field["field"]
                        russian_name, description = russian_names_manager.get_russian_name(f"{table}|{field_name}")

                        # Добавляем русское название и описание к полю
                        field["russian_name"] = russian_name
                        if description:
                            field["description"] = description

                        # Если русское название отличается от английского, обновляем label
                        if russian_name != field_name and russian_name != field_name.lower():
                            field["label"] = russian_name

        return data
    except Exception as e:
        logger.error(f"Ошибка при добавлении русских названий: {str(e)}")
        return data


@router.get("/fragments")
async def get_fragments():
    """Получить список фрагментов."""
    try:
        data = await get_all_fragments()
        return {"data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении фрагментов: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении фрагментов")


@router.get("/russian-names")
async def get_russian_names():
    """Получить все русские названия колонок."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        data = russian_names_manager.get_all_mappings()
        return {"data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении русских названий: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Ошибка при получении русских названий")


@router.get("/russian-names/{table}")
async def get_table_russian_names(table: str):
    """Получить русские названия колонок для указанной таблицы."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        data = russian_names_manager.get_table_mappings(table)
        return {"table": table, "data": data}
    except Exception as e:
        logger.error(f"Ошибка при получении русских названий для таблицы {table}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении русских названий для таблицы {table}")


@router.get("/russian-names/column/{column}")
async def get_column_russian_name(column: str):
    """Получить русское название для указанной колонки."""
    try:
        if not russian_names_manager.initialized:
            raise HTTPException(status_code=503, detail="Русские названия не инициализированы")

        russian_name, description = russian_names_manager.get_russian_name(column)
        return {
            "column": column,
            "russian_name": russian_name,
            "description": description
        }
    except Exception as e:
        logger.error(f"Ошибка при получении русского названия для колонки {column}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении русского названия для колонки {column}")


@router.get("/line/{table}/{id}")
async def get_line(table: str, id: int, include_russian_names: bool = False):
    """Получить данные для линейного объекта."""
    try:
        logger.debug(f"Fetching line data for table={table}, id={id}")
        result = await create_select_line(table, id)
        logger.debug(f"Line data fetched: {result[:100]}...")

        data = json.loads(result)

        # Добавляем русские названия если запрошено
        if include_russian_names and russian_names_manager.initialized:
            data = await _add_russian_names_to_response(data, table)

        return {"data": data}
    except Exception as e:
        logger.error(f"Error fetching line data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching line data: {str(e)}")


@router.get("/node/{table}/{id}")
async def get_node(table: str, id: int, include_russian_names: bool = False):
    """Получить данные для точечного объекта."""
    try:
        logger.debug(f"Fetching node data for table={table}, id={id}")
        result = await create_select_node(table, id)
        logger.debug(f"Node data fetched: {result[:100]}...")

        data = json.loads(result)

        # Добавляем русские названия если запрошено
        if include_russian_names and russian_names_manager.initialized:
            data = await _add_russian_names_to_response(data, table)

        return {"data": data}
    except Exception as e:
        logger.error(f"Error fetching node data: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching node data: {str(e)}")


@router.get("/lookup")
@router.get("/api/v1/lookup")
async def get_lookup(table: str, id_col: str, name_col: str, sort_col: str = 'none'):
    """Получает справочные данные (Select Options)."""
    try:
        data = await get_lookup_data(table, id_col, name_col, sort_col)
        return {"data": data}
    except Exception as e:
        logger.error(f"Error getting lookup for {table}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении справочника: {str(e)}")
