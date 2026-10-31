import connect

import pyodbc
import sys


def del_baza(conn, name, central_meridian, false_east, false_north, Tnv_r):
    cursor = conn.cursor()

    cursor.execute('delete from opora')
    cursor.execute('delete from kompensator')
    cursor.execute('delete from defect')

    cursor.execute('DELETE FROM fragments')
    conn.commit()

#    Tnv_r = -24
#    name = 'Днепропетровск'


    cursor.execute(f'''UPDATE heatSystem 
                   SET t_or={Tnv_r}, t_vr={Tnv_r}, name=\'{name}\', 
                   Central_Meridian={central_meridian}, False_Easting={false_east}, False_Northing={false_north}''')
    conn.commit()

    cursor.execute('DELETE FROM ulitsy')
    conn.commit()

    cursor.execute('DELETE FROM ulitsy')
    conn.commit()


if __name__ == '__main__':
    baza = sys.argv[1]

    c = {}

    c['server'] = 'localhost'
    c['user'] = ''
    c['password'] = ''

    c['db'] = baza
    c['port'] = 1433

    conn = connect.connect_ms_sql(**c)

    del_baza(conn, 'Санкт-Петербург', -24)
