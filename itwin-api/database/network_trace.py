"""Трассировки сети по топологии (фаза 1 модернизации, по образцу трассировок ArcGIS Utility Network).

Граф — тот же, что у локализации отключений (``outage_simulation.get_outage_network_graph``):
магистральные участки без отключённых труб, источники — ``heatsources.nodeid``.
Закрытые задвижки (``damperarmaturestateid = 2``) воду не проводят и всегда служат барьером.

Типы трассировки:

- ``connected`` — всё, что связано с начальными точками по проводящим участкам;
- ``upstream`` — путь к источникам: узлы и участки, лежащие хотя бы на одном простом пути
  от источника к начальной точке (кольца дают несколько путей — берутся все);
- ``downstream`` — что останется без связи с источниками, если вывести начальные элементы;

Источник здесь — любая питающая точка графа: ``heatsources`` и узлы заданного напора
(``setpressnodes``), через которые квартальные сети берут воду из магистрали.
- ``subnetwork`` — зона (подсеть), в которую входит начальная точка, и её источники.

Дополнительно пользователь задаёт барьеры (участки, узлы) и барьеры по условию (``stop_at``,
у трассировок «связанные» и «зона»): объект-барьер попадает в результат, но дальше обход не идёт.

- ``valves`` — задвижки: участок с задвижкой и узел с задвижками во внутренней схеме
  (прежний флаг ``stop_at_valves``);
- ``pumpstations`` — узлы насосных станций (в т. ч. ЦТП, заведённые насосными);
- ``setpress`` — узлы заданного напора (вход квартальной сети из магистрали);
- ``sources`` — источники тепла.

Набор «тип + барьеры по условию» сохраняется как именованная настройка (database/trace_configs.py).

Это оценка по связности: направление потока и достаточность напора не учитываются
(``model = topology``), направление «вверх/вниз» задают источники. Схему базы модуль не меняет.
"""

from __future__ import annotations

import json
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

import asyncpg
import networkx as nx

from database.outage_simulation import (
    _consumer_features,
    _consumers,
    get_outage_network_graph,
    reachable_from_sources,
)

TRACE_TYPES = ("connected", "upstream", "downstream", "subnetwork")
# Барьеры по условию (stop_at) и трассировки, к которым они применяются
STOP_KINDS = ("valves", "pumpstations", "setpress", "sources")
STOP_TRACE_TYPES = ("connected", "subnetwork")
_STOP_NODE_SQL = {
    "pumpstations": "SELECT nodeid FROM pumpstations WHERE nodeid IS NOT NULL",
    "setpress": "SELECT nodeid FROM setpressnodes WHERE nodeid IS NOT NULL",
    "sources": "SELECT nodeid FROM heatsources WHERE nodeid IS NOT NULL",
}

# Больше этого геометрия участков не отдаётся (только id): карта всё равно не покажет
# сотню тысяч объектов GeoJSON-ом, а ответ раздувается до десятков мегабайт.
MAX_GEOJSON_LINES = 20_000
MAX_LISTED_CONSUMERS = 2_000

Adjacency = dict[int, list[tuple[int, int]]]


@dataclass(frozen=True)
class TraceResult:
    nodes: frozenset[int]
    lines: frozenset[int]
    sources: frozenset[int] = frozenset()
    stopped_at: frozenset[int] = field(default_factory=frozenset)  # узлы, где обход остановлен


def _conducts(lid: int, other: int, blocked_lines: set[int], removed_nodes: set[int]) -> bool:
    return lid not in blocked_lines and other not in removed_nodes


def trace_connected(
    adj: Adjacency,
    start_nodes: Iterable[int],
    *,
    blocked_lines: set[int] = frozenset(),
    removed_nodes: set[int] = frozenset(),
    stop_lines: set[int] = frozenset(),
    stop_nodes: set[int] = frozenset(),
) -> TraceResult:
    """Связанные элементы. ``stop_*`` попадают в результат, но обход через них не идёт."""
    seen = {n for n in start_nodes if n not in removed_nodes}
    lines: set[int] = set()
    stopped: set[int] = set()
    queue = [n for n in seen if n not in stop_nodes]
    stopped.update(n for n in seen if n in stop_nodes)
    while queue:
        node = queue.pop()
        for lid, other in adj.get(node, ()):
            if not _conducts(lid, other, blocked_lines, removed_nodes):
                continue
            lines.add(lid)
            if lid in stop_lines:
                stopped.add(node)
                continue
            if other in seen:
                continue
            seen.add(other)
            if other in stop_nodes:
                stopped.add(other)
                continue
            queue.append(other)
    return TraceResult(nodes=frozenset(seen), lines=frozenset(lines), stopped_at=frozenset(stopped))


def _simple_graph(adj: Adjacency, blocked_lines: set[int], removed_nodes: set[int]) -> nx.Graph:
    """Граф без параллельных рёбер и петель — для блоков (компонент двусвязности)."""
    g = nx.Graph()
    for node, edges in adj.items():
        if node in removed_nodes:
            continue
        g.add_node(node)
        for lid, other in edges:
            if other != node and _conducts(lid, other, blocked_lines, removed_nodes):
                g.add_edge(node, other)
    return g


@dataclass(frozen=True)
class BlockTree:
    """Дерево блоков и точек сочленения: простые пути между двумя узлами проходят ровно по блокам
    на пути между ними в этом дереве, и каждый узел такого блока лежит на одном из этих путей."""

    blocks: tuple[frozenset[int], ...]
    tree: nx.Graph
    cut_vertices: frozenset[int]
    node_block: dict[int, int]
    bridges: frozenset[frozenset[int]]

    @classmethod
    def build(cls, g: nx.Graph) -> "BlockTree":
        blocks = tuple(frozenset(b) for b in nx.biconnected_components(g))
        cut = frozenset(nx.articulation_points(g))
        tree = nx.Graph()
        node_block: dict[int, int] = {}
        for i, block in enumerate(blocks):
            tree.add_node(("B", i))
            for v in block:
                node_block.setdefault(v, i)
                if v in cut:
                    tree.add_edge(("B", i), ("C", v))
        bridges = frozenset(b for b in blocks if len(b) == 2)
        return cls(blocks=blocks, tree=tree, cut_vertices=cut, node_block=node_block, bridges=bridges)

    def _vertex(self, v: int) -> tuple[str, int] | None:
        if v in self.cut_vertices:
            return ("C", v)
        block = self.node_block.get(v)
        return None if block is None else ("B", block)

    def is_bridge(self, a: int, b: int) -> bool:
        """Ребро a–b — мост (блок из двух узлов): без него концы оказываются в разных частях сети."""
        return frozenset((a, b)) in self.bridges

    def nodes_on_paths(self, a: int, b: int) -> set[int]:
        """Все узлы, лежащие хотя бы на одном простом пути a → b (пусто, если пути нет)."""
        return self.paths_to_many(a, [b]).get(b, set())

    def paths_to_many(self, a: int, targets: Iterable[int]) -> dict[int, set[int]]:
        """Для каждой достижимой цели — узлы на простых путях a → цель. Один обход дерева от a."""
        va = self._vertex(a)
        wanted = {t: self._vertex(t) for t in targets}
        out: dict[int, set[int]] = {t: {a} for t in wanted if t == a}
        if va is None:
            return out
        parent = {va: None}
        queue = deque([va])
        while queue:
            cur = queue.popleft()
            for nxt in self.tree.neighbors(cur):
                if nxt not in parent:
                    parent[nxt] = cur
                    queue.append(nxt)
        for t, vt in wanted.items():
            if t == a or vt is None or vt not in parent:
                continue
            nodes = {a, t}
            step = vt
            while step is not None:
                kind, ref = step
                if kind == "B":
                    nodes |= self.blocks[ref]
                else:
                    nodes.add(ref)
                step = parent[step]
            out[t] = nodes
        return out


def _lines_within(adj: Adjacency, nodes: set[int], blocked_lines: set[int]) -> set[int]:
    return {lid for n in nodes for lid, other in adj.get(n, ()) if other in nodes and lid not in blocked_lines}


def trace_upstream(
    adj: Adjacency,
    sources: set[int],
    start_nodes: Iterable[int],
    *,
    blocked_lines: set[int] = frozenset(),
    removed_nodes: set[int] = frozenset(),
    block_tree: BlockTree | None = None,
) -> TraceResult:
    """Узлы и участки на путях от источников к начальным узлам (с учётом колец)."""
    tree = block_tree or BlockTree.build(_simple_graph(adj, blocked_lines, removed_nodes))
    nodes: set[int] = set()
    reached: set[int] = set()
    live_sources = [s for s in sources if s not in removed_nodes]
    for start in start_nodes:
        nodes.add(start)
        for src, on_paths in tree.paths_to_many(start, live_sources).items():
            nodes |= on_paths
            reached.add(src)
    return TraceResult(nodes=frozenset(nodes), lines=frozenset(_lines_within(adj, nodes, blocked_lines)),
                       sources=frozenset(reached))


def upstream_of_line(
    adj: Adjacency,
    sources: set[int],
    line: tuple[int, int, int],
    *,
    blocked_lines: set[int] = frozenset(),
    removed_nodes: set[int] = frozenset(),
    block_tree: BlockTree | None = None,
) -> TraceResult:
    """Путь к источникам от участка: со стороны того конца, что ближе к источнику.

    На тупиковой ветке путь к дальнему концу проходит через сам участок и захватывает дальний узел —
    берём только ближний конец. В кольце к обоим концам есть пути в обход — объединяем оба.
    """
    lid, n1, n2 = line
    tree = block_tree or BlockTree.build(_simple_graph(adj, blocked_lines, removed_nodes))
    per_end = {n: trace_upstream(adj, sources, [n], blocked_lines=blocked_lines,
                                 removed_nodes=removed_nodes, block_tree=tree) for n in (n1, n2)}
    near = [n1, n2]
    if tree.is_bridge(n1, n2):
        near = [n for n, other in ((n1, n2), (n2, n1)) if other not in per_end[n].nodes] or near
    nodes = set().union(*(per_end[n].nodes for n in near))
    srcs = set().union(*(per_end[n].sources for n in near))
    lines = _lines_within(adj, nodes, blocked_lines) | {lid}
    return TraceResult(nodes=frozenset(nodes | {n1, n2}), lines=frozenset(lines), sources=frozenset(srcs))


def trace_downstream(
    adj: Adjacency,
    sources: set[int],
    *,
    start_nodes: set[int] = frozenset(),
    start_lines: set[int] = frozenset(),
    blocked_lines: set[int] = frozenset(),
    removed_nodes: set[int] = frozenset(),
) -> TraceResult:
    """Что теряет связь с источниками, если вывести начальные узлы и участки."""
    before = reachable_from_sources(adj, sources, blocked_lines=blocked_lines, removed_nodes=removed_nodes)
    after = reachable_from_sources(adj, sources, blocked_lines=blocked_lines | start_lines,
                                   removed_nodes=removed_nodes | start_nodes)
    lost = {n for n in before if n not in after and n not in start_nodes}
    lines = {lid for n in lost for lid, other in adj.get(n, ())
             if lid not in blocked_lines and other not in removed_nodes}
    return TraceResult(nodes=frozenset(lost | (start_nodes & before)),
                       lines=frozenset(lines | start_lines))


def subnetworks(
    adj: Adjacency,
    sources: set[int],
    *,
    blocked_lines: set[int] = frozenset(),
) -> list[TraceResult]:
    """Компоненты связности сети (зоны). Зона без источника — «остров», признак ошибки данных
    или участка, отключённого задвижками. Порядок — по убыванию числа узлов."""
    seen: set[int] = set()
    zones: list[TraceResult] = []
    for node in adj:
        if node in seen:
            continue
        zone = trace_connected(adj, [node], blocked_lines=blocked_lines)
        seen |= zone.nodes
        zones.append(TraceResult(nodes=zone.nodes, lines=zone.lines, sources=frozenset(zone.nodes & sources)))
    zones.sort(key=lambda z: len(z.nodes), reverse=True)
    return zones


# --- обращение к базе -------------------------------------------------------------------------

def _base_block_tree(net: dict[str, Any]) -> BlockTree:
    """Дерево блоков без пользовательских барьеров живёт вместе с кешем графа (60 с)."""
    tree = net.get("_block_tree")
    if tree is None:
        tree = BlockTree.build(_simple_graph(net["adj"], set(net["normally_closed_lines"]), set()))
        net["_block_tree"] = tree
    return tree


def _sources_out(net: dict[str, Any], nodes: Iterable[int],
                 names: Optional[dict[int, str]] = None) -> list[dict[str, Any]]:
    """Питающие точки с видом: heat_source — источник, set_pressure — узел заданного напора; name — если есть."""
    kinds = net.get("source_kinds", {})
    out = []
    for n in sorted(nodes):
        item: dict[str, Any] = {"node_id": n, "kind": kinds.get(n, "heat_source")}
        if names and names.get(n):
            item["name"] = names[n]
        out.append(item)
    return out


async def _source_names(conn: asyncpg.Connection, nodes: Iterable[int]) -> dict[int, str]:
    """Название питающей точки: источник (heatsources) или имя узла — чтобы ответ можно было прочитать."""
    ids = sorted(nodes)
    if not ids:
        return {}
    rows = await conn.fetch(
        """SELECT n.id, coalesce(nullif(hs.name, ''), nullif(hs.sourcename, ''), nullif(n.externalnodename, '')) AS name
             FROM nodes n LEFT JOIN heatsources hs ON hs.nodeid = n.id
            WHERE n.id = ANY($1::int[])""", ids)
    return {r["id"]: r["name"] for r in rows if r["name"]}


async def stop_barriers(conn: asyncpg.Connection, net: dict[str, Any],
                        stop_at: Iterable[str]) -> tuple[set[int], set[int]]:
    """Барьеры по условию → (участки, узлы), где обход останавливается."""
    kinds = set(stop_at)
    unknown = kinds - set(STOP_KINDS)
    if unknown:
        raise ValueError(f"Неизвестный барьер: {', '.join(sorted(unknown))}")
    lines: set[int] = set(net["dampers_by_line"]) if "valves" in kinds else set()
    nodes: set[int] = set(net["dampers_by_node"]) if "valves" in kinds else set()
    for kind in sorted(kinds & set(_STOP_NODE_SQL)):
        nodes |= {r["nodeid"] for r in await conn.fetch(_STOP_NODE_SQL[kind])}
    return lines, nodes


def _check_ids(kind: str, ids: Iterable[int], known: Iterable[int] | dict) -> None:
    missing = [i for i in ids if i not in known]
    if missing:
        sample = ", ".join(str(i) for i in missing[:10])
        raise ValueError(f"{kind} не входят в расчётную схему (удалены, отключены или без топологии): {sample}")


async def run_trace(
    conn: asyncpg.Connection,
    *,
    trace_type: str,
    start_line_ids: list[int],
    start_node_ids: list[int],
    barrier_line_ids: list[int] | None = None,
    barrier_node_ids: list[int] | None = None,
    stop_at_valves: bool = False,
    stop_at: Iterable[str] = (),
    include_geometry: bool = True,
) -> dict[str, Any]:
    if trace_type not in TRACE_TYPES:
        raise ValueError(f"Неизвестный тип трассировки: {trace_type}")
    stop_kinds = set(stop_at) | ({"valves"} if stop_at_valves else set())
    if not start_line_ids and not start_node_ids:
        raise ValueError("Укажите хотя бы одну начальную точку: участок или узел.")

    net = await get_outage_network_graph(conn)
    adj: Adjacency = net["adj"]
    line_info: dict[int, dict[str, Any]] = net["line_info"]
    sources: set[int] = set(net["sources"])
    _check_ids("Участки", start_line_ids, line_info)
    _check_ids("Узлы", start_node_ids, adj)

    user_lines = set(barrier_line_ids or ())
    user_nodes = set(barrier_node_ids or ())
    blocked = set(net["normally_closed_lines"]) | user_lines
    starts = set(start_node_ids)
    for lid in start_line_ids:
        starts |= {line_info[lid]["nodeid1"], line_info[lid]["nodeid2"]}

    stop_lines, stop_nodes = await stop_barriers(conn, net, stop_kinds if trace_type in STOP_TRACE_TYPES else ())
    if trace_type == "connected":
        res = trace_connected(adj, starts, blocked_lines=blocked, removed_nodes=user_nodes,
                              stop_lines=stop_lines, stop_nodes=stop_nodes - starts)
        res = TraceResult(nodes=res.nodes, lines=res.lines | set(start_line_ids),
                          sources=frozenset(res.nodes & sources), stopped_at=res.stopped_at)
    elif trace_type == "upstream":
        tree = _base_block_tree(net) if not user_lines and not user_nodes else None
        if tree is None:
            tree = BlockTree.build(_simple_graph(adj, blocked, user_nodes))
        parts = [trace_upstream(adj, sources, start_node_ids, blocked_lines=blocked,
                                removed_nodes=user_nodes, block_tree=tree)]
        for lid in start_line_ids:
            info = line_info[lid]
            parts.append(upstream_of_line(adj, sources, (lid, info["nodeid1"], info["nodeid2"]),
                                          blocked_lines=blocked, removed_nodes=user_nodes, block_tree=tree))
        res = TraceResult(nodes=frozenset().union(*(p.nodes for p in parts)),
                          lines=frozenset().union(*(p.lines for p in parts)),
                          sources=frozenset().union(*(p.sources for p in parts)))
    elif trace_type == "downstream":
        res = trace_downstream(adj, sources, start_nodes=set(start_node_ids), start_lines=set(start_line_ids),
                               blocked_lines=blocked, removed_nodes=user_nodes)
    else:  # subnetwork
        zone = trace_connected(adj, starts, blocked_lines=blocked, removed_nodes=user_nodes,
                               stop_lines=stop_lines, stop_nodes=stop_nodes - starts)
        res = TraceResult(nodes=zone.nodes, lines=zone.lines | set(start_line_ids),
                          sources=frozenset(zone.nodes & sources), stopped_at=zone.stopped_at)

    return await _trace_response(conn, net, trace_type, res, include_geometry=include_geometry,
                                 start={"line_ids": start_line_ids, "node_ids": start_node_ids})


async def _trace_response(
    conn: asyncpg.Connection,
    net: dict[str, Any],
    trace_type: str,
    res: TraceResult,
    *,
    include_geometry: bool,
    start: dict[str, list[int]],
) -> dict[str, Any]:
    line_info = net["line_info"]
    length_m = 0.0
    volume_m3 = 0.0
    for lid in res.lines:
        info = line_info.get(lid)
        if not info:
            continue
        mult = 2.0 if info["externalsignlineid"] == 1 else 1.0
        length_m += info["length"] * mult
        volume_m3 += (math.pi / 4.0) * ((info["diameter_internal"] / 1000.0) ** 2) * info["length"] * mult

    valves = [v for lid in res.lines for v in net["dampers_by_line"].get(lid, ())]
    valves += [v for n in res.nodes for v in net["dampers_by_node"].get(n, ())]

    # Путь к источнику — это не зона потребления: потребители на нём не «отключаются»
    consumers = [] if trace_type == "upstream" else await _consumers(conn, set(res.nodes))
    load = sum(c["total_load"] for c in consumers)

    truncated = len(res.lines) > MAX_GEOJSON_LINES
    line_features: list[dict[str, Any]] = []
    if include_geometry and res.lines and not truncated:
        rows = await conn.fetch(
            "SELECT id, ST_AsGeoJSON(ST_Transform(shape, 4326)) AS g FROM linesobj "
            "WHERE id = ANY($1::int[]) AND shape IS NOT NULL", list(res.lines))
        line_features = [{"type": "Feature", "geometry": json.loads(r["g"]),
                          "properties": {"id": r["id"], "trace": trace_type}} for r in rows if r["g"]]

    return {
        "success": True,
        "trace_type": trace_type,
        "model": "topology",
        "start": start,
        "summary": {
            "nodes_count": len(res.nodes),
            "lines_count": len(res.lines),
            "sources_count": len(res.sources),
            "valves_count": len(valves),
            "consumers_count": len(consumers),
            "total_load_gcal_h": round(load, 4),
            "total_pipe_length_m": round(length_m, 2),
            "total_pipe_volume_m3": round(volume_m3, 2),
            "stopped_at_count": len(res.stopped_at),
        },
        "source_node_ids": sorted(res.sources),
        "sources": _sources_out(net, res.sources, await _source_names(conn, res.sources)),
        "node_ids": sorted(res.nodes),
        "line_ids": sorted(res.lines),
        "stopped_at_node_ids": sorted(res.stopped_at),
        "valves": sorted(({k: v[k] for k in ("id", "lineid", "owner_node_id", "display_name", "state_name",
                                              "lng", "lat")} for v in valves), key=lambda v: v["id"]),
        "consumers": consumers[:MAX_LISTED_CONSUMERS],
        "consumers_truncated": len(consumers) > MAX_LISTED_CONSUMERS,
        "geometry_truncated": truncated,
        "geojson": {
            "lines": {"type": "FeatureCollection", "features": line_features},
            "consumers": {"type": "FeatureCollection",
                          "features": _consumer_features(consumers[:MAX_LISTED_CONSUMERS]) if include_geometry else []},
        },
    }


async def list_subnetworks(conn: asyncpg.Connection, *, min_nodes: int = 1) -> dict[str, Any]:
    """Сводка зон сети: источники, размер, «острова» без источника (кандидаты на проверку данных)."""
    net = await get_outage_network_graph(conn)
    zones = subnetworks(net["adj"], set(net["sources"]), blocked_lines=set(net["normally_closed_lines"]))
    out = []
    for i, zone in enumerate(zones, start=1):
        if len(zone.nodes) < min_nodes:
            continue
        out.append({
            "zone": i,
            "nodes_count": len(zone.nodes),
            "lines_count": len(zone.lines),
            "source_node_ids": sorted(zone.sources),
            "sources": _sources_out(net, zone.sources),
            "has_source": bool(zone.sources),
            # любой узел зоны годится как начальная точка трассировки «subnetwork»
            "sample_node_id": min(zone.nodes),
        })
    islands = [z for z in out if not z["has_source"]]
    return {
        "success": True,
        "model": "topology",
        "zones_count": len(out),
        "zones_with_source": len(out) - len(islands),
        "islands_count": len(islands),
        "islands_nodes_count": sum(z["nodes_count"] for z in islands),
        "zones": out,
    }
