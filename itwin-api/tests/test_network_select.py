"""Выборка объектов сети по условиям (network_select), вопрос → выборка (ИИ) и инструмент MCP."""

import asyncio
import json
from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient

from database import network_select as ns


class _Tx:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _Conn:
    """Запросы выборки: пишет SQL и аргументы, отдаёт заданные строки."""

    def __init__(self, rows=(), *, run=None, node=None, refs=()):
        self.rows = list(rows)
        self.run = run
        self.node = node
        self.refs = list(refs)
        self.sql: list[tuple[str, tuple]] = []
        self.executed: list[str] = []

    def transaction(self):
        return _Tx()

    async def execute(self, sql, *args):
        self.executed.append(sql)

    async def fetchval(self, sql, *args):
        return True

    async def fetchrow(self, sql, *args):
        if "FROM nodes" in sql:
            return self.node
        return self.run

    async def fetch(self, sql, *args):
        if sql.startswith("SELECT id, ") and "ORDER BY id" in sql:
            return self.refs
        if "FROM tgid_poi" in sql:  # счётчики социальных объектов для справочника полей
            return []
        self.sql.append((sql, args))
        return self.rows


def _line_row(i, **values):
    row = {"id": i, "fileid": 74, "node1": "ТК-1", "node2": "ТК-2", "length": 120.04, "distance_m": None,
           "lon": 76.9, "lat": 43.2, "total": 3, "total_length": 360.0,
           "geometry": json.dumps({"type": "LineString", "coordinates": [[76.9, 43.2], [76.91, 43.21]]})}
    row.update(values)
    return row


def _spec(**kw):
    return ns.SelectSpec(**kw)


def test_validate_rejects_unknown_field_and_bad_op():
    with pytest.raises(ns.SelectError, match="недоступно"):
        ns.validate(_spec(conditions=[{"field": "colour", "op": "eq", "value": 1}]))
    with pytest.raises(ns.SelectError, match="операция"):
        ns.validate(_spec(conditions=[{"field": "diameter", "op": "contains", "value": "4"}]))
    with pytest.raises(ns.SelectError, match="число"):
        ns.validate(_spec(conditions=[{"field": "diameter", "op": "gt", "value": "много"}]))
    with pytest.raises(ns.SelectError, match="конечное"):
        ns.validate(_spec(conditions=[{"field": "diameter", "op": "gt", "value": float("nan")}]))
    with pytest.raises(ns.SelectError, match="значение"):
        ns.validate(_spec(conditions=[{"field": "tubing_type", "op": "in", "values": []}]))
    with pytest.raises(ns.SelectError, match="неизвестные"):
        ns.validate(_spec(target="nodes", conditions=[{"field": "card_type", "op": "in", "values": ["XX"]}]))
    with pytest.raises(ns.SelectError, match="Рядом"):
        ns.validate(_spec(near={"meters": 100}))
    with pytest.raises(ns.SelectError, match="недоступно"):
        ns.validate(_spec(order_by="load"))  # поле узлов у участков


def test_validate_normalises_values():
    spec = ns.validate(_spec(conditions=[
        {"field": "diameter", "op": "between", "value": "500", "value2": 300, "values": [1]},
        {"field": "tubing_type", "op": "in", "values": ["2"], "value": 5},
        {"field": "wear", "op": "is_null", "value": 3},
    ], fragment_ids=[74, 72, 74], order_by="distance"))
    between, tubing, wear = spec.conditions
    assert (between.value, between.value2, between.values) == (300, 500, [])
    assert tubing.values == [2] and tubing.value is None
    assert wear.value is None
    assert spec.fragment_ids == [72, 74] and spec.order_by is None  # по расстоянию — только с near


def test_describe_reads_like_the_query():
    spec = ns.validate(_spec(conditions=[{"field": "diameter", "op": "ge", "value": 400},
                                         {"field": "tubing_type", "op": "in", "values": [2]}],
                             near={"node_name": "ТК-12", "meters": 300}, fragment_ids=[74], order_by="diameter"))
    text = ns.describe(spec, {"tubing_type": {2: "бесканальная"}}, near_label="узла «ТК-12» (id 5)")
    assert text == ("Участки: Условный диаметр ≥ 400 мм и Тип прокладки — бесканальная; в 300 м от узла «ТК-12» "
                    "(id 5); фрагмент 74; по убыванию: условный диаметр")
    spec = ns.validate(_spec(target="nodes", match="any", in_view=True))
    assert ns.describe(spec, {}) == "Узлы: все; в видимой области карты; все фрагменты"


def test_lines_sql_is_parameterised_and_joins_sources():
    rows = [_line_row(1, f_velocity=1.834, f_wear=71.26), _line_row(2, f_velocity=None, f_wear=65.0)]
    conn = _Conn(rows, run={"id": 9, "name": "Износ", "daterascheta": __import__("datetime").date(2026, 10, 1)},
                 node={"id": 5, "fileid": 74, "name": "ТК-12", "lon": 76.9, "lat": 43.2})
    spec = _spec(conditions=[{"field": "velocity", "op": "gt", "value": 1.5},
                             {"field": "wear", "op": "gt", "value": 60}],
                 near={"node_name": "ТК-12'; DROP TABLE nodes; --", "meters": 500}, fragment_ids=[74], limit=2)
    res = asyncio.run(ns.run_select(conn, spec))
    sql, args = conn.sql[0]
    # значения — только параметрами; источники — расчёт фрагмента и последний износ
    assert "DROP TABLE" not in sql and "calc_ut AS MATERIALIZED" in sql and "wear_out w" in sql
    assert "ST_Distance(" in sql and "ST_MakeEnvelope(" in sql and "internalnodeid" in sql
    assert 1.5 in args and 60.0 in args and 500.0 in args and [74] in args and 9 in args and args[-1] == 2
    assert conn.executed == [f"SET LOCAL statement_timeout = '{ns.STATEMENT_TIMEOUT}'"]
    assert res["total"] == 3 and res["truncated"] is True and res["total_length_m"] == 360.0
    assert res["items"][0]["values"] == {"velocity": 1.83, "wear": 71.3} and res["items"][0]["length"] == 120.0
    assert res["items"][0]["title"] == "ТК-1 — ТК-2"
    assert res["near_center"] == {"lon": 76.9, "lat": 43.2, "meters": 500.0}
    assert len(res["geojson"]["features"]) == 2 and "«ТК-12» (id 5, фрагмент 74)" in res["description"]


def test_lines_without_wear_run_is_404():
    conn = _Conn(run=None)
    with pytest.raises(ns.SelectError) as e:
        asyncio.run(ns.run_select(conn, _spec(conditions=[{"field": "wear", "op": "gt", "value": 60}])))
    assert e.value.status == 404 and "износа" in e.value.message


def test_near_node_not_found_is_404():
    with pytest.raises(ns.SelectError) as e:
        asyncio.run(ns.run_select(_Conn(node=None), _spec(near={"node_id": 77, "meters": 100})))
    assert e.value.status == 404


def test_in_view_needs_bbox_and_bbox_ignored_without_flag():
    with pytest.raises(ns.SelectError, match="охвата"):
        asyncio.run(ns.run_select(_Conn(), _spec(in_view=True)))
    conn = _Conn()
    res = asyncio.run(ns.run_select(conn, _spec(), bbox=(76.9, 43.2, 77.0, 43.3)))
    assert "ST_MakeEnvelope" not in conn.sql[0][0] and res["total"] == 0 and res["items"] == []


def test_nodes_card_type_and_labels():
    rows = [{"id": 7, "fileid": 74, "name": "ж/д 5", "node_type_label": "Ввод здание", "card": "PR",
             "distance_m": None, "f_card_type": "PR", "f_node_type": 12, "l_node_type": "Ввод здание",
             "f_load": 1.23456, "lon": 76.9, "lat": 43.2, "total": 1, "total_length": None,
             "geometry": json.dumps({"type": "Point", "coordinates": [76.9, 43.2]})}]
    conn = _Conn(rows, refs=[{"id": 12, "label": "Ввод здание"}])
    spec = _spec(target="nodes", conditions=[{"field": "card_type", "op": "in", "values": ["PR", "PO"]},
                                             {"field": "node_type", "op": "not_in", "values": [9]},
                                             {"field": "load", "op": "gt", "value": 1}], order_by="load")
    res = asyncio.run(ns.run_select(conn, spec))
    sql, args = conn.sql[0]
    assert "realconsumers" in sql and "::text[]" in sql and ["PR", "PO"] in args and [9] in args
    assert "IS NULL OR NOT" in sql  # «кроме» оставляет узлы без вида
    item = res["items"][0]
    assert item["card_type"] == "Потребитель" and item["values"] == {
        "card_type": "Потребитель", "node_type": "Ввод здание", "load": 1.235}
    # кода 9 нет в справочнике — в описании код, а не выдуманная подпись
    assert "total_length_m" not in res and "Вид узла не код 9" in res["description"]


def test_concurrency_limits_and_value_ranges(monkeypatch):
    monkeypatch.setattr(ns, "_inflight", {"ivan": ns.MAX_CONCURRENT_PER_USER})
    with pytest.raises(ns.SelectError) as e:
        asyncio.run(ns.run_select(_Conn(), _spec(), user_key="ivan"))
    assert e.value.status == 429
    asyncio.run(ns.run_select(_Conn(), _spec(), user_key="petr"))  # другой пользователь — можно
    assert ns._inflight == {"ivan": ns.MAX_CONCURRENT_PER_USER}  # место петра освобождено
    monkeypatch.setattr(ns, "_inflight", {f"u{i}": 1 for i in range(ns.MAX_CONCURRENT)})
    with pytest.raises(ns.SelectError, match="занят"):
        asyncio.run(ns.run_select(_Conn(), _spec(), user_key="petr"))

    with pytest.raises(ValueError):
        _spec(fragment_ids=[99_999_999_999])
    with pytest.raises(ValueError):
        _spec(near={"node_id": 99_999_999_999, "meters": 100})
    with pytest.raises(ns.SelectError, match="диапазона"):
        ns.validate(_spec(conditions=[{"field": "tubing_type", "op": "in", "values": [99_999_999_999]}]))


def test_db_value_error_is_422():
    class DataError(Exception):
        pass

    class _Bad(_Conn):
        async def fetch(self, sql, *args):
            raise DataError("value out of range for type integer")

    with pytest.raises(ns.SelectError) as e:
        asyncio.run(ns.run_select(_Bad(), _spec()))
    assert e.value.status == 422


def test_near_envelope_stays_within_coordinates():
    p = ns._Params()
    ns._spatial_sql("l.shape", p, (179.99, 89.99), 5000, None)
    w, s, e, n = p.values[:4]
    assert -180 <= w < e <= 180 and -90 <= s < n <= 90


def test_fields_payload_lists_targets_and_choices():
    payload = asyncio.run(ns.fields_payload(_Conn(refs=[{"id": 2, "label": "бесканальная"}])))
    targets = {t["key"]: {f["key"]: f for f in t["fields"]} for t in payload["targets"]}
    assert {"diameter", "year", "wear", "velocity", "tubing_type", "length"} <= set(targets["lines"])
    assert targets["lines"]["tubing_type"]["choices"] == [{"value": 2, "label": "бесканальная"}]
    assert targets["nodes"]["card_type"]["choices"][0] == {"value": "PR", "label": "Потребитель"}
    assert targets["lines"]["diameter"]["ops"][0] == "lt" and payload["max_limit"] == ns.MAX_LIMIT


def test_endpoints(monkeypatch):
    import main
    from auth import invalidate_user_status
    from routers import network_select as router

    monkeypatch.setenv("AUTH_DISABLED", "true")
    invalidate_user_status()

    @asynccontextmanager
    async def acquire():
        yield _Conn([_line_row(1, f_diameter=400.0)])

    monkeypatch.setattr(router, "acquire_conn", acquire)
    client = TestClient(main.app)
    assert client.get("/api/v1/network-select/fields").json()["targets"][0]["key"] == "lines"
    body = {"spec": {"conditions": [{"field": "diameter", "op": "ge", "value": 400}]}, "bbox": "76.9,43.2,77,43.3"}
    r = client.post("/api/v1/network-select", json=body)
    assert r.status_code == 200 and r.json()["items"][0]["values"] == {"diameter": 400}
    bad = {"spec": {"conditions": [{"field": "colour", "op": "eq", "value": 1}]}}
    assert client.post("/api/v1/network-select", json=bad).status_code == 422
    assert client.post("/api/v1/network-select", json={"spec": {}, "bbox": "1,2"}).status_code == 422
    assert client.post("/api/v1/network-select", json={"spec": {"limit": 99999}}).status_code == 422


def test_select_post_is_not_logged_as_action():
    import activity

    assert activity._READONLY_POST.search("/api/v1/network-select")


def test_ai_select_fills_visible_fragments_and_reports_bad_query(monkeypatch):
    from ai import client as ai_client
    from ai import tools

    calls = []

    async def fake_ask(**kw):
        calls.append(kw)
        return tools.SelectPlan(spec=ns.SelectSpec(conditions=[{"field": "diameter", "op": "ge", "value": 400}],
                                                   in_view=True), confidence=0.9, note="")

    monkeypatch.setattr(ai_client, "ask_structured", fake_ask)
    conn = _Conn([_line_row(1, f_diameter=500.0)], refs=[{"id": 2, "label": "бесканальная"}])
    out = asyncio.run(tools.select_by_phrase(conn, text="трубы Ду 400 и больше на экране", fragment_ids=[74]))
    assert out["spec"]["fragment_ids"] == [74] and out["spec"]["in_view"] is False  # охвата нет — без него
    assert out["total"] == 3 and out["confidence"] == 0.9 and "Условный диаметр ≥ 400" in out["description"]
    assert "2=бесканальная" in calls[0]["user"] and "Текущий год" in calls[0]["user"]

    async def fake_near(**kw):
        return tools.SelectPlan(spec=ns.SelectSpec(near={"node_name": "3-47", "meters": 500}), confidence=0.9)

    monkeypatch.setattr(ai_client, "ask_structured", fake_near)
    near_conn = _Conn(node={"id": 1, "fileid": 1, "name": "3-47", "lon": 76.9, "lat": 43.2})
    out = asyncio.run(tools.select_by_phrase(near_conn, text="всё в 500 м от 3-47", fragment_ids=[72]))
    assert out["spec"]["fragment_ids"] is None  # место задаёт узел, а не фрагменты на карте

    async def fake_empty(**kw):
        return tools.SelectPlan(spec=ns.SelectSpec(fragment_ids=[]), confidence=0.9)

    monkeypatch.setattr(ai_client, "ask_structured", fake_empty)
    out = asyncio.run(tools.select_by_phrase(_Conn(), text="все участки", fragment_ids=[72]))
    assert out["spec"]["fragment_ids"] == [72]  # пустой список модели — как «не названы»

    async def fake_bad(**kw):
        return tools.SelectPlan(spec=ns.SelectSpec(conditions=[{"field": "colour", "op": "eq", "value": 1}]),
                                confidence=0.5)

    monkeypatch.setattr(ai_client, "ask_structured", fake_bad)
    out = asyncio.run(tools.select_by_phrase(_Conn(), text="цветные трубы"))
    assert out["items"] == [] and "недоступно" in out["error"]


def test_mcp_select_tool(monkeypatch):
    from auth import AuthUser
    from tgid_mcp import tools

    async def write(**kwargs):
        pass

    monkeypatch.setattr(tools.activity, "write", write)

    @asynccontextmanager
    async def acquire():
        yield _Conn([_line_row(1, f_diameter=400.0)])

    monkeypatch.setattr(tools, "acquire_conn", acquire)
    assert "diameter" in tools.TOOLS["select_network"].description
    user = AuthUser(sub="petr", role="viewer", username="petr")
    res = asyncio.run(tools.call_tool("select_network", {"conditions": [
        {"field": "diameter", "op": "ge", "value": 400}]}, user))
    data = res["structuredContent"]
    assert res["isError"] is False and data["total"] == 3 and "geojson" not in data
    res = asyncio.run(tools.call_tool("select_network", {"conditions": [
        {"field": "colour", "op": "eq", "value": 1}]}, user))
    assert res["isError"] is True and "недоступно" in res["content"][0]["text"]
