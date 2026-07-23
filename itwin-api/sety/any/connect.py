import pyodbc
import platform
from typing import *

from pyodbc import Connection

#from pyodbc import connect as pyodbc.connect
#from pyodbc import Error as pyodbc.Error

#-----------------------------------------------

def br_text(text):
#    return f'"[{text}]"'
    return f'"{text.lower()}"'


#-----------------------------------------------

def HandleHierarchyId(v: Any) -> str:
#    print(str(v))
    return str(0)
#    return str(v)


#-----------------------------------------------------------------------------------

def connect_pg(**conn_str: Any) -> Connection | None:
    driver = 'PostgreSQL ODBC Driver(Unicode)'

    driver = 'PostgreSQL Unicode'
    
#    if platform.system() == "Windows":
#        driver = 'PostgreSQL Unicode(x64)'

    _host = conn_str.get('server', 'localhost')
    _user = conn_str.get('user', 'gena1967')
    _password = conn_str.get('password', '12345098')
    _db = conn_str.get('db', 'gis')
    _port = conn_str.get('port', 5432)
    
    str_connect = (f'DRIVER={{{driver}}};'
            + f'DATABASE={_db};')

    str_connect += f'SERVER={_host};PORT={_port};'
    str_connect += f'Uid={_user};Pwd={_password}'

#    print(str_connect)

    try:
        conn = pyodbc.connect(str_connect)
        return conn
    except pyodbc.Error as ex:
        if _db != 'sprav':
            print(ex)

    return None

#-----------------------------------------------

def connect(**conn_str: Any) -> Connection | None:
    _rdbms = conn_str.get('rdbms', )

    if _rdbms == 'postgreSQL':
        return connect_pg(**conn_str)

    driver = 'SQL Server'
    driver = 'ODBC Driver 17 for SQL Server'
    
    _host = conn_str.get('server', '45.132.85.23')
    _user = conn_str.get('user', 'Lifan')
    _password = conn_str.get('password', 'Danil228')
    _db = conn_str.get('db', 'Water')
    _port = conn_str.get('port', 1437)

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

if __name__ == "__main__":
    conn = connect(server='localhost', port=1433, password='', db='Astana')
    print(conn)
