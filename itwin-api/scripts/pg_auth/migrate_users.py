"""Перенос пользователей в роли PostgreSQL (sql/pg_auth, docs/pg-auth.md).

Источники (одинаковые логины объединяются в одного пользователя):
  - passwords — десктоп gid8/gid6: MD5, битовая маска user_right (gid8/gid8/any/rights.h);
  - UsersDB users — веб: bcrypt, роль viewer/calculator/editor/admin;
  - auth.users + auth.user_fragments — QGIS-плагин (gid8/python/qgis/new): sha256, фрагменты.

Пароли не переносятся (MD5/bcrypt в SCRAM не превратить): старые хеши кладутся в
tgid_auth.legacy_credentials, и при первом входе через веб пароль переносится в роль.
Стандартный пароль QGIS admin/admin не переносится — пароль такой учётке задаёт администратор.

Запуск (env из .env + .env.copy; по умолчанию — только план, без хешей):
    ./venv/Scripts/python.exe scripts/pg_auth/migrate_users.py            # план
    ./venv/Scripts/python.exe scripts/pg_auth/migrate_users.py --apply    # записать (копия)
На базе без маркера _this_is_copy нужен ещё --prod (прод переносит администратор БД).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

import asyncpg

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

BASE_ORDER = {"viewer": 1, "calculator": 2, "editor": 3, "admin": 4}
# Права веба до перехода: редактор правил журналы, оборудование (сеть), ПТС, коррозию и ремонты
WEB_EDITOR_CAPS = {"network", "pts", "corrosion", "repairs"}
DEFAULT_ADMIN_SHA256 = hashlib.sha256(b"admin").hexdigest()

# Биты user_right (gid8/gid8/any/rights.h: маска = 2 << R_x; инвертированы admin, akt, geo)
R_ADMIN, R_REGIM, R_AKT, R_GEO, R_NEUD = 2, 4, 8, 16, 32
R_PROIZ, R_INDIKATOR, R_WEB_READ, R_WEB_WRITE, R_REMONT = 64, 128, 256, 512, 1024
COMPARED_BITS = R_ADMIN | R_REGIM | R_AKT | R_GEO | R_NEUD | R_PROIZ | R_INDIKATOR | R_WEB_READ | R_REMONT


@dataclass
class Planned:
    login: str
    base: str = "viewer"
    caps: set[str] = field(default_factory=set)
    fragments: set[int] = field(default_factory=set)
    web_access: bool = False
    legacy: dict[str, str] = field(default_factory=dict)  # source → hash
    legacy_passwords_id: Optional[int] = None
    legacy_usersdb_id: Optional[int] = None
    legacy_auth_id: Optional[int] = None
    legacy_right: Optional[int] = None
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    block: bool = False

    @property
    def role(self) -> str:
        return "tgid_u_" + self.login.strip()  # как tgid_auth.role_for_login

    def raise_base(self, base: str) -> None:
        if BASE_ORDER[base] > BASE_ORDER[self.base]:
            self.base = base


def decode_right(mask: int) -> tuple[str, set[str], bool]:
    """user_right → (базовая роль, предметные права, доступ к вебу)."""
    is_admin = not mask & R_ADMIN
    if is_admin:
        base = "admin"
    elif mask & R_WEB_WRITE:
        base = "editor"
    elif mask & R_REGIM:
        base = "calculator"  # режимщик: расчёты в десктопе прав не требовали
    else:
        base = "viewer"
    caps: set[str] = set()
    if mask & R_REGIM:
        caps.add("network")
        if not mask & R_NEUD:
            caps.add("network_struct")
    if not mask & R_AKT:
        caps.add("acts")
    if not mask & R_GEO:
        caps.add("geo")
    if mask & R_PROIZ:
        caps.add("pts")
    if mask & R_INDIKATOR:
        caps.add("corrosion")
    if mask & R_REMONT:
        caps.add("repairs")
    if is_admin:
        caps = set()  # администратор и так имеет все права
    return base, caps, bool(mask & R_WEB_READ) or is_admin


def comparable(mask: int) -> int:
    """Биты, которые проверяет десктоп; «нельзя удалять» (32) имеет смысл только с правом сети (4).

    Администратор в новой модели имеет все права (в gid8 админ без бита 4 не мог править сеть) —
    у администраторов сверяется только сам признак администратора.
    """
    if not mask & R_ADMIN:
        return 0
    m = mask & COMPARED_BITS
    if not m & R_REGIM:
        m &= ~R_NEUD
    return m


async def _connect(database: str, *, users: bool = False) -> asyncpg.Connection:
    p = "USERS_DB_" if users else "DB_"
    return await asyncpg.connect(
        host=os.getenv(p + "HOST") or os.getenv("DB_HOST"), port=int(os.getenv(p + "PORT") or os.getenv("DB_PORT") or 5432),
        user=os.getenv(p + "USER") or os.getenv("DB_USER"), password=os.getenv(p + "PASSWORD") or os.getenv("DB_PASSWORD"),
        database=database,
    )


async def collect(conn: asyncpg.Connection) -> dict[str, Planned]:
    users: dict[str, Planned] = {}

    def get(login: str) -> Planned:
        key = login.strip().lower()
        if key not in users:
            users[key] = Planned(login=login.strip())
        return users[key]

    # 1) десктоп; один логин встречается в passwords несколько раз — берётся последняя запись
    if await conn.fetchval("SELECT to_regclass('public.passwords') IS NOT NULL"):
        rows = await conn.fetch("SELECT id, user_name, user_password, user_right FROM passwords ORDER BY id")
        latest: dict[str, asyncpg.Record] = {}
        dup_ids: dict[str, list[int]] = {}
        for r in rows:
            if not (r["user_name"] or "").strip():
                continue
            key = r["user_name"].strip().lower()
            dup_ids.setdefault(key, []).append(r["id"])
            latest[key] = r
        for key, r in latest.items():
            u = get(r["user_name"])
            if len(dup_ids[key]) > 1:
                u.notes.append(f"в passwords {len(dup_ids[key])} записи (id {', '.join(map(str, dup_ids[key]))}) — взята id {r['id']}")
            mask = int(r["user_right"] or 0)
            base, caps, web = decode_right(mask)
            u.raise_base(base)
            u.caps |= caps
            u.web_access = u.web_access or web
            u.legacy_passwords_id, u.legacy_right = r["id"], mask
            u.sources.append("passwords")
            if r["user_password"]:
                u.legacy["passwords"] = r["user_password"]
            else:
                # десктоп пускает такой логин без пароля — переносится заблокированным
                u.notes.append("пустой пароль в passwords — заблокирован, пароль задаёт администратор")
                u.block = True

    # 2) QGIS
    if await conn.fetchval("SELECT to_regclass('auth.users') IS NOT NULL"):
        frags: dict[int, set[int]] = {}
        if await conn.fetchval("SELECT to_regclass('auth.user_fragments') IS NOT NULL"):
            for r in await conn.fetch("SELECT user_id, fragment_id FROM auth.user_fragments "
                                      "WHERE coalesce(can_edit, true) AND fragment_id IS NOT NULL"):
                frags.setdefault(r["user_id"], set()).add(r["fragment_id"])
        for r in await conn.fetch("SELECT id, username, password_hash, is_admin FROM auth.users ORDER BY id"):
            u = get(r["username"])
            u.raise_base("admin" if r["is_admin"] else "viewer")
            u.fragments |= frags.get(r["id"], set())
            u.legacy_auth_id = r["id"]
            u.sources.append("auth")
            if (r["password_hash"] or "").lower() == DEFAULT_ADMIN_SHA256:
                u.notes.append("стандартный пароль QGIS admin — заблокирован, пароль задаёт администратор")
                u.block = True
            elif r["password_hash"]:
                u.legacy["auth"] = r["password_hash"]
    return users


async def collect_usersdb(users: dict[str, Planned]) -> None:
    name = os.getenv("USERS_DB_NAME")
    if not name:
        return
    try:
        conn = await _connect(name, users=True)
    except Exception as exc:  # noqa: BLE001
        print(f"UsersDB недоступна ({exc.__class__.__name__}) — пропущена")
        return
    try:
        rows = await conn.fetch("SELECT id, username, hashed_password, is_active, is_admin, role FROM users ORDER BY id")
    finally:
        await conn.close()
    for r in rows:
        key = r["username"].strip().lower()
        u = users.setdefault(key, Planned(login=r["username"].strip()))
        role = r["role"] if r["role"] in BASE_ORDER else ("admin" if r["is_admin"] else "viewer")
        u.raise_base(role)
        if role in ("editor", "admin"):
            u.caps |= WEB_EDITOR_CAPS if role == "editor" else set()
        u.web_access = True
        u.legacy_usersdb_id = r["id"]
        u.sources.append("usersdb")
        if not r["is_active"]:
            u.notes.append("заблокирован в UsersDB")
            u.block = True
        if r["hashed_password"]:
            u.legacy["usersdb"] = r["hashed_password"]


async def apply(conn: asyncpg.Connection, plan: list[Planned]) -> None:
    async with conn.transaction():
        for u in plan:
            exists = await conn.fetchval("SELECT 1 FROM tgid_auth.users WHERE role_name = $1", u.role)
            if exists:
                print(f"  {u.login}: уже перенесён — пропущен")
                continue
            caps = sorted(u.caps if u.base != "admin" else set())
            role = await conn.fetchval(
                "SELECT tgid_auth._create_user('migrate_users', $1, $2, $3::text[], $4::int[], NULL, NULL, $5)",
                u.login, u.base, caps, sorted(u.fragments), u.web_access)
            assert role == u.role, (role, u.role)
            await conn.execute(
                "UPDATE tgid_auth.users SET legacy_passwords_id = $2, legacy_usersdb_id = $3, legacy_auth_id = $4, "
                "legacy_right = $5 WHERE role_name = $1",
                u.role, u.legacy_passwords_id, u.legacy_usersdb_id, u.legacy_auth_id, u.legacy_right)
            for source, h in u.legacy.items():
                await conn.execute("INSERT INTO tgid_auth.legacy_credentials (role_name, source, hash) VALUES ($1, $2, $3)",
                                   u.role, source, h)
            if u.block:
                await conn.execute("SELECT tgid_auth._set_active('migrate_users', $1, false)", u.role)
        # Сверка маски для перенесённых из десктопа
        bad = []
        for u in plan:
            if u.legacy_right is None:
                continue
            await conn.execute(f'SET LOCAL ROLE "{u.role}"')
            got = await conn.fetchval("SELECT tgid_auth.legacy_right()")
            await conn.execute("RESET ROLE")
            if comparable(got) != comparable(u.legacy_right):
                bad.append((u.login, u.legacy_right, got))
        if bad:
            for login, want, got in bad:
                print(f"  ! {login}: user_right {want} → legacy_right() {got}")
            raise SystemExit("Маска прав не совпала — перенос отменён (транзакция откатится)")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="записать (иначе только план)")
    ap.add_argument("--prod", action="store_true", help="разрешить базу без маркера _this_is_copy")
    args = ap.parse_args()

    db = os.getenv("DB_NAME")
    conn = await _connect(db)
    try:
        is_copy = await conn.fetchval("SELECT to_regclass('public._this_is_copy') IS NOT NULL")
        if args.apply and not is_copy and not args.prod:
            print(f"{db}: нет маркера _this_is_copy — для прода нужен --prod")
            return 2
        if not await conn.fetchval("SELECT to_regnamespace('tgid_auth') IS NOT NULL"):
            print(f"{db}: нет схемы tgid_auth — сначала sql/pg_auth/01–04")
            return 2
        users = await collect(conn)
        await collect_usersdb(users)
        plan = sorted(users.values(), key=lambda u: u.login.lower())
        print(f"База {db}: пользователей к переносу {len(plan)}")
        print(f"{'логин':24} {'роль':10} {'права':40} {'фрагм.':8} {'веб':4} источники; заметки")
        for u in plan:
            caps = ",".join(sorted(u.caps)) if u.base != "admin" else "(все)"
            frags = ",".join(map(str, sorted(u.fragments))) or "все"
            note = ("; " + "; ".join(u.notes)) if u.notes else ""
            print(f"{u.login[:24]:24} {u.base:10} {caps[:40]:40} {frags[:8]:8} {'да' if u.web_access else 'нет':4} "
                  f"{'+'.join(u.sources)}{note}")
            if len(u.role.encode()) > 63:
                print(f"  ! {u.login}: имя роли длиннее 63 байт — перенос невозможен")
                return 2
        if not args.apply:
            print("\nПлан. Записать: --apply")
            return 0
        await apply(conn, plan)
        print(f"\nПеренесено. Пароли перенесутся при первом входе через веб (legacy_credentials).")
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
