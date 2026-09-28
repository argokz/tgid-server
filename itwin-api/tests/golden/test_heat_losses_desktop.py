"""Эталон нормативных теплопотерь: веб (database/heat_losses_norm.py) против десктопа gid8 poteriNewPg.

Десктоп считается в отдельном процессе исходниками gid8 (только чтение):
- `Controllers/exportController.py` — запросы всех листов Excel (init_* из DESKTOP_SHEETS: МатХар …
  ГодПотери, Нагрузка, Емкость, К(исп), ТехнПСВ/ТехнТП, ИТОГО, баки, заполнение, опрессовка, промывки,
  САРЗ) по представлениям и функциям `functions/new/*.sql`. Их нет в БД: процесс создаёт их в своей
  транзакции на копии БД и откатывает её (DDL в PostgreSQL транзакционен), так же заполняет
  TEMP_LINE/TEMP_NODE для режима «по фрагменту» и синтетические данные (баки, обвязка, САРЗ,
  заполнение, таблицы *Fact — на копии их нет). Нормы — через dblink к `sprav`, как у десктопа;
- `Controllers/mainController.py::set_cond_env_temperatures` — строки heatLosesSourceMonths
  («Условия работы») с подменённым DAO, без БД.

Веб читает те же таблицы (только чтение). Часть с БД пропускается без копии (`_this_is_copy`),
без каталога gid8 или БД `sprav`; путь к gid8 — переменная GID8_ROOT.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from database import heat_losses_norm as hl

API_ROOT = Path(__file__).resolve().parents[2]
GID8 = Path(os.environ.get("GID8_ROOT") or Path(__file__).resolve().parents[4] / "gid8")
POTERI = GID8 / "python" / "poteriNewPg"

pytestmark = pytest.mark.skipif(
    not (POTERI / "Controllers" / "exportController.py").exists(),
    reason=f"нет исходников десктопа poteriNewPg ({POTERI})",
)

# ---------------------------------------------------------------- общая обвязка процесса десктопа

_PRELUDE = r'''
import contextlib, ctypes, datetime, decimal, io, json, os, sys, tempfile, types
root = sys.argv[1]
sys.path.insert(0, root)
real_stdout = sys.stdout
sys.stdout = io.StringIO()          # десктоп печатает запросы и строку dblink с паролем
tmp = tempfile.mkdtemp(prefix="poteri_golden_")
import platformdirs
platformdirs.user_data_dir = lambda *a, **k: tmp  # лог DAO — во временный каталог
for name in ("xlwt", "xlrd", "xlutils", "xlutils.copy"):
    mod = types.ModuleType(name)
    mod.copy = lambda *a, **k: None
    mod.easyxf = lambda *a, **k: None
    sys.modules[name] = mod
props = types.ModuleType("DAO.connector.properties")
def _load(name):
    with open(os.path.join(root, name), encoding="utf8") as f:
        return json.load(f)
props.locale, props.tooltips, props.tableIndexes = _load("locale.json"), _load("tooltips.json"), _load("tableIndexes.json")
props.config = {"postgresql": json.loads(os.environ.get("GOLDEN_PG") or "{}")}
sys.modules["DAO.connector.properties"] = props
if hasattr(ctypes, "windll"):
    ctypes.windll.user32.MessageBoxW = lambda *a, **k: 0

def plain(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v

def rows(items):
    return [{k: plain(v) for k, v in r.items()} for r in (items or [])]

def emit(obj):
    real_stdout.buffer.write(json.dumps(obj, ensure_ascii=False).encode("utf-8"))
'''

_WORK_CONDITIONS = _PRELUDE + r'''
import DAO.DAO as daomod
class FakeDAO:
    graph = []
    def __init__(self): pass
    def getOneParamQuery(self, param, table, flag=False, order=None, where=None, params=None):
        if table == "heatSources":
            return [{"id": 0, "temperdwflowsummer": 0, "temperdwretsummer": 0}]
        if table == "deployedTempGraphs":
            full = [{"id": i, "q_otn": 0, "t3": 0, "tv": 0, "t_bn": 0, "tg": 0, **r} for i, r in enumerate(FakeDAO.graph)]
            return sorted(full, key=lambda r: (r["hsourceid"], r["tn"]))
        return []
    def delete(self, *a, **k): pass
daomod.DAO = FakeDAO
import Controllers.tempGraphController as tgc
tgc.DAO = FakeDAO
import Controllers.mainController as mcm
mcm.DAO = FakeDAO

class QD:
    def __init__(self, s):
        self.d = datetime.date.fromisoformat(s)
    def year(self): return self.d.year
    def month(self): return self.d.month
    def day(self): return self.d.day

cases = json.load(sys.stdin)
out = []
for case in cases:
    FakeDAO.graph = case["graph"]
    mc = mcm.MainController()
    got = []
    mc.insert_heat_loses_source_months = lambda hs, number, month, season, tn, tpod, tgr, tgP, tgO, wc: got.append(
        {"heatsourceid": hs, "r": number, "m": month, "sezon": season, "tn": tn, "tpod": tpod,
         "tgr": tgr, "tgp": tgP, "tgo": tgO, "workcount": wc})
    ok = mc.set_cond_env_temperatures(case["air"], case["podv"], case["ground"], QD(case["start"]),
                                      QD(case["end"]), case["hs"])
    out.append({"ok": ok, "rows": got})
emit(out)
'''

_EXPORT = _PRELUDE + r'''
from Controllers.exportController import ExportController
req = json.load(sys.stdin)
ec = ExportController()
ec.loses_type = req.get("loses_type") or "norm"
ec.season = req["season_id"]
ec.heat_source_name = "golden"
conn = ec.mdao._DAO__db._ConnectionPostgreSQL__connection
cur = conn.cursor()
cur.execute("SELECT to_regclass('_this_is_copy') IS NOT NULL")
if not cur.fetchone()[0]:
    raise SystemExit("не копия БД: нет таблицы-маркера _this_is_copy")
out = {}
try:
    base = os.path.join(root, "functions", "new")
    for rel in req["sql_files"]:
        with open(os.path.join(base, rel), encoding="utf-8-sig") as f:
            cur.execute(f.read())
    if req.get("fragment_id"):
        cur.execute("CREATE TABLE IF NOT EXISTS temp_line (id int PRIMARY KEY)")
        cur.execute("CREATE TABLE IF NOT EXISTS temp_node (id int PRIMARY KEY)")
        cur.execute("DELETE FROM temp_line")
        cur.execute("DELETE FROM temp_node")
        cur.execute("INSERT INTO temp_line (id) SELECT id FROM linesobj WHERE fileid = %s AND removed = 0",
                    (req["fragment_id"],))
        cur.execute("INSERT INTO temp_node (id) SELECT id FROM nodes WHERE fileid = %s", (req["fragment_id"],))
    for m in req.get("months") or []:
        cur.execute("INSERT INTO heatlosessourcemonths (heatsourceid, r, m, sezon, tn, tpod, tgr, tgp, tgo, workcount) "
                    "VALUES (%(heatsourceid)s, %(r)s, %(m)s, %(sezon)s, %(tn)s, %(tpod)s, %(tgr)s, %(tgp)s, %(tgo)s, "
                    "%(workcount)s)", m)
    for hs in req.get("hls_insert") or []:
        cur.execute("INSERT INTO heatlosessource (heatsourceid, t_percent) VALUES (%s, %s)", (hs, 0))
    for stmt in req.get("setup_sql") or []:
        cur.execute(stmt)
    frag = "yes" if req.get("fragment_id") else "no"
    for hs in req["heat_sources"]:
        s = str(hs)
        sheets, errors = {}, {}
        for key, method, with_frag in req["sheets"]:
            cur.execute("SAVEPOINT golden_sheet")
            try:
                fn = getattr(ec, method)
                sheets[key] = rows(fn(s, frag) if with_frag else fn(s))
                cur.execute("RELEASE SAVEPOINT golden_sheet")
            except Exception as e:  # SQL десктопа для fact частично нерабочий — фиксируем ошибку листа
                cur.execute("ROLLBACK TO SAVEPOINT golden_sheet")
                errors[key] = str(e).splitlines()[0][:300]
        out[s] = {"sheets": sheets, "errors": errors}
finally:
    conn.rollback()
emit(out)
'''

SQL_FILES_FULL = [
    "_functions/UT_KTP_OUT_view.sql", "_functions/get_qq_interp.sql", "_functions/get_qq_interp2.sql",
    "_functions/getmon.sql", "_functions/getTypnet.sql", "_functions/getCoeff.sql",
    "_view/real.sql", "_view/tempView.sql", "_view/heatPipeSectionIst.sql", "_view/normmon.sql",
    "_view/losesVolumesView.sql", "_view/avgHeatLosesMonth.sql", "_view/psvView.sql", "_view/tankbatteryView.sql",
]
SQL_FILES_FRAGMENT = SQL_FILES_FULL + [
    "_view/heatPipeSectionIstFragment.sql", "_view/normmonFragment.sql",
    "_view/losesVolumesViewFragment.sql", "_view/avgHeatLosesMonthFragment.sql",
    "_view/psvViewFragment.sql", "_view/tankbatteryViewFragment.sql",
]
SQL_FILES_FACT = SQL_FILES_FULL + [
    "_view/tempViewFact.sql", "_view/heatPipeSectionIstFact.sql", "_view/normmonFact.sql",
    "_view/losesVolumesViewFact.sql", "_view/avgHeatLosesMonthFact.sql", "_view/tankbatteryViewFact.sql",
]

# лист веба, метод exportController, передаётся ли признак «по фрагменту»
DESKTOP_SHEETS = [
    ("material_characteristics", "init_material_characteristics", True),
    ("month_temperatures", "init_month_temperatures", False),
    ("winter_norms", "init_winter_norms", True), ("summer_norms", "init_summer_norms", True),
    ("avg_month_loses", "init_avg_month_loses", True), ("avg_year_loses", "init_avg_year_loses", True),
    ("loads", "init_loads", True), ("capacities", "init_capacities", True),
    ("heat_tests", "init_heat_tests", False), ("repair_heat_tests", "init_repair_heat_tests", False),
    ("net_water_loses", "init_net_water_loses", True), ("net_water_year_loses", "init_net_water_year_loses", True),
    ("overalls", "init_overalls", True), ("tank_batteries", "init_tank_batteries", True),
    ("tank_batteries_loses", "init_tank_batteries_loses", True), ("fillings", "init_fillings", True),
    ("pressings", "init_pressings", True), ("flushings_hs", "init_flushings_hs", True),
    ("flushings", "init_flushings", True), ("sarz_flows", "init_sarz_flows", False),
    ("sarz_rets", "init_sarz_rets", False),
]


def _run_desktop(script: str, payload, with_db: bool = False):
    """Процесс десктопа; реквизиты БД — только через окружение (не аргументы: pytest печатает аргументы)."""
    env = dict(os.environ)
    secret = None
    if with_db:
        db = _db_env() or {}
        secret = db.get("DB_PASSWORD")
        env["GOLDEN_PG"] = json.dumps({"host": db.get("DB_HOST"), "user": db.get("DB_USER"), "password": secret,
                                       "port": int(db.get("DB_PORT") or 5432), "db": db.get("DB_NAME")})
    proc = subprocess.run(
        [sys.executable, "-c", script, str(POTERI)], input=json.dumps(payload, default=str).encode(),
        capture_output=True, cwd=str(POTERI), timeout=900, env=env,
    )
    err = proc.stderr.decode("utf-8", "replace")
    if secret:
        err = err.replace(secret, "***")
    if proc.returncode != 0:
        pytest.fail("процесс десктопа завершился с ошибкой:\n" + err[-3000:], pytrace=False)
    return json.loads(proc.stdout.decode("utf-8"))


# ---------------------------------------------------------------- «Условия работы» без БД

GRAPH = [{"hsourceid": 7, "tn": float(tn), "t1": 70 + 2.5 * (8 - tn), "t2": 45 + 0.9 * (8 - tn)}
         for tn in range(-25, 9)]
CLIMATE = [(-6.8, 5, 7.2), (-5.1, 5, 5.9), (1.9, 5, 5.2), (10.7, 10, 7.7), (16.2, 15, 10.9), (20.9, 15, 13.8),
           (23.1, 15, 16.0), (22.3, 15, 17.4), (17.0, 15, 16.6), (9.6, 10, 15.5), (1.1, 5, 12.3), (-4.4, 5, 8.9)]
SEASONS = [("2025-10-15", "2026-04-15"), ("2024-10-01", "2025-04-30"), ("2023-10-20", "2024-04-10")]


def test_work_conditions_match_desktop():
    cases = []
    for start, end in SEASONS:
        cases.append({
            "graph": GRAPH, "hs": 7, "start": start, "end": end,
            "air": [{"tn": c[0]} for c in CLIMATE], "podv": [{"tpod": c[1]} for c in CLIMATE],
            "ground": [{"tgr": c[2]} for c in CLIMATE],
        })
    ref = _run_desktop(_WORK_CONDITIONS, cases)
    map_tg, bounds = hl.temp_graph_maps(GRAPH)
    climate = [{"m": i + 1, "tn": c[0], "tpod": c[1], "tgr": c[2]} for i, c in enumerate(CLIMATE)]
    for (start, end), r in zip(SEASONS, ref):
        assert r["ok"] is True
        web = hl.work_condition_months(7, climate, date.fromisoformat(start), date.fromisoformat(end), map_tg, bounds)
        assert len(web) == len(r["rows"]) == 14
        for w, d in zip(web, r["rows"]):
            for k in ("heatsourceid", "r", "m", "sezon", "workcount"):
                assert w[k] == d[k], (start, k, w, d)
            for k in ("tn", "tpod", "tgr", "tgp", "tgo"):
                assert w[k] == pytest.approx(d[k], abs=1e-9), (start, k)


def test_temp_graph_lookup_is_first_point_not_interpolation():
    map_tg, bounds = hl.temp_graph_maps(GRAPH)
    # desktop get_temp_graph: интерполяционная ветка недостижима (tn2 = tn1 + 1 > tn1) — берётся точка сетки
    assert hl.temp_graph_at(map_tg, bounds, 7, -6.8) == (GRAPH[19]["t1"], GRAPH[19]["t2"])  # tn = -6
    assert hl.temp_graph_at(map_tg, bounds, 7, 30) == (GRAPH[-1]["t1"], GRAPH[-1]["t2"])
    assert hl.temp_graph_at(map_tg, bounds, 7, -40) == (GRAPH[0]["t1"], GRAPH[0]["t2"])
    assert hl.temp_graph_at(map_tg, bounds, 99, 0) == (None, None)


# ---------------------------------------------------------------- листы Excel на копии БД


def _db_env() -> dict | None:
    try:
        from dotenv import dotenv_values
    except ImportError:
        return None
    env = {**dotenv_values(API_ROOT / ".env"), **dotenv_values(API_ROOT / ".env.copy")}
    if not env.get("DB_NAME") or not env.get("DB_PASSWORD"):
        return None
    return {k: v for k, v in env.items() if v is not None}


async def _connect(database: str | None = None):
    import asyncpg
    env = _db_env() or {}
    return await asyncpg.connect(user=env.get("DB_USER"), password=env.get("DB_PASSWORD"), host=env.get("DB_HOST"),
                                 port=int(env.get("DB_PORT") or 5432), database=database or env.get("DB_NAME"))


async def _web(season_id, sources, fragment_id=None, extra_months=None, extra_hls=None, setup_sql=None,
               loses_type="norm"):
    conn = await _connect()
    try:
        if not await conn.fetchval("SELECT to_regclass('_this_is_copy') IS NOT NULL"):
            pytest.skip("не копия БД")
        sprav = await _connect("sprav")
        try:
            norms = await hl.load_norms(sprav)
        finally:
            await sprav.close()
        tr = conn.transaction()
        await tr.start()
        try:  # синтетика — только внутри откатываемой транзакции копии
            for stmt in setup_sql or []:
                await conn.execute(stmt)
            inputs = await hl.load_inputs(conn, season_id=season_id, heat_source_ids=sources,
                                          fragment_id=fragment_id, norms=norms, loses_type=loses_type)
        finally:
            await tr.rollback()
        if extra_months:
            inputs.months = inputs.months + extra_months
        if extra_hls:
            inputs.hls_rows = inputs.hls_rows + [{"heatsourceid": hs, "t_percent": 0.0} for hs in extra_hls]
            for s in inputs.sections:  # новый heatLosesSource — коэффициенты по умолчанию (1), как DEFAULT в БД
                if s["heatsourceid"] in extra_hls:
                    s.update({"coeffdefault": 1, **{c: 1.0 for c in hl.COEFF_COLUMNS}})
            hl.section_coefficients(inputs.sections)
        climate = None
        if fragment_id is not None:
            climate = [dict(r) for r in await conn.fetch(
                "SELECT m, tn, tpod, tgr FROM heatloses WHERE heatlosesmainid IS NULL ORDER BY m")]
        return inputs, climate
    finally:
        await conn.close()


def _close(a, b, rel=1e-9, abs_=1e-9):
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))


def _cmp_rows(web_rows, ref_rows, key_fields, num_fields, rounded=None, what=""):
    rounded = rounded or {}
    assert len(web_rows) == len(ref_rows), f"{what}: строк {len(web_rows)} ≠ {len(ref_rows)}"
    keyf = lambda r: tuple((r.get(k) is None, str(r.get(k))) for k in key_fields)
    for w, d in zip(sorted(web_rows, key=keyf), sorted(ref_rows, key=keyf)):
        for k in key_fields:
            assert str(w.get(k)) == str(d.get(k)), (what, k, w, d)
        for k in num_fields:
            tol = rounded.get(k)
            if tol is not None:
                ok = _close(w.get(k), d.get(k), rel=0, abs_=tol)
            else:
                ok = _close(w.get(k), d.get(k))
            assert ok, (what, k, w.get(k), d.get(k), d)


MAT_NUM = ("lenp_n", "leno_n", "lenpodzp", "lenpodzo", "lenall", "len_tr", "mn_p", "mn_o", "mp_p", "mp_o", "m", "vv")
NORM_NUM = ("lennp", "lenno", "qnp", "qno", "potnp", "potno", "lenkp", "lenko", "qk", "lenbp", "lenbo", "qb", "potp")
LOSS_NUM = ("potnp", "potno", "potpodz", "potall", "v1", "vall")


TIGHT = "tight"  # числа без округления в SQL; остальные — ROUND(…, 2): допуск 0.0101


def _spec(*fields):
    """Поле: "name" (строка) или ("web", "desktop") / ("web", "desktop", TIGHT) / ("key", TIGHT)."""
    out = []
    for f in fields:
        if isinstance(f, str):
            out.append((f, f, "s"))
        elif len(f) == 2 and f[1] == TIGHT:
            out.append((f[0], f[0], TIGHT))
        else:
            out.append((f[0], f[1], f[2] if len(f) > 2 else "n"))
    return out


def _nums(*keys, tight=False):
    return [(k, TIGHT) if tight else (k, k) for k in keys]


def _sarz(sfx):
    return _spec("monthname", *[(k, f"{k}{sfx}", TIGHT) for k in ("netwaterexp", "workcount", "regcount",
                                                                  "regcountnode")],
                 ("avggsarzg", f"avggsarzg{sfx}"), ("avggsarznodeg", f"avggsarznodeg{sfx}"),
                 ("avggsarzgall", f"avggsarzg{sfx}all"), ("tgp", "tgp"), ("tn", "tn"), ("qsarz", "qsarz"))


WATER_SPECS = {
    "loads": _spec("heatsourcename", *_nums("got_pr", "gvent_pr", "ggvs_pr", tight=True)),
    "capacities": _spec("name", *_nums("v1", "v2", "vpodv", tight=True),
                        *_nums("v1leto", "v2leto", "vpodvleto", "vob", "vobleto", "vot", "votleto", "vvent",
                               "vventleto", "vgvs", "vgvsleto", "vall", "vallleto", "podp", "podpleto")),
    "heat_tests": _spec("name", *_nums(*hl.HEAT_TEST_COLUMNS, tight=True)),
    "repair_heat_tests": _spec("name", *[(c, c + "_r", TIGHT) for c in hl.HEAT_TEST_COLUMNS]),
    "net_water_loses": _spec("monthname", *_nums(*hl.PSV_G_KEYS, tight=True), ("gall", "gall")),
    # ПСВ2.sql: колонка Gall — сумма G, а не Q (десктоп читает «Qall» и оставляет итог пустым); веб — сумма Q
    "net_water_year_loses": _spec("monthname", *_nums(*hl.PSV_Q_KEYS, tight=True)),
    "overalls": _spec("monthname", ("season", TIGHT), *_nums("normq", "normg", tight=True),
                      *_nums("isolq", "qtb", "reglq", "reglg", "gall", "allq")),
    "tank_batteries": _spec("name", "mesto", *_nums("designcapacity", "quantity", "height", "diameter", tight=True)),
    "tank_batteries_loses": _spec("monthname", ("workcount", TIGHT),
                                  *_nums("tn", "tgo", "monthloses", "yearloses")),
    "fillings": _spec("monthname", *_nums("magistralshare", "distsiteshare", "heatingsystemshare", "nettemperature",
                                          "tx", tight=True),
                      *_nums("gmag", "grs", "gtep", "qms", "qrs", "qtep")),
    "pressings": _spec("monthname", "opr", *_nums("tset", "percent1", tight=True),
                       *_nums("tn", "v1", "v2", "vpodv", "vobm", "vobr", "vall", "avgqpressing")),
    "flushings_hs": _spec("monthname", ("flushinghs_temp1", TIGHT),
                          *_nums("tn", "flushinghs", "vot1", "vot2", "vall", "q")),
    "flushings": _spec("monthname", ("kolv", TIGHT),
                       *_nums("flushing_temp1", "tn", "flushing", "v1", "v2", "vpodv", "vobm", "vobr", "vall", "q")),
    "sarz_flows": _sarz("flow"),
    "sarz_rets": _sarz("ret"),
}


def _cmp_multiset(web_rows, ref_rows, spec, what):
    """Сравнение строк без учёта порядка (у части запросов десктопа нет ORDER BY)."""
    assert len(web_rows) == len(ref_rows), f"{what}: строк {len(web_rows)} ≠ {len(ref_rows)}"

    def key(r, side):
        out = []
        for w, d, kind in spec:
            v = r.get(w if side == 0 else d)
            out.append((0, str(v)) if kind == "s" else (1, "" if v is None else f"{float(v):.1f}"))
        return out

    for w, d in zip(sorted(web_rows, key=lambda r: key(r, 0)), sorted(ref_rows, key=lambda r: key(r, 1))):
        for wk, dk, kind in spec:
            a, b = w.get(wk), d.get(dk)
            if kind == "s":
                assert str(a) == str(b), (what, wk, w, d)
            elif kind == TIGHT:
                assert _close(a, b, rel=1e-8, abs_=1e-9), (what, wk, a, b, d)
            else:
                assert _close(a, b, rel=0, abs_=0.0101), (what, wk, a, b, d)


def _compare_water(web: dict, ref_sheets: dict, hs: int, keys=None, relaxed=False):
    """relaxed: *_fact.sql десктопа местами округляют (ROUND(…, 2)) то, что в norm не округлено."""
    for sheet, spec in WATER_SPECS.items():
        if (keys is not None and sheet not in keys) or sheet not in ref_sheets:
            continue
        if relaxed:
            spec = [(w, d, "n" if kind == TIGHT else kind) for w, d, kind in spec]
            # tempViewFact даёт месячным строкам m = 13/14 (номер периода): у десктопа в названии месяца —
            # период, САРЗ не находит температур по r, листы с отбором по месяцу (опрессовка, промывки) пусты
            spec = [f for f in spec if f[0] not in ("monthname", "tgp", "tn", "qsarz")]
        _cmp_multiset([r for r in web[sheet] if r["heatsourceid"] == hs], ref_sheets[sheet], spec, f"{sheet} {hs}")


def _compare_sheets(web: dict, ref: dict, sources: list[int]):
    for hs in sources:
        assert not ref[str(hs)]["errors"], ref[str(hs)]["errors"]
        d = ref[str(hs)]["sheets"]
        _compare_water(web, d, hs)
        pick = lambda key: [r for r in web[key] if r["heatsourceid"] == hs]
        _cmp_rows(pick("material_characteristics"), d["material_characteristics"],
                  ("typnet1", "diameterexternal", "diameterinternal"), MAT_NUM, what=f"МатХар {hs}")
        _cmp_rows(pick("month_temperatures"), d["month_temperatures"], ("m1", "sezon1", "workcount", "tn"),
                  ("tpod", "tgr", "tgp", "tgo", "tx"), rounded={k: 0.1001 for k in ("tpod", "tgr", "tgp", "tgo", "tx")},
                  what=f"МесТемп {hs}")
        for sheet in ("winter_norms", "summer_norms"):
            _cmp_rows(pick(sheet), d[sheet], ("typnet1", "a5000", "diametercondit"), NORM_NUM,
                      rounded={k: 0.0101 for k in NORM_NUM if not k.startswith("pot")} | {
                          k: 0.101 for k in NORM_NUM if k.startswith("pot")}, what=f"{sheet} {hs}")
        # МесПотери/ГодПотери: порядок строк ORDER BY r — сравнение по порядку
        for sheet in ("avg_month_loses", "avg_year_loses"):
            w_rows, d_rows = pick(sheet), d[sheet]
            assert [r["monthname"] for r in w_rows] == [r["monthname"] for r in d_rows], sheet
            for w, r in zip(w_rows, d_rows):
                for k in LOSS_NUM:
                    ok = _close(w[k], r[k], abs_=0.0101) if sheet == "avg_year_loses" else _close(w[k], r[k], rel=1e-8)
                    assert ok, (sheet, hs, w["monthname"], k, w[k], r[k])


@pytest.fixture(scope="module")
def db_env():
    """Только признак доступности: реквизиты не передаются через аргументы (pytest печатает их)."""
    if _db_env() is None:
        pytest.skip("нет .env/.env.copy с доступом к копии БД")
    return True


def test_sheets_match_desktop_whole_network(db_env):
    """Источники с заполненными «Условиями работы» на копии, сезон 2, режим без фрагмента."""
    sources = [1, 3, 48, 49, 63, 64]
    inputs, _ = asyncio.run(_web(2, sources))
    if not inputs.months:
        pytest.skip("на копии нет heatLosesSourceMonths")
    web = hl.compute(inputs)
    ref = _run_desktop(_EXPORT, {"season_id": 2, "heat_sources": sources, "sql_files": SQL_FILES_FULL,
                                 "sheets": DESKTOP_SHEETS}, with_db=True)
    _compare_sheets(web, ref, sources)
    # сверка итогов: сумма потерь участков = потерям источника (Гкал/ч, отопительный период)
    for hs in sources:
        per_sections = sum(
            s["q"] * s["dlina"] * s["beta"] * s["kti"] / 1e6 for s in web["sections"]
            if s["heatsourceid"] == hs and None not in (s["q"], s["dlina"], s["beta"], s["kti"]))
        annual = [r for r in web["avg_month_loses"] if r["heatsourceid"] == hs and r["m"] == 15]
        if annual and annual[0]["potall"] is not None:
            assert per_sections == pytest.approx(annual[0]["potall"], rel=1e-9)


def test_sheets_match_desktop_fragment_74(db_env):
    """Фрагмент 74 («по фрагменту»): «Условия работы» источников строятся портом set_cond_env_temperatures
    и вставляются в транзакцию десктопа, которая откатывается."""
    inputs, climate = asyncio.run(_web(2, None, fragment_id=74))
    sources = inputs.heat_source_ids
    if not sources or not climate or len(climate) != 12:
        pytest.skip("нет участков фрагмента 74 или климата")

    async def graphs():
        conn = await _connect()
        try:
            return [dict(r) for r in await conn.fetch(
                "SELECT hsourceid, tn, t1, t2 FROM deployedtempgraphs WHERE hsourceid = ANY($1::int[])", sources)]
        finally:
            await conn.close()

    map_tg, bounds = hl.temp_graph_maps(asyncio.run(graphs()))
    missing = [hs for hs in sources if not any(m["heatsourceid"] == hs for m in inputs.months)]
    months = []
    for hs in missing:
        months += hl.work_condition_months(hs, climate, date(2025, 10, 15), date(2026, 4, 15), map_tg, bounds)
    for m in months:
        m["tx"] = 0.0  # DEFAULT heatlosessourcemonths.tx
    no_hls = [hs for hs in sources if not any(h["heatsourceid"] == hs for h in inputs.hls_rows)]
    inputs, _ = asyncio.run(_web(2, sources, fragment_id=74, extra_months=months, extra_hls=no_hls))
    web = hl.compute(inputs)
    assert web["sections"], "по фрагменту 74 нет строк ut_teplo_out"
    ref = _run_desktop(_EXPORT, {"season_id": 2, "heat_sources": sources, "sql_files": SQL_FILES_FRAGMENT,
                                 "fragment_id": 74, "months": months, "hls_insert": no_hls,
                                 "sheets": DESKTOP_SHEETS}, with_db=True)
    _compare_sheets(web, ref, sources)


# ---------------------------------------------------------------- синтетика: листы по воде и фактические потери

SYNTH_SOURCE, SYNTH_SEASON = 48, 2


def _synthetic_sql(hs: int, season: int) -> list[str]:
    """Баки, обвязка, САРЗ, заполнение, промывка источника hs (на копии этих данных нет).

    Остальные сезоны и «Условия работы» других источников удаляются (в транзакции): десктоп соединяет
    баки со всеми сезонами (ON 1=1) и берёт среднегодовую температуру любого источника (tankbattery2.sql).
    """
    return [
        f"DELETE FROM heatlosesmain WHERE id <> {season}",
        f"DELETE FROM heatlosessourcemonths WHERE heatsourceid <> {hs}",
        "UPDATE heatlosessourcemonths SET netwaterexpflow = 0.4 + r * 0.01, regcountflow = 3, workcountflow = 10 + r, "
        "regcountnodeflow = 2, netwaterexpret = 0.3, regcountret = 1, workcountret = 5 + r, regcountnoderet = 4 "
        f"WHERE heatsourceid = {hs}",
        "UPDATE losesbyfilling SET magistralshare = 10 + monthid, distsiteshare = 5, heatingsystemshare = 2.5, "
        f"nettemperature = 60 WHERE heatsourceid = {hs}",
        "UPDATE heatlosessource SET t_percent = 60, flushing_flow = 1, flushing_ret = 0, spring_pressing = 60, "
        f"autumn_pressing = 40 WHERE heatsourceid = {hs}",
        "INSERT INTO heatpipesectionsharness (heatsourceid, diameterexternal, diameterinternal, belongms, pipesectlength) "
        f"VALUES ({hs}, 219, 207, 1, 120.5), ({hs}, 159, 150, 2, 80), ({hs}, 108, 100, NULL, 40)",
        "INSERT INTO tankbatteries (designcapacity, quantity, height, diameter, nodeid, shape) "
        "SELECT 1000 * k, 2, 12000, 10430 - k * 100, n.id, ST_SetSRID(ST_MakePoint(0, 0), 9998) "
        "FROM (SELECT n.id FROM nodes n JOIN externalcodes ec ON ec.id = n.externalcodeid "
        f"WHERE ec.heatsourceid = {hs} AND ec.objectid <> 2 AND n.removed = 0 ORDER BY n.id LIMIT 2) n, "
        "generate_series(1, 2) k",
    ]


def _fact_copy_sql(hs: int, season: int) -> list[str]:
    """Таблицы *Fact = копия нормативных данных источника (после синтетики)."""
    out = []
    for fact, norm, where in (("heatlosesmainfact", "heatlosesmain", f"id = {season}"),
                              ("heatlosessourcefact", "heatlosessource", f"heatsourceid = {hs}"),
                              ("heatlosessourcemonthsfact", "heatlosessourcemonths", f"heatsourceid = {hs}"),
                              ("losesbyfillingfact", "losesbyfilling", f"heatsourceid = {hs}"),
                              ("heatpipesectionsharnessfact", "heatpipesectionsharness", f"heatsourceid = {hs}")):
        out += [f"DELETE FROM {fact}", f"INSERT INTO {fact} SELECT * FROM {norm} WHERE {where}"]
    return out


def _assert_same(a, b, path):
    """Равенство результатов с допуском на порядок суммирования SUM в PostgreSQL."""
    if isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            _assert_same(a[k], b[k], f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            _assert_same(x, y, f"{path}[{i}]")
    elif isinstance(a, float) or isinstance(b, float):
        assert _close(a, b, rel=1e-9, abs_=1e-9), (path, a, b)
    else:
        assert a == b, (path, a, b)


def test_water_sheets_match_desktop_synthetic(db_env):
    """Листы по воде на синтетике источника 48 (баки, обвязка, САРЗ, заполнение) против десктопа."""
    setup = _synthetic_sql(SYNTH_SOURCE, SYNTH_SEASON)
    inputs, _ = asyncio.run(_web(SYNTH_SEASON, [SYNTH_SOURCE], setup_sql=setup))
    if not inputs.months or not inputs.tanks:
        pytest.skip("нет «Условий работы» или узлов для баков у источника 48")
    web = hl.compute(inputs)
    assert web["tank_batteries"] and web["sarz_flows"] and any(r["qtb"] for r in web["overalls"])
    ref = _run_desktop(_EXPORT, {"season_id": SYNTH_SEASON, "heat_sources": [SYNTH_SOURCE],
                                 "sql_files": SQL_FILES_FULL, "setup_sql": setup, "sheets": DESKTOP_SHEETS},
                       with_db=True)
    _compare_sheets(web, ref, [SYNTH_SOURCE])


def test_fact_losses_synthetic(db_env):
    """Фактические потери: на копии таблицы *Fact пусты — заполняются копией синтетики в откатываемой
    транзакции. Веб (fact) = веб (norm) по всем листам; с десктопом (fact) сверяются листы, SQL которых
    у десктопа выполняется (остальные ссылаются на отсутствующие psvViewFact и колонки)."""
    setup = _synthetic_sql(SYNTH_SOURCE, SYNTH_SEASON)
    norm_inputs, _ = asyncio.run(_web(SYNTH_SEASON, [SYNTH_SOURCE], setup_sql=setup))
    fact_setup = setup + _fact_copy_sql(SYNTH_SOURCE, SYNTH_SEASON)
    fact_inputs, _ = asyncio.run(_web(SYNTH_SEASON, [SYNTH_SOURCE], setup_sql=fact_setup, loses_type="fact"))
    if not fact_inputs.months:
        pytest.skip("нет «Условий работы» источника 48")
    assert fact_inputs.loses_type == "fact" and fact_inputs.tanks
    norm, fact = hl.json_safe(hl.compute(norm_inputs)), hl.json_safe(hl.compute(fact_inputs))
    _assert_same(fact, norm, "fact")
    ref = _run_desktop(_EXPORT, {"season_id": SYNTH_SEASON, "heat_sources": [SYNTH_SOURCE], "loses_type": "fact",
                                 "sql_files": SQL_FILES_FACT, "setup_sql": fact_setup, "sheets": DESKTOP_SHEETS},
                       with_db=True)[str(SYNTH_SOURCE)]
    web = hl.compute(fact_inputs)
    ok = set(ref["sheets"]) - {"pressings", "flushings_hs", "flushings"}
    assert {"material_characteristics", "month_temperatures", "heat_tests", "loads", "sarz_flows",
            "tank_batteries_loses"} <= ok, ref["errors"]
    _compare_water(web, ref["sheets"], SYNTH_SOURCE, keys=ok, relaxed=True)
