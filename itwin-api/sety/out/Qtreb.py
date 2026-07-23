from sety.consumption import get_tr
from sety.consumption import get_beta_pr
from sety.consumption import get_beta_sm

from sety import config
from sety.teplo.teplo2 import N_GWS
from sety.teplo.t import getS28

from sety.teplo.otopl import getUFpr


def write_Qtreb(pr, pt_out, Tn):
    #  double Qras_ot, Qras_ven, Qras_gvs_o, Qras_gvs_z
#    double Qras_ven, Qras_gvs_z
#    double Qras_ot_z, Qras_ot_n

    #  Qras_ot = (pr.get('otoplz', 0)+pr.get('otopln', 0))*(pr.get('Tr_tv_co', 0)-Tn)/(pr.get('Tr_tv_co', 0)-tr.get('Tn_r', 0))

#    if pr.get('name', '???') == 'эу3/38':
#        print('==================')
#        print(pr.get('name', '???'))
#        exit(1)


    tr = get_tr(pr)

#    'Tn_r': 'Tn_r',  # Расчетная температура наружного воздуха для отопления
#    'calcTempHR': 'Tr_tv_co',  # Расчетная температура в отапливаемых помещений
#    'calcTempVS': 'Tr_tv_cv',  # Расчетная температура нагретого воздуха после КУ


    Qras_ot_z = pr.get('otoplz', 0) * (pr.get('Tr_tv_co', 0) - Tn) / (pr.get('Tr_tv_co', 0) - tr.get('Tn_r', 0))
    Qras_ot_n = pr.get('otopln', 0) * (pr.get('Tr_tv_co', 0) - Tn) / (pr.get('Tr_tv_co', 0) - tr.get('Tn_r', 0))


    Qras_ven = pr.get('ventil', 0) * (pr.get('Tr_tv_cv', 0) - Tn) / (pr.get('Tr_tv_cv', 0) - tr.get('Tn_r_v', 0))

    #  switch (getGlobal()->n_GWS2) {
    #  case 0:  Qras_gvs_o = pr.get('gvoo', 0)+pr.get('gvop', 0) break
    #  case 1:  Qras_gvs_o = (pr.get('gvoo', 0)+pr.get('gvop', 0))*pr.get('gvs_max', 0) break
    #  case 2:  Qras_gvs_o = 0 break
    #  }

    koef = 1
    koef_rez = 0.85 # Манюк стр.205

    if config.args.GWS2 == 0:  
        koef = 1            
        koef_rez = 0.85
    elif config.args.GWS2 == 1:  
        koef = pr.get('gvs_max', 0)  
        koef_rez = 0    
    elif config.args.GWS2 == 2:  
        koef = 0            
        koef_rez = 1

#    koef = 1            
#    koef_rez = 0.85

    Qras_gvs_o = (pr.get('gvoo', 0) + pr.get('gvop', 0)) * koef

#    const S28* getS28()

    """
        if (avt) {
          beta = pt->gvs_max
        }
        else {
          beta = getS28()->pr
        }
        pt_G->G_gvpr = pt->gvpr*beta*1000/(t1_2r-dt-tn->t2pod_parl)
    """


    ngws = N_GWS(pr)

#    switch (N_GWS(pr)) {
        #  case 4:  Qras_gvs_z = (pr.get('gvpr', 0)+pr.get('gvsm', 0))*pr.get('gvs_max', 0)+pr.get('gvps', 0)*getS28()->ps+pr.get('gvpw', 0)*getS28()->pw break

            # Для неавтоматизированной ГВС
        #  case 4:  Qras_gvs_z = pr.get('gvpr', 0)*getS28()->pr+pr.get('gvsm', 0)*getS28()->sm+pr.get('gvps', 0)*getS28()->ps+pr.get('gvpw', 0)*getS28()->pw break
##    case 4:  Qras_gvs_z =           # рассчетная
    if ngws == 4:  
        Qras_gvs_z =  (         # рассчетная
        pr.get('gvpr', 0) * get_beta_pr(pr) +
        pr.get('gvsm', 0) * get_beta_sm(pr) +
        pr.get('gvps', 0) * getS28().ps +
        pr.get('gvpw', 0) * getS28().pw
        )

    elif ngws == 1:  
        Qras_gvs_z = pr.get('gvpr', 0) + pr.get('gvsm', 0) + pr.get('gvps', 0) + pr.get('gvpw', 0)
    elif ngws == 2:  
        Qras_gvs_z = (pr.get('gvpr', 0) + pr.get('gvsm', 0) + pr.get('gvps', 0) + pr.get('gvpw', 0)) * pr.get('gvs_max', 0) 
    elif ngws == 3:  
        Qras_gvs_z = pr.get('gvpr', 0) * getS28().pr + pr.get('gvsm', 0) * getS28().sm + pr.get('gvps', 0) * getS28().ps + pr.get('gvpw', 0) * getS28().pw
    elif ngws == 0:  
        Qras_gvs_z = 0 

    if not config.args.is_leto:
        pt_out['Qtreb'] = Qras_ot_z + Qras_ot_n + Qras_ven + Qras_gvs_o + Qras_gvs_z
        pt_out['Qotz_treb'] = Qras_ot_z
        pt_out['Qotn_treb'] = Qras_ot_n
        pt_out['Qvent_treb'] = Qras_ven


#    print('+++', pt_out['Qotn_treb'])

    pt_out['Qgvz_treb'] = Qras_gvs_z
    pt_out['Qgvop_treb'] = pr.get('gvop', 0) * koef
    pt_out['Qgvoo_treb'] = pr.get('gvoo', 0) * koef
    pt_out['Qrez_treb'] = (pr.get('gvop', 0) + pr.get('gvoo', 0)) * pr.get('rez', 0) / 100 * koef_rez

    Qras_gvs_z1 = (
        pr.get('gvpr', 0) * get_beta_pr(pr) +
        pr.get('gvsm', 0) * get_beta_sm(pr) +
        pr.get('gvps', 0) * getS28().ps +
        pr.get('gvpw', 0) * getS28().pw
        )

    pt_out['Qras_gv_z'] = Qras_gvs_z1
    pt_out['Gneob'] = get_gneob(pr, pr)

    pt_out = teploobesp(pr, pt_out)


    return pt_out


def write_Qtreb_po(pr, pt_out, Tn):

    debug = False
    if pr.get('name', '???') == '7АБ-1':
        debug = True

    tr = get_tr(pr)

    Qras_ven = 0
    Qras_gvs_z = 0

    otopl_zco = (pr.get('otopl_zco', 0)
        + (pr.get('otopl_pr', 0) if pr.get('cx_co_pr', 0) != 3 else 0) #  /*'Н'*/
        + (pr.get('otopl_ps', 0) if pr.get('cx_co_ps', 0) != 3 else 0) #  /*'Н'*/
        + (pr.get('otopl_pw', 0) if pr.get('cx_co_pw', 0) != 3 else 0) #  /*'Н'*/
        + (pr.get('otopl_sm', 0) if pr.get('cx_co_sm', 0) != 3 else 0) #  /*'Н'*/
        )

    otopl_nco = (pr.get('otopl_nco', 0)
        + (pr.get('otopl_pr', 0) if pr.get('cx_co_pr', 0) == 3 else 0)   #  /*'Н'*/
        + (pr.get('otopl_ps', 0) if pr.get('cx_co_ps', 0) == 3 else 0)   #  /*'Н'*/
        + (pr.get('otopl_pw', 0) if pr.get('cx_co_pw', 0) == 3 else 0)   #  /*'Н'*/
        + (pr.get('otopl_sm', 0) if pr.get('cx_co_sm', 0) == 3 else 0)   #  /*'Н'*/
        )


    #  Qras_ot = 
    Qras_ot_z = otopl_zco * (pr.get('Tr_tv_co_zco', 0) - Tn) / (pr.get('Tr_tv_co_zco', 0) - tr.get('Tn_r', 0))
    Qras_ot_n = otopl_nco * (pr.get('Tr_tv_co_nco', 0) - Tn) / (pr.get('Tr_tv_co_nco', 0) - tr.get('Tn_r', 0))

    Qras_ven = pr.get('ventil_cv', 0) * (pr.get('Tr_tv_cv', 0) - Tn) / (pr.get('Tr_tv_cv', 0) - tr.get('Tn_r_v', 0))

        



    koef = 1
    koef_rez = 0.85 # Манюк стр.205

    if config.args.GWS2 == 0:  
        koef = 1            
        koef_rez = 0.85
    elif config.args.GWS2 == 1:  
        koef = pr.get('gvs_max', 0)  
        koef_rez = 0    
    elif config.args.GWS2 == 2:  
        koef = 0            
        koef_rez = 1

    koef = 1            
    koef_rez = 0.85

    ngws = N_GWS(pr)

    Qras_gvs_o = (pr.get('gv_oo', 0) + pr.get('gv_op', 0)) * koef

#    switch (N_GWS(pr)) {
        #  case 4:  Qras_gvs_z = pr.get('gv_pr', 0)*pr.get('gvs_max_pr', 0)+pr.get('gv_sm', 0)*pr.get('gvs_max_sm', 0)+pr.get('gv_ps', 0)*getS28().ps+pr.get('gv_pw', 0)*getS28().pw break
            # Для неавтоматизированной ГВС
        #  case 4:  Qras_gvs_z = pr.get('gv_pr', 0)*getS28().pr+pr.get('gv_sm', 0)*getS28().sm+pr.get('gv_ps', 0)*getS28().ps+pr.get('gv_pw', 0)*getS28().pw break
    if ngws == 4:  # рассчетная
#    case 4:  
        Qras_gvs_z = (          
        pr.get('gv_pr', 0) * pr.get('gvs_max_pr', 0) +
        pr.get('gv_sm', 0) * pr.get('gvs_max_sm', 0) +
        pr.get('gv_ps', 0) * getS28().ps +
        pr.get('gv_pw', 0) * getS28().pw
        )

    elif ngws == 1:  # Средняя
        Qras_gvs_z = (          
            pr.get('gv_pr', 0) + pr.get('gv_sm', 0) + pr.get('gv_ps', 0) + pr.get('gv_pw', 0) 
        )

    elif ngws == 2:  # Максимальная
        Qras_gvs_z = (          
            pr.get('gv_pr', 0) * pr.get('gvs_max_pr', 0) +
            pr.get('gv_sm', 0) * pr.get('gvs_max_sm', 0) +
            pr.get('gv_ps', 0) * pr.get('gvs_max_ps', 0) +
            pr.get('gv_pw', 0) * pr.get('gvs_max_pw', 0)
        )

    elif ngws == 3:  # Балансовая
        Qras_gvs_z = (                 
            pr.get('gv_pr', 0) * getS28().pr +
            pr.get('gv_sm', 0) * getS28().sm +
            pr.get('gv_ps', 0) * getS28().ps +
            pr.get('gv_pw', 0) * getS28().pw
        )

    elif ngws == 0:  # Нулевая
        Qras_gvs_z = 0 
           



    #  return Qras_ot+Qras_ven+Qras_gvs_o+Qras_gvs_z

    if not config.args.is_leto:
        pt_out['Qtreb'] = Qras_ot_z + Qras_ot_n + Qras_ven + Qras_gvs_o + Qras_gvs_z
        pt_out['Qotz_treb'] = Qras_ot_z
        pt_out['Qotn_treb'] = Qras_ot_n
        pt_out['Qvent_treb'] = Qras_ven


    pt_out['Qgvz_treb'] = Qras_gvs_z
    pt_out['Qgvop_treb'] = pr.get('gv_op', 0) * koef
    pt_out['Qgvoo_treb'] = pr.get('gv_oo', 0) * koef
    pt_out['Qrez_treb'] = (pr.get('gv_op', 0) + pr.get('gv_oo', 0)) * pr.get('rez_op', 0) / 100 * koef_rez

    Qras_gvs_z1 = (
        pr.get('gv_pr', 0) * pr.get('gvs_max_pr', 0) +
        pr.get('gv_sm', 0) * pr.get('gvs_max_sm', 0) +
        pr.get('gv_ps', 0) * getS28().ps +
        pr.get('gv_pw', 0) * getS28().pw
    )

    pt_out['Qras_gv_z'] = Qras_gvs_z1

    pt_out = teploobesp(pr, pt_out)

    return pt_out


# Теплообеспеченность

def teploobesp(pr, pt_out):

    ''' Теплообеспеченность
        write_PT_OUT_Q_obesp_min(ado, pt_out.Qfact * 100 / pt_out.Qtreb)
        write_PT_OUT_Q_obesp_otopl_min(ado, (pt_out.Qotz + pt_out.Qotn + pt_out.dop12 + pt_out.dop13) / (pt_out.Qotz_treb + pt_out.Qotn_treb + pt_out.Qvent_treb) * 100)
        write_PT_OUT_Q_obesp_gvs_min(ado, (pt_out.dop18 + pt_out.dop19 + pt_out.dop20 + pt_out.dop17) / (pt_out.Qgvz_treb + pt_out.Qgvop_treb + pt_out.Qgvoo_treb + pt_out.Qrez_treb) * 100)
       '''

#    return pt_out
    
    Qtreb = pt_out.get('Qtreb', 0)
    
    if Qtreb == 0:
        return pt_out

    Qfact = pt_out.get('Qfact', 0)

    dop12 = pt_out.get('dop12', 0)   # Тепловая нагрузка потребителя на вентиляцию
    dop13 = pt_out.get('dop13', 0)   # Тепл.нагрузка на кондиционирование
    Qotz = pt_out.get('Qotz', 0)     # Тепл.нагрузка  на отопление, зав.сх.
    Qotn = pt_out.get('Qotn', 0)     # Тепл.нагрузка  на отопление, незав.сх.

#    print(pt_out)
#    exit(1)


    # требуемые готовы

    Qotz_treb = pt_out.get('Qotz_treb', 0) # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,зав.схема  
    Qotn_treb = pt_out.get('Qotn_treb', 0) # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,незав.схема
    Qvent_treb = pt_out.get('Qvent_treb', 0) #  Требуемый расход тепла на вентиляцию при текущей температуре наружного воздуха

    dop17 = pt_out.get('dop17', 0)   #  Тепл.нагрузка на ГВ в закрытой системе              
    dop18 = pt_out.get('dop18', 0)   #  Тепл.нагрузка на ГВ из под.теплопр. в откр.сист.    
    dop19 = pt_out.get('dop19', 0)   #  Тепл.нагрузка на ГВ из обр.теплопр. в откр.сист.    
    dop20 = pt_out.get('dop20', 0)   #  Тепл.нагрузка в цирк.теплопроводе ГВС               

    # требуемые готовы

    Qgvz_treb  = pt_out.get('Qgvz_treb', 0)  # Требуемый расход тепла  на горячее водоснабжение  в закрытой системе
    Qgvop_treb = pt_out.get('Qgvop_treb', 0)  # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из под.трубопр.
    Qgvoo_treb = pt_out.get('Qgvoo_treb', 0)  # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из обр.трубопр.
    Qrez_treb  = pt_out.get('Qrez_treb', 0)  # Требуемый расход тепла на рециркуляцию в  в открытой системе ГВ

#    print(f'{Qfact}  {Qtreb}')
#    Qfact = Qotopl + Qvent + Qkond + Qgvz + Qgvop + Qgvoo

#    if pr.get('name', '???') == '5.9':
#        print('!!', Qfact)
#        exit(1)



    if Qtreb != 0:
        pt_out['Q_obesp_min'] = Qfact * 100 / Qtreb
    if Qotz_treb + Qotn_treb + Qvent_treb != 0:
        pt_out['Q_obesp_otopl_min'] = (Qotz + Qotn + dop12 + dop13 ) / (Qotz_treb + Qotn_treb + Qvent_treb) * 100
    if Qgvz_treb + Qgvop_treb + Qgvoo_treb + Qrez_treb != 0:
        pt_out['Q_obesp_gvs_min'] = (dop18 + dop19 + dop20 + dop17) / (Qgvz_treb + Qgvop_treb + Qgvoo_treb + Qrez_treb) * 100

#    Q_obesp_min = nP.get('Qfact', 0) * 100 / nP.get('Qtreb', 0)
#    Q_obesp_otopl_min = (nP.get('Qotz', 0) + nP.get('Qotn', 0) + nP.get('dop12', 0) + nP.get('dop13', 0)) / (nP.get('Qotz_treb', 0) + nP.get('Qotn_treb', 0) + nP.get('Qvent_treb', 0)) * 100
#    Q_obesp_gvs_min = (nP.get('dop18', 0) + nP.get('dop19', 0) + nP.get('dop20', 0) + nP.get('dop17', 0)) / (nP.get('Qgvz_treb', 0) + nP.get('Qgvop_treb', 0) + nP.get('Qgvoo_treb', 0) + nP.get('Qrez_treb', 0)) * 100



    return pt_out


def get_gneob(n, pr):
    gneob = 10

    uf = getUFpr(n, pr)

#    if pr.get('name', '???') == 'эу10/3':
#        print('==================')
#        print(uf)
#        print(pr)
#        print('==================')



    if pr.get('otoplz', 0) != 0 and uf != 0:
        gneob = 1.4 * pr.get('a7', 0) * pow(1 + uf, 2)
        if pr.get('gvpr', 0) != 0 or pr.get('gvoo', 0) != 0 or pr.get('gvop', 0) != 0:
            gneob = 1.4 * pr.get('a7', 0) * pow(1 + uf, 2)
        elif pr.get('gvsm', 0) != 0:
            gneob = 1.4 * pr.get('a7', 0) * pow(1 + uf, 2) + pr.get('a22', 0)
        elif pr.get('gvps', 0) != 0 or pr.get('gvpw', 0) != 0:
            gneob = 1.4 * pr.get('a7', 0) * pow(1 + uf, 2) + pr.get('a22', 0) + pr.get('a23', 0)

    if pr.get('otoplz', 0) != 0 and uf == 0:
        gneob = 6
        if pr.get('gvpr', 0) != 0 or pr.get('gvoo', 0) != 0 or pr.get('gvop', 0) != 0:
            gneob = 6
        elif pr.get('gvsm', 0) != 0:
            gneob = 6 + pr.get('a22', 0)
        elif pr.get('gvps', 0) != 0 or pr.get('gvpw', 0) != 0:
            gneob = 6 + pr.get('a22', 0) + pr.get('a23', 0)

    if pr.get('otopln', 0) != 0:
        gneob = 10
        if pr.get('gvpr', 0) != 0 or pr.get('gvoo', 0) != 0 or pr.get('gvop', 0) != 0:
            gneob = 10
        elif pr.get('gvsm', 0) != 0:
            gneob = 10 + pr.get('a22', 0)
        elif pr.get('gvps', 0) != 0 or pr.get('gvpw', 0) != 0:
            gneob = 10 + pr.get('a22', 0) + pr.get('a23', 0)

    return gneob



