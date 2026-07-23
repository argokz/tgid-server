import math

from sety.dross.drsh3 import drsh3

from sety.dross.w_print import w_print

H_DOPUST  = 3.0  # /* допустимый остаток располагаемого напора */
H_DOPUST1 = 2.0  # /* мин.допустимый гасимый напор на головной диаф.*/

#short drvary5(DRS* drs, DR_OUT* dr_out, double rasp, double pih, double pihO, double otopl, double otn_fs, double vn,
#    double gvpr, double gvsm, double gvps, double gvpw, double gvop, double gvoo, double rez, short* fss,
#    double ho, double hv, double hgv, UZEL ptr)
#{

def drvary5(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name):


#    double   hrc, ggv, hoost, hogrost, hgvost, hvost, h_3mm
#    int     n_3mm, ferr = 0

    hoost = hvost = hgvost = ggv = hogrost = 0.

    ggv = otopl + vn + gvpr + gvsm + gvps + gvpw + gvoo
    if ggv > 0:
        w_print(f"\n Для потребителя {ptr_name} (признак ступени 5) возможны только тепловые")
        w_print(f"\n нагрузки: ГВС из подающ. трубопровода и на компенсацию тепл. потерь в")
        w_print(f"\n циркуляционном трубопроводе. Расчет дроссельн. диафрагм не производится")
    else:
        hrc = pih - pihO - drs['a10'] - drs['a11'] - drs['a7']
        hrc = pih - pihO - drs['a10'] - drs['a11']
        if hrc > 0.:
            h_3mm = hrc
            n_3mm = 1

            ferr, hrc, dr_out['b39'] = drsh3(rez, drs['a15'], drs['a16'], hrc)
            if ferr:
                n_3mm = int(h_3mm / hrc)
                if n_3mm > 3:
                    n_3mm = 3
                w_print(f"\n В потребителе {ptr_name} на обратном трубопроводе ГВС")
                w_print(f"\n необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                w_print(f"\n\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc} м.")
            dr_out['b40'] = hrc * n_3mm
            dr_out['b41'] = rez
            if pihO + dr_out['b40'] > 80.:
                w_print(f"\n Напор в обратном трубопр. потребителя {ptr_name} после установки на")
                w_print(f"\n циркуляц. трубопроводе подпорно-ограничит. диафрагмы будет превышать")
                w_print(f"\n предельно-допутимый напор по условию механической прочности полотенцесушителей")
        else:
            w_print(f"\n Для потребителя {ptr_name} не обеспечено заданное значение напора")
            w_print(f"\n на выходе водоразборных приборов.")
            w_print(f"\n\t Расчет подпорно-ограничительной диафрагмы на обратном трубопроводе ГВС не выполняется.", color='red')

    return ferr
