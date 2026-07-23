'''
from collections import namedtuple


def getS28():
    S28 = namedtuple('S28', 'pr sm ps pw o')

    s28 = S28(pr=1.15, sm=1.1, ps=1.25, pw=1.25, o=1)

    return s28

from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class S28:
    pr: float = 1.15
    sm: float = 1.1
    ps: float = 1.25
    pw: float = 1.25
    o : float = 1.0

'''
# один раз в модуле (вне функций!)
from collections import namedtuple

S28 = namedtuple('S28', ['pr', 'sm', 'ps', 'pw', 'o'])
S28_DEFAULT = S28(1.15, 1.1, 1.25, 1.25, 1.0)

# теперь функция может быть просто
def getS28():
    return S28_DEFAULT

