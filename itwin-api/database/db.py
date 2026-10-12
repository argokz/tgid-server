import json
import re
from typing import Optional, Dict, List, Tuple
from database.connect import acquire_conn, query_log
from database.sql_ident import (
    UnknownIdentifierError,
    quote_ident,
    resolve_column,
    resolve_columns,
    resolve_table,
)
from utils.ini import list_tab_tables, parse_filtr, storage
from database.typed_edit import _KINDS, FieldSpec, coerce_value
import logging

logger = logging.getLogger(__name__)


def card_tables() -> frozenset:
    """Allow-list карточек /line и /node: таблицы с описанием tab/*.txt и таблицы CRUD."""
    from auth import MUTABLE_TABLES

    return list_tab_tables() | frozenset(t.lower() for t in MUTABLE_TABLES)


def mutable_tables() -> frozenset:
    from auth import MUTABLE_TABLES

    return frozenset(t.lower() for t in MUTABLE_TABLES)


def _sql_table(name: str) -> str:
    """Имя таблицы для FROM: как у прежнего некавыченного имени (PostgreSQL приводит к lower)."""
    return quote_ident(name.lower())

async def br_text(text: str) -> str:
    return f'"{text}"'



async def get_xml_path(povrezhdennyiElementForDefect: str, povrezhdennyiElement: str, name: str, defect: str, prefix: str) -> str:
    s = f'''\'{name}\' =
        STUFF(
        ( SELECT concat(\', \', rtt2.name) AS n FROM {defect} r2 
        LEFT JOIN {povrezhdennyiElementForDefect} rt2 ON r2.id=rt2.objID
        LEFT JOIN {povrezhdennyiElement} rtt2 ON rtt2.id=rt2.activityID
        WHERE r2.id={prefix}.id 
        FOR XML PATH(\'\')
        , TYPE
        ).value(\'.\', \'NVARCHAR(MAX)\'), 1, 1, \'\')
        '''
    return s

async def get_obj_line(defect: str, prefix: str, prefix_l: str) -> str:
    s = f'''
    LEFT JOIN (
        select l_id, obj_id FROM (
            select
                    l.id as l_id,
                    d.id as obj_id,
                    l.nodeID1,
                    l.shape.STDistance(d.shape) as length,
                    MIN(l.shape.STDistance(d.shape)) OVER(PARTITION BY d.id ) AS min_len
            from {defect} d
            join (
                SELECT l.id,  l.nodeID1, l.shape
                FROM linesobj l
                WHERE l.removed=0
            ) l ON ( l.shape.STDistance(d.shape) < 0.1 )
        ) k
        JOIN nodes n ON k.nodeID1=n.id
        WHERE k.min_len = k.length AND n.internalNodeID IS NULL
    ) l_obj ON l_obj.obj_id={prefix}.id
    LEFT JOIN linesobj {prefix_l} ON {prefix_l}.id=l_obj.l_id
    '''
    return s

async def get_3_param(tn: str, prefix: str, i: int, par1: str, par2: str, joins: str, filtr: Optional[List[str]]) -> Tuple[int, str, str, str]:
    async with acquire_conn() as conn:
        logger.debug(f"Fetching columns for table {tn}")
        rows = await query_log(conn, f'SELECT * FROM {_sql_table(tn)} LIMIT 1')
        columns = list(rows[0].keys()) if rows else []
        logger.debug(f"Columns fetched for {tn}: {columns[:5]}...")

        if filtr is None:
            logger.debug(f"No filter provided, reading tab2 for {tn}")
            filtr = await storage.read_tab2(tn)

        if filtr is None:
            logger.debug(f"No tab2 data, using columns from query")
            filtr = columns

        filtr = [c.lower() for c in filtr]
        filtr = [c for c in filtr if c in columns or c[0:1] == '$']
        logger.debug(f"Filtered columns: {filtr[:5]}...")

        for c in filtr:
            if c == 'shape': continue
            if c == 'id': continue

            if c[0:1] == '$':
                v = parse_filtr(c)
                if v:
                    tab1, tab2, title = v
                    if par1 != '': par1 += ',\n'
                    par1 += await get_xml_path(tab1, tab2, title, tn, prefix)
            else:
                l = storage.get_lookup(tn, c)
                (tnr, fnr, txt, f1) = storage.get_help(tn, c)
                txt = fnr
                tn_txt = f'{txt}||{prefix}' if prefix != 'T' else txt

                if par1 != '': par1 += ',\n'
                if l:
                    (tn1, fn1, tn2, id2, fn2, srt) = l
                    l2 = storage.get_lookup2(tn2)
                    if l2:
                        par1 += f'CASE {prefix}.{fn1}\n'
                        for n, t in l2.items():
                            par1 += f'    WHEN {n} THEN \'{t}\'\n'
                        par1 += f'END AS "{tn_txt}"'
                        par2 += f',\n{prefix}.{c}'
                        par2 += f' AS "{tn_txt}||"'
                    else:
                        par1 += f'{prefix}_{i}.{fn2}'
                        par1 += f' AS "{tn_txt}"'
                        joins += f'LEFT JOIN {tn2} {prefix}_{i} ON {prefix}_{i}.{id2} = {prefix}.{c}\n'
                        par2 += f',\n{prefix}.{c}'
                        par2 += f' AS "{tn_txt}||"'
                    i += 1
                else:
                    par1 += f'{prefix}.{c}'
                    par1 += f' AS "{tn_txt}"'
                i += 1

        return (i, par1, par2, joins)

async def create_select_line(tn: str, id: int) -> str:
    logger.info(f"Creating select for line: table={tn!r}, id={id}")
    async with acquire_conn() as conn:
        # Имя таблицы — из URL: allow-list карточек + сверка с каталогом (UnknownIdentifierError)
        actual = await resolve_table(conn, tn, card_tables())
        (i, par1, par2, joins) = (1, '', '', '')
        joins += 'LEFT JOIN linesobj L ON T.lineID=L.id\n'
        (i, par1, par2, joins) = await get_3_param("linesobj", "L", i, par1, par2, joins, ['externalSignLineID','organizationID','hydroRes','archiveChangeDateoperatorID'])
        joins += 'LEFT JOIN nodes N1 ON N1.id=L.nodeID1\n'
        (i, par1, par2, joins) = await get_3_param("nodes", "N1", i, par1, par2, joins, ['externalCodeID','externalNodeName'])
        joins += 'LEFT JOIN nodes N2 ON N2.id=L.nodeID2\n'
        (i, par1, par2, joins) = await get_3_param("nodes", "N2", i, par1, par2, joins, ['externalCodeID','externalNodeName'])
        
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(actual, "T", i, par1, par2, joins, filtr)

        q = f'SELECT \nT.id,L.id as L_id,N1.id AS N1_id,N2.id AS N2_id,\n{par1}{par2}\nFROM {quote_ident(actual)} T\n{joins}\nWHERE L.id=$1'
        logger.debug(f"Generated query: {q[:100]}...")
        return await print_q(conn, 'L', tn, q, id, filtr)

# Поля узла в карточке точечного объекта (десктоп: property/PropertyDial.cpp, _init_table): блок «Узел»
# перед полями объекта и, кроме узлов и узлов с заданным напором, блоки в конце первой вкладки
NODE_HEAD_FIELDS = ['externalCodeID', 'externalNodeName', 'externalSignID', 'geoMarkTopTube', 'geoMarkNodeArea']
NODE_TAIL_SUBSECTIONS = [
    ('Производственная служба', ['nodeTypeID', 'organizationID', 'inventNumber', 'registNumber']),
    ('Даты эксплуатации', ['PICdate', 'lastRepairDate']),
    ('Архив', ['archiveChangeDate', 'operatorID']),
]
NO_NODE_TAIL = frozenset({'nodes', 'setpressnodes'})

_SCHEME_RE = re.compile(r'^(C?)([0-9]+)\.([0-9]+)$')
_GVS_BY_N1 = {5: 'ps', 4: 'sm', 3: 'pr', 15: 'pw', 6: 'op', 7: 'oo'}


def read_cxema(scheme: str) -> Optional[Dict[str, str]]:
    """Признаки схемы подключения потребителя по номеру (десктоп: property/potr_fun.cpp, readCxema).

    Ключи — как в realConsumers.vis: elev, otop (z/n), gvs (ps/sm/pr/pw/op/oo), gvs_all, vent, rez.
    Пустая строка — признак не задан (правило видимости тогда берёт значение «1», как десктоп).
    """
    if scheme == '':
        return None
    r = {'elev': '0', 'otop': '', 'gvs': '', 'gvs_all': '', 'vent': '', 'rez': ''}
    m = _SCHEME_RE.match(scheme)
    if not m:
        return r
    c1, n1, n2 = m.group(1), int(m.group(2)), int(m.group(3))
    if scheme == '2.1':  # только вентиляция
        r['vent'] = '1'
        return r
    el = False
    if n2 in (5, 6, 7, 8) or scheme in ('1.3', '1.4'):
        r['otop'], el = 'z', True        # зависимая элеваторная
    elif n2 in (1, 2, 3, 4):
        r['otop'] = 'z'                  # зависимая
    if n2 in (9, 10, 11, 12) or scheme in ('1.5', '1.6'):
        r['otop'], el = 'n', False       # независимая
    if c1:
        r['otop'] = ''
    r['elev'] = '1' if el else '0'
    r['gvs'] = _GVS_BY_N1.get(n1, '')
    if r['gvs']:
        r['gvs_all'] = '1'
    vent = (n1 > 2 and n2 in (3, 4, 7, 8, 11, 12)) or (n1 == 1 and n2 in (2, 4, 6)) or (n1 == 2 and n2 == 1)
    r['vent'] = '1' if vent else '0'
    r['rez'] = '1' if n1 > 2 and n2 % 2 == 0 and r['gvs'] in ('op', 'oo') else '0'
    return r


def _vis_text(value) -> str:
    """Значение поля строкой, как QVariant::toString десктопа (1.0 → «1», NULL → «»)."""
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _apply_vis(rules: Dict[str, Dict[str, List[str]]], key: str, value: str, shown: Dict[str, bool]) -> None:
    """init_map_b десктопа: поля ключа скрыть, поля ветки значения (пусто → «1») показать."""
    branches = rules.get(key.lower())
    if not branches:
        return
    for cols in branches.values():
        for c in cols:
            shown[c] = False
    for c in branches.get((value or '1').lower(), []):
        shown[c] = True


def hidden_fields(tn: str, rules: Dict[str, Dict[str, List[str]]], row: Dict[str, object]) -> set:
    """Поля карточки, которые десктоп скрывает (setPR для потребителя, затем setVisAll).

    ``row`` — значения полей объекта (lower-колонка → значение; у справочных полей — код).
    """
    if not rules:
        return set()
    hidden: Dict[str, bool] = {}
    if tn.lower() == 'realconsumers':
        cx = read_cxema(_vis_text(row.get('schemenum')))
        if cx:
            for key in ('elev', 'otop', 'gvs', 'gvs_all', 'vent', 'rez'):
                shown: Dict[str, bool] = {}
                _apply_vis(rules, key, cx[key], shown)
                hidden.update({c: not on for c, on in shown.items()})
    shown = {}
    for key in rules:
        if key in row:
            _apply_vis(rules, key, _vis_text(row[key]), shown)
    hidden.update({c: not on for c, on in shown.items()})
    return {c for c, h in hidden.items() if h}


async def create_select_node(tn: str, id: int) -> str:
    logger.info(f"Creating select for node: table={tn!r}, id={id}")
    if tn == 'nodes':
        result = await create_select(tn, id)
        return result
    async with acquire_conn() as conn:
        actual = await resolve_table(conn, tn, card_tables())
        (i, par1, par2, joins) = (1, '', '', '')
        joins += 'LEFT JOIN nodes N ON N.id=T.nodeID\n'
        node_fields = NODE_HEAD_FIELDS + [c for _, cols in NODE_TAIL_SUBSECTIONS for c in cols]
        (i, par1, par2, joins) = await get_3_param("nodes", "N", i, par1, par2, joins, node_fields)
        
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(actual, "T", i, par1, par2, joins, filtr)

        q = f'SELECT \nT.id,N.id as N_id,\n{par1}{par2}\nFROM {quote_ident(actual)} T\n{joins}\nWHERE N.id=$1'
        logger.debug(f"Generated query: {q[:100]}...")
        return await print_q(conn, 'N', tn, q, id, filtr)

async def create_select_geoline(tn: str) -> str:
    logger.info(f"Creating select for geoline: table={tn!r}")
    async with acquire_conn() as conn:
        tn = await resolve_table(conn, tn, card_tables())
        (i, par1, par2, joins) = (1, '', '', '')
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(tn, "T", i, par1, par2, joins, filtr)
        joins += await get_obj_line(tn, 'T', 'L')
        (i, par1, par2, joins) = await get_3_param('linesobj', "L", i, par1, par2, joins, '')
        joins += 'LEFT JOIN heatPipeSections HPS ON HPS.lineID=L.id\n'
        (i, par1, par2, joins) = await get_3_param('heatPipeSections', "HPS", i, par1, par2, joins, '')
        joins += 'LEFT JOIN pipeSections PSS ON PSS.id=HPS.pipeSectionID\n'
        (i, par1, par2, joins) = await get_3_param('pipeSections', "PSS", i, par1, par2, joins, None)
        joins += 'LEFT JOIN nodes N1 ON N1.id=PSS.nodeID1\n'
        (i, par1, par2, joins) = await get_3_param('nodes', "N1", i, par1, par2, joins, ['externalCodeID','externalNodeName','nodeName'])
        joins += 'LEFT JOIN nodes N2 ON N2.id=PSS.nodeID2\n'
        (i, par1, par2, joins) = await get_3_param('nodes', "N2", i, par1, par2, joins, ['externalCodeID','externalNodeName','nodeName'])

        q = f'SELECT TOP 10\nT.id,\n{par1}{par2}\nFROM {quote_ident(tn)} T\n{joins}'
        logger.debug(f"Generated query: {q[:100]}...")
        return q

async def create_select(tn: str, id: int) -> str:
    logger.info(f"Creating select: table={tn!r}, id={id}")
    async with acquire_conn() as conn:
        actual = await resolve_table(conn, tn, card_tables())
        (i, par1, par2, joins) = (1, '', '', '')
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(actual, "T", i, par1, par2, joins, filtr)

        q = f'SELECT\nT.id,\n{par1}{par2}\nFROM {quote_ident(actual)} T\n{joins}\nWHERE T.id=$1'
        logger.debug(f"Generated query: {q[:100]}...")
        return await print_q(conn, '?', tn, q, id, filtr)

async def print_q(conn, typ: str, tn: str, q: str, id: int, cols: Optional[List[str]] = None) -> str:
    logger.debug(f"Executing query for {tn} with id={id}")
    rows = await query_log(conn, q, id)
    
    if not rows:
        logger.debug(f"No rows returned for query: {q[:100]}...")
        return json.dumps({"tabs": []}, ensure_ascii=False, indent=4, default=str)

    columns = list(rows[0].keys())
    if cols is None:
        logger.debug(f"No columns provided, reading tab2 for {tn}")
        cols = await storage.read_tab2(tn)

    # без описания карточки — все колонки запроса; служебные (n_id, …||N) отсекает требование подписи
    no_card = cols is None
    if no_card:
        logger.debug(f"No tab2 data, using query columns")
        cols = columns
        cols.insert(0, "!1 111")
        cols.insert(1, "!2 222")

    logger.debug(f"Processing {len(columns)} columns")
    data = {"tabs": []}

    # имена колонок в запросе — как в справочнике подписей или в lower; сверяем без регистра
    map_col = {k.lower(): v for k, v in rows[0].items()}
    labels = {} if no_card else await storage.read_tab_labels(tn)
    # видимость полей как в десктопе (tab/<table>.vis, у потребителя — по номеру схемы)
    vis_row = {k: map_col.get(k + '||', v) for k, v in map_col.items() if '||' not in k}
    hidden = hidden_fields(tn, await storage.read_vis(tn), vis_row)

    async def print_col(subsection, tn, col, prefix, labels=None):
        (tnr, fnr, txt, f1) = storage.get_help(tn, col)
        # подпись как в десктопе: из строки описания карточки, иначе справочник, иначе имя колонки
        label = (labels or {}).get(col.lower()) or txt
        if no_card and txt == col:
            return
        key = (f'{col}||{prefix}' if prefix else col).lower()
        if key not in map_col:
            return

        id = -1
        if prefix == '':
            id = map_col.get('id')
        elif prefix == 'N':
            id = map_col.get('n_id')
        elif prefix == 'N1':
            id = map_col.get('n1_id')
        elif prefix == 'N2':
            id = map_col.get('n2_id')
        elif prefix == 'L':
            id = map_col.get('l_id')

        field = {'table': tn, 'field': col, 'label': label, 'value': map_col.get(key), 'id': id}

        if key + '||' in map_col:
            l = storage.get_lookup(tn, col)
            if l is None:
                logger.error('Error: No lookup found!')
                return

            (tn1, fn1, tn2, id2, fn2, srt) = l
            field['code'] = map_col.get(key + '||')
            field['type'] = 'select'
            field['select'] = f'{tn2} {id2} {fn2} {srt}'
        else:
            field['type'] = 'text'

        subsection['fields'].append(field)

    first_tab = None
    tab = None

    for col in cols:
        if col[0:2] == '!1':
            tab = {"title": col[3:], "subsections": []}
            data["tabs"].append(tab)
            if first_tab is None:
                first_tab = tab
                if typ == 'L':
                    subsection = {"title": "Начальный узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for c in ['externalCodeID', 'externalNodeName']:
                        await print_col(subsection, 'nodes', c, 'N1')

                    subsection = {"title": "Конечный узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for c in ['externalCodeID', 'externalNodeName']:
                        await print_col(subsection, 'nodes', c, 'N2')

                    subsection = {"title": "Общая информация", "fields": []}
                    tab["subsections"].append(subsection)
                    for c in ['externalSignLineID','organizationID','hydroRes']:
                        await print_col(subsection, 'linesobj', c, 'L')
                elif typ == 'N':
                    subsection = {"title": "Узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for c in NODE_HEAD_FIELDS:
                        await print_col(subsection, 'nodes', c, 'N')
        elif col[0:2] == '!2':
            if tab is None:
                tab = {"title": '!!', "subsections": []}
                data["tabs"].append(tab)
            subsection = {'title': col[3:], "fields": []}
            tab["subsections"].append(subsection)
        elif col.lower() in ('id', 'shape') or col.lower() in hidden:
            continue
        else:
            await print_col(subsection, tn, col, '', labels)

    # десктоп: у НС, источника, потребителей — поля узла в конце первой вкладки
    if typ == 'N' and first_tab is not None and tn.lower() not in NO_NODE_TAIL:
        for title, node_cols in NODE_TAIL_SUBSECTIONS:
            subsection = {"title": title, "fields": []}
            for c in node_cols:
                await print_col(subsection, 'nodes', c, 'N')
            if subsection["fields"]:
                first_tab["subsections"].append(subsection)

    # подразделы, оставшиеся без полей (всё скрыто или нет колонок), не показываем
    for t in data["tabs"]:
        t["subsections"] = [s for s in t["subsections"] if s["fields"]]

    logger.debug(f"Query result processed, returning JSON")
    return json.dumps(data, ensure_ascii=False, indent=4, default=str)


async def get_all_fragments() -> List[Dict[str, str]]:
    """Получить список фрагментов (id, name)."""
    from database.connect import acquire_conn, query_log

    query = "SELECT id, name FROM fragments ORDER BY name"

    async with acquire_conn() as conn:
        rows = await query_log(conn, query)
        return rows

async def _coerce_for_columns(conn, table: str, columns: Dict[any, str], fields: Dict[any, any]) -> List[any]:
    """Значения JSON → типы колонок (дата строкой, число строкой, '' → NULL).

    Без этого asyncpg падает на ``'2026-01-01'`` для date (toordinal) → 500. Ошибка типа —
    ``TypedEditError`` 422 (роутеры превращают её в HTTPException). Типы без описания
    (геометрия, массивы) передаются как есть.
    """
    rows = await conn.fetch(
        "SELECT column_name, data_type, character_maximum_length FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = $1",
        table,
    )
    types = {str(r["column_name"]): (r.get("data_type"), r.get("character_maximum_length")) for r in rows}
    values = []
    for key, val in fields.items():
        name = columns[key]
        data_type, max_len = types.get(name, (None, None))
        kind = _KINDS.get(data_type) if data_type else None
        values.append(coerce_value(FieldSpec(name=name, label=name, kind=kind, max_length=max_len), val) if kind else val)
    return values

async def update_object_attributes(table: str, obj_id: int, fields: Dict[str, any]) -> bool:
    """Обновляет атрибуты объекта в БД."""
    if not fields:
        return True
    
    set_clauses = []
    values = []

    async with acquire_conn() as conn:
        # Таблица — только из allow-list CRUD, колонки — только из каталога этой таблицы
        actual = await resolve_table(conn, table, mutable_tables())
        columns = await resolve_columns(conn, actual, fields.keys())
        typed = await _coerce_for_columns(conn, actual, columns, fields)
        for i, (key, val) in enumerate(zip(fields.keys(), typed), start=1):
            set_clauses.append(f'{quote_ident(columns[key])} = ${i}')
            values.append(val)

        values.append(obj_id)
        id_index = len(values)

        q = f'UPDATE {quote_ident(actual)} SET {", ".join(set_clauses)} WHERE id = ${id_index}'

        logger.info(f"Updating object in {actual}: ID {obj_id}, Fields: {list(columns.values())}")
        try:
            await conn.execute(q, *values)
            return True
        except Exception as e:
            logger.error(f"Error updating {table} ID {obj_id}: {e}")
            raise e

async def create_object(table: str, fields: Dict[str, any]) -> int:
    """Создает новый объект в БД и возвращает его ID."""
    if not fields:
        raise ValueError("No fields provided for insertion")
        
    cols = []
    vals = []
    placeholders = []

    async with acquire_conn() as conn:
        actual = await resolve_table(conn, table, mutable_tables())
        columns = await resolve_columns(conn, actual, fields.keys())
        typed = await _coerce_for_columns(conn, actual, columns, fields)
        for i, (key, val) in enumerate(zip(fields.keys(), typed), start=1):
            cols.append(quote_ident(columns[key]))
            vals.append(val)
            placeholders.append(f'${i}')

        q = f'INSERT INTO {quote_ident(actual)} ({", ".join(cols)}) VALUES ({", ".join(placeholders)}) RETURNING id'

        logger.info(f"Creating object in {actual}: Fields: {list(columns.values())}")
        try:
            new_id = await conn.fetchval(q, *vals)
            return new_id
        except Exception as e:
            logger.error(f"Error creating object in {table}: {e}")
            raise e

async def delete_object(table: str, obj_id: int) -> bool:
    """Удаляет объект из БД по ID."""
    async with acquire_conn() as conn:
        actual = await resolve_table(conn, table, mutable_tables())
        q = f'DELETE FROM {quote_ident(actual)} WHERE id = $1'
        logger.info(f"Deleting object in {actual}: ID {obj_id}")
        try:
            await conn.execute(q, obj_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting object from {table} ID {obj_id}: {e}")
            raise e

async def get_lookup_data(table: str, id_col: str, name_col: str, sort_col: str) -> List[Dict[str, any]]:
    """Получает данные справочника для селектов.

    Все четыре идентификатора приходят из query-строки: таблица — только из справочников
    kls/gid.lookup, колонки — только из каталога этой таблицы. sort_col «none», пустой
    или числовой (флаг сортировки из gid.lookup) — сортировка по name_col.
    """
    async with acquire_conn() as conn:
        actual = await resolve_table(conn, table, storage.lookup_tables())
        id_sql = quote_ident(await resolve_column(conn, actual, id_col))
        name_sql = quote_ident(await resolve_column(conn, actual, name_col))
        if sort_col and sort_col.lower() != 'none' and not sort_col.isdigit():
            order_sql = quote_ident(await resolve_column(conn, actual, sort_col))
        else:
            order_sql = name_sql
        q = f'SELECT {id_sql} AS value, {name_sql} AS title FROM {quote_ident(actual)} ORDER BY {order_sql}'
        logger.debug(f"Fetching lookup: {q}")
        rows = await query_log(conn, q)
        return [dict(r) for r in rows]

if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await create_select_line('heatPipeSections', 137)
        print(result)

    asyncio.run(main())