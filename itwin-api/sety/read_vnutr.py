import unicodedata
import networkx as nx
import pyodbc
import sys
import math

import logging

from sety import atm

from sety import config

from sety.read_db import read_row
from sety import consumption
from sety import const
from sety import w_data
from sety import sopr2
from sety.b5.b5 import get_b5

from sety.atm import add_atm

from sety.any.colors import cprint
from consumption import get_pt_name



#-----------------------------------------------------------------------------------

def add_node_for_pr(map_node, G, nP, name1, po1, x1, y1, id, externalCodeID, id1, debug):

    po1 = 1 if po1 == 'P' else 2
    
    coef = 100.
    coef = 30.
    
    n = map_node.get((name1, po1), None)
    if not n is None:
        return id1

    x = nP.get('x', None)
    y = nP.get('y', None)
    uzel = nP.get('uzel', None)
    uzel = nP.get('uzel', None)
    geoMarkTopTube = nP.get('geoMarkTopTube', None)
    fileID = nP.get('fileID', None)


    if name1 != '0':  # Узел подключения
        x *= coef
        y *= coef

        data = {}

        data['typ'] = 'nodes'

        if x: data['x'] = x
        if y: data['y'] = -y

        if name1: data['name'] = name1
        if name1: data['nodeName'] = name1
        if id: data['id'] = id
        if externalCodeID: data['kod'] = externalCodeID
        if externalCodeID: data['externalCodeID'] = externalCodeID
        if id: data['internalNodeID'] = id
        if geoMarkTopTube: data['geoMarkTopTube'] = geoMarkTopTube
        if fileID: data['fileID'] = fileID

        if uzel is None: uzel = ''

        if y: data['y'] = -y-20

#        popo = id1*2 + po1
#        popo = id1 + 10
        popo = id1

        G.add_node((id, popo), **data, po = popo, G=0.)

        map_node[(name1, po1)] = (id, popo)
#        if debug: print((name1, po1), (id, popo))
    else:
        map_node[(name1, po1)] = (id, po1)
#        if debug: print((name1, po1), (id, po1))

    id1 += 1

    return id1

#-----------------------------------------------------------------------------------
# Добавляем внутреннюю схему потребителей

def read_pt_vnutr(G, conn, tn, s_fileID):
    cursor = conn.cursor()
    cols = w_data.str_for_sql(tn, 'o')
#    q = f'''SELECT o.id, o.lineID, l.externalSignLineID, l.hydroRes, {cols} FROM {tn} o JOIN linesobj l ON l.id=o.lineID WHERE l.removed=0'''
    q = f'''SELECT o.id, o.nodeID, n.externalSignID, n.externalCodeID, n.externalNodeName, {cols} FROM {tn} o 
            JOIN nodes n ON n.id=o.nodeID 
            WHERE n.removed=0 AND n.fileID IN ({s_fileID})'''

#    print('---------------------')
#    print(q)
#    print('---------------------')

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr, flush=True)

    try:
        cursor.execute(q)

        nn = 1

        while True:
            row = cursor.fetchone()
            if not row: break
            id2, nodeID, externalSignID, externalCodeID, externalNodeName, *qq = row
            if id2 is None or nodeID is None: continue

            pr = read_row(tn, cursor, row)
            pr['id2'] = id2
            pr['nodeID'] = nodeID


            if pr.get('sost', 0) == 2:  # Закрыт
                continue


#            print('-------------------')
#            print(qq)
#            for col, val in qq.items():
#                print(col, val)

#            ut['hydroRes'] = hydroRes

            GZ, GP, GO, Qz, Qp, Qo, pr_out = 0, 0, 0, 0, 0, 0, None

            if tn == 'realConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_pr(G, pr, externalCodeID, externalNodeName, True)
            else:
                print(f'Error {__file__}')
                exit(1)

            if (pr.get('gvop', 0) == 0 and pr.get('gvoo', 0) == 0 and 
                pr.get('gvpr', 0) == 0 and pr.get('gvps', 0) == 0 and 
                pr.get('gvpw', 0) == 0 and pr.get('gvsm', 0) == 0 and
                config.args.is_leto):

                    continue
                    

#            nP = G.nodes.get((nodeID, 1), None)
#            nO = G.nodes.get((nodeID, 2), None)

            ut = dict()

            ut['id'] = nodeID
            ut['typ'] = tn
#            ut['h'] = pP-pO
            ut['sost'] = const.L_OPEN
            ut['externalSignLineID'] = 4

            # сопротивления

#            gsz = pr.get('gsz', 0)
#            gszl = pr.get('gszl', 0)
#            gsop = pr.get('gsop', 0)
#            gsoo = pr.get('gsoo', 0)

#-------------
            nP = G.nodes.get((nodeID, 1), None)
            nO = G.nodes.get((nodeID, 2), None)

            nP['typ'] = 'realConsumers3'
#            nO['typ'] = 'realConsumers3'
            if pr: nP |= pr
            if pr_out: nP |= pr_out

            cxema_name = pr.get('cxema', '??')
            cxema = get_b5(pr.get('cxema', '??'))

            x = nP.get('x', None)
            y = nP.get('y', None)
            uzel = nP.get('uzel', None)
            uzel = nP.get('uzel', None)
            geoMarkTopTube = nP.get('geoMarkTopTube', None)
            fileID = nP.get('fileID', None)

            map_node = dict()

            name = nP.get('name', '???')

            debug = name == '7.10'
            debug = False

            if debug: print('--------------------', name,  pr.get('cxema', '??'), nodeID)
#            exit(1)

            id1 = 10


            '''
            
            for line in cxema:
                name1,po1,name2,po2,typ,x1,y1,x2,y2,t = line
                if typ == 'Расходомер': 
                    continue

                if name2 == '' and typ != 'Узел подпитки':
                    continue

#                if debug: print(typ)
#                id1 = add_node_for_pr(map_node, G, nP, name1, po1, x1, y1, nodeID, externalCodeID, id1, debug)
                id1 = add_node_for_pr(map_node, G, nP, name1, po1, x1, y1, nodeID, externalCodeID, int(t)*2, debug)

                if name2 != '':
#                    id1 = add_node_for_pr(map_node, G, nP, name2, po2, x2, y2, nodeID, externalCodeID, id1, debug)
                    id1 = add_node_for_pr(map_node, G, nP, name2, po2, x2, y2, nodeID, externalCodeID, int(t)*2+1, debug)

#                id1 = 1000000
        '''
                    

            for line in cxema:
                name1,po1,name2,po2,typ,x1,y1,x2,y2,t = line
                if typ in ('Расходомер', 'Манометр', 'Термометр'):
                    continue

#                if debug: print(line)

                popo1 = 0 if po1 == 'P' else 1
                popo2 = 0 if po2 == 'P' else 1

                id1 = add_node_for_pr(map_node, G, nP, name1, po1, x1, y1, nodeID, externalCodeID, int(name1)*2 + 10 + popo1, debug)

                if name2 != '':
                    id1 = add_node_for_pr(map_node, G, nP, name2, po2, x2, y2, nodeID, externalCodeID, int(name2)*2 + 10 + popo2, debug)

#                id1 = 1000000


            ut['typ'] = 'inner_line'

            for line in cxema:
                ut['typTO'] = t
                name1,po1,name2,po2,typ,x1,y1,x2,y2,t = line
                popo1 = 0 if po1 == 'P' else 1
                popo2 = 0 if po2 == 'P' else 1

                if typ == 'Расходомер': 
                    continue

                if typ == 'Узел подпитки': 
                    po1 = 1 if po1 == 'P' else 2
                    id1, po1 = map_node.get((name1, po1), None)


                    a12 = pr.get('a12', 0)
                    G_gvop = pr_out.get('G_gvop', 0)
                    G_gvoo = pr_out.get('G_gvoo', 0)
                    h = nP.get('geoMarkTopTube', 0)


#                    if po1%2 == 1:
                    if G_gvop != 0:
                        S = (a12 + h) / math.pow(G_gvop + G_gvoo, 2.)
                        ut['typ'] = 'OP'
                        ut['S'] = S
                        
                        _ATMOSPHERE = add_atm(G)
                        G.add_edge((id1, po1), _ATMOSPHERE, key=(id, 5), po=1, Y=1, **ut, state=1)


                    if G_gvoo != 0:
                        S = (a12 + h) / math.pow(G_gvop + G_gvoo, 2.)
                        ut['typ'] = 'OO'
                        ut['S'] = S
                        
                        _ATMOSPHERE = add_atm(G)
                        G.add_edge((id1, po1), _ATMOSPHERE, key=(id, 6), po=1, Y=1, **ut, state=1)

                    continue
                
                
                po1 = 1 if po1 == 'P' else 2
                po2 = 1 if po2 == 'P' else 2
                
                if name2 != '': # 
                    id1, po1 = map_node.get((name1, po1), None)
                    id2, po2 = map_node.get((name2, po2), None)

                    ut['typ'] = 'inner_line'
                    ut['S'] = 0

#                    if name == '11111': print((name1, po1), (name2, po2), (id1, po1), (id2, po2), typ, t)
                    t = int(t)

                    """
                    1, Отопление
                    2, Вентиляция
                    3, ГВС
                    4, Подпорная
                    5, Вход теплового пункта
                    6, Циркуляционная

                   "b23","Отопление"
                   "b28","Вентиляция (воздушного отопления)"
                   "b32","ГВС; закрытая"
                   "b20","Подпорная"
                   "b14","Вход теплового пункта"
                   "b38","Ограничительная в циркуляционном контуре ГВС"
                   "b35","На входе подающего трубопровода открытой ГВС"
                   "b36","Подпорно-циркуляционная в открытой ГВС"

                    """

                    ut['nodeID_pr'] = nodeID

                    if typ == 'Элеватор':
                        ut['typ'] = 'EL'

                        du_elevat = pr.get('du_elevat', 0)

                        if du_elevat != 0:
                            ut['S'] = math.pow(9.6 / du_elevat, 4.);
                            ut['ZZ'] = pr.get('otoplz', 0)

                    elif typ == 'Задвижка':
                        ut['typ'] = 'ZD'
                        col = f'zd{t}'
#                        openclose = pr.get(col, 3)
#                        if openclose == 2: continue         # Закрытоо
#                        if openclose == 3:
#                            print('Ошибка', pr)
#                            exit(1)
                        
#                        if t == 39:    #  Летняя закрГВС
#                            continue
#                        if t == 50:    # Летняя открГВС
#                            continue
                        ''''''

                        if config.args.is_leto:
                            if   t == 27:   #  Вход СО
                                continue   #  Летняя закрГВС

                        if config.args.is_leto:
                            if   t == 39: pass   #  Летняя закрГВС
                            elif t == 49: continue    # Летняя открГВС
                            elif t == 50: pass    # Летняя открГВС открыто

                            elif t == 48: continue    # Вентиляция
#                            elif t == 28: continue    # Вх.II ступен.ГВ
                        
                        else:

                            openclose = pr.get(col, 3)
                            if openclose == 2: continue         # Закрыто
                            if openclose == 3:
                                print('Ошибка', pr)
                                exit(1)
                        
#                        if t == 39:    #  Летняя закрГВС
#                            continue
#                        if t == 50:    # Летняя открГВС
#                            continue
                        ''''''

#                            if   t == 39: continue   #  Летняя закрГВС
#                            elif t == 49: pass   # Летняя открГВС
#                            elif t == 50: continue   # Летняя открГВС
                                     # закрыто


                    elif typ == 'Участок теплопровода':
                        ut['typ'] = 'UT'
                        ut['S'] = 0
#                        print('==========', t)

                        G_gvop = pr_out.get('G_gvop', 0)
                        G_gvoo = pr_out.get('G_gvoo', 0)
                        G_rez = pr_out.get('G_rez', 0)


                        if t == 43:
                            a11 = pr.get('a11', 0)

                            if G_rez == 0:
                                cprint(f'Не задана нагрузка рециркуляции для [{get_pt_name(nP)}]', color='red')
                                exit(1)
                            if a11 == 0:
                                cprint(f'Не задана потеря напора в открытой ГВ [{get_pt_name(nP)}]', color='red')
                                exit(1)

                            if G_rez != 0:
                                ut['S'] = a11 / math.pow(G_rez, 2.)

                        if t == 46: # Рециркуляция 
                            a10 = pr.get('a10', 0)

                            if a10 == 0:
                                cprint(f'Не задан напор на выходе приборов ГВ [{get_pt_name(nP)}]', color='red')
                                exit(1)
                            if G_gvop + G_gvoo + G_rez == 0:
                                cprint(f'Не задана нагрузка ГВ [{get_pt_name(nP)}]', color='red')
#                                print(nP)
#                                print(pr)
                                exit(1)

#                            ut1 = dict()
#                            S1 = sopr.soprUT(ut1, 1)
                            if debug:
                                print(f'a10={a10} {G_gvop} + {G_gvoo} + {G_rez} ')
                            ut['S'] = a10 / math.pow(G_gvop + G_gvoo + G_rez, 2.) 



                    elif typ == 'Радиаторы системы отопления':
                         if config.args.is_leto: continue

                         ut['typ'] = 'SO'
                         ut['S'] = sopr2.Sopr_otoplz(pr, pr_out, debug)
                         ut['ZZ'] = pr.get('otoplz', 0)

                    elif typ == 'Теплообменник':
                        ut['typ'] = 'TO'
                        ut['typTO'] = t

                        a17 = pr.get('a17', 0)
                        G_gvpr = pr_out.get('G_gvpr', 0)
                        G_gvsm = pr_out.get('G_gvsm', 0)
                        G_gvpw = pr_out.get('G_gvpw', 0)
                        G_gvps = pr_out.get('G_gvps', 0)
                        G_otopln = pr_out.get('G_otopln', 0)
                        G_otoplz = pr_out.get('G_otoplz', 0)
                        G_ventil = pr_out.get('G_ventil', 0)
                        
                        if t == 12: # Отопление
#                            ut['S'] = sopr2.Sopr_otopln(pr, pr_out, debug)

                            ut['ZZ'] = pr.get('otopln', 0);

                            ras = G_otopln

                            if G_gvps != 0 or G_gvpw != 0:
                                ras = G_otopln + G_otoplz
                                if a17 == 1: #/*'О'*/: 
                                    ras += (G_gvps + G_gvpw)

                            if ras != 0:
                                ut['S'] = pr.get('a7', 0) / math.pow(ras, 2.);

                        elif t == 11: # ГВС 2 ступень 
#                            ut['S'] = sopr2.Sopr_gvs(pr, pr_out, debug)

                             ut['ZZ'] = pr.get('gvpr', 0) + pr.get('gvps', 0) + pr.get('gvpw', 0) + pr.get('gvsm', 0);

                             if G_gvps != 0:
                                 ut['typ_gvs'] = 'ps'
                                 ras = G_otopln + G_otoplz
                                 if a17 == 1: #/*'О'*/: 
                                    ras += G_gvps

                             elif G_gvpw != 0:
                                 ut['typ_gvs'] = 'pw'
                                 ras = G_otopln + G_otoplz
                                 if a17 == 1: #/*'О'*/: 
                                    ras += G_gvpw

                             elif G_gvpr != 0:
                                ut['typ_gvs'] = 'pr'
                                ras = G_gvpr

                             elif G_gvsm != 0:
                                 ut['typ_gvs'] = 'sm'
                                 ras = G_gvsm
                             else:
                                pass

                             if ras != 0: 
                                ut['S'] = pr.get('a23', 0) / math.pow(ras, 2.);

                        elif t == 10: #
                            if G_gvps != 0 or G_gvpw != 0:
                                ras = G_otopln + G_otoplz + G_ventil
                                if a17 == 1: #/*'О'*/: 
                                    ras += G_gvps + G_gvpw

                                if G_gvps != 0:
                                    ut['typ_gvs'] = 'ps'
                                else:
                                    ut['typ_gvs'] = 'pw'

                            elif G_gvsm != 0:
                                ut['typ_gvs'] = 'sm'
                                ras = G_gvsm + G_otopln + G_otoplz + G_ventil


                            nP['nIn'] = (id1, po1)

#                            parent->nIin = where(ll);

                            if ras != 0:  
                                ut['S'] = pr.get('a22', 0) / math.pow(ras, 2.)

                            ut['ZZ'] = pr.get('gvpr', 0) + pr.get('gvps', 0) + pr.get('gvpw', 0) + pr.get('gvsm', 0);

                        else:
                            if debug:    
                                print('++', t)
                                exit(1)

                    elif typ == 'Калориферная установка':
                        if config.args.is_leto:
                            continue

                        ut['typ'] = 'VN'
                        ut['S'] = sopr2.Sopr_ventil(pr, pr_out, debug)
                        ut['ZZ'] = pr.get('ventil', 0)


                    elif typ == 'Диафрагма':
                        diam = 0
                        ut['typ'] = 'DR'

                        if   t == 1:  diam = pr.get('b23', 0) #  Отопление
                        elif t == 2:  diam = pr.get('b28', 0) #  Вентиляция
                        elif t == 3:  diam = pr.get('b32', 0) #  ГВС, закрытая
                        elif t == 4:  diam = pr.get('b20', 0) #  Подпорная
                        elif t == 5:  diam = pr.get('b14', 0) #  Вход теплового пункта
                        elif t == 6:  diam = pr.get('b38', 0) #  Ограничительная в циркуляционном контуре ГВС
                        elif t == 37: diam = pr.get('b35', 0) #  На входе подающего трубопровода открытой ГВС
                        elif t == 45: diam = pr.get('b36', 0) #  Подпорно-циркуляционная в открытой ГВС
                        else: 
                            print('Внутренняя ошибка!!!', cxema_name, (name1, po1), (name2, po2), (id1, po1), (id2, po2), typ, t)
                            exit(1)

                        ut['S'] = sopr2.soprDR(diam, debug)
                    else:
                        print(f'Неизвестный тип {typ} {t}')
                        exit(1)
                        continue

                    if ut['typ'] == 'inner_line':
                        print(typ, ut)
                        exit(1)

#                    if debug and ut['S'] != 0:
#                        print((name1, po1), (name2, po2), (id1, po1), (id2, po2), typ, t, 'S=', ut['S'])
                        

#                    ut['S'] = 1000000

                    if debug: 
                        if ut['S'] != 0:
                            print((id1, po1), (id2, po2), typ, t, 'S=', ut['S'])

#                    ut['nodeID1'] = int(name1)*2 + 10 + popo1
#                    ut['nodeID2'] = int(name2)*2 + 10 + popo2
                    ut['mesto'] = t

                    G.add_edge((id1, po1), (id2, po2), key=(id, 1), po=2, **ut, state=1)

            
            if cxema is None:
                cprint(f'Не задана внутренняя схема для потребителя', color='red')
                exit(1)



            print(nn, '              ', end='\x0D', file=sys.stderr, flush=True)
            nn += 1

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)
#    exit(1)

#-----------------------------------------------------------------------------------



