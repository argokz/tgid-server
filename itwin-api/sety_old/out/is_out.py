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

from sety import w_print
from sety.ct import get_ct
from sety.out.podpitka import n_ras
from sety.any.colors import nbsp
from sety.any.colors import cprint

def out_IS_OUT(G, conn, calculationid):
    t1 = 0
    t2 = 0

    G0 = 0
    Q0 = 0

    ct = get_ct()
    ct5 = ct.get('tx', 5)

    for n in G.nodes:
        nP = G.nodes[n]

        po = nP['po']
        pih = nP.get('P', 0.)
        id = nP['id']
        typ = nP['typ']
        t = nP.get('t', -10000)
        t = nP.get('t0', t)

        if np.isnan(t):
            t = -10000;

        t2 = 0



        if typ == 'heatSources' and po == 1:      # 

            name = w_print.node_name(G, n, False, False) 
            
            nO = G.nodes.get((id, 2), None)
            t2 = nO.get('t', -10000)
            t2 = nO.get('t0', t2)
            
            GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, (id, 1), False)
            GG_O, Gin_O, Gout_O, Gp_O, Gout_O =  n_ras(G, (id, 2), False) 

            if abs(Gin_P) < 0.000001:
                cprint(f'Источник {name} отключен', color='red')
                continue

            if abs(Gin_O) < 0.000001:
                cprint(f'В источник {name} не идет вода!!!!', color='red')


#            cprint(name)
#            cprint(f'GG_P={GG_P}, Gin_P={Gin_P}, Gout_P={Gout_P}, Gp_P={Gp_P}')
#            cprint(f'GG_O={GG_O}, Gin_O={Gin_O}, Gout_O={Gout_O}, Gp_O={Gp_O}')

#            3.727272745355732
#32.4675

            Gpodp = Gin_P-Gin_O

            t2_ispr = t2

            if Gin_O != 0:
                t2_ispr *= Gin_P/Gin_O


#            print(f'пришло {Gin_O} t={t2_ispr} ушло {Gin_P} t={t} подпитка {Gpodp}')

            GP = Gin_P
            Q = (Gpodp*(t-ct5) + Gin_O*(t-t2_ispr))*0.001


            G0 += GP
            Q0 += Q
        
            heatSourceID = nP.get('heatSourceID', 0)

#    exit(0)