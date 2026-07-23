import numpy as np
import networkx as nx
import networkx as nx
import tempfile

import itertools

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert
from sety import read_gid

from sety import config

from sety import read_tg
from sety.ct import get_ct

from sety.teplo.rasto import rasTO_pr2
from sety.teplo.rasto_po import rasTO_po
from sety.teplo.teplo import rasTO_po2
from sety.any.colors import cprint

from sety.out.Qtreb import write_Qtreb
from sety.out.Qtreb import write_Qtreb_po

from sety.any.colors import nbsp

import consumption

def print_bal(text, v1, v2):
    if v1 is None: v1 = 0
    if v2 is None: v2 = 0
    if v1 != 0 or v2 != 0:
        s1 = f'{v1:7.2f}'
        s2 = f'{v2:7.2f}'
        if v1 == 0: s1 = ' '*7
        if v2 == 0: s2 = ' '*7

#        print(f'{len(text)} {text} ')
        s = f'  {text}, {'.'*(50-len(text))} {s1} {s2}'
        s = nbsp(s)
        cprint(s)


def n_ras(G, n, nO):
    nP = G.nodes[n]

    pt_name = nP.get('name', '???')

#    print('-----------------')
#    print(n, pt_name)

    GGG = 0
    GZ = 0

    for k, (nn1, nn2, key) in itertools.chain(
            zip(itertools.repeat(1), G.in_edges(n, keys=True)),
            zip(itertools.repeat(2), G.out_edges(n, keys=True))
            ): 

        l = G.edges[nn1, nn2, key]

        GG = l.get('G', 0)
        GGG += GG


    return GGG, GZ



def out_PT_OUT3(G, conn, calculationid, Tn, delete):

#    print('-----------------------')

    for n in G.nodes:
        nP = G.nodes[n]

        num = nP.get('num', -1)
        if num == -1:
            continue

        po = nP['po']
        typ = nP['typ']

        if typ in ('realConsumers3') and po == 1:      # 
#            G_gvpr = pr.get('G_gvpr', 0)
#            G_gvsm = pr.get('G_gvsm', 0)
#            G_gvps = pr.get('G_gvps', 0)
#            G_gvpw = pr.get('G_gvpw', 0)

             nP['G_gvpr'] = 0
             nP['G_gvps'] = 0
             nP['G_gvpw'] = 0
             nP['G_gvsm'] = 0

             nP['G_otopln'] = 0
             nP['G_otoplz'] = 0
             nP['G_ventil'] = 0
             nP['G_gvop'] = 0
             nP['G_gvoo'] = 0

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]
        GG = e.get('G', 0)

        if abs(GG) < 0.000001: GG = 0


        nodeID = e.get('nodeID_pr', -1)
        if nodeID != -1:
            typ = e.get('typ', '???')
            t = e.get('typTO', '???')

            pr = G.nodes.get((nodeID, 1), None)

#            G_gvpr = pr.get('G_gvpr', 0)
#            G_gvsm = pr.get('G_gvsm', 0)
#            G_gvps = pr.get('G_gvps', 0)
#            G_gvpw = pr.get('G_gvpw', 0)

            if not pr is None:
#                if typ in ('TO', 'EL', 'SO', 'VN'):        
#                    print(nodeID, typ, t, pr.get('name', '??'))

#                if pr.get('name', '??') == '11':
#                    print('--->', pr.get('name', '??'), typ, t, GG )
                

#                if GG < 0:
#                    print(pr.get('name'), typ, f'GG={GG:.2f}', nn1.get('name'), nn2.get('name'))
#                    exit(0)

                if GG < 0:
                    GG = 0

                if typ == 'UT':
                    if t == 43:   #  рециркуляция
                        pr['G_rez'] = GG
                    
                if typ == 'TO':
                    if t == 12: # Отопление
                        pr['G_otopln'] = GG
                        
#                    elif t == 11: # ГВС 2 ступень 
#                    elif t == 10: # ГВС 1 ступень 

                    elif t == 11 or t == 10: 
                        typ_gvs = e.get('typ_gvs', '??')

                        if typ_gvs in ('pw', 'pr'):   # Только вторая ступень 11
                            if t == 11: 
                                pr[f'G_gv{typ_gvs}'] = GG

                        if typ_gvs in ('ps', 'sm'):   # Только вторая и первая ступени
                            if t == 11: 
                                pr[f'G_gv{typ_gvs}'] = GG
                            
                                
                        '''
                        if typ_gvs in ('ps', 'pw', 'pr', 'sm'):
                            pr[f'G_gv{typ_gvs}'] = pr.get(f'G_gv{typ_gvs}', 0) + GG
                            if pr.get('name', '??') == '11':
                                print(f'G_gv{typ_gvs}', pr[f'G_gv{typ_gvs}']);
                                '''

                    else:
                        print('Ошибка! Проверьте файл b5.txt')
                        exit(0)            
                
                elif typ in ('EL', 'SO'):
                    pr['G_otoplz'] = GG
                elif typ == 'VN':
                    pr['G_ventil'] = GG
                elif typ == 'OP':
                    pr['G_gvop'] = GG
                elif typ == 'OO':
                    pr['G_gvoo'] = GG
                
            
#            nn1 = G.nodes[nodeID, ]
            
    cursor = conn.cursor()

    if delete:
        cursor.execute(f'delete from PT_OUT where calculationid={calculationid}')
        conn.commit()

    insert = Insert('PT_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('nodeid')
    insert.add_col('ist')
#    insert.add_col('externalsign')

    insert.add_col('a3')   # Содержательное наименование
    insert.add_col('a4')   # Расход на отопление, зав.сх.
    insert.add_col('a5')   # Расход на отопление, незав.сх.
    insert.add_col('a6')   # Расход на вентиляцию
    insert.add_col('a7')   # Расход на кондиционирование
    insert.add_col('a8')   # Расход на технологию в закр.сист.
    insert.add_col('a9')   # Расход на техн. из под.теплопр. в откр сист.
    insert.add_col('a10')   # Расход на техн. из обр.теплопр. в откр.cистеме
    insert.add_col('a11')   # Расход  на ГВ в закрытой системе
    insert.add_col('a12')   # Расход на ГВ из под.трубопр. в откр.системе
    insert.add_col('a13')   # Расход  на ГВ из обр.теплопр. в откр.системе
    insert.add_col('a14')   # Расход в циркуляционном теплопроводе ГВС
    insert.add_col('a15')   # Суммарный расход  в закрытой системе
    insert.add_col('a16')   # Суммарный расход  из под.трубопр. в откр.системе
    insert.add_col('a17')   # Суммарный расход потребителя из обр.теплопр. в откр.системе
    insert.add_col('a18')   # Относительный расход сетевой воды в закрытой системе
    insert.add_col('a19')   # Заданное значение утечки из подающего теплопровода
    insert.add_col('a20')   # Заданное значение утечки из обратного теплопровода
    insert.add_col('a21')   # Пьезометрический напор в подающем теплопроводе
    insert.add_col('a22')   # Пьезометрический напор в обратном теплопроводе
    insert.add_col('a23')   # Располагаемый напор в узле присоединения потребителя
    insert.add_col('Gsm')   # Расход сет.воды в СО после узла смешения
    insert.add_col('Gm')   # Расход воды на входе мест. СО, незав.присоед.
    insert.add_col('Gx')   # Расход водопроводной воды в закрытой ГВС
    insert.add_col('Ggws')   # Расход сет.воды на вторую ступень закрытой ГВС
    insert.add_col('t1')   # Температура сет.воды на входе теплового пункта
    insert.add_col('t2')   # Температура сет.воды на выходе теплового пункта
    insert.add_col('t01')   # Температура в подающем теплопроводе СО
    insert.add_col('t02')   # Температура в обратном теплопроводе СО
    insert.add_col('t03')   # Температура после узла смешения в СО
    insert.add_col('t2co')   # Температура сет.воды на выходе подогревателя СО
    insert.add_col('t2gws')   # Температура сет.воды на вых.подогревателя 2 ст.ГВС
    insert.add_col('tv')   # Температура внутри отапливаемых помещений
    insert.add_col('tg')   # Горячая вода на выходе водоразб.приборов в ГВС
    insert.add_col('dop8')   # Темп.нагретого воздуха в системе вентиляции
    insert.add_col('dop9')   # Темп. нагретого воздуха в системе кондиционирования
    insert.add_col('Qotz')   # Тепл.нагрузка  на отопление, зав.сх.
    insert.add_col('Qotn')   # Тепл.нагрузка  на отопление, незав.сх.
    insert.add_col('dop12')   # Тепловая нагрузка потребителя на вентиляцию
    insert.add_col('dop13')   # Тепл.нагрузка на кондиционирование
    insert.add_col('dop14')   # Тепл.нагрузка на технологию в закрытой системе
    insert.add_col('dop15')   # Тепл.нагрузка на техн. из под.теплопр. в откр.сист.
    insert.add_col('dop16')   # Тепл.нагрузка на техн. из обр.теплопр. в откр. сист.
    insert.add_col('dop17')   # Тепл.нагрузка на ГВ в закрытой системе
    insert.add_col('dop18')   # Тепл.нагрузка на ГВ из под.теплопр. в откр.сист.
    insert.add_col('dop19')   # Тепл.нагрузка на ГВ из обр.теплопр. в откр.сист.
    insert.add_col('dop20')   # Тепл.нагрузка в цирк.теплопроводе ГВС
    insert.add_col('Qsum_z')   # Суммарная тепл.нагрузка  в закрытой системе
    insert.add_col('dop22')   # Сумм.тепл.нагрузка  из под.теплопр.в откр.системе
    insert.add_col('dop23')   # Сумм.тепл.нагрузка  из обр.теплопр.в откр.системе
    insert.add_col('Gneob')   # Необходимый располагаемый напор
    insert.add_col('Qras_gv_z')   # Расчетная тепловая нагрузка в закрытых ГВС
    insert.add_col('Qotz_treb')   # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,зав.схема
    insert.add_col('Qotn_treb')   # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,незав.схема
    insert.add_col('Qvent_treb')   # Требуемый расход тепла на вентиляцию при текущей температуре наружного воздуха
    insert.add_col('Qgvz_treb')   # Требуемый расход тепла  на горячее водоснабжение  в закрытой системе
    insert.add_col('Qgvop_treb')   # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из под.трубопр.
    insert.add_col('Qgvoo_treb')   # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из обр.трубопр.
    insert.add_col('Qrez_treb')   # Требуемый расход тепла на рециркуляцию в  в открытой системе ГВ
    insert.add_col('Qtreb')   # Суммарный требуемый расход тепла в системах теплопотребления теплового пункта
    insert.add_col('Qfact')   # Суммарная тепловая нагрузка систем теплопотребления
    insert.add_col('Q_obesp_min')   # Суммарная теплообеспеченность
    insert.add_col('Q_obesp_otopl_min')   # Теплообеспеченность отопительной нагрузки
    insert.add_col('Q_obesp_gvs_min')   # Теплообеспеченность нагрузки горячего водоснабжения
    insert.add_col('b101')   #  Коэффициент смешения элеватора
    insert.add_col('b102')   #  Температура воздуха

    ct = get_ct()
    Tn_otop = ct.get('t_or')

    G_otoplz0 = 0
    G_otopln0 = 0
    G_ventil0 = 0

    Q_otoplz0 = 0
    Q_otopln0 = 0
    Q_ventil0 = 0

    G_gvz0 = 0
    Q_gvz0 = 0
    Q_rez0 = 0

    Qgvz = 0
    G_gvz = 0
    G_rez = 0

    for n in G.nodes:
        nP = G.nodes[n]

        num = nP.get('num', -1)
        if num == -1:
            continue

        id = nP['id']
        typ = nP['typ']

        po = nP['po']
        pih = nP.get('P', 0.)
        t = 0
        t2 = 0

        if typ in ('realConsumers3') and po == 1:      # 

            nO = G.nodes.get((id, 2), None)
            out = nP

            t = nP.get('t', -10000)
            t2 = nO.get('t', -10000)

            GP, GZ1 = n_ras(G, (id, 1), (id, 2))
            GO, GZ2 = n_ras(G, (id, 2), (id, 1))

            if abs(GP) < 1e-8 and abs(GO):
#            if abs(GP) < 1e-8 or abs(GO) < 1e-8:
#                print(nP.get('name', '???'), GP, GO, GZ1, GZ2)
#                exit(0)
                continue


#            rasz = 

#            a4 = (ado, fabs(pt_G->G_otoplz * x[l->n] / rasz))
#            a5 = (ado, fabs(pt_G->G_otopln * x[l->n] / rasz))

            if True:
                G_txz = out.get('G_txz', 0)
                G_rez = out.get('G_rez', 0)

                G_gvpr = out.get('G_gvpr', 0)
                G_gvsm = out.get('G_gvsm', 0)
                G_gvps = out.get('G_gvps', 0) # - (G_otopln + G_otoplz)
                G_gvpw = out.get('G_gvpw', 0) # - (G_otopln + G_otoplz)

                G_otoplz = out.get('G_otoplz', 0)
                G_otopln = out.get('G_otopln', 0)

                G_ventil = out.get('G_ventil', 0)
                G_kondiz = out.get('G_kondiz', 0)

                if G_otoplz > 0.00001:
                    G_otoplz -= (G_gvps+G_gvpw)
                if G_otopln > 0.00001:
                    G_otopln -= (G_gvps+G_gvpw)

            else:
                G_txz = out.get('G_txz', 0)
                G_rez = out.get('G_rez', 0)

                G_gvpr = out.get('G_gvpr', 0)
                G_gvsm = out.get('G_gvsm', 0)
                G_gvps = out.get('G_gvps', 0)
                G_gvpw = out.get('G_gvpw', 0)

                G_otoplz = out.get('G_otoplz', 0)
                G_otopln = out.get('G_otopln', 0)

                G_ventil = out.get('G_ventil', 0)
                G_kondiz = out.get('G_kondiz', 0)


            G_gvz = G_gvpr + G_gvsm + G_gvps + G_gvpw


#            print(f'{nP.get('name', '???')} G_gvz = {G_gvz}')
#            print(f'{G_gvz} = {G_gvpr} + {G_gvsm} + {G_gvps} + {G_gvpw}')

            G_gvop = out.get('G_gvop', 0)
            G_gvoo = out.get('G_gvoo', 0)

            heatSourceID = nP.get('heatSourceID', 0)

            ras_z = (G_otoplz + G_otopln + G_ventil + G_kondiz + G_txz +
                   G_gvpr + G_gvsm + G_gvps + G_gvpw)

            if G_gvop > 0:
                ras_z += G_rez


            ras_p = G_gvop
            ras_o = G_gvoo

            pihP = nP.get('P', 0.)
            pihO = nO.get('P', 0.)

            GG = ras_z
            debug1 = False

            if ras_z == 0 and ras_o == 0 and ras_p == 0:
#                print('!!!>>>>>>>>>>>>', nP.get('name'), ras_z, ras_o, ras_p)
                continue


            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('nodeid', id)
#            insert.db_write('externalsign', po)
            insert.db_write('ist', heatSourceID)


            if True:
#                print(nP.get('name'), '!!1', t)
                t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(nP, nP, nP, GG, t, Tn, debug1)

#                print(nP.get('name'), '!!2')

                cxema = nP.get('cxema', '1.1')
                vv = consumption.type_of_cons(cxema)

                if Qotopl is None:
                    print(cxema, Qotopl, vv)

                if vv:
                    otop, vent, gv, rez, isEl = vv
                    if otop == 'n':
                        Qotopln = Qotopl
                        Qotoplz = 0
                    else:
                        Qotopln = 0
                        Qotoplz = Qotopl
                else:
                    print(cxema, Qotopl, vv)



            Qsum_z = None

            Qrez = 0

            if True:
                if nP.get('gvop', 0) > 0:
                    tt = (nP.get('Tr_gvs', 0) - ct.get('tx', 5)) - nP.get('T_pot_rez', 0)
                    Qrez = abs(G_rez * tt / 1000)

            if not Qotopl is None:
                Qsum_z = Qotopl + Qvent + Qkond + Qgvz
                Qfact = Qotopl + Qvent + Qkond + Qgvz + Qgvop + Qgvoo + Qrez

#                print(f'{Qfact} = {Qotopl} + {Qvent} + {Qkond} + {Qgvz} + {Qgvop} + {Qgvoo}')
                
                nP['Qotopl'] = Qotopl
                nP['Qvent'] = Qvent
                nP['Qkond'] = Qkond
                nP['Qgvz'] = Qgvz

                nP['Qgvop'] = Qgvop
                nP['Qgvoo'] = Qgvoo
                nP['Qsum_z'] = Qsum_z
                nP['Qfact'] = Qfact

            nP['G_gvz'] = G_gvz
            nP['G_rez'] = G_rez
            nP['a14'] = G_rez

#            if nP.get('name', '???') == '6.2':
#                print(G_rez)


#            print('>>>>>>>>>>>>', nP.get('name'), G_ventil)
#            exit(0)


            geodez = nP.get('geoMarkTopTube', 0)

            insert.db_write('a3', nP.get('name_building', ''))   # Содержательное наименование
            insert.db_write('a4', G_otoplz)   # + Расход на отопление, зав.сх.
            insert.db_write('a5', G_otopln)   # + Расход на отопление, незав.сх.
            insert.db_write('a6', G_ventil)   # + Расход на вентиляцию
            insert.db_write('a7', G_kondiz)   # + Расход на кондиционирование
            insert.db_write('a8')   # ----- Расход на технологию в закр.сист.
            insert.db_write('a9')   # ----- Расход на техн. из под.теплопр. в откр сист.
            insert.db_write('a10')   # ----- Расход на техн. из обр.теплопр. в откр.cистеме
            insert.db_write('a11', G_gvz)   # + Расход на ГВ в закрытой системе
            insert.db_write('a12', G_gvop)   # + Расход на ГВ из под.трубопр. в откр.системе
            insert.db_write('a13', G_gvoo)   # + Расход на ГВ из обр.теплопр. в откр.системе
            insert.db_write('a14', G_rez)   # + Расход в циркуляционном теплопроводе ГВС
            insert.db_write('a15', ras_z)   # + Суммарный расход в закрытой системе
            insert.db_write('a16', ras_p)   # + Суммарный расход из под.трубопр. в откр.системе
            insert.db_write('a17', ras_o)   # + Суммарный расход потребителя из обр.теплопр. в откр.системе
            insert.db_write('a18')   # Относительный расход сетевой воды в закрытой системе
            insert.db_write('a19')   # Заданное значение утечки из подающего теплопровода
            insert.db_write('a20')   # Заданное значение утечки из обратного теплопровода
            insert.db_write('a21', pihP)   # + Пьезометрический напор в подающем теплопроводе
            insert.db_write('a22', pihO)   # + Пьезометрический напор в обратном теплопроводе
            insert.db_write('a23', pihP-pihO)   # + Располагаемый напор в узле присоединения потребителя
            insert.db_write('Gsm')   # Расход сет.воды в СО после узла смешения
            insert.db_write('Gm')   # Расход воды на входе мест. СО, незав.присоед.
            insert.db_write('Gx')   # Расход водопроводной воды в закрытой ГВС
            insert.db_write('Ggws')   # Расход сет.воды на вторую ступень закрытой ГВС

#            Qrez = 0

            if t != -10000:
                insert.db_write('t1', t)   # Температура сет.воды на входе теплового пункта

            if t > 0:  # Не писать если не считали теплп
#                insert.db_write('t1', t)   # Температура сет.воды на входе теплового пункта
                insert.db_write('t2', t2)   # Температура сет.воды на выходе теплового пункта
# - Это в 
                insert.db_write('t01')   # Температура в подающем теплопроводе СО
                insert.db_write('t02')   # Температура в обратном теплопроводе СО
                insert.db_write('t03')   # Температура после узла смешения в СО

                insert.db_write('t2co')   # Температура сет.воды на выходе подогревателя СО
                insert.db_write('t2gws')   # Температура сет.воды на вых.подогревателя 2 ст.ГВС
                insert.db_write('tv', tv)   # Температура внутри отапливаемых помещений
                insert.db_write('tg', tg)   # Горячая вода на выходе водоразб.приборов в ГВС

                insert.db_write('dop8', tvv)   # Темп.нагретого воздуха в системе вентиляции
                insert.db_write('dop9')   # Темп. нагретого воздуха в системе кондиционирования
                insert.db_write('Qotz', Qotoplz)   # Тепл.нагрузка  на отопление, зав.сх.
                insert.db_write('Qotn', Qotopln)   # Тепл.нагрузка  на отопление, незав.сх.

                nP['Qotz'] = Qotoplz
                nP['Qotn'] = Qotopln
                nP['dop12'] = Qvent
                nP['dop13'] = Qkond
                nP['Qrez'] = Qrez

                nP['dop17'] = Qgvz   # Тепл.нагрузка на ГВ в закрытой системе
                nP['dop18'] = Qgvop   # Тепл.нагрузка на ГВ из под.теплопр. в откр.сист.
                nP['dop19'] = Qgvoo   # Тепл.нагрузка на ГВ из обр.теплопр. в откр.сист.
#               nP['dop20')   # Тепл.нагрузка в цирк.теплопроводе ГВС
                nP['Qsum_z'] = Qsum_z   # Суммарная тепл.нагрузка  в закрытой системе

#pt_out['Qrez_treb']
#pt_out['Qras_gv_z']

                insert.db_write('dop12', Qvent)   # Тепловая нагрузка потребителя на вентиляцию
                insert.db_write('dop13', Qkond)   # Тепл.нагрузка на кондиционирование
                insert.db_write('dop14')   # Тепл.нагрузка на технологию в закрытой системе
                insert.db_write('dop15')   # Тепл.нагрузка на техн. из под.теплопр. в откр.сист.
                insert.db_write('dop16')   # Тепл.нагрузка на техн. из обр.теплопр. в откр. сист.
                insert.db_write('dop17', Qgvz)   # Тепл.нагрузка на ГВ в закрытой системе
                insert.db_write('dop18', Qgvop)   # Тепл.нагрузка на ГВ из под.теплопр. в откр.сист.
                insert.db_write('dop19', Qgvoo)   # Тепл.нагрузка на ГВ из обр.теплопр. в откр.сист.
                insert.db_write('dop20', Qrez)   # Тепл.нагрузка в цирк.теплопроводе ГВС
                insert.db_write('Qsum_z', Qsum_z)   # Суммарная тепл.нагрузка  в закрытой системе
                insert.db_write('dop22', Qgvop)   # Сумм.тепл.нагрузка  из под.теплопр.в откр.системе
                insert.db_write('dop23', Qgvoo)   # Сумм.тепл.нагрузка  из обр.теплопр.в откр.системе

                if typ in ('realConsumers'):      # 
                    nP = write_Qtreb(nP, nP, Tn)
                if typ in ('generalizedConsumers'):      # 
                    nP = write_Qtreb_po(nP, nP, Tn)


#                insert.db_write('Gneob', nP.get('Gneob', 0))   # Необходимый располагаемый напор
                insert.db_write('Qotz_treb', nP.get('Qotz_treb', 0))   # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,зав.схема
                insert.db_write('Qotn_treb', nP.get('Qotn_treb', 0))   # Требуемый расход тепла на отопление при текущей температуре наружного воздуха,незав.схема
                insert.db_write('Qvent_treb', nP.get('Qvent_treb', 0))   # Требуемый расход тепла на вентиляцию при текущей температуре наружного воздуха
                insert.db_write('Qgvz_treb', nP.get('Qgvz_treb', 0))   # Требуемый расход тепла  на горячее водоснабжение  в закрытой системе
                insert.db_write('Qgvop_treb', nP.get('Qgvop_treb', 0))   # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из под.трубопр.
                insert.db_write('Qgvoo_treb', nP.get('Qgvoo_treb', 0))   # Требуемый расход тепла  на горячее водоснабжение  в открытой системе из обр.трубопр.
                insert.db_write('Qrez_treb')   # Требуемый расход тепла на рециркуляцию в  в открытой системе ГВ


                insert.db_write('Gneob', nP.get('Gneob', 0))   # Необходимый располагаемый напор

                insert.db_write('Qras_gv_z', nP.get('Qras_gv_z', 0))   # Расчетная тепловая нагрузка в закрытых ГВС

                insert.db_write('Qtreb', nP.get('Qtreb', 0))   # Суммарный требуемый расход тепла в системах теплопотребления теплового пункта
                insert.db_write('Qfact', Qfact)   # Суммарная тепловая нагрузка систем теплопотребления

#                Q_obesp_min = nP.get('Qfact', 0) * 100 / nP.get('Qtreb', 0)
#                Q_obesp_otopl_min = (nP.get('Qotz', 0) + nP.get('Qotn', 0) + nP.get('dop12', 0) + nP.get('dop13', 0)) / (nP.get('Qotz_treb', 0) + nP.get('Qotn_treb', 0) + nP.get('Qvent_treb', 0)) * 100
#                Q_obesp_gvs_min = (nP.get('dop18', 0) + nP.get('dop19', 0) + nP.get('dop20', 0) + nP.get('dop17', 0)) / (nP.get('Qgvz_treb', 0) + nP.get('Qgvop_treb', 0) + nP.get('Qgvoo_treb', 0) + nP.get('Qrez_treb', 0)) * 100
                
#                print(f'---{nP.get('Q_obesp_min', 0)}')

                insert.db_write('Q_obesp_min', nP.get('Q_obesp_min', 0))   # Суммарная теплообеспеченность
                insert.db_write('Q_obesp_otopl_min', nP.get('Q_obesp_otopl_min', 0))   # Теплообеспеченность отопительной нагрузки
                insert.db_write('Q_obesp_gvs_min', nP.get('Q_obesp_gvs_min', 0))   # Теплообеспеченность нагрузки горячего водоснабжения

            ut = nP.get('ut', 2.2)

            v_ot = read_tg.get_tg(heatSourceID, Tn_otop)
            if not v_ot is None:
                tv1, tv2, tv3, tv = v_ot
                ut = (tv1 - tv3) / (tv3 - tv2)


    #        insert.db_write('pih', pih)      # Пьезометрический напор       
            if t != -10000:  # Не писать если не считали теплп
                insert.db_write('t1', t)             # Температура сетевой воды     
                insert.db_write('t2', t2)            #                              
            

            insert.db_write('b101', ut)   # Коэффициент смешения элеватора
            if not config.args.is_leto:
                insert.db_write('b102', config.args.Tn)   #

            insert.db_insert_vals()


            G_otoplz0 += G_otoplz
            G_otopln0 += G_otopln
            G_ventil0 += G_ventil
            Q_otoplz0 += Qotoplz
            Q_otopln0 += Qotopln
            Q_ventil0 += Qvent

            G_gvz0 += G_gvz
            Q_gvz0 += Qgvz
            Q_rez0 += Qrez


    insert.exec()



