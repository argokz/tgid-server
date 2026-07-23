import networkx as nx

from sety import w_print
from sety import sopr
from sety import const

from sety.any.colors import cprint

#-----------------------------------------------------------------------------------

def read_RD(G, ut, ut2, nodeID1, nodeID2, externalSignLineID):
   
    name = w_print.line_name(G, nodeID1, nodeID2, externalSignLineID)

    nodeID = ut.get('nodeID', -1)
    przu = ut.get('przu', 1)
    sost = ut.get('sost', 1)
    kv = ut.get('kv', 0)

    r1 = ut.get('min_sm', 0.)
    r2 = ut.get('max_sm', 0.)

    otn_kv = ut.get('otn_kv', 0)

    if r1 == 0:
        if kv != 0.:
            r1 = 10. / kv / kv
        else:
            r1 = 1.e-6
            r1 = 1.e-8  # Это я исправил нужно проверить
            cprint('Не задана пропускная способность или миним. сопр.', color='yellow')
            cprint(f'регулятора [{name}] Значение берется по умолчанию', color='yellow')

    if r2 == 0:
        if kv * otn_kv != 0.:
            r2 = 1.0e+5 / kv / kv / otn_kv / otn_kv
        else:
            r2 = 1.0e+8 * r1
            if r1 == 1.e-8:    # Это я исправил нужно проверить
                r2 = 1.e+8

            cprint('Не задана относительная протечка или макс. сопр.', color='yellow')
            cprint(f'регулятора [{name}] Значение берется по умолчанию', color='yellow')

    node = G.nodes.get((nodeID, przu), None)
    if node:
        ut2['nodeID'] = nodeID
        ut2['przu'] = przu
        ut2['Z'] = ut.get('h_uzu', 0)

    else:    
        cprint(f'[yellow]В регуляторе [{name}] ', end='')
        if nodeID > 0:
            print(f' не найден узел с регулируемым напором {nodeID}', flush=True)
        else:
            print(' не задан узел с регулируемым напором', flush=True)
        cprint('[-]')

    if sost == 3:   # Неактивен
        r2 = r1

    if r1 == r2:
        S = r1
        ut2['fixed'] = True

    ut2['r1'] = r1
    ut2['r2'] = r2
    ut2['S'] = r1
    ut2['delta'] = ut.get('delta', 0.)
    ut2['sost'] = sost

#-----------------------------------------------------------------------------------

def read_RR(G, ut, ut2, nodeID1, nodeID2, externalSignLineID):
   
    name = w_print.line_name(G, nodeID1, nodeID2, externalSignLineID)

    q_zad = ut.get('q_zad', 0)
    kv = ut.get('kv', 0)
    r1 = ut.get('min_sm', 0.)
    r2 = ut.get('max_sm', 0.)
    sost = ut.get('sost', 1)
    otn_kv = ut.get('otn_kv', 0)
    
#    l->r1 = rr->min_sm
    if r1 == 0:
        if kv != 0:
            r1 = 10. / kv / kv
            if kv < q_zad:
                cprint(f'[yellow]Пропускная способность регулятора [{name}]')
                cprint('меньше требуемого регулируемого расхода регулятора[-]')
        else:
            r1 = 1.e-6
            r1 = 1.e-8  # Это я исправил нужно проверить
            cprint('[yellow]Не заданы миним. сопр. или пропускная способность')
            cprint(f'регулятора [{name}] Значение берется по умолчанию[-]')

    if r2 == 0:
        if kv * otn_kv != 0.:
            r2 = 1.0e+5 / kv / kv / otn_kv / otn_kv
        else:
            r2 = 1.0e+8 * r1
            if r1 == 1.e-8:    # Это я исправил нужно проверить
                r2 = 1.e+8
            cprint('[yellow]Не заданы макс. сопр. или относительная протечка')
            cprint(f'регулятора [{name}] Значение берется по умолчанию[-]')

    S = r1
    Z = q_zad
    
    if sost == 3:    # Неактивен
        r2 = r1

    if sost == 1:    # Открыт
        S = 10000

    if r1 == r2:
        S = r1
        ut2['fixed'] = True

    ut2['r1'] = r1
    ut2['r2'] = r2
    ut2['S'] = S
    ut2['Z'] = Z

#    cprint(f'==== {name} r1={r1} r2={r2}')

    ut2['delta'] = ut.get('delta', 0.)
    
    if Z == 0:
        sost = 2
    
    ut2['sost'] = sost

#    print('rr', ut2)

#-----------------------------------------------------------------------------------

def read_BP(G, ut, ut2, nodeID1, nodeID2, externalSignLineID):
   
    name = w_print.line_name(G, nodeID1, nodeID2, externalSignLineID)

#    print(ut)

    sost = ut.get('sost', 1)

    r1 = sopr.soprBP(ut)
    r2 = r1 * 1.0e+8

    delta = ut.get('delta', 0.)
    diam = ut.get('diam', 0)
    dln = ut.get('dln', 0)
    h = ut.get('h', 0)  #  Значение регулируемого напора 
    q = ut.get('q', 0)  #  Значение регулируемого расхода

    if sost == const.L_INACTIVE: r2 = r1

    nodeID = ut.get('nodeID', -1)
    przu = ut.get('przu', 1)

#    if node:
#        ut2['nodeID'] = nodeID
#        ut2['przu'] = przu

#    print('!!!!!!!!!')

    if nodeID >= 0:
        node = G.nodes.get((nodeID, przu), None)
        if node:
            ut2['nodeID'] = nodeID
            ut2['przu'] = przu

            Z = h
#            delta = delta_h
    else:
        Z = q

    if diam == 0:
        print(f'В байпасном участке [{name}]')
        print(f'не задан диаметр. Установлено значение по умолчанию 400 мм');

    if dln == 0:
        print(f'В байпасном участке [{name}]')
        print(f'не задан длина. Установлено значение по умолчанию 1 м');

    S = r1

    if nodeID <= 0:
        if sost == 1:    # Открыт
            S = 10000

    if sost == 3:    # Неактивен
        r2 = r1

    if r1 == r2:
        S = r1
        ut2['fixed'] = True

    ut2['r1'] = r1
    ut2['r2'] = r2
    ut2['S'] = S
    ut2['Z'] = Z

    ut2['delta'] = delta

#    if sost != 2:
#        print(ut)

    if Z == 0 and nodeID <= 0:
        sost = 2

    ut2['sost'] = sost

    ut2['diam'] = diam
    ut2['dlina'] = dln
    ut2['ustanovka'] = ut.get('ustanovka', '')

#    print(f'r1={r1} r2={r2}')
#    print('bp', sost, nodeID, ut2)

#-----------------------------------------------------------------------------------

# Регулятор перепада давления

def read_RP(G, ut, ut2, nodeID1, nodeID2, externalSignLineID):
    kv = ut.get('kv', 0)
    otn_kv = ut.get('otn_kv', 0)
    

    if kv != 0:
        r1 = 10. / kv / kv
    else:
        r1 = 1.e-6
#        wout << "Не заданы миним. сопр. или пропускная способность\n"
#        wout << "регулятора " << l->name_br() << endl

    if kv * otn_kv != 0.:
        r2 = 1.0e+5 / kv / kv / otn_kv / otn_kv
    else:
        r2 = 1.0e+8 * r1
#        wout << "Не заданы макс. сопр. или относительная протечка\n"
#        wout << "регулятора " << l->name_br() << endl
    '''

    l->n3 = m_graph->find(rp->nodeID, CPOD)
    l->n4 = m_graph->find(rp->nodeID, COBR)

    #  l->n3 = m_graph->find(rp->nodeID, rp->pipelineSignID == 1 ? CPOD : COBR)


    if (!l->n3) {
        wout << "В регуляторе " << l->name_br()
        if (rp->uzel_impulsa[0]) {
            wout << " не найден узел присоединения импульсной трубки " << name_br(rp->kod_impulsa, rp->uzel_impulsa) << endl
        }
        else {
            wout << " не задан узел присоединения импульсной трубки\n"
        }
    }

    if l->n3:
         l->Z = rp->h_regul

    l->S = l->r1
    if (rp->sost == MY_NEAKT || !l->n3) l->r2 = l->r1
    l->delta = rp->delta

    l->S_old = l->S
    l->r1_old = l->r1
    l->r2_old = l->r2

    return l->S != 0.
    '''

