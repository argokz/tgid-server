from collections import namedtuple


def getS28():
    S28 = namedtuple('S28', 'pr sm ps pw o')

    s28 = S28(pr=1.15, sm=1.1, ps=1.25, pw=1.25, o=1)

    return s28
