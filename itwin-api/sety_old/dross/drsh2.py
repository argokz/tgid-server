import math
"""
 ot - расход на отопление
 hrc - располагаемый напор

 diam_so  a14; 14.Диаметр сопла элеватора минимально допустимый,мм        
 k_smes   a6;  6.Коэффициент смешения элеватора                           

 dc       b7;  7. Диаметр сопла элеватора,мм                 
"""

from sety.dross.w_print import w_print

#include '../DREDIT1.H'


#short drsh2(double ot, double diam_so, double k_smes, double nap_ras, double *dc, double *hrc,double *nal,UZEL ptr)

def drsh2(ot, diam_so, k_smes, nap_ras, hrc, ptr_name): # , UZEL ptr)

#    dc, hrc, nal
   
#     char  *buf;
#     short  ferr=0;
#     double   dg;
# dc - Апарцев формула 7.5

    ferr = 0

    dc = 9.6*math.sqrt(abs(ot)/math.sqrt(hrc));


    if dc < diam_so: # Недостаточный располагаемый напор
        dc = diam_so
        hrc = 8493.47*ot*ot/(math.pow(dc, 4))
        ferr = 1

# dg - Диаметр горловины элеватора
# - Апарцев формула 7.2

    dg = 8.5 * math.sqrt(abs(ot)*(1.+k_smes)/math.sqrt(nap_ras))

# Выбор номера элеватора по диаметру горловины

    if dg <= 10.:
        nal = 0
    elif dg <= 15.:
        nal = 1
    elif dg <= 20.:
        nal = 2
    elif dg <= 25.:
        nal = 3
    elif dg <= 30.:
        nal = 4
    elif dg <= 35.:
        nal = 5
    elif dg <= 47.:
        nal = 6
    elif dg <= 59:
        nal = 7
    else:
        nal = 8
        w_print(f'Для потребителя {ptr_name} рассчитанный диаметр горловины') #,N3, ptr.a1,N10,ptr.a2);
        w_print(f'  элеватора превышает допустимый для элеватора N 7');
        w_print(f'Элеваторное смешение должно быть заменено на насосное смешение');
        nal = 7;

    return ferr, hrc, dc, nal


if __name__ == "__main__":

    hrc = 1
    ot = 1
    diam_so = 1
    k_smes = 1
    nap_ras = 1

    ferr, hrc, dc, nal = drsh2(ot, diam_so, k_smes, nap_ras, hrc) # , UZEL ptr)

    print(ferr, hrc, dc, nal)
    
