"""Правила связности сети и проверка области правки (фаза 1, «грязная область»).

Диагностика фрагмента (database/topology_diagnostics.py) проверяет весь фрагмент по запросу.
Здесь — те же инварианты плюс правила связности, но только для области одной правки: узлы и
участки операции из журнала topology_undo_log, концы её участков и всё, что к ним примыкает.
Веб вызывает проверку после каждой операции редактора и показывает замечания сразу, пока
правку ещё можно отменить. Ничего не пишет и правку не запрещает: десктоп gid8 правит ту же
базу без этих правил, поэтому они — предупреждения, а не ограничения схемы.

Правила (severity: error — sety не рассчитает или считает неверно, warning — подозрительно):
  * dangling_line, zero_length_line, duplicate_line, cross_fragment_line, orphaned_node,
    geometry_mismatch — как в диагностике фрагмента;
  * node_type_conflict — узел сразу в нескольких таблицах типа (потребитель, обобщённый
    потребитель, источник, насосная): в gid8 тип узла один (cxema1.cpp nodef), sety возьмёт
    любую из карточек;
  * unsnapped_end — тупиковый конец ближе допуска к другому узлу или участку того же фрагмента:
    трубу довели до сети, но не привязали (фрагменты-копии лежат друг на друге, поэтому только
    свой фрагмент);
  * no_supply — узел магистральной сети не достижим от питающих точек (источник, заданный
    напор) с учётом закрытых задвижек: граф outage_simulation, кэш которого сбрасывает каждая
    операция топологии.

Правило «пара подающий/обратный» сознательно не включено: в Алматы у подающей и обратной сетей
разные узлы, без пары между теми же узлами 35,8 тыс. участков с признаком 2/3 — это норма данных.
"""

from __future__ import annotations

import json
from typing import Any, Iterable, Optional

from database.outage_simulation import get_outage_network_graph
from database.topology_diagnostics import FAULT_TYPES, GEOMETRY_TOLERANCE_M, _attach_fault_coords
from database.topology_history import _ids
from database.topology_journal import JOURNAL_TABLE, journal_available, table_columns
from database.topology_transfer import _ident

AREA_LIMIT = 500
SNAP_TOLERANCE_M = GEOMETRY_TOLERANCE_M

RULES: dict[str, dict[str, str]] = {
    "dangling_line": {"title": FAULT_TYPES["dangling_line"], "severity": "error"},
    "zero_length_line": {"title": FAULT_TYPES["zero_length_line"], "severity": "error"},
    "node_type_conflict": {
        "title": "Узел одновременно в нескольких типах (потребитель, источник, насосная)",
        "severity": "error",
    },
    "duplicate_line": {"title": FAULT_TYPES["duplicate_line"], "severity": "warning"},
    "unsnapped_end": {
        "title": f"Конец трубы ближе {SNAP_TOLERANCE_M:g} м к сети, но не привязан к ней",
        "severity": "warning",
    },
    "orphaned_node": {"title": FAULT_TYPES["orphaned_node"], "severity": "warning"},
    "cross_fragment_line": {"title": FAULT_TYPES["cross_fragment_line"], "severity": "warning"},
    "geometry_mismatch": {"title": FAULT_TYPES["geometry_mismatch"], "severity": "warning"},
    "no_supply": {
        "title": "Узлы без питания: нет пути от источника или узла заданного напора",
        "severity": "warning",
    },
}

# Таблицы типа узла (gid8: PR, PO, IS, HS); connectNodes (US2) — связь, а не карточка
_NODE_TYPE_TABLES = {
    "realconsumers": "потребитель",
    "generalizedconsumers": "обобщённый потребитель",
    "heatsources": "источник",
    "pumpstations": "насосная",
}
_OBJECT_TABLES = (*_NODE_TYPE_TABLES, "setpressnodes")


def _nodes_word(n: int) -> str:
    """«1 узел», «2 узла», «5 узлов»."""
    if n % 10 == 1 and n % 100 != 11:
        return "узел"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "узла"
    return "узлов"


def _int_ids(values: Iterable[Any]) -> set[int]:
    out: set[int] = set()
    for v in values:
        if isinstance(v, (int, float)) or (isinstance(v, str) and v.isdigit()):
            out.add(int(v))
    return out


async def operation_area(conn, operation_id: int) -> Optional[tuple[set[int], set[int]]]:
    """Узлы и участки операции журнала (до и после неё). None — журнала или операции нет."""
    if not await journal_available(conn):
        return None
    row = await conn.fetchrow(
        f"SELECT summary, before_rows, after_hashes FROM {JOURNAL_TABLE} WHERE id = $1", operation_id)
    if row is None:
        return None

    def load(v: Any) -> Any:
        return json.loads(v) if isinstance(v, str) else v

    summary = load(row["summary"]) or {}
    before = load(row["before_rows"]) or []
    after = load(row["after_hashes"]) or {}

    nodes = set(_ids(summary, "node_id", "target_node_id", "source_node_id", "new_node_id",
                     "created_nodes", "updated_nodes"))
    lines = set(_ids(summary, "line_id", "pair_line_id", "new_line_id", "created_lines",
                     "removed_lines", "split_lines"))
    created: dict[str, list[int]] = {}
    for item in before:
        table, rid, img = item.get("t"), item.get("id"), item.get("row")
        if table is None or rid is None:
            continue
        if table == "nodes":
            nodes.add(int(rid))
        elif table == "linesobj":
            lines.add(int(rid))
        if img is None:
            created.setdefault(table, []).append(int(rid))
            continue
        # образ «до»: концы снятого участка, узел/участок карточки
        nodes |= _int_ids(img.get(k) for k in ("nodeid", "nodeid1", "nodeid2"))
        lines |= _int_ids([img.get("lineid")])
    for k in after:
        table, _, rid = str(k).rpartition(":")
        if rid.isdigit() and table == "nodes":
            nodes.add(int(rid))
        elif rid.isdigit() and table == "linesobj":
            lines.add(int(rid))
    # созданные строки карточек — по их текущему узлу/участку
    for table, ids in created.items():
        if table in ("nodes", "linesobj"):
            continue
        cols = set(await table_columns(conn, table))
        for col, bucket in (("nodeid", nodes), ("lineid", lines)):
            if col in cols:
                bucket |= _int_ids(r[0] for r in await conn.fetch(
                    f"SELECT {col} FROM {_ident(table)} WHERE id = ANY($1::int[])", ids))
    return nodes, lines


async def check_area(conn, node_ids: Iterable[int], line_ids: Iterable[int]) -> dict[str, Any]:
    """Правила связности для узлов и участков правки и всего, что к ним примыкает."""
    seed_nodes = sorted(set(node_ids))
    seed_lines = sorted(set(line_ids))
    truncated = len(seed_nodes) > AREA_LIMIT or len(seed_lines) > AREA_LIMIT
    seed_nodes, seed_lines = seed_nodes[:AREA_LIMIT], seed_lines[:AREA_LIMIT]

    # концы участков правки, в том числе снятых
    for r in await conn.fetch(
            "SELECT nodeid1, nodeid2 FROM linesobj WHERE id = ANY($1::int[])", seed_lines):
        seed_nodes += [n for n in (r["nodeid1"], r["nodeid2"]) if n is not None]

    nodes = {r["id"]: r for r in await conn.fetch(
        """SELECT id, fileid, internalnodeid, shape IS NOT NULL AS has_shape FROM nodes
            WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0""", sorted(set(seed_nodes)))}
    area = sorted(nodes)
    lines = await conn.fetch(
        """SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid,
                  n1.id IS NOT NULL AS n1_exists, COALESCE(n1.removed, 0) <> 0 AS n1_removed, n1.fileid AS n1_fileid,
                  n2.id IS NOT NULL AS n2_exists, COALESCE(n2.removed, 0) <> 0 AS n2_removed, n2.fileid AS n2_fileid
             FROM linesobj l
             LEFT JOIN nodes n1 ON n1.id = l.nodeid1
             LEFT JOIN nodes n2 ON n2.id = l.nodeid2
            WHERE COALESCE(l.removed, 0) = 0
              AND (l.id = ANY($1::int[]) OR l.nodeid1 = ANY($2::int[]) OR l.nodeid2 = ANY($2::int[]))
            ORDER BY l.id""",
        seed_lines, area,
    )
    found: dict[str, list[dict]] = {t: [] for t in RULES}

    degree: dict[int, int] = {}
    neighbours: dict[int, set[int]] = {}
    pairs: dict[tuple, list[int]] = {}
    for r in lines:
        n1, n2 = r["nodeid1"], r["nodeid2"]
        live1 = bool(r["n1_exists"]) and not r["n1_removed"]
        live2 = bool(r["n2_exists"]) and not r["n2_removed"]
        if not (live1 and live2):
            bad = []
            for end, exists, removed in ((n1, r["n1_exists"], r["n1_removed"]), (n2, r["n2_exists"], r["n2_removed"])):
                if end is None:
                    bad.append("конец не задан")
                elif not exists:
                    bad.append(f"узел {end} не существует")
                elif removed:
                    bad.append(f"узел {end} снят")
            found["dangling_line"].append({
                "object_type": "line", "object_id": r["id"],
                "description": f"Участок {n1}–{n2}: " + "; ".join(bad),
                "related_ids": [n for n in (n1, n2) if n is not None],
            })
        for end, other, live in ((n1, n2, live1), (n2, n1, live2)):
            if live and end is not None:
                degree[end] = degree.get(end, 0) + 1
                if other is not None:
                    neighbours.setdefault(end, set()).add(other)
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
            pairs.setdefault((min(n1, n2), max(n1, n2), r["externalsignlineid"]), []).append(r["id"])
    for (a, b, _sign), ids in pairs.items():
        for dup in ids[1:]:
            found["duplicate_line"].append({
                "object_type": "line", "object_id": dup,
                "description": f"Повторяет участок {ids[0]} между узлами {a} и {b}",
                "related_ids": [ids[0], a, b],
            })

    kinds: dict[int, list[str]] = {}
    union = " UNION ALL ".join(
        f"SELECT DISTINCT nodeid, '{t}' AS t FROM {_ident(t)} WHERE nodeid = ANY($1::int[])" for t in _OBJECT_TABLES)
    for r in await conn.fetch(union, area):
        kinds.setdefault(r["nodeid"], []).append(r["t"])
    for nid in area:
        types = [_NODE_TYPE_TABLES[t] for t in kinds.get(nid, []) if t in _NODE_TYPE_TABLES]
        if len(types) > 1:
            found["node_type_conflict"].append({
                "object_type": "node", "object_id": nid,
                "description": "Карточки: " + ", ".join(sorted(types)),
            })

    connected = {r["n"] for r in await conn.fetch(
        """SELECT nodeid AS n FROM connectnodes WHERE nodeid = ANY($1::int[]) OR connectid = ANY($1::int[])
           UNION SELECT connectid FROM connectnodes WHERE nodeid = ANY($1::int[]) OR connectid = ANY($1::int[])
           UNION SELECT internalnodeid FROM nodes
                  WHERE internalnodeid = ANY($1::int[]) AND COALESCE(removed, 0) = 0""", area)}
    dead_ends: list[int] = []
    for nid in area:
        deg = degree.get(nid, 0)
        if nid in connected:
            continue
        if deg == 0:
            found["orphaned_node"].append({
                "object_type": "node", "object_id": nid, "description": "Нет участков и связей",
            })
        elif deg == 1 and nid not in kinds and not nodes[nid]["internalnodeid"] and nodes[nid]["has_shape"]:
            dead_ends.append(nid)
    await _unsnapped_ends(conn, dead_ends, neighbours, found["unsnapped_end"])

    for r in await conn.fetch(
            """SELECT l.id FROM linesobj l
                 JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.shape IS NOT NULL
                 JOIN nodes n2 ON n2.id = l.nodeid2 AND n2.shape IS NOT NULL
                WHERE l.id = ANY($1::int[]) AND l.shape IS NOT NULL
                  AND GeometryType(ST_LineMerge(l.shape)) = 'LINESTRING'
                  AND LEAST(
                        GREATEST(ST_Distance(ST_StartPoint(ST_LineMerge(l.shape)), n1.shape),
                                 ST_Distance(ST_EndPoint(ST_LineMerge(l.shape)), n2.shape)),
                        GREATEST(ST_Distance(ST_StartPoint(ST_LineMerge(l.shape)), n2.shape),
                                 ST_Distance(ST_EndPoint(ST_LineMerge(l.shape)), n1.shape))
                      ) > $2
                ORDER BY l.id""",
            [r["id"] for r in lines], GEOMETRY_TOLERANCE_M):
        found["geometry_mismatch"].append({
            "object_type": "line", "object_id": r["id"],
            "description": f"Концы линии не совпадают с узлами (допуск {GEOMETRY_TOLERANCE_M:g} м)",
        })

    await _no_supply(conn, area, found["no_supply"])

    issues: list[dict] = []
    for t, rule in RULES.items():
        for item in found[t]:
            issues.append({"type": t, "title": rule["title"], "severity": rule["severity"], **item})
    await _attach_fault_coords(conn, issues)
    counts = {t: len(found[t]) for t in RULES}
    return {
        "area": {"nodes": len(area), "lines": len(lines)},
        "truncated": truncated,
        "counts": counts,
        "total": len(issues),
        "errors": sum(1 for i in issues if i["severity"] == "error"),
        "rules": RULES,
        "issues": issues,
    }


async def _unsnapped_ends(conn, dead_ends: list[int], neighbours: dict[int, set[int]], out: list[dict]) -> None:
    """Тупиковый конец рядом с чужим узлом или участком своего фрагмента — не привязан."""
    if not dead_ends:
        return
    near_nodes = await conn.fetch(
        """SELECT a.id AS a, o.id AS o, ST_Distance(o.shape, a.shape) AS d
             FROM nodes a JOIN nodes o
               ON o.id <> a.id AND COALESCE(o.removed, 0) = 0 AND o.shape IS NOT NULL
              AND o.fileid IS NOT DISTINCT FROM a.fileid AND ST_DWithin(o.shape, a.shape, $2)
            WHERE a.id = ANY($1::int[])
            ORDER BY a.id, d""", dead_ends, SNAP_TOLERANCE_M)
    near_lines = await conn.fetch(
        """SELECT a.id AS a, l.id AS l, l.nodeid1, l.nodeid2, ST_Distance(l.shape, a.shape) AS d
             FROM nodes a JOIN linesobj l
               ON COALESCE(l.removed, 0) = 0 AND l.shape IS NOT NULL AND l.internalnodeid IS NULL
              AND l.nodeid1 IS DISTINCT FROM a.id AND l.nodeid2 IS DISTINCT FROM a.id
              AND ST_DWithin(l.shape, a.shape, $2)
             LEFT JOIN nodes ln ON ln.id = l.nodeid1
            WHERE a.id = ANY($1::int[]) AND COALESCE(l.fileid, ln.fileid) IS NOT DISTINCT FROM a.fileid
            ORDER BY a.id, d""", dead_ends, SNAP_TOLERANCE_M)
    hits: dict[int, dict] = {}
    for r in near_nodes:
        own = neighbours.get(r["a"], set())
        if r["o"] in own or r["a"] in hits:
            continue
        hits[r["a"]] = {"related_ids": [r["o"]], "description": f"Узел {r['o']} в {r['d']:.2f} м"}
    for r in near_lines:
        own = neighbours.get(r["a"], set())
        # трубы соседнего узла тоже рядом с коротким участком — это не ошибка привязки
        if r["a"] in hits or r["nodeid1"] in own or r["nodeid2"] in own:
            continue
        hits[r["a"]] = {"related_ids": [r["l"]], "description": f"Участок {r['l']} в {r['d']:.2f} м: нужна врезка"}
    for nid in dead_ends:
        if nid in hits:
            out.append({"object_type": "node", "object_id": nid, **hits[nid]})


async def _no_supply(conn, area: list[int], out: list[dict]) -> None:
    """Острова без питания, в которые попала область правки (одно замечание на остров)."""
    net = await get_outage_network_graph(conn)
    adj, reachable = net["adj"], net["baseline_reachable"]
    seen: set[int] = set()
    for nid in area:
        if nid not in adj or nid in reachable or nid in seen:
            continue
        island = {nid}
        stack = [nid]
        while stack:
            for _lid, nxt in adj.get(stack.pop(), ()):
                if nxt not in island and nxt not in reachable:
                    island.add(nxt)
                    stack.append(nxt)
        seen |= island
        out.append({
            "object_type": "node", "object_id": nid,
            "description": f"Часть сети без питания: {len(island)} {_nodes_word(len(island))} (узел {nid} и связанные с ним)",
            "component_size": len(island),
        })
