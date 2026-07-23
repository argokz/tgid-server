import math

'''
if not __package__:
    import os
    import sys
    parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
    sys.path.append(os.path.abspath(os.path.join(parent_dir, '..', '..')))
    print(os.path.abspath(os.path.join(parent_dir, '..', '..', '..')))
    from sety.gid_init import get_ct
'''

from sety import read_gid

from sety import config
from sety.teplo import gid_init

from sety.teplo.m import srlog
from sety.teplo import otopl
from sety.teplo import tepl_vent

from sety.ct import get_ct

def fatal_error_teplo():
    pass


from sety.teplo.teplo2 import N_GWS
from sety.teplo.teplo2 import getW
from sety.teplo.teplo2 import rasTO2


#const PC* getPC(const CNode* n)
#const CT* getCT()

#void potreb(double t1, double* t2, double* tv)

#int rasVENT(const PR* pr, double G, double _q, double t, double* t2, double* tv, double Tn)
#double getW(const PR* pr, const PT_G* pt_G, const TR* tr)
#double getEp(CNode* node, int stupen, const PR* pr, const PT_G* pt_G, const TR* tr, double G)

#int N_GWS(const PR* pr)
#int N_GWS(const PO* po)

#void otopl(CNode* node, const PR* pr, const TR* tr, double W0, double Tn, double t1, double& t2, double& tv, double& Q, int is_leto)



#-----------------------------------------------------------------------------------

def rasTO_pr(node, pr, tr, pt_G, G, t, Tn, obob, debug):

#, double& t2, double& qq, double& tg, double& tv, double& tvv, double& Qotopl, double& Qvent, double& Qkond, double& Qgvz, double& Qgvop, double& Qgvoo


    g = t2v = ggv = got = gvent = gkond = t2_1 = t2_2 = GG = 0

    Qotopl = Qvent = Qgvz = Qgvop = Qgvoo = Qkond = 0.

    tvv = tv = tg = 0

    if t < 0:
#        print('------------ Ошибка t=', t)
        t = t2 = qq = 0
        return

    t2 = t

    if abs(G) < 0.00001:
#        print('G < 0.00001 ошибка')
#        print('!2')
        return


    pr_ventil = pr.get('ventil', 0)
    pr_kondiz = pr.get('kondiz', 0)

    pr_gvsm = pr.get('gvsm', 0)
    pr_gvps = pr.get('gvps', 0)
    pr_gvpw = pr.get('gvpw', 0)
    pr_gvpr = pr.get('gvpr', 0)

    G_gvoo = pt_G.get('G_gvoo', 0)
    G_gvop = pt_G.get('G_gvop', 0)
    G_gvpr = pt_G.get('G_gvpr', 0)
    G_gvps = pt_G.get('G_gvps', 0)
    G_gvpw = pt_G.get('G_gvpw', 0)
    G_gvsm = pt_G.get('G_gvsm', 0)
    G_kondiz = pt_G.get('G_kondiz', 0)
    G_otopln = pt_G.get('G_otopln', 0)
    G_otoplz = pt_G.get('G_otoplz', 0)
    G_rez = pt_G.get('G_rez', 0)
    G_ventil = pt_G.get('G_ventil', 0)


    '''

    print(f'G_gvoo = {G_gvoo}')
    print(f'G_gvop = {G_gvop}')
    print(f'G_gvpr = {G_gvpr}')
    print(f'G_gvps = {G_gvps}')
    print(f'G_gvpw = {G_gvpw}')
    print(f'G_gvsm = {G_gvsm}')
    print(f'G_kondiz = {G_kondiz}')
    print(f'G_otopln = {G_otopln}')
    print(f'G_otoplz = {G_otoplz}')
    print(f'G_rez = {G_rez}')
    print(f'G_ventil = {G_ventil}')

    '''

    G_otopl = (G_otoplz + G_otopln)

    if G_otopln < 0:
        print('G_otopln', G_otopln)
        print(pr, pt_G)
        exit(0)

        
#    if debug:
#        print(pr_gvpr, pr_gvps, pr_gvsm, pr_gvpw, pr_ventil)


#    const TR* tr = getTR(pr.get('kodtr', 0))
#    if !tr:
#        wout << "Не заданы расчетные температуры для " << node.get('getNameObBr', 0)() << endl
#        fatal_error_teplo()
#        return


    if pr_gvpr == 0 and pr_gvps == 0 and pr_gvsm == 0 and pr_gvpw == 0:
        g = 1000 * (G_otoplz + G_otopln)
        if g: 
            t2, tv, Qotopl = otopl.otopl(node, pr, tr, g, Tn, t, config.args.is_leto, debug)





#        print(f'G = {G} t = {t} t2 = {t2} tv = {tv} Qotopl = {Qotopl}')

        GG = g

    elif pr_gvpr != 0:
        
        t2_1, tg = rasTO2(node, 11, pr, pt_G, tr, 1000 * (G_gvpr), t, tr.get('Tx', 0), debug)

        if config.args.is_leto or abs(G_otopl) < 0.00001:
            t2 = t2_1

        else:
            t2_2, tv, Qotopl = otopl.otopl(node, pr, tr, 1000 * (G_otoplz + G_otopln), Tn, t, config.args.is_leto, debug)

            t2 = (t2_1 * G_gvpr + t2_2 * (G_otoplz + G_otopln)) / (G_gvpr + G_otoplz + G_otopln)

        g = 1000 * (G_gvpr + G_otoplz + G_otopln)
        #    Qgvz = (t-t2)*G_gvpr/1000
        Qgvz = (t - t2_1) * G_gvpr / 1000
        GG = g

        if config.args.is_leto:
            GG = 1000 * (G_gvpr)

    elif pr_gvps != 0:
        tx2 = tr.get('Tx', 0)
        tx = 0

        for i in range(100):
            g = 1000 * (G_gvps + G_otoplz + G_otopln)
            gvent = 1000 * (G_ventil + G_kondiz)

            if config.args.is_leto:
                gvent = 0
                gkond = 0
                g = G

            tx0 = tx

            t2, tx = rasTO2(node, 11, pr, pt_G, tr, g, t, tx2, debug)

#            print('============== g=', g, 't2=', t2, 'tx', tx, 'G_otopl', G_otopl)

            tg = tx
            t2_1 = t2

            if config.args.is_leto or abs(G_otopl) < 0.00001:
                t2 = t
                Qotopl = 0
            else:
                t2, tv, Qotopl = otopl.otopl(node, pr, tr, g, Tn, t2, config.args.is_leto, debug)

            if gvent:
                t2v, tvv = tepl_vent.rasVENT(pr, gvent, (pr_ventil + pr_kondiz) * 1e6, t, Tn, debug)

                t2 = (t2 * g + t2v * gvent) / (g + gvent)
                Qvent = gvent * (t - t2v) / 1e6

            t2_2, tx2 = rasTO2(node, 10, pr, pt_G, tr, g + gvent, t2, tr.get('Tx', 0), debug)

#            print('2============= g + gvent=', g + gvent, 't2_2=', t2_2, 'tx2', tx2)

            #      Qgvz = (t-t2_1+t2-t2_2)*g*1e-6
            Qgvz = (t - t2_1) * g * 1e-6 + (t2 - t2_2) * (g + gvent) * 1e-6

            t2 = t2_2

            if abs(tx - tx0) < 0.1 and i > 10: break

        g = 1000 * (G_gvps)
        GG = g + 1000 * (G_otopln + G_otoplz)
        GG += gvent

        if config.args.is_leto:
            GG = g

    elif pr_gvpw != 0:
        tx2 = tr.get('Tx', 0)
        tx = 0

#        if debug:
#            print(f'{G_gvpw + G_otoplz + G_otopln} {G_gvpw} + {G_otoplz} + {G_otopln}')

        for i in range(100):
            g = 1000 * (G_gvpw + G_otoplz + G_otopln)

            if config.args.is_leto or abs(G_otopl) < 0.00001:
                g = G
                gvent = gkond = 0

            tx0 = tx

            t2, tx = rasTO2(node, 11, pr, pt_G, tr, g, t, tx2, debug)


#            if debug:
#                print(f't={t} g={g} t2={t2} tx={tx}')

            tg = tx
            Qgvz = (t - t2) * g * 1e-6

            if config.args.is_leto:
                t2 = t2
                Qotopl = 0
            else:
                t2, tv, Qotopl = otopl.otopl(node, pr, tr, g, Tn, t2, config.args.is_leto, debug)
#                if debug:
#                    print(f't2={t2} tv={tv} Qotopl={Qotopl} g={g}, Tn={Tn}')

            tx2 = tr.get('Tx', 0)

            if abs(tx - tx0) < 0.1: break

#        if debug:
#            print(t2, tv, Qotopl)

        #    g = 1000*(G_gvpw)
        GG = g

#        if debug:
#            print(f'GG={GG}')

        if config.args.is_leto:
            GG = 1000 * (G_gvpw)

    elif pr_gvsm != 0:
        tx2 = tr.get('Tx', 0)
        tx = tx0 = 0

        ggv = 1000 * (G_gvsm)
        got = 1000 * (G_otoplz + G_otopln)
        gvent = 1000 * (G_ventil + G_kondiz)

        if config.args.is_leto or abs(G_otopl) < 0.00001:
            got = G - ggv
            gvent = 0
            gkond = 0

        g = ggv + got + gvent
        #    if (config.args.is_leto) g = ggv

        for i in range(100):
            tx0 = tx
            t2_1, tx = rasTO2(node, 11, pr, pt_G, tr, ggv, t, tx2, debug)      # II ступень верхняя
            tg = tx  # горячая на ГВС

            if config.args.is_leto:
                t2_2 = t
                Qotopl = 0
            else:
                t2_2, tv, Qotopl = otopl.otopl(node, pr, tr, got, Tn, t, config.args.is_leto, debug)

            if gvent:
                t2v, tvv = tepl_vent.rasVENT(pr, gvent, (pr_ventil + pr_kondiz) * 1.e6, t, Tn, debug)
                Qvent = gvent * (t - t2v) / 1e6

            if ggv + got + gvent:
                t2 = (t2_1 * ggv + t2_2 * got + t2v * gvent) / (ggv + got + gvent)
            else:
                t2 = t

            #      if (config.args.is_leto) t2 = t2_1

            t2_2, tx2 = rasTO2(node, 10, pr, pt_G, tr, g, t2, tr.get('Tx', 0), debug)  # I ступень нижняя

      #      Qgvz = (t-t2_1)*ggv*1e-6+(t2-t2_2)*g*1e-6
      #      Qgvz = (t-t2_2)*ggv*1e-6
            Qgvz = (t - t2_1) * ggv * 1e-6 + (t2 - t2_2) * g * 1e-6

            t2 = t2_2

            if abs(tx - tx0) < 0.0001: break

        GG = g
        if config.args.is_leto:
            GG = 1000 * (G_gvsm)

    if not config.args.is_leto:
        if pr_ventil + pr_kondiz != 0 and pr_gvsm == 0 and pr_gvps == 0:
            gvent = 1000 * (G_ventil + G_kondiz)

            t2v, tvv  = tepl_vent.rasVENT(pr, (G_ventil + G_kondiz) * 1000, (pr_ventil + pr_kondiz) * 1e6, t, Tn, debug)

            t2 = (t2 * g + t2v * gvent) / (g + gvent)
            Qvent = gvent * (t - t2v) / 1e6
            GG += gvent

    if G_gvop and G_rez:
        grez = G_rez * 1000
        Qrez = grez * t
        t2 = (t2 * (g + gvent) + Qrez) / (g + gvent + grez)
#        t2 = (t2 * (g + gvent) + grez* pr.get('T_pot_rez', 0)) / (g + gvent + grez)
#        t2 = pr.get('T_pot_rez', 0)

        GG += grez

    #  if ((G_gvop or G_gvoo) and G_rez) {
    #    GG += G_rez*1000
    #  }

    if G != 0 and not obob:
        qq = (t - t2) * G
    else:
        qq = (t - t2) * GG


    if abs(G - GG) > 0.00001:
        GG = GG

    ct = get_ct()
    ct5 = ct.get('tx', 5)
    # Тут проверить !!!!!!!!!!!!!!!!
#    ct5 = 0


    Qgvop = G_gvop * (t-ct5) / 1000;
    Qgvoo = G_gvoo * (t2-ct5) / 1000;




#    print(f'!!!!!!!!!! {Qgvop} = {G_gvop} * ({t}-{ct5}) / 1000')
#    print(f'!!!!!!!!!! {Qgvoo} = {G_gvoo} * ({t2}-{ct5}) / 1000')


#    if debug:
#        print(f'>>> t={t} t2={t2} tg={tg} qq={qq}')



    return t2, tg, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo

#-----------------------------------------------------------------------------------

def rasTO10(node, pr, pt_G, G, t, Tn, debug):
    pass



#-----------------------------------------------------------------------------------

def rasTO_pr2(node, pr, pt_G, G, t, Tn, debug):

    
#, double& t2, double& qq
#             rasTO_pr(node, pr, tr, pt_G, G, t, Tn, obob):
    
    tr = node.get('kodtr', None)
#    print(f't={t} tr = {tr}')

    tr = read_gid.map_tr.get(tr, None)

    v = rasTO_pr(node, pr, tr, pt_G, G, t, Tn, False, debug)

    if v is None: 
        return t, 0, None, None, None, 0, 0, 0, 0, 0, 0

    t2, tg, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = v

#    if debug:
#        print(G, t, Tn)
#        print(t2, tg, qq)

#    if debug:
#        print('t = ', t, 't2 = ', t2, 'qq=', qq)

#    if pr.get('name', '???') == '5.9':
#        print('!!', Qotopl)
#        exit(0)

    return t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo




#-----------------------------------------------------------------------------------

if __name__ == '__main__':

    config.init()

    pt_G = {}
    node = {}

    tr = gid_init.get_tr0()
    pr = gid_init.get_pr0()


    pt_G['G_otopln'] = pr['otopln'] * 1000/(150-80)
    pt_G['G_otoplz'] = pr['otoplz'] * 1000/(150-70)

    ur = gid_init.get_ur0()

    pt_G['G_gvpr'] = pr['gvpr'] * ur.get('gvpr', 0)
    pt_G['G_gvps'] = pr['gvps'] * ur.get('gvps', 0)
    pt_G['G_gvpw'] = pr['gvpw'] * ur.get('gvpw', 0)
    pt_G['G_gvsm'] = pr['gvsm'] * ur.get('gvsm', 0)
    pt_G['G_gvop'] = pr['gvop'] * ur.get('gvop', 0)
    pt_G['G_gvoo'] = pr['gvoo'] * ur.get('gvoo', 0)

    G = 12500
    Q = 1e6
    t = 150
    Tn = -32

    obob = False

    a = rasTO_pr(node, pr, tr, pt_G, G, t, Tn, obob)

#    a = rasTO_pr2(node, pr, pt_G, G, t, Tn)

