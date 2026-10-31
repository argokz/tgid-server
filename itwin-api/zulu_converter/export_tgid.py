import io
import csv

import sys
import os
import tempfile
import pyodbc
from zipfile import ZipFile, ZIP_DEFLATED
import datetime
import csv
import re
from collections import defaultdict
from pyodbc import Connection

import connect
import lookup
import list_tab
import db2


old_version = False

def br_text(text):
#    return f'"[{text}]"'

    if RDBMS == 'MsSql':
        return f'[{text.lower()}]'
    else:
        return f'"{text.lower()}"'



#------------------------------------------------------------------------------------

def cursor_execute(cursor, q, msg = True):
    try:
        cursor.execute(q)
        return True
    except pyodbc.Error as e:
        if msg:
            print('!', e)
            print('------------------------')
            print(q)
            print('------------------------')

    return False


#------------------------------------------------------------------------------------

def print_q(f, conn, q):
    cursor = conn.cursor()
    
    if not cursor_execute(cursor, q, False):
        return


#    print('------------------')
#    print(q)
#   print('------------------')

#    csv.register_dialect('tgid', delimiter=':', quoting=csv.QUOTE_NONE)
    csv.register_dialect('tgid', 
        delimiter=',',
        doublequote=True,
        quotechar='"',
        lineterminator='\r\n',
        escapechar='\\',
        quoting=csv.QUOTE_STRINGS)


#    columns = [column[0] for column in cursor.description if column[0] not in ('id')]
    
    columns = [f'"{column[0]}"' for column in cursor.description]
    print(",".join(columns), file=f)

    while True:
        row = cursor.fetchone()
        if not row: break

        for i in range(len(row)):
#            print(row[i], type(row[i]))
            if type(row[i]) is str:
                row[i] = row[i].replace('\r\n', '¶')
                row[i] = row[i].replace('\n', '¶')
                row[i] = row[i].replace('\r', '¶')

#        x = [str(value) for value in row]
        line = io.StringIO()
        writer = csv.writer(line, dialect='tgid')
        writer.writerow(row)
        s = line.getvalue().rstrip()
        print(s, file=f)

#        x = [str(value) for value in x]




#        col_name, col_data_type = row
#        col_types[col_name.lower()] = col_data_type

#------------------------------------------------------------------------------------

def print_tab(f, conn, tn):
    tn = tn.lower()

    list_tab_l = [tn.lower() for tn in list_tab.list_tab]

    if tn in list_tab_l: return

#    print(list_tab_l)
#    exit(0)


    print('-------------------------', file=f)
    print(tn, file=f)

    print_q(f, conn, f'select * from {br_text(tn)}')

#------------------------------------------------------------------------------------

def get_cols(conn, tn, prefix):
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
            s += prefix+'.'+br_text(col)

#        if tn == 'nodes':
#            print('   ', col, typ)
            

#    if tn == 'nodes':
#        print(s)

#    if tn == 'pipesections' and prefix == 'o':
#        print(s)
#        exit(0)

    return s



#------------------------------------------------------------------------------------

def print_tab0(f, conn, tn, fileID):

    print('-------------------------', file=f)
    print(tn, file=f)

    tn = tn.lower()

    get_cols(conn, tn, 'w')

    col_types = db2.read_table_cols(conn, tn)


    q = f'select {get_cols(conn, tn, 'o')} from {br_text(tn)} o'

    if 'fileid' in col_types.keys():
        q = f'select {get_cols(conn, tn, 'o')} from {br_text(tn)} o where o.fileID={fileID}'

    if tn == 'linesobj':
        q = f'select {get_cols(conn, tn, 'l')} from linesobj l join nodes n1 on n1.id=l.nodeID1 and n1.fileID={fileID} and l.removed=0'

    if 'nodeid' in col_types.keys():
        q = f'''
select {get_cols(conn, tn, 'o')} from {tn} o 
join nodes n on n.id=o.nodeID 
and n.fileID={fileID} and n.removed=0'''


    if 'lineid' in col_types.keys():
        q = f'''
select {get_cols(conn, tn, 'o')} from {tn} o
join linesobj l on l.id=o.lineID
join nodes n on n.id=l.nodeID1 
where n.fileID={fileID} and n.removed=0 and l.removed=0
'''

    if tn == 'heatsystem':
        q = f'select {get_cols(conn, tn, 'o')} from {br_text(tn)} o where o.id=1'
    
    if tn == 'fragments':
        q = f'select {get_cols(conn, tn, 'o')} from {br_text(tn)} o where o.id={fileID}'

    if tn == 'deployedtempgraphs':
        q = f'''
select {get_cols(conn, tn, 'dt')} from deployedtempgraphs dt
join heatSources hs on hs.id=dt.hSourceID
join nodes n on n.id=hs.nodeID and n.fileid={fileID} and n.removed=0
'''
    
    if tn == 'pipesections':
        q = f'''
select distinct {get_cols(conn, tn, 'ps')} from pipeSections ps
join heatPipeSections hps on hps.pipeSectionID=ps.id
join linesobj l on l.id=hps.lineID
join nodes n1 on n1.id=l.nodeID1
where n1.fileid={fileID}
'''


#    print(q)
    print_q(f, conn, q)

#------------------------------------------------------------------------------------

def print_head(f):
    dt = str(datetime.datetime.today().strftime('%d-%m-%Y %H:%M:%S'))
    
    print(f'=========================', file=f)

#    old_version = c.get('old_version', False)
    old_version = False

    if not old_version:
        print(f'Version: 2.0', file=f)
        print(f'CodePage: utf-8', file=f)
    print(f'Server: localhost', file=f)
    print(f'Database: db', file=f)
    print(f'User: user', file=f)
    print(f'Date: {dt}', file=f)


#def export_tgid(f, **c):

def export_tgid(f, sqlite_file, fn, fileID):

#def export_tgid(f, sqlite_file):
    global RDBMS
#    RDBMS = c['rdbms']
    RDBMS = 'MsSql'

#    if RDBMS == 'MsSql':
    global prefix
    prefix = '#'

#    fn = c['fn']
#    fileID = c['fileID']

#    old_version = c.get('old_version', False)
    old_version = False

    conn = connect.connect_sqlite(sqlite_file)

    print_head(f)

    print_tab0(f, conn, 'heatSystem', fileID)

    for tn in list_tab.list_tab:
        print_tab0(f, conn, tn, fileID)

    if old_version:
        return

    print(f'=========================', file=f)
    print(f'Lookups', file=f)

    map_lookup, set_lookup = lookup.init_lookup()

    for tn in set_lookup:
        print_tab(f, conn, tn)


#------------------------------------------------------

def read_list(sqlite_file):
#    conn = connect.connect(**c)
    conn = connect.connect_sqlite(sqlite_file)
    cursor = conn.cursor()

    map_list = dict()

    q = 'select id, name from fragments order by id'
    q = '''
       select distinct fr.id, fr.name 
       from fragments fr
       join nodes n on n.fileID=fr.id
       order by fr.id
    '''
    
    if not cursor_execute(cursor, q, False):
        print('Error 1')
        exit(0)

    while True:
        row = cursor.fetchone()
        if not row: break
        id, name = row

        map_list[id] = name


    return map_list


#------------------------------------------------------

def run_export_tgid(sqlite_file, path_out):
#    sys.stdout.reconfigure(encoding='cp866')
    sys.stdout.reconfigure(encoding='utf-8')  # Устанавливаем кодировку UTF-8

    path = os.path.splitext(os.path.basename(__file__))[0]
#    args = config2.init(path, 'Программа для экспорта itwin-файлов')

    tdir = tempfile.gettempdir()
#    tmpn = os.path.join(tempfile.mkdtemp(), 'something')
    tmpn = os.path.join(tdir, 'tgid.txt')

    

#    if config2.args.fileID == -1:
    map_list = read_list(sqlite_file)

#    print(map_list)

    encoding = 'utf-8'

    old_version = False

    if old_version:
        encoding = 'cp1251'

    for fileID, name in map_list.items():
#        fn = f'D:/Qt/gid8/python/zulu2/1/itwin{fileID}.itwin'
        fn = f'{path_out}/itwin{fileID}.itwin'
        fn = f'{path_out}/{name}_{fileID}.itwin'

        with open(tmpn, 'w', encoding=encoding) as f:
            export_tgid(f, sqlite_file, fn=fn, fileID=fileID)
            print(fileID, fn)

       
            with ZipFile(fn, 'w') as myzip:
                myzip.write(tmpn, 'tgid.txt', compress_type = ZIP_DEFLATED)


#------------------------------------------------------

def run():
    run_export_tgid('D:/Qt/gid8/python/zulu2/1/baza.sqlite', 'D:/Qt/gid8/python/zulu2/1')

#------------------------------------------------------


if __name__ == "__main__":
    run()
    sys.exit(0)
