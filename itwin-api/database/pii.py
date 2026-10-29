"""Персональные данные в ответах API: маскирование для пользователей без права «Персональные данные» (pii_view).

Раздел 2б плана модернизации (152-ФЗ, закон РК о ПДн): ФИО физических лиц, телефоны, e-mail, ИИН, лицевые счета
и номера договоров потребителей видны полностью только с правом pii_view; остальным — замаскированными.
Данные в базе не меняются (их ведёт и десктоп): маскируется ответ.

Поле узнаётся по имени колонки (телефон, e-mail, ИИН, счёт, договор, владелец/абонент), значение — по виду:
в поле владельца или абонента маскируются только ФИО и телефоны («ТОО "Пример"» остаётся, «Индивидуальный
предприниматель ИВАНОВА МАРИЯ ПЕТРОВНА, тел. 8 700 000 0012» → «… И*** М. П., тел. * *** *** **12»).
Где применяется — main.PiiMaskMiddleware (JSON-ответы API) и выгрузки, которые отдают такие поля.
"""
from __future__ import annotations

import os
import re
from typing import Any, Callable, Optional

PERMISSION = "pii_view"
MASK = "*"

# --- поля по имени колонки ------------------------------------------------------------------
_PHONE_KEY = re.compile(r"phone|telefon|kontaktn", re.I)
_EMAIL_KEY = re.compile(r"(^|_)e?-?mail($|_)", re.I)
_IIN_KEY = re.compile(r"(^|_)(iin|inn)($|_)", re.I)
_ACCOUNT_KEY = re.compile(r"lic\w*schet|(^|_)lsch?($|_)|account_?(num|number|no)?$|dogovor|contract_number", re.I)
_PARTY_KEY = re.compile(r"(^|_)(owner(_dop)?|abonent|vladelets\w*|vladelec\w*)$", re.I)

# грубая проверка тела ответа до разбора JSON: есть ли вообще такие ключи
_BODY_HINT = re.compile(rb'"[A-Za-z0-9_]*(phone|telefon|kontaktn|mail|iin|inn|schet|lsch|account|dogovor|contract_number'
                        rb'|owner|abonent|vladel)[A-Za-z0-9_]*"\s*:', re.I)

# --- значения -------------------------------------------------------------------------------
_UP = "А-ЯЁӘІҢҒҮҰҚӨҺ"
# «?» внутри слова — казахская буква, потерянная при перекодировке исходных данных («Нурлан?ызы»)
_LO = "а-яёәіңғүұқөһ?"
_WORD = f"(?:[{_UP}][{_LO}]+(?:-[{_UP}][{_LO}]+)?|[{_UP}]{{2,}}(?:-[{_UP}]{{2,}})?)"
_PATRONYMIC = (rf"(?:[{_UP}][{_LO}]+(?:вич|вна|ична|улы|ұлы|\?лы|ызы|оглы)"
               rf"|[{_UP}]{{2,}}(?:ВИЧ|ВНА|ИЧНА|УЛЫ|ҰЛЫ|\?ЛЫ|ЫЗЫ|ОГЛЫ))")
# Фамилия Имя Отчество (в любом регистре слов)
_FULL_NAME = re.compile(rf"(?<![{_UP}{_LO}])({_WORD})\s+({_WORD})\s+({_PATRONYMIC})(?![{_UP}{_LO}])")
# Фамилия И.О. / Фамилия И. О. / Фамилия И. — у инициала точка обязательна
_INITIALS = re.compile(rf"(?<![{_UP}{_LO}])({_WORD})\s+([{_UP}])\.(?:\s?([{_UP}])\.)?")
# «… Орлов А» — фамилия и инициал без точки в конце перечня
_TAIL_INITIAL = re.compile(rf"(?<![{_UP}{_LO}])([{_UP}][{_LO}]+)\s+([{_UP}])(?=\s*(?:$|[,;]))")
# телефон или другой длинный номер внутри текста: от 6 цифр с разделителями
_NUMBER = re.compile(r"\+?\d(?:[\d\s\-().]*\d){5,}")
_EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def enabled() -> bool:
    """PII_MASKING=false выключает маскирование (например, на закрытом стенде без ПДн)."""
    return os.getenv("PII_MASKING", "true").strip().lower() not in {"0", "false", "no", "off"}


def can_view(user: Any) -> bool:
    """Пользователь видит ПДн полностью: право pii_view (у администратора — всегда)."""
    if user is None:
        return False
    try:
        return bool(user.perms.has(PERMISSION))
    except Exception:  # noqa: BLE001 — права не определить: безопаснее маскировать
        return False


def _digits_but_last(text: str, keep: int) -> str:
    total = sum(ch.isdigit() for ch in text)
    out, seen = [], 0
    for ch in text:
        if ch.isdigit():
            seen += 1
            out.append(ch if seen > total - keep else MASK)
        else:
            out.append(ch)
    return "".join(out)


def mask_phone(text: str) -> str:
    """Все цифры, кроме двух последних: «8-700-000-00-88» → «*-***-***-**-88»."""
    return _digits_but_last(text, 2)


def mask_account(text: str) -> str:
    """Счёт, договор, ИИН: цифры, кроме четырёх последних; буквы номера остаются."""
    return _digits_but_last(text, 4)


def _surname(word: str) -> str:
    return word[0] + MASK * 3


def mask_person_text(text: str) -> str:
    """ФИО физических лиц и номера в свободном тексте (владелец, абонент); названия организаций не трогает."""
    original = text
    text = _FULL_NAME.sub(lambda m: f"{_surname(m.group(1))} {m.group(2)[0]}. {m.group(3)[0]}.", text)
    text = _INITIALS.sub(
        lambda m: f"{_surname(m.group(1))} {m.group(2)}.{(m.group(3) + '.') if m.group(3) else ''}", text)
    if text != original:
        # в перечне лиц («Козлов С. Орлов А») последний бывает без точки; «Корпус А» сам по себе — не лицо
        text = _TAIL_INITIAL.sub(lambda m: f"{_surname(m.group(1))} {m.group(2)}", text)
    text = _NUMBER.sub(lambda m: mask_phone(m.group(0)), text)
    return _EMAIL.sub(lambda m: f"{m.group(1)}{MASK * 3}@{m.group(2)}", text)


def mask_email(text: str) -> str:
    """«ivan@mail.kz» → «i***@mail.kz»; не похоже на адрес — первая буква и звёздочки."""
    masked = _EMAIL.sub(lambda m: f"{m.group(1)}{MASK * 3}@{m.group(2)}", text)
    return masked if masked != text else text[:1] + MASK * 3


def masker_for(key: str) -> Optional[Callable[[str], str]]:
    """Как маскировать значение колонки key; None — колонка без ПДн."""
    if _PHONE_KEY.search(key):
        return mask_phone
    if _EMAIL_KEY.search(key):
        return mask_email
    if _IIN_KEY.search(key) or _ACCOUNT_KEY.search(key):
        return mask_account
    if _PARTY_KEY.search(key):
        return mask_person_text
    return None


def may_contain(body: bytes) -> bool:
    """Быстрая проверка тела JSON: есть ли ключи, похожие на поля ПДн (до разбора)."""
    return bool(_BODY_HINT.search(body))


def mask_json(data: Any) -> tuple[Any, int]:
    """Копия JSON с замаскированными полями ПДн и число изменённых значений."""
    changed = 0

    def walk(node: Any) -> Any:
        nonlocal changed
        if isinstance(node, dict):
            out = {}
            for k, v in node.items():
                fn = masker_for(k) if isinstance(k, str) else None
                if fn is not None and isinstance(v, str) and v:
                    masked = fn(v)
                    if masked != v:
                        changed += 1
                    out[k] = masked
                else:
                    out[k] = walk(v)
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(data), changed


def mask_record(record: dict[str, Any]) -> dict[str, Any]:
    """Одна строка выгрузки (колонка → значение) с замаскированными ПДн."""
    out = {}
    for k, v in record.items():
        fn = masker_for(k)
        out[k] = fn(v) if fn is not None and isinstance(v, str) and v else v
    return out
