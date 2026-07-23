import math
import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

#from termcolor import colored
#from termcolor import cprint
from sety.any.colors import cprint

ok_print = True
rd_print = True
ns_print = True

#------------------------------------------------------
def round2(v, d):
    if abs(v) >= 1: return round(v, d)
    if abs(v) >= 0.1: return round(v, d+1)
    if abs(v) >= 0.01: return round(v, d+2)
    if abs(v) >= 0.001: return round(v, d+3)
    return round(v, d+4)

def round_significant(number, digits):
    if number == 0:
        return 0
    shift = 10 ** (digits - 1 - int(math.floor(math.log10(abs(number)))))
    result = round(number * shift) / shift
    return float(f"{result:.{digits}g}")

#------------------------------------------------------
# Участки

def set_UT_out(G, ut, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
   
    r = x[l_n]
    h1 = x[n_n1]
    h2 = x[n_n2]
    S = ut['S']

    n_kon, po_kon = n2
    nom_kon = 1   # Это какой из узлов конечный 1 или 2

    if r < 0 and po_kon == 1 or r >= 0 and po_kon != 1:
        n_kon, po_kon = n2
        nom_kon = 2
    else:
        n_kon, po_kon = n1
        nom_kon = 1

    nP_kon = G.nodes.get((n_kon, 1), None)
    nO_kon = G.nodes.get((n_kon, 2), None)

    if nP_kon and nO_kon:
        pass
    else:
        id = ut['id']
        n1_obr = ut.get('n1_obr', None)
        n2_obr = ut.get('n2_obr', None)
        key_obr = ut.get('key_obr', None)

        ut_obr = G.edges.get((n1_obr, n2_obr, key_obr), None)

        if ut_obr:
            if nom_kon == 1:
                nP_kon = n1            
                nO_kon = n1_obr
            else:
                nP_kon = n2
                nO_kon = n2_obr

            if po_kon == 2:
                nP_kon, nO_kon = nO_kon, nP_kon

            nP_kon = G.nodes.get(nP_kon, None)
            nO_kon = G.nodes.get(nO_kon, None)
            
#            print('--------')
#            print(nP_kon)
#            print(nO_kon)

#@            print(ut_obr)
#            exit(0)


#        ut2 = G.edges.get((id, 2), None)

#        print('---', ut1)
#        print('---', ut2)
#        exit(0)
    if nP_kon and nO_kon:
        hP_kon = nP_kon.get('P', 0)
        hO_kon = nO_kon.get('P', 0)

        hP_geo = nP_kon.get('geoMarkTopTube', 0)

        ut['a18'] = hP_kon - hO_kon
        ut['a19'] = hP_kon
        ut['a21'] = hP_kon + hP_geo

#        ut['a19'] = x[nk->nP] - nk->h
#        ut['a20'] = nk->h
#        ut['a21'] = x[nk->nP]



#    name = w_print.line_name_n1_n2(G, n1, n2)
#    print('!!', name, x[l_n])

#    print(f'******* {n1} {po1} ***')
    
    if r != 0. and S != 0.:
        dh = abs((h2-h1)/S/r/r)-1

        if dh > 0.01 and abs(h1 - h2) > 1e-6:
            name = w_print.line_name_n1_n2(G, n1, n2)
            print('Невязка', name, dh, flush=True)
    
    truba = max(1, ut.get('truba', 1))
    dlina = ut.get('dlina', 1)
    diametr = ut.get('diametr', 1000)
    scher = ut.get('scher', 0.5)

    ut['a7'] = dlina
    ut['a8'] = diametr

    v = 0.785e-6 * diametr*diametr*dlina*truba

    ut['a9'] = v
    #  ut['nomer_m'] = l->nomer)

#    if l_n < 0: return

    p1 = abs(353.86 * x[l_n] / diametr / diametr / truba)


    ut['a10'] = round_significant(p1, 3)   # скорость

    if p1 != 0:
#        ut['a11'] = dlina / p1 / 3600.0
        ut['a11'] = dlina / p1 / 60.0  # минут

    ut['a13'] = x[l_n]        # Расход сетевой воды на участке
    ut['a12'] = ut['S']

    gs, lyam = sopr.gsprn(diametr, scher, ' ')
    gs /= (truba*truba)

    if ut.get('dolja') > 0.:
        rmn = gs * dlina*ut.get('dolja')
    else:
        rmn = gs * diametr / lyam / 1000.*ut.get('mestnoe')

    if l_n >= 0:
        ptrm = x[l_n] * x[l_n] * rmn

    ptro = abs(x[n_n1] - x[n_n2])

    ut['a14'] = (ptro - ptrm) / dlina*1000.
    ut['a15'] = ptro - ptrm
    ut['a16'] = ptrm
    ut['a17'] = ptro


#    print(ut)
    ut['b101'] = ut.get('b101')
    ut['b102'] = ut.get('b102')
    ut['b103'] = ut.get('b103')
    ut['b104'] = ut.get('b104')

    ut['y'] = ut.get('Y')  # тепловые потери

    if x[l_n] >= 0:
        nk = n_n2
    else:
        nk = n_n1




    '''

    n = m_graph->findPO(nk)
    if n:
        if nk->po() == COBR:
            nkO = nk; nkP = n;
        else:
            nkP = nk; nkO = n;
        if nkP->nP >= 0 && nkO->nP >= 0:
             ut['a18'] = (x[nkP->nP] - nkP->h) - (x[nkO->nP] - nkO->h));
    ''

    ut['a19'] = x[nk->nP] - nk->h
    ut['a20'] = nk->h
    ut['a21'] = x[nk->nP]

    ''
    ut['tpot'] = tpot[l_n])

    double t1, t2

    if x[l_n] >= 0:
        t1 = temp[n1->nP]
    else:
        t1 = temp[n2->nP]


    t2 = tpot[l_n] / fabs(x[l_n]) * 1000

    ut['t1'] = t1
    ut['t2'] = t2
    ut['qq'] = l->qq_t

    ptsum()->Ql_sum += tpot[l_n]
    if n1->po() == CPOD:
        ptsum()->Qlp_sum += tpot[l_n]
    else:
        ptsum()->Qlo_sum += tpot[l_n]

    const CNode *n1P = (x[l_n] >= 0) ? n1 : n2
    const CNode *n2P = (x[l_n] >= 0) ? n2 : n1

    const CNode *n1O = m_graph->findPO(n2P)

    double tt1 = temp[n1P->nP]
    double tt2 = n1O && n1O->nP >= 0 ? temp[n1O->nP] : tt1

    if tt1 < tt2:
        double t
        t = tt1 
        tt1 = tt2 
        tt2 = t

    double t

    if l->typ_pr != 4 /*'Н'*/:
        const CT *getCT()
        const CT *ct = getCT()

        if (t:
            t = t_zamP(l, tt1, tt2, ct->tg_god, diametr, Tn)
    else:
        t = t_zam(l, t1, 0, diametr, Tn)

    if (!getGlobal()->is_leto) ut['tzam'] = t

    '''

#------------------------------------------------------
# Насосы

def set_HC_out(G, ns, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
    geo1 = nn1.get('geoMarkTopTube', 0)
    geo2 = nn2.get('geoMarkTopTube', 0)

    qmax = ns.get('qmax', 0)
    k_nas = ns.get('k_nas', 0)

    '''
    const STN * stn = get_STN(ns->tip_nas)

    if (stn):
        writen0_NS_OUT_a9(ado, stn->h_min)
        writen0_NS_OUT_a10(ado, stn->q_min)
        writen0_NS_OUT_a11(ado, stn->h_max)
        writen0_NS_OUT_a12(ado, stn->q_max)
        '''

    ns['a18'] = ns.get('k_nas', 0)
    ns['a19'] = ns.get('tip_nas', 0)

    ns['a4'] = geo1
    ns['a8'] = geo2

    #  ns['nomer_m'] = l->nomer)

    if l_n < 0: return

    ns['a13'] = (x[n_n2] - geo2) - (x[n_n1] - geo1)

    ns['a14'] = x[l_n]
    ns['a15'] = x[n_n1] - geo1
    ns['a16'] = x[n_n2] - geo2

    R2NS = -3.e-9

    q = x[l_n]

    if ns.get('h') > 0.:
        a2 = ns.get('h')
        a3 = 0.
        a4 = R2NS
    else:
        a2 = ns.get('r0')
        a3 = ns.get('r1')

        if ns.get('r2', 0.) < 0.:
            a4 = ns.get('r2', 0.)
        else:
            a4 = R2NS

    if q < ns.get('qmin', 0) and q != 0.:
        if q > 0.:
            ns['a17'] = "недогруз"
        else:
            ns['a17'] = "противоток"

    elif (q > qmax*k_nas) and (a3 != 0.0 and a4 != 0.0):
        ns['a17'] = "перегруз"
    elif q == 0:
         ns['a17'] = "отключен"
    else: 
        ns['a17'] = "рабочая"

    name = w_print.line_name_n1_n2(G, n1, n2)

    if ns_print:
        if x[l_n] < 0:
            cprint(f'[red]Направление потока воды через насос {name}')
            cprint(f'   противоположно заданному !!! Расход {x[l_n]}[-]')

        if x[l_n] >  qmax*k_nas and qmax != 0:
            cprint(f'[red]Расход через насос {name} превышает')
            cprint(f'   его пропускную способность !!! Расход {x[l_n]}[-]')

#------------------------------------------------------
# Обратные клапаны

#def set_OK_out(G, ns, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
#    geo1 = nn1.get('geoMarkTopTube', 0)
#    geo2 = nn2.get('geoMarkTopTube', 0)
    
#    pass

#------------------------------------------------------

#MY_OK = 1
#MY_OTKL = 2
#MY_NEAKT = 3

def set_RD_out(G, rd, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2, node3, n3):

    geo1 = nn1.get('geoMarkTopTube', 0)
    geo2 = nn2.get('geoMarkTopTube', 0)
    S = rd.get('S')
    Z = rd.get('Z')

    r = x[l_n]
    h1 = x[n_n1]
    h2 = x[n_n2]

    S = abs(h2-h1)/r/r

    #  write_RS_OUT_kod3'] = rd->uzu_k
    #  write_RS_OUT_uzel3'] = rd->uzu
    #  write_RS_OUT_pr3'] = rd->przu

    rd['a4'] = geo1
    rd['a8'] = geo2

    #  rd['nomer_m'] = l_nomer)
#    if (l_n < 0 || !x) return

    rd['a11'] = x[l_n]
    rd['a12'] = S
    rd['a13'] = x[n_n1] - geo1
    rd['a14'] = x[n_n2] - geo2

    namel = w_print.line_name_n1_n2(G, n1, n2)
    namen = w_print.node_name(G, n3, False)

    typ = rd['typ']

    typ_name = 'Регулятор давления'
    if typ == 'bypass':
        typ_name = 'Байпас'

    if node3 is not None:
        l_n3 = node3.get('num', -1)
        geo3 = node3.get('geoMarkTopTube', 0)

        if l_n3 >= 0:
            dh = abs(x[l_n3] - (Z+geo3))
            delta = rd.get('delta')

            if delta < 0.1: delta = 0.1

            if rd_print:
#                print(f'dh={dh} delta={delta}')
#                cprint(f'   Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')
                
                if (dh > delta or delta == 0 and dh > 1) and rd.get('sost') != const.L_INACTIVE:
                    if abs(x[l_n]) > 0.001:
                        cprint(f'[yellow]{typ_name} {namel} не может обеспечить давление в узле {namen}')
                        cprint(f'   Задано {Z} получено {x[l_n3]-geo3:.2f}, сопротивление {S:.5f}, расход {r:.2f}[-]')
                    else:
                        pass
#                        cprint(f'[yellow]В регуляторе давления {namel} нет воды {namen}')
#                        cprint(f'  Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')
                else:
                    pass
#                    cprint(f'[green]Регулятор давления {namel} обеспечил давление в узле {namen}')
#                    cprint(f'  Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')

            rd['a15'] = "давление"

        #    rd['a16'] = rd.get('h_uzu')
            rd['a18'] = rd.get('delta')

            if l_n3 >= 0: 
                rd['a17'] = x[l_n3] - geo3

            if rd.get('sost') == const.L_CLOSED:
                rd['a19'] = "отключ."
            elif rd.get('sost') == const.L_INACTIVE:
                rd['a19'] = "неакт. "

            elif S <= rd.get('r1'):
                 rd['a19'] = "открыт "
            elif S >= rd.get('r2', 0.):
                 rd['a19'] = "закрыт "
            else: 
                rd['a19'] = "рабочее"

            if x[l_n] < 0.: 
                rd['a19'] = "реверс."

            if rd.get('sost') == const.L_OPEN and l_n3 >= 0:
                rd['dx'] = abs(rd.get('h_uzu', 0) - (x[l_n3] - geo3))
    else:
        if rd_print:
            cprint(f'[yellow]{typ_name} {namel} не задан узел с заданным напором')
            cprint(f'   Задано {Z:.2f}, сопротивление {S:.5f}, расход {r:.2f}[-]')

#------------------------------------------------------

def set_RR_out(G, rr, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
    geo1 = nn1.get('geoMarkTopTube', 0)
    geo2 = nn2.get('geoMarkTopTube', 0)
    
    r = x[l_n]
    Z = rr.get('Z')
    delta = rr.get('delta', 1)

    name = w_print.line_name_n1_n2(G, n1, n2)

    r = x[l_n]

#    print(rr['r1'], rr['r2'])

#    print(f'=== {name}  {rr.get('fixed')}' )

    if rr.get('sost') == const.L_OPEN and not rr.get('fixed', False):
        r += Z


    h1 = x[n_n1]
    h2 = x[n_n2]

#    S = abs(h2-h1)/r/r

    S = abs(h2-h1)/r/r

    rr['S'] = S
    rr['r'] = r
    rr['G'] = r

    rr['a4'] = geo1
    rr['a8'] = geo2

    rr['a11'] = x[l_n]
    rr['a12'] = S
    rr['a13'] = x[n_n1] - geo1
    rr['a14'] = x[n_n2] - geo2

    typ = rr['typ']

    typ_name = 'Регулятор расхода'
    if typ == 'bypass':
        typ_name = 'Байпас'

    if r < 0.:
        cprint(f'[red]Направление потока воды через {typ_name} {name}')
        cprint(f'   противоположно заданному !!! Задано {Z} получено {r}[-]')

    dh = abs(r - Z)

    if (dh > delta or (delta == 0 and dh > 1)) and rr.get('sost') != const.L_INACTIVE:
        if abs(r) > 0.001:
            cprint(f'[yellow] {typ_name}{name} не может обеспечить заданный расход')
            cprint(f'   Задано {Z:.2f} получено {r:.2f}[-], сопротивление {S:.5f}, перепад {h1-h2:.2f}')


#------------------------------------------------------

def diaf(q, h1, h2, r_min):

#    double diafr, dh;
#    /*   для расчета диафрагмы на байпасе  */
    dh = h1 - h2 - r_min * q*q

#    print(q, h1, h2, r_min, dh)


    diafr = 10 * math.sqrt(abs(q) / math.sqrt(abs(dh)))
    return diafr


#------------------------------------------------------
def set_BP_RD_out(G, rd, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2, node3, n3):
    geo1 = nn1.get('geoMarkTopTube', 0)
    geo2 = nn2.get('geoMarkTopTube', 0)
    
    r = x[l_n]
    Z = rd.get('Z')
    delta = rd.get('delta', 1)

    namel = w_print.line_name_n1_n2(G, n1, n2)
    namen = w_print.node_name(G, n3, False)

    r = x[l_n]

#    if rd.get('sost') == const.L_OPEN and not rd.get('fixed', False):
#        r += Z

    h1 = x[n_n1]
    h2 = x[n_n2]

    S = abs(h2-h1)/r/r

    rd['S'] = S
    rd['r'] = r
    rd['G'] = r

    rd['a4'] = geo1
    rd['a8'] = geo2

    r1 = rd.get('r1', 0)

    p1 = diaf(r, h1, h2, r1);
#    print(p1)


    rd['a4'] = geo1
    rd['a9'] = geo2

    rd['a5'] = h1-geo1
    rd['a10'] = h2-geo2

    rd['a11'] = p1
    rd['a18'] = h1-h2


    rd['a17'] = r1 * r*r


#    rd['a11'] = x[l_n]
#    rd['a12'] = S
#    rd['a13'] = x[n_n1] - geo1
#    rd['a14'] = x[n_n2] - geo2

    typ = rd['typ']

    typ_name = 'Байпас'

    '''
    if r < 0.:
        cprint(f'[red]Направление потока воды через {typ_name} {namel}')
        cprint(f'   противоположно заданному !!! Задано {Z} получено {r}[-]')

    dh = abs(r - Z)

    if (dh > delta or (delta == 0 and dh > 1)) and rd.get('sost') != const.L_INACTIVE:
        if abs(r) > 0.001:
            cprint(f'[yellow] {typ_name}{namel} не может обеспечить заданный расход')
            cprint(f'   Задано {Z} получено {r}[-], сопротивление {S}, перепад {h1-h2}')
            '''


    if node3 is not None:
        l_n3 = node3.get('num', -1)
        geo3 = node3.get('geoMarkTopTube', 0)

        if l_n3 >= 0:
            dh = abs(x[l_n3] - (Z+geo3))
            delta = rd.get('delta')

            if delta < 0.1: delta = 0.1

            if rd_print:
#                print(f'dh={dh} delta={delta}')
#                cprint(f'   Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')
                
                if (dh > delta or delta == 0 and dh > 1) and rd.get('sost') != const.L_INACTIVE:
                    if abs(x[l_n]) > 0.001:
                        cprint(f'[yellow]{typ_name} {namel} не может обеспечить давление в узле {namen}')
                        cprint(f'   Задано {Z:.2f} получено {x[l_n3]-geo3:.2f}, сопротивление {S:.5f}, расход {r:.2f}[-]')
                    else:
                        pass
#                        cprint(f'[yellow]В регуляторе давления {namel} нет воды {namen}')
#                        cprint(f'  Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')
                else:
                    pass
#                    cprint(f'[green]Регулятор давления {namel} обеспечил давление в узле {namen}')
#                    cprint(f'  Задано {Z} получено {x[l_n3]-geo3}, сопротивление {S}, расход {r}[-]')

            rd['a15'] = "давление"

        #    rd['a16'] = rd.get('h_uzu')
            rd['a18'] = rd.get('delta')

            if l_n3 >= 0: 
                rd['a17'] = x[l_n3] - geo3

#            if rd.get('sost') == const.L_CLOSED:
#                rd['a19'] = "отключ."
#            elif rd.get('sost') == const.L_INACTIVE:
#                rd['a19'] = "неакт. "

            elif S <= rd.get('r1'):
                 rd['a19'] = "открыт "
            elif S >= rd.get('r2', 0.):
                 rd['a19'] = "закрыт "
            else: 
                rd['a19'] = "рабочее"

            if x[l_n] < 0.: 
                rd['a19'] = "реверс."

            if rd.get('sost') == const.L_OPEN and l_n3 >= 0:
                rd['dx'] = abs(rd.get('h_uzu', 0) - (x[l_n3] - geo3))
    else:
        if rd_print:
            cprint(f'[yellow]{typ_name} {namel} не задан узел с заданным напором')
            cprint(f'   Задано {Z:.2f}, сопротивление {S:.5f}, расход {r:.2f}[-]')





#------------------------------------------------------
def set_BP_RR_out(G, rr, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
    geo1 = nn1.get('geoMarkTopTube', 0)
    geo2 = nn2.get('geoMarkTopTube', 0)
    
    r = x[l_n]
    Z = rr.get('Z')
    delta = rr.get('delta', 1)

    name = w_print.line_name_n1_n2(G, n1, n2)

    r = x[l_n]

    if rr.get('sost') == const.L_OPEN and not rr.get('fixed', False):
        r += Z

    h1 = x[n_n1]
    h2 = x[n_n2]

    S = abs(h2-h1)/r/r

    rr['S'] = S
    rr['r'] = r
    rr['G'] = r

    rr['a4'] = geo1
    rr['a8'] = geo2

    r1 = rr.get('r1', 0)

    p1 = diaf(r, h1, h2, r1);
#    print(p1)


    rr['a4'] = geo1
    rr['a9'] = geo2

    rr['a5'] = h1-geo1
    rr['a10'] = h2-geo2

    rr['a11'] = p1
    rr['a18'] = h1-h2


    rr['a17'] = r1 * r*r


#    rr['a11'] = x[l_n]
#    rr['a12'] = S
#    rr['a13'] = x[n_n1] - geo1
#    rr['a14'] = x[n_n2] - geo2

    typ = rr['typ']

    typ_name = 'Байпас'

    if r < 0.:
        cprint(f'[red]Направление потока воды через {typ_name} {name}')
        cprint(f'   противоположно заданному !!! Задано {Z:.2f} получено {r:.2f}[-]')

    dh = abs(r - Z)

    if (dh > delta or (delta == 0 and dh > 1)) and rr.get('sost') != const.L_INACTIVE:
        if abs(r) > 0.001:
            cprint(f'[yellow] {typ_name}{name} не может обеспечить заданный расход')
            cprint(f'   Задано {Z:.2f} получено {r:.2f}[-], сопротивление {S:.5f}, перепад {h1-h2:.2f}')

#------------------------------------------------------


def set_OK_out(G, ok, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2):
    r = x[l_n]

    name = w_print.line_name_n1_n2(G, n1, n2)

    ok['ras'] = r

    if ok_print:
        if r < 0.0001:
            cprint(f'Обратный клапан {name} закрыт', color='yellow')
        else:
            cprint(f'Обратный клапан {name} открыт, расход {r}', color='yellow')

#------------------------------------------------------

def set_G_out(G, x):
#    print('Запись результата началась', flush=True)
    
    for n in G.nodes:
        num = G.nodes[n]['num']
        geodez = G.nodes[n].get('geoMarkTopTube', 0)
        out = round(x[num] - geodez, 2)
        typ = G.nodes[n]['typ']
        
        if not np.isnan(out):
            G.nodes[n]['out'] = out
            G.nodes[n]['P'] = x[num] - geodez

#        if typ == 'realConsumers': #
#            print(G.nodes[n])
#            set_PT_out(G, n, x, num)
#            pass     

#        e = {key:val for key, val in e.items() if val is not np.nan}
#        name = G.nodes[n].get('name', None)
#        print('<<<', name, flush=True)

#        if name is None:
#            G.nodes[n]['name'] = ''


    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

#        print('!', n1, n2, e, flush=True)
        
        l_n = e['num']

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        n_n1 = nn1['num']
        n_n2 = nn2['num']

#        if e['externalSignLineID'] in (4, 5):
#            print('-----', e, flush=True)

        if np.isnan(x[l_n]):
            e['out'] = 0
            continue

        e['G'] = x[l_n]
        e['out'] = round(x[l_n], 2)

        typ = e['typ']

        nodeID3 = e.get('nodeID', 0)   
        przu3 = e.get('przu', 1)
        node3 = G.nodes.get((nodeID3, przu3), None)

        if typ == 'heatPipeSections':      # Участки
            set_UT_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
        elif typ == 'pumps':               # Насосы
            set_HC_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
        elif typ == 'reverseValves':       # OK Обратный клапан
            set_OK_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
        elif typ == 'consumptRegulators':  # RR
            set_RR_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
        elif typ == 'pressRegulators':     # RD
            set_RD_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2, node3, (nodeID3, przu3))

        elif typ == 'bypass' and nodeID3 != 0:     # Байпас, как регулятор давления
            set_BP_RD_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2, node3, (nodeID3, przu3))

        elif typ == 'bypass' and nodeID3 == 0:     # Байпас, как регулятор расхода
            set_BP_RR_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
        elif typ == 'dampers':             #
            pass

        elif typ == 'realConsumers':             #
#            set_UT_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
            name = w_print.line_name_n1_n2(G, n1, n2)

            r = x[l_n]
            h1 = x[n_n1]
            h2 = x[n_n2]
            S = e['S']
            S2 = (h1-h2)/r/r

#            print('!!!', name, h1, h2, r)

        elif typ == 'generalizedConsumers':             #
#            set_UT_out(G, e, x, l_n, n_n1, n_n2, nn1, nn2, n1, n2)
            pass
        
        elif typ == 'atm':             #
            pass
        elif typ == 'inner_line':             #
            pass
        elif typ in ('TO', 'EL', 'SO', 'VN', 'OO', 'OP', 'DR', 'ZD', 'UT'):             #
            pass
        else:    
            print(f'Не понял что за {typ}', flush=True)

#    print('Запись результата закончена', flush=True)
           
#------------------------------------------------------
