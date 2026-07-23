import re
import os
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

class RussianNamesManager:
    """Менеджер для работы с русскими названиями колонок базы данных."""
    
    def __init__(self):
        self.map_col: Dict[Tuple[str, str], Tuple[str, str]] = {}
        self.initialized = False
    
    def init_column_rus_name(self, database: str) -> None:
        """Инициализирует русские названия для указанной базы данных."""
        try:
            # Определяем путь к файлам с русскими названиями
            rus_names_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rus_names")
            
            # Загружаем файлы с русскими названиями
            for i in range(1, 5):  # txt1, txt2, txt3, txt4
                filename = f"{database}.txt{i}"
                filepath = os.path.join(rus_names_dir, filename)
                
                if os.path.exists(filepath):
                    self._init_column_rus_name_file(database, filepath)
                else:
                    logger.warning(f"Файл {filepath} не найден")
            
            self.initialized = True
            logger.info(f"Инициализированы русские названия для базы данных: {database}")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации русских названий: {str(e)}")
            raise
    
    def _init_column_rus_name_file(self, database: str, filepath: str) -> None:
        """Инициализирует русские названия из файла."""
        logger.debug(f"Загрузка русских названий из файла: {filepath}")
        
        try:
            with open(filepath, 'r', encoding='cp1251', errors='replace') as file:
                for line_num, line in enumerate(file, 1):
                    line = line.rstrip()
                    if line == '' or line[0] == '-':
                        continue
                    
                    # Парсим строку формата: "table","column","russian_name","full_description"
                    m = re.match(r'"(.+?)"\s*,\s*"(.+?)"\s*,\s*"(.*?)"\s*(,\s*"(.+?)")?', line)
                    if m:
                        name_e = m.group(1)
                        name_col_e = m.group(2)
                        name_col_r = m.group(3)
                        name_full = m.group(5) if m.group(5) else ""
                        
                        # Нормализуем ключи (в нижнем регистре)
                        table = name_e.lower()
                        column = name_col_e.lower()
                        
                        # Сохраняем русское название и полное описание
                        self.map_col[(table, column)] = (name_col_r, name_full)
                    else:
                        if line != '' and line[0] != '-':
                            logger.warning(f"Ошибка парсинга строки {line_num} в файле {filepath}: {line}")
        
        except Exception as e:
            logger.error(f"Ошибка при чтении файла {filepath}: {str(e)}")
            raise
    
    def get_russian_name(self, column: str) -> Tuple[str, str]:
        """
        Получает русское название для колонки.
        
        Args:
            column: Название колонки в формате "table|column" или просто "column"
            
        Returns:
            Tuple[str, str]: (русское_название, полное_описание)
        """
        if not self.initialized:
            logger.warning("RussianNamesManager не инициализирован")
            return (column, "")
        
        # Разделяем строку по символу |
        words = re.split(r'\|', column)
        
        if len(words) == 1:
            # Только название колонки, ищем в таблице "?"
            column_lower = words[0].lower()
            result = self.map_col.get(('?', column_lower))
            if result:
                return result
            
            # Если не найдено, попробуем найти в любой таблице
            return self._find_column_in_any_table(column_lower)
        
        if len(words) == 2:
            # Таблица и колонка
            table_lower = words[0].lower()
            column_lower = words[1].lower()
            result = self.map_col.get((table_lower, column_lower))
            if result:
                return result
            
            # Если не найдено, попробуем найти в любой таблице
            return self._find_column_in_any_table(column_lower)
        
        # Если формат не распознан, возвращаем исходную строку
        return (column, column)
    
    def _find_column_in_any_table(self, column_name: str) -> Tuple[str, str]:
        """
        Ищет колонку в любой таблице (без учета регистра).
        
        Args:
            column_name: Название колонки в нижнем регистре
            
        Returns:
            Tuple[str, str]: (русское_название, полное_описание)
        """
        # Сначала ищем точное совпадение
        for (table, column), (russian_name, description) in self.map_col.items():
            if column == column_name:
                return (russian_name, description)
        
        # Если точного совпадения нет, ищем частичное совпадение
        for (table, column), (russian_name, description) in self.map_col.items():
            if column_name in column or column in column_name:
                return (russian_name, description)
        
        # Если ничего не найдено, возвращаем исходное название
        return (column_name, "")
    
    def get_all_mappings(self) -> Dict[str, Dict[str, Tuple[str, str]]]:
        """
        Возвращает все маппинги русских названий, сгруппированные по таблицам.
        
        Returns:
            Dict[str, Dict[str, Tuple[str, str]]]: Словарь таблиц -> колонки -> (русское_название, описание)
        """
        result = {}
        
        for (table, column), (russian_name, description) in self.map_col.items():
            if table not in result:
                result[table] = {}
            result[table][column] = (russian_name, description)
        
        return result
    
    def get_table_mappings(self, table: str) -> Dict[str, Tuple[str, str]]:
        """
        Возвращает маппинги русских названий для указанной таблицы.
        
        Args:
            table: Название таблицы (поиск без учета регистра)
            
        Returns:
            Dict[str, Tuple[str, str]]: Словарь колонки -> (русское_название, описание)
        """
        result = {}
        table_lower = table.lower()
        
        # Сначала ищем точное совпадение
        for (t, column), (russian_name, description) in self.map_col.items():
            if t == table_lower:
                result[column] = (russian_name, description)
        
        # Если точного совпадения нет, ищем частичное совпадение
        if not result:
            for (t, column), (russian_name, description) in self.map_col.items():
                if table_lower in t or t in table_lower:
                    result[column] = (russian_name, description)
        
        return result
    

# Глобальный экземпляр менеджера
russian_names_manager = RussianNamesManager()
