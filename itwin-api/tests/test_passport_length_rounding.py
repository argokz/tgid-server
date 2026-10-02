"""QA F55: длина паспорта после правок топологии пишется с округлением до 2 знаков."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pipesectlength_writes_are_rounded():
    for name in ("database/topology.py", "database/network_import.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        writes = re.findall(r"pipesectlength['\"]?\s*(?:=|,)\s*([^\n]+)", src)
        for expr in writes:
            if "ST_Length" in expr:
                assert expr.lstrip().startswith("round(ST_Length"), (name, expr)
        assert "length_sql = \"round(ST_Length" in src or name.endswith("network_import.py")
