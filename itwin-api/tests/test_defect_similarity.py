"""Похожие аварии: признаки из текста дефекта, сходство, маскирование текста, MCP-инструменты."""

from types import SimpleNamespace

import pytest

from database import defect_similarity as ds


@pytest.mark.parametrize("text, kind, pipe, diameter", [
    ("Порыв на Т1 Ду 273", "rupture", "supply", 273),
    ("Свищ 2Ду100 по Т2 на 7 часов", "fistula", "both", 100),
    ("утечка на теплотрассе Ду100мм Т1", "leak", "supply", 100),
    ("Утечка на т/тр Ду150 по Т2", "leak", "return", 150),
    ("Замена участка трубы ДУ100 L=12м Т1,Т2", "reconstruction", "both", 100),
    ("Парение из камеры, обратный трубопровод 219 мм", "leak", "return", 219),
    ("Провал плиты перекрытия камеры", "chamber", None, None),
    ("Коррозия стенки, утонение до 3 мм", "corrosion", None, None),  # 3 мм — не диаметр
    ("", None, None, None),
])
def test_features(text, kind, pipe, diameter):
    assert ds.features(text) == {"kind": kind, "pipe": pipe, "diameter": diameter}


def test_partial_scores():
    assert ds.kind_score("rupture", "rupture") == 1 and ds.kind_score("rupture", "fistula") == 0.6
    assert ds.kind_score("rupture", "chamber") == 0 and ds.kind_score(None, "leak") == 0
    assert ds.pipe_score("supply", "supply") == 1 and ds.pipe_score("supply", "both") == 0.5
    assert ds.pipe_score("supply", "return") == 0
    assert ds.diameter_score(100, 100) == 1 and ds.diameter_score(219, 273) == 0.5 and ds.diameter_score(100, 273) == 0


def test_score_and_reasons():
    ref = ds.features("Свищ по Т2 Ду100")
    near = ds.score(ref, ds.features("Свищ Т2 Ду100"), 50, 0.4, 0.4)
    far = ds.score(ref, ds.features("Порыв Т1 Ду100"), 900, 0.1, 0.4)
    assert near["score"] > 0.9 and near["reasons"] == ["тот же вид — свищ", "Т2", "Ду100", "50 м", "общие слова"]
    assert far["score"] < near["score"] and far["reasons"][0] == "похожий вид — порыв"
    no_place = ds.score(ref, ds.features("Свищ Т2 Ду100"), None, 0, 0)
    assert no_place["parts"]["distance"] == 0 and "м" not in " ".join(no_place["reasons"])


def test_masked_text_without_pii_permission(monkeypatch):
    from routers.defect_similarity import masked

    monkeypatch.setenv("PII_MASKING", "true")
    result = {"items": [{"text": "Утечка у дома, сообщил Иванов Пётр Сергеевич, тел. 87011234567"}]}
    viewer = SimpleNamespace(perms=SimpleNamespace(has=lambda p: False))
    text = masked(result, viewer)["items"][0]["text"]
    assert "Иванов" not in text and "1234567" not in text and text.startswith("Утечка у дома")
    admin = SimpleNamespace(perms=SimpleNamespace(has=lambda p: True))
    raw = {"items": [{"text": "Иванов Пётр Сергеевич"}]}
    assert masked(raw, admin)["items"][0]["text"] == "Иванов Пётр Сергеевич"


def test_mcp_tools_registered():
    from tgid_mcp import tools

    assert {"similar_defects", "failure_hotspots"} <= set(tools.TOOLS)
    names = {t["name"] for t in tools.describe_tools()}
    assert {"similar_defects", "failure_hotspots"} <= names


def test_display_text_drops_repeats():
    parts = ["", "Утечка на т/тр Ду100 Т1", "Утечка на т/тр Ду100 Т1 Замена 2 м", None, "утечка на т/тр ду100 т1"]
    assert ds.display_text(parts) == "Утечка на т/тр Ду100 Т1 Замена 2 м"
    assert ds.display_text(["Порыв Т1", "Замена отвода"]) == "Порыв Т1 · Замена отвода"
