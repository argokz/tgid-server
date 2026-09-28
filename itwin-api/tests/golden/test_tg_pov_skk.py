"""Эталон графиков ПОВ и СКК: веб (database/tg_pov_skk.py) против C++ десктопа gid8 `gid8/tg/tempgraph.cpp`.

Функции CTempGraph::CheckInputPOV / CalculatePOV / CheckInputSK / CalculateSK и init_tn_obr
вырезаются из исходника дословно, собираются MSVC (cl.exe через vcvars64.bat) в маленькую
программу и считаются в отдельном процессе. Массивы данных обнуляются после Init (в десктопе
они не инициализированы — см. docstring модуля о «точке излома» СКК).
Без каталога gid8 или без MSVC тест пропускается; путь к gid8 — GID8_ROOT, к vcvars64.bat — VCVARS64.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from database import tg_pov_skk as tp

GID8 = Path(os.environ.get("GID8_ROOT") or Path(__file__).resolve().parents[4] / "gid8")
TG_DIR = GID8 / "gid8" / "tg"
VCVARS_CANDIDATES = [
    os.environ.get("VCVARS64") or "",
    r"C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat",
    r"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat",
]
VCVARS = next((p for p in VCVARS_CANDIDATES if p and Path(p).exists()), None)

pytestmark = pytest.mark.skipif(
    not (TG_DIR / "tempgraph.cpp").exists() or VCVARS is None,
    reason="нет исходников gid8/tg или компилятора MSVC",
)

FUNCS = [
    "int init_tn_obr(",
    "bool CTempGraph::CheckInputPOV(",
    "bool CTempGraph::CalculatePOV(",
    "bool CTempGraph::CheckInputSK(",
    "bool CTempGraph::CalculateSK(",
]


def _strip_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return re.sub(r"//[^\n]*", "", src)


def _extract(src: str, signature: str) -> str:
    start = src.index(signature)
    brace = src.index("{", start)
    depth = 0
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[start:i + 1]
    raise AssertionError(f"не найден конец функции {signature}")


HARNESS_HEAD = r'''
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
using namespace std;
typedef unsigned int UINT;
#define IDS_ERROR 500
#define ERR_POW IDS_ERROR+0
#define ERR_SK IDS_ERROR+14
#define TRUE true
#define FALSE false
typedef std::string QString;
#include "povs.h"
#include "sks.h"
static std::vector<int> g_err;
struct CTempGraph {
  void AddError(UINT uID, QString& s) { g_err.push_back((int)uID); }
  bool CheckInputPOV(POV& ot, QString& sError);
  bool CalculatePOV(POV& tg, POVDATA& data);
  bool CheckInputSK(SKK& sk, QString& sError);
  bool CalculateSK(SKK& tg, SKDATA& data);
};
'''

HARNESS_MAIN = r'''
static void zero(double* a, int n) { for (int i = 0; i < n; i++) a[i] = 0; }
int main() {
  char mode[16];
  while (scanf("%15s", mode) == 1) {
    CTempGraph g; QString err; g_err.clear();
    if (strcmp(mode, "pov") == 0) {
      POV p; double v[16];
      for (int i = 0; i < 16; i++) scanf("%lf", &v[i]);
      p.THOR=v[0]; p.THK=v[1]; p.TVR=v[2]; p.TAURP=v[3]; p.TAURO=v[4]; p.TAURS=v[5]; p.QOR=v[6];
      p.QGW=v[7]; p.TSMIN=v[8]; p.TSMAX=v[9]; p.TVRO=v[10]; p.TV=v[11]; p.TB=v[12]; p.NEDOG=v[13];
      p.KSR=v[14]; p.V=v[15];
      scanf("%lf", &p.QMAX);
      p.KOL = -p.THOR + p.THK + 1;
      POVDATA d; d.Init((int)p.KOL);
      int sz = (int)p.KOL + 10;
      zero(d.tn,sz); zero(d.tau01,sz); zero(d.tau02,sz); zero(d.t01,sz); zero(d.t02,sz);
      zero(d.tau01v,sz); zero(d.tb,sz); zero(d.tg,sz);
      bool ok = g.CheckInputPOV(p, err);
      printf("{\"mode\":\"pov\",\"errors\":[");
      for (size_t i = 0; i < g_err.size(); i++) printf("%s%d", i ? "," : "", g_err[i]);
      printf("],\"points\":[");
      if (ok) {
        g.CalculatePOV(p, d);
        for (int i = 0; i <= d.n; i++)
          printf("%s[%.17g,%.17g,%.17g,%.17g,%.17g,%.17g]", i ? "," : "", d.tn[i], d.tau01[i], d.tau02[i],
                 d.tau01v[i], d.tb[i], d.tg[i]);
      }
      printf("]}\n");
    } else {
      SKK p; double v[24];
      for (int i = 0; i < 24; i++) scanf("%lf", &v[i]);
      p.IsPov=(bool)v[0]; p.THOR=v[1]; p.THK=v[2]; p.TVR=v[3]; p.TAURP=v[4]; p.TAURO=v[5]; p.TAURS=v[6];
      p.QOR=v[7]; p.QGW=v[8]; p.TSMIN=v[9]; p.TSMAX=v[10]; p.T2MIN=v[11]; p.KGUP=v[12]; p.KGUO=v[13];
      p.PSN=(int)v[14]; p.PSP=(int)v[15]; p.PSO=(int)v[16]; p.PSY=(int)v[17]; p.T2GW=v[18]; p.TV=v[19];
      p.TB=v[20]; p.TVRO=v[21]; p.KSR=v[22]; p.V=v[23];
      scanf("%lf", &p.QMAX);
      p.KOL = (int)(-p.THOR + p.THK + 1);
      SKDATA d; d.Init(p.KOL);
      int sz = p.KOL + 10;
      zero(d.tn,sz); zero(d.tau01,sz); zero(d.tau02,sz); zero(d.tau03,sz); zero(d.tau01v,sz);
      zero(d.t01,sz); zero(d.t02,sz); zero(d.tb,sz); zero(d.tgw,sz);
      bool ok = g.CheckInputSK(p, err);
      printf("{\"mode\":\"skk\",\"errors\":[");
      for (size_t i = 0; i < g_err.size(); i++) printf("%s%d", i ? "," : "", g_err[i]);
      printf("],\"iw\":");
      if (ok) {
        g.CalculateSK(p, d);
        printf("%d,\"kol\":%d,\"points\":[", p.iw, p.KOL);
        for (int i = 0; i <= d.n; i++)
          printf("%s[%.17g,%.17g,%.17g,%.17g,%.17g]", i ? "," : "", d.tn[i], d.tau01[i], d.tau02[i],
                 d.tau03[i], d.tau01v[i]);
      } else printf("-1,\"kol\":0,\"points\":[");
      printf("]}\n");
    }
  }
  return 0;
}
'''


@pytest.fixture(scope="module")
def desktop_exe(tmp_path_factory) -> Path:
    src = (TG_DIR / "tempgraph.cpp").read_text(encoding="utf-8")
    code = _strip_comments(src)
    body = "\n\n".join(_extract(code, sig) for sig in FUNCS)
    work = tmp_path_factory.mktemp("tg_cpp")
    for h in ("povs.h", "sks.h"):
        (work / h).write_text(_strip_comments((TG_DIR / h).read_text(encoding="utf-8")), encoding="utf-8")
    (work / "harness.cpp").write_text(HARNESS_HEAD + body + HARNESS_MAIN, encoding="utf-8")
    (work / "build.bat").write_text(
        f'@call "{VCVARS}" >nul\r\ncl /nologo /EHsc /O2 /fp:precise harness.cpp /Fe:harness.exe\r\n',
        encoding="cp866")
    proc = subprocess.run(["cmd", "/c", str(work / "build.bat")], cwd=work, capture_output=True, timeout=300)
    exe = work / "harness.exe"
    if proc.returncode != 0 or not exe.exists():
        pytest.fail("сборка эталона C++ не удалась:\n" + proc.stdout.decode("cp866", "replace")[-3000:])
    return exe


BASE = dict(tn_5=-25, tn_1=8, tvn_r=18, t1_r=150, t2_r=70, t3_r=95, q_r=100, q_gv=20, t1_4r=150, tg_r=60,
            tx_r=5, tvb_tr=18, t_gv1=6, uf=0, v=0, hsourcepower=110, t2_2r=40, g1=0.6, g2=0.3, t2_gv=60, pr=1)

POV_CASES = [
    dict(BASE),
    dict(BASE, tn_5=-32, t1_r=130, t3_r=95, q_gv=12, hsourcepower=90),        # дефицит мощности
    dict(BASE, v=5, t1_4r=120),                                               # ветер и верхняя срезка
    dict(BASE, tn_5=-20.1, tn_1=8, uf=1.4, t_gv1=10, q_gv=35),
    dict(BASE, tvn_r=20, tvb_tr=20, t1_r=115, t2_r=70, t3_r=95, q_gv=5),
    dict(BASE, hsourcepower=0),                                               # ошибка 509: мощность не задана
    dict(BASE, q_gv=0),                                                       # ошибка 512
]
SKK_CASES = [
    *[dict(BASE, pr=pr) for pr in (1, 2, 3, 4)],
    *[dict(BASE, pr=pr, tn_5=-32, t1_r=130, t2_2r=45, v=6) for pr in (1, 2, 3, 4)],
    dict(BASE, pr=1, t2_gv=55, uf=2.2, hsourcepower=80),
    dict(BASE, pr=4, g1=0.2, g2=0.5, tn_5=-20.1),
    dict(BASE, pr=0),                                                         # ошибка 530: способ водоразбора
]


def _pov_line(src) -> str:
    p = tp.pov_params(src)
    keys = ("THOR", "THK", "TVR", "TAURP", "TAURO", "TAURS", "QOR", "QGW", "TSMIN", "TSMAX", "TVRO", "TV", "TB",
            "NEDOG", "KSR", "V", "QMAX")
    return "pov " + " ".join(repr(float(p[k])) for k in keys)


def _skk_line(src, pov: bool) -> str:
    p = tp.skk_params(src, pov)
    keys = ("IsPov", "THOR", "THK", "TVR", "TAURP", "TAURO", "TAURS", "QOR", "QGW", "TSMIN", "TSMAX", "T2MIN",
            "KGUP", "KGUO", "PSN", "PSP", "PSO", "PSY", "T2GW", "TV", "TB", "TVRO", "KSR", "V", "QMAX")
    return "skk " + " ".join(repr(float(p[k])) for k in keys)


def _run(exe: Path, lines: list[str]) -> list[dict]:
    proc = subprocess.run([str(exe)], input="\n".join(lines).encode(), capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr.decode(errors="replace")
    return [json.loads(line) for line in proc.stdout.decode().splitlines() if line.strip()]


@pytest.mark.parametrize("i", range(len(POV_CASES)))
def test_pov_matches_desktop_cpp(desktop_exe, i):
    src = POV_CASES[i]
    ref = _run(desktop_exe, [_pov_line(src)])[0]
    web_errors = tp.check_input_pov(tp.pov_params(src))
    assert web_errors == ref["errors"]
    if ref["errors"]:
        with pytest.raises(tp.TgInputError):
            tp.calculate_graph(src, "pov")
        return
    web = tp.calculate_pov(tp.pov_params(src))
    assert len(web) == len(ref["points"])
    for w, (tn, t1, t2, tv, tb, tgv) in zip(web, ref["points"]):
        assert w["tn"] == pytest.approx(tn, abs=1e-9)
        for key, val in (("t1", t1), ("t2", t2), ("tv", tv), ("t_bn", tb), ("tg", tgv)):
            assert w[key] == pytest.approx(val, rel=1e-9, abs=1e-9), (tn, key)


@pytest.mark.parametrize("i", range(len(SKK_CASES)))
@pytest.mark.parametrize("pov", [True, False], ids=["skk_pov", "skk_pon"])
def test_skk_matches_desktop_cpp(desktop_exe, i, pov):
    src = SKK_CASES[i]
    ref = _run(desktop_exe, [_skk_line(src, pov)])[0]
    params = tp.skk_params(src, pov)
    assert tp.check_input_sk(params) == ref["errors"]
    if ref["errors"]:
        with pytest.raises(tp.TgInputError):
            tp.calculate_graph(src, "skk_pov" if pov else "skk_pon")
        return
    web = tp.calculate_sk(params)
    ref_points = ref["points"]
    kol, iw = ref["kol"], ref["iw"]
    if iw >= kol + 1 or iw < 0:
        # нет излома: у десктопа лишняя точка по неинициализированной памяти — веб её не выводит
        ref_points = ref_points[:kol + 1]
    assert len(web) == len(ref_points), (iw, kol)
    for w, (tn, t1, t2, t3, tv) in zip(web, ref_points):
        assert w["tn"] == pytest.approx(tn, abs=1e-9)
        for key, val in (("t1", t1), ("t2", t2), ("t3", t3), ("tv", tv)):
            assert w[key] == pytest.approx(val, rel=1e-9, abs=1e-9), (tn, key)


def test_mode_by_graph_type():
    assert tp.graph_mode({"graphtypeid": 3}) == "pov"
    assert tp.graph_mode({"graphtypeid": 2}) == "skk_pov"
    assert tp.graph_mode({"graphtypeid": 4}) == "skk_pon"
    assert tp.graph_mode({"graphtypeid": 1}) == "otop"
    assert tp.graph_mode({"graphtypeid": None}) == "otop"
