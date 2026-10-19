"""«История»: подпись правки карточки, откат до выбранной операции (остановка на первой неотменяемой)."""
import asyncio

from database import topology_history as th
from database.topology import TopologyConflictError, TopologyNothingToUndo
from routers.card_edit import card_edit_summary


def test_card_edit_summary_text_and_fields():
    rows = [{"table": "heatPipeSections", "key": 5, "changed": {"x1": {"old": 1, "new": 2}, "x2": {"old": "a", "new": "b"}}},
            {"table": "heatPipeSections", "key": 6, "changed": {"x3": {"old": None, "new": 3}, "x4": {"old": 0, "new": 1}}}]
    s = card_edit_summary(rows)
    assert s["text"].startswith("паспорт участка 5 — ") and s["text"].endswith("и ещё 1")
    assert [f["field"] for f in s["fields"]] == ["x1", "x2", "x3", "x4"]
    assert s["table"] == "heatpipesections" and s["id"] == 5


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


def test_undo_to_stops_at_target_and_on_conflict(monkeypatch):
    queue = [30, 29, 28, 27]

    async def fake_undo(actor, operation_id=None):
        if not queue:
            raise TopologyNothingToUndo("пусто")
        op = queue.pop(0)
        if op == 27:
            raise TopologyConflictError({"nodes:1": "changed"}, "изменён")
        return {"operation_id": op}

    monkeypatch.setattr(th, "undo_last_operation", fake_undo)
    res = _run(th.undo_to("ivan", 29))
    assert res["undone"] == [30, 29] and res["complete"] and res["stopped"] is None
    res = _run(th.undo_to("ivan", 20))  # дальше 28 — конфликт на 27
    assert res["undone"] == [28] and not res["complete"] and "изменён" in res["stopped"]["reason"]
