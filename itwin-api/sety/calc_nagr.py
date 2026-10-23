import numpy as np
import scipy as sp
import networkx as nx
import itertools

import logging
import traceback


from collections import defaultdict

from sety.any.colors import cprint
from sety import w_print
from sety import config


#------------------------------------------------

# [Claude, 2026-08-24] Уравнение деления нагрузки между параллельными
# трубами (ниже, при n_P > 1) кодирует пропорцию load_A/load_B = GG_A/GG_B
# коэффициентами matrix[ii,*] = ±GG. Если у обеих параллельных труб расход
# почти нулевой одновременно (типичный случай, когда решатель не может
# однозначно поделить расход между похожими параллельными трубами), эти
# коэффициенты — тоже почти ноль, при том что в остальной матрице стоят
# коэффициенты порядка 1 (см. matrix[ii, i1] = sign чуть выше) — строка
# получается на 5+ порядков меньше соседних, отсюда и "Matrix is exactly
# singular" в spsolve. NAGR_LOAD_EPS — нижний порог по модулю для этих
# коэффициентов: для реальных (не почти нулевых) расходов ничего не меняет
# (sqrt(GG^2+eps^2) ~= |GG| при |GG| >> eps), а у вырожденных пар не даёт
# коэффициенту провалиться в ноль. Порог взят на два порядка выше порога
# отсечения "нулевого" расхода (0.00001) чуть ниже по коду, чтобы покрыть и
# пограничные случаи прямо над этим порогом.
NAGR_LOAD_EPS = 1e-3

# порог "нулевого" расхода на участке (см. init_matrix_nagr)
NAGR_ZERO_G = 0.00001


# [Claude 2026-10-22] Перемычка подача->обратка: участок между узлами подачи и обратки, по которому вода
# (расход g по направлению n1->n2) идет из подачи в обратку.
def is_jumper(n1, n2, g):
    if n1[1] == n2[1]:
        return False
    src = n1 if g > 0 else n2
    return src[1] == 1

# [Claude 2026-10-18] Сглаженный |v| со знаком: sign(v)*sqrt(v^2+eps^2) - не дает коэффициенту упасть в ноль.
def _smooth_gg(v):
    return np.sign(v) * np.sqrt(v * v + NAGR_LOAD_EPS * NAGR_LOAD_EPS)


# [Claude 2026-10-18] Нагрузка узла потребителя для расчета нагрузок по участкам: b101 - суммарная, b102 - отопление,
# b103 - вентиляция, b104 - ГВС закрытое, b105 - ГВС из подачи, b106 - ГВС из обратки.
# Для узла обратки - со знаком минус; для прочих узлов 0.
def getQ(G, n, b101):
#    n_nodes = G.number_of_nodes()

    node = G.nodes[n]
    nn, po = n

    Q = 0
    typ = node['typ']


    if typ in ('generalizedConsumers', 'realConsumers'):

#        print(typ, name)
#        if typ != 'generalizedConsumers':
#            print(typ)
#            exit(1)

        nn, po = n
    
        nodeP = node
        
#        if po == 2:
        nodeP = G.nodes.get((nn, 1), None)

        Qot =   0
        Qgvz =  0
        Qgvp =  0
        Qgvo =  0
        Qvent = 0
        
        if not nodeP is None:
            Qot =   nodeP.get('Qot0', 0)
            Qgvz =  nodeP.get('Qgvz0', 0)
            Qgvp =  nodeP.get('Qgvp0', 0)
            Qgvo =  nodeP.get('Qgvo0', 0)
            Qvent = nodeP.get('Qvent0', 0)

        Q = Qot + Qgvz + Qgvp + Qgvo + Qvent

#        print(f'{Q} = {Qot} + {Qgvz} + {Qgvp} + {Qgvo} + {Qvent}')

        if b101 == 'b101':
            Q = Q
        elif b101 == 'b102':
            Q = Qot
        elif b101 == 'b103':
            Q = Qvent
        elif b101 == 'b104':
            Q = Qgvz

#            if po == 1:
#                Q += Qgvp

        elif b101 == 'b105':
            Q = Qgvp

        elif b101 == 'b106':
            Q = Qgvo

        if po == 2:
            Q = -Q

    return Q

#------------------------------------------------

from itertools import combinations

# [Claude, 2026-08-24] Раньше строились ВСЕ пары C(n,2) — при 3+ параллельных
# трубах из одного узла это лишнее: если зафиксированы отношения A/B и B/C,
# то A/C уже следует из них, третье уравнение избыточно. C(n,2) вместо n-1
# независимых уравнений давало на некоторых узлах больше строк, чем
# n_lines (столбцов) — система переопределялась, последняя строка не
# помещалась в выделенный размер и обрубалась предохранителем
# "if ii >= n_lines: break" в init_matrix_nagr → пустая строка → сингулярная
# матрица. Обнаружено на реальном фрагменте с узлами, где нарисовано 3+
# параллельных трубы (astanagid_2026_03_17, fileID 3165). "Звезда" от первой
# ветки ко всем остальным (n-1 пар) — минимальный независимый набор,
# для n=2 (обычный случай) даёт ту же единственную пару, что и раньше.
# [Claude 2026-10-18] Пары ключей словаря d для уравнений пропорций ('звезда' от первого ключа ко всем остальным),
# каждая пара - словарь из двух элементов.
def get_pairs(d):
    keys = list(d.keys())
    if len(keys) < 2:
        return []
    first = keys[0]
    pairs = [(first, k) for k in keys[1:]]

    # превращаем в словари
    result = [{k: d[k] for k in pair} for pair in pairs]

    return result

#    for item in result:
#        print(item)

# [Claude 2026-10-18] Возвращает первый и второй элементы (ключ, значение) словаря-пары.
def get_from_item(result):
    item1 = None
    item2 = None
    for i, item in enumerate(result.items()):
        if i == 0:
            item1 = item
        else:
            item2 = item
            
    return item1, item2



# [Claude 2026-10-18] Строит разреженную систему для распределения нагрузок b101 по участкам при известных расходах x:
# баланс нагрузки в узлах (кроме одного опорного на компоненту связности) и пропорции нагрузок
# в параллельных ветвях по их расходам. Возвращает (матрица csc, правая часть).
# [Claude 2026-10-22] Матрица от вида нагрузки не зависит, от него зависит только правая часть (getQ).
# b101 может быть списком видов - тогда правая часть - массив (n_lines, len(b101)), по столбцу на вид,
# и матрица строится один раз на все виды.
def init_matrix_nagr(G, x, b101):

    keys = (b101,) if isinstance(b101, str) else tuple(b101)

#    nn = 100000
    n_nodes = G.number_of_nodes()
    n_lines = G.number_of_edges()

    # [Claude, 2026-08-24] Раньше матрица была (n_lines+n_ist) x (n_lines+n_ist):
    # под каждый источник (t0) резервировался лишний столбец-неизвестная
    # (matrix[ii, n_lines-1+n_ist0] = 1, см. ниже), но уравнения, которое бы
    # её ограничивало, никто не писал — соответствующая строка так и
    # оставалась полностью нулевой. Реально записываемых строк (по узлу +
    # по параллельным трубам) ровно n_lines, лишние n_ist строк в конце были
    # всегда пустые -> "Matrix is exactly singular" в spsolve, причём
    # регулярно (это не про близкие к нулю параллельные трубы — та находка
    # была про другое и уже пофикшена отдельно через _smooth_gg). Столбцы
    # с индексами n_lines-1+n_ist0 нигде и не читались (calc_nagr1 достаёт
    # результат только по l['i1'] = k_l - n_nodes, обычным edge-неизвестным),
    # так что просто убрал лишний размер и запись в эти столбцы.
    n_ist = 0

    beta0 = np.zeros((n_lines, len(keys)))
    matrix = sp.sparse.lil_array((n_lines, n_lines))

#    print(f'{n_lines=} {n_nodes=} {n_ist=}')

    # [Claude, 2026-08-24] Настоящая причина периодических сингулярных матриц
    # (найдена на реальном фрагменте astanagid_2026_03_17/3165): число строк,
    # которые писал код (по 1 на узел + по узлам с несколькими параллельными
    # трубами), не обязано совпадать с n_lines (числом рёбер/столбцов) — это
    # была ничем не обоснованная посылка. По теории графов для связной
    # компоненты с V узлами независимых узловых уравнений баланса ровно V-1,
    # не V — одно всегда линейно зависит от остальных (аналог: сумма токов по
    # всей схеме равна нулю тождественно, включая любой один "опорный" узел).
    # Раньше уравнение писалось для всех V узлов без исключения — на 1 лишнее
    # (независимое) уравнение на каждую отдельную компоненту связности.
    # Ниже помечаем по одному "опорному" узлу на компоненту (произвольный,
    # неважно какой) — для него не пишем его собственную строку баланса (её
    # смысл уже гарантированно следует из остальных узлов этой же компоненты),
    # но его строки под параллельные трубы (n_P>1, если есть) всё равно
    # пишутся как обычно — это независимая информация, к балансу узла
    # отношения не имеющая.
    #
    # [Claude 2026-10-22] Опорный узел "по одному на компоненту" (выше) на реальной схеме не работает
    # (astanagid_2026_09_22, fileID 3179): источник в графе - перемычка обратка->подача, и по правилу
    # знаков она - приток в обоих своих узлах; участок с нулевым расходом входил в балансы обоих узлов
    # с коэффициентом +1; перемычка подача->обратка не была притоком ни в одном узле. Число уравнений
    # не совпадало с числом участков, матрица была вырожденной, на большой подсети нагрузки участков
    # получались до 4 раз больше суммарной нагрузки потребителей.
    # Теперь:
    # - нагрузка = 0 для участка с нулевым расходом и для перемычки подача->обратка (за ней потребителей нет);
    #   в балансы узлов они не входят;
    # - перемычка источника (обратка->подача) - приток только в узле подачи;
    # - баланс пишется для каждого узла, в который есть приток (n_P > 0); узел без притока - исток
    #   (источник, узел за участком с нулевым расходом), для него баланс не пишется.
    # Каждый участок с расходом - приток ровно в одном узле, поэтому уравнений
    # (нагрузка = 0) + (балансы узлов с притоком) + (пропорции, n_P - 1 на узел) ровно n_lines,
    # и при обходе против потока каждая нагрузка определяется однозначно.
    zero_lines = []

    for n1, n2, l in G.edges(data=True):
        if abs(x[l['num']]) < NAGR_ZERO_G or is_jumper(n1, n2, x[l['num']]):
            zero_lines.append(l['num'] - n_nodes)

    ii = 0

    for i1 in zero_lines:
        matrix[ii, i1] = 1
        ii += 1

    for n in G.nodes:
        node = G.nodes[n]
        nn, po = n

        k_n = G.nodes[n]['num']
        typ = node['typ']

        zn = False
        if node.get('p_zn', None):
            zn = True

        t0 = False
        if node.get('t0', None):
            t0 = True

        if ii >= n_lines + n_ist:
            break

        row = {}   # строка баланса узла: пишется после цикла, если в узел есть приток

#        print('(((((((((((((((((((((((((')

        Gin = defaultdict(float)
        Gout = defaultdict(float)

        GG_P = 0
        GG_O = 0
        n_P = 0
        n_O = 0

#        print('-------------------')
#        print(name, f'{Q=:.1f}')

        lst_G = []

        for k, (n1, n2, key) in itertools.chain(
                zip(itertools.repeat(1), G.in_edges(n, keys=True)),
                zip(itertools.repeat(2), G.out_edges(n, keys=True))
                ):


            l = G.edges[n1, n2, key]

            l_typ = l['typ']

            k_l = l['num']
            GG = x[k_l]

#            print('.........', k, po, GG, n1, n2)
            if k == 2:
                GG = -GG
                n1, n2 = n2, n1

            if GG > 0 and po == 1 or GG < 0 and po == 2:
                n0 = n2
            else:
                n0 = n1

#            n0 = n2

            sign = 1 if GG > 0 else -1

#            if po == 1 or po == 1:
#                print('>>>>>>>>>>>>>>>', sign, po, GG, name1, name2, ' == ', name0)

            if abs(GG) > 0.00001: yes = True

            if po == 2:
                sign = -sign

#            i1 = G.nodes[n0]['num']
            i1 = k_l - n_nodes

            l['i1'] = i1

            if abs(GG) < NAGR_ZERO_G or is_jumper(n1, n2, GG):   # нагрузка = 0, уравнение записано выше
                continue

            if po == 2 and n1[1] != n2[1]:   # перемычка источника - приток только в узле подачи
                continue

            row[i1] = row.get(i1, 0) + sign

#            print(f'{matrix[ii, i1]=:.0f} {ii=} {i1=} {GG=:.2f} {sign=}')

            lst_G.append(GG)

            if sign > 0:
                n_P += 1
                GG_P += GG
                Gout[i1] = GG

            if sign < 0:
                n_O += 1
                GG_O -= GG
                Gin[i1] = GG

#            if zn:
#            [Claude, 2026-08-24] запись в лишний столбец-источник убрана вместе
#            с самими столбцами выше — см. комментарий у аллокации matrix/beta0.

        if n_P > 0:   # без притока - исток, баланс не пишется
            for i1, sign in row.items():
                matrix[ii, i1] = sign
            beta0[ii] = [getQ(G, n, k) for k in keys]
            ii += 1

        if n_P > 1:
#            print('>>>>>>>>>>>P', ii)
            result = get_pairs(Gout)

#            print('(((', name, n_P, lst_G)

            for i, item in enumerate(result):
                item1, item2 = get_from_item(item)

                matrix[ii, item1[0]] = _smooth_gg(item2[1])
                matrix[ii, item2[0]] = -_smooth_gg(item1[1])

                beta0[ii] = 0
                ii += 1

        if n_O > 1 and False:
#            print('>>>>>>>>>>>O', ii)
            result = get_pairs(Gin)
            for i, item in enumerate(result):
                item1, item2 = get_from_item(item)

                matrix[ii, item1[0]] = 1
                matrix[ii, item2[0]] = -1

                beta0[ii] = 0
                ii += 1
            



        # Тут добавляем все сходящиеся

#        if n_P > 1:
#            print(f'{name} {k=} {n_P=} {GG_P=:.2f}')
#            print(map_P)

#        matrix[ii, ] = 



#    matrix[n_nodes, 0] = 1
#    ii += 1

#    print(f'=== {n_nodes=} {n_lines=} {ii=}')
#    exit(-1)

#    w_print.print_matrix(matrix, beta0)
#    exit(1)


    # [Claude 2026-10-22] Регуляризация диагонали (DIAG_REG) перенесена в regularize() и применяется
    # только если матрица без нее не раскладывается: система теперь невырождена по построению,
    # а DIAG_REG сдвигал нагрузки на ~1e-3.

    matrix = sp.sparse.csc_array(matrix)

#    print(ii, n_nodes)
#    w_print.print_matrix(matrix, beta0)

    if isinstance(b101, str):
        return matrix, beta0[:, 0]
    return matrix, beta0


error345 = False

# b101 - суммарная, b102 - отопление, b103 - вентиляция, b104 - ГВС закрытое, b105 - ГВС из подачи, b106 - ГВС из обратки
NAGR_KEYS = ('b101', 'b102', 'b103', 'b104', 'b105', 'b106')


# [Claude 2026-10-22] Сообщение об ошибке расчета нагрузок - один раз за запуск.
def nagr_error():
    global error345
    if not error345:
        error345 = True
        cprint('Ошибка при расчете нагрузок по участкам', color='red')


# [Claude 2026-10-22] Записывает нагрузку |t| в атрибут b101 ребер (участки с i1 из init_matrix_nagr).
def set_nagr(G, t, b101):
    for n1, n2, l in G.edges(data=True):
        i1 = l.get('i1', -1)

        if i1 >= 0 and abs(t[i1]) < 10000:
            l[b101] = abs(t[i1])


# [Claude, 2026-08-24] Тот же приём, что и в teplo1.py::init_matrix_teplo —
# "diag==0 -> eps" не ловит "плавающие" пары узлов, связанные только друг
# с другом (их собственная диагональ ненулевая, вырожден весь блок 2x2).
# DIAG_REG добавляется к диагонали каждой строки, а не только нулевой.
# [Claude 2026-10-22] Запасной вариант для матрицы, которая не раскладывается (calc_nagr_all).
NAGR_DIAG_REG = 1e-6

def regularize(matrix):
    eps = 0.00000000001

    diag = matrix.diagonal()
    d = diag + NAGR_DIAG_REG
    d[d == 0] = eps

    return sp.sparse.csc_array(matrix + sp.sparse.diags_array(d - diag))


# [Claude 2026-10-18] Решает систему init_matrix_nagr и записывает нагрузку |t| в атрибут b101 ребер.
# Ошибки перехватываются, сообщение печатается один раз за запуск.
def calc_nagr1(G, x, b101):
    calc_nagr_all(G, x, (b101,))


# [Claude 2026-10-22] Все виды нагрузки keys за одно построение матрицы и одно LU-разложение
# (раньше - 6 построений и 6 разложений одной и той же матрицы). Если матрица не раскладывается,
# раскладывается регуляризованная (regularize); если и она - каждый вид решается через spsolve.
# Идея - от Даниила (копия D:\Qt\gid8_d\sety), переписано под текущую init_matrix_nagr.
def calc_nagr_all(G, x, keys=NAGR_KEYS):
    try:
        matrix, beta = init_matrix_nagr(G, x, keys)
    except Exception as e:
        nagr_error()
        return

    t = None
    for m in (matrix, regularize(matrix)):
        try:
            t = sp.sparse.linalg.splu(m, permc_spec='COLAMD').solve(beta)
            break
        except RuntimeError:
            matrix = m

    for j, key in enumerate(keys):
        try:
            tj = t[:, j] if t is not None else sp.sparse.linalg.spsolve(matrix, beta[:, j])
            set_nagr(G, tj, key)
        except Exception as e:
            nagr_error()


# [Claude 2026-10-18] Для планового расчета считает нагрузки по участкам по всем видам b101-b106.
def calc_nagr(G, x):
#    return
    if not config.args.g_is_avar:   # плановый расчет
        calc_nagr_all(G, x)
