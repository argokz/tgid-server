"""Переход с ZuluGIS / ZuluThermo (фаза 5): слой Zulu → фрагмент ТГИД конвертером десктопа (zulu_converter/).

1. upload — файлы слоя или zip: найти слой (*.b00 + *.b01 + *.b02), проверить базу слоя *.sqlite, посчитать объекты
   по типам; файлы слоя — zip в хранилище файлов (file_jobs.put_blob) на TTL с владельцем.
2. convert — фоновая задача file-jobs «zulu_convert»: конвертер отдельным процессом (свой TMP, таймаут), результат —
   .itwin (несколько фрагментов — zip из .itwin) и сводка в заголовке X-Zulu-Report: объекты слоя по типам и
   строки фрагмента (узлы, участки, источники, потребители).
3. Веб подаёт .itwin в импорт фрагмента (database/fragment_transfer.py): превью, применение, отмена.

Конвертер — код десктопа без изменений (кроме удалённых учётных данных): что и как он переносит — его решения
(например, расход обобщённого потребителя Zulu Gpod — в calcHLdep с признаком задания нагрузки расходом).
"""
from __future__ import annotations

import asyncio
import glob
import io
import json
import os
import subprocess
import sys
import tempfile
import uuid
import zipfile
from typing import Any, Optional

from app_logging import get_logger
from database.file_jobs import FileJobError, FileResult, load_blob, put_blob, report_progress

logger = get_logger(__name__)

CONVERTER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zulu_converter")
UPLOAD_PREFIX = "zulu-upload:"
LAYER_EXTS = (".b00", ".b01", ".b02")
REPORT_TIMEOUT_S = 60
LOG_TAIL_LINES = 15
# строки фрагмента в сводке: таблица .itwin → подпись
SUMMARY_TABLES = {
    "nodes": "узлы", "linesobj": "участки", "heatsources": "источники", "realconsumers": "потребители",
    "generalizedconsumers": "обобщённые потребители", "pumpstations": "насосные", "setpressnodes": "узлы заданного напора",
}


class ZuluImportError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def timeout_s() -> int:
    try:
        return max(60, int(os.getenv("ZULU_TIMEOUT_S", "1800")))
    except ValueError:
        return 1800


def find_layers(folder: str) -> list[str]:
    """Слои в каталоге: путь без расширения, у которого есть *.b00, *.b01 и *.b02."""
    bases = {os.path.splitext(p)[0] for p in glob.glob(os.path.join(folder, "*")) if p.lower().endswith(".b00")}
    return sorted(b for b in bases if all(_file(b, ext) for ext in LAYER_EXTS))


def _file(base: str, ext: str) -> Optional[str]:
    """Файл слоя с расширением в любом регистре (Teplo.B05 у примеров ZuluGIS)."""
    folder, name = os.path.split(base)
    for p in glob.glob(os.path.join(folder, glob.escape(name) + ".*")):
        if os.path.splitext(p)[1].lower() == ext:
            return p
    return None


def _python() -> str:
    return sys.executable


def _run(args: list[str], *, workdir: str, timeout: int) -> subprocess.CompletedProcess:
    env = {**os.environ, "TMP": workdir, "TEMP": workdir, "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([_python(), "-I", os.path.join(CONVERTER_DIR, "run_converter.py"), *args],
                          cwd=CONVERTER_DIR, env=env, capture_output=True, timeout=timeout)


def layer_report(base: str, workdir: str) -> dict[str, Any]:
    try:
        proc = _run(["--report", base], workdir=workdir, timeout=REPORT_TIMEOUT_S)
    except subprocess.TimeoutExpired as exc:
        raise ZuluImportError(422, "Слой Zulu не разобрался за минуту — файлы повреждены?") from exc
    if proc.returncode != 0:
        logger.warning("Zulu: сводка слоя не получена: %s", _tail(proc))
        raise ZuluImportError(422, "Файлы слоя Zulu не читаются — нужны *.b00–*.b10, *.d*, *.l*, *.zsx, *.zx слоя")
    return json.loads(proc.stdout.decode("utf-8").strip().splitlines()[-1])


def _tail(proc: subprocess.CompletedProcess) -> str:
    text = (proc.stdout or b"").decode("utf-8", "replace") + (proc.stderr or b"").decode("utf-8", "replace")
    return "\n".join(line for line in text.splitlines() if line.strip())[-4000:]


def _pack_layer(base: str) -> bytes:
    """Файлы одного слоя (и его база) — zip для хранилища."""
    folder, name = os.path.split(base)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(glob.glob(os.path.join(folder, glob.escape(name) + ".*"))):
            z.write(p, os.path.basename(p))
    return buf.getvalue()


def upload(files: list[tuple[str, bytes]], owner: str, layer: Optional[str] = None) -> dict[str, Any]:
    """Проверить загрузку и положить слой в хранилище; вернуть upload_id, слой и сводку."""
    from database.network_import import _extract

    with tempfile.TemporaryDirectory(prefix="zulu-up-") as tmp:
        try:
            _extract(files, tmp)
        except ValueError as exc:
            raise ZuluImportError(422, str(exc)) from exc
        layers = find_layers(tmp)
        if not layers:
            raise ZuluImportError(422, "Нет слоя Zulu: нужны файлы слоя *.b00, *.b01, *.b02 и остальные (папка слоя или zip)")
        names = [os.path.basename(b) for b in layers]
        if layer:
            if layer not in names:
                raise ZuluImportError(422, f"Слоя «{layer}» нет в загрузке: {', '.join(names)}")
            base = layers[names.index(layer)]
        elif len(layers) > 1:
            raise ZuluImportError(422, f"В загрузке несколько слоёв — выберите один: {', '.join(names)}")
        else:
            base = layers[0]
        report = layer_report(base, tmp)
        if not report["has_sqlite"]:
            raise ZuluImportError(422, f"У слоя «{os.path.basename(base)}» нет базы *.sqlite — базы Paradox (*.db) "
                                       "старых версий Zulu не поддерживаются: в ZuluGIS переведите базу слоя в SQLite")
        upload_id = uuid.uuid4().hex
        meta = {"owner": owner, "layer": os.path.basename(base), "report": report}
        ttl = put_blob(UPLOAD_PREFIX + upload_id, _pack_layer(base), meta)
    return {"upload_id": upload_id, "layer": meta["layer"], "layers": names, "report": report, "ttl": ttl}


def upload_meta(upload_id: str) -> Optional[dict[str, Any]]:
    stored = load_blob(UPLOAD_PREFIX + upload_id)
    return stored[0] if stored else None


def fragment_summary(data: bytes) -> dict[str, Any]:
    from database.fragment_transfer import parse_tgid

    tables = parse_tgid(data)
    rows = {key: len((tables.get(key) or {}).get("rows") or []) for key in SUMMARY_TABLES}
    fragments = tables.get("fragments") or {}
    cols = [c.lower() for c in fragments.get("columns") or []]
    first = (fragments.get("rows") or [[]])[0]
    name = first[cols.index("name")] if "name" in cols and len(first) > cols.index("name") else None
    return {"name": name, "rows": {k: v for k, v in rows.items() if v}}


async def convert(upload_id: str, name: str, tn: float) -> FileResult:
    """Построитель фоновой задачи: слой из хранилища → конвертер → .itwin (или zip из нескольких)."""
    stored = load_blob(UPLOAD_PREFIX + upload_id)
    if stored is None:
        raise FileJobError(404, "Загрузка слоя не найдена или срок хранения истёк — загрузите слой заново")
    meta, data = stored
    return await asyncio.to_thread(_convert_sync, meta, data, name, tn)


def _convert_sync(meta: dict[str, Any], data: bytes, name: str, tn: float) -> FileResult:
    with tempfile.TemporaryDirectory(prefix="zulu-cv-") as tmp:
        src, out, work = (os.path.join(tmp, d) for d in ("in", "out", "work"))
        for d in (src, out, work):
            os.makedirs(d)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            z.extractall(src)
        base = os.path.join(src, meta["layer"])
        report_progress(f"Конвертация слоя «{meta['layer']}»")
        args = ["-name", name, "-path", base, "-Tn", f"{tn:g}", "-reset", "-path_out", out]
        try:
            proc = _run(args, workdir=work, timeout=timeout_s())
        except subprocess.TimeoutExpired as exc:
            raise FileJobError(504, f"Конвертация не уложилась в {timeout_s() // 60} мин (ZULU_TIMEOUT_S)") from exc
        files = sorted(glob.glob(os.path.join(out, "*.itwin")))
        if proc.returncode != 0 or not files:
            tail = _tail(proc)
            logger.error("Zulu: конвертация слоя %s не удалась (код %s):\n%s", meta["layer"], proc.returncode, tail)
            last = "\n".join(tail.splitlines()[-LOG_TAIL_LINES:])
            raise FileJobError(422, f"Конвертер не создал фрагмент. Конец журнала конвертера:\n{last}")
        fragments = []
        for path in files:
            with open(path, "rb") as f:
                content = f.read()
            fragments.append((os.path.basename(path), content, fragment_summary(content)))
    summary = {"layer": meta["layer"], "objects": meta["report"]["layer"],
               "db_tables": meta["report"]["db_tables"], "fragments": [s for _, _, s in fragments]}
    headers = {"X-Zulu-Report": json.dumps(summary, ensure_ascii=True)}
    if len(fragments) == 1:
        return FileResult(fragments[0][1], f"{name}.itwin", "application/octet-stream", headers)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for fname, content, _ in fragments:
            z.writestr(fname, content)
    return FileResult(buf.getvalue(), f"{name}.zip", "application/zip", headers)
