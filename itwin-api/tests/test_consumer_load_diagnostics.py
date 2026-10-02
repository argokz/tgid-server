"""QA F36: «без нагрузки» по gid6 OnPotNagr0 и счётчики по фильтрам."""

import asyncio

from database import consumer_load_diagnostics as cld


def test_zero_load_is_gid6_qot_qgvs_qvent():
    assert ("(consumer.heating_load + consumer.ventilation_load + consumer.hot_water_load = 0) AS zero_load"
            in cld.CONSUMER_DIAGNOSTICS_CTE)
    where, values = cld._build_filters(diagnostic="zero_load", consumer_type=None, fragment_id=None,
                                       state_id=None, search=None)
    assert where == " WHERE consumer.zero_load" and values == []


class _Conn:
    def __init__(self):
        self.calls = []

    async def fetchval(self, sql, *args):
        self.calls.append(("val", sql, args))
        return 3

    async def fetch(self, sql, *args):
        self.calls.append(("fetch", sql, args))
        return []

    async def fetchrow(self, sql, *args):
        self.calls.append(("row", sql, args))
        return {"total": 10, "zero_load": 3, "closed": 1, "disconnected": 0, "not_calculated": 10}


def test_counts_follow_filters_but_not_diagnostic():
    conn = _Conn()
    res = asyncio.run(cld.get_consumer_load_diagnostics(
        conn, page=1, page_size=50, diagnostic="closed", fragment_id=74))
    assert res["counts"]["zero_load"] == 3
    row_sql, row_args = next((sql, args) for kind, sql, args in conn.calls if kind == "row")
    assert row_sql.split("FROM consumer_diagnostics consumer")[-1].strip() == "WHERE consumer.fragment_id=$1"
    assert row_args == (74,)
