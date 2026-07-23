import os
import psycopg2 as pyodbc
import traceback
from collections import defaultdict

import networkx as nx

import config
import connect
from psycopg2.extensions import connection as Connection
import math

import graph2
import graph_pts

#------------------------------------------------------------------------------------------

def euclidean_distance(node1, node2):
    x1, y1 = G.nodes[node1]['pos']
    x2, y2 = G.nodes[node2]['pos']
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

#------------------------------------------------------------------------------------------

def dfs_with_priority(G, start_node, weight_name):
    visited = set()
    stack = [start_node]
    sorted_edges = []

    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)
            
            # Получаем все смежные рёбра и сортируем по весу (по убыванию)
            neighbors = G.edges(node, data=True)
            sorted_neighbors = sorted(neighbors, key=lambda x: x[2][weight_name], reverse=True)
            
            for neighbor in sorted_neighbors:
                edge = (neighbor[0], neighbor[1])
                if edge not in sorted_edges and tuple(reversed(edge)) not in sorted_edges:
                    sorted_edges.append(edge)
                    stack.append(neighbor[1] if neighbor[0] == node else neighbor[0])

    return sorted_edges

# Модифицированный DFS с приоритетом на рёбрах и сохранением порядка узлов
def dfs_with_ordered_edges(G, start_node, weight_name):
    visited = set()  # посещенные узлы
    visited_e = set()  # посещенные ребра
    stack = [start_node]  # стек для обхода
    sorted_edges = []  # результат с правильным порядком рёбер

    while stack:
        node = stack.pop()
        if node not in visited:
            visited.add(node)

            # Получаем все смежные рёбра и сортируем по весу (по убыванию)

            neighbors = G.edges(node, data=True)

            sorted_neighbors = sorted(neighbors, key=lambda x: x[2][weight_name], reverse=True)

            for neighbor in sorted_neighbors:
                next_node = neighbor[1] if neighbor[0] == node else neighbor[0]
                
                # Если соседний узел не был посещен, добавляем ребро и продолжаем обход
                if next_node not in visited:
                    edge_data = G.get_edge_data(neighbor[0], neighbor[1])

                    key, val = next(iter( edge_data.items() )) 

                    id = val.get('id')
                    pts = val.get('pts_id')

                    if id in visited_e:
                        continue

                    nodeID1 = val.get('nodeID1')
                    nodeID2 = val.get('nodeID2')

                    visited_e.add(id)

                    napr = (neighbor[0] == nodeID1)
                    sorted_edges.append((node, next_node, id, napr, pts))

#                    print(G.nodes[node], G.nodes[next_node],  napr)

                    stack.append(next_node)

#    exit(0)
    return sorted_edges

#------------------------------------------------------------------------------------------

def sort_graph(G):
    components = list(nx.connected_components(G))
    sorted_edges = []

    for component in components:
        # Строим подграф для текущей компоненты
        subgraph = G.subgraph(component)

        end_nodes = [node for node, degree in subgraph.degree() if degree == 1]

        if len(end_nodes) > 0:
            start_node = next(iter(end_nodes))

            max_weight = -float('inf')
            nodes_with_max_weight = []

            for node in end_nodes:
                # Концевой узел будет связан только с одним узлом, получаем его
                neighbor = list(G.neighbors(node))[0]
                # Получаем вес ребра

                edge_data = G.get_edge_data(node, neighbor)

                key, v = next(iter( edge_data.items() )) 
                weight = v['diam']

#                weight = edge_data[0]['diam']
                
                if weight > max_weight:
                    max_weight = weight
                    nodes_with_max_weight = [node]
                    start_node = node
                elif weight == max_weight:
                    nodes_with_max_weight.append(node)

        else:
            # Берем любое ребро из этой компоненты
            start_node = next(iter(component))

#        print('!', start_node)
        
        # Выполним поиск в глубину (DFS) для получения отсортированных рёбер
        dfs_edges = list(dfs_with_ordered_edges(subgraph, start_node, 'diam'))

        # Добавляем рёбра в общий список
        sorted_edges.extend(dfs_edges)

    return sorted_edges

#------------------------------------------------------------------------------------------

#    print("Отсортированные рёбра:", sorted_edges)

def make_graph(conn, fragments, ms_rs, ms_rs_id):

    ms_rs_q = '(1=1)'
    if ms_rs == 'ms':
        ms_rs_q = f'(hps.magistralSite={ms_rs_id})'
    else:
        ms_rs_q = f'(hps.distSite={ms_rs_id})'

    if fragments != '':
        fr = f'(n1.fileID in ({fragments}))'
    else:
        fr = f'(1=1)'


    q = f'''
select
l.id, l.externalSignLineID, l.nodeID1, l.nodeID2,

n1.externalNodeName as name1,
n2.externalNodeName as name2,

n1.x as n1_x, 
n1.y as n1_y, 
n2.x as n2_x, 
n2.y as n2_y, 


case when n1.nodeName is null or n1.nodeName = '' then 0 else 1 end as pts1,
case when n2.nodeName is null or n2.nodeName = '' then 0 else 1 end as pts2,

hps.diameterCondit as diam,
hps.magistralSite as ms,
hps.distSite as rs

from linesobj l
join heatPipeSections hps on hps.lineID=l.id
join nodes n1 on n1.id=l.nodeID1 and n1.removed=0
join nodes n2 on n2.id=l.nodeID2 and n2.removed=0
where l.removed=0
and ({fr})
and n1.internalNodeID is NULL
and {ms_rs_q}
    '''

#    print(q)
#    exit(0)

    G = nx.MultiGraph()

    cursor = conn.cursor()
    cursor.execute(q)

    while True:
        row = cursor.fetchone()
        if not row: break
#        print(row)
        (id, po, nodeID1, nodeID2,
            name1, name2,

            n1_x, n1_y, n2_x, n2_y, 
            pts1, pts2, diam, ms, rs) = row

        G.add_edge(nodeID1, nodeID2, key=id, id=id, 
            nodeID1=nodeID1, nodeID2=nodeID2, 
            name1=name1, name2=name2,
            diam=diam, po=po)
        G.nodes[nodeID1]['pts'] = pts1
        G.nodes[nodeID2]['pts'] = pts2

        G.nodes[nodeID1]['name'] = name1
        G.nodes[nodeID2]['name'] = name2

        G.nodes[nodeID1]['pos'] = (n1_x, n1_y)
        G.nodes[nodeID2]['pos'] = (n2_x, n2_y)


#    pts_nodes = [node for node, degree in G.degree() if degree != 2]

#    for node, degree in G.degree():
#        pts_nodes

    for node, degree in G.degree():
#        if degree != 2:
#            G.nodes[node]['pts'] = 1
#        else:
#            for n1, n2, key, attr in G.edges(node, data=True, keys=True):
#                po = attr.get('po', -1)
#                if po != 1:
#                    G.nodes[node]['pts'] = 1
#                    break

        deg = 0
            
        for n1, n2, key, attr in G.edges(node, data=True, keys=True):
            po = attr.get('po', 1)
            if po == 1:
                deg  += 2
            else:
                deg += 1

        if deg != 4 and deg != 3:
            G.nodes[node]['pts'] = 1
#            print(deg, '===', G.nodes[node])
                


    nodes12 = graph_pts.graph_pts(G)

    sorted_edges = sort_graph(G)

    nodes123 = {}

#    print('-------------------')

    for nodeID1, nodeID2, id, napr, pts in sorted_edges:

#        print(nodeID1, nodeID2, id, napr, pts)
        pts_nodeID1 = None
        pts_nodeID2 = None
        
        node12 = nodes12.get(pts)
        node12 = list(node12)

        if len(node12) >= 1:
            pts_nodeID1 = node12[0]

            if len(node12) == 2:
                pts_nodeID2 = node12[1]

                if pts_nodeID1 == nodeID1 or pts_nodeID2 == nodeID2:
                    nodes123[pts] = (pts_nodeID1, pts_nodeID2)
                if pts_nodeID1 == nodeID2 or pts_nodeID2 == nodeID1:
                    nodes123[pts] = (pts_nodeID2, pts_nodeID1)
            elif len(node12) == 1:
                print(f'Кольцо в участке ПТС {pts} {G.nodes[pts_nodeID1]}')
                nodes123[pts] = (pts_nodeID1, pts_nodeID1)
            else:
                print(f'Страшная ошибка {pts}!!!')
                for n in node12:
                    print(G.nodes[n])
                


    graph2.unite(G) 

#    print('-------------------')

#    for k, v in nodes123.items():
#        print(k, v)

#    exit(0)


    mark_line = ''
    ord_l = 1;

    for nodeID1, nodeID2, id, napr, pts in sorted_edges:
        vals = nodes123.get(pts, None)
        if vals is None:
            return
            

        pts_nodeID1, pts_nodeID2 = vals




        if mark_line != '': mark_line += ','

#        mark_line += f"({ord_l}, {id}, {1 if napr else 0}, {pts}, {pts_nodeID1}, {pts_nodeID2})"
        mark_line += f"({ord_l}, {id}, {1 if napr else 0}, {pts})"
        ord_l += 1


    mark_node = ''
    ord_n = 1;

    for nodeID1, nodeID2, id, napr, pts in sorted_edges:
        if mark_node == '': 
            mark_node += f"(1, {nodeID1})"

        mark_node += f",({ord_n+1}, {nodeID2})"
        ord_n += 1


    mark_pts = ''
    ord_p = 1;
    pts_old = -1

    for nodeID1, nodeID2, id, napr, pts in sorted_edges:
        if pts != pts_old:

            pts_nodeID1, pts_nodeID2 = nodes123.get(pts, None)

            if mark_pts != '': mark_pts += ','

            mark_pts += f"({ord_p}, {pts}, {pts_nodeID1}, {pts_nodeID2})"
            ord_p += 1
            pts_old = pts

    return mark_line, mark_node, mark_pts

