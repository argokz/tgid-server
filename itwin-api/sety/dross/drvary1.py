import math

from sety.dross.drsh2 import drsh2
from sety.dross.drsh3 import drsh3

from sety.dross.w_print import w_print

##include        "pfedit1.h"
##include        "grext.h"
H_DOPUST = 3.0   # """ допустимый остаток располагаемого напора """

def msg3(n_3mm):
  if n_3mm > 1:  
    w_print(f"Из практики технической эксплуатации устанавливается не более одного дросселя");
    w_print(f"    диаметром 3 мм, который используется при расчете фактического режима.");


def drvary1(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn,
            gvpr, gvsm, gvps, gvpw, gvop, gvoo, rez, fss,
             ho, hv, hgv, ptr_name, rezh, message=True):

    ferr = False

#    print(ptr_name, rasp)
#    print('>>>> pihP=', pihP, 'pihO', pihO, 'rasp=', rasp, 'Gz=', Gz, 'otopl=', otopl, 'gvop=', gvop, 'gvoo=', gvoo, 'rez=', rez)


#    w_print(fss)
#      hrc,ggv,hoost,hogrost,hgvost,hvost,h_3mm,f
#      n_3mm,ferr=0,t_g
#     fss = [True, True, True, True, True, True, True]
#    rez = 10
#    hrc = 10

#    print(fss)

#    hoost, hvost, hgvost, ggv, hogrost = 0, 0, 0, 0, 0

    if fss[7]: # """ если есть откр. ГВ из обратки """

        if rez > 0.:  # есть рециркуляция
            if fss[0] != 0:
#                 hrc=drs['a10']*rez*rez/gvoo/gvoo+drs['a11']
                 hrc = drs['a12']-drs['a11']-pihO
                 n_3mm = 1

#                 print(f'!== hrc={hrc} {drs['a12']}-{drs['a11']}-{pihO}')

                 if hrc > 0.:
                     h_3mm = hrc
               
                     ferr, hrc, dr_out['b39'] = drsh3(rez, drs['a15'],drs['a16'], hrc)
               
                     dr_out['b40'] = hrc
                     dr_out['b41'] = otopl
                 else:
                     if message:
                          w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                          w_print(f"    на входе водоразборных приборов.")
                          w_print(f"    Расчет подпорно циркул. диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')
                          msg3(n_3mm)
           
            else:
                if message:
                    w_print(f"Для потребителя {ptr_name} не может быть рассчитана ")
                    w_print(f"    подпорно циркул. диафрагма в сети ГВС, т.к. не задана нагрузка на отопление")
           
#    drs['a10'] = pr['a10']  # /*  10.Расчетные потери напора в подающем трубопроводе,м.вод.ст             */
#    drs['a11'] = pr['a11']  # /*  11.Расчетные потери напора в циркуляционном трубопроводе,м.вод.ст       */
#    drs['a12'] = pr['a12']  # /*  12.Расчетный напор на входе водоразборных приборов,м.вод.ст             */


            hrc = drs['a12'] + drs['a10'] - pihO

#            print(f'{hrc} = {drs['a12']} + {drs['a10']} - {pihO}')
           
            if hrc > 0.:
                   h_3mm = hrc
                     
                   n_3mm = 1
           
                   ferr, hrc, dr_out['b36'] = drsh3(otopl+vn-(gvoo+rez), drs['a15'], drs['a16'], hrc)
           
                   if ferr:
                        n_3mm = int(h_3mm/hrc)
                        if  n_3mm > 3:
                           n_3mm = 3

                        if message:
                            
                            w_print(f"В потребителе {ptr_name} на входе подающ. ГВС")
                            w_print(f"    необходимо установить ({n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                            w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                            msg3(n_3mm)
#                        dr_out['b33'] = drs['a15']
           
                   dr_out['b37'] = hrc*n_3mm
                   dr_out['b38'] = gvoo+rez
           
            else:
                if message:
                   w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                   w_print(f"    на входе водоразборных приборов.")
                   w_print(f"    Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')
           
        else:  # Нет рециркуляции
            hrc = pihO+dr_out['b37']-drs['a12']-drs['a10']
#            print(f'{hrc} = {pihO}+{dr_out['b37']}-{drs['a12']}-{drs['a10']}')

            if hrc > 0.:
                  h_3mm = hrc
                  n_3mm = 1
                  ferr, hrc, dr_out['b33'] = drsh3(gvoo + rez, drs['a15'], drs['a16'], hrc)

                  if ferr:
                       n_3mm = int(h_3mm/hrc)
                       if n_3mm > 3:
                          n_3mm = 3
                       if message:
                           w_print(f"В потребителе {ptr_name} на входе подающ. ГВС")
                           w_print(f"    необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                           w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                           msg3(n_3mm)
    #                     dr_out['b33'] = drs['a15']
                  dr_out['b34'] = hrc*n_3mm
                  dr_out['b35'] = gvoo+rez
            else:
                if message:
                    w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                    w_print(f"    на входе водоразборных приборов. ")
                    w_print(f"    Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')

    if fss[6]:  # """ если есть открытое ГВ из подачи """

       

##############/
#                dr_out['b5'] - Напор в обратном трубопроводе ТПП
#                drs['a12'] - Расчетный напор на входе водоразборных приборов
#            w_print(f" %ld %g ", drs['a12'], dr_out['b5'])
#


#           вставлено  and rez > 0. 25.06.03
#           считать шайбу если есть рециркуляция

        if drs['a12'] < dr_out['b5'] and rez > 0.:
            if message:
                w_print(f"Для потребителя {ptr_name} возможен переток воды из обратного")
                w_print(f"    трубопровода в водоразборные приборы, так как заданный напор")
                w_print(f"    на входе водоразборных приборов меньше напора в обратном")
                w_print(f"    трубопроводе теплового пункта. При этом расчет диафрагм")
                w_print(f"    для подающего и циркуляционного трубопроводов ГВС не выполняется.", color='red')
            ferr = 1
        else:
#            print(f'''??? {pihP}-{drs['a12']}-{drs['a10']}''')
            hrc = pihP-drs['a12']-drs['a10']
            if hrc > 0.:
                h_3mm = hrc
                n_3mm = 1
#
#   ИСПРАВЛЕНО 5.08.02
#                    if(drsh3(gvop+rez,drs['a15'],drs['a16'],&hrc,&dr_out['b33']))
#

#                    if(drsh3(gvop,drs['a15'],drs['a16'],&hrc,&dr_out['b33']))

                ferr, hrc, dr_out['b33'] = drsh3(gvop+rez, drs['a15'], drs['a16'], hrc)

                if ferr:
                     n_3mm = int(h_3mm/hrc)
                     if n_3mm > 3:
                        n_3mm = 3
                     if message:
                         w_print(f"В потребителе {ptr_name} на входе подающего трубопровода")
                         w_print(f"    ГВС необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                         w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                         msg3(n_3mm)

                dr_out['b34'] = hrc*n_3mm
#
#   ИСПРАВЛЕНО 5.08.02
#                    dr_out['b35'] = gvop+rez
# 
                dr_out['b35'] = gvop
                dr_out['b35'] = gvop+rez
  
            else:
                if message:
                    w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                    w_print(f"    на входе водоразборных приборов.")
                    w_print(f"    Расчет ограничительной диафрагмы на входе подающего трубопровода ГВС не выполняется.", color='red')

            if rez > 0.:
#
#   ИСПРАВЛЕНО 5.08.02
#                hrc=rasp-dr_out['b34']/(gvop+rez)/(gvop+rez)*rez*rez-
#                    (drs['a10']*rez*rez/gvop/gvop+drs['a11'])
                  hrc = rasp-dr_out['b34']/gvop/gvop*rez*rez-(drs['a10']*rez*rez/gvop/gvop+drs['a11'])
     
    #             hrc = rasp - dr_out['b34']
                  hrc = drs['a12']-drs['a11']-pihO

                  if hrc > 0.:
                      h_3mm = hrc
                      n_3mm = 1
                      ferr, hrc, dr_out['b39'] = drsh3(rez, drs['a15'], drs['a16'], hrc)

                      if ferr:
                           n_3mm = int(h_3mm/hrc)
                           if n_3mm > 3:
                              n_3mm = 3
                           if message:
                               w_print(f"В потребителе {ptr_name} в циркул. сети ГВС")
                               w_print(f"    необходимо установить {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                               w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                               msg3(n_3mm)

                      dr_out['b40'] = hrc*n_3mm
                      dr_out['b41'] = rez
                  else:
                      if message:
                          w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                          w_print(f"    в циркул. сети ГВС.")
                          w_print(f"    Расчет ограничительной диафрагмы в циркул. сети ГВС не выполняется.", color='red')

    if fss[3]:    #  г.в. парал.       
        hrc = rasp - hgv
#        print(f'{ptr_name} {hrc} = {rasp}-{hgv}')

        if hrc > 0.:
            h_3mm = hrc
            n_3mm = 1
           
            ferr, hrc, dr_out['b30'] = drsh3(gvpr, drs['a15'], drs['a16'], hrc)
           
            if ferr:
                n_3mm = int(h_3mm/hrc)
                if n_3mm > 3:
                    n_3mm = 3
           
#                w_print(f"%hrc = %g  n_3mm = %g\n", hrc, h_3mm/hrc)
           
                if message:
                    w_print(f"В потребителе {ptr_name} на входе пар. включ.подогр. ГВС ")
                    w_print(f"    необходимо установить последовательно {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                    w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                    msg3(n_3mm)

            dr_out['b31'] = hrc*n_3mm
            dr_out['b32'] = gvpr
        else:
            if message:
                w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                w_print(f"    на входе пар. включ.подогр. ГВС.")
                w_print(f"    Расчет ограничительной диафрагмы на входе пар. включ.подогр. ГВС не выполняется.", color='red')

    if fss[4]:   #  г.в. смеш.
        hrc = rasp-hgv
        if hrc > 0:
           h_3mm = hrc
           n_3mm = 1

           ferr, hrc, dr_out['b30'] = drsh3(gvsm, drs['a15'], drs['a16'], hrc)

           if ferr:
                n_3mm = int(h_3mm/hrc)
                if n_3mm > 3:
                   n_3mm = 3

                if message:
                    w_print(f"В потребителе {ptr_name} на входе второй ступени")
                    w_print(f"    подогревателя ГВС необходимо установить последовательно ")
                    w_print(f"    {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                    w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                    msg3(n_3mm)
           dr_out['b31'] = hrc*n_3mm
           dr_out['b32'] = gvsm
        else:
           if message:
               w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
               w_print(f"    на входе второй ступени подогревателя ГВС.")
               w_print(f"    Расчет ограничительной диафрагмы на входе второй ступени подогр. ГВС не выполняется.", color='red')

      
    if fss[1]: # """ если есть вентиляция """
            hrc = rasp-hv
            hrc -= dr_out['b37']

#            print(f'{ptr_name} rasp={rasp} hc={hv} b37={dr_out['b37']} hrc={hrc}')

            if hrc > 0.:
                h_3mm = hrc
                n_3mm = 1

                ferr, hrc, dr_out['b27'] = drsh3(vn, drs['a15'], drs['a16'], hrc)

                if ferr:
                      n_3mm = int(h_3mm/hrc)
                      if n_3mm > 3:
                          n_3mm = 3
                      if message:
                          w_print(f"В потребителе {ptr_name} для гашения избыточного напора")
                          w_print(f"    на входе системы вентиляции необходимо установить последовательно ")
                          w_print(f"    {n_3mm} диафрагмы диаметром {drs['a15']} мм")
                          w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                          msg3(n_3mm)

                dr_out['b28'] = hrc*n_3mm
                dr_out['b29'] = vn
            else:
                if message:
                      w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                      w_print(f"    на входе системы вентиляции. ")
                      w_print(f"    Расчет ограничительной диафрагмы на входе системы вентиляции не выполняется.", color='red')
      
      
    if fss[0] == 0:
        pass        
        
#            case  0  : break
#   """ Э """  
    elif fss[0] == 1:
        hrc = rasp

#        print(f'hrc={hrc} drs[\'a23\']={drs['a23']}')
#        print(f'hrc={hrc} drs[\'a22\']={drs['a22']}')

# -------------------------------------------------------------------
        if fss[5] != 0: 
            hrc -= drs['a23']
# -------------------------------------------------------------------
#        hrc = rasp-ho

#        print(ptr_name, hrc, dr_out['b37'])
        hrc -= dr_out['b37']

        if hrc > 0.:
            qq6 = False

            if hrc > 40 and rezh == 6:
                hrc /= 2
                qq6 = True

            if hrc > 2*ho:
                if message:
                     w_print(f"Для потребителя {ptr_name} элеватор работает")
                     w_print(f"    при повышенном напоре. Возможны вибрация и шум.")

            hoost = hrc
#            t_g = drs['a17']&255
            t_g = drs['a17']  # """&255"""


            if t_g == 1:    # """'О'"""
                otopl = otopl + gvps + gvpw

            if qq6:       # режим 6 и перепад > 40
                hrc1 = hrc

                ferr, hrc1, dr_out['b21'] = drsh3(otopl, drs['a15'], drs['a16'], hrc1)

                hrc = hrc*2 - hrc1

            ferr, hrc, dr_out['b7'], dr_out['b11'] = drsh2(otopl,drs['a14'],drs['a6'],drs['a7'], hrc, ptr_name)

            if ferr:
                hoost = hoost-hrc

                h_3mm = hoost
                if gvps == 0. and gvpw == 0.:
                   f = otopl*otn_fs # """***********************************************************************"""
                   if f != 0:
                      n_3mm = 1
#                      h_3mm = hrc

                      ferr, hoost, dr_out['b21'] = drsh3(f,drs['a15'],drs['a16'], hoost)

                      if ferr:
                        n_3mm = int(h_3mm/hoost)
                        if n_3mm > 3:
                            n_3mm = 3

                        if otn_fs == 1.: 
                            if message:
                                w_print(f"В системе отопления потребителя {ptr_name} ")
                        else:  
                            if message:
                                w_print(f"В системе отопления уличн. фасада потребителя {ptr_name} ")

                        if message:
                            w_print(f"    необходимо установить последовательно {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                            w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hoost:.1f} м.")
                            msg3(n_3mm)

                      dr_out['b22'] = hoost
                      dr_out['b23'] = f


                   f = otopl*(1.-otn_fs)
                   if f != 0:
                      n_3mm = 1
#                      h_3mm = hrc

                      ferr, hoost, dr_out['b24'] = drsh3(f, drs['a15'], drs['a16'], hoost)
                        
                      if ferr:
                        n_3mm = int(h_3mm/hoost)
                        if n_3mm > 3:
                            n_3mm = 3

                        if message:
                            w_print(f"В системе отопления дворов. фасада потребителя {ptr_name} ")
                            w_print(f"    необходимо установить последовательно {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                            w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hoost:.1f} м.")
                            msg3(n_3mm)

                      dr_out['b25'] = hoost
                      dr_out['b26'] = f
                else:
                   ferr, hoost, dr_out['b30'] = drsh3(otopl, drs['a15'], drs['a16'], hoost)

                   if ferr:
                     n_3mm = int(h_3mm/hoost)
                     if n_3mm > 3:
                         n_3mm = 3

                     if message:
                         w_print(f"В потребителе {ptr_name} на входе второй ступени")
                         w_print(f"    подогревателя ГВС необходимо установить последовательно ")
                         w_print(f"    {n_3mm} диафрагмы диаметром {drs['a15']} мм.")
                         w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hoost:.1f} м.")
                         msg3(n_3mm)

                     dr_out['b12'] = drs['a15']

                   dr_out['b31'] = hoost
                   dr_out['b32'] = otopl

            dr_out['b8'] = hrc
            dr_out['b9'] = otopl
        else:
            if message:
                w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                w_print(f"    на входе системы отопления.")
                w_print(f"    Расчет сопла и ограничительной диафрагмы на входе системы отопления не выполняется.", color='red')

    elif fss[0] == 3 or fss[0] == 2:
#   """ З """  case  3  :
#   """ Н """  case  2  :
        hrc = rasp-ho


#        print(ptr_name, hrc, rasp, ho, dr_out['b37'], drs['a23'])


# -------------------------------------------------------------------
        if fss[5] != 0: 
            hrc -= drs['a23']
# -------------------------------------------------------------------


        hrc -= dr_out['b37']
        t_g = drs['a17'] #"""&255"""
        if t_g == 1:   # """'О'"""
            otopl = otopl + gvps + gvpw

        if hrc > 0.:

            f = otopl*otn_fs #"""***********************************************************************"""
            
#            print(ptr_name,  'f=', f)
            
            if f != 0:
               h_3mm = hrc
               n_3mm = 1

               ferr, hrc, dr_out['b21'] = drsh3(f, drs['a15'], drs['a16'], hrc)

#               print(ptr_name, 'f=', f, 'a15=', drs['a15'], 'a16=', drs['a16'], 'hrc=', hrc, dr_out['b21'])

               if ferr:
                    n_3mm = int(h_3mm/hrc)
                    if n_3mm > 3:
                        n_3mm = 3
                    if otn_fs == 1.: 
                        if message:
                            w_print(f"В системе отопления потребителя {ptr_name} ")
                    else:  
                        if message:
                            w_print(f"В системе отопления уличн. фасада потребителя {ptr_name} ")

                    if message:
                        w_print(f"    необходимо установить последовательно {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                        w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                        msg3(n_3mm)

               dr_out['b22'] = hrc*n_3mm
               dr_out['b23'] = f

            f = otopl*(1.-otn_fs) # """***********************************************************************"""
            if f != 0:
               h_3mm = hrc
               n_3mm = 1

               ferr, hrc, dr_out['b24'] = drsh3(f, drs['a15'], drs['a16'], hrc)

               if ferr:
                    n_3mm = int(h_3mm/hrc)
                    if n_3mm > 3:
                        n_3mm = 3

                    if message:
                        w_print(f"В системе отопления дворов. фасада потребителя {ptr_name} ")
                        w_print(f"    необходимо установить последовательно {n_3mm} диафрагм диаметром {drs['a15']} мм.")
                        w_print(f"    Остаток непогашенного напора равен {h_3mm-n_3mm*hrc:.1f} м.")
                        msg3(n_3mm)
               dr_out['b25'] = hrc*n_3mm
               dr_out['b26'] = f
        else:
            if message and rezh != 2:
                 w_print(f"Для потребителя {ptr_name} не обеспечено заданное значение напора")
                 w_print(f"    на входе системы отопления.")
                 w_print(f"    Расчет ограничительной диафрагмы на входе системы отопления не выполняется.", color='red')

#    exit(1)
    return ferr


if __name__ == "__main__":

    pass
#    drvary1()
