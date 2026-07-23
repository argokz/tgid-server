import os
import sys
import time
import psycopg2 as pyodbc
from typing import *

from psycopg2.extensions import connection as Connection

import any
import db2
import db3

from db2 import cursor_execute


#from pyodbc import connect as pyodbc.connect
#from pyodbc import Error as pyodbc.Error

#-----------------------------------------------

def HandleHierarchyId(v: Any) -> str:
#    print(str(v))
    return str(0)
#    return str(v)

#-----------------------------------------------

#def connect_ms_sql(**conn_str: Any) -> Connection | None:
def connect_ms_sql(**conn_str: Any):
    driver = 'SQL Server'
    driver = 'ODBC Driver 17 for SQL Server'
#    driver = 'PostgreSQL ODBC Driver(Unicode)'


    _host = conn_str.get('server', '45.132.85.23')
    _host = conn_str.get('server', 'localhost')
    _user = conn_str.get('user', 'Lifan')
    _password = conn_str.get('password', 'Danil228')
    _password = conn_str.get('password', '')
    _db = conn_str.get('db', 'AlmatyGID')
    _db = conn_str.get('db', 'AstanaGID_2023_07_10')
    _db = conn_str.get('db', 'AstanaGID_03_06_24')

    _port = conn_str.get('port', 1437)


#    _password = os.getenv('tgid_password', _password)
#    print(_password)
#    exit(0)


    
    str_connect = (f'DRIVER={{{driver}}};'
            + f'DATABASE={_db};')

    if _password == '':
        str_connect += f'SERVER={_host};'
        str_connect += f'Trusted_Connection=yes;'
    else:
        str_connect += f'SERVER={_host},{_port};'
        str_connect += f'Uid={_user};Pwd={_password}'

#    print(str_connect)

    try:
        conn = pyodbc.connect(str_connect)

        # Это чтобы читать данные geometry и не вылетать
        conn.add_output_converter(-151, HandleHierarchyId)
        return conn
    except pyodbc.Error as ex:
        print('Error: ', ex)
        exit(0)

    return None

#-----------------------------------------------


#def connect_pg(**conn_str: Any) -> Connection | None:
def connect_pg(**conn_str: Any):
    """psycopg2-подключение по параметрам server/user/password/db/port."""
    _host = conn_str.get('server') or os.getenv('DB_HOST', 'localhost')
    _user = conn_str.get('user') or os.getenv('DB_USER', 'postgres')
    _password = conn_str.get('password') or os.getenv('DB_PASSWORD', '')
    _db = conn_str.get('db') or os.getenv('DB_NAME', 'postgres')
    _port = conn_str.get('port') or os.getenv('DB_PORT', 5432)

    try:
        conn = pyodbc.connect(
            host=_host,
            port=int(_port),
            user=_user,
            password=_password,
            dbname=_db,
        )
        if conn_str.get('autocommit'):
            conn.autocommit = True
        return conn
    except pyodbc.Error as ex:
        print('Error', ex)
        raise

#-----------------------------------------------
#def connect_sqlite(**conn_str: Any) -> Connection | None:
def connect_sqlite(**conn_str: Any):

    fn = 'c:\\data\\baza.sqlite'

#    driver = 'Devart ODBC Driver for SQLite'
#    str_connect = f'DRIVER={{{driver}}}; Direct=False; Database={{{fn}}}; Client Library=C:\\bin\\sqlite3.dll'

    
    driver = 'SQLite3 ODBC Driver'
    str_connect = f'DRIVER={{{driver}}};Database={{{fn}}}'
    str_connect = f'DRIVER={{{driver}}};Database={fn}'

#    print(str_connect)

    try:
        conn = pyodbc.connect(str_connect)

        # Это чтобы читать данные geometry и не вылетать
        conn.add_output_converter(-151, HandleHierarchyId)
        return conn
    except pyodbc.Error as ex:
        print(ex)
        exit(0)

    return None

#-----------------------------------------------



#def connect_mdb(db_file: str) -> Connection | None:
def connect_mdb(db_file: str):
    driver = 'Microsoft Access Driver (*.mdb, *.accdb)'
    user = 'admin'
    password = ''
 
    str_connect = f'DRIVER={{{driver}}};DBQ={db_file};UID={user};PWD={password}'

    try:
        conn = pyodbc.connect(str_connect)
        return conn
    except pyodbc.Error as ex:
        print(ex)

    return None


#-----------------------------------------------------------------------------------


#def connect(**conn_str: Any) -> Connection | None:
def connect(**conn_str: Any):

    _rdbms = conn_str.get('rdbms')
    if _rdbms == 'postgreSQL':
        return connect_pg(**conn_str)

    autocommit = conn_str.get('autocommit', False)

    driver = 'SQL Server'
    driver = 'ODBC Driver 17 for SQL Server'
    
    _host = conn_str.get('server', '45.132.85.23')
    _user = conn_str.get('user', 'Lifan')
    _password = conn_str.get('password', 'Danil228___')

#    print(conn_str)
#    exit(0)
    _db = conn_str.get('db', 'Water')
    _port = conn_str.get('port', 1437)

    str_connect = (f'DRIVER={{{driver}}};'
            + f'DATABASE={_db};')

    _password = os.getenv('tgid_password', _password)
#    print(_password)
#    exit(0)


    if _password == '':
        str_connect += f'SERVER={_host};'
        str_connect += f'Trusted_Connection=yes;'
    else:
        str_connect += f'SERVER={_host},{_port};'
        str_connect += f'Uid={_user};Pwd={_password}'

#    print(str_connect)

    try:
        conn = pyodbc.connect(str_connect, autocommit=autocommit)

        # Это чтобы читать данные geometry и не вылетать
        conn.add_output_converter(-151, HandleHierarchyId)
        return conn
    except pyodbc.Error as ex:
        print(ex)
        exit(2)

    return None

def shrink_log(**c):
    rdbms = c['rdbms']
    
    if rdbms == 'MsSql':
#        c['autocommit'] = True
        db = c['db']
        t1 = time.time()

        print(f'Сжатие лога ', end='', flush=True)

        try:
            conn = connect(**c, autocommit=True)
            cursor = conn.cursor()

            q = f'SELECT Name FROM sys.master_files WHERE type_desc = \'LOG\' AND database_id = DB_ID(\'{db}\')'
            log_file_name , = db2.read_db_val(conn, q)

#            q = f'''ALTER DATABASE [{db}] SET RECOVERY SIMPLE'''
#            cursor.execute(q)

            q = f'''DBCC SHRINKFILE ({log_file_name}, 1)'''
            cursor.execute(q)

#            q = f'''ALTER DATABASE [{db}] SET RECOVERY FULL'''
#            cursor.execute(q)

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            cursor.close()
            conn.close()

        t2 = time.time()

        print(f' {t2-t1} секунд', flush=True)

#    print(f' {t2-t1} секунд', flush=True)




def reindex(c):
   
    rdbms = c['rdbms']
    
    if rdbms == 'MsSql':
#        c['autocommit'] = True
        db = c['db']
        t1 = time.time()

        try:
            print(f'Переиндексация ', end='', flush=True)
            t1 = time.time()
            
            conn = connect(**c, autocommit=True)
            cursor = conn.cursor()

            q = any.readFile('help_script_rebuild_index_for_tables.sql').replace('$BAZA$', c['db'])
            cursor_execute(cursor, q, True)

            cursor_execute(cursor, 'EXEC sp_updatestats')

            t2 = time.time()

            print(f' {t2-t1} секунд', flush=True)


        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            cursor.close()
            conn.close()


#    print(f' {t2-t1} секунд', flush=True)

#-----------------------------------------------


def triggers_on_off(start, c):
    _rdbms = c.get('rdbms')

    if _rdbms == 'MsSql':
        db = c.get('db')
        conn = connect(**c, autocommit=True)
        cursor = conn.cursor()

        if start:
            cursor_execute(cursor, f'ALTER DATABASE [{db}] SET RECOVERY BULK_LOGGED;')
#            cursor_execute(cursor, f'ALTER DATABASE [{db}] SET RECOVERY SIMPLE;')
            cursor_execute(cursor, 'sp_msforeachtable \'ALTER TABLE ? DISABLE TRIGGER all\'')
        else:
            reindex(c)

            cursor_execute(cursor, 'sp_msforeachtable \'ALTER TABLE ? ENABLE TRIGGER all\'')
            cursor_execute(cursor, f'ALTER DATABASE [{db}] SET RECOVERY FULL;')

        cursor.close()
        conn.close()

