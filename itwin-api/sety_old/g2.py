import numpy as np
import math
import networkx as nx
import networkx as nx
import tempfile
import itertools

from collections import defaultdict
from sety.consumption import is_bezelevator
import consumption

from sety import w_data
from sety import w_print
from sety.out.podpitka import n_ras

#------------------------------------------------------------------------------------
# Тут мы записываем, что нужно исправить в PO
#------------------------------------------------------------------------------------


def write_po(G, param_sum, out_file):
    if out_file == '':
        return

#    print(param_sum)

    q = ''

    for p, v in param_sum.items():
        n = G.nodes[p]
        kod = n.get('kod_main', '')
        name = n.get('name_main', '')
        fragment_resultid = n.get('fragment_resultid', -1)

#        print(kod, name, fragment_resultid, v, file=f)

        vv = ','.join(map(str, v))

        cols1 = ''
        cols2 = ''
        vals = ''
        sset = ''

#        for kk, vv in v.items():
#            key = next((kkk for kkk, vvv in w_data.tab_generalizedConsumers.items() if vvv == kk), None)
#            print(kk, vv, key)

        for kk, vv in v.items():
            key = next((kkk for kkk, vvv in w_data.tab_generalizedConsumers.items() if vvv == kk), None)
            if cols1 != '': cols1 += ','
            if cols2 != '': cols2 += ','
            if vals != '': vals += ','
            cols1 += kk


            cols2 += key
            vals += str(vv)
            if sset != '': sset += ',\n'
            sset += f'    {key} = _t.{kk}'
                                           
#        print(cols1)
#        print(cols2)
#        print(vals)
#        exit(0)
        if not kod is None:
            kod = kod.replace('\'', '\'\'')
        if not name is None:
           name = name.replace('\'', '\'\'')

#        print (kk, vv, key, kod, name)

        if name != '' and not name is None:
            if q != '': q += ',\n'
            q += f'''('{kod}','{name}',{fragment_resultid},{vals})'''


#    print('============')
#    print(q)
#    print('============')
    if q == '':
        return


# otoplz,otopln,ventil,gvop,gvoo,gvpr,gvsm,gvps,gvpw

# Создаём временный файл
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
#        temp_file.flush()  # Сохраняем записанные данные
    
        qq =f'''
UPDATE generalizedconsumers
set 
{sset}
from nodes n
join externalcodes ec on ec.id=n.externalcodeid 
join (
    select * from (
values
{q}
) _t (kod, uzel, fileID, {cols1})
) _t on _t.uzel = n.externalnodename and _t.kod=ec.name and n.fileID=_t.fileID

where n.id=generalizedconsumers.nodeid and n.removed = 0
        '''

        # Не удалять!!! Это не отладка!!!
        print(qq, file=temp_file)

        with open(out_file, 'w') as f:
            print(temp_file.name, file=f)


#------------------------------------------------------------------------------------


# Ищем откуда идет вода 

def make_G2(G, param_sum):
#    print('Проверяем фрагмент')
    GG = nx.MultiDiGraph()

    for n1, n2, data in G.edges(data=True):
        ras = data.get('G', 0)
        Y = data.get('Y', 0)

        if ras < 0:
            n1, n2, = n2, n1
            ras = -ras

        if ras < 0.00001:
            continue

        name1 = G.nodes[n1].get('name')
        name2 = G.nodes[n2].get('name')
        po1 = G.nodes[n1].get('po')
        po2 = G.nodes[n2].get('po')

#        print(name1, po1, name2, po2, ras)

        GG.add_edge(n1, n2, G=ras, Y=Y)

#    sources = [node for node in GG.nodes() if GG.in_degree(node) == 0]
#    zn = [node for node in G.nodes() if 'p_zn' in G.nodes[node]]
    zn = [node for node in GG.nodes() if 'p_zn' in G.nodes[node]]  # Список узлов с заданным напором

    if len(zn) == 0:
        return 

    # Смотрим узля с заданным напором, чтобы узнать расход и перепад
#    print('--------')
    for node in zn:
        nodeID, po = node

        nodeP = G.nodes.get((nodeID, 1), None)
        nodeO = G.nodes.get((nodeID, 2), None)

        pihP = nodeP.get('P', None) 
        pihO = nodeO.get('P', None) 


        GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, (nodeID, 1), False)
        GG_O, Gin_O, Gout_O, Gp_O, Gout_O =  n_ras(G, (nodeID, 2), False) 

#        print(pihP, pihO, Gin_P, Gin_O)


        
#    exit(0)

# Участки

#    print('--------------------------------')
    
    for zn0 in zn:
#        print(zn0)
        param_sum[zn0]['tpotepi__pod'] = 0
        param_sum[zn0]['tpotepi__obr'] = 0
    
        param_sum[zn0]['gv_oo'] = 0
        param_sum[zn0]['gv_op'] = 0
        param_sum[zn0]['gv_pr'] = 0
        param_sum[zn0]['gv_ps'] = 0
        param_sum[zn0]['gv_pw'] = 0
        param_sum[zn0]['gv_sm'] = 0
        param_sum[zn0]['otopl_zco'] = 0
        param_sum[zn0]['otopl_nco'] = 0
        param_sum[zn0]['ventil_cv'] = 0

        param_sum[zn0]['otopl_pr'] = 0
        param_sum[zn0]['otopl_ps'] = 0
        param_sum[zn0]['otopl_pw'] = 0
        param_sum[zn0]['otopl_sm'] = 0
        param_sum[zn0]['otopl_tp_zco'] = 0
        param_sum[zn0]['otopl_tp_nco'] = 0

        param_sum[zn0]['cx_zco'] = 0
#        param_sum[zn0]['cx_nco'] = 0

        param_sum[zn0]['cx_co_pr'] = 0
        param_sum[zn0]['cx_co_ps'] = 0
        param_sum[zn0]['cx_co_pw'] = 0
        param_sum[zn0]['cx_co_sm'] = 0

        param_sum[zn0]['Tr_tv_co_pr'] = 18
        param_sum[zn0]['Tr_tv_co_ps'] = 18
        param_sum[zn0]['Tr_tv_co_pw'] = 18
        param_sum[zn0]['Tr_tv_co_sm'] = 18
        param_sum[zn0]['Tr_tv_co_zco'] = 18
        param_sum[zn0]['Tr_tv_co_nco'] = 18


        param_sum[zn0]['Tr_gvs_pw'] = 60
        param_sum[zn0]['Tr_gvs_ps'] = 60
        param_sum[zn0]['Tr_gvs_pr'] = 60
        param_sum[zn0]['Tr_gvs_sm'] = 60
        param_sum[zn0]['Tr_gvs_oo_op'] = 60
        
#    print('--------------------------------')

    distances, paths = nx.multi_source_dijkstra(GG, zn)

    node_to_closest_source = {}
    for node, distance in distances.items():
        # Находим ближайший источник для текущего узла
        min_distance = float('inf')
        zn0 = None
        for source in zn:
            # Если путь от источника существует и является минимальным
            if node in paths and paths[node][0] == source and distances[node] < min_distance:
                min_distance = distances[node]
                zn0 = source

        if zn0 is not None:
            po = G.nodes[node].get('po', '???')
#            print('!!', zn0, G.nodes[node].get('name', '???'), po)
            data = G.nodes[node]

            for k, (n1, n2, key) in itertools.chain(
                    zip(itertools.repeat(1), GG.in_edges(node, keys=True)),
                    zip(itertools.repeat(2), GG.out_edges(node, keys=True))
                    ): 

                '''

                name1 = w_print.node_name(G, n1, False)
                name2 = w_print.node_name(G, n2, False)
                
                l = GG.edges[n1, n2, key]
                ras = l.get('G', 0)
                Y = l.get('Y', 0)
                print('  ', k, ras, Y, name1, name2)
                '''

                
                if k == po:
                    name1 = w_print.node_name(G, n1, False)
                    name2 = w_print.node_name(G, n2, False)

                    l = GG.edges[n1, n2, key]
                    ras = l.get('G', 0)
                    Y = l.get('Y', 0)
#                    print('  ', k, ras, Y, name1, name2)

                    if ras > 0.00001 and True:
#                        print('  ', k, ras, Y, name1, name2)

                        if k == 1:
                            param_sum[zn0]['tpotepi__pod'] += Y
                        else:
                            param_sum[zn0]['tpotepi__obr'] += Y


           
#    exit(0)

# Потребители


    distances, paths = nx.multi_source_dijkstra(GG, zn)

    node_to_closest_source = {}
    for node, distance in distances.items():
        # Находим ближайший источник для текущего узла
        min_distance = float('inf')
        zn0 = None
        for source in zn:
            # Если путь от источника существует и является минимальным
            if node in paths and paths[node][0] == source and distances[node] < min_distance:
                min_distance = distances[node]
                zn0 = source


        if zn0 is not None:

            if G.nodes[node].get('typ', '') == 'realConsumers':
#                print('!!', zn0, node)
                data = G.nodes[node]

                otoplz = data.get('otoplz', 0)
                otopln = data.get('otopln', 0)
                ventil = data.get('ventil', 0)

                gvop = data.get('gvop', 0)
                gvoo = data.get('gvoo', 0)
                
                gvpr = data.get('gvpr', 0)
                gvsm = data.get('gvsm', 0)
                gvps = data.get('gvps', 0)
                gvpw = data.get('gvpw', 0)

                otopl_tp = data.get('otopl_tp', 0)

                cxema = data.get('cxema', '1.1')

                Tr_tv_co = data.get('Tr_tv_co', 18)
                Tr_gvs = data.get('Tr_gvs', 60)
                Tr_gvs_oo_op =  data.get('Tr_gvs_oo_op', 60)

                isEl = not is_bezelevator(cxema)
#                print(cxema)

#                '''
                itog2 = dict()

                def num(otopln, otoplz, isEl):
                    if otoplz > 0 and isEl: return 1
                    if otoplz > 0 and not isEl: return 2
                    return 3


                otop, vent, gv, rez, isEl = '', '', '', '', False
                cx = num(otopln, otoplz, isEl)

                vv = consumption.type_of_cons(cxema)

                if vv:
                    otop, vent, gv, rez, isEl = vv

                itog2['gv_oo'] = 0.0
                itog2['gv_op'] = 0.0
                itog2['gv_pr'] = 0.0
                itog2['gv_ps'] = 0.0
                itog2['gv_pw'] = 0.0
                itog2['gv_sm'] = 0.0
                itog2['otopl_nco'] = 0.0
                itog2['otopl_pr'] = 0.0
                itog2['otopl_ps'] = 0.0
                itog2['otopl_pw'] = 0.0
                itog2['otopl_sm'] = 0.0
                itog2['otopl_tp_zco'] = 0.0
                itog2['otopl_tp_nco'] = 0.0
                itog2['otopl_zco'] = 0.0

                itog2['ventil_cv'] = 0.0


                itog2['cx_co_pr'] = 0
                itog2['cx_co_ps'] = 0
                itog2['cx_co_pw'] = 0
                itog2['cx_co_sm'] = 0

                itog2['cx_zco'] = 0
#                itog2['cx_nco'] = 0

                itog2['Tr_tv_co_pr'] = 18
                itog2['Tr_tv_co_ps'] = 18
                itog2['Tr_tv_co_pw'] = 18
                itog2['Tr_tv_co_sm'] = 18
                itog2['Tr_tv_co_nco'] = 18
                itog2['Tr_tv_co_zco'] = 18

                itog2['Tr_gvs_pw'] = 60
                itog2['Tr_gvs_ps'] = 60
                itog2['Tr_gvs_pr'] = 60
                itog2['Tr_gvs_sm'] = 60
                itog2['Tr_gvs_oo_op'] = 60

#                '''


                if vent != 0:
                    itog2['ventil_cv'] += ventil

                if gvpr != 0:
                    itog2['gv_pr'] += gvpr
                    itog2['otopl_pr'] += otoplz + otopln
                    itog2['cx_co_pr'] = cx
                    itog2['Tr_tv_co_pr'] = Tr_tv_co
                    itog2['Tr_gvs_pr'] = Tr_gvs

#                    cx.pr[cxema_pr-1] += itog2['otopl_pr']+itog2['gv_pr']
#                    cx_tv.pr[cxema_pr-1] += otopl_tp

#                    ttt.pr[pr->Tr_tv_co] += otoplz + otopln
#                    ttt2.pr[pr->Tr_gvs] += otoplz + otopln

                elif gvps != 0:
                    itog2['gv_ps'] += gvps
                    itog2['otopl_ps'] += otoplz + otopln
                    itog2['cx_co_ps'] = cx
                    itog2['Tr_tv_co_ps'] = Tr_tv_co
                    itog2['Tr_gvs_ps'] = Tr_gvs
#                    cx.ps[cxema_pr-1] += itog2['otopl_ps']+itog2['gv_ps']
#                    cx_tv.ps[cxema_pr-1] += otopl_tp

#                    ttt.ps[pr->Tr_tv_co] += otoplz + otopln
#                    ttt2.ps[pr->Tr_gvs] += otoplz + otopln

                elif gvpw != 0:
                    itog2['gv_pw'] += gvpw
                    itog2['otopl_pw'] += otoplz + otopln
                    itog2['cx_co_pw'] = cx
                    itog2['Tr_tv_co_pw'] = Tr_tv_co
                    itog2['Tr_gvs_pw'] = Tr_gvs
#                    cx.pw[cxema_pr-1] += itog2['otopl_pw']+itog2['gv_pw']
#                    cx_tv.pw[cxema_pr-1] += otopl_tp

#                    ttt.pw[pr->Tr_tv_co] += itog2['otopl_pw']
#                    ttt2.pw[pr->Tr_gvs] += otoplz + otopln

                elif gvsm != 0:
                    itog2['gv_sm'] += gvsm
                    itog2['otopl_sm'] += otoplz + otopln
                    itog2['cx_co_sm'] = cx
                    itog2['Tr_tv_co_sm'] = Tr_tv_co
                    itog2['Tr_gvs_sm'] = Tr_gvs
#                    cx.sm[cxema_pr-1] += itog2['otopl_sm']+itog2['gv_sm']
#                    cx_tv.sm[cxema_pr-1] += otopl_tp

#                    ttt.sm[pr->Tr_tv_co] += otoplz + otopln
#                    ttt2.sm[pr->Tr_gvs] += otoplz + otopln
                else:

                    itog2['cx_zco'] = 2 if isEl else 1
                    
                    itog2['otopl_zco'] += otoplz  # /*  на отопление                   */
                    itog2['otopl_nco'] += otopln  # /*  на отопление                   */

                    if otoplz > 0:
                        itog2['otopl_tp_zco'] += otopl_tp
                        itog2['Tr_tv_zco'] = Tr_tv_co

                    if otopln > 0:
                        itog2['otopl_tp_nco'] += otopl_tp
                        itog2['Tr_tv_nco'] = Tr_tv_co

                    itog2['Tr_gvs_'] = Tr_gvs_oo_op



#                    ttt.z[pr->Tr_tv_co] += otoplz
#                    ttt.n[pr->Tr_tv_co] += otopln

                itog2['gv_oo'] += gvoo    # /*  г.в. открытое из обратки       */
                itog2['gv_op'] += gvop    # /*  г.в. открытое из подачи        */


                param_sum[zn0]['gv_oo'] +=             itog2['gv_oo']
                param_sum[zn0]['gv_op'] +=             itog2['gv_op']
                param_sum[zn0]['gv_pr'] +=             itog2['gv_pr']
                param_sum[zn0]['gv_ps'] +=             itog2['gv_ps']
                param_sum[zn0]['gv_pw'] +=             itog2['gv_pw']
                param_sum[zn0]['gv_sm'] +=             itog2['gv_sm']

                param_sum[zn0]['ventil_cv'] +=         itog2['ventil_cv']

                param_sum[zn0]['otopl_zco'] +=         itog2['otopl_zco']
                param_sum[zn0]['otopl_nco'] +=         itog2['otopl_nco']
                param_sum[zn0]['otopl_pr'] +=          itog2['otopl_pr']
                param_sum[zn0]['otopl_ps'] +=          itog2['otopl_ps']
                param_sum[zn0]['otopl_pw'] +=          itog2['otopl_pw']
                param_sum[zn0]['otopl_sm'] +=          itog2['otopl_sm']
                param_sum[zn0]['otopl_tp_zco'] +=      itog2['otopl_tp_zco']
                param_sum[zn0]['otopl_tp_nco'] +=      itog2['otopl_tp_nco']

                if gv == 'pr':
                    param_sum[zn0]['cx_co_pr'] =      itog2['cx_co_pr']
                    param_sum[zn0]['Tr_tv_co_pr'] =   itog2['Tr_tv_co_pr']
                    param_sum[zn0]['Tr_gvs_pr'] =   itog2['Tr_gvs_pr']
                if gv == 'ps':
                    param_sum[zn0]['cx_co_ps'] =      itog2['cx_co_ps']
                    param_sum[zn0]['Tr_tv_co_ps'] =   itog2['Tr_tv_co_ps']
                    param_sum[zn0]['Tr_gvs_ps'] =   itog2['Tr_gvs_ps']
                if gv == 'pw':
                    param_sum[zn0]['cx_co_pw'] =      itog2['cx_co_pw']
                    param_sum[zn0]['Tr_tv_co_pw'] =   itog2['Tr_tv_co_pw']
                    param_sum[zn0]['Tr_gvs_pw'] =   itog2['Tr_gvs_pw']
                if gv == 'sm':
                    param_sum[zn0]['cx_co_sm'] =      itog2['cx_co_sm']
                    param_sum[zn0]['Tr_tv_co_sm'] =   itog2['Tr_tv_co_sm']
                    param_sum[zn0]['Tr_gvs_sm'] =   itog2['Tr_gvs_sm']

                if not gv in ('sm', 'pr', 'ps', 'pw') and otop == 'z':
                    param_sum[zn0]['cx_zco'] =      itog2['cx_zco']
                    param_sum[zn0]['Tr_tv_co_zco'] =   itog2['Tr_tv_co_zco']

                if not gv in ('sm', 'pr', 'ps', 'pw') and otop == 'n':
#                    param_sum[zn0]['cx_nco'] =      itog2['cx_nco']
                    param_sum[zn0]['Tr_tv_co_nco'] =   itog2['Tr_tv_co_nco']

                if gv in ('op', 'oo'):
                    param_sum[zn0]['Tr_gvs_oo_op'] =   itog2['Tr_gvs_oo_op']

                itog2['Tr_tv_co_pr'] = 0
                itog2['Tr_tv_co_ps'] = 0
                itog2['Tr_tv_co_pw'] = 0
                itog2['Tr_tv_co_sm'] = 0
                itog2['Tr_tv_nco'] = 0
                itog2['Tr_tv_zco'] = 0


#    for zn0 in zn:
#        print(param_sum[zn0])


#    for p, v in param_sum.items():
#        print(p, v)

#    exit(0)

#    print('Закончили проверять фрагмент')

    return param_sum
    




def make_G2_leto(G, out_file):
#    print('Проверяем фрагмент')
    GG = nx.MultiDiGraph()

    for n1, n2, data in G.edges(data=True):
        ras = data.get('G', 0)
        Y = data.get('Y', 0)

        if ras < 0:
            n1, n2, = n2, n1
            ras = -ras

        if ras < 0.00001:
            continue

        name1 = G.nodes[n1].get('name')
        name2 = G.nodes[n2].get('name')
        po1 = G.nodes[n1].get('po')
        po2 = G.nodes[n2].get('po')

#        print(name1, po1, name2, po2, ras)

        GG.add_edge(n1, n2, G=ras, Y=Y)

#    sources = [node for node in GG.nodes() if GG.in_degree(node) == 0]
#    zn = [node for node in G.nodes() if 'p_zn' in G.nodes[node]]
    zn = [node for node in GG.nodes() if 'p_zn' in G.nodes[node]]  # Список узлов с заданным напором

    if len(zn) == 0:
        return 

    # Смотрим узля с заданным напором, чтобы узнать расход и перепад

    val = ''

    for node in zn:
        nodeID, po = node

        nP = G.nodes.get((nodeID, 1), None)
        nO = G.nodes.get((nodeID, 2), None)

#        print(nP, nO)

        if nP is None or nO is None: 
            continue

        pihP = nP.get('P', None) 
        pihO = nO.get('P', None) 


        GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, (nodeID, 1), False)
        GG_O, Gin_O, Gout_O, Gp_O, Gout_O =  n_ras(G, (nodeID, 2), False) 

        kod = nO.get('kod_main', '')
        name = nO.get('name_main', '')
        fragment_resultid = nO.get('fragment_resultid', None)



        if ((kod == '' or kod is None) and (name == '' or name is None) ) or fragment_resultid is None:
            continue

        S = (pihP-pihO) / math.pow(Gin_P, 2)

#        print(pihP, pihO, Gin_P, Gin_O)
        val += f'''('{kod}','{name}',{fragment_resultid},{S})'''

    if val == '':
        return

    qq = f'''

UPDATE generalizedconsumers
set 

hydroResCloseSysSummer = 
case when closeSysCalcSignID <> 2 then s_summer
else hydroResCloseSysSummer
end
from nodes n
join externalcodes ec on ec.id=n.externalcodeid 
join (
    select * from (
values
{val}
) _t (kod, uzel, fileID, s_summer)
) _t on _t.uzel = n.externalnodename and _t.kod=ec.name and n.fileID=_t.fileID

where n.id=generalizedconsumers.nodeid and n.removed = 0

'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as temp_file:
        # Не удалять!!! Это не отладка!!!
        print(qq, file=temp_file)

        with open(out_file, 'w') as f:
            print(temp_file.name, file=f)


