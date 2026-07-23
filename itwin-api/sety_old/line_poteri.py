import numpy as np
import scipy as sp
import networkx as nx
import math
import itertools
from sety import config

#-----------------------------------------------------------------------------------

def getLinePoteri(G, n):

#    if (!getGlobal()->is_ZULU) return 0;

    p = 0

    for k, (n1, n2, key) in itertools.chain(
            zip(itertools.repeat(1), G.in_edges(n, keys=True)),
            zip(itertools.repeat(2), G.out_edges(n, keys=True))
            ): 

        l = G.edges[n1, n2, key]

        l_typ = l['typ']

        if l_typ == 'heatPipeSections':
            p += l.get('dlina', 0) * math.pow(l.get('diametr', 0) / 1000, 2) * math.pi / 4

    return p * 0.25 * 0.01 / 2;



def line_poteri(G):
    if not config.args.is_ZULU:
        return
    
    max_pot = 0

    for n in G.nodes:
        pot = getLinePoteri(G, n)

        if pot > max_pot:   # для отладки
            max_pot = pot;
            pot = getLinePoteri(G, n)
        
        nP = G.nodes.get(n, None)

        GG = nP.get('G', 0)
        GP = nP.get('Gout', 0)

        nP['G'] = GG + pot
        nP['Gout'] = GP + pot
        nP['utechka'] = pot

