"""Фоновые файлы: «задача → статус → скачать файл».

Тяжёлые выгрузки (паспорт 10–15 с, Excel-отчёты до 13 с, сверки АЛСЕКО / электросети) строятся
в воркере Celery (задача ``build_file_job``); готовый файл кладётся в Redis с TTL, API отдаёт
статус задачи и сам файл. Синхронные эндпоинты остаются для совместимости и используют те же
построители.

Построитель: ``async (params) -> FileResult``; ошибки данных — ``FileJobError`` (HTTP-код +
сообщение). Параметры проверяются pydantic-моделями ``PARAM_MODELS`` до постановки задачи.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import date
from typing import Annotated, Any, Awaitable, Callable, Literal, Optional
from urllib.parse import quote

from pydantic import BaseModel, Field

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
KEY_PREFIX = "tgid:filejob:"


class FileJobError(Exception):
    def __init__(self, status_code: int, detail: Any):
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail

    @property
    def message(self) -> str:
        if isinstance(self.detail, dict):
            return str(self.detail.get("message") or self.detail)
        return str(self.detail)


@dataclass
class FileResult:
    content: bytes
    filename: str
    media_type: str = XLSX
    headers: dict[str, str] = field(default_factory=dict)


# --- параметры -------------------------------------------------------------------------

class PassportParams(BaseModel):
    table: Literal["linesobj", "nodes", "uchastok_ms", "uchastok_rs"]
    obj_id: int = Field(..., ge=1)


class ReportExcelParams(BaseModel):
    doc_type: str = Field(..., min_length=1, max_length=64)
    year: Optional[int] = Field(None, ge=1990, le=2200)
    fragments: Optional[list[Annotated[int, Field(ge=1)]]] = Field(None, max_length=500)


class CatalogReportParams(BaseModel):
    report_id: str = Field(..., min_length=1, max_length=128)
    fragment_id: int = Field(..., ge=1)
    calculation_id: Optional[int] = Field(None, ge=1)


class AlsekoReconciliationParams(BaseModel):
    kinds: Optional[list[str]] = Field(None, max_length=50)


class ElectricalReconciliationParams(BaseModel):
    tolerance: float = Field(8.0, gt=0, le=1000)


# --- построители -----------------------------------------------------------------------

async def _passport(p: PassportParams) -> FileResult:
    from database.passport_excel import PassportError, build_passport_xlsx

    try:
        content, filename = await asyncio.to_thread(build_passport_xlsx, p.table, p.obj_id)
    except PassportError as e:
        raise FileJobError(e.status_code, e.detail) from e
    return FileResult(content, filename)


async def _report_excel(p: ReportExcelParams) -> FileResult:
    from reports_generator import build_excel_report, report_filename

    frags = sorted(set(p.fragments)) if p.fragments else None
    try:
        report = await build_excel_report(p.doc_type, year=p.year, fragment_ids=frags)
    except ValueError as e:
        raise FileJobError(400, str(e)) from e
    return FileResult(
        report.content,
        report_filename(p.doc_type, year=p.year, fragment_ids=frags),
        headers=report.headers(),
    )


async def _catalog_report(p: CatalogReportParams) -> FileResult:
    import asyncpg

    from database import excel_reports
    from database.connect import acquire_conn

    try:
        report = excel_reports.get_report(p.report_id)
    except KeyError as e:
        raise FileJobError(404, f"Нет отчёта {p.report_id}") from e
    try:
        async with acquire_conn() as conn:
            calc, results = await excel_reports.fetch_report(conn, report, p.fragment_id, p.calculation_id)
    except LookupError as e:
        raise FileJobError(404, str(e)) from e
    except asyncpg.QueryCanceledError as e:
        raise FileJobError(504, "Отчёт не уложился в таймаут запроса") from e
    data = await asyncio.to_thread(excel_reports.render_report, report, calc, results)
    summary = excel_reports.report_summary(report, p.fragment_id, calc, results)
    title = f"{report.title} ф{p.fragment_id}.xlsx"
    return FileResult(data, title, headers={
        "X-Report-Rows": ",".join(str(s["rows"]) for s in summary["sheets"]),
        "X-Report-Calculation": str(summary["calculation_id"] or ""),
    })


async def _alseko_reconciliation(p: AlsekoReconciliationParams) -> FileResult:
    from database import alseko_binding as ab
    from database.connect import acquire_conn

    selected = [k.strip() for k in (p.kinds or []) if k and k.strip()] or None
    async with acquire_conn() as conn:
        try:
            content = await ab.reconciliation_workbook(conn, selected)
        except ab.AlsekoError as e:
            raise FileJobError(e.status, e.detail) from e
    return FileResult(content, f"alseko_reconciliation_{date.today().isoformat()}.xlsx")


async def _electrical_reconciliation(p: ElectricalReconciliationParams) -> FileResult:
    from database import electrical_binding as eb
    from database.connect import acquire_conn

    async with acquire_conn() as conn:
        try:
            content = await eb.reconciliation_workbook(conn, p.tolerance)
        except eb.ElectricalError as e:
            raise FileJobError(e.status, e.detail) from e
    return FileResult(content, f"electrical_reconciliation_{date.today().isoformat()}.xlsx")


PARAM_MODELS: dict[str, type[BaseModel]] = {
    "passport": PassportParams,
    "report_excel": ReportExcelParams,
    "catalog_report": CatalogReportParams,
    "alseko_reconciliation": AlsekoReconciliationParams,
    "electrical_reconciliation": ElectricalReconciliationParams,
}

BUILDERS: dict[str, Callable[[Any], Awaitable[FileResult]]] = {
    "passport": _passport,
    "report_excel": _report_excel,
    "catalog_report": _catalog_report,
    "alseko_reconciliation": _alseko_reconciliation,
    "electrical_reconciliation": _electrical_reconciliation,
}

KINDS = tuple(PARAM_MODELS)


def validate_params(kind: str, params: dict[str, Any] | None) -> dict[str, Any]:
    """Проверка параметров до постановки в очередь; ValueError / ValidationError — 422."""
    model = PARAM_MODELS.get(kind)
    if model is None:
        raise ValueError(f"Неизвестный вид файла: {kind}")
    return model.model_validate(params or {}).model_dump()


async def build(kind: str, params: dict[str, Any]) -> FileResult:
    model = PARAM_MODELS[kind]
    return await BUILDERS[kind](model.model_validate(params))


def content_disposition(filename: str) -> str:
    ascii_name = filename.encode("ascii", "replace").decode("ascii").replace("?", "_").replace('"', "")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


# --- хранилище результата (Redis, TTL) --------------------------------------------------

def ttl_seconds() -> int:
    try:
        return max(60, int(os.getenv("FILE_JOBS_TTL") or 3600))
    except ValueError:
        return 3600


def queue_name() -> Optional[str]:
    return os.getenv("FILE_JOBS_QUEUE") or None


def redis_url() -> str:
    addr = os.getenv("REDIS_ADDR", "127.0.0.1:6379")
    password = os.getenv("REDIS_PASSWORD", "").strip()
    db = os.getenv("REDIS_DB", "").strip() or "0"
    return f"redis://:{password}@{addr}/{db}" if password else f"redis://{addr}/{db}"


_client = None


def _redis():
    global _client
    if _client is None:
        import redis

        _client = redis.Redis.from_url(redis_url(), socket_timeout=10)
    return _client


def store_result(task_id: str, result: FileResult, *, owner: str = "", kind: str = "") -> dict[str, Any]:
    meta = {
        "filename": result.filename, "media_type": result.media_type, "size": len(result.content),
        "headers": result.headers, "owner": owner, "kind": kind,
    }
    ttl = ttl_seconds()
    pipe = _redis().pipeline()
    pipe.set(f"{KEY_PREFIX}{task_id}:data", result.content, ex=ttl)
    pipe.set(f"{KEY_PREFIX}{task_id}:meta", json.dumps(meta, ensure_ascii=False), ex=ttl)
    pipe.execute()
    return {**meta, "ttl": ttl}


def load_meta(task_id: str) -> Optional[dict[str, Any]]:
    raw = _redis().get(f"{KEY_PREFIX}{task_id}:meta")
    return json.loads(raw) if raw else None


def load_result(task_id: str) -> Optional[tuple[dict[str, Any], bytes]]:
    meta = load_meta(task_id)
    if meta is None:
        return None
    data = _redis().get(f"{KEY_PREFIX}{task_id}:data")
    if data is None:
        return None
    return meta, data
