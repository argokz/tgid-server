import networkx as nx


ATMOSPHERE = -99999

def add_atm(G):
    global ATMOSPHERE

    ATMOSPHERE -= 1

    data = {}
    data['typ'] = 'nodes'
    data['id'] = ATMOSPHERE
    data['t'] = 0
    data['p_zn'] = 0
    data['name'] = 'ATMOSPHERE'
    data['nodeName'] = 'ATMOSPHERE'
    data['geoMarkTopTube'] = 0

    G.add_node((ATMOSPHERE, 1), **data, po=1, G=0.)

    return (ATMOSPHERE, 1)

