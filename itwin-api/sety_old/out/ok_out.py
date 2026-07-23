import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

def out_OK_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from OK_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('OK_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('lineid')
    insert.add_col('externalsignlineid')
    insert.add_col('ist')

    insert.add_col('sost')   # Состояние насосного агрегата
    insert.add_col('ras')   # Расход воды 


    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход

        if typ == 'reverseValves':      # 
            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('lineid', id)
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)
            insert.db_write('ist', heatSourceID)

            insert.db_write('sost')   # Состояние насосного агрегата
            insert.db_write('ras', GG) # Расход

            insert.db_insert_vals()


#    ins = insert.insert_text()
    insert.exec()

#    print(ins)

#    cursor.execute(ins)
#   conn.commit()

