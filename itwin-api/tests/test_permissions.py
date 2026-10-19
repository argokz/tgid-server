"""Права пользователей: шаблоны ролей, отличия, права PostgreSQL, «только свои», маршруты."""
import asyncio

import pytest
from fastapi.testclient import TestClient

import permissions as pm
from auth import AuthUser, create_access_token


def _run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


def test_role_presets():
    viewer = pm.effective("viewer")
    assert not viewer.any_network() and viewer.has("export") and not viewer.has("calc_run")

    calc = pm.effective("calculator")  # режимщик: режимные параметры и расчёты, без структуры сети
    assert calc.scope("consumer", "edit") == "all" and calc.scope("equipment", "edit") == "all"
    assert calc.scope("regime", "edit") == "all"
    assert calc.scope("line", "edit") == "none" and calc.scope("line", "create") == "none"
    assert calc.has("calc_run") and calc.has("calc_save") and not calc.has("journals")

    op = pm.effective("operator")
    assert op.scope("line", "create") == "all"
    assert op.scope("line", "delete") == "own" and op.scope("node", "move") == "own"
    assert op.scope("consumer", "edit") == "own" and not op.has("import")

    ed = pm.effective("editor")
    assert ed.scope("line", "edit") == "all" and ed.scope("line", "move") == "all"
    assert ed.scope("line", "delete") == "own" and ed.has("journals") and not ed.has("users_admin")

    adm = pm.effective("admin")
    assert all(adm.scope(k, a) == "all" for k, acts in pm.KIND_ACTIONS.items() for a in acts)
    assert adm.general == frozenset(pm.GENERAL)
    # неизвестная роль — как просмотр
    assert pm.effective("ghost").to_dict() == viewer.to_dict()


def test_overrides_and_diff_roundtrip():
    raw = '{"matrix": {"line": {"delete": "all", "fly": "all"}, "x": {}}, "general": {"import": true, "bad": true}}'
    ov = pm.parse_overrides(raw)
    assert ov == {"matrix": {"line": {"delete": "all"}}, "general": {"import": True}}
    p = pm.effective("operator", pm.overrides_json(ov))
    assert p.scope("line", "delete") == "all" and p.has("import")
    # «создавать только свои» не бывает — own → all
    assert pm.parse_overrides({"matrix": {"node": {"create": "own"}}}) == {"matrix": {"node": {"create": "all"}}}
    # снять право у роли
    p = pm.effective("editor", pm.overrides_json({"general": {"journals": False}, "matrix": {"line": {"edit": "own"}}}))
    assert not p.has("journals") and p.scope("line", "edit") == "own"
    # мусор — права роли
    assert pm.effective("editor", "{not json").to_dict() == pm.effective("editor").to_dict()

    # полный набор из админки → отличия → те же права
    full = pm.effective("editor").to_dict()
    full["matrix"]["consumer"]["delete"] = "all"
    full["general"] = [g for g in full["general"] if g != "refs"]
    diff = pm.diff_from_role("editor", full["matrix"], full["general"])
    assert diff == {"matrix": {"consumer": {"delete": "all"}}, "general": {"refs": False}}
    assert pm.effective("editor", pm.overrides_json(diff)).to_dict() == {**full, "general": sorted(full["general"])}


def test_pg_caps_map_to_matrix():
    p = pm.effective("viewer", "", frozenset({"network"}))
    assert p.scope("line", "edit") == "all" and p.scope("line", "delete") == "none"
    p = pm.effective("viewer", "", frozenset({"network_struct", "repairs"}))
    assert p.scope("node", "delete") == "all" and p.has("import") and p.has("journals")
    # пользователь PostgreSQL: сеть — только по предметным правам, журналы — по роли
    p = pm.effective("editor", "", frozenset(), True)
    assert not p.any_network() and p.has("journals")
    assert pm.effective("calculator", "", frozenset({"network"}), True).scope("line", "edit") == "all"
    assert pm.effective("admin", "", frozenset(), True).scope("line", "delete") == "all"


def test_auth_user_perms_and_catalog():
    u = AuthUser(sub="5", role="operator", username="ivan", overrides='{"general": {"calc_run": true}}')
    assert u.perms.has("calc_run") and u.perms.scope("line", "delete") == "own"
    cat = pm.catalog()
    assert [r["role"] for r in cat["roles"]] == ["viewer", "calculator", "operator", "editor", "admin"]
    assert {r["role"]: r["label"] for r in cat["roles"]}["calculator"] == "Режимщик"
    assert [k["kind"] for k in cat["kinds"]][:2] == ["line", "node"]
    assert pm.table_kind("realConsumers") == "consumer" and pm.table_kind("Dampers") == "equipment"


def test_ensure_targets_own_scope(monkeypatch):
    from database import authorship

    seen = {}

    async def fake_foreign(conn, username, targets):
        seen["args"] = (username, targets)
        return [f"участок {i}" for i in targets.get("linesobj", []) if i != 10]

    monkeypatch.setattr(authorship, "foreign_objects", fake_foreign)
    op = pm.effective("operator")
    # свой участок — можно
    _run(pm.ensure_targets(None, op, "ivan", "line", "delete", {"linesobj": [10]}))
    assert seen["args"] == ("ivan", {"linesobj": [10]})
    # чужой — отказ с перечнем
    with pytest.raises(pm.PermissionDenied) as exc:
        _run(pm.ensure_targets(None, op, "ivan", "line", "delete", {"linesobj": [10, 11]}))
    assert exc.value.objects == ["участок 11"] and "не ваши: участок 11" in exc.value.message
    # охват all — без проверки автора, none — отказ
    seen.clear()
    _run(pm.ensure_targets(None, pm.effective("admin"), "a", "line", "delete", {"linesobj": [11]}))
    assert not seen
    with pytest.raises(pm.PermissionDenied):
        _run(pm.ensure_targets(None, pm.effective("calculator"), "a", "line", "delete", {"linesobj": [11]}))


def _bearer(role, **extra):
    return {"Authorization": "Bearer " + create_access_token(username=f"t-{role}", role=role, **extra)}


def test_routes_follow_permissions(monkeypatch):
    import main

    monkeypatch.setenv("AUTH_DISABLED", "false")
    monkeypatch.setenv("AUTH_LIVE_USER_CHECK", "false")
    monkeypatch.setenv("MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("TOPOLOGY_MUTATIONS_ENABLED", "true")
    client = TestClient(main.app, raise_server_exceptions=False)
    chain = {"points": [{"kind": "new", "lng": 76.9, "lat": 43.2}, {"kind": "new", "lng": 76.901, "lat": 43.2}],
             "dry_run": True}
    # режимщик не создаёт участки, просмотр — тем более
    for role in ("viewer", "calculator"):
        r = client.post("/api/v1/topology/chains", json=chain, headers=_bearer(role))
        assert r.status_code == 403, role
    r = client.post("/api/v1/topology/chains", json=chain, headers=_bearer("calculator"))
    assert r.json()["detail"]["code"] == "permission_denied"
    # оператор и редактор проходят проверку прав (дальше — база)
    for role in ("operator", "editor"):
        assert client.post("/api/v1/topology/chains", json=chain, headers=_bearer(role)).status_code != 403, role
    # потребителя создать: оператор — да, режимщик — нет
    node = {"lng": 76.9, "lat": 43.2, "node_type": "PR"}
    assert client.post("/api/v1/topology/node", json=node, headers=_bearer("calculator")).status_code == 403
    assert client.post("/api/v1/topology/node", json=node, headers=_bearer("operator")).status_code != 403
    # карточка потребителя: режимщик правит (дальше — база), паспорт трубы — нет
    cons = {"changes": [{"table": "realConsumers", "id": 1, "field": "name", "value": "x"}], "dry_run": True}
    pipe = {"changes": [{"table": "heatPipeSections", "id": 1, "field": "x", "value": 1}], "dry_run": True}
    assert client.put("/api/v1/card-edit", json=cons, headers=_bearer("calculator")).status_code != 403
    assert client.put("/api/v1/card-edit", json=pipe, headers=_bearer("calculator")).status_code == 403
    # расчёт: режимщик — да, оператор — нет
    assert client.post("/api/v1/calculations/run", json={}, headers=_bearer("operator")).status_code == 403
    # управление пользователями — только с правом users_admin
    assert client.get("/api/v1/admin/users", headers=_bearer("editor")).status_code == 403
    assert client.get("/api/v1/admin/roles", headers=_bearer("admin")).json()["model"]["roles"][1]["label"] == "Режимщик"
