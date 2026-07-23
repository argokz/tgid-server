import numpy as np
import networkx as nx
import networkx as nx

import logging

from sety import const
from sety import w_print
from sety import sopr

from sety.any import db2
from sety.any.insert2 import Insert

def out_NS_OUT(G, conn, calculationid):
    cursor = conn.cursor()
    
    cursor.execute(f'delete from NS_OUT where calculationid={calculationid}')
    conn.commit()

    insert = Insert('NS_OUT', conn)

    insert.add_col('calculationid')
    insert.add_col('lineid')
    insert.add_col('externalsignlineid')
    insert.add_col('ist')

    insert.add_col('sos')   # Состояние насосного агрегата
    insert.add_col('a4')   # Геодезическая отметка поверхности земли узла на входе
    insert.add_col('a8')   # Геодезическая отметка поверхности земли узла на выходе
    insert.add_col('a9')   # Координаты рабочей зоны: 1-я точка -напор
    insert.add_col('a10')   # Координаты рабочей зоны: 1-я точка -расход
    insert.add_col('a11')   # Координаты рабочей зоны:2-я точка -напор
    insert.add_col('a12')   # Координаты рабочей зоны:2-я точка -расход
    insert.add_col('a13')   # Рабочий напор насоса
    insert.add_col('a14')   # Расход воды через насос
    insert.add_col('a15')   # Пьезометрический напор в узле на входе насоса
    insert.add_col('a16')   # Пьезометрический напор в узле на выходе
    insert.add_col('a17')   # Загрузка насосной станции
    insert.add_col('a18')   # Количество насосов
    insert.add_col('a19')   # Тип насосов



    for n1, n2, key, orient in nx.edge_dfs(G, orientation="ignore"):
        e = G.edges[n1, n2, key]

        id = e['id']
        typ = e['typ']
        po = e['po']
        GG = e.get('G', 0.)           # расход
        externalSignLineID = e.get('externalSignLineID', 6)


        if typ == 'pumps' and externalSignLineID < 6:      # 
            insert.addRow()

            insert.db_write('calculationid', calculationid)
            insert.db_write('lineid', id)
            insert.db_write('externalsignlineid', po+1)

            heatSourceID = e.get('heatSourceID', 0)
            insert.db_write('ist', heatSourceID)

            insert.db_write('sos')   # Состояние насосного агрегата
            insert.db_write('a4')   # Геодезическая отметка поверхности земли узла на входе
            insert.db_write('a8')   # Геодезическая отметка поверхности земли узла на выходе
            insert.db_write('a9')   # Координаты рабочей зоны: 1-я точка -напор
            insert.db_write('a10')   # Координаты рабочей зоны: 1-я точка -расход
            insert.db_write('a11')   # Координаты рабочей зоны:2-я точка -напор
            insert.db_write('a12')   # Координаты рабочей зоны:2-я точка -расход
            insert.db_write('a13', e.get('a13', 0))   # Рабочий напор насоса
            insert.db_write('a14', GG)   # Расход воды через насос
            insert.db_write('a15', e.get('a15', 0))   # Пьезометрический напор в узле на входе насоса
            insert.db_write('a16', e.get('a16', 0))   # Пьезометрический напор в узле на выходе
#            insert.db_write('a17', e.get('a17', 0))   # Загрузка насосной станции
            insert.db_write('a18', e.get('a18', 0))   # Количество насосов
            insert.db_write('a19', e.get('a19', 0))   # Тип насосов

            insert.db_insert_vals()


#    ins = insert.insert_text()
    insert.exec()

#    print(ins)

#    cursor.execute(ins)
#   conn.commit()

