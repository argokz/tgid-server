import networkx as nx
import numpy as np
import scipy as sp

import logging

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

number = 0

def check_RD(G, list_rd, root, itr, finish):

    fnl = 0.

    debug0 = False

#    if debug0:
#        print('=================================================================================')

    logging.info(f'== Регуляторы давления')

    for i in range(len(list_rd)):
        nodeID3, przu3, k_l, k_n, i1, i2, n1, n2, key, S, Z, r1, r2, delta, drr, Sold, rdh, rash_old, Z_old = list_rd[i]

        debug = debug0

        name = w_print.node_name(G, (nodeID3, przu3), False, False)

        delr = 0

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


#                if not "фикт пав 13дж-5" in name:
#                if not "5-46" in name:
                if not "4-18 fdhfgjhfgА34534" in name:
                    debug = False


                delr = float((Zhd - Z) / np.power(rash, 2.))

                dr = 0

#                if debug: print(f'Zhd={Zhd} Z={Z} rash={rash} delr={delr} delh={delh} r1={r1} r2={r2}')


                if drr is None:
                    newr = S + abs(delr)
#                    if debug: print(f'!!! newr = {newr} S={S} delr={delr} Zhd={Zhd} Z={Z}')
                else:
                    '''
                    if abs(delr) > drr:
                        delr = drr * np.sign(delr)  # 1.12.09 Убрал комментарии Нужно проверить
                        '''

                    sign1 = np.sign(Zhd - rdh) * np.sign(S - Sold)
                    if sign1 == 0: sign1 = 1

                    dr = delr * sign1
                    newr = S - dr

#                    if debug: print(f'+++ newr = {newr} S={S} delr={dr}')


                Sold = S


#                if newr < 0:
#                    logging.info(f'!!! {name}  newr={newr} S={S}, r1={r1}, r2={r2} ')
                    
                if newr < r1:

#                    if 'У1815006627' in name:
                    logging.info(f'  newr < r1, {newr} < {r1}')
                    
#                    if debug: print(f'  newr ( r1, {newr} ( {r1}')

                    
                    S = r1
                elif newr > r2:

#                    if 'У1815006627' in name:
                    logging.info(f'  newr > r2, {newr} > {r2}')
                    
#                    if debug: print(f'  newr ) r2, {newr} ) {r2}')
                    
                    S = r2
                else:

#                    if 'У1815006627' in name:
                    logging.info(f'  S:=newr, {S} := {newr} dr = {dr} := {delr} * np.sign({Zhd} - {rdh}) * np.sign({S} - {Sold})')

#                    if debug: print(f'  S:=newr, {S} := {newr} dr = {dr} := {delr} * np.sign({Zhd} - {rdh}) * np.sign({S} - {Sold})')
                    

                    S = newr

                drr = abs(delr)

#                if nodeID3 == 1906:
#                    print('Zhd', Zhd, 'rash', rash, 'delh', delh, 'delr', delr, 'dr', dr, 'Zhd', Zhd, 'rdh', rdh, 'newr', newr, 'S', S, 'drr', drr, '!!', (Zhd - rdh)*10e6)

###                if debug: print('Zhd', Zhd, 'rash', rash, 'delh', delh, 'delr', delr, 'dr', dr, 'Zhd', Zhd, 'rdh', rdh, 'newr', newr, 'S', S, 'drr', drr, '!!', (Zhd - rdh)*10e6)


#                if debug: print(f'delr={delr}  hd={Zhd} Z={Z} rash={rash} Snew={S} dr={dr}')


#                print(f'{w_print.node_name(G, (nodeID3, przu3), False)}  {itr:2} S = {S:2.10f} rash = {rash:5f} r1={r1} r2={r2} Z={Z} Z_old={Z_old} Zhd = {Zhd} delh={delh} dr={dr}')

#                if 'У1815006627' in name:
                logging.info(f'{name}  {itr:2} rash = {rash:5f} Z={Z:8.2f} Z_old={Z_old:8.2f} Zhd = {Zhd:8.2f} delh={delh} delr={delr} dr={dr} dP={dP} S = {S} r1={r1} r2={r2}')

            S = S
            rdh = Zhd

            global number


            r1r2 = '<>'
            if S <= r1: r1r2 = 'r1'
            if S >= r2: r1r2 = 'r2'

#            print(debug, name)

#            print(f'{name} {number:>5} {S=:.2E} {delr=:9.2E} {r1r2} {rash=:5f} {Zhd=:8.2f} {Z=:8.2f} dx={Z-Zhd:5.2f} | {r1=:.2E} {r2=:.2E} | ')

            number += 1

        if finish:
            r1 = S
            r2 = S

        list_rd[i] = nodeID3, przu3, k_l, k_n, i1, i2, n1, n2, key, S, Z, r1, r2, delta, drr, Sold, rdh, rash, Zhd


        e = G.edges[n1, n2, key]
        e['S'] = S
#        print(e)


#        if nodeID3 == 37316922:
#            print(nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'delh', delh, 'S', S, 'delr', delr)


#        if nodeID3 == 1906:
#            print('===', Z, nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'r1', r1, 'r2', r2, 'S', S, 'rash', rash)

            
#            print('===', Z, nodeID3, w_print.node_name(G, (nodeID3, przu3), False), 'hd', hd, 'Z', Z, 'delh', delh, 'S', S, 'delr', delr)


#        print(r1, r2, S)
#    exit(1)

#    print(fnl)

    return fnl

