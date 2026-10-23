# создано Claude, 2026-10-23: расчет регуляторов давления как уравнений в системе Ньютона (по умолчанию; -rd_old - старый w_rd.check_RD)

import logging

import numpy as np
import scipy as sp

from sety import w_print


# Обработка регуляторов давления: активный регулятор вместо уравнения потерь напора на ветви
# дает уравнение H[узел импульса] = Z, сопротивление вычисляется после решения S = (H1-H2)/(G*|G|).
# Если S вышло за [r1, r2] - регулятор фиксируется на границе (обычное сопротивление) и выводится сообщение.

MAX_PASS = 10        # проходов по набору активных регуляторов
MAX_FLIPS = 3        # переключений одного регулятора, после этого он остается на границе
TOL_H = 0.01         # м, допуск на напор, если delta не задана
FLOW_MIN = 1e-3      # т/ч, расход, ниже которого регулятор считается без расхода
SENS_MIN = 1e-6      # доля перепада на регуляторе, доходящая до узла импульса, ниже - узел не управляется
# Кроме того, регулятор должен на всем диапазоне [r1, r2] сдвигать напор узла импульса хотя бы на допуск:
# |dH/dS|*(r2-r1) >= tol. Иначе (почти нулевой расход) уравнение H = Z вырождает матрицу.

# Индексы в кортеже list_rd (см. w_calc.init_matrix)
I_K_L, I_K_N, I_I1, I_I2, I_N1, I_N2, I_KEY, I_S, I_Z, I_R1, I_R2, I_DELTA = 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13

#------------------------------------------------------

# [Claude 2026-10-23] Записывает сопротивление S регулятора i в list_rd и в ветвь графа.
def set_S(G, list_rd, i, S):
    rd = list(list_rd[i])
    rd[I_S] = S
    list_rd[i] = tuple(rd)

    G.edges[rd[I_N1], rd[I_N2], rd[I_KEY]]['S'] = S

#------------------------------------------------------

# [Claude 2026-10-23] Имя регулятора и узла импульса для сообщений.
def rd_names(G, rd):
    nodeID3, przu3 = rd[0], rd[1]
    e = G.edges[rd[I_N1], rd[I_N2], rd[I_KEY]]
    typ_name = 'Байпас' if e.get('typ') == 'bypass' else 'Регулятор давления'
    namel = w_print.line_name_n1_n2(G, rd[I_N1], rd[I_N2], False)
    namen = w_print.node_name(G, (nodeID3, przu3), False, False)
    geo = G.nodes[(nodeID3, przu3)].get('geoMarkTopTube', 0)
    return typ_name, namel, namen, geo

#------------------------------------------------------

# [Claude 2026-10-23] Регуляторы давления методом активного набора.
#   solve(active) - пересобирает матрицу с активными регуляторами (множество индексов list_rd) и решает Ньютоном,
#                   True - решение получено (root обновлен на месте);
#   jacobian()    - матрица Якоби в текущей точке root без активных регуляторов.
# Перед выходом решает систему без активных регуляторов с найденными S, так что root - обычное решение сети.
# Возвращает (True, сообщения {индекс: текст}) или (False, {}) - тогда root и S восстановлены, нужен старый метод.
def calc_RD_active(G, list_rd, root, solve, jacobian):
    idx = [i for i in range(len(list_rd)) if list_rd[i][I_R1] != list_rd[i][I_R2]]
    if not idx:
        return True, {}

    root0 = root.copy()
    S0 = [rd[I_S] for rd in list_rd]

    # [Claude 2026-10-23] Откат к состоянию на входе.
    def restore():
        root[:] = root0
        for i in range(len(list_rd)):
            set_S(G, list_rd, i, S0[i])

    logging.info(f'== Регуляторы давления (активный набор)')

    if not solve(set()):
        restore()
        return False, {}

    # Чувствительность напора узла импульса к сопротивлению: J*v = e_kl*G|G|, dH/dS = v[k_n]

    try:
        lu = sp.sparse.linalg.splu(sp.sparse.csc_matrix(jacobian()))
    except Exception as ex:
        logging.info(f'  splu: {ex}')
        restore()
        return False, {}

    mode = {}    # 'a' активен, 'r1'/'r2' на границе, 'x' не подбирается
    dirn = {}    # знак dH/dS
    sg0 = {}     # знак расхода через регулятор в исходном решении
    flips = {}
    reason = {}
    owner = {}   # узел импульса -> регулятор

    for i in idx:
        rd = list_rd[i]
        k_l, k_n = rd[I_K_L], rd[I_K_N]
        g = root[k_l]
        flips[i] = 0

        if abs(g) < FLOW_MIN:
            mode[i] = 'x'
            reason[i] = 'нет расхода через регулятор, сопротивление не подбиралось'
            continue

        if k_n in owner:
            mode[i] = 'x'
            reason[i] = f'узел импульса уже регулируется [{rd_names(G, list_rd[owner[k_n]])[1]}], сопротивление не подбиралось'
            continue

        rhs = np.zeros(len(root))
        rhs[k_l] = g * abs(g)
        v = lu.solve(rhs)
        sens = v[k_n]

        S, Z, r1, r2 = rd[I_S], rd[I_Z], rd[I_R1], rd[I_R2]
        tol = max(rd[I_DELTA] or 0., TOL_H)

        if not np.isfinite(sens) or abs(sens) < SENS_MIN * g * g or abs(sens) * (r2 - r1) < tol:
            mode[i] = 'x'
            reason[i] = 'в этом режиме регулятор не влияет на напор в узле импульса (узел питается в обход регулятора)'
            logging.info(f'  {rd_names(G, rd)[1]} G={g} dH/dS={sens} r2-r1={r2 - r1} -> x')
            continue

        owner[k_n] = i
        dirn[i] = np.sign(sens)
        sg0[i] = np.sign(g)
        err = Z - root[k_n]
        need = np.sign(err) * dirn[i]    # куда нужно менять S

        at_r1 = S <= r1
        at_r2 = S >= r2

        if (at_r1 or at_r2) and abs(err) <= tol:
            mode[i] = 'r1' if at_r1 else 'r2'
        elif at_r1 and need < 0:
            mode[i] = 'r1'
        elif at_r2 and need > 0:
            mode[i] = 'r2'
        else:
            mode[i] = 'a'

        logging.info(f'  {rd_names(G, rd)[1]} k_l={k_l} k_n={k_n} i1={rd[I_I1]} i2={rd[I_I2]} G={g} sens/G2={sens / (g * g)} '
                     f'S={S} r1={r1} r2={r2} Z={Z} H={root[k_n]} -> {mode[i]}')

    converged = False

    for p in range(MAX_PASS):
        active = {i for i in idx if mode[i] == 'a'}

        if not active:
            converged = True
            break

        if not solve(active):
            logging.info(f'  отказ на наборе: ' + '; '.join(rd_names(G, list_rd[i])[1] for i in sorted(active)))
            restore()
            return False, {}

        changed = False

        for i in idx:
            rd = list_rd[i]
            k_l, k_n, i1, i2 = rd[I_K_L], rd[I_K_N], rd[I_I1], rd[I_I2]
            Z, r1, r2 = rd[I_Z], rd[I_R1], rd[I_R2]
            tol = max(rd[I_DELTA] or 0., TOL_H)

            if mode[i] == 'a':
                g = root[k_l]
                dh = root[i1] - root[i2]

                # расход упал до нуля или сменил направление - уставка требует закрыть регулятор
                if abs(g) < FLOW_MIN or np.sign(g) != sg0[i]:
                    S_new = np.inf
                else:
                    S_new = dh / (g * abs(g))   # < 0 - нужен подъем напора, регулятор полностью открыт

                if S_new < r1:
                    mode[i] = 'r1'
                    S_new = r1
                elif S_new > r2:
                    mode[i] = 'r2'
                    S_new = r2

                if mode[i] != 'a':
                    flips[i] += 1
                    changed = True
                    logging.info(f'  {p} {rd_names(G, rd)[1]} -> {mode[i]}  G={g} dh={dh}')

                set_S(G, list_rd, i, S_new)

            elif mode[i] in ('r1', 'r2') and flips[i] < MAX_FLIPS and i not in active:
                err = Z - root[k_n]
                need = np.sign(err) * dirn[i]

                if abs(err) > tol and ((mode[i] == 'r1' and need > 0) or (mode[i] == 'r2' and need < 0)):
                    mode[i] = 'a'
                    flips[i] += 1
                    changed = True
                    logging.info(f'  {p} {rd_names(G, rd)[1]} -> a  err={err}')

        if not changed:
            converged = True
            break

    # Итоговое решение без активных регуляторов с найденными S

    if not solve(set()):
        restore()
        return False, {}

    msgs = {}

    if not converged:
        msgs[-1] = f'Регуляторы давления: состояние не установилось за {MAX_PASS} проходов, взяты последние значения сопротивлений'

    for i in idx:
        rd = list_rd[i]
        typ_name, namel, namen, geo = rd_names(G, rd)
        Z = rd[I_Z]
        Zhd = root[rd[I_K_N]]
        tol = max(rd[I_DELTA] or 0., TOL_H)

        txt = None

        if mode[i] == 'x':
            txt = reason[i]
        elif abs(Z - Zhd) > tol and mode[i] in ('r1', 'r2'):
            sost = 'полностью открыт' if mode[i] == 'r1' else 'полностью закрыт (максимальное сопротивление)'
            txt = f'напор не обеспечивается, регулятор {sost}'

        if txt:
            msgs[i] = (f'{typ_name} [{namel}], узел импульса [{namen}]: {txt}. '
                       f'Задано {Z - geo:.2f} м, получено {Zhd - geo:.2f} м')

        logging.info(f'  {namel} {mode[i]} S={rd[I_S]} Z={Z:8.2f} Zhd={Zhd:8.2f}')

    return True, msgs
