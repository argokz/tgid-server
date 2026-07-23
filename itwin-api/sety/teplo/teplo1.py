import sys
import numpy as np
import networkx as nx

import numpy as np
import scipy as sp

import time

from collections import defaultdict

import itertools

#from scipy.sparse.linalg import spsolve

from sety import config

from sety import w_print

#from sety.teplo.rasto import map_t
#from sety.teplo.rasto import map_pt_cnt


from sety.teplo.rasto import rasTO_pr2
from sety.teplo.rasto_po import rasTO_po
from sety import read_gid
from sety import read_tg
from sety.ct import get_ct
from sety.any.colors import cprint
from sety.teplo.teplo2 import rasTO2
from sety.teplo.rasto3 import rasTO
from sety.teplo.otopl import otopl
from sety.teplo.tepl_vent import rasVENT

from sety.consumption import get_tr

from sety.safe_spsolvefile import safe_spsolve
from sety.safe_spsolvefile import dump_system


import inspect

class LineNo:
    def __str__(self):
        return str(inspect.currentframe().f_back.f_lineno)


__line__ = LineNo()
#-----------------------------------------------------------------------------------

# Возвращает температуру источника или узла с заданным напором

from sety.teplo.zt import getZT

'''
def getZT(G, node, curT):

    name = f'{node.get('kod')} {node.get('name')}'
                
    t0 = node.get('t0', None)
    if curT:
        return t0

    ist0 = node.get('ist0', None)

    if ist0 is None:
#       cprint(f'Не известен источник для узла с заданным напором [{name}]', color='red')
       return None

    if not ist0 is None:
        ct = get_ct()
        ist = read_gid.map_ist.get(ist0, None)

        if not ist:
#            cprint(f'Не известен источник для узла с заданным напором [{name}]', color='red')
            return None


        if config.args.is_leto:
            t70 = ist.get('t1_leto', 0)  # летняя температура источника
            return t70
        
        Tn_otop = ct.get('t_or')
        v = read_tg.get_tg(ist0, Tn_otop)
        
        if v is None:
#            print(ist)
#            cprint(f'[red]Нет Температурного графика в Источнике {ist0}[-]')
            return None
            exit(1)

        t1, t2, t3, tv = v
        t0 = t1

#        print(t0, Tn_otop, ist0, v)


#    print(node.get('typ','??'), node.get('name','??'), t0)

    return t0

'''
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
#        exit(1)
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


def get_t2(pr, t1):
    tr = get_tr(pr)
    
    t01 = tr.get('Tr_co_1_zco', 150)
    t02 = tr.get('Tr_co_2_zco', 70)

    return t1 - (t01-t02)
    


#-----------------------------------------------------------------------------------

def init_matrix_teplo(G, x, Tn, curT, teploYes, debug=False):
#    print(G)
    n_ist = 0

#    if not config.args.is_tg:
#        teploYes = False

#    Tn = config.args.Tn   # Температура наружного воздуха

    dict_ist = {}

    tt1 = time.time()


    for n in G.nodes:
        nodeID, po1 = n
        node = G.nodes[n]
        t0 = node.get('t0', None)
        tn = node.get('typ', None)

        t0 = getZT(G, node, curT)

        if tn == 'heatSources' and t0 is None and po1 == 1:
            name = w_print.node_name(G, n, False)
            cprint(f'Не задан температурный график в источнике {name}', color='red')

        if t0:  
            dict_ist[n] = n_ist
            n_ist += 1

    tt2 = time.time()

    if n_ist == 0:
        for n in G.nodes:
            nodeID, po1 = n
            node = G.nodes[n]
            t0 = node.get('t0', None)
            tn = node.get('typ', None)

            if po1 == 2:
                
                zn = node.get('p_zn', None)

                if zn:
                    nodeP = G.nodes.get((nodeID, 1), 0)

                    if nodeP:
                        t0 = getZT(G, nodeP, curT)
                        if t0 is None:  
                            name = w_print.node_name(G, n, False)
                            cprint(f'Не известен источник для узла с заданным напором {name}', color='red')
                        if t0:  
                            dict_ist[n] = n_ist
                            n_ist += 1

    if n_ist == 0:
#        cprint(f'Тепловой расчет не производится', color='red')
#        return None
        return None, None, n_ist

    n_nodes = G.number_of_nodes()

    nn = n_nodes + n_ist

    n_ist0 = n_ist

    beta = np.zeros(nn)

#    print('nn=', nn)

    matrix = sp.sparse.lil_array((nn, nn))

    n_ist = 0
    ii = 0

    debug = False
#    debug = True


    if debug:
        print('===========================')


    nnn = len(G.nodes)

    nnn1 = 0

#    print('Начали')

    dt1 = 0
    dt2 = 0
    dt3 = 0
    dt4 = 0

    tt3 = time.time()

    for n in G.nodes:
#        name = w_print.node_name(G, n, False)

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
        t0 = getZT(G, node, curT)

        is_ist = False

        if t0:  
            n_ist += 1
            is_ist = True


        B = 0

        g = 0
        yes = False

        t0 = node.get('t0', None)
        t0 = getZT(G, node, curT)

#        if debug: print('n_nodes', n_nodes, 'n_ist', n_ist)

        n_in = 0
        n_out = 0 

        kkkk1 = 0


        debug1 = False
        debug2 = False

        debug = False
#        debug = node.get('name', '') in ( '5Б-18', 'Узел_538290')
        if debug:
            debug2 = True
            print('-------------------------')

            name = w_print.node_name(G, n, False)
            print(name)

        if debug1:
            debug2 = True
            print('-------------------------')
            name = w_print.node_name(G, n, False)
            print(name)
            print(f'{B=:.4f}')
            pass
       
        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 


            kkkk1 += 1

#            print(f'{k}                  \r', end='')
            
            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            k_l = l['num']
            GG = x[k_l]

            nodeID3 = l.get('nodeID', -1)

            if l_typ == 'consumptRegulators' or (l_typ == 'bypass' and nodeID3 <= 0) :   # RR
                fixed = l.get('fixed', False)

                if not fixed:
#                    r1 = l.get('r1')
#                    r2 = l.get('r2')
                    ZZ = l.get('Z', 0)
#                if ZZ > 1000:
#                        print(f'{ZZ=:.2f} {GG=:.2f} {r1=} {r2=} {fixed=}')
                    GG += ZZ

#            yes = False

            if abs(GG) > 0.00001: yes = True
            if abs(GG) < 0.00001:
                continue

            if GG < 0:
                GG = -GG
                n1, n2 = n2, n1

#            name1 = w_print.node_name(G, n1, False)
#            name2 = w_print.node_name(G, n2, False)

#            if yes:
#                print('    +', k, l_typ, name1, name2, GG, l.get('Y', 0))
#            if debug: print('    +', name1, name2, x[k_l], n, n1, n2)

            if n != n1 and n != n2:
                print('!!!!!!!!!!!!')
            
            node1 = G.nodes[n1]

            if n == n2:   # втекает
            
                n_in += 1

                i1 = G.nodes[n1]['num']

                nnode1 = G.nodes[n1]
                nnode2 = G.nodes[n2]

                i1 = nnode1['num']
                i2 = nnode2['num']

                t0 = nnode1.get('t0', None)
                t0 = getZT(G, nnode1, curT)

                if t0:  
                    nist = dict_ist.get(n1)
                    i1 = n_nodes + nist

                matrix[ii, i1] += GG

                nodeID_pr = l.get('nodeID_pr', 0)

                # Это для обобщенных потребителей и для эквивалентных реальных
                if l_typ in ('generalizedConsumers', 'realConsumers') and n != (-99999, 1):
                    nodeP = G.nodes[n1]
                    t = nodeP.get('t', 0)

                    if teploYes:
                        t2, *qq = rasTO_pr2(l, l, l, GG, t, Tn, False)
                    else:
                        t2 = get_t2(l, t)

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

                    debug1 = False
#                    debug1 = nodeP.get('cxema', '') == '1.5'
#                    debug1 = nodeP.get('name', '') == '5Б-18'



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
#                        exit(1)
                    
                    y = (t - t2) * GG/1000

                else:
                    y = l.get('Y', 0)

#                    if l_typ == 'bypass':
#                        print(f'{y=} {GG=}')

                    if config.args.is_leto:
                        y = 0   # летом  тепловые потери не учитываем

#                    if not config.args.is_tg:
#                        y = 0

                B += y*1e3

                if debug2:
                    print(f'B += {y*1e3} = {B}   -- y')

                t0s = ''
                if t0:
                    t0s = f'{t0=}'


                if debug: 
                    name1 = w_print.node_name(G, n1, False)
                    name2 = w_print.node_name(G, n2, False)
                    print(f'  <{k} {name1} {name2} {GG=:.4f} {ii=} {i1=} {y=:.8f} {t0s}')


            else:       # вытекают
                n_out += 1
                g += GG
#                y = l.get('Y', 0)
#                B += y*1e3

                if debug: 
                    name1 = w_print.node_name(G, n1, False)
                    name2 = w_print.node_name(G, n2, False)
                    print(f'  >{k}', name1, name2, GG)


        tt1_pt = 0
        tt2_pt = 0
        tt1_pt2 = 0
        tt2_pt2 = 0

        if typ in ('generalizedConsumers', 'realConsumers') and not config.args.g_is_avar:

            n1 = n
            n2 = (nodeID, po2)

            node1 = G.nodes.get((nodeID, po1), None)
            node2 = G.nodes.get((nodeID, po2), None)

            GG = node.get('G', 0)
            Gout = node.get('Gout', 0)

            GG_Z = GG - Gout

#            print(node['name'], f'{GG_Z=}')

            if GG_Z < 0:
                GG_Z = -GG_Z
                n1, n2 = n2, n1

#            name1 = w_print.node_name(G, n1, False)
#            name2 = w_print.node_name(G, n2, False)

            yes0 = False
            if abs(GG_Z) > 0.00001: yes0 = True

            Qz = node.get('Qz', 0)
            if Qz == 0 and node2:
                Qz = node2.get('Qz', 0)

#            nodeP = G.nodes[n1]
            nodeP = G.nodes.get(n1, None)

#            if nodeP is None:
#                node21 = G.nodes.get((nodeID, 1), None)
#                node22 = G.nodes.get((nodeID, 2), None)
                
#                print(nodeID, 1, node21)
#                print(nodeID, 2, node22)
#                exit(1)

            t = 0
            t2 = -1

            if nodeP:
                tr = nodeP.get('kodtr', None)
                if tr:
                    tr = read_gid.map_tr.get(tr, None)
                    if tr:
                        t2 = tr.get('T1_isl_2stup', 69)

                t = nodeP.get('t', 0)
            else:
               t = 0
               yes0 = False
               g = 0
               GG_Z = 0
               Qz = 0

            if yes0 and t != 0 and nodeP:
                debug1 = False
            
#                if G.nodes[n].get('name', '') in ('мтк6-2 45435634256'):
#                    print('~~~~~~~~~~~~~~~~~~~~~')
#                    print(G.nodes[n]['name'])
#                    debug1 = True


                if teploYes:
                    if typ =='realConsumers':
                        t2, *qq = rasTO_pr2(nodeP, nodeP, nodeP, GG_Z, t, Tn, debug1)
                    else:
                        t2, *qq = rasTO_po2(nodeP, GG_Z, t, Tn, debug1)

                        if debug1: 
                            print(f'{t=} {t2=} {GG_Z=} {Tn=}')

                else:
                    t2 = get_t2(nodeP, t)
                    if debug1: 
                        print('t2====', t2)

#                if nodeP.get('cxema', '') == '1.5':
#                    print("!!", GG_Z, t, t2)
#                    exit(1)

                Qz2 = (t - t2) * GG_Z/1000
                if Qz2 > 0: Qz = Qz2

                if debug2:
                    print(f'Qz2 = (t - t2) * GG_Z/1000   {Qz2} = ({t} - {t2}) * {GG_Z}/1000')


            if debug: print('1 t2=', t2)

            if yes0 and not config.args.is_tg and nodeP:     # Если не по ТГ
                tr = nodeP.get('kodtr', None)

                if tr is None:
                    t2 = 70
#                    print(nodeP)
#                    exit(1)
                else:
                    tr = read_gid.map_tr.get(tr, None)
                    t2 = tr.get('T1_isl_2stup', 69)

                t2 = get_t2(nodeP, t)

                if debug: print('2 t2=', t2)

                Qz2 = (t - t2) * GG_Z/1000
                if Qz2 > 0: Qz = Qz2
            
            if yes0:
                if n == n2:
                    if debug: 
                        name1 = w_print.node_name(G, n1, False)
                        name2 = w_print.node_name(G, n2, False)
                        print(f'* &lt;{k} {name1} {name2} {GG_Z=:.4f} {Gout=:.4f} {Qz=:.4f} {t=:.2f} {t2=:.2f}')
                    i1 = G.nodes[n1]['num']
                    matrix[ii, i1] = GG_Z

                    B += Qz*1000

                    if debug2:
                        print(f'B += {Qz}*1000 = {B}       {Qz=:.4f}')

                else:       # вытекают
                    if debug: 
                        name1 = w_print.node_name(G, n1, False)
                        name2 = w_print.node_name(G, n2, False)
                        print(f'* &gt;{k} {name1} {name2} {GG_Z=:.4f} {Gout=:.4f}')

                    g += (GG_Z + Gout)

#            if not yes0 and Gout != 0:  # 
#                print(f'!! {name1} {name2} {Gout=} {yes=} {po1=} {po2=}')
#                print('------------------------------')

            if not yes0 and Gout != 0:  # 
                g += Gout

#            if not yes0 and po1 == 2:  # 
#                if g == 0:
#                    print(f'!! {name1} {name2} {yes=} {g=}')
                    


        if yes:    
            matrix[ii, k_n1] = -g
            beta[ii] = B
            if debug: print(f'   << {n_in}  >> {n_out} {ii=} {k_n1=}  --   {g=:.4f}  {B=:.4f}\n')
        else:
            if debug: 
                name = w_print.node_name(G, n, False)
                print('     !!', name)

            matrix[ii, k_n1] = 1
            beta[ii] = 0   # Это температура узла, куда не идет вода

        ii += 1

#        dt4 += (tt2_pt2-tt1_pt2)

#        print(f'{nnn1}:{nnn}     {kkkk1}  ==  {dt4}                         \r', end='')
        if teploYes and nnn1 % 100 == 0:
            print(f'{nnn1}:{nnn}                     \r', end='', file=sys.stderr)
        nnn1 += 1

    tt4 = time.time()


#        if debug:
#            exit(1)

#    print('Закончили')

    for n in G.nodes:
        node = G.nodes[n]
        t0 = node.get('t0', None)
        t0 = getZT(G, node, curT)

        if t0:  
            matrix[ii, ii] = 1
            beta[ii] = t0

            if debug:
                name1 = w_print.node_name(G, n, False)
                print(f'!    {name1}  --  {t0=}')

            ii += 1

    diag = matrix.diagonal()

    eps = 0.00000000001

    for i in range(nn):
        if diag[i] == 0:
            matrix[i, i] = eps

    matrix = sp.sparse.csc_array(matrix)


#    print(f'{tt4-tt3:.2f} ')


    return matrix, beta, n_ist

#-----------------------------------------------------------------------------------

# curT - это значит, что текущая температура


from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed



def teplo_pt(nodeP, Tn, debug1):
    GG = nodeP.get('G', 0)
    Gout = nodeP.get('Gout', 0)

    GG_Z = GG - Gout
    typ = nodeP.get('typ')

    t = nodeP.get('t', 150)
    t2 = t

    if typ =='realConsumers':
        t2, *qq = rasTO_pr2(nodeP, nodeP, nodeP, GG_Z, t, Tn, debug1)
    else:
        t2, *qq = rasTO_po2(nodeP, GG_Z, t, Tn, debug1)

#    print(nodeP, t2)

    return nodeP, t2


def check_pt(G, x, Tn):
    cprint('Проверка потребителей', color='green')

    pt_n = 0

    map_l = defaultdict(int)
    map_n = defaultdict(int)


    debug1 = False

    tt1 = time.time()


    nodes = list()


    for n in G.nodes:
#        name = w_print.node_name(G, n, False)

        nodeID, po1 = n
        
        node = G.nodes[n]
        k_n1 = G.nodes[n]['num']

        typ = node['typ']

        if typ in ('generalizedConsumers', 'realConsumers') and po1 == 1:
            pt_n += 1

            nodeP = G.nodes.get((nodeID, 1), None)
            nodeO = G.nodes.get((nodeID, 2), None)

            nn, t2 = teplo_pt(nodeP, Tn, debug1)
            nodes.append(nodeP)

#            print(f'{name} {t=} {GG=} {Gout=} {GG_Z=}')
#            exit(1)

        map_n[typ] += 1





    '''

    chunk_size = 1000  # Экспериментируйте
    chunk_size = 10  # Экспериментируйте
    chunks = [nodes[i:i + chunk_size] for i in range(0, len(nodes), chunk_size)]

#    print(chunks[0])
#    exit(1)


    # Функция для чанка (в отдельном файле или здесь)
    def process_chunk(chunk):
        return [teplo_pt(edge, Tn, debug1) for edge in chunk]

#    with ProcessPoolExecutor(max_workers=4) as executor:  # Число процессов = ядрам CPU
    with ThreadPoolExecutor(max_workers=4) as executor:  # Число процессов = ядрам CPU

        print('begin')

#        r = executor.submit(process_chunk, nodes)

        futures = [executor.submit(process_chunk, chunk) for chunk in chunks]
#        print('>>', futures)

        results = []
        for future in as_completed(futures):
            results.append(future.result())
#            print('>>', future.result())


    tt2 = time.time()

    print(f'Проверка {tt2-tt1:.2f}')


    for n in G.nodes:
        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 

            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            map_l[l_typ] += 1


#    print(f'Всего {pt_n} потребителей узлов')    
#    print(map_l)
#    print(map_n)

       '''

    tt2 = time.time()

    print(f'Проверка {tt2-tt1:.2f}')

#    print(f'{map_t}')
#    print(f'{map_pt_cnt}')
    

n_all_calc = 0





def calc_teplo(G, x, Tn, curT, teploYes0):
#    teploYes = False
    teploYes = True

#    check_pt(G, x, Tn)
#    return True

#    print('-----------------------------------------')
#    print('Расчет тепла')

    n_calc = 5

    for i in range(n_calc):
        if i == n_calc-1 and teploYes0:
            teploYes = True

        global n_all_calc
        n_all_calc += 1

        debug_yes = (n_all_calc in (1, 21))
        debug_yes = False


#        print(f'Шаг {i} Начали инициализацию ')

        tt1  = time.time()

        ret = init_matrix_teplo(G, x, Tn, curT, teploYes, debug_yes)

        tt2  = time.time()


#        print(f'Закончили инициализацию {tt2-tt1:.4f}')


#        print(f'Шаг {i+1}')

        if ret is None:
            return False

        matrix, beta, n_ist = ret

        if n_ist == 0:
            cprint('Во фрагменте нет источников тепла, тепловой расчет не производится', color='red')
            return False

#        w_print.print_matrix(matrix, beta)

#        t = sp.sparse.linalg.spsolve(matrix, beta)
        t, yes = safe_spsolve(matrix, beta)

        if not yes:
            return False

#        if not yes and False:
        if False:
            dump_system(matrix, beta, t, 200)

            ii = 0
            for n in G.nodes:
                name = w_print.node_name(G, n, False)
                print(f'{ii:5d}', name)
                ii += 1


 #           exit(1)
            

        ii = 0

        ## Проверка
#        debug_yes = False

        if debug_yes:
            print()
            dump_system(matrix, beta, t, 200)
            print()
#            w_print.print_matrix(matrix, beta)

        for n in G.nodes:
            num = G.nodes[n]['num']
#            name = w_print.node_name(G, n, False)
            G.nodes[n]['t'] = t[ii]

#            if 'ТК4= П' in name:
#                if i == n_calc-1:
#                    name = w_print.node_name(G, n, False)
#                    print('>', name, t[ii])

#            print(f'{ii:>5}', len(t), name, n_all_calc, ii, t[ii])


#            if t[ii] > 200 or t[ii] < 0 :
#                print(f'{ii:>5}', len(t), name, n_all_calc, ii, t[ii])

            if debug_yes:
                
                name = w_print.node_name(G, n, False)
                print(name, n_all_calc, ii, t[ii])

                for k, (n1, n2, key) in itertools.chain(
                        zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                        zip(itertools.repeat(2), G.out_edges(n, keys=True))
                        ): 

                        l = G.edges[n1, n2, key]

                        l_typ = l['typ']

                        k_l = l['num']
                        GG = x[k_l]

                        if abs(GG) > 0.00001: yes = True
                        if abs(GG) < 0.00001:
                            continue

                        
                        if GG < 0:
                            GG = -GG
                            n1, n2 = n2, n1

#                        name1 = w_print.node_name(G, n1, False)
#                        name2 = w_print.node_name(G, n2, False)

                        if n != n1 and n != n2:
                            print('!!!!!!!!!!!!')
                        
                        node1 = G.nodes[n1]

                        if n == n2:   # вытекает
                            node2 = G.nodes[n1]
                            tt = node2.get('t', 0)
                            Y = l.get('Y', 0)

                            dt = Y*1000/GG
#                             = (t - t2)
                                         
                            if dt > 1:
                                name1 = w_print.node_name(G, n1, False)
                                name2 = w_print.node_name(G, n2, False)
                                print(f'      {name1} -> {name2}  {GG=:.2f} {dt=:.2f} {tt=:.2f} {Y=:.2e}', l)

            if np.isnan(t[ii]):
                print(f'Какая-то ошибка t[{ii}] = {t[ii]}')
                exit(1)

            nn, po = n;

            ii += 1

        tt3  = time.time()
#        print(f'Закончили шаг {i} {tt3-tt2:.4f}')

    return True
