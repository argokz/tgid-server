from collections import namedtuple

import math

#from sety.gid_init import get_ct
from sety.ct import get_ct
from sety import config
from sety.teplo.tepl_gws2pw import getF2pw
from sety.teplo.tepl_gws2ps import getF2
from sety.teplo.tepl_gws1ps import getF1


from sety.teplo.t import getS28

#from m import srlog
from sety.teplo.m import srlog


def N_GWS(pr):
    return 4

#-----------------------------------------------------------------------------------

def getQ(pr, debug):
    Q = (pr.get('gvpw', 0) + pr.get('gvps', 0) + pr.get('gvsm', 0) + pr.get('gvpr', 0))

    if N_GWS(pr) == 1:  # Средненедельная
        pass
    elif N_GWS(pr) == 2: # Максимальная
        Q *= pr.get('gvs_max', 0)
    elif N_GWS(pr) == 3: # Балансовая
        Q = (
            pr.get('gvpw', 0) * getS28().pw
            + pr.get('gvps', 0) * getS28().ps
            + pr.get('gvsm', 0) * getS28().sm
            + pr.get('gvpr', 0) * getS28().pr)
    elif (N_GWS(pr) == 4): # Расчетная
        Q = (
            pr.get('gvpw', 0) * getS28().pw
            + pr.get('gvps', 0) * getS28().ps
            + pr.get('gvsm', 0) * getS28().sm
            + pr.get('gvpr', 0) * getS28().pr)
    #  Q *= (1.+pr.get('rez', 0)/100.)

#    if debug:
#        print('>>', Q, pr.get('cxema', '???'))

    return Q * 1e6

#-----------------------------------------------------------------------------------

def getW(pr, pt_G, tr, debug):
    koef = 1

    #  ZULU смешанная !!!

    if config.args.is_ZULU_SM:
        if pr.get('gvsm', 0) > 0:
            #            koef = 0.35
            return getQ(pr, debug) / (tr.get('Tr_co_1_zco_sm', 0) - tr.get('Tx', 0))

#    print(f'koef={koef} getQ(pr)={getQ(pr, debug)} / {pr.get('Tr_gvs', 60)} - {tr.get('Tx', 0)}')

    W = koef * getQ(pr, debug) / (pr.get('Tr_gvs', 60) - tr.get('Tx', 0))

    return W


def get_beta_pr(pt):
#    bool avt = pt.get('pr_avtomat', 0) == 2 /*'А'*/
    avt = False

    if avt:
        #расчетный расход считается через максимальную нагрузку
        beta = pt.get('gvs_max', 0)
    else:
        #расчетный расход считается через балансовую нагрузку.
        # Qгвс_бал = 1.15*Qгвс_ср
        # 1.15 по умолчанию 
        beta = getS28().pr  # 1.15

    return beta
    
#-----------------------------------------------------------------------------------

def get_beta_sm(pt):
#    avt = pt.get('pr_avtomat', 0) == 2 /*'А'*/
    avt = False

    if avt:
        beta = pt.get('gvs_max', 0)  # 1.2
#        dt2v_sm = tn.get('dt2v_sm_avm', 0)   # 10
    else:
        beta = getS28().sm   # 1.1
#        dt2v_sm = tn.get('dt2v_sm_noavm', 0)   # 5
    return beta

#-----------------------------------------------------------------------------------

def getF(pr, pr2, tr):
  Q_gvs_max = pr.get('gvpr', 0)*get_beta_pr(pr)*1e6
  Q = Q_gvs_max

  t1is = tr.get('T1_isl_2stup', 0) #  Расчетная температура воды на входе 2 ступени ГВС в точке излома темпер.графика 
  t2is = tr.get('T2_isl_2stup_pr', 0) #  Расчетная температура воды на выходе 2 ступени ГВС в точке излома темпер.графика
  tgvs = pr.get('Tr_gvs', 60)       #  Расчетная температура горячей воды в местах водоразбора                         

  Wp = pr2.get('G_gvpr', 0)*1000  # Расход сетевой воды
  Wvod = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))  # Водопроводная вода

  Wm = min(Wp, Wvod) # Расход минимальный 
  Wb = max(Wp, Wvod) # Расход максимальный

  Wvodmax = Wvod
  Wpmax = Q/(tr.get('T1_isl_2stup', 0) - tr.get('T2_isl_2stup_pr', 0))

  tx = tr.get('Tx', 0)

  dtsr = srlog(t2is-tx, t1is-tgvs)

  if dtsr == 0: 
    dtsr = 1

  Fp = Q/math.sqrt(Wb*Wm)/dtsr
  return Fp

#-----------------------------------------------------------------------------------

def getF1sm(pr, pr2, tr):

#  Q_gvs_max = get_beta_sm(pr) != 0 ? get_beta_sm(pr) : pr.get('gvsm', 0)
  Q_gvs_max = pr.get('gvsm', 0)*get_beta_sm(pr)
  Q_gvs_max *= 1e6
  Q = Q_gvs_max
  
#  Q = pr.get('gvsm', 0)*1e6
  Gs = (pr2.get('G_otopln', 0)+pr2.get('G_otoplz', 0)+pr2.get('G_ventil', 0)+pr2.get('G_gvsm', 0))*1000
#  Gs = (pr2.get('G_otopln', 0)+pr2.get('G_otoplz', 0)+pr2.get('G_gvsm', 0))*1000
  Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))

  #  ZULU смешанная !!!

  if config.args.is_ZULU_SM:
      Gx =  Q / (tr.get('Tr_co_1_zco_sm', 0) - tr.get('Tx', 0))

  QII = Gx*(pr.get('Tr_gvs', 60)-(tr.get('T2_isl_2stup_sm', 0)-tr.get('delta_tg_sm', 0)))

  QI = Q-QII

  t2cm = tr.get('T2_isl_2stup_sm', 0)

  t211 = tr.get('T2_isl_2stup_sm', 0) - QI/Gs

  dtsr = srlog(tr.get('delta_tg_sm', 0), t211-tr.get('Tx', 0))

  Wm = min(Gs, Gx) # Расход минимальный 
  Wb = max(Gs, Gx) # Расход максимальный

  kFI = QI/dtsr
  FI = kFI/math.sqrt(Wb*Wm)

  return FI


#-----------------------------------------------------------------------------------

def getF2sm(pr, pr2, tr):
  Q_gvs_max = pr.get('gvsm', 0)*get_beta_sm(pr)
  Q_gvs_max *= 1e6
  Q = Q_gvs_max

  Gx = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))

  if config.args.is_ZULU_SM:
      Gx =  Q / (tr.get('Tr_co_1_zco_sm', 0) - tr.get('Tx', 0))


#  Gs = pr2.get('gvs_max', 0) != 0 ? pr2.get('gvs_max', 0) : pr2.get('gvsm', 0)
  Gs = pr2.get('G_gvsm', 0)*get_beta_sm(pr)
  Gs *= 1000  # кг/ч

  t1is = tr.get('T1_isl_2stup', 0) #  Расчетная температура воды на входе 2 ступени ГВС в точке излома темпер.графика 
  t2is = tr.get('T2_isl_2stup_sm', 0) #  Расчетная температура воды на выходе 2 ступени ГВС в точке излома темпер.графика
  tgvs = pr.get('Tr_gvs', 60)       #  Расчетная температура горячей воды в местах водоразбора

  Wp = Gs  # Расход на 2 ступени
  Wvod = Gx ## = Q/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))  # Водопроводная вода

  Wm = min(Wp, Wvod) # Расход минимальный 
  Wb = max(Wp, Wvod) # Расход максимальный

  dt = tr.get('delta_tg_sm', 0)  #  Недогрев водопроводной воды в первой ступени системы горячего водоснабжения
#  t2cm  # Температура сетевой воды на входе I ступени в точке излома

  t2cm = tr.get('T2_isl_2stup_sm', 0)
 
  T2_isl_co = tr.get('T2_isl_2stup_sm', 0)

  tp_isl = t2cm-dt # Температура водопроводной воды на входе II ступени в точке излома

  QII = Q*(tgvs-tp_isl)/(tgvs-tr.get('Tx', 0))

  dtsr = srlog(t1is-tgvs, tr.get('T2_isl_2stup_sm', 0)-tp_isl);

  if dtsr == 0: dtsr = 1

  kF = QII/dtsr
  FII = kF/math.sqrt(Wm*Wb)

  return FII

#-----------------------------------------------------------------------------------


def getFp(node, stupen, pr, pt_G, tr):
    Fp = 0
    if stupen == 1:
        if (pr.get('gvpr', 0)): Fp = getF(pr, pt_G, tr)
        elif (pr.get('gvps', 0) > 0): Fp = getF1(node, pr, pt_G, tr)
        elif (pr.get('gvsm', 0) > 0): Fp = getF1sm(pr, pt_G, tr)
    elif stupen == 2:
        if (pr.get('gvpr', 0) > 0): Fp = getF(pr, pt_G, tr)
        elif (pr.get('gvps', 0) > 0): Fp = getF2(node, pr, pt_G, tr)
        elif (pr.get('gvpw', 0) > 0): Fp = getF2pw(node, pr, pt_G, tr)
        elif (pr.get('gvsm', 0) > 0): Fp = getF2sm(pr, pt_G, tr)
    else:
        print('stupen=', stupen)
        exit(0)

    if Fp == 0:
        print(pr)
        exit(0)


    return Fp

#-----------------------------------------------------------------------------------

def getEp(node, stupen, pr, pt_G, tr, G, debug=False):
    Ep = 0.8

    Gx = getW(pr, pt_G, tr, True)

    Wm = min(Gx, G) # Расход минимальный
    Wb = max(Gx, G) # Расход максимальный

#    print(f'Gx={Gx} G={G}')
#    print(f'Wm={Wm} Wb={Wb}')


    Fp = getFp(node, stupen, pr, pt_G, tr)
    Ep = 1 / (0.35 * Wm / Wb + 0.65 + math.sqrt(Wm / Wb) / Fp)

    if Ep > 1 or Ep <= 0 or Ep != Ep:
        Ep = 1

    return Ep

#-------------------------------------
