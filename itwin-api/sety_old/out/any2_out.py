import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

from sety.out.pt_out import print_bal

def out_ANY2_OUT(G, conn, calculationid):
    cursor = conn.cursor()


    cursor.execute(f'delete from ANY2_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('ANY2_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('nodeid')
    insert.add_col('mesto')
    insert.add_col('sopr')
    insert.add_col('externalsignlineid')
    insert.add_col('ras')   
    insert.add_col('ist')

    yP = 0
    yO = 0

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        t1 = nn1.get('t', None)
        t2 = nn2.get('t', None)

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход

        num = e.get('num', -1)
        if num == -1:
            continue

        if typ in ('TO', 'EL', 'SO', 'VN', 'DR', 'ZD', 'UT'): 

            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('nodeid', id)
#            insert.db_write('nodeid1', e.get('nodeID1', None))
#            insert.db_write('nodeid2', e.get('nodeID2', None))
            insert.db_write('mesto', e.get('mesto', None))
            insert.db_write('sopr', e.get('S', None))
            
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)


            insert.db_write('ist', heatSourceID)

            insert.db_write('ras', e.get('G', 0.))   # Расход сетевой воды на участке
            insert.db_insert_vals()



    insert.exec()

#    print(insert.ins)
#    exit(0)


