"""B7 golden-приёмка редактора топологии на копии БД: операция → инварианты → расчёт → undo.

Для каждой операции редактора (создание узла и участка, перенос узла, разрезание участка
с оборудованием, слияние узлов с зависимостями, удаление участка и узла, разворот пары
подача/обратка, правка геометрии) на выбранном фрагменте:

  1. снимок таблиц сети (nodes, linesobj, heatpipesections, оборудование на участках и все
     таблицы со ссылками nodeid*, кроме *_out) — md5 без учёта порядка строк;
  2. операция через HTTP API (как web-клиент: dry-run там, где он есть, версии объектов);
  3. инварианты целостности:
       - ссылки: ни в одной колонке-ссылке на узел (nodeid*, internalnodeid, remontnodeid,
         linesobj.nodeid1/2) не прибавилось ссылок на несуществующие или снятые узлы;
       - концы геометрии затронутых участков совпадают с их узлами (≤ 1 см);
       - длины паспортов пересчитаны по геометрии (операции, меняющие геометрию);
       - fileid согласован: концы участка в одном фрагменте, fileid участка пуст или равен
         фрагменту узла, у новых/затронутых узлов есть фрагмент и код (externalcodeid);
       - записаны audit_log (change_group_id операции) и журнал отмены (topology_undo_log);
       - проверки конкретной операции (сохранение оборудования при разрезании и т. п.);
  4. расчёт sety по фрагменту (POST /api/v1/calculations/run → Celery), ожидание,
     проверка статуса и того, что затронутые участки/узлы есть в ut_out/us_out (а снятые —
     нет); расчёт удаляется DELETE /api/v1/calculations/{id};
  5. отмена (POST /api/v1/topology/undo) в обратном порядке и сравнение снимка с исходным.

Запуск (API с кодом редактора на копии, флаги топологии включены, AUTH_DISABLED=false,
тот же JWT_SECRET; Celery-воркер на копии):

    ./venv/Scripts/python.exe scripts/golden/topology_acceptance.py \
        --base-url http://127.0.0.1:8041 --fragment 74 --out ../../web-itwin/docs/stage-b-acceptance.md

Подключение к БД: .env, поверх него .env.copy. Скрипт отказывается работать, если в БД нет
таблицы-маркера `_this_is_copy`. Код возврата 0 — все операции прошли, 1 — есть провалы.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

END_TOLERANCE_M = 0.01
LENGTH_TOLERANCE_M = 0.01
CALC_TIMEOUT_S = 900
LENGTH_OPS = {"CREATE_LINE", "MOVE", "SPLIT", "MERGE", "GEOMETRY"}

# Оборудование с реальным lineid (см. database/topology_transfer.SPLIT_TRANSFER_RULES)
LINE_EQUIPMENT = (
    "pressregulators", "consumptregulators", "pressdropregulators", "diaphragms", "dampers",
    "elevators", "systemradiators", "pumps", "heatexchangers", "airheaters",
)


def q(name: str) -> str:
    if not name.replace("_", "").isalnum():
        raise ValueError(name)
    return '"' + name + '"'


# ---------------------------------------------------------------------------
# Результаты
# ---------------------------------------------------------------------------

@dataclass
class Check:
    name: str
    ok: Optional[bool]  # None — не применимо
    detail: str = ""


@dataclass
class Step:
    title: str
    operation: str
    objects: str = ""
    operation_id: Optional[int] = None
    error: Optional[str] = None
    checks: list[Check] = field(default_factory=list)
    calc: dict = field(default_factory=dict)
    touched_nodes: list[int] = field(default_factory=list)
    touched_lines: list[int] = field(default_factory=list)
    # Объекты, которых в результатах расчёта быть не должно по правилам движка (с пояснением):
    # sety пишет в ut_out только участки с ненулевым расходом, в us_out — узлы связной сети.
    not_expected: dict = field(default_factory=dict)

    def add(self, name: str, ok: Optional[bool], detail: str = "") -> None:
        self.checks.append(Check(name, ok, detail))

    @property
    def ok(self) -> bool:
        return (
            self.error is None
            and all(c.ok is not False for c in self.checks)
            and self.calc.get("ok", False)
        )


@dataclass
class Scenario:
    title: str
    steps: list[Step] = field(default_factory=list)
    undo: list[str] = field(default_factory=list)
    undo_ok: Optional[bool] = None
    snapshot_ok: Optional[bool] = None
    snapshot_diff: list[str] = field(default_factory=list)
    refs_after_undo_ok: Optional[bool] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return (
            self.error is None and bool(self.steps) and all(s.ok for s in self.steps)
            and bool(self.undo_ok) and bool(self.snapshot_ok) and self.refs_after_undo_ok is not False
        )


class ApiError(Exception):
    def __init__(self, status: int, body: Any):
        super().__init__(f"HTTP {status}: {json.dumps(body, ensure_ascii=False)[:600]}")
        self.status = status
        self.body = body


# ---------------------------------------------------------------------------
# Контекст: БД + HTTP
# ---------------------------------------------------------------------------

class Ctx:
    def __init__(self, conn, http, fragment: int, username: str, calc_body: dict):
        self.conn = conn
        self.http = http
        self.fragment = fragment
        self.username = username
        self.calc_body = calc_body
        self.ref_columns: list[tuple[str, str, bool]] = []  # (table, column, has_removed)
        self.snapshot_tables: list[str] = []
        self.ref_baseline: dict[str, tuple[int, int]] = {}
        self.baseline_calc: dict = {}
        self.baseline_lines: set[int] = set()  # участки и узлы с результатом в базовом расчёте
        self.baseline_nodes: set[int] = set()
        self.created_calcs: list[int] = []
        self.skip_calc = False  # отладка выбора объектов: без расчётов (отчёт не для приёмки)

    # --- HTTP ---
    async def api(self, method: str, path: str, **kw) -> Any:
        r = await self.http.request(method, path, **kw)
        try:
            body = r.json()
        except ValueError:
            body = r.text
        if r.status_code >= 400:
            raise ApiError(r.status_code, body)
        return body

    # --- схема ---
    async def discover(self) -> None:
        rows = await self.conn.fetch(
            """
            SELECT c.table_name, c.column_name,
                   EXISTS (SELECT 1 FROM information_schema.columns r
                           WHERE r.table_schema = 'public' AND r.table_name = c.table_name
                             AND r.column_name = 'removed') AS has_removed
            FROM information_schema.columns c
            JOIN information_schema.tables t
              ON t.table_schema = c.table_schema AND t.table_name = c.table_name AND t.table_type = 'BASE TABLE'
            WHERE c.table_schema = 'public'
              AND (lower(c.column_name) LIKE 'nodeid%' OR lower(c.column_name) IN ('internalnodeid', 'remontnodeid'))
              AND c.data_type IN ('integer', 'bigint', 'smallint', 'numeric')
            ORDER BY 1, 2
            """
        )
        self.ref_columns = [
            (r["table_name"], r["column_name"], r["has_removed"])
            for r in rows if not r["table_name"].lower().endswith("_out")
        ]
        tables = {"nodes", "linesobj", "heatpipesections"} | {t for t, _, _ in self.ref_columns}
        existing = {
            r["table_name"] for r in await self.conn.fetch(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_name = ANY($1::text[])",
                list(LINE_EQUIPMENT),
            )
        }
        self.snapshot_tables = sorted(tables | existing)

    # --- снимок ---
    async def snapshot(self) -> dict[str, tuple[int, str]]:
        snap = {}
        for t in self.snapshot_tables:
            row = await self.conn.fetchrow(
                f"SELECT count(*) AS n, md5(COALESCE(string_agg(h, '' ORDER BY h), '')) AS h "
                f"FROM (SELECT md5(_t::text) AS h FROM {q(t)} _t) s"
            )
            snap[t] = (row["n"], row["h"])
        return snap

    # --- ссылки на узлы ---
    async def ref_counts(self) -> dict[str, tuple[int, int]]:
        """{table.column: (ссылок на несуществующий узел, ссылок активных строк на снятый узел)}."""
        out = {}
        for t, c, has_removed in self.ref_columns:
            active = " AND COALESCE(_t.removed, 0) = 0" if has_removed else ""
            row = await self.conn.fetchrow(
                f"""
                SELECT count(*) FILTER (WHERE n.id IS NULL) AS missing,
                       count(*) FILTER (WHERE n.id IS NOT NULL AND COALESCE(n.removed, 0) <> 0{active}) AS removed
                FROM {q(t)} _t LEFT JOIN nodes n ON n.id = _t.{q(c)}
                WHERE _t.{q(c)} IS NOT NULL AND _t.{q(c)} <> 0
                """
            )
            out[f"{t}.{c}"] = (row["missing"], row["removed"])
        return out

    def ref_regressions(self, counts: dict) -> dict:
        bad = {}
        for k, (missing, removed) in counts.items():
            m0, r0 = self.ref_baseline.get(k, (0, 0))
            if missing > m0 or removed > r0:
                bad[k] = {"missing": [m0, missing], "to_removed": [r0, removed]}
        return bad

    # --- расчёт ---
    async def run_calc(self, label: str) -> dict:
        name = f"b7-{label}-{datetime.now():%H%M%S}"
        started = time.monotonic()
        body = {**self.calc_body, "fragment_ids": [self.fragment], "name": name}
        res = await self.api("POST", "/api/v1/calculations/run", json=body)
        task_id = res["task_id"]
        status: dict = {}
        while time.monotonic() - started < CALC_TIMEOUT_S:
            await asyncio.sleep(3)
            status = await self.api("GET", f"/api/v1/task/{task_id}")
            if status["status"] in ("SUCCESS", "FAILURE", "REVOKED"):
                break
        seconds = round(time.monotonic() - started, 1)
        result = status.get("result") or {}
        ok = status.get("status") == "SUCCESS" and isinstance(result, dict) and result.get("status") == "success"
        calc_id = None
        listing = await self.api("GET", "/api/v1/calculations", params={"file_id": self.fragment, "limit": 50})
        for item in listing.get("items", []):
            if item.get("name") == name:
                calc_id = item["id"]
                break
        out = {
            "name": name, "task_status": status.get("status"), "ok": ok and calc_id is not None,
            "seconds": seconds, "calc_id": calc_id,
            "error": None if ok else (status.get("error") or (result.get("error") if isinstance(result, dict) else None)
                                      or f"task {status.get('status')}"),
        }
        if calc_id is not None:
            self.created_calcs.append(calc_id)
            out["ut_lines"] = await self.conn.fetchval(
                "SELECT count(DISTINCT lineid) FROM ut_out WHERE calculationid = $1", calc_id)
            out["us_nodes"] = await self.conn.fetchval(
                "SELECT count(DISTINCT nodeid) FROM us_out WHERE calculationid = $1", calc_id)
            if label == "baseline":
                self.baseline_lines = {r["lineid"] for r in await self.conn.fetch(
                    "SELECT DISTINCT lineid FROM ut_out WHERE calculationid = $1", calc_id)}
                self.baseline_nodes = {r["nodeid"] for r in await self.conn.fetch(
                    "SELECT DISTINCT nodeid FROM us_out WHERE calculationid = $1", calc_id)}
            if out["ut_lines"] == 0:
                out["ok"] = False
                out["error"] = "расчёт без результатов по участкам"
        return out

    async def delete_calc(self, calc_id: int) -> None:
        await self.api("DELETE", f"/api/v1/calculations/{calc_id}")
        if calc_id in self.created_calcs:
            self.created_calcs.remove(calc_id)

    # --- утилиты ---
    async def lnglat(self, sql_point: str, *args) -> tuple[float, float]:
        row = await self.conn.fetchrow(
            f"SELECT ST_X(g) AS lng, ST_Y(g) AS lat FROM (SELECT ST_Transform({sql_point}, 4326) AS g) s", *args)
        return float(row["lng"]), float(row["lat"])

    async def versions(self, nodes=(), lines=()) -> dict:
        params = {}
        if nodes:
            params["nodes"] = ",".join(map(str, nodes))
        if lines:
            params["lines"] = ",".join(map(str, lines))
        return await self.api("GET", "/api/v1/topology/versions", params=params)


# ---------------------------------------------------------------------------
# Проверки после операции
# ---------------------------------------------------------------------------

async def journal_checks(ctx: Ctx, step: Step) -> Optional[dict]:
    if step.operation_id is None:
        step.add("журнал отмены", False, "operation_id не вернулся (журнал не установлен?)")
        return None
    row = await ctx.conn.fetchrow(
        "SELECT change_group_id::text AS gid, actor, operation, after_hashes, "
        "jsonb_array_length(before_rows) AS n FROM topology_undo_log WHERE id = $1",
        step.operation_id,
    )
    if row is None:
        step.add("журнал отмены", False, f"нет записи {step.operation_id}")
        return None
    hashes = json.loads(row["after_hashes"]) if isinstance(row["after_hashes"], str) else row["after_hashes"]
    ok = row["actor"] == ctx.username and row["operation"] == step.operation and row["n"] > 0
    step.add("журнал отмены", ok, f"#{step.operation_id} {row['operation']}, строк {row['n']}")
    audit = await ctx.conn.fetchval(
        "SELECT count(*) FROM audit_log WHERE change_group_id::text = $1", row["gid"])
    step.add("audit_log", audit > 0, f"{audit} зап. группы {row['gid'][:8]}")
    step.touched_nodes = sorted(int(k.split(":")[1]) for k in hashes if k.startswith("nodes:"))
    step.touched_lines = sorted(int(k.split(":")[1]) for k in hashes if k.startswith("linesobj:"))
    return hashes


async def integrity_checks(ctx: Ctx, step: Step) -> None:
    conn = ctx.conn
    # 1. ссылки на узлы — не хуже исходного состояния
    bad = ctx.ref_regressions(await ctx.ref_counts())
    step.add("ссылки nodeid*", not bad, f"{len(ctx.ref_columns)} колонок" + (f"; регрессии: {bad}" if bad else ""))

    lines = await conn.fetch(
        """
        SELECT l.id, l.fileid, l.nodeid1, l.nodeid2, l.shape IS NOT NULL AS has_shape,
               n1.fileid AS f1, n2.fileid AS f2, n1.externalcodeid AS c1, n2.externalcodeid AS c2,
               n1.internalnodeid AS i1, n2.internalnodeid AS i2,
               COALESCE(n1.removed, 0) AS r1, COALESCE(n2.removed, 0) AS r2,
               ST_Distance(ST_StartPoint(l.shape), n1.shape) AS d1,
               ST_Distance(ST_EndPoint(l.shape), n2.shape) AS d2,
               ST_Length(l.shape) AS geom_len,
               (SELECT max(abs(h.pipesectlength - ST_Length(l.shape))) FROM heatpipesections h WHERE h.lineid = l.id) AS len_diff,
               (SELECT count(*) FROM heatpipesections h WHERE h.lineid = l.id) AS passports
        FROM linesobj l
        LEFT JOIN nodes n1 ON n1.id = l.nodeid1
        LEFT JOIN nodes n2 ON n2.id = l.nodeid2
        WHERE l.id = ANY($1::int[]) AND COALESCE(l.removed, 0) = 0
        """,
        step.touched_lines,
    )
    # 2. концы геометрии
    ends_bad = [
        f"{r['id']}: {r['d1']:.3f}/{r['d2']:.3f} м" for r in lines
        if r["has_shape"] and ((r["d1"] or 0) > END_TOLERANCE_M or (r["d2"] or 0) > END_TOLERANCE_M)
    ]
    step.add("концы = узлы", not ends_bad, f"{len(lines)} участков" + (f"; {ends_bad}" if ends_bad else ""))
    # 3. длины
    if step.operation in LENGTH_OPS:
        len_bad = [
            f"{r['id']}: Δ{(r['len_diff'] if r['len_diff'] is not None else float('nan')):.3f} м"
            for r in lines if r["has_shape"] and (r["passports"] == 0 or (r["len_diff"] or 0) > LENGTH_TOLERANCE_M)
        ]
        step.add("длины пересчитаны", not len_bad, f"{len(lines)} участков" + (f"; {len_bad}" if len_bad else ""))
    else:
        step.add("длины пересчитаны", None, "геометрия не меняется")
    # 4. fileid / код / схема
    fbad = []
    for r in lines:
        if r["f1"] != ctx.fragment or r["f2"] != ctx.fragment:
            fbad.append(f"участок {r['id']}: узлы во фрагментах {r['f1']}/{r['f2']}")
        if r["fileid"] is not None and r["fileid"] != r["f1"]:
            fbad.append(f"участок {r['id']}: fileid {r['fileid']} ≠ {r['f1']}")
        if r["c1"] is None or r["c2"] is None:
            fbad.append(f"участок {r['id']}: узел без externalcodeid")
        if r["i1"] != r["i2"]:
            fbad.append(f"участок {r['id']}: концы в разных схемах")
        if r["r1"] or r["r2"]:
            fbad.append(f"участок {r['id']}: активный участок на снятом узле")
    nodes = await conn.fetch(
        "SELECT id, fileid, externalcodeid FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0",
        step.touched_nodes,
    )
    for n in nodes:
        if n["fileid"] != ctx.fragment or n["externalcodeid"] is None:
            fbad.append(f"узел {n['id']}: fileid {n['fileid']}, код {n['externalcodeid']}")
    step.add("fileid согласован", not fbad, f"{len(lines)} уч., {len(nodes)} узл." + (f"; {fbad}" if fbad else ""))


async def calc_checks(ctx: Ctx, step: Step) -> None:
    if ctx.skip_calc:
        step.calc = {"ok": True, "skipped": True}
        return
    calc = await ctx.run_calc(step.operation.lower())
    step.calc = calc
    cid = calc.get("calc_id")
    if cid is None:
        return
    conn = ctx.conn
    active_lines = [r["id"] for r in await conn.fetch(
        "SELECT l.id FROM linesobj l JOIN heatpipesections h ON h.lineid = l.id "
        "WHERE l.id = ANY($1::int[]) AND COALESCE(l.removed, 0) = 0", step.touched_lines)]
    removed_lines = [r["id"] for r in await conn.fetch(
        "SELECT id FROM linesobj WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) <> 0", step.touched_lines)]
    active_nodes = [r["id"] for r in await conn.fetch(
        "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0", step.touched_nodes)]
    removed_nodes = [r["id"] for r in await conn.fetch(
        "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) <> 0", step.touched_nodes)]
    in_ut = {r["lineid"] for r in await conn.fetch(
        "SELECT DISTINCT lineid FROM ut_out WHERE calculationid = $1 AND lineid = ANY($2::int[])",
        cid, active_lines + removed_lines)}
    in_us = {r["nodeid"] for r in await conn.fetch(
        "SELECT DISTINCT nodeid FROM us_out WHERE calculationid = $1 AND nodeid = ANY($2::int[])",
        cid, active_nodes + removed_nodes)}
    skip_l = set(step.not_expected.get("lines", ()))
    skip_n = set(step.not_expected.get("nodes", ()))
    active_lines = [i for i in active_lines if i not in skip_l]
    active_nodes = [i for i in active_nodes if i not in skip_n]
    missing_l = sorted(set(active_lines) - in_ut)
    missing_n = sorted(set(active_nodes) - in_us)
    ghost = sorted((set(removed_lines) & in_ut) | (set(removed_nodes) & in_us))
    calc["lines_seen"] = f"{len(set(active_lines) & in_ut)}/{len(active_lines)}"
    calc["nodes_seen"] = f"{len(set(active_nodes) & in_us)}/{len(active_nodes)}"
    calc["missing"] = {"lines": missing_l, "nodes": missing_n, "removed_in_results": ghost}
    visible = not missing_l and not missing_n and not ghost
    calc["visible"] = visible
    if not visible:
        calc["ok"] = False
    b = ctx.baseline_calc
    if b.get("ut_lines") is not None:
        calc["delta"] = f"{calc['ut_lines'] - b['ut_lines']:+d} уч., {calc['us_nodes'] - b['us_nodes']:+d} узл."
    try:
        await ctx.delete_calc(cid)
        calc["deleted"] = True
    except ApiError as e:
        calc["deleted"] = False
        calc["delete_error"] = str(e)


async def after_operation(ctx: Ctx, step: Step, extra: Optional[Callable[[Step], Awaitable[None]]] = None) -> None:
    await journal_checks(ctx, step)
    await integrity_checks(ctx, step)
    if extra is not None:
        await extra(step)
    await calc_checks(ctx, step)


async def undo_all(ctx: Ctx, sc: Scenario, steps: list[Step]) -> None:
    ok = True
    for step in reversed(steps):
        if step.operation_id is None:
            continue
        try:
            res = await ctx.api("POST", "/api/v1/topology/undo", json={"operation_id": step.operation_id})
            report = {"restored": res.get("restored"), "deleted": res.get("deleted")}
            sc.undo.append(f"#{step.operation_id} {step.operation}: ok {json.dumps(report, ensure_ascii=False)}")
        except ApiError as e:
            ok = False
            sc.undo.append(f"#{step.operation_id} {step.operation}: {e}")
    sc.undo_ok = ok


async def run_scenario(ctx: Ctx, title: str, body: Callable[[Scenario], Awaitable[None]]) -> Scenario:
    sc = Scenario(title)
    print(f"== {title}", flush=True)
    before = await ctx.snapshot()
    try:
        await body(sc)
    except ApiError as e:
        sc.error = str(e)
    except Exception as e:  # noqa: BLE001 - провал сценария попадает в отчёт
        sc.error = f"{type(e).__name__}: {e}"
    done = [s for s in sc.steps if s.operation_id is not None]
    if done:
        await undo_all(ctx, sc, done)
    else:
        sc.undo_ok = sc.error is None and not sc.steps
    after = await ctx.snapshot()
    diff = [f"{t}: {before[t][0]}→{after[t][0]} строк" + ("" if before[t][0] != after[t][0] else ", содержимое")
            for t in before if before[t] != after[t]]
    sc.snapshot_ok = not diff
    sc.snapshot_diff = diff
    sc.refs_after_undo_ok = not ctx.ref_regressions(await ctx.ref_counts())
    status = "OK" if sc.ok else "FAIL"
    print(f"   {status}: steps={[(s.operation, s.ok) for s in sc.steps]} undo={sc.undo_ok} snapshot={sc.snapshot_ok}"
          + (f" error={sc.error}" if sc.error else ""), flush=True)
    return sc


# ---------------------------------------------------------------------------
# Выбор объектов на фрагменте
# ---------------------------------------------------------------------------

EXACT_LINE = """
    l.shape IS NOT NULL
    AND ST_Distance(ST_StartPoint(l.shape), n1.shape) <= 0.001
    AND ST_Distance(ST_EndPoint(l.shape), n2.shape) <= 0.001
"""


async def fragment_graph(ctx: Ctx):
    import networkx as nx
    rows = await ctx.conn.fetch(
        """
        SELECT l.id, l.nodeid1, l.nodeid2 FROM linesobj l
        JOIN nodes n1 ON n1.id = l.nodeid1 JOIN nodes n2 ON n2.id = l.nodeid2
        WHERE COALESCE(l.removed, 0) = 0 AND n1.fileid = $1 AND COALESCE(n1.removed, 0) = 0
          AND COALESCE(n2.removed, 0) = 0 AND n1.internalnodeid IS NULL
        """,
        ctx.fragment,
    )
    g = nx.MultiGraph()
    for r in rows:
        g.add_edge(r["nodeid1"], r["nodeid2"], key=r["id"])
    return g


async def candidate_lines(ctx: Ctx, extra_where: str = "", order: str = "l.id", limit: int = 50) -> list:
    """Участки фрагмента основной сети с паспортом, точными концами и результатом в базовом расчёте."""
    return await ctx.conn.fetch(
        f"""
        SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid, ST_Length(l.shape) AS len
        FROM linesobj l
        JOIN nodes n1 ON n1.id = l.nodeid1 JOIN nodes n2 ON n2.id = l.nodeid2
        WHERE COALESCE(l.removed, 0) = 0 AND n1.fileid = $1 AND n2.fileid = $1
          AND n1.internalnodeid IS NULL AND n2.internalnodeid IS NULL
          AND COALESCE(n1.removed, 0) = 0 AND COALESCE(n2.removed, 0) = 0
          AND EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id)
          AND l.id = ANY($2::int[])
          AND {EXACT_LINE} {extra_where}
        ORDER BY {order}
        LIMIT {int(limit)}
        """,
        ctx.fragment, sorted(ctx.baseline_lines),
    )


async def line_equipment(ctx: Ctx, line_ids: list[int]) -> dict:
    out = {}
    for t in LINE_EQUIPMENT:
        if t not in ctx.snapshot_tables:
            continue
        n = await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE lineid = ANY($1::int[])", line_ids)
        if n:
            out[t] = n
    return out


def version_of(vers: dict, kind: str, obj_id: int) -> Optional[str]:
    return (vers.get(kind) or {}).get(str(obj_id), {}).get("version")


# ---------------------------------------------------------------------------
# Сценарии
# ---------------------------------------------------------------------------

async def sc_create(ctx: Ctx, sc: Scenario) -> None:
    g = await fragment_graph(ctx)
    cands = await candidate_lines(ctx, "AND l.externalsignlineid = 1", "l.id", 200)
    base = next(r for r in cands if g.degree(r["nodeid1"]) == 2 and r["nodeid1"] in ctx.baseline_nodes
                and r["nodeid2"] in ctx.baseline_nodes)
    anchor, other = base["nodeid1"], base["nodeid2"]
    lng, lat = await ctx.lnglat(
        "ST_Translate((SELECT shape FROM nodes WHERE id = $1), 15, 10)", anchor)

    step = Step("Создание узла", "CREATE_NODE", f"рядом с узлом {anchor} (+15 м, +10 м)")
    sc.steps.append(step)
    res = await ctx.api("POST", "/api/v1/topology/node", json={"lng": lng, "lat": lat, "near_node_id": anchor})
    step.operation_id = res.get("operation_id")
    new_node = res["id"]
    step.objects += f" → узел {new_node}"
    step.not_expected = {"nodes": [new_node], "why": "изолированный узел не входит в расчётную сеть"}

    async def node_extra(s: Step) -> None:
        ref = await ctx.conn.fetchrow("SELECT fileid, externalcodeid, externalsignid FROM nodes WHERE id = $1", anchor)
        got = await ctx.conn.fetchrow("SELECT fileid, externalcodeid, externalsignid FROM nodes WHERE id = $1", new_node)
        s.add("атрибуты от образца", dict(ref) == dict(got), f"образец {dict(ref)}, новый {dict(got)}")

    await after_operation(ctx, step, node_extra)

    step2 = Step("Создание участка", "CREATE_LINE", f"{anchor} → {new_node}")
    sc.steps.append(step2)
    vers = await ctx.versions(nodes=[anchor, new_node])
    res = await ctx.api("POST", "/api/v1/topology/line", json={
        "nodeid1": anchor, "nodeid2": new_node,
        "nodeid1_version": version_of(vers, "nodes", anchor),
        "nodeid2_version": version_of(vers, "nodes", new_node),
    })
    step2.operation_id = res.get("operation_id")
    new_line = res["id"]
    step2.objects += f" → участок {new_line} (тупик)"
    step2.not_expected = {"lines": [new_line], "why": "тупик без потребителя: расход 0, sety не пишет его в ut_out"}

    async def line_extra(s: Step) -> None:
        p = res.get("passport") or {}
        row = await ctx.conn.fetchrow(
            "SELECT h.diametercondit AS d, t.diametercondit AS td FROM heatpipesections h "
            "LEFT JOIN heatpipesections t ON t.lineid = $2 WHERE h.lineid = $1", new_line, p.get("template_line_id"))
        s.add("паспорт от образца", p.get("template_line_id") is not None and row is not None and row["d"] == row["td"],
              f"{p}; Ду {row['d'] if row else None}")
        layer = await ctx.conn.fetchval(
            """
            SELECT count(*) FROM linesobj l
            JOIN heatpipesections hps ON hps.lineid = l.id
            JOIN nodes n1 ON n1.id = l.nodeid1 JOIN nodes n2 ON n2.id = l.nodeid2
            JOIN externalcodes ec1 ON ec1.id = n1.externalcodeid
            JOIN externalcodes ec2 ON ec2.id = n2.externalcodeid
            WHERE l.id = $1 AND l.removed = 0 AND n1.internalnodeid IS NULL
            """,
            new_line,
        )
        s.add("виден SQL view слоя heatpipesections", layer == 1, f"строк {layer}")

    await after_operation(ctx, step2, line_extra)

    # Замыкание обхода: новый узел → второй конец исходного участка; расход по обоим новым
    # участкам ненулевой, оба должны появиться в ut_out
    step3 = Step("Создание участка (обход)", "CREATE_LINE", f"{new_node} → {other}, параллельно участку {base['id']}")
    sc.steps.append(step3)
    vers = await ctx.versions(nodes=[new_node, other])
    res3 = await ctx.api("POST", "/api/v1/topology/line", json={
        "nodeid1": new_node, "nodeid2": other,
        "nodeid1_version": version_of(vers, "nodes", new_node),
        "nodeid2_version": version_of(vers, "nodes", other),
    })
    step3.operation_id = res3.get("operation_id")
    line3 = res3["id"]
    step3.objects += f" → участок {line3}"

    async def loop_extra(s: Step) -> None:
        s.touched_lines = sorted(set(s.touched_lines) | {new_line})  # тупик стал обходом
        s.add("паспорт от образца", (res3.get("passport") or {}).get("template_line_id") is not None,
              f"{res3.get('passport')}")

    await after_operation(ctx, step3, loop_extra)


async def sc_move(ctx: Ctx, sc: Scenario) -> None:
    g = await fragment_graph(ctx)
    cands = await candidate_lines(ctx, "AND l.externalsignlineid = 1", "l.id DESC", 300)
    exact = {r["id"] for r in cands}
    node = None
    for r in cands:
        n = r["nodeid2"]
        if g.degree(n) == 2 and n in ctx.baseline_nodes and all(k in exact for _, _, k in g.edges(n, keys=True)):
            node = n
            break
    if node is None:
        raise RuntimeError("нет узла степени 2 с точными концами участков")
    lng, lat = await ctx.lnglat("ST_Translate((SELECT shape FROM nodes WHERE id = $1), 4, -3)", node)
    step = Step("Перенос узла", "MOVE", f"узел {node} на 5 м")
    sc.steps.append(step)
    vers = await ctx.versions(nodes=[node])
    res = await ctx.api("PUT", f"/api/v1/topology/node/{node}/move",
                        json={"lng": lng, "lat": lat, "expected_version": version_of(vers, "nodes", node)})
    step.operation_id = res.get("operation_id")

    async def extra(s: Step) -> None:
        s.add("участки пересчитаны", res.get("recalculated_lines", 0) >= 2, f"recalculated_lines={res.get('recalculated_lines')}")

    await after_operation(ctx, step, extra)


async def sc_split(ctx: Ctx, sc: Scenario) -> None:
    eq_tables = [t for t in LINE_EQUIPMENT if t in ctx.snapshot_tables]
    on_line = " OR ".join(f"EXISTS (SELECT 1 FROM {q(t)} e WHERE e.lineid = l.id)" for t in eq_tables)

    # 1. Звено-оборудование (задвижка, насос, регулятор…) — участок без паспорта трубы:
    #    разрезание отклоняется (половина без объекта выпала бы из расчёта и разорвала сеть).
    link = await ctx.conn.fetchrow(
        f"""
        SELECT l.id FROM linesobj l JOIN nodes n1 ON n1.id = l.nodeid1
        WHERE COALESCE(l.removed, 0) = 0 AND n1.fileid = $1 AND l.shape IS NOT NULL
          AND ST_Length(l.shape) > 2 AND ({on_line})
          AND NOT EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id)
        ORDER BY l.id LIMIT 1
        """,
        ctx.fragment,
    )
    if link is not None:
        lid = link["id"]
        eq = await line_equipment(ctx, [lid])
        st = Step("Разрезание звена-оборудования", "SPLIT", f"участок {lid} ({eq}) — должен быть отклонён")
        st.calc = {"ok": True, "skipped": "операция отклонена, данные не менялись"}
        sc.steps.append(st)
        lng, lat = await ctx.lnglat("ST_LineInterpolatePoint((SELECT shape FROM linesobj WHERE id = $1), 0.5)", lid)
        for dry in (True, False):
            try:
                await ctx.api("POST", "/api/v1/topology/split-line", json={
                    "line_id": lid, "lng": lng, "lat": lat, "dry_run": dry, "review_to_new": {}})
                st.add(f"отказ ({'dry-run' if dry else 'запись'})", False, "разрезано")
            except ApiError as e:
                detail = e.body.get("detail") if isinstance(e.body, dict) else None
                code = detail.get("code") if isinstance(detail, dict) else None
                not_pipe = isinstance(detail, dict) and "not_a_pipe" in (detail.get("blockers") or {})
                st.add(f"отказ ({'dry-run' if dry else 'запись'})", e.status == 409 and code == "blocked" and not_pipe,
                       f"HTTP {e.status} {code}: {detail.get('message') if isinstance(detail, dict) else detail}")

    # 2. Труба, смежная со звеньями оборудования: разрезание, оборудование и узловые объекты
    #    остаются на своих звеньях/узлах, обе половины и новый узел — в расчёте.
    near_eq = " OR ".join(
        f"EXISTS (SELECT 1 FROM linesobj e JOIN {q(t)} x ON x.lineid = e.id WHERE COALESCE(e.removed, 0) = 0 "
        f"AND (e.nodeid1 IN (l.nodeid1, l.nodeid2) OR e.nodeid2 IN (l.nodeid1, l.nodeid2)))"
        for t in eq_tables
    )
    cands = await candidate_lines(ctx, f"AND ({near_eq}) AND ST_Length(l.shape) > 10", "l.id", 20)
    if not cands:
        raise RuntimeError("нет трубы, смежной со звеньями оборудования")
    line = cands[0]
    lid = line["id"]
    adjacent = [r["id"] for r in await ctx.conn.fetch(
        "SELECT id FROM linesobj WHERE COALESCE(removed, 0) = 0 AND id <> $1 "
        "AND (nodeid1 IN ($2, $3) OR nodeid2 IN ($2, $3))", lid, line["nodeid1"], line["nodeid2"])]
    eq_before = await line_equipment(ctx, adjacent + [lid])
    node_refs_before = {}
    for t, c, _ in ctx.ref_columns:
        if t in ("linesobj", "nodes"):
            continue
        n = await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE {q(c)} IN ($1, $2)", line["nodeid1"], line["nodeid2"])
        if n:
            node_refs_before[f"{t}.{c}"] = n
    lng, lat = await ctx.lnglat("ST_LineInterpolatePoint((SELECT shape FROM linesobj WHERE id = $1), 0.5)", lid)
    step = Step("Разрезание трубы у оборудования", "SPLIT",
                f"участок {lid}; на смежных звеньях {eq_before}, на узлах {node_refs_before}")
    sc.steps.append(step)
    preview = await ctx.api("POST", "/api/v1/topology/split-line",
                            json={"line_id": lid, "lng": lng, "lat": lat, "dry_run": True})
    items = (preview.get("transferred") or {}).get("review_items") or {}
    review_to_new = {t: [it["id"] for it in lst[1::2]] for t, lst in items.items()}  # решение B2, если есть
    res = await ctx.api("POST", "/api/v1/topology/split-line", json={
        "line_id": lid, "lng": lng, "lat": lat, "dry_run": False,
        "expected_version": (preview.get("versions") or {}).get(f"line:{lid}"),
        "review_to_new": review_to_new,
    })
    step.operation_id = res.get("operation_id")
    new_line, new_node = res["new_line_id"], res["new_node_id"]
    step.objects += f" → узел {new_node}, участок {new_line}; перенесено {res.get('transferred', {}).get('moved')}"

    async def extra(s: Step) -> None:
        eq_after = await line_equipment(ctx, adjacent + [lid, new_line])
        s.add("оборудование сохранено", eq_after == eq_before, f"до {eq_before}, после {eq_after}")
        refs_after = {}
        for t, c, _ in ctx.ref_columns:
            if t in ("linesobj", "nodes"):
                continue
            n = await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE {q(c)} IN ($1, $2)", line["nodeid1"], line["nodeid2"])
            if n:
                refs_after[f"{t}.{c}"] = n
        s.add("объекты на узлах сохранены", refs_after == node_refs_before, f"{refs_after}")
        lens = await ctx.conn.fetchrow(
            "SELECT (SELECT ST_Length(shape) FROM linesobj WHERE id = $1) + "
            "(SELECT ST_Length(shape) FROM linesobj WHERE id = $2) AS s", lid, new_line)
        s.add("сумма длин половин", abs(lens["s"] - float(line["len"])) < 0.01,
              f"{lens['s']:.3f} vs {float(line['len']):.3f} м")
        d = await ctx.conn.fetchrow(
            "SELECT a.diametercondit AS a, b.diametercondit AS b FROM heatpipesections a, heatpipesections b "
            "WHERE a.lineid = $1 AND b.lineid = $2", lid, new_line)
        s.add("паспорт клонирован", d is not None and d["a"] == d["b"], f"Ду {dict(d) if d else None}")

    await after_operation(ctx, step, extra)


async def sc_merge(ctx: Ctx, sc: Scenario) -> None:
    g = await fragment_graph(ctx)
    cands = await candidate_lines(ctx, "AND ST_Length(l.shape) < 40", "ST_Length(l.shape)", 120)
    exact = {r["id"] for r in await candidate_lines(ctx, "", "l.id", 100000)}
    chosen = None
    tried = 0
    for r in cands:
        for target, source in ((r["nodeid1"], r["nodeid2"]), (r["nodeid2"], r["nodeid1"])):
            if (g.degree(source) < 2 or target not in ctx.baseline_nodes
                    or not all(k in exact for _, _, k in g.edges(source, keys=True))):
                continue
            deps = sum(
                [await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE {q(c)} = $1", source)
                 for t, c, _ in ctx.ref_columns if t not in ("nodes", "linesobj")]
            )
            if not deps:
                continue
            tried += 1
            prev = await ctx.api("POST", "/api/v1/topology/merge-nodes", json={
                "target_node_id": target, "source_node_id": source, "dry_run": True})
            if not prev.get("blockers") and prev.get("transfer"):
                chosen = (target, source, prev)
                break
            if tried > 40:
                break
        if chosen or tried > 40:
            break
    if chosen is None:
        raise RuntimeError(f"нет пары узлов для слияния с переносом зависимостей (проверено {tried})")
    target, source, prev = chosen
    step = Step("Слияние узлов с зависимостями", "MERGE",
                f"{source} → {target}; перенос {prev.get('transfer')}, снимаются {prev.get('removed_lines')}")
    sc.steps.append(step)
    vers = prev.get("versions") or {}
    res = await ctx.api("POST", "/api/v1/topology/merge-nodes", json={
        "target_node_id": target, "source_node_id": source, "dry_run": False,
        "target_version": vers.get(f"node:{target}"), "source_version": vers.get(f"node:{source}"),
    })
    step.operation_id = res.get("operation_id")

    async def extra(s: Step) -> None:
        left = {}
        for t, c, _ in ctx.ref_columns:
            n = await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE {q(c)} = $1", source)
            if n and t != "nodes":
                left[f"{t}.{c}"] = n
        # Ссылки выхода расчёта (*_out) исключены из ref_columns; снятые участки источника допустимы
        left.pop("linesobj.nodeid1", None)
        left.pop("linesobj.nodeid2", None)
        s.add("ссылки источника перенесены", not left, f"остались {left}" if left else f"{prev.get('transfer')}")

    await after_operation(ctx, step, extra)


async def sc_delete(ctx: Ctx, sc: Scenario) -> None:
    import networkx as nx
    g = await fragment_graph(ctx)
    simple = nx.Graph(g)
    bridges = {frozenset(e) for e in nx.bridges(simple)}
    cands = await candidate_lines(ctx, "AND l.externalsignlineid = 1", "l.id", 400)
    line = None
    for r in cands:
        if frozenset((r["nodeid1"], r["nodeid2"])) in bridges:
            continue
        if not await line_equipment(ctx, [r["id"]]):
            line = r
            break
    if line is None:
        raise RuntimeError("нет участка вне мостов без оборудования")
    lid = line["id"]
    step = Step("Удаление участка", "DELETE_LINE", f"участок {lid} (в кольце, без оборудования)")
    sc.steps.append(step)
    vers = await ctx.versions(lines=[lid])
    res = await ctx.api("DELETE", f"/api/v1/topology/line/{lid}",
                        params={"expected_version": version_of(vers, "lines", lid)})
    step.operation_id = res.get("operation_id")

    async def extra(s: Step) -> None:
        row = await ctx.conn.fetchrow(
            "SELECT l.removed, (SELECT count(*) FROM heatpipesections h WHERE h.lineid = l.id) AS p FROM linesobj l WHERE l.id = $1",
            lid)
        s.add("участок снят", row["removed"] == 1, f"removed={row['removed']}, паспортов {row['p']}")

    await after_operation(ctx, step, extra)

    # Удаление узла (каскадом с участками): узел степени 2 в кольце, без ссылок
    g = await fragment_graph(ctx)
    arts = set(nx.articulation_points(nx.Graph(g)))
    exact = {r["id"] for r in await candidate_lines(ctx, "", "l.id", 100000)}
    node = None
    for n in sorted(g.nodes):
        if n in arts or g.degree(n) != 2 or n in (line["nodeid1"], line["nodeid2"]) or n not in ctx.baseline_nodes:
            continue
        if not all(k in exact for _, _, k in g.edges(n, keys=True)):
            continue
        if await line_equipment(ctx, [k for _, _, k in g.edges(n, keys=True)]):
            continue
        refs = 0
        for t, c, _ in ctx.ref_columns:
            if t in ("linesobj",):
                continue
            refs += await ctx.conn.fetchval(f"SELECT count(*) FROM {q(t)} WHERE {q(c)} = $1", n)
            if refs:
                break
        if not refs:
            node = n
            break
    if node is None:
        raise RuntimeError("нет узла для удаления")
    step2 = Step("Удаление узла (каскад)", "DELETE_NODE", f"узел {node} степени 2 в кольце")
    sc.steps.append(step2)
    try:
        await ctx.api("DELETE", f"/api/v1/topology/node/{node}")
        step2.add("safe-delete без cascade", False, "узел с участками удалён без cascade")
    except ApiError as e:
        step2.add("safe-delete без cascade", e.status == 409, f"HTTP {e.status}")
    vers = await ctx.versions(nodes=[node])
    res = await ctx.api("DELETE", f"/api/v1/topology/node/{node}",
                        params={"cascade": "true", "expected_version": version_of(vers, "nodes", node)})
    step2.operation_id = res.get("operation_id")
    step2.objects += f"; сняты участки {res.get('removed_lines')}"
    await after_operation(ctx, step2)


async def sc_reverse(ctx: Ctx, sc: Scenario) -> None:
    cands = await candidate_lines(ctx, "AND l.externalsignlineid = 2", "l.id", 60)
    chosen = None
    for r in cands:
        prev = await ctx.api("POST", "/api/v1/topology/reverse-line", json={"line_id": r["id"], "dry_run": True})
        if prev.get("pair_line_id") and not prev.get("requires_confirmation"):
            chosen = (r, prev)
            break
    if chosen is None:
        raise RuntimeError("нет парного участка подачи без направленного оборудования")
    line, prev = chosen
    lid, pid = line["id"], prev["pair_line_id"]
    before = {r["id"]: dict(r) for r in await ctx.conn.fetch(
        "SELECT id, nodeid1, nodeid2, externalsignlineid, ST_AsEWKB(ST_Reverse(shape)) AS rev FROM linesobj WHERE id = ANY($1::int[])",
        [lid, pid])}
    step = Step("Разворот пары", "REVERSE", f"участок {lid} + парный {pid}")
    sc.steps.append(step)
    vers = prev.get("versions") or {}
    res = await ctx.api("POST", "/api/v1/topology/reverse-line", json={
        "line_id": lid, "dry_run": False, "expected_version": vers.get(f"line:{lid}"),
        "pair_line_id": pid, "pair_version": vers.get(f"line:{pid}"),
    })
    step.operation_id = res.get("operation_id")

    async def extra(s: Step) -> None:
        after = {r["id"]: dict(r) for r in await ctx.conn.fetch(
            "SELECT id, nodeid1, nodeid2, externalsignlineid, ST_AsEWKB(shape) AS g FROM linesobj WHERE id = ANY($1::int[])",
            [lid, pid])}
        bad = []
        for i in (lid, pid):
            b, a = before[i], after[i]
            if (a["nodeid1"], a["nodeid2"]) != (b["nodeid2"], b["nodeid1"]):
                bad.append(f"{i}: узлы не поменялись")
            if bytes(a["g"]) != bytes(b["rev"]):
                bad.append(f"{i}: геометрия не развёрнута")
        s.add("оба участка развёрнуты", not bad, "; ".join(bad) if bad else f"{lid}, {pid}")

    await after_operation(ctx, step, extra)


async def sc_geometry(ctx: Ctx, sc: Scenario) -> None:
    cands = await candidate_lines(ctx, "AND l.externalsignlineid = 1 AND ST_Length(l.shape) > 30", "l.id DESC", 20)
    lid = cands[0]["id"]
    geo = await ctx.api("GET", f"/api/v1/topology/line/{lid}/geometry")
    coords = geo["coordinates"]
    # вставка вершины на середине первого сегмента со сдвигом ~3 м к северу
    (x1, y1), (x2, y2) = coords[0][:2], coords[1][:2]
    mid = [(x1 + x2) / 2, (y1 + y2) / 2 + 0.000027]
    new_coords = [coords[0], mid] + coords[1:]
    step = Step("Правка геометрии", "GEOMETRY", f"участок {lid}: +1 вершина ({len(coords)}→{len(new_coords)})")
    sc.steps.append(step)
    res = await ctx.api("PUT", f"/api/v1/topology/line/{lid}/geometry",
                        json={"coordinates": new_coords, "expected_version": geo["version"]})
    step.operation_id = res.get("operation_id")

    async def extra(s: Step) -> None:
        n = await ctx.conn.fetchval("SELECT ST_NumPoints(shape) FROM linesobj WHERE id = $1", lid)
        s.add("вершина добавлена", n == len(new_coords), f"точек {n}")

    await after_operation(ctx, step, extra)


SCENARIOS: list[tuple[str, Callable[[Ctx, Scenario], Awaitable[None]]]] = [
    ("Создание узла и участка", sc_create),
    ("Перенос узла", sc_move),
    ("Разрезание: звено оборудования и труба у оборудования", sc_split),
    ("Слияние узлов с зависимостями", sc_merge),
    ("Удаление участка и узла", sc_delete),
    ("Разворот пары подача/обратка", sc_reverse),
    ("Правка геометрии (вершины)", sc_geometry),
]


# ---------------------------------------------------------------------------
# Отчёт
# ---------------------------------------------------------------------------

def _mark(ok: Optional[bool]) -> str:
    return "—" if ok is None else ("✅" if ok else "❌")


def render(ctx: Ctx, scenarios: list[Scenario], started: datetime, seconds: float) -> str:
    all_ok = all(s.ok for s in scenarios)
    lines = [
        "# Этап B7 — golden-приёмка редактора топологии",
        "",
        f"Прогон: {started:%Y-%m-%d %H:%M}, БД `{os.environ.get('DB_NAME')}` (копия), фрагмент {ctx.fragment}, "
        f"пользователь `{ctx.username}`, {seconds / 60:.1f} мин. "
        f"Скрипт: `itwin-api/itwin-api/scripts/golden/topology_acceptance.py`.",
        "",
        f"**Итог: {'все операции прошли' if all_ok else 'есть провалы'}** "
        f"({sum(s.ok for s in scenarios)}/{len(scenarios)} сценариев).",
        "",
        "Каждая операция: снимок таблиц сети → операция через HTTP API (dry-run/версии как в web) → "
        "инварианты → расчёт sety по фрагменту (Celery) → проверка ut_out/us_out → удаление расчёта → "
        "undo → сравнение снимка с исходным. Параметры расчёта: "
        f"`{json.dumps(ctx.calc_body, ensure_ascii=False)}`.",
        "",
        f"Базовый расчёт до операций: {ctx.baseline_calc.get('seconds')} с, участков в ut_out "
        f"{ctx.baseline_calc.get('ut_lines')}, узлов в us_out {ctx.baseline_calc.get('us_nodes')}.",
        "",
        "| Операция | Объекты | Ссылки | Концы | Длины | fileid | Аудит/журнал | Проверки операции | Расчёт | В ut_out/us_out | Undo + снимок | Итог |",
        "|---|---|:-:|:-:|:-:|:-:|:-:|---|---|:-:|:-:|:-:|",
    ]
    common = {"ссылки nodeid*", "концы = узлы", "длины пересчитаны", "fileid согласован", "журнал отмены", "audit_log"}
    for sc in scenarios:
        if not sc.steps:
            lines.append(f"| {sc.title} | — | | | | | | | | | {_mark(False)} | ❌ {sc.error or ''} |")
            continue
        for i, st in enumerate(sc.steps):
            by = {c.name: c for c in st.checks}
            def m(name):
                c = by.get(name)
                return _mark(c.ok) if c else "—"
            aj = [by.get("журнал отмены"), by.get("audit_log")]
            aj_ok = None if not any(aj) else all(c.ok for c in aj if c)
            specific = "; ".join(f"{_mark(c.ok)} {c.name}" for c in st.checks if c.name not in common) or "—"
            calc = st.calc
            calc_txt = "— (не требуется)" if calc.get("skipped") else (f"{'✅' if calc.get('task_status') == 'SUCCESS' else '❌'} {calc.get('seconds', '')} с"
                        + (f", {calc['delta']}" if calc.get("delta") else "")) if calc else "—"
            seen = (f"{_mark(calc.get('visible'))} уч. {calc.get('lines_seen')}, узл. {calc.get('nodes_seen')}"
                    + ("*" if st.not_expected else "") if calc.get("calc_id") else "—")
            undo = f"{_mark(sc.undo_ok)} {_mark(sc.snapshot_ok)}" if i == len(sc.steps) - 1 else "↓"
            verdict = "✅" if st.ok and (i < len(sc.steps) - 1 or sc.ok) else "❌"
            err = f" {st.error}" if st.error else ""
            lines.append(
                f"| {st.title} (`{st.operation}`) | {st.objects} | {m('ссылки nodeid*')} | {m('концы = узлы')} | "
                f"{m('длины пересчитаны')} | {m('fileid согласован')} | {_mark(aj_ok)} | {specific} | {calc_txt} | "
                f"{seen} | {undo} | {verdict}{err} |"
            )
        if sc.error:
            lines.append(f"| ↳ ошибка сценария | {sc.error} | | | | | | | | | | ❌ |")
    lines += [
        "",
        "\\* часть объектов по правилам движка в результаты не попадает (sety пишет в `ut_out` только "
        "участки с ненулевым расходом, в `us_out` — узлы связной сети), см. подробности.",
        "", "## Подробности", "",
    ]
    for sc in scenarios:
        lines.append(f"### {sc.title} — {'OK' if sc.ok else 'FAIL'}")
        if sc.error:
            lines.append(f"- Ошибка: `{sc.error}`")
        for st in sc.steps:
            lines.append(f"- **{st.title}** (`{st.operation}`, журнал #{st.operation_id}): {st.objects}")
            for c in st.checks:
                lines.append(f"  - {_mark(c.ok)} {c.name}: {c.detail}")
            if st.not_expected:
                ne = {k: v for k, v in st.not_expected.items() if k != "why"}
                lines.append(f"  - не ожидаются в результатах расчёта {ne}: {st.not_expected.get('why')}")
            if st.calc.get("skipped"):
                lines.append(f"  - расчёт не запускался: {st.calc['skipped']}")
            elif st.calc:
                c = st.calc
                lines.append(
                    f"  - расчёт `{c.get('name')}` #{c.get('calc_id')}: {c.get('task_status')}, {c.get('seconds')} с, "
                    f"ut_out {c.get('ut_lines')} уч., us_out {c.get('us_nodes')} узл."
                    + (f" ({c['delta']})" if c.get("delta") else "")
                    + (f"; нет в результатах: {c.get('missing')}" if c.get("visible") is False else "")
                    + (f"; ошибка: {c.get('error')}" if c.get("error") else "")
                    + ("; удалён" if c.get("deleted") else f"; НЕ удалён: {c.get('delete_error')}")
                )
        for u in sc.undo:
            lines.append(f"- undo {u}")
        lines.append(f"- снимок после undo: {'совпал' if sc.snapshot_ok else 'расхождения: ' + '; '.join(sc.snapshot_diff)}")
        lines.append("")
    lines += [
        "## Что проверяется",
        "",
        f"- **Ссылки**: {len(ctx.ref_columns)} колонок-ссылок на узел (все `nodeid*` числового типа, "
        "`internalnodeid`, `remontnodeid`, `linesobj.nodeid1/2`; без `*_out`). Счётчики «ссылка на "
        "несуществующий узел» и «активная строка ссылается на снятый узел» не должны вырасти "
        "относительно состояния до прогона (исторические висячие ссылки данных не считаются).",
        f"- **Концы**: начало/конец геометрии каждого затронутого активного участка ≤ {END_TOLERANCE_M} м от его узлов.",
        f"- **Длины**: `heatpipesections.pipesectlength` = `ST_Length(shape)` (≤ {LENGTH_TOLERANCE_M} м) "
        "для операций, меняющих геометрию.",
        "- **fileid**: оба узла участка во фрагменте прогона, `linesobj.fileid` пуст или равен ему, "
        "у затронутых узлов есть `externalcodeid`, концы участка в одной схеме (`internalnodeid`).",
        "- **Аудит/журнал**: запись `topology_undo_log` (автор, операция, before-image) и строки "
        "`audit_log` с `change_group_id` операции.",
        "- **Расчёт**: задача Celery `SUCCESS` со статусом `success`, затронутые активные участки "
        "(с паспортом) есть в `ut_out`, узлы — в `us_out`, снятых объектов в результатах нет.",
        f"- **Снимок**: md5 всех строк {len(ctx.snapshot_tables)} таблиц сети (без учёта порядка) до "
        "сценария и после undo совпадают.",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------

async def main() -> int:
    import asyncpg
    import httpx
    from dotenv import load_dotenv

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base-url", default="http://127.0.0.1:8041")
    ap.add_argument("--fragment", type=int, default=74)
    ap.add_argument("--user", default=None, help="имя в токене (по умолчанию b7-<время>)")
    ap.add_argument("--only", default=None, help="номера сценариев через запятую (1..7)")
    ap.add_argument("--out", default=None, help="куда записать отчёт .md")
    ap.add_argument("--skip-calc", action="store_true", help="отладка: без расчётов (базовый — только для выбора объектов)")
    args = ap.parse_args()

    load_dotenv(ROOT / ".env")
    if (ROOT / ".env.copy").exists():
        load_dotenv(ROOT / ".env.copy", override=True)
    from auth import create_access_token

    conn = await asyncpg.connect(
        host=os.environ["DB_HOST"], port=int(os.environ.get("DB_PORT", 5432)),
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], database=os.environ["DB_NAME"],
    )
    if not await conn.fetchval("SELECT to_regclass('public._this_is_copy') IS NOT NULL"):
        print("Отказ: в БД нет таблицы-маркера _this_is_copy — приёмка пишет данные только в копию.")
        return 2
    username = args.user or f"b7-{datetime.now():%m%d%H%M}"
    token = create_access_token(username=username, role="admin", expires_minutes=240)
    calc_body = {"mode": "plan", "tn": -25, "tg": True, "teplovyd": False, "iter": 20, "trtp": 0}
    started = datetime.now()
    t0 = time.monotonic()
    async with httpx.AsyncClient(base_url=args.base_url, timeout=180,
                                 headers={"Authorization": f"Bearer {token}"}) as http:
        ctx = Ctx(conn, http, args.fragment, username, calc_body)
        ctx.skip_calc = args.skip_calc
        cfg = await ctx.api("GET", "/api/v1/auth/config")
        if not (cfg.get("topology_mutations_enabled") and cfg.get("mutations_enabled")):
            print(f"Отказ: на {args.base_url} выключены флаги топологии: {cfg}")
            return 2
        await ctx.discover()
        ctx.ref_baseline = await ctx.ref_counts()
        print(f"Колонок-ссылок: {len(ctx.ref_columns)}, таблиц в снимке: {len(ctx.snapshot_tables)}", flush=True)
        ctx.baseline_calc = await ctx.run_calc("baseline")
        print(f"Базовый расчёт: {ctx.baseline_calc}", flush=True)
        if ctx.baseline_calc.get("calc_id"):
            await ctx.delete_calc(ctx.baseline_calc["calc_id"])
        if not ctx.baseline_calc.get("ok"):
            print("Базовый расчёт не прошёл — приёмка операций бессмысленна")
        selected = SCENARIOS
        if args.only:
            idx = {int(x) for x in args.only.split(",")}
            selected = [s for i, s in enumerate(SCENARIOS, start=1) if i in idx]
        scenarios = []
        for title, fn in selected:
            scenarios.append(await run_scenario(ctx, title, lambda sc, fn=fn: fn(ctx, sc)))
        for cid in list(ctx.created_calcs):
            try:
                await ctx.delete_calc(cid)
            except ApiError as e:
                print(f"Не удалён расчёт {cid}: {e}")
    await conn.close()
    report = render(ctx, scenarios, started, time.monotonic() - t0)
    if args.out:
        Path(args.out).write_text(report, encoding="utf-8")
        print(f"Отчёт: {args.out}")
    else:
        print(report)
    return 0 if all(s.ok for s in scenarios) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
