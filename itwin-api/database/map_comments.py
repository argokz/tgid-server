"""Комментарии на карте (фаза 2, п. 4 плана модернизации, по образцу Felt): ветка обсуждения в точке карты.

Ветка (tgid_map_thread) — точка, вид карты при создании, необязательная привязка к участку или узлу сети; сообщения
(tgid_map_comment) — с @упоминаниями (логины, mentions). Ветку можно отметить «решено» и открыть снова. Своё
сообщение автор правит и удаляет; удалённое остаётся строкой «удалено», если на него уже отвечали, а ветка из одного
сообщения удаляется целиком. Непрочитанное — по tgid_map_comment_seen: новые сообщения других в ветках, где
пользователь писал или где его упомянули. Таблицы — sql/migrations/20261030_map_comments.sql.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

MAX_BODY = 4000
MAX_LIST = 500
SNIPPET = 160
# @логин: буквы (и кириллица), цифры, точка, дефис, подчёркивание; перед @ — не буква (не почта)
_MENTION = re.compile(r"(?<![\w.])@([\w.\-]{2,100})", re.UNICODE)

Status = Literal["open", "resolved", "all"]
Scope = Literal["all", "mine"]


class CommentError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class ThreadIn(BaseModel):
    lon: float = Field(..., ge=-180, le=180)
    lat: float = Field(..., ge=-90, le=90)
    zoom: Optional[float] = Field(None, ge=0, le=24)
    object_kind: Optional[Literal["line", "node"]] = None
    object_id: Optional[int] = Field(None, ge=1)
    body: str = Field(..., min_length=1, max_length=MAX_BODY)


class CommentIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=MAX_BODY)


def mentions_in(body: str, known: Optional[set[str]] = None) -> list[str]:
    """Логины из @упоминаний по порядку, без повторов; known — только существующие (регистр как в справочнике)."""
    by_lower = {k.lower(): k for k in known} if known is not None else None
    out: list[str] = []
    for m in _MENTION.finditer(body):
        login = m.group(1).rstrip(".-")
        if by_lower is not None:
            login = by_lower.get(login.lower(), "")
        if login and login not in out:
            out.append(login)
    return out


def _iso(v: Any) -> Any:
    return v.isoformat() if isinstance(v, (datetime, date)) else v


def _clean(body: str) -> str:
    text = body.strip()
    if not text:
        raise CommentError(422, "Пустой комментарий")
    return text


# --- чтение ---------------------------------------------------------------------------------

_THREAD_SELECT = """
    SELECT t.*, first.body AS first_body, first.deleted_at AS first_deleted,
           (SELECT count(*) FROM tgid_map_comment c WHERE c.thread_id = t.id AND c.deleted_at IS NULL) AS comment_count,
           (SELECT max(c.created_at) FROM tgid_map_comment c
             WHERE c.thread_id = t.id AND c.author <> $1 AND c.deleted_at IS NULL
               AND c.created_at > COALESCE((SELECT s.seen_at FROM tgid_map_comment_seen s
                                             WHERE s.login = $1 AND s.thread_id = t.id), '-infinity')
               AND (EXISTS (SELECT 1 FROM tgid_map_comment mine WHERE mine.thread_id = t.id AND mine.author = $1)
                    OR EXISTS (SELECT 1 FROM tgid_map_comment m WHERE m.thread_id = t.id AND $1 = ANY(m.mentions))))
               AS unread_since,
           EXISTS (SELECT 1 FROM tgid_map_comment m WHERE m.thread_id = t.id AND $1 = ANY(m.mentions)) AS mentions_me
      FROM tgid_map_thread t
      LEFT JOIN LATERAL (SELECT c.body, c.deleted_at FROM tgid_map_comment c WHERE c.thread_id = t.id
                          ORDER BY c.created_at, c.id LIMIT 1) first ON TRUE
"""


def _thread_row(r) -> dict[str, Any]:
    out = {k: _iso(v) for k, v in dict(r).items() if k not in ("first_body", "first_deleted", "unread_since")}
    body = "" if r["first_deleted"] else (r["first_body"] or "")
    out["snippet"] = body[:SNIPPET] + ("…" if len(body) > SNIPPET else "")
    out["unread"] = r["unread_since"] is not None
    out["resolved"] = r["resolved_at"] is not None
    return out


async def list_threads(conn, user: str, *, status: Status = "open", scope: Scope = "all",
                       q: Optional[str] = None, limit: int = MAX_LIST) -> dict[str, Any]:
    where, args = [], [user]
    if status == "open":
        where.append("t.resolved_at IS NULL")
    elif status == "resolved":
        where.append("t.resolved_at IS NOT NULL")
    if scope == "mine":
        where.append("(EXISTS (SELECT 1 FROM tgid_map_comment c WHERE c.thread_id = t.id AND c.author = $1)"
                     " OR EXISTS (SELECT 1 FROM tgid_map_comment c WHERE c.thread_id = t.id AND $1 = ANY(c.mentions)))")
    if q and q.strip():
        args.append(q.strip()[:100])
        where.append(f"EXISTS (SELECT 1 FROM tgid_map_comment c WHERE c.thread_id = t.id AND c.deleted_at IS NULL"
                     f" AND c.body ILIKE '%' || ${len(args)} || '%')")
    args.append(min(max(limit, 1), MAX_LIST))
    sql_where = f"WHERE {' AND '.join(where)}" if where else ""
    rows = await conn.fetch(f"{_THREAD_SELECT} {sql_where} ORDER BY t.last_at DESC LIMIT ${len(args)}", *args)
    counts = await conn.fetchrow(
        "SELECT count(*) FILTER (WHERE resolved_at IS NULL) AS open, count(*) FILTER (WHERE resolved_at IS NOT NULL)"
        " AS resolved FROM tgid_map_thread")
    return {"items": [_thread_row(r) for r in rows], "counts": dict(counts), "unread": await unread_count(conn, user)}


async def unread_count(conn, user: str) -> int:
    """Открытые ветки с новыми сообщениями других — где пользователь писал или где его упомянули."""
    return int(await conn.fetchval(
        """SELECT count(*) FROM tgid_map_thread t
            WHERE t.resolved_at IS NULL
              AND (EXISTS (SELECT 1 FROM tgid_map_comment c WHERE c.thread_id = t.id AND c.author = $1)
                   OR EXISTS (SELECT 1 FROM tgid_map_comment c WHERE c.thread_id = t.id AND $1 = ANY(c.mentions)))
              AND EXISTS (SELECT 1 FROM tgid_map_comment c
                           WHERE c.thread_id = t.id AND c.author <> $1 AND c.deleted_at IS NULL
                             AND c.created_at > COALESCE((SELECT s.seen_at FROM tgid_map_comment_seen s
                                                          WHERE s.login = $1 AND s.thread_id = t.id), '-infinity'))""",
        user) or 0)


async def geojson(conn, user: str, *, status: Status = "open") -> dict[str, Any]:
    data = await list_threads(conn, user, status=status)
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature", "id": t["id"],
        "geometry": {"type": "Point", "coordinates": [t["lon"], t["lat"]]},
        "properties": {"id": t["id"], "count": t["comment_count"], "resolved": t["resolved"], "unread": t["unread"],
                       "snippet": t["snippet"], "created_by": t["created_by"]},
    } for t in data["items"]]}


async def get_thread(conn, thread_id: int, user: str, *, mark_seen: bool = True) -> dict[str, Any]:
    row = await conn.fetchrow(f"{_THREAD_SELECT} WHERE t.id = $2", user, thread_id)
    if row is None:
        raise CommentError(404, f"Комментария {thread_id} нет — его удалили")
    out = _thread_row(row)
    comments = await conn.fetch(
        "SELECT id, body, mentions, author, created_at, edited_at, deleted_at FROM tgid_map_comment"
        " WHERE thread_id = $1 ORDER BY created_at, id", thread_id)
    out["comments"] = [{
        **{k: _iso(v) for k, v in dict(c).items()},
        "body": "" if c["deleted_at"] else c["body"],
        "mentions": [] if c["deleted_at"] else list(c["mentions"] or []),
        "deleted": c["deleted_at"] is not None,
    } for c in comments]
    if mark_seen:
        await conn.execute(
            """INSERT INTO tgid_map_comment_seen (login, thread_id, seen_at) VALUES ($1, $2, now())
               ON CONFLICT (login, thread_id) DO UPDATE SET seen_at = now()""", user, thread_id)
        out["unread"] = False
    return out


# --- запись ---------------------------------------------------------------------------------

async def create_thread(conn, body: ThreadIn, user: str, known: Optional[set[str]] = None) -> dict[str, Any]:
    text = _clean(body.body)
    if (body.object_kind is None) != (body.object_id is None):
        raise CommentError(422, "Объект сети — вид и номер вместе")
    async with conn.transaction():
        thread_id = await conn.fetchval(
            """INSERT INTO tgid_map_thread (lon, lat, zoom, object_kind, object_id, created_by)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            body.lon, body.lat, body.zoom, body.object_kind, body.object_id, user)
        await _insert_comment(conn, thread_id, text, user, known)
    return await get_thread(conn, thread_id, user)


async def _insert_comment(conn, thread_id: int, text: str, user: str, known: Optional[set[str]]) -> None:
    await conn.execute(
        "INSERT INTO tgid_map_comment (thread_id, body, mentions, author) VALUES ($1, $2, $3::text[], $4)",
        thread_id, text, mentions_in(text, known), user)
    await conn.execute("UPDATE tgid_map_thread SET last_at = now() WHERE id = $1", thread_id)


async def reply(conn, thread_id: int, body: CommentIn, user: str, known: Optional[set[str]] = None) -> dict[str, Any]:
    text = _clean(body.body)
    resolved = await conn.fetchval("SELECT resolved_at IS NOT NULL FROM tgid_map_thread WHERE id = $1", thread_id)
    if resolved is None:
        raise CommentError(404, f"Комментария {thread_id} нет — его удалили")
    async with conn.transaction():
        await _insert_comment(conn, thread_id, text, user, known)
        if resolved:
            # ответ в решённой ветке открывает её снова: обсуждение продолжилось
            await conn.execute("UPDATE tgid_map_thread SET resolved_at = NULL, resolved_by = NULL WHERE id = $1",
                               thread_id)
    return await get_thread(conn, thread_id, user)


async def _own_comment(conn, comment_id: int, user: str, is_admin: bool) -> dict[str, Any]:
    row = await conn.fetchrow(
        "SELECT id, thread_id, author, deleted_at FROM tgid_map_comment WHERE id = $1", comment_id)
    if row is None or row["deleted_at"] is not None:
        raise CommentError(404, f"Сообщения {comment_id} нет")
    if row["author"] != user and not is_admin:
        raise CommentError(403, "Править и удалять можно только свои сообщения")
    return dict(row)


async def edit_comment(conn, comment_id: int, body: CommentIn, user: str, *, is_admin: bool = False,
                       known: Optional[set[str]] = None) -> dict[str, Any]:
    row = await _own_comment(conn, comment_id, user, is_admin)
    text = _clean(body.body)
    await conn.execute(
        "UPDATE tgid_map_comment SET body = $2, mentions = $3::text[], edited_at = now() WHERE id = $1",
        comment_id, text, mentions_in(text, known))
    return await get_thread(conn, row["thread_id"], user)


async def delete_comment(conn, comment_id: int, user: str, *, is_admin: bool = False) -> Optional[dict[str, Any]]:
    """Удалить сообщение; последнее живое сообщение ветки — удалить ветку (ответ None)."""
    row = await _own_comment(conn, comment_id, user, is_admin)
    async with conn.transaction():
        alive = await conn.fetchval(
            "SELECT count(*) FROM tgid_map_comment WHERE thread_id = $1 AND deleted_at IS NULL", row["thread_id"])
        if alive <= 1:
            await conn.execute("DELETE FROM tgid_map_thread WHERE id = $1", row["thread_id"])
            return None
        await conn.execute("UPDATE tgid_map_comment SET deleted_at = now() WHERE id = $1", comment_id)
    return await get_thread(conn, row["thread_id"], user)


async def set_resolved(conn, thread_id: int, user: str, resolved: bool) -> dict[str, Any]:
    status = await conn.execute(
        f"""UPDATE tgid_map_thread SET resolved_at = {'now()' if resolved else 'NULL'},
                   resolved_by = {'$2' if resolved else 'NULL'}
             WHERE id = $1""", *((thread_id, user) if resolved else (thread_id,)))
    if not str(status).endswith(" 1"):
        raise CommentError(404, f"Комментария {thread_id} нет — его удалили")
    return await get_thread(conn, thread_id, user)
