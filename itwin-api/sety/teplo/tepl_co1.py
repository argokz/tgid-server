'''
if not __package__:
    import sys
    sys.path.append('..') 
    from gid_init import get_ct
else:
    from read_gid import get_ct
'''

import math
import numpy as np

import time


from scipy.optimize import fsolve
from scipy.optimize import newton

from sety.ct import get_ct

from sety.any.any import fatal_error

#import sety.teplo.gid_init
from sety.teplo import gid_init

from sety.teplo.m import srlog


#-----------------------------------------------
#   Расчет системы отопления
# для независимой схемы присоединения
#-----------------------------------------------

#-----------------------------------------------
# Расход тепла на отопление
#-----------------------------------------------

# Температура наружного воздуха текущая

# Температуры для основного режима

t11 = 150  # /* 150 */   # Температура в подаче расчетная
t12 = 80  # /* 70 */    # Температура в обратке расчетная

t01 = 0  # /* 150 */   # Температура в подаче расчетная
t02 = 0  # /* 70 */    # Температура в обратке расчетная
t03 = 0  # /* 95 */    # Температура в после узла расчетная
tvn1 = 0  # /* 18 */   # Температура внутри помещения расчетная
tn1 = 0  # /* -32 */   # Температура наружного воздуха расчетная

#Q   # = 1e6  # Нагрузка ккал/час для основного режима
#u   # = 2.2

# Текущий режим

#Dv = 0  # /*  = 0.309 */    # внутренний диаметр корпуса подогревателя, м
#dn = 0  # /*  = 0.017 */    # наружный диаметр трубок, м
#static int z = 0  # /*  = 151 */          # число трубок
n = 0  # /*  = 1 */            # количество секций подогревателя
pr1 = 0  # /*  = 1 */      # место установки 1 - ГВС 0 - СО
pr2 = 0  # /*  = 0 */      # движение сред : 1 - противоток 0 - прямоток
pr3 = 0  # /*  = 0 */      # движение сред : 1 - противоток 0 - прямоток

Gs = 0  # /*  = 30. */   # расход сетевой воды, т/ч
Gx = 0  # /*  = 25. */     # расход водопроводной воды (или местной СО), т/ч
T1 = 0  # /*  = 150. */     # температура сетевой воды на входе
Tx = 0  # /*  = 5. */       # температура водопроводной (местной) воды на входе

#-----------------------------------------------------------------------------------

#no_otopl = false
no_avtomat = True

#-----------------------------------------------------------------------------------

def setNoOtopl():
    global no_otopl
    no_otopl = False

def noOtopl():
    global no_otopl
    return no_otopl


def setAvtomat(avto):
    global no_avtomat
    no_avtomat = not avto


# Не хватает отопления

#-----------------------------------------------------------------------------------

#def rasTT2(const TT* tt, const PR* pr, const TR* tr, double G, double _q, double _tn, double t):

#_tx = 0
#_tg = 40

def rasTT2(pr, tr, G,  _q, _tn, t, debug):
#, double* t2, double* tv, double* tt01, double* tt02, double* tt03
    no_otopl = 0

#    if pr.get('name') == '5.11=':
#        debug = True

    ct = get_ct()

    tt1  = time.time()

    if not ct:
        print('Не создан объект "Система теплоснабжения"')
        fatal_error()
        return 0


    Tn = _tn

    t11 = tr.get('Tr_to_1_nco', 0)   # Расчетная температура сетевой воды на входе подогревателя системы отопления при независимом присоединении системы отопления
    t12 = tr.get('Tr_to_2_nco', 0)   # Расчетная температура сетевой воды на выходе подогревателя системы отопления  при независимом присоединении системы отопления

    t01 = tr.get('Tr_co_1m_nco', 0)   # Расчетная температура воды в под.трубопроводе местной СО, незав.СО
    t02 = tr.get('Tr_co_2m_nco', 0)   # Расчетная температура воды в обрат.трубопроводе местной СО, незав.СО
    t03 = tr.get('Tr_co_3m_nco', 0)   # Расчетная температура воды после узла смешения местной СО, незав.СО


#    if debug:
#        print(f't01={t01} t02={t02} t03={t03} t11={t11} t12={t12}')


  #  t11 = 100   # Расчетная температура сетевой воды на входе подогревателя системы отопления при независимом присоединении системы отопления
  #  t12 = 70   # Расчетная температура сетевой воды на выходе подогревателя системы отопления  при независимом присоединении системы отопления
  #  t01 = 95   # Температура в подаче расчетная
  #  t02 = 70   # Температура в обратке расчетная

  #########
    '''
    G = 14300
    t11 = 150
    t12 = 70
    t01 = 140
    t02 = 60
    t03 = 95
    '''
  #######



    tvn1 = pr.get('Tr_tv_co', 0) # Температура внутри помещения расчетная
    tn1 = ct.get('t_or', 0)      # Температура наружного воздуха расчетная


    Gs = G / 1000
    Gx = pr.get('otopln', 0) * 1e3 / (t01 - t02)#  Система отоплеия, горячая в трубках, пока

#    print(f'G = {G} Gs = {Gs} Gx = {Gx}')



#    pr2 = tt == NULL || tt.get('pr1_', 0) == 'П'     # движение сред : 1 - противоток 0 - прямоток
          # П - противоток Т - прямоток

  # Исправлено 24.02.09 
  # по указанию Н.И.Томиловой, потому, что в местной системе отопления нет узла смешения
  # Еще раз исправлено 06.02.13 
  # по указанию Н.И.Томиловой, потому, что в местной системе отопления нет узла смешения


#    if t02 != t03:
#        u = (t01 - t03) / (t03 - t02) # В местной системе отопления

    u = 0
    t03 = t01

    T1 = t
    Q = _q

#    print('====================================================')

    G = Gx * 1000
    dt = ((t03 + t02) / 2 - tvn1)

    if Gx < Gs:
        WmWb = Gx / Gs
    else:
        WmWb = Gs / Gx

    dt0 = t01 - t02
    dtp = t11 - t12
    dtsr = srlog(t11 - t01, t12 - t02)

    pr2 = True

    if pr2:
        dtsr = srlog(t11 - t01, t12 - t02)
    else:
        dtsr = srlog(t11 - t02, t01 - t12)

    if dtsr == 0:
        dtsr = 1
        Ep = 1. / (0.35 * WmWb + 0.65)
    else:
        Fp = math.sqrt(dt0 * dtp) / dtsr
        Ep = 1. / (0.35 * WmWb + 0.65 + 1 / Fp * math.sqrt(WmWb))

    if Ep > 1 and no_avtomat:
        Ep = 1
        no_otopl = 1

    Wmp = min(Gs, Gx) * 1000


    def fun(root):
        tx, tg = root[0], root[1]

        tv = Tn + G * (tg - tx) * (tvn1 - tn1) / Q
        xx = (Tn - tv) / (tn1 - tvn1)

        if xx < 0:
            xx = 0

    #    *f = pow(xx, 0.2) * (tg - Q / (2. * G) * xx - tv) - xx * dt

        f1 = math.pow(xx, 0.2) * (tg - (1. + 2. * u) / (1. + u) * Q / (2. * G) * xx - tv) - xx * dt

        if debug:
            print(f'{tg=} {tx=}')

        if tg < tx:
            df11 = 0
            df12 = 0
#             * (tg + 0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tg - tx) * (tvn1 - tn1) / (tn1 - tvn1) - Tn - G * (tg - tx) * (tvn1 - tn1) / Q) * G * (tvn1 - tn1) / Q / (tn1 - tvn1) + math.pow(-G * (tg - tx) * (tvn1 - tn1) / Q / (tn1 - tvn1), 0.2) * (-0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tvn1 - tn1) / (tn1 - tvn1) + G * (tvn1 - tn1) / Q) - G * (tvn1 - tn1) / Q / (tn1 - tvn1) * dt)
        else:
            df11 = (0.2 
                /  math.pow(-G * (tg - tx) * (tvn1 - tn1) / Q / (tn1 - tvn1), 0.8) * (tg + 0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tg - tx) * (tvn1 - tn1) / (tn1 - tvn1) - Tn - G * (tg - tx) * (tvn1 - tn1) / Q) * G * (tvn1 - tn1) / Q / (tn1 - tvn1) + math.pow(-G * (tg - tx) * (tvn1 - tn1) / Q / (tn1 - tvn1), 0.2) * (-0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tvn1 - tn1) / (tn1 - tvn1) + G * (tvn1 - tn1) / Q) - G * (tvn1 - tn1) / Q / (tn1 - tvn1) * dt)

            df12 = -0.2 / math.pow(-G * (tg - tx) * (tvn1 - tn1) / Q / (tn1 - tvn1), 0.8) * (tg + 0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tg - tx) * (tvn1 - tn1) / (tn1 - tvn1) - Tn - G * (tg - tx) * (tvn1 - tn1) / Q) * G * (tvn1 - tn1) / Q / (tn1 - tvn1) + math.pow(-G * (tg - tx) * (tvn1 - tn1) / Q / (tn1 - tvn1), 0.2) * (1.0 + 0.5 * (1.0 + 2.0 * u) / (1.0 + u) * (tvn1 - tn1) / (tn1 - tvn1) - G * (tvn1 - tn1) / Q) + G * (tvn1 - tn1) / Q / (tn1 - tvn1) * dt

#----------------------------

        tg2 = T1 - (tg - tx) * Gx / Gs

        f2 = 1000 * (tg - tx) * Gx - Wmp * Ep * (T1 - tx)

        df21 = -1000 * Gx + Wmp * Ep
        df22 = 1000 * Gx

        return f1, f2, df11, df12, df21, df22

    def fun1(root):
        f1, f2, df11, df12, df21, df22 = fun(root)
        return f1, f2
        
    def fun2(root):
        f1, f2, df11, df12, df21, df22 = fun(root)
        jac = np.array([[df11, df12],[df21, df22]])
        return jac

#    print(pr)

#    global _tx, _tg


    _tg = pr.get("_tg", 150)
    _tx = pr.get("_tx", 40)

    if _tg < _tx:
#        print('!!!', pr.get('name'), _tg, _tx)
        _tg = 150
        _tx = 40
        

    root = [_tx, _tg]

    if debug:
        print(pr.get('name'))
        print('fsolve', root)

    root = fsolve(fun1, root, fprime=fun2)

    
    tx, tg = root
    _tx, _tg = tx, tg

    pr['_tg'] = tg
    pr['_tx'] = tx

    if debug:
        print(f'fsolve {tx=} {tg=}')
        print(f'{tvn1=} {tn1=} {Gx=} {Gs=} {dtsr=}')
        if tx > 200:
            exit(1)

    

#    fun1(root)

#    tx, tg = root
#    _tx, _tg = root

    T2 = T1 - (tg - tx) * Gx / Gs
    t2 = T2
#    *tv = Tn + G * (T1 - T2) * (tvn1 - tn1) / Q
    tv = Tn + Gs*1000 * (T1 - T2) * (tvn1 - tn1) / Q

    tv2 = Tn + Gx * 1000 * (tg - tx) * (tvn1 - tn1) / Q

    T3 = (tg + tx * u) / (1 + u)

    G1 = math.pow(Gx * 1000 * (1 + u) / Q, 0.2)


    F0 = Q / ((t03 + t02) / 2 - tvn1)
    
    if T3 > tx:
        q3 = F0 * G1 * math.pow(T3 - tx, 0.2) * ((T3 + tx) / 2 - tv) # Отдача тепла радиаторами
    else:
        q3 = 0

    
    q4 = Q / (tvn1 - tn1) * (tv - Tn)  # Потери тепла зданием

  #  double q5 = 

    tt01 = tg
    tt02 = tx
    tt03 = (tg + u * tx) / (1 + u)

#    if debug:
#        print(f'<<< T2 = {T2} Q = {Q} Gs = {Gs} tvn1 = {tvn1} tn1 = {tn1}' )

    tt2  = time.time()

#    print(tt2-tt1)

    return t2, tv, tt01, tt02, tt03

#-----------------------------------------------------------------------------------

if __name__ == '__main__':
    Q = 1000000
    G = Q/70

    po = {}

    pr = gid_init.get_pr0('gvsm', 0.2)

    pr['otoplz'] = 0
    pr['otopln'] = 1

    tr = gid_init.get_tr0()

#    set_rasz_pr(pr, tr, -32)

    aa = rasTT2(pr, tr, G,  Q, -32, 150, True)
    print(aa)
