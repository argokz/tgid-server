"""Создание сети на карте (CAD): цепочка участков одной операцией и данные для привязки.

Цепочка — то, что оператор рисует одним движением: начало (узел, врезка в трубу или новый
узел) → изломы → … → конец. Каждая точка-граница (узел/врезка/новый узел) завершает участок,
изломы остаются вершинами геометрии. Всё — одна транзакция и одна запись журнала отмены
(CHAIN): врезки (разрезание трубы, для пары П/О — обеих труб в одном узле), новые узлы,
участки и их паспорта.

Признак трубы (linesobj.externalsignlineid, enum SignLine десктопа gid8):
  1 — общий (одна запись — обе трубы), 2 — подающий, 3 — обратный,
  4 — подающий-обратный (подача приходит в узел без подающей сети), 5 — обратный-подающий.
Режим рисования задаёт трубы: common → 1; pair → 2 + 3 с общей геометрией и узлами
(так десктоп и find_pair_line узнают пару); supply/return → 2/3, а если конечный узел не в
нужной сети — 4/5, как getExternalSignLineId в graph2.cpp.

Проверки до записи (dry_run возвращает их списком issues; ошибки блокируют сохранение):
новая точка почти в существующем узле, врезка у конца трубы, участок короче
MIN_LINE_LENGTH_M, самопересечение, дубль участка, разные фрагменты/схемы — ошибки;
пересечение трубы без узла — предупреждение. Длина — ST_Length в SRID 9998, как везде.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from database.connect import get_pool
from database.outage_simulation import invalidate_outage_cache
from database.topology import (
    TopologyDependencyError,
    _capture_lines_with_passports,
    _create_line_passport,
    _lock_active,
    _new_node_reference,
    _run,
    _split_line_body,
    find_pair_line,
)
from database.topology_transfer import SPLIT_TRANSFER_RULES

# Новая точка ближе этого к узлу — это тот же узел (иначе «почти совпадающие» узлы рвут сеть).
ALMOST_NODE_M = 0.3
MIN_LINE_LENGTH_M = 0.1
MAX_CHAIN_POINTS = 500
# Пересечения с чужими трубами — не больше стольких в предупреждениях на участок.
MAX_CROSSINGS = 10

# Данные привязки: окно не больше SNAP_MAX_SIDE_M по стороне, объектов — не больше SNAP_LIMIT.
SNAP_MAX_SIDE_M = 6000.0
SNAP_LIMIT = 20000

PIPE_MODES = ("common", "pair", "supply", "return")
NODE_SIGN_BY_MODE = {"common": 1, "pair": 1, "supply": 2, "return": 3}
SIGN_NAMES = {1: "общий", 2: "подающий", 3: "обратный", 4: "подающий-обратный", 5: "обратный-подающий"}
# Какие трубы (подача P / обратка O) представляет участок с признаком
_SIGN_PIPES = {1: {"P", "O"}, 2: {"P"}, 4: {"P"}, 3: {"O"}, 5: {"O"}}

BOUNDARY_KINDS = ("node", "tap", "new")
POINT_KINDS = BOUNDARY_KINDS + ("vertex",)


class ChainValidationError(Exception):
    """Цепочку нельзя сохранить: есть ошибки проверки (HTTP 422 со списком issues)."""

    def __init__(self, issues: list[dict]):
        super().__init__("; ".join(i["message"] for i in issues if i["level"] == "error"))
        self.issues = issues


def line_signs(pipe_mode: str, end_node_sign: Optional[int]) -> list[int]:
    """Признаки участков, которые создаёт режим; end_node_sign — externalsignid конечного узла
    (1 — узел обеих сетей, 2 — только подающей, 3 — только обратной)."""
    if pipe_mode == "common":
        return [1]
    if pipe_mode == "pair":
        return [2, 3]
    if pipe_mode == "supply":
        return [4 if end_node_sign == 3 else 2]
    if pipe_mode == "return":
        return [5 if end_node_sign == 2 else 3]
    raise ValueError(f"Неизвестный режим трубы: {pipe_mode}")


def signs_overlap(new_signs: list[int], existing_sign: Optional[int]) -> bool:
    """Новый участок дублирует существующий между теми же узлами: те же трубы (П/О)."""
    new_pipes = set().union(*(_SIGN_PIPES.get(s, set()) for s in new_signs))
    return bool(new_pipes & _SIGN_PIPES.get(existing_sign if existing_sign is not None else 1, {"P", "O"}))


def _issue(level: str, code: str, message: str, **extra: Any) -> dict:
    return {"level": level, "code": code, "message": message, **{k: v for k, v in extra.items() if v is not None}}


def normalize_points(points: list[dict]) -> list[dict]:
    """Проверка формы цепочки (без БД). Точка: {kind, node_id?, line_id?, lng?, lat?}.

    node — существующий узел; tap — врезка в участок line_id в точке lng/lat; new — новый
    узел; vertex — излом. Первая и последняя точки — границы (не излом). Повторы подряд
    одной и той же точки отбрасываются.
    """
    if not isinstance(points, list) or len(points) < 2:
        raise ValueError("Цепочка — не меньше двух точек")
    if len(points) > MAX_CHAIN_POINTS:
        raise ValueError(f"Слишком много точек в цепочке (не больше {MAX_CHAIN_POINTS})")
    result: list[dict] = []
    for i, raw in enumerate(points):
        p = dict(raw)
        kind = p.get("kind")
        if kind not in POINT_KINDS:
            raise ValueError(f"Точка {i + 1}: неизвестный вид «{kind}»")
        if kind == "node":
            if not isinstance(p.get("node_id"), int) or p["node_id"] <= 0:
                raise ValueError(f"Точка {i + 1}: нужен node_id")
        else:
            for c in ("lng", "lat"):
                v = p.get(c)
                if not isinstance(v, (int, float)) or v != v:
                    raise ValueError(f"Точка {i + 1}: нужны координаты lng/lat")
            if not (-180 <= p["lng"] <= 180 and -90 <= p["lat"] <= 90):
                raise ValueError(f"Точка {i + 1}: координаты вне диапазона")
            if kind == "tap" and (not isinstance(p.get("line_id"), int) or p["line_id"] <= 0):
                raise ValueError(f"Точка {i + 1}: для врезки нужен line_id")
        p["index"] = i
        prev = result[-1] if result else None
        if prev is not None and _same_point(prev, p):
            if prev["kind"] == "vertex" and kind != "vertex":
                result[-1] = p  # излом в месте границы — это сама граница
            continue
        result.append(p)
    if result[0]["kind"] == "vertex" or result[-1]["kind"] == "vertex":
        raise ValueError("Цепочка начинается и заканчивается узлом, врезкой или новым узлом, а не изломом")
    if len(segments(result)) == 0:
        raise ValueError("В цепочке нет ни одного участка")
    return result


def _same_point(a: dict, b: dict) -> bool:
    if a["kind"] == "node" or b["kind"] == "node":
        return a["kind"] == b["kind"] == "node" and a["node_id"] == b["node_id"]
    return a["lng"] == b["lng"] and a["lat"] == b["lat"]


def segments(points: list[dict]) -> list[tuple[int, int]]:
    """Участки цепочки: пары позиций соседних границ в списке точек."""
    bounds = [i for i, p in enumerate(points) if p["kind"] in BOUNDARY_KINDS]
    return list(zip(bounds, bounds[1:]))


async def _capture_split(conn, op, line_id: int) -> None:
    """Образы «до» разрезаемой трубы и зависимых таблиц — как split_line."""
    if not op.journal.enabled:
        return
    await _capture_lines_with_passports(conn, op, [line_id])
    for rule in SPLIT_TRANSFER_RULES:
        try:
            async with conn.transaction():
                await op.journal.capture(conn, rule.table, "_r.lineid = $1", line_id)
        except Exception:  # noqa: BLE001 - таблицы нет в этой БД
            continue


_SEGMENT_GEOM = (
    "ST_MakeLine(ARRAY(SELECT ST_SetSRID(ST_MakePoint(t.x, t.y), 9998) "
    "FROM unnest($1::float8[], $2::float8[]) WITH ORDINALITY AS t(x, y, i) ORDER BY t.i))"
)


async def create_chain(
    points: list[dict],
    pipe_mode: str = "common",
    fileid: Optional[int] = None,
    dry_run: bool = False,
    versions: Optional[dict[str, str]] = None,
    review_to_new: Optional[dict] = None,
    actor: Optional[str] = None,
) -> dict:
    """Цепочка участков одной операцией (см. модуль). dry_run — проверки и отчёт без записи.

    versions — {"node:ID" | "line:ID": версия} объектов, которые видел клиент (409 при чужой
    правке). review_to_new — {line_id: {таблица: [id…]}}: решение по оборудованию без позиции
    на разрезаемых трубах, как в split_line ({} — всё остаётся на первой половине).
    """
    if pipe_mode not in PIPE_MODES:
        raise ValueError(f"Неизвестный режим трубы: {pipe_mode}")
    pts = normalize_points(points)
    versions = versions or {}
    review = {int(k): v for k, v in (review_to_new or {}).items()}

    async def body(conn, op):
        return await _chain_body(conn, op, pts, pipe_mode, fileid, versions, review, dry_run)

    result = await _run(dry_run, body, "CHAIN", actor)
    if not dry_run:
        invalidate_outage_cache()
    return result


async def _chain_body(conn, op, pts, pipe_mode, fileid, versions, review, dry_run) -> dict:
    issues: list[dict] = []
    node_ids = sorted({p["node_id"] for p in pts if p["kind"] == "node"})
    tap_ids = [p["line_id"] for p in pts if p["kind"] == "tap"]
    if len(set(tap_ids)) != len(tap_ids):
        raise ValueError("В один участок можно врезаться только один раз за операцию")

    # --- блокировки и версии ------------------------------------------------
    if node_ids:
        await _lock_active(conn, "node", node_ids, {i: versions.get(f"node:{i}") for i in node_ids})
    pairs: dict[int, int] = {}
    if tap_ids:
        await _lock_active(conn, "line", sorted(tap_ids), {i: versions.get(f"line:{i}") for i in tap_ids})
        for lid in tap_ids:
            pair = await find_pair_line(conn, lid)
            if pair:
                pairs[lid] = pair["line_id"]
        if set(pairs.values()) & set(tap_ids):
            raise ValueError("Врезка в обе трубы пары П/О делается одной точкой — вторая труба режется сама")
        if pairs:
            pair_ids = sorted(pairs.values())
            await _lock_active(conn, "line", pair_ids, {i: versions.get(f"line:{i}") for i in pair_ids})

    # --- существующие узлы и врезки ------------------------------------------
    nodes: dict[int, Any] = {}
    if node_ids:
        for r in await conn.fetch(
            "SELECT id, fileid, externalcodeid, externalsignid, internalnodeid, "
            "ST_X(shape) AS x, ST_Y(shape) AS y FROM nodes WHERE id = ANY($1::int[])",
            node_ids,
        ):
            nodes[r["id"]] = r
        no_shape = [i for i in node_ids if i not in nodes or nodes[i]["x"] is None]
        if no_shape:
            raise ValueError("У узлов " + ", ".join(map(str, no_shape)) + " нет геометрии")
    taps: dict[int, Any] = {}
    for p in pts:
        if p["kind"] != "tap":
            continue
        row = await conn.fetchrow(
            """
            WITH c AS (SELECT ST_Transform(ST_SetSRID(ST_MakePoint($2, $3), 4326), 9998) AS g),
                 l AS (SELECT * FROM linesobj WHERE id = $1),
                 q AS (SELECT ST_LineInterpolatePoint(l.shape, ST_LineLocatePoint(l.shape, c.g)) AS p,
                              ST_Distance(l.shape, c.g) AS off FROM l, c)
            SELECT l.id, l.nodeid1, l.nodeid2, COALESCE(l.fileid, n1.fileid) AS fileid, l.internalnodeid,
                   n1.externalcodeid, n1.externalsignid, n1.fileid AS n1_fileid,
                   EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id) AS is_pipe,
                   ST_X(q.p) AS x, ST_Y(q.p) AS y, q.off,
                   ST_Distance(n1.shape, q.p) AS d1, ST_Distance(n2.shape, q.p) AS d2,
                   ST_X(ST_Transform(q.p, 4326)) AS lng, ST_Y(ST_Transform(q.p, 4326)) AS lat
            FROM l CROSS JOIN q
            LEFT JOIN nodes n1 ON n1.id = l.nodeid1
            LEFT JOIN nodes n2 ON n2.id = l.nodeid2
            """,
            p["line_id"], p["lng"], p["lat"],
        )
        if row is None or row["x"] is None:
            raise ValueError(f"Участок {p['line_id']} не найден или без геометрии")
        taps[p["line_id"]] = row

    # --- фрагмент и схема ----------------------------------------------------
    contexts = {(r["fileid"], r["internalnodeid"]) for r in nodes.values()}
    contexts |= {(r["fileid"], r["internalnodeid"]) for r in taps.values()}
    if len(contexts) > 1:
        issues.append(_issue(
            "error", "mixed_context",
            "Узлы и трубы цепочки из разных фрагментов или схем: участок соединяет объекты одного фрагмента",
        ))
    if contexts:
        ctx_fileid, ctx_inner = sorted(contexts, key=lambda c: (c[0] is None, c))[0]
        if fileid is not None and ctx_fileid != fileid:
            issues.append(_issue(
                "error", "other_fragment",
                f"Объекты цепочки во фрагменте {ctx_fileid}, а рабочий фрагмент — {fileid}",
            ))
    else:
        first = pts[0]
        ref = await _new_node_reference(conn, first["lng"], first["lat"], fileid, None, None)
        ctx_fileid, ctx_inner = ref["fileid"], ref["internalnodeid"]
    if ctx_fileid is None:
        issues.append(_issue("error", "no_fragment", "Не удалось определить фрагмент цепочки"))
    # код (externalcodeid) новых узлов и узлов врезки — от узла того же фрагмента
    code = next((r["externalcodeid"] for r in nodes.values()
                 if r["externalcodeid"] is not None and r["fileid"] == ctx_fileid), None)
    code = code or next((r["externalcodeid"] for r in taps.values()
                         if r["externalcodeid"] is not None and r["n1_fileid"] == ctx_fileid), None)
    if code is None and ctx_fileid is not None and any(p["kind"] in ("new", "tap") for p in pts):
        code = await conn.fetchval(
            "SELECT externalcodeid FROM nodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0 "
            "AND externalcodeid IS NOT NULL ORDER BY id LIMIT 1",
            ctx_fileid,
        ) or await conn.fetchval(
            "SELECT min(id) FROM externalcodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0", ctx_fileid,
        )
        if code is None:
            issues.append(_issue("error", "no_code", f"У фрагмента {ctx_fileid} нет кода (externalcodes)"))

    # --- координаты точек в 9998 ------------------------------------------------
    free = [p for p in pts if p["kind"] in ("new", "vertex")]
    if free:
        rows = await conn.fetch(
            "SELECT t.i, ST_X(g) AS x, ST_Y(g) AS y FROM unnest($1::float8[], $2::float8[]) "
            "WITH ORDINALITY AS t(lng, lat, i), "
            "LATERAL (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(t.lng, t.lat), 4326), 9998) AS g) s",
            [p["lng"] for p in free], [p["lat"] for p in free],
        )
        by_i = {int(r["i"]): r for r in rows}
        for k, p in enumerate(free, start=1):
            p["x"], p["y"] = by_i[k]["x"], by_i[k]["y"]
    for p in pts:
        if p["kind"] == "node":
            p["x"], p["y"] = nodes[p["node_id"]]["x"], nodes[p["node_id"]]["y"]
        elif p["kind"] == "tap":
            p["x"], p["y"] = taps[p["line_id"]]["x"], taps[p["line_id"]]["y"]

    # --- проверки точек -----------------------------------------------------
    for p in pts:
        n = p["index"] + 1
        if p["kind"] == "tap":
            t = taps[p["line_id"]]
            if not t["is_pipe"]:
                issues.append(_issue(
                    "error", "not_a_pipe",
                    f"Участок {p['line_id']} — не труба (оборудование): врезаться можно только в теплопровод",
                    point=n, line_id=p["line_id"],
                ))
            near = min(
                ((t["d1"], t["nodeid1"]), (t["d2"], t["nodeid2"])),
                key=lambda d: d[0] if d[0] is not None else float("inf"),
            )
            if near[0] is not None and near[0] < ALMOST_NODE_M:
                issues.append(_issue(
                    "error", "tap_at_node",
                    f"Врезка в {near[0]:.2f} м от узла {near[1]} — привяжитесь к узлу",
                    point=n, line_id=p["line_id"], node_id=near[1],
                ))
        elif p["kind"] == "new" and ctx_fileid is not None:
            close = await conn.fetchrow(
                """
                SELECT id, ST_Distance(shape, ST_SetSRID(ST_MakePoint($1, $2), 9998)) AS d
                FROM nodes
                WHERE COALESCE(removed, 0) = 0 AND fileid = $3 AND internalnodeid IS NOT DISTINCT FROM $4
                  AND ST_DWithin(shape, ST_SetSRID(ST_MakePoint($1, $2), 9998), $5)
                ORDER BY d LIMIT 1
                """,
                p["x"], p["y"], ctx_fileid, ctx_inner, ALMOST_NODE_M,
            )
            if close is not None:
                issues.append(_issue(
                    "error", "almost_node",
                    f"Новый узел в {float(close['d']):.2f} м от узла {close['id']} — привяжитесь к нему",
                    point=n, node_id=close["id"],
                ))

    def end_sign(p: dict) -> Optional[int]:
        if p["kind"] == "node":
            return nodes[p["node_id"]]["externalsignid"]
        if p["kind"] == "tap":
            return taps[p["line_id"]]["externalsignid"]
        return NODE_SIGN_BY_MODE[pipe_mode]

    # --- проверки участков ---------------------------------------------------
    excluded_lines = sorted(set(tap_ids) | set(pairs.values()))
    plan: list[dict] = []
    for k, (a, b) in enumerate(segments(pts), start=1):
        part = pts[a:b + 1]
        xs, ys = [p["x"] for p in part], [p["y"] for p in part]
        signs = line_signs(pipe_mode, end_sign(pts[b]))
        geo = await conn.fetchrow(
            f"SELECT ST_Length(g) AS length, ST_IsSimple(g) AS simple FROM (SELECT {_SEGMENT_GEOM} AS g) s",
            xs, ys,
        )
        length = float(geo["length"] or 0.0)
        if length < MIN_LINE_LENGTH_M:
            issues.append(_issue(
                "error", "short_line", f"Участок {k} короче {MIN_LINE_LENGTH_M:g} м ({length:.2f} м)", segment=k,
            ))
        if not geo["simple"]:
            issues.append(_issue("error", "self_intersection", f"Участок {k} пересекает сам себя", segment=k))
        ends = [pts[a].get("node_id"), pts[b].get("node_id")]
        if pts[a]["kind"] == "node" and pts[b]["kind"] == "node":
            for r in await conn.fetch(
                """
                SELECT id, externalsignlineid FROM linesobj
                WHERE COALESCE(removed, 0) = 0
                  AND ((nodeid1 = $1 AND nodeid2 = $2) OR (nodeid1 = $2 AND nodeid2 = $1))
                """,
                ends[0], ends[1],
            ):
                if signs_overlap(signs, r["externalsignlineid"]):
                    issues.append(_issue(
                        "error", "duplicate_line",
                        f"Между узлами {ends[0]} и {ends[1]} уже есть участок {r['id']} "
                        f"({SIGN_NAMES.get(r['externalsignlineid'], 'признак ?')})",
                        segment=k, line_id=r["id"],
                    ))
                    break
        if ctx_fileid is not None:
            boundary_nodes = [e for e in ends if e is not None]
            for r in await conn.fetch(
                f"""
                WITH s AS (SELECT {_SEGMENT_GEOM} AS g)
                SELECT l.id,
                       ST_X(ST_Transform(ST_PointOnSurface(ST_Intersection(l.shape, s.g)), 4326)) AS lng,
                       ST_Y(ST_Transform(ST_PointOnSurface(ST_Intersection(l.shape, s.g)), 4326)) AS lat
                FROM linesobj l, s
                WHERE COALESCE(l.removed, 0) = 0 AND l.shape IS NOT NULL
                  AND l.fileid = $3 AND l.internalnodeid IS NOT DISTINCT FROM $4
                  AND ST_Intersects(l.shape, s.g)
                  AND l.id <> ALL($5::int[])
                  AND NOT (l.nodeid1 = ANY($6::int[]) OR l.nodeid2 = ANY($6::int[]))
                ORDER BY l.id LIMIT {MAX_CROSSINGS}
                """,
                xs, ys, ctx_fileid, ctx_inner, excluded_lines, boundary_nodes,
            ):
                issues.append(_issue(
                    "warning", "crossing_without_node",
                    f"Участок {k} пересекает участок {r['id']} без узла — если это соединение, врежьтесь в него",
                    segment=k, line_id=r["id"], lng=r["lng"], lat=r["lat"],
                ))
        if signs and signs[0] in (4, 5):
            issues.append(_issue(
                "info", "transition",
                f"Участок {k}: переход между сетями — признак «{SIGN_NAMES[signs[0]]}»", segment=k,
            ))
        plan.append({"segment": k, "a": a, "b": b, "xs": xs, "ys": ys, "signs": signs, "length_m": round(length, 2)})

    base = {
        "pipe_mode": pipe_mode,
        "fileid": ctx_fileid,
        "internalnodeid": ctx_inner,
        "segments": [
            {"segment": s["segment"], "signs": s["signs"], "length_m": s["length_m"],
             "sign_names": [SIGN_NAMES[x] for x in s["signs"]]}
            for s in plan
        ],
        "taps": [{"line_id": lid, "pair_line_id": pairs.get(lid)} for lid in tap_ids],
        "total_length_m": round(sum(s["length_m"] for s in plan), 2),
    }
    if any(i["level"] == "error" for i in issues):
        if dry_run:
            return {"ok": False, "issues": issues, **base}
        raise ChainValidationError(issues)

    # --- запись: врезки ------------------------------------------------------
    now = datetime.now()
    point_node: dict[int, int] = {}
    created_nodes: list[int] = []
    created_lines: list[int] = []
    split_lines: list[int] = []
    tap_report: list[dict] = []
    for i, p in enumerate(pts):
        if p["kind"] == "node":
            point_node[i] = p["node_id"]
        elif p["kind"] == "tap":
            lid = p["line_id"]
            t = taps[lid]
            await _capture_split(conn, op, lid)
            res = await _split_line_body(conn, lid, t["lng"], t["lat"], review_to_new=review.get(lid))
            _check_review(lid, res, review, dry_run, issues)
            point_node[i] = res["new_node_id"]
            # узел врезки — во фрагменте трубы (начальный узел бывает граничным, из соседнего фрагмента)
            await conn.execute(
                "UPDATE nodes SET fileid = $2, externalcodeid = COALESCE($3, externalcodeid) "
                "WHERE id = $1 AND fileid IS DISTINCT FROM $2",
                res["new_node_id"], ctx_fileid, code,
            )
            op.journal.created("nodes", res["new_node_id"])
            op.journal.created("linesobj", res["new_line_id"])
            await op.journal.created_where(conn, "heatpipesections", "_r.lineid = $1", res["new_line_id"])
            created_nodes.append(res["new_node_id"])
            split_lines.append(lid)
            entry = {"line_id": lid, "node_id": res["new_node_id"], "new_line_id": res["new_line_id"],
                     "transferred": res["transferred"]}
            pair_id = pairs.get(lid)
            if pair_id:
                await _capture_split(conn, op, pair_id)
                res2 = await _split_line_body(
                    conn, pair_id, t["lng"], t["lat"], review_to_new=review.get(pair_id),
                    at_node_id=res["new_node_id"],
                )
                _check_review(pair_id, res2, review, dry_run, issues)
                op.journal.created("linesobj", res2["new_line_id"])
                await op.journal.created_where(conn, "heatpipesections", "_r.lineid = $1", res2["new_line_id"])
                split_lines.append(pair_id)
                entry.update(pair_line_id=pair_id, pair_new_line_id=res2["new_line_id"],
                             pair_transferred=res2["transferred"])
            tap_report.append(entry)

    # --- новые узлы ----------------------------------------------------------
    for i, p in enumerate(pts):
        if p["kind"] != "new":
            continue
        new_id = await conn.fetchval(
            """
            INSERT INTO nodes (shape, x, y, removed, archivechangedate, nodetypeid,
                               fileid, externalcodeid, externalsignid, internalnodeid)
            VALUES (ST_SetSRID(ST_MakePoint($1, $2), 9998), $1 * 100.0, -$2 * 100.0, 0, $3, 1,
                    $4, $5, $6, $7)
            RETURNING id
            """,
            p["x"], p["y"], now, ctx_fileid, code, NODE_SIGN_BY_MODE[pipe_mode], ctx_inner,
        )
        op.journal.created("nodes", new_id)
        point_node[i] = new_id
        created_nodes.append(new_id)

    # --- участки -------------------------------------------------------------
    lines_report: list[dict] = []
    for s in plan:
        n1, n2 = point_node[s["a"]], point_node[s["b"]]
        for sign in s["signs"]:
            line_id = await conn.fetchval(
                f"""
                INSERT INTO linesobj (nodeid1, nodeid2, externalsignlineid, shape, removed,
                                      archivechangedate, fileid, internalnodeid)
                SELECT $3, $4, $5,
                       ST_SetPoint(ST_SetPoint({_SEGMENT_GEOM}, 0, n1.shape), -1, n2.shape),
                       0, $6, $7, $8
                FROM nodes n1, nodes n2 WHERE n1.id = $3 AND n2.id = $4
                RETURNING id
                """,
                s["xs"], s["ys"], n1, n2, sign, now, ctx_fileid, ctx_inner,
            )
            op.journal.created("linesobj", line_id)
            passport = await _create_line_passport(conn, line_id, n1, n2)
            await op.journal.created_where(conn, "heatpipesections", "_r.lineid = $1", line_id)
            length = await conn.fetchval(
                "SELECT round(ST_Length(shape)::numeric, 2)::float8 FROM linesobj WHERE id = $1", line_id,
            )
            created_lines.append(line_id)
            lines_report.append({
                "id": line_id, "segment": s["segment"], "nodeid1": n1, "nodeid2": n2,
                "sign": sign, "sign_name": SIGN_NAMES[sign], "length_m": length, "passport": passport,
            })

    result = {
        "ok": True,
        "issues": issues,
        **base,
        "taps": tap_report,
        "created_nodes": created_nodes,
        "created_lines": created_lines,
        "split_lines": split_lines,
        "lines": lines_report,
    }
    if created_lines:
        await op.audit("CHAIN", "linesobj", created_lines[0], {
            "pipe_mode": pipe_mode, "created_nodes": created_nodes, "created_lines": created_lines,
            "split_lines": split_lines, "total_length_m": base["total_length_m"],
        })
    return result


def _check_review(line_id: int, res: dict, review: dict, dry_run: bool, issues: list[dict]) -> None:
    """Оборудование без узла и позиции на разрезаемой трубе: решение оператора, как в split_line."""
    items = res["transferred"].get("review") or {}
    if not items or line_id in review:
        return
    detail = res["transferred"].get("review_items", items)
    if dry_run:
        issues.append(_issue(
            "warning", "review",
            f"На участке {line_id} есть оборудование без узла и позиции — по умолчанию оно останется "
            "на первой половине",
            line_id=line_id, items=detail,
        ))
        return
    raise TopologyDependencyError(
        "На участке есть оборудование без узла и позиции — укажите, на какую половину его отнести",
        blockers={"line_id": line_id, "review": detail, "requires_resolution": True},
    )


# ---------------------------------------------------------------------------
# Данные для привязки (точная геометрия окна карты)
# ---------------------------------------------------------------------------

async def snap_data(
    bbox: tuple[float, float, float, float],
    fragment_ids: Optional[list[int]] = None,
    limit: int = SNAP_LIMIT,
) -> dict:
    """Узлы и участки основной сети в окне карты — полная точность, WGS84.

    Векторные тайлы для привязки не годятся: координаты в них квантованы сеткой тайла и
    обрезаны по его краю. Окно больше SNAP_MAX_SIDE_M по стороне — too_large (клиент
    выключает привязку к трубам до приближения); больше limit объектов — truncated.
    """
    min_lng, min_lat, max_lng, max_lat = bbox
    if not (min_lng < max_lng and min_lat < max_lat):
        raise ValueError("bbox: minLng,minLat,maxLng,maxLat")
    fragments = list(fragment_ids or []) or None
    pool = get_pool()
    async with pool.acquire() as conn:
        size = await conn.fetchrow(
            "SELECT ST_XMax(e) - ST_XMin(e) AS w, ST_YMax(e) - ST_YMin(e) AS h "
            "FROM (SELECT ST_Transform(ST_MakeEnvelope($1, $2, $3, $4, 4326), 9998) AS e) s",
            min_lng, min_lat, max_lng, max_lat,
        )
        if max(float(size["w"]), float(size["h"])) > SNAP_MAX_SIDE_M:
            return {"too_large": True, "max_side_m": SNAP_MAX_SIDE_M, "nodes": [], "lines": [], "truncated": False}
        env = "ST_Transform(ST_MakeEnvelope($1, $2, $3, $4, 4326), 9998)"
        node_rows = await conn.fetch(
            f"""
            SELECT n.id, n.fileid, n.externalsignid,
                   ST_X(ST_Transform(n.shape, 4326)) AS lng, ST_Y(ST_Transform(n.shape, 4326)) AS lat
            FROM nodes n
            WHERE COALESCE(n.removed, 0) = 0 AND n.internalnodeid IS NULL AND n.shape IS NOT NULL
              AND n.shape && {env}
              AND ($5::int[] IS NULL OR n.fileid = ANY($5::int[]))
            ORDER BY n.id LIMIT $6
            """,
            min_lng, min_lat, max_lng, max_lat, fragments, limit + 1,
        )
        line_rows = await conn.fetch(
            f"""
            SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid, l.fileid,
                   EXISTS (SELECT 1 FROM heatpipesections h WHERE h.lineid = l.id) AS pipe,
                   ST_AsGeoJSON(ST_Transform(l.shape, 4326), 8) AS geojson
            FROM linesobj l
            WHERE COALESCE(l.removed, 0) = 0 AND l.internalnodeid IS NULL AND l.shape IS NOT NULL
              AND l.shape && {env}
              AND ($5::int[] IS NULL OR l.fileid = ANY($5::int[]))
            ORDER BY l.id LIMIT $6
            """,
            min_lng, min_lat, max_lng, max_lat, fragments, limit + 1,
        )
    truncated = len(node_rows) > limit or len(line_rows) > limit
    return {
        "too_large": False,
        "truncated": truncated,
        "nodes": [
            {"id": r["id"], "c": [round(r["lng"], 8), round(r["lat"], 8)], "f": r["fileid"], "s": r["externalsignid"]}
            for r in node_rows[:limit]
        ],
        "lines": [
            {"id": r["id"], "n1": r["nodeid1"], "n2": r["nodeid2"], "s": r["externalsignlineid"],
             "f": r["fileid"], "pipe": r["pipe"], "c": json.loads(r["geojson"])["coordinates"]}
            for r in line_rows[:limit]
            if r["geojson"]
        ],
    }
