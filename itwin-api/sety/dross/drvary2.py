import math

from sety.dross.drsh2 import drsh2
from sety.dross.drsh3 import drsh3

from sety.dross.w_print import w_print

from sety.dross.drvary1 import drvary1


#short drvary2(DRS* drs, DR_OUT* dr_out, double rasp, double pih, double pihO, double otopl, double otn_fs, double vn,
#    double gvpr, double gvsm, double gvps, double gvpw, double gvop, double gvoo, double rez, short* fss,
#    double ho, double hv, double hgv, UZEL ptr)

H_DOPUST = 3.0   # """ допустимый остаток располагаемого напора """

def drvary2(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name):

    pih = pihP

    hoost = 0
    hvost = 0
    hgvost = 0
    ggv = 0
    hogrost = 0
    ferr = 0.

#    print('*', ptr_name, ho)


    if fss[1]:   #  /*  вентиляция        */
        if rasp >= 2 * hv:
            hvost = rasp - 2 * hv
        else:
            if rasp >= hv:
                hvost = rasp - hv
            else:
                hvost = 0.
                ferr = 1
    else:
        hvost = 0.

    if fss[6]:   #  /*  г.в. открыт. под. */

        if drs['a12'] < dr_out['b5'] and rez > 0.:
            ferr = 1
        else:
#            print(pih, drs['a12'], drs['a10'])

            if pih - drs['a12'] >= 2. * drs['a10'] and False:
                hgvostop = pih - drs['a12'] - 2. * drs['a10']
            else:
                if pih - drs['a12'] >= drs['a10']:
                    hgvostop = pih - drs['a12'] - drs['a10']
                else:
                    hgvostop = 0.
                    ferr = 1
    else:
        hgvostop = 0.

    if fss[3]:  #  /*  г.в. парал.       */
        if rasp >= 2. * hgv:
            hgvostpr = rasp - 2. * hgv
        else:
            if rasp >= hgv:
                hgvostpr = rasp - hgv
            else:
                hgvostpr = 0.
                ferr = 1

    else:
        hgvostpr = 0.

    if fss[4]:  #  /*  г.в. смеш.        */
        if rasp >= 2. * hgv:
            hgvostsm = rasp - 2. * hgv
        else:
            if rasp >= hgv:
                hgvostsm = rasp - hgv
            else:
                hgvostsm = 0.
                ferr = 1

    else:
        hgvostsm = 0.

    if fss[0]:
        ho0 = ho

#    drs['a22'] = pr['a22']  # /*  22.Расчетные потери напора на подогревателе 1-ой ступени,м              */
#    drs['a23'] = pr['a23']  # /*  23.Расчетные потери напора на подогревателе 2-ой ступени,м              */
        
#        if gvps != 0:
#            ho0 += drs.get('a22', 0)
        if gvps != 0 or gvpw != 0:
            ho0 += drs.get('a23', 0)

        if rasp >= ho0:
            hoost = rasp - ho0
        else:
            hoost = 0.
            ferr = 1
    else:
        hoost = 0.

#    print(ptr_name, pihP, pihO, rasp)

#    print('ferr=', ferr);

    if ferr == 0:
        hgvost = hgvostop + hgvostpr + hgvostsm
        ggv = gvpr + gvsm + gvop + gvoo + gvps + gvpw + rez


        if (otopl + vn + ggv) > 0.:
            hrc = (hoost * otopl + hvost * vn + hgvost * ggv) / (otopl + vn + ggv)


#            print('-----------')
#            print(hoost)
#            print(hvost)
#            print(hgvost)

            hrc = hoost
            if hvost != 0 and hvost < hrc:
                hrc = hvost
                
            if hgvost != 0 and hgvost < hrc:
                hrc = hgvost


#            print(f'{ptr_name} hv={hv} hvost={hvost} hgvost={hgvost} hoost={hoost} hrc={hrc}')

            if fss[6]:   #  /*  г.в. открыт. под. */
#                print(f'''{pihP} - {hrc} - {drs['a12']}''', drs['a10'])

                if pihP - hrc - drs['a12'] < drs['a10']:
                    hrc0 = pihP - drs['a12'] - drs['a10'] - 2

#                    print('hrc', hrc)

                    if hrc0 < 0:
                        hrc0 = 0
                    if hrc0 < hrc:
                        hrc = hrc0


            if fss[7]: # """ если есть откр. ГВ из обратки """
                h_kran = drs['a12']
                h_kran0 = drs['a10']

                hrc0 = pihP - hrc - (h_kran+h_kran0) - 2

                if hrc0 < 0:
                    hrc0 = 0

                if hrc0 < hrc:
                   hrc = hrc0


#                print(f'=hrc={hrc} {(h_kran+h_kran0)}')


#            if fss[1]: # """ если есть вентиляция """

#                if pihP - hrc - drs['a12'] < drs['a10']:
#                    hrc = pihP - drs['a12'] - drs['a10'] - 2


#            print(ptr_name, 'hrc=', hrc)

        
            if hrc > 0:
                if hrc >= H_DOPUST:
                    h_3mm = hrc
                    n_3mm = 1

#                    ferr, hrc, dr_out['b12'] = drsh3(otopl + vn + ggv, drs['a15'], drs['a16'], hrc)
                    ferr, hrc, dr_out['b12'] = drsh3(Gz, drs['a15'], drs['a16'], hrc)

                    if ferr:
                        n_3mm = int(h_3mm / hrc)
                        if n_3mm > 3:
                            n_3mm = 3
                        w_print(f" На входе теплового пункта потребителя {ptr_name} необходимо ")
                        w_print(f" установить последовательно {n_3mm} головных диафрагмы диаметром {drs['a15']} мм.")
                        w_print(f"\t Остаток непогашенного напора равен {h_3mm - n_3mm * hrc:.1f} м.")

                    dr_out['b13'] = hrc * n_3mm
                    dr_out['b14'] = otopl + vn + ggv

                h20 = hrc
#                ras = gvpr + gvsm + gvps + gvpw + gvop + gvoo + rez + otopl + vn 



#                print(f'{ptr_name} ras={ras} Gz={Gz}')

#                print(f'{ras} = {gvpr} + {gvsm} + {gvps} + {gvpw} + {gvop} + {gvoo} + {rez} + {otopl} + {vn}');



                pihP -= h20
                rasp -= h20

#                print('pihP=', pihP, 'h20=', h20)
#                exit(1)

#    print(ptr_name, pihP, pihO, rasp)
    
    ferr = drvary1(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name, 2, True)

    return ferr 


