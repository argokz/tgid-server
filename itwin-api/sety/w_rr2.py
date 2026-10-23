# создано Claude, 2026-10-23: регуляторы расхода (и байпасы как регуляторы расхода) уравнениями в системе Ньютона;
# -rr_old - прежний w_rr.check_RR (подкачка Z в узлы + ветвь S = 10000)

import logging

import numpy as np

from sety import w_print


# Состояния регулятора (st['mode'][i], i - индекс в list_rr):
#   'a'  - работает: в системе уравнение G = Z, сопротивление S = (H1-H2)/(Z|Z|) после решения;
#   'r1' - полностью открыт (S = r1), 'r2' - полностью закрыт (S = r2): обычное сопротивление.
# Начальное состояние - 'r1': регулятор включается в работу, только если полностью открытый пропускает больше Z,
# поэтому тупик (расхода нет) не получает принудительный расход.

RR_MAX_FLIPS = 4     # переключений одного регулятора, дальше остается в текущем состоянии
FLOW_MIN = 1e-3      # т/ч, расход, ниже которого считается, что расхода нет

# Индексы в кортеже list_rr (см. w_calc.init_matrix)
I_N1, I_N2, I_I1, I_I2, I_K_L, I_S, I_Z, I_R1, I_R2, I_KEY = range(10)

#------------------------------------------------------

# [Claude 2026-10-23] Допуск на расход регулятора: delta из базы, не меньше 0.1 % уставки и 0.01 т/ч.
def rr_tol(G, rr):
    e = G.edges[rr[I_N1], rr[I_N2], rr[I_KEY]]
    return max(e.get('delta', 0.) or 0., 0.001 * abs(rr[I_Z]), 0.01)

#------------------------------------------------------

# [Claude 2026-10-23] Записывает сопротивление S регулятора i в list_rr и в ветвь графа.
def set_S(G, list_rr, i, S):
    rr = list(list_rr[i])
    rr[I_S] = S
    list_rr[i] = tuple(rr)

    G.edges[rr[I_N1], rr[I_N2], rr[I_KEY]]['S'] = S

#------------------------------------------------------

# [Claude 2026-10-23] Начальное состояние: все регуляторы полностью открыты. Возвращает состояние st,
# st['active'] - множество работающих регуляторов (передается в make_matrix как rr_active, меняется на месте).
def init_RR(G, list_rr):
    st = {'mode': ['r1'] * len(list_rr), 'flips': [0] * len(list_rr), 'active': set()}

    for i in range(len(list_rr)):
        set_S(G, list_rr, i, list_rr[i][I_R1])

    return st

#------------------------------------------------------

# [Claude 2026-10-23] Пересмотр состояний регуляторов по решению root. Работающий: требуемое сопротивление вне
# [r1, r2] -> на границу. На границе: открытый пропускает больше Z или закрытый меньше Z -> снова в работу.
# Возвращает True, если состояние изменилось (у работающего другая строка матрицы - нужен make_matrix(first=True)).
def check_RR(G, list_rr, root, st):
    changed = False

    logging.info(f'== Регуляторы расхода (уравнения)')

    for i in range(len(list_rr)):
        rr = list_rr[i]
        k_l, i1, i2, Z, r1, r2 = rr[I_K_L], rr[I_I1], rr[I_I2], rr[I_Z], rr[I_R1], rr[I_R2]

        if Z == 0:
            continue

        sz = np.sign(Z)
        g = root[k_l] * sz            # расход в сторону уставки
        dh = (root[i1] - root[i2]) * sz
        za = abs(Z)
        tol = rr_tol(G, rr)
        mode = st['mode'][i]
        new = mode

        if mode == 'a':
            S_req = dh / (za * za)

            if S_req < r1:
                new = 'r1'      # перепада не хватает даже полностью открытому
            elif S_req > r2:
                new = 'r2'      # даже полностью закрытый пропускает больше Z
            else:
                set_S(G, list_rr, i, S_req)

        elif st['flips'][i] < RR_MAX_FLIPS:
            if (mode == 'r1' and g > za + tol) or (mode == 'r2' and g < za - tol):
                new = 'a'

        if new != mode:
            if mode != 'r1' or st['flips'][i] or new != 'a':
                st['flips'][i] += 1   # первое включение из начального 'r1' не считается

            st['mode'][i] = new
            changed = True

            if new == 'a':
                st['active'].add(i)
            else:
                st['active'].discard(i)
                set_S(G, list_rr, i, r1 if new == 'r1' else r2)

            logging.info(f'  {w_print.line_name_n1_n2(G, rr[I_N1], rr[I_N2], False)}: {mode} -> {new}  G={g} Z={za} dh={dh}')

    return changed

#------------------------------------------------------

# [Claude 2026-10-23] Сообщения о регуляторах, не обеспечивших расход (по итоговому решению root). {индекс: текст}
def messages(G, list_rr, root, st):
    msgs = {}

    for i in range(len(list_rr)):
        rr = list_rr[i]
        Z = rr[I_Z]
        mode = st['mode'][i]

        if mode == 'a' or Z == 0:
            continue

        g = root[rr[I_K_L]] * np.sign(Z)
        za = abs(Z)

        if abs(g - za) <= rr_tol(G, rr):
            continue

        if mode == 'r1' and abs(g) < FLOW_MIN:
            txt = 'нет расхода через регулятор (тупик или нет перепада)'
        elif mode == 'r1':
            txt = 'расход не обеспечивается, регулятор полностью открыт'
        else:
            txt = 'расход больше заданного, регулятор полностью закрыт'

        e = G.edges[rr[I_N1], rr[I_N2], rr[I_KEY]]
        typ_name = 'Байпас' if e.get('typ') == 'bypass' else 'Регулятор расхода'
        name = w_print.line_name_n1_n2(G, rr[I_N1], rr[I_N2], False)

        msgs[i] = f'{typ_name} {name}: {txt}. Задано {za:.1f} т/ч, получено {g:.1f} т/ч'

    return msgs
