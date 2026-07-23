import sys
import os
import time
import logging

import pyodbc
 
parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
sys.path.append(os.path.abspath(os.path.join(parent_dir, '..')))
#print(parent_dir)

from sety import config
from sety import w



#------------------------------------------------------

def run() -> None:

#   for i in pyodbc.drivers(): print(i)
#   exit(0)

    args = config.init()

    t1 = time.time()

    w.run(
          rdbms = args.rdbms,
          server = args.server, 
          user = args.user, 
          password = args.password, 
          db = args.database, 
          port = args.port, 
          files = {args.fileID})

    t2 = time.time()
    print(f'Время расчета {t2-t1:0.2f} секунд', flush=True)

    logging.info(f'Время расчета {t2-t1} секунд')


if __name__ == "__main__":
    run()
