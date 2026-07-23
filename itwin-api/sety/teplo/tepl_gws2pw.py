import math

from sety.teplo.otopl import otopl
from sety.teplo.m import srlog
from sety.teplo.t import getS28


#-----------------------------------------------------------------------------------

def getF2pw(node, pr, pr2, tr):

    Q_gvs_max = pr.get('gvpw', 0)*pr.get('gvs_max', 0)

#    Wv = Q_gvs_max*1e6/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))+pr2->G_rez*pr.get('gvs_max', 0)*1000
    Wv = Q_gvs_max*1e6/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))



#    Q, G0_s, dGbo

    if pr.get('otopln', 0) != 0:
      G0_s = pr.get('otopln', 0)/(tr.get('Tr_to_1_pw', 0)-tr.get('Tr_to_2_pw', 0)) #расчетный расход сет.воды на отопление
    else:
      G0_s = pr.get('otoplz', 0)/(tr.get('Tr_co_1_zco', 0)-tr.get('Tr_co_2_zco', 0)) #расчетный расход сет.воды на отопление

    Qbal = pr.get('gvpw', 0)*getS28().pw*1e6

#    Qrez = Q_gvs_max*1e6*pr.get('rez', 0)/100.

#    dGbo = (Qbal+Qrez)/(tr.get('T1_isl_2stup', 0)-tr.get('T2_isl_2stup_pw', 0))#расчетная добавка за счет ГВС
    dGbo = (Qbal)/(tr.get('T1_isl_2stup', 0)-tr.get('T2_isl_2stup_pw', 0))#расчетная добавка за счет ГВС

    W0 = G0_s*1000000 + dGbo                     #расчетный расход сет.воды на вход

#    dtII_sr
#    kFII
#    F2

    Wm = min(W0, Wv) # Расход минимальный
    Wb = max(W0, Wv) # Расход максимальный

#    t01
#    t02, tv

    t01 = tr.get('T1_isl_2stup', 0)-Q_gvs_max*1e6/W0

    t02, tv, Q = otopl(node, pr, tr, W0, tr.get('tn_isl', 0), t01, False, False)

    QII = Q_gvs_max*1e6

    dtII_sr = srlog(t01-tr.get('Tx', 0), tr.get('T1_isl_2stup', 0)-pr.get('Tr_gvs', 60))
    kFII = QII/dtII_sr

#    print(W0, Wv)

    F2 = kFII/math.sqrt(W0*Wv)

    return F2
