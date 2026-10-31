import time
import pyodbc
from pyodbc import Connection

def read_table_cols(conn, tn):
    q = f'''SELECT col.column_name, col.data_type FROM INFORMATION_SCHEMA.COLUMNS col
        WHERE LOWER(TABLE_NAME) = \'{tn.lower()}\''''


    q = f'''PRAGMA table_info([{tn.lower()}])
    '''

    cursor = conn.cursor()
    cursor.execute(q)

    col_types = {}

    while True:
        row = cursor.fetchone()
        if not row: break

#        print(row)

        id, col_name, col_data_type, notnull, dflt_value, pr = row

#        col_name, col_data_type = row
        col_types[col_name.lower()] = col_data_type


#    exit(0)
    return col_types
#        print(col_name, col_data_type)

#---------------------------------------------------------
'''
def get_cols(conn, tn, prefix = ''):
    col_types = db2.read_table_cols(conn, tn)

    s = ''

#    print(tn)

    for col, typ in col_types.items():
        if col == 'shape': continue
        if col == 'id_old': continue
        if col == 'removed': continue
        if col == 'idremoved': continue
        if col == 'fileid' and tn == 'linesobj': continue
        if col == 'internalnodeid' and tn == 'linesobj': continue
        
        if s != '': s += ','

        if typ == 'timestamp without time zone':
            s += f'date({prefix}.{br_text(col)}) as {br_text(col)}'
        else:
            if prefix != '':
                s += prefix+'.'+br_text(col)
            else:
                s += br_text(col)

#        if tn == 'nodes':
#            print('   ', col, typ)
            

#    if tn == 'nodes':
#        print(s)

    return s
'''


#---------------------------------------------------------

def getLastID(cursor, tn):
    q = f'SELECT IDENT_CURRENT(\'{tn}\') AS id'
    r = cursor.execute(q)
#    r = cursor.execute("SELECT SCOPE_IDENTITY() AS id")
    rr = r.fetchone()
    return int(rr[0])


#---------------------------------------------------------

def cursor_execute(cursor, q, msg = True):
    try:
        t1 = time.time()
    
        ret = cursor.execute(q)

        t2 = time.time()

        if msg and False:
            print('------------------------')
            print(q)
            print('------------------------')
            print(f'{round(t2-t1, 2)} секунд', flush=True)
            print('------------------------')
    
    
    except pyodbc.Error as e:
        if msg:
            print('!', e)
            print('------------------------')
            print(q)
            print('------------------------')

