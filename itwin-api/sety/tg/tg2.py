import sys
import os

if not __package__:
    parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
    sys.path.append(os.path.abspath(os.path.join(parent_dir, '..', '..')))

# Расчет без срезки.

import math

from dataclasses import dataclass

from sety.tg.tg_h import Tg 
from sety.tg.tg_h import tg_range

'''
class tg_range:
    def __init__(self, tg1, tg2):
        self.tg1 = tg1
        self.tg2 = tg2
        self.tg = None
 
    def __iter__(self):
        return self
 
    def __next__(self):

        if self.tg is None:
            self.tg = self.tg1
            return self.tg1

        if self.tg2 > self.tg1:    
            dt = 1
        else:
            dt = -1

        if (self.tg >= self.tg2 and dt == 1) or (self.tg <= self.tg2 and dt == -1): 
            raise StopIteration

        self.tg += dt
        self.tg = math.floor(self.tg) if dt == 1 else math.ceil(self.tg)

        if (self.tg >= self.tg2 and dt == 1) or (self.tg <= self.tg2 and dt == -1): 
            self.tg = self.tg2

        return self.tg

def tg_range(tg1, tg2):
    tg = tg1
    yield tg

    if tg2 > tg1:
        tg += 1
        tg = math.floor(tg)
        while tg < tg2:
            yield tg
            tg += 1
    else:
        tg -= 1
        tg = math.floor(tg)
        while tg > tg2:
            yield tg
            tg -= 1

    yield tg2

'''

def CalculateOT1(tg: Tg, tn: float):

    TSMIN = tg.TSMIN
    TSMAX = tg.TSMAX
    QMAX = tg.QMAX

    tg.TSMIN = 0
    tg.TSMAX = 200
    tg.QMAX = 100000

    uf = tg.KSR

    DTAU = tg.TAURP - tg.TAURO
    TETA = tg.TAURS + tg.TAURO
    DTR = TETA / 2.0 - tg.TVR
    TETA = tg.TAURS - tg.TAURO

    qopc = (tg.TB - tn) / (tg.TVR - tg.THOR)

    tau01 = tn + qopc * (tg.TVR - tg.THOR + (0.5 + uf) * DTAU / (1 + uf) + DTR / pow(qopc, 0.2))

    tau02 = tau01 - DTAU * qopc
    tau03 = tau02 + TETA * qopc

    return pow(qopc, 0.2), tau01, tau02, tau03

if __name__ == "__main__":

    tg = Tg(MAG = '567')
#    print(tg)
    tn = 25

#    tg.TAURP = 132

    tg.KSR = (tg.TAURP-tg.TAURS)/(tg.TAURS-tg.TAURO)

    print(tg.KSR)

    print(tg_range(tg.THOR, tg.THK))

    tn = tg.THOR

#    while tn < tg.THK:
#       v = CalculateOT1(tg, tn)        

    kol = len(list(tg_range(tg.THOR, tg.THK)))

    print(len(list(tg_range(tg.THOR, tg.THK))))
    print(len(list(tg_range(tg.THOR, tg.THK))))

    for tn in tg_range(tg.THOR, tg.THK):
        v = CalculateOT1(tg, tn)
        print(tn, v)
