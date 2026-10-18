"""Окно свойств: правка нескольких участков (или объектов в узлах) одной карточкой.

Узлы (kind="node") — одна колонка, строки nodes выбора; потребители, обобщённые потребители,
источники и насосные (consumer/genconsumer/source/pumpstation) — выбор тоже по id узла, строки
своей таблицы с этим nodeid; дальше — как у участков.

Выбор — участки (linesobj.id). Пары П/О дополняются (как карточка одного участка, db.line_pair_ids):
колонка «Подача» — участки с признаком не «обратный», «Обратка» — обратные. Карточка — та же, что у
одного участка (поля, списки, функции, правила), но значения сведены по колонке: одинаковые —
значение, разные — «разные» (mixed). Поля узлов (N1/N2) и вкладки расчёта не показываются.

Изменение — значение поля для всех строк колонки. Предпросмотр: сколько строк изменится и какие
значения были. Применение — одна транзакция, строки audit_log с общей группой и итог GROUP_SET
(setter="card_edit"); отмена — общая с групповыми установщиками (/api/v1/group-setters/undo).
"""

from __future__ import annotations

import json
import uuid
from collections import Counter
from typing import Any, Optional

from database import card_edit as ce
from database import typed_edit as te
from database.sql_ident import quote_ident, resolve_column, resolve_table
from utils.ini import storage

SETTER = "card_edit"
MAX_LINES = 5000
COLUMN_TITLES = ["Подача", "Обратка"]
# Вид объектов → таблица карточки → колонка, по которой строки относятся к объекту выбора
KIND_KEYS: dict[str, dict[str, str]] = {
    "line": {"heatpipesections": "lineid", "linesobj": "id"},
    "node": {"nodes": "id"},
    "consumer": {"realconsumers": "nodeid"},
    "genconsumer": {"generalizedconsumers": "nodeid"},
    "source": {"heatsources": "nodeid"},
    "pumpstation": {"pumpstations": "nodeid"},
}
LINE_KEY = KIND_KEYS["line"]
KIND_LABEL = {"line": "Свойства участков", "node": "Свойства узлов", "consumer": "Свойства потребителей",
              "genconsumer": "Свойства обобщённых потребителей", "source": "Свойства источников",
              "pumpstation": "Свойства насосных станций"}
# таблица строки-итога GROUP_SET / GROUP_UNDO
KIND_TABLE = {"line": "heatpipesections", "node": "nodes", "consumer": "realconsumers",
              "genconsumer": "generalizedconsumers", "source": "heatsources", "pumpstation": "pumpstations"}
# объекты в узле: «Среди выбранных узлов нет …»
OWNER_NOUN = {"consumer": "потребителей", "genconsumer": "обобщённых потребителей", "source": "источников",
              "pumpstation": "насосных станций"}

_EXPAND_SQL = """
WITH sel AS (SELECT l.id, l.nodeid1, l.nodeid2, l.externalsignlineid AS sign
               FROM linesobj l WHERE l.id = ANY($1::int[]) AND l.removed = 0)
SELECT id, sign FROM sel
UNION
SELECT b.id, b.externalsignlineid
  FROM sel a
  JOIN linesobj b ON b.nodeid1 = a.nodeid1 AND b.nodeid2 = a.nodeid2 AND b.id <> a.id AND b.removed = 0
   AND b.externalsignlineid = CASE a.sign WHEN 2 THEN 3 WHEN 3 THEN 2 END
 WHERE EXISTS (SELECT 1 FROM heatpipesections t WHERE t.lineid = b.id)
"""


def _err(status: int, code: str, message: str, **extra) -> te.TypedEditError:
    return te.TypedEditError(status, {"code": code, "message": message, **extra})


async def line_columns(conn, ids: list[int]) -> list[list[int]]:
    """Участки выбора с парами П/О → колонки [[подача и одиночные], [обратка]] (пустая — убирается)."""
    ids = sorted({int(i) for i in ids if int(i) > 0})
    if not ids:
        raise _err(422, "no_objects", "Не выбраны участки")
    if len(ids) > MAX_LINES:
        raise _err(422, "too_many", f"Не более {MAX_LINES} участков за операцию")
    rows = await conn.fetch(_EXPAND_SQL, ids)
    if not rows:
        raise _err(404, "not_found", "Выбранные участки не найдены")
    flow = sorted(int(r["id"]) for r in rows if r["sign"] != 3)
    ret = sorted(int(r["id"]) for r in rows if r["sign"] == 3)
    return [c for c in (flow, ret) if c]


async def node_columns(conn, ids: list[int]) -> list[list[int]]:
    """Узлы выбора (не удалённые) → одна колонка."""
    ids = sorted({int(i) for i in ids if int(i) > 0})
    if not ids:
        raise _err(422, "no_objects", "Не выбраны узлы")
    if len(ids) > MAX_LINES:
        raise _err(422, "too_many", f"Не более {MAX_LINES} узлов за операцию")
    found = sorted(int(r["id"]) for r in await conn.fetch(
        "SELECT id FROM nodes WHERE id = ANY($1::int[]) AND COALESCE(removed, 0) = 0", ids))
    if not found:
        raise _err(404, "not_found", "Выбранные узлы не найдены")
    return [found]


async def owner_columns(conn, kind: str, ids: list[int]) -> list[list[int]]:
    """Узлы выбора, в которых есть объект вида (строка таблицы с этим nodeid) → одна колонка."""
    ids = sorted({int(i) for i in ids if int(i) > 0})
    if not ids:
        raise _err(422, "no_objects", "Не выбраны объекты")
    if len(ids) > MAX_LINES:
        raise _err(422, "too_many", f"Не более {MAX_LINES} объектов за операцию")
    table, key = next(iter(KIND_KEYS[kind].items()))
    actual = await resolve_table(conn, table)
    found = sorted(int(r["nodeid"]) for r in await conn.fetch(
        f"SELECT DISTINCT t.{quote_ident(key)} AS nodeid FROM {quote_ident(actual)} t "
        "JOIN nodes n ON n.id = t." + quote_ident(key) + " "
        f"WHERE t.{quote_ident(key)} = ANY($1::int[]) AND COALESCE(n.removed, 0) = 0", ids))
    if not found:
        raise _err(404, "not_found", f"Среди выбранных узлов нет {OWNER_NOUN[kind]}")
    return [found]


async def object_columns(conn, kind: str, ids: list[int]) -> list[list[int]]:
    if kind == "node":
        return await node_columns(conn, ids)
    if kind in OWNER_NOUN:
        return await owner_columns(conn, kind, ids)
    if kind == "line":
        return await line_columns(conn, ids)
    raise _err(422, "bad_kind", f"Вид объектов «{kind}» не поддерживается")


async def _table_rows(conn, table: str, line_ids: list[int], cols: list[str], kind: str = "line") -> list[dict]:
    actual = await resolve_table(conn, table)
    key = KIND_KEYS[kind][table]
    sel = ", ".join(quote_ident(c) for c in cols) or "1"
    return [dict(r) for r in await conn.fetch(
        f"SELECT id AS __id, {sel} FROM {quote_ident(actual)} WHERE {quote_ident(key)} = ANY($1::int[])",
        line_ids)]


async def value_title(conn, table: str, field: str, value: Any) -> Any:
    """Подпись значения списка, как в карточке (встроенный список или имя в справочнике)."""
    if value is None:
        return None
    lookup = storage.get_lookup(table, field)
    if not lookup:
        return value
    inline = storage.get_lookup2(lookup[2])
    if inline:
        try:
            return inline.get(str(int(float(value))), value)
        except (TypeError, ValueError):
            return value
    try:
        actual = await resolve_table(conn, lookup[2])
        id_col = await resolve_column(conn, actual, lookup[3])
        name_col = await resolve_column(conn, actual, lookup[4])
        title = await conn.fetchval(
            f"SELECT {quote_ident(name_col)}::text FROM {quote_ident(actual)} WHERE {quote_ident(id_col)} = $1",
            value)
    except Exception:  # noqa: BLE001 — справочника нет: показываем код
        title = None
    return title if title is not None else value


async def batch_card(conn, ids: list[int], kind: str = "line") -> dict:
    """Карточка выбора: поля карточки участка (узла), значения сведены по колонкам."""
    from database.db import create_select_line, create_select_node

    columns = await object_columns(conn, kind, ids)
    ncols = len(columns)
    own = KIND_KEYS[kind]
    # образец карточки: участок-пара, если колонок две
    sample = columns[0][0]
    if ncols == 2:
        partners = set(columns[1])
        for lid in columns[0]:
            other = await conn.fetchval(
                "SELECT b.id FROM linesobj a JOIN linesobj b ON b.nodeid1 = a.nodeid1 AND b.nodeid2 = a.nodeid2 "
                "AND b.id <> a.id AND b.removed = 0 AND b.externalsignlineid = 3 WHERE a.id = $1", lid)
            if other in partners:
                sample = lid
                break
    if kind in ce.NODE_CARD_TABLE:
        card = json.loads(await create_select_node(ce.NODE_CARD_TABLE[kind], sample, include_hidden=True))
    else:
        card = json.loads(await create_select_line("heatPipeSections", sample, include_hidden=True))
    card = await ce.annotate_card(conn, kind, card)

    tabs = []
    wanted: dict[str, set[str]] = {}
    for tab in card.get("tabs", []):
        if tab.get("readonly"):
            continue
        subs = []
        for sub in tab.get("subsections", []):
            fields = [f for f in sub.get("fields", []) if str(f["table"]).lower() in own and f.get("edit")]
            if fields:
                subs.append({**sub, "fields": fields})
                for f in fields:
                    wanted.setdefault(str(f["table"]).lower(), set()).add(str(f["field"]).lower())
        if subs:
            tabs.append({**tab, "subsections": subs})

    # значения по колонкам: {table: [ {col: Counter} на колонку ]}
    real_cols: dict[str, dict[str, str]] = {}
    stats: dict[str, list[dict[str, Counter]]] = {}
    counts: dict[str, list[int]] = {}
    for t, cols in wanted.items():
        actual = await resolve_table(conn, t)
        names = {}
        for c in cols:
            try:
                names[c] = await resolve_column(conn, actual, c)
            except Exception:  # noqa: BLE001 — колонки нет в базе
                continue
        real_cols[t] = names
        stats[t], counts[t] = [], []
        for line_ids in columns:
            rows = await _table_rows(conn, t, line_ids, list(names.values()), kind)
            counts[t].append(len(rows))
            stats[t].append({c: Counter(_key(r.get(n)) for r in rows) for c, n in names.items()})

    for tab in tabs:
        for sub in tab["subsections"]:
            for f in sub["fields"]:
                t, c = str(f["table"]).lower(), str(f["field"]).lower()
                e = f["edit"]
                spec_ok = e.get("kind") is not None
                ro = ce.readonly_columns(kind, t, c, ncols, e.get("fun"), spec_ok and t in own)
                if e.get("fun_name") in ce.BATCH_READONLY_FUNS:
                    ro = [True] * ncols
                raw, mixed, titles = [], [], []
                for ci in range(ncols):
                    cnt = stats.get(t, [{}] * ncols)[ci].get(c) or Counter()
                    if len(cnt) == 1:
                        v = next(iter(cnt))
                        raw.append(v)
                        mixed.append(False)
                        titles.append(await value_title(conn, f["table"], f["field"], v))
                    else:
                        raw.append(None)
                        mixed.append(len(cnt) > 1)
                        titles.append(None)
                f["id"] = 1
                f["value"] = titles[0]
                f["code"] = raw[0]
                if ncols == 2:
                    f["id2"] = 2
                    f["value2"] = titles[1]
                    f["code2"] = raw[1]
                else:
                    f.pop("id2", None)
                    f.pop("value2", None)
                    f.pop("code2", None)
                e["raw"] = raw
                e["mixed"] = mixed
                e["readonly"] = ro

    return {
        "kind": kind, "batch": True, "table": ce.NODE_CARD_TABLE.get(kind, "heatPipeSections"), "id": 0,
        "fileid": card.get("fileid"),
        "tabs": tabs,
        "columns": COLUMN_TITLES[:ncols] if ncols == 2 else [""],
        "selection": {"columns": [{"title": COLUMN_TITLES[i] if ncols == 2 else "", "line_ids": ids_}
                                  for i, ids_ in enumerate(columns)],
                      "lines": sum(len(c) for c in columns),
                      "rows": {t: counts[t] for t in counts}},
        "versions": {},
        "rules": card.get("rules", {}),
        "edit_tables": card.get("edit_tables", []),
    }


def _key(v: Any) -> Any:
    """Значение для сравнения (Decimal/дата → JSON-вид; 1.0 и 1 — одно)."""
    v = te.jsonable(v)
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


# --- предпросмотр и применение ---------------------------------------------------------------------

async def _plan(conn, ids: list[int], changes: list[dict[str, Any]], kind: str = "line"):
    """changes [{table, id: колонка 1|2, field, value}] → [(table, line_ids, {col: value}, specs)]."""
    columns = await object_columns(conn, kind, ids)
    ncols = len(columns)
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for ch in changes:
        t = str(ch.get("table", "")).lower()
        if t not in KIND_KEYS[kind]:
            raise _err(403, "table_not_editable", f"Таблица {ch.get('table')} не правится через карточку")
        try:
            ci = int(ch["id"]) - 1
        except (KeyError, TypeError, ValueError):
            raise _err(422, "bad_column", "Нет колонки изменения")
        if not 0 <= ci < ncols:
            raise _err(422, "bad_column", "Колонка не относится к выбору")
        field = str(ch.get("field", ""))
        if ce.readonly_columns(kind, t, field.lower(), ncols, None, True)[ci]:
            raise _err(422, "field_readonly", f"Поле {field} в этой колонке не правится")
        if ce.fun_name((await storage.read_fun(t)).get(field.lower())) in ce.BATCH_READONLY_FUNS:
            raise _err(422, "field_readonly", f"Поле {field} правится только в карточке одного объекта")
        grouped.setdefault((t, ci), {})[field] = ch.get("value")
    plans = []
    specs_cache: dict[str, list[te.FieldSpec]] = {}
    for (t, ci), raw in grouped.items():
        if t not in specs_cache:
            specs_cache[t] = await ce.writable_specs(conn, t)
        fields = ce.check_inline_codes(t, specs_cache[t], raw)
        by_name, values = te.prepare_values(fields, raw)
        await te._check_refs(conn, by_name, values)
        plans.append((t, ci, columns[ci], values, by_name))
    return columns, plans


async def _plan_rows(conn, table: str, line_ids: list[int], values: dict[str, Any], lock: bool = False,
                     kind: str = "line"):
    actual = await resolve_table(conn, table)
    key = KIND_KEYS[kind][table]
    cols = ", ".join(quote_ident(c) for c in values)
    rows = await conn.fetch(
        f"SELECT id AS __id, {cols} FROM {quote_ident(actual)} WHERE {quote_ident(key)} = ANY($1::int[]) "
        f"ORDER BY id{' FOR UPDATE' if lock else ''}", line_ids)
    return actual, [dict(r) for r in rows]


async def preview(conn, ids: list[int], changes: list[dict[str, Any]], kind: str = "line") -> dict:
    """Сколько строк изменится по каждому полю и какие значения были (до 5 самых частых)."""
    columns, plans = await _plan(conn, ids, changes, kind)
    fields_out, rows_changed = [], set()
    for t, ci, line_ids, values, by_name in plans:
        actual, rows = await _plan_rows(conn, t, line_ids, values, kind=kind)
        for col, new in values.items():
            olds = [r[col] for r in rows if r[col] != new]
            for r in rows:
                if r[col] != new:
                    rows_changed.add((actual, r["__id"]))
            label = by_name[col].label if col in by_name else col
            top = Counter(_key(v) for v in olds).most_common(5)
            fields_out.append({
                "table": actual, "field": col, "label": label, "column": ci,
                "column_title": COLUMN_TITLES[ci] if len(columns) == 2 else "",
                "new": te.jsonable(new),
                "new_title": await value_title(conn, t, col, new) if storage.get_lookup(t, col) else te.jsonable(new),
                "rows": len(rows), "changes": len(olds),
                "was": [{"value": v, "title": await value_title(conn, t, col, v) if storage.get_lookup(t, col) else v,
                         "count": n} for v, n in top],
            })
    return {"lines": sum(len(c) for c in columns), "fields": fields_out,
            "changes": len(rows_changed), "cells": sum(f["changes"] for f in fields_out)}


async def apply(conn, ids: list[int], changes: list[dict[str, Any]], *, audit_row,
                expected_changes: Optional[int] = None, kind: str = "line") -> dict:
    """Применение в транзакции вызывающего: UPDATE строк колонки, audit_log с группой, итог GROUP_SET."""
    columns, plans = await _plan(conn, ids, changes, kind)
    group_id = str(uuid.uuid4())
    await conn.execute("SELECT set_config('tgid.current_group_id', $1, true)", group_id)
    changed_rows: set[tuple[str, int]] = set()
    applied: dict[str, int] = {}
    touched: dict[str, set[str]] = {}
    pending = []
    for t, ci, line_ids, values, _ in plans:
        actual, rows = await _plan_rows(conn, t, line_ids, values, lock=True, kind=kind)
        diff = [r for r in rows if any(r[c] != v for c, v in values.items())]
        for r in diff:
            changed_rows.add((actual, r["__id"]))
        pending.append((actual, values, diff))
    if expected_changes is not None and expected_changes != len(changed_rows):
        raise _err(409, "stale_preview",
                   f"Данные изменились после предпросмотра: изменится {len(changed_rows)} строк вместо "
                   f"{expected_changes}. Повторите предпросмотр.", changes=len(changed_rows))
    own_audit = {}
    for actual, values, diff in pending:
        if not diff:
            continue
        if actual not in own_audit:
            from database.group_setters import _has_audit_trigger

            own_audit[actual] = audit_row is not None and not await _has_audit_trigger(conn, actual)
        sets = ", ".join(f"{quote_ident(c)} = ${i + 2}" for i, c in enumerate(values))
        await conn.execute(
            f"UPDATE {quote_ident(actual)} SET {sets} WHERE id = ANY($1::int[])",
            [r["__id"] for r in diff], *values.values())
        applied[actual] = applied.get(actual, 0) + len(diff)
        touched.setdefault(actual, set()).update(values)
        if own_audit[actual]:
            for r in diff:
                await audit_row(conn, operation="UPDATE", table=actual, record_id=r["__id"],
                                old={c: te.jsonable(r[c]) for c in values},
                                new={c: te.jsonable(v) for c, v in values.items()}, group=group_id)
    if audit_row is not None and changed_rows:
        await audit_row(conn, operation="GROUP_SET", table=KIND_TABLE[kind], record_id=None, old=None, new={
            "setter": SETTER, "label": KIND_LABEL[kind], "kind": kind, "lines": sum(len(c) for c in columns),
            "applied": applied, "columns": {t: sorted(c) for t, c in touched.items()},
            "changes": [{k: ch.get(k) for k in ("table", "id", "field", "value")} for ch in changes][:200],
        }, group=group_id)
    return {"changed": len(changed_rows), "applied": applied,
            "change_group_id": group_id if changed_rows else None}


async def undo(conn, group: str, summary: dict, *, dry_run: bool, audit_row) -> dict:
    """Отмена правки нескольких участков: по строкам audit_log группы — старые значения записанных
    колонок; строки, изменённые после операции, не трогаются (conflicts)."""
    from database.group_setters import _column_cast

    result: dict[str, Any] = {"setter": SETTER, "label": summary.get("label") or "Свойства участков",
                              "change_group_id": group, "by_table": {}, "conflicts": [], "restorable": 0,
                              "already_undone": False, "dry_run": dry_run}
    undone_already = await conn.fetchval(
        "SELECT EXISTS (SELECT 1 FROM audit_log WHERE operation = 'GROUP_UNDO' AND new_data->>'undo_of' = $1)", group)
    result["already_undone"] = bool(undone_already)
    if not dry_run and undone_already:
        from database.group_setters import GroupSetterError

        raise GroupSetterError(409, {"code": "already_undone", "message": "Операция уже отменена"})
    undo_group = str(uuid.uuid4())
    if not dry_run:
        await conn.execute("SELECT set_config('tgid.current_group_id', $1, true)", undo_group)
    for table, written in (summary.get("columns") or {}).items():
        actual = await resolve_table(conn, table)
        # триггер log_changes пишет строку целиком — возвращаем только колонки операции
        written_lc = {str(c).lower() for c in written}
        audit = await conn.fetch(
            "SELECT DISTINCT ON (record_id) record_id, old_data, new_data FROM audit_log "
            "WHERE change_group_id = $1::uuid AND table_name = $2 AND operation = 'UPDATE' "
            "ORDER BY record_id, log_id", group, actual)
        casts: dict[str, str] = {}
        ok, bad = 0, 0
        for a in audit:
            old, new = _as_dict(a["old_data"]), _as_dict(a["new_data"])
            cols = [await resolve_column(conn, actual, c) for c in new if str(c).lower() in written_lc]
            old = {k.lower(): v for k, v in old.items()}
            new = {k.lower(): v for k, v in new.items()}
            if not cols:
                continue
            for c in cols:
                if c not in casts:
                    casts[c] = await _column_cast(conn, actual, c)
            conflict_sql = " OR ".join(
                f"{quote_ident(c)} IS DISTINCT FROM ${i + 2}::text::{casts[c]}" for i, c in enumerate(cols))
            params = [_txt(new.get(c.lower())) for c in cols]
            conflict = await conn.fetchval(
                f"SELECT ({conflict_sql}) FROM {quote_ident(actual)} WHERE id = $1", a["record_id"], *params)
            if conflict is None or conflict:
                bad += 1
                if len(result["conflicts"]) < 200:
                    result["conflicts"].append({"table": actual, "row_id": a["record_id"]})
                continue
            ok += 1
            if dry_run:
                continue
            sets = ", ".join(f"{quote_ident(c)} = ${i + 2}::text::{casts[c]}" for i, c in enumerate(cols))
            await conn.execute(f"UPDATE {quote_ident(actual)} SET {sets} WHERE id = $1",
                               a["record_id"], *[_txt(old.get(c.lower())) for c in cols])
            if audit_row is not None and not await _trigger(conn, actual):
                await audit_row(conn, operation="UPDATE", table=actual, record_id=a["record_id"],
                                old={c: new.get(c.lower()) for c in cols}, new={c: old.get(c.lower()) for c in cols},
                                group=undo_group)
        result["by_table"][actual] = {"rows": len(audit), "restorable": ok, "conflicts": bad}
        result["restorable"] += ok
    if not dry_run:
        has_flag = await conn.fetchval(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' "
            "AND table_name = 'audit_log' AND column_name = 'is_rolled_back')")
        if has_flag:
            await conn.execute("UPDATE audit_log SET is_rolled_back = TRUE WHERE change_group_id = $1::uuid", group)
        if audit_row is not None:
            await audit_row(conn, operation="GROUP_UNDO", table=KIND_TABLE.get(str(summary.get("kind")), "heatpipesections"),
                            record_id=None, old=None,
                            new={"undo_of": group, "setter": SETTER, "restored": result["restorable"],
                                 "conflicts": len(result["conflicts"])}, group=undo_group)
        result["undo_group_id"] = undo_group
    return result


async def _trigger(conn, table: str) -> bool:
    from database.group_setters import _has_audit_trigger

    return await _has_audit_trigger(conn, table)


def _txt(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}
