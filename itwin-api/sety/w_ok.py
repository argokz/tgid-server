import networkx as nx
import numpy as np
import scipy as sp

from sety import w_print

import logging


# Обработка обратных клапанов
# если расход отрицательный, то закрываем

def check_OK(G, list_ok, root):
    ferr = False

    logging.info(f'== Обратные клапаны')

    for i in range(len(list_ok)):
        k_l, n1, n2, is_open = list_ok[i]

        if is_open and root[k_l] < 0:
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