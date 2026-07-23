from sety import config
from sety.teplo import gid_init

#from sety.teplo.gid_init import get_ct
from sety.ct import get_ct


from sety.teplo.potreb import potreb1
from sety.teplo.potreb import potreb2
from sety.teplo.tepl_co1 import rasTT2

from sety.teplo.potreb import set_rasz_pr
from sety import read_tg
from sety.consumption import is_bezelevator

import time


def getUFpr(n, pr):
    
    cxema = pr.get('cxema', '??')
    if is_bezelevator(cxema):
        return 0

#    print(n.get('typ'))
    if config.args.uf_calc and config.args.is_tg:
        '''
        pr_typ = n.get('typ')


        if pr.get('uf0', 0) == 0:
            return 0

        uf = pr.get('uf0', None)

        if pr_typ == 'realConsumers':
            uf = pr.get('uf0', None)
            if not uf is None:
                return uf
        else:
            uf = pr.get('uf0', None)
            if not uf is None:
                return uf
        '''

        ct = get_ct()
        Tn_otop = ct.get('t_or')
        heatSourceID = pr.get('heatSourceID', -1)
        v_ot = read_tg.get_tg(heatSourceID, Tn_otop)

        if not v_ot is None:
            t1, t2, t3, tv = v_ot

    #        const PC *pc = getPC(n)

    #        if pc:
    #            get_TG_ot(pc->kod_ist, t1, t2, t3, tv)
#            print(f'===({t1}-{t3})/({t3}-{t2}) =  {(t1 - t3) / (t3 - t2)}==')

            return (t1 - t3) / (t3 - t2)

        return 0

#    print(pr.get('uf', None))

    return pr.get('uf', 1)


EPS = 0.00001
EPS = 0.001

def otopl(node, pr, tr, W0, Tn, t1, is_leto, debug):
#, double& t2, double& tv, double& Q    

#    return t1, Tn,  0


#    print('t1', t1, W0, node.get('name'))
#    if t1 < 0:
#        return t1, Tn,  0

    if abs(t1) > 1000:
        return t1, Tn,  0


    if abs(W0) < 0.00001:
        return t1, Tn,  0
#    print(node, pr, tr, W0, Tn, t1, is_leto)

#    if W0 < 0:
#        print(W0)
#        exit(1)

    tt1  = time.time()

    kf = 1.

    t2 = t1
    tv = 18

    '''
    if (t1 < 30) {
        t2 = t1
        tv = 0
        Q = 0
    }
    '''
    pr_otopln = pr.get('otopln', 0)
    pr_otoplz = pr.get('otoplz', 0)

    if is_leto or (pr_otoplz == 0 and pr_otopln == 0) or W0 == 0:
        Q = 0
        return t1, 0, 0

    ct = get_ct()

    '''
    if config.args.is_veter:
        const PC* pc = getPC(node)
        if pc:
            get_TG(pc.get('kod_ist', 0), Tn, T1, T2, T3, TV)
            kf = (TV - T2) / (T1 - T2)
    '''

    otopl_tp = 0

    if not config.args.no_teplovyd: 
        otopl_tp = pr.get('otopl_tp', 0)


    if pr_otopln > 0:
#        t2, tv, tt01, tt02, tt03 = rasTT2(NULL, pr, tr, W0, kf * (pr_otopln+otopl_tp) * 1e6, Tn, t1)

#        print('~~~~~~~~~~', t1)
        t2, tv, tt01, tt02, tt03 = rasTT2(pr, tr, W0, kf * (pr_otopln+otopl_tp) * 1e6, Tn, t1, debug)

    elif pr_otoplz > 0:
        u = getUFpr(node, pr)

        if u > 0.:
            set_rasz_pr(pr, tr, ct.get('t_or', 0))

            qq, t2, t3, tv = potreb2(pr, t1, Tn, W0, kf * (pr_otoplz+otopl_tp) * 1e6, u, debug)

#            if debug:    
#                print(f'!!<<>> t1={t1} qq={qq}, t2={t2}, t3={t3}, tv={tv}')

        else:
            set_rasz_pr(pr, tr, ct.get('t_or', 0))
            qq, t2, tv = potreb1(pr, t1, Tn, W0, kf * (pr_otoplz+otopl_tp) * 1e6)

    Q = W0 * (t1 - t2) * 1e-6

#    if debug:
#        print(f'u={u} n={pr_otopln} z={pr_otoplz} t1={t1} -> t2={t2} tv={tv} Q={Q}')

    tt2  = time.time()

#    print(tt2-tt1)

    return t2, tv, Q


if __name__ == "__main__":

    config.init()
    
    is_leto = False 
    Tn = -32
    t1 = 150
    W0 = 12500    # Расход через потребитель

    node = {}

    tr = gid_init.get_tr0()
    pr = gid_init.get_pr0('gvsm', 0.2)

    aa = otopl(node, pr, tr, W0, Tn, t1, is_leto)

    print(aa)
