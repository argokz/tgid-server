"""Экспорт, импорт и слияние фрагментов в формате .tgid десктопа (этап 10).

Эталон — gid8/python/unite (его вызывает gid8 gidview/export.cpp и gidrSlot.cpp):
- export_tgid.py: zip с одним файлом tgid.txt. Заголовок «=====», Version: 2.0, CodePage: utf-8,
  Server/Database/User/Date; затем секции «-----», имя таблицы, строка заголовков, строки CSV
  (строки в кавычках, переводы строк → ¶). Таблицы и порядок — list_tab.py; отбор строк —
  print_tab0 (по fileid, через nodeid/lineid узлов фрагмента, deployedtempgraphs через
  heatsources, pipesections через heatpipesections). Колонки без shape, id_old, removed,
  idremoved, globalid, gistable, sync, gis, sync_tgid; у linesobj ещё без fileid, internalnodeid.
  Секцию «Lookups» (справочники) десктоп пишет, но при импорте не загружает — здесь не пишем.
- import_tgid.py: все строки получают новые id; ссылки map_qq (fileid, externalcodeid, nodeid,
  lineid, …) перенумеровываются через id_old; ссылка на объект вне файла становится NULL;
  internalnodeid и externalcodes.heatsourceid правятся после вставки (ispr_nodes,
  ispr_externalCodes); removed = 0; shape = NULL.
- unite_tgid.py («Объединить фрагменты»): каждый выбранный фрагмент экспортируется и
  импортируется копией, fileid копий переносится в первую (chFileID), лишние строки fragments
  удаляются, первая переименовывается. Исходные фрагменты не меняются.

Отличия от десктопа (осознанные):
- геометрия восстанавливается сразу после импорта, как в gid8 GidWidget::import_tgid0: узел —
  (x/100, −y/100) в SRID 9998, участок — узел1 + coords + узел2; без этого фрагмент не виден на карте;
- pipesections вставляются раньше heatpipesections (в list_tab они последние, и ссылка
  pipesectionid при импорте десктопа теряется);
- deployedtempgraphs.hsourceid перенумеровывается (в map_qq десктопа его нет — ссылка
  указывала бы на источник исходного фрагмента);
- при слиянии сообщается о совпадающих названиях кодов (externalcodes.name) и, по флагу
  unify_external_codes, ссылки externalcodeid переводятся на первый код, дубли удаляются.

Всё выполняется в одной транзакции (database/topology._run): dry-run откатывается, при
применении созданные строки попадают в журнал отмены (topology_undo_log) — отмена
POST /api/topology/undo удаляет их; запись в audit_log.
"""

from __future__ import annotations

import csv
import datetime as dt
import decimal
import io
import zipfile
from typing import Any, Optional

from database.topology_transfer import _ident

MAX_UPLOAD_BYTES = 100 * 1024 * 1024
SECTION = "-------------------------"
HEADER = "========================="

# gid8/python/unite/list_tab.py (порядок вставки; pipesections перенесены до участков)
LIST_TAB = [
    "fragments", "externalcodes", "calctemperatures", "calculations", "gvsloadgraphs", "specexpends",
    "texts", "varcoefficients", "nodes", "linesobj", "setpressnodes", "directions", "deployeddirections",
    "connectnodes", "wdodevices", "buildingentries", "generalizedconsumers", "heatchambers", "heatsources",
    "realconsumers", "refillnodes", "threewayvalves", "deployedtempgraphs", "internalnodes",
    "overgroundnodes", "pavilions", "pumpstations", "trps", "undergroundnodes", "uninstallednodes",
    "airheaters", "bypass", "consumptregulators", "dampers", "diaphragms", "elevators", "heatexchangers",
    "heatpipesections", "opresdeployed", "pressdropregulators", "pressregulators", "pumps",
    "regularmatures", "reversevalves", "systemradiators", "pipesections",
]
IMPORT_ORDER = [t for t in LIST_TAB if t != "pipesections"]
IMPORT_ORDER.insert(IMPORT_ORDER.index("linesobj") + 1, "pipesections")

# import_tgid.py map_qq (+ hsourceid) — ссылки, которые перенумеровываются
REF_COLUMNS = {
    "fileid": "fragments", "externalcodeid": "externalcodes", "heatsourceid": "heatsources",
    "hsourceid": "heatsources", "pipesectionid": "pipesections", "nodeid": "nodes", "nodeid1": "nodes",
    "nodeid2": "nodes", "connectid": "nodes", "lineid": "linesobj", "directionid": "directions",
    "calctemperatureid": "calctemperatures", "gvsloadgraphid": "gvsloadgraphs", "specexpendid": "specexpends",
    "varcoeffid": "varcoefficients", "varcoeffidflow": "varcoefficients", "varcoeffidret": "varcoefficients",
}
SKIP_EXPORT = {"shape", "id_old", "removed", "idremoved", "globalid", "gistable", "sync", "gis", "sync_tgid"}
NULL_ON_IMPORT = {"shape", "idremoved", "globalid", "gistable", "sync", "gis", "sync_tgid"}
# chFileID: таблицы, где fileid копий переносится в объединённый фрагмент (+ linesobj.fileid)
FILEID_TABLES = [
    "nodes", "linesobj", "externalcodes", "texts", "gvsloadgraphs", "setpressnodes", "directions",
    "calctemperatures", "specexpends", "calculations", "varcoefficients",
]
TEXT_TYPES = {"text", "character varying", "character", "nvarchar", "ntext"}


class FragmentFileError(ValueError):
    """Файл не разобран как .tgid."""


# ---------------------------------------------------------------------------
# Схема БД
# ---------------------------------------------------------------------------

async def _columns(conn, table: str) -> dict[str, str]:
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position",
        table,
    )
    return {r["column_name"]: r["data_type"] for r in rows}


# ---------------------------------------------------------------------------
# Экспорт
# ---------------------------------------------------------------------------

def _export_query(table: str, cols: dict[str, str]) -> tuple[str, list[str]]:
    names = [c for c in cols if c not in SKIP_EXPORT
             and not (table == "linesobj" and c in ("fileid", "internalnodeid"))]

    def sel(prefix: str) -> str:
        return ", ".join(
            f"{prefix}.{_ident(c)}::date AS {_ident(c)}" if cols[c].startswith("timestamp") else f"{prefix}.{_ident(c)}"
            for c in names
        )

    # print_tab0: последнее подходящее правило побеждает
    q = f"SELECT {sel('o')} FROM {_ident(table)} o"
    if "fileid" in cols:
        # удалённые (removed) не выгружаем, как C++ export_tgid (nodes … AND removed=0); python-
        # экспорт десктопа их выгружал, а импорт снимал пометку — удалённые объекты «воскресали»
        alive = " AND COALESCE(o.removed, 0) = 0" if "removed" in cols else ""
        q = f"SELECT {sel('o')} FROM {_ident(table)} o WHERE o.fileid = $1{alive}"
    if table == "linesobj":
        q = (f"SELECT {sel('l')} FROM linesobj l JOIN nodes n1 ON n1.id = l.nodeid1 AND n1.fileid = $1 "
             f"WHERE COALESCE(l.removed, 0) = 0")
    if "nodeid" in cols:
        q = (f"SELECT {sel('o')} FROM {_ident(table)} o JOIN nodes n ON n.id = o.nodeid "
             f"AND n.fileid = $1 AND COALESCE(n.removed, 0) = 0")
    if "lineid" in cols:
        q = (f"SELECT {sel('o')} FROM {_ident(table)} o JOIN linesobj l ON l.id = o.lineid "
             f"JOIN nodes n ON n.id = l.nodeid1 WHERE n.fileid = $1 AND COALESCE(n.removed, 0) = 0 "
             f"AND COALESCE(l.removed, 0) = 0")
    if table == "heatsystem":
        q = f"SELECT {sel('o')} FROM heatsystem o WHERE o.id = 1 AND $1::int IS NOT NULL"
    if table == "fragments":
        q = f"SELECT {sel('o')} FROM fragments o WHERE o.id = $1"
    if table == "deployedtempgraphs":
        q = (f"SELECT {sel('dt')} FROM deployedtempgraphs dt JOIN heatsources hs ON hs.id = dt.hsourceid "
             f"JOIN nodes n ON n.id = hs.nodeid AND n.fileid = $1 AND COALESCE(n.removed, 0) = 0")
    if table == "pipesections":
        q = (f"SELECT DISTINCT {sel('ps')} FROM pipesections ps JOIN heatpipesections hps ON hps.pipesectionid = ps.id "
             f"JOIN linesobj l ON l.id = hps.lineid JOIN nodes n1 ON n1.id = l.nodeid1 WHERE n1.fileid = $1")
    return q + " ORDER BY 1", names


def _cell(v: Any) -> Any:
    if isinstance(v, str):
        return v.replace("\r\n", "¶").replace("\n", "¶").replace("\r", "¶")
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()[:10]
    if isinstance(v, decimal.Decimal):
        return format(v, "f")
    return v


async def export_fragment_text(conn, fileid: int, meta: Optional[dict] = None) -> tuple[str, dict[str, int]]:
    """Текст tgid.txt фрагмента и число строк по таблицам."""
    if not await conn.fetchval("SELECT 1 FROM fragments WHERE id = $1", fileid):
        raise LookupError(f"Фрагмент {fileid} не найден")
    meta = meta or {}
    out = io.StringIO()
    out.write(f"{HEADER}\r\nVersion: 2.0\r\nCodePage: utf-8\r\n")
    out.write(f"Server: {meta.get('server', 'itwin')}\r\nDatabase: {meta.get('database', '')}\r\n")
    out.write(f"User: {meta.get('user', '')}\r\nDate: {dt.datetime.now():%d-%m-%Y %H:%M:%S}\r\n")
    counts: dict[str, int] = {}
    for table in ["heatsystem", *LIST_TAB]:
        cols = await _columns(conn, table)
        if not cols:
            continue
        q, names = _export_query(table, cols)
        rows = await conn.fetch(q, fileid)
        out.write(f"{SECTION}\r\n{table}\r\n")
        writer = csv.writer(out, delimiter=",", quotechar='"', doublequote=True, escapechar="\\",
                            quoting=csv.QUOTE_STRINGS, lineterminator="\r\n")
        writer.writerow(names)
        for r in rows:
            writer.writerow([_cell(r[c]) for c in names])
        counts[table] = len(rows)
    return out.getvalue(), counts


async def export_fragment_zip(conn, fileid: int, meta: Optional[dict] = None) -> tuple[bytes, dict[str, int], str]:
    text, counts = await export_fragment_text(conn, fileid, meta)
    name = await conn.fetchval("SELECT name FROM fragments WHERE id = $1", fileid) or f"fragment_{fileid}"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("tgid.txt", text.encode("utf-8"))
    return buf.getvalue(), counts, name


# ---------------------------------------------------------------------------
# Разбор файла
# ---------------------------------------------------------------------------

def parse_tgid(data: bytes) -> dict[str, dict]:
    """{table: {"columns": [...], "rows": [[...], ...]}} — секции данных до «Lookups»."""
    if data[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                names = [n for n in z.namelist() if n.lower().endswith(".txt")]
                if not names:
                    raise FragmentFileError("В архиве нет tgid.txt")
                data = z.read("tgid.txt" if "tgid.txt" in names else names[0])
        except zipfile.BadZipFile as e:
            raise FragmentFileError(f"Повреждённый архив: {e}")
    head = data[:400]
    encoding = "utf-8" if b"Version:" in head or b"CodePage: utf-8" in head else "cp1251"
    text = data.decode(encoding, errors="replace").lstrip("﻿")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("="):
        raise FragmentFileError("Не формат .tgid: нет заголовка «=====»")
    sections: dict[str, dict] = {}
    i, current, headers_seen = 1, None, 1
    while i < len(lines):
        line = lines[i]
        if line.startswith("="):
            headers_seen += 1
            if i + 1 < len(lines) and lines[i + 1].strip() == "Lookups":
                break
            if headers_seen > 1:
                raise FragmentFileError("В файле несколько фрагментов — импортируйте по одному")
        elif line.startswith("-----"):
            if i + 2 >= len(lines):
                break
            table = lines[i + 1].strip().lower()
            columns = [c.lower() for c in next(csv.reader([lines[i + 2]], escapechar="\\"))]
            current = sections.setdefault(table, {"columns": columns, "rows": []})
            i += 3
            continue
        elif current is not None and line.strip():
            row = next(csv.reader([line], escapechar="\\"))
            current["rows"].append([v.replace("¶", "\n") for v in row])
        i += 1
    if "fragments" not in sections or not sections["fragments"]["rows"]:
        raise FragmentFileError("В файле нет секции fragments")
    if "nodes" not in sections:
        raise FragmentFileError("В файле нет секции nodes")
    return sections


# ---------------------------------------------------------------------------
# Импорт
# ---------------------------------------------------------------------------

def _value(raw: Optional[str], data_type: str) -> Optional[str]:
    if raw is None:
        return None
    if data_type in TEXT_TYPES:
        return raw
    if raw == "":
        return None
    if data_type in ("integer", "smallint", "bigint") and raw.upper() in ("TRUE", "FALSE"):
        return "1" if raw.upper() == "TRUE" else "0"
    return raw


async def import_sections(conn, op, sections: dict[str, dict], name: Optional[str] = None) -> dict:
    """Вставляет фрагмент из разобранного файла новыми id; возвращает отчёт."""
    import json

    id_map: dict[str, dict[int, int]] = {}
    counts: dict[str, int] = {}
    unresolved: dict[str, int] = {}
    skipped_tables = sorted(t for t in sections if t not in LIST_TAB and t != "heatsystem")
    dropped_columns: dict[str, list[str]] = {}
    pending_internal: list[tuple[int, int]] = []  # (новый id узла, старый internalnodeid)
    pending_hs: list[tuple[int, int]] = []  # (новый id кода, старый heatsourceid)
    new_fileid: Optional[int] = None

    for table in IMPORT_ORDER:
        sec = sections.get(table)
        if not sec or not sec["rows"]:
            continue
        cols = await _columns(conn, table)
        if not cols or "id" not in cols:
            continue
        file_cols = sec["columns"]
        if "id" not in file_cols:
            raise FragmentFileError(f"В секции {table} нет колонки id")
        dropped = [c for c in file_cols if c not in cols]
        if dropped:
            dropped_columns[table] = dropped
        idx = {c: k for k, c in enumerate(file_cols)}
        seq_ok = await conn.fetchval("SELECT pg_get_serial_sequence($1, 'id')", f"public.{table}")
        if not seq_ok:
            raise FragmentFileError(f"У таблицы {table} нет последовательности id")
        new_ids = [r[0] for r in await conn.fetch(
            "SELECT nextval(pg_get_serial_sequence($1, 'id')) FROM generate_series(1, $2)",
            f"public.{table}", len(sec["rows"]),
        )]
        records = []
        tmap = id_map.setdefault(table, {})
        for row, new_id in zip(sec["rows"], new_ids):
            raw = {c: (row[k] if k < len(row) else None) for c, k in idx.items()}
            try:
                old_id = int(float(raw["id"]))
            except (TypeError, ValueError):
                raise FragmentFileError(f"{table}: неверный id «{raw.get('id')}»")
            tmap[old_id] = new_id
            rec: dict[str, Any] = {"id": new_id}
            for c, dtype in cols.items():
                if c == "id":
                    continue
                if c == "id_old":
                    rec[c] = old_id
                elif c == "removed":
                    rec[c] = 0
                elif c in NULL_ON_IMPORT:
                    rec[c] = None
                elif table == "fragments" and c == "name":
                    stamp = f"{dt.datetime.now():%d-%m-%Y %H:%M}"
                    rec[c] = (name or f"{raw.get('name') or 'Фрагмент'} (импорт {stamp})")[:200]
                elif c == "internalnodeid" and table == "nodes":
                    v = _value(raw.get(c), dtype)
                    if v is not None:
                        pending_internal.append((new_id, int(float(v))))
                    rec[c] = None
                elif c == "heatsourceid" and table == "externalcodes":
                    v = _value(raw.get(c), dtype)
                    if v is not None:
                        pending_hs.append((new_id, int(float(v))))
                    rec[c] = None
                elif c in REF_COLUMNS and REF_COLUMNS[c] in sections:
                    v = _value(raw.get(c), dtype)
                    if v is None:
                        rec[c] = None
                    elif dtype not in ("integer", "bigint", "smallint"):
                        rec[c] = v  # одноимённая колонка другого смысла (текст) — не ссылка
                    else:
                        target = id_map.get(REF_COLUMNS[c], {}).get(int(float(v)))
                        if target is None:
                            unresolved[f"{table}.{c}"] = unresolved.get(f"{table}.{c}", 0) + 1
                        rec[c] = target
                elif c in idx:
                    rec[c] = _value(raw.get(c), dtype)
            records.append(rec)
        col_list = list(records[0].keys())
        col_sql = ", ".join(_ident(c) for c in col_list)
        await conn.execute(
            f"INSERT INTO {_ident(table)} ({col_sql}) SELECT {col_sql} "
            f"FROM jsonb_populate_recordset(NULL::{_ident(table)}, $1::jsonb)",
            json.dumps(records, ensure_ascii=False, default=str),
        )
        for new_id in new_ids:
            op.journal.created(table, new_id)
        counts[table] = len(records)
        if table == "fragments":
            new_fileid = new_ids[0]

    # ispr_nodes / ispr_externalCodes
    node_map = id_map.get("nodes", {})
    for new_id, old_internal in pending_internal:
        target = node_map.get(old_internal)
        if target is None:
            unresolved["nodes.internalnodeid"] = unresolved.get("nodes.internalnodeid", 0) + 1
        else:
            await conn.execute("UPDATE nodes SET internalnodeid = $1 WHERE id = $2", target, new_id)
    hs_map = id_map.get("heatsources", {})
    for new_id, old_hs in pending_hs:
        target = hs_map.get(old_hs)
        if target is not None:
            await conn.execute("UPDATE externalcodes SET heatsourceid = $1 WHERE id = $2", target, new_id)

    new_nodes = list(node_map.values())
    new_lines = list(id_map.get("linesobj", {}).values())
    if new_lines:
        # у linesobj fileid/internalnodeid не экспортируются — берутся от начального узла
        await conn.execute(
            "UPDATE linesobj l SET fileid = n1.fileid, internalnodeid = n1.internalnodeid "
            "FROM nodes n1 WHERE n1.id = l.nodeid1 AND l.id = ANY($1::int[])",
            new_lines,
        )
    geometry = await _restore_geometry(conn, new_nodes, new_lines)
    return {
        "fileid": new_fileid,
        "tables": counts,
        "created_nodes": len(new_nodes),
        "created_lines": len(new_lines),
        "unresolved_refs": unresolved,
        "skipped_tables": skipped_tables,
        "dropped_columns": dropped_columns,
        "geometry": geometry,
    }


async def _restore_geometry(conn, node_ids: list[int], line_ids: list[int]) -> dict:
    """gid8 GidWidget::import_tgid0: узел — (x/100, −y/100); участок — узел1 + coords + узел2."""
    nodes_done = 0
    if node_ids:
        status = await conn.execute(
            "UPDATE nodes SET shape = ST_SetSRID(ST_MakePoint(x / 100.0, -y / 100.0), 9998) "
            "WHERE id = ANY($1::int[]) AND x IS NOT NULL AND y IS NOT NULL AND (x <> 0 OR y <> 0)",
            node_ids,
        )
        nodes_done = int(status.split()[-1])
    lines_done = 0
    if line_ids:
        status = await conn.execute(
            r"""
            UPDATE linesobj l SET shape = ST_SetSRID(ST_MakeLine(pts.p), 9998)
              FROM (
                SELECT l2.id,
                       ARRAY[ST_MakePoint(n1.x / 100.0, -n1.y / 100.0)]
                       || COALESCE((
                            SELECT array_agg(ST_MakePoint(split_part(btrim(c.pt), ' ', 1)::float / 100.0,
                                                          -split_part(btrim(c.pt), ' ', 2)::float / 100.0)
                                             ORDER BY c.ord)
                              FROM unnest(string_to_array(l2.coords, ',')) WITH ORDINALITY AS c(pt, ord)
                             WHERE btrim(c.pt) ~ '^-?[0-9.]+ +-?[0-9.]+$'
                          ), ARRAY[]::geometry[])
                       || ARRAY[ST_MakePoint(n2.x / 100.0, -n2.y / 100.0)] AS p
                  FROM linesobj l2
                  JOIN nodes n1 ON n1.id = l2.nodeid1
                  JOIN nodes n2 ON n2.id = l2.nodeid2
                 WHERE l2.id = ANY($1::int[]) AND n1.internalnodeid IS NULL
                   AND (n1.x <> n2.x OR n1.y <> n2.y)
                   AND (n1.x <> 0 OR n1.y <> 0) AND (n2.x <> 0 OR n2.y <> 0)
              ) pts
             WHERE pts.id = l.id
            """,
            line_ids,
        )
        lines_done = int(status.split()[-1])
    return {"nodes_with_shape": nodes_done, "lines_with_shape": lines_done}


# ---------------------------------------------------------------------------
# Слияние
# ---------------------------------------------------------------------------

async def merge_fragments(conn, op, fragment_ids: list[int], name: Optional[str],
                          unify_external_codes: bool = False) -> dict:
    """unite_tgid.py: копии фрагментов (экспорт → импорт) сводятся в одну; исходные не меняются."""
    if len(set(fragment_ids)) < 2:
        raise ValueError("Для слияния нужно два или более разных фрагмента")
    missing = [f for f in fragment_ids
               if not await conn.fetchval("SELECT 1 FROM fragments WHERE id = $1", f)]
    if missing:
        raise LookupError(f"Фрагменты не найдены: {missing}")
    first: Optional[int] = None
    parts = []
    for fid in dict.fromkeys(fragment_ids):
        text, _ = await export_fragment_text(conn, fid)
        rep = await import_sections(conn, op, parse_tgid(text.encode("utf-8")))
        parts.append({"source_fileid": fid, "copy_fileid": rep["fileid"], "tables": rep["tables"],
                      "unresolved_refs": rep["unresolved_refs"]})
        if first is None:
            first = rep["fileid"]
            continue
        for table in FILEID_TABLES:
            if "fileid" in await _columns(conn, table):
                await conn.execute(f"UPDATE {_ident(table)} SET fileid = $1 WHERE fileid = $2", first, rep["fileid"])
        await conn.execute("DELETE FROM fragments WHERE id = $1", rep["fileid"])

    stamp = f"{dt.datetime.now():%Y_%m_%d %H:%M:%S}"
    final_name = f"{(name or 'Объединенный фрагмент')[:60]} {stamp}"
    await conn.execute("UPDATE fragments SET name = $1 WHERE id = $2", final_name, first)

    # Совпадающие коды (в десктопе не проверяются): одинаковое название в объединённом фрагменте
    dups = await conn.fetch(
        "SELECT name, array_agg(id ORDER BY id) AS ids FROM externalcodes "
        "WHERE fileid = $1 AND COALESCE(name, '') <> '' GROUP BY name HAVING count(*) > 1 ORDER BY name",
        first,
    )
    unified = 0
    if unify_external_codes and dups:
        ref_tables = [r["table_name"] for r in await conn.fetch(
            "SELECT table_name FROM information_schema.columns WHERE table_schema = 'public' "
            "AND column_name = 'externalcodeid' AND table_name IN "
            "(SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE')"
        )]
        for d in dups:
            keep, drop = d["ids"][0], d["ids"][1:]
            for table in ref_tables:
                if table in LIST_TAB:
                    # только строки, созданные этой операцией (копии) — исходные фрагменты не трогаем
                    await conn.execute(
                        f"UPDATE {_ident(table)} SET externalcodeid = $1 WHERE externalcodeid = ANY($2::int[])",
                        keep, drop,
                    )
            await conn.execute("DELETE FROM externalcodes WHERE id = ANY($1::int[])", drop)
            unified += len(drop)

    # Стыковые узлы (одинаковые x, y в разных исходных фрагментах) — десктоп их не сливает
    joint = await conn.fetchval(
        "SELECT count(*) FROM (SELECT x, y FROM nodes WHERE fileid = $1 AND internalnodeid IS NULL "
        "AND (x <> 0 OR y <> 0) GROUP BY x, y HAVING count(*) > 1) s",
        first,
    )
    counts = await _fragment_counts(conn, first)
    return {
        "fileid": first,
        "name": final_name,
        "parts": parts,
        "tables": counts,
        "created_nodes": counts.get("nodes", 0),
        "created_lines": counts.get("linesobj", 0),
        "duplicate_external_codes": [{"name": d["name"], "ids": list(d["ids"])} for d in dups],
        "unified_external_codes": unified,
        "coincident_node_positions": joint,
    }


async def _fragment_counts(conn, fileid: int) -> dict[str, int]:
    return {
        "nodes": await conn.fetchval("SELECT count(*) FROM nodes WHERE fileid = $1 AND COALESCE(removed, 0) = 0", fileid),
        "linesobj": await conn.fetchval(
            "SELECT count(*) FROM linesobj l JOIN nodes n ON n.id = l.nodeid1 "
            "WHERE n.fileid = $1 AND COALESCE(l.removed, 0) = 0", fileid),
        "externalcodes": await conn.fetchval("SELECT count(*) FROM externalcodes WHERE fileid = $1", fileid),
    }


async def fragment_summary(conn, fileid: int) -> dict[str, int]:
    """Число строк фрагмента по таблицам (для сверки экспорт → импорт)."""
    _, counts = await export_fragment_text(conn, fileid)
    counts.pop("heatsystem", None)
    counts.pop("fragments", None)
    return counts
