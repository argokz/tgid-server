import sys
import pyodbc
from collections import defaultdict

from sety import read_gid
#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Читает из deployedTempGraphs температурные графики всех источников в глобальный map_tg[id источника]
# = список (tn, Q_otn, t1, t2, t3, tv, t_bn, tg), отсортированный по tn.
def read_tg(conn):
    tn2 = 'Температурный график'

    print(f'Начал читать {tn2}', file=sys.stderr, flush=True)
    
    q = '''
SELECT n.fileID, tg.hSourceID, tg.tn, tg.Q_otn, tg.t1, tg.t2, tg.t3, tg.tv, tg.t_bn, tg.tg   
FROM deployedTempGraphs tg
JOIN heatSources hs ON hs.id=tg.hSourceID
JOIN nodes n ON n.id=hs.nodeID
ORDER BY tg.hSourceID, tg.tn

'''
    cursor = conn.cursor()

    global map_tg

    map_tg = defaultdict(list)
#    map_tg = defaultdict(OrderedDict)

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break

            fileID, hSourceID, tn, Q_otn, t1, t2, t3, tv, t_bn, tg = row

#            map_tg[hSourceID][tn] = (tn, Q_otn, t1, t2, t3, tv, t_bn, tg)
            map_tg[hSourceID].append((tn, Q_otn, t1, t2, t3, tv, t_bn, tg))

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)

    print(f'Закончил читать {tn2}', file=sys.stderr, flush=True)

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Температуры (t1, t2, t3, tv) по температурному графику источника id для наружной температуры tn
# (линейная интерполяция по таблице map_tg). None, если графика нет; вне диапазона - крайняя точка.
def get_tg(id, tn):

    global map_tg

    ist = read_gid.map_ist.get(id)

    tgr = map_tg.get(id, None)
  
    if tgr is None:
        return None

    # исправлено Claude, 2026-10-20 (ревью п. 1.1): линейная интерполяция по отрезку [tn0, tn1],
    # в котором лежит tn, с делением на шаг таблицы. Вне диапазона графика - значения крайней точки
    # (было: наклон следующего отрезка без деления на шаг, на последнем отрезке без интерполяции,
    # выше последней точки - None).
    if not tgr:
        return None

    tn_first, _, t1, t2, t3, tv, _, _ = tgr[0]
    if tn <= tn_first:
        return t1, t2, t3, tv

    for i in range(1, len(tgr)):
        tn1, _, t1_1, t2_1, t3_1, tv_1, _, _ = tgr[i]

        if tn <= tn1:
            tn0, _, t1_0, t2_0, t3_0, tv_0, _, _ = tgr[i-1]

            k = (tn - tn0) / (tn1 - tn0)   # tn0 < tn <= tn1, поэтому tn1 != tn0

            t1 = t1_0 + (t1_1 - t1_0)*k
            t2 = t2_0 + (t2_1 - t2_0)*k
            t3 = t3_0 + (t3_1 - t3_0)*k
            tv = tv_0 + (tv_1 - tv_0)*k

            return t1, t2, t3, tv

    tn_last, _, t1, t2, t3, tv, _, _ = tgr[-1]
    return t1, t2, t3, tv

#-----------------------------------------------------------------------------------

# [Claude 2026-10-18] Отладочная копия get_tg для проверки графика источника id (печатает источник). Нерабочая: tn не определен.
def check_tg(id):
    global map_tg

    ist = read_gid.map_ist.get(id)

    t1_2r = ist.get('t1_2r', 0)

    print(ist, flush=True)

    tgr = map_tg.get(id, None)
  
    if tgr is None:
        return None

    v1 = tgr[0]
    v2 = tgr[-1]

    t1_0 = 0
    t2_0 = 0
    t3_0 = 0
    tv_0 = 0
    tn0 = 0

    for i in range(len(tgr)):
        tn1, Q_otn_1, t1_1, t2_1, t3_1, tv_1, t_bn_1, tg_1 = tgr[i]

#        print('==', tn , tn1)

        if tn <= tn1:
            if i < len(tgr)-1:
                tn2, Q_otn_2, t1_2, t2_2, t3_2, tv_2, t_bn_2, tg_2 = tgr[i+1]

                t1 = t1_1 + (t1_2 - t1_1)*(tn - tn1)
                t2 = t2_1 + (t2_2 - t2_1)*(tn - tn1)
                t3 = t3_1 + (t3_2 - t3_1)*(tn - tn1)
                tv = tv_1 + (tv_2 - tv_1)*(tn - tn1)
            else:
                t1 = t1_1 + (t1_0 - t1_1)*(tn - tn0)
                t2 = t2_1 + (t2_0 - t2_1)*(tn - tn0)
                t3 = t3_1 + (t3_0 - t3_1)*(tn - tn0)
                tv = tv_1 + (tv_0 - tv_1)*(tn - tn0)

            return t1, t2, t3, tv

        t1_0 = t1_1
        t2_0 = t2_1
        t3_0 = t3_1
        tv_0 = tv_1
        tn0 = tn

    return None
