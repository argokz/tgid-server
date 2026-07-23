import sys
import time
import networkx as nx
import numpy as np
import scipy as sp

from collections import defaultdict

#from scipy.sparse.linalg import spsolve

from sety import config

from sety.any.colors import cprint

from sety import w_rd
from sety import w_rr
from sety import w_ok

from sety.errors import error_1234

from sety.teplo.teplo import calc_teplo
from sety.calc_nagr import calc_nagr

from sety import w_print
from sety import w_out
from sety import g2
from sety.ct import get_ct

from sety import consumption

from sety.out.pt_out import n_ras
from sety.sopr_ut import reset_sopr

eps = 0.00000000001



#------------------------------------------------------
# Смотрим если истосник отключен на подаче или обратке

def reset_consumptions_PO(G, root):
#    return True

    yes = True

    for n in G.nodes:
        id, po = n

        nP = G.nodes[n]
        
        typ = nP['typ']

        if typ in ('generalizedConsumers', 'realConsumers'):
            numP = nP['num']
            pr = nP
            
            nP = G.nodes.get((id, 1), None)
            nO = G.nodes.get((id, 2), None)

            if nP is None and not nO is None:
                nO['G'] = 0
                nO['Gout'] = 0
                yes = False

            if nO is None and not nP is None:
                nP['G'] = 0
                nP['Gout'] = 0
                yes = False

    return yes

#------------------------------------------------------
# Пересчитываем источники


def reset_consumptions(G, beta0):
#    print('Начали пересчитывать потребители')

    for n in G.nodes:
        id, po = n

        nP = G.nodes[n]
        
        typ = nP['typ']
#        po = nP['po']

        if typ in ('generalizedConsumers', 'realConsumers') and po == 1:
            numP = nP['num']
            
#@            id = nP['nodeID']

            nP = G.nodes.get((id, 1), None)
            nO = G.nodes.get((id, 2), None)

            if nO is None:  
                error_1234(G, (id, 1))
                return

#                exit(0)
#            else:
#                print('OK', nO)

            numO = nO['num']

            pr = nP

            externalNodeName = pr.get('name', '')
            externalCodeID = pr.get('externalCodeID', 0)

            if typ == 'generalizedConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out = consumption.consumption_po(G, pr, externalCodeID, externalNodeName)

            if typ == 'realConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out = consumption.consumption_pr(G, pr, externalCodeID, externalNodeName, True)

#            print(GZ, GP, GO, Qz, Qp, Qo, pr_out)

            beta0[numP] = GZ+GP
            beta0[numO] = -GZ+GO


            nP['G'] = GZ+GP
            nO['G'] = -GZ+GO

            nP['Gout'] = GP
            nO['Gout'] = GO

            if pr_out: nP |= pr_out
            
#            print(beta0[numP], beta0[numO], nP, nO)
#            exit(0)
#    print('Закончили пересчитывать потребители')


#------------------------------------------------------

def set_G_num(G):
    num = 0

    for n in G.nodes:
        G.nodes[n]['num'] = num
        num += 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        G.edges[n1, n2, key]['num'] = num
        num += 1

    return num

#------------------------------------------------------

def init_root(G):
    num = 0

    n_n = G.number_of_nodes()
    n_l = G.number_of_edges()

    n_zn = 0

    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            n_zn += 1

    root = np.full(n_n + n_l + n_zn, 0.)

    for n in G.nodes:
        geodez = G.nodes[n].get('geoMarkTopTube', 0)
        root[num] = geodez
        num += 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        G.edges[n1, n2, key]['num'] = num
        root[num] = 0
        num += 1

    root[num] = 0

    return root, n_n, n_l, n_zn

#------------------------------------------------------

def get_delta(b):
    delta = 0
    for i in range(len(b)): 
        delta += abs(b[i])

    return delta

#------------------------------------------------------

def get_delta_max(b):
    delta = 0
    for i in range(len(b)): 
        if abs(b[i]) > delta:
            delta = abs(b[i])

    return delta
#------------------------------------------------------

def init_matrix(G, x, n_n, n_l, n_zn):
#    n_n = G.number_of_nodes()
#    n_l = G.number_of_edges()

#    nn = n_n + n_l + 1

    nn = n_n + n_l + n_zn

    t0 = time.time()

    beta0 = np.zeros(nn)
    
    list_n = list()
    list_l = list()
    list_zd = list()  # Узлы с заданным напором
    list_rd = list()  # Регулятор давления
    list_rr = list()  # Регулятор расхода
    list_ok = list()  # Обратный клапан

    # Первый закон Кирхгофа

    t1 = time.time()

    for n in G.nodes:
        k_n = G.nodes[n]['num']
        g = G.nodes[n].get('G', 0.)

        beta0[k_n] = g

        for n1, n2, key in G.in_edges(n, keys=True):
            k_l = G.edges[n1, n2, key]['num']
            napr = 1
            list_n.append((k_n, k_l, napr))

        for n1, n2, key in G.out_edges(n, keys=True):
            k_l = G.edges[n1, n2, key]['num']
            napr = -1
            list_n.append((k_n, k_l, napr))

    t2 = time.time()

    # Второй закон Кирхгофа

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
#        print('>>', n1, n2, key, orient, flush=True)

        e = G.edges[n1, n2, key]
        k_l = e['num']
        typ = e['typ']
        nodeID3 = e.get('nodeID', 0)

        i1 = G.nodes[n1]['num']
        i2 = G.nodes[n2]['num']

        param = ()

        if typ == 'pumps':
            h = e.get('h', 0.)
            r1 = 0.
            r2 = 0.

            if h == 0:
                h = e.get('r0', 0.)
                r1 = e.get('r1', 0.)
                r2 = e.get('r2', 0.)

            beta0[k_l] = -h

            param = (h, r1, r2)

        elif typ == 'regulArmatures':  # Регулирующая арматура (ZD2)
#            h = e.get('h', 0.)
            r1 = e.get('r1', 0.)
            param = (r1,)
#            beta0[i] = -((x[n1] - x[n2]) - r1 * sign(x[nl])) * 100000;
#            beta0[k_l] = h


        elif typ == 'reverseValves':  # Обратный клапан
            is_open = True
            list_ok.append((k_l, n1, n2, is_open))
            param = (len(list_ok)-1, )
            beta0[k_l] = 0

        else:
            '''
            if not typ in  (
                            'dampers',
                            'diaphragms',
                            'pressDropRegulators',
                            'regulArmatures',
                            ):
                    print(typ, flush=True)
                    '''

            S = e['S']
            if S == 0: S = 0.0000001

            param = (typ, S, None)

            if typ == 'pressRegulators' or (typ == 'bypass' and nodeID3 > 0):       # RD
                przu3 = e.get('przu', 1)
                nodeID3 = e.get('nodeID', -1)
                r1 = e['r1']
                r2 = e['r2']
                delta = e['delta']
                node3 = G.nodes.get((nodeID3, przu3), None)
                if node3:
                    geodez = node3.get('geoMarkTopTube', 0)
                    Z = e['Z']+geodez

                    k_n = node3['num']
                    list_rd.append((nodeID3, przu3, k_l, k_n, i1, i2, S, Z, r1, r2, delta, None, None, 0, 0, 0))

                    param = ('d', S, len(list_rd)-1)

            elif typ == 'consumptRegulators' or (typ == 'bypass' and nodeID3 <= 0):   # RR
                Z = e.get('Z', 0)
                r1 = e['r1']
                r2 = e['r2']

#                list_rr.append((n1, n2, i1, i2, k_l, S, Z, r1, r2))
#                param = ('r', S, len(list_rr)-1)
                
                if r1 != r2:
                    name = w_print.line_name_n1_n2(G, n1, n2)
                    print(name, Z, r1, r2, flush=True)

                    list_rr.append((n1, n2, i1, i2, k_l, S, Z, r1, r2, key))

                    param = ('r', S, len(list_rr)-1)

        list_l.append((n1, n2, key, i1, i2, k_l, typ, param))


    t3 = time.time()

# Узлы с заданным напором

    n_zn1 = None
    nn1 = n_n + n_l + 1

    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if p_zn is not None:
            geodez = G.nodes[n].get('geoMarkTopTube', 0)
            n_zn1 = G.nodes[n]['num']

            beta0[nn1-1] = p_zn + geodez
            list_zd.append((n_zn1, nn1, p_zn+geodez))

            nn1 += 1


    if n_zn1 is None:
        return None

    t4 = time.time()

#    print((t1-t0)*1000, (t2-t1)*1000, (t3-t2)*1000, (t4-t3)*1000, file=sys.stderr, flush=True)

    return list_n, list_l, list_zd, list_rd, list_rr, list_ok, beta0



#------------------------------------------------------

def check_OK2(G, list_ok, root):
    for i in range(len(list_ok)):
        k_l, n1, n2, is_open = list_ok[i]

        if root[k_l] < 0:
            print('Закрыто ', w_print.line_name_n1_n2(G, n1, n2), root[k_l], flush=True)
        else:
            print('Открыто ', w_print.line_name_n1_n2(G, n1, n2), root[k_l], flush=True)


#------------------------------------------------------

def make_matrix(x, list_n, list_l, list_zd, list_rd, list_rr, list_ok, beta0, matrix0, first):
    nn = len(beta0)

    t0 = time.time()

    t1 = time.time()

    beta = np.copy(beta0)

    # Первый закон Кирхгофа

    t2 = time.time()

    for k_n, k_l, napr in list_n:
        if first:
            matrix0[k_n, k_l] = napr
        beta[k_n] -= x[k_l]*napr

    t3 = time.time()

    # Второй закон Кирхгофа

    for n1, n2, key, i1, i2, k_l, typ, param in list_l:
#        print(n1, n2, i1, i2, 'k_l=', k_l, typ, param, flush=True)
        if first:
            matrix0[k_l, i1] = 1
            matrix0[k_l, i2] = -1

        if typ == 'pumps':
            h, r1, r2 = param
            matrix0[k_l, k_l] =  (r1 + r2 * 2 * x[k_l])
            beta[k_l] = -((x[i1] - x[i2]) + (h + r1 * x[k_l] + r2 * x[k_l] * x[k_l]))

        elif typ == 'regulArmatures':  # Регулирующая арматура (ZD2)
            r1, = param
            beta[k_l] = -((x[i1] - x[i2]) - r1 * np.sign(x[k_l]))

        elif typ == 'reverseValves':
            n_ok, = param
            k_l_, n1_, n2_, is_open = list_ok[n_ok]

            if is_open:
                S = 0
                matrix0[k_l, k_l] =  0
                beta[k_l] = -(x[i1] - x[i2])
            
            else:
                S = 1.e6

                matrix0[k_l, k_l] =  -S * 2 * x[k_l] * np.sign(x[k_l])
                beta[k_l] = -(x[i1] - x[i2] - S * x[k_l] * x[k_l] * np.sign(x[k_l]))
#                print('5beta[2]=', beta[2], flush=True)

#                print('-------', flush=True)
#                matrix0[k_l, i1] = 0
#                matrix0[k_l, i2] = 0

        else:
            typ2, S, n_rd = param

            if typ2 == 'd':
               if not n_rd is None:
                   nodeID3, przu3, k_l, k_n, i1i, ii2, S, Z, r1, r2, delta, drr, rdr, rdh, rash_old, Z_old = list_rd[n_rd]
            elif typ2 == 'r':
                if not n_rd is None:
                   n1, n2, i1, i2, k_l, S, Z, r1, r2, key = list_rr[n_rd]

#                print('S=', S, list_rr[n_rd])
                
                if r1 != r2:
#                    print('rr', i1, i2, Z, flush=True)

#                    matrix0[k_l, i1] = 0
#                    matrix0[k_l, i2] = 0

#                    S = 10000

#                    print('beta[i1]=', beta[i1],'beta[i2]=', beta[i2], flush=True)
                    
                    beta[i1] += Z
                    beta[i2] -= Z
#                    print('beta[i1]=', beta[i1],'beta[i2]=', beta[i2], flush=True)

#                    matrix0[k_l, k_l] =  -S * 2 * x[k_l] * np.sign(x[k_l])
#                    beta[k_l] = -(x[i1] - x[i2] - S * x[k_l] * x[k_l] * np.sign(x[k_l]))

#                    continue
#                else:
#                    matrix0[k_l, i1] = 1
#                    matrix0[k_l, i2] = -1

#            if S == 0: S = 0.0000001
            if S == 0: S = 1e-20

            matrix0[k_l, k_l] =  -S * 2 * x[k_l] * np.sign(x[k_l])
            beta[k_l] = -(x[i1] - x[i2] - S * x[k_l] * x[k_l] * np.sign(x[k_l]))

            '''
            if S == 0: 
                matrix0[k_l, k_l] =  0
                beta[k_l] = -(x[i1] - x[i2])
            else:
                matrix0[k_l, k_l] =  -S * 2 * x[k_l] * np.sign(x[k_l])
                beta[k_l] = -(x[i1] - x[i2] - S * x[k_l] * x[k_l] * np.sign(x[k_l]))
            '''



    t4 = time.time()

# Узлы с заданным напором

    for n_zn, nn1, p_zn in list_zd:
        if first:
            matrix0[nn1-1, n_zn] = 1
        beta[nn1-1] = p_zn - x[n_zn]
        
        if first:
            matrix0[n_zn, nn1-1] = 1
        beta[n_zn] -= x[nn1-1]

    t5 = time.time()

    diag = matrix0.diagonal()

    for i in range(nn):
        if diag[i] == 0:
            matrix0[i, i] = eps

    t6 = time.time()

    matrix = sp.sparse.csc_array(matrix0)

    t7 = time.time()

#    print(f'all:{(t7-t0)*1000:4.1f} lil:{(t1-t0)*1000:4.1f} copy:{(t2-t1)*1000:4.1f} К1:{(t3-t2)*1000:4.1f} К2:{(t4-t3)*1000:4.1f} zn:{(t5-t4)*1000:4.1f} tr:{(t6-t5)*1000:4.1f} conv:{(t7-t6)*1000:4.1f}', file=sys.stderr, flush=True)

    return matrix0, matrix, beta


#------------------------------------------------------

# Проверяем источники
def check_ist2(G, root):
    ispr = False
    
#    print('Начали проверять источники', flush=True)
    
    GG = nx.MultiDiGraph()

    list_ist  = []
    
    for nn in G.nodes:
        n = G.nodes[nn]
#        id = n['nodeID']
#        po = n['po']
        id, po = nn

        typ = n['typ']
        ist0 = n.get('ist0', None) # Источник

        name = w_print.node_name(G, nn, False) 
#        GG.add_node((id, po), name=name, typ=typ)
        GG.add_node((id, po), typ=typ)

        if po == 1 and not ist0 is None:
            list_ist.append((id, po))
#            print(name)

    kk = 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]
        k_l = e['num']
        sost = e.get('sost', 1)

        g = root[k_l]
        if g < 0:
            n1, n2 = n2, n1

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        i1, p1 = n1
        i2, p2 = n2

#        i1 = nn1['nodeID']
#        p1 = nn1['po']
#        i2 = nn2['nodeID']
#        p2 = nn2['po']

#        name1 = w_print.node_name(G, n1, False) 
#        name2 = w_print.node_name(G, n2, False) 

        if sost != 2 and abs(g) > 0.00001 and p1 == 1:
#            GG.add_edge((i1, p1), (i2, p2), key=kk, txt=f'{name1} - {name2} = {orient} {g}', e=e)
            GG.add_edge((i1, p1), (i2, p2), key=kk, e=e)
            kk += 1

    ni = 1

    for i in list_ist:
        nist = G.nodes[i]['ist0']
        
        reachable_nodes = nx.descendants(GG, i)
        reachable_nodes.add(i)

        name = w_print.node_name(G, i, False) 

#        print(name)
#        print(len(reachable_nodes))

#        print('-----------------')
        for n in reachable_nodes:
            k, v = n

            n1 = G.nodes.get(n, None)

            if n1 is None:
                continue

#            n2 = G.nodes.get((k, 2), None)
#            print(k, v)
#            print(n1)
#            print(n2)
#            exit(0)

#            n1 = G.nodes[n]
            typ = n1['typ']

            if typ in ('realConsumers', 'generalizedConsumers'):
                ist_old = n1.get('heatSourceID', None)
                if ist_old != nist:
                    ispr = True

            n1['heatSourceID'] = nist


#            n2 = GG.nodes[n]
#            n2[f'ist{ni}'] = nist

            for nn1, nn2, key in GG.out_edges(n, keys=True):
                e = GG.edges[nn1, nn2, key]
                ee = e['e']
                ee['heatSourceID'] = nist

        ni += 1

#    nx.write_graphml(GG, f'C:/data/qq{name1}.graphml', edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)
    
#    print('Закончили проверять источники', flush=True)

    return ispr;

#------------------------------------------------------

def check_ist(G, root):
    n_ist = 0
    
    heatSourceID = None

    for n in G.nodes:
        nP = G.nodes[n]

        typ = nP['typ']
        po = nP['po']
        ist0 = nP.get('ist0', None) # Источник из магистрали

        if po == 1 and not ist0 is None:
            heatSourceID = ist0
            n_ist += 1

#    print(f'Источников {n_ist}')

    if n_ist == 1:
        for n in G.nodes:
            nP = G.nodes[n]
            nP['heatSourceID'] = heatSourceID

        '''
        for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
            e = G.edges[n1, n2, key]
            e['heatSourceID'] = heatSourceID
            '''

    return n_ist, heatSourceID
    



#------------------------------------------------------

def solve_G(G, root, n_n, n_l, n_zn):
    '''
    matrix, beta = init_matrix(G, root)
    matrix2 = sp.sparse.csc_array(matrix)
    root = spsolve(matrix2, beta)
    set_G_out(G, root)
    return
    '''

#    n_n = G.number_of_nodes()
#    n_l = G.number_of_edges()
#    nn = n_n + n_l + 1
    nn = n_n + n_l + n_zn

    if root is None:
        root = np.full(nn, 0.)

    delta = 10000

    ret = init_matrix(G, root, n_n, n_l, n_zn)
    
    if ret is None:
        return None

    list_n, list_l, list_zd, list_rd, list_rr, list_ok, beta0 = ret

    matrix0 = sp.sparse.lil_array((nn, nn))
    matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, beta0, matrix0, True)
    
#    w_print.print_b('beta', beta)
#    exit(0)

#    w_print.print_matrix(matrix, beta)
#    w_print.print_b('beta', beta)

#    reset_consumptions(G, beta0)

#    Tn0 = ct->t_or
    ct = get_ct()
    Tn0 = ct.get('t_or')

    n_ist, heatSourceID = check_ist(G, root)

    n_potr = 1

    if config.args.is_tg and not config.args.no_teplopoter:
        n_potr = 4

    is_teplo = False

    for m in range(n_potr): # Пересчет потребителей с учетом тепловых потерь
        for j in range(4): # регуляторы расхода
            for i in range(250): # Регуляторы давления
                for it in range(100):  # Итерация уравнения
                    t1 = time.time()

                    if n_ist == 1:
                        reset_consumptions(G, beta0)

                    t2 = time.time()

                    matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, beta0, matrix0, False)

                    t3 = time.time()

    #                w_print.print_matrix(matrix, beta)

                    beta1 = matrix @ root

    #                w_print.print_b('beta1', beta1)
            #        if get_delta(beta) < 0.0001: break
            #        delta = get_delta(beta1)
            #        print('iter1 = ', it, 'delta = ', delta, 'delta/nn = ', delta/nn, file=sys.stderr, flush=True)


                    beta2 = sp.sparse.linalg.spsolve(matrix, beta)

    #                beta2 = spsolve(matrix, beta)

                    root += beta2

                    delta = get_delta(beta2)
                    delta2 = get_delta_max(beta2)

                    t4 = time.time()

                    print(f'iter: {m:1d} {j:1d} {i:2d} {it:2d} d={delta:14f} d_max={delta2:10f} dt={(t2 - t1) * 1000:5f} ms dt2={(t3 - t2) * 1000:5f} ms dt2={(t4 - t3) * 1000:5f} ms', file=sys.stderr, flush=True)

#                    if n_ist > 0:
#                    check_ist2(G, root)

                    reset_sopr(G, root, list_l, heatSourceID)  # пересчитываеи сопротивления по температуре

                    if delta < 0.001:
                        break

                f1 = w_rd.check_RD(G, list_rd, root, i)

#                if f1 < 0.001:
                if f1 == 0:
                   break



            f_RR = w_rr.check_RR(G, list_rr, root)
            f_OK = w_ok.check_OK(G, list_ok, root)

            if f_RR:
                print(list_rr)

#            print('f_RR', f_RR, 'f_OK', f_OK, flush=True)
    #        break

            if not f_RR and not f_OK:
               break

        if n_ist > 0:
            check_ist2(G, root)

        is_teplo = False

#        if config.args.is_tg or config.args.g_is_avar:
        if True:
            t1 = time.time()
#            print('Начали считать тепло', flush=True)
            is_teplo = calc_teplo(G, root, Tn0, False)
#            reset_sopr(G)  # пересчитываеи сопротивления по температуре

            if not is_teplo and config.args.is_tg:
                cprint('Во фрагменте нет источников тепла, расчет по температурному графику невозможен', color='red')
                return None

            t2 = time.time()
#            print(f'Закончили считать тепло {(t2-t1)*1000}', flush=True)

#        print('~~~~~~~~~~~~~~~~~~~~~~', Tn0)



#        if is_teplo:
#            reset_consumptions(G, beta0)

    if is_teplo:
        calc_teplo(G, root, config.args.Tn, True)

    calc_nagr(G, root)

#        print('bb:', bb, flush=True)
#    print_matrix(matrix, beta, x)


#    print('--------------------', flush=True)
#    check_OK2(G, list_ok, root)
#    print('--------------------', flush=True)

    return root

#------------------------------------------------------

def w_calc2(G, param_sum):
    set_G_num(G)

    print('Начал расчет фрагмента', file=sys.stderr, flush=True)

    first = True

    while True:
        root, n_n, n_l, n_zn = init_root(G)
        root = solve_G(G, root, n_n, n_l, n_zn)

        if root is None:
            print(f'Ошибка расчета', file=sys.stderr, flush=True)
            return


    #    print('delta = ', delta, ' iter = ', it, flush=True)



        print()
        print(f'Расчет закончен', file=sys.stderr, flush=True)
        
        w_out.set_G_out(G, root)

        f_PO = True

        if first and not config.args.g_is_avar:   # плановый 
            f_PO = reset_consumptions_PO(G, root)

        first = False

        if f_PO: 
            break

    if not config.args.g_is_avar:   # плановый расчет
        g2.make_G2(G, param_sum)

    if config.args.is_leto and config.args.is_save_po:
#    if config.args.is_save_po:
 #       g2.write_po(G, param_sum, config.args.out_file)
        g2.make_G2_leto(G, config.args.out_file)

#    matrix, beta = init_matrix(G)

#    print(beta, flush=True)

#------------------------------------------------------

# Ищет любой узел с ЗН
def find_zn(G):
    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            nn0 = G.nodes.get(n, None)
            if nn0:
                if nn0.get('name', '') != 'ATMOSPHERE':
                    return n

    return None

#------------------------------------------------------

def find_zn2(G):
    
    zn = set()
    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            zn.add(n)

    return zn

#------------------------------------------------------

def w_calc(G):
    print('Расчет начат', flush=True)

    w_print.setG(G)

    nn = 0
    for i in nx.weakly_connected_components(G): 
        if len(i) > 1: 
            if True:
                GG = G.subgraph(i)
                n0 = find_zn(GG)
                if n0 is not None:
                    nn0 = G.nodes.get(n0, None)
                    if nn0:
                        if nn0.get('name', '') != 'ATMOSPHERE':
                            nn += 1

#    param_sum = defaultdict(lambda: [0] * 9)  # Начальные значения для обобщенных потребителей
    param_sum = defaultdict(dict)  # Начальные значения для обобщенных потребителей
 
    print(f'{nn} фрагментов')

    ii = 0
    for i in nx.weakly_connected_components(G):
        if len(i) > 1:
#            if ii in (4,):
            if True:
                GG = G.subgraph(i)
                n0 = find_zn(GG)

                if n0 is not None:
                    print('-----------------', flush=True)

                    name = w_print.node_name(G, n0, True)    
                    print(f'Фрагмент {ii+1}/{nn} [{name}]', flush=True)

                    n_n = GG.number_of_nodes()
                    n_l = GG.number_of_edges()
                    print(f'Узлов : {n_n} Ребер: {n_l}')

                    print(f'Узлы с заданым напором', flush=True)
                    nn0 = find_zn2(GG)
                    z = 1
                    for pp in nn0:
                        p_zn = G.nodes[pp].get('p_zn', None)
#                        print(z, w_print.node_name(G, pp, False), ' = ', p_zn, flush=True)
                        if G.nodes[pp].get('name', '') != 'ATMOSPHERE':
#                            print(G.nodes[pp].get('name', ''))
                            print(z, w_print.node_name(G, pp, False), flush=True)
                        z += 1

                    w_calc2(GG, param_sum)

                    ii += 1

    if config.args.is_save_po:
        g2.write_po(G, param_sum, config.args.out_file)

#    print('Закончил расчет', flush=True)
#    print('Расчет закончен', flush=True)

#------------------------------------------------------

if __name__ == "__main__":
    G = nx.MultiDiGraph()

    G.add_node(1, p_zn=100, x=0, y=0)
    G.add_node(2, G=1.1, x = 0, y=1000)
    G.add_node(3, G=1.2, x=1000, y=0)

#    G.add_edge(1, 2, 1, sopr = 0.12)
    G.add_edge(1, 2, 1, S=0.12, typ='heatPipeSections')
    G.add_edge(3, 1, 2, S=0.01, typ='heatPipeSections')
    G.add_edge(2, 3, 3, S=0.01, typ='heatPipeSections')

    param_sum = defaultdict(lambda: [0] * 9)  # Начальные значения для обобщенных потребителей
    
    w_calc2(G, param_sum)
    nx.write_graphml(G, 'C:/data/qq.graphml', edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)

