# Расчет ТГ со срезкой
import sys
import os

if not __package__:
    parent_dir = os.path.dirname(os.path.abspath(__file__))  # Получаем путь к текущему файлу
    sys.path.append(os.path.abspath(os.path.join(parent_dir, '..', '..')))

from dataclasses import dataclass

from sety.tg.tg_h import Tg 
from sety.tg.tg_h import tg_range

#-----------------------------------------------

def CalculateOT1(tg: Tg, tn: float, is_srezki: bool):
    ex = 0.001
    pr = 0  # # Спросить у Надежды Ивановны

    TSMIN = tg.TSMIN
    TSMAX = tg.TSMAX
    QMAX = tg.QMAX

    if not is_srezki:
        tg.TSMIN = 0
        tg.TSMAX = 200
        tg.QMAX = 100000

    uf = tg.KSR
    #  if(tg.TAURP == tg.TAURS)
    #    uf = 0 # добвалено 27.02.2002

    DTAU = tg.TAURP - tg.TAURO
    TETA = tg.TAURS + tg.TAURO
    DTR = TETA / 2.0 - tg.TVR
    TETA = tg.TAURS - tg.TAURO

    tm = 1
    tbn = tg.TB
    qopc = (tg.TB - tn) / (tg.TVR - tg.THOR)


#    print('qopc', qopc)


    qq = qopc
    n = 100

    while True:
#    do {
        ex = 0.01              # по дефициту мощности
        tau01 = tn + qopc * (tg.TVR - tg.THOR + (0.5 + uf) * DTAU / (1 + uf) + DTR / pow(qopc, 0.2))

        qocn = qopc
        qoc = qocn

        while True:
#        do {                    # по нижней верхней срезке
            tau02 = tau01 - DTAU * qopc
            tau03 = tau02 + TETA * qopc

            while True:
#            do {                  # Температура внутри помещения
                qoc = qocn
                tb = tn + (tg.TB - tn) * qoc / qq  # qopc ????

                # соответствует Qo/QOR ( см. Зингер стр.160 )
                qocn = (tau01 - tb) / ((0.5 + uf) / (1 + uf) * DTAU + DTR / pow(qoc, 0.2))
                eq = (qoc - qocn) / qoc  

                if eq < 0: 
                    eq = -eq

                if not eq > ex: break
#            } while (eq > ex)


#            print(tg)

            if tau01 < tg.TSMIN or tau01 > tg.TSMAX or tau02 < tg.T2MIN:
                # срезка
                if tau01 < tg.TSMIN :
                    tm = 0 
                    tau01 = tg.TSMIN
                if tau01 > tg.TSMAX: 
                    tm = 0 
                    tau01 = tg.TSMAX

                if tau02 < tg.T2MIN:
                    tm = 0
                    if tau01 < tg.TSMAX: 
                        tau01 = tau01 + 0.05
                    else: tm = 1

                while True:
#                do {
                    qocn = (tau01 - tb) / ((0.5 + uf) / (1 + uf) * DTAU + DTR / pow(qoc, 0.2))
#                    print(f'==tau01={tau01} tb={tb} qocn={qocn} uf={uf}')
                    
                    eq = (qoc - qocn) / qoc 
                    if eq < 0: 
                        eq = -eq

                    qoc = qocn
                    tb = tn + (tg.TB - tn) * qoc / qq
                    if not eq > ex: break
#                } while (eq > ex)

                qopc = qocn
            else:
                 tm = 1

            if not tm == 0: break
#        } while (tm == 0) # по нижней верхней срезке

        if qoc > tg.QMAX and n >= 1:
            qopc = tg.QMAX
            tbn = tn + qopc * (tg.TB - tn) / qq
            data.defm = (tg.QMAX - qq) * 100 / tg.QMAX
            if data.defm < 0: 
                data.defm = -data.defm

            qopc = (tbn - tn) / (tg.TVR - tg.THOR)
            dq = ex + 1
            n -= 1
        else:
            dq = ex - 1

        if not dq > ex: break
#    } while (dq > ex)

    QO = qocn

    if tg.V > 3:      # Поправка на ветер

        tau01v = tau01 + (tau01 - tg.TB) * (tg.V / 100)
        qocnv = qocn
        while True:
#        do {
            qocv = qocnv
            if pr == 1: 
                tbv = tg.TB
            else:        
                tbv = tn + (tg.TB - tn) * qocv / qq
            qocnv = (tau01v - tbv) / ((0.5 + uf) / (1 + uf) * DTAU + DTR / pow(qocv, 0.2))
            eq = (qocv - qocnv) / qocv 
            if eq < 0:
                eq = -eq
            if not eq > ex: break
#        } while (eq > ex)

        if qocnv > tg.QMAX:
            qocnv = tg.QMAX
            tbn = tn + qocnv * (tg.TB - tn) / qq
            qocnv = (tbn - tn) / (tg.TVR - tg.THOR)
            tau01v = tn + qocnv * (tg.TVR - tg.THOR + (0.5 + uf) * DTAU / (1 + uf) + DTR / pow(qocnv, 0.2))

        if tau01 <= tg.TSMIN: tau01v = tg.TSMIN # срезка
        if tau01v > tg.TSMAX: tau01v = tg.TSMAX

    else: 
        tau01v = tau01

    tg.TSMIN = TSMIN
    tg.TSMAX = TSMAX
    tg.QMAX = QMAX

    return tau01, tau02, tau03, tb, QO, tau01v

#-----------------------------------------------

def find_izlom(tg, t_izlom):
    tn1 = tg.THOR
    tn2 = tg.THK

    if t_izlom == 0:
        return tn2

    while True:
        tn = (tn1+tn2)/2

        v = CalculateOT1(tg, tn, False)

        if not v: 
            break
        

        tau01, tau02, tau03, tb, QO, tau01v = v


        if tau01 < t_izlom:
            tn2 = tn
        else:
            tn1 = tn

        if abs(tau01-t_izlom) < 0.001 or abs(tn1 - tn2) < 0.001: 
            return tn

    return 0

#-----------------------------------------------

def make_tg(tgm):
    tg = Tg()  

#    tg.KOL: int      = 0            # Количество точек расчета
                                 
    tg.THOR = tgm.get("tn_5")        # Расчетная температура наружного воздуха
    tg.TVR = tgm.get("tvn_r")        # Расчетная температура воздуха внутри помещения
    tg.TAURP = tgm.get('t1_r', 0)       # Расчетная темп-ра сетевой воды в подающем трубопроводе
    tg.TAURO = tgm.get('t2_r', 0)       #      -"-                       в обратном
    tg.TAURS = tgm.get('t3_r', 0)       #      -"-                       после узла смешения
    tg.QR = tgm.get("q_r")           # Расчетная тепловая нагузка на отопление
    tg.TSMIN = tgm.get("t1_2r", 0)   # Температура нижней срезки сетевой воды
    tg.TSMAX = tgm.get("t1_4r",200)  # Температура верхней срезки сетевой воды
    tg.T2MIN = tgm.get("t2_2r", 0)   # Температура нижней срезки обратной воды
    tg.THK = tgm.get("tn_1")         # Температура наружного воздуха конца отопительного сезона
#    tg.TEC = tgm.get("")            # Наименование ТЭЦ
#    tg.MAG = tgm.get("")            # Наименование магистали
#    tg.GDN = tgm.get("")            # Начало отопительного сезона
#    tg.GDK = tgm.get("")            # Конец отопительного сезона
    tg.KSR = tgm.get("uf", 0)        # Поправка коэффициента смешения
    tg.V = tgm.get("v", 0)           # Скорость ветра
    tg.TB = tgm.get("tvb_tr")        # Требуемая температура воздуха внутри отап-х помещениях
    tg.QMAX = tgm.get("")            # Отношение максимального количества тепла отпускаемого ТЭЦ
                                     # к расчетному теплу на отопление магистрали

    tg.KOL = len(list(tg_range(tg.THK, tg.THOR))) # Количество точек расчета

    return tg                  

#-----------------------------------------------


#-----------------------------------------------

if __name__ == "__main__":

    print(__package__)
    print(os.path.dirname(__file__))

    os.path.abspath(os.path.dirname(__file__))
    tg = Tg(MAG = '567')
    print(tg)
    tn = 25

    tg.TAURP = 132
    tg.KSR = (tg.TAURP-tg.TAURS)/(tg.TAURS-tg.TAURO)

    v = CalculateOT1(tg, -25, True)

    t_izl = find_izlom(tg, 60)

    print(t_izl)


#    print(v)

