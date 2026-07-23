import networkx as nx
import numpy as np
import scipy as sp

import logging

from sety import w_print

#------------------------------------------------------

# Обработка регуляторов расхода и байпасов

def check_RR(G, list_rr, root):
    ferr = False

    j = 0

    logging.info(f'== Регуляторы расхода')

    for i in range(len(list_rr)):
        n1, n2, i1, i2, k_l, S, Z, r1, r2, key = list_rr[i]

#        print(f' r1={r1} r2={r2} S={S} Z={Z} ')

        name = w_print.line_name_n1_n2(G, n1, n2, False)

        if r1 != r2:
            
            nn1 = G.nodes[n1]['num']
            nn2 = G.nodes[n2]['num']

            geo1 = G.nodes[n1].get('geoMarkTopTube', 0)
            geo2 = G.nodes[n2].get('geoMarkTopTube', 0)

            dH =  root[nn1] - root[nn2]

            r_new = dH / Z / Z
            j += 1

#            print(f' r_new = {r_new} ')


#            print(n1, n2, r_new)

            prz_k = False

#            if r_new < r1 and r_new >= 0:
            if r_new < r1:
                logging.info(f' r_new < r1  {r_new} < {r1}      {dH}/{Z}/{Z}')
                r_new = r1
#                print(f' r_new le r1 ')
#                if S != r_new:
                prz_k = True

            elif r_new > r2:
                logging.info(f' r_new > r2 {r_new} > {r2}       {dH}/{Z}/{Z}')
#                print(f' r_new  ge  r2 ')
                r_new = r2
#                if S != r_new: 
                prz_k = True

            else:
#                print(f' else ')
                logging.info(f'?  {name} r_new={r_new:10f} r1={r1} r2={r2} Z={Z:10f} dH={dH} h1={root[nn1]-geo1} h2={root[nn2]-geo2}')
                continue

#            print('== Регулятор расхода', name)
#            print(f'r_new={r_new:10f} r1={r1} r2={r2} Z={Z:10f} dH={dH} h1={root[nn1]-geo1} h2={root[nn2]-geo2}')
            logging.info(f'  {name} r_new={r_new:10f} r1={r1} r2={r2} Z={Z:10f} dH={dH} h1={root[nn1]-geo1} h2={root[nn2]-geo2}')

            if prz_k:
                logging.info(f' За пределами')

                ferr = True
#                n1->ras -= Z
#                n2->ras += Z

                S = r_new
                r1 = S
                r2 = r1

                G.edges[n1, n2, key]['fixed'] = True

#                print(f'----- r1={r1} r2={r2} S={S} ferr={ferr}')
#                print(f'!!!! S={S}')


          
            else:
                pass
#                root[k_l] += Z
#                x[ll->n] += Z
            

        list_rr[i] = n1, n2, i1, i2, k_l, S, Z, r1, r2, key

    return ferr

