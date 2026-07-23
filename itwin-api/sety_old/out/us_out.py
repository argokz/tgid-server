import numpy as np
import networkx as nx
import networkx as nx
import itertools

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert
from sety.out.pt_out import print_bal
from sety import config

# Считаем подпитку

def n_ras(G, n, debug):
    nP = G.nodes[n]

    nn, po = n

    pt_name = nP.get('name', '???')

    if debug:
        print('-----------------')
        print(n, pt_name)

    GGG = 0

    Gin = 0
    Gout = 0

    for k, (nn1, nn2, key) in itertools.chain(
            zip(itertools.repeat(1), G.in_edges(n, keys=True)),
            zip(itertools.repeat(2), G.out_edges(n, keys=True))
            ): 

        l = G.edges[nn1, nn2, key]

        GG = l.get('G', 0)

        externalSignLineID = l.get('externalSignLineID', 1)

        if k == 2:
            GG = -GG

#        if externalSignLineID == 6 and po == 1:  # Узел с заданным напором
#            GG = -GG

        if debug:
            print('........', GG, k, externalSignLineID)

        GGG += GG

        if GG > 0:
            Gin += GG
        else:
            Gout += GG


    Gp = nP.get('G', 0)

    if Gp != 0:
        if debug:
            print('........', Gp, 'pt')
        GGG -= Gp


    if debug:
        print('........', GGG, 'итого')

    return GGG, Gin, Gout, Gp



def out_US_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from US_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('US_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('nodeid')
    insert.add_col('externalsign')

    insert.add_col('pih')    # Пьезометрический напор
    insert.add_col('t')      # Температура сетевой воды 
    insert.add_col('t2')     #
    insert.add_col('ist')

    for n in G.nodes:
        nn = G.nodes[n]

        num = nn.get('num', -1)
        if num == -1:
            continue

        po = nn['po']
        pih = nn.get('P', 0.)
        id = nn['id']
        t = nn.get('t', -10000)
        t = nn.get('t0', t)


#        if config.args.is_leto:
#            t = -10000;

        if np.isnan(t):
            t = -10000;
        t2 = 0

        # Подпитка
        GG, Gin, Gout, Gp = n_ras(G, n, False)

        if abs(GG) > 0.000001 and Gin > 0 and Gout < 0:
            t =  -t*Gout/Gin  # Поправка на подпитку
#            name = w_print.node_name(G, n, False, False) 
#            if GG < 0:
#                print_bal(f'Подпитка в узле {name} {GG:.1f} т/ч', 0, GG)
#                print_bal(f'Подпитка в узле {name}', 0, GG)
    
#            print(nn.get('name', '???'), po, GG, Gin, Gout, Gp, t)
#            GG = n_ras(G, n, True)
#            if GG < 0:
#                t * GG

        
        insert.addRow()

        insert.db_write('calculationid', calculationid)
        insert.db_write('nodeid', id)
        insert.db_write('externalsign', po)
 
        heatSourceID = nn.get('heatSourceID', 0)
        insert.db_write('ist', heatSourceID)

        insert.db_write('pih', pih)      # Пьезометрический напор       

        if t != -10000:
#            print(nn.get('name', '???'), '----------->', t)
            insert.db_write('t', t)             # Температура сетевой воды     
            insert.db_write('t2')            #                              
    
        insert.db_insert_vals()

    insert.exec()
#    ins = insert.insert_text()

#    cursor.execute(ins)
#    conn.commit()

