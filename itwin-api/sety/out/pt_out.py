import numpy as np
import networkx as nx
import networkx as nx
import tempfile
import math
import re


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
from sety.teplo.teplo1 import rasTO_po2
from sety.any.colors import cprint

from sety.out.Qtreb import write_Qtreb
from sety.out.Qtreb import write_Qtreb_po

from sety.any.colors import nbsp

import consumption
from consumption import get_pt_name

def soprPT(dH, G):
    if dH < 0 and G <= 0: return 0
#    if dH < 0: return abs(getGlobal()->dH_zero) / G / G

    sopr = 0 if G == 0 else abs(dH) / G / G
    return sopr



def make_sql_potr(potr_name, sopr_pr):
    
    s_uf = ''
    if config.args.is_save_uf_new and config.args.is_tg and potr_name == 'realconsumers':
        s_uf = 'mixFactCoeff = t.uf,'

    if sopr_pr == '': return None

    if config.args.rdbms == 'MsSql':
        q = f'''
UPDATE {potr_name}
set 

{s_uf}

hydroResCloseSys = 
case when closeSysCalcSignID <> 2 then t.s1
else hydroResCloseSys
end,

hydroResCloseSysSummer =
case when closeSysCalcSignID <> 2 then t.s1l
else hydroResCloseSysSummer
end,

hydroResWDOFlow = 
case when calcSignOpenSysFlowID <> 2 then t.s2
else hydroResWDOFlow
end,

hydroResWDORet = 
case when calcSignResWDORetID <> 2 then t.s3
else hydroResWDOFlow
end

from {potr_name} rc
join 
from
(
select * from (
values {sopr_pr}
) _t (id, s1, s1l, s2, s3, ut)
) t where {potr_name}.id=t.id
        '''


    elif config.args.rdbms == 'postgreSQL':
        q = f'''
UPDATE {potr_name}
set 

{s_uf}

hydroResCloseSys = 
case when closeSysCalcSignID <> 2 then t.s1
else hydroResCloseSys
end,

hydroResCloseSysSummer =
case when closeSysCalcSignID <> 2 then t.s1l
else hydroResCloseSysSummer
end,

hydroResWDOFlow = 
case when calcSignOpenSysFlowID <> 2 then t.s2
else hydroResWDOFlow
end,

hydroResWDORet = 
case when calcSignResWDORetID <> 2 then t.s3
else hydroResWDOFlow
end,

calcExpendDep = t.calcExpendDep,
calcExpendIndep = t.calcExpendIndep,
calcExpendVentil = t.calcExpendVentil,
calcExpendCond = t.calcExpendCond,
calcExpendHWFlow = t.calcExpendHWFlow,
calcExpendHWRet = t.calcExpendHWRet,
calcExpendRecircOpen = t.calcExpendRecircOpen,
calcExpendHWparall = t.calcExpendHWparall,
calcExpendHWmix = t.calcExpendHWmix,
calcExpendHWconseq = t.calcExpendHWconseq,
calcExpendHWpreON = t.calcExpendHWpreON


--from {potr_name} rc
--join 
from
(
select * from (
values {sopr_pr}
) _t (id, s1, s1l, s2, s3, ut

,calcExpendDep   -- Расчетный расход на  отопление
,calcExpendIndep   -- Расчетный расход на  отопление
,calcExpendVentil   -- Расчетный расход на  вентиляцию
,calcExpendCond   -- Расчетный расход на  кондиционирование
,calcExpendHWFlow   -- Расчетный расход на горячее водоснабжение
,calcExpendHWRet   -- Расчетный расход на ГВС, в открытой системе
,calcExpendRecircOpen   -- Расчетный расход на рециркуляцию в открытой ГВС
,calcExpendHWparall   -- Расчетный расход на горячее водоснабжение
,calcExpendHWmix   -- Расчетный расход на горячее водоснабжение
,calcExpendHWconseq   -- Расчетный расход на горячее водоснабжение
,calcExpendHWpreON   -- Расчетный расход на горячее водоснабжение



)
) t where {potr_name}.id=t.id
        '''

    return q


def print_bal(text, v1, v2):
    if v1 is None: v1 = 0
    if v2 is None: v2 = 0
    if v1 != 0 or v2 != 0:
        s1 = f'{v1:8.1f}'
        s2 = f'{v2:8.1f}'
        if v1 == 0: s1 = ' '*8
        if v2 == 0: s2 = ' '*8

#        clean = re.sub(r"<[^>]+>", "", text)
        clean = re.sub(r"</?[A-Za-z][^>]*>", "", text)

#        print(f'{len(text)} {text} ')
        s = f'  {text}, {'.'*(50-len(clean))} {s1} {s2}'
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



def out_PT_OUT(G, conn, calculationid, Tn):
    
    cursor = conn.cursor()
    
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


    n_pt_negat = 0
    n_pt_negat_max = 10


    sopr_po = ''
    sopr_pr = ''
    sopr_po_pr = ''

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

        if typ in ('generalizedConsumers', 'realConsumers') and po == 1:      # 
            nO = G.nodes.get((id, 2), None)
            out = nP

            t = nP.get('t', -10000)
            t2 = nO.get('t', -10000)

            GP, GZ1 = n_ras(G, (id, 1), (id, 2))
            GO, GZ2 = n_ras(G, (id, 2), (id, 1))

            if abs(GP) < 1e-8 and abs(GO) < 1e-8:
#            if abs(GP) < 1e-8 or abs(GO) < 1e-8:
#                print(nP.get('name', '???'), 'Без нагрузки')
                continue

            id2 = nP['id2']

            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('nodeid', id)
#            insert.db_write('externalsign', po)

#            rasz = 

#            a4 = (ado, fabs(pt_G->G_otoplz * x[l->n] / rasz))
#            a5 = (ado, fabs(pt_G->G_otopln * x[l->n] / rasz))
            pt_G = nP

            G_otoplz = out.get('G_otoplz', 0)
            G_otopln = out.get('G_otopln', 0)
            G_ventil = out.get('G_ventil', 0)
            G_kondiz = out.get('G_kondiz', 0)
            
            G_txz = out.get('G_txz', 0)
            G_rez = out.get('G_rez', 0)

            G_gvpr = out.get('G_gvpr', 0)
            G_gvsm = out.get('G_gvsm', 0)
            G_gvps = out.get('G_gvps', 0)
            G_gvpw = out.get('G_gvpw', 0)

            G_gvz = G_gvpr + G_gvsm + G_gvps + G_gvpw

#            print(f'{nP.get('name', '???')} G_gvz = {G_gvz}')
#            print(f'{G_gvz} = {G_gvpr} + {G_gvsm} + {G_gvps} + {G_gvpw}')

            G_gvop = out.get('G_gvop', 0)
            G_gvoo = out.get('G_gvoo', 0)

            heatSourceID = nP.get('heatSourceID', 0)
            insert.db_write('ist', heatSourceID)

            ras_z = (G_otoplz + G_otopln + G_ventil + G_kondiz + G_txz +
                   G_gvpr + G_gvsm + G_gvps + G_gvpw)

            if G_gvop > 0:
                ras_z += G_rez



            ras_p = G_gvop
            ras_o = G_gvoo

            pihP = nP.get('P', 0.)
            pihO = nO.get('P', 0.)

            raspol = pihP-pihO

            pt_name = w_print.node_name(G, n, False, True) 

            if pihP < pihO:
#                pt_name = get_pt_name(nP)
#                pt_name = w_print.node_name(G, n, False, False) 
                pt_name = w_print.node_name(G, n, False, True) 
                if n_pt_negat < n_pt_negat_max:
                    cprint(f'Располагаемый напор потребителя {pt_name} - отрицателен  {raspol}', color='red');

                n_pt_negat += 1



            sopr_l = 0
            sopr_z = 0
            sopr_p = 0
            sopr_o = 0

            GG = ras_z
            debug1 = False

            if typ =='realConsumers':

                t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = rasTO_pr2(nP, nP, nP, GG, t, Tn, debug1)

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


#                print('r', t2, qq, tg, tv, tvv, Qotopl, Qvent, Qkond, Qgvz, Qgvop, Qgvoo)
            else:
                qq, tg, tv, tvv = None, None, None, None
                vv = rasTO_po2(nP, GG, t, Tn, debug1)
                t2, Qotoplz, Qotopln, Qvent, Qkond, Qgvz, Qgvop, Qgvoo = vv

                if not Qotoplz is None and not Qotopln is None:
                    Qotopl = Qotoplz + Qotopln



            Qsum_z = None

            Qrez = 0

            if typ =='realConsumers':
                if nP.get('gvop', 0) > 0:
                    tt = (nP.get('Tr_gvs', 0) - ct.get('tx', 5)) - nP.get('T_pot_rez', 0)
                    Qrez = abs(G_rez * tt / 1000)
            else:
                if nP.get('gv_op', 0) > 0:
                    tt = (nP.get('Tr_gvs_oo_op',0) - ct.get('tx', 5)) - nP.get('T_pot_rez_op', 0)
                    Qrez = abs(G_rez * tt / 1000);


            Qfact = 0

            if not Qotopl is None and Qotopl > 0:
                Qsum_z = Qotopl + Qvent + Qkond + Qgvz     + Qrez   # !!!!!!!!!!
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

#            print(f'{nP.get('name', '???')} rez = {G_rez}')


#            nP['a14'] = G_rez

            nP['Gz'] = ras_z

#            if nP.get('name', '???') == '6.2':
#                print(G_rez)


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

#                print(heatSourceID, Tn_otop, tv1, tv2, tv3, tv)

                if tv3 == tv2:
                    ut = 0
                else:
                    ut = (tv1 - tv3) / (tv3 - tv2)
#                print(f'===({tv1}-{tv3})/({tv3}-{tv2}) =  {(tv1 - tv3) / (tv3 - tv2)}==')

            if ras_z != 0:
                sopr_z = (pihP-pihO)/(ras_z ** 2)
                if sopr_z < 0: sopr_z = 0

            if ras_p != 0:
                sopr_p = (pihP+geodez)/(ras_p ** 2)
                if sopr_p < 0: sopr_p = 0

            if ras_o != 0:
                sopr_o = (pihO+geodez)/(ras_o ** 2)
                if sopr_o < 0: sopr_o = 0


#            pt->pP = x[n1->nP] - n1->h
#            pt->pO = x[n2->nP] - n1->h

#            print('z', f'{sopr_z} = {(pihP-pihO)}/({ras_z} ** 2)')


            dP = pihP-pihO

#            print(dP, pt_G.get('G_gvps', 0), pt_G.get('G_ot_ps', 0))


            if typ == 'realConsumers':
                dP_ps = nP.get('a22', 0) + nP.get('a23', 0)
                dP_pw = nP.get('a23', 0)
            else:
                dP_ps = dP
                dP_pw = dP
                dP_ps = 8
                dP_pw = 4

            Sps_l = soprPT(dP_ps, pt_G.get('G_gvps', 0) + pt_G.get('G_ot_ps', 0))

#            print('l', Sps_l, f'dP= {dP} {pt_G.get('G_gvps', 0)} + {pt_G.get('G_ot_ps', 0)}')
#            exit(1)



            Spw_l = soprPT(dP_pw, pt_G.get('G_gvpw', 0) + pt_G.get('G_ot_pw', 0))
            Ssm_l = soprPT(dP, pt_G.get('G_gvsm', 0) + pt_G.get('G_ot_sm', 0))

            Spr_l = soprPT(dP, pt_G.get('G_gvpr', 0))
            Soo_l = soprPT(dP, pt_G.get('G_rez', 0))

            q = 0
            if Sps_l > 0: q += 1. / math.sqrt(Sps_l)
            if Spw_l > 0: q += 1. / math.sqrt(Spw_l)
            if Spr_l > 0: q += 1. / math.sqrt(Spr_l)
            if Ssm_l > 0: q += 1. / math.sqrt(Ssm_l)
            if pt_G.get('G_rez', 0) > 0 and Soo_l > 0:
                q += 1. / math.sqrt(Soo_l)

            sopr_l = 0
            if q > 0: 
                sopr_l = 1. / pow(q, 2.)

#            if typ == 'generalizedConsumers':
#                if sopr_po != '': sopr_po += ',\n'
#                sopr_po += f'({id2}, {sopr_z}, {sopr_l}, {sopr_p}, {sopr_o}, {ut})'
#            if typ == 'realConsumers':
#                if sopr_pr != '': sopr_pr += ',\n'
#                sopr_pr += f'({id2}, {sopr_z}, {sopr_l}, {sopr_p}, {sopr_o}, {ut})'


            if typ in ('realConsumers', 'generalizedConsumers'):
                sopr_po_pr = f'({id2}, {sopr_z}, {sopr_l}, {sopr_p}, {sopr_o}, {ut}'
                sopr_po_pr += f',{G_otoplz}'  # Расчетный расход на  отопление
                sopr_po_pr += f',{G_otopln}'  # Расчетный расход на  отопление
                sopr_po_pr += f',{G_ventil}'  # Расчетный расход на  вентиляцию
                sopr_po_pr += f',{G_kondiz}'  # Расчетный расход на  кондиционирование
                sopr_po_pr += f',{G_gvop}'  # Расчетный расход на горячее водоснабжение
                sopr_po_pr += f',{G_gvoo}'  # Расчетный расход на ГВС, в открытой системе
                sopr_po_pr += f',{G_rez}'  # Расчетный расход на рециркуляцию в открытой ГВС
                sopr_po_pr += f',{G_gvpr}'  # Расчетный расход на горячее водоснабжение
                sopr_po_pr += f',{G_gvsm}'  # Расчетный расход на горячее водоснабжение
                sopr_po_pr += f',{G_gvps}'  # Расчетный расход на горячее водоснабжение
                sopr_po_pr += f',{G_gvpw}'  # Расчетный расход на горячее водоснабжение

                sopr_po_pr += ')'

            if typ == 'generalizedConsumers':
                if sopr_po != '': sopr_po += ','
                sopr_po += sopr_po_pr
            if typ == 'realConsumers':
                if sopr_pr != '': sopr_pr += ','
                sopr_pr += sopr_po_pr


    #        insert.db_write('pih', pih)      # Пьезометрический напор       
            if t != -10000:  # Не писать если не считали теплп
                insert.db_write('t1', t)             # Температура сетевой воды     
                insert.db_write('t2', t2)            #                              
            

            insert.db_write('b101', ut)   # Коэффициент смешения элеватора
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


    if n_pt_negat > n_pt_negat_max:
        cprint(f'Всего {n_pt_negat} потребителей с отрицательным располагаемым напором ', color='red');

    insert.exec()

#    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
#    with (
#        tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file_po, 
#        tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file_pr
#    ):

    if config.args.is_dross_yes and not config.args.g_is_avar:
        q = make_sql_potr('realconsumers', sopr_pr)

#        print(q)

        if not q is None:
            cursor.execute(q)

        q = make_sql_potr('generalizedConsumers', sopr_po)
        if not q is None:
            cursor.execute(q)

    conn.commit()


    '''
    print('\u00A0')
    print('Теплопотребление и тепловые потери')
    print('Потребители')

    print_bal('Отопление, зав. схема', Q_otoplz0, G_otoplz0)
    print_bal('Отопление, незав. схема', Q_otopln0, G_otopln0)
    print_bal('Вентиляция', Q_ventil0, G_ventil0)
    print_bal('ГВ закрытое', Q_gvz0, G_gvz0)
    print_bal('ГВ рецирк', Q_rez0, G_rez)
    print_bal('Всего, закрытые системы', 
        Q_otoplz0 + Q_otopln0 + Q_ventil0 + Q_gvz0,
        G_otoplz0 + G_otopln0 + G_ventil0 + G_gvz0)
        '''


#    ins = insert.insert_text()
#    print(ins)
#    exit(1)

#    cursor.execute(ins)
#    conn.commit()

