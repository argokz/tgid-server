"""Диагностика топологии фрагмента (GET /api/v1/topology/diagnostics, QA F35).

Отдельной проверки топологии у десктопа нет: gid8 ограничивается выделением изолированной
части сети от узла, а sety молча считает только связные части, в которых есть узел с
заданным давлением. Проверки ниже — инварианты целостности, которыми пользуется
golden-приёмка редактора (scripts/golden/topology_acceptance.py), и то, что мешает расчёту.

Фрагмент определяется как у sety (read_gid.read_line2): узлы с nodes.fileid = фрагменту,
участки — живые linesobj, у которых хотя бы один конец в этих узлах (linesobj.fileid
ненадёжен: на копии 2002 участка с fileid=74 соединяют узлы фрагмента 99).

Связь узла с сетью, кроме участков: connectnodes (nodeid/connectid) и internalnodeid —
вход в схему потребителя; к узлу могут быть привязаны источник, потребитель, насосная или
заданное давление (setPressNodes — точка питания районной сети от магистрального фрагмента).
"""

from __future__ import annotations

from typing import Any, Optional

from database.regime_queries import attach_coords

# Порядок — по важности для расчёта
FAULT_TYPES: dict[str, str] = {
    "dangling_line": "Участок ссылается на снятый или несуществующий узел",
    "zero_length_line": "Начальный и конечный узлы участка совпадают",
    "duplicate_line": "Повторяющийся участок: та же пара узлов и тот же признак трубопровода",
    "cross_fragment_line": "Концы участка в разных фрагментах",
    "orphaned_node": "Узел не связан с сетью: нет участков, связей connectNodes и ссылок internalNodeID",
    "no_source_component": "Связная часть сети без источника тепла и узла с заданным давлением: sety её не рассчитает",
    "dangling_node": "Тупиковый узел: один участок, нет источника, потребителя, насосной и внутренней схемы",
    "geometry_mismatch": "Концы геометрии участка дальше 1 м от его узлов",
}

GEOMETRY_TOLERANCE_M = 1.0

# Живые узлы фрагмента ($1 — fragment_id)
_FRAG_NODES = "(SELECT id FROM nodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0)"

_LINES_SQL = f"""
    SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid,
           n1.id IS NOT NULL AS n1_exists, COALESCE(n1.removed, 0) <> 0 AS n1_removed, n1.fileid AS n1_fileid,
           n2.id IS NOT NULL AS n2_exists, COALESCE(n2.removed, 0) <> 0 AS n2_removed, n2.fileid AS n2_fileid
      FROM linesobj l
      LEFT JOIN nodes n1 ON n1.id = l.nodeid1
      LEFT JOIN nodes n2 ON n2.id = l.nodeid2
     WHERE COALESCE(l.removed, 0) = 0
       AND (l.nodeid1 IN {_FRAG_NODES} OR l.nodeid2 IN {_FRAG_NODES})
"""


class _DSU:
    def __init__(self) -> None:
        self.parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


async def get_topology_diagnostics(conn, fragment_id: int, limit: int = 200) -> Optional[dict[str, Any]]:
    """Проблемы топологии фрагмента. counts — полные числа, faults — не больше limit на тип.

    None — фрагмента нет (или он снят)."""
    frag = await conn.fetchrow(
        "SELECT id, name FROM fragments WHERE id = $1 AND COALESCE(removed, 0) = 0", fragment_id)
    if frag is None:
        return None

    found: dict[str, list[dict]] = {t: [] for t in FAULT_TYPES}

    nodes = await conn.fetch(
        "SELECT id, internalnodeid FROM nodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0", fragment_id)
    lines = await conn.fetch(_LINES_SQL, fragment_id)
    connect = await conn.fetch(
        f"""SELECT nodeid, connectid FROM connectnodes
            WHERE nodeid IN {_FRAG_NODES} OR connectid IN {_FRAG_NODES}""", fragment_id)
    internal_refs = {r["internalnodeid"] for r in await conn.fetch(
        f"""SELECT internalnodeid FROM nodes
            WHERE COALESCE(removed, 0) = 0 AND internalnodeid IN {_FRAG_NODES}""", fragment_id)}
    objects = {r["nodeid"]: r["kind"] for r in await conn.fetch(
        f"""SELECT nodeid, 'heat_source' AS kind FROM heatsources WHERE nodeid IN {_FRAG_NODES}
           UNION ALL SELECT nodeid, 'consumer' FROM realconsumers WHERE nodeid IN {_FRAG_NODES}
           UNION ALL SELECT nodeid, 'consumer' FROM generalizedconsumers WHERE nodeid IN {_FRAG_NODES}
           UNION ALL SELECT nodeid, 'pump_station' FROM pumpstations WHERE nodeid IN {_FRAG_NODES}
           UNION ALL SELECT nodeid, 'set_pressure' FROM setpressnodes WHERE nodeid IN {_FRAG_NODES}""", fragment_id)}
    # sety считает связную часть, если в ней есть узел с заданным давлением (find_zn): источник
    # или узел setPressNodes (давления из магистрального фрагмента — районные сети)
    feed_nodes = {nid for nid, kind in objects.items() if kind in ("heat_source", "set_pressure")}
    geometry_bad = await conn.fetch(
        f"""SELECT l.id FROM linesobj l
             JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.shape IS NOT NULL
             JOIN nodes n2 ON n2.id = l.nodeid2 AND n2.shape IS NOT NULL
            WHERE COALESCE(l.removed, 0) = 0 AND l.shape IS NOT NULL
              AND (l.nodeid1 IN {_FRAG_NODES} OR l.nodeid2 IN {_FRAG_NODES})
              AND GeometryType(ST_LineMerge(l.shape)) = 'LINESTRING'
              AND LEAST(
                    GREATEST(ST_Distance(ST_StartPoint(ST_LineMerge(l.shape)), n1.shape),
                             ST_Distance(ST_EndPoint(ST_LineMerge(l.shape)), n2.shape)),
                    GREATEST(ST_Distance(ST_StartPoint(ST_LineMerge(l.shape)), n2.shape),
                             ST_Distance(ST_EndPoint(ST_LineMerge(l.shape)), n1.shape))
                  ) > $2
            ORDER BY l.id""",
        fragment_id, GEOMETRY_TOLERANCE_M,
    )

    node_ids = {r["id"] for r in nodes}
    has_internal = {r["id"] for r in nodes if r["internalnodeid"]}
    degree: dict[int, int] = {}
    dsu = _DSU()
    pairs: dict[tuple, list[int]] = {}
    linked_outside: set[int] = set()  # узлы фрагмента, связанные с узлами вне его

    for r in lines:
        n1, n2 = r["nodeid1"], r["nodeid2"]
        live1 = r["n1_exists"] and not r["n1_removed"]
        live2 = r["n2_exists"] and not r["n2_removed"]
        if not (live1 and live2):
            bad = []
            for end, exists, removed in ((n1, r["n1_exists"], r["n1_removed"]), (n2, r["n2_exists"], r["n2_removed"])):
                if not exists:
                    bad.append(f"узел {end} не существует")
                elif removed:
                    bad.append(f"узел {end} снят (removed)")
            found["dangling_line"].append({
                "object_type": "line", "object_id": r["id"],
                "description": f"Участок {n1}–{n2}: " + "; ".join(bad),
                "related_ids": [n for n in (n1, n2) if n is not None],
            })
        for end, live in ((n1, live1), (n2, live2)):
            if live and end is not None:
                degree[end] = degree.get(end, 0) + 1
        if n1 is not None and n1 == n2:
            found["zero_length_line"].append({
                "object_type": "line", "object_id": r["id"],
                "description": f"Участок замкнут на узел {n1}", "related_ids": [n1],
            })
            continue
        if live1 and live2:
            if r["n1_fileid"] != r["n2_fileid"]:
                found["cross_fragment_line"].append({
                    "object_type": "line", "object_id": r["id"],
                    "description": f"Узел {n1} во фрагменте {r['n1_fileid']}, узел {n2} — во фрагменте {r['n2_fileid']}",
                    "related_ids": [n1, n2],
                })
            if n1 in node_ids and n2 in node_ids:
                dsu.union(n1, n2)
            else:
                linked_outside.update(n for n in (n1, n2) if n in node_ids)
            key = (min(n1, n2), max(n1, n2), r["externalsignlineid"])
            pairs.setdefault(key, []).append(r["id"])

    # признак может быть NULL — сортируем по первому участку, а не по ключу
    for (a, b, _sign), ids in sorted(pairs.items(), key=lambda kv: kv[1][0]):
        if len(ids) > 1:
            for dup in ids[1:]:
                found["duplicate_line"].append({
                    "object_type": "line", "object_id": dup,
                    "description": f"Повторяет участок {ids[0]} между узлами {a} и {b}",
                    "related_ids": [ids[0], a, b],
                })

    connected = set(internal_refs)
    for r in connect:
        for nid in (r["nodeid"], r["connectid"]):
            if nid is not None:
                connected.add(nid)
        if r["nodeid"] in node_ids and r["connectid"] in node_ids:
            dsu.union(r["nodeid"], r["connectid"])
        else:
            linked_outside.update(n for n in (r["nodeid"], r["connectid"]) if n in node_ids)
    for r in nodes:
        if r["internalnodeid"] in node_ids:
            dsu.union(r["id"], r["internalnodeid"])

    for nid in sorted(node_ids):
        deg = degree.get(nid, 0)
        if deg == 0 and nid not in connected:
            kind = objects.get(nid)
            suffix = {"heat_source": " (источник тепла)", "consumer": " (потребитель)",
                      "pump_station": " (насосная станция)", "set_pressure": " (узел с заданным давлением)"}.get(kind, "")
            found["orphaned_node"].append({
                "object_type": "node", "object_id": nid,
                "description": f"Нет участков и связей{suffix}",
            })
        elif deg == 1 and nid not in connected and nid not in objects and nid not in has_internal:
            found["dangling_node"].append({
                "object_type": "node", "object_id": nid,
                "description": "Один участок, к узлу ничего не подключено",
            })

    components: dict[int, list[int]] = {}
    for nid in node_ids:
        if nid in dsu.parent:
            components.setdefault(dsu.find(nid), []).append(nid)
    for root, members in sorted(components.items()):
        # связь с другим фрагментом — питание может прийти оттуда, не судим
        if len(members) > 1 and not (feed_nodes | linked_outside).intersection(members):
            found["no_source_component"].append({
                "object_type": "node", "object_id": min(members),
                "description": f"{len(members)} узлов без источника и заданного давления (узел {min(members)} и связанные с ним)",
                "component_size": len(members),
            })

    for r in geometry_bad:
        found["geometry_mismatch"].append({
            "object_type": "line", "object_id": r["id"],
            "description": f"Концы линии не совпадают с узлами (допуск {GEOMETRY_TOLERANCE_M:g} м)",
        })

    counts = {t: len(found[t]) for t in FAULT_TYPES}
    faults: list[dict] = []
    for t in FAULT_TYPES:
        for item in found[t][:limit]:
            faults.append({"type": t, "title": FAULT_TYPES[t], **item})
    await _attach_fault_coords(conn, faults)
    return {
        "fragment_id": fragment_id,
        "fragment_name": frag["name"],
        "nodes": len(node_ids),
        "lines": len(lines),
        "counts": counts,
        "total": sum(counts.values()),
        "limit": limit,
        "truncated": any(n > limit for n in counts.values()),
        "types": FAULT_TYPES,
        "faults": faults,
    }


async def _attach_fault_coords(conn, faults: list[dict]) -> None:
    """lat/lng: узел — точка узла; участок — середина линии, иначе живой конец участка."""
    nodes = [{"node_id": f["object_id"]} for f in faults if f["object_type"] == "node"]
    lines = [{"line_id": f["object_id"]} for f in faults if f["object_type"] == "line"]
    await attach_coords(conn, nodes, key="node_id")
    await attach_coords(conn, lines, key="line_id")
    by_node = {i["node_id"]: i for i in nodes}
    by_line = {i["line_id"]: i for i in lines}
    fallback = [{"node_id": nid, "fault": f} for f in faults if f["object_type"] == "line"
                and by_line[f["object_id"]].get("latitude") is None for nid in f.get("related_ids", [])]
    await attach_coords(conn, fallback, key="node_id")
    for f in faults:
        src = (by_node if f["object_type"] == "node" else by_line)[f["object_id"]]
        f["lat"], f["lng"] = src.get("latitude"), src.get("longitude")
    for item in fallback:
        f = item["fault"]
        if f["lat"] is None and item.get("latitude") is not None:
            f["lat"], f["lng"] = item["latitude"], item["longitude"]
