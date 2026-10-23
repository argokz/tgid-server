import math

# [Claude 2026-10-18] Диаметр шайбы (мм) по расходу ot и требуемому напору hz: 10*sqrt(|ot|/sqrt(hz)).
def drsh1(ot, hz):

    dsh = 10.* math.sqrt(abs(ot)/math.sqrt(hz))

    return dsh
