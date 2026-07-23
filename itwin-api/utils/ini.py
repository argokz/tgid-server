import re
import os
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv
import aiofiles
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загружаем переменные из .env
load_dotenv()

# Более точное определение корня проекта
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Получаем путь к директории с файлами из переменной окружения
FILES_DIR = os.getenv("FILES_DIR", "./files")

# Определяем, является ли путь абсолютным
if os.path.isabs(FILES_DIR):
    ARG_PATH = FILES_DIR
else:
    # Удаляем начальный слеш, если он есть, чтобы путь всегда обрабатывался как относительный
    FILES_DIR = FILES_DIR.lstrip('/')
    # Если путь относительный, объединяем с ROOT_DIR
    ARG_PATH = os.path.abspath(os.path.join(ROOT_DIR, FILES_DIR))

logger.info(f"ROOT_DIR: {ROOT_DIR}")
logger.info(f"Computed ARG_PATH: {ARG_PATH}")
if not os.path.isdir(ARG_PATH):
    logger.error(f"Directory {ARG_PATH} does not exist")
    raise ValueError(f"Directory {ARG_PATH} does not exist. Check FILES_DIR in .env")

class LookupStorage:
    def __init__(self):
        self.map_lookup: Dict[Tuple[str, str], Tuple[str, str, str, str, str, int]] = {}
        self.map_lookup2: Dict[str, Dict[str, str]] = {}
        self.map_help: Dict[Tuple[str, str], Tuple[str, str, str, Optional[str]]] = {}

    async def read_lookup(self, fn: str) -> None:
        path = await open_arg(fn)
        async with aiofiles.open(path, mode="r", encoding="cp1251") as f:
            count = 0
            async for line in f:
                m = re.match(r'^"(.+?)","(.+?)","(.+?)","(.+?)","(.+?)",([0-9]+)', line)
                if m:
                    tn1, fn1, tn2, id2, fn2, srt = m.groups()
                    self.map_lookup[(tn1.lower(), fn1.lower())] = (tn1, fn1, tn2, id2, fn2, int(srt))
                    count += 1
            logger.info(f"[read_lookup] Loaded {count} lookup entries from {fn}")

    async def read_lookup2(self, fn: str) -> None:
        tn = ""
        try:
            path = await open_arg(fn)
            async with aiofiles.open(path, mode="r", encoding="cp1251") as f:
                count = 0
                async for line in f:
                    line = line.rstrip()
                    if line.startswith(" "):
                        m = re.match(r'^\s+([0-9]+)\s+(.+)$', line)
                        if m:
                            num, txt = m.groups()
                            self.map_lookup2[tn][num] = txt
                            count += 1
                    else:
                        tn = line.lower()
                        self.map_lookup2[tn] = {}
                logger.info(f"[read_lookup2] Loaded {count} entries for {fn}")
        except Exception as e:
            logger.error(f"[read_lookup2] Error reading {fn}: {e}")

    async def read_help(self, fn: str) -> None:
        path = await open_arg(fn)
        async with aiofiles.open(path, mode="r", encoding="cp1251") as f:
            count = 0
            async for line in f:
                m = re.match(r'^"(.+?)","(.+?)","(.+?)","(.+?)"', line)
                rd = 4 if m else 3
                if not m:
                    m = re.match(r'^"(.+?)","(.+?)","(.+?)"', line)
                if m:
                    tn, fn, txt = m.group(1), m.group(2), m.group(3)
                    f1 = m.group(4) if rd == 4 else None
                    self.map_help[(tn.lower(), fn.lower())] = (tn, fn, txt, f1)
                    count += 1
            logger.info(f"[read_help] Loaded {count} help entries from {fn}")

    async def read_tab2(self, fn: str) -> Optional[List[str]]:
        filtr: List[str] = []
        try:
            path = await open_tab(f"{fn}.txt")
            async with aiofiles.open(path, mode="r", encoding="cp1251") as f:
                async for line in f:
                    line = line.rstrip()
                    if line.startswith("-!"):
                        filtr.append("!1 " + line[2:])
                    elif line.startswith("-"):
                        continue
                    elif line[0] != " ":
                        filtr.append("!2 " + line)
                    elif line.strip().startswith("$"):
                        filtr.append(line.strip())
                    else:
                        m = re.match(r'^\s+([^ \r\n]+)', line)
                        if m:
                            filtr.append(m.group(1))
            logger.info(f"[read_tab2] Parsed {len(filtr)} fields from {fn}.txt")
            return filtr
        except FileNotFoundError:
            logger.warning(f"[read_tab2] File not found: {fn}.txt")
            return None

    def get_lookup(self, tn1: str, fn1: str) -> Optional[Tuple[str, str, str, str, str, int]]:
        key = (tn1.lower(), fn1.lower())
        if key not in self.map_lookup:
            logger.debug(f"[get_lookup] Missing: {key}")
        return self.map_lookup.get(key)

    def get_lookup2(self, tn1: str) -> Optional[Dict[str, str]]:
        key = tn1.lower()
        if key not in self.map_lookup2:
            logger.debug(f"[get_lookup2] Missing: {key}")
        return self.map_lookup2.get(key)

    def get_help(self, tn1: str, fn1: str) -> Tuple[str, str, str, Optional[str]]:
        key = (tn1.lower(), fn1.lower())
        if key not in self.map_help:
            logger.debug(f"[get_help] Missing help for: {key}")
        return self.map_help.get(key, (tn1, fn1, fn1, None))

storage = LookupStorage()

async def open_in_dirs(filename: str, dirs: List[str], encoding: str = "cp1251") -> str:
    for directory in dirs:
        path = os.path.join(directory, filename)
        if os.path.isfile(path):
            logger.info(f"Found file: {path}")
            return path
    raise FileNotFoundError(f"Файл '{filename}' не найден в каталогах: {dirs}")

async def open_tab(filename: str, encoding: str = "cp1251") -> str:
    dirs = ["tab/gid8", "tab", "tab/remont", "tab/ps", "tab/pts"]
    full_dirs = [os.path.join(ARG_PATH, d) for d in dirs]
    return await open_in_dirs(filename, full_dirs, encoding)

async def open_arg(filename: str, encoding: str = "cp1251") -> str:
    path = os.path.join(ARG_PATH, filename)
    logger.debug(f"Opening file: {path}")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Файл '{path}' не найден")
    return path

def parse_filtr(line: str) -> Optional[Tuple[str, str, str]]:
    m = re.match(r'\$view_filtr\$(.+)\$(.+)\$\s+(.+)$', line)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return None

async def read_tab(fn: str) -> Optional[List[str]]:
    filtr: List[str] = []
    try:
        path = await open_tab(f"{fn}.txt")
        async with aiofiles.open(path, mode="r", encoding="cp1251") as f:
            async for line in f:
                line = line.strip()
                if not line or line[0] != " ":
                    continue
                if line[0] == "$":
                    filtr.append(line)
                else:
                    m = re.match(r'^\s+([^ \r\n]+)', line)
                    if m:
                        filtr.append(m.group(1))
        return filtr
    except FileNotFoundError:
        logger.warning(f"[read_tab] File not found: {fn}.txt")
        return None