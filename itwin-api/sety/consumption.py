from sety import read_gid
from sety import w_print
from sety import config

from sety import read_tg
from sety.ct import get_ct
from sety.any.colors import cprint
from sety.read_zn import ec_ist


#-----------------------------------------------

#def check_ur_tr():

# Проверяем расход из обратки

def check_GO(po, pr_out, gO, gZ):
    
    if gZ < gO:
        if not po.get('error_go', False) :
            pt_name = get_pt_name(po)
            cprint(f'В потребителе [{pt_name}] водоразбор на ГВС из обратки невозможен, расход в обратке меньше требуемого на ГВС', color='red')
            po['error_go'] = True

        gO = gZ-0.1
        po['G_gvoo'] = gO

    return gO

def get_pt_name(pr):

    externalNodeName = pr.get('name', '')
    externalCodeID = pr.get('externalCodeID', 0)

#    print(pr, externalCodeID, externalNodeName)

    rs = read_gid.map_rs.get(externalCodeID, None)

    rs_name = '???'
    rs_name = ''
    if not rs is None:
        rs_name = rs.get('name', '')

    pt_name = f'{rs_name} {externalNodeName}'

    return pt_name


def get_tr(pr):
    tr = pr.get('kodtr', None)

    if not tr is None:
        tr = read_gid.map_tr.get(tr, None)

    if tr is None:
        pt_name = get_pt_name(pr)
        cprint(f'Не задан Код расчетных температур в потребителе [{pt_name}]', color='red')
        exit(1)

    return tr


def get_ur(pr):
    ur = pr.get('kodur', None)

    if not ur is None:
        ur = read_gid.map_ur.get(ur, None)

    if ur is None and not config.args.is_tg:
        pt_name = get_pt_name(pr)
        cprint(f'Не задан Код удельных расходов в потребителе [{pt_name}]', color='red')
        exit(1)

    return ur

def get_kv(pr):
    kv = pr.get('kodkv', None)

    if not kv is None:
        kv = read_gid.map_kv.get(kv, None)

    return kv


#-----------------------------------------------

def type_of_cons(cxema):
    isEl = True

    try:
        part = cxema.split('.')

        n1 = int(part[0])
        n2 = int(part[1])

        isEl = False
        if n2 == 5 or n2 == 6 or n2 == 7 or n2 == 8 or cxema == '1.3' or cxema == '1.4':
            otop = 'z' # Зависимая
            isEl = True

        elif n2 == 1 or n2 == 2 or n2 == 3 or n2 == 4:
            otop = 'z' # Зависимая
            isEl = False

        if n2 == 9 or n2 == 10 or n2 == 11 or n2 == 12 or cxema == '1.5' or cxema == '1.6':
            otop = 'n' # Независимая
            isEl = False

        if cxema[0] == 'С' or cxema[0] == 'C':
            otop = ''

        gv = ''

        if n1 == 5: gv = 'ps' 
        elif n1 == 4: gv = 'sm'
        elif n1 == 3: gv = 'pr'
        elif n1 == 15: gv = 'pw'
        elif n1 == 6: gv = 'op'
        elif n1 == 7: gv = 'oo'

        if gv != '': gvs_all = '1'

        vent = '0'

        if n1 > 2 and (n2 == 3 or n2 == 4 or n2 == 7 or n2 == 8 or n2 == 11 or n2 == 12 ) or n1 == 1 and (n2 == 2 or n2 == 4 or n2 == 6) or n1 == 2 and n2 == 1:
            vent = '1'

        rez = '0'
        if n1 > 2 and n2 % 2 == 0:
            rez = '1'

        return otop, vent, gv, rez, isEl

    except:
        pass



#-----------------------------------------------

def is_bezelevator(cxema):
    try:
        part = cxema.split('.')

        n1 = int(part[0])
        n2 = int(part[1])

        if n1 == 1:
            if n2 == 1 or n2 == 2:
                return True
        else:
            if n2 == 1 or n2 == 2 or n2 == 3 or n2 == 4:
                return True
    except:
        pass

    return False

#-----------------------------------------------

def is_rez(cxema):
    try:
        part = cxema.split('.')

        n1 = int(part[0])
        n2 = int(part[1])

        if n1 > 2 and n2 % 2 == 0:
            return True
    except:
        pass

    return False

#-----------------------------------------------


def get_beta_pr(pr):
    return 1.15
    '''

    avt = pt->pr_avtomat == 2 /*'А'*/

    if avt:
        #расчетный расход считается через максимальную нагрузку
        beta = pt->gvs_max
    else:
        #расчетный расход считается через балансовую нагрузку.
        # Qгвс_бал = 1.15*Qгвс_ср
        # 1.15 по умолчанию 
        beta = getS28()->pr  # 1.15
    return beta
    '''


def get_beta_sm(pr):
    return 1.1

    '''

    avt = pt->pr_avtomat == 2 # /*'А'*/

    if avt:
        beta = pt->gvs_max  # 1.2
    else:
        beta = getS28()->sm  # 1.1

    return beta
    '''

def error_tp(p):
    print('Error tp', p)
    exit(1)
    pass

def error_tp2(num, p, pt_name):
#    print('Error tp2', num, p)
#    cprint(f'Ошибка tp2 {num} в потребителе [{pt_name}]', color='red')
    if not p.get('error_tp2', False):
        cprint(f"Расчетные тепловые потери на входе в подающем трубопроводе потребителя [{pt_name}]", color='red')
        cprint("    несоизмеримы с его расчетной тепловой нагрузкой. Необходимо уточнить исходную", color='red')
        cprint("    информацию по расчетным нагрузкам, характеристикам подающего трубопровода потребителя.", color='red')
        cprint("    Расчетный расход данного потребителя рассчитывается без учета тепловых потерь.", color='red')
        p['error_tp2'] = True

#    exit(1)

def fatal_error():
    print('Fatal error', p)
    exit(1)
    pass

#-----------------------------------------------


def get_ist(externalCodeID):
    rs = read_gid.map_rs.get(externalCodeID)

    if rs is None:
        cprint(f'[red]Нет externalCodeID {externalCodeID}[-]')
        exit(1)
        
    heatSourceID = rs.get('heatSourceID', None)
    ist = read_gid.map_ist.get(heatSourceID, None)

    if not ist:
        heatSourceID = ec_ist.get(externalCodeID, None)
        ist = read_gid.map_ist.get(heatSourceID, None)

    if not ist:
        cprint(f'Нет источника тепла в расчетной схеме {rs.get('name', '')}!!! Считать по температурному графику невозможно', color='red')
        exit(1)

    return ist, heatSourceID

#-----------------------------------------------

def get_rs_name(externalCodeID):
    rs = read_gid.map_rs.get(externalCodeID)
    if rs is None:
        cprint(f'[red]Нет externalCodeID {externalCodeID}[-]')
        exit(1)

    rs_name = rs.get('name', '')
    return rs_name


#-----------------------------------------------

def ist_node_name(G, heatSourceID):
    nodeID = read_gid.map_ist2.get(heatSourceID, None)

    if nodeID is None: 
        ist = read_gid.map_ist.get(heatSourceID, None)
        if ist:        
            name = ist.get('name', heatSourceID)    
            return name
        else:
            return heatSourceID

    return w_print.node_name(G, (nodeID, 1), False)
        

#-----------------------------------------------

def consumption_tg(G, pr, pr_out, externalCodeID, externalNodeName):
    is_leto = False
    is_leto = config.args.is_leto

    debug = False
    
    if externalNodeName == 'Тестовый':
        debug = True


    if pr.get('name') == 'ТК4=':
#        print(pr)
        debug = True

    s28_ps = 1.25   #  1.25
    s28_pw = 1.25   #  1.25

    ct = get_ct()
#    Tn = config.args.Tn   # Температура наружного воздуха
#    print(ct)

    Tn_otop = ct.get('t_or')
    Tn_vent = ct.get('t_vr')
    ct_tx = ct.get('tx')


    tn_tip = 1

    avt = (pr.get('pr_avtomat', 0) == 2) #/*'А'*/

#    ist, heatSourceID = get_ist(externalCodeID)

    rs = read_gid.map_rs.get(externalCodeID)
    if rs is None:
#        cprint(f'Не задан Код Расчетной схемы {externalCodeID} в [{get_pt_name(pr)}]', color='red')
        cprint(f'Не задан Код Расчетной схемы в [{get_pt_name(pr)}]', color='red')
        exit(1)

    rs_name = rs.get('name', '')

    heatSourceID = pr.get('heatSourceID', None)
#    print(rs, heatSourceID)

    if heatSourceID is None or heatSourceID == 0:
        heatSourceID = rs.get('heatSourceID', None)
        pr['heatSourceID'] = heatSourceID
    else:
        pass

#    if heatSourceID is None or heatSourceID == 0:
#        for k, v in read_gid.map_ist.items():
#            print(k, v )
#        print(read_gid.map_ist.keys())
#        exit(1)


    ist = read_gid.map_ist.get(heatSourceID, None)

    if not ist:
        heatSourceID = ec_ist.get(externalCodeID, None)
        ist = read_gid.map_ist.get(heatSourceID, None)


    if not ist:
#        print(read_gid.map_ist)
        cprint(f'Нет Источника тепла в расчетной схеме {rs_name}! Расчет теплогидравлического режима невозможен', color='red')
#        cprint(f'Нет Источника тепла в расчетной схеме {rs_name} с номером {heatSourceID}! Считать по температурному графику невозможно', color='red')
        exit(1)

    tn_dt2v_posl = ist.get('dt2v_posl', 0)
    tn_t1pod_posll = ist.get('t1pod_posll', 0)
    t1_2r = ist.get('t1_2r', 0)
    tn_t2pod_parl = ist.get('t2pod_parl', 0)
    tn_t1pod_sm = ist.get('t1pod_sm', 0)
    tn_dt2_co = ist.get('dt2_co', 0)

    tn_izl = ist.get('tn_izl', 0)

    if avt:
        dt2v_sm = ist.get('dt2v_sm_avm', 0)   # 10
    else:
        dt2v_sm = ist.get('dt2v_sm_noavm', 0)   # 5

    v = read_tg.get_tg(heatSourceID, Tn_otop)

    if v is None:
        cprint(f'[red]Нет Температурного графика в Источнике {ist_node_name(G, heatSourceID)}[-]')
        exit(1)
        
    t1, t2, t3, tv = v
#    print(t1, t2, t3, tv)

    t1_1 = t1

    pt_name = f'{rs_name} {externalNodeName}'

    tr = get_tr(pr)

    tr_Tx = tr.get('Tx', 0)
#    print(tr_Tx)

#    cprint('[red]', Tn, t1, t2, t3, tv, '[-]')

    otopl_tp = 0
    pt_otoplz = pr_out.get('G_otoplz', 0)
    pt_otopln = pr_out.get('G_otopln', 0)
    pt_ventil = pr_out.get('G_ventil', 0)

    pt_gvsm = pr_out.get('G_gvsm', 0)
    pt_gvps = pr_out.get('G_gvps', 0)
    pt_gvpr = pr_out.get('G_gvpr', 0)
    pt_gvpw = pr_out.get('G_gvpw', 0)
    pt_gvop = pr_out.get('G_gvop', 0)
    pt_gvoo = pr_out.get('G_gvoo', 0)

    pr_Tr_gvs = pr.get('Tr_gvs', 60)

    pr_Tr_gvs_ps = pr.get('Tr_gvs_ps', pr_Tr_gvs)
    pr_Tr_gvs_pr = pr.get('Tr_gvs_pr', pr_Tr_gvs)
    pr_Tr_gvs_pw = pr.get('Tr_gvs_pw', pr_Tr_gvs)
    pr_Tr_gvs_sm = pr.get('Tr_gvs_sm', pr_Tr_gvs)

    pr_Tr_gvs_oo_op = pr.get('Tr_gvs_oo_op', pr_Tr_gvs)

#    tn_dt2_co = 0
    dt = 0

    G_kondiz = 0
    G_ventil = 0

    G_gvop = 0
    G_gvoo = 0
    G_gvpr = 0
    G_gvsm = 0
    G_gvps = 0
    G_gvpw = 0

    G_otopln = 0
    G_otoplz = 0

    dt = 0.

    is_teplopoter = True

    is_teplopoter = not config.args.no_teplopoter

    if is_teplopoter:
        nodeID = pr.get('nodeID', -1)
        nP = G.nodes.get((nodeID, 1), None)
        nO = G.nodes.get((nodeID, 2), None)
        
        if nP and nO:
            ist = read_gid.map_ist.get(heatSourceID, None)
            nIst = G.nodes.get((heatSourceID, 1), None)

            dt = 0

            tP = nP.get('t', None)

            if debug:
#                print(nP)
                print(f'< {tP=} {t1=}')


            if not tP is None:
    #            print(tP, t1)
                dt = t1-tP
                t1 = tP

        else:
            cprint(f'Какая-то странная ошибка, не должно быть такого {nodeID}', color='red')
            print(pr)
            exit(1)

        '''
#        CNode* n = nP
        int istn = getIsNode(pc->kod_ist)
        CNode* n_ist = m_graph->find(istn, CPOD)

        if not n_ist:
            double get_zn_t(int id, double Tdef)

            CNode * n_zn = getGlobal()->n_ZN
            if n_zn:
                t1 = get_zn_t(n_zn->id, n->T)
                dt = 0
                t1 = n->T
        else:
            if n_ist:
                long kod_ist = getIsKod(n_ist->id)
                double Tist = get_T1_ot(kod_ist)
                dt = Tist - n->T

            if n->T > 0:
                dt = 0
                t1 = n->T


       '''
    dt = 0


#---------------------------

    if pt_otoplz > 0 and not is_leto: # /* 14.10.2014 */) {
        G_otoplz = (pt_otoplz - otopl_tp) * 1000 / (t1 - t2)
#        print(f'=!=!= {pr.get('name')} {G_otoplz=:.4f} {t1=:.2f} {t2=:.2f}')


#        print('otoplz', pt_name, G_otoplz, pt_otoplz - otopl_tp, t1, t2)

#        if debug: 
#            print('==== G_otoplz', G_otoplz)
#            print('==== ', Tn_otop, pt_otoplz, otopl_tp, t1, t2)

        if G_otoplz < 0 and not is_leto:
#            print(f'Ошибка в потребителе [{rs_name} {externalNodeName}]')
#            print('!!')

#            print('==== G_otoplz', G_otoplz)
#            print('==== ', Tn_otop, pt_otoplz, otopl_tp, t1, t2)

            error_tp2(1, pr, pt_name)
            
#            exit(1)
#            print('otoplz=', pt_otoplz, 't1=', t1, 't2=', t2)
            G_otoplz = (pt_otoplz - otopl_tp) * 1000 / (t1_1 - t2)


#---------------------------

    if pt_otopln > 0 and not is_leto:

        G_otopln = (pt_otopln - otopl_tp) * 1000 / (t1 - dt - (t2 + tn_dt2_co))

        if debug:
            print(f'{G_otopln=} = ({pt_otopln=} - {otopl_tp=}) * 1000 / ({t1=} - {dt=} - ({t2=} + {tn_dt2_co=}))')



        if debug:
#            print(f' dt = {dt} pt_otopln={pt_otopln} otopl_tp={otopl_tp} t1={t1} dt={dt} t2={t2} tn_dt2_co={tn_dt2_co}')
            print(f'>>  t1={t1} dt={dt} t2={t2} tn_dt2_co={tn_dt2_co} G_otopln = {G_otopln} ')

        if G_otopln < 0 and not is_leto:
            '''
            print('pt_otopln = ', pt_otopln)
            print('tP = ', tP)
            print('t1_1 = ', t1_1)
            print('t1 = ', t1)
            print('t2 = ', t2)
            print('dt = ', dt)
            print('tn_dt2_co = ', tn_dt2_co)
            '''


            error_tp2(1, pr, pt_name)
#            exit(1)

#            error_tp(pr)
            G_otopln = (pt_otopln - otopl_tp) * 1000 / (t1_1 - (t2 + tn_dt2_co))
            #      fatal_error()
            # Убрал 4.06.2020

#---------------------------

#    is_teplopoter = False

    dt = 0  # Для зимнего периода по указанию Надежды Сергеевны
             # Только для отопления
    # Вентиляция


    if not is_teplopoter:
        
        if pt_ventil > 0 and not is_leto: # 14.10.2014 */
            if debug:
                print('>==pt_ventil =', pt_ventil)

            v = read_tg.get_tg(heatSourceID, Tn_vent)

            if v is None:
                cprint(f'[red]Нет Температурного графика в Источнике {ist_node_name(G, heatSourceID)}[-]')
                exit(1)
                    
            t1_v, t2_v, t3_v, tv_v = v

            G_ventil = pt_ventil * 1000 / (t1_v - dt - t2_v)



# Что-то странное

    else:


#        cprint('[red]Не доделали!!!![-]')
#        exit(1)    
        if pt_ventil > 0 and not is_leto: # /* 14.10.2014 */) {

        

            if debug:
                print('!==pt_ventil =', pt_ventil)
            
            
            k = 1
            G_ventil = pt_ventil * 1000 / (t1 - t2)  # t1 - текущее
      # добавил 04.06.2020
            if G_ventil < 0 and not is_leto:
#                print(f'Вениляция t1={t1} t2={t2}')

#                print('!2')

                error_tp2(2, pr, pt_name)
                G_ventil = pt_ventil * 1000 / (t1_1 - t2)

#                get_TG_ot(pc->kod_ist, t1, t2, t3, tv)
#                get_TG_vent(pc->kod_ist, t1vent, t2vent, t3vent, tvvent)

                v_ot = read_tg.get_tg(heatSourceID, Tn_otop)
                t1, t2, t3, tv = v_ot

                v_vent = read_tg.get_tg(heatSourceID, Tn_vent)
                t1vent, t2vent, t3vent, tvvent = v_vent
                

                k = (t1 - t2) / (t1vent - t2vent)

                k = 1

#            print('k=', k)

            G_ventil *= k

    if is_leto:
        pt_G_G_ventil = 0

#---------------------------

    if t1_2r == 0:
        # Tg при температуре начала отопит сезона

#        get_TG(pc->kod_ist, ct->t_vnew, t1_2r, tt2, tt3, ttv)
#        get_TG_new(pc->kod_ist, t1_2r, tt2, tt3, ttv)

        v = read_tg.get_tg(heatSourceID, ct.get('t_vnew'))
        if v is None:
            print('Не могу посчитать температуру')
            exit(1)

        t1_2r, tt2, tt3, ttv = v

        # тут был static

        '''
        is_mess = False
        if not is_mess and pt_gvsm + pt_gvpr + pt_gvps + pt_gvpw: 
            print(f'Не задана температура нижней срезки')
        is_mess = True
        '''


    if pt_gvpr != 0:
        beta = get_beta_pr(pr)

#'t2pod_parl': 't2pod_parl',  # Температура сет. воды в т.изл. темп.графика после подогревателя ГВ, при парал. схеме ГВ


        G_gvpr = pt_gvpr * beta * 1000 / (t1_2r - dt - tn_t2pod_parl)

#        print('gvpr', pt_name, G_gvpr, beta, beta * 1000 / (t1_2r - dt - tn_t2pod_parl))

        if G_gvpr < 0:
            G_gvpr = pt_gvpr * beta * 1000 / (t1_2r - tn_t2pod_parl)

            error_tp2(3, pr, pt_name)

    if pt_gvsm:
        v = read_tg.get_tg(heatSourceID, tn_izl)
        
        t1, t2, t3, tv = v


#        t_isl = get_T_ns(pc->kod_ist, t1_2r)
#        get_TG(pc->kod_ist, t_isl, t1, t2, t3, tv)

#        t1, t2, t3, tv
        # Тут нижняя срезка нужно исправить

#        get_TG_ns(pc->kod_ist, t1, t2, t3, tv)

        beta = get_beta_sm(pr)

        '''
beta=1.1
pr_Tr_gvs_sm=60.0
tn_t1pod_sm=41.7
dt2v_sm=5.0
tr_Tx=5.0
t1=130.0
tn_t1pod_sm=41.7
G_gvsm=9.158192978482445
{'k_akkuml': 32.0, 'pr_avar_TP': 3, 'kodur': 3938, 'kodtr': 3600, 'Tr_tv_co_zco': 18.0, 'cx_zco': 2, 'uf_zco': 1.29348, 'Tr_tv_co_nco': 18.0, 'uf_nco': 1.29348, 'gvs_max_pr': 1.2, 'T_pot_rez_pr': 40.0, 'Tr_tv_co_pr': 18.0, 'Tr_gvs_pr': 60.0, 'uf_zco_pr': 1.29348, 'otopl_sm': 6.0, 'gv_sm': 1.73534, 'gvs_max_sm': 1.2, 'T_pot_rez_sm': 40.0, 'Tr_tv_co_sm': 18.0, 'Tr_gvs_sm': 60.0, 'uf_zco_sm': 1.29348, 'gvs_max_ps': 1.2, 'T_pot_rez_ps': 40.0, 'Tr_tv_co_ps': 18.0, 'Tr_gvs_ps': 60.0, 'uf_zco_ps': 1.29348, 'gvs_max_pw': 1.2, 'T_pot_rez_pw': 40.0, 'Tr_tv_co_pw': 18.0, 'Tr_gvs_pw': 60.0, 'uf_zco_pw': 1.29348, 'gvs_max_o': 1.2, 'T_pot_rez_op': 40.0, 'Tr_gvs_oo_op': 60.0, 'a24': 13.3, 'a25': 5.5, 'gsz': 0.000608903, 'gszl': 0.000608903, 'gszpr': 1, 'gsoppr': 1, 'gsoopr': 1, 'prznz': 1, 'prznp': 1, 'przno': 1, 'pP': 66.0993, 'pO': 55.2928, 'G_otoplz': 104.644, 'G_gvsm': 28.5751, 'sost': 1}
{'gvop': 0, 'gvoo': 0, 'otoplz': 100.0, 'otopln': 0, 'ventil': 0, 'kondiz': 0, 'gvpr': 0, 'gvsm': 9.158192978482445, 'gvps': 0, 'gvpw': 0}
        
        '''


        G_gvsm = pt_gvsm * 1000 * beta * (pr_Tr_gvs_sm - tn_t1pod_sm + dt2v_sm) / (pr_Tr_gvs_sm - tr_Tx) / (t1 - dt - tn_t1pod_sm)

        if externalNodeName == '222/185453':
            print(f'beta={beta}')
            print(f'pr_Tr_gvs_sm={pr_Tr_gvs_sm}')
            print(f'tn_t1pod_sm={tn_t1pod_sm}')
            print(f'dt2v_sm={dt2v_sm}')
            print(f'tr_Tx={tr_Tx}')
            print(f't1={t1}')
            print(f'tn_t1pod_sm={tn_t1pod_sm}')
            print(f'G_gvsm={G_gvsm}')



        if G_gvsm < 0:
            G_gvsm = pt_gvsm * 1000 * beta * (pr_Tr_gvs_sm - tn_t1pod_sm + dt2v_sm) / (pr_Tr_gvs_sm - tr_Tx) / (t1 - tn_t1pod_sm)
            error_tp2(4, pr, pt_name)

    if pt_gvps:
        if tn_tip == 3 :  # /*'П'*/ Повышенный график, расход на ГВС = 0
            G_gvps = 0
        else:

            beta = s28_ps   #   1.25
            G_gvps = pt_gvps * 1000 * beta * (pr_Tr_gvs_ps - tn_t1pod_posll + tn_dt2v_posl) / (pr_Tr_gvs_ps - tr_Tx) / (t1_2r - dt - tn_t1pod_posll)
            if G_gvps < 0:
                G_gvps = pt_gvps * 1000 * beta * (pr_Tr_gvs_ps - tn_t1pod_posll + tn_dt2v_posl) / (pr_Tr_gvs_ps - tr_Tx) / (t1_2r - tn_t1pod_posll)
                error_tp2(5, pr, pt_name)

    if pt_gvpw:
        if tn_tip == 3: # /*'П'*/
            G_gvpw = 0
        else:
            beta = s28_pw   #  1.25
            G_gvpw = pt_gvpw * 1000 * beta / (t1_2r - dt - tn_t1pod_posll)
            if G_gvpw < 0:
                G_gvpw = pt_gvpw * 1000 * beta / (t1_2r - tn_t1pod_posll)
                error_tp2(6, pr, pt_name)

    '''

    if pr_out->sost != MY_OTKL and G_gvpr + G_gvps + G_gvpw + G_gvsm < 0:
        fatal_error()
        print(f'Температура обратной воды потребителя " << nP->getNameObBr()')
        print(f'в точке излома температурного графика выше подающей.')
        print(f'Скорректируйте значения вкладки "Точка излома ГВС"')
        print(f'температурного графика источника " << getIsName(pc->kod_ist)')
        '''

                                 #скорректир

    if (tn_tip == 2 or tn_tip == 4) and ((pt_gvop + pt_gvoo) > 0 and (pt_gvop + pt_gvoo) < 0.1 * (pt_otoplz + pt_otopln)):
        G_gvop = 0
        G_gvoo = 0
    else:
        if pt_gvop:
            G_gvop = pt_gvop * 1000 / (pr_Tr_gvs_oo_op - tr_Tx)
        if pt_gvoo:
            G_gvoo = pt_gvoo * 1000 / (pr_Tr_gvs_oo_op - tr_Tx)

        if G_gvop < 0:
            cprint(f'Ошибка при расчете [{pt_name}]. Неверная раcчетная температура горячей воды' , color='red') #, f'{pt_gvop} * 1000 / ({pr_Tr_gvs_oo_op} - {tr_Tx})')
#            exit(1)
#            cprint('Ошибка!!!' , color='red')


#        if debug:
#            print('G_gvop', G_gvop, 'G_gvoo', G_gvoo)


    '''
10.8965



    if (0 and ((pt_gvop + pt_gvoo) > 0 and (pt_gvop + pt_gvoo) < 0.1 * (pt_otoplz + pt_otopln))) {
        G_gvop = 0
        G_gvoo = 0
    }
    else {
        if (pt_gvop) {
            G_gvop = pt_gvop * 1000 / (pr_Tr_gvs - tr_Tx)
        }
        if (pt_gvoo) {
            G_gvoo = pt_gvoo * 1000 / (pr_Tr_gvs - tr_Tx)
        }
    }
'''

    #  G_rez = (G_gvop+G_gvoo)*pr_out->rez/100. # Рециркуляция для открытой ГВС

    #  G_rez = (pt_gvop+pt_gvoo)*pr_out->rez*1000/tr->T_pot_rez/100.
    # Исправили 21.02.2012 Надежда Ивановна

    # Расчет температуры остиывания
    # ct->tx -  Температура холодной воды из Системы теплоснабжения

    G_rez = 0

    pr_cxema = pr.get('cxema', 0)
    T_pot_rez = pr.get('T_pot_rez', 0)

    if is_bezelevator(pr_cxema):
        pr['uf'] = 0

    if is_rez(pr_cxema):
#        print(f'{t_ost} = ({pr_Tr_gvs} - {ct_tx}) - {T_pot_rez}')
        t_ost = (pr_Tr_gvs - ct_tx) - T_pot_rez
#        print(f'{t_ost} = ({pr_Tr_gvs} - {ct_tx}) - {T_pot_rez}')
#        G_rez = (pt_gvop + pt_gvoo) * pr_out->rez * 1000 / t_ost / 100.

    # Рециркуляцию считаеи по подаче и по обратке.
    # Почему-то в свое время только по подаче, непонятно почему

#        G_rez = (pt_gvop) * pr['rez'] * 1000 / t_ost / 100.
        G_rez = (pt_gvop + pt_gvoo) * pr.get('rez', 0) * 1000 / t_ost / 100.
 #       print(f'{G_rez}')

        if G_rez > 0 and t_ost <= 0:
            fatal_error()
            print(f'Температура в рециркуляционном трубопроводе воды потребителя {pt_name}')
            print(f'выше температуры на входе приборов ГВС')
            print(f'Недопустимый режим')

    pr_out2 = {}

    pr_out2['G_gvop'] = G_gvop
    pr_out2['G_gvoo'] = G_gvoo

    pr_out2['G_otoplz'] = G_otoplz
    pr_out2['G_otopln'] = G_otopln
    pr_out2['G_ventil'] = G_ventil
    pr_out2['G_kondiz'] = G_kondiz
    pr_out2['G_gvpr'] = G_gvpr
    pr_out2['G_gvsm'] = G_gvsm
    pr_out2['G_gvps'] = G_gvps
    pr_out2['G_gvpw'] = G_gvpw
    pr_out2['G_rez'] = G_rez

#    print(f'{pt_name} {G_rez}')

#    print(pr)
#    print(pr_out2)
#    exit(1)

#---------------------------

#    print(pt_otopln, pt_otoplz, '<------>', G_otopln, G_otoplz)

#    exit(1)

#    if debug: 
#        print(pr_out2)


    return pr_out2

#-----------------------------------------------

def set_kv(G, pr, kv, no_kv):

    if no_kv or kv is None: return pr

    kvpot = kv.get('kvpot', 0)

    if kvpot > 0:
        kv_otoplz = kvpot
        kv_otopln = kvpot
        kv_ventil = kvpot
        kv_kondiz = kvpot

        kv_txz = kvpot
        kv_txop = kvpot
        kv_txoo = kvpot
        kv_gvop = kvpot
        kv_gvoo = kvpot
        kv_gvz = kvpot
        kv_ut = kvpot
    else:
        kv_otoplz = kv.get('otoplz', 0)
        kv_otopln = kv.get('otopln', 0)
        kv_ventil = kv.get('ventil', 0)
        kv_kondiz = kv.get('kondiz', 0)

        kv_txz = kv.get('txz', 0)
        kv_txop = kv.get('txop', 0)
        kv_txoo = kv.get('txoo', 0)
        kv_gvop = kv.get('gvop', 0)
        kv_gvoo = kv.get('gvoo', 0)
        kv_gvz = kv.get('gvz', 0)
        kv_ut = kv.get('ut', 0)


#    if True:
#        kv_otoplz = kvpot
#        kv_otopln = 0
#        kv_ventil = 0
#        kv_kondiz = 0

#        kv_txz = 0
#        kv_txop = 0
#        kv_txoo = 9
#        kv_gvop = 0
#        kv_gvoo = 0
#        kv_gvz = 0

#    kv_gvop = 0
#    kv_gvoo = 0





#        if (getGlobal()->g_is_avar && !getGlobal()->g_equival):
#            if (kv_otoplz == 0) kv_otoplz = 0.0000001
#            if (kv_otopln == 0) kv_otopln = 0.0000001
#            if (kv_ventil == 0) kv_ventil = 0.0000001


    if 'otoplz' in pr: pr['otoplz'] *= kv_otoplz
    if 'otopln' in pr: pr['otopln'] *= kv_otopln
    if 'ventil' in pr: pr['ventil'] *= kv_ventil

    if 'kondiz' in pr: pr['kondiz'] *= kv_kondiz
    if 'txz' in pr: pr['txz'] *= kv_txz
    if 'txop' in pr: pr['txop'] *= kv_txop
    if 'txoo' in pr: pr['txoo'] *= kv_txoo
    if 'gvop' in pr: pr['gvop'] *= kv_gvop
    if 'gvoo' in pr: pr['gvoo'] *= kv_gvoo
    if 'gvps' in pr: pr['gvps'] *= kv_gvz
    if 'gvpw' in pr: pr['gvpw'] *= kv_gvz
    if 'gvpr' in pr: pr['gvpr'] *= kv_gvz
    if 'gvsm' in pr: pr['gvsm'] *= kv_gvz
    if 'utechp' in pr: pr['utechp'] *= kv_ut
    if 'utecho' in pr: pr['utecho'] *= kv_ut
  
#------------------------------------------------------

    if 'otopl_zco' in pr: pr['otopl_zco'] *= kv_otoplz
    if 'otopl_nco' in pr: pr['otopl_nco'] *= kv_otopln
    if 'ventil_cv' in pr: pr['ventil_cv'] *= kv_ventil
    if 'gv_op' in pr: pr['gv_op'] *= kv_gvop
    if 'gv_oo' in pr: pr['gv_oo'] *= kv_gvoo
    if 'gv_ps' in pr: pr['gv_ps'] *= kv_gvz
    if 'gv_pw' in pr: pr['gv_pw'] *= kv_gvz
    if 'gv_pr' in pr: pr['gv_pr'] *= kv_gvz
    if 'gv_sm' in pr: pr['gv_sm'] *= kv_gvz

    if 'otopl_ps' in pr: pr['otopl_ps'] *= (kv_otopln if pr.get('cx_co_ps', 0) == 3 else kv_otoplz)
    if 'otopl_pw' in pr: pr['otopl_pw'] *= (kv_otopln if pr.get('cx_co_pw', 0) == 3 else kv_otoplz)
    if 'otopl_pr' in pr: pr['otopl_pr'] *= (kv_otopln if pr.get('cx_co_pr', 0) == 3 else kv_otoplz)
    if 'otopl_sm' in pr: pr['otopl_sm'] *= (kv_otopln if pr.get('cx_co_sm', 0) == 3 else kv_otoplz)

    ## Поля в ПО как в ПР
##    if 'kondiz' in pr: pr['kondiz'] *= kv_kondiz
##    if 'txz' in pr: pr['txz'] *= kv_txz
##    if 'txop' in pr: pr['txop'] *= kv_txop
##    if 'txoo' in pr: pr['txoo'] *= kv_txoo
##    if 'utechp' in pr: pr['utechp'] *= kv_ut
##    if 'utecho' in pr: pr['utecho'] *= kv_ut



    return pr

#-----------------------------------------------


def kv_ur(G, pr, pr_out, ur, kv, externalCodeID, externalNodeName, is_tg, no_kv):

    if is_tg:
        # Считаем через ТГ
        pr_out = consumption_tg(G, pr, pr_out, externalCodeID, externalNodeName)

    else:
        if ur is None:
            rs_name = get_rs_name(externalCodeID)
            if True:
                cprint(f'Ошибка, не заданы Удельные расходы в потребителе [{rs_name} {externalNodeName}]', color='red')
                return None

#        print('!!!!', pr_out)

        # считаем по УР
        pr_out['G_gvop'] *= ur.get('gvo', 0)
        pr_out['G_gvoo'] *= ur.get('gvo', 0) 

        pr_out['G_otoplz'] *= ur.get('otoplz', 0)
        pr_out['G_otopln'] *= ur.get('otopln', 0)
        pr_out['G_ventil'] *= ur.get('ventil', 0)
        pr_out['G_kondiz'] *= ur.get('kondiz', 0)
        pr_out['G_gvpr'] *= ur.get('gvpr', 0)
        pr_out['G_gvsm'] *= ur.get('gvsm', 0)
        pr_out['G_gvps'] *= ur.get('gvps', 0)
        pr_out['G_gvpw'] *= ur.get('gvpw', 0)

        ur_rez = ur.get('rez', 0)
        gvop = pr.get('gvop', 0)
        gvoo = pr.get('gvoo', 0)

        pr_out['G_rez'] *= (gvop + gvoo) * ur_rez / 100.

#        print('>>>>>>>>>>>>>', externalNodeName, pr_out['G_rez'], gvop + gvoo, ur_rez)


    return pr_out

#-----------------------------------------------
def consumption_pr(G, pr, externalCodeID, externalNodeName, kv_yes, debug=False):
#    if debug:
#        print('1-----', pr)

    tr = get_tr(pr)
    ur = get_ur(pr)
    kv = get_kv(pr)

    pr = set_kv(G, pr, kv, config.args.no_kv or not kv_yes)

    pr_sost = pr.get('sost', 0)

    if pr_sost != 1:
        return 0., 0., 0., 0., 0., 0.,None, pr

#    if debug:
#        print('2-----', pr)


    pr_out = {}
    pr_out['G_otoplz'] = pr.get('otoplz', 0)
    pr_out['G_otopln'] = pr.get('otopln', 0)
    pr_out['G_ventil'] = pr.get('ventil', 0)
    pr_out['G_kondiz'] = pr.get('kondiz', 0)
    pr_out['G_txz'] = pr.get('txz', 0)
    pr_out['G_txop'] = pr.get('txop', 0)
    pr_out['G_txoo'] = pr.get('txoo', 0)
    pr_out['G_gvop'] = pr.get('gvop', 0)
    pr_out['G_gvoo'] = pr.get('gvoo', 0)
    pr_out['G_gvpr'] = pr.get('gvpr', 0)
    pr_out['G_gvsm'] = pr.get('gvsm', 0)
    pr_out['G_gvps'] = pr.get('gvps', 0)
    pr_out['G_gvpw'] = pr.get('gvpw', 0)
    pr_out['G_rez'] = pr.get('rez', 0)


    Qp = pr.get('gvop', 0)+pr.get('txop', 0)
    Qo = pr.get('gvoo', 0)+pr.get('txoo', 0)

    Qz = pr.get('otoplz', 0)+pr.get('otopln', 0)+pr.get('ventil', 0)+pr.get('kondiz', 0)+pr.get('txz', 0)+pr.get('gvpr', 0)+pr.get('gvsm', 0)+pr.get('gvps', 0)+pr.get('gvpw', 0)

    pr_out = kv_ur(G, pr, pr_out, ur, kv, externalCodeID, externalNodeName, config.args.is_tg, config.args.no_kv)


    Qot = pr.get('otoplz', 0) + pr.get('otopln', 0)
    Qvent = pr.get('ventil', 0)
    Qgvz = pr.get('gvpr', 0)+pr.get('gvsm', 0)+pr.get('gvps', 0)+pr.get('gvpw', 0)
    Qgvp = pr.get('gvop', 0)
    Qgvo = pr.get('gvoo', 0)

    pr_out['Qot0'] = Qot  
    pr_out['Qvent0'] = Qvent
    pr_out['Qgvz0'] = Qgvz 
    pr_out['Qgvp0'] = Qgvp 
    pr_out['Qgvo0'] = Qgvo 

    ot = pr_out.get('G_otoplz', 0) + pr_out.get('G_otopln', 0)

    if pr_out.get('G_gvpr', 0) != 0: pr_out['G_ot_pr'] = ot
    if pr_out.get('G_gvps', 0) != 0: pr_out['G_ot_ps'] = ot
    if pr_out.get('G_gvpw', 0) != 0: pr_out['G_ot_pw'] = ot
    if pr_out.get('G_gvsm', 0) != 0: pr_out['G_ot_sm'] = ot


    if pr_out is None:
        print('!')
        exit(1)
        return 0., 0., 0., 0., 0., 0.,None, pr


    gP = pr_out['G_gvop']
    gO = pr_out['G_gvoo']
    gZ = (
        pr_out['G_otoplz']+pr_out['G_otopln']+pr_out['G_ventil']+pr_out['G_kondiz']+
        pr_out['G_gvpr']+pr_out['G_gvsm']+pr_out['G_gvps']+pr_out['G_gvpw']
        )


    gO = check_GO(pr, pr_out, gO, gZ)

    if pr.get('gvop', 0) > 0:
        gZ += pr_out['G_rez']

#    print(gZ, gP, gO, Qz, Qp, Qo, pr_out)
#    print(pr_out['G_otoplz'])

    '''
    if gZ < gO:
        pt_name = get_pt_name(pr)
        if not pr.get('error', False) :
            cprint(f'В потребителе [{pt_name}] водоразбор на ГВС из обратки невозможен, расход в обратке меньше требуемого на ГВС', color='red')
            pr['error'] = True

        gO = gZ
        pr['G_gvoo'] = gO
        '''

    return gZ, gP, gO, Qz, Qp, Qo, pr_out, pr

#-----------------------------------------------
'''
1   элеваторная зависимая   У   1
2   безэлеваторная зависимая    2
3   независимая Н   3
'''
"""
def make_pr(po, ps):
    pr = {}

    cx = po.get(f'cx_co_{ps}', 1)   #  Схема присоединения СО
    if cx == 3:
        pr['otopln'] = po.get(f'otopl_{ps}', 0)
    else:
        pr['otoplz'] = po.get(f'otopl_{ps}', 0)
    pr[f'gv{ps}'] = po.get(f'gv_{ps}', 0)

    print(pr)

    return pr



def make_pr_op(po, ps):
    pr = {}

    pr['otopln'] = po.get(f'otopl_{ps}', 0)
    pr['otoplz'] = po.get(f'otopl_{ps}', 0)

    pr[f'gv{ps}'] = po.get(f'gv_{ps}', 0)

    print(pr)

    return pr




def po_to_pr(po):
    pr_ps = make_pr(po, 'ps')
    pr_sm = make_pr(po, 'sm')
    pr_pw = make_pr(po, 'pw')
    pr_pr = make_pr(po, 'pr')

    pr_op = make_pr_op(po, 'op')
    pr_oo = make_pr_oo(po, 'oo')


    return pr_ps, pr_sm, pr_ps, pr_pw

"""

#-----------------------------------------------


def set_po_typ(po, typ1, typ2):
    if typ1 != typ2:
        if po.get(f'gv_{typ1}', 0) != 0 or po.get(f'otopl_{typ1}', 0) != 0:

            po[f'otopl_{typ2}'] =   po.get(f'otopl_{typ1}', 0)
            po[f'cx_co_{typ2}'] =   po.get(f'cx_co_{typ1}', 0)
            po[f'gv_{typ2}'] =      po.get(f'gv_{typ1}', 0)
            po[f'rez_{typ2}'] =     po.get(f'rez_{typ1}', 0)
            
            
            po[f'otopl_{typ1}'] = 0
            po[f'cx_co_{typ1}'] = 0
            po[f'gv_{typ1}'] = 0
            po[f'rez_{typ1}'] = 0

    return po

def set_po_otopl_typ(po, typ1, typ2):
    if po.get(f'otopl_{typ1}co', 0) != 0:
        po[f'otopl_{typ2}co'] = po.get(f'otopl_{typ1}co', 0)
        po[f'otopl_{typ1}co'] = 0

    for t in ['sm', 'ps', 'pr', 'pw']:
        if typ2 == 'z':
            po[f'cx_co_{t}'] = 1
        else:
            po[f'cx_co_{t}'] = 3
    
    
    return po



def consumption_po(G, po, externalCodeID, externalNodeName, kv_yes, debug=False):

    tr = get_tr(po)
    ur = get_ur(po)
    kv = get_kv(po)

    po = set_kv(G, po, kv, config.args.no_kv or not kv_yes)


    po_sost = po.get('sost', 1)   #  Состояние потребителя

    if po_sost != 1:
        return 0., 0., 0., 0., 0., 0.,None, po

    po_otopl_zco = po.get('otopl_zco', 0)   #  Расчетная тепловая нагрузка на  отопление
    po_otopl_nco = po.get('otopl_nco', 0)   #  Расчетная тепловая нагрузка на  отопление
    po_ventil_cv = po.get('ventil_cv', 0)   #  Расчетная тепловая нагрузка  на вентиляцию
    po_kondiz = po.get('kondiz', 0)   #  Расчетная тепловая нагрузка на кондиционирование
    po_txz = po.get('txz', 0)   #  Расчетная тепловая нагрузка на технологию в закрытой системе
    po_txop = po.get('txop', 0)   #  Средняя нагрузка на технологию в открытой системе из подающего теплопровода
    po_txoo = po.get('txoo', 0)   #  Средняя нагрузка на технологию в открытой системе из обратного теплопровода

    po_otopl_pr = po.get('otopl_pr', 0)   #  Расчетная тепловая нагрузка на отопление
    po_cx_co_pr = po.get('cx_co_pr', 1)   #  Схема присоединения СО
    po_gv_pr = po.get('gv_pr', 0)   #  Средняя тепловая нагрузка на ГВС
    po_rez_pr = po.get('rez_pr', 0)   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    
    po_otopl_sm = po.get('otopl_sm', 0)   #  Расчетная тепловая нагрузка на  отопление
    po_cx_co_sm = po.get('cx_co_sm', 1)   #  Схема присоединения системы отопления
    po_gv_sm = po.get('gv_sm', 0)   #  Средняя тепловая нагрузка на ГВС.
    po_rez_sm = po.get('rez_sm', 0)   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС

    po_otopl_ps = po.get('otopl_ps', 0)   #  Расчетная тепловая нагрузка на  отопление
    po_cx_co_ps = po.get('cx_co_ps', 1)   #  Схема присоединения системы отопления
    po_gv_ps = po.get('gv_ps', 0)   #  Средняя тепловая нагрузка на ГВС
    po_rez_ps = po.get('rez_ps', 0)   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    
    po_otopl_pw = po.get('otopl_pw', 0)   #  Расчетная тепловая нагрузка на  отопление
    po_cx_co_pw = po.get('cx_co_pw', 1)   #  Схема присоединения системы отопления
    po_gv_pw = po.get('gv_pw', 0)   #  Средняя тепловая нагрузка на ГВС
    po_rez_pw = po.get('rez_pw', 0)   #  Расчетная тепл.нагрузка на компенсацию тепл.потерь в цирк.труб.ГВС
    
    po_gv_op = po.get('gv_op', 0)   #  Средняя тепловая нагрузка на ГВС, подающий трубопровод
    po_gv_oo = po.get('gv_oo', 0)   #  Средняя тепловая нагрузка на ГВС, обратный трубопровод
    po_utechp = po.get('utechp', 0)   #  Заданная утечка из подающего трубопровода
    po_utecho = po.get('utecho', 0)   #  Заданная утечка из обратного  трубопровода



    pr_out = {}
    pr_out['G_ventil'] = po_ventil_cv
    pr_out['G_kondiz'] = po_kondiz

#    pr_out['G_otoplz'] = po_otopl_zco


#    print('>>>', externalNodeName, po_otopl_zco)

    pr_out['G_otopln'] = po_otopl_nco
    pr_out['G_otoplz'] = po_otopl_zco

    pr_out['G_otopln0'] = po_otopl_nco
    pr_out['G_otoplz0'] = po_otopl_zco


    #1  элеваторная зависимая   У   
    #2  безэлеваторная зависимая    
    #3  независимая Н   

    if po_cx_co_pr != 3: pr_out['G_otoplz'] += po_otopl_pr
    if po_cx_co_sm != 3: pr_out['G_otoplz'] += po_otopl_sm
    if po_cx_co_ps != 3: pr_out['G_otoplz'] += po_otopl_ps 
    if po_cx_co_pw != 3: pr_out['G_otoplz'] += po_otopl_pw 

    if po_cx_co_pr == 3: pr_out['G_otopln'] += po_otopl_pr 
    if po_cx_co_sm == 3: pr_out['G_otopln'] += po_otopl_sm 
    if po_cx_co_ps == 3: pr_out['G_otopln'] += po_otopl_ps 
    if po_cx_co_pw == 3: pr_out['G_otopln'] += po_otopl_pw 


#    print(externalNodeName, 'z', pr_out['G_otoplz'])

    pr_out['G_ot_pr'] = po_otopl_pr 
    pr_out['G_ot_sm'] = po_otopl_sm 
    pr_out['G_ot_ps'] = po_otopl_ps 
    pr_out['G_ot_pw'] = po_otopl_pw 

    pr_out['G_gvpr'] = po_gv_pr
    pr_out['G_gvsm'] = po_gv_sm
    pr_out['G_gvps'] = po_gv_ps

    pr_out['G_gvpw'] = po_gv_pw

    pr_out['G_gvop'] = po_gv_op
    pr_out['G_gvoo'] = po_gv_oo     

    pr_out['G_rez'] = 0


    Qp = pr_out['G_gvop']
    Qo = pr_out['G_gvoo']

    Qz = (pr_out['G_otoplz'] + pr_out['G_otopln'] + pr_out['G_ventil']
#            + pr_out['G_kondiz'] + pr.get('txz', 0) 
            + pr_out['G_gvpr']
            + pr_out['G_gvsm'] + pr_out['G_gvps'] + pr_out['G_gvpw']
            )


#    if externalNodeName == '15.4_O':
#        print(pr_out)

    Q_ot_pr = pr_out.get('G_ot_pr', 0)
    Q_ot_ps = pr_out.get('G_ot_ps', 0)
    Q_ot_pw = pr_out.get('G_ot_pw', 0)
    Q_ot_sm = pr_out.get('G_ot_sm', 0)

    Q_ot = Q_ot_pr + Q_ot_ps + Q_ot_pw + Q_ot_sm

    pr_out = kv_ur(G, po, pr_out, ur, kv, externalCodeID, externalNodeName, config.args.is_tg, config.args.no_kv)

    ''' Это для лета!!!!
    if Q_ot > 0:
#        if externalNodeName == '15.4_O':
#            print(Q_ot)
        
        G_otopl = pr_out.get('G_otoplz') + pr_out.get('G_otopln')

        pr_out['G_ot_pr'] = G_otopl*Q_ot_pr/Q_ot
        pr_out['G_ot_ps'] = G_otopl*Q_ot_ps/Q_ot
        pr_out['G_ot_pw'] = G_otopl*Q_ot_pw/Q_ot
        pr_out['G_ot_sm'] = G_otopl*Q_ot_sm/Q_ot
        '''

    """
    Q_ot0 = Q_ot_pr + Q_ot_ps + Q_ot_pw + Q_ot_sm + po_otopl_zco + po_otopl_nco

    if Q_ot0 > 0:
        G_otopl = pr_out.get('G_otoplz') + pr_out.get('G_otopln')

        pr_out['G_ot_pr'] = G_otopl*Q_ot_pr/Q_ot0
        pr_out['G_ot_ps'] = G_otopl*Q_ot_ps/Q_ot0
        pr_out['G_ot_pw'] = G_otopl*Q_ot_pw/Q_ot0
        pr_out['G_ot_sm'] = G_otopl*Q_ot_sm/Q_ot0

        print('(+)', externalNodeName, pr_out['G_ot_pr'], pr_out['G_otoplz'], pr_out['G_otopln'])
        """

    Q_otz0 = po_otopl_zco
    if po_cx_co_pr != 3:
        Q_otz0 += Q_ot_pr
    if po_cx_co_ps != 3:
        Q_otz0 += Q_ot_ps
    if po_cx_co_pw != 3:
        Q_otz0 += Q_ot_pw
    if po_cx_co_sm != 3:
        Q_otz0 += Q_ot_sm

    Q_otn0 = po_otopl_nco
    if po_cx_co_pr == 3:
        Q_otn0 += Q_ot_pr
    if po_cx_co_ps == 3:
        Q_otn0 += Q_ot_ps
    if po_cx_co_pw == 3:
        Q_otn0 += Q_ot_pw
    if po_cx_co_sm == 3:
        Q_otn0 += Q_ot_sm

    if Q_otz0 > 0:
        G_otopl = pr_out.get('G_otoplz')

        if po_cx_co_pr != 3:
            pr_out['G_ot_pr'] = G_otopl*Q_ot_pr/Q_otz0
        if po_cx_co_ps != 3:
            pr_out['G_ot_ps'] = G_otopl*Q_ot_ps/Q_otz0
        if po_cx_co_pw != 3:
            pr_out['G_ot_pw'] = G_otopl*Q_ot_pw/Q_otz0
        if po_cx_co_sm != 3:
            pr_out['G_ot_sm'] = G_otopl*Q_ot_sm/Q_otz0

    if Q_otn0 > 0:
        G_otopl = pr_out.get('G_otopln')

        if po_cx_co_pr == 3:
            pr_out['G_ot_pr'] = G_otopl*Q_ot_pr/Q_otn0
        if po_cx_co_ps == 3:
            pr_out['G_ot_ps'] = G_otopl*Q_ot_ps/Q_otn0
        if po_cx_co_pw == 3:
            pr_out['G_ot_pw'] = G_otopl*Q_ot_pw/Q_otn0
        if po_cx_co_sm == 3:
            pr_out['G_ot_sm'] = G_otopl*Q_ot_sm/Q_otn0



#        if externalNodeName == '5.5':
#            print(f'{G_otopl}*{Q_ot_ps}/{Q_ot0}')
#            exit(1)



#        if externalNodeName == '15.4_O':
#            print(pr_out)

    if pr_out is None:
        return 0., 0., 0., 0., 0., 0.,None, po

    gP = pr_out['G_gvop']
    gO = pr_out['G_gvoo']
    gZ = (
        pr_out['G_otoplz']+pr_out['G_otopln']+pr_out['G_ventil']+pr_out['G_kondiz']+
        pr_out['G_gvpr']+pr_out['G_gvsm']+pr_out['G_gvps']+pr_out['G_gvpw']
        )

    gO = check_GO(po, pr_out, gO, gZ)
        
    Qot = po_otopl_zco + po_otopl_nco + po_otopl_pr + po_otopl_ps + po_otopl_pw + po_otopl_sm
    
    Qvent = po_ventil_cv
    Qgvz = po_gv_pr + po_gv_ps + po_gv_pw + po_gv_sm
    Qgvp = po_gv_op
    Qgvo = po_gv_oo

    pr_out['Qot'] = Qot  
    pr_out['Qvent'] = Qvent
    pr_out['Qgvz'] = Qgvz 
    pr_out['Qgvp'] = Qgvp 
    pr_out['Qgvo'] = Qgvo 

    pr_out['Qot0'] = Qot  
    pr_out['Qvent0'] = Qvent
    pr_out['Qgvz0'] = Qgvz 
    pr_out['Qgvp0'] = Qgvp 
    pr_out['Qgvo0'] = Qgvo 



#    print(externalNodeName, pr_out.get('G_otopln', 0))

    '''
    if gZ < gO:
        if not po.get('error', False) :
            pt_name = get_pt_name(po)
            cprint(f'В потребителе [{pt_name}] водоразбор на ГВС из обратки невозможен, расход в обратке меньше требуемого на ГВС', color='red')
            po['error'] = True

        gO = gZ
        pr['G_gvoo'] = gO

        '''

    return gZ, gP, gO, Qz, Qp, Qo, pr_out, po
    
#-----------------------------------------------
    
if __name__ == "__main__":
    pass
