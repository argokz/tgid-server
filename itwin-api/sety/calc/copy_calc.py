import os
import pyodbc
from typing import List, Tuple, Sequence
import argparse

#------------------------------------------------------------------------

def connect_to_database(db_name, host, port, user, password):
    try:
        conn_str = (
            "DRIVER={PostgreSQL Unicode};"
            f"SERVER={host};"
            f"PORT={port};"
            f"DATABASE={db_name};"
            f"UID={user};"
            f"PWD={password};"
        )
        connection = pyodbc.connect(conn_str)
        return connection
    except Exception as e:
        print(f"Error connecting to database {db_name}: {e}")
        return None
#------------------------------------------------------------------------

def fetch_columns_and_rows(conn, select_sql: str, select_params: Sequence = ()):
    """
    Выполняет SELECT и возвращает:
      - columns: список имён колонок
      - rows: список кортежей данных
    """
    cur = conn.cursor()
    cur.execute(select_sql, select_params)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    cur.close()
    return columns, rows

#------------------------------------------------------------------------

#------------------------------------------------------------------------

def update_many(cur, table, key_column, update_columns, rows):
    """
    Массовый UPDATE для pyodbc.
    
    rows должны быть в формате:
    [(id, val1, val2, ...), (id, val1, val2, ...), ...]
    """
    if not rows:
        return

    set_clause = ', '.join(f"{col} = ?" for col in update_columns)

    sql = f"""
        UPDATE {table}
        SET {set_clause}
        WHERE {key_column} = ?
    """

    # Для executemany параметры должны совпадать по порядку
    params = [tuple(r[1:] + (r[0],)) for r in rows]  
    # r[1:] -> значения обновляемых колонок
    # r[0]  -> id в WHERE

    cur.executemany(sql, params)
#------------------------------------------------------------------------

def copy_calc(conn1, conn2, fileID):
    lst = [
      ('us.sql',    'gid.nodes',                       'nodes',      ),
      ('pr.sql',    'gid.realconsumers',               'nodes',      ),
      ('po.sql',    'gid.generalizedconsumers',        'nodes',      ),
      ('nst.sql',   'gid.pumpstations',                'nodes',      ),
      ('ist.sql',   'gid.heatsources',                 'nodes',      ),
      ('hps1.sql',  'gid.heatpipesections',            'linesobj',      ),
    ]


    for fn, table, typ in lst:
        parent_dir = os.path.dirname(os.path.abspath(__file__))  
        with open(parent_dir + '/' + fn, 'r', encoding='utf-8') as f:
            select_sql = f.read().replace('$fileID$', f'{fileID}')
            cols, rows = fetch_columns_and_rows(conn1, select_sql, ())
            cur2 = conn2.cursor()
            update_many(cur2, table, f'{typ}_id', cols[1:], rows)
            conn2.commit()
            cur2.close()

#------------------------------------------------------------------------

if __name__ == '__main__':

    # Настройка аргументов командной строки
    parser = argparse.ArgumentParser(description='from demo9gid to demo9')
    parser.add_argument('--host', required=True, help='Database host')
    parser.add_argument('--port', required=True, help='Database port')
    parser.add_argument('--user', required=True, help='Database user')
    parser.add_argument('--password', required=True, help='Database password')
    parser.add_argument('--db1', required=True, help='First database name')
    parser.add_argument('--db2', required=True, help='Second database name')
    parser.add_argument('--fileID', required=True, type=int, help='Fragment')

    args = parser.parse_args()

    conn1 = connect_to_database(args.db1, args.host, args.port, args.user, args.password)
    conn2 = connect_to_database(args.db2, args.host, args.port, args.user, args.password)

    copy_calc(conn1, conn2, args.fileID)

    conn1.close()
    conn2.close()
