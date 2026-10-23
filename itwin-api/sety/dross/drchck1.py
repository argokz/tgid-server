
# [Claude 2026-10-18] Если kn != 0 - признак fss=1 и напор hk берется равным p_ras, иначе fss=0. Возвращает (fss, hk).
def drchck1(kn, p_ras, hk):
    if kn != 0.:
          fss = 1
          hk = p_ras
    else:
        fss = 0

    return fss, hk