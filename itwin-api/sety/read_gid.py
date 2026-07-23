import unicodedata
import networkx as nx
import pyodbc
import sys
import math

import logging

import sety.any.connect
from sety import w_data

from sety import config

from sety import read_gid2

from sety import read_tg

from sety import teplo

import sety.teplo.y_ut

from sety.read_db import read_tab_node
from sety.read_db import read_tab
from sety.read_db import read_row
from sety.read_db import read_lookup

from sety.ct import map_ct

from sety.sprav import read_sprav

from sety import atm
from sety import w_print
from sety import sopr
from sety import sopr2
from sety import consumption
from sety import const

from sety.tg.tg_h import Tg

from sety.tg.tg1 import make_tg
from sety.tg.tg1 import find_izlom
from sety.tg.tg1 import CalculateOT1

from sety.any.colors import cprint

from sety.line_poteri import line_poteri

from sety.b5.b5 import get_b5

from consumption import get_pt_name

from sety import read_vnutr

from sety.atm import add_atm

from sety.read_zn import read_zn0

from check_ec_hs import check_ec_hs


#L_OPEN = 1
#L_CLOSED = 2
#L_INACTIVE = 3

L2_OBA = 1
L2_POD = 2
L2_OBR = 3
L2_PO = 4
L2_OP = 5


#-----------------------------------------------------------------------------------

s_fileID = '2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,48,49,50,51,52,54,55,58,801,806,2149,3150,3151,3152'
s_fileID = '4'
s_fileID = '3151'

map_fragments = {}

#map_ct = {}

map_ist = {}
map_kod = {}
map_ur = {}
map_tr = {}
map_kv = {}
map_rs = {}

map_ns = {}

#G = nx.MultiGraph()

#-----------------------------------------------------------------------------------

# Читает узлы

#map_node_vn = set()     # Узлы с внутренними схемами

set_node_vn = set()     # Узлы с внутренними схемами
map_connectNodes = {}   # Узлы подключения

#-----------------------------------------------------------------------------------

# Тут читаем узлы с внутренними схемами


# ТМ-14(С2) О в П-1(22) дублируется !!!!
# П-1(22)  37316699
#
'''
Вот это запрос для проверки

SELECT 
l.id, 
n.externalNodeName,
n1.externalNodeName, n1.externalSignID, 
n2.externalNodeName, n2.externalSignID
 
FROM connectNodes cn1
JOIN connectNodes cn2 ON cn1.connectID=cn2.connectID AND cn1.id != cn2.id 
JOIN nodes n1 ON n1.id=cn1.nodeID AND n1.removed=0
JOIN nodes n2 ON n2.id=cn2.nodeID AND n2.removed=0
JOIN nodes n ON n.id=n1.internalNodeID AND n.removed=0
LEFT JOIN linesobj l ON l.nodeID1=n1.id OR l.nodeID2=n1.id
WHERE n1.internalNodeID = n2.internalNodeID 
    AND n1.externalSignID = n2.externalSignID
--  AND n.externalNodeName='П-1(22)'
    AND n.fileID = 3151
--  AND l.id IS NULL
ORDER BY n.externalNodeName

'''


def read_node_vn(conn):
    cursor = conn.cursor()
    q = f'''
SELECT DISTINCT n.internalNodeID 
FROM nodes n
JOIN nodes n0 ON n0.id=n.internalnodeid AND n0.removed=0 
LEFT JOIN realConsumers rc ON rc.nodeID=n.internalNodeID
WHERE rc.id IS NULL AND n.internalNodeID IS NOT NULL AND n.fileID IN ({s_fileID}) and n.removed=0 
    '''

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            id, = row

            set_node_vn.add(id)

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

#-----------------------------------------------------------------------------------

def read_zn(G, conn):
    cursor = conn.cursor()

    q = f'''
SELECT n.id, sp.pressFlow, sp.pressRet FROM setPressNodes sp
JOIN nodes n ON n.id=sp.nodeID 
WHERE n.fileID IN ({s_fileID})  '''

    q = f'''

SELECT
n.id,
sp.pressFlow, sp.pressRet,
us2.pihP,us2.pihO,
us2.t1P,us2.t1O,
us2.t2P,us2.t2O,
ec.name as kod, n.externalNodeName AS name,
us2.id AS id_m,
sp.kod_m, sp.uzel_m,
fr.name AS fr_name,
us2.ist,
sp.fragment_resultid

FROM setPressNodes sp
JOIN nodes n ON n.id=sp.nodeID 
JOIN externalCodes ec ON ec.id=n.externalCodeID

LEFT JOIN 
(

SELECT 
n2.id,
n2.fileID,
ec2.name AS kod, n2.externalNodeName AS name,
usP.pih AS pihP, usP.t AS t1P, usP.t2 AS t2P,
usO.pih AS pihO, usO.t AS t1O, usO.t2 AS t2O,
usP.ist

FROM nodes n2
JOIN externalCodes ec2 ON ec2.id=n2.externalCodeID 
JOIN US_OUT usP ON usP.nodeID=n2.id AND usP.externalSign=1
JOIN US_OUT usO ON usO.nodeID=n2.id AND usO.externalSign=2

JOIN
(
    SELECT 
    c.fileID,
    max(c.id) AS cid
    FROM CALCULATION c
    LEFT JOIN fragments fr ON fr.id=c.fileID
    GROUP BY c.fileID
) calc ON n2.fileID=calc.fileID and usP.calculationID=calc.cid and usO.calculationID=calc.cid

) us2 ON us2.kod=sp.kod_m AND us2.name=sp.uzel_m AND us2.fileID=sp.fragment_resultID
LEFT JOIN fragments fr ON fr.id=sp.fragment_resultID

WHERE n.fileID IN ({s_fileID}) and n.removed=0'''

#    print(q)
#    exit(1)

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()

            if not row: break
            (id, pP, pO, pP_m, pO_m, tP_m, tO_m, t2P_m, t2O_m, 
                kod, name,    # Узел с ЗН
                id_m,        # Найденный узел из магистрали
                kod_m, uzel_m, # Заданный узел из магистрали
                fr_name,
                ist0, #   Источник из магистрали. Использовать только после конвертации
                fragment_resultid
                )  = row

#            if kod is None: kod = ''
            if kod_m is None: kod_m = ''
                           
            if config.args.is_mag_fragment:
                if fr_name is None:
                    cprint(f'Для узла с заданным напором [{kod} {name}] не задан фрагмент присоединения')
                    cprint('    Расчет режима производится через заданный располагаемый напор')
                elif id_m is None:
                    if (kod_m is None and uzel_m is None) or (kod_m == '' and uzel_m == ''):
                        cprint(f'Для узла с заданным напором [{kod} {name}] не задан узел во фрагменте [{fr_name}]', color='red')
                        cprint('    Расчет режима производится через заданный располагаемый напор', color='red')
                    else:
                        cprint(f'В узле с заданным напором [{kod} {name}] указан несуществующий узел [{kod_m} {uzel_m}] на магистральном фрагменте [{fr_name}]: Уточните', color='red')
#                        cprint(f'Для узла с заданным напором [{kod} {name}] не могу найти узел [{kod_m} {uzel_m}] во фрагменте [{fr_name}]', color='red')
                        cprint('    Расчет режима производится через заданный располагаемый напор', color='red')
                else:
                    pP = pP_m
                    pO = pO_m
#                   print(f'Узел с заданным напором [{kod} {name}]  {pP} {pO} Подключен к [({fr_name}) {kod_m} {uzel_m}] температура {tP_m}', flush=True)



            if pP is None: pP = 0
            if pO is None: pO = 0


            '''
            #--- Это для проверки
            if pP != 0 and pO == 0: 
                print('Узел ЗН ')
                if tP_m is not None:
                    nP['t0'] = tP_m
                    nP['zT'] = True

                ut = dict()

                ut['id'] = id
                ut['typ'] = 'pumps'
                ut['h'] = pP-pO
                ut['sost'] = const.L_OPEN
                ut['externalSignLineID'] = 6

                G.add_edge((id, 2), (id, 1), key=(id, 1), po=2, **ut, state=1)
                '''



#            print(id, pP, pO, flush=True)

            if pP != 0 and pO != 0:
#            if True:
#                print(kod, name, pP, pO)
                nP = G.nodes.get((id, 1), None)
                nO = G.nodes.get((id, 2), None)
                if nP is not None and nO is not None: 
                    if tP_m is not None:
                        nP['t0'] = tP_m
                        nP['zT'] = True

                    nO['p_zn'] = pO
                    nO['kod_main'] = kod_m
                    nO['name_main'] = uzel_m
                    nO['fragment_resultid'] = fragment_resultid

                    ut = dict()

                    ut['id'] = id
                    ut['typ'] = 'pumps'
                    ut['h'] = pP-pO
                    ut['sost'] = const.L_OPEN
                    ut['externalSignLineID'] = 6

                    nO['p_zn'] = pO

                    if not ist0 is None:
                        nP['ist0'] = ist0

#                        print('ИСТОЧНИК:', ist0, nP)

                    G.add_edge((id, 2), (id, 1), key=(id, 1), po=2, **ut, state=1)



            elif pO != 0:
                nO = G.nodes.get((id, 2), None)
                if nO is not None:
                    nO['p_zn'] = pO
            elif pP != 0:
                nP = G.nodes.get((id, 1), None)
                if nP is not None:
                    nP['p_zn'] = pP

            if pP != 0:
                nP = G.nodes.get((id, 1), None)
                if nP is not None and not ist0 is None:
                    nP['ist0'] = ist0


    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)
        print(q)


#-----------------------------------------------------------------------------------

def remove_control_characters(s):
    return ''.join(ch for ch in s if unicodedata.category(ch)[0] != 'C')

#-----------------------------------------------------------------------------------



# Внутренние узлы для источника

def read_ist_vn(G, conn, fileID):

    q = f'''

SELECT
n1.id, n.id, n1.externalsignid
FROM nodes n
JOIN heatsources hs ON hs.nodeid=n.id
JOIN nodes n1 ON n.id=n1.internalnodeid 
JOIN connectNodes cn ON cn.nodeid=n1.id -- AND n1.externalsignid = 2

WHERE n.removed=0 AND n1.removed=0
AND n.fileid={fileID}


'''

    try:
        cursor = conn.cursor()
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            n_id, n_ist, po  = row

            nPist = G.nodes.get((n_ist, 1), None)
            nOist = G.nodes.get((n_ist, 2), None)

            if po == 2:
                nP = G.nodes.get((n_id, 1), None)

                if nP:
                    if nPist:
#                        print('ВНУТРИ', nP, nPist)

                        nP['ist0'] = nPist.get('ist0', 0)
                        nP['t0'] = nPist.get('t0', 0)
                        nP['zT'] = True

                        nPist['n1'] = n_id




            if po == 3:
                nO = G.nodes.get((n_id, 2), None)
                if nO:
                    if nPist:
                        nPist['n2'] = n_id

#                        print('ВНУТРИ', nO, nPist.get('ist0', 0))

                        nO['ist0'] = nPist.get('ist0', 0)

                
    
    #            ec_ist[ec_id] = ist

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

#    print(ec_ist)




def read_node(G, conn, tn):
    cursor = conn.cursor()

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr, flush=True)

    q = f'''SELECT 
            n.id, n.externalCodeID, n.externalNodeName, n.nodeName, n.externalSignID, n.internalNodeID, 
            case 
            when n.internalNodeID is null
            then n.geoMarkTopTube
            else n0.geoMarkTopTube
            end as geoMarkTopTube,

            case 
            when n.internalNodeID is null
            then n.geoMarkNodeArea
            else n0.geoMarkNodeArea
            end as geoMarkNodeArea,

--            n.geoMarkNodeArea, 
            n.externalCodeID, n.fileID, n.x AS stx, n.y AS sty 
            FROM {tn} n 
            LEFT JOIN nodes n0 on n0.id=n.internalNodeID

            WHERE n.removed=0 AND n.fileID IN ({s_fileID})

            order by n.internalNodeID is not null, n.id
--            order by n.id
            
            '''

#    print(q)
#    exit(1)

    coef = 100.
    coef = 30.

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
            id, kod, uzel, nodeName, externalSignID, internalNodeID, geoMarkTopTube, geoMarkNodeArea, externalCodeID, fileID, x, y = row

            if id is None: continue

#            qq = read_row(tn, cursor, row)

            kod = map_kod.get(kod, str(kod))

            if uzel is None: uzel = ''
            uzel = remove_control_characters(uzel)
            if nodeName: nodeName = remove_control_characters(nodeName)
            
            if x is None: x = 0.
            if y is None: y = 0.

            x /= 100.    #  Это перевод в метры
            y /= -100.

            if not internalNodeID is None:
                if not internalNodeID in set_node_vn:
                    continue

                n0 = G.nodes.get((internalNodeID, 1), None)

#                print(internalNodeID)

                if not n0 is None:
                    x0 = n0.get('x', 0)
                    y0 = n0.get('y', 0)
                    geoMarkTopTube = n0.get('geoMarkTopTube', 0)

                    if x < 1000:
                        x -= 400.
                        y -= 400.
                    else:
                        x -= 8000.
                        y -= 8000.

                    x = x0/coef + x/10
                    y = -y0/coef + y/10
                else:
#                    print('Error', internalNodeID)
                    continue

            x *= coef
            y *= coef

            try:
                data = {}

                data['typ'] = 'nodes'

                if x: data['x'] = x
                if y: data['y'] = -y
                if uzel: data['name'] = uzel
                if nodeName: data['nodeName'] = nodeName
                if id: data['id'] = id
                if externalCodeID: data['kod'] = kod
                if externalCodeID: data['externalCodeID'] = externalCodeID
                if internalNodeID: data['internalNodeID'] = internalNodeID
                if geoMarkTopTube: data['geoMarkTopTube'] = geoMarkTopTube
                if fileID: data['fileID'] = fileID

                if uzel is None: uzel = ''

#                print(data)

                if externalSignID != 3:
                    if y: data['y'] = -y-20
                    G.add_node((id, 1), **data, po=1, G=0.)
                
                if externalSignID != 2:
                    if y: data['y'] = -y+20
                    G.add_node((id, 2), **data, po=2, G=0.)


            except nx.NetworkXError:
                pass

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)


#-----------------------------------------------------------------------------------

def read_connectNodes(conn):
    cursor = conn.cursor()
    q = '''
SELECT n.internalNodeID, n.id, n.externalSignID, cn.connectID FROM connectNodes cn
JOIN nodes n ON n.id=cn.nodeID
JOIN nodes nm ON nm.id=cn.connectID
WHERE n.removed=0 AND n.fileID IN ({s_fileID})    
    '''

    q = f'''
SELECT n.internalNodeID, n.id, n.externalSignID, cn.connectID FROM connectNodes cn
JOIN nodes n ON n.id=cn.nodeID
JOIN nodes nm ON nm.id=cn.connectID
JOIN linesobj l ON l.nodeID1=n.id OR l.nodeID2=n.id
WHERE n.removed=0 AND n.fileID IN ({s_fileID})
    '''

    q = f'''
    SELECT n.id, n.externalSignID, n.internalNodeID, connectID 
    FROM connectNodes cn, nodes n
    WHERE n.id=cn.nodeID AND n.fileID IN ({s_fileID}) AND n.removed=0
    '''

    q = f'''
    SELECT n.id, n.externalSignID, n.internalNodeID, connectID 
    FROM connectNodes cn
    JOIN nodes n on n.id=cn.nodeID AND n.removed=0 AND n.fileID IN ({s_fileID})
    JOIN nodes n2 on cn.connectID = n2.id and n2.removed=0 AND n2.fileID IN ({s_fileID})
    '''


#    print(q)
    
    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
#            internalNodeID, id, externalSignID, connectID = row

            id, externalSignID, internalNodeID, connectID = row

            if internalNodeID is None: continue

            map_connectNodes[(internalNodeID, connectID, externalSignID-1)] = id
    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

#    for k, v in map_connectNodes.items():
#        print(k, v)
#    exit(1)

#-----------------------------------------------------------------------------------


def read_line_row(G, tn, ut, lineID, nodeID1, nodeID2, externalSignLineID, internalNodeID):
    ut2 = {}

    ut2['S'] = 0

    name = w_print.line_name(G, lineID, nodeID1, nodeID2, externalSignLineID)

    if tn != 'heatPipeSections':
        ut2['sost'] = ut.get('sost', 1)
    
    if tn == 'heatPipeSections': # Участок теплопровода
        try:
#            if internalNodeID != 0 and internalNodeID is not None:
#                ut2['S'] = 0    
#            else:

            diametr = ut.get('diametr', 1000)

#            if diametr != 0:
#                name = w_print.line_name(G, nodeID1, nodeID2, externalSignLineID)

#                cprint(f'Не задан внутренний диаметр в Участке {name} {diametr}')
#                exit(1)

            heatSourceID = ut.get('heatSourceID', None)

            t1 = 150
            t2 = 70

            if not heatSourceID is None:
                ist = map_ist.get(heatSourceID, None)
                if ist:
                    t1 = ist.get('t1_r', None)
                    t2 = ist.get('t2_r', None)

#                print(t1, t2)
#            print(t1, t2)
#            exit(1)



            ut2['S'] = sopr.soprUT(ut, t1)
            ut2['S_P'] = sopr.soprUT(ut, t1)
            ut2['S_O'] = sopr.soprUT(ut, t2)

            ut2['diametr'] = ut.get('diametr', 1000)
            ut2['dlina'] = ut.get('dlina', 1)
            ut2['scher'] = ut.get('scher', 0.5)
            ut2['dolja'] = ut.get('dolja', 0)
            ut2['mestnoe'] = ut.get('mestnoe', 0)

#            po = {1:1, 2:2, 3:1, 4:2, 5:1}.get(externalSignLineID, 1)

#            name = w_print.line_name(G, nodeID1, nodeID2, externalSignLineID)
#            print(name)
#            print(name, y_ut.Y(ut, 1), y_ut.Y(ut, 2))

            try:
                ut2['YP'] = teplo.y_ut.Y(ut, 1)
                ut2['YO'] = teplo.y_ut.Y(ut, 2)

                ut2['normaP'] = teplo.y_ut.norma(ut, 1)
                ut2['normaO'] = teplo.y_ut.norma(ut, 2)
#                print(ut2['normaP'], ut2['normaO'])

            except Exception as e:
                print(f'Что-то с нормами тепловых потерь {e}')
                exit(1)


#            if name == '[Р1 1(1)К2 П] - [Р1 1(1)К1/1 П]':
#                print('===================================')
#                nor = y_ut.norma(ut, 1)
#                print('!!', name, nor)
#                exit(1)


        except Exception as e:
#        except:
            print(e, file=sys.stderr)
            exit(1)

    elif tn == 'dampers':            # Задвижка
        ut2['S'] = sopr.soprZD(ut)
        ut2['sost'] = ut.get('sost', 1)

    elif tn == 'regulArmatures':     # Регулирующая арматура ZD2
        ut2['S'] = sopr.soprZD2(ut)
        ut2['sost'] = ut.get('sost', 1)
        ut2['r1'] = ut.get('q_zad', 0)
#        print(ut, flush=True)

    elif tn == 'diaphragms': # Диафрагма
        ut2['S'] = sopr.soprDR(ut)
        ut2['sost'] = ut.get('sost', 1)

    elif tn == 'pumps':              # Насос
        ut2['h'] = ut.get('h', 0)
        ut2['r0'] = ut.get('r0_z', 0)
        ut2['r1'] = ut.get('r1_z', 0)
        ut2['r2'] = ut.get('r2_z', 0)
        ut2['qmin'] = ut.get('qmin', 0)
        ut2['sost'] = ut.get('sost', 1)

        ut2['k_nas'] = ut.get('k_nas', 0)
        ut2['tip_nas'] = ut.get('tip_nas', '')



    elif tn == 'consumptRegulators': # Сетевые регуляторы расхода
        read_gid2.read_RR(G, ut, ut2, lineID,nodeID1, nodeID2, externalSignLineID)
    
    elif tn == 'pressRegulators':    # Сетевые регуляторы давления
        read_gid2.read_RD(G, ut, ut2, lineID,nodeID1, nodeID2, externalSignLineID)

    elif tn == 'bypass':             # Байпаc
        read_gid2.read_BP(G, ut, ut2, lineID, nodeID1, nodeID2, externalSignLineID)

    elif tn == 'reverseValves':      # Обратный клапан
        ut2['sost'] = ut.get('sost', 1)

#        ut2 = ut
#        if ut.get('stateID'): ut2['stateID'] = ut['stateID']

    elif tn == 'pressDropRegulators': # Регулятор перепада давления
        ut2['sost'] = ut.get('sost', 1)
        cprint('[red]---', tn, ut, '[-]')
#        read_gid2.read_RP(G, ut, ut2, nodeID1, nodeID2, externalSignLineID)

    else:
#        if ut.get('stateID'): ut2['stateID'] = ut['stateID']
#        cprint(f'Читаем {tn} [{name}]', color='red')
        pass

    ut2['out'] = 0
    ut2['externalSignLineID'] = externalSignLineID

    return ut2

#-----------------------------------------------------------------------------------

def read_line2(G, conn, tn: str) -> None:
    cursor = conn.cursor()
    cols = w_data.str_for_sql(tn, 'o')
#    q = f'''SELECT o.id, o.lineID, l.nodeID1, l.nodeID2, l.externalSignLineID, n.internalNodeID, ec.heatSourceID, l.hydroRes, {cols} 
    q = f'''SELECT o.id, o.lineID, l.nodeID1, l.nodeID2, l.externalSignLineID, n.internalNodeID, ec.heatSourceID, l.hydroRes, {cols} 
            FROM {tn} o 
            JOIN linesobj l ON l.id=o.lineID 
            JOIN nodes n ON n.id=l.nodeID1 and n.removed=0
            JOIN externalCodes ec ON n.externalCodeID = ec.id
            LEFT JOIN nodes n0 on n0.id=n.internalNodeID and n0.removed=0
            LEFT JOIN realConsumers rc ON rc.nodeID=n.internalNodeID

            WHERE l.removed=0 AND n.removed=0 AND n.fileID IN ({s_fileID})
            AND (n0.id is NULL or n0.removed=0) AND rc.id is NULL
            
            '''

#    print('--------------------------------')
#    print(q)
#    print('--------------------------------')

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr, flush=True)

    pn = 1

    try:
        cursor.execute(q)

        nn = 1

        while True:
            row = cursor.fetchone()
            if not row: break
#            id, lineID, nodeID1, nodeID2, externalSignLineID, hydroRes, *qq = row
            id, lineID, nodeID1, nodeID2, externalSignLineID, internalNodeID, heatSourceID, hydroRes, *qq = row
            if id is None or lineID is None or nodeID1 is None or nodeID2 is None or nodeID1 == nodeID2: continue

#            ut = read_row(tn, cursor, row)


#            if heatSourceID is None:
#                print(lineID, nodeID1, nodeID2, tn)
                
                


            if internalNodeID is not None:
                n0 = G.nodes.get((internalNodeID, 1), None)
                if n0 is None:
#                    print(f'Узла {internalNodeID} нет, удалили скорее всего', flush=True)
                    continue

            ut = read_row(tn, cursor, row)

            if hydroRes: ut['sopr'] = hydroRes


#            if tn in ('bypass', 'pressRegulators'):
#                print(tn, ut)

            stateID_P = ut.get('key_ut_p', const.L_OPEN)
            stateID_O = ut.get('key_ut_o', const.L_OPEN)

            ut['heatSourceID'] = heatSourceID

            ut = read_line_row(G, tn, ut, lineID, nodeID1, nodeID2, externalSignLineID, internalNodeID)

            try:
                yP = ut.get('YP', 0)
                yO = ut.get('YO', 0)

                normaP = ut.get('normaP', 0)
                normaO = ut.get('normaO', 0)
#                print(ut['normaP'], ut['normaO'])

            except:
                print('!!!')
                exit(1)
                

            try:
                del ut['YP'], ut['YO'], ut['normaP'], ut['normaO']
            except:
                pass


#            if tn == 'heatPipeSections':
#                print('===============================')
#                print(tn, ut)
#                print(nodeID1, nodeID2)


            nodeID1p = map_connectNodes.get((nodeID1, nodeID2, 1), nodeID1)
            nodeID1o = map_connectNodes.get((nodeID1, nodeID2, 2), nodeID1)
            nodeID2p = map_connectNodes.get((nodeID2, nodeID1, 1), nodeID2)
            nodeID2o = map_connectNodes.get((nodeID2, nodeID1, 2), nodeID2)

#            if tn == 'heatPipeSections':
#                print(nodeID1p, nodeID2p)
#                print(nodeID1o, nodeID2o)

#            print(nodeID1p, nodeID1o, nodeID2p, nodeID2o)

            n1p = G.nodes.get((nodeID1p, 1), None)
            n1o = G.nodes.get((nodeID1o, 2), None)
            n2p = G.nodes.get((nodeID2p, 1), None)
            n2o = G.nodes.get((nodeID2o, 2), None)

            sost = ut.get('sost', 0)

            if sost != 0:
                stateID_P = sost
                stateID_O = sost

#            ut['id'] = id
            ut['id'] = lineID
            ut['typ'] = tn

#            print(ut)

#            print(tn)
            
            if tn == 'heatPipeSections':
                if externalSignLineID in (1, 3, 5):
                    ut['S'] = ut['S_P']
                else:
                    ut['S'] = ut['S_O']

#                print('SOPR', externalSignLineID, ut['S'], ut['S_P'], ut['S_O'])

#            print('!', externalSignLineID, stateID_P, stateID_O, n1p, n2p, n1o, n2o)

            if externalSignLineID == 1:
                if stateID_P != const.L_CLOSED and n1p and n2p: 
                    if externalSignLineID == 1 and tn == 'heatPipeSections':
                        ut['S'] = ut['S_P']
                    G.add_edge((nodeID1p, 1), (nodeID2p, 1), key=(lineID, 1), po=1, Y=yP, norma=normaP, **
                    ut, state=stateID_P, n1_obr = (nodeID1o, 2), n2_obr = (nodeID2o, 2), key_obr=(lineID, 2))
                if stateID_O != const.L_CLOSED and n1o and n2o: 
                    if externalSignLineID == 1 and tn == 'heatPipeSections':
                        ut['S'] = ut['S_O']
                    G.add_edge((nodeID1o, 2), (nodeID2o, 2), key=(lineID, 2), po=2, Y=yO, norma=normaO, **ut, state=stateID_O, n1_obr = (nodeID1p, 1), n2_obr = (nodeID2p, 1), key_obr=(lineID, 1))
            elif externalSignLineID == 2:
                if stateID_P != const.L_CLOSED and n1p and n2p: 
                    G.add_edge((nodeID1p, 1), (nodeID2p, 1), key=(lineID, 1), po=1, Y=yP, norma=normaP, **ut, state=stateID_P)
            elif externalSignLineID == 3:
                if stateID_O != const.L_CLOSED and n1o and n2o: 
                    G.add_edge((nodeID1o, 2), (nodeID2o, 2), key=(lineID, 2), po=2, Y=yO, norma=normaO, **ut, state=stateID_O)
            elif externalSignLineID == 4:
                if stateID_P != const.L_CLOSED and n1p and n2o: 
                    G.add_edge((nodeID1p, 1), (nodeID2o, 2), key=(lineID, 1), po=1, Y=yP, norma=normaP, **ut, state=stateID_P)
            elif externalSignLineID == 5:
                if stateID_O != const.L_CLOSED and n1o and n2p: 
                    G.add_edge((nodeID1o, 2), (nodeID2p, 1), key=(lineID, 2), po=2, Y=yO, norma=normaO, **ut, state=stateID_O)

            print(nn, '              ', end='\x0D', file=sys.stderr, flush=True)
            nn += 1


    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)

#-----------------------------------------------------------------------------------

def add_pr_vn(G, pr):
    print(get_b5(pr.get('cxema', '??')))

#-----------------------------------------------------------------------------------


map_ist2 = {}  # для поиска узла источника по его номеру


def read_node2(G, conn, tn):
    cursor = conn.cursor()
    cols = w_data.str_for_sql(tn, 'o')
#    q = f'''SELECT o.id, o.lineID, l.externalSignLineID, l.hydroRes, {cols} FROM {tn} o JOIN linesobj l ON l.id=o.lineID WHERE l.removed=0'''
    q = f'''SELECT o.id, o.nodeID, n.externalSignID, n.externalCodeID, n.externalNodeName, 
            n.internalnodeid, {cols} 
            FROM {tn} o 
            JOIN nodes n ON n.id=o.nodeID 
            WHERE n.removed=0 AND n.fileID IN ({s_fileID}) AND n.internalNodeID IS NULL'''

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr, flush=True)
#    print('--', tn)

    try:
        cursor.execute(q)

        nn = 1

        while True:
            row = cursor.fetchone()
            if not row: break
            id2, nodeID, externalSignID, externalCodeID, externalNodeName, internalNodeID, *qq = row
            if id2 is None or nodeID is None: continue

            pr = read_row(tn, cursor, row)

            pr['id2'] = id2
            pr['nodeID'] = nodeID
            pr['externalCodeID']  = externalCodeID
            pr['name']  = externalNodeName

#            print('-------------------')
#            print(qq)
#            for col, val in qq.items():
#                print(col, val)

#            ut['hydroRes'] = hydroRes

            GZ, GP, GO, Qz, Qp, Qo, pr_out = 0, 0, 0, 0, 0, 0, None

#            print(tn)

            if tn == 'realConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_pr(G, pr, externalCodeID, externalNodeName, True)
#                print(externalNodeName, GZ, GP, GO, Qz, Qp, Qo)

            elif tn == 'generalizedConsumers':

                # тут переключение типов обобщенных потребителей
                if False:
                    pr = consumption.set_po_typ(pr, 'pr', 'pr')
                    pr = consumption.set_po_typ(pr, 'sm', 'pr')
                    pr = consumption.set_po_typ(pr, 'ps', 'pr')
                    pr = consumption.set_po_typ(pr, 'pw', 'pr')

                    pr = consumption.set_po_otopl_typ(pr, 'n', 'z')


                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_po(G, pr, externalCodeID, externalNodeName, True)

#                print(externalNodeName, GZ, GP, GO, Qz, Qp, Qo)
            elif tn == 'refillNodes':   # Узел подпитки
                r_p = pr.get('r_p', 0);
                r_v = pr.get('r_v', 0);
                r_z = pr.get('r_z', 0);
                r_r = pr.get('r_r', 0);

                GZ = -(r_p - r_v + r_z - r_r)
                GO = GZ

            if tn == 'heatSources':
#                cprint('[red]', qq, '[-]')
                pass

#        read_node2(G, conn, 'refillNodes')          #  "Узел подпитки",         "Узлы подпитки и прис.баков-аккумуляторов", NULL,
#    'WDOdevices': tab_WDOdevices,     #       Водоразборный прибор

 

            if externalSignID in (1,2):
                try:
                    nP = G.nodes.get((nodeID, 1), None)
                    nP['typ'] = tn
                    if GZ != 0 or GP != 0:
                        nP['G'] = GZ+GP
                        nP['Gout'] = GP

                    if Qz != 0:
                        nP['Qz'] = Qz
                
                except:
                    print('Error', (nodeID, 1))
                    continue

            if externalSignID in (1,3):
                try:
                    nO = G.nodes.get((nodeID, 2), None)
                    nO['typ'] = tn
                    if GZ != 0 or GO != 0:
                        nO['G'] = -GZ+GO
                        nO['Gout'] = GO

                    if Qz != 0:
                        nP['Qz'] = Qz
                except:
                    print('Error', (nodeID, 2))
                    continue

            nP['id2'] = id2

            if tn == 'heatSources':

                nP['ist0'] = id2
#                print('ИСТОЧНИК:', id2, nP)

                map_ist2[id2] = nodeID

#                v = read_tg.get_tg(id2, config.args.Tn)
                v = read_tg.get_tg(id2, config.args.Tn)
                if v:
                    t1, t2, t3, tv = v

                    if config.args.is_leto:
                        t1 = pr.get('t1_leto', 0)  # летняя температура источника

                    nP['t0'] = t1
                    nP['zT'] = True


#                    print('ist >>> ', id2, nodeID)


            if tn == 'realConsumers':
                if pr: nP |= pr
                if pr_out: nP |= pr_out
            if tn == 'generalizedConsumers':
                if pr: nP |= pr
                if pr_out: nP |= pr_out


            print(nn, '              ', end='\x0D', file=sys.stderr, flush=True)
            nn += 1

    except pyodbc.Error as ex:
        print(ex)
        print(ex, file=sys.stderr)
        exit(1)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)

#-----------------------------------------------------------------------------------





def read_pt_line(G, conn, tn):
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

            GZ, GP, GO, Qz, Qp, Qo, pr_out = 0, 0, 0, 0, 0, 0, None

            if tn == 'realConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_pr(G, pr, externalCodeID, externalNodeName, True)
            elif tn == 'generalizedConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_po(G, pr, externalCodeID, externalNodeName, True)
            else:
                exit(1)

            ut = dict()

            ut['id'] = id
            ut['typ'] = tn
#            ut['h'] = pP-pO
            ut['sost'] = const.L_OPEN
            ut['externalSignLineID'] = 4

#            if tn == 'generalizedConsumers':
#                print(pr)
#                exit(1)

            ut['name'] = externalNodeName
            ut['externalCodeID'] = externalCodeID
            ut['kodur'] = pr.get('kodur', 0)
            ut['kodtr'] = pr.get('kodtr', 0)


            # сопротивления

            gsz = pr.get('gsz', 0)
            gszl = pr.get('gszl', 0)
            gsop = pr.get('gsop', 0)
            gsoo = pr.get('gsoo', 0)

            if config.args.is_leto:
                gsz = gszl

#-------------

            nP = G.nodes.get((nodeID, 1), None)

#            nP['typ'] = tn + '_2' # realConsumers_2

            nO = G.nodes.get((nodeID, 2), None)

            if gsz > 0:
                ut['S'] = gsz

                if tn == 'realConsumers':
                    if pr: ut |= pr
                    if pr_out: ut |= pr_out
                if tn == 'generalizedConsumers':
                    if pr: ut |= pr
                    if pr_out: ut |= pr_out

                G.add_edge((nodeID, 1), (nodeID, 2), key=(nodeID, 4), po=1, Y=1, **ut, state=1)

            if gsop > 0:
                ut['S'] = gsop
                _ATMOSPHERE = add_atm(G)
                G.add_edge((nodeID, 1), _ATMOSPHERE, key=(nodeID, 5), po=1, Y=1, **ut, state=1)
#                print(f'{gsop=}')

#                _ATMOSPHERE = add_atm(G)
#                G.add_edge((id1, po1), _ATMOSPHERE, key=(id, 5), po=1, Y=1, **ut, state=1)


            if gsoo > 0:
                ut['S'] = gsoo
                _ATMOSPHERE = add_atm(G)
                G.add_edge((nodeID, 2), _ATMOSPHERE, key=(nodeID, 6), po=1, Y=1, **ut, state=1)
#                print(f'{gsoo=}')

            print(nn, '              ', end='\x0D', file=sys.stderr, flush=True)
            nn += 1

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)

#-----------------------------------------------------------------------------------

def read_gid(conn, ff, db_name):

#    print(conn_str)
#    read_sprav(conn_str)

#    conn = connect.connect(**conn_str)
#    if not conn:
#        return

#    ff = conn_str.get('files')

#    print(config.args.no_kv)

    global s_fileID

    if ff:
        s_fileID = ''        
        for i in ff:
            if s_fileID != '': s_fileID += ','
            s_fileID += str(i)

    G = nx.MultiDiGraph()

    w_print.setG(G)

    if conn:
        check_ec_hs(conn, fileID=s_fileID)

        read_tg.read_tg(conn)  # Температурные графики

        read_tab_node(conn, 'heatSources', map_ist)          #  "Источник тепла",         "Источник тепла", "US_OUT",        

        for k, v in map_ist.items():
            tg = make_tg(v)
            tn_izl = find_izlom(tg, tg.TSMIN)
            v['tn_izl'] = tn_izl

        read_tab(conn, 'heatSystem', map_ct)        #  Система теплоснабжения

        if len(map_ct) < 1:
            print('!!!Страшная ошибка, нет системы теплоснабжения!!', flush=True)
            exit(1)

        k_ct = next(iter(map_ct))
#        print(map_ct[k_ct])

        ct = map_ct[k_ct]

        read_zn0(conn, fileID=s_fileID)


#    q_min float default ((0)),                -- G_min
#    h_min float default ((0)),                -- H_min
#    q_max float default ((0)),                -- G_max
#    h_max float default ((0)),                -- H_max



#        read_lookup(conn, 'standardpumps', 'tip_nas', map_ns)
        read_tab(conn, 'standardpumps', map_ns)


        read_tab(conn, 'specExpends', map_ur, fileID=s_fileID)       #  Удельные расходы
        read_tab(conn, 'calcTemperatures', map_tr, fileID=s_fileID)  #  Расчетные температуры
        read_tab(conn, 'varCoefficients', map_kv, fileID=s_fileID)   # Коэффицтенты вариации
        read_tab(conn, 'externalCodes', map_rs, fileID=s_fileID)     #  Расчетные схемы

        read_lookup(conn, 'fragments', 'name', map_fragments)
        read_lookup(conn, 'externalCodes', 'name', map_kod)

        read_connectNodes(conn)
        read_node_vn(conn)

        read_node(G, conn, 'nodes')

        read_node2(G, conn, 'heatSources')          #  "Источник тепла",         "Источник тепла", "US_OUT",        

        if not config.args.g_is_avar:   # плановый расчет
            read_node2(G, conn, 'realConsumers')        #  "Потребитель реальный",   "Потребитель реальный", "PT_OUT",  
            read_node2(G, conn, 'generalizedConsumers') #  "Потребитель обобщенный", "Потребитель обобщенный", "PT_OUT",
        else:                           # аварийный
            pass 
            """
            data = {}
            data['typ'] = 'nodes'
            data['id'] = ATMOSPHERE
            data['t'] = 0
            data['p_zn'] = 0
            data['name'] = 'ATMOSPHERE'
            data['nodeName'] = 'ATMOSPHERE'
            data['geoMarkTopTube'] = 0
#            data['fileID'] = fileID

#                if externalCodeID: data['kod'] = kod
#                if externalCodeID: data['externalCodeID'] = externalCodeID
#                if internalNodeID: data['internalNodeID'] = internalNodeID

            G.add_node((ATMOSPHERE, 1), **data, po=1, G=0.)
            """

            if config.args.g_equival:
                read_pt_line(G, conn, 'realConsumers')        #  "Потребитель реальный",   "Потребитель реальный", "PT_OUT",  
            else:
                read_vnutr.read_pt_vnutr(G, conn, 'realConsumers', s_fileID)        #  "Потребитель реальный",   "Потребитель реальный", "PT_OUT",  

            read_pt_line(G, conn, 'generalizedConsumers') #  "Потребитель обобщенный", "Потребитель обобщенный", "PT_OUT",

#            if tn == 'realConsumers':   # Добавляем внутреннюю схему
#                add_pr_vn(G, pr)

        read_node2(G, conn, 'pumpStations')         #  "Насосная станция",       "Насосная станция", "US_OUT",      
        read_node2(G, conn, 'threeWayValves')       #  "Клапан трехходовой",     "Клапан трехходовой", "US_OUT",    

        read_node2(G, conn, 'refillNodes')          #  "Узел подпитки",         "Узлы подпитки и прис.баков-аккумуляторов", NULL,



#    'WDOdevices': tab_WDOdevices,     #       Водоразборный прибор

#Водоразборный прибор

        read_line2(G, conn, 'heatPipeSections')     #  "Участок",     "Участок теплопровода", "UT_OUT", "", -1, -1, -1,
        read_line2(G, conn, 'pumps')                #  "Насос",       "Насосы(насосные станции расчетной схемы", "NS_OUT", "stateID", -1, -1, -1,
        read_line2(G, conn, 'pressRegulators')      #  "Регул. давл.", "Сетевые регуляторы давления", "RS_OUT", "regulatorStateID", -1, -1, -1,
        read_line2(G, conn, 'consumptRegulators')   #  "Регул. расх.", "Сетевые регуляторы расхода", "RS_OUT", "regulatorStateID", -1, -1, -1,
        read_line2(G, conn, 'dampers')              #  "Задвижка",    "Задвижка", "ZD_OUT", "damperArmatureStateID", -1, -1, -1,
        read_line2(G, conn, 'regulArmatures')       #  "Регулирующая арматура", "Регулирующая арматура", "ZD2_OUT", "damperArmatureStateID", -1, -1, -1,
        read_line2(G, conn, 'bypass')               #  "Байпас",      "Байпаc", "BP_OUT", "regulatorStateID", -1, -1, -1,
        read_line2(G, conn, 'diaphragms')           #  "Диафрагма",   "Диафрагма", "DRO_OUT", "stateID", -1, -1, -1,
        read_line2(G, conn, 'elevators')            #  "Элеватор",    "Элеватор", "ANY_OUT", "stateID", -1, -1, -1,
        read_line2(G, conn, 'systemRadiators')      #  "Радиатор",    "Радиатор", "ANY_OUT", "stateID", -1, -1, -1,
        read_line2(G, conn, 'heatExchangers')       #  "Теплообменник","Теплообменник", "ANY_OUT", "stateID", -1, -1, -1,
        read_line2(G, conn, 'airHeaters')           #  "Калориферная установка",  "Калориферная установка", "ANY_OUT", "", -1, -1, -1,
        read_line2(G, conn, 'pressDropRegulators')  #  "Регул. переп.", "Регулятор перепада давления", "RS_OUT", "regulatorStateID", -1, -1, -1,
        read_line2(G, conn, 'reverseValves')        #  "Обратный клапан", "Обратный клапан", "OK_OUT", "stateID", -1, -1, -1,

        read_zn(G, conn)


        read_ist_vn(G, conn, fileID=s_fileID)


        line_poteri(G)

#        print(f'Закончил читать {conn_str["db"]}', file=sys.stderr, flush=True)
        print(f'Закончил читать {db_name}', file=sys.stderr, flush=True)

#        print(map_s07)

#    except:
#        print(f' !!!error!!!')

#    exit(1)

    return G

#-----------------------------------------------------------------------------------

if __name__ == "__main__":
    pass
