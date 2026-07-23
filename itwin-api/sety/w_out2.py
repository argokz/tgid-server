import numpy as np
import networkx as nx
import networkx as nx

from datetime import datetime


import logging

from sety import config
from sety import const
from sety.any import db2

from sety.any.colors import nbsp


from sety.out.us_out import out_US_OUT
from sety.out.pt_out import out_PT_OUT
from sety.out.pt_out2 import out_PT_OUT2  # Эквиваленитный
from sety.out.pt_out3 import out_PT_OUT3  # Детализированный

from sety.out.pt_out2 import dr_out_to_new


from sety.out.bp_out import out_BP_OUT
from sety.out.is_out import out_IS_OUT

from sety.out.any2_out import out_ANY2_OUT
from sety.out.ut_out import out_UT_OUT
from sety.out.zd_out import out_ZD_OUT
from sety.out.any_out import out_ANY_OUT


from sety.out.rs_out import out_RS_OUT
from sety.out.ns_out import out_NS_OUT
from sety.out.ok_out import out_OK_OUT

from sety.check_ist import check_ist
import sety.out.out_teplo


from sety.any.colors import cprint

def del_old_out(conn, tn, s_id, max_num):
    q = f'''
;WITH NumberedCalculations AS (
    SELECT 
        c.id,
        fr.id as fr_id,
        ROW_NUMBER() OVER (PARTITION BY c.user_gid, fr.id ORDER BY c.id DESC) AS rn
    FROM CALCULATION c
    LEFT JOIN fragments fr ON fr.id = c.fileID
)

DELETE FROM {tn}
WHERE {s_id} IN (
    SELECT id
    FROM NumberedCalculations
    WHERE rn > {max_num}
)
'''
#    print('---------------------------')
#    print(q)
#    print('---------------------------')

    cursor = conn.cursor()

    try:
        cursor.execute(q)
    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)



def del_out(conn):

    return
    max_num = 3

    del_old_out(conn, 'ut_out', 'calculationID', max_num)

    del_old_out(conn, 'any_out', 'calculationID', max_num)
    del_old_out(conn, 'any2_out', 'calculationID', max_num)
    del_old_out(conn, 'bp_out', 'calculationID', max_num)
    del_old_out(conn, 'dro_out', 'calculationID', max_num)
    del_old_out(conn, 'ist_out', 'calculationID', max_num)
    del_old_out(conn, 'nst_out', 'calculationID', max_num)
    del_old_out(conn, 'ns_out', 'calculationID', max_num)
    del_old_out(conn, 'ok_out', 'calculationID', max_num)
    del_old_out(conn, 'rpp_out', 'calculationID', max_num)
    del_old_out(conn, 'rs_out', 'calculationID', max_num)
    del_old_out(conn, 'zd2_out', 'calculationID', max_num)
    del_old_out(conn, 'zd_out', 'calculationID', max_num)


    del_old_out(conn, 'us_out', 'calculationID', max_num)
    del_old_out(conn, 'pt_out', 'calculationID', max_num)
    del_old_out(conn, 'dr_out', 'calculationID', max_num)


    del_old_out(conn, 'calculation', 'id', max_num)

    conn.commit()




def w_out(G, conn, fileID):
#    print('Запись результата началась', flush=True)
    cursor = conn.cursor()

    calculationid = 1;

    q = f'SELECT MAX(id) FROM calculation where fileid={fileID}'

    c = db2.read_q_value(cursor, q)

    q = f'SELECT * FROM calculation where fileid={fileID}'

    cursor.execute(q)

    while True:
        row = cursor.fetchone()
        if not row: break
        pass

#        print(row)

#    exit(1)

    current_dateTime = datetime.now()
    name = config.args.name_calc.replace('\'','\'\'')

    dt = current_dateTime.strftime('%Y-%m-%d %H:%M:%S')

#    dt = str(current_dateTime)[0:22]

#
#    if c is None:
##        cursor.execute(f'insert into calculation (fileID) values({fileID})')
#
##        q = f'insert into calculation (fileID) values({fileID}) returning id'
##        c = any.db2.read_q_value(cursor, q)
#        q = f'''insert into calculation (fileID, tn, date1, name) 
#                values({fileID}, {config.args.Tn}, \'{dt}\', \'{name}\')'''
#        c = any.db2.exec_insert(cursor, q)
#    else:
#        q = f'''update calculation set 
#            fileID = {fileID},
#            tn = {config.args.Tn},
#            name = \'{name}\',
#            date1 = \'{dt}\'
#            where id={c}
#            '''


    if True or c is None:
#        q = f'insert into calculation (fileID, tn, date1, name) $MS_SQL_OUTPUT$ values(?, ?, ?, ?)'
#        c = any.db2.exec_insert(cursor, q, (fileID, config.args.Tn, name, current_dateTime))
#        q = f'insert into calculation (fileID, tn, date1, name) $MS_SQL_OUTPUT$ values(?, ?, ?, ?)'
#        c = any.db2.exec_insert(cursor, q, (fileID, config.args.Tn, name, dt))
        
#        exit(1)



        json_str = config.get_args_json(config.args)


        q = f'insert into calculation (fileID, tn, date1, name, user_gid, calc_params, calc_plan) $MS_SQL_OUTPUT$ values(?, ?, ?, ?, ?, ?, ?)'
#        c = db2.exec_insert(cursor, q, (fileID, config.args.Tn, dt, name))
        c = db2.exec_insert(cursor, q, (fileID, config.args.Tn, current_dateTime, name, config.args.user_gid, json_str, config.args.is_plan))

#        print('c=', c)

    else:
        q = f'update calculation set fileID = ?,tn = ?,name = ?,date1 = ?, user_gid = ? where id={c}'
        cursor.execute(q, (fileID, config.args.Tn, name, current_dateTime, config.args.user_gid))
#        cursor.execute(q, (fileID, config.args.Tn, name, dt))
        conn.commit()

        q = f'SELECT MAX(id) FROM calculation where fileid={fileID}'
#        c = db2.read_q_value(cursor, 'SELECT MAX(id) FROM calculation')
        c = db2.read_q_value(cursor, q)

    if c is None:
        print('Не могу записать!!!!')
        exit(1)

    calculationid = c;
#    cursor.execute(f'update calculation set fileID={fileID} where id={calculationid}')
#    conn.commit()


#    cprint('**** информация по тепловому и материальному балансу ****')
#    cprint(nbsp('                                                       Нагрузка    Расход'))
#    cprint(nbsp('                                                         Гкал/ч      т/ч'))

    out_US_OUT(G, conn, calculationid)
    out_IS_OUT(G, conn, calculationid)

    if not config.args.g_is_avar:
        out_PT_OUT(G, conn, calculationid, config.args.Tn)
    else:
        out_PT_OUT2(G, conn, calculationid, config.args.Tn, 'generalizedConsumers', True)
        if config.args.g_equival:
            out_PT_OUT2(G, conn, calculationid, config.args.Tn, 'realConsumers', False)
        else:
            out_PT_OUT3(G, conn, calculationid, config.args.Tn, False)
    
    out_BP_OUT(G, conn, calculationid)

    out_UT_OUT(G, conn, calculationid)
    out_ZD_OUT(G, conn, calculationid)
    out_ANY_OUT(G, conn, calculationid)
    out_RS_OUT(G, conn, calculationid)
    out_NS_OUT(G, conn, calculationid)
    out_OK_OUT(G, conn, calculationid)

    out_ANY2_OUT(G, conn, calculationid)

    sety.out.out_teplo.out_teplo(G)

    if config.args.g_is_avar:
        dr_out_to_new(conn, calculationid)
    

    check_ist(conn, fileID, calculationid)

    conn.commit()


#    del_out(conn)
#    conn.commit()


#    print('Запись результата закончена 2', flush=True)

    return calculationid
