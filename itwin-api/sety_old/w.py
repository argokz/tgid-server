import networkx as nx
import pyodbc
import datetime
import sys
import os
import logging
import itertools

from sety.any.any import argpath_2

from sety.any import connect
#from . import w_data
from sety import read_gid
from sety import w_calc
from sety import w_print
from sety import w_out2

from sety import config
from sety.any import db2

from sety.sprav import read_sprav

from sety.any import any

from sety import dross1
from sety.ct import get_ct

from sety.b5.b5 import open_b5
from sety.any.colors import cprint

map_fragments = {}
map_kod = {}

G = nx.MultiDiGraph()
#G = nx.MultiGraph()

def print_kol_char(G):

    if not config.args.is_char_sety:
        return

    nl = 0
    nrd = 0
    nrr = 0
    ns = 0
    mp = 0
    mo = 0
    nu = 0
    zd = 0
    dr = 0
    ro = 0
    el = 0
    to = 0
    ku = 0
    ok = 0
    bp = 0

    nu1 = 0
    nu2 = 0

    for n in G.nodes:
        typ = G.nodes[n]['typ']
        po = G.nodes[n]['po']

        ll = 0

        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ): 

            ll += 1

            if k == 1:
                l = G.edges[n1, n2, key]

                l_typ = l['typ']

#               print(n1, n2, l_typ)

                nu += 1

                if l_typ == 'heatPipeSections':
                    nl += 1
                elif l_typ == 'pressRegulators':
                    nrd += 1
                elif l_typ == 'consumptRegulators':
                    nrr += 1
                elif l_typ == 'pumps':
                    if l.get('externalSignLineID')  != 6:
                        ns += 1
                elif l_typ == 'dampers':
                    zd += 1
                elif l_typ == 'reverseValves':
                    ok += 1
                elif l_typ == 'bypass':
                    bp += 1
                elif l_typ == 'VN':
                    ku += 1
                elif l_typ == 'TO':
                    to += 1
                elif l_typ == 'SO':
                    ro += 1
                elif l_typ == 'EL':
                    el += 1
                elif l_typ == 'DR':
                    dr += 1
                elif l_typ in ('OO', 'OP', 'ZD', 'UT'):
                    pass
                else:
                    print(l_typ)
                    exit(0)

        if ll > 0:
            if po == 1:
                mp += 1
            else:
                mo += 1

#           print(n, G.nodes.get(n, None).get('name', None))


    print('кол-во узлов сети на подающем трубопроводе.........' , mp)
    print('кол-во узлов сети на обратном трубопроводе.........' , mo)
    print('кол-во участков сети...............................' , nl)
    print('кол-во регуляторов давления сети...................' , nrd)
    print('кол-во регуляторов расхода сети....................' , nrr)
    print('кол-во байпасов....................................' , bp)
    print('кол-во насосных станций (насосов) сети.............' , ns)
    print('кол-во задвижек сети...............................' , zd)
    print('кол-во обратных клапанов...........................' , ok)

    if config.args.g_is_avar:
        print('кол-во дроссельных органов сети....................' , dr)
        print('кол-во гидравлических трактов отопительных приборов' , ro + el)
        print('кол-во гидравлических трактов теплообменников......' , to)
        print('кол-во гидравлических трактов колориферов..........' , ku)

    print('кол-во циклов сети.................................' , nu - (mp + mo) + 1)


#-----------------------------------------------

def ispr_xy(x):
#    x = int(x*100)
    return x

def ispr_xy2(x):
#    x = int(x*100)
    return x

#-----------------------------------------------

def water2():
#    conn = connect.connect('AlmatyGID')
    conn = connect.connect('AstanaGID')

    G = nx.MultiDiGraph()

    if conn:
        read_gid.read_fragments(G, conn, 'fragments', 'name')
        read_gid.read_kod(G, conn, 'externalCodes', 'name')

        read_gid.read_connectNodes(conn)
        
        read_gid.read_node_vn(conn)

        read_gid.read_node_id(G, conn, 'nodes', 'externalCodeID', 'externalNodeName')
        read_gid.read_line_id(G, conn, 'linesobj')

#    except:
#        print(f' !!!error!!!')

    return G

#-----------------------------------------------

def check(G):
    """
    for (p, d) in G.nodes(data=True):
#        if d['name'] == '2':
        if d['name'] == '234':
            p1 = p
        if d['name'] == '34556':
            p2 = p
            """
      
#    print(nx.node_connected_component(G, p1))
#    print(nx.node_connected_component(G, p2))
#    print('!!!!!!')

    for i in nx.weakly_connected_components(G):
        if len(i) > 1:
            n0 = next(iter(i))

            if True:
#            if G.nodes[n0].get('internalNodeID', None) is None:
                print('L:', len(i))

                print(w_print.node_name(G, n0, True))

                for n in i:
                    print(w_print.node_name(G, n, False))

#                print()
#    print(p1, p2)

#    l = nx.dijkstra_path(G,p1,p2)
#    for pp in l:
#        print(pp, G.nodes[pp]['name'])

#-----------------------------------------------

'''
1 Магистральные сети АлЭС (ЦЭР-ВЭР-ЗЭР-СЭР)
2 ВЭР ,3 СЭР,4 ЦЭР,5 ЮЭР,41 СВЭР Жумабаева 36Б,42 СВЭР Толстого,6б
43 СВЭР ТП Алтай,72 ЗЭР,73 CЗЭР
'''
'''
2 Автономные котельные 2017-2018г.г.,
3 Пар, 4 тм-1, 5 тм-2, 6 тм-3, 7 тм-4, 8 тм-5, 9 тм-6, 10 тм-7, 11 тм-8, 12 тм-9, 13 тм-10, 14 тм-11, 15 тм-12,
16 тм-13, 17 тм-17, 18 тм-18, 19 тм-19, 20 тм-20, 21 тм-21, 22 тм-22, 23 тм-23, 24 тм-24, 25 тм-248,1, 26 тм-25,
27 тм-26, 28 тм-27, 29 тм-28, 30 тм-29, 31 тм-30, 32 тм-31, 33 тм-32, 34 тм-33, 35 тм-34, 36 тм-36, 37 тм-37,
38 тм-38, 39 тм-39, 40 тм-43, 41 тм-44, 42 тм-45, 43 тм-46, 44 тм-47, 45 тм-48, 46 тм-50, 48 тм-52, 
49 Железнодорожный, 50 Интернациональный, 51 Мичурино, 52 Пригородный (общая схема), 54 Промышленный, 55 УПТК, 
58 Магистрали 2021-2022,
801 тм-51,
806 Энергетик_только для расчета сопел по удельным,
2149 Магистрали 2022-2023 без прироста,
3150 Магистрали 2022-2023 без прироста импортирован 14-02-2023 10:18 импортирован 10-,
3151 Магистрали 2023-2024 без прироста,
3152 Фрагмент от 23-06-2023 13:53:40
'''


def save(G, file_name):
    for node in G.nodes:
        for attrib in G.nodes[node]:
            if G.nodes[node][attrib] is None:
                G.nodes[node][attrib] = 0
#            if type(G.node[node][attrib]) == dict:
#                print node



    nx.write_graphml(G, file_name, edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)


def run(**db):
    if sys.platform == 'win32':
        import ctypes

        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

        os.system('color')

    log_date = str(datetime.datetime.today().strftime("%Y_%m_%d"))
    logging.basicConfig(filename=f'{argpath_2()}/{log_date}.log',
                    level=logging.INFO, filemode='a+')

    logging.info('-----------------')
    logging.info(db)

    open_b5()

#    FORMAT = '%(asctime)s %(clientip)-15s %(user)-8s %(message)s'
#    logging.basicConfig(format=FORMAT)
     
#    G = read_gid.read_gid(**db)

    conn = connect.connect(**db)
    if not conn:
        print('Не могу подключиться')
        return
    
    ff = db.get('files')
    db_name = db.get("db")

    fileID = list(ff)[0]


    ff_str = '.'.join([str(x) for x in ff])

    q = f'select id from fragments where id in ({ff_str})'

    if not db2.exists_q(conn, q):
        q = 'select id, name from fragments order by id'
        db2.print_q(sys.stdout, conn, q)
        print('Какая-то ошибка!!!!')
        exit(0)

    if config.args.is_leto:
        cprint('Расчет летнего режима', color='b')
    else:
        if not config.args.g_is_avar:
            cprint('Расчет планового режима, отопительный период', color='b')

        if config.args.g_is_avar and config.args.g_equival:
            cprint('Расчет фактического режима (эквивалентный), отопительный период', color='b')

        if config.args.g_is_avar and not config.args.g_equival:
            cprint('Расчет фактического режима (детализированный), отопительный период', color='b')

    read_sprav(db)


    G = read_gid.read_gid(conn, ff, db_name)


#    G = read_gid.read_gid(**db)
#    G = read_gid.read_gid(db='AlmatyGID', files={1})

    if not G: 
        print('Нет данных для расчета')
        exit(0)

    ct = get_ct()

    t_or = ct.get('t_or')
    t_vnew = ct.get('t_vnew')
    Tn = config.args.Tn
        

    if (Tn > t_vnew or Tn < t_or) and not config.args.is_leto:
        cprint(f'Температура наружного воздуха должна быть от {t_or} до {t_vnew}', color='red')
        exit(1)

#    print('w_calc.w_calc(G)')
    w_calc.w_calc(G)
#    print('w_out2.w_out(G, conn, fileID)')

    calculationid = w_out2.w_out(G, conn, fileID)


    if config.args.is_dross_yes:
        print('Дроссели')
        dross1.dross(G, conn, calculationid)


    print_kol_char(G)

#    nx.write_graphml(G, 'C:/data/qq.graphml', edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)

    print('\u00A0', flush=True)
    print('Расчет закончен', flush=True)

#    save(G, 'D:/Qt/gid8/python/sety/sety/1/qq.graphml')


#    check(G)

#-----------------------------------------------------------------------------------

if __name__ == "__main__":
    config.init()

    run(db='AstanaGID', files={3151})
    
#    G = read_gid.read_gid(db='AlmatyGID', files={1})
#    G = read_gid.read_gid(db='AstanaGID', files={4})  # тм-1
#    G = read_gid.read_gid(db='AstanaGID', files={3151})
#    G = read_gid.read_gid(db='AstanaGID', 
#        files={2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,48,49,50,51,52,54,55,58,801,806,2149,3150,3151,3152})

