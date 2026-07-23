
#-----------------------------------------------
# Расход тепла на отопление
#-----------------------------------------------

from sety import read_gid
from sety.teplo.m import srlog
from sety.ct import get_ct


t11 = 150  # /* 150 */   # Температура в подаче расчетная
t12 = 80  # /* 70 */    # Температура в обратке расчетная


t01 = 0  # /* 150 */   # Температура в подаче расчетная
t02 = 0  # /* 70 */    # Температура в обратке расчетная
t03 = 0  # /* 95 */    # Температура в после узла расчетная
tvn1 = 0  # /* 18 */   # Температура внутри помещения расчетная

   # = 1e6  # Нагрузка ккал/час для основного режима

# Текущий режим

Gs = 0  # /*  = 30. */   # расход сетевой воды, т/ч
Gx = 0  # /*  = 25. */     # расход водопроводной воды (или местной СО), т/ч
T1 = 0  # /*  = 150. */     # температура сетевой воды на входе
Tx = 0  # /*  = 5. */       # температура водопроводной (местной) воды на входе


#def rasVENT(const PR *pr, double G, double _q, double t, double *t2, double *tv, double Tn):

#-----------------------------------------------------------------------------------

def rasVENT(pr, G, _q, t, Tn, debug):
    '''
     G = 12500
     _q = 1000000
     t = 70
     Tn = -1
   '''

    ct = get_ct()
    tr = pr.get('kodtr', None)
    tr = read_gid.map_tr.get(tr, None)
    
#    const TR *tr = getTR(pr->kodtr)

    if tr is None:
        print('Не создан объект "Расчетные температуры"')
        fatal_error()
        return 0, 0

    if ct is None:
        print('Не создан объект \"Система теплоснабжения"')
        fatal_error()
        return 0, 0

    if _q == 0 or G == 0:
      tv = Tn
      t2 = t
      return t2, tv

    Qv1 = _q
    tnv1 = ct.get('t_vr', 0)  # Температура наружного воздуха расчетная
    tv1 = pr.get('Tr_tv_cv', 0) # Температура внутри помещения расчетная

    tau1v = tr.get('Tr_1_cv', 0) #  Расчетная температура сетевой воды на входе вентиляции или воздушной системы отопления      
    tau2v = tr.get('Tr_2_cv', 0) #  Расчетная температура сетевой воды на выходе вентиляции или воздушной системы отопления     

    tau1 = t

    Gv = G
    tn = Tn

    Wvozd1 = Qv1/(tv1-tnv1)
    Wv1 = Qv1/(tau1v-tau2v)
    dtsr1 = (tau1v+tau2v)/2-(tv1+tnv1)/2
    F = Qv1/(pow(Wvozd1, 0.4)*pow(Wv1,0.15)*dtsr1)
    Qvr = (tv1-tn)/(tv1-tnv1)*Qv1
    Qv = (tau1-tn)/(0.5/Wvozd1+0.5/Gv+1/(F*pow(Wvozd1, 0.4)*pow(Gv,0.15)))

    Qv_ = Qv/Qvr

    tv = tn+(tv1-tn)*Qv_
    t2 = tau1-Qv/Gv

#    if debug:
#        print(f'<  q={_q} t={t} Tn={Tn} tau1v={tau1v} tau2v={tau2v} tv1={tv1} G={G}')
#        print(f'<  tv={tv} t2={t2}')


    return t2, tv
