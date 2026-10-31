"""Запись участка в журнал нарушений: нарушения без участка (defect.lineid) — к участку по месту.

Поиск — тот же, что в расчёте износа (database/wear.snap_defects): ближайший участок не дальше DEFECT_SNAP_M и его
копии с той же геометрией в других фрагментах (версии магистралей — одна труба). В журнал пишется одна копия:
фрагмент, к которому в журнале чаще всего привязывают нарушения (при равенстве — наименьший id участка).
Правило выбрано проверкой на 106 нарушениях Астаны с участком: совпадение с журналом 84 из 106; ближайший объект — 77,
наименьший / наибольший id или новейший фрагмент — 74–75 (та же труба с любой копией — 94).

Запись — одной операцией (журнал действий, change_group_id) только туда, где участок всё ещё пуст; отмена очищает
участок только у тех нарушений, где он не менялся после записи. Правка данных десктопа: в его журнале нарушений
участок появится тоже.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Optional

from database.wear import DEFECT_SNAP_M, _SNAP_SQL

# audit_log.operation в базах городов — varchar(10): длинное имя не записывается (уходит только в лог приложения),
# поэтому операция — UPDATE, а что сделано — в new_data.action
OPERATION = "UPDATE"
ACTION = "bind_lines"
UNDO_ACTION = "unbind_lines"


class BindingError(Exception):
    """Запись в журнал действий не легла — без неё отмена невозможна, операция откатывается."""


async def _audit(conn, user: str, data: dict[str, Any]) -> str:
    from audit import write_audit_log

    group = await write_audit_log(changed_by=user, operation=OPERATION, table_name="defect", conn=conn, new_data=data)
    if not await conn.fetchval("SELECT EXISTS (SELECT 1 FROM audit_log WHERE change_group_id::text = $1)", group):
        raise BindingError("Журнал действий не принял запись — участки не записаны (без записи нельзя отменить)")
    return group
PREVIEW_ROWS = 200


async def _fragment_frequency(conn) -> Counter:
    rows = await conn.fetch(
        """SELECT l.fileid, count(*) AS n FROM defect d JOIN linesobj l ON l.id = d.lineid
            WHERE l.fileid IS NOT NULL GROUP BY l.fileid""")
    return Counter({r["fileid"]: r["n"] for r in rows})


def choose(copies: list[dict[str, Any]], freq: Counter) -> dict[str, Any]:
    """Копия трубы для журнала: фрагмент, чаще всего встречающийся в журнале, затем наименьший id участка."""
    return max(copies, key=lambda c: (freq.get(c["fileid"], 0), -c["lineid"]))


async def preview(conn) -> dict[str, Any]:
    """Что будет записано: нарушение → участок, расстояние, сколько копий трубы; и что не привязывается."""
    unplaced = int(await conn.fetchval(
        "SELECT count(*) FROM defect WHERE lineid IS NULL AND shape IS NOT NULL") or 0)
    no_place = int(await conn.fetchval("SELECT count(*) FROM defect WHERE lineid IS NULL AND shape IS NULL") or 0)
    rows = await conn.fetch(_SNAP_SQL, None, DEFECT_SNAP_M) if unplaced else []
    freq = await _fragment_frequency(conn)
    by_defect: dict[int, list[dict[str, Any]]] = {}
    for r in rows:
        by_defect.setdefault(r["defect_id"], []).append(dict(r))
    names = {r["id"]: r["name"] for r in await conn.fetch(
        "SELECT id, name FROM fragments WHERE id = ANY($1::int[])", sorted({r["fileid"] for r in rows if r["fileid"]}))}
    items = []
    for defect_id, copies in sorted(by_defect.items()):
        pick = choose(copies, freq)
        items.append({"defect_id": defect_id, "line_id": pick["lineid"], "fileid": pick["fileid"],
                      "fragment": names.get(pick["fileid"]), "distance_m": round(pick["distance_m"], 1),
                      "copies": len(copies)})
    by_fragment = Counter(i["fragment"] or str(i["fileid"]) for i in items)
    return {
        "unplaced": unplaced, "without_place": no_place, "to_bind": len(items), "far": unplaced - len(items),
        "snap_m": DEFECT_SNAP_M, "with_copies": sum(1 for i in items if i["copies"] > 1),
        "by_fragment": dict(by_fragment.most_common(10)),
        "rule": "ближайший участок не дальше 20 м; из копий трубы в версиях фрагментов — фрагмент, к которому в "
                "журнале чаще всего привязывают нарушения",
        "items": items,
    }


async def apply(conn, user: str, exclude: Optional[set[int]] = None) -> dict[str, Any]:
    """Пересчитать предпросмотр и записать участки (только где lineid ещё пуст) одной операцией;
    exclude — нарушения, которые пользователь снял; вернуть change_group_id для отмены."""
    plan = await preview(conn)
    pairs = [(i["defect_id"], i["line_id"]) for i in plan["items"] if i["defect_id"] not in (exclude or set())]
    async with conn.transaction():
        rows = await conn.fetch(
            """UPDATE defect d SET lineid = q.line_id
                 FROM unnest($1::int[], $2::int[]) AS q(defect_id, line_id)
                WHERE d.id = q.defect_id AND d.lineid IS NULL
                  AND EXISTS (SELECT 1 FROM linesobj l WHERE l.id = q.line_id AND coalesce(l.removed, 0) = 0)
            RETURNING d.id, d.lineid""",
            [p[0] for p in pairs], [p[1] for p in pairs])
        bound = [[r["id"], r["lineid"]] for r in rows]
        if not bound:
            return {"bound": 0, "skipped": len(pairs), "far": plan["far"], "change_group_id": None}
        group = await _audit(conn, user, {"action": ACTION, "count": len(bound), "items": bound})
    return {"bound": len(bound), "skipped": len(pairs) - len(bound), "far": plan["far"], "change_group_id": group}


async def undo(conn, change_group_id: str, user: str) -> Optional[dict[str, Any]]:
    """Отменить запись: очистить участок у нарушений операции, если он не менялся после неё."""
    data = await conn.fetchval(
        """SELECT new_data FROM audit_log WHERE change_group_id::text = $1 AND table_name = 'defect'
            ORDER BY log_id LIMIT 1""", change_group_id)
    record = (json.loads(data) if isinstance(data, str) else data) if data is not None else None
    if not record or record.get("action") != ACTION:
        return None
    items = record.get("items", [])
    async with conn.transaction():
        rows = await conn.fetch(
            """UPDATE defect d SET lineid = NULL
                 FROM unnest($1::int[], $2::int[]) AS q(defect_id, line_id)
                WHERE d.id = q.defect_id AND d.lineid = q.line_id
            RETURNING d.id""",
            [i[0] for i in items], [i[1] for i in items])
        await _audit(conn, user, {"action": UNDO_ACTION, "undo_of": change_group_id, "count": len(rows)})
    return {"unbound": len(rows), "changed_since": len(items) - len(rows)}
