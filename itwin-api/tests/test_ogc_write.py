"""OGC API — Features, часть 4: правила записи (database/ogc_transactions.py) и маршруты (routers/ogc_write.py)."""

import pytest
from fastapi.testclient import TestClient

from database import ogc_transactions as ot

PIPE = {"fileid": 74, "name": "M-1", "node_start": 1, "node_end": 2, "sign": 1, "diameter_mm": 300.0,
        "diameter_internal_mm": 309.0, "length_m": 52.4, "state_supply": 1, "state_return": 1}
PIPE_VERSIONS = {"linesobj:10": "2026-10-29T10:00:00#123", "heatpipesections:77": "456"}


def test_etag_and_if_match():
    tag = ot.etag(PIPE_VERSIONS)
    assert tag.startswith('"') and tag == ot.etag(dict(reversed(list(PIPE_VERSIONS.items()))))
    assert tag != ot.etag({**PIPE_VERSIONS, "heatpipesections:77": "457"})
    assert ot.if_match_ok(None, tag) and ot.if_match_ok("*", tag) and ot.if_match_ok(f'"x", {tag}', tag)
    assert not ot.if_match_ok('"stale"', tag)
    assert ot.row_xmin("2026-10-29T10:00:00#123") == "123" and ot.row_xmin("456") == "456"


def test_property_changes_whole_feature_and_read_only():
    # клиент прислал объект целиком: совпадающие только читаемые свойства пропускаются
    assert ot.property_changes("pipes", PIPE, {**PIPE, "diameter_mm": 400, "name": " M-1 "}) == {"diameter_mm": 400}
    with pytest.raises(ot.OgcWriteError) as e:
        ot.property_changes("pipes", PIPE, {"length_m": 60})
    assert e.value.status == 422 and "только для чтения" in e.value.message
    with pytest.raises(ot.OgcWriteError, match="нет свойства"):
        ot.property_changes("pipes", PIPE, {"color": "red"})
    assert ot.property_changes("pipes", PIPE, {"name": None}) == {"name": None}  # merge patch: очистить


def test_card_changes_map_to_rows():
    rows = ot.card_changes("pipes", 10, {"name": "M-2", "diameter_mm": 400}, PIPE_VERSIONS)
    assert rows == [{"table": "linesobj", "id": 10, "field": "registnum", "value": "M-2"},
                    {"table": "heatpipesections", "id": 77, "field": "diametercondit", "value": 400}]
    two = {**PIPE_VERSIONS, "heatpipesections:78": "1"}
    with pytest.raises(ot.OgcWriteError) as e:
        ot.card_changes("pipes", 10, {"diameter_mm": 400}, two)
    assert e.value.status == 409
    assert ot.card_changes("valves", 5, {"state": 2}, {"dampers:5": "9"}) == [
        {"table": "dampers", "id": 5, "field": "damperarmaturestateid", "value": 2}]


@pytest.mark.parametrize("geometry", [
    {"type": "Point", "coordinates": [200, 43]},
    {"type": "Point", "coordinates": ["a", 43]},
    {"type": "LineString", "coordinates": [[76.9, 43.2]]},
    {"type": "Polygon", "coordinates": []},
])
def test_bad_geometry(geometry):
    with pytest.raises(ot.OgcWriteError):
        ot.point(geometry) if geometry["type"] != "LineString" else ot.line_coords(geometry)


def test_same_geometry():
    cur = {"type": "LineString", "coordinates": [[76.9, 43.2], [76.91, 43.21]]}
    assert ot.same_geometry("pipes", cur, {"type": "LineString", "coordinates": [[76.90000001, 43.2], [76.91, 43.21]]})
    assert not ot.same_geometry("pipes", cur, {"type": "LineString", "coordinates": [[76.9, 43.2], [76.905, 43.205],
                                                                                    [76.91, 43.21]]})
    assert ot.same_geometry("nodes", {"type": "Point", "coordinates": [76.9, 43.2]},
                            {"type": "Point", "coordinates": [76.9, 43.2]})


# --- маршруты ---------------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    import main
    from auth import invalidate_user_status

    monkeypatch.setenv("AUTH_DISABLED", "true")  # пользователь dev (admin); права проверяют операции веба
    monkeypatch.delenv("TGID_CITY_DBS", raising=False)
    invalidate_user_status()
    from routers import ogc_write

    state = {"feature": {"type": "Feature", "id": 10, "geometry": {"type": "Point", "coordinates": [76.9, 43.2]},
                         "properties": {"fileid": 74, "name": "", "line_id": 3, "diameter_mm": 400.0, "state": 1}},
             "versions": {"dampers:10": "100"}, "saved": []}

    async def fake_state(cid, fid):
        return (dict(state["feature"]), dict(state["versions"])) if fid == 10 else (None, None)

    async def fake_save(body, user):
        state["saved"].append(([c.model_dump() for c in body.changes], body.versions))
        state["feature"]["properties"] = {**state["feature"]["properties"], "state": body.changes[0].value}
        state["versions"] = {"dampers:10": "101"}
        return {"rows": []}

    monkeypatch.setattr(ogc_write, "_state", fake_state)
    monkeypatch.setattr(ogc_write.card_router, "card_edit_save", fake_save)
    return TestClient(main.app), state


def test_patch_valve_state_with_etag(client):
    http, state = client
    tag = ot.etag({"dampers:10": "100"})
    r = http.patch("/api/ogc/collections/valves/items/10", json={"properties": {"state": 2}}, headers={"If-Match": tag})
    assert r.status_code == 200 and r.json()["properties"]["state"] == 2
    assert r.headers["etag"] == ot.etag({"dampers:10": "101"})
    assert state["saved"] == [([{"table": "dampers", "id": 10, "field": "damperarmaturestateid", "value": 2}],
                               {"dampers:10": "100"})]
    # тот же ETag ещё раз — версия ушла вперёд
    r = http.patch("/api/ogc/collections/valves/items/10", json={"properties": {"state": 1}}, headers={"If-Match": tag})
    assert r.status_code == 412 and len(state["saved"]) == 1


def test_patch_rejects_read_only_and_derived_geometry(client):
    http, state = client
    assert http.patch("/api/ogc/collections/valves/items/10", json={"properties": {"diameter_mm": 500}}).status_code == 422
    r = http.patch("/api/ogc/collections/valves/items/10",
                   json={"geometry": {"type": "Point", "coordinates": [76.95, 43.25]}})
    assert r.status_code == 422 and state["saved"] == []


def test_unsupported_operations(client):
    http, _ = client
    assert http.patch("/api/ogc/collections/consumers/items/10", json={"properties": {"name": "x"}}).status_code == 405
    assert http.delete("/api/ogc/collections/valves/items/10").status_code == 405
    assert http.post("/api/ogc/collections/heat_sources/items", json={"type": "Feature"}).status_code == 405
    assert http.patch("/api/ogc/collections/valves/items/11", json={"properties": {"state": 2}}).status_code == 404
    assert http.patch("/api/ogc/collections/nope/items/10", json={}).status_code == 404


def test_create_validation(client):
    http, _ = client
    r = http.post("/api/ogc/collections/pipes/items", json={"type": "Feature", "properties": {"node_start": 5, "node_end": 5}})
    assert r.status_code == 422
    r = http.post("/api/ogc/collections/nodes/items",
                  json={"type": "Feature", "geometry": {"type": "Point", "coordinates": [76.9, 43.2]},
                        "properties": {"node_kind": "XX"}})
    assert r.status_code == 422
    r = http.post("/api/ogc/collections/nodes/items", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400
