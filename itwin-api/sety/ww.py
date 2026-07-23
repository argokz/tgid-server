import sys
import os
import time
import logging
import traceback

import pyodbc
 
parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
sys.path.append(os.path.abspath(os.path.join(parent_dir, '..')))
#print(parent_dir)

from sety import config
from sety import w

from sety.any.colors import cprint

from sety.calc.copy_calc import connect_to_database
from sety.calc.copy_calc import copy_calc



#------------------------------------------------------


def run() -> None:

#   for i in pyodbc.drivers(): print(i)
#   exit(1)

    args = config.init()

#    json_str = config.get_args_json(args)
#    print(json_str)
#    exit(1)


    t1 = time.time()

    w.run(
          rdbms = args.rdbms,
          server = args.server, 
          user = args.user, 
          password = args.password, 
          db = args.database, 
          port = args.port, 
          files = {args.fileID}
    )

    t2 = time.time()
    print(f'Время расчета {t2-t1:0.2f} секунд', flush=True)


    if args.copy_calc:
    
        conn1 = connect_to_database(args.database, args.server, args.port, args.user, args.password)
        conn2 = connect_to_database(args.database2, args.server, args.port, args.user, args.password)
        
        print(f'Копирую данные в базу данных {args.database2}')

        copy_calc(conn1, conn2, args.fileID)

        print('Закончил копирование')

        conn1.close()
        conn2.close()



    logging.info(f'Время расчета {t2-t1} секунд')


if __name__ == "__main__":
    
    try:
        run()
    except Exception as e:
        cprint(f'Ошибка при выполнении!', color='red')
        cprint(f'{e}', color='red')
        print(traceback.format_exc())

        exit(1)

#    exit(1)