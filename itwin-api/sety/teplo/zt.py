from sety import read_gid
from sety import config

from sety import read_tg
from sety.ct import get_ct


# Возвращает температуру источника или узла с заданным напором


def getZT(G, node, curT):

    name = f'{node.get('kod')} {node.get('name')}'
                
    t0 = node.get('t0', None)
    if curT:
        return t0

    ist0 = node.get('ist0', None)

    if ist0 is None:
#       cprint(f'Не известен источник для узла с заданным напором [{name}]', color='red')
       return None

    if not ist0 is None:
        ct = get_ct()
        ist = read_gid.map_ist.get(ist0, None)

        if not ist:
#            cprint(f'Не известен источник для узла с заданным напором [{name}]', color='red')
            return None


        if config.args.is_leto:
            t70 = ist.get('t1_leto', 0)  # летняя температура источника
            return t70
        
        Tn_otop = ct.get('t_or')
        v = read_tg.get_tg(ist0, Tn_otop)
        
        if v is None:
#            print(ist)
#            cprint(f'[red]Нет Температурного графика в Источнике {ist0}[-]')
            return None
            exit(1)

        t1, t2, t3, tv = v
        t0 = t1

#        print(t0, Tn_otop, ist0, v)


#    print(node.get('typ','??'), node.get('name','??'), t0)

    return t0

