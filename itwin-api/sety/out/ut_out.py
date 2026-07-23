import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

from sety.out.pt_out import print_bal

def out_UT_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from UT_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('UT_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('lineid')
    insert.add_col('externalsignlineid')
    insert.add_col('ist')

    insert.add_col('sos')   # Состояние участка
    insert.add_col('a7')   # Длина участка теплопровода
    insert.add_col('a8')   # Внутренний диаметр трубы участка
    insert.add_col('a9')   # Объем воды на участке теплопровода
    insert.add_col('a10')   # Скорость потока сетевой воды
    insert.add_col('a11')   # Время прохождения потока воды
    insert.add_col('a12')   # Полное гидравлическое сопротивление участка
    insert.add_col('a13')   # Расход сетевой воды на участке
    insert.add_col('a14')   # Удельные линейные потери напора на участке
    insert.add_col('a15')   # Линейные потери напора на участке
    insert.add_col('a16')   # Местные потери напора на участке
    insert.add_col('a17')   # Общие потери напора на участке
    insert.add_col('a18')   # Располагаемый напор в конечном узле участка
    insert.add_col('a19')   # Пьзометрический напор в конечном узле участка
    insert.add_col('a20')   # Геодезич.отметка местности в конечном узле участка
    insert.add_col('a21')   # Полный напор в конечном узле участка
    insert.add_col('tpot')   # Тепловые потери  теплопроводом
    insert.add_col('t1')   # Температура сет. воды  во входном узле
    insert.add_col('t2')   # Температура остывания сет. воды
    insert.add_col('qq')   # Нормы тепловых потерь
    insert.add_col('tzam')   # Время остывания воды при остановке движения

    insert.add_col('b101')
    insert.add_col('b102')
    insert.add_col('b103')
    insert.add_col('b104')
    insert.add_col('b105')
    insert.add_col('b106')

    yP = 0
    yO = 0

    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        nn1 = G.nodes[n1]
        nn2 = G.nodes[n2]

        t1 = nn1.get('t', None)
        t2 = nn2.get('t', None)

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход

        num = e.get('num', -1)
        if num == -1:
            continue


        if typ == 'heatPipeSections' and GG != 0:      # Участки

            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('lineid', id)
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)

#            if po == 2:
#                print('>>>>>>>>>>>>>>>', heatSourceID)

            insert.db_write('ist', heatSourceID)

            norma = e.get('norma', 0)
            y = e.get('y', 0)

            insert.db_write('sos')   # Состояние участка
            insert.db_write('a7', e.get('dlina', 0.))   # Длина участка теплопровода
            insert.db_write('a8', e.get('diametr', 0.))   # Внутренний диаметр трубы участка
            insert.db_write('a9', e.get('a9', 0.))   # Объем воды на участке теплопровода
            insert.db_write('a10', e.get('a10', 0.))   # Скорость потока сетевой воды
            insert.db_write('a11', e.get('a11', 0.))   # Время прохождения потока воды
            insert.db_write('a12', e.get('a12', 0.))   # Полное гидравлическое сопротивление участка
            insert.db_write('a13', e.get('G', 0.))   # Расход сетевой воды на участке
            insert.db_write('a14', e.get('a14', 0))   # Удельные линейные потери напора на участке
            insert.db_write('a15', e.get('a15', 0))   # Линейные потери напора на участке
            insert.db_write('a16', e.get('a16', 0))   # Местные потери напора на участке
            insert.db_write('a17', e.get('a17', 0))   # Общие потери напора на участке
            insert.db_write('a18', e.get('a18', 0))   # Располагаемый напор в конечном узле участка
            insert.db_write('a19', e.get('a19', 0))   # Пьзометрический напор в конечном узле участка
            insert.db_write('a20', e.get('a20', 0))   # Геодезич.отметка местности в конечном узле участка
            insert.db_write('a21', e.get('a21', 0))   # Полный напор в конечном узле участка
#            insert.db_write('tpot', e.get('tpot', 0))   # Тепловые потери  теплопроводом

            insert.db_write('tpot', y)   # Тепловые потери  теплопроводом

            if po == 1:
                yP += y
            else:
                yO += y


            insert.db_write('t1', t1)   # Температура сет. воды  во входном узле

            if t1 and t2:
                insert.db_write('t2', abs(t2-t1))   # Температура остывания сет. воды

            insert.db_write('qq', norma)   # Нормы тепловых потерь
            insert.db_write('tzam', e.get('tzam', 0))   # Время остывания воды при остановке движения

            if po == 1:
                insert.db_write('b101', e.get('b101', 0))
                insert.db_write('b102', e.get('b102', 0))
                insert.db_write('b103', e.get('b103', 0))
                insert.db_write('b104', e.get('b104', 0))

                insert.db_write('b105', e.get('b105', 0))
                insert.db_write('b106', e.get('b106', 0))

         
            insert.db_insert_vals()


#    ins = insert.insert_text()

    insert.exec()



#    print('Тепловые потери')
#    print('Участки\n')
#    print_bal('Тепловые потери, подающий теплопровод', yP, 0)
#    print_bal('Тепловые потери, обратный теплопровод', y, 0)


#    print(ins)

#    cursor.execute(ins)
#   conn.commit()

