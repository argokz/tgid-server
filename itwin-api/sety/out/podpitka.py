import numpy as np
import networkx as nx
import networkx as nx
import itertools

# Считает расходы в узде

def n_ras(G, n, debug):
    nP = G.nodes.get(n)

    if nP is None:
        return 0, 0, 0, 0, 0

    nn, po = n

    pt_name = nP.get('name', '???')

    if debug:
        print('-----------------')
        print(n, pt_name)

    GGG = 0

    Gin = 0
    Gout = 0


    if debug:
        print('n=', n)


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
    Gout = nP.get('Gout', 0)

    if Gp != 0:
        if debug:
            print('........', Gp, 'pt')
        GGG -= Gp


    if debug:
        print('........', GGG, 'итого')

#    G_in входит
#    G_out выходит
#    GGG подпитка
#    Gp между подачей и обраткой

    return GGG, Gin, Gout, Gp, Gout

