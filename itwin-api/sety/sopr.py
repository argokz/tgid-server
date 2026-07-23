import math
from collections import OrderedDict

from sety import const
from sety import w_print

from sety import sopr_ut
from sety import config

#-----------------------------------------------------------------------------------

def gsprn(d: float, ke: float, t_form: str):
    if ke == 0.: ke = 0.5

#    print('d = ', d, 'ke = ', ke)

    if t_form == 'SIFRENSON':
        lyam = 0.11*pow(ke / d, 0.25)
    else:
        ppr = math.log10(3.715*d / ke)
        lyam = 1. / 4. / ppr / ppr
    rgr = (6.94988e+6)*lyam / pow(d, 5.)

    return rgr, lyam

#-----------------------------------------------------------------------------------

def soprUT(ut, t):
    gs = 0.
    '''
    double rmn;
    int truba;
    double lyam;
    double scher = ut->scher;
    '''

    ut_dlina = ut.get('dlina', 1.)
    ut_sopr = ut.get('sopr', 0.)
    
#    if ut_sopr is None:
#        print('!!!!!!!!')

    ut_truba = ut.get('truba', 1)
    ut_diametr = ut.get('diametr', 1000.)
    ut_scher = ut.get('scher', 0.5)
    ut_dolja = ut.get('dolja', 0.)      # Доля местных потерь
    ut_mestnoe = ut.get('mestnoe', 0.)  # Сумма коэффициентов местных сопротивлений


    if ut_sopr > 0.:
        gs = ut_sopr
        return gs
        rmn = -1.
    else:
        '''
        const KV* kv

        if (po == CPOD) {
            kv = getKV(ut_kodkvp)
        }
        else {
            kv = getKV(ut_kodkvo)
        }

        if (kv && kv->cher > 0) {
            ut_scher *= kv->cher
        }
        '''

        if ut_truba < 1: ut_truba = 1

        #    gs = gsprn(ut_diametr,ut_scher,&lyam, ut_name_typ)/(ut_truba*ut_truba)

        gs, lyam = gsprn(ut_diametr, ut_scher, ' ')

#        print(gs, lyam)
    
        gs /= (ut_truba * ut_truba)

#        print(gs, lyam)

        if ut_dolja > 0.:
            rmn = gs * ut_dlina * ut_dolja
            gs *= ut_dlina * (1 + ut_dolja)


        else:

            try:
                rmn = gs * ut_diametr / lyam / 1000. * ut_mestnoe
            except:
                print('Ошибка !!!')
                print(gs)
                print(ut_diametr)
                print(lyam)
                print(ut_mestnoe)
                print(ut)
                exit(1)


#            rmn = gs * ut_diametr / lyam / 1000. * ut_mestnoe


            gs *= (ut_dlina + ut_diametr * ut_mestnoe / lyam / 1000.)
            #      double me = ut_diametr/lyam/1000.*ut_mestnoe
            #    if (ut_mestnoe) wout << ut_diametr << " mestn=" << ut_mestnoe << " dolya=" << me/ut_dlina << " " << ut_dlina <<  " " << me << endl


        if config.args.sopr != 0:  # Zulu
            gsZ = sopr_ut.soprUT(ut, t, None, config.args.sopr)

            if not gsZ is None:
                return gsZ


    return gs

#-----------------------------------------------------------------------------------
def ksi(otn):
#    struct
#    {
#        double otn, koef
#    } table[] =

    table = OrderedDict({
        10: 1300,
        15: 433.7,
        20: 80.2,
        25: 23.8,
        30: 17.9,
        35: 13.1,
        40: 9.4,
        45: 6.55,
        50: 4.45,
        55: 3.0,
        60: 2.05,
        65: 2.05,
        70: 1.5,
        75: 1.25,
        80: 1.1,
        85: 1.0,
        90: 0.8,
        95: 0.35,
        100: 0.35,
        110: 0.35
    })

    if otn >= 100.: return 0.35
    if otn <= 10.: return 1300

    kk = 1300

    for o, k in table.items():
#        print(otn, o, k, flush=True)
        if o >= otn:
#            print('=', otn, o, k, flush=True)
            return kk

        kk = k

    return 1300

#-----------------------------------------------------------------------------------


def soprZD(zd):
    Du = zd.get('diametr', 0)  # Диаметр условный, мм

    if Du == 0:     # Диаметр не задан, сопротивление 0
        Du = 1000

        return 1e-20
    
    proc = zd.get('proz_kv', 0) / 100.

    Kp = 0.95 # Коэффициент поправочный на размер проходного сечения


#    Du = zd.get('diametr', 1000)  # Диаметр условный, мм
                       #  Du = 1000

    Fpr = math.pi / 4 * (Du*Du / 100.)*Kp

    if zd.get('sost', 1) == const.L_PART:
        #    if (zd['proz']_kv = )
        koef = ksi(zd.get('proz_kv', 0))
    else:
        koef = 0.35

    kv = 5.04*Fpr / math.sqrt(koef)

    sopr = 10. / kv / kv # 10 метров водяного столба - перепад на открытой задвижке
                          #  sopr = 0
#    print(sopr)
#    exit(1)

    return sopr

#-----------------------------------------------------------------------------------

def soprZD2(zd):
    proc = zd.get('proz_kv', 0) / 100.

    Kp = 0.95 # Коэффициент поправочный на размер проходного сечения

    Du = zd.get('diametr', 1000)  # Диаметр условный, мм
                                  #  Du = 1000

    Fpr = math.pi / 4 * (Du*Du / 100.)*Kp

    if zd.get('sost', 1) == const.L_PART:
        #    if (zd.get('proz_kv', 0) = )
        koef = ksi(zd.get('proz_kv', 0))
    else:
        koef = 0.35

    kv = 5.04*Fpr / math.sqrt(koef)

    sopr = 10. / kv / kv # 10 метров водяного столба - перепад на открытой задвижке
                          #  sopr = 0
    return sopr

#-----------------------------------------------------------------------------------

def soprBP(bp):
    d = bp.get('diam', 400)
    l = bp.get('dln', 1)
    scher = bp.get('scher', 0)

    if d == 0: d = 400
    if l == 0: l = 1
    if scher == 0: scher = 0.5

    ppr = math.log10(3.715*d / scher)
    ppr = 1. / 4. / ppr / ppr
    sopr_u = 6.94988e+6*ppr / math.pow(d, 5.)
    sopr_u *= (l + d / ppr / 1000.*bp.get('sum_m_s', 0))

    return sopr_u

#-----------------------------------------------------------------------------------

def soprDR(dr):
    d0 = dr.get('dru_home', 400)
    n = dr.get('kol_home', 1)

    if d0 == 0: return 1
    if n == 0: n = 1

    sopr = 1e4 / math.pow(d0, 4.) * n

    return sopr

#-----------------------------------------------------------------------------------

if __name__ == "__main__":
    ut = {}

    ut['dlina'] = 100
    ut['sopr'] = 0
    ut['truba'] = 1
    ut['scher'] = 0.5
    ut['diametr'] = 100
    ut['dolja'] = 0
    ut['mestnoe'] = 0

    zd = {}
    zd['sost'] = 4
    zd['proz_kv'] = 31

    s = soprBP(zd)

    s = soprUT(ut, 1)

    print(s, flush=True)
