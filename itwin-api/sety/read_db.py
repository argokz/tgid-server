import sys
import pyodbc
import logging
import csv

from sety import w_data
from sety.any.any import get_gidr_path
from sety.any.connect import br_text

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Читает таблицу tn (колонки по описанию w_data) в словарь look[id] = {имя поля: значение};
# при fileID - только записи указанных фрагментов.
def read_tab(conn, tn: str, look, id='id', fileID=None) -> None:
    cursor = conn.cursor()

    tn2 = w_data.map_tn.get(tn , tn)

    logging.info(f'Начал читать {tn2}')

    print(f'Начал читать {tn2}', file=sys.stderr)

    cols = w_data.str_for_sql(tn, 'o')

    q = f'SELECT {id}, {cols} FROM {br_text(tn)} o'

    if fileID is not None:
        q += f' WHERE fileID IN ({fileID})'

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
           
            id0, *qq = row
            qq = read_row(tn, cursor, row)

            look[id0] = qq

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr)


#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Как read_tab, но для таблиц узловых объектов: соединяет с nodes (только не удаленные) и добавляет fileID узла.
def read_tab_node(conn, tn: str, look, id='id', fileID=None) -> None:
    cursor = conn.cursor()

    tn2 = w_data.map_tn.get(tn , tn)

    logging.info(f'Начал читать {tn2}')

    print(f'Начал читать {tn2}', file=sys.stderr)

    cols = w_data.str_for_sql(tn, 'o')

    q = f'''
        SELECT o.{id}, n.fileID, {cols}
        FROM {br_text(tn)} o
        join nodes n on n.id = o.nodeid  
        where n.removed = 0
        '''

    if fileID is not None:
        q += f' WHERE fileID IN ({fileID})'

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
           
            id0, fileID, *qq = row
            qq = read_row(tn, cursor, row)
            qq['fileID'] = fileID

            look[id0] = qq

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr)


#-----------------------------------------------------------------------------------

# Читает строчку
# [Claude 2026-10-18] Строка CSV -> словарь {колонка (нижний регистр): значение}; числа преобразуются в int/float.
# На значении 'NULL' чтение строки прекращается (см. отчет).
def read_row3(cols, row) -> dict:
    map_row = dict()
#    print(cols)
#    print(row)

    for col, v in zip(cols, row):
        if v == 'NULL':
            break
#            v = None
        else:
            try:
               v = int(v)
            except ValueError:
                try:
                   v = float(v)
                except ValueError:
                   pass
           
        map_row[col.lower()] = v


    return map_row

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Строка результата запроса -> словарь {колонка (нижний регистр): значение}; пустые/нулевые значения пропускаются.
def read_row2(tn, cursor, row) -> dict:
    map_row = dict()

    for col, v in zip(cursor.description, row):
        if v:
            map_row[col[0].lower()] = v

    return map_row

#-----------------------------------------------------------------------------------


# [Claude 2026-10-18] Читает всю таблицу tn (SELECT id, *) в look[id] = словарь полей. При ошибке БД - выход из программы.
def read_tab2(conn, tn: str, look, id='id', fileID=None) -> None:
    cursor = conn.cursor()

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr)

    q = f'SELECT {id}, * FROM {br_text(tn)} o'

    if fileID is not None:
        q += f' WHERE fileID IN ({fileID})'

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
           
            id0, *qq = row
            qq = read_row2(tn, cursor, row)

            look[id0] = qq

    except pyodbc.Error as ex:
        print(q)
        print(ex, file=sys.stderr)
        exit(1)

    print(f'Закончил читать {tn2}', file=sys.stderr)


#-----------------------------------------------------------------------------------


# [Claude 2026-10-18] Читает справочник из CSV sprav/<tn>.csv (разделитель ';') в look[первая колонка] = словарь полей.
def read_csv2(tn: str, look, id='id') -> None:

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr)

#    print(f'{get_gidr_path()}/sprav/{tn}.csv')
#    exit(1)

    with open(f'{get_gidr_path()}/sprav/{tn}.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        cols = next(reader)
#        print(cols)
        
        for row in reader:
            id0, *qq = row
            qq = read_row3(cols, row)

            look[id0] = qq


    print(f'Закончил читать {tn2}', file=sys.stderr)


#-----------------------------------------------------------------------------------


# [Claude 2026-10-18] Читает таблицу tn в справочник look[id] = значение колонки col_name.
def read_lookup(conn, tn: str, col_name: str, look) -> None:
    cursor = conn.cursor()

    q = f'SELECT id, {col_name} FROM {tn}'

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            id, name = row
            look[id] = (name)

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Строка результата запроса -> словарь с переименованием колонок по w_data.tab_list[tn];
# колонки не из списка и пустые/нулевые значения пропускаются.
def read_row(tn: str, cursor, row):
    map_row = dict()

    tab = w_data.tab_list.get(tn, None)


    if not tab is None: 
        for i in range(len(cursor.description)):
            col = cursor.description[i][0]

            if col in tab:
                v = row[i]
                if v:
                    map_row[tab[col]] = v

    return map_row

