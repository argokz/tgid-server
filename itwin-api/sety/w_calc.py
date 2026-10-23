import sys
import time
import math  # вставлено Claude, 2026-10-22 (профилирование): для _smooth_loss
import logging  # вставлено Claude, 2026-10-23: для регуляторов давления (-rd_new)
import networkx as nx
import numpy as np
import scipy as sp

from sety.any.dbg import dbg
from collections import defaultdict

#from scipy.sparse.linalg import spsolve

from sety import config
from sety import const

from sety.any.colors import cprint

from sety import w_data


from sety import w_rd
from sety import w_rd2  # вставлено Claude, 2026-10-23: регуляторы давления в системе Ньютона (-rd_new)
from sety import w_rr
from sety import w_rr2  # вставлено Claude, 2026-10-23: регуляторы расхода уравнениями (по умолчанию; -rr_old - старые)
from sety import w_ok

from sety.errors import error_1234

from sety.teplo.teplo1 import calc_teplo
from sety.calc_nagr import calc_nagr

from sety import w_print
from sety import w_out
from sety import g2
from sety.ct import get_ct

from sety import consumption

from sety.out.pt_out import n_ras

NO_ZN_LIST_MAX = 50   # сколько подсетей без узла с заданным напором перечислять в протоколе
from sety.sopr_ut import reset_sopr

from sety.check_ist3 import check_ist3


eps = 0.00000000001

# [Claude, 2026-08-24] Потери давления на трубе/закрытом обратном клапане
# считаются по формуле S*x*|x| (реализовано как S*x^2*sign(x)), у неё
# производная 2*S*|x| ровно обнуляется в x=0 и совсем мала рядом с нулём —
# при почти нулевом расходе (типичная ситуация для одной из двух похожих
# параллельных труб, когда решатель не может однозначно поделить расход
# между ними) диагональ матрицы почти исчезает, и линейная система на этой
# итерации становится плохо обусловленной вплоть до отказа spsolve.
# FLOW_EPS — сглаживание: |x| заменяется на sqrt(x^2 + FLOW_EPS^2), что вдали
# от нуля (|x| >> FLOW_EPS) неотличимо от исходной формулы, а в x=0 даёт
# производную S*FLOW_EPS вместо нуля. Величина взята заведомо маленькой
# относительно реальных расходов (в занесённых по проекту данных наименьшие
# ненулевые величины такого масштаба — тысячные), чтобы не исказить обычный
# (не вырожденный) расчёт.
FLOW_EPS = 1e-6

# [Claude 2026-10-18] Сглаженные потери напора S*x*|x| (|x| ~ sqrt(x^2+eps^2)) и производная для метода Ньютона - без излома в нуле.
# Внимание: возвращаемая производная берется со знаком минус.
def _smooth_loss(S, xk):
    r = math.sqrt(xk * xk + FLOW_EPS * FLOW_EPS)  # исправлено Claude, 2026-10-22: было np.sqrt - медленно на скалярах
    return S * xk * r, -S * (2 * xk * xk + FLOW_EPS * FLOW_EPS) / r


# [Claude 2026-10-18] Заготовка проверки насосов: перебирает насосы, но ничего не проверяет и не меняет (ferr не возвращается).
def check_NS(G, list_ns, root):
    ferr = False

    j = 0

#    logging.info(f'== Насосы')

    for i in range(len(list_ns)):
        k_l, n1, n2, param = list_ns[i]

        name = w_print.line_name_n1_n2(G, n1, n2, False)
        
        rash = abs(root[k_l]) 
#        print(name, rash, list_ns[i])

#    exit(1)


#------------------------------------------------------
# Смотрим если истосник отключен на подаче или обратке

# [Claude 2026-10-18] Для потребителей, у которых в графе есть только подающий или только обратный узел, обнуляет отбор.
# Возвращает False, если такие были (нужен повторный расчет).
def reset_consumptions_PO(G, root):
#    return True


    yes = True

    for n in G.nodes:
        id, po = n

        nP = G.nodes[n]
        
        typ = nP['typ']

        if typ in ('generalizedConsumers', 'realConsumers'):
            numP = nP['num']
            pr = nP
            
            nP = G.nodes.get((id, 1), None)
            nO = G.nodes.get((id, 2), None)

            if nP is None and not nO is None:
                nO['G'] = 0
                nO['Gout'] = 0
                yes = False

            if nO is None and not nP is None:
                nP['G'] = 0
                nP['Gout'] = 0
                yes = False

    return yes

#------------------------------------------------------
# Пересчитываем источники


# [Claude 2026-10-18] Пересчитывает отборы потребителей (реальных и обобщенных) по текущим напорам/температурам через
# consumption_pr/po и записывает их в правую часть beta0 и в узлы ('G', 'Gout'). При отсутствии узла
# обратки - сообщение error_1234 и выход из функции (остальные потребители не пересчитываются).
def reset_consumptions(G, beta0):
#    print('Начали пересчитывать потребители')

    for n in G.nodes:
        id, po = n

        nP = G.nodes[n]
        
        typ = nP['typ']
#        po = nP['po']

        if typ in ('generalizedConsumers', 'realConsumers') and po == 1:
            numP = nP['num']
            
#@            id = nP['nodeID']

            nP = G.nodes.get((id, 1), None)
            nO = G.nodes.get((id, 2), None)

            if nO is None:  
                error_1234(G, (id, 1))
                return

#                exit(1)
#            else:
#                print('OK', nO)

            numO = nO['num']

            pr = nP

            externalNodeName = pr.get('name', '')
            externalCodeID = pr.get('externalCodeID', 0)

            if typ == 'generalizedConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_po(G, pr, externalCodeID, externalNodeName, False)

            if typ == 'realConsumers':
                GZ, GP, GO, Qz, Qp, Qo, pr_out, pr = consumption.consumption_pr(G, pr, externalCodeID, externalNodeName, False, True)

#            print(nP['name'], nP['po'], GZ, GP, GO, Qz, Qp, Qo, pr_out)
#            print(nP['name'], nP['po'], f'{GZ=:.4f} {GP=:.4f} {GO=:.4f}')

            beta0[numP] = GZ+GP
            beta0[numO] = -GZ+GO


            nP['G'] = GZ+GP
            nO['G'] = -GZ+GO

            nP['Gout'] = GP
            nO['Gout'] = GO

            if pr_out: nP |= pr_out
            
#            print(beta0[numP], beta0[numO], nP, nO)
#            exit(1)
#    print('Закончили пересчитывать потребители')


#------------------------------------------------------

# [Claude 2026-10-18] Нумерует узлы, затем ветви графа подряд (атрибут 'num'); возвращает общее число.
def set_G_num(G):
    num = 0

    for n in G.nodes:
        G.nodes[n]['num'] = num
        num += 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        G.edges[n1, n2, key]['num'] = num
        num += 1

    return num

#------------------------------------------------------

# [Claude 2026-10-18] Начальное приближение: напоры узлов = геодезические отметки, расходы ветвей = 10, плюс места под
# неизвестные узлов с заданным напором. Возвращает (root, число узлов, ветвей, узлов с заданным напором).
def init_root(G):
    num = 0

    n_n = G.number_of_nodes()
    n_l = G.number_of_edges()

    n_zn = 0

    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            n_zn += 1

    root = np.full(n_n + n_l + n_zn, 0.)

    for n in G.nodes:
        geodez = G.nodes[n].get('geoMarkTopTube', 0)
        root[num] = geodez
        num += 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        G.edges[n1, n2, key]['num'] = num
        root[num] = 10
        num += 1

    root[num] = 0

    return root, n_n, n_l, n_zn

#------------------------------------------------------

# [Claude 2026-10-18] Сумма модулей элементов вектора.
def get_delta(b):
    # исправлено Claude, 2026-10-22: было сложение в цикле по b[i]; cumsum складывает последовательно, как цикл -
    # результат бит в бит тот же (np.sum и sum() в Python 3.12 складывают иначе и расходятся в последних битах)
    if len(b) == 0:
        return 0
    return float(np.cumsum(np.abs(b))[-1])

#------------------------------------------------------

# [Claude 2026-10-18] Максимальный модуль элемента вектора.
def get_delta_max(b):
    # исправлено Claude, 2026-10-22: было сравнение в цикле по b[i]
    if len(b) == 0:
        return 0
    return float(np.abs(b).max())
#------------------------------------------------------

# [Claude 2026-10-18] Подготовка гидравлической системы: списки уравнений баланса узлов (list_n), уравнений ветвей (list_l)
# с параметрами по типам (насосы, арматура, обратные клапаны, регуляторы давления/расхода), узлов
# с заданным напором (list_zd) и правая часть beta0. None, если нет узлов с заданным напором.
def init_matrix(G, x, n_n, n_l, n_zn):
#    n_n = G.number_of_nodes()
#    n_l = G.number_of_edges()

#    nn = n_n + n_l + 1

    nn = n_n + n_l + n_zn

    t0 = time.time()

    beta0 = np.zeros(nn)
    
    list_n = list()
    list_l = list()
    list_zd = list()  # Узлы с заданным напором
    list_rd = list()  # Регулятор давления
    list_rr = list()  # Регулятор расхода
    list_ok = list()  # Обратный клапан
    G.graph['ok_flips'] = {}  # вставлено Claude, 2026-10-23: переключения обратных клапанов (w_ok.check_OK)

    list_ns = list()  # Насосы


    # Первый закон Кирхгофа

    t1 = time.time()

    for n in G.nodes:
        k_n = G.nodes[n]['num']
        g = G.nodes[n].get('G', 0.)

        beta0[k_n] = g

        for n1, n2, key in G.in_edges(n, keys=True):
            k_l = G.edges[n1, n2, key]['num']
            napr = 1
            list_n.append((k_n, k_l, napr))

        for n1, n2, key in G.out_edges(n, keys=True):
            k_l = G.edges[n1, n2, key]['num']
            napr = -1
            list_n.append((k_n, k_l, napr))

    t2 = time.time()

    # Второй закон Кирхгофа

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
#        print('>>', n1, n2, key, orient, flush=True)

        e = G.edges[n1, n2, key]
        k_l = e['num']
        typ = e['typ']
        nodeID3 = e.get('nodeID', 0)

        i1 = G.nodes[n1]['num']
        i2 = G.nodes[n2]['num']

        param = ()

        if typ == 'pumps':
            h = e.get('h', 0.)
            r1 = 0.
            r2 = 0.

            if h == 0:
                h = e.get('r0', 0.)
                r1 = e.get('r1', 0.)
                r2 = e.get('r2', 0.)
#                r1 = 0
#                r2 = 0

            beta0[k_l] = -h

            param = (h, r1, r2)
            list_ns.append((k_l, n1, n2, param))

        elif typ == 'regulArmatures':  # Регулирующая арматура (ZD2)
#            h = e.get('h', 0.)
            r1 = e.get('r1', 0.)
            param = (r1,)
#            beta0[i] = -((x[n1] - x[n2]) - r1 * sign(x[nl])) * 100000;
#            beta0[k_l] = h


        elif typ == 'reverseValves':  # Обратный клапан
            is_open = True
            list_ok.append((k_l, n1, n2, is_open))
            param = (len(list_ok)-1, )
            beta0[k_l] = 0

        else:
            '''
            if not typ in  (
                            'dampers',
                            'diaphragms',
                            'pressDropRegulators',
                            'regulArmatures',
                            ):
                    print(typ, flush=True)
                    '''

            S = e['S']
            if S == 0: S = 0.0000001

            param = (typ, S, None)

            if typ == 'pressRegulators' or (typ == 'bypass' and nodeID3 > 0):       # RD
                przu3 = e.get('przu', 1)
                nodeID3 = e.get('nodeID', -1)
                r1 = e['r1']
                r2 = e['r2']
                
                delta = e['delta']
                node3 = G.nodes.get((nodeID3, przu3), None)
                if node3:
                    geodez = node3.get('geoMarkTopTube', 0)
                    Z = e['Z']+geodez

                    k_n = node3['num']

                    list_rd.append((nodeID3, przu3, k_l, k_n, i1, i2, n1, n2, key, S, Z, r1, r2, delta, None, None, 0, 0, 0))

                    param = ('d', S, len(list_rd)-1)

            elif typ == 'consumptRegulators' or (typ == 'bypass' and nodeID3 <= 0):   # RR
                Z = e.get('Z', 0)
                r1 = e['r1']
                r2 = e['r2']

#                list_rr.append((n1, n2, i1, i2, k_l, S, Z, r1, r2))
#                param = ('r', S, len(list_rr)-1)
                
                if r1 != r2:
                    name = w_print.line_name_n1_n2(G, n1, n2)
#                    print('!!!', name, Z, r1, r2, flush=True)

                    list_rr.append((n1, n2, i1, i2, k_l, S, Z, r1, r2, key))

                    param = ('r', S, len(list_rr)-1)

        list_l.append((n1, n2, key, i1, i2, k_l, typ, param))


    t3 = time.time()

# Узлы с заданным напором

    n_zn1 = None
    nn1 = n_n + n_l + 1

    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if p_zn is not None:
            geodez = G.nodes[n].get('geoMarkTopTube', 0)
            n_zn1 = G.nodes[n]['num']

            beta0[nn1-1] = p_zn + geodez
            list_zd.append((n_zn1, nn1, p_zn+geodez))

            nn1 += 1


    if n_zn1 is None:
        return None

    t4 = time.time()

#    print((t1-t0)*1000, (t2-t1)*1000, (t3-t2)*1000, (t4-t3)*1000, file=sys.stderr, flush=True)

    return list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0



#------------------------------------------------------

# [Claude 2026-10-18] Отладка: печатает состояние обратных клапанов (открыт/закрыт) по знаку расхода.
def check_OK2(G, list_ok, root):
    for i in range(len(list_ok)):
        k_l, n1, n2, is_open = list_ok[i]

        if root[k_l] < 0:
            print('Закрыто ', w_print.line_name_n1_n2(G, n1, n2), root[k_l], flush=True)
        else:
            print('Открыто ', w_print.line_name_n1_n2(G, n1, n2), root[k_l], flush=True)


#------------------------------------------------------

# [Claude, 2026-08-24] make_matrix пересобирал матрицу целиком через lil_array
# на каждой итерации (755 раз за реальный расчет), хотя структура (какие
# позиции ненулевые) не меняется после первого вызова (first=True) — меняются
# только значения на диагонали для рёбер типа pumps/reverseValves/обычная
# труба (остальное — только правая часть beta, обычный numpy-массив, и так
# был быстрый). Начиная со второго вызова (first=False) больше не трогаем
# lil вообще: пишем новые значения напрямую в data-массив уже готовой CSC-
# матрицы по заранее посчитанным смещениям (diag_offsets) — это убирает и
# поэлементную запись через lil.__setitem__, и полную пересборку lil->csc
# на каждой итерации. matrix0 с этого момента — не сам массив, а кортеж
# (csc-матрица, словарь смещений диагонали), эта "непрозрачность" наружу не
# протекает — вызывающий код просто передаёт matrix0 туда и обратно, не
# заглядывая внутрь (проверено, других обращений к matrix0 в файле нет).
#
# Есть тонкость: если посчитанное диагональное значение оказывается ровно 0
# (например, нулевой расход через трубу — sign(0)=0, или открытый обратный
# клапан), исходный код полагался на отдельный проход "diag==0 -> eps" ПОСЛЕ
# основного цикла, и это могло срабатывать на любой итерации, не только на
# первой. Здесь эта подстановка сделана прямо на месте записи каждого
# диагонального элемента — по итоговому результату (сверено построчно на
# реальном расчете) это то же самое, так как между записью и проверкой
# ничего больше эту позицию не трогает.
# [Claude 2026-10-18] Строит (first=True) или обновляет на месте (first=False) матрицу Якоби и невязку для шага Ньютона
# по текущему решению x: баланс узлов, уравнения потерь напора на ветвях, насосы, клапаны, регуляторы,
# заданные напоры. Возвращает ((матрица, позиции диагонали), матрица, beta).
# вставлено Claude, 2026-10-23: rd_active - индексы list_rd активных регуляторов давления (ключ -rd_new),
# для них вместо потерь напора на ветви уравнение H[узел импульса] = Z. При смене набора нужен first=True.
# вставлено Claude, 2026-10-23: rr_active - работающие регуляторы расхода (w_rr2.py), None - прежняя модель (-rr_old).
def make_matrix(x, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, first, rd_active=None, rr_active=None):
    nn = len(beta0)

    ok_old = getattr(config.args, 'ok_old', False)  # вставлено Claude, 2026-10-23: обратные клапаны по-старому

    beta = np.copy(beta0)

    if first:
        lil = sp.sparse.lil_array((nn, nn))

        # Первый закон Кирхгофа

        for k_n, k_l, napr in list_n:
            lil[k_n, k_l] = napr
            beta[k_n] -= x[k_l]*napr

        # Второй закон Кирхгофа

        for n1, n2, key, i1, i2, k_l, typ, param in list_l:
            lil[k_l, i1] = 1
            lil[k_l, i2] = -1

            if typ == 'pumps':
                h, r1, r2 = param
                lil[k_l, k_l] = (r1 + r2 * 2 * x[k_l])
                beta[k_l] = -((x[i1] - x[i2]) + (h + r1 * x[k_l] + r2 * x[k_l] * x[k_l]))

            elif typ == 'regulArmatures':  # Регулирующая арматура (ZD2)
                r1, = param
                beta[k_l] = -((x[i1] - x[i2]) - r1 * np.sign(x[k_l]))

            elif typ == 'reverseValves':
                n_ok, = param
                k_l_, n1_, n2_, is_open = list_ok[n_ok]

                if is_open:
                    S = 0
                    lil[k_l, k_l] = 0
                    beta[k_l] = -(x[i1] - x[i2])

                # вставлено Claude, 2026-10-23: закрытый клапан - уравнение G = 0 (без протечки через S = 1e6);
                # при смене состояния клапанов матрица пересобирается (first=True). -ok_old - прежний вариант
                elif not ok_old:
                    lil[k_l, i1] = 0
                    lil[k_l, i2] = 0
                    lil[k_l, k_l] = 1
                    beta[k_l] = -x[k_l]

                else:
                    S = 1.e6

                    loss, dloss = _smooth_loss(S, x[k_l])
                    lil[k_l, k_l] = dloss
                    beta[k_l] = -(x[i1] - x[i2] - loss)

            else:
                typ2, S, n_rd = param

                if typ2 == 'd':
                   if not n_rd is None:
                       nodeID3, przu3, k_l, k_n, i1i, ii2, n1, n2, key, S, Z, r1, r2, delta, drr, rdr, rdh, rash_old, Z_old = list_rd[n_rd]

                       # вставлено Claude, 2026-10-23: активный регулятор давления - строка H[k_n] = Z
                       if rd_active and n_rd in rd_active:
                           lil[k_l, i1] = 0
                           lil[k_l, i2] = 0
                           lil[k_l, k_n] = 1
                           beta[k_l] = Z - x[k_n]
                           continue
                elif typ2 == 'r':
                    if not n_rd is None:
                       n1, n2, i1, i2, k_l, S, Z, r1, r2, key = list_rr[n_rd]

                    # вставлено Claude, 2026-10-23: регуляторы расхода уравнениями (rr_active не None, w_rr2.py):
                    # работающий - строка G = Z, остальные - сопротивление S (r1 или r2), без подкачки Z в узлы
                    if rr_active is not None:
                        if n_rd in rr_active:
                            lil[k_l, i1] = 0
                            lil[k_l, i2] = 0
                            lil[k_l, k_l] = 1
                            beta[k_l] = Z - x[k_l]
                            continue

                    elif r1 != r2:
                        beta[i1] += Z
                        beta[i2] -= Z

                if S == 0: S = 1e-20

                loss, dloss = _smooth_loss(S, x[k_l])
                lil[k_l, k_l] = dloss
                beta[k_l] = -(x[i1] - x[i2] - loss)

        # Узлы с заданным напором

        for n_zn, nn1, p_zn in list_zd:
            lil[nn1-1, n_zn] = 1
            beta[nn1-1] = p_zn - x[n_zn]

            lil[n_zn, nn1-1] = 1
            beta[n_zn] -= x[nn1-1]

        diag = lil.diagonal()

        # [Claude, 2026-08-24] Пробовал добавлять DIAG_REG к КАЖДОЙ диагонали здесь
        # так же, как в teplo1.py/calc_nagr.py (защита от "плавающих" изолированных
        # кусков сети) — но это гидравлика, матрица Ньютона пересобирается заново на
        # каждой из ~755 итераций одного решения, и постоянная подмешанная добавка на
        # КАЖДОЙ итерации вызвала реальное расхождение (d разошлось до ~1e28) на
        # одном из реальных фрагментов при проверке. В отличие от teplo1.py/calc_nagr.py
        # (там это разовый линейный решает, не итеративный процесс), здесь так
        # рисковать не стал — откатил к исходному "только ровно нулевая -> eps".
        for i in range(nn):
            if diag[i] == 0:
                lil[i, i] = eps

        matrix = sp.sparse.csc_array(lil)

        diag_offsets = {}
        for row in range(nn):
            start, end = matrix.indptr[row], matrix.indptr[row + 1]
            rows_in_col = matrix.indices[start:end]
            pos = np.nonzero(rows_in_col == row)[0]
            if len(pos):
                diag_offsets[row] = start + pos[0]

        return (matrix, diag_offsets), matrix, beta

    else:
        matrix, diag_offsets = matrix0
        data = matrix.data

        for k_n, k_l, napr in list_n:
            beta[k_n] -= x[k_l]*napr

        for n1, n2, key, i1, i2, k_l, typ, param in list_l:
            if typ == 'pumps':
                h, r1, r2 = param
                val = (r1 + r2 * 2 * x[k_l])
                data[diag_offsets[k_l]] = val if val != 0 else eps
                beta[k_l] = -((x[i1] - x[i2]) + (h + r1 * x[k_l] + r2 * x[k_l] * x[k_l]))

            elif typ == 'regulArmatures':  # Регулирующая арматура (ZD2)
                r1, = param
                beta[k_l] = -((x[i1] - x[i2]) - r1 * np.sign(x[k_l]))

            elif typ == 'reverseValves':
                n_ok, = param
                k_l_, n1_, n2_, is_open = list_ok[n_ok]

                if is_open:
                    S = 0
                    data[diag_offsets[k_l]] = eps
                    beta[k_l] = -(x[i1] - x[i2])

                elif not ok_old:   # вставлено Claude, 2026-10-23: закрытый клапан - G = 0
                    data[diag_offsets[k_l]] = 1
                    beta[k_l] = -x[k_l]

                else:
                    S = 1.e6

                    loss, dloss = _smooth_loss(S, x[k_l])
                    data[diag_offsets[k_l]] = dloss if dloss != 0 else eps
                    beta[k_l] = -(x[i1] - x[i2] - loss)

            else:
                typ2, S, n_rd = param

                if typ2 == 'd':
                   if not n_rd is None:
                       nodeID3, przu3, k_l, k_n, i1i, ii2, n1, n2, key, S, Z, r1, r2, delta, drr, rdr, rdh, rash_old, Z_old = list_rd[n_rd]

                       # вставлено Claude, 2026-10-23: активный регулятор давления - строка H[k_n] = Z (постоянная)
                       if rd_active and n_rd in rd_active:
                           data[diag_offsets[k_l]] = eps
                           beta[k_l] = Z - x[k_n]
                           continue
                elif typ2 == 'r':
                    if not n_rd is None:
                       n1, n2, i1, i2, k_l, S, Z, r1, r2, key = list_rr[n_rd]

                    # вставлено Claude, 2026-10-23: работающий регулятор расхода - G = Z (w_rr2.py)
                    if rr_active is not None:
                        if n_rd in rr_active:
                            data[diag_offsets[k_l]] = 1
                            beta[k_l] = Z - x[k_l]
                            continue

                    elif r1 != r2:
                        beta[i1] += Z
                        beta[i2] -= Z

                if S == 0: S = 1e-20

                loss, dloss = _smooth_loss(S, x[k_l])
                data[diag_offsets[k_l]] = dloss if dloss != 0 else eps
                beta[k_l] = -(x[i1] - x[i2] - loss)

        for n_zn, nn1, p_zn in list_zd:
            beta[nn1-1] = p_zn - x[n_zn]
            beta[n_zn] -= x[nn1-1]

        return (matrix, diag_offsets), matrix, beta


#------------------------------------------------------

# Проверяем источники
# [Claude 2026-10-18] Старый вариант определения источников: по графу потоков от каждого источника назначает heatSourceID
# достижимым узлам и ветвям. Возвращает True, если у потребителей источник изменился.
def check_ist2(G, root):
    ispr = False
    
#    print('Начали проверять источники', flush=True)
    
    GG = nx.MultiDiGraph()

    list_ist  = []
    
    for nn in G.nodes:
        n = G.nodes[nn]
#        id = n['nodeID']
#        po = n['po']
        id, po = nn

        typ = n['typ']
        ist0 = n.get('ist0', None) # Источник

        name = w_print.node_name(G, nn, False) 
#        GG.add_node((id, po), name=name, typ=typ)
        GG.add_node((id, po), typ=typ)

        if po == 1 and not ist0 is None:
            list_ist.append((id, po))
#            print(name)

    kk = 1

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]
        k_l = e['num']
        sost = e.get('sost', 1)

        g = root[k_l]
        if g < 0:
            n1, n2 = n2, n1

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        i1, p1 = n1
        i2, p2 = n2

#        i1 = nn1['nodeID']
#        p1 = nn1['po']
#        i2 = nn2['nodeID']
#        p2 = nn2['po']

#        name1 = w_print.node_name(G, n1, False) 
#        name2 = w_print.node_name(G, n2, False) 

        if sost != 2 and abs(g) > 0.00001 and p1 == 1:
#            GG.add_edge((i1, p1), (i2, p2), key=kk, txt=f'{name1} - {name2} = {orient} {g}', e=e)
            GG.add_edge((i1, p1), (i2, p2), key=kk, e=e)
            kk += 1

    ni = 1

    for i in list_ist:
        nist = G.nodes[i]['ist0']
        
        reachable_nodes = nx.descendants(GG, i)
        reachable_nodes.add(i)

        name = w_print.node_name(G, i, False) 

#        print(name)
#        print(len(reachable_nodes))

#        print('-----------------')
        for n in reachable_nodes:
            k, v = n

            n1 = G.nodes.get(n, None)

            if n1 is None:
                continue

#            n2 = G.nodes.get((k, 2), None)
#            print(k, v)
#            print(n1)
#            print(n2)
#            exit(1)

#            n1 = G.nodes[n]
            typ = n1['typ']

            if typ in ('realConsumers', 'generalizedConsumers'):
                ist_old = n1.get('heatSourceID', None)
                if ist_old != nist:
                    ispr = True

            n1['heatSourceID'] = nist


#            n2 = GG.nodes[n]
#            n2[f'ist{ni}'] = nist

            for nn1, nn2, key in GG.out_edges(n, keys=True):
                e = GG.edges[nn1, nn2, key]
                ee = e['e']
                ee['heatSourceID'] = nist

        ni += 1

#    nx.write_graphml(GG, f'C:/data/qq{name1}.graphml', edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)
    
#    print('Закончили проверять источники', flush=True)

    return ispr;

#------------------------------------------------------

# [Claude 2026-10-18] Считает источники (узлы подачи с ist0); если источник один - назначает его всем узлам.
# Возвращает (число источников, id источника).
def check_ist(G, root):
    n_ist = 0
    
    heatSourceID = None

    for n in G.nodes:
        nP = G.nodes[n]

        typ = nP['typ']
        po = nP['po']
        ist0 = nP.get('ist0', None) # Источник из магистрали

        if po == 1 and not ist0 is None:
            heatSourceID = ist0
            n_ist += 1

#    print(f'Источников {n_ist}')

    if n_ist == 1:
        for n in G.nodes:
            nP = G.nodes[n]
            nP['heatSourceID'] = heatSourceID

        '''
        for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
            e = G.edges[n1, n2, key]
            e['heatSourceID'] = heatSourceID
            '''

    return n_ist, heatSourceID
    



#------------------------------------------------------

# [Claude 2026-10-18] Гидравлический и тепловой расчет компоненты сети: вложенные итерации - пересчет потребителей с учетом
# тепловых потерь, регуляторы расхода и обратные клапаны, регуляторы давления, метод Ньютона
# (spsolve); затем определение источников, тепловой расчет (calc_teplo) и нагрузки по участкам.
# Возвращает решение root или None.
def solve_G(G, root, n_n, n_l, n_zn):
    '''
    matrix, beta = init_matrix(G, root)
    matrix2 = sp.sparse.csc_array(matrix)
    root = spsolve(matrix2, beta)
    set_G_out(G, root)
    return
    '''

#    n_n = G.number_of_nodes()
#    n_l = G.number_of_edges()
#    nn = n_n + n_l + 1
    nn = n_n + n_l + n_zn

    if root is None:
        root = np.full(nn, 0.)

    delta = 10000

    ret = init_matrix(G, root, n_n, n_l, n_zn)

    if ret is None:
        return None

    list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0 = ret

    # вставлено Claude, 2026-10-23: регуляторы расхода уравнениями (w_rr2.py), по умолчанию; -rr_old - прежняя модель.
    # rr_act - работающие регуляторы (строка G = Z), передается во все make_matrix и меняется в w_rr2.check_RR
    rr_new = not config.args.rr_old
    rr_st = w_rr2.init_RR(G, list_rr) if rr_new else None
    rr_act = rr_st['active'] if rr_new else None

    matrix0 = sp.sparse.lil_array((nn, nn))
    matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, True, rr_active=rr_act)

    

#    w_print.print_b('beta', beta)
#    exit(1)

#    w_print.print_matrix(matrix, beta)
#    w_print.print_b('beta', beta)

#    reset_consumptions(G, beta0)

#    Tn0 = ct->t_or
    ct = get_ct()
    Tn0 = ct.get('t_or')

    n_ist, heatSourceID = check_ist(G, root)

    n_potr = 1

    if config.args.is_tg and not config.args.no_teplopoter:
        n_potr = 4

    is_teplo = False

    # вставлено Claude, 2026-10-23: регуляторы давления в системе Ньютона (w_rd2.py), по умолчанию; -rd_old - старый подбор.
    # rd_solve(active) пересобирает матрицу с активными регуляторами и решает ее Ньютоном (как цикл it ниже);
    # если не получилось - откат и старый метод w_rd.check_RD.
    rd_new = config.args.rd_new and any(rd[11] != rd[12] for rd in list_rd)
    rd_msgs = {}
    rd_old_msg = False

    def rd_newton(active, label):
        nonlocal matrix0

        delta = None

        for it in range(100):
            if n_ist == 1:
                reset_consumptions(G, beta0)

            matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, False, active, rr_active=rr_act)

            beta2 = sp.sparse.linalg.spsolve(matrix, beta)

            if not np.all(np.isfinite(beta2)):
                logging.info(f'  Ньютон {label}: nan/inf')
                return False

            root[:] += beta2   # на месте: root - переменная solve_G

            delta = get_delta(beta2)
            delta2 = get_delta_max(beta2)

            check_NS(G, list_ns, root)

            print(f'iter: {m:1d} {j:1d} {label} {it:2d} d={delta:14f} d_max={delta2:10f}', file=sys.stderr, flush=True)

            root[np.abs(root) < 0.00001] = 0

            reset_sopr(G, root, list_l, heatSourceID)  # пересчитываеи сопротивления по температуре

            if delta < 0.001:
                break

        if delta is None or delta >= 1.0 or not np.all(np.isfinite(root)):
            logging.info(f'  Ньютон {label}: не сошелся d={delta}')
            return False

        return True

    rd_pass = 0

    ok_msg = False   # вставлено Claude, 2026-10-23: сообщение о неустановившихся обратных клапанах выведено

    def rd_solve(active):
        nonlocal matrix0, rd_pass

        matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, True, active, rr_active=rr_act)
        rd_pass += 1

        return rd_newton(active, f'p{rd_pass:<2d}')

    def rd_jacobian():
        nonlocal matrix0

        matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, False, rr_active=rr_act)

        return matrix

    for m in range(n_potr): # Пересчет потребителей с учетом тепловых потерь
#        print(f'Расчет потерь {m} из {n_potr} {n_ist=}')
        for j in range(5): # регуляторы расхода
#            print('=====================================================================')
#            print(f'Потребители {j+1}')

            # вставлено Claude, 2026-10-23: новый расчет регуляторов давления, при неудаче - старый цикл ниже
            rd_done = False

            if rd_new:
                rd_done, msgs = w_rd2.calc_RD_active(G, list_rd, root, rd_solve, rd_jacobian)

                if rd_done:
                    rd_msgs = msgs
                else:
                    rd_msgs = {}
                    if not rd_old_msg:
                        cprint('Регуляторы давления: расчет с уравнениями регуляторов не сошелся, '
                               'использован итерационный подбор сопротивлений', color='yellow')
                        rd_old_msg = True

                    # структура матрицы без активных регуляторов
                    matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, True, rr_active=rr_act)

            for i in range(0 if rd_done else config.args.iter): # Регуляторы давления
#            for i in range(1): # Регуляторы давления
                for it in range(100):  # Итерация уравнения
                    t1 = time.time()

                    if n_ist == 1:
#                        cprint('Пересчет потребителей', color='b')
                        reset_consumptions(G, beta0)

                    t2 = time.time()

                    matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, False, rr_active=rr_act)


                    t3 = time.time()

    #                w_print.print_matrix(matrix, beta)

#                    beta1 = matrix @ root  # закомментировано Claude, 2026-10-22: не используется

    #                w_print.print_b('beta1', beta1)
            #        if get_delta(beta) < 0.0001: break
            #        delta = get_delta(beta1)
            #        print('iter1 = ', it, 'delta = ', delta, 'delta/nn = ', delta/nn, file=sys.stderr, flush=True)


                    beta2 = sp.sparse.linalg.spsolve(matrix, beta)

#                    from sety.safe_spsolvefile import dump_system
#                    dump_system(matrix, beta, beta2, 200)
#                    print('==========================================')
#                    exit(1)

    #                beta2 = spsolve(matrix, beta)

                    root += beta2

                    delta = get_delta(beta2)
                    delta2 = get_delta_max(beta2)

                    check_NS(G, list_ns, root)

                    t4 = time.time()

                    print(f'iter: {m:1d} {j:1d} {i:2d} {it:2d} d={delta:14f} d_max={delta2:10f} dt={(t2 - t1) * 1000:5f} ms dt2={(t3 - t2) * 1000:5f} ms dt2={(t4 - t3) * 1000:5f} ms', file=sys.stderr, flush=True)

#                    if n_ist > 0:
#                    check_ist2(G, root)

                    for i in range(len(root)):
                        if abs(root[i]) < 0.00001:
                            root[i] = 0

                    reset_sopr(G, root, list_l, heatSourceID)  # пересчитываеи сопротивления по температуре

                    if delta < 0.001:
                        break

#                finish = (i == config.args.iter-1)

#                if i < config.args.iter-1:
                f1 = w_rd.check_RD(G, list_rd, root, i, finish=False)

#                if f1 < 0.001:
                if f1 == 0:
                       break



            if rr_new:   # вставлено Claude, 2026-10-23
                f_RR = w_rr2.check_RR(G, list_rr, root, rr_st)
            else:
                f_RR = w_rr.check_RR(G, list_rr, root)
            ok_old = config.args.ok_old   # вставлено Claude, 2026-10-23
            f_OK = w_ok.check_OK(G, list_ok, root, reopen=not ok_old)

            # вставлено Claude, 2026-10-23: у закрытого клапана и работающего регулятора расхода другая структура
            # строки - пересобрать матрицу
            if (f_OK and not ok_old) or (f_RR and rr_new):
                matrix0, matrix, beta = make_matrix(root, list_n, list_l, list_zd, list_rd, list_rr, list_ok, list_ns, beta0, matrix0, True, rr_active=rr_act)

                # состояние клапанов / регуляторов расхода не установилось за 5 проходов - одно сообщение
                if j == 4 and not ok_msg:
                    cprint('Обратные клапаны и регуляторы расхода: состояние не установилось за 5 проходов, взято последнее', color='yellow')
                    ok_msg = True

#            if f_RR:
#                dbg(list_rr)

#            print('f_RR', f_RR, 'f_OK', f_OK, flush=True)
    #        break

            if not f_RR and not f_OK:
               break

        if n_ist > 0:
#            check_ist2(G, root)
            check_ist3(G, root, 1)
            check_ist3(G, root, 2)

        is_teplo = False

#        if config.args.is_tg or config.args.g_is_avar:
        if True:
            t1 = time.time()
#            print('Начали считать тепло 1', flush=True)
            is_teplo = calc_teplo(G, root, Tn0, False, False)
#            reset_sopr(G)  # пересчитываеи сопротивления по температуре

            if not is_teplo and config.args.is_tg:
#                cprint('Во фрагменте нет источников тепла, расчет по температурному графику невозможен', color='red')
                return None

            t2 = time.time()
#            print(f'Закончили считать тепло {(t2-t1)*1000}', flush=True)

#        print('~~~~~~~~~~~~~~~~~~~~~~', Tn0)



        if is_teplo and m < n_potr-1:
            reset_consumptions(G, beta0)

    if is_teplo:
        t1 = time.time()
#        print('---------------------------------', flush=True)
#        print('Начали считать тепло 2', flush=True)
        calc_teplo(G, root, config.args.Tn, True, True)
        t2 = time.time()
#        print(f'Закончили считать тепло {(t2-t1):0.2f} секунд', flush=True)
#        print('---------------------------------', flush=True)

    # вставлено Claude, 2026-10-23: регуляторы давления, не обеспечившие напор (-rd_new); печатает w_calc2
    # после последнего solve_G, чтобы при повторном расчете подсети сообщения не дублировались
    G.graph['rd_msgs'] = rd_msgs
    G.graph['rr_msgs'] = w_rr2.messages(G, list_rr, root, rr_st) if rr_new else {}  # вставлено Claude, 2026-10-23

    calc_nagr(G, root)

#        print('bb:', bb, flush=True)
#    print_matrix(matrix, beta, x)


#    print('--------------------', flush=True)
#    check_OK2(G, list_ok, root)
#    print('--------------------', flush=True)

    return root

#------------------------------------------------------

from sety.out.podpitka import n_ras


# [Claude 2026-10-18] Проверка решения: печатает подпитку/водоразбор в узлах с небалансом, участки без сопротивления,
# невязки на арматуре, насосах, регуляторах и других ветвях.
def proverka(G, x):

#    return
#    cprint('---------------------------', color='b')
    cprint('Проверка', color='b')

    for n in G.nodes:
        nn0 = G.nodes.get(n, None)
        if nn0.get('name', '') == 'ATMOSPHERE': continue
        n_n0 = nn0['num']
        h0 = x[n_n0]

        GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, n, False)

        if GG_P != 0 and abs(GG_P) > 0.01:  #1.0e-10:
#            GG_P, Gin_P, Gout_P, Gp_P, Gout_P =  n_ras(G, n, True)
            if abs(GG_P) > 0.0001:
                name = w_print.node_name(G, n, False)
                
                if GG_P < 0:
                    print(f'В узле {name} с напором {h0:.2f} подпитка {-GG_P:0.2f} т/ч');
                else:
                    print(f'В узле {name} с напором {h0:.2f} водоразбор {GG_P:0.2f} т/ч');
#            exit(1)
    

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        l_n = e['num']

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        n_n1 = nn1['num']
        n_n2 = nn2['num']

        r = x[l_n]
        h1 = x[n_n1]
        h2 = x[n_n2]

        nodeID3 = e.get('nodeID', 0)

        name = w_print.line_name_n1_n2(G, n1, n2)

        typ = e['typ']


        typ_r = w_data.map_tn.get(typ, typ)


        S = e.get('S', 0)  # сопротивление
        Z = e.get('Z', 0)  # расход


#        if not typ in ('pumps','reverseValves','consumptRegulators','pressDropRegulators', 'bypass'):
        if typ in ('heatPipeSections'):
           if S == 0:
               cprint(f'В {name} не задано сопротивление!!', color='red')
#               print(e)

        elif typ == 'regulArmatures':
            if r != 0.:
                q_zad = e.get('r1', 0)

                # исправлено Claude, 2026-10-20 (ревью п. 2.4): в расчете h1 - h2 = r1*sign(G), было сравнение с h2 - h1 -
                # ложное предупреждение при каждом прямом потоке
                if abs(q_zad * np.sign(r) - (h1 - h2)) > 1e-6:
                    print(f'{typ_r} {name}. Перепад задано: {q_zad} получено: {h1 - h2:.2f} м., расход {r:.2f} т/ч')

#        if typ == 'pressDropRegulators':
#            if r != 0.:
#                print(f'{typ} {name}. Перепад задано: {h} получено: {h2 - h1:.2f} м., расход {r:.2f} т/ч')


        elif typ == 'pumps':
            if r != 0.:
                h = e.get('h', 0)
                if h != 0:
                    if abs(h - (h2 - h1)) < 1e-6:
                        continue
                else:
                    r0 = e.get('r0', 0)
                    r1 = e.get('r1', 0)
                    r2 = e.get('r2', 0)
                    h = r0 + r1*r + r2*r*r

                if abs(h - (h2-h1)) > 0.01: 
                    print(f'{typ_r} {name}. Перепад задано: {h} получено: {h2 - h1:.2f} м., расход {r:.2f} т/ч')
                
        elif typ == 'consumptRegulators' or typ == 'bypass' and nodeID3 == 0:
            # исправлено Claude, 2026-10-22: x - отклонение от заданного только у открытого и не фиксированного
            # регулятора, иначе (не обеспечил расход, перешел на сопротивление) x - сам расход; как в w_out.py
            G_r = Z + r if config.args.rr_old and e.get('sost') == const.L_OPEN and not e.get('fixed', False) else r  # rr_old - Claude, 2026-10-23
            print(f'{typ_r} {name}. Расход задано: {Z} получено: {G_r:.2f}  т/ч')
#            print(e.get('sost'))

        elif typ == 'pressRegulators' or typ == 'bypass' and nodeID3 != 0:
            if r != 0. and S != 0.:
                dh = abs((h2-h1)/S/r/r)-1

                if dh > 0.01 and abs(h1 - h2) > 1e-6:
                    S2 = abs(h1-h2)/r/r

                    if S != 0:
                        dS = S - S2
                        print(f'Невязка в {typ_r} {name}. Перепад {h1 - h2:.2f} м., расход {r:.2f} т/ч, сопротивление {S:.5f} должно быть {S2:.5f} Разница {dS*100/S:.1f}%')
#                        print(e.get('sost'))




#        elif not typ in ('pumps','pressRegulators','consumptRegulators','pressDropRegulators', 'bypass', 'regulArmatures'):
        else:
#        if typ in ('heatPipeSections'):
#        if not typ in ('pumps'):
            if r != 0. and S != 0.:
                dh = abs((h2-h1)/S/r/r)-1

                if dh > 0.01 and abs(h1 - h2) > 1e-6:
                    S2 = abs(h1-h2)/r/r

                    if S != 0:
                        dS = S - S2
                        print(f'Невязка в {typ_r} {name}. Перепад {h1 - h2:.2f} м., расход {r:.2f} т/ч, сопротивление {S:.5f} должно быть {S2:.5f} Разница {dS*100/S:.1f}%')

    cprint('---------------------------', color='b')


#------------------------------------------------------


# [Claude 2026-10-18] Расчет одной связной компоненты: нумерация, решение solve_G, перенос результатов в граф (set_G_out),
# при необходимости повтор после обнуления 'висячих' потребителей, проверка, суммирование для
# обобщенных потребителей (make_G2) и летний режим (make_G2_leto).
def w_calc2(G, param_sum):
    set_G_num(G)


    print('Начал расчет фрагмента', file=sys.stderr, flush=True)

    first = True

    while True:
        root, n_n, n_l, n_zn = init_root(G)


        root = solve_G(G, root, n_n, n_l, n_zn)


        if root is None:
            print(f'Ошибка расчета', file=sys.stderr, flush=True)
            # в протокол (stdout): подсеть не рассчитана — веб покажет её среди ошибок
            cprint('Расчет подсети не выполнен: система уравнений не решена (проверьте сопротивления, '
                   'регуляторы и узлы с заданным напором)', color='red')
            return


    #    print('delta = ', delta, ' iter = ', it, flush=True)

        print()
        print(f'Расчет закончен', file=sys.stderr, flush=True)
    

        w_out.set_G_out(G, root)


        f_PO = True

        if first and not config.args.g_is_avar:   # плановый 
            f_PO = reset_consumptions_PO(G, root)

        first = False

        if f_PO: 
            break

    # вставлено Claude, 2026-10-23: сообщения по регуляторам давления (-rd_new) последнего solve_G
    rd_msgs = G.graph.pop('rd_msgs', {})
    for k in sorted(rd_msgs):
        cprint(rd_msgs[k], color='yellow')

    rr_msgs = G.graph.pop('rr_msgs', {})  # вставлено Claude, 2026-10-23: регуляторы расхода (w_rr2.py)
    for k in sorted(rr_msgs):
        cprint(rr_msgs[k], color='yellow')

    proverka(G, root)

    if not config.args.g_is_avar:   # плановый расчет
        g2.make_G2(G, param_sum)

    if config.args.is_leto and config.args.is_save_po:
#    if config.args.is_save_po:
 #       g2.write_po(G, param_sum, config.args.out_file)
        g2.make_G2_leto(G, config.args.out_file)

#    matrix, beta = init_matrix(G)

#    print(beta, flush=True)

#------------------------------------------------------

# Ищет любой узел с ЗН
# [Claude 2026-10-18] Первый узел с заданным напором (кроме атмосферы) или None.
def find_zn(G):
    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            nn0 = G.nodes.get(n, None)
            if nn0:
                if nn0.get('name', '') != 'ATMOSPHERE':
                    return n

    return None

#------------------------------------------------------

# [Claude 2026-10-18] Множество всех узлов с заданным напором.
def find_zn2(G):
    
    zn = set()
    for n in G.nodes:
        p_zn = G.nodes[n].get('p_zn', None)
        if not p_zn is None:
            zn.add(n)

    return zn

#------------------------------------------------------

# [Claude 2026-10-18] Расчет всей сети: по каждой слабосвязной компоненте с узлом заданного напора вызывает w_calc2,
# в конце при -save_po пишет суммарные нагрузки для обобщенных потребителей (write_po).
def w_calc(G):
    print('Расчет начат', flush=True)

    w_print.setG(G)

    nn = 0
    for i in nx.weakly_connected_components(G): 
        if len(i) > 1: 
            if True:
                GG = G.subgraph(i)
                n0 = find_zn(GG)
                if n0 is not None:
                    nn0 = G.nodes.get(n0, None)
                    if nn0:
                        if nn0.get('name', '') != 'ATMOSPHERE':
                            nn += 1

#    param_sum = defaultdict(lambda: [0] * 9)  # Начальные значения для обобщенных потребителей
    param_sum = defaultdict(dict)  # Начальные значения для обобщенных потребителей
 
    print(f'{nn} фрагментов')

    ii = 0
    no_zn = []
    for i in nx.weakly_connected_components(G):
        if len(i) > 1:
#            if ii in (4,):
            if True:
                GG = G.subgraph(i)
                n0 = find_zn(GG)

                if n0 is not None:
                    name_zn = G.nodes[n0].get('name', '')
                    if name_zn != '9-28':  ###МТК-13-19':
                        pass
#                        continue



#                        continue

#                    if ii+1 != 98:
#                        ii += 1
#                        continue


                    print('-----------------', flush=True)

                    name = w_print.node_name(G, n0, True)    
                    print(f'Фрагмент {ii+1}/{nn} [{name}]', flush=True)

                    if ii == 2 or True:

                        n_n = GG.number_of_nodes()
                        n_l = GG.number_of_edges()
    #                    print(f'Узлов : {n_n} Ребер: {n_l}')

                        print(f'Узлы с заданым напором', flush=True)
                        nn0 = find_zn2(GG)
                        z = 1
                        for pp in nn0:
                            p_zn = G.nodes[pp].get('p_zn', None)
    #                        print(z, w_print.node_name(G, pp, False), ' = ', p_zn, flush=True)
                            if G.nodes[pp].get('name', '') != 'ATMOSPHERE':
    #                            print(G.nodes[pp].get('name', ''))
                                print(z, w_print.node_name(G, pp, False), flush=True)
                            z += 1

                        w_calc2(GG, param_sum)

                    ii += 1
                else:
                    no_zn.append(i)

    # Подсети без узла с заданным напором не считаются — раньше молча
    if no_zn:
        # подача и обратка одной подсети — разные компоненты графа с теми же узлами: считаем один раз
        uniq = {}
        for c in no_zn:
            uniq.setdefault(frozenset(n[0] if isinstance(n, tuple) else n for n in c), c)
        no_zn = list(uniq.values())
        no_zn.sort(key=len, reverse=True)
        total = sum(len(c) for c in no_zn)
        print('-----------------', flush=True)
        cprint(f'Не рассчитано подсетей без узла с заданным напором: {len(no_zn)} (узлов {total})', color='brown')
        for c in no_zn[:NO_ZN_LIST_MAX]:
            n_show = min(c, key=lambda n: (G.nodes[n].get('name', '') in ('', 'ATMOSPHERE'), str(n)))
            cprint(f'    Подсеть из {len(c)} узлов: {w_print.node_name(G, n_show, True)}', color='brown')
        if len(no_zn) > NO_ZN_LIST_MAX:
            cprint(f'    … и ещё {len(no_zn) - NO_ZN_LIST_MAX}', color='brown')

    if config.args.is_save_po:
        g2.write_po(G, param_sum, config.args.out_file)

#    print('Закончил расчет', flush=True)
#    print('Расчет закончен', flush=True)

#------------------------------------------------------

if __name__ == "__main__":
    G = nx.MultiDiGraph()

    G.add_node(1, p_zn=100, x=0, y=0)
    G.add_node(2, G=1.1, x = 0, y=1000)
    G.add_node(3, G=1.2, x=1000, y=0)

#    G.add_edge(1, 2, 1, sopr = 0.12)
    G.add_edge(1, 2, 1, S=0.12, typ='heatPipeSections')
    G.add_edge(3, 1, 2, S=0.01, typ='heatPipeSections')
    G.add_edge(2, 3, 3, S=0.01, typ='heatPipeSections')

    param_sum = defaultdict(lambda: [0] * 9)  # Начальные значения для обобщенных потребителей
    
    w_calc2(G, param_sum)
    nx.write_graphml(G, 'C:/data/qq.graphml', edge_id_from_attribute=True, named_key_ids=True, infer_numeric_types=True)

