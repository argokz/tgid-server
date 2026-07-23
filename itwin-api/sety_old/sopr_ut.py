import networkx as nx
import math
import numpy as np
from collections import OrderedDict

from sety import const
from sety import w_print

from sety import read_gid

from sety.ct import get_ct
from sety.teplo.teplo import getZT
from sety.any.colors import cprint
from sety import config

# новое сопротивление по Zulu

#-----------------------------------------------------------------------------------

def skor(G, D, t):

    c = 353.86
    c = 4*1e6/math.pi/3600

    return c * G / D / D

#-----------------------------------------------------------------------------------

# удельное сопротивление по lambda - коэффициент гидравлического сопротивления.

def get_sprn(ld, d, t):

    c = 4*1e6/math.pi/3600
    g = 9.80665

    ro = get_ro(t)

#    coef = c * c / math.pow(d, 5)/ ro / ro * 1e-6 / 2 / g
    sopr =  ld * c * c / math.pow(d, 5) * 1e-6 / 2 / g / ro /1e6

    return sopr

#-----------------------------------------------------------------------------------

# # динамическая вязкость

def get_vj(t):
    coef_v =[ 7.36020953e-17, -5.45811383e-14, 1.74149835e-11, -3.14667231e-09,
      3.58638236e-07, -2.74678686e-05, 1.49386117e-03, -6.06823700e-02,
      1.78959824e+00]

    vv = np.polyval(coef_v, t)    # динамическая вязкость

    return vv

#-----------------------------------------------------------------------------------

# Плотность воды 1000
def get_ro(t):
#    print(config.args.ro_temp)

    if not config.args.ro_temp:
        if t > 79:
            return config.args.roP
        else:
            return config.args.roO

    a3, a2, a1, a0 = [ 8.24652663e-09, -4.76126242e-06, -2.75700364e-05,  1.00039846e+00]
    ro = a0 + a1*t + a2*t*t + a3*t*t*t

#    print(ro)

    return ro

ds_max = 0

#-----------------------------------------------------------------------------------

def soprUT(ut, t, ras, formula):

    if ras is None:
        return None

    if abs(ras) < 0.00001:
        return None

    global ds_max

    ut_dlina = ut.get('dlina', 1.)
    ut_sopr = ut.get('hydroRes', 0.)
    
#    if ut_sopr is None:
#        print('!!!!!!!!')

    ut_truba = ut.get('truba', 1)
    ut_diametr = ut.get('diametr', 1000.)
    ut_scher = ut.get('scher', 0.5)
    ut_dolja = ut.get('dolja', 0.)      # Доля местных потерь
    ut_mestnoe = ut.get('mestnoe', 0.)  # Сумма коэффициентов местных сопротивлений
    ke = ut_scher / 1000  # Шероховатость, мм

    d = ut_diametr / 1000  # диаметр, метр
    l = ut_dlina  # длина, м

    if ut_dolja > 0:
        lekv = l * (1 + ut_dolja)

    g = 9.80665

    ro = get_ro(t)  # плотность воды
    V = abs(skor(ras, d*1000, t)/ro)  # скорость

    vv = get_vj(t)  # динамическая вязкость
    vvk = vv/ro     # кинематическая вязкость

    Re = V*d/vvk*1e6  # Число Рейнольдса

    if ut_diametr == 990.4:
        print(f'_____D={ut_diametr} Re={Re}')


    ld_s = 0.11*math.pow(ke / d, 0.25)   # Шифринсона

    ld_a = 0.11*pow(ke / d + 68/Re, 0.25)   # Альтшуля

    c = 2
    a = 3.7
    b = 1.14

    ld_n = 1/math.pow((c*math.log10(d/ke)+b),2)     # Никурадзе

    if formula == 4:  # Колбрука-Уайта
        ld_k = ld_s

        for i in range(10):
            qqq = (ke/d)/3.7+2.51/(Re*math.sqrt(ld_k))
            if qqq <= 0:
                return None

            qqq = math.pow(-2*math.log10(qqq), -2)
            ld_k2 = qqq
            if abs((ld_k-ld_k2)/ld_k2) < 1e-20:
                break

            ld_k = ld_k2

    lekv = 0

    ut_dolja = ut.get('dolja', 0.)      # Доля местных потерь

    if formula == 1:  # Альтшуля
        ld = ld_a
    if formula == 2:  # Никурадзе
        ld = ld_n
    if formula == 3:  # Шифринсона
        ld = ld_s
    if formula == 4:  # Колбрука-Уайта
        ld = ld_k

    gs = get_sprn(ld, d, t)

    if ut_dolja > 0:
        gs *= l
        gs *= (1 + ut_dolja)
    else:
        gs *= (l + ut_diametr * ut_mestnoe / ld / 1000.)

    return gs

#-----------------------------------------------------------------------------------

# Пересчитывает сопротивление

def reset_sopr(G, x, list_l, heatSourceID):

    '''
        0 ItWin, 
        1 Альтшуля, 
        2 Никурадзе, 
        3 Шифринсона, 
        4 Колбрука-Уайта
    '''

    if config.args.sopr == 0:  # Наше сопротивление
        return

#    print('==========================================')

    ct = get_ct()
    Tn0 = ct.get('t_or')

    try:
        for i in range(len(list_l)):
            n1, n2, key, i1, i2, k_l, typ, param = list_l[i]

            e = G.edges[n1, n2, key]

            if typ == 'heatPipeSections':      # Участки
                nn1 = G.nodes[n1]
                nn2 = G.nodes[n2]
                t1 = nn1.get('t')
                t2 = nn1.get('t')
                po = e.get('po')

                kod1 = nn1.get('externalCodeID')
                kod2 = nn2.get('externalCodeID')

                rs1 = read_gid.map_rs.get(kod1, None)
                rs2 = read_gid.map_rs.get(kod2, None)

                rs = rs1

                name = w_print.line_name_n1_n2(G, n1, n2)            

                if heatSourceID is None:
                    heatSourceID = rs.get('heatSourceID', None)

                ist = read_gid.map_ist.get(heatSourceID, None)

                if ist is None:
                    print('!!!!!!!!!!!!!!!!', t1, t2)
                    tP = 150
                    tO = 70
#                    continue

                else:
                    tP = ist.get('t1_r')
                    tO = ist.get('t2_r')
    
                t1 = tP if po == 1 else tO
                t2 = tP if po == 1 else tO

                ut_diametr = e.get('diametr', 1000.)

                if ut_diametr == 990.4:
                    print(name, t1)
                
                l_n = e['num']
                ras = x[l_n]

                ut = e

                S = soprUT(ut, t1, ras, config.args.sopr)

                if S:
                    e['S'] = S
                    typ2, S_old, n_rd = param
                    param = typ2, S, n_rd
                    list_l[i] = n1, n2, key, i1, i2, k_l, typ, param


    except Exception as e:
        print(f'Что-то с сопротивлениями {e}')
        exit(0)



