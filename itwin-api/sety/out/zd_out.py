import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

def out_ZD_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from ZD_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('ZD_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('lineid')
    insert.add_col('externalsignlineid')
    insert.add_col('ist')


    insert.add_col('sos')   # Состояние
    insert.add_col('a7')   # Состояние задвижки
    insert.add_col('a8')   # Содержательное наименование задвижки.
    insert.add_col('a9')   # Расход сетевой воды через задвижку
    insert.add_col('a10')   # Потери напора на задвижке
    insert.add_col('a11')   # Полное гидравлическое сопротивление задвижки
    insert.add_col('a12')   # Располагаемый напор в конечном узле задвижки
    insert.add_col('a13')   # Пьзометрический напор в конечном узле задвижки
    insert.add_col('a14')   # Геодезические отметки местности в конечном узле задвижки
    insert.add_col('a15')   # Полный напор в конечном узле задвижки


    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход

        if typ == 'dampers':      # Участки
            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('lineid', id)
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)
            insert.db_write('ist', heatSourceID)

            insert.db_write('sos')   # Состояние
            insert.db_write('a7')   # Состояние задвижки
            insert.db_write('a8')   # Содержательное наименование задвижки.
            insert.db_write('a9', GG)   # Расход сетевой воды через задвижку
            insert.db_write('a10')   # Потери напора на задвижке
            insert.db_write('a11')   # Полное гидравлическое сопротивление задвижки
            insert.db_write('a12')   # Располагаемый напор в конечном узле задвижки
            insert.db_write('a13')   # Пьзометрический напор в конечном узле задвижки
            insert.db_write('a14')   # Геодезические отметки местности в конечном узле задвижки
            insert.db_write('a15')   # Полный напор в конечном узле задвижки

            insert.db_insert_vals()


#    ins = insert.insert_text()
    insert.exec()

#    print(ins)

#    cursor.execute(ins)
#   conn.commit()

