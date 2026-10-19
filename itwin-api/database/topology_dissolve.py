"""«Убрать узел, соединив трубы» и предпросмотры удаления (редактор сети, Del).

Узел между двумя участками (или между двумя парами П/О с общей трассой) убирается, а его участки
склеиваются в один: геометрия — подряд, длина — по земле, местные сопротивления паспортов складываются.
Как удаление вершины в QGIS / iD, но с правилами сети:
  - у узла нет карточки (потребитель, источник…), заданного напора, подпитки, внутренних узлов
    и ссылок из других таблиц;
  - на склеиваемых участках нет оборудования;
  - участки одного фрагмента и схемы, одного признака (подача/обратка/общий), диаметры паспортов равны.
Одна операция журнала DISSOLVE_NODE: Ctrl+Z возвращает узел и оба участка.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from database.node_types import node_cards
from database.outage_simulation import invalidate_outage_cache
from database.topology import (
    TopologyDependencyError,
    _capture_lines_with_passports,
    _lock_active,
    _run,
    _soft_remove_heatpipesections,
    find_pair_line,
    ground_length_sql,
)
from database.topology_transfer import line_dependency_report, node_dependency_report

NODE_TYPE_TITLES = {"PR": "потребитель", "PO": "обобщённый потребитель", "IS": "источник",
                    "HS": "насосная станция", "US2": "узел-камера"}


async def _incident(conn, node_id: int) -> list[dict]:
    rows = await conn.fetch(
        f"""
        SELECT l.id, l.nodeid1, l.nodeid2, l.fileid, l.internalnodeid, l.externalsignlineid AS sign,
               round({ground_length_sql("l.shape")}::numeric, 2)::float8 AS length_m,
               h.id AS passport_id, h.diameterinternal AS du
        FROM linesobj l
        LEFT JOIN heatpipesections h ON h.lineid = l.id
        WHERE (l.nodeid1 = $1 OR l.nodeid2 = $1) AND COALESCE(l.removed, 0) = 0
        ORDER BY l.id
        """,
        node_id,
    )
    out = []
    for r in rows:
        d = dict(r)
        d["other"] = r["nodeid2"] if r["nodeid1"] == node_id else r["nodeid1"]
        out.append(d)
    return out


async def dissolve_plan(conn, node_id: int) -> dict[str, Any]:
    """Можно ли убрать узел, соединив трубы: {ok, reasons, joins: [{keep, remove, length_m}]}."""
    reasons: list[str] = []
    lines = await _incident(conn, node_id)
    info = await node_cards(conn, node_id)
    if info["type"] not in ("US",):
        reasons.append(f"у узла карточка: {NODE_TYPE_TITLES.get(info['type'], info['type'])}")
    if any(info["flags"].values()):
        reasons.append("у узла заданный напор или подпитка")
    inner = await conn.fetchval("SELECT count(*) FROM nodes WHERE internalnodeid = $1 AND COALESCE(removed, 0) = 0",
                                node_id)
    if inner:
        reasons.append(f"во внутренней схеме узла {inner} узл.")
    refs = {k: v for k, v in (await node_dependency_report(conn, node_id)).items()
            if not k.lower().startswith(("realconsumers.", "generalizedconsumers.", "heatsources.", "pumpstations.",
                                         "setpressnodes.", "refillnodes."))}
    if refs:
        reasons.append("на узел ссылаются: " + ", ".join(f"{k} ({v})" for k, v in refs.items()))

    groups: dict[int, list[dict]] = {}
    for line in lines:
        groups.setdefault(line["other"], []).append(line)
    joins: list[dict] = []
    if any(o == node_id for o in groups):
        reasons.append("у узла участок-петля")
    elif len(groups) != 2:
        reasons.append(f"к узлу подходят {len(lines)} уч. — соединить можно только две трубы (или две пары П/О)")
    else:
        (a_other, a_lines), (b_other, b_lines) = groups.items()
        if len(a_lines) != len(b_lines) or len(a_lines) > 2:
            reasons.append("с разных сторон узла разное число труб")
        else:
            by_sign_b = {l["sign"]: l for l in b_lines}
            for a in a_lines:
                b = by_sign_b.get(a["sign"])
                if b is None:
                    reasons.append(f"у участка {a['id']} нет продолжения с тем же признаком (подача/обратка)")
                    continue
                if len(a_lines) == 2 and not await find_pair_line(conn, a["id"]):
                    reasons.append(f"участки {', '.join(str(x['id']) for x in a_lines)} — не пара П/О")
                if a["fileid"] != b["fileid"]:
                    reasons.append(f"участки {a['id']} и {b['id']} в разных фрагментах")
                if (a["internalnodeid"] or 0) != (b["internalnodeid"] or 0):
                    reasons.append(f"участки {a['id']} и {b['id']} в разных схемах")
                if a["du"] is not None and b["du"] is not None and abs(float(a["du"]) - float(b["du"])) > 1e-6:
                    reasons.append(f"разный диаметр: {a['id']} — {a['du']:g} мм, {b['id']} — {b['du']:g} мм")
                for line in (a, b):
                    eq = await line_dependency_report(conn, line["id"])
                    if eq:
                        reasons.append(f"на участке {line['id']} оборудование: " + ", ".join(f"{k} ({v})" for k, v in eq.items()))
                joins.append({"keep": a["id"], "remove": b["id"], "length_m": round((a["length_m"] or 0) + (b["length_m"] or 0), 2),
                              "sign": a["sign"]})
    return {"ok": not reasons and bool(joins), "reasons": reasons, "joins": joins,
            "lines": [{k: l[k] for k in ("id", "other", "sign", "length_m", "du")} for l in lines],
            "node_type": info["type"]}


async def _join(conn, node_id: int, keep: int, remove: int, now: datetime) -> float:
    """Склеить участок remove в keep через узел node_id; → новая длина keep."""
    a = await conn.fetchrow("SELECT id, nodeid1, nodeid2 FROM linesobj WHERE id = $1", keep)
    b = await conn.fetchrow("SELECT id, nodeid1, nodeid2 FROM linesobj WHERE id = $1", remove)
    b_other = b["nodeid2"] if b["nodeid1"] == node_id else b["nodeid1"]
    if a["nodeid2"] == node_id:
        # keep идёт к узлу: дальше — remove от узла
        geom = ("ST_RemoveRepeatedPoints(ST_MakeLine(a.shape, "
                "CASE WHEN b.nodeid1 = $3 THEN b.shape ELSE ST_Reverse(b.shape) END))")
        set_end = "nodeid2 = $4"
    else:
        # keep идёт от узла: впереди — remove к узлу
        geom = ("ST_RemoveRepeatedPoints(ST_MakeLine("
                "CASE WHEN b.nodeid2 = $3 THEN b.shape ELSE ST_Reverse(b.shape) END, a.shape))")
        set_end = "nodeid1 = $4"
    new_len = await conn.fetchval(
        f"""
        UPDATE linesobj AS a SET shape = {geom}, {set_end}, archivechangedate = $5
        FROM linesobj b WHERE a.id = $1 AND b.id = $2
        RETURNING round({ground_length_sql("a.shape")}::numeric, 2)::float8
        """,
        keep, remove, node_id, b_other, now,
    )
    # паспорт: длина, местные сопротивления складываются (mestn — «id|k|v» через пробел)
    await conn.execute(
        """
        UPDATE heatpipesections ha SET pipesectlength = $3,
               localressum = round((COALESCE(ha.localressum, 0) + COALESCE(hb.localressum, 0))::numeric, 4),
               mestn = COALESCE(NULLIF(trim(concat_ws(' ', NULLIF(trim(ha.mestn), ''), NULLIF(trim(hb.mestn), ''))), ''), ha.mestn)
        FROM heatpipesections hb WHERE ha.lineid = $1 AND hb.lineid = $2
        """,
        keep, remove, new_len,
    )
    await conn.execute("UPDATE heatpipesections SET pipesectlength = $2 WHERE lineid = $1 AND NOT EXISTS "
                       "(SELECT 1 FROM heatpipesections WHERE lineid = $3)", keep, new_len, remove)
    await conn.execute("UPDATE linesobj SET removed = 1, archivechangedate = $2 WHERE id = $1", remove, now)
    await _soft_remove_heatpipesections(conn, [remove], now)
    return float(new_len or 0)


async def dissolve_node(node_id: int, dry_run: bool = False, expected_version: Optional[str] = None,
                        actor: Optional[str] = None) -> dict:
    """Убрать узел, соединив его трубы; dry_run — план и причины, если нельзя."""

    async def body(conn, op):
        await _lock_active(conn, "node", [node_id], {node_id: expected_version})
        plan = await dissolve_plan(conn, node_id)
        if not plan["ok"]:
            if dry_run:
                return {"node_id": node_id, **plan}
            raise TopologyDependencyError("Узел нельзя убрать, соединив трубы: " + "; ".join(plan["reasons"]),
                                          blockers={"reasons": plan["reasons"]})
        ids = [x for j in plan["joins"] for x in (j["keep"], j["remove"])]
        await _lock_active(conn, "line", ids)
        await op.journal.capture_ids(conn, "nodes", [node_id])
        await _capture_lines_with_passports(conn, op, ids)
        now = datetime.now()
        joined = []
        for j in plan["joins"]:
            length = await _join(conn, node_id, j["keep"], j["remove"], now)
            joined.append({"line_id": j["keep"], "removed_line_id": j["remove"], "length_m": round(length, 2)})
        await conn.execute("UPDATE nodes SET removed = 1, archivechangedate = $2 WHERE id = $1", node_id, now)
        result = {"node_id": node_id, "ok": True, "joined": joined,
                  "line_id": joined[0]["line_id"], "removed_lines": [j["removed_line_id"] for j in joined]}
        await op.audit("DISSOLVE", "nodes", node_id, result)
        return result

    result = await _run(dry_run, body, "DISSOLVE_NODE", actor)
    if not dry_run:
        invalidate_outage_cache()
    return result


async def node_delete_preview(conn, node_id: int) -> dict:
    """Окно удаления узла: участки узла, ссылки на него и можно ли убрать его, соединив трубы."""
    exists = await conn.fetchval("SELECT 1 FROM nodes WHERE id = $1 AND COALESCE(removed, 0) = 0", node_id)
    if not exists:
        raise ValueError(f"Узел {node_id} не найден или удалён")
    plan = await dissolve_plan(conn, node_id)
    return {
        "node_id": node_id,
        "node_type": plan["node_type"],
        "lines": plan["lines"],
        "references": await node_dependency_report(conn, node_id),
        "dissolve": {"ok": plan["ok"], "reasons": plan["reasons"], "joins": plan["joins"]},
    }


async def line_delete_preview(conn, line_id: int) -> dict:
    """Окно удаления участка: паспорт, оборудование на нём, парная труба П/О."""
    row = await conn.fetchrow(
        f"""
        SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid AS sign,
               round({ground_length_sql("l.shape")}::numeric, 2)::float8 AS length_m,
               h.id AS passport_id, h.diameterinternal AS du
        FROM linesobj l LEFT JOIN heatpipesections h ON h.lineid = l.id
        WHERE l.id = $1 AND COALESCE(l.removed, 0) = 0
        """,
        line_id,
    )
    if row is None:
        raise ValueError(f"Участок {line_id} не найден или удалён")
    pair = await find_pair_line(conn, line_id)
    return {
        **dict(row),
        "equipment": await line_dependency_report(conn, line_id),
        "pair_line_id": pair["line_id"] if pair else None,
        "pair_equipment": await line_dependency_report(conn, pair["line_id"]) if pair else {},
    }
