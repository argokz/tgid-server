import math


def drsh3(kn, diam_sh, diam_fl, hrc):
    ferr = False


#    print('diam_sh', diam_sh)
#    diam_sh = 1

    dsh = 10. * math.sqrt(abs(kn)/math.sqrt(abs(hrc)))

    if dsh < diam_sh:
        dsh = diam_sh
        hrc = 10000.*kn*kn/math.pow(dsh, 4)
        ferr = True

    return ferr, hrc, dsh
