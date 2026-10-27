# вставлено Claude, 2026-10-24: проверка исходных данных фрагмента перед расчетом.
# Только чтение базы. Находит то, из-за чего расчет останавливается или дает неверный результат:
# коды РС без источника, латиница/кириллица в кодах, температурные графики, узлы с заданным напором
# (связь с магистралью, несколько в одной подсети), неподключенные потребители, подсети без узла
# с заданным напором, незаполненные коды потребителей, участки без длины/диаметра.
# Пояснения к пунктам - claude-notes/sety_messages_2026-10-24.md (разделы указаны в выводе).
#
# Запуск (параметры подключения - как у ww.py):
#   python check_fragment.py -server 192.168.0.37 -port 5440 -user postgres -database astanagid_2026_09_22 -fileID 16
#   без -fileID - краткая сводка по всем фрагментам; -json - вывод в JSON (для помощника/LLM).

import os
import re
import sys
import json
import argparse
import collections

import networkx as nx

parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.abspath(os.path.join(parent_dir, '..')))

from sety.any import connect

ERR = 'ОШИБКА'      # расчет остановится
WARN = 'ПРЕДУПР'    # расчет пройдет, результат неверен
INFO = 'ИНФО'

LAT2CYR = str.maketrans('ABCEHKMOPTXaceopxy', 'АВСЕНКМОРТХасеорху')
RE_LAT = re.compile('[A-Za-z]')

LIST_MAX = 15   # сколько объектов показывать в каждом пункте

#------------------------------------------------------

# Код без различий латиница/кириллица, регистр, пробелы по краям
def norm(s):
    return (s or '').strip().translate(LAT2CYR).upper()


def rows(cur, q, *args):
    cur.execute(q, *args)
    return cur.fetchall()


#------------------------------------------------------

class Report:
    def __init__(self):
        self.items = []

    def add(self, level, section, title, objs=()):
        self.items.append(dict(level=level, section=section, title=title, objs=list(objs)))

    def counts(self):
        return collections.Counter(x['level'] for x in self.items)

    def print(self):
        for level in (ERR, WARN, INFO):
            for x in self.items:
                if x['level'] != level:
                    continue
                print(f"[{level}] {x['title']}  (справочник, раздел {x['section']})")
                for o in x['objs'][:LIST_MAX]:
                    print(f'    {o}')
                if len(x['objs']) > LIST_MAX:
                    print(f"    … и ещё {len(x['objs']) - LIST_MAX}")
        c = self.counts()
        print(f'Итого: ошибок {c[ERR]}, предупреждений {c[WARN]}, к сведению {c[INFO]}')


#------------------------------------------------------

# Коды РС фрагмента и узлы, которые на них ссылаются
def check_codes(cur, f, rep, fname):
    codes = rows(cur, '''
        SELECT e.id, coalesce(e.name, ''), e.heatsourceid, hn.id, coalesce(k.cnt, 0), coalesce(p.cnt, 0)
        FROM externalcodes e
        LEFT JOIN heatsources hs ON hs.id = e.heatsourceid
        LEFT JOIN nodes hn ON hn.id = hs.nodeid AND coalesce(hn.removed, 0) = 0
        LEFT JOIN (SELECT externalcodeid, count(*) cnt FROM nodes
                   WHERE fileid = ? AND coalesce(removed, 0) = 0 GROUP BY externalcodeid) k ON k.externalcodeid = e.id
        LEFT JOIN (SELECT n.externalcodeid, count(*) cnt FROM nodes n
                   WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0
                     AND (EXISTS (SELECT 1 FROM realconsumers c WHERE c.nodeid = n.id)
                          OR EXISTS (SELECT 1 FROM generalizedconsumers c WHERE c.nodeid = n.id))
                   GROUP BY n.externalcodeid) p ON p.externalcodeid = e.id
        WHERE e.fileid = ? AND coalesce(e.removed, 0) = 0
        ''', (f, f, f))

    # источник нужен потребителям (расход по температурному графику при -tg)
    no_src = [c for c in codes if c[3] is None and c[5] > 0]
    if no_src:
        rep.add(ERR, 2, f'Коды РС потребителей без источника тепла: {len(no_src)} (с -tg расчет остановится)',
                [f'{c[1]!r}: узлов {c[4]}, потребителей {c[5]}' for c in sorted(no_src, key=lambda c: -c[4])])
    no_src = [c for c in codes if c[3] is None and c[4] > 0 and c[5] == 0]
    if no_src:
        rep.add(INFO, 2, f'Коды РС без источника тепла (потребителей с ними нет): {len(no_src)}',
                [f'{c[1]!r}: узлов {c[4]}' for c in sorted(no_src, key=lambda c: -c[4])])

    lat = [c for c in codes if RE_LAT.search(c[1] or '') and c[4] > 0]
    if lat:
        rep.add(INFO, 9, f'Коды РС с латинскими буквами: {len(lat)}',
                [f'{c[1]!r}: узлов {c[4]}' for c in lat])

    by_norm = collections.defaultdict(list)
    for c in codes:
        by_norm[norm(c[1])].append(c)
    twins = [v for k, v in by_norm.items() if k and len({c[1] for c in v}) > 1]
    if twins:
        rep.add(WARN, 9, f'Коды-двойники (отличаются латиницей/кириллицей или регистром): {len(twins)}',
                ['; '.join(f"{c[1]!r}({'лат' if RE_LAT.search(c[1]) else 'кир'}) узлов {c[4]}, "
                           f"{'источник есть' if c[3] else 'БЕЗ источника'}" for c in v) for v in twins])

    # узлы без кода / с кодом другого фрагмента
    bad = rows(cur, '''
        SELECT n.id, n.externalnodename, e.name, e.fileid
        FROM nodes n LEFT JOIN externalcodes e ON e.id = n.externalcodeid
        WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0
          AND (e.id IS NULL OR e.fileid IS NULL OR e.fileid <> n.fileid OR coalesce(e.removed, 0) <> 0)
        ''', (f,))
    if bad:
        rep.add(WARN, 2, f'Узлы с кодом РС из другого фрагмента, удаленным или без кода: {len(bad)}',
                [f'{b[1]} (id {b[0]}): код {b[2]!r}, фрагмент кода {fname.get(b[3], b[3])}' for b in bad])

    return {c[0]: c for c in codes}


#------------------------------------------------------

# Температурные графики источников, на которые ссылаются коды РС фрагмента
def check_tg(cur, f, rep, t_or):
    src = rows(cur, '''
        SELECT DISTINCT hs.id, hn.externalnodename, g.cnt, g.tn_min
        FROM nodes n
        JOIN externalcodes e ON e.id = n.externalcodeid
        JOIN heatsources hs ON hs.id = e.heatsourceid
        JOIN nodes hn ON hn.id = hs.nodeid
        LEFT JOIN (SELECT hsourceid, count(*) cnt, min(tn) tn_min FROM deployedtempgraphs GROUP BY hsourceid) g
               ON g.hsourceid = hs.id
        WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0
        ''', (f,))
    no_tg = [s for s in src if not s[2]]
    if no_tg:
        rep.add(ERR, 2, f'Источники без температурного графика: {len(no_tg)} (с -tg расчет остановится)',
                [f'{s[1]} (id {s[0]})' for s in no_tg])
    if t_or is not None:
        short = [s for s in src if s[2] and s[3] is not None and s[3] > t_or + 0.01]
        if short:
            rep.add(WARN, 2, f'Температурный график не доходит до расчетной температуры {t_or}',
                    [f'{s[1]} (id {s[0]}): график с {s[3]}' for s in short])
    if src:
        tg = rows(cur, f'''
            SELECT hsourceid, tn, t1, t2 FROM deployedtempgraphs
            WHERE hsourceid IN ({','.join(str(int(s[0])) for s in src)}) ORDER BY hsourceid, tn
            ''')
        first = {}
        for hs, tn, t1, t2 in tg:
            first.setdefault(hs, (tn, t1, t2))
        name = {s[0]: s[1] for s in src}
        rep.add(INFO, 2, 'Источники фрагмента (по кодам РС) и график при самой низкой температуре',
                [f'{name[h]} (id {h}): Tn={v[0]} t1/t2={v[1]}/{v[2]}' for h, v in first.items()])


#------------------------------------------------------

# Узлы с заданным напором: связь с магистралью
def check_zn(cur, f, rep, fname):
    zn = rows(cur, '''
        SELECT s.nodeid, n.externalnodename, e.name, s.fragment_resultid, coalesce(s.kod_m, ''), coalesce(s.uzel_m, ''),
               s.pressflow, s.pressret
        FROM setpressnodes s
        JOIN nodes n ON n.id = s.nodeid
        LEFT JOIN externalcodes e ON e.id = n.externalcodeid
        WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0
        ''', (f,))

    not_found = []
    hint = []
    no_link = []
    for nodeid, name, kod, m, kod_m, uzel_m, pf, pr in zn:
        label = f'[{kod} {name}]'
        if m is None or (kod_m == '' and uzel_m == ''):
            no_link.append(f'{label}: напоры из узла П={pf} О={pr}')
            continue
        exact = rows(cur, '''
            SELECT count(*) FROM nodes n JOIN externalcodes e ON e.id = n.externalcodeid
            WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0 AND e.name = ? AND n.externalnodename = ?
            ''', (m, kod_m, uzel_m))[0][0]
        if exact:
            continue
        cand = rows(cur, '''
            SELECT e.name, n.externalnodename FROM nodes n JOIN externalcodes e ON e.id = n.externalcodeid
            WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0 AND upper(trim(n.externalnodename)) = upper(trim(?))
            ''', (m, uzel_m))
        cand = [c for c in cand if norm(c[0]) == norm(kod_m)]
        if cand:
            hint.append(f'{label} -> [{kod_m} {uzel_m}], в магистрали [{cand[0][0]} {cand[0][1]}] '
                        f'(отличие в латинице/кириллице, регистре или пробелах)')
        else:
            not_found.append(f'{label} -> [{kod_m} {uzel_m}] во фрагменте {fname.get(m, m)}')

    if hint:
        rep.add(WARN, 3, f'Узлы с заданным напором: узел магистрали не найден из-за написания: {len(hint)}', hint)
    if not_found:
        rep.add(WARN, 3, f'Узлы с заданным напором: узла нет в магистрали: {len(not_found)} '
                         f'(напоры возьмутся из самого узла)', not_found)
    if no_link:
        rep.add(INFO, 3, f'Узлы с заданным напором без связи с магистралью: {len(no_link)}', no_link)

    return {z[0]: f'[{z[2]} {z[1]}]' for z in zn}


#------------------------------------------------------

# Связность: подсети по ветвям, неподключенные потребители, подсети без узла с заданным напором,
# несколько узлов с заданным напором в подсети. Участки, закрытые по подаче или обратке
# (pipesectstateidflow/ret = 2), связи не дают; состояние задвижек и других ветвей не учитывается.
# Внутренние узлы и ветви потребителей (internalnodeid) не учитываются - они не связывают потребителя с сетью.
def check_graph(cur, f, rep, zn_names):
    G_all = nx.Graph()   # все ветви
    G = nx.Graph()       # без закрытых участков
    nodes = rows(cur, '''
        SELECT n.id, n.externalnodename, e.name FROM nodes n LEFT JOIN externalcodes e ON e.id = n.externalcodeid
        WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0 AND n.internalnodeid IS NULL
        ''', (f,))
    name = {}
    for nid, nm, kod in nodes:
        G.add_node(nid)
        G_all.add_node(nid)
        name[nid] = f'[{kod} {nm}]'
    for a, b, closed in rows(cur, '''
            SELECT l.nodeid1, l.nodeid2,
                   CASE WHEN h.pipesectstateidflow = 2 OR h.pipesectstateidret = 2 THEN 1 ELSE 0 END
            FROM linesobj l JOIN nodes n ON n.id = l.nodeid1
            LEFT JOIN heatpipesections h ON h.lineid = l.id
            WHERE n.fileid = ? AND coalesce(l.removed, 0) = 0 AND l.nodeid1 <> l.nodeid2 AND l.internalnodeid IS NULL
            ''', (f,)):
        if a in G and b in G:
            G_all.add_edge(a, b)
            if not closed:
                G.add_edge(a, b)

    # потребители и их расчетная нагрузка на отопление и вентиляцию
    cons = {}
    for t, cols in (('realconsumers', 'coalesce(c.calchldep,0)+coalesce(c.calchlindep,0)+coalesce(c.calchlventil,0)'),
                    ('generalizedconsumers', 'coalesce(c.calchldep,0)+coalesce(c.calchlindep,0)+coalesce(c.calchlventil,0)')):
        for nid, q, sp, ct in rows(cur, f'''
                SELECT c.nodeid, {cols}, c.specexpendid, c.calctemperatureid FROM {t} c JOIN nodes n ON n.id = c.nodeid
                WHERE n.fileid = ? AND coalesce(n.removed, 0) = 0
                ''', (f,)):
            cons[nid] = (float(q or 0), t, sp, ct)

    q_all = sum(v[0] for v in cons.values())

    # неподключенные не считаются - для них коды не важны
    linked = [n for n in cons if n in G and G.degree(n) > 0]
    no_tr = [name.get(n, n) for n in linked if not cons[n][3]]
    if no_tr:
        rep.add(ERR, 6, f'Потребители без кода расчетных температур: {len(no_tr)} (расчет остановится)', no_tr)
    no_ur = [name.get(n, n) for n in linked if not cons[n][2]]
    if no_ur:
        rep.add(WARN, 6, f'Потребители без кода удельных расходов: {len(no_ur)} (без -tg расчет остановится)', no_ur)

    def pct(q):
        return f'{q:.2f} Гкал/ч из {q_all:.2f} ({100 * q / q_all if q_all else 0:.0f} %)'

    isolated = [n for n in cons if n in G_all and G_all.degree(n) == 0]
    if isolated:
        q = sum(cons[n][0] for n in isolated)
        rep.add(WARN, 4, f'Потребители, не подключенные ни одним участком: {len(isolated)}, нагрузка {pct(q)} - не считаются',
                [f'{name[n]}: {cons[n][0]:.3f} Гкал/ч' for n in sorted(isolated, key=lambda n: -cons[n][0])])

    cut = [n for n in cons if n in G and G.degree(n) == 0 and G_all.degree(n) > 0]
    if cut:
        q = sum(cons[n][0] for n in cut)
        rep.add(INFO, 4, f'Потребители, отключенные закрытыми участками: {len(cut)}, нагрузка {pct(q)} - не считаются '
                         f'(проверьте, что отключение намеренное)',
                [f'{name[n]}: {cons[n][0]:.3f} Гкал/ч' for n in sorted(cut, key=lambda n: -cons[n][0])])

    no_zn = []
    multi = []
    for comp in nx.connected_components(G):
        z = [n for n in comp if n in zn_names]
        c = [n for n in comp if n in cons]
        if not z and c and len(comp) > 1:
            no_zn.append((sum(cons[n][0] for n in c), len(comp), len(c), min(c, key=lambda n: name[n])))
        if len(z) > 1:
            multi.append(', '.join(sorted(zn_names[n] for n in z)))
    if no_zn:
        rep.add(WARN, 4, f'Подсети с потребителями без узла с заданным напором: {len(no_zn)} - не считаются',
                [f'узлов {k}, потребителей {p}, нагрузка {q:.2f} Гкал/ч, например {name[n]}'
                 for q, k, p, n in sorted(no_zn, reverse=True)])
    if multi:
        rep.add(WARN, 3, f'Подсети с несколькими узлами с заданным напором: {len(multi)} - возможны перетоки '
                         f'(без учета закрытых задвижек)', multi)

    return len(nodes), len(cons), q_all


#------------------------------------------------------

# Участки без длины или диаметра
def check_pipes(cur, f, rep):
    bad = rows(cur, '''
        SELECT h.name, n1.externalnodename, n2.externalnodename,
               coalesce(h.pipesectlength, 0), coalesce(h.diameterinternal, 0)
        FROM heatpipesections h
        JOIN linesobj l ON l.id = h.lineid
        JOIN nodes n1 ON n1.id = l.nodeid1
        JOIN nodes n2 ON n2.id = l.nodeid2
        WHERE n1.fileid = ? AND coalesce(l.removed, 0) = 0 AND coalesce(n1.removed, 0) = 0
          AND (coalesce(h.pipesectlength, 0) <= 0 OR coalesce(h.diameterinternal, 0) <= 0)
        ''', (f,))
    if bad:
        rep.add(WARN, 5, f'Участки без длины или внутреннего диаметра: {len(bad)}',
                [f'{b[1]} - {b[2]}: длина {b[3]}, диаметр {b[4]}' for b in bad])


#------------------------------------------------------

def check_fragment(conn, f, fname, t_or):
    cur = conn.cursor()
    rep = Report()
    check_codes(cur, f, rep, fname)
    check_tg(cur, f, rep, t_or)
    zn_names = check_zn(cur, f, rep, fname)
    n_nodes, n_cons, q_all = check_graph(cur, f, rep, zn_names)
    check_pipes(cur, f, rep)
    if not zn_names:
        rep.add(ERR, 3, 'Во фрагменте нет узлов с заданным напором - рассчитывать нечего')
    # вставлено Claude, 2026-10-25: имя фрагмента может быть NULL
    head = dict(fileID=f, name=fname.get(f) or '', nodes=n_nodes, consumers=n_cons, load=round(q_all, 3))
    return head, rep


def main():
    p = argparse.ArgumentParser(description='Проверка исходных данных фрагмента перед расчетом (только чтение)')
    p.add_argument('-server', default='localhost')
    p.add_argument('-port', type=int, default=5432)
    p.add_argument('-user', default='postgres')
    p.add_argument('-password', default=os.getenv('PGPASSWORD', ''))
    p.add_argument('-database', required=True)
    p.add_argument('-rdbms', default='postgreSQL')
    p.add_argument('-fileID', type=int, default=None, help='Фрагмент; без него - сводка по всем')
    p.add_argument('-json', action='store_true', help='Вывод в JSON')
    a = p.parse_args()

    conn = connect.connect(rdbms=a.rdbms, server=a.server, port=a.port, user=a.user, password=a.password, db=a.database)
    if not conn:
        print('Не могу подключиться')
        sys.exit(1)
    cur = conn.cursor()

    fname = dict(rows(cur, 'SELECT id, name FROM fragments'))
    hs = rows(cur, 'SELECT t_or FROM heatsystem ORDER BY id')
    t_or = float(hs[0][0]) if hs and hs[0][0] is not None else None

    files = [a.fileID] if a.fileID is not None else sorted(fname, key=lambda x: str(fname[x]))
    out = []
    for f in files:
        try:
            head, rep = check_fragment(conn, f, fname, t_or)
        except Exception as ex:   # один фрагмент с необычными данными не должен останавливать сводку
            if a.fileID is not None:
                raise
            print(f'{str(fname.get(f, ""))[:40]:40s} [{f}] не проверен: {type(ex).__name__}: {ex}', flush=True)
            continue
        out.append(dict(head, items=rep.items))
        if a.json:
            continue
        if a.fileID is not None:
            print(f"БД {a.database}, фрагмент {head['name']} [{f}]: узлов {head['nodes']}, "
                  f"потребителей {head['consumers']}, нагрузка отопл.+вент. {head['load']} Гкал/ч, t_or={t_or}")
            rep.print()
        else:
            c = rep.counts()
            titles = '; '.join(x['title'].split(':')[0] for x in rep.items if x['level'] in (ERR, WARN))
            print(f"{head['name'][:40]:40s} [{f}] ошибок {c[ERR]} предупр. {c[WARN]}  {titles[:160]}", flush=True)

    if a.json:
        json.dump(out if a.fileID is None else out[0], sys.stdout, ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
