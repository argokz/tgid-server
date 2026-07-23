if not __package__:
    import os
    import sys
    parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
    sys.path.append(os.path.abspath(os.path.join(parent_dir, '..', '..')))
#    w_print(os.path.abspath(os.path.join(parent_dir, '..', '..', '..')))


from sety.dross.drchck1 import drchck1
from sety.dross.drsh1 import drsh1
from sety.dross.drvary1 import drvary1
from sety.dross.drvary2 import drvary2
from sety.dross.drvary3 import drvary3
from sety.dross.drvary4 import drvary4
from sety.dross.drvary5 import drvary5

from sety.dross.w_print import w_print
from sety.dross.w_print import w_init
from sety.dross.w_print import get_text

from sety.teplo.otopl import getUFpr


def getTR(tr):
    return None

def pr_name(pr, a):
    return f'{a}'

#def getUFpr(n, pr):
#    return 2.2


errmsg = "Расчет дроссельных органов не выполняется."

def init_dr_out():
    dr_out = dict()

    dr_out['b7'] = 0
    dr_out['b8'] = 0
    dr_out['b9'] = 0.
    dr_out['b11'] = 0
    dr_out['b12'] = 0
    dr_out['b13'] = 0
    dr_out['b14'] = 0
    dr_out['b15'] = 0
    dr_out['b16'] = 0
    dr_out['b17'] = 0
    dr_out['b18'] = 0
    dr_out['b19'] = 0
    dr_out['b20'] = 0
    dr_out['b21'] = 0
    dr_out['b22'] = 0
    dr_out['b23'] = 0
    dr_out['b24'] = 0
    dr_out['b25'] = 0
    dr_out['b26'] = 0
    dr_out['b27'] = 0
    dr_out['b28'] = 0
    dr_out['b29'] = 0
    dr_out['b30'] = 0
    dr_out['b31'] = 0
    dr_out['b32'] = 0
    dr_out['b33'] = 0
    dr_out['b34'] = 0
    dr_out['b35'] = 0
    dr_out['b36'] = 0
    dr_out['b37'] = 0
    dr_out['b38'] = 0
    dr_out['b39'] = 0
    dr_out['b40'] = 0
    dr_out['b41'] = 0
    dr_out['b42'] = 0
    dr_out['b43'] = 0

    return dr_out

def dross(potr_name, pr, pr2, pt_out, el, isEl): ##(CNode* n,  const EL* el, bool isEl, const ZE* ze, const PT_OUT* pt_out, DR_OUT* dr_out)
#    DRS drs
#    UZEL ptr

#    w_print(pr)
#    w_print(pr2)
#   w_print(pt_out)
#    exit(0)



    w_init()

    dr_out = init_dr_out()
    
    pihP = pt_out['a21']
    pihO = pt_out['a22']

    svqp = pt_out['a16']
    svqo = pt_out['a17']
    otz = pt_out['a4']   #  Расход на отопление, зав.сх.
    otn = pt_out['a5']   #  Расход на отопление, незав.сх.
    ot_f = pr['otn_fs']  #/ Так надо
    vn = pt_out['a6']
    gvop = pt_out['a12']
    gvoo = pt_out['a13']
    rez = pt_out['G_rez']

#    print(pt_out)

    Gz = pt_out['Gz']   # Суммарный расход в закрытой системе


    gvps = pr2['G_gvps']   # Пойдет
    gvpw = pr2['G_gvpw']   # Пойдет
    gvpr = pr2['G_gvpr']
    gvsm = pr2['G_gvsm']


    h_pih = 9

#    double rasp
#    double ho, hv, hgv, h_pih = 0
#    double ggv
#    short rezh
    #  short *hz

    nagr = otz + otn + gvop + gvoo + gvps + gvpw + gvpr + gvsm + vn


#    w_print(f'Дроссель nagr = {nagr}')

    if nagr == 0: 
        return False, dr_out

    """
    ptr.a1[0] = 0
    ptr.a2[0] = 0
    """

#    ptr.a1 = n->getName().c_str()

#    CString getKod(long nomer)

#    ptr.a1 = getKod(n->externalCodeID)
#    ptr.a2 = n->name_uzel.c_str()
    #  strcat(ptr.a2, "    ")


#    CString a1 = n->getName().c_str()
    a1 = 'Название узла!!'
    a1 = potr_name


#    w_print(f'Считаем дроссели на {pr_name(pr, a1)}')


###    hz = ze ? ze->h : pr['h']  # ?????????

    hz = pr['h']  # ?????????

    if (gvoo > 0 or gvop > 0) and hz > pr['a12']:
        #    w_print(f" У потребителя {pr_name(pr, a1)} hz = %g > a12 = %d", pr_name(pr, a1), hz, pr['a12'])
        w_print(f" Заданный расчетный напор на входе водоразборных приборов")
        w_print(f" у потребителя {pr_name(pr, a1)} меньше высоты здания")

    if gvoo > 0 and gvoo > otz + otn + vn:
        w_print(f" У потребителя {pr_name(pr, a1)} расход на ГВС превышает")
        w_print(f" суммарный расход в закрытых теплопотребляющих системах")

    elif gvoo > 0 and rez + gvoo > otz + otn + vn:
        w_print(f" У потребителя {pr_name(pr, a1)} суммарный расход на ГВС и рециркуляцию превышает")
        w_print(f" суммарный расход в закрытых теплопотребляющих системах")

    if gvoo > 0 and rez > 0 and pr['a12'] - pr['a11'] < pihO:
        w_print(f" У потребителя {pr_name(pr, a1)} полученный напор на входе водоразборных ")
        w_print(f" приборов превышает заданный")


    fss = dict()
#    short fss[30]
    prelev = 'Н'
    ferr = 0
#    double otopl, otn_fs


    #  strncpy(ptr.a1, pr['kod'], 3) ptr.a1[3] = 0
    #  strncpy(ptr.a2, pr['uzel'], 10) ptr.a2[10] = 0


    drs = dict()

    drs['a1'] = pr['id']

    n = 0

    if el:
        drs['a4'] = 'Э'  # /*  4.Способ присоединения системы отопления                                */
        drs['a5'] = el['a5'] #/*  5.Номер  элеватора                                                      */
    #    drs['a6'] = el['a6'] #/*  6.Коэффициент смешения элеватора                                        */
        drs['a6'] = getUFpr(n, pr) #/*  6.Коэффициент смешения элеватора                                        */

    elif isEl:
        drs['a4'] = 'Э'  # /*  4.Способ присоединения системы отопления                                */
        drs['a5'] = 0 #/*  5.Номер  элеватора                                                      */
        drs['a6'] = getUFpr(n, pr) #/*  6.Коэффициент смешения элеватора                                        */

#        if drs['a6'] == 1:
#            print('!!!', pr.get('uf'))
#            exit(0)


    
    else:
        drs['a4'] = ' '  # /*  4.Способ присоединения системы отопления                                */
        drs['a5'] = 0    # /*  5.Номер  элеватора                                                      */
        drs['a6'] = 0    # /*  6.Коэффициент смешения элеватора                                        */

    drs['a7'] = pr['a7']    # /*  7.Потери напора в отопительной системе или отопительном подогpевателе,м */
    drs['a8'] = pr['a8']    # /*  8.Потери напора в калориферах, м                                        */
    drs['a9'] = pr['a9']    # /*  9.Потери напора в кондиционерах,м                                       */
    drs['a10'] = pr['a10']  # /*  10.Расчетные потери напора в подающем трубопроводе,м.вод.ст             */
    drs['a11'] = pr['a11']  # /*  11.Расчетные потери напора в циркуляционном трубопроводе,м.вод.ст       */
    drs['a12'] = pr['a12']  # /*  12.Расчетный напор на входе водоразборных приборов,м.вод.ст             */

    drs['a13'] = 1

#    print('-----------------', pr['a13'])

#    if pr['a13'] in ('1','2','3','4','5','6'):
#        drs['a13'] = pr['a13']  # /*  13.Признак ступени                                                      */

    if pr['a13'] in (1,2,3,4,5,6):
        drs['a13'] = pr['a13']  # /*  13.Признак ступени                                                      */


    drs['a14'] = pr['a14']  # /*  14.Диаметр сопла элеватора минимально допустимый,мм                     */
    drs['a15'] = pr['a15']  # /*  15.Диаметр дроссельной диафрагмы минимально допустимый,мм               */
  # ????????????????
 #  drs['a16'] = el['d_entry']# /*  16.Диаметр внутренний установочного фланца,мм                           */


    #### !!!!!!!!!!!!!
    drs['a16'] = 0    # /*  16.Диаметр внутренний установочного фланца,мм                           */
    #### !!!!!!!!!!!!!

    drs['a17'] = pr['a17']  # /*  17.Признак температурного графика                                       */
    drs['a18'] = pr['a18']  # /*  18.Число параллельно включенных подогревателей 1-ой ступени             */
    drs['a19'] = pr['a19']  # /*  19.Число параллельно включенных подогревателей 2-ой ступени             */
  #  drs['a20'] = pr['a20']  # /*  20.Расчетный расход через подогреватель 1-ой ступени,т/ч                */
  #  drs['a21'] = pr['a21']  # /*  21.Расчетный расход через подогреватель 2-ой ступени,т/ч                */

    drs['a20'] = 0          # /*  20.Расчетный расход через подогреватель 1-ой ступени,т/ч                */
    drs['a21'] = 0          # /*  21.Расчетный расход через подогреватель 2-ой ступени,т/ч                */
    
    drs['a22'] = pr['a22']  # /*  22.Расчетные потери напора на подогревателе 1-ой ступени,м              */
    drs['a23'] = pr['a23']  # /*  23.Расчетные потери напора на подогревателе 2-ой ступени,м              */
    drs['a24'] = pr['a24']  # /*  24.Удельный объем воды в системе отопления,м3*ч/Гкал                    */
    drs['a25'] = pr['a25']  # /*  25.Удельный объем воды в системе вентиляции,м3*ч/Гкал                   */

    if pr['gvpw'] != 0.:
        drs['a22'] = 0. # Нет первой ступени

#    print(drs)
#    exit(0)

    dr_out['id'] = drs['a1']
    #  dr_out['b43'] = vn * drs['a25'] / tvur[p_ur].ventil
    #  dr_out['b43'] = pr2['G_ventil'] * drs['a25']
    dr_out['b43'] = pr['ventil'] * drs['a25']
    rasp = pihP - pihO
    dr_out['b10'] = drs['a5']
    dr_out['b4'] = pihP
    dr_out['b5'] = pihO
    dr_out['b6'] = rasp


#    print(potr_name, pr['cxema'])

    debug = False
    if pr['cxema'] == '6.2':
        debug = True

    if pr['cxema'] is None:
        return False, dr_out

    dr_out['cxema'] = pr['cxema']

    if dr_out['cxema'][0] == '1':
        if dr_out['cxema'][2] <= '4':
            dr_out['cxema'] = "Зав.СО"
        else:
            dr_out['cxema'] = "Нез.СО"

    elif dr_out['cxema'][0] == '2':
        dr_out['cxema'] = "Вентиляция" 

    elif dr_out['cxema'][0] == '3':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "Пар.ЗСО"
        else:
            dr_out['cxema'] = "Пар.НСО"

    elif dr_out['cxema'][0] == '4':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "Смеш.ЗСО"
        else:
            dr_out['cxema'] = "Смеш.НСО"
    elif dr_out['cxema'][0] == '5':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "Посл.ЗСО"
        else:
            dr_out['cxema'] = "Посл.НСО"

    elif dr_out['cxema'][0] == '6':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "ОткрПодача.ЗСО"
        else:
            dr_out['cxema'] = "ОткрПодача.НСО"
    elif dr_out['cxema'][0] == '7':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "ОткрОбрат.ЗСО"
        else:
            dr_out['cxema'] = "ОткрОбрат.НСО"
    elif dr_out['cxema'][0] == '15':
        if dr_out['cxema'][2] <= '8':
            dr_out['cxema'] = "Предвкл.ЗСО"
        else:
            dr_out['cxema'] = "Предвкл.НСО"

    dr_out['otoplz'] = pr['otoplz']
    dr_out['otopln'] = pr['otopln']
    dr_out['ventil'] = pr['ventil']
    dr_out['kondiz'] = pr['kondiz']
    dr_out['gvop'] = pr['gvop']
    dr_out['gvoo'] = pr['gvoo']
    dr_out['gvpr'] = pr['gvpr']
    dr_out['gvsm'] = pr['gvsm']
    dr_out['gvps'] = pr['gvps']
    dr_out['gvpw'] = pr['gvpw']

    dr_out['b3'] = pr.get('name_building', '')   # Содержательное наименование

    if rasp < 0:
        return  False, dr_out

    rezh = drs['a13']
#    rezh = 2

#    print('----')
#    print(rezh)
#    exit(0)

#    if rezh != '1' and rezh != '2' and rezh != '3' and rezh != '4' and rezh != '5' and rezh != '6':
#        rezh = '1'

    if rezh != 1 and rezh != 2 and rezh != 3 and rezh != 4 and rezh != 5 and rezh != 6:
        rezh = 1



#    print(rezh)

   # /* проверка условий подключенния потребителя  */

    # Исправил Гена 11.07.04
    #  if (gvps == 0.) drs['a22'] = 0.

    pih38 = 38.


#    const TR* tr = getTR(pr['kodtr'])


    tr = getTR(pr['kodtr'])

    if tr:
        T = 0

        gv = pr['gvpr'] + pr['gvsm'] + pr['gvps'] + pr['gvpw']

        if gv == 0 and pr['otoplz'] != 0:  
            T = tr['Tr_co_1_zco']  #  Расчетная температура сет.воды в подающем трубопроводе, зависимой СО
        elif gv == 0 and pr['otopln'] != 0:
            T = tr['Tr_to_1_nco']  #  Расчетная температура сет.воды на входе подогревателя, незав.СО
        elif pr['gvpr'] != 0:  
            T = tr['Tr_co_1_zco_pr']  #  Расчетная температура сет.воды в под.трубопр.зав.СО, парал.ГВС
        elif pr['gvsm'] != 0:  
            T = tr['Tr_co_1_zco_sm']  #  Расчетная температура сет.воды в под.трубопроводе зав.СО,смеш.ГВС
        elif pr['gvps'] != 0:  
            T = tr['Tr_co_1_zco_ps']  #  Расчетная температура воды в под.трубопроводе зав.СО, посл.ГВС
        elif pr['gvpw'] != 0:  
            T = tr['Tr_co_1_zco_pw']  #  Расчетная температура воды в под.трубопроводе зав., предвкл.ГВС

        pih38 = T2P(T) * 10

        if (pihP < pih38) and (rezh != 4):
            w_print(f" Напор в подающем трубопроводе потребителя {pr_name(pr, a1)}")
            w_print(f" может не обеспечивать невскипание воды при расчетная температуре сетевой воды {T}°C")
            #      w_print(f" превышает 100 Град.C .")
    '''
    /*
    Исправили 02.02.2012 по желанию Н.И.Томиловой

      if ((pihP < pih38) and (rezh != 4)) {
        w_print(f" Напор в подающем трубопроводе потребителя {pr_name(pr, a1)}")
        w_print(f" может не обеспечивать невскипание воды, если ее расчетная температура")
        w_print(f" превышает 100 Град.C .")
      }
    */
    '''

    if (otz != 0.) and (otn != 0.):
        w_print(f" Для потребителя {pr_name(pr, a1)} заданы обе нагрузки")
        w_print(f" на отопление, что недопустимо. {errmsg}")
        return  False, dr_out

    otopl = 0.
    if (rezh == 4 or rezh == 5) and (gvop == 0.):
        w_print(f" У потребителя {pr_name(pr, a1)} не задана нагрузка ГВС при")
        w_print(f" четырехтрубной системе присоединения(признак ступени равен 4 или 5)")
        return False, dr_out

    else:
        if (rezh == 4 or rezh == 5) and (rez == 0.):
            w_print(f" У потребителя {pr_name(pr, a1)} не задана циркуляционная нагрузка при")
            w_print(f" четырехтрубной системе присоединения(признак ступени равен 4 или 5)")
            return False, dr_out

    if otz != 0.:
        otopl = otz
        prelev = drs['a4']
        #    dr_out['b42'] = otopl * drs['a24'] / tvur[p_ur].otoplz
        #    dr_out['b42'] = pr2['G_otoplz'] * drs['a24']
        dr_out['b42'] = pr['otoplz'] * drs['a24']

    if otn != 0.:
        otopl = otn
        prelev = 'Н'
        #    dr_out['b42'] = otopl * drs['a24'] / tvur[p_ur].otopln
        #    dr_out['b42'] = otopl * drs['a24']
        dr_out['b42'] = pr['otopln'] * drs['a24']

    otn_fs = ot_f

    if otn_fs == 0.:
        otn_fs = 1.

    if prelev == 'Э' or prelev == ' ':
        if pihO > 60.:
            w_print(f" Напор в обратном трубопроводе потребителя {pr_name(pr, a1)}")
            w_print(f" превышает допустимое значение по условиям прочности")
            w_print(f" нагревательных приборов систем отопления.")

    if prelev == 'Н':
        if pihO > 100.:
            w_print(f" Напор в обратном трубопроводе потребителя {pr_name(pr, a1)}")
            w_print(f" превышает допустимое значение по условиям прочности")
            w_print(f" нагревательных приборов систем отопления.")

    if rasp < 0.:
        w_print(f" Потребитель {pr_name(pr, a1)} имеет отрицательный располагаемый напор.")
        w_print(f" Прямое присоединение к ОС невозможно. {errmsg}")
        return False, dr_out

#    if debug:
#        print(otopl)
#        exit(0)

    if otopl != 0.:
        if drs['a7'] == 0.:
            w_print(f" Не заданы потери напора в отопительной системе или отопительном")
            w_print(f" подогревателе потребителя {pr_name(pr, a1)}. Расчет не выдолняется")
            return False, dr_out

        if prelev == 'Э':
            if drs['a6'] == 0.:
                w_print(f" Не задан коэффициент смешения элеватора потребителя {pr_name(pr, a1)}")
                return False, dr_out

#     / a6 *  6.Коэффициент смешения элеватора                                        */
#    'calcThrustLosHS': 'a7',  # Расчетные потери напора в отопит.системе (подогревателе)

            fss[0] = 1              # /* включ. элев. */
            ho = 1.4 * drs['a7'] * (1. + drs['a6']) * (1. + drs['a6']) # /*минимально необходимый перепад на системе отопления */
#            print(f'-!-!-!- ho={ho}  {drs['a7']}   {drs['a6']}')
            otopl = otz

        elif prelev == 'Н':
            fss[0] = 2              # /* включ. по независ. схеме */
            ho = drs['a7']
            otopl = otn

        elif prelev == ' ':
            fss[0] = 3              # /* включ. без элеватора */
            ho = drs['a7']
            otopl = otz
        else:
            w_print(f" Ошибка в данных ")

    else:
        fss[0] = 0
        ho = 0.

    hv = 0.
    hgv = 0.

    if drs['a7'] == 0 and pr['otopln'] + pr['otoplz'] > 0:
        w_print(f" Не заданы расчетные потери напора в отопительной системе для {pr_name(pr, a1)} ")

    if drs['a8'] == 0 and pr['ventil'] > 0:
        w_print(f" Не заданы расчетные потери напора в КУ для {pr_name(pr, a1)} ")

    fss[1], hv = drchck1(vn, drs['a8'], hv)     # /*  вентиляция        */
    fss[3], hgv = drchck1(gvpr, drs['a23'], hgv) # /*  г.в. парал.       */
    fss[4], hgv = drchck1(gvsm, drs['a23'], hgv) # /*  г.в. смеш.        */
    fss[5], hgv = drchck1(gvps + gvpw, drs['a23'], hgv) # /*  г.в. послед.      */

    if fss[5]:
        drs['a20'] = 0.
        drs['a21'] = 0.

    fss[6], hgv = drchck1(gvop, drs['a10'], hgv)  # /*  г.в. открыт. под. */
    fss[7], hgv = drchck1(gvoo, drs['a10'], hgv)  # /*  г.в. открыт. обр. */

    if (fss[3] + fss[4] + fss[5] + fss[6] + fss[7]) > 1:
        w_print(f" Для потребителя {pr_name(pr, a1)} задано несколько разнородных ")
        w_print(f" нагрузок на ГВ, что недопустимо. {errmsg}")
        return False, dr_out

   # /*if((pihP-hz <= ho)or(pihP-hz <= hv)or(pihP-hz <= hgv)) */

   

    if pihP - hz <= 0:
        if prelev != 'Н':
            w_print(f" Напор в подающем трубопроводе потребителя {pr_name(pr, a1)} меньше высоты здания.")
            w_print(f" Нормальная работа возможна при независимом присоединении или подкачке.")


#    print('-------')
#    ptr = pr_name(pr, a1)
#    print(ptr)
#    print(prelev)
#    print(pihP, pihO, hz, rezh)
#    print(pihO < (hz + 5.) , prelev != 'Н' , rezh < 5)         # /* 'Н' */
#    exit(0)

    D5 = 5.

#    if gvoo > 0 and rez != 0:
#        D5 = -5.

#    if pihO < (hz + D5) and prelev != 'Н' and rezh < D5 and ( gvoo > 0 and rez == 0):         # /* 'Н' */
    if pihO < (hz + D5) and prelev != 'Н' and rezh < 5:         # /* 'Н' */
#    if pihO < (hz + D5) and prelev != 'Н' and rezh < 5  and not (gvoo > 0 and rez != 0):         # /* 'Н' */
        dr_out['b19'] = hz + D5 - pihO
        h_pih = pihO
        if (hz + D5) > 60.:
            dr_out['b19'] = 0.
            w_print(f" Установка подпорной диафрагмы на потребителе {pr_name(pr, a1)}")
            w_print(f" приводит к повышению напора на обратном трубопроводе ")
            w_print(f" выше допустимого значения по СНИП. {errmsg}")
            return False, dr_out
        else:
            pihO = (hz + D5)

        rasp = pihP - pihO
#        ggv = gvpr + gvsm + gvps + gvpw + rez
        ggv = gvpr + gvsm + gvps + gvpw
        
#        rashod = otopl + vn + ggv    -    gvoo

        rashod = Gz - gvoo



        if rashod < 0:
            w_print(f" Расход из открытой гвс {pr_name(pr, a1)} больше чем ")
            w_print(f" расход на отопление, вентиляцию и рециркуляцию ")
            return False, dr_out

        dr_out['b18'] = drsh1(rashod, dr_out['b19'])
        dr_out['b20'] = rashod 

#        print('--------------------------------')
#        print(f'Gz={Gz}')
#        print(f'{rashod} = {otopl} + {vn} + {ggv}    -    {gvoo}')
#        print(f'|{prelev}|', f'r={rashod}, o={otopl}, v={vn}, g={ggv}, {gvoo}, {gvop}')
#        print(f'pihO = {pihO}')
#        exit(0)




    if fss[4] != 0 or fss[5] != 0:    #  г.в. смеш.   г.в. послед
        rasp -= drs['a22']

# Убрал в начале 25 года  
#    if fss[5] != 0:      #   г.в. послед.     
#        rasp -= drs['a23']

    if (rasp <= ho) or (rasp <= hv) or (rasp <= hgv):
        if rasp <= 0.:
            w_print(f" Располагаемый напор потребителя {pr_name(pr, a1)}")
            w_print(f" недостаточен для компенсации потерь в первой ступени подогревателя ГВС.")
            w_print(f" {errmsg}")
            return False, dr_out

        w_print(f" Располагаемый напор потребителя {pr_name(pr, a1)}")
        w_print(f" недостаточен для обеспечения расчетного перепада {rasp:.2f}." )

#        print(rasp, ho, hv, hgv)

    #  w_print(f" {pr_name(pr, a1)}")
    #  w_print(f" rasp = %g ho = %g hv = %g hgv = %g", rasp, ho, hv, hgv)


    ptr = pr_name(pr, a1)
#    print(ptr, a1)
#    exit(0)


#    if debug:
#        print(rez, fss)
#        exit(0)

    # ho - минимальный перепад через отопление
    # hv - перепад через венитиляцию
    # hgv - перепад через гвс
#    print(f'ho={ho} hv={hv} hgv={hgv} pihP={pihP} pihO={pihO} rasp={rasp}')
#    exit(0)


    if rezh == 1:
        drvary1(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr, 1)
    elif rezh == 6:
        drvary1(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr, 6)
    elif rezh == 2:
        drvary2(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr)
    elif rezh == 3:
        drvary3(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr)
    elif rezh == 4:
        drvary4(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr)
    elif rezh == 5:
        drvary5(drs, dr_out, rasp, pihP, pihO, Gz, otopl, otn_fs, vn, gvpr, gvsm, gvps, gvpw, gvop,
            gvoo, rez, fss, ho, hv, hgv, ptr)

#    exit(0)

    pihO = h_pih

#    sss = pr['name_building']
#    sss = sss[:49]
#    dr_out['b3'] = sss

    #  dr_out['balans'] = pr['kod_owner']
    #  dr_out['balans'] = pr['otv']

    #  dr_out['balans'] = pr['otv']
    #  WRIMAS("drou", (char *) dr_out, 1, l_dr)

#    w_print(dr_out)


    txt = get_text()

    dr_out['comment'] = txt

    return True, dr_out

#---------------------------------------------------------------------------------------------------

if __name__ == "__main__":

    pt_out = {}

    pt_out['a4'] = 12.5   # Расход на отопление, зав.сх.                                           
    pt_out['a5'] = 0      # Расход на отопление, незав.сх.                                         
    pt_out['a6'] = 0      # Расход на вентиляцию                                                   
    pt_out['a12'] = 0     # Расход на ГВ из под.трубопр. в откр.системе                            
    pt_out['a13'] = 0     # Расход на ГВ из обр.теплопр. в откр.системе                           
    pt_out['a14'] = 0     # Расход в циркуляционном теплопроводе ГВС                               
    pt_out['Gz'] = 0

    pt_out['a16'] = 0     # Суммарный расход  из под.трубопр. в откр.системе                       
    pt_out['a17'] = 0     # Суммарный расход потребителя из обр.теплопр. в откр.системе            
    pt_out['a21'] = 60    # Пьезометрический напор в подающем теплопроводе                         
    pt_out['a22'] = 50    # Пьезометрический напор в обратном теплопроводе                         

    pr = {}

    pr['cxema'] = '1.1'

    pr['id'] = 0


# Значения по-умолчанию
    pr['a13'] = 1     #  throtStageSignID       # Признак ступени дросселирования
                                                
    pr['a7'] = 1.5    #  calcThrustLosHS        # Расчетные потери напора в отопит.системе (подогревателе)
    pr['a8'] = 5      #  calcThrustLosAH        # Расчетные потери напора в калориферах
    pr['a9'] = 6      #  calcThrustLosAC        # Расчетные потери напора в кондиционерах
    pr['a10'] = 3     #  calcThrustLosFlow      # Расч.потери напора в подающем трубопроводе ГВС
    pr['a11'] = 4     #  calcThrustLosFlowCirc  # Расчетные потери напора в циркул. трубопроводе ГВС
    pr['a12'] = 25    #  calcThrustInWDO        # Расчетный напор на входе водоразборных приборов
    pr['a14'] = 0     #  diameterElevNozzle     # Диаметр сопла элеватора минимально допустимый
    pr['a15'] = 0     #  diameterThrotDiaph     # Диаметр дроссельной диафрагмы минимально допустимый
    pr['a17'] = 1     #  temperChartSignID      # Признак температурного графика
    pr['a18'] = 0     #  parallHeatersCount1    # Число параллельно включенных подогревателей 1 ступени
    pr['a19'] = 0     #  parallHeatersCount2    # Число параллельно включенных подогревателей 2 ступени
# ???  a20                                      
# ???  a21                                      
    pr['a22'] = 0     #  calcThrustLosHeaters1  # Расчетные потери напора на подогревателе 1-ой ступени ГВС
    pr['a23'] = 0     #  calcThrustLosHeaters2  # Расчетные потери напора на подогревателе 2-ой ступени ГВС
    pr['a24'] = 13.3  #  volWaterHS             # Удельный объем воды в системе отопления
    pr['a25'] = 5.5   #  volWaterVS             # Удельный объем воды в системе вентиляции

# ----------------------------------

    pr['h'] = 0       #  buildHeight            # Высота здания
    pr['kodtr'] = 1   #  calcTemperatureID      # Код расчетных температур

# ----------------------------------
# Нагрузки

    pr['otopln'] = 0  #  calcHLindep            # Расчетная тепловая нагрузка на  отопление независимое
    pr['otoplz'] = 1  #  calcHLdep              # Расчетная тепловая нагрузка на  отопление зависимое

    pr['otn_fs'] = 0  #  relLoadFacade          # Относительная нагрузка уличного фасада
    pr['kondiz'] = 0  #  avgHLcond              # Расчетная  тепловая нагрузка на кондиционирование
    pr['ventil'] = 0  #  calcHLventil           # Расчетная тепловая нагрузка  на вентиляцию

    pr['gvop'] = 0    #  avgHLGVSopenFlow       # Средняя тепловая нагрузка на горячее водоснабжение
    pr['gvoo'] = 0    #  avgHLGVSopenRet        # Средняя тепловая нагрузка на горячее водоснабжение
    pr['gvpr'] = 0    #  avgHLGVScloseParall    # Средняя тепловая нагрузка на горячее водоснабжение
    pr['gvsm'] = 0    #  avgHLGVScloseMix       # Средняя тепловая нагрузка на горячее водоснабжение
    pr['gvps'] = 0    #  avgHLGVScloseConseq    # Средняя тепловая нагрузка на горячее водоснабжение
    pr['gvpw'] = 0    #  avgHLGVSclosePreON     # Средняя тепловая нагрузка на горячее водоснабжение

# ----------------------------------
    
    pr['otv'] = 'Техник'   #  responsibleID  # Техник
    pr['name_building'] = 'Содержательное наименование здания'   #  name  # Содержательное наименование здания
# ----------------------------------


    pr2 = {}
# ----------------------------------
#  Расходы на ГВС заданные   
    
    pr2['G_gvps'] = 0     # 
    pr2['G_gvpw'] = 0     #  
    pr2['G_gvpr'] = 0     # 
    pr2['G_gvsm'] = 0     # 
# ----------------------------------

    el = {}

    el['a5'] = 1         # /*  5.Номер  элеватора                                                      */
#    el['a6']            # /*  6.Коэффициент смешения элеватора                                        */
#    el['d_entry']       # /*  16.Диаметр внутренний установочного фланца,мм                           */
    isEl = False

    ret, dr_out = dross(pr, pr2, pt_out, el, isEl)




#    if ret:
#        for k, v in dr_out.items():
#            w_print(k, v)

