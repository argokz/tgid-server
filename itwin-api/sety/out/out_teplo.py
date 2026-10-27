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

# вставлено Claude, 2026-10-24: баланс источника по ребрам, пересекающим его границу (узлы источника
# nodes - подача и, если есть, обратка; ребра между ними, например насос, внутренние).
# Вытекающий поток уносит температуру узла источника (заданную t0), втекающий приносит температуру
# узла, откуда пришел; разница расходов - подпитка с температурой холодной воды tx.
# Q = (Σ Gвых*tвых - Σ Gвх*tвх - (Σ Gвых - Σ Gвх)*tx) / 1000, Гкал/ч.
# Возвращает (расход, вытекающий из узла подачи, Q).
def ist_balans(G, nodes, tx):
    nodes = {x for x in nodes if x in G.nodes}

    # [Claude 2026-10-24] Температура узла: заданная t0 (источник), иначе расчетная t; nan/нет - 0.
    def node_t(x):
        nd = G.nodes[x]
        t = nd.get('t0', nd.get('t', 0))
        return 0 if t is None or np.isnan(t) else t

    G_out = 0
    G_in = 0
    G_P = 0   # отпуск в подающий теплопровод (транзит через обратку источника не учитывается)
    H = 0

    for x in nodes:
        for a, b, key in itertools.chain(G.out_edges(x, keys=True), G.in_edges(x, keys=True)):
            if a in nodes and b in nodes:
                continue

            GG = G.edges[a, b, key].get('G', 0)

            # поток GG идет a -> b; при GG < 0 - обратно
            src, dst = (a, b) if GG > 0 else (b, a)
            GG = abs(GG)

            if src in nodes:
                G_out += GG
                H += GG * node_t(src)
                if src[1] == 1:
                    G_P += GG
            else:
                G_in += GG
                H -= GG * node_t(src)

    Q = (H - (G_out - G_in) * tx) * 0.001

    return G_P, Q

#---------------------------------------------------------------------------

# [Claude 2026-10-18] Протокол отпущенного тепла: по каждому источнику считает расход и тепло (с учетом подпитки) и печатает баланс.
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

            # исправлено Claude, 2026-10-24: тепло источника по потокам через его границу. Было - по паре узлов
            # (id, 1)/(id, 2): у источника из одного узла (обратка входит прямо в узел подачи) узла (id, 2) нет,
            # t2 бралась 0, весь расход считался подпиткой и тепло завышалось примерно вдвое.
            GP, Q = ist_balans(G, {n, (idP, 1), (idO, 2), (nP['id'], 2)}, ct5)

            if abs(GP) < 0.000001:
                continue

            # вставлено Claude, 2026-10-25: нет температуры (тепловой расчет сети не делался) - тепло не считаем,
            # иначе остается только подпитка * tx со знаком минус
            if t <= -10000:
                Q = 0



            print_bal(f'Источник {name}', Q, GP)
            G0 += GP
            Q0 += Q
        
            heatSourceID = nP.get('heatSourceID', 0)
    print_bal(f'Всего', Q0, None)


#---------------------------------------------------------------------------


#---------------------------------------------------------------------------


# [Claude 2026-10-18] Поиск узлов с подпиткой (podpitka=True) или водоразбором. Сейчас вся печать закомментирована - результата нет.
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

# [Claude 2026-10-18] Протокол тепловых потерь: суммы потерь по подающим и обратным участкам теплопроводов.
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


# [Claude 2026-10-18] Печать информации по тепловому и материальному балансу: источники, подпитка, потребители, тепловые потери.
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
    