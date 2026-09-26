"""Прогон формы паспорта участка по одной на живой базе (только чтение).

Паспорт ведётся там, где трубы привязаны к участкам (heatpipesections.magistralSite /
distSite) — в базах Астаны. В Алматы привязок нет, паспорт там пустой по данным.

    cd itwin-api/itwin-api
    set -a; . ./.env; set +a
    DB_NAME=astanagid_2026_03_17 ./venv/Scripts/python.exe scripts/golden/passport_forms.py ms 19 [out.xlsx]
    FORMS=f10,f13 ... — только выбранные формы

Для каждой формы печатает число строк листа, время и первую ошибку SQL.
Код возврата 1, если хоть одна форма упала.
"""

from __future__ import annotations

import contextlib
import io
import logging
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "passport_module"))

import openpyxl  # noqa: E402

import connect  # noqa: E402
import db2  # noqa: E402
import ms1  # noqa: E402
import rs1  # noqa: E402
import sort_graph  # noqa: E402
import sql_pass  # noqa: E402
from passport_module import p as passport  # noqa: E402

FORMS = ["f1", "f2_1", "f2_2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12", "f13", "f14", "f15"]
WITH_NODES = {"f4", "f5"}


class _Grab(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.msgs: list[str] = []

    def emit(self, record):
        self.msgs.append(record.getMessage())


def main() -> int:
    ms_rs, site = sys.argv[1], int(sys.argv[2])
    out = sys.argv[3] if len(sys.argv) > 3 else None
    only = {f for f in os.getenv("FORMS", "").split(",") if f}
    grab = _Grab()
    logging.getLogger().addHandler(grab)

    c = {"rdbms": "postgreSQL"}  # параметры берутся из DB_* окружения
    conn = connect.connect(**c)
    wb = openpyxl.Workbook()
    title = wb.active
    title.title = "Паспорт"
    t = time.time()
    with contextlib.redirect_stdout(io.StringIO()):
        head = db2.read_q(conn, sql_pass.passport(ms_rs, site))
        (ms1.write_ms if ms_rs == "ms" else rs1.write_rs)(title, head)
        vals = passport.read_ms_rs(conn, ms_rs, site)
        graph = sort_graph.make_graph(conn, "", ms_rs, site)
    conn.close()
    if not graph or not graph[0]:
        print(f"{ms_rs}/{site}: у участка нет труб (make_graph пуст)")
        return 1
    mark_line, mark_node, mark_pts = graph
    print(f"{ms_rs}/{site}: граф {mark_line.count('),(') + 1} труб, "
          f"{mark_pts.count('),(') + 1} участков ПТС, {time.time() - t:.1f} с")

    failed = 0
    for name in FORMS:
        if only and name not in only:
            continue
        mod = __import__(name)
        ws = wb.create_sheet(name)
        grab.msgs.clear()
        t = time.time()
        err = ""
        try:
            args = [c, ws, ms_rs, site, "", mark_line, mark_pts]
            if name in WITH_NODES:
                args += [mark_node, vals]
            with contextlib.redirect_stdout(io.StringIO()):
                mod.do_passport(*args)
        except Exception as e:  # noqa: BLE001 — отчёт по каждой форме
            failed += 1
            err = f"ОШИБКА {type(e).__name__}: {str(e).splitlines()[0][:200]}"
        print(f"  {name:5} строк {ws.max_row:4}  {time.time() - t:5.1f} с  {err or 'ok'}")
    if out:
        wb.save(out)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
