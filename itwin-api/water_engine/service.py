"""HTTP-служба расчётного движка водопровода (water_engine/engine.py) — отдельный процесс со своей средой.

    pip install -r water_engine/requirements-water.txt
    WATER_ENGINE_TOKEN=<секрет> uvicorn water_engine.service:app --host 127.0.0.1 --port 8070

ТГИД (API) ходит сюда по WATER_ENGINE_URL с тем же WATER_ENGINE_TOKEN (заголовок Authorization: Bearer). Служба
не хранит ничего: модель приходит в запросе (текст .inp или имя учебной сети), ответ — сеть или результаты расчёта.
Слушать — только 127.0.0.1 или внутреннюю сеть.

GET  /health     — версия WNTR
GET  /library    — учебные сети EPANET, идущие с WNTR
POST /parse      — сеть модели {inp | library} (+ inp — текст модели, если пришло имя учебной сети)
POST /simulate   — гидравлический расчёт {inp | library, duration_h?, report_step_h?}
"""
from __future__ import annotations

import hmac
import os
from typing import Any, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from water_engine import engine

app = FastAPI(title="ТГИД: расчётный движок водопровода", version="1")


def _auth(authorization: Optional[str] = Header(None)) -> None:
    token = os.getenv("WATER_ENGINE_TOKEN", "")
    if not token:
        return  # стенд: служба на 127.0.0.1 без секрета
    got = (authorization or "").removeprefix("Bearer ").strip()
    if not hmac.compare_digest(got, token):
        raise HTTPException(status_code=401, detail="Нужен WATER_ENGINE_TOKEN")


class ModelIn(BaseModel):
    inp: Optional[str] = Field(None, description="Текст модели EPANET (.inp)")
    library: Optional[str] = Field(None, max_length=40, description="Учебная сеть WNTR: Net1, Net3, Net6, ky4…")


class SimulateIn(ModelIn):
    duration_h: Optional[float] = Field(None, ge=0, le=engine.MAX_DURATION_H)
    report_step_h: Optional[float] = Field(None, gt=0, le=24)


def _http(exc: engine.EngineError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.message)


@app.get("/health")
def health() -> dict[str, Any]:
    import wntr

    return {"status": "ok", "wntr": wntr.__version__}


@app.get("/library", dependencies=[Depends(_auth)])
def library() -> list[dict[str, Any]]:
    return engine.library()


@app.post("/parse", dependencies=[Depends(_auth)])
async def parse(body: ModelIn) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        wn = engine.load(body.inp, body.library)
        out = engine.describe(wn)
        if body.library:
            out["inp"] = engine.inp_text(wn)
        return out

    try:
        return await run_in_threadpool(run)
    except engine.EngineError as exc:
        raise _http(exc) from exc


@app.post("/simulate", dependencies=[Depends(_auth)])
async def simulate(body: SimulateIn) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        wn = engine.load(body.inp, body.library)
        return engine.simulate(wn, duration_h=body.duration_h, report_step_h=body.report_step_h)

    try:
        return await run_in_threadpool(run)
    except engine.EngineError as exc:
        raise _http(exc) from exc
