"""Глава «Электронная модель системы теплоснабжения» (database/em_chapter.py): черновик по данным города.

POST /api/v1/reports/em-chapter       — данные главы по подпунктам а–к п. 55 Требований (просмотр в окне)
POST /api/v1/reports/em-chapter.docx  — та же глава в Word (право «Выгрузка»)
"""
from __future__ import annotations

from typing import Annotated, Any, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth import AuthUser, require_permission, require_roles
from database import em_chapter as em
from database.connect import acquire_conn

router = APIRouter(tags=["em-chapter"])
Viewer = Annotated[AuthUser, Depends(require_roles("viewer"))]
Export = Annotated[AuthUser, Depends(require_permission("export"))]
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ChapterIn(BaseModel):
    fileids: Optional[list[int]] = Field(None, max_length=1000,
                                         description="Фрагменты модели; нет — все, кроме сценариев и копий")
    city: str = Field("", max_length=100, description="Название города в заголовке")


async def _collect(body: ChapterIn) -> dict[str, Any]:
    try:
        async with acquire_conn() as conn:
            return await em.collect(conn, body.fileids)
    except em.ChapterError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


@router.post("/api/v1/reports/em-chapter")
async def em_chapter(body: ChapterIn, _: Viewer) -> dict[str, Any]:
    return await _collect(body)


@router.post("/api/v1/reports/em-chapter.docx")
async def em_chapter_docx(body: ChapterIn, _: Export) -> Response:
    data = await _collect(body)
    filename = "Глава 3 Электронная модель" + (f" — {body.city}" if body.city else "") + ".docx"
    return Response(em.to_docx(data, body.city), media_type=DOCX_MEDIA_TYPE, headers={
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    })
