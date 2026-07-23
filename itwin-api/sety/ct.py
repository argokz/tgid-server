map_ct = {}


import sety.teplo.gid_init

#-----------------------------------------------------------------------------------

def get_ct():
    if len(map_ct) == 0:
        return sety.teplo.gid_init.get_ct()

    ct = map_ct[next(iter(map_ct))]   # Система теплоснабжения
#    print(ct)
    return ct;

#-----------------------------------------------------------------------------------
