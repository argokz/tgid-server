from sety import config
from sety.teplo.rasto import rasTO_pr2
from sety.teplo.tepl_vent import rasVENT

#PR* pr, PT_G* pt_G
def setPR(node, po, typ, debug):
    is_leto2 = 0

    pt_name = node.get('name', '??')


#    debug1 = pt_name in ('1', '2', 'ТК23')
    debug1 = False


    if debug1:
#        print('============')
#        print('===', po.get('otopl_zco', 0), pt_G.get('G_otoplz', 0))
        print(node.get('name', '??'), typ)
#        print(po)

    pt_GO = po

    pt_G_gvoo = pt_GO.get('G_gvoo', 0)
    pt_G_gvop = pt_GO.get('G_gvop', 0)
    pt_G_gvpr = pt_GO.get('G_gvpr', 0)
    pt_G_gvps = pt_GO.get('G_gvps', 0)
    pt_G_gvpw = pt_GO.get('G_gvpw', 0)
    pt_G_gvsm = pt_GO.get('G_gvsm', 0)
    pt_G_kondiz = pt_GO.get('G_kondiz', 0)
    pt_G_ot_pr = pt_GO.get('G_ot_pr', 0)
    pt_G_ot_ps = pt_GO.get('G_ot_ps', 0)
    pt_G_ot_pw = pt_GO.get('G_ot_pw', 0)
    pt_G_ot_sm = pt_GO.get('G_ot_sm', 0)
    pt_G_otopln = pt_GO.get('G_otopln', 0)
    pt_G_otoplz = pt_GO.get('G_otoplz', 0)
    pt_G_ventil = pt_GO.get('G_ventil', 0)
    pt_u_new = pt_GO.get('u_new', 0)

    if debug1:
        print('--------------------')
        print(pt_name)
        print(f'pt_G_gvoo {pt_G_gvoo}')
        print(f'pt_G_gvop {pt_G_gvop}')
        print(f'pt_G_gvpr {pt_G_gvpr}')
        print(f'pt_G_gvps {pt_G_gvps}')
        print(f'pt_G_gvpw {pt_G_gvpw}')
        print(f'pt_G_gvsm {pt_G_gvsm}')
        print(f'pt_G_kondiz {pt_G_kondiz}')
        print(f'pt_G_ot_pr {pt_G_ot_pr}')
        print(f'pt_G_ot_ps {pt_G_ot_ps}')
        print(f'pt_G_ot_pw {pt_G_ot_pw}')
        print(f'pt_G_ot_sm {pt_G_ot_sm}')
        print(f'pt_G_otopln {pt_G_otopln}')
        print(f'pt_G_otoplz {pt_G_otoplz}')
        print(f'pt_G_ventil {pt_G_ventil}')
        print(f'pt_u_new {pt_u_new}')




    pr = dict()
    pt_G = dict()


#    memset(pr, 0, sizeof(PR))
#    memset(pt_G, 0, sizeof(PT_G))

    pr['id'] = po.get('id', 0)


    pr['sost'] = po.get('sost', 0)  #  Состояние потребителя
  #  strcpy(pr['kod'], po.get('kod', 0))  #  Код расчетной схемы узла присоединения
  #  strcpy(pr['uzel'], po.get('uzel', 0))  #  Наименование узла
  #  pr['pr'] = po.get('pr', 0)  #  Признак теплопровода  узла просоединения

  #  strcpy(pr['cxema'], po.get('cxema', 0))  #  Номер расчетной схемы
  #  strcpy(pr['name_building'], po.get('name_building', 0))  #  Содержательное наименование здания
    pr['h'] = po.get('h', 0)  #  Высота здания


    # исправил 2020.04.18 

  #  pr['geodz'] = po.get('geodz', 0)  #  Геодезическая отметка низа трубы подвальной прокладки

    pr['kodur'] = po.get('kodur', 0)  #  Код удельных расходов тепло/вода
    pr['kodtr'] = po.get('kodtr', 0)  #  Код расчетных температур
  #  strcpy(pr['kod_gvs'], po.get('kod_gvs', 0))  #  Код графика суточного нагрузки ГВ
    pr['kodkv'] = po.get('kodkv', 0)  #  Код группы коэффициентов вариации
  #  pr['otn_fs'] = po.get('otn_fs', 0)  #  Относительная нагрузка уличного фасада
  #  pr['otopl_tp'] = po.get('otopl_tp_zco', 0)  #  Расчетные внутренние тепловыделения
  #  pr['dolja_vent'] = po.get('dolja_vent', 0)  #  Доля расхода воды через КУ, при отключении её по воздуху
  #  pr['kondiz'] = po.get('kondiz', 0)  #  Расчетная  тепловая нагрузка на кондиционирование
  #  pr['txz'] = po.get('txz', 0)  #  Расчетная тепловая нагрузка на технологию в закрытой системе
  #  pr['txop'] = po.get('txop', 0)  #  Расчетная нагрузка на технологию в открытой системе из подающего теплопровода
  #  pr['txoo'] = po.get('txoo', 0)  #  Расчетная нагрузка на технологию в открытой системе из обратного теплопровода

    pr['otopl_tp'] = 0  #  Расчетные внутренние тепловыделения


    if typ == 'TVV':
        pr['ventil'] = po.get('ventil_cv', 0)  #  Расчетная тепловая нагрузка  на вентиляцию
        pt_G['G_ventil'] = pt_G_ventil

    if typ == 'TKN':
        pr['ventil'] = po.get('kondiz', 0)  #  Расчетная тепловая нагрузка  на вентиляцию
        pt_G['G_kondiz'] = pt_G_kondiz

    if typ == 'TOP':
        pr['Tr_gvs'] = po.get('Tr_gvs_oo_op', 60)  #  Расчетная температура горячей воды
        pr['gvop'] = po.get('gv_op', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['rez'] = po.get('rez_op', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС

        pt_G['G_otoplz'] = pt_G_otoplz

        if pt_G['G_otoplz'] == 0:
            pt_G['G_otopln'] = pt_G_otopln

        #    pt_G['G_otoplz'] = pt_G['G_otopln'] = 0

        pt_G['G_gvop'] = pt_G_gvop

        pt_G['G_rez'] = pt_G.get('G_rez', 0)

    if typ == 'TOO':
        pr['Tr_gvs'] = po.get('Tr_gvs_oo_op', 60)  #  Расчетная температура горячей воды
        pr['gvoo'] = po.get('gv_oo', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['rez'] = po.get('rez_op', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС

        pt_G['G_otoplz'] = pt_G_otoplz

        if pt_G['G_otoplz'] == 0: 
            pt_G['G_otopln'] = pt_G_otopln

        #    pt_G['G_otoplz'] = pt_G.get('G_otopln', 0) = 0

        pt_G['G_gvoo'] = pt_G_gvoo

        pt_G['G_rez'] = pt_G.get('G_rez', 0)

    if typ == 'TPR':

        pr['gvpr'] = po.get('gv_pr', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['gvs_max'] = po.get('gvs_max_pr', 0)  #  Коэфф.часовой неравномерности нагрузки горячего водоснабжения

    #    pr['rez'] = po.get('rez_op', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
        pr['Tr_gvs'] = po.get('Tr_gvs_pr', 60)  #  Расчетная температура горячей воды
        pr['Tr_tv_co'] = po.get('Tr_tv_co_pr', 0)
        pt_G['G_gvpr'] = pt_G_gvpr

        if not is_leto2:
            if po.get('cx_co_pr', 0) == 3 : # {  # /*'Н'*/
                pr['otopln'] = po.get('otopl_pr', 0)
                pt_G['G_otopln'] = pt_G_ot_pr

            else:
                pr['otoplz'] = po.get('otopl_pr', 0)
                pt_G['G_otoplz'] = pt_G_ot_pr

        pr['otopl_tp'] = po.get('otopl_tp_pr', 0)  #  Расчетные внутренние тепловыделения

    if typ == 'TSM':
        pr['gvsm'] = po.get('gv_sm', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['gvs_max'] = po.get('gvs_max_sm', 0)  #  Коэфф.часовой неравномерности нагрузки горячего водоснабжения
    #    pr['rez'] = po.get('rez_sm', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
        pr['Tr_gvs'] = po.get('Tr_gvs_sm', 60)  #  Расчетная температура горячей воды
        pr['Tr_tv_co'] = po.get('Tr_tv_co_sm', 0)
        pt_G['G_gvsm'] = pt_G_gvsm
        if not is_leto2:
            if po.get('cx_co_sm', 0) == 3: #  /*'Н'*/
                pr['otopln'] = po.get('otopl_sm', 0)
                pt_G['G_otopln'] = pt_G_ot_sm

            else:
                pr['otoplz'] = po.get('otopl_sm', 0)
                pt_G['G_otoplz'] = pt_G_ot_sm

            pt_G['G_ot_sm'] = pt_G_ot_sm

        pr['otopl_tp'] = po.get('otopl_tp_sm', 0)  #  Расчетные внутренние тепловыделения

    if typ == 'TPS':
        pr['gvps'] = po.get('gv_ps', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['gvs_max'] = po.get('gvs_max_ps', 0)  #  Коэфф.часовой неравномерности нагрузки горячего водоснабжения
    #    pr['rez'] = po.get('rez_ps', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
        pr['Tr_gvs'] = po.get('Tr_gvs_ps', 60)  #  Расчетная температура горячей воды
        pr['Tr_tv_co'] = po.get('Tr_tv_co_ps', 0)
        pt_G['G_gvps'] = pt_G_gvps

        if not is_leto2:
            if po.get('cx_co_ps', 0) == 3: # /*'Н'*/
                pr['otopln'] = po.get('otopl_ps', 0)
                pt_G['G_otopln'] = pt_G_ot_ps
            else:
                pr['otoplz'] = po.get('otopl_ps', 0)
                pt_G['G_otoplz'] = pt_G_ot_ps

        pr['otopl_tp'] = po.get('otopl_tp_ps', 0)  #  Расчетные внутренние тепловыделения

    if typ == 'TPW':
        pr['gvpw'] = po.get('gv_pw', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
        pr['gvs_max'] = po.get('gvs_max_pw', 0)  #  Коэфф.часовой неравномерности нагрузки горячего водоснабжения
    #    pr['rez'] = po.get('rez_pw', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
        pr['Tr_gvs'] = po.get('Tr_gvs_pw', 60)  #  Расчетная температура горячей воды
        pr['Tr_tv_co'] = po.get('Tr_tv_co_pw', 0)
        pt_G['G_gvpw'] = pt_G_gvpw

        if not is_leto2:
            if po.get('cx_co_pw', 0) == 3: # ) { # /*'Н'*/
                pr['otopln'] = po.get('otopl_pw', 0)
                pt_G['G_otopln'] = pt_G_ot_pw
            else:
                pr['otoplz'] = po.get('otopl_pw', 0)
                pt_G['G_otoplz'] = pt_G_ot_pw

        pr['otopl_tp'] = po.get('otopl_tp_pw', 0)  #  Расчетные внутренние тепловыделения

    pt_G['u_new'] = pt_u_new

    otgn = otgz = 0

    if po.get('cx_co_pw', 0) == 3: #  /*'Н'*/
        otgn += pt_G_ot_pw
    else:
        otgz += pt_G_ot_pw
#        print('pw', pt_G_ot_pw)

    if po.get('cx_co_ps', 0) == 3: # {#  /*'Н'*/
        otgn += pt_G_ot_ps
    else:
        otgz += pt_G_ot_ps
#        print('ps', pt_G_ot_ps)

    if po.get('cx_co_pr', 0) == 3: # {#  /*'Н'*/
        otgn += pt_G_ot_pr
    else:
        otgz += pt_G_ot_pr
#        print('pr', pt_G_ot_pr)

    if po.get('cx_co_sm', 0) == 3: # {#  /*'Н'*/
        otgn += pt_G_ot_sm
    else:
        otgz += pt_G_ot_sm
#        print('sm', pt_G_ot_sm)

    if typ == 'TZZ':
        pr['Tr_tv_co'] = po.get('Tr_tv_co_zco', 0)  #  Расчетная температура в отапливаемых помещений
        if not is_leto2:
            pr['otoplz'] = po.get('otopl_zco', 0)  #  Расчетная нагрузка на  отопление

#            if debug1:
#                print('otgz', otgz)

            pt_G['G_otoplz'] = pt_G_otoplz - otgz
#            if pt_G_otoplz - otgz < 0:
#                print('7>>', pt_G_otoplz, otgz, '|', pt_G_ot_pr, pt_G_ot_sm, pt_G_ot_ps, pt_G_ot_pw)

            #      pr['uf'] = po.get('uf_zco', 0)

        pr['otopl_tp'] = po.get('otopl_tp_zco', 0)  #  Расчетные внутренние тепловыделения

#        if (po.get('uf_zco', 0) > 0 and po.get('cx_zco', 0) and po.get('cx_zco', 0) == 2) {
#            pr['uf'] = po.get('uf_zco', 0)



    if typ == 'TNN':
        pr['Tr_tv_co'] = po.get('Tr_tv_co_nco', 0)  #  Расчетная температура в отапливаемых помещений
        if not is_leto2:
            pr['otopln'] = po.get('otopl_nco', 0)  #  Расчетная тепловая нагрузка на  отопление, независимая схема присоединения СО
            
            
            if pt_G_otopln < otgn:
#                print('!!!', pt_G_otopln, otgn)
                pt_G['G_otopln'] = 0
            else:
                pt_G['G_otopln'] = pt_G_otopln - otgn


        pr['otopl_tp'] = po.get('otopl_tp_nco', 0)  #  Расчетные внутренние тепловыделения


    #  if (typ == 'TZZ' or (typ == 'TNN' and po.get('Tr_tv_co_zco', 0) == 0) ) {
    if typ == 'TZZ' or typ == 'TNN':
        if po.get('gv_op', 0) != 0:
            pr['gvop'] = po.get('gv_op', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
            pr['rez'] = po.get('rez_op', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
            pr['Tr_gvs'] = po.get('Tr_gvs_oo_op', 60)  #  Расчетная температура горячей воды

        if po.get('gv_oo', 0) != 0:
            pr['gvoo'] = po.get('gv_oo', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
            pr['rez'] = po.get('rez_op', 0)  #  Расчетная тепловая нагрузка на компенсацию тепловых потерь в теплопроводе циркуляционной  ГВС
            pr['Tr_gvs'] = po.get('Tr_gvs_oo_op', 60)  #  Расчетная температура горячей воды

        """
            if (po.get('ventil_cv', 0)) {
              pr['ventil'] = po.get('ventil_cv', 0)
              pr['dolja_vent'] = po.get('dolja_vent_cv', 0)
              pr['Tr_tv_cv'] = po.get('Tr_tv_cv', 0)
            }
            if (po.get('kondiz', 0)) {
              pr['kondiz'] = po.get('kondiz', 0)
              pr['dolja_vent'] = po.get('dolja_vent_cv', 0)
              pr['Tr_tv_cv'] = po.get('Tr_tv_cv', 0)
            }
        """


#    if debug:
#        print('---------> cx' ,  po.get('cx_co_pw', 0))

    pr['uf'] = 0

    if typ == 'TZZ' and po.get('cx_zco', 0) == 2: # /*'У'*/) {
        pr['uf'] = po.get('uf_zco', 0)
    #  elif (po.get('cx_nco', 0)[0] == 'Э') {
    #    pr['uf'] = po.get('uf_nco', 0)
    elif typ == 'TPR' and po.get('cx_co_pr', 0) == 1: # /*'У'*/):
        pr['uf'] = po.get('uf_zco_pr', 0)
    elif typ == 'TSM' and po.get('cx_co_sm', 0) == 1: # /*'У'*/):
        pr['uf'] = po.get('uf_zco_sm', 0)
    elif typ == 'TPS' and po.get('cx_co_ps', 0) == 1: # /*'У'*/):
        pr['uf'] = po.get('uf_zco_ps', 0)
    elif typ == 'TPW' and po.get('cx_co_pw', 0) == 1: # /*'У'*/):
        pr['uf'] = po.get('uf_zco_pw', 0)


    #  pr['uf'] = po.get('uf', 0)  #  Коэффициент  смешения  элеватора
    pr['utechp'] = po.get('utechp', 0)  #  Заданная утечка из подающего теплопровода
    pr['utecho'] = po.get('utecho', 0)  #  Заданная утечка из обратного  теплопровода


    #  pr['a24'] = po.get('a24', 0)  #  Удельный объем воды в системе отопления
  #  pr['a25'] = po.get('a25', 0)  #  Удельный объем воды в системе вентиляции
  #  pr['a13'] = po.get('a13', 0)  #  Признак ступени дросселирования
  #  pr['a15'] = po.get('a15', 0)  #  Диаметр дроссельной диафрагмы минимально допустимый
  #  pr['a14'] = po.get('a14', 0)  #  Диаметр сопла элеватора минимально допустимый
  #  pr['a17'] = po.get('a17', 0)  #  Признак температурного графика


    pr['Tr_tv_cv'] = po.get('Tr_tv_cv', 0)  #  Расчетная температура нагретого воздуха после КУ
  #  pr['pr_avtomat'] = po.get('pr_avtomat', 0)  #  Степень автоматизации


    """


      pt_G['G_otoplz'] = 0  #  Расчетная нагрузка на  отопление
      pt_G['G_otopln'] = 0  #  Расчетная нагрузка на  отопление
      pt_G['G_utechp'] = 0  #  Утечка из подающего теплопровода
      pt_G['G_utecho'] = 0  #  Утечка из обратного  теплопровода



    pt_G['G_otoplz'] = po.get('G_otoplz', 0)  #  Расчетная нагрузка на  отопление
    pt_G['G_otopln'] = po.get('G_otopln', 0)  #  Расчетная нагрузка на  отопление
    pt_G['G_ventil'] = po.get('G_ventil', 0)  #  Расчетная нагрузка  на вентиляцию
    pt_G['G_kondiz'] = po.get('G_kondiz', 0)  #  Расчетная  нагрузка на кондиционирование
    pt_G['G_gvop'] = po.get('G_gvop', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_gvoo'] = po.get('G_gvoo', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_rez'] = po.get('G_rez', 0)  #  Расчетная нагрузка на компенсацию тепловых потерь
    pt_G['G_gvpr'] = po.get('G_gvpr', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_gvsm'] = po.get('G_gvsm', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_gvps'] = po.get('G_gvps', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_gvpw'] = po.get('G_gvpw', 0)  #  Средняя тепловая нагрузка на горячее водоснабжение
    pt_G['G_utechp'] = po.utechp  #  Утечка из подающего теплопровода
    pt_G['G_utecho'] = po.utecho  #  Утечка из обратного  теплопровода


    """

    if pr.get('Tr_gvs', 0) == 0:
        pr['Tr_gvs'] = 60

    if debug1:
        print(pt_G)

    return pr, pt_G

#def rasTO_po(node, po, pt_G, G, t, double& t2, double& Qotoplz1, double& Qotopln1, double& Qvent1, double& Qkond1, double& Qgvz1, double& Qgvop1, double& Qgvoo1, double Tn):


def rasTO_po(node, po, pt_G, G, t, Tn, debug):
#t2, Qotoplz1, Qotopln1, Qvent1, Qkond1, Qgvz1, Qgvop1, Qgvoo1


    #  const PT_G *pt_GO = getPT_G(node_name(po))
#    pt_GO = getPT_G(node->node_name_potr())

    pt_name = node.get('name', '??')

#    debug1 = pt_name in ('1', '2', 'ТК23')
    debug1 = False
#    debug1 = pt_name in ('1', '2', 'ЦТП- 2')

    pt_GO = po

    pt_G_gvoo = pt_GO.get('G_gvoo', 0)
    pt_G_gvop = pt_GO.get('G_gvop', 0)
    pt_G_gvpr = pt_GO.get('G_gvpr', 0)
    pt_G_gvps = pt_GO.get('G_gvps', 0)
    pt_G_gvpw = pt_GO.get('G_gvpw', 0)
    pt_G_gvsm = pt_GO.get('G_gvsm', 0)
#    pt_G_kondiz = pt_GO.get('G_kondiz', 0)
#    pt_G_ot_pr = pt_GO.get('G_ot_pr', 0)
#    pt_G_ot_ps = pt_GO.get('G_ot_ps', 0)
#    pt_G_ot_pw = pt_GO.get('G_ot_pw', 0)
#    pt_G_ot_sm = pt_GO.get('G_ot_sm', 0)
#    pt_G_otopln = pt_GO.get('G_otopln', 0)
#    pt_G_otoplz = pt_GO.get('G_otoplz', 0)
#    pt_G_ventil = pt_GO.get('G_ventil', 0)
#    pt_u_new = pt_GO.get('u_new', 0)

    if debug1:
        print('==================')
        print(pt_name)
#        print(po)
#        exit(0)



    tg = 0
    tv = 0
    tvv = 0
    qq = 0

#    PR pr

    qq_pr = qq_ps = qq_pw = qq_sm = qq_oo = qq_op = qq_z = qq_n = qq_v = qq_k = 0
    qq_pr2 = qq_ps2 = qq_pw2 = qq_sm2 = qq_oo2 = qq_op2 = qq_z2 = qq_n2 = qq_v2 = qq_k2 = qq_rez2 = 0

    pr = {}

#    PT_G pt_G2
#    double Qotopl

    #  pt_G2.init()

    Qotoplz = Qotopln = Qvent = Qkond = Qgvz = Qgvop = Qgvoo = Qotopl = 0
    Qotoplz1 = Qotopln1 = Qvent1 = Qkond1 = Qgvz1 = Qgvop1 = Qgvoo1 = Qotopl = 0

    Got_z = 0
    Got_n = 0


    if debug1:
        print('!!!!!!!!!')


    if po.get('gv_pr', 0) != 0  or po.get('otopl_pr', 0) != 0 :

        if debug1:
            print('TPR')

        pr, pt_G2 = setPR(node, po, 'TPR', debug)
        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug)

        qq_pr = qq
        Qgvz1 += Qgvz

        if po.get('cx_co_pr', 0) == 3: #  /*'Н'*/
            Qotopln1 += Qotopl
            Got_n += pt_G2.get('G_otopln', 0)
        else:
            Qotoplz1 += Qotopl
            Got_z += pt_G2.get('G_otoplz', 0)

        qq_pr2 = t2 * (pt_G.get('G_ot_pr', 0)+pt_G.get('G_gvpr', 0))*1000


    if po.get('gv_ps', 0) != 0  or po.get('otopl_ps', 0) != 0 :

        if debug1:
            print('TPS')

        pr, pt_G2 = setPR(node, po, 'TPS', debug)
        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug)

        qq_ps = qq
        Qgvz1 += Qgvz
        if po.get('cx_co_ps', 0) == 3: #  /*'Н'*/
            Qotopln1 += Qotopl
            Got_n += pt_G2.get('G_otopln', 0)
        else:
            Qotoplz1 += Qotopl
            Got_z += pt_G2.get('G_otoplz', 0)
        qq_ps2 = t2 * (pt_G.get('G_ot_ps', 0) + pt_G.get('G_gvps', 0)) * 1000


    if po.get('gv_pw', 0) != 0 or po.get('otopl_pw', 0) != 0 :
        if debug1:
            print('TPW')


        pr, pt_G2 = setPR(node, po, 'TPW', debug)

        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug)

        qq_pw = qq
        Qgvz1 += Qgvz

        if po.get('cx_co_pw', 0) == 3: #  /*'Н'*/
            Qotopln1 += Qotopl
            Got_n += pt_G2.get('G_otopln', 0)
        else:
            Qotoplz1 += Qotopl
            Got_z += pt_G2.get('G_otoplz', 0)

        qq_pw2 = t2 * (pt_G.get('G_ot_pw', 0) + pt_G.get('G_gvpw', 0)) * 1000

    if po.get('gv_sm', 0) != 0 or po.get('otopl_sm', 0):

        if debug1:
            print('TSM')


        pr, pt_G2 = setPR(node, po, 'TSM', debug)
        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug)
        qq_sm = qq
        Qgvz1 += Qgvz
        if po.get('cx_co_sm', 0) == 3: #  /*'Н'*/
            Qotopln1 += Qotopl
            Got_n += pt_G2.get('G_otopln', 0)

        else:
            Qotoplz1 += Qotopl
            Got_z += pt_G2.get('G_otoplz', 0)

        qq_sm2 = t2*(pt_G.get('G_ot_sm', 0) + pt_G.get('G_gvsm', 0)) * 1000


    #  if (po.get('otopl_zco', 0) != 0 or po.get('otopl_nco', 0) != 0) {

    """
        if (po.get('gv_oo', 0)) {
          setPR(po, &pr, &pt_G2, TOO, debug)
          rasTO_pr2(&pr, &pt_G2, G, t, t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo, Tn, 1)
          qq_oo = qq
          Qgvoo1 += Qgvoo
          Qotoplz1 += Qotopl
        }
        if (po.get('gv_op', 0)) {
          setPR(po, &pr, &pt_G2, TOP, debug)
          rasTO_pr2(&pr, &pt_G2, G, t, t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo, Tn, 1)
          qq_op = qq
          Qgvop1 += Qgvop
          Qotoplz1 += Qotopl
        }
    """
    if po.get('ventil_cv', 0) != 0 and not config.args.is_leto:
        if debug1:
            print('TVV')


        gvent = 1000 * pt_G.get('G_ventil', 0)
    
        pr, pt_G2 = setPR(node, po, 'TVV', debug)
        
        t2v, tvv = rasVENT(pr, pt_G.get('G_ventil', 0) * 1000, pr.get('ventil', 0) * 1e6, t,  Tn, debug)

        qq_v = gvent * (t - t2v)
        Qvent1 += qq_v / 1e6

        qq_v2 = pt_G.get('G_ventil', 0) * t2v*1000

    if po.get('kondiz', 0) != 0 and not config.args.is_leto:
        gvent = 1000 * pt_G.get('G_kondiz', 0)
#        double t2v
        pr, pt_G2 = setPR(node, po, 'TKN', debug)
        t2v, tvv, = rasVENT(pr, pt_G.get('G_kondiz', 0) * 1000, pr.get('ventil', 0) * 1e6, t, Tn, debug)
        qq_k = gvent * (t - t2v)
        Qkond1 += qq_v / 1e6
        qq_k2 = pt_G.get('G_kondiz', 0) * t2v * 1000


    Ggvo = (pt_G.get('G_gvop', 0) + pt_G.get('G_gvoo', 0)) * 1000
    Got = (pt_G.get('G_otoplz', 0) + pt_G.get('G_otopln', 0))

    if Got != 0:
        d_z = pt_G.get('G_otoplz', 0) / Got
        d_n = pt_G.get('G_otopln', 0) / Got
    else:
        d_z = 0
        d_n = 0


#    double G_ot_gv = pt_G.get('G_ot_pr', 0) + pt_G.get('G_ot_sm', 0) + pt_G.get('G_ot_ps', 0) + pt_G.get('G_ot_pw', 0)




    if po.get('otopl_zco', 0) != 0 and pt_G.get('G_otoplz', 0) != 0 :
        if debug1:
            print('TZZ')

#        if debug1:
#            print('!!', po.get('otopl_zco', 0),  po.get('G_otoplz0', 0))

#            exit(0)

#        double  tvv
        pr, pt_G2 = setPR(node, po, 'TZZ', debug)
        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug1)
        qq_z = qq
        Qotoplz1 += Qotopl
#        qq_z2 = (pt_G.get('G_otoplz', 0)*1000 - pt_G.get('G', 0) * pt_G.get('G_otoplz', 0) /Got) * t2
        qq_z2 = (pt_G.get('G_otoplz', 0)- Got_z - pt_G.get('G_gvoo', 0) * d_z)*1000*t2
        


    if po.get('otopl_nco', 0) != 0  and pt_G.get('G_otopln', 0) != 0 :

        if debug1:
            print('TNN')


#        double  tvv
        pr, pt_G2 = setPR(node, po, 'TNN', debug)

        t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(node, pr, pt_G2, G, t, Tn, debug)
        qq_n = qq
        Qotopln1 += Qotopl

        qq_n2 = (pt_G.get('G_otopln', 0) - Got_n - pt_G.get('G_gvoo', 0) * d_n) * 1000 * t2

    GG = (pt_G.get('G_otoplz', 0) + pt_G.get('G_otopln', 0) + pt_G.get('G_ventil', 0) +
        pt_G.get('G_kondiz', 0) + pt_G.get('G_txz', 0) + pt_G.get('G_txop', 0) + pt_G.get('G_txoo', 0) +
        pt_G.get('G_gvpr', 0) + pt_G.get('G_gvsm', 0) + pt_G.get('G_gvps', 0) + pt_G.get('G_gvpw', 0))

    GG -= pt_G.get('G_gvoo', 0)

    #  GG*t + pt_G.get('G_gvoo', 0)*t-qq_oo


    #  GG += pt_G.get('G_gvop', 0)
    #  GG += pt_G.get('G_gvoo', 0)

    if po.get('gv_op', 0) > 0:
        GG += pt_G.get('G_rez', 0)
        qq_rez2 = t * pt_G.get('G_rez', 0) * 1000


    if config.args.is_leto:
        GG = pt_G.get('G_gvpr', 0) + pt_G.get('G_gvsm', 0) + pt_G.get('G_gvps', 0) + pt_G.get('G_gvpw', 0)

    GG *= 1000

    #  double QQ = qq_pr+qq_ps+qq_pw+qq_sm+qq_z+qq_n+qq_v+qq_k+qq_oo+qq_op
    QQ = qq_pr + qq_ps + qq_pw + qq_sm + qq_z + qq_n + qq_v + qq_k

#    t2 = t - QQ / GG

    QQ2 = qq_pr2 + qq_ps2 + qq_pw2 + qq_sm2 + qq_z2 + qq_n2 + qq_v2 + qq_k2 + qq_rez2


    if GG != 0:
        t2 = QQ2 / GG
    else:
        t2 = t


    if po.get('gv_oo', 0) != 0:
        Qgvoo1 = t2 * pt_G_gvoo / 1000
    if po.get('gv_op', 0) != 0:
        Qgvop1 = t * pt_G_gvop / 1000


    """
      if (pt_G.get('G_gvop', 0) or pt_G.get('G_gvoo', 0)) {
        QQ += (t*pt_G.get('G_gvop', 0)+t2*pt_G.get('G_gvoo', 0))*1000
        GG += (pt_G.get('G_gvop', 0)+pt_G.get('G_gvoo', 0))*1000
        t2 = t-QQ/GG
      }
    """

    #  double t2_pr = t-qq_pr/pt_G.get('gvpr', 0)
    #  double t2_ps = t-qq_pr/pt_G.get('gvps', 0)
    #  double t2_pw = t-qq_pr/pt_G.get('gvpw', 0)
    #  double t2_sm = t-qq_pr/pt_G.get('gvsm', 0)


    return t2, Qotoplz1, Qotopln1, Qvent1, Qkond1, Qgvz1, Qgvop1, Qgvoo1
