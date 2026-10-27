"""Протокол расчёта sety: разбор HTML-вывода в записи, хранение и переход к объектам."""

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from database import calc_protocols as CP
from routers import calc
from utils.calc_protocol import categorize, parse_protocol

HEAD = """<span style="font-weight:bold;">БД: almatygid_copy Фрагмент: Маг. сети</span>
<span style="font-weight:bold;">Температура наружного воздуха -25.0</span>
Расчет начат
1 фрагментов
-----------------
Фрагмент 1/1 [<a name='node' id='535303' href='x'>Маг. сети [РС1 ТЭЦ-1 О]</a>]
Узлы с заданым напором
1 <a name='node' id='535303' href='[РС1 ТЭЦ-1 О]'>[РС1 ТЭЦ-1 О]</a>
"""

REGULATOR = """<span style="color:brown">Регулятор давления <a name='line2' id1='535330' id2='535330' href='a'>[(УР2) М2 А О - М2 Б О]</a> не может обеспечить давление в узле <a name='node' id='535330' href='b'>[(УР2) М2 А О]</a>
    Задано 59.0 м. получено 49.66 м., расход 69.96 т/ч</span>
"""

# незакрытый span («режим реверса») не должен склеиваться со следующим сообщением
REVERSE = """<span style="color:brown">Регулятор давления <a name='line2' id1='536013' id2='535143' href='a'>[мтк13-21 О - ур13 О]</a> работает в режиме реверса: уточните направление установки РД
<span style="color:red">Насос <a name='line2' id1='7' id2='8' href='a'>[Н1]</a> не обеспечивает напор</span>
"""

SUBNET = """-----------------
<span style="color:brown">Не рассчитано подсетей без узла с заданным напором: 2 (узлов 30)</span>
<span style="color:brown">    Подсеть из 26 узлов: <a name='node' id='535273' href='a'>[М18 18-42 О]</a></span>
<span style="color:brown">    Подсеть из 4 узлов: <a name='node' id='534666' href='a'>[М1 ТК-5 О]</a></span>
"""


def test_entries_carry_severity_objects_category_and_fix():
    p = parse_protocol(HEAD + "\n" + REGULATOR + REVERSE + SUBNET + "Время расчета 1.5 сек\n")
    entries = p["entries"]
    assert [e["category"] for e in entries] == ["regulator", "regulator", "pump", "subnetwork"]

    reg = entries[0]
    assert reg["severity"] == "warning" and reg["fix"] == "object"
    assert "Задано 59.0 м." in reg["text"]  # строка продолжения — в той же записи
    assert reg["objects"][0] == {"kind": "line2", "id1": 535330, "id2": 535330, "label": "(УР2) М2 А О - М2 Б О"}
    assert reg["component"]["object"]["id"] == 535303

    assert entries[1]["severity"] == "warning" and "Насос" not in entries[1]["text"]
    assert entries[2]["severity"] == "error" and entries[2]["objects"][0]["id1"] == 7

    sub = entries[3]
    assert sub["fix"] == "fixed_head"
    assert [o["id"] for o in sub["objects"]] == [535273, 534666]

    s = p["summary"]
    assert (s["errors"], s["warnings"]) == (1, 3)
    assert s["by_category"]["regulator"] == {"error": 0, "warning": 2}
    assert s["category_labels"]["pump"] == "Насосы"
    assert s["duration_s"] == 1.5
    assert any("Температура наружного воздуха" in h for h in s["header"])


def test_calc_params_error_without_objects_and_duplicates_counted():
    msg = '<span style="color:red">Температура наружного воздуха должна быть от -25.0 до 8.0</span>\n'
    p = parse_protocol(msg + msg)
    assert len(p["entries"]) == 1
    e = p["entries"][0]
    assert (e["category"], e["fix"], e["count"], e["objects"]) == ("calc_params", "calc_params", 2, [])


def test_entry_without_link_falls_back_to_component_object():
    out = HEAD + '\n<span style="color:red">Во фрагменте нет источников тепла</span>\n'
    e = parse_protocol(out)["entries"][0]
    assert e["category"] == "source" and e["fix"] == "object"
    assert e["objects"] == [{"kind": "node", "id": 535303, "label": "Маг. сети [РС1 ТЭЦ-1 О]", "context": True}]


def test_fragment_list_sets_fragment_id_and_negative_ids_are_dropped():
    out = ("==== Фрагмент 41: Сети ТЭЦ-2 ====\n"
           "<span style=\"color:red\">Ошибка: <a name='node' id='-1' href='a'>[?]</a> нет данных</span>\n")
    e = parse_protocol(out)["entries"][0]
    assert e["fragment_id"] == 41 and e["objects"] == [] and e["fix"] is None


def test_categorize_order():
    assert categorize("Не задан узел с ЗН")[0] == "fixed_head"
    assert categorize("Расчет подсети не выполнен: система уравнений не решена")[0] == "divergence"
    assert categorize("Нет Источника тепла в расчетной схеме РС1")[0] == "rs"
    assert categorize("что-то непонятное") == ("other", None)


# --- маршруты ---

class _Conn:
    def __init__(self, rows=None, exists=True):
        self.rows = rows or []
        self.exists = exists
        self.calls = []

    async def fetchval(self, sql, *args):
        return self.exists

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        if callable(self.rows):
            return self.rows(sql, args)
        return self.rows


def _client(monkeypatch, conn):
    import main

    monkeypatch.setenv("AUTH_DISABLED", "true")  # test_auth выставляет false на весь процесс

    @asynccontextmanager
    async def _acq():
        yield conn

    monkeypatch.setattr(calc, "acquire_conn", _acq)
    return TestClient(main.app)


def test_protocol_routes(monkeypatch):
    row = {"id": 5, "request_id": "r1", "fileid": 74, "status": "success", "errors": 1, "warnings": 2,
           "summary": '{"errors": 1}', "entries": "[]", "created_at": None, "output": "<b>x</b>"}
    client = _client(monkeypatch, _Conn([row]))
    r = client.get("/api/v1/calculations/protocols/5")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] == {"errors": 1} and body["entries"] == [] and "output" not in body
    assert client.get("/api/v1/calculations/protocols/5", params={"output": True}).json()["output"] == "<b>x</b>"
    assert client.get("/api/v1/calculations/protocols/by-request/r1").json()["items"][0]["id"] == 5
    assert client.get("/api/v1/calculations/protocols").json()["items"][0]["id"] == 5


def test_protocol_routes_without_table(monkeypatch):
    client = _client(monkeypatch, _Conn(exists=False))
    assert client.get("/api/v1/calculations/protocols").json() == {"items": []}
    assert client.get("/api/v1/calculations/protocols/1").status_code == 404
    assert client.get("/api/v1/calculations/35/protocol").status_code == 404


def test_internal_line_by_label_matches_names_of_internal_scheme():
    rows = [
        {"id": 325861, "name1": "1КЗ-22Б", "name2": "1КЗ-22А"},
        {"id": 324152, "name1": "1КЗ-22А", "name2": "1КЗ-22Б"},
        {"id": 1, "name1": "Рег  вх", "name2": "Рег вых"},
    ]
    # порядок концов как в подписи важнее обратного
    assert CP.internal_line_by_label(rows, "(6-8 УР2ЧАП) М2 1КЗ-22А О - М2 1КЗ-22Б О") == 324152
    assert CP.internal_line_by_label(rows, "(6-8 УР2ЧАП) М2 1КЗ-22Б О - М2 1КЗ-22А О") == 325861
    # вложенные скобки владельца и лишние пробелы в именах
    assert CP.internal_line_by_label(rows, "(М5 НС5 (подпор)) М5 Рег вх О - М5 Рег вых О") == 1
    # имя — целым словом: «1КЗ-22» не совпадает с «1КЗ-22А»
    assert CP.internal_line_by_label([{"id": 9, "name1": "1КЗ-22", "name2": "1КЗ-22Б"}],
                                     "(X) М2 1КЗ-22А О - М2 1КЗ-22Б О") is None
    assert CP.internal_line_by_label(rows, "без разделителя") is None


def test_locate_objects_resolves_pairs_and_internal_nodes(monkeypatch):
    point = {"type": "Point", "coordinates": [76.9, 43.2]}
    line = {"type": "LineString", "coordinates": [[76.9, 43.2], [76.91, 43.21]]}

    def rows(sql, args):
        if sql is CP._PAIR_SQL:
            return [{"a": 2, "b": 1, "id": 900}]  # найден в обратном направлении
        if sql is CP._NODE_SQL:
            return [{"id": i, "shown_id": 100 if i == 5 else i, "geom": point} for i in args[0]]
        if sql is CP._INTERNAL_LINES_SQL:
            return [{"owner": 8, "id": 950, "name1": "Рег вх", "name2": "Рег вых"}]
        return [{"id": i, "owner_id": 8 if i == 950 else None, "geom": line} for i in args[0]]

    conn = _Conn(rows)
    r = _client(monkeypatch, conn).post("/api/v1/calculations/protocols/locate", json={"objects": [
        {"kind": "node", "id": 5},
        {"kind": "line2", "id1": 1, "id2": 2},
        {"kind": "line2", "id1": 7, "id2": 7},       # внутри одного узла — точка узла
        # устройство внутренней схемы камеры 8: sety пишет оба конца владельцем — участок по подписи
        {"kind": "line2", "id1": 8, "id2": 8, "label": "(НС-8) М1 Рег вх О - М1 Рег вых О"},
        {"kind": "line2", "id1": 3, "id2": 4},       # участка нет — первый узел
        {"kind": "line", "id": "bad"},
    ]})
    assert r.status_code == 200
    d = r.json()
    assert d["pairs"] == {"1-2": {"line_id": 900}, "3-4": {"node_id": 3},
                          "8-8|(НС-8) М1 Рег вх О - М1 Рег вых О": {"line_id": 950}}
    assert sorted(d["nodes"]) == ["3", "5", "7", "8"] and d["nodes"]["5"]["shown_id"] == 100
    assert sorted(d["lines"]) == ["900", "950"] and d["lines"]["900"]["geometry"]["type"] == "LineString"
    assert d["lines"]["950"]["owner_id"] == 8
