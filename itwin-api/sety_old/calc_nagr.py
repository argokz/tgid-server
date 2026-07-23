import numpy as np
import scipy as sp
import networkx as nx
import itertools

from sety import w_print
from sety import config

def init_matrix_nagr(G, x, b101):

#    nn = 100000

    n_nodes = G.number_of_nodes()

    nn = n_nodes

    beta0 = np.zeros(n_nodes + 1)

    matrix = sp.sparse.lil_array((n_nodes + 1, n_nodes + 1))

#    print('==========', b101)

    ii = 0

    for n in G.nodes:
        name = w_print.node_name(G, n, False)

        node = G.nodes[n]
        nn, po = n

        k_n = G.nodes[n]['num']

        typ = node['typ']

        Q = 0

#        print(name)

        if typ in ('generalizedConsumers', 'realConsumers'):

                
            nodeP = node
            
#            if po == 2:
            nodeP = G.nodes.get((nn, 1), None)

            Qot =   0
            Qgvz =  0
            Qgvp =  0
            Qgvo =  0
            Qvent = 0
            
            if not nodeP is None:
                Qot =   nodeP.get('Qot', 0)
                Qgvz =  nodeP.get('Qgvz', 0)
                Qgvp =  nodeP.get('Qgvp', 0)
                Qgvo =  nodeP.get('Qgvo', 0)
                Qvent = nodeP.get('Qvent', 0)

            Q = Qot + Qgvz + Qgvp + Qgvo + Qvent

#            print(f'{Q} = {Qot} + {Qgvz} + {Qgvp} + {Qgvo} + {Qvent}')

            if b101 == 'b101':
                Q = Q
            elif b101 == 'b102':
                Q = Qot
            elif b101 == 'b103':
                Q = Qvent
            elif b101 == 'b104':
                Q = Qgvz

            if po == 2:
                Q = -Q

        zn = False
        if node.get('p_zn', None):
            zn = True

#        print(k_n, name, Q)
        beta0[k_n] = Q

#        print('(((((((((((((((((((((((((')

        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 


            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            k_l = l['num']
            GG = x[k_l]


            name1 = w_print.node_name(G, n1, False)
            name2 = w_print.node_name(G, n2, False)

#            print('.........', k, po, GG, name1, name2)
            if k == 2:
                GG = -GG
                n1, n2 = n2, n1

            if GG > 0 and po == 1 or GG < 0 and po == 2:
                n0 = n2
            else:
                n0 = n1

#            n0 = n2

            name0 = w_print.node_name(G, n0, False)


            sign = 1 if GG > 0 else -1

#            if po == 1 or po == 1:
#                print('>>>>>>>>>>>>>>>', sign, po, GG, name1, name2, ' == ', name0)

            if abs(GG) > 0.00001: yes = True

            if po == 2:
                sign = -sign

            i1 = G.nodes[n0]['num']

            l['i1'] = i1

#            print('--->>>>', nnode1['name'], sign)

#            print('!!!', matrix[ii, i1])

            if matrix[ii, i1] == 0:
                matrix[ii, i1] = sign
            else:
                matrix[ii, i1] += sign

#            print(f'n0={G.nodes.get(n0).get('name')}')
#            print(f'matrix[{ii}, {i1}] = {matrix[ii, i1]}')

            if zn:
                matrix[ii, n_nodes] = 1
                
#        print(')))))))))))))))))')
        ii += 1

    matrix[n_nodes, 0] = 1
    ii += 1


    diag = matrix.diagonal()

    eps = 0.00000000001

    for i in range(ii):
        if diag[i] == 0:
            matrix[i, i] = eps

    matrix = sp.sparse.csc_array(matrix)

#    print(ii, n_nodes)
#    w_print.print_matrix(matrix, beta0)

    return matrix, beta0


def calc_nagr1(G, x, b101):
        
        matrix, beta = init_matrix_nagr(G, x, b101)

        t = sp.sparse.linalg.spsolve(matrix, beta)

#        for tt in t:
#            print(tt, end=',')

        ii = 0
        n_nodes = G.number_of_nodes()

        for n in G.nodes:

#            print(n, G.nodes[n].get('name'))
            for k, (n1, n2, key) in itertools.chain(
                    zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                    zip(itertools.repeat(2), G.out_edges(n, keys=True))
                    ): 

                l = G.edges[n1, n2, key]

                l_typ = l['typ']

                k_l = l['num']
                i1 = l['i1']

                if abs(t[i1]) < 10000:
#                    print(f't[i1] = {t[i1]}')
                    l[b101] = abs(t[i1])
                    
            ii += 1
        


def calc_nagr(G, x):
    if not config.args.g_is_avar:   # плановый расчет
        calc_nagr1(G, x, 'b101')
        calc_nagr1(G, x, 'b102')
        calc_nagr1(G, x, 'b103')
        calc_nagr1(G, x, 'b104')
