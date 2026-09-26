"""Движок sety в API — копия десктопного (gid8/python/sety). Модули, которые он
вызывает, должны быть на месте: пустой sopr2.py валил расчёт фрагментов с
радиаторами, вентиляцией и диафрагмами во внутренних схемах (read_vnutr.py)."""

import re
from pathlib import Path

import sety.sopr2 as sopr2

SETY = Path(__file__).resolve().parents[1] / "sety"


def test_sopr2_has_every_function_the_engine_calls():
    called = set()
    for f in SETY.glob("*.py"):
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lstrip().startswith("#"):
                continue
            called |= set(re.findall(r"sopr2\.(\w+)\(", line))
    assert called, "read_vnutr.py больше не вызывает sopr2?"
    missing = sorted(name for name in called if not callable(getattr(sopr2, name, None)))
    assert not missing, missing


def test_diaphragm_resistance_is_positive():
    assert sopr2.soprDR(50.0, False) > 0
