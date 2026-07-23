import math

if not __package__:
    import sys
    sys.path.append('..') 
    from gid_init import get_ct

import config

from sety.teplo.m import srlog


from sety.teplo.f import N_GWS
from sety.teplo.f import getW
from sety.teplo.f import getEp

#-------------------------------------
'''
def N_GWS(pr):
def getS28():
def getQ(pr):
def get_beta_pr(pt):
def get_beta_sm(pt):
def getF(pr, pr2, tr):
def getF1sm(pr, pr2, tr):
def getFp(node, stupen, pr, pt_G, tr):
def getEp(node, stupen, pr, pt_G, tr, G):
'''
#-------------------------------------


#-----------------------------------------------
# Расчет теплообменников для ГВС реальных потребителей
#-----------------------------------------------

def rasTO2(node, typ, pr, pt_G, tr, G, t, tx, debug):
#    double& t2, double& tg

#    print(typ, pr, pt_G, tr, G, t, tx)

    step = 1
    if typ == 11: step = 2

    if step == 2 : # Вторая ступень Автоматизированная
        if tx > pr.get('Tr_gvs', 60) and pr.get('pr_avtomat', 0) == 2: # /*'А'*/
            return t, tx

    if N_GWS(pr) == 0 or G == 0:
        tg = tx  # Горячая водопроводная
        t2 = t  # На входе системы отопления
        return t2, tg

    Wv = getW(pr, pt_G, tr, debug)
#    if debug:
#        print('Фатальная ошибка rasTO2', Wv)
#        exit(1)
    
    Ep = getEp(node, step, pr, pt_G, tr, G)

#    Ep = getEp(node, step, pr, pt_G, tr, G)

#    if debug:
#        print(f'step={step} G={G} Wv={Wv} Ep={Ep}')



    Wm = min(G, Wv)
    Qp = Ep * Wm * (t - tx)

    tg = tx + Qp / Wv  # Горячая водопроводная
    t2 = t - Qp / G  # На входе системы отопления

    return t2, tg

