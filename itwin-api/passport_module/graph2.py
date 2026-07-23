import networkx as nx
import numpy as np

# Ваш исходный мультиграф
#G = nx.Graph()  # или nx.MultiGraph() если важно
# Добавьте сюда ваши узлы и рёбра


def unite(G):
    # Получение всех компонентов связности
    components = [G.subgraph(c).copy() for c in nx.connected_components(G)]

    # Функция для вычисления евклидова расстояния
    def euclidean_distance(node1, node2):
        x1, y1 = G.nodes[node1]['pos']
        x2, y2 = G.nodes[node2]['pos']
        return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

    len_comp = len(components)

    # Объединение графов
    while len(components) > 1:
        min_dist = float('inf')
        best_edge = None

        # Найти минимальное расстояние между компонентами
        for i in range(len(components)):
            for j in range(i + 1, len(components)):

                for node1 in components[i].nodes:
                    for node2 in components[j].nodes:
                        dist = euclidean_distance(node1, node2)
                        if dist < min_dist:
                            min_dist = dist
                            best_edge = (node1, node2)


            # Добавить минимальное ребро
        if best_edge:
            G.add_edge(best_edge[0], best_edge[1], po=1, diam='11111')

            components = [G.subgraph(c).copy() for c in nx.connected_components(G)]

