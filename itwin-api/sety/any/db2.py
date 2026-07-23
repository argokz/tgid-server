import pyodbc

from sety import config


def print_q(f, conn, q):
    cursor = conn.cursor()
    
    if not cursor.execute(q):
        return

#    columns = [f'"{column[0]}"' for column in cursor.description]
#    print(",".join(columns), file=f)

    while True:
        row = cursor.fetchone()
        if not row: break

        for i in range(len(row)):
            print(row[i], file=f, end=' ')

        print()

#        col_name, col_data_type = row
#        col_types[col_name.lower()] = col_data_type

#-----------------------------------------------

def exists_q(conn, q):
    cursor = conn.cursor()

    if not cursor.execute(q):
        return False

    while True:
        row = cursor.fetchone()
        if not row: break

        return True

    return False


#-----------------------------------------------


def read_q_value(cursor, q, vals=None):
    try:
#        q = 'insert into calculation (fileID) values(58) SELECT SCOPE_IDENTITY()'
#        vals = None

        if vals is None:
            cursor.execute(q)
        else:
            cursor.execute(q, vals)

        while True:
            row = cursor.fetchone()
#            print(row)

            if not row: break
            v, *qq = row
            return v

    except pyodbc.Error as ex:
        print(ex)
        print('----------------')
        print(q)
        print(vals)
        print('----------------')
        exit(1)

#    print('!!!!!!!!!!!!!!!!!')
#    exit(1)
    return None


#-----------------------------------------------


def exec_insert(cursor, q, vals=None):
    if config.args.rdbms == 'postgreSQL':
        q = q.replace('$MS_SQL_OUTPUT$', '')
        q += ' returning id'
        return read_q_value(cursor, q, vals)

    elif config.args.rdbms == 'MsSql':
        q = q.replace('$MS_SQL_OUTPUT$', 'OUTPUT INSERTED.id')
        return read_q_value(cursor, q, vals)

    return None


