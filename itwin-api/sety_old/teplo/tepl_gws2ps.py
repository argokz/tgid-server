import math

from sety.teplo.otopl import otopl
from sety.teplo.m import srlog
from sety.teplo.tepl_gws1ps import getF1
from sety.teplo.t import getS28

#-----------------------------------------------
# Расход тепла на ГВС ступень II
# последовательная схема
#-----------------------------------------------

#const PC *getPC(CNode *n)



# Указывает, что отопления не хватает для нагрева.

#-----------------------------------------------------------------------------------

def getF2(node, pr, pr2, tr):

    Q_gvs_max = pr.get('gvps', 0) * pr.get('gvs_max', 0) #rez - рециркуляция

  #  Wv = Q_gvs_max*1e6/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))+pr2->G_rez*pr.get('gvs_max', 0)*1000
    Wv = Q_gvs_max * 1e6 / (pr.get('Tr_gvs', 60) - tr.get('Tx', 0))

#    G0_s, dGbo

    if pr.get('otopln', 0) != 0:
        G0_s = pr.get('otopln', 0) / (tr.get('Tr_to_1_ps', 0) - tr.get('Tr_to_2_ps', 0)) #расчетный расход сет.воды на отопление
    else:
        G0_s = pr.get('otoplz', 0) / (tr.get('Tr_co_1_zco', 0) - tr.get('Tr_co_2_zco', 0)) #расчетный расход сет.воды на отопление

    Qbal = pr.get('gvps', 0) * getS28().ps * 1e6

    #  Qrez = Q_gvs_max*1e6*pr.get('rez', 0)/100.
    #  dGbo = (Qbal+Qrez)*(pr.get('Tr_gvs', 60)-(tr.get('T2_isl_2stup_ps', 0)-tr.get('delta_tg_ps', 0)))/(tr.get('T1_isl_2stup', 0)-tr.get('T2_isl_2stup_ps', 0))/(pr.get('Tr_gvs', 60) - tr.get('Tx', 0))#расчетная добавка за счет ГВС

    dGbo = Qbal * (pr.get('Tr_gvs', 60) - (tr.get('T2_isl_2stup_ps', 0) - tr.get('delta_tg_ps', 0))) / (tr.get('T1_isl_2stup', 0) - tr.get('T2_isl_2stup_ps', 0)) / (pr.get('Tr_gvs', 60) - tr.get('Tx', 0))#расчетная добавка за счет ГВС


    W0 = G0_s * 1000000 + dGbo                     #расчетный расход сет.воды на вход

#    dtII_sr
#    kFII
#    F2

#    Q, QI

    Wm = min(W0, Wv) # Расход минимальный
    Wb = max(W0, Wv) # Расход максимальный

#    t01
    F1 = getF1(node, pr, pr2, tr)
#    t02, tv
    E1 = 1 / (0.35 * Wm / Wb + 0.65 + math.sqrt(Wm / Wb) / F1)

    tn = tr.get('T2_isl_2stup_ps', 0) - tr.get('delta_tg_ps', 0) # Начальное значение
    QIn = Wv * (tn - tr.get('Tx', 0)) # Начальное значение

    while True:
        QI = QIn

        t01 = 60.39
        t01 = (W0 * tr.get('T1_isl_2stup', 0) - (Q_gvs_max * 1e6 - QI)) / W0

        #    otopl(pr, tr, 12500, 3, 70.6, t02, tv)
        #    otopl(pr, tr, 12500, 2.5, 70, t02, tv)

        t02, tv, Q = otopl(node, pr, tr, W0, tr.get('tn_isl', 0), t01, False, False)

        QIn = E1 * Wm * (t02 - tr.get('Tx', 0))
        tn = (Wv * tr.get('Tx', 0) + QI) / Wv

        if abs((QI - QIn) / QIn) < 1e-3: break

    QII = Q_gvs_max * 1e6 - QI

    dtII_sr = srlog(t01 - tn, tr.get('T1_isl_2stup', 0) - pr.get('Tr_gvs', 60))
    kFII = QII / dtII_sr


#    if (W0 * Wv) <= 0:
#        print('!!')
#        exit(0)

    F2 = kFII / math.sqrt(W0 * Wv)

    #  wout << "kf2 = " << kFII << endl


    return F2
