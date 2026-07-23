import numpy as np
import networkx as nx
import networkx as nx
import itertools

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any.colors import nbsp
from sety.any.colors import cprint
from sety.any import db2
from sety.any.insert2 import Insert
from sety.out.pt_out import print_bal

from sety.out.podpitka import n_ras
from sety.out.protocol_pt import protocol_pt 
from sety.ct import get_ct

#---------------------------------------------------------------------------

def protocol_IS_OUT(G):

    print('Отпущенное тепло')

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
        idP = nP['id']
        idO = nP['id']
        typ = nP['typ']
        t = nP.get('t', -10000)
        t = nP.get('t0', t)

        if np.isnan(t):
            t = -10000;

        t2 = 0



        if typ == 'heatSources' and po == 1:      # 

#            name = w_print.node_name(G, n, False, False) 
            name = w_print.node_name(G, n, False, True) 

            
            idP = nP.get('n1', idP) 
            idO = nP.get('n2', idO) 

            nO = G.nodes.get((idO, 2), None)


            if not nO is None:
                t2 = nO.get('t', -10000)
                t2 = nO.get('t0', t2)
            else:
                t2 = 0
            

#            print('!!!!!!', name, idP, idO, nP)

            GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, (idP, 1), False)
            GG_O, Gin_O, Gout_O, Gp_O, Gout_O =  n_ras(G, (idO, 2), False) 


#            if idP == idO:
#                print(f"============>>> {t=} {t2=}")
#                print(f'{GG_P=}, {Gin_P=}, {Gout_P=}, {Gp_P=}, {Gout_P=}')
#                print(f'{GG_O=}, {Gin_O=}, {Gout_O=}, {Gp_O=}, {Gout_O=}')




            if abs(Gin_P) < 0.000001:
                continue


#            cprint(name)
#            cprint(f'GG_P={GG_P}, Gin_P={Gin_P}, Gout_P={Gout_P}, Gp_P={Gp_P}')
#            cprint(f'GG_O={GG_O}, Gin_O={Gin_O}, Gout_O={Gout_O}, Gp_O={Gp_O}')

#            3.727272745355732
#32.4675

            Gpodp = Gin_P-Gin_O

            t2_ispr = t2

            if Gin_O != 0:
                t2_ispr *= Gin_P/Gin_O


#            print(t2, t2_ispr)

#            print(f'пришло {Gin_O} t={t2_ispr} ушло {Gin_P} t={t} подпитка {Gpodp}')

            GP = Gin_P
            Q = (Gpodp*(t-ct5) + Gin_O*(t-t2_ispr))*0.001



            print_bal(f'Источник {name}', Q, GP)
            G0 += GP
            Q0 += Q
        
            heatSourceID = nP.get('heatSourceID', 0)
    print_bal(f'Всего', Q0, None)


#---------------------------------------------------------------------------


#---------------------------------------------------------------------------


def protocol_podpitka(G, podpitka):

    first = True

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

        if np.isnan(t):
            t = -10000;

        t2 = 0

        GG_all = 0

        # Подпитка
        GG, Gin, Gout, Gp, Gout_P = n_ras(G, n, False)

#        name = w_print.node_name(G, n, False, False) 
#        cprint(f'{name} GG={GG}, Gin={Gin}, Gout={Gout}, Gp={Gp}, Gout={Gout}')

        if abs(GG) > 0.000001 and abs(Gin) > 0.000001: # and Gin > 0 and Gout < 0:
            t = -t*Gout/Gin
#            name = w_print.node_name(G, n, False, False) 
            name = w_print.node_name(G, n, False, True) 

            if podpitka:
                GG = -GG

            if GG > 0:
                if first:
                    firrst = False
#                    print('\u00A0')
#                    if podpitka:    
#                        print(f'Подпитка')
#                    else:
#                        print(f'Водоразбор')
                
#                name = w_print.node_name(G, n, False, False) 
                name = w_print.node_name(G, n, False, True) 
#                print_bal(f'{name}', 0, GG)
                GG_all = GG

#        print_bal('Всего', 0, GG_all)
 
#        heatSourceID = nn.get('heatSourceID', 0)
    


#---------------------------------------------------------------------------

def protocol_ut(G):

    print('\u00A0')
    print('Тепловые потери')
    print('Участки\n')

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

        if typ == 'heatPipeSections':      # Участки
            heatSourceID = e.get('heatSourceID', 0)

            norma = e.get('norma', 0)
            y = e.get('y', 0)

            if po == 1:
                yP += y
            else:
                yO += y

    print_bal('Тепловые потери, подающий теплопровод', yP, 0)
    print_bal('Тепловые потери, обратный теплопровод', yO, 0)



#---------------------------------------------------------------------------


def out_teplo(G):
    cprint('===========================================================', color='red')
    cprint(nbsp('****  информация по тепловому и материальному балансу  ****'))
    cprint(nbsp('                                                         Нагрузка   Расход'))
    cprint(nbsp('                                                          Гкал/ч     т/ч'))


    protocol_IS_OUT(G)
    protocol_podpitka(G, True)
    protocol_podpitka(G, False)
    protocol_pt(G)
    protocol_ut(G)
    