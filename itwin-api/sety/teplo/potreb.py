import math

from scipy.optimize import fsolve
from scipy.optimize import newton

from sety.teplo import gid_init
from sety.any.colors import cprint


'''
t01  = 150;  # Температура в подаче расчетная
t02  = 70;   # Температура в обратке расчетная
t03  = 95;   # Температура в после узла расчетная
tvn1 = 18;   # Температура внутри помещения расчетная
tn1  = -32;  # Температура наружного воздуха расчетная
'''

#-----------------------------------------------------------------------------------

#-----------------------------------------------
# Тепловые потери без узла смешения
#-----------------------------------------------

def potreb1(pr, t1, tn, g, _q):
#, double *t2, double *tv, double *q


    if t1 > 200:
        cprint(f'Нужно разобраться с потребителем [{pr.get('kod', '??')} {pr.get('name', '??')}]', color='red')
        t1 = 200



#    print('====', t1, tn, g, _q)
    Q = _q;
    T1 = t1;
    Tn = tn;
    G = g;

    dt = ((t01+t02)/2-tvn1)

#    for key, value in vars().items(): print(key, value)

    def funcd1(x):
         xx = (Tn-x)/(tn1-tvn1)

         if xx <= 0:
            return 0
         f = math.pow(xx, 0.2)*(T1-Q/(2.*G)*xx-x) - xx*dt
         return f

    def funcd2(x):
         xx = (Tn-x)/(tn1-tvn1)
         if xx <= 0:
            return 0

         df = -0.2/math.pow(xx,0.8)*(T1-0.5*Q/G*xx-x)/(tn1-tvn1)+math.pow(xx,0.2)*(0.5*Q/G/(tn1-tvn1)-1.0)+1/(tn1-tvn1)*dt
         return df


    Tvn = 0

    try:
        Tvn = newton( funcd1, 18, funcd2)
    except Exception:
        print(f'1 [{pr.get('kod', '??')} {pr.get('name', '??')}]', t1, tn, g, _q)
        exit(1)

#    for key, value in vars().items(): print(key, value)


    tv = Tvn
    t2 = T1 - Q/G*(Tn-Tvn)/(tn1-tvn1)
    q = G*(T1-t2)

#  for key, value in vars().items(): print(key, value)

# Тут все линеаризовано 

    dt = ((t01+t02)/2-tvn1)
    x = (dt+Q/2./G)/(tvn1-tn1)

    ttvn = (T1+x*Tn)/(1+x)
    tt2 = T1 - Q/G*(Tn-ttvn)/(tn1-tvn1)
    qq = G*(T1-tt2)




#  if qq != 0:
#    dq = abs((qq-q)/qq)
#    if dq > maxdq and t1 > 0 and t1 < 200:
#      maxdq = dq

    return q, t2, tv


#-----------------------------------------------------------------------------------

#-----------------------------------------------
# Тепловые потери с узлом смешения
#-----------------------------------------------

def potreb2(pr, t1, tn, g, _q, _u, debug):
  #, double *t2, double *t3, double *tv, double *q  

#    for key, value in vars().items(): print(key, value)

    if t1 > 200:
        cprint(f'Нужно разобраться с потребителем [{pr.get('kod', '??')} {pr.get('name', '??')}]', color='red')
        t1 = 200


#    print('===========================================')
#    print(t1, tn, g, _q, _u)

#    print(t01, t02, t03, 'tvn = ', tvn1, tn1)

    Q = _q
    u = _u  
    T1 = t1
    Tn = tn
    G = g

    dt = ((t03+t02)/2-tvn1)

    def funcd1(x):
        xx = (Tn-x)/(tn1-tvn1)

#        print(f'({Tn}-{x})/({tn1}-{tvn1})')

        if xx <= 0 : 
            return 1
      
        f = math.pow(xx, 0.2)*(T1-(1.+2.*u)/(1.+1.*u)*Q/(2.*G)*xx-x) - xx*dt
        return f

    def funcd2(x):
        xx = (Tn-x)/(tn1-tvn1)

        if xx <= 0 : 
            return 1

        df = (-0.2/math.pow(xx,0.8)*(T1-0.5*(1.0+2.0*u)/(1.0+1.0*u)*Q/G*xx-x)/(tn1-tvn1)
            +pow(xx,0.2)*(0.5*(1.0+2.0*u)/(1.0+1.0*u)*Q/G/(tn1-tvn1)-1.0)+1/(tn1-tvn1)*dt)
        return df

    try:
        Tvn = newton( funcd1, 18, funcd2)
    except Exception:
        print(f'2 [{pr.get('kod', '??')} {pr.get('name', '??')}]', t1, tn, g, _q)
        a = 1/0
        exit(1)

#    if debug:
#        print(f'Tvn={Tvn}')

    tv = Tvn
    t3 = T3 = T1 - Q/G*(Tn-Tvn)/(tn1-tvn1)
    t2 = (T1+u*T3)/(1.+u)
    q = G*(T1-T3);  # Тепло

#    if debug:
#        print(f'()() tv={tv} t3={t3} t2={t2} q={q}')

    return q, t3, t2, tv
    return q, t2, t3, tv

    ttt2 = (G*T1*t01 + G*T1*t02 - 2*G*T1*tn1 - Q*T1 + 2*Q*Tn)/(G*t01 + G*t02 - 2*G*tn1 + Q)

    dt = (t01+t02)/2-tvn1

    x = (dt+Q/2./G)/(tvn1-tn1)

    ttvn = (T1+x*Tn)/(1+x)
    tt2 = T1 - Q/G*(Tn-ttvn)/(tn1-tvn1)
    qq = G*(T1-tt2)

    t3 = T1 - Q/G*(Tn-Tvn)/(tn1-tvn1)

#    if debug:
#        print(f'tv={ttvn} t3={t3} t2={tt2} q={qq}')


    return qq, tt2, t3, ttvn

#-----------------------------------------------------------------------------------

def set_rasz(_t01, _t02, _t03, _tvn1, Tn1):
    global t01, t02, t03, tvn1, tn1

    t01 = _t01   # Температура в подаче расчетная
    t02 = _t02   # Температура в обратке расчетная
    t03 = _t03   # Температура в после узла расчетная
    tvn1 = _tvn1 # Температура внутри помещения расчетная
    tn1 = Tn1    # Температура наружного воздуха расчетная


    if tvn1 > 30:
        cprint('set_rasz', _t01, _t02, _t03, _tvn1, Tn1, color='red')
        exit(1)


#-----------------------------------------------------------------------------------

def set_rasz_pr(pr, tr, Tn1):
    global t01, t02, t03, tvn1, tn1

    t01 = tr.get('Tr_co_1_zco', 0)   # Температура в подаче расчетная
    t02 = tr.get('Tr_co_2_zco', 0)   # Температура в обратке расчетная
    t03 = tr.get('Tr_co_3_zco', 0)   # Температура в после узла расчетная
    tvn1 = pr.get('Tr_tv_co', 0) # Температура внутри помещения расчетная
    tn1 = Tn1           # Температура наружного воздуха расчетная

    if tvn1 > 30:
        kod = pr.get('kod', '')
        name = pr.get('name', '')
#        print(1, pr)
        cprint(f'Неправильная расчетная температура {tvn1} в отапливаемых помещениях в потребителе [{kod} {name}]', color='red')
#        print('set_rasz_pr', t01, t02, t03, tvn1, Tn1)
        exit(1)


def set_rasz_po(po, tr, Tn1):
    global t01, t02, t03, tvn1, tn1

    t01 = tr.get('Tr_co_1_zco', 0)   # Температура в подаче расчетная
    t02 = tr.get('Tr_co_2_zco', 0)   # Температура в обратке расчетная
    t03 = tr.get('Tr_co_3_zco', 0)   # Температура в после узла расчетная
    tvn1 = po.get('Tr_tv_co_zco', 0) # Температура внутри помещения расчетная
    tn1 = Tn1           # Температура наружного воздуха расчетная

    if tvn1 > 30:
        kod = po.get('kod', '')
        name = po.get('name', '')
        print(2,po)
        cprint(f'Неправильная расчетная температура {tvn1} в отапливаемых помещениях в потребителе [{kod} {name}]', color='red')
#        print('set_rasz_po', t01, t02, t03, tvn1, Tn1)
        exit(1)



#-----------------------------------------------------------------------------------


if __name__ == "__main__":

    Q = 1000000
    G = 12500

    po = {}

    tr = gid_init.get_tr0()
    pr = gid_init.get_pr0('gvsm', 0.2)

    set_rasz_pr(pr, tr, -32)

#    qq, t2, tv = potreb1(150, -32, G, Q)
#    print(qq, t2, tv)


    qq, t2, t3, tv = potreb2(131.81394823191573, -25.0, 2145.29, 133000.0, 1.48)

#    qq, t2, t3, tv = potreb2(150, -32, G, Q, 2.2)
    print(qq, t2, t3, tv)



