import networkx as nx
import numpy as np
import scipy as sp

from sety import w_print

import logging


# Обработка обратных клапанов
# если расход отрицательный, то закрываем

# [Claude 2026-10-18] Проверка обратных клапанов по решению root: открытый клапан с отрицательным расходом закрывается.
# list_ok - список (индекс ветви, n1, n2, открыт), меняется на месте. Возвращает True, если что-то закрыли (нужен пересчет).
# вставлено Claude, 2026-10-23: reopen=True - закрытый клапан открывается снова, если напор перед ним выше, чем
# за ним, больше чем на OK_DH. Переключений одного клапана не больше OK_MAX_FLIPS, дальше он остается закрытым.
OK_DH = 0.01         # м
OK_MAX_FLIPS = 4

def check_OK(G, list_ok, root, reopen=False):
    ferr = False

    logging.info(f'== Обратные клапаны')

    flips = G.graph.setdefault('ok_flips', {})   # вставлено Claude, 2026-10-23: переключения по k_l

    for i in range(len(list_ok)):
        k_l, n1, n2, is_open = list_ok[i]

        # вставлено Claude, 2026-10-23: повторное открытие закрытого клапана
        if reopen and not is_open and flips.get(k_l, 0) < OK_MAX_FLIPS:
            dh = root[G.nodes[n1]['num']] - root[G.nodes[n2]['num']]
            if dh > OK_DH:
                logging.info(f'Открыли {w_print.line_name_n1_n2(G, n1, n2, False)} dh={dh}')
                list_ok[i] = k_l, n1, n2, True
                flips[k_l] = flips.get(k_l, 0) + 1
                ferr = True
            continue

        if is_open and root[k_l] < 0:
            flips[k_l] = flips.get(k_l, 0) + 1   # вставлено Claude, 2026-10-23
#            if abs(root[k_l]) > 0.0001:
#                print('Закрыли ', w_print.line_name_n1_n2(G, n1, n2), root[k_l])

            if abs(root[k_l]) > 0.0001:
                name = w_print.line_name_n1_n2(G, n1, n2, False)
                logging.info(f'Закрыли {name} {root[k_l]}')

            is_open = False
            list_ok[i] = k_l, n1, n2, is_open
            ferr = True

        if is_open and root[k_l] > 0:
            pass
#            print('Открыто ', w_print.line_name_n1_n2(G, n1, n2), root[k_l])

    return ferr