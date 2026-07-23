import networkx as nx
import numpy as np
import scipy as sp

from sety import w_print

# Обработка регуляторов давления

#------------------------------------------------------

def fntnl(hmin: float, hmax: float, hd: float) -> float:
# вычисление функционала 
    if hd < hmin: return hmin - hd

    if hd > hmax: return hd - hmax

    return 0.

#------------------------------------------------------
'''
def check_RD(G):

    fnl = 0.
    
    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]
        num = e['num']
        typ = e['typ']

        if typ == 'pressRegulators':
            nodeID = e.get('nodeID', -1)
            przu = e.get('przu', 1)
            node = G.nodes.get((nodeID, przu), None)
            if node is None: continue

            name = node.get('name', 0.)
            k_reg = e['num']

            r1 = e['r1']
            r2 = e['r2']

            if r1 != r2:
                Z = e['Z']
                S = e['S']

                hd = node['out']

                delta = e.get('delta', 0.1)

                hmin = Z - delta
                hmax = Z + delta
                delh = fntnl(hmin, hmax, hd)

                delr = 0
                dr = 0

                rash = abs(e['out'])

                if delh > 1.e-6 and rash > 1.e-6:
                    fnl += delh

                    print(hd, Z)

                    delr = (hd - Z) / np.power(rash, 2.)

                    drr = e.get('drr', None)

                    if drr is None:
                        newr = S + abs(delr)
                    else:
                        ds = e['drr']
                        if abs(delr) > ds:
                            delr = ds * np.sign(delr)  # 1.12.09 Убрал комментарии Нужно проверить

                        dr = delr * np.sign(hd - e['rdh']) * np.sign(S - e['rdr'])
                        newr = S - dr

                    e['rdr'] = S

                    if newr < r1:
                        S = r1
                    elif newr > r2:
                        S = r2
                    else:
                        S = newr

                    e['drr'] = abs(delr)

                e['S'] = S
                e['rdh'] = hd

            name = w_print.line_name_n1_n2(G, n1, n2)
#            print(f'Регулятор [{name}]')

    return fnl
'''

#------------------------------------------------------

def check_RD(G, list_rd, root, itr):

    fnl = 0.

    debug = False

#    if debug:
#        print('=================================================================================')

    for i in range(len(list_rd)):
        nodeID3, przu3, k_l, k_n, i1, i2, S, Z, r1, r2, delta, drr, rdr, rdh, rash_old, Z_old = list_rd[i]

        Zhd = Z_old
        rash = rash_old

        k_reg = k_l                      # e['num']

        if r1 != r2:
            Zhd = root[k_n]   #node['out']

            P1 = root[i1]   # Давление
            P2 = root[i2]
            dP = P1-P2

            hmin = Z - delta
            hmax = Z + delta
            delh = fntnl(hmin, hmax, Zhd)

            delh = abs(Z-Zhd)

            delr = 0
            dr = 0

            rash = abs(root[k_l])  # abs(e['out'])

#            if delh > 1.e-6 and rash > 1.e-6:
            if rash > 1.e-6 and delh > delta:
                if delh > delta:
                    fnl += delh

                rash1 = rash_old
                if rash1 == 0:
                    rash1 = rash
                rash1 = rash

#                S1-S2 = (dP1*G2**2 - dP2*G1**2)/((G1**2)*(G2**2))


                delr = (Zhd - Z) / np.power(rash, 2.)

                if drr is None:
                    newr = S + abs(delr)
                else:
                    '''
                    if abs(delr) > drr:
                        delr = drr * np.sign(delr)  # 1.12.09 Убрал комментарии Нужно проверить
#                        '''

                    dr = delr * np.sign(Zhd - rdh) * np.sign(S - rdr)
                    newr = S - dr


                rdr = S


                if newr < r1:
                    S = r1
                elif newr > r2:
                    S = r2
                else:
                    S = newr

                drr = abs(delr)

#                if nodeID3 == 1906:
#                    print('Zhd', Zhd, 'rash', rash, 'delh', delh, 'delr', delr, 'dr', dr, 'Zhd', Zhd, 'rdh', rdh, 'newr', newr, 'S', S, 'drr', drr, '!!', (Zhd - rdh)*10e6)

#                if debug:
#                    print('Zhd', Zhd, 'rash', rash, 'delh', delh, 'delr', delr, 'dr', dr, 'Zhd', Zhd, 'rdh', rdh, 'newr', newr, 'S', S, 'drr', drr, '!!', (Zhd - rdh)*10e6)

#                print(f'{w_print.node_name(G, (nodeID3, przu3), False)}  {itr:2} S = {S:2.10f} rash = {rash:5f} r1={r1} r2={r2} Z={Z} Z_old={Z_old} Zhd = {Zhd} delh={delh} dr={dr}')
#                print(f'{w_print.node_name(G, (nodeID3, przu3), False)}  {itr:2} S = {S:5f} rash = {rash:5f} Z={Z:8.2f} Z_old={Z_old:8.2f} Zhd = {Zhd:8.2f} delh={delh} dr={dr} dP={dP}')

            S = S
            rdh = Zhd

        list_rd[i] = nodeID3, przu3, k_l, k_n, i1, i2, S, Z, r1, r2, delta, drr, rdr, rdh, rash, Zhd

#        if nodeID3 == 37316922:
#            print(nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'delh', delh, 'S', S, 'delr', delr)


#        if nodeID3 == 1906:
#            print('===', Z, nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'r1', r1, 'r2', r2, 'S', S, 'rash', rash)

            
#            print('===', Z, nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'delh', delh, 'S', S, 'delr', delr)


#        print(r1, r2, S)
#    exit(0)

#    print(fnl)

    return fnl

