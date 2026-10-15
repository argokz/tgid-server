import numpy as np
import scipy as sp
import networkx as nx
import itertools

import logging
import traceback


from collections import defaultdict

from sety.any.colors import cprint
from sety import w_print
from sety import config


#------------------------------------------------

def getQ(G, n, b101):
#    n_nodes = G.number_of_nodes()

    node = G.nodes[n]
    nn, po = n

    Q = 0
    typ = node['typ']


    if typ in ('generalizedConsumers', 'realConsumers'):

#        print(typ, name)
#        if typ != 'generalizedConsumers':
#            print(typ)
#            exit(1)

        nn, po = n
    
        nodeP = node
        
#        if po == 2:
        nodeP = G.nodes.get((nn, 1), None)

        Qot =   0
        Qgvz =  0
        Qgvp =  0
        Qgvo =  0
        Qvent = 0
        
        if not nodeP is None:
            Qot =   nodeP.get('Qot0', 0)
            Qgvz =  nodeP.get('Qgvz0', 0)
            Qgvp =  nodeP.get('Qgvp0', 0)
            Qgvo =  nodeP.get('Qgvo0', 0)
            Qvent = nodeP.get('Qvent0', 0)

        Q = Qot + Qgvz + Qgvp + Qgvo + Qvent

#        print(f'{Q} = {Qot} + {Qgvz} + {Qgvp} + {Qgvo} + {Qvent}')

        if b101 == 'b101':
            Q = Q
        elif b101 == 'b102':
            Q = Qot
        elif b101 == 'b103':
            Q = Qvent
        elif b101 == 'b104':
            Q = Qgvz

#            if po == 1:
#                Q += Qgvp

        elif b101 == 'b105':
            Q = Qgvp

        elif b101 == 'b106':
            Q = Qgvo

        if po == 2:
            Q = -Q

    return Q

#------------------------------------------------

from itertools import combinations

def get_pairs(d):
    # все пары ключей
    pairs = list(combinations(d.keys(), 2))

    # превращаем в словари
    result = [{k: d[k] for k in pair} for pair in pairs]

    return result

#    for item in result:
#        print(item)

def get_from_item(result):
    item1 = None
    item2 = None
    for i, item in enumerate(result.items()):
        if i == 0:
            item1 = item
        else:
            item2 = item
            
    return item1, item2



def init_matrix_nagr(G, x, b101):
    """Матрица распределения нагрузок по участкам и правая часть для вида нагрузки b101.

    Матрица от вида нагрузки не зависит, меняется только правая часть: b101 может быть списком
    видов — тогда возвращается {вид: правая часть} для одного разложения матрицы на все виды.
    """
    keys = (b101,) if isinstance(b101, str) else tuple(b101)

#    nn = 100000
    n_nodes = G.number_of_nodes()
    n_lines = G.number_of_edges()

    n_ist = 0
#    n_ist += 1

    n_ist0 = 0

    set_ist = set()
    set_zero = set()

    for n in G.nodes:
        node = G.nodes[n]
        nn, po = n

        if node.get('t0', None):
            if not nn in set_ist :
                n_ist += 1
                set_ist.add(nn)

    set_ist = set()

    betas = {k: np.zeros(n_lines + n_ist) for k in keys}
    beta0 = betas[keys[0]]
    matrix = sp.sparse.lil_array((n_lines + n_ist, n_lines + n_ist))

#    print(f'{n_lines=} {n_nodes=} {n_ist=}')

    ii = 0

    for n in G.nodes:
        node = G.nodes[n]
        nn, po = n

        k_n = G.nodes[n]['num']
        typ = node['typ']

        zn = False
        if node.get('p_zn', None):
            zn = True

        t0 = False
        if node.get('t0', None):
            t0 = True

        if ii >= n_lines + n_ist:
            break

#        beta0[k_n] = Q
        for k in keys:
            betas[k][ii] = getQ(G, n, k)

#        print('(((((((((((((((((((((((((')

        Gin = defaultdict(float)
        Gout = defaultdict(float)

        GG_P = 0
        GG_O = 0
        n_P = 0
        n_O = 0

#        print('-------------------')
#        print(name, f'{Q=:.1f}')

        lst_G = []

        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 


            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            k_l = l['num']
            GG = x[k_l]

#            print('.........', k, po, GG, name1, name2)
            if k == 2:
                GG = -GG
                n1, n2 = n2, n1

            if GG > 0 and po == 1 or GG < 0 and po == 2:
                n0 = n2
            else:
                n0 = n1

#            n0 = n2

            sign = 1 if GG > 0 else -1

#            if po == 1 or po == 1:
#                print('>>>>>>>>>>>>>>>', sign, po, GG, name1, name2, ' == ', name0)

#            if 'рег1' in name:
#                print(name, name0, po, GG)

            if abs(GG) > 0.00001: yes = True

            if po == 2:
                sign = -sign

#            i1 = G.nodes[n0]['num']
            i1 = k_l - n_nodes

            l['i1'] = i1

            if abs(GG) < 0.00001: 
                matrix[ii, i1] = 1
                continue

            if matrix[ii, i1] == 0:
                matrix[ii, i1] = sign
            else:
                matrix[ii, i1] += sign

#            print(f'{matrix[ii, i1]=:.0f} {ii=} {i1=} {GG=:.2f} {sign=}')

            lst_G.append(GG)

            if sign > 0: 
                n_P += 1
                GG_P += GG
                Gout[i1] = GG

            if sign < 0: 
                n_O += 1
                GG_O -= GG
                Gin[i1] = GG

#            if zn:
            if t0:   # Источник
                if not nn in set_ist :
                    n_ist0 += 1
                    matrix[ii, n_lines - 1 + n_ist0] = 1
#                    print(f'{name}, {n_ist0=}')
                    set_ist.add(nn)

        ii += 1

        if n_P > 1:
#            print('>>>>>>>>>>>P', ii)
            result = get_pairs(Gout)

#            print('(((', name, n_P, lst_G)

            for i, item in enumerate(result):
                item1, item2 = get_from_item(item)

                matrix[ii, item1[0]] = item2[1]
                matrix[ii, item2[0]] = -item1[1]
 
                beta0[ii] = 0
                ii += 1

        if n_O > 1 and False:
#            print('>>>>>>>>>>>O', ii)
            result = get_pairs(Gin)
            for i, item in enumerate(result):
                item1, item2 = get_from_item(item)

                matrix[ii, item1[0]] = 1
                matrix[ii, item2[0]] = -1

                beta0[ii] = 0
                ii += 1
            



        # Тут добавляем все сходящиеся

#        if n_P > 1:
#            print(f'{name} {k=} {n_P=} {GG_P=:.2f}')
#            print(map_P)

#        matrix[ii, ] = 



#    matrix[n_nodes, 0] = 1
#    ii += 1

#    print(f'=== {n_nodes=} {n_lines=} {ii=}')
#    exit(-1)

#    w_print.print_matrix(matrix, beta0)
#    exit(1)


    diag = matrix.diagonal()

    eps = 0.00000000001

    for i in range(ii):
        if diag[i] == 0:
            matrix[i, i] = eps



    matrix = sp.sparse.csc_array(matrix)

#    print(ii, n_nodes)
#    w_print.print_matrix(matrix, beta0)

    if isinstance(b101, str):
        return matrix, beta0
    return matrix, betas


error345 = False

NAGR_KEYS = ('b101', 'b102', 'b103', 'b104', 'b105', 'b106')


def _nagr_error():
    global error345
    if not error345:
        error345 = True
        cprint('Ошибка при расчете нагрузок по участкам', color='red')


def _set_nagr(G, t, b101):
    """Нагрузка вида b101 на участки из решения t."""
    for n in G.nodes:
        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ):
            l = G.edges[n1, n2, key]
            i1 = l.get('i1', -1)
            if i1 >= 0 and abs(t[i1]) < 10000:
                l[b101] = abs(t[i1])


def calc_nagr1(G, x, b101):
    try:
        matrix, beta = init_matrix_nagr(G, x, b101)
        t = sp.sparse.linalg.spsolve(matrix, beta)
        _set_nagr(G, t, b101)
    except Exception:
        _nagr_error()


def calc_nagr_all(G, x, keys=NAGR_KEYS):
    """Все виды нагрузки одним разложением матрицы (матрица у видов общая, различаются правые части).

    Тот же порядок столбцов COLAMD, что у spsolve, поэтому результат тот же, а разложение — одно
    вместо шести (на сети в 20 тыс. узлов — минуты). Вырожденная матрица: spsolve по каждому виду,
    как раньше (предупреждение и NaN вместо исключения).
    """
    try:
        matrix, betas = init_matrix_nagr(G, x, keys)
    except Exception:
        _nagr_error()
        return
    try:
        solve = sp.sparse.linalg.splu(matrix, permc_spec='COLAMD').solve
    except RuntimeError:
        solve = lambda beta: sp.sparse.linalg.spsolve(matrix, beta)
    for key in keys:
        try:
            _set_nagr(G, solve(betas[key]), key)
        except Exception:
            _nagr_error()


def calc_nagr(G, x):
#    return
    if not config.args.g_is_avar:   # плановый расчет
        calc_nagr_all(G, x)
