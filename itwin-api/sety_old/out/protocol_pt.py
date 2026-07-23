import numpy as np
import networkx as nx
import networkx as nx
import itertools

from sety.out.podpitka import n_ras
from sety.any.colors import cprint
from sety import w_print
from sety.out.pt_out import print_bal


def protocol_pt(G):

    G_otoplz0 = 0
    G_otopln0 = 0
    G_ventil0 = 0
    Q_otoplz0 = 0
    Q_otopln0 = 0
    Q_ventil0 = 0

    G_gvop0 = 0
    G_gvoo0 = 0

    G_gvz0 = 0
    Q_gvz0 = 0
    Q_rez0 = 0
    Q_gvop0 = 0
    Q_gvoo0 = 0
    G_rez0 = 0



    for n in G.nodes:
        nP = G.nodes[n]

        num = nP.get('num', -1)
        if num == -1:
            continue

        id = nP['id']
        typ = nP['typ']

        po = nP['po']
        pih = nP.get('P', 0.)
        t = 0
        t2 = 0

        if typ in ('generalizedConsumers', 'realConsumers') and po == 1:      # 
            nO = G.nodes.get((id, 2), None)
            out = nP

            t = nP.get('t', -10000)
            t2 = nO.get('t', -10000)

#            GP, GZ1 = n_ras(G, (id, 1), (id, 2))
#            GO, GZ2 = n_ras(G, (id, 2), (id, 1))


            GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, (id, 1), False)
            GG_O, Gin_O, Gout_O, Gp_O, Gout_O =  n_ras(G, (id, 2), False) 


#            continue

#            if abs(GP) < 1e-8 or abs(GO) < 1e-8:
#                print(nP.get('name', '???'), 'Без нагрузки')
#                continue

            name = w_print.node_name(G, n, False, False) 
#            cprint(name)
#            cprint(f'GG_P={GG_P}, Gin_P={Gin_P}, Gout_P={Gout_P}, Gp_P={Gp_P}, Gout_P={Gout_P}')
#            cprint(f'GG_O={GG_O}, Gin_O={Gin_O}, Gout_O={Gout_O}, Gp_O={Gp_O}, Gout_O={Gout_O}')
#            cprint(f'Gpo = {Gp_P+Gp_O}')


            Qotoplz = nP.get('Qotz', 0)
            Qotopln = nP.get('Qotn', 0)

            Qvent = nP.get('Qvent', 0)
            Qkond = nP.get('Qkond', 0)
            Qgvz = nP.get('Qgvz', 0)
            Qrez = nP.get('Qrez', 0)

            G_otoplz = out.get('G_otoplz', 0)
            G_otopln = out.get('G_otopln', 0)
            G_ventil = out.get('G_ventil', 0)
            G_kondiz = out.get('G_kondiz', 0)
            G_gvz = out.get('G_gvz', 0)
            G_rez = out.get('G_rez', 0)

            G_gvop = out.get('G_gvop', 0)
            G_gvoo = out.get('G_gvoo', 0)

            Qgvop = nP.get('Qgvop', 0)
            Qgvoo = nP.get('Qgvoo', 0)

            G_otoplz0 += G_otoplz
            G_otopln0 += G_otopln
            G_ventil0 += G_ventil
            G_gvz0 += G_gvz
            G_gvop0 += G_gvop
            G_gvoo0 += G_gvoo

            
            Q_otoplz0 += Qotoplz
            Q_otopln0 += Qotopln
            Q_ventil0 += Qvent

            Q_gvop0 += Qgvop
            Q_gvoo0 += Qgvoo

            G_rez0 += G_rez

            Q_gvz0 += Qgvz
            Q_rez0 += Qrez



#    return


    print('\u00A0')
    print('Теплопотребление и тепловые потери')
    print('Потребители')

    print_bal('Отопление, зав. схема', Q_otoplz0, G_otoplz0)
    print_bal('Отопление, незав. схема', Q_otopln0, G_otopln0)
    print_bal('Вентиляция', Q_ventil0, G_ventil0)
    print_bal('ГВ закрытое', Q_gvz0, G_gvz0)
    print_bal('ГВ из подачи', Q_gvop0, G_gvop0)
    print_bal('ГВ из обратки', Q_gvoo0, G_gvoo0)
    print_bal('ГВ рецирк', Q_rez0, G_rez0)

    print('\u00A0')

    Qz = Q_otoplz0 + Q_otopln0 + Q_ventil0 + Q_gvz0
    Gz = G_otoplz0 + G_otopln0 + G_ventil0 + G_gvz0

    print_bal('Всего, закрытые системы', Qz, Gz)
    print_bal('Всего из подачи', Q_gvop0, G_gvop0)
    print_bal('Всего из обратки', Q_gvoo0, G_gvoo0)

    print_bal('Всего', Qz + Q_gvop0 + Q_gvoo0, Gz + G_gvop0 + G_gvoo0)

