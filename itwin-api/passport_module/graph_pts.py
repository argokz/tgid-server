# Р Р°Р·Р±РёРІР°РµС‚ СѓС‡Р°СЃС‚РєРё РЅР° СѓС‡Р°СЃС‚РєРё РџРўРЎ

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

debug = True
debug = False

def pts_neighbors(G, node):

#    if debug:
#        print('-----------------------------------------------')
#        print('0>>', G.nodes[node])

    pts = -1

    for n1, n2, attr in G.edges(node, data=True):
        pts1 = attr.get('pts_id', -1)
#        if debug:
#            print('    >>>>', pts)
        if pts1 != -1:
            pts = pts1
            
    return pts

def set_neighbors_1(G, node, pts):

    if debug:
        print('-----------------------------------------------')
        print('    ПТС>>', pts, G.nodes[node])

    pts0 = pts

    n_ob = 0
    n_P = 0
    n_O = 0

    pts_old = -1

    for n1, n2, key, attr in G.edges(node, data=True, keys=True):
        e = G.edges[(n1, n2, key)]
        po = attr.get('po', -1)

        if po == 1: n_ob += 1
        elif po == 2: n_P += 1
        elif po == 3: n_O += 1


    if n_P == 0 and n_O == 0:
        for n1, n2, key, attr in G.edges(node, data=True, keys=True):
            e = G.edges[(n1, n2, key)]
            po = attr.get('po', -1)
            pts_old = e.get('pts_id', -1)

            if debug:
                print('1       ????', pts, G.edges[(n1, n2, key)])

            if po == 1:   # Общий участок
                n_ob += 1
                if pts_old == -1:
                    pts += 1
                    G.edges[(n1, n2, key)]['pts_id'] = pts
                    if debug:
                        print('1       >>>>', pts, G.edges[(n1, n2, key)])

        if debug:
            print('1 pts=', pts)

        return pts


#        elif po == 2: n_P += 1
#        elif po == 3: n_O += 1


    for n1, n2, key, attr in G.edges(node, data=True, keys=True):
        e = G.edges[(n1, n2, key)]
        po = attr.get('po', -1)
        pts_old = e.get('pts_id', -1)

#        print('        ?????', pts, G.edges[(n1, n2, key)])

        if po == 1:   # Общий участок
            n_ob += 1
            if pts_old == -1:
                pts += 1
                G.edges[(n1, n2, key)]['pts_id'] = pts
                if debug:
                    print('-       >>>>', pts, G.edges[(n1, n2, key)])

    if debug:
        print('-----')

    for n1, n2, key, attr in G.edges(node, data=True, keys=True):
        e = G.edges[(n1, n2, key)]
        po = attr.get('po', -1)
        n_next = n1 if n2 == node else n2

        if po != 1:   # Не общий узел
#            e = G.edges[n1, n2]
            edges = G.get_edge_data(n1, n2)
                                        
            pts1 = -1
            for edge in edges:
                e = G.edges[n1, n2, edge]
                pts1 = e.get('pts_id', pts1)

            if pts1 != -1:
                pass
#                pts = pts1
            else:
                pts += 1
                pts1 = pts

            for edge in edges:
                e = G.edges[n1, n2, edge]
#                pts1 = e.get('pts_id', pts1)
                e['pts_id'] = pts1


    for n1, n2, key, attr in G.edges(node, data=True, keys=True):
        e = G.edges[(n1, n2, key)]
        po = attr.get('po', -1)
        pts_old = e.get('pts_id', -1)

#        print('        >>>>', pts, G.edges[(n1, n2, key)])


#    print('-----------------------------------------------')

    if debug:
      print('5 pts=', pts)

    return pts

def set_neighbors_2(G, node, pts):

    if debug:
        print('-----------------------------------------------')
        print('    ТР >>', pts, G.nodes[node])

    for n1, n2, key, attr in G.edges(node, data=True, keys=True):
        G.edges[(n1, n2, key)]['pts_id'] = pts
        if debug:
            print('        >>>>', pts, G.edges[(n1, n2, key)])

    return pts + 1

def graph_pts(G):
    components = list(nx.connected_components(G))
    sorted_edges = []

    next_pts = 0

    for component in components:

        # Строим подграф для текущей компоненты
        subgraph = G.subgraph(component)

        visited = set()
        start_node = next(iter(component))
        stack = [start_node]

        while stack:
            # Берем любое ребро из этой компоненты

            node = stack.pop()
            if node not in visited:
                visited.add(node)

                n_pts = pts_neighbors(G, node)  # Получаем ПТС из соседних узлов 

                node_pts = G.nodes[node]['pts']

                if n_pts == -1:  # первый узел в компоненте
                    if debug:
                        print('!!---------------------------------')
                    next_pts += 1
                    n_pts = next_pts   # 


                if debug:
                    print(f'(((((( next_pts {next_pts} n_pts = {n_pts}')

                if node_pts == 1: # ПТС
                    next_pts = set_neighbors_1(subgraph, node, next_pts)
                else:
                    set_neighbors_2(subgraph, node, n_pts)

                if debug:
                    print(f')))))) next_pts {next_pts} n_pts = {n_pts}')
                    


                neighbors = G.edges(node, data=True)

                for n1, n2, v in G.edges(node, data=True):
                    n_next = n2 if n1 == node else n1

                    stack.append(n2 if n1 == node else n1)


    nodes12 = defaultdict(set)

#    exit(0)


    if debug: print('===========')

#    exit(0)
    for node, data in G.nodes(data=True):
        node_pts = data['pts']
        if node_pts == 1: 
            
            if debug: 
                print('---------------')
                print(G.nodes[node])    

#            for n1, n2, key, data in G.edges(node, data=True, keys=True):
#                print(n1, n2, key, data)
#            exit(0)
            
            for n1, n2, key, data in G.edges(node, data=True, keys=True):
                if G.nodes[node]['pts'] == 1:
                    if debug: print(data)
                    l_pts = data['pts_id']

                    if debug: print(l_pts, '->', G.nodes[node])
                    nodes12[l_pts].add(node)
#    '''

    if debug: print('===========')

    if debug:
        for k, v in nodes12.items():
            print(k)
            for n in v:
                print('    ', G.nodes[n])
  
        exit(0)
#    '''

    return nodes12
#    print(nodes12)

