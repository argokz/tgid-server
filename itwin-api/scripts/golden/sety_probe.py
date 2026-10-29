"""Запуск sety с зондами — проверка пунктов ревью sety на данных без правки кода sety.

run_reference.py --probe <зонд>[,<зонд>] запускает этот файл вместо sety/ww.py с теми же
аргументами: он импортирует sety из SETY_ROOT, подменяет функции (monkeypatch) и вызывает
ww.run(). Зонды двух видов:
  * наблюдение (count, teplo_iters) — результат расчёта не меняют, только считают;
  * изменение (keep_zeros, kv1, no_podpitka_t, diag_reg_off) — меняют поведение так, как
    предлагает ревью; сверка снимка с эталоном показывает, влияет ли пункт на результат.
Наблюдения печатаются в stderr одной строкой «PROBE_JSON {...}» при выходе.
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import traceback
from collections import Counter, defaultdict

STATS: dict = defaultdict(Counter)
EXTRA: dict = {}


def _replace(orig, new) -> int:
    """Подменяет функцию orig во всех загруженных модулях sety (и в импортированных по имени)."""
    n = 0
    for name, mod in list(sys.modules.items()):
        if not (name == "sety" or name.startswith("sety.")) or mod is None:
            continue
        for attr, val in list(vars(mod).items()):
            if val is orig:
                setattr(mod, attr, new)
                n += 1
    return n


def _counted(group: str, label: str, fn):
    def wrapper(*a, **kw):
        STATS[group][label] += 1
        return fn(*a, **kw)
    return wrapper


def _zero(v) -> bool:
    return not isinstance(v, (str, bool)) and v is not None and v == 0


def probe_count():
    """Сколько раз срабатывают подозрительные ветки и сколько нулей отбрасывает read_row (п. 2.1, 2.6, 2.7, 2.12)."""
    from sety import calc_nagr, read_db
    from sety.dross import drvary5
    from sety.teplo import tepl_gws1ps, y_ut

    _replace(tepl_gws1ps.getF1, _counted("calls", "tepl_gws1ps.getF1", tepl_gws1ps.getF1))
    _replace(tepl_gws1ps.getE1, _counted("calls", "tepl_gws1ps.getE1", tepl_gws1ps.getE1))
    _replace(drvary5.drvary5, _counted("calls", "drvary5.drvary5", drvary5.drvary5))
    _replace(calc_nagr.regularize, _counted("calls", "calc_nagr.regularize (запасная регуляризация)",
                                            calc_nagr.regularize))
    orig_q = y_ut.get_q_new

    def get_q_new(*a, **kw):
        v = orig_q(*a, **kw)
        STATS["calls"]["y_ut.get_q_new"] += 1
        if v == 300:
            STATS["calls"]["y_ut.get_q_new = 300 (нет норм для года/прокладки)"] += 1
        return v
    _replace(orig_q, get_q_new)

    orig_row, orig_row2 = read_db.read_row, read_db.read_row2

    def read_row(tn, cursor, row):
        res = orig_row(tn, cursor, row)
        tab = read_db.w_data.tab_list.get(tn) or {}
        for i, d in enumerate(cursor.description):
            if d[0] in tab and _zero(row[i]):
                STATS["zeros_dropped"][f"{tn}.{d[0]}→{tab[d[0]]}"] += 1
        return res

    def read_row2(tn, cursor, row):
        res = orig_row2(tn, cursor, row)
        for d, v in zip(cursor.description, row):
            if _zero(v):
                STATS["zeros_dropped"][f"{tn}.{d[0].lower()}"] += 1
        return res
    _replace(orig_row, read_row)
    _replace(orig_row2, read_row2)


def probe_keep_zeros():
    """п. 2.1: read_row/read_row2 сохраняют числовые нули из БД (а не подставляют умолчания)."""
    from sety import read_db

    orig_row, orig_row2 = read_db.read_row, read_db.read_row2

    def read_row(tn, cursor, row):
        res = orig_row(tn, cursor, row)
        tab = read_db.w_data.tab_list.get(tn) or {}
        for i, d in enumerate(cursor.description):
            if d[0] in tab and _zero(row[i]) and tab[d[0]] not in res:
                res[tab[d[0]]] = row[i]
                STATS["zeros_kept"][f"{tn}.{d[0]}"] += 1
        return res

    def read_row2(tn, cursor, row):
        res = orig_row2(tn, cursor, row)
        for d, v in zip(cursor.description, row):
            if _zero(v) and d[0].lower() not in res:
                res[d[0].lower()] = v
                STATS["zeros_kept"][f"{tn}.{d[0].lower()}"] += 1
        return res
    _replace(orig_row, read_row)
    _replace(orig_row2, read_row2)


KV_KEYS = ("otoplz", "otopln", "ventil", "kondiz", "txz", "txop", "txoo", "gvop", "gvoo", "gvz", "ut")


def probe_kv1():
    """п. 2.2: незаполненный коэффициент вариации = 1 (в sety — 0, нагрузка обнуляется)."""
    from sety import consumption

    orig = consumption.set_kv

    def set_kv(G, pr, kv, no_kv):
        if not no_kv and kv is not None and not kv.get("kvpot", 0) > 0:
            missing = [k for k in KV_KEYS if not kv.get(k)]
            for k in missing:
                STATS["kv_missing"][k] += 1
            kv = {**kv, **{k: 1 for k in missing}}
        return orig(G, pr, kv, no_kv)
    _replace(orig, set_kv)


def probe_no_podpitka_t():
    """п. 2.3: без «поправки на подпитку» температуры узла в us_out (t = -t*Gout/Gin)."""
    from sety.out import us_out

    orig = us_out.n_ras

    def n_ras(G, n, debug):
        GG, Gin, Gout, Gp = orig(G, n, debug)
        if abs(GG) > 0.000001 and Gin > 0 and Gout < 0:
            STATS["podpitka"]["узлов с поправкой"] += 1
        return 0.0, Gin, Gout, Gp
    us_out.n_ras = n_ras


def probe_diag_reg_off():
    """п. 2.12: тепловой расчёт без добавки DIAG_REG = 1e-6 к каждой диагонали (где диагональ ≠ 0)."""
    import numpy as np
    import scipy.sparse as sp
    from sety.teplo import teplo1

    orig = teplo1.safe_spsolve

    def safe_spsolve(matrix, beta, *a, **kw):
        m = sp.csc_matrix(matrix)
        d = m.diagonal()
        shift = np.where(np.abs(d - 1e-6) > 1e-12, 1e-6, 0.0)
        STATS["diag_reg"]["систем"] += 1
        return orig(sp.csc_matrix(m - sp.diags(shift)), beta, *a, **kw)
    teplo1.safe_spsolve = safe_spsolve


def probe_nagr_reg_off():
    """п. 2.12: запасная регуляризация нагрузок (calc_nagr.regularize) без добавки к каждой строке."""
    from sety import calc_nagr

    calc_nagr.NAGR_DIAG_REG = 0.0  # нулевые диагонали по-прежнему заменяются eps


def probe_teplo_iters():
    """п. 2.13: сколько итераций делает calc_teplo (до 5) и сошлась ли температура (Δt < 0,01 °C)."""
    import numpy as np
    from sety.teplo import teplo1

    orig_solve, orig_calc = teplo1.safe_spsolve, teplo1.calc_teplo
    calls: list[list[float]] = []
    state = {"prev": None}

    def safe_spsolve(matrix, beta, *a, **kw):
        t, yes = orig_solve(matrix, beta, *a, **kw)
        arr = np.asarray(t, dtype=float)
        prev = state["prev"]
        calls[-1].append(float(np.max(np.abs(arr - prev))) if prev is not None and len(prev) == len(arr) else -1.0)
        state["prev"] = arr
        return t, yes

    def calc_teplo(*a, **kw):
        calls.append([])
        state["prev"] = None
        return orig_calc(*a, **kw)
    teplo1.safe_spsolve = safe_spsolve
    _replace(orig_calc, calc_teplo)
    EXTRA["teplo_calls"] = calls


PROBES = {
    "count": probe_count,
    "keep_zeros": probe_keep_zeros,
    "kv1": probe_kv1,
    "no_podpitka_t": probe_no_podpitka_t,
    "diag_reg_off": probe_diag_reg_off,
    "nagr_reg_off": probe_nagr_reg_off,
    "teplo_iters": probe_teplo_iters,
}


def _report():
    data = {k: dict(v) for k, v in STATS.items()}
    data.update(EXTRA)
    print("PROBE_JSON " + json.dumps(data, ensure_ascii=False), file=sys.stderr, flush=True)


def main() -> None:
    root = os.environ["SETY_ROOT"]
    names = [p for p in os.environ.get("SETY_PROBE", "").split(",") if p]
    unknown = [p for p in names if p not in PROBES]
    if unknown:
        raise SystemExit(f"Неизвестные зонды: {', '.join(unknown)}")
    # как при запуске sety/ww.py: первым в пути каталог sety/ (там импорты без пакета, например
    # check_ec_hs), корень — в конце (ww.py добавляет его сам)
    sys.path[0] = os.path.join(root, "sety")
    sys.path.append(root)
    from sety import ww  # грузит config, w и всё дерево модулей sety
    from sety.any.colors import cprint

    for p in names:
        PROBES[p]()
    atexit.register(_report)
    try:
        ww.run()
    except Exception as e:  # как sety/ww.py: протокол об ошибке и код 1
        cprint('Ошибка при выполнении!', color='red')
        cprint(f'{e}', color='red')
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
