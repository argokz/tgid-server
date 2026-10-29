"""Эталонные расчёты sety: scripts/golden/run_reference.py и сверка снимков compare_calc.

Без БД проверяются снимки, допуски, нагрузки b101–b106, баланс и сборка команды. Сам прогон
эталонов (маркер sety_golden) идёт только при SETY_GOLDEN=1 — нужен доступ к копиям БД и
снятые эталоны; команда — docs/sety-golden-reference.md.
"""

import csv
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("run_reference", ROOT / "scripts" / "golden" / "run_reference.py")
rr = importlib.util.module_from_spec(_spec)
sys.modules["run_reference"] = rr
_spec.loader.exec_module(rr)
cc = rr.compare_calc

UT_COLS = ["sos", "a13", "a19", "t1", *cc.LOAD_KEYS]


def _ut(flow=100.0, head=60.0, t=95.0, loads=(1.0, 0.6, 0.1, 0.2, 0.05, 0.05)):
    return {"sos": "1", "a13": flow, "a19": head, "t1": t, **dict(zip(cc.LOAD_KEYS, loads))}


def _write_snapshot(path: Path, ut_rows: dict, balance=None, protocol=None, returncode=0) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    key = ["lineid", "externalsignlineid"]
    with open(path / "ut_out.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([*key, *UT_COLS])
        for k, r in ut_rows.items():
            w.writerow([*k, *("" if r[c] is None else r[c] for c in UT_COLS)])
    with open(path / "objects.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["kind", "id", "name"])
        w.writerow(["line", 7, "ТК-1 – ТК-2"])
    meta = {"case": "t", "db": "x_copy", "fragment": 1, "tn": -20, "args": [], "calc_id": 1,
            "returncode": returncode, "elapsed_s": 1.0, "sety": {"root": "r", "hash": "h"},
            "tables": {"ut_out": {"key": key, "columns": UT_COLS, "text_columns": ["sos"], "rows": len(ut_rows)}},
            "balance": balance or [["Всего", 474.1, None]], "protocol": protocol or []}
    (path / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return path


def _cmp(tmp_path, ref_rows, new_rows, **kw):
    ref = cc.load_snapshot(_write_snapshot(tmp_path / "ref", ref_rows))
    new = cc.load_snapshot(_write_snapshot(tmp_path / "new", new_rows, **kw))
    return ref, new


def test_same_snapshot_matches(tmp_path):
    rows = {(7, 2): _ut(), (7, 3): _ut(flow=-99.0, head=40.0, t=60.0)}
    ref, new = _cmp(tmp_path, rows, rows)
    report, ok, sections = cc.compare_snapshots(ref, new)
    assert ok and all(sections.values())
    assert "**Итог: совпадает.**" in report


def test_tolerances_by_kind_and_where(tmp_path):
    ref_rows = {(7, 2): _ut(), (7, 3): _ut()}
    new_rows = {(7, 2): _ut(head=60.008, t=95.04), (7, 3): _ut(flow=100.5)}  # напор/t в допуске, расход нет
    ref, new = _cmp(tmp_path, ref_rows, new_rows)
    report, ok, sections = cc.compare_snapshots(ref, new)
    assert not ok and sections["таблицы"] is False
    assert "a13 расход (расход, т/ч)" in report
    assert "участок 7 О «ТК-1 – ТК-2»" in report  # «где»: участок, сторона и имя
    assert "a19" not in report.split("## Что ушло и где")[1].split("Худшие")[0]

    _, ok, _ = cc.compare_snapshots(ref, new, {"flow": (1.0, 0.001)})  # ослабили допуск расхода
    assert ok


def test_text_column_and_row_sets(tmp_path):
    ref_rows = {(7, 2): _ut(), (8, 2): _ut()}
    new_rows = {(7, 2): {**_ut(), "sos": "0"}, (9, 2): _ut()}
    ref, new = _cmp(tmp_path, ref_rows, new_rows)
    report, ok, _ = cc.compare_snapshots(ref, new)
    assert not ok
    assert "только в эталоне: участок 8 П" in report and "только в кандидате: участок 9 П" in report
    assert "| текст |" in report


def test_synthetic_nodes_compared_by_count(tmp_path):
    # id < 0 — синтетические узлы эквивалентных схем: номера при каждом расчёте свои
    ref_rows = {(7, 2): _ut(), (-100001, 2): _ut(t=-1e6)}
    new_rows = {(7, 2): _ut(), (-100002, 2): _ut(t=-4e9)}
    ref, new = _cmp(tmp_path, ref_rows, new_rows)
    report, ok, _ = cc.compare_snapshots(ref, new)
    assert ok and "| ut_out | 1 | 1 |" in report
    new_rows[(-100003, 2)] = _ut()
    _, ok, _ = cc.compare_snapshots(ref, cc.load_snapshot(_write_snapshot(tmp_path / "new2", new_rows)))
    assert not ok


def test_load_identity_and_sums():
    good = {(1, 2): _ut()}
    bad = {(1, 2): _ut(loads=(1.0, 0.5, 0.1, 0.2, 0.05, 0.05))}  # b101 больше суммы видов на 0.1
    assert cc.load_identity_violations(good, 1e-4, 0.001) == []
    assert len(cc.load_identity_violations(bad, 1e-4, 0.001)) == 1
    lines, ok = cc.compare_loads(good, bad, 1e-4, 0.001)
    text = "\n".join(lines)
    assert not ok
    assert "Новые нарушения тождества у кандидата: 1" in text
    assert "| b102 отопление | 0.6000 | 0.5000 | -0.1 | 1 |" in text


def test_returncode_balance_and_protocol(tmp_path):
    rows = {(7, 2): _ut()}
    ref = cc.load_snapshot(_write_snapshot(tmp_path / "ref", rows, protocol=[["warning", "A", 1]]))
    new = cc.load_snapshot(_write_snapshot(tmp_path / "new", rows, balance=[["Всего", 573.2, None]],
                                           protocol=[["warning", "B", 2]], returncode=1))
    report, ok, sections = cc.compare_snapshots(ref, new)
    assert not ok
    assert sections == {"код выхода": False, "таблицы": True, "нагрузки b101–b106": True,
                        "баланс": False, "сообщения протокола": False}
    assert "| Всего | 474.1 | 573.2 | **+99.1** |" in report
    assert "[предупр.] ×2 B" in report
    _, _, sections = cc.compare_snapshots(ref, new, check_protocol=False)
    assert "сообщения протокола" not in sections


def test_parse_balance_fixed_columns():
    out = "\n".join([
        "  Источник <a name='node' id='5'>[ТЭЦ-1 П]</a>, " + "." * 20 + f" {474.1:8.1f} {1520.0:8.1f}",
        "  Всего, " + "." * 43 + f" {474.1:8.1f} " + " " * 8,
        "  Тепловые потери, подающий теплопровод, " + "." * 11 + " " * 9 + f"{3.2:8.1f}",
        "  Всего, " + "." * 43 + f" {470.0:8.1f} {1500.0:8.1f}",
        "Обычная строка, без баланса",
    ])
    assert rr.parse_balance(out) == [
        ["Источник [ТЭЦ-1 П]", 474.1, 1520.0], ["Всего", 474.1, None],
        ["Тепловые потери, подающий теплопровод", None, 3.2], ["Всего [2]", 470.0, 1500.0]]


def test_only_copy_databases():
    with pytest.raises(SystemExit):
        rr.check_copy_db("almatygid")
    with pytest.raises(SystemExit):
        rr.check_copy_db("astanagid_2026_09_22")
    rr.check_copy_db("almatygid_copy")
    assert all(c.db.endswith("_copy") for c in rr.CASES)


def test_command_like_worker_without_password(monkeypatch):
    env = {"DB_HOST": "127.0.0.1", "DB_PORT": "5440", "DB_USER": "u", "DB_PASSWORD": "секрет-пароль"}
    case = rr.CASES[0]
    cmd = rr.build_command(case, ROOT, env, "out.txt")
    assert "секрет-пароль" not in " ".join(cmd) and "-password" not in cmd
    assert cmd[cmd.index("-database") + 1] == case.db
    assert cmd[1] == str(ROOT / "sety" / "ww.py")
    assert "-dross" in cmd and cmd[-2:] == ["-fileID", str(case.fragment)]
    assert cmd[cmd.index("-Tn") + 1] == "-20"
    fact = next(c for c in rr.CASES if not c.dross)
    fcmd = rr.build_command(fact, ROOT, env, "out.txt")
    assert "-dross" not in fcmd and "-a" in fcmd


def test_overrides_and_probe_command():
    case = rr.select_cases("almaty74_plan", ["trtp=1", "tg=true"])[0]
    assert case.request == {"mode": "plan", "trtp": 1, "tg": True}
    args = rr.mode_args(case)
    assert args[args.index("-trtp") + 1] == "1" and "-tg" in args
    with pytest.raises(SystemExit):
        rr.select_cases("нет_такого")
    env = {"DB_HOST": "h", "DB_PORT": "1", "DB_USER": "u", "DB_PASSWORD": "p"}
    cmd = rr.build_command(case, ROOT, env, "out.txt", probe="count")
    assert cmd[1].endswith("sety_probe.py")


def test_boundary_diff_ignores_calc_ids():
    ref = [[1, 74, 511, 63.3, 36.0, 120.7, 57.0, 177], [2, 74, None, None, None, None, None, None]]
    same = [[1, 74, 518, 63.3, 36.0, 120.7, 57.0, 177], [2, 74, None, None, None, None, None, None]]
    summer = [[1, 74, 520, 108.9, -0.7, 65.0, 0.0, 176], [2, 74, None, None, None, None, None, None]]
    assert rr.boundary_diff(ref, same) == ""
    assert "фрагмент 74" in rr.boundary_diff(ref, summer) and "у 1 узлов" in rr.boundary_diff(ref, summer)
    assert rr.boundary_diff(None, summer) == ""  # старый снимок без граничных условий


def test_probe_names_known():
    spec = importlib.util.spec_from_file_location("sety_probe", ROOT / "scripts" / "golden" / "sety_probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    assert {"count", "teplo_iters", "keep_zeros", "kv1", "no_podpitka_t", "diag_reg_off", "nagr_reg_off"} == set(probe.PROBES)


@pytest.mark.sety_golden
@pytest.mark.skipif(os.environ.get("SETY_GOLDEN") != "1", reason="эталонные расчёты: SETY_GOLDEN=1 и копии БД")
def test_reference_calculations_match(tmp_path):
    """Пересчёт всех случаев текущим кодом sety совпадает со снятыми эталонами."""
    ref_dir = Path(os.environ.get("SETY_GOLDEN_DIR") or rr.DEFAULT_REF_DIR)
    if not any(ref_dir.glob("*/meta.json")):
        pytest.skip(f"нет эталонов в {ref_dir}: сначала run_reference.py capture")
    cases = ",".join(c.name for c in rr.CASES if (ref_dir / c.name / "meta.json").exists())
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "golden" / "run_reference.py"), "check", "--cases", cases,
         "--ref-dir", str(ref_dir), "--new-dir", str(tmp_path)],
        capture_output=True, cwd=str(ROOT), env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=3 * 3600)
    out = proc.stdout.decode("utf-8", errors="replace")
    assert proc.returncode == 0, out + proc.stderr.decode("utf-8", errors="replace")[-3000:]
