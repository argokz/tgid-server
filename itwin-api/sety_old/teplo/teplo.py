import numpy as np
import networkx as nx

import numpy as np
import scipy as sp

import itertools

#from scipy.sparse.linalg import spsolve

from sety import config

from sety import w_print

from sety.teplo.rasto import rasTO_pr2
from sety.teplo.rasto_po import rasTO_po
from sety import read_gid
from sety import read_tg
from sety.ct import get_ct
from sety.any.colors import cprint
from sety.teplo import gid_init
from sety.teplo.teplo2 import rasTO2
from sety.teplo.rasto3 import rasTO
from sety.teplo.otopl import otopl
from sety.teplo.tepl_vent import rasVENT

import inspect

class LineNo:
    def __str__(self):
        return str(inspect.currentframe().f_back.f_lineno)


__line__ = LineNo()
#-----------------------------------------------------------------------------------

# Возвращает температуру источника или узла с заданным напором

def getZT(node, curT):
    t0 = node.get('t0', None)
    if curT:
        return t0

    ist0 = node.get('ist0', None)

    if not ist0 is None:
        ct = get_ct()
        ist = read_gid.map_ist.get(ist0, None)

        if config.args.is_leto:
            t70 = ist.get('t1_leto', 0)  # летняя температура источника
            return t70
        
        Tn_otop = ct.get('t_or')
        v = read_tg.get_tg(ist0, Tn_otop)
        
        if v is None:
            cprint(f'[red]Нет Температурного графика в Источнике[-]')
            return 150
            exit(0)

        t1, t2, t3, tv = v
        t0 = t1

#        print(t0, Tn_otop, ist0, v)


#    print(node.get('typ','??'), node.get('name','??'), t0)

    return t0


'''

def get_beta(typ_pr, diam) -> float:
{
    static map<char, S30>::const_iterator it

    typ = get_char_typ(typ_pr)

    if typ == 'П': typ = 'К'

    it = map_s30.find(typ)
    if it == map_s30.end():
        return 0

    if diam < it->second.diametr:
        return it->second.beta_rasp
    else:
        return it->second.beta_mag


    return 0


def Y(l):
    beta = get_beta(l->typ_pr, l->diametr + 2 * l->tol)
    qq = l->qq

    switch (n_trtp) {
    case 0: qq = l->qq_ras35   break
    case 1: qq = l->qq_ras15   break
    }

    y = qq * l->dlina * beta * l->kti / 1.e6  # Нормативная среднегодовая Гкал

    return y
'''
#-----------------------------------------------------------------------------------

def rasTO_po2(po, G, t, Tn, debug):

    gv_ps = po.get('gv_ps', 0)
    gv_pw = po.get('gv_pw', 0)
    gv_pr = po.get('gv_pr', 0)
    gv_sm = po.get('gv_sm', 0)

#    if po.get('otopl_ps', 0) != 0 and po.get('gv_ps', 0) == 0: 
#        exit(0)
#        po['gv_ps'] = 1e-12


    if po.get('otopl_ps', 0) != 0 and po.get('gv_ps', 0) == 0: po['gv_ps'] = 1e-12
    if po.get('otopl_pw', 0) != 0 and po.get('gv_pw', 0) == 0: po['gv_pw'] = 1e-12
    if po.get('otopl_pr', 0) != 0 and po.get('gv_pr', 0) == 0: po['gv_pr'] = 1e-12
    if po.get('otopl_sm', 0) != 0 and po.get('gv_sm', 0) == 0: po['gv_sm'] = 1e-12

#    double Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo;

    t2, Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_po(po, po, po, G, t, Tn, debug)


    po['gv_ps'] = gv_ps
    po['gv_pw'] = gv_pw
    po['gv_pr'] = gv_pr
    po['gv_sm'] = gv_sm


#    if debug:
#        print(t2, Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo)

#    if (isnan(t2)) {
#        int qq;
#        qq = 1;
#        rasTO_po(node, &po2, pt_G, G, t, t2, Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo, Tn)

    return t2, Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo


#-----------------------------------------------------------------------------------

"""
def potrebitel(nodeP, GG, debug):
    t = nodeP.get('t', 0)

    if t != 0:
        Tn = config.args.Tn   # Температура наружного воздуха

        debug1 = False
        t2, qq = rasTO_pr2(nodeP, nodeP, nodeP, GG, t, Tn, debug1)

        Qz2 = (t - t2) * GG/1000
        if Qz2 > 0:
            Qz = Qz2
    
    else:
        pass

"""

#-----------------------------------------------------------------------------------

def init_matrix_teplo(G, x, Tn, curT):
#    print(G)
    n_ist = 0

#    Tn = config.args.Tn   # Температура наружного воздуха

    dict_ist = {}

    for n in G.nodes:
        nodeID, po1 = n
        node = G.nodes[n]
        t0 = node.get('t0', None)
        tn = node.get('typ', None)

        t0 = getZT(node, curT)

        if tn == 'heatSources' and t0 is None and po1 == 1:
            name = w_print.node_name(G, n, False)
            cprint(f'Не задан температурный график в источнике {name}, тепловой расчет не производится', color='red')
            return None

        if t0:  
#            print(node.get('name'), t0)
            dict_ist[n] = n_ist
            n_ist += 1

    n_nodes = G.number_of_nodes()

    nn = n_nodes + n_ist

    n_ist0 = n_ist

    beta = np.zeros(nn)

#    print('nn=', nn)

    matrix = sp.sparse.lil_array((nn, nn))

    n_ist = 0
    ii = 0

    debug = False;


    for n in G.nodes:
        name = w_print.node_name(G, n, False)
#        print('!!!', name, ii)
#        print('====', n, G.nodes[n]['name'])

#        if debug: print('!!!', name, ii)
        
        node = G.nodes[n]
        k_n1 = G.nodes[n]['num']

        typ = node['typ']

        # Тут ищем смежный узел
        nodeID, po1 = n
        po2 = (2 if po1 == 1 else 1)

        t0 = node.get('t0', None)
        t0 = getZT(node, curT)

        is_ist = False

        if t0:  
            n_ist += 1
            is_ist = True


        B = 0

        g = 0
        yes = False

        t0 = node.get('t0', None)
        t0 = getZT(node, curT)

#        if debug: print('n_nodes', n_nodes, 'n_ist', n_ist)

        n_in = 0
        n_out = 0 

        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 

            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            k_l = l['num']
            GG = x[k_l]

#            yes = False

            if abs(GG) > 0.00001: yes = True
            if abs(GG) < 0.00001:
                continue

            if GG < 0:
                GG = -GG
                n1, n2 = n2, n1

            name1 = w_print.node_name(G, n1, False)
            name2 = w_print.node_name(G, n2, False)

#            if yes:
#                print('    +', k, l_typ, name1, name2, GG, l.get('Y', 0))

#            if debug: print('    +', name1, name2, x[k_l], n, n1, n2)

            if n != n1 and n != n2:
                print('!!!!!!!!!!!!')
            
            node1 = G.nodes[n1]

#            print('    +', k, l_typ, name1, name2, GG, l.get('Y', 0))

            if n == n2:   # втекает
                n_in += 1

                i1 = G.nodes[n1]['num']

                nnode1 = G.nodes[n1]
                nnode2 = G.nodes[n2]

                i1 = nnode1['num']
                i2 = nnode2['num']

                t0 = nnode1.get('t0', None)
                t0 = getZT(nnode1, curT)

                if t0:  
                    nist = dict_ist.get(n1)
                    i1 = n_nodes + nist

                matrix[ii, i1] += GG

                nodeID_pr = l.get('nodeID_pr', 0)

                if l_typ in ('generalizedConsumers', 'realConsumers') and n != (-99999, 1):
                    nodeP = G.nodes[n1]
                    t = nodeP.get('t', 0)
                    t2, *qq = rasTO_pr2(l, l, l, GG, t, Tn, False)

                    y = (t - t2) * GG/1000
                    
                elif l_typ in ('EL', 'SO'):
                    nodeP = G.nodes[(nodeID_pr, 1)]
#                    nodeP = G.nodes[n1]
                    t = nodeP.get('t', 0)
                    t = node1.get('t', 0)
                    is_leto = False

                    tr = nodeP.get('kodtr', None)
                    if not tr is None:
                        tr = read_gid.map_tr.get(tr, None)

                    W0 = GG
#                    print('!!', W0, t, nodeP.get('name'))
                    t2, tv, Q = otopl(nodeP, nodeP, tr, W0*1000, Tn, t, is_leto, False)

                    y = (t - t2) * GG/1000

                elif l_typ in ('VN'):
                    nodeP = G.nodes[(nodeID_pr, 1)]
#                    nodeP = G.nodes[n1]
                    t = nodeP.get('t', 0)
                    is_leto = False

                    tr = nodeP.get('kodtr', None)
                    if not tr is None:
                        tr = read_gid.map_tr.get(tr, None)

                    QQ = l.get('ZZ', 0)
                    t2, tv = rasVENT(nodeP, GG*1000, QQ*1e6, t, Tn, False)

                    y = (t - t2) * GG/1000

                elif l_typ in ('TO'):
                    nodeP = G.nodes[(nodeID_pr, 1)]

                    t = nodeP.get('t', 0)
                    t = node1.get('t', 0)

                    typTO = l.get('typTO', 0)
                    tr = nodeP.get('kodtr', None)
                    if not tr is None:
                        tr = read_gid.map_tr.get(tr, None)

                    tx = tr.get('Tx', 0)

                    debug1 = nodeP.get('cxema', '') == '1.5'

                    nIin = None

                    if typTO == 10:
                        pass
                    elif typTO == 11:
                        pass
                    elif typTO == 12:
                        pass
                    y = 0

                    GG0 = 0

                    nIin = None
                    nIin0 = None

                    if typTO == 11:
                        nIin0 = nodeP.get('nIn')
                        if nIin0:
                            nodeID0, po0 = nIin0
                            nIin = G.nodes.get((nodeID0, po0), None)


                            for k, (n1, n2, key) in itertools.chain(
                                    zip(itertools.repeat(1), G.in_edges(nIin0, keys=True)),
                                    zip(itertools.repeat(2), G.out_edges(nIin0, keys=True))
                                    ): 
    #                            print(k, (n1, n2, key))

                                l = G.edges[n1, n2, key]

                                l_typ = l['typ']

                                k_l = l['num']

                                GG1 = x[k_l]
                                if k == 2:  
                                    GG1 = -GG1

                                if GG1 > 0:
                                    GG0 += GG1

                    # Начальный узел для второй 
                    
                    pr = l
                    pr = nodeP

                    QQ = l.get('ZZ', 0)

#                    if l.get('cxema', '') == '15.2':
#                        debug1 = True
#                        print(typTO, nIin0, GG, GG0)

                    t2 = rasTO(nIin, pr, typTO, tr, GG, GG0, QQ, t, Tn, debug1)

#                    if abs(GG) > 0.0001:
#                        print(name, typTO, t, t2, GG, GG0)

#                    if debug1:
#                        print(n1, nodeP)
#                        print('.......==', typTO, round(GG, 1), 'GG0', round(GG0, 1), round(t, 1), round(t2, 1))
#                        exit(0)
                    
                    
                    y = (t - t2) * GG/1000
#                    print(f'{y} = ({t} - {t2}) * {GG}/1000')

                else:
                    y = l.get('Y', 0)
#                    print(yes, name1, name2, l_typ, y)

                    if config.args.is_leto:
                        y = 0   # летом  тепловые потери не учитываем

                    if not config.args.is_tg:
                        y = 0

                B += y*1e3
#                print(l_typ, 'B += y*1e3', y)

                if debug: print(f'  <{k}', name1, name2, GG, ii, i1, y, t0 is not None)

            else:       # вытекают
                n_out += 1
                g += GG
#                y = l.get('Y', 0)
#                B += y*1e3

                if debug: print(f'  >{k}', name1, name2, GG)

        if typ in ('generalizedConsumers', 'realConsumers') and not config.args.g_is_avar:
            n1 = n
            n2 = (nodeID, po2)

            node1 = G.nodes.get((nodeID, po1), None)
            node2 = G.nodes.get((nodeID, po2), None)

            GG = node['G']

            if GG < 0:
                GG = -GG
                n1, n2 = n2, n1

            name1 = w_print.node_name(G, n1, False)
            name2 = w_print.node_name(G, n2, False)

            yes0 = False
            if abs(GG) > 0.00001: yes0 = True

            Qz = node.get('Qz', 0)
            if Qz == 0 and node2:
                Qz = node2.get('Qz', 0)

#            nodeP = G.nodes[n1]
            nodeP = G.nodes.get(n1, None)

            t = 0

            if nodeP:
                t = nodeP.get('t', 0)
            else:
#               print('t=', t, 'GG=', GG, n, n2)
               t = 0
               yes0 = False
               g = 0
               GG = 0
               Qz = 0

            if t != 0 and nodeP:
                debug1 = False
            
#                if G.nodes[n].get('name', '') in ('4.6==-0'):
#                    print('~~~~~~~~~~~~~~~~~~~~~')
#                    print(G.nodes[n]['name'])
#                    debug1 = True

                if typ =='realConsumers':
                    t2, *qq = rasTO_pr2(nodeP, nodeP, nodeP, GG, t, Tn, debug1)
                else:
                    t2, *qq = rasTO_po2(nodeP, GG, t, Tn, debug1)

#                if nodeP.get('cxema', '') == '1.5':
#                    print("!!", GG, t, t2)
#                    exit(0)


                Qz2 = (t - t2) * GG/1000
                if Qz2 > 0: Qz = Qz2

            if not config.args.is_tg and nodeP:     # Если не по ТГ
                tr = nodeP.get('kodtr', None)

                if tr is None:
                    t2 = 70
#                    print(nodeP)
#                    exit(0)
                else:
                    tr = read_gid.map_tr.get(tr, None)
                    t2 = tr.get('T1_isl_2stup', 69)

                Qz2 = (t - t2) * GG/1000
                if Qz2 > 0: Qz = Qz2


            if yes0:
                if n == n2:
                    if debug: print(f'* <{k}', name1, name2, GG, Qz)
                    i1 = G.nodes[n1]['num']
                    matrix[ii, i1] = GG
                    B += Qz*1000
                
                else:       # вытекают
                    if debug: print(f'* >{k}', name1, name2, GG)
                    g += GG
        if yes:    
            matrix[ii, k_n1] = -g
            beta[ii] = B
#            print('B=', B)
            if debug: print(f'   << {n_in}  >> {n_out} ii={ii} k_n1={k_n1}  --   g={g}  B={B}')
        else:
            if debug: print('     !!', name)
            matrix[ii, k_n1] = 1
            beta[ii] = 0   # Это температура узла, куда не идет вода

        ii += 1

    for n in G.nodes:
        node = G.nodes[n]
        t0 = node.get('t0', None)
        t0 = getZT(node, curT)

        if t0:  
            name1 = w_print.node_name(G, n, False)
            matrix[ii, ii] = 1
            beta[ii] = t0
            ii += 1


    diag = matrix.diagonal()

    eps = 0.00000000001

    for i in range(nn):
        if diag[i] == 0:
            matrix[i, i] = eps

    matrix = sp.sparse.csc_array(matrix)

    return matrix, beta, n_ist

#-----------------------------------------------------------------------------------

# curT - это значит, что текущая температура

def calc_teplo(G, x, Tn, curT):

    for i in range(5):
        ret = init_matrix_teplo(G, x, Tn, curT)

        if ret is None:
            return False

        matrix, beta, n_ist = ret

        if n_ist == 0:
            cprint('Во фрагменте нет источников тепла, тепловой расчет не производится', color='red')
            return False

#        w_print.print_matrix(matrix, beta)

        t = sp.sparse.linalg.spsolve(matrix, beta)
    #    t = spsolve(matrix, beta)

        ii = 0

        for n in G.nodes:
            num = G.nodes[n]['num']
            name = w_print.node_name(G, n, False)
#            print(name, num, t[ii])
    #        G.nodes[n]['t'] = round(t[ii], 2)
            G.nodes[n]['t'] = t[ii]

            nn, po = n;

#            print(G.nodes[n].get('name', '???'), po, t[ii])

            ii += 1

#        exit(0)


#    print(f't{ii}', t[ii])

#    for r in t:
#        print(r)
    
#    exit(0)
    return True
