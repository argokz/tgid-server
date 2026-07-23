from sety.teplo.tepl_co1 import rasTT2
from sety.teplo.teplo2 import getW
from sety.teplo.f import getEp


# Расчет теплообменников


def rasTO(nIin, pr, typ, tr, G, GG0, QQ, t, Tn, debug):
#    double tv, tx, tg
#    double& t2, double& qq, double* x, double* temp, 

#    double t01, t02, t03

#    tr = read_gid.map_tr.get(tr, None)
    t2 = t

    pt_G = pr
    node = pr

    if abs(G) < 0.00001:
        return t

    QQ *= 1e6
    G *= 1000

    if typ == 12: # Отопление
#        print('~~~~~~~~~~', t, pr.get('name'))
        t2, tv, tt01, tt02, tt03 = rasTT2(pr, tr, G, QQ, Tn, t, debug)

        return t2

    elif typ == 11 or typ == 10:  #        ГВС
        tx = tr.get('Tx', 0)

#        if N_GWS(pr) == 0:
        if False:
            tg = tx  # Горячая водопроводная
            t2 = t  # На входе системы отопления
        else:
            Wv = getW(pr, pt_G, tr, debug)

            if typ == 11 and pr.get('gvpr', 0) == 0:  # II ступень верхняя параллельно отоплению

                if nIin and pr.get('gvpw', 0) == 0:
                    tt = nIin.get('t', 0)
                    
                    G2 = GG0*1000

                    '''
                    for (CLINE* l = nIin->lines; l; l = next(l)):
                        if (IsBegin(l)):
                            G2 += fabs(x[bline(l)->n]) * 1000
                            '''

                    #                        wout << " tt = " << tt << endl
                    E1 = getEp(node, 1, pr, pt_G, tr, G2)
                    Wm = min(G2, Wv)
                    Qp = E1 * Wm * (tt - tr.get('Tx', 0))
                    tx = tr.get('Tx', 0) + Qp / Wv  # Горячая водопроводная

            if tx > pr.get('Tr_gvs', 0) and pr.get('pr_avtomat', 0) == 2: # /*'А'*/) {
                tg = tx  # Горячая водопроводная
                t2 = t  # На входе системы отопления
            else:
                Ep = getEp(node, 2 if typ == 11 else 1, pr, pt_G, tr, G)
                Wm = min(G, Wv)
                Qp = Ep * Wm * (t - tx)

                tg = tx + Qp / Wv  # Горячая водопроводная
                t2 = t - Qp / G  # На входе системы отопления

#                print(f'Ep={Ep} tg={tg} t2={t2} tx={tx}')


    return t2

