"""QA F38: Zap6 «закрытые потребители» как в gid6 — состояние != 1 (NULL тоже закрыт)."""

import asyncio

from database import network_queries as nq


class _Conn:
    def __init__(self):
        self.sql = ""

    async def fetch(self, sql, *args):
        self.sql = sql
        return []


def test_closed_consumers_state_not_equal_one():
    conn = _Conn()
    asyncio.run(nq.query_closed_consumers(conn))
    assert "COALESCE(gc.consumerstateid, 0) <> 1" in conn.sql
    assert "COALESCE(rc.consumerstateid, 0) <> 1" in conn.sql
    assert "consumerstateid = 2" not in conn.sql
