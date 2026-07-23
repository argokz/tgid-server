import json
from typing import Optional, Dict, List, Tuple
from database.connect import acquire_conn, query_log
from utils.ini import parse_filtr, storage
import logging

logger = logging.getLogger(__name__)  
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
        rows = await query_log(conn, f'SELECT * FROM {tn} LIMIT 1')
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
    logger.info(f"Creating select for line: table={tn}, id={id}")
    async with acquire_conn() as conn:
        (i, par1, par2, joins) = (1, '', '', '')
        joins += 'LEFT JOIN linesobj L ON T.lineID=L.id\n'
        (i, par1, par2, joins) = await get_3_param("linesobj", "L", i, par1, par2, joins, ['externalSignLineID','organizationID','hydroRes','archiveChangeDateoperatorID'])
        joins += 'LEFT JOIN nodes N1 ON N1.id=L.nodeID1\n'
        (i, par1, par2, joins) = await get_3_param("nodes", "N1", i, par1, par2, joins, ['externalCodeID','externalNodeName'])
        joins += 'LEFT JOIN nodes N2 ON N2.id=L.nodeID2\n'
        (i, par1, par2, joins) = await get_3_param("nodes", "N2", i, par1, par2, joins, ['externalCodeID','externalNodeName'])
        
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(tn, "T", i, par1, par2, joins, filtr)

        q = f'SELECT \nT.id,L.id as L_id,N1.id AS N1_id,N2.id AS N2_id,\n{par1}{par2}\nFROM {tn} T\n{joins}\nWHERE L.id=$1'
        logger.debug(f"Generated query: {q[:100]}...")
        return await print_q(conn, 'L', tn, q, id, filtr)

async def create_select_node(tn: str, id: int) -> str:
    logger.info(f"Creating select for node: table={tn}, id={id}")
    if tn == 'nodes':
        result = await create_select(tn, id)
        return result
    async with acquire_conn() as conn:
        (i, par1, par2, joins) = (1, '', '', '')
        joins += 'LEFT JOIN nodes N ON N.id=T.nodeID\n'
        (i, par1, par2, joins) = await get_3_param("nodes", "N", i, par1, par2, joins, ['externalCodeID','externalNodeName','externalSignID','geoMarkTopTube','geoMarkNodeArea'])
        
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(tn, "T", i, par1, par2, joins, filtr)

        q = f'SELECT \nT.id,N.id as N_id,\n{par1}{par2}\nFROM {tn} T\n{joins}\nWHERE N.id=$1'
        logger.debug(f"Generated query: {q[:100]}...")
        return await print_q(conn, 'N', tn, q, id, filtr)

async def create_select_geoline(tn: str) -> str:
    logger.info(f"Creating select for geoline: table={tn}")
    async with acquire_conn() as conn:
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

        q = f'SELECT TOP 10\nT.id,\n{par1}{par2}\nFROM {tn} T\n{joins}'
        logger.debug(f"Generated query: {q[:100]}...")
        return q

async def create_select(tn: str, id: int) -> str:
    logger.info(f"Creating select: table={tn}, id={id}")
    async with acquire_conn() as conn:
        (i, par1, par2, joins) = (1, '', '', '')
        filtr = await storage.read_tab2(tn)
        (i, par1, par2, joins) = await get_3_param(tn, "T", i, par1, par2, joins, filtr)

        q = f'SELECT\nT.id,\n{par1}{par2}\nFROM {tn} T\n{joins}\nWHERE T.id=$1'
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

    if cols is None:
        logger.debug(f"No tab2 data, using query columns")
        cols = columns
        cols.insert(0, "!1 111")
        cols.insert(1, "!2 222")

    logger.debug(f"Processing {len(columns)} columns")
    data = {"tabs": []}

    async def print_col(subsection, map_col, tn, col, prefix):
        (tnr, fnr, txt, f1) = storage.get_help(tn, col)
        col1 = col

        field = dict()

        if txt != col:
            if prefix != '':
                col += '||' + prefix

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

            v1 = map_col.get(col)
            v2 = map_col.get(col+'||')

            field['table'] = tn
            field['field'] = col1
            field['label'] = txt
            field['value'] = v1
            field['id'] = id

            if col+'||' in map_col:
                l = storage.get_lookup(tn, col1)
                if l is None:
                    logger.error('Error: No lookup found!')
                    return

                (tn1, fn1, tn2, id2, fn2, srt) = l
                field['code'] = v2
                field['type'] = 'select'
                field['select'] = f'{tn2} {id2} {fn2} {srt}'
            else:
                field['type'] = 'text'

            subsection['fields'].append(field)

    map_col = dict(rows[0])

    first = True
    tab = None

    for col in cols:
        if col[0:2] == '!1':
            tab = {"title": col[3:], "subsections": []}
            data["tabs"].append(tab)
            if first:
                first = False
                if typ == 'L':
                    subsection = {"title": "Начальный узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for col in ['externalCodeID', 'externalNodeName']:
                        await print_col(subsection, map_col, 'nodes', col, 'N1')

                    subsection = {"title": "Конечный узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for col in ['externalCodeID', 'externalNodeName']:
                        await print_col(subsection, map_col, 'nodes', col, 'N2')

                    subsection = {"title": "Общая информация", "fields": []}
                    tab["subsections"].append(subsection)
                    for col in ['externalSignLineID','organizationID','hydroRes']:
                        await print_col(subsection, map_col, 'linesobj', col, 'L')
                elif typ == 'N':
                    subsection = {"title": "Узел", "fields": []}
                    tab["subsections"].append(subsection)
                    for col in ['externalCodeID','externalNodeName','externalSignID','geoMarkTopTube','geoMarkNodeArea']:
                        await print_col(subsection, map_col, 'nodes', col, 'N')
        elif col[0:2] == '!2':
            if tab is None:
                tab = {"title": '!!', "subsections": []}
                data["tabs"].append(tab)
            subsection = {'title': col[3:], "fields": []}
            tab["subsections"].append(subsection)
        elif col in map_col:
            await print_col(subsection, map_col, tn, col, '')

    logger.debug(f"Query result processed, returning JSON")
    return json.dumps(data, ensure_ascii=False, indent=4, default=str)


async def get_all_fragments() -> List[Dict[str, str]]:
    """Получить список фрагментов (id, name)."""
    from database.connect import acquire_conn, query_log

    query = "SELECT id, name FROM fragments ORDER BY name"

    async with acquire_conn() as conn:
        rows = await query_log(conn, query)
        return rows

async def update_object_attributes(table: str, obj_id: int, fields: Dict[str, any]) -> bool:
    """Обновляет атрибуты объекта в БД."""
    if not fields:
        return True
    
    set_clauses = []
    values = []
    
    for i, (key, val) in enumerate(fields.items(), start=1):
        # Если значение пустая строка и это может быть NULL, можно обрабатывать
        # Но пока просто передаем
        set_clauses.append(f'"{key}" = ${i}')
        values.append(val)
        
    values.append(obj_id)
    id_index = len(values)
    
    q = f'UPDATE "{table}" SET {", ".join(set_clauses)} WHERE id = ${id_index}'
    
    logger.info(f"Updating object in {table}: ID {obj_id}, Fields: {list(fields.keys())}")
    
    async with acquire_conn() as conn:
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
    
    for i, (key, val) in enumerate(fields.items(), start=1):
        cols.append(f'"{key}"')
        vals.append(val)
        placeholders.append(f'${i}')
        
    q = f'INSERT INTO "{table}" ({", ".join(cols)}) VALUES ({", ".join(placeholders)}) RETURNING id'
    
    logger.info(f"Creating object in {table}: Fields: {list(fields.keys())}")
    
    async with acquire_conn() as conn:
        try:
            new_id = await conn.fetchval(q, *vals)
            return new_id
        except Exception as e:
            logger.error(f"Error creating object in {table}: {e}")
            raise e

async def delete_object(table: str, obj_id: int) -> bool:
    """Удаляет объект из БД по ID."""
    q = f'DELETE FROM "{table}" WHERE id = $1'
    
    logger.info(f"Deleting object in {table}: ID {obj_id}")
    
    async with acquire_conn() as conn:
        try:
            await conn.execute(q, obj_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting object from {table} ID {obj_id}: {e}")
            raise e

async def get_lookup_data(table: str, id_col: str, name_col: str, sort_col: str) -> List[Dict[str, any]]:
    """Получает данные справочника для селектов."""
    q = f'SELECT "{id_col}" AS value, "{name_col}" AS title FROM "{table}"'
    if sort_col and sort_col.lower() != 'none':
        q += f' ORDER BY "{sort_col}"'
    else:
        q += f' ORDER BY "{name_col}"'
        
    logger.debug(f"Fetching lookup: {q}")
    async with acquire_conn() as conn:
        rows = await query_log(conn, q)
        return [dict(r) for r in rows]

if __name__ == "__main__":
    import asyncio
    
    async def main():
        result = await create_select_line('heatPipeSections', 137)
        print(result)

    asyncio.run(main())