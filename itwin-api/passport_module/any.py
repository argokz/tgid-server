from functools import lru_cache
import os

from platformdirs import user_data_dir


#app_name = 'passport'
app_name = 'tgid'
app_author = 'Sirius' 

def readFile(fn):
    s = ''
    fn = os.path.dirname(os.path.abspath(__file__)) + '/' + fn

    try:
        with open(fn) as f:
            s = f.read()
    except:
        pass
        
    return s


@lru_cache(maxsize=None)
def argpath_2():
    path = user_data_dir(app_name, app_author, roaming=True)
    os.makedirs(path, exist_ok=True)
    return path
