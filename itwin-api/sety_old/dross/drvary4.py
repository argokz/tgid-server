import math

from sety.dross.drsh3 import drsh3

from sety.dross.w_print import w_print

H_DOPUST  = 3.0  # /* допустимый остаток располагаемого напора */
H_DOPUST1 = 2.0  # /* мин.допустимый гасимый напор на головной диаф.*/

def drvary4(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name):

#    double   hrc, ggv, hoost, hogrost, hgvost, hvost, h_3mm
#    int     n_3mm, ferr = 0

    hoost = hvost = hgvost = ggv = hogrost = 0.
    ggv = otopl + vn + gvpr + gvsm + gvps + gvpw + gvoo

    if ggv > 0.:
        w_print(f"\n Для потребителя {ptr_name} (признак ступени 4) возможны только тепловые")
        w_print(f"\n нагрузки: ГВС из подающ. трубопровода и на компенсацию тепл. потерь в")
        w_print(f"\n циркуляционном трубопроводе. Расчет дроссельн. диафрагм не производится")
    else:
        ggv = (gvop + rez) / 2.
        hrc = pih - drs['a10'] - drs['a11'] - drs['a7']
        if hrc > 0.:
            h_3mm = hrc
            n_3mm = 1
            ferr, hrc, dr_out['b33'] = drsh3(ggv, drs['a15'], drs['a16'], hrc)

            if ferr:
                n_3mm = int(h_3mm / hrc)
                if n_3mm > 3:
                    n_3mm = 3
                w_print(f"\n В потребителе {ptr_name} на входе подающ. ГВС")
                w_print(f"\n необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                w_print(f"\n\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc} м.")
            dr_out['b34'] = hrc * n_3mm
            dr_out['b35'] = ggv
        else:
            w_print(f"\n Для потребителя {ptr_name} не обеспечено заданное значение напора")
            w_print(f"\n на входе водоразборных приборов.")
            w_print(f"\n\t Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')

    return ferr
