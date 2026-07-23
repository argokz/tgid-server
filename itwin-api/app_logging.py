"""Единая настройка логирования приложения.

Ранее конфигурация жила в main.py и была привязана к логгеру "main".
Теперь общий корневой логгер приложения — "itwin_api"; модули-роутеры
получают дочерние логгеры через get_logger(__name__), сообщения которых
поднимаются к общим handler'ам (файл + консоль).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOGGER_NAME = "itwin_api"

_configured = False


def configure_logging() -> logging.Logger:
    """Настраивает файловый и консольный handler'ы. Идемпотентно."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    if _configured:
        return logger

    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    _configured = True
    return logger


def get_logger(module_name: str) -> logging.Logger:
    """Дочерний логгер модуля, пишущий в общие handler'ы приложения."""
    return logging.getLogger(f"{LOGGER_NAME}.{module_name}")
