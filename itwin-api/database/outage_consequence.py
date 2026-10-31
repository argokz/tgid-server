"""Последствия повреждения участка теплосети (фаза 5, шаг 3): кого отключит авария на каждом участке.

Для плана перекладок нужна не одна изоляция, а все сразу — по участку на запуск simulate_outage_isolation это
десятки тысяч обходов графа. Здесь — тот же результат (зона между задвижками + потребители ниже закрытых задвижек,
кольца учитываются) за один обход:

1. Сеть сжимается в «отсеки»: узлы без задвижек во внутренней схеме, связанные участками без задвижек, — один отсек
   (зона отключения любого его участка; участок между двумя камерами — отсек без узлов). Камеры (узлы с задвижками)
   и участки с задвижками — отдельные вершины графа отсеков; нормально закрытые участки не проводят.
2. Авария на участке отсека S = удаление вершины S. Ниже задвижек без питания остаются вершины, отделённые от
   источников, — для неориентированного графа это поддеревья обхода в глубину от общего источника, у которых
   low ≥ disc(S) (S — точка сочленения). Нагрузки поддеревьев копятся в том же обходе.
3. Участок с задвижкой на нём самом (зона — отсеки обоих концов) считается прямым обходом графа отсеков.

Потребители — включённые (consumerstateid = 1), как в изоляции; социальные — по названию потребителя (poi.classify):
школы, детсады, больницы, поликлиники, соцучреждения. Результат — оценка по топологии, как и изоляция
(гидравлика обходного питания не проверяется). Пересчёт — после изменения сети (кнопка в плане перекладок).
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from typing import Any

from database import poi
from database.outage_simulation import _Q_CONSUMERS, get_outage_network_graph

ROOT = -1                 # общий источник графа отсеков
MAX_VALVE_LINE_BFS = 500  # участки с задвижками считаются прямым обходом — их единицы
_ensured: set[str] = set()


class Loads:
    """Потребители, нагрузка и социальные объекты — по вершине графа."""
    __slots__ = ("consumers", "load", "social")

    def __init__(self) -> None:
        self.consumers = 0
        self.load = 0.0
        self.social = 0

    def add(self, other: "Loads") -> None:
        self.consumers += other.consumers
        self.load += other.load
        self.social += other.social


# --- граф отсеков (чистые функции над графом изоляции) ------------------------------------------

def compartments(net: dict[str, Any]) -> dict[str, Any]:
    """Вершины графа отсеков и связи. Вершина — ("s", корень отсека) | ("v", камера) | ("l", участок с задвижкой)."""
    valve_nodes = set(net["dampers_by_node"])
    valve_lines = set(net["dampers_by_line"])
    closed = set(net["normally_closed_lines"])
    line_info = net["line_info"]
    parent: dict[Any, Any] = {}

    def find(k: Any) -> Any:
        parent.setdefault(k, k)
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    def union(a: Any, b: Any) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for n in net["adj"]:
        if n not in valve_nodes:
            find(("n", n))
    for lid, info in line_info.items():
        if lid in valve_lines:
            continue
        ends = [("n", n) for n in (info["nodeid1"], info["nodeid2"]) if n not in valve_nodes]
        find(("ln", lid))
        for e in ends:
            union(("ln", lid), e)

    def vertex_of_node(n: int) -> tuple[str, Any]:
        return ("v", n) if n in valve_nodes else ("s", find(("n", n)))

    line_vertex: dict[int, tuple[str, Any]] = {}
    nodes_of: dict[Any, list[int]] = defaultdict(list)
    edges: dict[Any, set[Any]] = defaultdict(set)

    def link(a: Any, b: Any) -> None:
        if a != b:
            edges[a].add(b)
            edges[b].add(a)

    node_vertex: dict[int, tuple[str, Any]] = {}
    for n in net["adj"]:
        v = vertex_of_node(n)
        node_vertex[n] = v
        nodes_of[v].append(n)
        edges.setdefault(v, set())
    for lid, info in line_info.items():
        if lid in valve_lines:
            v = ("l", lid)
            line_vertex[lid] = v
            edges.setdefault(v, set())
            if lid in closed:
                continue
            for n in (info["nodeid1"], info["nodeid2"]):
                link(v, vertex_of_node(n))
            continue
        v = ("s", find(("ln", lid)))
        line_vertex[lid] = v
        edges.setdefault(v, set())
        for n in (info["nodeid1"], info["nodeid2"]):
            if n in valve_nodes:
                link(v, ("v", n))
    for s in net["sources"]:
        link(ROOT, vertex_of_node(s))
    return {"edges": edges, "line_vertex": line_vertex, "nodes_of": nodes_of, "node_vertex": node_vertex}


def articulation_losses(edges: dict[Any, set[Any]], loads: dict[Any, Loads]) -> tuple[dict[Any, Loads], set[Any]]:
    """Для каждой вершины — что теряет связь с ROOT при её удалении (без неё самой); и множество вершин, связанных с
    ROOT. Обход в глубину без рекурсии (сеть города — десятки тысяч вершин)."""
    disc: dict[Any, int] = {ROOT: 0}
    low: dict[Any, int] = {ROOT: 0}
    sub: dict[Any, Loads] = {ROOT: Loads()}
    lost: dict[Any, Loads] = defaultdict(Loads)
    stack: list[tuple[Any, Any, Any]] = [(ROOT, None, iter(edges.get(ROOT, ())))]
    counter = 1
    while stack:
        v, par, it = stack[-1]
        nxt = next(it, None)
        if nxt is not None:
            if nxt == par:
                continue
            if nxt in disc:
                low[v] = min(low[v], disc[nxt])
                continue
            disc[nxt] = low[nxt] = counter
            counter += 1
            sub[nxt] = Loads()
            sub[nxt].add(loads.get(nxt, Loads()))
            stack.append((nxt, v, iter(edges.get(nxt, ()))))
            continue
        stack.pop()
        if par is None:
            continue
        low[par] = min(low[par], low[v])
        sub[par].add(sub[v])
        if par != ROOT and low[v] >= disc[par]:
            lost[par].add(sub[v])
    return lost, set(disc) - {ROOT}


def lost_without(edges: dict[Any, set[Any]], removed: set[Any], reachable: set[Any]) -> set[Any]:
    """Вершины, связанные с ROOT до удаления и потерявшие связь после (прямой обход)."""
    seen = {ROOT}
    queue = [ROOT]
    while queue:
        v = queue.pop()
        for w in edges.get(v, ()):
            if w not in seen and w not in removed:
                seen.add(w)
                queue.append(w)
    return {v for v in reachable if v not in seen and v not in removed}


def line_consequences(net: dict[str, Any], node_loads: dict[int, Loads]) -> dict[int, dict[str, Any]]:
    """Последствия аварии на каждом участке графа: зона (отсек) и потребители ниже задвижек."""
    g = compartments(net)
    edges, line_vertex, nodes_of = g["edges"], g["line_vertex"], g["nodes_of"]
    loads: dict[Any, Loads] = {}
    for v, nodes in nodes_of.items():
        acc = Loads()
        for n in nodes:
            if n in node_loads:
                acc.add(node_loads[n])
        loads[v] = acc
    lost, reachable = articulation_losses(edges, loads)
    line_info = net["line_info"]
    out: dict[int, dict[str, Any]] = {}
    valve_line_runs = 0
    for lid, v in line_vertex.items():
        if v[0] == "l":
            if valve_line_runs >= MAX_VALVE_LINE_BFS:
                continue
            valve_line_runs += 1
            info = line_info[lid]
            # зона — сам участок и отсеки обоих концов; камера на конце — граница, не зона
            zone_v = {v} | {g["node_vertex"][n] for n in (info["nodeid1"], info["nodeid2"])
                            if g["node_vertex"][n][0] == "s"}
            zone, down = Loads(), Loads()
            for w in zone_v:
                zone.add(loads.get(w, Loads()))
            for w in lost_without(edges, zone_v, reachable):
                down.add(loads.get(w, Loads()))
        else:
            zone, down = loads.get(v, Loads()), lost.get(v, Loads())
        out[lid] = {"zone_consumers": zone.consumers, "zone_load": zone.load, "zone_social": zone.social,
                    "down_consumers": down.consumers, "down_load": down.load, "down_social": down.social}
    return out



# --- база ----------------------------------------------------------------------------------------

async def node_loads(conn, node_ids: list[int]) -> dict[int, Loads]:
    """Включённые потребители по узлам: число, нагрузка (Гкал/ч, как в изоляции), социальные — по названию."""
    out: dict[int, Loads] = {}
    for r in await conn.fetch(_Q_CONSUMERS, node_ids):
        acc = out.setdefault(r["nodeid"], Loads())
        acc.consumers += 1
        acc.load += float((r["heating_load"] or 0) + (r["ventilation_load"] or 0) + (r["hot_water_load"] or 0)
                          + (r["technology_load"] or 0))
        if poi.classify(r["name"]):
            acc.social += 1
    return out


async def refresh(conn, user: str = "system") -> dict[str, Any]:
    """Пересчитать последствия всех участков графа изоляции и записать в tgid_line_consequence."""
    t0 = time.monotonic()
    net = await get_outage_network_graph(conn, force_refresh=True)
    loads = await node_loads(conn, list(net["adj"]))
    result = line_consequences(net, loads)
    rows = [(lid, r["zone_consumers"], r["zone_load"], r["zone_social"], r["down_consumers"], r["down_load"],
             r["down_social"]) for lid, r in result.items()]
    with_down = sum(1 for r in result.values() if r["down_consumers"])
    report = {"lines": len(rows), "consumers": sum(x.consumers for x in loads.values()),
              "lines_with_consumers": sum(1 for r in result.values() if r["zone_consumers"] or r["down_consumers"]),
              "lines_with_downstream": with_down, "seconds": round(time.monotonic() - t0, 1)}
    async with conn.transaction():
        # два первых плана сразу (ensure) пишут по очереди, а не вперемешку
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext('tgid_line_consequence'))")
        await conn.execute("DELETE FROM tgid_line_consequence")
        await conn.copy_records_to_table(
            "tgid_line_consequence", records=rows,
            columns=["lineid", "zone_consumers", "zone_load", "zone_social", "down_consumers", "down_load",
                     "down_social"])
        run_id = await conn.fetchval(
            "INSERT INTO tgid_line_consequence_run (report, created_by) VALUES ($1::jsonb, $2) RETURNING id",
            json.dumps(report), user)
    return {"id": run_id, **report}


async def status(conn) -> dict[str, Any]:
    r = await conn.fetchrow("SELECT id, report, created_by, created_at FROM tgid_line_consequence_run "
                            "ORDER BY id DESC LIMIT 1")
    if r is None:
        return {"computed": False}
    return {"computed": True, "id": r["id"], **json.loads(r["report"]), "created_by": r["created_by"],
            "created_at": r["created_at"].isoformat()}


async def ensure(conn) -> None:
    """Последствия ещё не считались в этой базе — посчитать (первый план перекладок по отключениям). Раз на базу за
    процесс; дальше — пересчёт по кнопке."""
    db = await conn.fetchval("SELECT current_database()")
    if db in _ensured:
        return
    if await conn.fetchval("SELECT NOT EXISTS (SELECT 1 FROM tgid_line_consequence_run)"):
        await refresh(conn)
    _ensured.add(db)
