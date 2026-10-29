"""Перенос правок сценария в основу (сценарии «что если», шаг 3).

Что переносится (виды отличий — database/scenarios.collect_differences):
  * changed — поля объекта основы получают значения сценария (ссылки — в id основы); у узла и
    участка вместе с полями переносится геометрия (shape не входит в сравниваемые колонки .tgid,
    перенос узла виден по x/y, правка вершин — по coords);
  * added — объект вставляется в основу новым id (fileid — фрагмент-основа, id_old — NULL),
    ссылки на объекты копии переводятся в id основы, на другие добавленные — в их новые id;
    в tgid_scenario_object появляется строка соответствия с merge_group_id операции;
  * removed — узел и участок помечаются снятыми (removed = 1, как удаление в вебе); строка другой
    таблицы (карточка, оборудование) удаляется, если её узел или участок не снимается этим же
    переносом (тогда карточка остаётся при снятом объекте, как при удалении в вебе);
  * conflict — по умолчанию не переносится; resolutions {"таблица:id копии": "scenario"} — перенести;
  * base_changed / base_added / base_removed — изменения основы, их не трогаем.

Одна транзакция database/topology._run с журналом отмены: образы «до» всех изменённых строк,
созданные строки — для удаления при отмене. dry_run — тот же перенос с откатом: отчёт и проверка
правил связности области переноса (database/topology_rules.check_area).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from database.fragment_transfer import IMPORT_ORDER, _columns
from database.scenarios import (
    OBJECT_TABLE,
    _table_rows,
    collect_differences,
    fingerprint,
    normalized_row,
    object_mapping,
    scenario_row,
)
from database.topology_transfer import _ident

# Объекты с пометкой «снят» (removed): их не удаляем
_SOFT_DELETE = ("nodes", "linesobj")
# Геометрия, которую переносит правка объекта
_GEOMETRY_TABLES = ("nodes", "linesobj")
RESOLUTIONS = ("scenario", "base")


class ScenarioMergeError(ValueError):
    """Перенос невозможен (понятная пользователю причина)."""


def conflict_key(table: str, copy_id: int) -> str:
    return f"{table}:{copy_id}"


def plan_merge(found: list[tuple[str, dict]], resolutions: dict[str, str]) -> dict[str, list]:
    """Что делать с каждым отличием: {"update": […], "insert": […], "remove": […], "skipped": […]}."""
    plan: dict[str, list] = {"update": [], "insert": [], "remove": [], "skipped": []}
    for table, f in found:
        kind = f["kind"]
        if kind == "changed":
            plan["update"].append((table, f))
        elif kind == "conflict":
            if resolutions.get(conflict_key(table, f["copy_id"])) == "scenario":
                plan["update"].append((table, f))
            else:
                plan["skipped"].append((table, f))
        elif kind == "added":
            plan["insert"].append((table, f))
        elif kind == "removed":
            plan["remove"].append((table, f))
    # вставка — в порядке импорта .tgid (узлы раньше участков, участки раньше карточек)
    plan["insert"].sort(key=lambda tf: (IMPORT_ORDER.index(tf[0]), tf[1]["copy_id"]))
    return plan


async def merge_scenario(conn, op, scenario_id: int, resolutions: Optional[dict[str, str]] = None) -> dict[str, Any]:
    """Переносит правки сценария в основу в транзакции op. LookupError — сценария нет."""
    sc = await scenario_row(conn, scenario_id)
    if sc is None:
        raise LookupError(f"Сценарий {scenario_id} не найден")
    for fid, what in ((sc["base_fileid"], "основы"), (sc["fileid"], "сценария")):
        if not await conn.fetchval("SELECT 1 FROM fragments WHERE id = $1 AND COALESCE(removed, 0) = 0", fid):
            raise ScenarioMergeError(f"Фрагмент {what} #{fid} удалён — переносить некуда или нечего")
    bad = {k: v for k, v in (resolutions or {}).items() if v not in RESOLUTIONS}
    if bad:
        raise ScenarioMergeError(f"Недопустимое решение конфликта: {', '.join(sorted(bad))}")

    diff = await collect_differences(conn, sc)
    copy_to_base: dict[str, dict[int, int]] = diff["copy_to_base"]
    plan = plan_merge(diff["found"], resolutions or {})
    new_ids: dict[str, dict[int, int]] = {}   # добавленные: {таблица: {id копии: новый id основы}}
    counts: dict[str, dict[str, int]] = {}
    touched = {"nodes": set(), "linesobj": set()}

    def count(table: str, action: str) -> None:
        counts.setdefault(table, {})
        counts[table][action] = counts[table].get(action, 0) + 1

    def to_base(target: str, value: Any) -> Any:
        """Ссылка копии → id основы; объект вне сценария (другой фрагмент) — как есть."""
        if value is None:
            return None
        mapped = copy_to_base.get(target, {}).get(value)
        if mapped is None:
            mapped = new_ids.get(target, {}).get(value)
        return value if mapped is None else mapped

    def touch_owner(row: Any, copy_side: bool) -> None:
        """Карточка или оборудование — в область проверки связности попадает их узел или участок."""
        for col, target in (("nodeid", "nodes"), ("lineid", "linesobj")):
            v = row.get(col)
            if v is not None:
                touched[target].add(to_base(target, v) if copy_side else v)

    # 1. Добавленные объекты: вставка; ссылки на ещё не вставленные — вторым проходом
    pending: list[tuple[str, int, str, str, int]] = []
    copy_ids_all = {t: set(m) for t, m in copy_to_base.items()}
    added_copy = {}
    for table, f in plan["insert"]:
        added_copy.setdefault(table, set()).add(f["copy_id"])
    for table, f in plan["insert"]:
        cols = await _columns(conn, table)
        refs = diff["tables"][table]["refs"]
        overrides: dict[str, Any] = {}
        row = await conn.fetchrow(f"SELECT * FROM {_ident(table)} WHERE id = $1", f["copy_id"])
        for c, target in refs.items():
            v = row[c]
            if v is None:
                continue
            if v in added_copy.get(target, set()) and v not in new_ids.get(target, {}):
                overrides[c] = None
                pending.append((table, -1, c, target, v))  # новый id строки — ниже
            elif v in copy_ids_all.get(target, set()) or v in new_ids.get(target, {}):
                overrides[c] = to_base(target, v)
        if "fileid" in cols:
            overrides["fileid"] = sc["base_fileid"]
        if "id_old" in cols:
            overrides["id_old"] = None
        names = [c for c in cols if c != "id"]
        params: list[Any] = [f["copy_id"]]
        select = []
        for c in names:
            if c in overrides:
                params.append(overrides[c])
                select.append(f"${len(params)}::{_sql_type(cols[c])}")
            else:
                select.append(f"s.{_ident(c)}")
        new_id = await conn.fetchval(
            f"""INSERT INTO {_ident(table)} (id, {", ".join(_ident(c) for c in names)})
                SELECT nextval(pg_get_serial_sequence('public.{table}', 'id')), {", ".join(select)}
                  FROM {_ident(table)} s WHERE s.id = $1
                RETURNING id""",
            *params)
        new_ids.setdefault(table, {})[f["copy_id"]] = new_id
        pending = [(t, new_id if rid == -1 else rid, c, tg, v) for t, rid, c, tg, v in pending]
        op.journal.created(table, new_id)
        count(table, "inserted")
        if table in touched:
            touched[table].add(new_id)
        else:
            touch_owner(row, copy_side=True)
    for table, row_id, col, target, value in pending:
        await conn.execute(f"UPDATE {_ident(table)} SET {_ident(col)} = $1 WHERE id = $2",
                           to_base(target, value), row_id)

    # 2. Изменённые: поля (и геометрия узла/участка) из сценария
    for table, f in plan["update"]:
        refs = diff["tables"][table]["refs"]
        base_id, copy_id = f["base_id"], f["copy_id"]
        row = await conn.fetchrow(f"SELECT * FROM {_ident(table)} WHERE id = $1", copy_id)
        fields = [c for c in f["fields"] if c in row.keys()]
        await op.journal.capture_ids(conn, table, [base_id])
        sets, params = [], [base_id]
        for c in fields:
            v = row[c]
            if c in refs and v is not None:
                v = to_base(refs[c], v)
            params.append(v)
            sets.append(f"{_ident(c)} = ${len(params)}")
        if table in _GEOMETRY_TABLES:
            params.append(copy_id)
            sets.append(f"shape = (SELECT shape FROM {_ident(table)} WHERE id = ${len(params)})")
            touched[table].add(base_id)
        else:
            touch_owner(row, copy_side=True)
        if sets:
            await conn.execute(f"UPDATE {_ident(table)} SET {', '.join(sets)} WHERE id = $1", *params)
        count(table, "updated")

    # 3. Удалённые: узел и участок — снять; карточку — удалить, если её объект остаётся
    removed_objects = {t: {f["base_id"] for tb, f in plan["remove"] if tb == t} for t in _SOFT_DELETE}
    now = datetime.now()
    for table, f in plan["remove"]:
        base_id = f["base_id"]
        await op.journal.capture_ids(conn, table, [base_id])
        if table in _SOFT_DELETE:
            await conn.execute(
                f"UPDATE {_ident(table)} SET removed = 1, archivechangedate = $2 WHERE id = $1", base_id, now)
            touched[table].add(base_id)
            count(table, "removed")
            continue
        row = f["row"]
        touch_owner(row, copy_side=False)
        if row.get("nodeid") in removed_objects["nodes"] or row.get("lineid") in removed_objects["linesobj"]:
            count(table, "kept_with_removed_object")
            continue
        await conn.execute(f"DELETE FROM {_ident(table)} WHERE id = $1", base_id)
        count(table, "deleted")

    # 4. Соответствие для добавленных: следующий перенос и сравнение их уже знают
    await _map_inserted(conn, op, sc, new_ids)

    return {
        "scenario_id": sc["id"],
        "base_fileid": sc["base_fileid"],
        "fileid": sc["fileid"],
        "counts": counts,
        "updated": len(plan["update"]),
        "inserted": len(plan["insert"]),
        "removed": len(plan["remove"]),
        "skipped_conflicts": [
            {"key": conflict_key(t, f["copy_id"]), "table": t, "base_id": f["base_id"], "copy_id": f["copy_id"],
             "fields": f.get("fields")}
            for t, f in plan["skipped"]
        ],
        "touched_nodes": sorted(touched["nodes"]),
        "touched_lines": sorted(touched["linesobj"]),
    }


def _sql_type(data_type: str) -> str:
    """Тип information_schema → приведение параметра (подставляются ссылки, fileid, id_old — числа)."""
    return "text" if data_type == "USER-DEFINED" else data_type


async def _map_inserted(conn, op, sc, new_ids: dict[str, dict[int, int]]) -> None:
    if not new_ids:
        return
    base_ids_all: dict[str, set[int]] = {}
    copy_to_base_all: dict[str, dict[int, int]] = {}
    tables, bases, copies, hashes = [], [], [], []
    copy_to_base, _ = await object_mapping(conn, sc["id"])
    for t, m in copy_to_base.items():
        copy_to_base_all[t] = dict(m)
    for t, m in new_ids.items():
        copy_to_base_all.setdefault(t, {}).update(m)
    for t, m in copy_to_base_all.items():
        base_ids_all[t] = set(m.values())
    for table, mapping in new_ids.items():
        base_rows, columns, refs = await _table_rows(conn, table, sc["base_fileid"])
        for copy_id, base_id in mapping.items():
            row = base_rows.get(base_id)
            tables.append(table)
            bases.append(base_id)
            copies.append(copy_id)
            hashes.append(fingerprint(normalized_row(row, columns, refs, base_ids_all)) if row else None)
    await conn.execute(
        f"""INSERT INTO {OBJECT_TABLE} (scenario_id, table_name, base_id, copy_id, base_hash, merge_group_id)
            SELECT $1, t, b, c, h, $6::uuid FROM unnest($2::text[], $3::int[], $4::int[], $5::text[]) AS u(t, b, c, h)""",
        sc["id"], tables, bases, copies, hashes, op.group_id,
    )
