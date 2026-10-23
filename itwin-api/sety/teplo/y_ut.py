import math
import traceback

from sety.ct import get_ct
from sety.sprav import map_s07
from sety.sprav import map_s39

from sety import read_tg
from sety import config


#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Теплопроводность изоляции по справочнику 07 (l + k*(t+40)/2); по умолчанию L0=0.087, K=0.00012.
def get_lambda(kod_izol: int, t: float) -> float:
    L0 = 0.087
    K = 0.00012

    v = map_s07.get(kod_izol, None)

    if v is not None:
        L0 = v.get('l', 0)
        K = v.get('k', 0)

    lam = L0 + K * (t + 40) / 2

    return lam

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Тепловые потери (подача, обратка) при канальной прокладке по термическим сопротивлениям
# изоляции, воздуха канала и грунта. Нерабочая: используется неопределенная log (см. отчет).
def get_qq_izol_kanal(utP: dict, utO: dict, Tn: float, Tg: float, tP: float, tO: float) -> (float, float):
    #, double& qP, double& qO

    dP = utP.get('diametr', 0) + 2 * utP.get('tol', 0)
    dO = utO.get('diametr', 0) + 2 * utO.get('tol', 0)

    k_izol = utP.get('k_izol', 0)  #  Коэффициент поправки теплопроводности изоляционного материала
    izol_air = utP.get('izol_air', 0)  #  Коэфф.теплоотдачи от изоляции трубопровода к воздуху канала
    air_ground = utP.get('air_ground', 0)  #  Коэфф.теплоотдачи от воздуха канала к грунту
    tpground = utP.get('tpground', 0)  #  Теплопроводность грунта
    thickizol = utP.get('thickizol', 0)  #  Толщина изоляции
    depth = utP.get('depth', 0)  #  Глубина заложения до оси теплопровода

    chanwidth = utP.get('chanwidth', 0)  #  Ширина канала
    chanheight = utP.get('chanheight', 0)  #  Высота канала

    RizolP = k_izol * log(1. + 2 * thickizol / dP) / (2 * math.pi * get_lambda(utP.get('kod_izol', 0), tP))
    RizolO = k_izol * log(1. + 2 * thickizol / dO) / (2 * math.pi * get_lambda(utO.get('kod_izol', 0), tO))

    RvozdP = 1000 / (math.pi * izol_air * (dP + 2 * thickizol))
    RvozdO = 1000 / (math.pi * izol_air * (dO + 2 * thickizol))

    dekv = 2 * chanwidth * chanheight / (chanwidth + chanheight)
    Rkan = 1000 / (math.pi * air_ground * dekv)

    Rgr = (math.log(3.5 * 1000 * depth / chanheight * pow(chanheight / chanwidth, 0.25)) /
        (tpground * (5.7 + 0.5 * chanwidth / chanheight)))

    tkan = ((tP / (RizolP + RvozdP) + tO / (RizolO + RvozdO) + Tg / (Rkan + Rgr)) /
        (1 / (RizolP + RvozdP) + 1 / (RizolO + RvozdO) + 1 / (Rkan + Rgr)))

    qkan = (tkan - Tg) / (Rkan + Rgr) / 1.163

    qP = qkan * tP / (tP + tO)
    qO = qkan * tO / (tP + tO)

    return qP, qO

#-----------------------------------------------------------------------------------


# [Claude 2026-10-18] Тепловые потери (подача, обратка) при бесканальной прокладке с учетом взаимного влияния труб.
# Нерабочая: используется неопределенная log.
def get_qq_izol_bezkanal(utP: dict, utO: dict, Tn, Tg, tP, tO):
#{
#, double& qP, double& qO

    dP = utP.get('diametr', 0) + 2 * utP.get('tol', 0)
    dO = utO.get('diametr', 0) + 2 * utO.get('tol', 0)

    k_izol = utP.get('k_izol', 0)  #  Коэффициент поправки теплопроводности изоляционного материала
    thickizol = utP.get('thickizol', 0)  #  Толщина изоляции
    depth = utP.get('depth', 0)  #  Глубина заложения до оси теплопровода
    tpground = utP.get('tpground', 0)  #  Теплопроводность грунта
    distance = utP.get('distance', 0)  #  Расстояние между осями теплопроводов

    RizolP = k_izol * log(1. + 2 * thickizol / dP) / (2 * math.pi * get_lambda(utP.get('kod_izol', 0), tP))
    RizolO = k_izol * log(1. + 2 * thickizol / dO) / (2 * math.pi * get_lambda(utO.get('kod_izol', 0), tO))

    RgrP = log(4 * depth * 1000 / (dP + 2 * thickizol)) / (2 * math.pi * tpground)
    RgrO = log(4 * depth * 1000 / (dO + 2 * thickizol)) / (2 * math.pi * tpground)

    Rpo = log(1 + pow(2 * 1000 * depth / distance, 2)) / (4 * math.pi * tpground)

    qP = ((tP - Tg) * (RizolO + RgrO) - (tO - Tg) * Rpo) / ((RizolP + RgrP) * (RizolO + RgrO) - Rpo * Rpo)
    qO = ((tO - Tg) * (RizolP + RgrP) - (tP - Tg) * Rpo) / ((RizolP + RgrP) * (RizolO + RgrO) - Rpo * Rpo)

    qP /= 1.163
    qO /= 1.163

    return qP, qO


#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Тепловые потери по типу прокладки (сейчас всегда канальная, typ=1). Нигде не вызывается.
def get_qq_izol(utP: dict, utO: dict, Tn: float, Tg: float, tP: float, tO : float) -> (float, float):
    typ = 1

    #, double& qP, double& qO

    if typ == 1: #'К 
        return get_qq_izol_kanal(utP, utO, Tn, Tg, tP, tO)

    if typ == 2: #'Б'
        return get_qq_izol_bezkanal(utP, utO, Tn, Tg, tP, tO)

#    case 3 #'П'
#    case 4 #'Н'
    if typ in (3, 4):
        return get_qq_izol_nadz(utP, utO, Tn, Tg, tP, tO)
    return 0, 0


#-----------------------------------------------------------------------------------

'''

def get_qq(ut, Tn, const CLine* l, tp_metod):

    if True:
#    if ut->name_calctpr == 'И' && tp_metod == 0 || tp_metod == 2:
#        double qP, qO, t1, t2, t3
#        const PC* pc = getPC(where(l))
        if (pc) {
            if get_TG(pc->kod_ist, Tn, t1, t2, t3):
                get_qq_izol(ut, ut, Tn, 5, t1, t2, qP, qO)
                if where(l)->po() == CPOD:
                    qq = qP
                }
                else:
                    qq = qO
    else:
        qq = get_qq(l, Tn)

    return qq

'''
#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Линейная интерполяция y в точке x по точкам (x1, y1), (x2, y2).
def appr(x, x1, y1, x2, y2):

#    print('appr, _________________')
#    for key, value in vars().items(): print(key, value)
    
    y = y1 + (x - x1)*(y2 - y1) / (x2 - x1)
    return y

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Норма удельных тепловых потерь для одной строки справочника 39 (один диаметр): интерполяция по
# температуре теплоносителя (среднегодовой или для надземной прокладки - по трубе) и выбор подачи/обратки.
def get_q_S39(year, typ_pr, po, t1, t2, tn, tg, kolvork, s39):
#    double  *tt = (double  *)& s39.t1_1
#    double  *qq
#    double tt1, tt2, propor, t
#    int i

#    for key, value in vars().items(): print(key, value)

#    print('<<<', s39)

    tt = s39['t1']

    if kolvork != 0:
        qP = s39['qp2']
        qO = s39['qo2']
    else:
        qP = s39['qp1']
        qO = s39['qo1']

    if typ_pr == 4 : #'Н'
        if po == 2:
            t = t2
        else:
            t = t1
    else:
        t = (t1 + t2) / 2

    if year == 1:
        if typ_pr == 4: #/*'Н'*/) {
            t -= tn
        else:
            t -= tg



    n = 4
    if tt[2] == tt[3]: n = 3
    if tt[1] == tt[2]: n = 2

#    print('n====', n, tt)


    for i in range(n - 1):
        tt1 = tt[i]
        tt2 = tt[i + 1]

        if typ_pr != 4: #/*'Н'*/) {
            tt1 = (tt[i] + s39.get('t2', 0)) / 2
            tt2 = (tt[i + 1] + s39.get('t2', 0)) / 2

        if year == 1:
            if typ_pr == 4: #/*'Н'*/) {
                tt1 -= s39.get('tn', 0)
                tt2 -= s39.get('tn', 0)
            else:
                tt1 -= s39.get('tg', 0)
                tt2 -= s39.get('tg', 0)

        if t <= tt2 or i + 1 == n - 1:
            break

    propor = (t - tt1) / (tt2 - tt1)

    dp = 0 if po == 1 else 1

    if typ_pr == 4: #/*'Н'*/) {
        dp = 0

    qP1 = qP[i] * (1. - propor) + qP[i+1] * propor
    qO1 = qO[i] * (1. - propor) + qO[i+1] * propor

#    print('qP1', qP1)
#    print('qO1', qO1)


    if typ_pr == 4: # /*'Н'*/) {
        qP = qP1
        qO = qO1
    else:
        dt = 1e10
        tP = 0

        for i in range(4):

#            print(i, t1, tt[i], dt)
            
            if abs(t1 - tt[i]) < dt:
                tP = tt[i]
                dt = abs(t1 - tt[i])


        qP = appr(t1, s39.get('t2', 0), qO1, tP, qP1)
        qO = appr(t2, s39.get('t2', 0), qO1, tP, qP1)


#    print('qP', qP)
#    print('qO', qO)


    if typ_pr == 4: #/*'Н'*/) {
        return qP
    elif po == 1:
        return qP
    else:
        return qO
        
#-----------------------------------------------------------------------------------

warned_s39 = set()   # исправлено Claude, 2026-10-20 (ревью п. 1.13): диаметры, о которых уже предупредили

# [Claude 2026-10-18] Норма удельных тепловых потерь по справочнику 39: выбирает таблицу по периоду прокладки year и типу
# прокладки, интерполирует по диаметру между соседними строками. Если таблицы нет - возвращает 300.
def get_q_new(
      year: int, 
      typ_pr: int, 
      diam_usl: float, 
      diam: float, 
      po: int, 
      t1: float, 
      t2: float, 
      tn: float, 
      tg: float, 
      kolvork: bool) -> float:

    if year != 1: diam = diam_usl

#    1: 'К', 2: 'Б', 3: 'П', 4: 'Н', 5: 'О'
    typ_pr_let = {1: 'К', 2: 'Б', 3: 'К', 4: 'Н', 5: 'К'}.get(typ_pr, 'К')
    
#    print(typ_pr)
#    for key, value in vars().items(): print(key, value)

#    for k, v in map_s39.items():
#        print(k, v)

    qqq = map_s39.get((year, typ_pr_let), None)

#    for k, v in qqq.items():
#        print(k, v)
#    print('====', year, typ_pr_let, typ_pr)
#    exit(1)

    if qqq is None: 
        print('Ошибка в s39 !!!!!!')
#        exit(1)
        return 300

#    for k, v in qqq.items():
#        print(k, v)
#    exit(1)

    # исправлено Claude, 2026-10-20 (ревью п. 1.13): строки сортируются по диаметру (справочник читается без ORDER BY); диаметр больше
    # максимального - линейная экстраполяция по последнему отрезку (раньше d1 == d2 - деление на ноль,
    # UnboundLocalError в norma и exit(1) всего расчета); меньше минимального - первая строка, как было.
    def d_s39(v):
        return max(v.get('d', 0), v.get('dy', 0))

    rows = sorted(qqq.values(), key=d_s39)

    i2 = next((i for i, v in enumerate(rows) if diam <= d_s39(v)), None)

    if i2 is None and len(rows) > 1:
        s39_1, s39_2 = rows[-2], rows[-1]
        if (year, typ_pr_let, diam) not in warned_s39:
            warned_s39.add((year, typ_pr_let, diam))
            print(f'Диаметр {diam} больше максимального в справочнике 39 ({d_s39(rows[-1])}), норма экстраполирована')
    elif i2 is None or i2 == 0:
        s39_1 = s39_2 = rows[-1] if i2 is None else rows[0]
    else:
        s39_1, s39_2 = rows[i2-1], rows[i2]

    d1 = d_s39(s39_1)
    d2 = d_s39(s39_2)
    propor = (diam - d1) / (d2 - d1) if d2 != d1 else 0


#    for key, value in vars().items(): print(key, value)
#    print('d1=', d2, 'd2=', d2 )
#    print('propor=', propor)

    q1 = get_q_S39(year, typ_pr, po, t1, t2, tn, tg, kolvork, s39_1)

#    print('!!!!!!!!!!!!!!!!!======================')

    q2 = get_q_S39(year, typ_pr, po, t1, t2, tn, tg, kolvork, s39_2)

#    print('===', year, typ_pr, po, t1, t2, tn, tg, kolvork, s39_2)
#    print('propor', propor, 'q2', q2)

    return q1 * (1. - propor) + q2 * propor

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Норма удельных тепловых потерь участка ut: период по году окончания строительства
# (до 1990, до 1998, до 2003, позже), тип прокладки, диаметр с изоляцией, температуры t1/t2.
def get_qq(ut: dict, Tn: float, t1: float, t2: float, po: int) -> float:
    qq = 0.
    y = 0

    l_dateend = ut.get('dateend')

    if l_dateend is None:
        l_dateend = 0
    else:
        l_dateend = l_dateend.year

#    print('l_dateend=', l_dateend.year)

    if l_dateend < 1990: y = 1
    elif l_dateend < 1998: y = 2
    elif l_dateend <= 2003: y = 3
    else: y = 4

#    print('y=', y)

    l_typ_pr = ut.get('name_typ', 0)
    l_diametr_usl = ut.get('diametr_usl', 0)
    l_diametr = ut.get('diametr', 0)
    l_tol = ut.get('tol', 0)
    l_kolwork = ut.get('kolwork', 0)

    ct = get_ct()
    ct_tg_god = ct.get('tg_god', 0)

#    for key, value in vars().items(): print(key, value)   

    qq = get_q_new(y, l_typ_pr, l_diametr_usl, l_diametr + 2 * l_tol, po, t1, t2, Tn, ct_tg_god, l_kolwork)

    return qq

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Коэффициент местных тепловых потерь: 1.15 при диаметре >= 150 и типе прокладки 1, иначе 1.2.
def get_beta(typ_pr: int, diam: float) -> float:
#    static map<char, S30>::const_iterator it

#    char typ = get_char_typ(typ_pr)

#    if (typ == 'П') typ = 'К'

#    if diam >= 150 and typ_pr == 2: # Бесканальная или магистраль
    if diam >= 150 and typ_pr == 1: # Бесканальная или магистраль
        return 1.15
    else:
        return 1.2
       
        

    '''


    it = map_s30.find(typ)
    if (it == map_s30.end()) {
        return 0
    }
    if (diam < it->second.diametr) {
        return it->second.beta_rasp
    }
    else {
        return it->second.beta_mag
    }
    
    '''

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Норма тепловых потерь участка для подачи (po=1) или обратки (po=2) при расчетной наружной температуре
# по температурному графику источника (по умолчанию 150/70).
def norma(ut: dict, po: int) -> float:

#    return 1
    
    ct = get_ct()
    Tn = ct.get('t_or', 0)

    if config.args.n_trtp == 0:  #  Расчетная температура наружного воздуха для отопления      
        Tn = ct.get('t_or', 0)
    elif config.args.n_trtp == 1:  #  Среднесезонная температура наружного воздуха, отопит.период
        Tn = ct.get('tn_god', 0)
    else:
        Tn = config.args.Tn

    Tn = ct.get('t_or', 0)

    t1, t2, t3, tv = 150, 70, 95, 150

    heatSourceID = ut.get('heatSourceID', None)


    try:
        v = read_tg.get_tg(heatSourceID, Tn)
    except Exception:
        print('!!!', traceback.print_exc())

    if v is not None:
        t1, t2, t3, tv = v

#    print(t1, t2, t3, tv, Tn)


    try:
        qq = get_qq(ut, Tn, t1, t2, po)
    except Exception as e:
        print('-----------')
        print(e)
        print('-----------')
        raise   # исправлено Claude, 2026-10-20 (ревью п. 1.13): было return неопределенного qq - UnboundLocalError вместо настоящей ошибки
        

#    print('    ', qq)

    return qq



#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Нормативные тепловые потери участка (Гкал): норма * длина * коэффициент местных потерь * kti / 1e6.
def Y(ut: dict, po: int) -> float:
#    if ut.typ != 'heatPipeSections':
#        return 0
    typ_pr = ut.get('name_typ', 0)
    diametr = ut.get('diametr', 0)
    dlina = ut.get('dlina', 0)
    tol = ut.get('tol', 0)
    kti = ut.get('kti', 1)


#    print('typ_pr=', typ_pr)
#    print('diametr=', diametr)
#    print('tol=', tol)


    beta = get_beta(typ_pr, diametr + 2 * tol)
    qq = norma(ut, po)

#    qq = get_qq(ut, getGlobal()->Tn, l, getGlobal()->tp_metod)
#    qq = ut.get('qq', 1)

    '''
    qq = l->qq

    switch (n_trtp) {
    case 0: qq = l->qq_ras35   break
    case 1: qq = l->qq_ras15   break
    }
    '''

    y = qq * dlina * beta * kti / 1.e6  # Нормативная среднегодовая Гкал


    if dlina == 100000000:
        print('typ_pr=', typ_pr, beta)
        print(y)

    return y

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    print(__package__)

    lam = get_lambda(1, -32) 

#    print('lam =', lam)

