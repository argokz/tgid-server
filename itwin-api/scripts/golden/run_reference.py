"""Эталонный набор расчётов sety: снять эталоны и сверить с ними любую поставку sety одной командой.

    venv/Scripts/python.exe scripts/golden/run_reference.py list
    venv/Scripts/python.exe scripts/golden/run_reference.py capture [--cases almaty74_plan,...]
    venv/Scripts/python.exe scripts/golden/run_reference.py check [--sety-root <каталог, где лежит sety/>]
    venv/Scripts/python.exe scripts/golden/run_reference.py compare --new-dir <снимки другой проверки>

capture — считает случаи (CASES) и сохраняет снимки в каталог эталонов; check — считает те же
случаи заново (по умолчанию текущим кодом, --sety-root — другой поставкой sety) и сверяет со
снимками compare_calc.compare_snapshots: допуски по напору/расходу/температуре/нагрузке,
нагрузки b101–b106, баланс и сообщения протокола. Код возврата 0 — всё совпало.

Запуск — как у воркера (worker._sety_base_cmd + sety_modes.build_sety_args): пароль только
из окружения (DB_PASSWORD из --env), не аргументом. Пишет расчёты ТОЛЬКО в базы *_copy —
другие имена отклоняются без возможности обойти. Перед каждым случаем — прогрев тем же
расчётом: sety берёт источник у узлов с заданным напором из ПОСЛЕДНЕГО расчёта (read_zn0),
прогрев делает это состояние одинаковым. Чужие расчёты в той же копии за время прогона
записываются в meta.json (foreign_calcs); при расхождении отчёт просит переснять.

Снимки лежат ВНЕ репозитория (репозиторий публичный, а это расчёт реальной сети): каталог
--ref-dir, по умолчанию $SETY_GOLDEN_DIR или <tgid-app>/golden/sety.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.golden import compare_calc  # noqa: E402

DEFAULT_REF_DIR = Path(os.environ.get("SETY_GOLDEN_DIR") or ROOT.parents[1] / "golden" / "sety")
AUTHOR = "golden"


@dataclass(frozen=True)
class Case:
    name: str
    db: str
    fragment: int
    tn: float
    request: dict = field(default_factory=dict)  # поля sety_modes.SetyRunRequest, кроме fragment_ids/tn
    note: str = ""

    @property
    def dross(self) -> bool:
        return self.request.get("mode", "plan") == "plan"


# Tн −20 у Алматы: при −25…−30 sety останавливается проверкой «должна быть от −25 до 8» у части графиков.
CASES: tuple[Case, ...] = (
    Case("almaty74_plan", "almatygid_copy", 74, -20, {"mode": "plan"},
         "Алматы, фрагмент 74 — плановый (нагрузки, регуляторы, теплопотери)"),
    Case("almaty72_plan", "almatygid_copy", 72, -20, {"mode": "plan"},
         "Алматы, фрагмент 72 — плановый, крупная сеть (8 тыс. узлов)"),
    Case("almaty74_fact", "almatygid_copy", 74, -20, {"mode": "emergency", "consumer_resistance": "equivalent"},
         "Алматы, фрагмент 74 — фактический, эквивалентные сопротивления потребителей (pt_out2, подпитка)"),
    Case("shatura3252_plan", "shatura_copy", 3252, -25, {"mode": "plan"},
         "Шатура, фрагмент 3252 «Тепловые сети» — плановый"),
    Case("astana_plan", "astanagid_copy", 3179, -20, {"mode": "plan"},
         "Астана, магистрали 3179 — нужна копия astanagid_copy (см. docs/sety-golden-reference.md)"),
)

# Таблицы и ключи строк, которые пишет sety (w_out2.w_out, dross1) — как compare_calc.ALL_TABLES.
TABLES = compare_calc.ALL_TABLES

# Вход, от которого зависит расчёт помимо исходных данных: источник узлов с заданным напором из
# последнего расчёта фрагмента, где лежит одноимённый узел (тот же запрос, что sety/read_zn.read_zn0).
READ_ZN0_SQL = """
SELECT ec.id, max(usP.ist) AS ist
FROM setPressNodes zn
JOIN nodes n ON n.id = zn.nodeid
JOIN externalCodes ec ON ec.id = n.externalCodeID
JOIN (SELECT n0.id, ec0.name AS kod, n0.externalnodename AS name, n0.fileID
      FROM nodes n0 JOIN externalCodes ec0 ON ec0.id = n0.externalCodeID) n0
  ON n0.kod = ec.name AND n0.name = n.externalnodename
LEFT JOIN (SELECT c.fileID, max(c.id) AS cid FROM calculation c GROUP BY c.fileID) calc ON calc.fileID = n0.fileid
JOIN us_out usP ON usP.nodeID = n0.id AND usP.externalSign = 1 AND usP.calculationid = cid
WHERE n.fileid = $1
GROUP BY ec.id
ORDER BY ec.id
"""

# Граничные условия узлов с заданным напором: напоры, температуры и источник одноимённого узла
# фрагмента-магистрали (setPressNodes.fragment_resultID) из ПОСЛЕДНЕГО его расчёта — тот же
# подзапрос, что в sety/read_gid.py (чтение setPressNodes). Магистралью может быть сам фрагмент.
MAGISTRAL_SQL = """
SELECT DISTINCT sp.fragment_resultid FROM setPressNodes sp JOIN nodes n ON n.id = sp.nodeID
WHERE n.fileID = $1 AND n.removed = 0 AND sp.fragment_resultid IS NOT NULL
"""
BOUNDARY_SQL = """
SELECT n.id, sp.fragment_resultid, us2.calc_id, round(us2.pihP::numeric, 4) AS pihp, round(us2.pihO::numeric, 4) AS piho,
       round(us2.t1P::numeric, 4) AS t1p, round(us2.t1O::numeric, 4) AS t1o, us2.ist
FROM setPressNodes sp
JOIN nodes n ON n.id = sp.nodeID
JOIN externalCodes ec ON ec.id = n.externalCodeID
LEFT JOIN (
  SELECT n2.fileID, ec2.name AS kod, n2.externalNodeName AS name, calc.cid AS calc_id,
         usP.pih AS pihP, usP.t AS t1P, usO.pih AS pihO, usO.t AS t1O, usP.ist
  FROM nodes n2
  JOIN externalCodes ec2 ON ec2.id = n2.externalCodeID
  JOIN us_out usP ON usP.nodeID = n2.id AND usP.externalSign = 1
  JOIN us_out usO ON usO.nodeID = n2.id AND usO.externalSign = 2
  JOIN (SELECT c.fileID, max(c.id) AS cid FROM calculation c GROUP BY c.fileID) calc
    ON n2.fileID = calc.fileID AND usP.calculationID = calc.cid AND usO.calculationID = calc.cid
) us2 ON us2.kod = sp.kod_m AND us2.name = sp.uzel_m AND us2.fileID = sp.fragment_resultID
WHERE n.fileID = $1 AND n.removed = 0
ORDER BY n.id
"""


def check_copy_db(db: str) -> None:
    """Расчёт пишет в базу: только копии (*_copy)."""
    if not db.endswith("_copy"):
        raise SystemExit(f"База {db}: эталоны считаются только на копиях (*_copy), рабочие базы не трогаем")


def sety_hash(sety_root: Path) -> str:
    """Отпечаток кода sety: sha1 по .py/.sql файлам каталога sety (путь + содержимое без CR)."""
    h = hashlib.sha1()
    base = sety_root / "sety"
    for p in sorted(base.rglob("*")):
        if p.suffix in (".py", ".sql") and "__pycache__" not in p.parts:
            h.update(p.relative_to(base).as_posix().encode())
            h.update(p.read_bytes().replace(b"\r", b""))
    return h.hexdigest()


def mode_args(case: Case) -> list[str]:
    """Флаги режима, как их собирает веб (sety_modes.build_sety_args), и -fileID."""
    from sety_modes import SetyRunRequest, build_sety_args

    req = SetyRunRequest(fragment_ids=[case.fragment], tn=case.tn, name=f"{AUTHOR} {case.name}", **case.request)
    return build_sety_args(req, AUTHOR) + ["-fileID", str(case.fragment)]


def build_command(case: Case, sety_root: Path, env: dict, out_file: str, probe: str = "") -> list[str]:
    """Команда как у воркера: worker._sety_base_cmd (подключение без пароля, -dross) + mode_args.

    С зондом вместо sety/ww.py запускается sety_probe.py (те же аргументы, подмены функций).
    """
    with mock.patch.dict(os.environ, {**env, "DB_NAME": case.db}):
        import worker  # noqa: PLC0415 — тяжёлый импорт (celery), нужен только здесь

        cmd = worker._sety_base_cmd(out_file, case.dross)
    cmd[1] = str(Path(__file__).with_name("sety_probe.py") if probe else sety_root / "sety" / "ww.py")
    return cmd + mode_args(case)


def _decode(raw: bytes) -> str:
    for enc in ("utf-8", "cp1251"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_balance(output: str) -> list[list]:
    """Строки баланса sety (out/pt_out.print_bal): «  текст, ....... v1 v2», поля по 8 символов.

    Повторяющиеся подписи («Всего» у источников и у потребителей) нумеруются: «Всего [2]».
    """
    import re

    tag = re.compile(r"</?[A-Za-z][^>]*>")
    rows, seen = [], {}
    for raw in (output or "").replace("\r\n", "\n").split("\n"):
        line = tag.sub("", raw).replace("&nbsp;", " ").replace("\xa0", " ")
        m = re.match(r"^  (?P<text>.+?), (?P<dots>\.+) (?P<rest>.*)$", line)
        if not m:
            continue
        rest = m.group("rest").ljust(17)
        vals = []
        for s in (rest[0:8], rest[9:17]):
            s = s.strip()
            try:
                vals.append(float(s) if s else None)
            except ValueError:
                vals = None
                break
        if vals is None:
            continue
        text = " ".join(m.group("text").split())
        seen[text] = seen.get(text, 0) + 1
        rows.append([text if seen[text] == 1 else f"{text} [{seen[text]}]", *vals])
    return rows


def protocol_messages(output: str) -> list[list]:
    """Ошибки и предупреждения протокола: [[важность, текст, повторов]] без времени и дат."""
    import re

    from utils.calc_protocol import parse_protocol

    volatile = [(re.compile(r"Время расчета [\d.,]+ секунд"), "Время расчета N секунд"),
                (re.compile(r"\d{2}\.\d{2}\.\d{4}( \d{1,2}:\d{2}(:\d{2})?)?"), "DATE"),
                (re.compile(r"out_[\w.-]+\.(txt|sql)"), "OUTFILE")]
    text = output or ""
    for rx, repl in volatile:
        text = rx.sub(repl, text)
    agg: dict[tuple[str, str], int] = {}
    for e in parse_protocol(text)["entries"]:
        k = (e["severity"], e["text"])
        agg[k] = agg.get(k, 0) + e["count"]
    return [[s, t, c] for (s, t), c in sorted(agg.items())]


@dataclass
class Run:
    returncode: int
    elapsed_s: float
    calc_id: int | None
    stdout: str
    stderr: str
    foreign: list = field(default_factory=list)  # чужие расчёты в базе за время прогона
    probe: dict = field(default_factory=dict)    # наблюдения sety_probe.py (PROBE_JSON)


async def _max_calc_id(conn) -> int:
    return int(await conn.fetchval("SELECT coalesce(max(id), 0) FROM calculation"))


async def run_sety(conn, case: Case, sety_root: Path, env: dict, timeout_s: int, probe: str = "") -> Run:
    with tempfile.TemporaryDirectory(prefix="golden_") as tmp:
        cmd = build_command(case, sety_root, env, str(Path(tmp) / "out.txt"), probe)
        run_env = {**os.environ, **env, "DB_NAME": case.db, "PYTHONIOENCODING": "utf-8",
                   # sety обходит шаблоны внутренних схем как множество — порядок от хеша строк
                   "PYTHONHASHSEED": "0", "SETY_ROOT": str(sety_root), "SETY_PROBE": probe}
        run_env.pop("PYTHONPATH", None)
        before = await _max_calc_id(conn)
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout_s, cwd=str(sety_root), env=run_env)
            rc, out, err = proc.returncode, _decode(proc.stdout), _decode(proc.stderr)
        except subprocess.TimeoutExpired as exc:
            rc, out, err = -1, _decode(exc.stdout or b""), f"таймаут {timeout_s} с"
        elapsed = time.perf_counter() - t0
    rows = await conn.fetch("SELECT id, fileid, name FROM calculation WHERE id > $1 ORDER BY id", before)
    mine = [r["id"] for r in rows if r["fileid"] == case.fragment and (r["name"] or "") == f"{AUTHOR} {case.name}"]
    foreign = [f"#{r['id']} фрагмент {r['fileid']} «{r['name'] or ''}»" for r in rows if r["id"] not in mine]
    probe_data = {}
    for line in err.splitlines():
        if line.startswith("PROBE_JSON "):
            probe_data = json.loads(line[len("PROBE_JSON "):])
    return Run(rc, elapsed, mine[-1] if mine else None, out, err, foreign, probe_data)


async def _table_columns(conn, name: str) -> list[tuple[str, bool]]:
    rows = await conn.fetch(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = $1 ORDER BY ordinal_position", name)
    return [(r["column_name"], r["data_type"] not in compare_calc._NUMERIC_TYPES) for r in rows]


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return repr(v)
    return str(v).strip() if isinstance(v, str) else str(v)


async def dump_snapshot(conn, case: Case, run: Run, out_dir: Path, sety_root: Path, zn0: list,
                        boundary: list, skip_tables: set[str]) -> None:
    """Таблицы *_out расчёта run.calc_id → <таблица>.csv, имена объектов → objects.csv, meta.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.csv"):
        old.unlink()
    tables, node_ids, line_ids, calc_params = {}, set(), set(), None
    if run.calc_id is not None:
        calc_params = await conn.fetchval("SELECT calc_params FROM calculation WHERE id = $1", run.calc_id)
        for name, key in TABLES.items():
            if name in skip_tables:
                continue
            cols = [(c, t) for c, t in await _table_columns(conn, name) if c not in ("id", "calculationid", *key)]
            if not cols:
                continue
            names = [*key, *(c for c, _ in cols)]
            sql = (f"SELECT {', '.join(names)} FROM {name} WHERE calculationid = $1 "
                   f"ORDER BY {', '.join(key)}")
            rows = await conn.fetch(sql, run.calc_id)
            with open(out_dir / f"{name}.csv", "w", encoding="utf-8", newline="") as fh:
                w = csv.writer(fh, lineterminator="\n")
                w.writerow(names)
                for r in rows:
                    w.writerow([_fmt(r[c]) for c in names])
            tables[name] = {"key": list(key), "columns": [c for c, _ in cols],
                            "text_columns": [c for c, t in cols if t], "rows": len(rows)}
            ids = {r[key[0]] for r in rows}
            (node_ids if key[0] == "nodeid" else line_ids).update(ids)
        await _dump_names(conn, out_dir, node_ids, line_ids)
    meta = {
        "case": case.name, "note": case.note, "db": case.db, "fragment": case.fragment, "tn": case.tn,
        "request": case.request, "args": mode_args(case),
        "sety": {"root": str(sety_root), "hash": sety_hash(sety_root)},
        "captured_at": dt.datetime.now().isoformat(timespec="seconds"),
        "calc_id": run.calc_id, "returncode": run.returncode, "elapsed_s": round(run.elapsed_s, 1),
        "foreign_calcs": run.foreign, "read_zn0": zn0, "skipped_tables": sorted(skip_tables),
        # [id узла, магистраль, расчёт магистрали, напор П, напор О, t П, t О, источник]
        "boundary": boundary,
        "probe": run.probe, "calc_params": calc_params,
        "tables": tables, "balance": parse_balance(run.stdout), "protocol": protocol_messages(run.stdout),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    (out_dir / "protocol.txt").write_text(run.stdout, encoding="utf-8")
    (out_dir / "stderr.txt").write_text(run.stderr, encoding="utf-8")  # ход итераций решателя (iter: …)


async def _dump_names(conn, out_dir: Path, node_ids: set, line_ids: set) -> None:
    node_sql = ("SELECT n.id, trim(coalesce(ec.name, '') || ' ' || coalesce(n.externalnodename, '')) AS name "
                "FROM nodes n LEFT JOIN externalcodes ec ON ec.id = n.externalcodeid WHERE n.id = ANY($1::int[])")
    line_sql = ("SELECT l.id, trim(coalesce(e1.name, '') || ' ' || coalesce(n1.externalnodename, '') || ' – ' || "
                "coalesce(e2.name, '') || ' ' || coalesce(n2.externalnodename, '')) AS name FROM linesobj l "
                "LEFT JOIN nodes n1 ON n1.id = l.nodeid1 LEFT JOIN externalcodes e1 ON e1.id = n1.externalcodeid "
                "LEFT JOIN nodes n2 ON n2.id = l.nodeid2 LEFT JOIN externalcodes e2 ON e2.id = n2.externalcodeid "
                "WHERE l.id = ANY($1::int[])")
    with open(out_dir / "objects.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["kind", "id", "name"])
        for kind, sql, ids in (("node", node_sql, node_ids), ("line", line_sql, line_ids)):
            for r in sorted(await conn.fetch(sql, sorted(i for i in ids if i is not None)), key=lambda r: r["id"]):
                w.writerow([kind, r["id"], r["name"]])


async def run_case(case: Case, env: dict, sety_root: Path, out_dir: Path, args) -> tuple[bool | None, str]:
    """Прогрев + расчёт + снимок. (успех или None — случай пропущен, строка для сводки)."""
    import asyncpg

    check_copy_db(case.db)
    try:
        conn = await asyncpg.connect(host=env["DB_HOST"], port=int(env.get("DB_PORT", 5432)), user=env["DB_USER"],
                                     password=env["DB_PASSWORD"], database=case.db, timeout=30)
    except asyncpg.InvalidCatalogNameError:
        return None, f"нет базы {case.db} — случай пропущен (см. docs/sety-golden-reference.md)"
    try:
        if not await conn.fetchval("SELECT 1 FROM fragments WHERE id = $1", case.fragment):
            return False, f"в {case.db} нет фрагмента {case.fragment}"
        mags = [r[0] for r in await conn.fetch(MAGISTRAL_SQL, case.fragment)]
        watched = {case.fragment, *mags}
        for attempt in range(1, args.retries + 2):
            start = await _max_calc_id(conn)
            if args.warmup:
                # граничные условия берутся из последнего расчёта магистрали — сначала она (тем же режимом и Tн)
                for mag in mags:
                    if mag != case.fragment:
                        await run_sety(conn, replace(case, name=f"{case.name}_mag{mag}", fragment=mag),
                                       sety_root, env, args.timeout)
                await run_sety(conn, case, sety_root, env, args.timeout)  # прогрев — без зондов
            zn0 = [list(r) for r in await conn.fetch(READ_ZN0_SQL, case.fragment)]
            boundary = [[float(v) if isinstance(v, Decimal) else v for v in r]
                        for r in await conn.fetch(BOUNDARY_SQL, case.fragment)]
            run = await run_sety(conn, case, sety_root, env, args.timeout, args.probe)
            # чужой расчёт этого фрагмента или его магистрали за всю попытку (магистраль → прогрев → расчёт)
            # мог поменять вход: read_zn0 и граничные условия берутся из ПОСЛЕДНЕГО расчёта
            rows = await conn.fetch("SELECT id, fileid, name FROM calculation WHERE id > $1 ORDER BY id", start)
            run.foreign = [f"#{r['id']} фрагмент {r['fileid']} «{r['name'] or ''}»" for r in rows
                           if not (r["name"] or "").startswith(f"{AUTHOR} {case.name}")]
            hit = sorted({r["fileid"] for r in rows if r["fileid"] in watched
                          and not (r["name"] or "").startswith(f"{AUTHOR} {case.name}")})
            if not hit or attempt > args.retries:
                break
            print(f"{case.name}: за время попытки чужой расчёт фрагмента {hit} — повтор {attempt}", flush=True)
        # фактический режим ПЕРЕНОСИТ dr_out прошлого расчёта в новый — строки зависят от истории базы
        skip = set() if case.dross else {"dr_out"}
        await dump_snapshot(conn, case, run, out_dir, sety_root, zn0, boundary, skip)
    finally:
        await conn.close()
    status = f"код {run.returncode}, расчёт #{run.calc_id}, {run.elapsed_s:.1f} с"
    if run.foreign:
        # sety зависит от чужих расчётов только через read_zn0; совпадение при сверке это подтверждает
        status += f"; чужие расчёты за время прогона ({len(run.foreign)}): {', '.join(run.foreign[:3])}"
    return run.calc_id is not None, status


def _load_env(path: Path) -> dict:
    from dotenv import dotenv_values

    env = {k: v for k, v in dotenv_values(path).items() if v is not None}
    missing = [k for k in ("DB_HOST", "DB_USER", "DB_PASSWORD") if not env.get(k)]
    if missing:
        raise SystemExit(f"В {path} нет {', '.join(missing)}")
    return {"DB_PORT": "5432", **{k: env[k] for k in ("DB_HOST", "DB_PORT", "DB_USER", "DB_PASSWORD") if k in env}}


def select_cases(spec: str, overrides: list[str] | None = None) -> list[Case]:
    """Случаи по именам; overrides «поле=значение» меняют поля SetyRunRequest (например trtp=1)."""
    by_name = {c.name: c for c in CASES}
    names = [s.strip() for s in spec.split(",") if s.strip()] or list(by_name)
    unknown = [n for n in names if n not in by_name]
    if unknown:
        raise SystemExit(f"Неизвестные случаи: {', '.join(unknown)}; есть: {', '.join(by_name)}")
    extra = {}
    for item in overrides or []:
        k, _, v = item.partition("=")
        try:
            extra[k.strip()] = json.loads(v)  # числа, true/false
        except json.JSONDecodeError:
            extra[k.strip()] = v
    cases = [by_name[n] for n in names]
    if extra:
        cases = [Case(c.name, c.db, c.fragment, c.tn, {**c.request, **extra}, c.note) for c in cases]
    return cases


def boundary_diff(ref: list | None, new: list | None) -> str:
    """Различие граничных условий из магистрали (без номеров расчётов): текст или ''."""
    if ref is None or new is None:
        return ""
    strip = lambda rows: {r[0]: (r[1], *r[3:]) for r in rows}  # noqa: E731 — без calc_id
    a, b = strip(ref), strip(new)
    changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    if not changed:
        return ""
    mags = sorted({str((a.get(k) or b.get(k))[0]) for k in changed})
    return (f"граничные условия из последнего расчёта магистрали (фрагмент {', '.join(mags)}) различаются "
            f"у {len(changed)} узлов с ЗН — результат зависит от того, кто считал магистраль последним")


def compare_dirs(ref_dir: Path, new_dir: Path, cases: list[Case], args) -> tuple[str, bool]:
    """Сверка снимков по случаям: сводка + отчёты <случай>.md в new_dir."""
    tol = compare_calc.parse_tolerances(args)
    lines = [f"# Эталонная сверка sety — {dt.datetime.now():%Y-%m-%d %H:%M}\n",
             f"Эталоны: `{ref_dir}`, кандидат: `{new_dir}`.\n",
             "| случай | итог | что разошлось |", "|---|---|---|"]
    all_ok = True
    for case in cases:
        ref, new = ref_dir / case.name, new_dir / case.name
        if not (ref / "meta.json").exists() or not (new / "meta.json").exists():
            lines.append(f"| {case.name} | нет снимка | {'эталон' if not (ref / 'meta.json').exists() else 'кандидат'} |")
            all_ok = False
            continue
        r, n = compare_calc.load_snapshot(ref), compare_calc.load_snapshot(new)
        report, ok, sections = compare_calc.compare_snapshots(r, n, tol, args.top, not args.ignore_protocol)
        notes = []
        if r.meta.get("read_zn0") != n.meta.get("read_zn0"):
            notes.append("вход read_zn0 (источники узлов с ЗН из прошлых расчётов) различается")
        bdiff = boundary_diff(r.meta.get("boundary"), n.meta.get("boundary"))
        if bdiff:
            notes.append(bdiff)
        if n.meta.get("foreign_calcs") and not ok:
            notes.append(f"в базе шли чужие расчёты ({len(n.meta['foreign_calcs'])}) — переснять перед выводами")
        if notes:
            report = report.replace("\n", "\n\n> Внимание: " + "; ".join(notes) + ".\n", 1)
        (new_dir / f"{case.name}.md").write_text(report, encoding="utf-8")
        all_ok = all_ok and ok
        bad = ", ".join(k for k, v in sections.items() if not v)
        lines.append(f"| {case.name} | {'совпадает' if ok else '**расходится**'} | {'; '.join([bad, *notes]).strip('; ') or '—'} |")
    lines.append(f"\n**Итог: {'совпадает' if all_ok else 'есть расхождения'}.** Подробности — `<случай>.md` рядом.")
    return "\n".join(lines) + "\n", all_ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["list", "capture", "check", "compare"])
    ap.add_argument("--cases", default="", help="случаи через запятую (по умолчанию все)")
    ap.add_argument("--env", type=Path, default=ROOT / ".env", help=".env с DB_HOST/DB_PORT/DB_USER/DB_PASSWORD")
    ap.add_argument("--ref-dir", type=Path, default=DEFAULT_REF_DIR, help="каталог эталонов")
    ap.add_argument("--new-dir", type=Path, help="check: куда класть снимки кандидата; compare: готовые снимки")
    ap.add_argument("--sety-root", type=Path, default=ROOT, help="каталог, в котором лежит пакет sety/")
    ap.add_argument("--timeout", type=int, default=1800, help="таймаут одного расчёта, с")
    ap.add_argument("--no-warmup", dest="warmup", action="store_false", help="без прогрева (результат зависит от истории)")
    ap.add_argument("--retries", type=int, default=3,
                    help="повторов случая, если за время прогона кто-то считал этот фрагмент или его магистраль")
    ap.add_argument("--top", type=int, default=20, help="сколько худших значений показывать")
    ap.add_argument("--ignore-protocol", action="store_true", help="сообщения протокола не влияют на итог")
    ap.add_argument("--probe", default="", help="check: зонды sety_probe.py через запятую (проверка ревью)")
    ap.add_argument("--set", action="append", default=[], metavar="ПОЛЕ=ЗНАЧЕНИЕ",
                    help="check: поменять параметр расчёта (поле sety_modes.SetyRunRequest), например trtp=1")
    compare_calc.add_tolerance_args(ap)
    args = ap.parse_args()
    if args.command == "capture" and (args.probe or args.set):
        ap.error("эталон снимается без зондов и без --set")
    cases = select_cases(args.cases, args.set)
    sety_root = args.sety_root.resolve()

    if args.command == "list":
        for c in cases:
            print(f"{c.name:18} {c.db:16} фрагмент {c.fragment:<5} Tн {c.tn:<5g} {c.note}")
        return 0
    if args.command == "compare":
        if not args.new_dir:
            ap.error("compare: нужен --new-dir")
        text, ok = compare_dirs(args.ref_dir, args.new_dir, cases, args)
        sys.stdout.buffer.write(text.encode("utf-8"))
        return 0 if ok else 1
    if not (sety_root / "sety" / "ww.py").exists():
        raise SystemExit(f"В {sety_root} нет sety/ww.py")
    for c in cases:
        check_copy_db(c.db)
    env = _load_env(args.env)
    if args.command == "capture":
        target = args.ref_dir
    else:
        stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        label = "_".join([args.probe.replace(",", "+"), *(s.replace("=", "") for s in args.set)]).strip("_")
        target = args.new_dir or args.ref_dir / ("_probes" if label else "_checks") / (f"{label}_{stamp}" if label else stamp)
    target.mkdir(parents=True, exist_ok=True)

    clean = True
    for c in cases:
        ok, status = asyncio.run(run_case(c, env, sety_root, target / c.name, args))
        clean = clean and ok is not False
        print(f"{c.name}: {status}", flush=True)
    if args.command == "capture":
        print(f"Эталоны: {target}")
        return 0 if clean else 1
    text, ok = compare_dirs(args.ref_dir, target, [c for c in cases if (target / c.name / "meta.json").exists()], args)
    (target / "summary.md").write_text(text, encoding="utf-8")
    sys.stdout.buffer.write(text.encode("utf-8"))
    return 0 if ok and clean else 1


if __name__ == "__main__":
    sys.exit(main())
