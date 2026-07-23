from typing import Any, Literal, Optional

import asyncpg


ElectricalObjectType = Literal[
    "source", "line", "receiver", "channel", "coupling", "support", "sleeve"
]


OBJECTS_CTE = """
    WITH electrical_objects AS (
        SELECT 'source'::text AS object_type, source.id,
               source.naimenovanie_istochnika_es::text AS name,
               source_type.znachenie::text AS type_name,
               source.vladeltsy_es_id AS owner_id, owner.naimenovanie::text AS owner_name,
               NULL::int AS parent_line_id, NULL::int AS source_id, NULL::int AS receiver_id,
               NULL::double precision AS voltage_kv,
               NULL::double precision AS capacity_kw,
               NULL::double precision AS length_m,
               source.data_vydachi_akta_razdela_es AS installed_on,
               source.primechanie::text AS note,
               CASE WHEN source.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(source.shape), 4326)) END AS longitude,
               CASE WHEN source.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(source.shape), 4326)) END AS latitude
          FROM istochnik_elektrosnabzheniya source
          LEFT JOIN tipy_istochnikov_elektricheskih_setey source_type ON source_type.id=source.typid
          LEFT JOIN vladeltsy_es owner ON owner.id=source.vladeltsy_es_id
        UNION ALL
        SELECT 'line', line.id,
               coalesce(nullif(line.naimenovanie_lep, ''), nullif(line.mestopolozhenie, '')),
               line_type.znachenie, line.vladelets_lep, owner.naimenovanie,
               NULL, line.naimenovanie_istochnika, line.naimenovanie_priemnika,
               line.napryazhenie__kv,
               NULL,
               coalesce(line.protyazhennost__linii_m, line.protyazhennost__m),
               line.data_vvoda_v_ekspluatatsiyu, line.primechanie,
               CASE WHEN line.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END,
               CASE WHEN line.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(line.shape), 4326)) END
          FROM liniya_elektroperedach line
          LEFT JOIN tipy_lep line_type ON line_type.id=line.tip_prokladki_lep
          LEFT JOIN vladeltsy_es owner ON owner.id=line.vladelets_lep
        UNION ALL
        SELECT 'receiver', receiver.id, receiver.naimenovanie_priemnika_es,
               receiver_type.znachenie, receiver.vladeltsy_es_id, owner.naimenovanie,
               receiver.naimenovanie_lep, NULL, NULL, NULL,
               receiver.maksimalno_dopustimaya_nagruzka_vneshnego_vvoda_rp__kvt, NULL,
               receiver.data_vydachi_akta_razdela_es, receiver.primechanie,
               CASE WHEN receiver.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(receiver.shape), 4326)) END,
               CASE WHEN receiver.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(receiver.shape), 4326)) END
          FROM priemnik_elektrosnabzheniya receiver
          LEFT JOIN tipy_priemnikov_elektricheskih_setey receiver_type ON receiver_type.id=receiver.typid
          LEFT JOIN vladeltsy_es owner ON owner.id=receiver.vladeltsy_es_id
        UNION ALL
        SELECT 'channel', channel.id,
               coalesce(nullif(channel.naimenovanie_lep2, ''), nullif(channel.nomer_kanala_es, '')),
               channel.tip__marka__harakteristika_, NULL, NULL, channel.naimenovanie_lep,
               NULL, NULL, NULL, NULL, channel.dlina_kanala, channel.data_ustanovki,
               channel.primechanie,
               CASE WHEN channel.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(channel.shape), 4326)) END,
               CASE WHEN channel.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(channel.shape), 4326)) END
          FROM kabelnyy_kanal_es channel
        UNION ALL
        SELECT 'coupling', coupling.id,
               coalesce(nullif(coupling.naimenovanie_lep2, ''), nullif(coupling.nomer_mufty_es, '')),
               coupling.tip__marka__harakteristika_, NULL, NULL, coupling.naimenovanie_lep,
               NULL, NULL, NULL, NULL, coupling.rasstoyanie_do_priemnika__m,
               coupling.data_ustanovki, coupling.primechanie,
               CASE WHEN coupling.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(coupling.shape), 4326)) END,
               CASE WHEN coupling.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(coupling.shape), 4326)) END
          FROM mufta coupling
        UNION ALL
        SELECT 'support', support.id,
               coalesce(nullif(support.naimenovanie_lep2, ''), nullif(support.nomer_opory_es, '')),
               support.tip__marka__harakteristika_, NULL, NULL, support.naimenovanie_lep,
               NULL, NULL, NULL, NULL, NULL, support.data_ustanovki, support.primechanie,
               CASE WHEN support.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(support.shape), 4326)) END,
               CASE WHEN support.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(support.shape), 4326)) END
          FROM opora_es support
        UNION ALL
        SELECT 'sleeve', sleeve.id,
               coalesce(nullif(sleeve.naimenovanie_lep2, ''), nullif(sleeve.nomer_gilzy_es, '')),
               sleeve.tip__marka__harakteristika_, NULL, NULL, sleeve.naimenovanie_lep,
               NULL, NULL, NULL, NULL, sleeve.dlina_gilzy, sleeve.data_ustanovki,
               sleeve.primechanie,
               CASE WHEN sleeve.shape IS NULL THEN NULL ELSE ST_X(ST_Transform(ST_PointOnSurface(sleeve.shape), 4326)) END,
               CASE WHEN sleeve.shape IS NULL THEN NULL ELSE ST_Y(ST_Transform(ST_PointOnSurface(sleeve.shape), 4326)) END
          FROM gilza_es sleeve
    )
"""


def _add_filter(
    clauses: list[str], values: list[Any], expression: str, value: Any, cast: str = ""
) -> None:
    values.append(value)
    clauses.append(expression.format(param=f"${len(values)}{cast}"))


def _build_filters(
    *,
    object_type: Optional[ElectricalObjectType],
    owner_id: Optional[int],
    parent_line_id: Optional[int],
    voltage_kv: Optional[float],
    search: Optional[str],
) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    values: list[Any] = []
    if object_type:
        _add_filter(clauses, values, "obj.object_type={param}", object_type, "::text")
    if owner_id is not None:
        _add_filter(clauses, values, "obj.owner_id={param}", owner_id)
    if parent_line_id is not None:
        _add_filter(
            clauses,
            values,
            "(obj.parent_line_id={param} OR (obj.object_type='line' AND obj.id={param}))",
            parent_line_id,
        )
    if voltage_kv is not None:
        _add_filter(clauses, values, "obj.voltage_kv={param}", voltage_kv)
    normalized_search = (search or "").strip()
    if normalized_search:
        _add_filter(
            clauses,
            values,
            """(
                obj.id::text={param}
                OR coalesce(obj.name, '') ILIKE '%' || {param} || '%'
                OR coalesce(obj.type_name, '') ILIKE '%' || {param} || '%'
                OR coalesce(obj.owner_name, '') ILIKE '%' || {param} || '%'
                OR coalesce(obj.note, '') ILIKE '%' || {param} || '%'
            )""",
            normalized_search,
            "::text",
        )
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", values


async def get_electrical_objects(
    conn: asyncpg.Connection,
    *,
    page: int,
    page_size: int,
    object_type: Optional[ElectricalObjectType] = None,
    owner_id: Optional[int] = None,
    parent_line_id: Optional[int] = None,
    voltage_kv: Optional[float] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    where_sql, values = _build_filters(
        object_type=object_type,
        owner_id=owner_id,
        parent_line_id=parent_line_id,
        voltage_kv=voltage_kv,
        search=search,
    )
    total = await conn.fetchval(
        OBJECTS_CTE + " SELECT count(*) FROM electrical_objects obj" + where_sql,
        *values,
    )
    rows = await conn.fetch(
        OBJECTS_CTE
        + " SELECT * FROM electrical_objects obj"
        + where_sql
        + f"""
          ORDER BY obj.object_type, obj.name NULLS LAST, obj.id
          LIMIT ${len(values) + 1} OFFSET ${len(values) + 2}
        """,
        *values,
        page_size,
        (page - 1) * page_size,
    )
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if total else 0,
    }


async def get_electrical_lookups(conn: asyncpg.Connection) -> dict[str, Any]:
    owners = await conn.fetch(
        "SELECT id, naimenovanie AS name FROM vladeltsy_es ORDER BY naimenovanie, id"
    )
    source_types = await conn.fetch(
        "SELECT id, znachenie AS name FROM tipy_istochnikov_elektricheskih_setey ORDER BY id"
    )
    receiver_types = await conn.fetch(
        "SELECT id, znachenie AS name FROM tipy_priemnikov_elektricheskih_setey ORDER BY id"
    )
    line_types = await conn.fetch(
        "SELECT id, znachenie AS name FROM tipy_lep ORDER BY id"
    )
    cable_marks = await conn.fetch(
        """SELECT id, kratkoe_naimenovanie_marki_tipa__kabelya AS short_name,
                  polnoe_naimenovanie_marki_tipa__kabelya AS name
             FROM marki_kabeley_es ORDER BY id"""
    )
    counts = await conn.fetchrow(
        OBJECTS_CTE
        + """ SELECT
            count(*)::int AS total,
            count(*) FILTER (WHERE object_type='source')::int AS sources,
            count(*) FILTER (WHERE object_type='line')::int AS lines,
            count(*) FILTER (WHERE object_type='receiver')::int AS receivers,
            count(*) FILTER (WHERE object_type='channel')::int AS channels,
            count(*) FILTER (WHERE object_type='coupling')::int AS couplings,
            count(*) FILTER (WHERE object_type='support')::int AS supports,
            count(*) FILTER (WHERE object_type='sleeve')::int AS sleeves
          FROM electrical_objects"""
    )
    voltages = await conn.fetch(
        """SELECT napryazhenie__kv AS value, count(*)::int AS count
             FROM liniya_elektroperedach WHERE napryazhenie__kv IS NOT NULL
            GROUP BY napryazhenie__kv ORDER BY napryazhenie__kv"""
    )
    return {
        "owners": [dict(row) for row in owners],
        "source_types": [dict(row) for row in source_types],
        "receiver_types": [dict(row) for row in receiver_types],
        "line_types": [dict(row) for row in line_types],
        "cable_marks": [dict(row) for row in cable_marks],
        "voltages": [dict(row) for row in voltages],
        "counts": dict(counts) if counts else {},
    }


DETAIL_QUERIES: dict[ElectricalObjectType, str] = {
    "source": """
        SELECT source.*, source_type.znachenie AS source_type_name,
               owner.naimenovanie AS owner_name
          FROM istochnik_elektrosnabzheniya source
          LEFT JOIN tipy_istochnikov_elektricheskih_setey source_type ON source_type.id=source.typid
          LEFT JOIN vladeltsy_es owner ON owner.id=source.vladeltsy_es_id
         WHERE source.id=$1
    """,
    "line": """
        SELECT line.*, source.naimenovanie_istochnika_es AS source_name,
               receiver.naimenovanie_priemnika_es AS receiver_name,
               line_type.znachenie AS installation_type_name,
               cable.polnoe_naimenovanie_marki_tipa__kabelya AS cable_mark_name,
               owner.naimenovanie AS owner_name
          FROM liniya_elektroperedach line
          LEFT JOIN istochnik_elektrosnabzheniya source ON source.id=line.naimenovanie_istochnika
          LEFT JOIN priemnik_elektrosnabzheniya receiver ON receiver.id=line.naimenovanie_priemnika
          LEFT JOIN tipy_lep line_type ON line_type.id=line.tip_prokladki_lep
          LEFT JOIN marki_kabeley_es cable ON cable.id=line.marka_kabelya_linii
          LEFT JOIN vladeltsy_es owner ON owner.id=line.vladelets_lep
         WHERE line.id=$1
    """,
    "receiver": """
        SELECT receiver.*, receiver_type.znachenie AS receiver_type_name,
               owner.naimenovanie AS owner_name
          FROM priemnik_elektrosnabzheniya receiver
          LEFT JOIN tipy_priemnikov_elektricheskih_setey receiver_type ON receiver_type.id=receiver.typid
          LEFT JOIN vladeltsy_es owner ON owner.id=receiver.vladeltsy_es_id
         WHERE receiver.id=$1
    """,
    "channel": "SELECT * FROM kabelnyy_kanal_es WHERE id=$1",
    "coupling": "SELECT * FROM mufta WHERE id=$1",
    "support": "SELECT * FROM opora_es WHERE id=$1",
    "sleeve": "SELECT * FROM gilza_es WHERE id=$1",
}


async def _get_documents(
    conn: asyncpg.Connection, table: str, object_id: int
) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        f"""SELECT document.id, document.date_doc, document.path,
                   document.remontdocumenttypeid AS document_type_id,
                   document_type.name AS document_type_name
              FROM {table} document
              LEFT JOIN remontdocumenttypes document_type
                ON document_type.id=document.remontdocumenttypeid
             WHERE document.objid=$1 ORDER BY document.date_doc DESC NULLS LAST, document.id""",
        object_id,
    )
    return [dict(row) for row in rows]


async def get_electrical_object(
    conn: asyncpg.Connection, object_type: ElectricalObjectType, object_id: int
) -> Optional[dict[str, Any]]:
    summary = await conn.fetchrow(
        OBJECTS_CTE
        + " SELECT * FROM electrical_objects obj WHERE obj.object_type=$1 AND obj.id=$2",
        object_type,
        object_id,
    )
    if summary is None:
        return None
    attributes = await conn.fetchrow(DETAIL_QUERIES[object_type], object_id)
    result = dict(summary)
    detail_values = dict(attributes) if attributes else {}
    detail_values.pop("shape", None)
    result["attributes"] = detail_values
    relations: dict[str, Any] = {}
    if object_type == "source":
        lines = await conn.fetch(
            """SELECT id, naimenovanie_lep AS name, napryazhenie__kv AS voltage_kv,
                      naimenovanie_priemnika AS receiver_id
                 FROM liniya_elektroperedach
                WHERE naimenovanie_istochnika=$1 ORDER BY naimenovanie_lep, id""",
            object_id,
        )
        relations["lines"] = [dict(row) for row in lines]
        relations["documents"] = await _get_documents(
            conn, "electrodocumentsist", object_id
        )
    elif object_type == "receiver":
        lines = await conn.fetch(
            """SELECT id, naimenovanie_lep AS name, napryazhenie__kv AS voltage_kv,
                      naimenovanie_istochnika AS source_id
                 FROM liniya_elektroperedach
                WHERE naimenovanie_priemnika=$1 ORDER BY naimenovanie_lep, id""",
            object_id,
        )
        relations["lines"] = [dict(row) for row in lines]
        for key, table in (
            ("transformers", "transf"),
            ("engines", "edv"),
            ("diesel_generators", "dgu"),
            ("lifting_equipment", "gruzob"),
        ):
            rows = await conn.fetch(f"SELECT * FROM {table} WHERE objid=$1 ORDER BY id", object_id)
            relations[key] = [dict(row) for row in rows]
        relations["documents"] = await _get_documents(
            conn, "electrodocumentspr", object_id
        )
    elif object_type == "line":
        child_rows = await conn.fetch(
            """
            SELECT 'channel'::text AS object_type, id, coalesce(naimenovanie_lep2, nomer_kanala_es) AS name FROM kabelnyy_kanal_es WHERE naimenovanie_lep=$1
            UNION ALL SELECT 'coupling', id, coalesce(naimenovanie_lep2, nomer_mufty_es) FROM mufta WHERE naimenovanie_lep=$1
            UNION ALL SELECT 'support', id, coalesce(naimenovanie_lep2, nomer_opory_es) FROM opora_es WHERE naimenovanie_lep=$1
            UNION ALL SELECT 'sleeve', id, coalesce(naimenovanie_lep2, nomer_gilzy_es) FROM gilza_es WHERE naimenovanie_lep=$1
            ORDER BY object_type, id
            """,
            object_id,
        )
        relations["children"] = [dict(row) for row in child_rows]
        relations["documents"] = await _get_documents(
            conn, "electrodocuments", object_id
        )
    elif object_type == "channel":
        relations["documents"] = await _get_documents(
            conn, "kabelnyy_kanal_esdocuments", object_id
        )
    result["relations"] = relations
    return result
