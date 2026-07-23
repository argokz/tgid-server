import sys
import time
import networkx as nx
import numpy as np
import scipy as sp

from sety import w_print

from sety.any.colors import cprint
from sety.any.colors import nbsp


#----------------------------------------------------------------------------------------------    
# Устанавливаем источники
#----------------------------------------------------------------------------------------------    

#----------------------------------------------------------------------------------------------    


def set_descendant(G, n0, n_source):
    reachable_nodes = nx.descendants(G, n0)

#    print(reachable_nodes)

#    print('------------- set_descendant', n0, )

#    n_source, po = n_source

    G.nodes[n0]['src'] = {n_source}

#    print('(((((((', n0, G.nodes[n0], '<<===', n_source)

    for n in reachable_nodes:
        if G.nodes.get(n, None) is None: 
            continue

        G.nodes[n]['src'] = {n_source}
#        print('(((((((', n, G.nodes[n], '<<===', n_source)

#----------------------------------------------------------------------------------------------    


def check_GG(G, podacha_obratka):
    
#    print('Начинаем проверку')
    for n, attr in G.nodes(data=True):
#        internalNodeID = attr.get('internalNodeID', 0)
#        if internalNodeID != 0: 
#            continue


        n, po = n


#        po = attr.get('po', 0)

#        print('--', n, po)
        
        
        if po != podacha_obratka: 
            continue


        set_src = attr.get('src', set())

#        print( attr)
#            print(n, po, attr)

        if len(set_src) > 1: 
            in_edges = G.in_edges((n, po))
            out_edges = G.out_edges((n, po))
    


            if len(in_edges) < 2:
                continue

            max_in = 0

            ras_max = -1
            src_max = None

#            print('===================')
            name = w_print.node_name(G, (n, po), False) 
#            print(name)

            for e in in_edges:
                ee = G.edges[e]
                src = ee.get('src', set())
                ras = abs(ee.get('ras', 0))

#                print('    ras = ', ras, ' src= ', src)

                if ras > ras_max:
                    ras_max = ras
                    src_max = next(iter(src))

#                   print(f'||| {src=} {ras=} {src_max=}')
                    
                max_in = max(max_in, len(src))

            max_out = 0
                
            for e in out_edges:
                ee = G.edges[e]
                src = ee.get('src', set())
                max_out = max(max_out, len(src))


            if max_out > max_in:
#                print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
#                print(attr)

#                for e in in_edges:
#                    print('  <-', G.edges[e])
#                for e in out_edges:
#                    print('  ->', G.edges[e])

#                print('!!!!!  set_descendant', src_max)

                set_descendant(G, (n, po), src_max)

#----------------------------------------------------------------------------------------------    

# Функция для поиска всех рёбер, через которые проходит поток из исходных узлов
def mark_flow_edges(G, source, node, po):
    
#    print('mark_flow_edges', source, node, po)

    nodeIst = G.nodes.get((node, po))

    if not nodeIst:
        return;


    nist = nodeIst.get('ist')

    if not nist:
        return

#    print('mark_flow_edges', nist)
        

    marked_edges = set()
    visited = set()
    queue = [(node, po)]
    
    while queue:
        current_node = queue.pop(0)


        if 'src' not in G.nodes[current_node]:
            G.nodes[current_node]['src'] = set()

#        G.nodes[current_node]['src'].add(source)
        G.nodes[current_node]['src'].add(nist)

        # Для каждого соседа текущего узла
        for neighbor in G.successors(current_node):
            edge = (current_node, neighbor)
            
            # Если ребро ещё не отмечено
            if edge not in marked_edges:
                marked_edges.add(edge)  # Отмечаем ребро
                queue.append(neighbor)  # Добавляем узел в очередь для дальнейшего поиска

                if 'src' not in G.edges[edge]:
                    G.edges[edge]['src'] = set()

                G.edges[edge]['src'].add(source)
                

#-----------------------------------------------------------------------------------

def add_edge(G, u, v, lineID, po, ras):

    if G.has_edge(u, v):
        # Если ребро существует, добавляем вес
        current_ras = G[u][v].get('ras', 0)
        new_ras = current_ras + ras
        G[u][v]['ras'] = new_ras
#        print(f"Ребро между {u} и {v} обновлено. {current_ras} + {ras} = {new_ras}")
#        print(G.nodes[u], G.nodes[v], v)

    elif G.has_edge(v, u):
        # Если ребро существует, отнимаем вес
        current_ras = G[v][u].get('ras', 0)
        new_ras = current_ras - ras
        if new_ras < 0:
            # Если новый вес меньше 0, разворачиваем ребро
            G.remove_edge(v, u)
            G.add_edge(u, v, ras=-new_ras, key=(lineID, po), po=po)
#            print(f"Ребро между {u} и {v} развёрнуто. {current_ras} - {ras} = {-new_ras}")
        else:
            # Если вес не меньше 0, просто обновляем его
            G[v][u]['ras'] = new_ras
#            print(f"Ребро между {u} и {v} обновлено. {current_ras} - {ras} = {new_ras}")
#            print(G.nodes[v], G.nodes[u], v)

    else:
        # Если ребра нет, добавляем новое с весом ras
        G.add_edge(u, v, ras=ras, key=(lineID, po), po=po)



#        print(G.nodes[u], G.nodes[v], v)


#        print(f"Добавлено новое ребро между {u} и {v} с весом: {ras}")



#-----------------------------------------------------------------------------------



def check_ist3(G, root, podacha_obratka):
#    GG = nx.MultiDiGraph()
    GG = nx.DiGraph()

    set_ist = set()

#    if podacha_obratka == 1:
#        cprint(f'Проверка подачи', color='b')
#    else:
#        cprint(f'Проверка обратки', color='b')

    for nn in G.nodes:
        n = G.nodes[nn]
#        id = n['nodeID']
#        po = n['po']
        id, po = nn

        typ = n['typ']
        ist0 = n.get('ist0', None) # Источник

        if not ist0 and po == 2:
            nP = G.nodes.get((id, 1))
            if nP:
                ist0 = nP.get('ist0', None) # Источник

        name = w_print.node_name(G, nn, False) 
#        GG.add_node((id, po), name=name, typ=typ)

        data = {}

        data['name'] = n.get('name', '')
        if id: data['id'] = id
#        if externalCodeID: data['kod'] = kod
#        if externalCodeID: data['externalCodeID'] = externalCodeID
#        if internalNodeID: data['internalNodeID'] = internalNodeID
#        if fileID: data['fileID'] = fileID
#        if uzel is None: uzel = ''

        if ist0:
            data['ist'] = ist0

        GG.add_node((id, po), **data, typ=typ)

#        if po == podacha_obratka and not ist0 is None:
        if not ist0 is None:
            set_ist.add((ist0, id, po))
#            set_ist.add(id)
#            print(name, ist0, id, po)
#            print(n)

    kk = 1


    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]
        k_l = e['num']
        sost = e.get('sost', 1)

        g = root[k_l]

        if podacha_obratka == 2:
#            n1, n2 = n2, n1
            g = -g

        if g < 0:
            n1, n2 = n2, n1

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        i1, p1 = n1
        i2, p2 = n2

        lineID = k_l

           
        externalSignLineID = e.get('externalSignLineID', 0)

        if sost != 2 and abs(g) > 0.00001 and p1 == podacha_obratka: # and externalSignLineID in (1, 2, 4):
            add_edge(GG, (i1, p1), (i2, p2), lineID, podacha_obratka, g)
            kk += 1


    for ist0, node, po in set_ist: 
#        print('=============================')
#        print(G.nodes[node])
#        ist = G.nodes[(node, podacha_obratka)]['ist0']

#        print('()()', node, po)

        ist_node = G.nodes.get((node, po))
        if not ist_node:
            continue

#        print(ist_node)
        ist = ist_node.get('ist0', None)

        if not ist:
            continue


        if po != podacha_obratka:
            continue

#        print(node, ist)
#        print('-----------------------------')
#        nnn1 = GG.nodes.get((node, 1), None)
#        print(nnn1)
#        nnn2 = GG.nodes.get((node, 2), None)
#        print(nnn2)

        try:
            reachable_nodes = nx.descendants(GG, (node, podacha_obratka))

#            print('=', podacha_obratka, ist, reachable_nodes)

            for n, po in reachable_nodes:
                node1 = G.nodes.get((n, po), None)

                if node1 is None: 
                    continue

                name = w_print.node_name(G, (n, po), False) 

                qq = ''
                ist_old = node1.get('ist', -1)


                if ist_old > 0 and False:

                    out_edges = G.out_edges((n, po), data=True)
                    in_edges = GG.in_edges((n, po), data=True)

#                    print('**', n, po, name, ist, ist_old)
#                    print(node1)

                    for n1, n2, data in in_edges:
#                        print((n, po), n1, n2)
                        n1n, p1p = n1
                        node2 = G.nodes.get((n1n, p1p), None)
                        name = w_print.node_name(G, (n1n, p1p), False) 
#                        print('    ', name, data.get('ras'), node2.get(ist, -1))
                        
#                        print('    ', name, node2.get(ist, -1), data.get('ras'))

#                    print(out_edges)

                
                node1['ist'] = ist

#                print(name, ist)

                
    #            zn = G.nodes[n].get('zn', -1)
    #            if zn > 0:
    #                print(G.nodes[n])
        except Exception as ex:
            print('Error', ex)



    for ist0, node, po in set_ist: 
#    for ist in set_ist:
#        print(ist, podacha_obratka)
        mark_flow_edges(GG, ist0, node, po)
#        mark_flow_edges(GG, (ist, podacha_obratka))

    check_GG(GG, podacha_obratka)

#    print('-----------------')

    # Вывод всех рёбер с атрибутами
#    for u, v, data in GG.edges(data=True):
#        print(f"{u} -> {v}, атрибуты: {data}")
#    exit(1)




    for (nodeID, po), attr in GG.nodes(data=True):
        src = attr.get('src', set()) 
        src0 = src

        
#        if len(src) > 0 and 'internalNodeID' not in attr:
        if len(src) > 0:

            name = w_print.node_name(G, (nodeID, po), False) 

#            if len(src) > 1:
#                print(name, nodeID, po, src)
        
            set_src = attr.get('src', set()) 
            if po == podacha_obratka:

                src = next(iter(set_src))

                srcID = src
#                srcID, po = src
                
                if not src is None:
#                    if podacha_obratka == 1: print(nodeID, srcID)
                    
#                    srcID, po = src
                    srcID = src

                    nnGG = GG.nodes.get((nodeID, podacha_obratka), None)
                    
                    nn = G.nodes.get((nodeID, podacha_obratka), None)
                    if not nn is None:

#                        if podacha_obratka == 2:
#                            print(nn)
                        
#                        print('!!!   ', srcID)

                        nn['heatSourceID'] = srcID

                        out_edges = GG.out_edges(nnGG)

                        for u, v, data in GG.out_edges((nodeID, podacha_obratka), data=True):
                            e = GG.edges[u, v]

                            if G.has_edge(u, v):
                                for k in G[u][v]:   # k — ключ конкретного ребра                                    
                                    G[u][v][k]['heatSourceID'] = srcID

                            elif G.has_edge(v, u):
                                for k in G[v][u]:   # k — ключ конкретного ребра                                    
                                    G[v][u][k]['heatSourceID'] = srcID

                            else:
                                print(f'Нет ребра между {u} и {v}')
                                    

#                            print(f"..... {u} -> {v}, атрибуты: {data}")


#                        for nn1, nn2 in GG.out_edges(nnGG):
#                            print(e)


#    exit(1)
#                        if qq2 != '': qq2 += ','

#                        nn['src'] = srcID
#                        print(src, nn)

#    print('--------------------------------')
#    print(qq2)
#    print('--------------------------------')




