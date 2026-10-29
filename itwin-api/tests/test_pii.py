"""Персональные данные: маскирование значений (database/pii.py), право pii_view и прослойка ответов API."""

import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.testclient import TestClient

import pii_middleware
from auth import AuthUser
from database import pii
from permissions import effective


@pytest.mark.parametrize("value, expected", [
    ("Индивидуальный  предприниматель ИВАНОВА МАРИЯ ПЕТРОВНА", "Индивидуальный  предприниматель И*** М. П."),
    ("Сидорова Айгуль Маратовна,  тел.8 700 000 0012", "С*** А. М.,  тел.* *** *** **12"),
    ("Тестов Арман Ерланұлы", "Т*** А. Е."),
    # казахские буквы, потерянные при перекодировке исходных данных, — «?»
    ("ИП Тестова Ба?ыт Нурлан?ызы", "ИП Т*** Б. Н."),
    ("Что? Где? Когда?", "Что? Где? Когда?"),
    ("Петров К.Т.", "П*** К.Т."),
    ("ИП Иванов И. И.", "ИП И*** И.И."),
    ("Козлов С. Орлов А", "К*** С. О*** А"),
    ("Иванов И. Петров П.", "И*** И. П*** П."),
    ("контакт ivan.petrov@mail.kz", "контакт i***@mail.kz"),
    # организации и объекты — без изменений
    ('ТОО "Тест Строй"', 'ТОО "Тест Строй"'),
    ("Следственный изолятор КНБ РК", "Следственный изолятор КНБ РК"),
    ('Некоммерческое акционерное общество "Тестовый университет"',
     'Некоммерческое акционерное общество "Тестовый университет"'),
    ("КСП Арман-11", "КСП Арман-11"),
    ("Корпус А", "Корпус А"),
])
def test_person_text(value, expected):
    assert pii.mask_person_text(value) == expected


def test_phone_account_email():
    assert pii.mask_phone("8-700-000-00-88") == "*-***-***-**-88"
    assert pii.mask_phone("10-20-30, 8700-000-00-71") == "**-**-**, ****-***-**-71"
    assert pii.mask_account("123456789012") == "********9012"
    assert pii.mask_account("Д-2024/15783") == "Д-****/*5783"
    assert pii.mask_email("ivan@mail.kz") == "i***@mail.kz"
    assert pii.mask_email("не адрес") == "н***"


def test_fields_by_column_name():
    masked = {k for k in ("phone", "managerphone", "telefon", "kontaktnyy_telefon", "responsiblephone", "owner",
                          "owner_dop", "abonent", "vladelets_istochnika_es", "contract_number", "dogovor", "email",
                          "e_mail", "iin", "licevoy_schet") if pii.masker_for(k)}
    assert len(masked) == 15
    for key in ("name", "fio", "potrebitel", "txt", "owner_id", "ownerid", "password", "binding", "mailing_list"):
        assert pii.masker_for(key) is None, key


def test_mask_json_keeps_labels_and_counts():
    data = {"items": [{"owner": "Петров К.Т.", "phone": "10-20-52", "name": "ж/д", "owner_id": 5}],
            "labels": {"phone": "Телефон", "owner": "Владелец"}, "total": 1}
    masked, changed = pii.mask_json(data)
    assert changed == 2
    assert masked["items"][0] == {"owner": "П*** К.Т.", "phone": "**-**-52", "name": "ж/д", "owner_id": 5}
    assert masked["labels"] == data["labels"] and data["items"][0]["owner"] == "Петров К.Т."
    assert pii.may_contain(b'{"items":[{"managerphone":"1"}]}') and not pii.may_contain(b'{"items":[{"name":"x"}]}')
    assert pii.mask_record({"owner": "Иванов И.И.", "dogovor": "12345678", "n": None}) == \
        {"owner": "И*** И.И.", "dogovor": "****5678", "n": None}


def test_permission_presets():
    assert not effective("viewer", "", frozenset(), False).has("pii_view")
    assert not effective("calculator", "", frozenset(), False).has("pii_view")
    assert effective("editor", "", frozenset(), False).has("pii_view")
    assert effective("admin", "", frozenset(), False).has("pii_view")
    assert effective("viewer", '{"general": {"pii_view": true}}', frozenset(), False).has("pii_view")
    assert effective("viewer", "", frozenset({"acts"}), True).has("pii_view")
    assert pii.can_view(AuthUser(sub="1", role="editor", username="e"))
    assert not pii.can_view(AuthUser(sub="2", role="viewer", username="v")) and not pii.can_view(None)


# --- прослойка ---------------------------------------------------------------------------------

def _client(monkeypatch, user):
    app = FastAPI()

    @app.get("/api/alseko/loads")
    def loads():
        return {"items": [{"id": 1, "owner": "Индивидуальный предприниматель Петров Пётр Петрович",
                           "contract_number": "445566778", "name": "ж/д"}]}

    @app.get("/api/plain")
    def plain():
        return {"items": [{"id": 1, "name": "ТК-12"}]}

    @app.get("/api/text")
    def text():
        return PlainTextResponse("owner: Иванов И.И.")

    @app.get("/api/v1/admin/users")
    def users():
        return {"items": [{"phone": "87011234567"}]}

    async def fake_user(scope):
        return user

    monkeypatch.setattr(pii_middleware, "_user", fake_user)
    app.add_middleware(pii_middleware.PiiMaskMiddleware)
    return TestClient(app)


def test_middleware_masks_for_viewer(monkeypatch):
    client = _client(monkeypatch, AuthUser(sub="2", role="viewer", username="v"))
    r = client.get("/api/alseko/loads")
    item = r.json()["items"][0]
    assert item["owner"] == "Индивидуальный предприниматель П*** П. П." and item["contract_number"] == "*****6778"
    assert item["name"] == "ж/д" and int(r.headers["content-length"]) == len(r.content)
    assert client.get("/api/plain").json() == {"items": [{"id": 1, "name": "ТК-12"}]}
    assert client.get("/api/text").text == "owner: Иванов И.И."  # не JSON — как есть
    assert client.get("/api/v1/admin/users").json()["items"][0]["phone"] == "87011234567"


def test_middleware_keeps_data_for_permitted_and_big_bodies(monkeypatch):
    client = _client(monkeypatch, AuthUser(sub="1", role="editor", username="e"))
    assert "Петров" in client.get("/api/alseko/loads").json()["items"][0]["owner"]

    client = _client(monkeypatch, None)  # без токена — маскировать
    assert "Петров" not in client.get("/api/alseko/loads").text

    monkeypatch.setattr(pii_middleware, "MAX_BYTES", 10)
    client = _client(monkeypatch, None)
    assert "Петров" in client.get("/api/alseko/loads").json()["items"][0]["owner"]

    monkeypatch.setenv("PII_MASKING", "false")
    monkeypatch.setattr(pii_middleware, "MAX_BYTES", 1 << 20)
    client = _client(monkeypatch, None)
    assert "Петров" in client.get("/api/alseko/loads").json()["items"][0]["owner"]
