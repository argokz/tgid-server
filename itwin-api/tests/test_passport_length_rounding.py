"""QA F55: длина паспорта после правок топологии пишется с округлением до 2 знаков —
и в метрах на земле (ground_length_sql: в Шатуре под SRID 9998 лежит Web Mercator)."""

import re
from pathlib import Path

from database.topology import MERCATOR_9998_SQL, ground_length_sql

ROOT = Path(__file__).resolve().parents[1]


def test_pipesectlength_writes_are_rounded():
    for name in ("database/topology.py", "database/network_import.py", "database/topology_cad.py"):
        src = (ROOT / name).read_text(encoding="utf-8")
        writes = re.findall(r"pipesectlength['\"]?\s*(?:=|,)\s*([^\n]+)", src)
        for expr in writes:
            if "length" in expr.lower() and "ST_" in expr or "ground_length_sql" in expr:
                assert expr.lstrip().startswith("round({ground_length_sql("), (name, expr)
            # плоская ST_Length без учёта Меркатора в Шатуре завысила бы длину ~1,7 раза
            assert "round(ST_Length" not in expr, (name, expr)
    src = (ROOT / "database/topology.py").read_text(encoding="utf-8")
    assert "length_sql = f\"round({ground_length_sql(" in src


def test_ground_length_uses_geography_only_for_mercator_9998():
    sql = ground_length_sql("l.shape")
    assert MERCATOR_9998_SQL in sql
    assert "ST_Length(ST_Transform(l.shape, 4326)::geography)" in sql
    assert "ELSE ST_Length(l.shape) END" in sql
