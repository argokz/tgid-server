import psycopg2 as pyodbc

#-----------------------------------------------------------------------------------

def split_sql_expressions(text):
    current = ''
    state = None
    for c in text:
        if state is None:  # default state, outside of special entity
            current += c
            if c in '"\'':
                # quoted string
                state = c
            elif c == '-':
                # probably "--" comment
                state = '-'
            elif c == '$':
                # probably $$"
                state = '$'
            elif c == '/':
                # probably '/*' comment
                state = '/'
            elif c == ';':
                # remove it from the statement
                current = current[:-1].strip()
                # and save current stmt unless empty
                if current:
                    yield current
                current = ''
        elif state == '-':
            if c != '-':
                # not a comment
                state = None
                current += c
                continue
            # remove first minus
            current = current[:-1]
            # comment until end of line
            state = '--'

        
        elif state == '$':
            current += c
            if c != '$':
                # not a $$
                state = None
            else:
                state = '$$'
        
        elif state == '--':
            if c == '\n':
                # end of comment
                # and we do include this newline
                current += c
                state = None
            # else just ignore
        elif state == '/':
            if c != '*':
                state = None
                current += c
                continue
            # remove starting slash
            current = current[:-1]
            # multiline comment
            state = '/*'

        
        elif state == '$$':
            current += c
            if c == '$':
                # probably end of $$
                state = '$$$'

        elif state == '$$$':
            current += c

            if c == '$':
                state = None
            else:
                # not an end
                state = '$$'
        
        elif state == '/*':
            if c == '*':
                # probably end of comment
                state = '/**'
        elif state == '/**':
            if c == '/':
                state = None
            else:
                # not an end
                state = '/*'
        elif state[0] in '"\'':
            current += c
            if state.endswith('\\'):
                # prev was backslash, don't check for ender
                # just revert to regular state
                state = state[0]
                continue
            elif c == '\\':
                # don't check next char
                state += '\\'
                continue
            elif c == state[0]:
                # end of quoted string
                state = None
        else:
            raise Exception('Illegal state %s' % state)

    if current:
        current = current.rstrip(';').strip()
        if current:
            yield current

#-----------------------------------------------------------------------------------

def execQ(cursor, qq, msg=True):
    for q in split_sql_expressions(qq):
        try:
            cursor.execute(q)
#            conn.commit()
        except pyodbc.Error as e:
            if msg:
                 print('!', e)
                 print('------------------------')
                 print(q)
                 print('------------------------')

#    conn.commit()

#-----------------------------------------------------------------------------------


def execFile(conn, file_name, map_f={}):
    with open(file_name, 'r') as f:
        cursor = conn.cursor()
        q = f.read()

        for k, v in map_f.items():
            q = q.replace(k, v)

        execQ(cursor, q)

        cursor.close()

#-----------------------------------------------------------------------------------



def listQ(cursor, q):
    
    list_q = list()

    cursor.execute(q)

    while True:
        row = cursor.fetchone()
        if not row: break

        c, = row

        list_q.append(c)

    return list_q

