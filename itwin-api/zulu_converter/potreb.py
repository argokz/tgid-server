import ur
import re

from r import r_get

#---------------------------------------------------------------------------

def is_elevator(id):
    return id in [12,13,18,19,2,24,29,6,7]

def is_nasos(id):
    return id in [11,15,17,21,23,30,36,37,38,39,40,41,42,43,44,5,9]

def is_nezav(id):
    return id in [1,10,14,16,20,22,3,31,8]

def is_bezel(id):
    return id in [28,32,33,35,4]

def is_otkr(id):
    return id in [1,2,3,4,5,6,26,36,37]

def is_pr(id):
    return id in [19,20,21,22,23,24,28,38,39]

def is_ps(id):
    return id in [10,11,12,33,42,43,7,8,9]

def is_sm(id):
    return id in [13,14,15,16,17,18,32,34,40,41]

def is_pw(id):
    return id in [29,30,31,35]

#---------------------------------------------------------------------------

def is_gvs(id):
    return is_otkr(id) or is_pr(id) or is_ps(id) or is_sm(id) or is_pw(id)


#def is_gvs_pod(id):
#    is_gvs(id)

#    return is_otkr(id) or is_pr(id) or is_ps(id) or is_sm(id) or is_pw(id)

#---------------------------------------------------------------------------


def get_nagr_gvs(N_schem):
    if is_nezav(N_schem):
         nagr = 'calcHLindep'
    else:
         nagr = 'calcHLdep'

    gvs = 'avgHLGVSopenFlow'

    if is_pr(N_schem):
        gvs = 'avgHLGVScloseParall'
    elif is_ps(N_schem):
        gvs = 'avgHLGVScloseConseq'
    elif is_sm(N_schem):
        gvs = 'avgHLGVScloseMix'
    elif is_pw(N_schem):
        gvs = 'avgHLGVSclosePreON'
    elif is_otkr(N_schem):
#        gvs = 'avgHLGVSopenRet'
        gvs = 'avgHLGVSopenFlow'

    return nagr, gvs

#---------------------------------------------------------------------------

def get_nagr_gvs_ctp(N_schem):
#    nagr = 'calcHLdep'
#    gvs = 'avgHLGVSopenSysFlow'
#    shema = ''
#    shema_v = ''

#    return nagr, gvs, shema, shema_v
    
    
#    nagr = 'calcHLdep'
    nagr = 'calcHLindep'
    gvs = 'avgHLGVSopenSysFlow'
    shema = ''
    shema_v = ''

    if N_schem == 2:
        nagr = 'calcHLmix'
        gvs = 'calcHLGVSmix'
        shema = 'schemeMixID'
        shema_v = 3

    if N_schem == 3:
        nagr = 'calcHLparall'
        gvs = 'calcHLGVSparall'
        shema = 'schemeParallID'
        shema_v = 3


    return nagr, gvs, shema, shema_v

#---------------------------------------------------------------------------

def get_nagr_gvs_ctp_real(N_schem):

    if True: #is_nezav(N_schem):
         nagr = 'calcHLindep'
    else:
         nagr = 'calcHLdep'

    gvs = 'avgHLGVSopenFlow'

    if N_schem == 3: # is_pr(N_schem):
        gvs = 'avgHLGVScloseParall'
#    elif is_ps(N_schem):
#        gvs = 'avgHLGVScloseConseq'
    elif N_schem == 2: #is_sm(N_schem):
        gvs = 'avgHLGVScloseMix'
#    elif is_pw(N_schem):
#        gvs = 'avgHLGVSclosePreON'
#    elif is_otkr(N_schem):
#        gvs = 'avgHLGVSopenRet'
#        gvs = 'avgHLGVSopenFlow'

    return nagr, gvs

#---------------------------------------------------------------------------
    
def get_cxema(id, Qo_r, Qsv_r, Qgv):
    n1 = 1

    is_gvs_b = Qgv > 0

    if is_gvs_b :
       if is_pr(id) : n1 = 3
       elif is_sm(id) : n1 = 4
       elif is_ps(id) : n1 = 5
       elif is_pw(id) : n1 = 15
       elif is_otkr(id) : n1 = 6  # Из подачи, а из обратки 7

#    is_rez = False
    is_rez = is_otkr(id)

    is_vent = False
    if Qsv_r:
        is_vent = True


#    print(is_gvs_b)
#    is_gvs(id)

    n2 = 3

    if is_gvs_b :
       if is_elevator(id) : n2 = 5
       elif is_nezav(id) : n2 = 9
       elif is_bezel(id) : n2 = 1

       if is_rez and not is_vent : n2 += 1
       elif not is_rez and is_vent : n2 += 2
       elif is_rez and is_vent : n2 += 3
    else:
       if is_elevator(id) : n2 = 3
       elif is_nezav(id) : n2 = 5
       elif is_bezel(id) : n2 = 1

       if is_vent : n2 += 1

#    print(n1, n2)

    return n1, n2

#---------------------------------------------------------------------------

def get_cxema_ctp(id, Qo_r, Qsv_r, Qgv):
    n1 = 1

    is_gvs_b = Qgv > 0

    if is_gvs_b :
       if id == 3 : n1 = 3  #pr
       elif id == 2: n1 = 4  #sm


#       elif is_ps(id) : n1 = 5
#       elif is_pw(id) : n1 = 15
#       elif is_otkr(id) : n1 = 7

    is_rez = False
    is_vent = False
    if Qsv_r:
        is_vent = True


#    print(is_gvs_b)
#    is_gvs(id)

    n2 = 3

    if is_gvs_b :
        n2 = 9
#       if is_elevator(id) : n2 = 5
#       elif is_nezav(id) : n2 = 9
#       elif is_bezel(id) : n2 = 1

#       if is_rez and not is_vent : n2 += 1
#       elif not is_rez and is_vent : n2 += 2
#       elif is_rez and is_vent : n2 += 3
    else:
        n2 = 5
#       if is_elevator(id) : n2 = 3
#       elif is_nezav(id) : n2 = 5
#       elif is_bezel(id) : n2 = 1

#       if is_vent : n2 += 1

#    print(n1, n2)

    return n1, n2

#---------------------------------------------------------------------------

def read_potreb(self, r, Nist, regim, id_new, node_name, adres, x, y):

    N_schem = int(r_get(r, 'N_schem', None))
    Qo_r       = r_get(r, 'Qo_r', 0)
    Qsv_r      = r_get(r, 'Qsv_r', 0)
    Qgv_sred   = r_get(r, 'Qgv_sred', 0)
    Qgv_max    = r_get(r, 'Qgv_max', 0)
    Hzdan = r_get(r, 'Hzdan', 0)

#    Qgv = max(Qgv_sred, Qgv_max)
    Qgv = Qgv_sred


#Hcirc Потери напора в системе ГВС, м Задается величина потери напора в системе горячего водоснабжения
#Hsec_so Потери напора в 1-й секции ТО на СО, м Указываются потери напора в одной секции ТО на СО, например 0.5, 1, 1.5 м вод.ст.
#Hsec_niz Потери напора в одной секции I ступени, м Указываются потери напора в одной секции ТО 1ой ступени на ГВС, например 0.5, 1, 1.5 м вод.ст.
#Hsec_verh Потери напора в одной секции II ступени, м Указываются потери напора в одной секции ТО 2ой ступени на ГВС, например 0.5, 1, 1.5 м вод.ст.


    mixFactCoeff = 0

    if (r_get(r, 'T3_r', 0) - r_get(r, 'T2_r', 0)) != 0: 
        mixFactCoeff = (r_get(r, 'T1_r', 0)-r_get(r, 'T3_r', 0))/(r_get(r, 'T3_r', 0)-r_get(r, 'T2_r', 0))

    specExpendID = ur.getUR(self, Nist, r_get(r, 'T1_r', 0), r_get(r, 'T2_r', 0), r_get(r, 'T3_r', 0))


    calcTemperatureID = ur.getTR(self, Nist, r)

    name2 = adres

#    name2 = '{} {} {} {} {}'.format(Nist, N_schem, r_get(r, 'T1_r', None), r_get(r, 'T2_r', None), r_get(r, 'T3_r', None))
#    name2 = '{} Gso={} Ggv={}'.format(r_get(r, 'Gsum_pod', None), r_get(r, 'Gso', None), r_get(r, 'Ggv', None))

#    result = re.match(r'^([^,]+),\s+(.+)$', node_name)
#    if result:
#        print('"{}", "{}", {}, {}'.format(result.group(1), result.group(2), x, y))

    nagr, gvs = get_nagr_gvs(N_schem)

    n1, n2 = get_cxema(N_schem, Qo_r,Qsv_r,Qgv)
 
    consumerStateID = 1
    if regim == 1: consumerStateID = 2


    volWaterHS = 26
    volWaterVS = 26

    # Утечка

#    setLeakageRet = (Qo_r, Qsv_r, Qgv)
    setLeakageRet = Qo_r*volWaterHS+Qsv_r*volWaterVS

    if is_otkr(N_schem):
        setLeakageRet += Qgv*volWaterHS

    setLeakageRet = setLeakageRet*0.25/100

#  volWaterHS float DEFAULT 13.3, -- COMMENT 'Удельный объем воды в системе отопления',
#  volWaterVS float DEFAULT 5.5, -- COMMENT 'Удельный объем воды в системе вентиляции',

    setLeakageRet = 0;

    Tvn_o = self.Tvn
    Tvn_v = self.Tvn

    Tvn_o = r_get(r, 'Tvso_r', 0)
    Tvn_v = r_get(r, 'Tvsv_r', 0)

    tempRecircPipe = r_get(r, 'Tcirc', 0)

    if Qgv_sred == 0 :
        hourIrregCoeff = 1.2
    else:
        hourIrregCoeff = Qgv_max/Qgv_sred

    insert = '''INSERT INTO [realConsumers] 
         (consumerStateID, name, nodeID, {}, calcHLventil, {}, schemeNum, specExpendID, buildHeight, mixFactCoeff, calcTemperatureID, volWaterHS, volWaterVS, setLeakageRet, calcTempHR, calcTempVS, calcTempHWDO, hourIrregCoeff,tempRecircPipe) 
         VALUES ({}, \'{}\', {}, {}, {}, {}, \'{}.{}\', {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {})'''\
         .format(nagr, gvs, 
         consumerStateID, name2, id_new, Qo_r, Qsv_r, Qgv, n1, n2, specExpendID, Hzdan, mixFactCoeff, calcTemperatureID, volWaterHS, volWaterVS, setLeakageRet, 
            Tvn_o, 
            Tvn_v, 
            r_get(r, 'Tgv', 0),
            hourIrregCoeff,
            tempRecircPipe
            )

    return insert



'''
                           Sys = r_get(r, 'Sys', 0)
                           Name = r_get(r, 'Name', 0)
                           tm_rs = r_get(r, 'tm_rs', 0)
                           Prim = r_get(r, 'Prim', 0)
                           Nist = r_get(r, 'Nist', 0)
                           H_geo = r_get(r, 'H_geo', 0)
                           N_schem = r_get(r, 'N_schem', 0)
                           Gpod = r_get(r, 'Gpod', 0)
                           H = r_get(r, 'H', 0)
                           Sr = r_get(r, 'Sr', 0)
                           Gu_r = r_get(r, 'Gu_r', 0)
                           H_ras = r_get(r, 'H_ras', 0)
                           H_pod = r_get(r, 'H_pod', 0)
                           H_obr = r_get(r, 'H_obr', 0)
                           Ppod = r_get(r, 'Ppod', 0)
                           Pobr = r_get(r, 'Pobr', 0)
                           Time = r_get(r, 'Time', 0)
                           Tpod = r_get(r, 'Tpod', 0)
                           Tobr = r_get(r, 'Tobr', 0)
                           St = r_get(r, 'St', 0)
                           G_ot = r_get(r, 'G_ot', 0)
                           G_v = r_get(r, 'G_v', 0)
                           Gu_t = r_get(r, 'Gu_t', 0)
                           Q_ot = r_get(r, 'Q_ot', 0)
                           Q_v = r_get(r, 'Q_v', 0)
                           Q_gvs = r_get(r, 'Q_gvs', 0)
                           Q_s = r_get(r, 'Q_s', 0)
                           Tgr_pod = r_get(r, 'Tgr_pod', 0)
                           Tgr_obr = r_get(r, 'Tgr_obr', 0)
                           Dist = r_get(r, 'Dist', 0)
                           Kso = r_get(r, 'Kso', 0)
                           Kgv = r_get(r, 'Kgv', 0)
                           Beta = r_get(r, 'Beta', 0)
                           Gt_pod = r_get(r, 'Gt_pod', 0)
                           Gt_obr = r_get(r, 'Gt_obr', 0)
                           Tb = r_get(r, 'Tb', 0)
                           Hstat = r_get(r, 'Hstat', 0)
                           Hstat_out = r_get(r, 'Hstat_out', 0)
                           Hzdan = r_get(r, 'Hzdan', 0)
                           Pers_primech = r_get(r, 'Pers_primech', 0)
                           Pers_q_circ = r_get(r, 'Pers_q_circ', 0)
                           Pers_q_gvs = r_get(r, 'Pers_q_gvs', 0)
                           G_gvs = r_get(r, 'G_gvs', 0)
                           S_Qot_v = r_get(r, 'S_Qot_v', 0)
                           G_zakr_gvs = r_get(r, 'G_zakr_gvs', 0)
                           Tobr_type = r_get(r, 'Tobr_type', 0)
                           Tobr_val = r_get(r, 'Tobr_val', 0)
                           CodeLine = r_get(r, 'CodeLine', 0)
                           Pmax_obr = r_get(r, 'Pmax_obr', 0)
                           tk_id = r_get(r, 'tk_id', 0)
                           Export = r_get(r, 'Export', 0)
                           G_gvs_cirk = r_get(r, 'G_gvs_cirk', 0)
'''

#---------------------------------------------------------------------------

def read_obob_potreb(self, r, Nist, regim, id_new, node_name, adres, x, y):

    N_schem = int(r_get(r, 'N_schem', 0))

    Gpod = r_get(r, 'Gpod', 0)  # Расход на СО,СВ и закр.системы ГВС, т/ч

    G_ot = r_get(r, 'G_ot', 0)  # Расчетный расход на отопление, т/ч
    G_v = r_get(r, 'G_v', 0)   # Расчетный расход на вентиляцию, т/ч
    Gu_r = r_get(r, 'Gu_r', 0)    # Расход на открытый водоразбор, т/ч
    G_gvs = r_get(r, 'G_gvs', 0)  # Расчетная нагрзка на ГВС, т/ч

    G_zakr_gvs = r_get(r, 'G_zakr_gvs', 0)   #   Расчетная нагрузка на закрытое ГВС, т/ч

    G_zakr_gvs = r_get(r, 'Gto_r', 0)   #   Расчетная нагрузка на закрытое ГВС, т/ч
    

    if G_ot == 0:
        G_ot = Gpod

    
#    Qo_r       = r_get(r, 'Qo_r', None)
#    Qsv_r      = r_get(r, 'Qsv_r', None)
#    Qgv_sred   = r_get(r, 'Qgv_sred', None)
#    Qgv_max    = r_get(r, 'Qgv_max', None)

    Hzdan = r_get(r, 'Hzdan', 0)

#    Qo_r = 
#    Qsv_r =
#    Qgv =


#    Qgv = max(Qgv_sred, Qgv_max)
#    Qgv = Qgv_sred


#Hcirc Потери напора в системе ГВС, м Задается величина потери напора в системе горячего водоснабжения
#Hsec_so Потери напора в 1-й секции ТО на СО, м Указываются потери напора в одной секции ТО на СО, например 0.5, 1, 1.5 м вод.ст.
#Hsec_niz Потери напора в одной секции I ступени, м Указываются потери напора в одной секции ТО 1ой ступени на ГВС, например 0.5, 1, 1.5 м вод.ст.
#Hsec_verh Потери напора в одной секции II ступени, м Указываются потери напора в одной секции ТО 2ой ступени на ГВС, например 0.5, 1, 1.5 м вод.ст.



    mixFactCoeff = 0
#    if (r_get(r, 'T3_r', None)-r_get(r, 'T2_r', None)) != 0: 
#        mixFactCoeff = (r_get(r, 'T1_r', None)-r_get(r, 'T3_r', None))/(r_get(r, 'T3_r', None)-r_get(r, 'T2_r', None))

#    specExpendID = ur.getUR(self, Nist, r_get(r, 'T1_r', None), r_get(r, 'T2_r', None), r_get(r, 'T3_r', None))
    calcTemperatureID = ur.getTR(self, Nist, r)

    name2 = adres

#    name2 = '{} {} {} {} {}'.format(Nist, N_schem, r_get(r, 'T1_r', None), r_get(r, 'T2_r', None), r_get(r, 'T3_r', None))
#    name2 = '{} Gso={} Ggv={}'.format(r_get(r, 'Gsum_pod', None), r_get(r, 'Gso', None), r_get(r, 'Ggv', None))

#    result = re.match(r'^([^,]+),\s+(.+)$', node_name)
#    if result:
#        print('"{}", "{}", {}, {}'.format(result.group(1), result.group(2), x, y))

#    nagr, gvs = get_nagr_gvs(N_schem)
#    n1, n2 = get_cxema(N_schem, Qo_r,Qsv_r,Qgv)

#    n1, n2 = 

    specExpendID = ur.getUR1(self, Nist)
 
    consumerStateID = 1
    if regim == 1: consumerStateID = 2

    insert = f'''INSERT INTO [generalizedConsumers] 
         (consumerStateID, specExpendID, name, nodeID, calcHLdep, calcHLventil, avgHLGVSopenSysFlow, calcHLGVSparall, calcTemperatureID) 
         VALUES ({consumerStateID}, {specExpendID}, \'{name2}\', {id_new}, {G_ot}, {G_v}, {Gu_r}, {G_zakr_gvs}, {calcTemperatureID})
         '''

#    print('Обоб')
#    print('gu_r', Gu_r)
#    print(insert)


    return insert
