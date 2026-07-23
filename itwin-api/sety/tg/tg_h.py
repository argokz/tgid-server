import math

from dataclasses import dataclass

from datetime import datetime
from datetime import date

#----------------------------------------------------------

@dataclass
class Tg:
  KOL: int      = 0 # Количество точек расчета

  THOR: float   = -31.8 # Расчетная температура наружного воздуха
  TVR: float    = 18 # Расчетная температура воздуха внутри помещения
  TAURP: float  = 150 # Расчетная темп-ра сетевой воды в подающем трубопроводе
  TAURO: float  = 70 #      -"-                       в обратном
  TAURS: float  = 95 #      -"-                       после узла смешения
  QR: float     = 0 # Расчетная тепловая нагузка на отопление
  TSMIN: float  = -200 # Температура нижней срезки  сетевой воды
  TSMAX: float  = 200 # Температура верхней срезки сетевой воды
  T2MIN: float  = -200 # Температура нижней срезки обратной воды
  THK: float    = 8.2 # Температура наружного воздуха конца отопительного сезона
  TEC: str      = '' # Наименование ТЭЦ
  MAG: str      = '' # Наименование магистали
  GDN: date      = datetime.now() # Начало отопительного сезона
  GDK: date      = datetime.now() # Конец отопительного сезона
  KSR: float    = 2.2 # Поправка коэффициента смешения
  V: float      = 0 # Скорость ветра
  TB: float     = 18 # Требуемая температура воздуха внутри отап-х помещениях
  QMAX: float   = 1 # Отношение максимального количества тепла отпускаемого ТЭЦ
                # к расчетному теплу на отопление магистрали

#TT = namedtuple('QQ', 'qq bb', defaults = (None,) * 2)
#tt = TT()
#print(tt)

#----------------------------------------------------------

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

#----------------------------------------------------------

if __name__ == "__main__":
    tg = Tg(MAG = '567')
    print(tg)
