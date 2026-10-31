import sys
import pyodbc
from typing import *

from pyodbc import Connection

#    return 'postgreSQL'


#from pyodbc import connect as pyodbc.connect
#from pyodbc import Error as pyodbc.Error


#-----------------------------------------------

def HandleHierarchyId(v: Any) -> str:
#    print(str(v))
    return str(0)
#    return str(v)

#-----------------------------------------------

def connect_ms_sql(**conn_str: Any) -> Connection | None:
    driver = 'SQL Server'
    driver = 'ODBC Driver 17 for SQL Server'
#    driver = 'PostgreSQL ODBC Driver(Unicode)'

#    _host = conn_str.get('server', 'localhost')
    _host = conn_str.get('server', 'localhost')
    _user = conn_str.get('user', 'Lifan')
    _password = conn_str.get('password', '')
    _password = conn_str.get('password', '')
    _db = conn_str.get('db', 'AlmatyGID')
    _db = conn_str.get('db', 'AstanaGID_2023_07_10')
    _port = conn_str.get('port', 1433)
    
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
        print(ex)

    return None

#-----------------------------------------------


def connect_pg(**conn_str: Any) -> Connection | None:
    driver = 'PostgreSQL ODBC Driver(Unicode)'
    driver = 'PostgreSQL Unicode(x64)'
    driver = 'PostgreSQL Unicode'

    _host = conn_str.get('server', 'localhost')
    _user = conn_str.get('user', 'gena1967')
    _password = conn_str.get('password', '')
    _db = conn_str.get('db', 'gis')
    _port = conn_str.get('port', 5432)
    
    str_connect = f'DRIVER={{{driver}}};'

    if _db != '':
        str_connect += f'DATABASE={_db};'

    str_connect += f'SERVER={_host};PORT={_port};'
    str_connect += f'Uid={_user};Pwd={_password}'

#    print(str_connect)

    try:
        conn = pyodbc.connect(str_connect)

        # Это чтобы читать данные geometry и не вылетать
        conn.add_output_converter(-151, HandleHierarchyId)
        return conn
    except pyodbc.Error as ex:
        print(ex)

    return None

#-----------------------------------------------
def connect_sqlite(fn) -> Connection | None:

#    fn = 'c:\\data\\baza.sqlite'

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
def connect_mdf(fn) -> Connection | None:

#    fn = 'c:\\data\\baza.sqlite'

#    driver = 'Devart ODBC Driver for SQLite'
#    str_connect = f'DRIVER={{{driver}}}; Direct=False; Database={{{fn}}}; Client Library=C:\\bin\\sqlite3.dll'

    

#    driver = 'SQLite3 ODBC Driver'
#    str_connect = f'DRIVER={{{driver}}};Database={{{fn}}}'
#    str_connect = f'DRIVER={{{driver}}};Database={fn}'

    driver = 'SQL Server'
    driver = 'ODBC Driver 17 for SQL Server'

    str_connect = f'''DRIVER={{{driver}}};
        SERVER=(local)\\SQLEXPRESS;'
        Trusted_Connection=yes;
        AttachDbFileName={fn};'''

    str_connect = f'''DRIVER={{{driver}}};
        SERVER=(localdb)\\MSSQLLocalDB;'
        DATABASE=master;
        Integrated Security=True;'''

#SERVER=(localdb)\\MSSQLLocalDB;


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


#-----------------------------------------------



def connect_mdb(db_file: str) -> Connection | None:
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
