"""Права пользователей: роли-шаблоны + индивидуальные отличия (users.permissions).

Матрица «вид объекта × действие» с охватом none / own / all («own» — только объекты,
созданные пользователем: object_authorship в базе города, database/authorship.py) и общие
права (расчёты, выгрузки, журналы…). Роль задаёт шаблон, администратор может выдать или
снять отдельные права галочками — в users.permissions хранятся только отличия от шаблона.

Сервер проверяет права всегда сам: веб по /auth/me лишь прячет недоступные кнопки.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable, Optional

# Вид объекта сети → подпись (порядок — строки матрицы в админке)
KINDS: dict[str, str] = {
    "line": "Участки",
    "node": "Узлы",
    "consumer": "Потребители",
    "source": "Источники и насосные станции",
    "equipment": "Оборудование",
    "regime": "Режим узла (заданный напор, подпитка)",
}
ACTIONS: dict[str, str] = {
    "edit": "Свойства",
    "create": "Создание",
    "move": "Перемещение и изломы",
    "delete": "Удаление",
}
# Какие действия есть у вида (оборудование не перемещается — оно на линии; режим только правится)
KIND_ACTIONS: dict[str, tuple[str, ...]] = {
    "line": ("edit", "create", "move", "delete"),
    "node": ("edit", "create", "move", "delete"),
    "consumer": ("edit", "create", "move", "delete"),
    "source": ("edit", "create", "move", "delete"),
    "equipment": ("edit", "create", "delete"),
    "regime": ("edit",),
}
SCOPES = ("none", "own", "all")
SCOPE_LABELS = {"none": "нет", "own": "только свои", "all": "все"}

GENERAL: dict[str, str] = {
    "calc_run": "Запуск расчётов",
    "calc_save": "Сохранение и сравнение расчётов, направления пьезометра",
    "export": "Выгрузки и отчёты",
    "import": "Импорт сети",
    "journals": "Журналы: ремонты, ПТС, акты, ТУ, привязки",
    "refs": "Справочники и шаблоны карточек",
    "audit_view": "Просмотр журнала действий",
    "users_admin": "Управление пользователями",
}

# Роль → подпись, описание, уровень (уровень — для прежних проверок require_roles)
ROLE_LABELS: dict[str, str] = {
    "viewer": "Просмотр",
    "calculator": "Режимщик",
    "operator": "Оператор сети",
    "editor": "Редактор",
    "admin": "Администратор",
}
ROLE_DESCRIPTIONS: dict[str, str] = {
    "viewer": "Просмотр карты, журналов и результатов, выгрузки",
    "calculator": "Режимные параметры потребителей, источников, оборудования; расчёты с сохранением и сравнением",
    "operator": "Создание объектов сети; правка, перемещение и удаление только своих",
    "editor": "Правка свойств и геометрии всей сети, создание, удаление своих; расчёты, журналы, справочники",
    "admin": "Всё, включая удаление любых объектов, пользователей и журнал действий",
}

_ALL_KINDS = tuple(KINDS)


def _matrix(spec: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Полная матрица: всё, что не задано, — none."""
    out: dict[str, dict[str, str]] = {}
    for kind, actions in KIND_ACTIONS.items():
        out[kind] = {a: spec.get(kind, {}).get(a, "none") for a in actions}
    return out


def _fill(kinds: Iterable[str], **actions: str) -> dict[str, dict[str, str]]:
    return {k: {a: s for a, s in actions.items() if a in KIND_ACTIONS[k]} for k in kinds}


def _merge(*specs: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for spec in specs:
        for kind, actions in spec.items():
            out.setdefault(kind, {}).update(actions)
    return out


ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "viewer": {"matrix": _matrix({}), "general": {"export"}},
    "calculator": {
        "matrix": _matrix(_fill(("consumer", "source", "equipment", "regime"), edit="all")),
        "general": {"calc_run", "calc_save", "export"},
    },
    "operator": {
        "matrix": _matrix(_fill(_ALL_KINDS, edit="own", create="all", move="own", delete="own")),
        "general": {"export"},
    },
    "editor": {
        "matrix": _matrix(_fill(_ALL_KINDS, edit="all", create="all", move="all", delete="own")),
        "general": {"calc_run", "calc_save", "export", "import", "journals", "refs"},
    },
    "admin": {
        "matrix": _matrix(_fill(_ALL_KINDS, edit="all", create="all", move="all", delete="all")),
        "general": set(GENERAL),
    },
}

# AUTH_BACKEND=pg: предметные права роли PostgreSQL → матрица (как в десктопе)
_CAP_MATRIX: dict[str, dict[str, dict[str, str]]] = {
    "network": _fill(_ALL_KINDS, edit="all"),
    "network_struct": _fill(_ALL_KINDS, create="all", move="all", delete="all"),
}
_CAP_GENERAL: dict[str, set[str]] = {
    "network_struct": {"import"},
    "pts": {"journals"},
    "repairs": {"journals"},
    "acts": {"journals"},
    "corrosion": {"journals"},
    "geo": {"refs"},
}


@dataclass(frozen=True)
class Permissions:
    matrix: dict = field(hash=False, compare=False)
    general: frozenset = frozenset()

    def scope(self, kind: str, action: str) -> str:
        return self.matrix.get(kind, {}).get(action, "none")

    def can(self, kind: str, action: str) -> bool:
        return self.scope(kind, action) != "none"

    def has(self, general: str) -> bool:
        return general in self.general

    def any_network(self) -> bool:
        return any(s != "none" for actions in self.matrix.values() for s in actions.values())

    def to_dict(self) -> dict[str, Any]:
        return {"matrix": self.matrix, "general": sorted(self.general)}


def parse_overrides(raw: Any) -> dict[str, Any]:
    """users.permissions → {"matrix": {kind: {action: scope}}, "general": {key: bool}}; мусор отбрасывается."""
    if not raw:
        return {}
    try:
        data = json.loads(raw) if isinstance(raw, str) else dict(raw)
    except (TypeError, ValueError):
        return {}
    out: dict[str, Any] = {}
    matrix = {}
    for kind, actions in (data.get("matrix") or {}).items():
        if kind not in KIND_ACTIONS or not isinstance(actions, dict):
            continue
        clean = {a: s for a, s in actions.items() if a in KIND_ACTIONS[kind] and s in SCOPES}
        if kind in KIND_ACTIONS and "create" in clean and clean["create"] == "own":
            clean["create"] = "all"  # «создавать только свои» не бывает
        if clean:
            matrix[kind] = clean
    if matrix:
        out["matrix"] = matrix
    general = {k: bool(v) for k, v in (data.get("general") or {}).items() if k in GENERAL}
    if general:
        out["general"] = general
    return out


def overrides_json(overrides: dict[str, Any]) -> Optional[str]:
    clean = parse_overrides(overrides)
    return json.dumps(clean, ensure_ascii=False, sort_keys=True) if clean else None


def diff_from_role(role: str, matrix: dict, general: Iterable[str]) -> dict[str, Any]:
    """Полный набор прав из админки → отличия от шаблона роли (то, что хранится)."""
    preset = ROLE_PRESETS.get(role, ROLE_PRESETS["viewer"])
    out_m: dict[str, dict[str, str]] = {}
    for kind, actions in KIND_ACTIONS.items():
        for a in actions:
            want = (matrix.get(kind) or {}).get(a, preset["matrix"][kind][a])
            if want in SCOPES and want != preset["matrix"][kind][a]:
                out_m.setdefault(kind, {})[a] = want
    want_g = set(general) & set(GENERAL)
    out_g = {k: (k in want_g) for k in GENERAL if (k in want_g) != (k in preset["general"])}
    out: dict[str, Any] = {}
    if out_m:
        out["matrix"] = out_m
    if out_g:
        out["general"] = out_g
    return out


@lru_cache(maxsize=512)
def effective(role: str, overrides: str = "", caps: frozenset = frozenset(), pg: bool = False) -> Permissions:
    """Права = шаблон роли + отличия пользователя.

    pg — пользователь-роль PostgreSQL (AUTH_BACKEND=pg): сеть, как в десктопе, — только по предметным
    правам (network, network_struct), кроме администратора; общие права — по шаблону роли и правам.
    """
    preset = ROLE_PRESETS.get(role, ROLE_PRESETS["viewer"])
    base = preset if not pg or role == "admin" else ROLE_PRESETS["viewer"]
    matrix = {k: dict(v) for k, v in base["matrix"].items()}
    general = set(preset["general"])
    for cap in caps:
        for kind, actions in _CAP_MATRIX.get(cap, {}).items():
            matrix[kind].update(actions)
        general |= _CAP_GENERAL.get(cap, set())
    ov = parse_overrides(overrides)
    for kind, actions in (ov.get("matrix") or {}).items():
        matrix[kind].update(actions)
    for key, on in (ov.get("general") or {}).items():
        (general.add if on else general.discard)(key)
    return Permissions(matrix=matrix, general=frozenset(general))


def catalog() -> dict[str, Any]:
    """Описание модели прав для админки: виды, действия, охваты, общие права, шаблоны ролей."""
    return {
        "kinds": [{"kind": k, "label": v, "actions": list(KIND_ACTIONS[k])} for k, v in KINDS.items()],
        "actions": [{"action": k, "label": v} for k, v in ACTIONS.items()],
        "scopes": [{"scope": k, "label": v} for k, v in SCOPE_LABELS.items()],
        "general": [{"key": k, "label": v} for k, v in GENERAL.items()],
        "roles": [
            {"role": r, "label": ROLE_LABELS[r], "description": ROLE_DESCRIPTIONS[r],
             "permissions": effective(r).to_dict()}
            for r in ROLE_PRESETS
        ],
    }


# === Вид объекта по таблице (карточка, групповая правка) ===
TABLE_KIND: dict[str, str] = {
    "heatpipesections": "line",
    "linesobj": "line",
    "nodes": "node",
    "realconsumers": "consumer",
    "generalizedconsumers": "consumer",
    "heatsources": "source",
    "pumpstations": "source",
    "setpressnodes": "regime",
    "refillnodes": "regime",
    "dampers": "equipment",
    "regularmatures": "equipment",
    "reversevalves": "equipment",
    "pumps": "equipment",
    "pressregulators": "equipment",
    "consumptregulators": "equipment",
    "pressdropregulators": "equipment",
    "bypass": "equipment",
    "elevators": "equipment",
    "heatexchangers": "equipment",
    "diaphragms": "equipment",
    "systemradiators": "equipment",
    "airheaters": "equipment",
}
# Тип нового узла (database/node_types) → вид карточки, которая создаётся вместе с ним
NODE_TYPE_KIND: dict[str, str] = {"US": "node", "US2": "node", "PR": "consumer", "PO": "consumer",
                                  "IS": "source", "HS": "source"}


def table_kind(table: str) -> Optional[str]:
    return TABLE_KIND.get((table or "").lower())


class PermissionDenied(Exception):
    """403 с понятным текстом: какого права не хватает и на каких объектах."""

    def __init__(self, message: str, objects: Optional[list[str]] = None):
        self.message = message
        self.objects = objects or []
        super().__init__(message)

    def detail(self) -> dict[str, Any]:
        return {"code": "permission_denied", "message": self.message, "objects": self.objects}


def need_label(kind: str, action: str, scope: str = "all") -> str:
    tail = "все" if scope == "all" else "свои"
    return f"«{ACTIONS[action]}: {KINDS[kind].lower()} ({tail})»"


def ensure_can(perms: Permissions, kind: str, action: str) -> str:
    """Охват действия; none → PermissionDenied."""
    scope = perms.scope(kind, action)
    if scope == "none":
        raise PermissionDenied(f"Нет права {need_label(kind, action, 'own')}")
    return scope


async def ensure_targets(conn, perms: Permissions, username: str, kind: str, action: str,
                         targets: dict[str, Iterable[int]]) -> None:
    """Право на действие с конкретными объектами {таблица: [id]}: охват own — только созданные пользователем."""
    scope = ensure_can(perms, kind, action)
    if scope == "all":
        return
    from database.authorship import foreign_objects

    foreign = await foreign_objects(conn, username, targets)
    if foreign:
        shown = ", ".join(foreign[:10]) + ("…" if len(foreign) > 10 else "")
        raise PermissionDenied(
            f"Можно только со своими объектами, а это не ваши: {shown}. Нужно право {need_label(kind, action)}",
            foreign,
        )
