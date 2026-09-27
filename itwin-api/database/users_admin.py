"""Администрирование пользователей UsersDB (аналог «Администратора» gid6).

Роли веба (auth.ROLE_ORDER) против прав десктопа: viewer — просмотр, calculator —
расчёты («режимщик» gid6), editor — правка журналов и атрибутов, admin — всё,
включая топологию и управление пользователями. Блокировка — users.is_active=false.
Пароли — только bcrypt (auth.hash_password), в ответы и журналы не попадают.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import func, select

from auth import ROLE_ORDER, hash_password, resolve_user_role
from database.connect import async_session
from database.models import User

ROLE_DESCRIPTIONS: dict[str, str] = {
    "viewer": "Просмотр карты, журналов и результатов",
    "calculator": "Просмотр + запуск расчётов (режимщик)",
    "editor": "Расчёты + правка журналов и атрибутов",
    "admin": "Всё, включая топологию и управление пользователями",
}


class UserAdminError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def user_to_dict(row: User) -> dict[str, Any]:
    return {
        "id": row.id,
        "username": row.username,
        "role": resolve_user_role(row.role, row.is_admin),
        "is_active": bool(row.is_active),
        "is_admin": bool(row.is_admin),
    }


def roles_catalog() -> list[dict[str, Any]]:
    return [
        {"role": role, "level": level, "description": ROLE_DESCRIPTIONS.get(role, "")}
        for role, level in sorted(ROLE_ORDER.items(), key=lambda item: item[1])
    ]


async def list_users() -> list[dict[str, Any]]:
    async with async_session() as session:
        rows = (await session.execute(select(User).order_by(User.username))).scalars().all()
        return [user_to_dict(r) for r in rows]


async def _other_active_admins(session, exclude_id: int) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.id != exclude_id,
        User.is_active.is_(True),
        (User.role == "admin") | (User.is_admin.is_(True)),
    )
    return int((await session.execute(stmt)).scalar_one())


async def create_user(username: str, password: str, role: str) -> dict[str, Any]:
    if role not in ROLE_ORDER:
        raise UserAdminError(422, f"Неизвестная роль: {role}")
    async with async_session() as session:
        exists = (
            await session.execute(select(User.id).where(func.lower(User.username) == username.lower()))
        ).scalar_one_or_none()
        if exists is not None:
            raise UserAdminError(409, f"Пользователь «{username}» уже существует")
        row = User(
            username=username,
            hashed_password=hash_password(password),
            is_active=True,
            is_admin=role == "admin",
            role=role,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return user_to_dict(row)


async def update_user(
    user_id: int,
    *,
    actor_id: Optional[str],
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Смена роли и/или блокировка. Возвращает (было, стало).

    Нельзя понизить или заблокировать себя и последнего активного администратора —
    иначе управлять пользователями станет некому.
    """
    if role is not None and role not in ROLE_ORDER:
        raise UserAdminError(422, f"Неизвестная роль: {role}")
    async with async_session() as session:
        row = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if row is None:
            raise UserAdminError(404, "Пользователь не найден")
        before = user_to_dict(row)
        new_role = role if role is not None else before["role"]
        new_active = is_active if is_active is not None else before["is_active"]
        loses_admin = before["role"] == "admin" and before["is_active"] and (
            new_role != "admin" or not new_active
        )
        if loses_admin:
            if actor_id is not None and str(user_id) == str(actor_id):
                raise UserAdminError(409, "Нельзя снять с себя роль admin или заблокировать себя")
            if await _other_active_admins(session, user_id) == 0:
                raise UserAdminError(409, "Это последний активный администратор")
        row.role = new_role
        row.is_admin = new_role == "admin"
        row.is_active = new_active
        await session.commit()
        await session.refresh(row)
        return before, user_to_dict(row)


async def set_password(user_id: int, password: str) -> dict[str, Any]:
    async with async_session() as session:
        row = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if row is None:
            raise UserAdminError(404, "Пользователь не найден")
        row.hashed_password = hash_password(password)
        await session.commit()
        return user_to_dict(row)
