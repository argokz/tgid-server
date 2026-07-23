import psycopg2 as pyodbc
import time

def get_ps_obj(conn, q):    

    t1 = time.time()
    
    cursor = conn.cursor()
    cursor.execute(q)

    ps2 = ''


    ps_id_old = -1

    while True:
        row = cursor.fetchone()
        if not row: break

#        print(row)

        row = ['null' if col is None else col for col in row]
        
        (obj_id, n_id, l_id, ps_id, nodeID1, nodeID2, ord, ps_ord) = row

        if ps_id_old == ps_id: 
            nodeID1 = 'null'
            nodeID2 = 'null'

        ps_id_old = ps_id

        if ps2 != '' : ps2 += ','
        ps2 += f'''({obj_id}, {n_id}, {l_id}, {ps_id}, {nodeID1}, {nodeID2}, {ord}, {ps_ord})\n'''


#    print(ps2)
#    exit(0)

    t2 = time.time()

    if ps2 == '':
        ps2 += f'''(null, null, null, null, null, null, null, null)\n'''



#    print(f' {t2-t1} секунд', flush=True)
#    exit(0)
    return ps2            
