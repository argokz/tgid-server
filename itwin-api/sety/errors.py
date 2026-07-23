from sety import w_print
from sety.any.colors import cprint


#------------------------------------------------------

def find_type(G, typ):
    for n in G.nodes:
        t = G.nodes[n].get('typ', None)
        if t == typ:
            return n

    return None

#------------------------------------------------------

def error_1234(G, nP):
    id, fragment, parent, kod, name, po = w_print.node_names(G, nP)

    n_ist = find_type(G, 'heatSources')

    cprint(f'Ошибка во фрагменте {fragment}', color='red')

    if not n_ist is None:
        cprint(f'Вода не течет через источник {w_print.node_name(G, n_ist, False)}', color='red')
#    exit(1)
    
    