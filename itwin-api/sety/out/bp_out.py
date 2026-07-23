import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

def out_BP_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from BP_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('BP_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('lineid')
    insert.add_col('externalsignlineid')
    insert.add_col('ist')

    insert.add_col('sos')   # Состояние насосного агрегата

    insert.add_col('a4')
    insert.add_col('a5')
    insert.add_col('a9')
    insert.add_col('a10')
    insert.add_col('a11')   # Диаметр диафрагмы
    insert.add_col('a12')
    insert.add_col('a13')
    insert.add_col('a14')
    insert.add_col('a15')
    insert.add_col('a16')
    insert.add_col('a17')
    insert.add_col('a18')

    insert.add_col('sopr')
    

#    insert.add_col('a19')

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход

        if typ in ('bypass'):      # 
            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('lineid', id)
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)
            insert.db_write('ist', heatSourceID)

            insert.db_write('sos', e.get('a19', ''))  

            insert.db_write('sopr', e.get('S', 0)) # Сопротивление

            insert.db_write('a4', e.get('a4', 0)) 
            insert.db_write('a5', e.get('a5', 0)) 
            insert.db_write('a9', e.get('a9', 0)) 
            insert.db_write('a10', e.get('a10', 0)) 
            insert.db_write('a11', e.get('a11', 0)) 

            insert.db_write('a13', GG) # Расход воды через клапан регулятора
            insert.db_write('a14', e.get('ustanovka', '')) 
            insert.db_write('a15', e.get('diam', 0)) 
            insert.db_write('a16', e.get('dlina', 0)) 
            insert.db_write('a17', e.get('a17', 0)) 
            insert.db_write('a18', e.get('a18', 0)) 
            
#            print(e)

            '''
            insert.db_write('a11', GG) # Расход воды через клапан регулятора

            insert.db_write('a12', e.get('a12', 0)) 
            insert.db_write('a13', e.get('a13', 0)) 
            insert.db_write('a14', e.get('a14', 0)) 
            insert.db_write('a15', e.get('a15', '')) 
            insert.db_write('a17', e.get('a17', 0)) 
            insert.db_write('a18', e.get('a18', 0)) 
            '''


            insert.db_insert_vals()


#    ins = insert.insert_text()
    insert.exec()

#    print(ins)

#    cursor.execute(ins)
#   conn.commit()

