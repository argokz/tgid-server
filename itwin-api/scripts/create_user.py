"""Создать (или обновить) пользователя UsersDB из консоли — первый администратор.

Запуск из itwin-api/itwin-api (окружение как у API: .env и, для копии, .env.copy):

    set -a; . ./.env; . ./.env.copy; set +a
    ./venv/Scripts/python.exe scripts/create_user.py admin --role admin

Пароль берётся из переменной TGID_NEW_PASSWORD или запрашивается (getpass), в аргументах
командной строки не передаётся. Хэш — bcrypt, как у проверки входа (auth.hash_password).
Существующему пользователю меняются пароль, роль и is_active=true.
"""

import argparse
import asyncio
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from auth import ROLE_ORDER, hash_password  # noqa: E402
from database.connect import USERS_DB_CONFIG, async_session  # noqa: E402
from database.models import User  # noqa: E402


async def upsert(username: str, password: str, role: str) -> str:
    async with async_session() as session:
        row = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        action = "обновлён"
        if row is None:
            row = User(username=username)
            session.add(row)
            action = "создан"
        row.hashed_password = hash_password(password)
        row.role = role
        row.is_admin = role == "admin"
        row.is_active = True
        await session.commit()
        return action


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("username")
    parser.add_argument("--role", default="viewer", choices=sorted(ROLE_ORDER, key=ROLE_ORDER.get))
    args = parser.parse_args()

    password = os.getenv("TGID_NEW_PASSWORD") or getpass.getpass("Пароль: ")
    if len(password) < 8 or len(password.encode("utf-8")) > 72:
        sys.exit("Пароль: от 8 символов и не длиннее 72 байт (ограничение bcrypt)")
    target = f"{USERS_DB_CONFIG['host']}:{USERS_DB_CONFIG['port']}/{USERS_DB_CONFIG['database']}"
    action = asyncio.run(upsert(args.username, password, args.role))
    print(f"Пользователь {args.username} ({args.role}) {action} в {target}")


if __name__ == "__main__":
    main()
