import math

from sety.dross.drsh2 import drsh2
from sety.dross.drsh3 import drsh3

from sety.dross.w_print import w_print

H_DOPUST  = 3.0  # /* допустимый остаток располагаемого напора */
H_DOPUST1 = 2.0  # /* мин.допустимый гасимый напор на головной диаф.*/




def drvary3(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name):


#    double   hrc, ggv, hoost, hogrost, hgvost, hvost, h_3mm
#    int     n_3mm, ferr = 0, t_g

    hoost = hvost = hgvost = ggv = hogrost = 0.
    ggv = gvpr + gvsm + gvop + gvps + gvpw
    if fss[7]: # /* если есть откр. ГВ из обратки */
        if rez > 0.:
            if fss[0] != 0:
                hrc = drs['a10'] * rez * rez / gvoo / gvoo + drs['a11']
                ferr, hrc, dr_out['b36'] = drsh3(otopl, drs['a15'], drs['a16'], hrc)
                dr_out['b37'] = hrc
                dr_out['b38'] = otopl
            else:
                w_print(f" Для потребителя {ptr_name} не может быть рассчитана ")
                w_print(f" подпорно циркул. диафрагма в сети ГВС, т.к. не задана нагрузка на отопление")
        hrc = pihO + dr_out['b34'] - drs['a12'] - drs['a10']
        if hrc > 0.:
            h_3mm = hrc
            n_3mm = 1
            ferr, hrc, dr_out['b33'] =  drsh3(gvoo, drs['a15'], drs['a16'], hrc)

            if ferr:
                n_3mm = int(h_3mm / hrc)
                if n_3mm > 3:
                    n_3mm = 3
                w_print(f" В потребителе {ptr_name} на входе подающ. ГВС")
                w_print(f" необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")
            dr_out['b34'] = hrc * n_3mm
            dr_out['b35'] = gvoo
        else:
            w_print(f" Для потребителя {ptr_name} не обеспечено заданное значение напора")
            w_print(f" на входе водоразборных приборов.")
            w_print(f"\t Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')

    if fss[0] == 0:
        pass
#    switch (fss[0])
#    {
#    case  0: break
#    /* Э */  case  1:
    if fss[0] == 1:
        if (otopl + vn + ggv) > 0.:
            hrc = rasp - 1.4 * drs['a7'] * (1 + drs['a6']) * (1 + drs['a6']) - dr_out['b34']

            if hrc >= H_DOPUST1:
                h_3mm = hrc
                n_3mm = 1
                ferr, hrc, dr_out['b12'] = drsh3(otopl + vn + ggv, drs['a15'], drs['a16'], hrc)

                if ferr:
                    n_3mm = int(h_3mm / hrc)
                    if n_3mm > 3:
                        n_3mm = 3
                    w_print(f" На входе теплового пункта потребителя {ptr_name} необходимо ")
                    w_print(f" установить последовательно {n_3mm} головных диафрагм диаметром {drs['a15']} мм.")
                    w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")
                    dr_out['b12'] = drs['a15']
                dr_out['b13'] = hrc * n_3mm
                dr_out['b14'] = otopl + vn + ggv
            else:
                w_print(f" На входе теплового пункта потребителя {ptr_name} установка ")
                w_print(f" головной диафрагмы нецелесообразна из-за недостаточности")
                w_print(f" располагаемого напора ТП равного {hrc:.1f} м.")
                w_print(f" Расчет дроссельных органов выполняется одноступенчатым способом")

                return drvary1(drs, dr_out, rasp, pihP, pihO, otopl, otn_fs, vn,
                    gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
                    ho, hv, hgv, ptr_name, 1)


            hrc = 1.4 * drs['a7'] * (1 + drs['a6']) * (1 + drs['a6']) - hgv
            if hrc >= 0:
                t_g = drs['a17']  #/*&255*/
                if t_g == 1:    #/*'О'*/:
                    otopl = otopl + gvps + gvpw

                ferr, hrc, dr_out['b7'], dr_out['b11'] = drsh2(otopl, drs['a14'], drs['a6'], drs['a7'], hrc, ptr_name)

                dr_out['b8'] = hrc
                dr_out['b9'] = otopl
                hoost = rasp - dr_out['b13'] - hrc
            else:
                w_print(f" Гасимый напор на сопле элеватора потребителя {ptr_name} меньше нуля. ")
                w_print(f" Это возможно при заниженном значении установленного коэффициента")
                w_print(f" смешения элеватора или заниженных потерях напора в отопительной")
                w_print(f" системе или завышенных потерях напора в сети ГВС.")
                w_print(f" Расчет сопла элеватора не производится.")

    if fss[0] == 3 or fss[0] == 2:
#    /*   */  case  3:
#    /* Н */  case  2:
        w_print(f" Признак ступени 3 не используется при независимом и безэлеваторном")
        w_print(f" присоединении систем отопления. Потребитель {ptr_name}")
 
    if fss[1]: # /* если есть вентиляция */
        hrc = rasp - dr_out['b13']
        ferr, hrc, dr_out['b27'] = drsh3(vn, drs['a15'], drs['a16'], hrc)
        dr_out['b28'] = hrc
        dr_out['b29'] = vn

    if fss[6]: # /* если есть открытое ГВ из подачи */

        hrc = pihP - drs['a12'] - drs['a10'] - dr_out['b13']
        if hrc > 0.:
            h_3mm = hrc
            n_3mm = 1

            ferr, hrc, dr_out['b33'] = drsh3(gvop, drs['a15'], drs['a16'], hrc)

            if ferr:
                n_3mm = int(h_3mm / hrc)
                if n_3mm > 3:
                    n_3mm = 3
                w_print(f" В потребителе {ptr_name} на входе подающего трубопровода")
                w_print(f" ГВС необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")
            dr_out['b34'] = hrc * n_3mm
            dr_out['b35'] = gvop
        else:
            w_print(f" Для потребителя {ptr_name} не обеспечено заданное значение напора")
            w_print(f" на входе водоразборных приборов.")
            w_print(f"\t Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')
        if rez > 0.:
            if dr_out['b12'] > 0:
                hrc = 1.e4 * (rez + vn + otopl) / dr_out['b12'] / dr_out['b12'] / dr_out['b12'] / dr_out['b12']
            else:
                hrc = 0.

            hrc = (rasp - hrc - dr_out['b34'] / dr_out['b35'] / dr_out['b35'] * rez * rez -
                (drs['a10'] * rez * rez / gvop / gvop + drs['a11']))
            if hrc > 0.:
                h_3mm = hrc
                n_3mm = 1

                ferr, hrc, dr_out['b39'] = drsh3(rez, drs['a15'], drs['a16'], hrc)
                if ferr:
                    n_3mm = int(h_3mm / hrc)
                    if n_3mm > 3:
                        n_3mm = 3
                    w_print(f" В потребителе {ptr_name} в циркул. сети ГВС")
                    w_print(f" необходимо установить {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                    w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")
                dr_out['b40'] = hrc * n_3mm
                dr_out['b41'] = rez
            else:
                w_print(f" Для потребителя {ptr_name} ограничение расхода")
                w_print(f" в циркуляционном режиме обеспечивается диафрагмой на входе в подающий ")
                w_print(f" трубопровод ГВС и / или головной диафрагмой")

    if fss[3]:
        hrc = 1.4 * drs['a7'] * (1 + drs['a6']) * (1 + drs['a6']) - hgv
        h_3mm = hrc
        n_3mm = 1

        ferr, hrc, dr_out['b30'] = drsh3(gvpr, drs['a15'], drs['a16'], hrc)
        if ferr:

            n_3mm = int(h_3mm / hrc)
            if n_3mm > 3:
                n_3mm = 3
            w_print(f" В потребителе {ptr_name} на входе пар. включ.подогр. ГВС ")
            w_print(f" необходимо установить последовательно {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
            w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")

        dr_out['b31'] = hrc * n_3mm
        dr_out['b32'] = gvpr

    if fss[4]:

        hrc = 1.4 * drs['a7'] * (1 + drs['a6']) * (1 + drs['a6']) - hgv
        h_3mm = hrc
        n_3mm = 1

        ferr, hrc, dr_out['b30'] = drsh3(gvsm, drs['a15'], drs['a16'], hrc)

        if ferr:

            n_3mm = int(h_3mm / hrc)
            if n_3mm > 3:
                n_3mm = 3
            w_print(f" В потребителе {ptr_name} на входе второй ступени")
            w_print(f" подогревателя ГВС необходимо установить последовательно ")
            w_print(f" {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
            w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")

        dr_out['b31'] = hrc * n_3mm
        dr_out['b32'] = gvsm

    return ferr
