"""Единое правило «объект во фрагменте» для выгрузок (SHP, DXF, GeoJSON, ведомости Excel).

Участок принадлежит фрагменту по ``linesobj.fileid`` — по самой линии, а не по узлу начала
(``nodes.fileid``): на копии Алматы у 2002 из 4018 живых участков фрагмента 74 узлы лежат
во фрагменте 99, и отбор по ``n1.fileid`` терял половину линий (QA F13). Живой участок —
``COALESCE(removed, 0) = 0``; геометрические выгрузки дополнительно требуют ``shape IS NOT NULL``.
"""

from __future__ import annotations

from typing import Optional

from fastapi import HTTPException

# $1 — int[] либо NULL (вся сеть); алиас таблицы linesobj — lo
LINE_IN_FRAGMENTS_SQL = "($1::int[] IS NULL OR lo.fileid = ANY($1::int[]))"
LIVE_LINE_SQL = "COALESCE(lo.removed, 0) = 0"


def parse_fragment_ids(fragment_id: Optional[int], fragments: Optional[str]) -> Optional[list[int]]:
    """fragment_id и/или fragments=1,2,3 -> отсортированный список fileid (None — вся сеть)."""
    ids: set[int] = set()
    if fragments:
        for part in fragments.split(","):
            part = part.strip()
            if not part:
                continue
            if not part.isdigit() or int(part) < 1:
                raise HTTPException(status_code=400, detail="fragments must be comma-separated positive integers")
            ids.add(int(part))
    if fragment_id is not None:
        ids.add(int(fragment_id))
    return sorted(ids) or None
