import sys
import pyodbc
import csv


from collections import defaultdict


from sety.any.any import get_gidr_path
from sety.any import connect
from sety.read_db import read_csv2

from sety.read_db import read_tab2
from sety.read_db import read_row2

from sety.read_db import read_row3
from sety.any.connect import br_text
from sety import w_data

#-----------------------------------------------------------------------------------

map_s30 = {}
map_s39 = defaultdict(dict)
map_s28 = {}
map_s07 = {}

#-----------------------------------------------------------------------------------

def read_tab_s39(conn, tn: str, look) -> None:
    cursor = conn.cursor()

    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr)

    q = f'SELECT * FROM {br_text(tn)} o'

    try:
        cursor.execute(q)

        while True:
            row = cursor.fetchone()
            if not row: break
           
            s39 = read_row2(tn, cursor, row)

#            print(s39)

            s39_2 = {}
            s39_2['d'] = s39.get('d', 0)
            s39_2['dy'] = s39.get('dy', 0)
            s39_2['date'] = s39.get('date', 0)
            s39_2['proklad'] = s39.get('proklad', 0)
            s39_2['tg'] = s39.get('tg', 0)
            s39_2['tn'] = s39.get('tn', 0)
            s39_2['t2'] = s39.get('t2', 0)

            s39_2['t1'] = [s39.get('t1_1', 0), s39.get('t1_2', 0), s39.get('t1_3', 0), s39.get('t1_4', 0)]
            s39_2['qp1'] = [s39.get('qp_1', 0), s39.get('qp_2', 0), s39.get('qp_3', 0), s39.get('qp_4', 0)]
            s39_2['qo1'] = [s39.get('qo_1', 0), s39.get('qo_2', 0), s39.get('qo_3', 0), s39.get('qo_4', 0)]
            s39_2['qp2'] = [s39.get('qp_1gt5000', 0), s39.get('qp_2gt5000', 0), s39.get('qp_3gt5000', 0), s39.get('qp_4gt5000', 0)]
            s39_2['qo2'] = [s39.get('qo_1gt5000', 0), s39.get('qo_2gt5000', 0), s39.get('qo_3gt5000', 0), s39.get('qo_4gt5000', 0)]

            d = max(s39.get('d', 0), s39.get('dy', 0))

            look[s39.get('date', 1), s39.get('proklad', 'К')][d] = s39_2

    except pyodbc.Error as ex:
        print(ex, file=sys.stderr)


    print(f'Закончил читать {tn2}', file=sys.stderr)



#-----------------------------------------------------------------------------------

def read_csv_s39(tn: str, look) -> None:
    tn2 = w_data.map_tn.get(tn , tn)

    print(f'Начал читать {tn2}', file=sys.stderr)

    with open(f'{get_gidr_path()}/sprav/{tn}.csv', mode='r', encoding='utf-8') as file:
        reader = csv.reader(file, delimiter=';')
        cols = next(reader)
#        print(cols)
        
        for row in reader:
            s39 = read_row3(cols, row)

#            print(s39)
#            exit(1)

            s39_2 = {}
            s39_2['d'] = s39.get('d', 0)
            s39_2['dy'] = s39.get('dy', 0)
            s39_2['date'] = s39.get('date', 0)
            s39_2['proklad'] = s39.get('proklad', 0)
            s39_2['tg'] = s39.get('tg', 0)
            s39_2['tn'] = s39.get('tn', 0)
            s39_2['t2'] = s39.get('t2', 0)

            s39_2['t1'] = [s39.get('t1_1', 0), s39.get('t1_2', 0), s39.get('t1_3', 0), s39.get('t1_4', 0)]
            s39_2['qp1'] = [s39.get('qp_1', 0), s39.get('qp_2', 0), s39.get('qp_3', 0), s39.get('qp_4', 0)]
            s39_2['qo1'] = [s39.get('qo_1', 0), s39.get('qo_2', 0), s39.get('qo_3', 0), s39.get('qo_4', 0)]
            s39_2['qp2'] = [s39.get('qp_1gt5000', 0), s39.get('qp_2gt5000', 0), s39.get('qp_3gt5000', 0), s39.get('qp_4gt5000', 0)]
            s39_2['qo2'] = [s39.get('qo_1gt5000', 0), s39.get('qo_2gt5000', 0), s39.get('qo_3gt5000', 0), s39.get('qo_4gt5000', 0)]

            d = max(s39.get('d', 0), s39.get('dy', 0))

            look[s39.get('date', 1), s39.get('proklad', 'К')][d] = s39_2


    print(f'Закончил читать {tn2}', file=sys.stderr)




#-----------------------------------------------------------------------------------



def read_sprav(conn_str):

    conn_str_sprav = conn_str.copy()

    conn_str_sprav['db'] = 'sprav'

    conn = connect.connect(**conn_str_sprav)

    if conn:
        print(f'Начал читать {conn_str_sprav["db"]}', file=sys.stderr)

        read_tab2(conn, '30_koeffitsienty_mestnyh_teplovyh_poter', map_s30)
        read_tab2(conn, '28_Koeffitsienty_rascheta_balansovoy_nagruzki_GV', map_s28)
        read_tab2(conn, '07_Teploizolyatsionnyy_material', map_s07, id='kod_izol')
#        read_tab2(conn, '39_normy_teplovyh_poter', map_s39)

        read_tab_s39(conn, '39_normy_teplovyh_poter', map_s39)

        qqq = map_s39.get((1, 'К'), None)


        print(f'Закончил читать {conn_str_sprav["db"]}', file=sys.stderr)
    else:
        print(f'Начал читать csv', file=sys.stderr)
        read_csv2('30_koeffitsienty_mestnyh_teplovyh_poter', map_s30)
        read_csv2('28_Koeffitsienty_rascheta_balansovoy_nagruzki_GV', map_s28)
        read_csv2('07_Teploizolyatsionnyy_material', map_s07, id='kod_izol')
        
        read_csv_s39('39_normy_teplovyh_poter', map_s39)
        qqq = map_s39.get((1, 'К'), None)
        
        print(f'Закончил читать csv', file=sys.stderr)

#    print('---')
#    for k, v in qqq.items():
#        print(k, v)
#    print('---')

#    exit(1)


#-----------------------------------------------------------------------------------

if __name__ == "__main__":
    pass
