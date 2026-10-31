import re

import list_tab


#------------------------------------------------------------------------------------

def init_lookup():

    map_lookup = {}
    
    set_tab_l = {tn.lower() for tn in list_tab.list_tab}


    lf = 'C:/vc_projects/gid6/gidr/kls/GID.lookup'
    lf = 'GID.lookup'

    with open(lf, "r") as f:
        while True:
            line = f.readline()  #.decode('cp1251')
            if not line:
                break

#            if line[0:1] == '-': continue
            if line[0:1] != '"': continue

            m = re.match(r'^"(.+?)","(.+?)","(.+?)","(.+?)","(.+?),([0-9]+).*$', line)
            if m:
                tn1 = m.group(1)
                col = m.group(2)
                tn2 = m.group(3)

                if not tn1.lower() in set_tab_l: continue
                if tn2.lower() == 'vozdushnik': continue

                map_lookup[(tn1.lower(), col.lower())] = tn2

    set_tn = set()

    for a, tn in map_lookup.items():
        set_tn.add(tn.lower())
    
#    exit(0)

    return map_lookup, set_tn
#------------------------------------------------------------------------------------

if __name__ == "__main__":
    init_lookup()

    set_tn = set()

    for a, tn in map_lookup.items():
        set_tn.add(tn)

    for tn in set_tn:
        print(tn)
        
