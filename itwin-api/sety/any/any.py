from functools import lru_cache

from platformdirs import user_data_dir

import inspect
import os
import sys

app_name = 'tgid'
app_author = 'Sirius' 

def debug(msg=""):
    frame = inspect.currentframe().f_back
    filename = os.path.basename(frame.f_code.co_filename)
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name
    print(f"[{filename}:{lineno} - {funcname}] {msg}")



def fatal_error_teplo():
    print('Фатальная ошибка с теплом')
    exit(1)


def fatal_error():
    print('Фатальная ошибка')
    exit(1)


@lru_cache(maxsize=None)
def argpath():
    script_path = os.path.abspath(__file__)
    main_script_path = os.path.abspath(sys.argv[0])
    path = os.path.dirname(main_script_path)
    return path


@lru_cache(maxsize=None)
def argpath_2():
    path = user_data_dir(app_name, app_author, roaming=True)
    os.makedirs(path, exist_ok=True)
    return path

@lru_cache(maxsize=None)
def get_gidr_path():
#    print (argpath())

    path = argpath()

#    print('!!', path)
#    exit(1)

#    if os.path.exists(f'{path}/sprav/GID.kls2'):
    return path

#    return 'C:/vc_projects/gid6/gidr'




